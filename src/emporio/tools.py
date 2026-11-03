"""Tools exposed to the LLM.

Each tool is a plain function returning a JSON-serialisable dict, plus an explicit
JSON schema in TOOL_SCHEMAS. Decisions with business impact (price, availability,
return eligibility, identity checks) are made here, deterministically; the LLM only
chooses which tool to call and phrases the answer.
"""

import json
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from emporio import clock
from emporio.data import ORDER_STATUS_LABELS, PRODUCT_STATUS_LABELS, format_payment_method, load_store
from emporio.policies import load_policies

TICKETS_DIR = Path(__file__).resolve().parents[2] / "tickets"

MATCH_THRESHOLD = 60
RETURN_REGRET_DAYS = 7
EXCHANGE_PREFERENCE_DAYS = 7
EXCHANGE_DEFECT_DAYS = 30
LEGAL_WARRANTY_DAYS = 90

# (open, close) per weekday, Monday=0. None = closed.
STORE_HOURS = {0: (9, 18), 1: (9, 18), 2: (9, 18), 3: (9, 18), 4: (9, 18), 5: (9, 13), 6: None}
WEEKDAYS_PT = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


# (min installments, max installments, minimum installment value) — policy section 3.1
INSTALLMENT_TIERS = [(7, 12, 100.0), (4, 6, 80.0), (1, 3, 50.0)]


def max_installments(price: float) -> int:
    """Largest interest-free installment count allowed for a price (policy section 3.1)."""
    for low, high, minimum in INSTALLMENT_TIERS:
        for n in range(high, low - 1, -1):
            if price / n >= minimum:
                return n
    return 1


# --------------------------------------------------------------------------- products

def _product_summary(row: pd.Series) -> dict:
    summary = {
        "product_id": int(row["product_id"]),
        "name": row["name"],
        "category": row["category"],
        "price_brl": float(row["price_brl"]),
        "available": bool(row["available"]),
        "status": PRODUCT_STATUS_LABELS.get(row["status"], row["status"]),
    }
    if row["discount_percent"] > 0:
        summary["promotion"] = {
            "name": row["promotion_name"],
            "discount_percent": int(row["discount_percent"]),
            "promotional_price_brl": float(row["final_price_brl"]),
        }
        summary["pix_price_brl"] = float(row["pix_price_brl"])
        summary["pix_note"] = "Produto já em promoção: o desconto de 5% no PIX NÃO se aplica (não é cumulativo)."
    else:
        summary["pix_price_brl"] = float(row["pix_price_brl"])
    if row["status"] == "active" and row["stock_quantity"] == 0:
        summary["status"] = "temporariamente sem estoque"
    return summary


def _fuzzy_rank(products: pd.DataFrame, query: str) -> pd.DataFrame:
    choices = (products["name"] + " " + products["category"]).tolist()
    scores = [fuzz.WRatio(query, c, processor=str.lower) for c in choices]
    ranked = products.assign(score=scores)
    return ranked[ranked["score"] >= MATCH_THRESHOLD].sort_values("score", ascending=False)


def search_products(
    query: str = "",
    category: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    only_available: bool = True,
    limit: int = 8,
) -> dict:
    products = load_store().products
    if category:
        products = products[products["category"] == category]
    if min_price is not None:
        products = products[products["final_price_brl"] >= min_price]
    if max_price is not None:
        products = products[products["final_price_brl"] <= max_price]
    products = _fuzzy_rank(products, query) if query.strip() else products.sort_values("final_price_brl")

    unavailable = products[~products["available"]]
    if only_available:
        products = products[products["available"]]

    result = {
        "total_found": len(products),
        "products": [_product_summary(r) for _, r in products.head(limit).iterrows()],
    }
    if only_available and len(unavailable):
        result["unavailable_matches"] = [_product_summary(r) for _, r in unavailable.head(3).iterrows()]
    if not result["products"] and category and load_store().products.query("category == @category").empty:
        result["note"] = f"No momento não há nenhum produto cadastrado na categoria '{category}'."
    return result


