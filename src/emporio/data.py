"""Loads the store CSVs into a cleaned, query-ready in-memory model.

Business rules that must never be left to the LLM (effective price, availability,
promotion validity) are computed here, once, so every tool returns consistent facts.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

PIX_DISCOUNT = 0.05

# Brands that appear in the catalogue. Used to detect descriptions that talk about
# a different instrument than the product name (e.g. "Music Man Bass 1X" described
# as a "Fender Jazz Bass") — those descriptions are unreliable and are dropped.
KNOWN_BRANDS = [
    "Yamaha", "Tagima", "Giannini", "Rozini", "Shelby", "Crafter", "Martin", "Taylor",
    "Takamine", "Kala", "Ohana", "Kalani", "Fender", "Gibson", "Ibanez", "PRS",
    "Music Man", "Pearl", "Tama", "Korg", "Nord", "Roland",
]

PRODUCT_STATUS_LABELS = {
    "active": "ativo",
    "discontinued": "descontinuado (fora de catálogo)",
    "coming_soon": "em breve (ainda não disponível para venda)",
}

ORDER_STATUS_LABELS = {
    "pending": "aguardando pagamento/processamento",
    "confirmed": "pagamento confirmado, em separação",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}


def _brands_in(text: str) -> set[str]:
    return {b for b in KNOWN_BRANDS if re.search(rf"\b{re.escape(b)}\b", text, re.IGNORECASE)}


def description_is_consistent(name: str, description: str) -> bool:
    """False when the description mentions a brand that is not the product's own brand."""
    name_brands = _brands_in(name)
    desc_brands = _brands_in(description)
    return not desc_brands or not name_brands or desc_brands <= name_brands


def format_payment_method(code: str) -> str:
    if code.startswith("credit_"):
        return f"cartão de crédito em {code.removeprefix('credit_')}"
    return {"pix": "PIX", "debit": "cartão de débito", "boleto": "boleto bancário"}.get(code, code)


@dataclass(frozen=True)
class Store:
    products: pd.DataFrame
    categories: pd.DataFrame
    orders: pd.DataFrame
    order_items: pd.DataFrame
    customers: pd.DataFrame


def _build_products(raw: pd.DataFrame, categories: pd.DataFrame, promotions: pd.DataFrame) -> pd.DataFrame:
    p = raw.merge(categories[["category_id", "name"]].rename(columns={"name": "category"}), on="category_id", how="left")

    consistent = [description_is_consistent(n, d) for n, d in zip(p["name"], p["description"])]
    p["description_reliable"] = consistent
    p.loc[~p["description_reliable"], "description"] = ""

    p["specs"] = p["specs"].apply(lambda s: json.loads(s) if isinstance(s, str) and s else {})

    # Only active promotions count; if a product had more than one, the best one wins.
    active = (
        promotions[promotions["is_active"] == 1]
        .sort_values("discount_percent", ascending=False)
        .drop_duplicates("product_id")[["product_id", "discount_percent", "description"]]
        .rename(columns={"description": "promotion_name"})
    )
    p = p.merge(active, on="product_id", how="left")
    p["discount_percent"] = p["discount_percent"].fillna(0).astype(int)
    p["final_price_brl"] = (p["price_brl"] * (1 - p["discount_percent"] / 100)).round(2)
    # PIX discount is not cumulative with promotions.
    on_promo = p["discount_percent"] > 0
    p["pix_price_brl"] = p["final_price_brl"].where(on_promo, (p["price_brl"] * (1 - PIX_DISCOUNT)).round(2))

    p["available"] = (p["status"] == "active") & (p["stock_quantity"] > 0)
    return p.sort_values("product_id").reset_index(drop=True)


def _build_orders(orders: pd.DataFrame, items: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    o = orders.copy()
    for col in ("order_date", "estimated_delivery"):
        o[col] = pd.to_datetime(o[col], errors="coerce").dt.date
    o["tracking_code"] = o["tracking_code"].fillna("")
    o["notes"] = o["notes"].fillna("")

    priced = items.merge(products[["product_id", "price_brl"]], on="product_id", how="left")
    priced["line_total"] = priced["quantity"] * priced["price_brl"]
    items_total = priced.groupby("order_id")["line_total"].sum().rename("items_total_brl")
    o = o.merge(items_total, on="order_id", how="left")
    # Two orders have a stored total that differs from the sum of their items (likely a
    # manual discount or a later price change). The stored total is what was charged, so
    # it is the one shown to customers; the mismatch is kept as a flag for the team.
    o["total_mismatch"] = (o["total_brl"] - o["items_total_brl"]).abs() > 0.01
    return o


@lru_cache
def load_store(raw_dir: Path = RAW_DIR) -> Store:
    read = lambda name: pd.read_csv(raw_dir / f"{name}.csv")  # noqa: E731
    categories = read("categories")
    products = _build_products(read("products"), categories, read("promotions"))
    items = read("order_items")
    orders = _build_orders(read("orders"), items, products)
    customers = read("customers")
    customers["email"] = customers["email"].str.strip().str.lower()
    customers["phone_digits"] = customers["phone"].str.replace(r"\D", "", regex=True)
    return Store(products, categories, orders, items, customers)
