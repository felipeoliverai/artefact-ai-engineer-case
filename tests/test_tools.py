import pytest

from emporio import tools
from emporio.data import description_is_consistent, load_store


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    monkeypatch.setenv("AGENT_TODAY", "2026-11-02T10:00")


def names(result):
    return [p["name"] for p in result["products"]]


# ------------------------------------------------------------------- data cleaning

def test_inconsistent_descriptions_are_dropped():
    assert not description_is_consistent("Music Man Bass 1X", "Contrabaixo elétrico Fender Jazz Bass")
    assert description_is_consistent("Yamaha C40", "Violão clássico Yamaha")
    p = load_store().products.set_index("product_id")
    assert p.loc[135, "description"] == ""
    assert p.loc[81, "description"] != ""


def test_only_active_promotions_affect_price():
    p = load_store().products.set_index("product_id")
    assert p.loc[93, "discount_percent"] == 0  # two inactive promos
    assert p.loc[127, "final_price_brl"] == pytest.approx(323.10)


def test_pix_discount_not_cumulative_with_promotion():
    p = load_store().products.set_index("product_id")
    assert p.loc[95, "pix_price_brl"] == pytest.approx(2199 * 0.95)
    assert p.loc[127, "pix_price_brl"] == p.loc[127, "final_price_brl"]


# ------------------------------------------------------------------------ products

def test_search_guitars_under_1000_excludes_unavailable():
    result = tools.search_products(category="Violões", max_price=1000)
    found = names(result)
    assert found and all(p["available"] for p in result["products"])
    assert "Giannini GF-3D Dreadnought Sunburst" not in found  # stock 0
    assert "Shelby SN-7C 7 Cordas Nylon Natural" not in found  # discontinued
    assert all(p["price_brl"] <= 1000 for p in result["products"])


def test_empty_category_is_reported():
    result = tools.search_products(category="Cordas Orquestrais")
    assert result["products"] == [] and "note" in result


def test_product_details_fuzzy_match():
    result = tools.get_product_details("takamine gd20")
    assert result["product"]["name"] == "Takamine GD20 Dreadnought Natural"
    assert result["product"]["price_brl"] == 2199


@pytest.mark.parametrize("price,expected", [(599.90, 6), (1200, 12), (439.20, 5), (120, 2), (40, 1)])
def test_max_installments_follow_policy_tiers(price, expected):
    assert tools.max_installments(price) == expected


def test_product_details_include_installments():
    card = tools.get_product_details("Yamaha C40")["product"]["credit_card"]
    assert card["max_installments_no_interest"] == 6


def test_promotional_product_has_no_extra_pix_discount():
    product = tools.get_product_details("Ohana CK-20")["product"]
    assert product["pix_price_brl"] == product["promotion"]["promotional_price_brl"] == pytest.approx(439.20)


def test_coming_soon_is_not_available_and_suggests_alternatives():
    result = tools.get_product_details("Kala KA-ABP-CTG Barítono")
    assert result["product"]["available"] is False
    assert result["similar_available_alternatives"]


def test_unknown_product():
    assert tools.get_product_details("Stradivarius 1715")["found"] is False


# -------------------------------------------------------------------------- orders

def test_order_requires_matching_contact():
    assert tools.get_order_status(8, "someone@else.com")["verified"] is False
    assert tools.get_order_status(999, "anacarol.ferreira@coldmail.com")["verified"] is False


def test_order_without_contact_asks_for_it_and_reveals_nothing():
    result = tools.get_order_status(8)
    assert result["verified"] is False and result["missing"] == "email_or_phone"
    assert "status" not in result and "items" not in result


def test_order_status_with_phone_and_delay():
    result = tools.get_order_status(8, "(67) 99654-7821")
    assert result["verified"] and result["status"] == "enviado"
    assert result["delayed_days"] > 0
    assert result["tracking_code"] == "BRJL5544332BR"


def test_return_after_regret_window_is_denied():
    result = tools.check_return_eligibility(7, "arrependimento", "leticia.rocha@jmail.com")
    assert result["eligible"] is False


def test_return_within_window(monkeypatch):
    monkeypatch.setenv("AGENT_TODAY", "2026-02-20")
    result = tools.check_return_eligibility(7, "arrependimento", "leticia.rocha@jmail.com")
    assert result["eligible"] is True


def test_return_for_undelivered_order():
    result = tools.check_return_eligibility(13, "arrependimento", "fernanda.ribeiro@coldmail.com")
    assert result["eligible"] is None


# --------------------------------------------------------------------------- store

def test_policy_sections():
    assert "Rua 14 de Maio" in tools.get_store_policy("loja")["content"]
    assert "error" in tools.get_store_policy("nope")


def test_store_hours(monkeypatch):
    assert tools.check_store_hours()["is_open_now"] is True  # Monday 10:00
    monkeypatch.setenv("AGENT_TODAY", "2026-11-01T10:00")  # Sunday
    closed = tools.check_store_hours()
    assert closed["is_open_now"] is False and closed["next_opening"].startswith("segunda-feira")


def test_call_tool_handles_bad_arguments():
    assert "error" in tools.call_tool("get_order_status", {"email_or_phone": "x@y.com"})
    assert "error" in tools.call_tool("does_not_exist", {})