def _alternatives(product: pd.Series, n: int = 3) -> list[dict]:
    products = load_store().products
    same_cat = products[
        (products["category_id"] == product["category_id"])
        & products["available"]
        & (products["product_id"] != product["product_id"])
    ]
    closest = same_cat.assign(diff=(same_cat["price_brl"] - product["price_brl"]).abs()).nsmallest(n, "diff")
    return [_product_summary(r) for _, r in closest.iterrows()]


def get_product_details(product_name: str) -> dict:
    ranked = _fuzzy_rank(load_store().products, product_name)
    if ranked.empty:
        return {"found": False, "message": f"Nenhum produto encontrado para '{product_name}'."}

    best = ranked.iloc[0]
    details = _product_summary(best)
    details["stock_quantity"] = int(best["stock_quantity"])
    details["description"] = best["description"] or None
    details["specs"] = best["specs"]
    n = max_installments(float(best["final_price_brl"]))
    details["credit_card"] = {
        "max_installments_no_interest": n,
        "installment_value_brl": round(float(best["final_price_brl"]) / n, 2),
    }
    result = {"found": True, "product": details}

    # Ambiguous match: let the model ask the customer which one they meant.
    close = ranked[(ranked["score"] >= best["score"] - 3) & (ranked["product_id"] != best["product_id"])]
    if len(close):
        result["other_possible_matches"] = close.head(3)["name"].tolist()
    if not best["available"]:
        result["similar_available_alternatives"] = _alternatives(best)
    return result


def get_active_promotions() -> dict:
    products = load_store().products
    promo = products[(products["discount_percent"] > 0) & products["available"]]
    return {
        "today": clock.today().isoformat(),
        "active_campaigns": sorted(promo["promotion_name"].unique().tolist()),
        "active_promotions": [_product_summary(r) for _, r in promo.iterrows()],
        "note": "Somente estas promoções estão ativas. Uma campanha que não está em active_campaigns "
        "(ex.: Black Friday, Semana do Músico) NÃO está ativa: diga isso claramente e, se quiser, "
        "apresente estas ofertas pelo nome real delas.",
    }


# ----------------------------------------------------------------------------- orders

def _verify_customer(order: pd.Series, email_or_phone: str) -> bool:
    customers = load_store().customers
    match = customers[customers["customer_id"] == order["customer_id"]]
    if match.empty:
        return False
    customer = match.iloc[0]
    given = email_or_phone.strip().lower()
    digits = "".join(ch for ch in given if ch.isdigit())
    if "@" in given:
        return given == customer["email"]
    # Accept phone with or without area code.
    return len(digits) >= 8 and customer["phone_digits"].endswith(digits[-9:] if len(digits) >= 9 else digits)


def _find_verified_order(order_id: int, email_or_phone: str) -> tuple[pd.Series | None, dict | None]:
    if int(order_id) <= 0:
        return None, {
            "verified": False,
            "missing": "order_id_and_contact",
            "message": "O cliente ainda não informou o número do pedido. Peça o número do pedido e o e-mail "
            "ou telefone do cadastro. Não invente números de pedido.",
        }
    if not email_or_phone.strip():
        # Calling with only the order number is allowed on purpose: the order id then lives
        # in the conversation as a tool call and the model does not ask for it again.
        return None, {
            "verified": False,
            "order_id": int(order_id),
            "missing": "email_or_phone",
            "message": "Peça o e-mail ou telefone do cadastro para confirmar a identidade e depois chame a "
            "ferramenta de novo com o mesmo order_id.",
        }
    orders = load_store().orders
    match = orders[orders["order_id"] == int(order_id)]
    # Same message whether the order does not exist or the contact is wrong, so the tool
    # cannot be used to discover which order numbers exist (LGPD).
    failure = {
        "verified": False,
        "message": "Não foi possível localizar o pedido com esses dados. Peça ao cliente para conferir "
        "o número do pedido e o e-mail ou telefone cadastrado.",
    }
    if match.empty or not _verify_customer(match.iloc[0], email_or_phone):
        return None, failure
    return match.iloc[0], None


