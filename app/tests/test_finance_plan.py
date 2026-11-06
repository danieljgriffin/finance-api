import pytest


def test_finance_plan_replaces_one_saved_plan_without_recording_cash_flows(client, test_user_id):
    assert client.get("/finance-plan").json() is None

    plan = {
        "take_home_monthly_pence": 423300,
        "bills": [
            {"name": "House payment", "amount_pence": 15000, "frequency": "monthly"},
            {"name": "Annual subscription", "amount_pence": 22500, "frequency": "annual"},
        ],
        "allocations": [{
            "platform": "Trading212 GIA", "amount_pence": 188300,
            "funds": [{"name": "Vanguard S&P 500", "amount_pence": 63300}],
        }],
    }
    assert client.put("/finance-plan", json=plan).json() == plan
    assert client.get("/finance-plan").json() == plan

    changed = {**plan, "take_home_monthly_pence": 420000}
    assert client.put("/finance-plan", json=changed).json() == changed
    assert client.get("/finance-plan").json() == changed
    assert client.get("/cashflow/movements").json() == []


def test_planned_purchase_uses_exact_fund_and_account_without_changing_plan(client, test_user_id, monkeypatch):
    from app.config import settings
    from app.utils.price_fetcher import PriceFetcher

    isin = "GB00BMJJJF91"
    result = client.get("/holdings/search", params={"q": isin}).json()
    assert len(result) == 1
    found = result[0]
    assert found["symbol"] == found["isin"] == isin
    assert found["type"] == "fund"
    assert found["currency"] == "GBP"
    name = found.pop("name")
    platform = "HL Stocks & Shares LISA"
    saved = client.put("/finance-plan", json={"allocations": [{
        "platform": platform, "amount_pence": 11111,
        "funds": [{"name": name, "amount_pence": 11111, "instrument": found}],
    }]}).json()
    assert saved["allocations"][0]["funds"][0]["instrument"] == found
    assert client.get("/holdings/").json()[platform] == []

    holding = {
        "platform": platform, "name": name, "symbol": "OTHER-LISTING",
        "holdings": 1, "amount_spent": 3, "average_buy_price": 3, "current_price": 3,
    }
    other = client.post("/holdings/", json=holding).json()

    def fetch_price(self, symbol, **kwargs):
        assert symbol == isin
        return 4.12

    monkeypatch.setattr(settings, "ENABLE_REMOTE_DATA", True)
    monkeypatch.setattr(PriceFetcher, "get_price", fetch_price)
    purchase = {"platform": platform, "symbol": isin, "holdings": 25, "amount_spent": 100}
    assert client.post("/finance-plan/purchase", json={**purchase, "platform": "Degiro"}).status_code == 404
    first = client.post("/finance-plan/purchase", json=purchase).json()
    assert first["id"] != other["id"]
    assert first["current_price"] == 4.12
    client.put(f'/holdings/{first["id"]}', json={"name": "HSBC fund in my account"})
    second = client.post("/finance-plan/purchase", json={
        **purchase, "holdings": 5, "amount_spent": 23,
    }).json()
    assert second["id"] == first["id"]
    assert second["holdings"] == 30
    assert second["amount_spent"] == 123
    assert second["average_buy_price"] == 4.10
    portfolio = client.get("/holdings/portfolio").json()
    assert portfolio["total_value"] == pytest.approx(126.6)
    assert client.get("/finance-plan").json() == saved
    assert client.get("/cashflow/movements").json() == []