def _order_items(order_id: int) -> list[dict]:
    store = load_store()
    items = store.order_items[store.order_items["order_id"] == order_id].merge(
        store.products[["product_id", "name"]], on="product_id", how="left"
    )
    return [{"product": r["name"], "quantity": int(r["quantity"])} for _, r in items.iterrows()]


def get_order_status(order_id: int, email_or_phone: str = "") -> dict:
    order, error = _find_verified_order(order_id, email_or_phone)
    if error:
        return error

    customers = load_store().customers
    first_name = customers.loc[customers["customer_id"] == order["customer_id"], "name"].iloc[0].split()[0]
    today = clock.today()
    result = {
        "verified": True,
        "customer_first_name": first_name,
        "order_id": int(order["order_id"]),
        "order_date": order["order_date"].isoformat(),
        "status": ORDER_STATUS_LABELS.get(order["status"], order["status"]),
        "items": _order_items(int(order["order_id"])),
        "total_brl": float(order["total_brl"]),
        "payment_method": format_payment_method(order["payment_method"]),
    }
    if order["tracking_code"]:
        result["tracking_code"] = order["tracking_code"]
    if isinstance(order["estimated_delivery"], date):
        result["estimated_delivery"] = order["estimated_delivery"].isoformat()
        if order["status"] == "shipped" and order["estimated_delivery"] < today:
            result["delayed_days"] = (today - order["estimated_delivery"]).days
            result["action"] = "Pedido atrasado: peça desculpas e ofereça abrir um chamado (create_support_ticket)."
    if order["status"] in ("pending", "confirmed"):
        days_open = (today - order["order_date"]).days
        if days_open > 10:
            result["days_since_order"] = days_open
            result["action"] = "Pedido parado há muito tempo: ofereça abrir um chamado para a equipe verificar."
    if order["notes"]:
        result["notes"] = order["notes"]
    return result


def check_return_eligibility(order_id: int, reason: str, email_or_phone: str = "") -> dict:
    """Applies sections 4.1–4.4 and 8 of the policy manual to a specific order."""
    order, error = _find_verified_order(order_id, email_or_phone)
    if error:
        return error

    today = clock.today()
    base = {"verified": True, "order_id": int(order["order_id"]), "reason": reason, "today": today.isoformat()}

    if order["status"] == "cancelled":
        return {**base, "eligible": False, "explanation": "O pedido já está cancelado."}
    if order["status"] != "delivered":
        return {
            **base,
            "eligible": None,
            "explanation": "O pedido ainda não foi entregue, então não se trata de devolução. O cliente pode "
            "solicitar o cancelamento; isso precisa ser feito pela equipe (abra um chamado).",
        }

    # The data has no actual delivery date; the estimated delivery date is used as a
    # proxy for the date the customer received the product (documented assumption).
    received = order["estimated_delivery"]
    purchased = order["order_date"]
    days_since_receipt = (today - received).days
    days_since_purchase = (today - purchased).days
    base.update(received_on=received.isoformat(), days_since_receipt=days_since_receipt)

    if reason == "arrependimento":
        eligible = days_since_receipt <= RETURN_REGRET_DAYS
        explanation = (
            f"Dentro do prazo de {RETURN_REGRET_DAYS} dias corridos do direito de arrependimento."
            if eligible
            else f"Prazo de arrependimento ({RETURN_REGRET_DAYS} dias corridos após o recebimento) encerrado "
            f"há {days_since_receipt - RETURN_REGRET_DAYS} dias."
        )
        conditions = "Produto na embalagem original, sem uso, com acessórios e manuais. Reembolso na forma de " \
            "pagamento original em até 10 dias úteis; frete de devolução por conta da loja."
    elif reason == "preferencia":
        eligible = days_since_receipt <= EXCHANGE_PREFERENCE_DAYS
        explanation = (
            "Dentro do prazo de troca por preferência." if eligible
            else f"Prazo de troca por preferência ({EXCHANGE_PREFERENCE_DAYS} dias) encerrado."
        )
        conditions = "Produto em perfeito estado e na embalagem original; sujeito à disponibilidade do item " \
            "desejado; diferenças de valor cobradas ou reembolsadas."
    elif reason == "defeito":
        eligible = days_since_purchase <= EXCHANGE_DEFECT_DAYS
        if eligible:
            explanation = f"Dentro do prazo de troca por defeito ({EXCHANGE_DEFECT_DAYS} dias corridos após a compra)."
        elif days_since_receipt <= LEGAL_WARRANTY_DAYS:
            explanation = (
                f"Fora do prazo de troca direta na loja ({EXCHANGE_DEFECT_DAYS} dias), mas dentro da garantia legal "
                f"de {LEGAL_WARRANTY_DAYS} dias: acionar a garantia; a loja pode intermediar com o fabricante."
            )
        else:
            explanation = (
                "Fora do prazo de troca direta e da garantia legal; ainda pode haver garantia do fabricante "
                "(6 meses a 2 anos, conforme certificado). A loja pode intermediar o contato."
            )
        conditions = "Não cobre mau uso, quedas, umidade excessiva, modificações não autorizadas ou desgaste natural."
    else:
        return {**base, "eligible": None, "explanation": "Motivo inválido. Use: arrependimento, defeito ou preferencia."}

    result = {**base, "eligible": eligible, "explanation": explanation, "conditions": conditions,
              "not_eligible_items": "Itens personalizados/com setup sob encomenda, liquidação 'venda final' e "
              "boquilhas de sopro não são elegíveis para troca."}
    if eligible:
        result["next_step"] = "Oferecer abrir um chamado (create_support_ticket, categoria 'devolucao') para a " \
            "equipe dar andamento."
    elif reason != "defeito":
        # Regret and preference share the same 7-day window: if one is closed, so is the other.
        result["exchange_for_other_model"] = (
            f"Não disponível: o prazo de troca por preferência ({EXCHANGE_PREFERENCE_DAYS} dias) também está encerrado."
        )
        result["only_remaining_option"] = (
            "Garantia, apenas se houver defeito de fabricação: legal de "
            f"{LEGAL_WARRANTY_DAYS} dias após o recebimento e, depois, a do fabricante (6 meses a 2 anos); "
            "a loja pode intermediar."
        )
        result["ask_customer"] = "O instrumento apresenta algum defeito?"
    return result


# ---------------------------------------------------------------------- store / policy

def get_store_policy(section: str) -> dict:
    policies = load_policies()
    if section not in policies:
        return {"error": f"Seção desconhecida. Opções: {', '.join(policies)}"}
    return {"section": section, **policies[section]}


def check_store_hours() -> dict:
    now = clock.now()
    hours = STORE_HOURS[now.weekday()]
    is_open = hours is not None and hours[0] <= now.hour < hours[1]

    next_open = None
    for offset in range(0, 8):
        day = now + timedelta(days=offset)
        h = STORE_HOURS[day.weekday()]
        if h and (offset > 0 or now.hour < h[0]):
            next_open = f"{WEEKDAYS_PT[day.weekday()]} ({day.date().isoformat()}) às {h[0]:02d}:00"
            break

    return {
        "now": now.strftime("%Y-%m-%d %H:%M"),
        "weekday": WEEKDAYS_PT[now.weekday()],
        "is_open_now": is_open,
        "closes_at": f"{hours[1]:02d}:00" if is_open else None,
        "next_opening": None if is_open else next_open,
        "weekly_hours": "Segunda a sexta 09:00–18:00; sábado 09:00–13:00; domingo fechado.",
        "holidays": "Fechado em feriados (datas de feriado não constam no sistema).",
    }


def create_support_ticket(summary: str, category: str, customer_contact: str = "", order_id: int | None = None) -> dict:
    TICKETS_DIR.mkdir(exist_ok=True)
    ticket_id = f"EM-{uuid.uuid4().hex[:6].upper()}"
    ticket = {
        "ticket_id": ticket_id,
        "created_at": clock.now().isoformat(timespec="minutes"),
        "category": category,
        "summary": summary,
        "customer_contact": customer_contact,
        "order_id": order_id,
    }
    (TICKETS_DIR / f"{ticket_id}.json").write_text(json.dumps(ticket, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ticket_id": ticket_id, "sla": "Retorno da equipe em até 24 horas úteis."}


# --------------------------------------------------------------------------- registry

def _category_names() -> list[str]:
    return load_store().categories["name"].tolist()


def _fn(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required or []},
        },
    }


_CONTACT = {"type": "string", "description": "E-mail ou telefone do cliente, usado para confirmar a identidade."}
_ORDER_ID = {"type": "integer", "description": "Número do pedido."}

TOOL_SCHEMAS = [
    _fn(
        "search_products",
        "Busca produtos no catálogo com filtros. Use para perguntas sobre opções, faixa de preço ou "
        "disponibilidade de um tipo de instrumento. Preços já consideram promoções ativas.",
        {
            "query": {"type": "string", "description": "Termo livre (marca, modelo, tipo). Opcional."},
            "category": {"type": "string", "enum": _category_names(), "description": "Categoria. Opcional."},
            "min_price": {"type": "number", "description": "Preço mínimo em R$. Opcional."},
            "max_price": {"type": "number", "description": "Preço máximo em R$. Opcional."},
            "only_available": {"type": "boolean", "description": "Somente itens disponíveis (padrão true)."},
        },
    ),
    _fn(
        "get_product_details",
        "Detalhes, preço, estoque e especificações de UM produto específico pelo nome/modelo.",
        {"product_name": {"type": "string", "description": "Nome ou modelo, ex.: 'Takamine GD20'."}},
        ["product_name"],
    ),
    _fn("get_active_promotions", "Lista as promoções ativas hoje no sistema.", {}),
    _fn(
        "get_order_status",
        "Consulta status, itens, rastreamento e previsão de entrega de um pedido. Chame assim que souber o "
        "número do pedido; se ainda não tiver o e-mail/telefone, a ferramenta indica o que pedir ao cliente.",
        {"order_id": _ORDER_ID, "email_or_phone": _CONTACT},
        ["order_id"],
    ),
    _fn(
        "check_return_eligibility",
        "Verifica se um pedido pode ser devolvido ou trocado, aplicando as regras da loja ao caso. "
        "Chame assim que souber o número do pedido; a ferramenta indica se falta o e-mail/telefone.",
        {
            "order_id": _ORDER_ID,
            "email_or_phone": _CONTACT,
            "reason": {"type": "string", "enum": ["arrependimento", "defeito", "preferencia"]},
        },
        ["order_id", "reason"],
    ),
    _fn(
        "get_store_policy",
        "Consulta uma seção do manual de políticas da loja (endereço/contato, horários, pagamento e "
        "parcelamento, trocas e devoluções, frete, promoções, garantia, privacidade).",
        {"section": {"type": "string", "enum": list(load_policies())}},
        ["section"],
    ),
    _fn("check_store_hours", "Informa se a loja está aberta agora e quando abre/fecha.", {}),
    _fn(
        "create_support_ticket",
        "Abre um chamado para a equipe humana (reclamação, atraso, cancelamento, caso não coberto). "
        "Use somente depois que o cliente concordar.",
        {
            "summary": {"type": "string", "description": "Resumo do problema."},
            "category": {"type": "string", "enum": ["reclamacao", "atraso", "cancelamento", "devolucao", "outro"]},
            "customer_contact": {"type": "string"},
            "order_id": _ORDER_ID,
        },
        ["summary", "category"],
    ),
]

TOOLS = {
    "search_products": search_products,
    "get_product_details": get_product_details,
    "get_active_promotions": get_active_promotions,
    "get_order_status": get_order_status,
    "check_return_eligibility": check_return_eligibility,
    "get_store_policy": get_store_policy,
    "check_store_hours": check_store_hours,
    "create_support_ticket": create_support_ticket,
}


def call_tool(name: str, arguments: dict) -> dict:
    """Dispatch a tool call from the model; errors are returned to the model, never raised."""
    if name not in TOOLS:
        return {"error": f"Ferramenta desconhecida: {name}"}
    try:
        return TOOLS[name](**(arguments or {}))
    except (TypeError, ValueError, KeyError) as exc:
        return {"error": f"Argumentos inválidos para {name}: {exc}"}
