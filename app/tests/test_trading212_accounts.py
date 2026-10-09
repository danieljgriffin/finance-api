import asyncio

import pytest

from app.models import Investment, PlatformCash, User
from app.services.holdings_service import HoldingsService
from app.services.trading212_service import Trading212Service
from app.utils.price_fetcher import PriceFetcher


def _mock_trading212(monkeypatch, *, account_id=9002, total_value=10.0, portfolio=None):
    monkeypatch.setattr(
        Trading212Service,
        "fetch_account_summary",
        lambda self: {
            "id": account_id,
            "currency": "GBP",
            "totalValue": total_value,
            "cash": {
                "availableToTrade": total_value,
                "inPies": 0.0,
                "reservedForOrders": 0.0,
            },
            "investments": {
                "currentValue": 0.0,
                "totalCost": 0.0,
                "unrealizedProfitLoss": 0.0,
                "realizedProfitLoss": 0.0,
            },
        },
    )
    monkeypatch.setattr(
        Trading212Service,
        "fetch_portfolio",
        lambda self: list(portfolio or []),
    )
    monkeypatch.setattr(PriceFetcher, "get_usd_to_gbp_rate", lambda self: 0.8)
    monkeypatch.setattr(
        HoldingsService,
        "get_company_name_safe",
        lambda self, symbol, default: default,
    )


def test_current_positions_api_is_normalized_when_legacy_endpoint_is_unavailable(
    monkeypatch,
):
    service = Trading212Service("key", "secret")

    def fake_fetch(endpoint_path, description):
        if endpoint_path == "/equity/portfolio":
            raise ValueError("legacy endpoint unavailable")
        assert endpoint_path == "/equity/positions"
        return [{
            "instrument": {
                "ticker": "AAPL_US_EQ",
                "name": "Apple",
                "currencyCode": "USD",
            },
            "quantity": 2.0,
            "averagePricePaid": 100.0,
            "currentPrice": 120.0,
            "walletImpact": {
                "currency": "GBP",
                "currentValue": 190.0,
                "totalCost": 160.0,
                "unrealizedProfitLoss": 30.0,
            },
        }]

    monkeypatch.setattr(service, "_fetch_json", fake_fetch)
    position = service.fetch_portfolio()[0]
    assert position["ticker"] == "AAPL_US_EQ"
    assert position["walletImpact"]["currentValue"] == pytest.approx(190.0)
    assert position["ppl"] == pytest.approx(30.0)


def test_trading212_credentials_are_stored_per_account_and_legacy_isa_survives(
    db, test_user_id
):
    service = HoldingsService(db, test_user_id)

    assert service.save_trading212_credentials(
        "isa-key", "isa-secret", "isa", account_id="1001"
    )
    assert service.save_trading212_credentials(
        "gia-key", "gia-secret", "gia", account_id="2002"
    )

    isa = service.get_trading212_credentials("isa")
    gia = service.get_trading212_credentials("gia")
    assert isa["api_key_id"] == "isa-key"
    assert isa["platform"] == "Trading212 ISA"
    assert isa["account_id"] == "1001"
    assert gia["api_key_id"] == "gia-key"
    assert gia["platform"] == "Trading212 GIA"
    assert gia["account_id"] == "2002"
    assert {item["account_type"] for item in service.get_trading212_connections()} == {
        "isa",
        "gia",
    }

    preferences = db.query(User).filter(User.id == test_user_id).one().preferences
    assert "trading212_sync" in preferences
    assert set(preferences["trading212_accounts"]) == {"isa", "gia"}


def test_cash_only_gia_sync_is_separate_and_visible(
    db, test_user_id, monkeypatch
):
    db.add(Investment(
        user_id=test_user_id,
        platform="Trading212 ISA",
        name="Existing ISA holding",
        symbol="ISA",
        holdings=1.0,
        amount_spent=50.0,
        average_buy_price=50.0,
        current_price=55.0,
    ))
    db.commit()
    _mock_trading212(monkeypatch, total_value=10.0, portfolio=[])

    service = HoldingsService(db, test_user_id)
    result = asyncio.run(service.sync_trading212_investments(
        "gia-key", "gia-secret", account_type="gia"
    ))

    assert result["platform"] == "Trading212 GIA"
    assert result["cash_balance"] == pytest.approx(10.0)
    assert db.query(Investment).filter(
        Investment.user_id == test_user_id,
        Investment.platform == "Trading212 ISA",
    ).count() == 1
    gia_cash = db.query(PlatformCash).filter(
        PlatformCash.user_id == test_user_id,
        PlatformCash.platform == "Trading212 GIA",
    ).one()
    assert gia_cash.cash_balance == pytest.approx(10.0)

    gia_summary = next(
        item for item in service.get_portfolio_summary()["platforms"]
        if item["name"] == "Trading212 GIA"
    )
    assert gia_summary["total_value"] == pytest.approx(10.0)
    assert gia_summary["total_pl"] == pytest.approx(0.0)
    assert gia_summary["total_pl_percent"] == pytest.approx(0.0)


def test_same_symbol_in_gia_does_not_overwrite_isa(
    db, test_user_id, monkeypatch
):
    db.add(Investment(
        user_id=test_user_id,
        platform="Trading212 ISA",
        name="Apple ISA",
        symbol="AAPL",
        holdings=2.0,
        amount_spent=200.0,
        average_buy_price=100.0,
        current_price=120.0,
    ))
    db.commit()
    _mock_trading212(
        monkeypatch,
        total_value=130.0,
        portfolio=[{
            "ticker": "AAPL_US_EQ",
            "name": "Apple GIA",
            "quantity": 1.0,
            "averagePrice": 100.0,
            "currentPrice": 125.0,
            "ppl": 30.0,
            "currency": "USD",
        }],
    )

    service = HoldingsService(db, test_user_id)
    asyncio.run(service.sync_trading212_investments(
        "gia-key", "gia-secret", account_type="gia"
    ))

    isa = db.query(Investment).filter(
        Investment.user_id == test_user_id,
        Investment.platform == "Trading212 ISA",
        Investment.symbol == "AAPL",
    ).one()
    gia = db.query(Investment).filter(
        Investment.user_id == test_user_id,
        Investment.platform == "Trading212 GIA",
        Investment.symbol == "AAPL",
    ).one()
    assert isa.holdings == pytest.approx(2.0)
    assert gia.holdings == pytest.approx(1.0)


def test_legacy_sync_does_not_overwrite_existing_market_price(
    db, test_user_id, monkeypatch
):
    db.add(Investment(
        user_id=test_user_id,
        platform="Trading212 ISA",
        name="Rolls-Royce",
        symbol="RR.L",
        holdings=59.0,
        amount_spent=700.0,
        average_buy_price=11.86,
        current_price=13.72,
    ))
    db.commit()
    _mock_trading212(
        monkeypatch,
        total_value=810.0,
        portfolio=[{
            "ticker": "RRl_EQ",
            "name": "Rolls-Royce",
            "quantity": 59.0,
            "averagePrice": 1186.0,
            "currentPrice": 1372.0,
            "currency": "GBX",
            # The legacy endpoint can expose wallet values in instrument minor
            # units, so they must not be treated as exact GBP position values.
            "walletImpact": {
                "currentValue": 80948.0,
                "totalCost": 69974.0,
            },
        }],
    )

    service = HoldingsService(db, test_user_id)
    asyncio.run(service.sync_trading212_investments(
        "isa-key", "isa-secret", account_type="isa"
    ))

    rr = db.query(Investment).filter(
        Investment.user_id == test_user_id,
        Investment.platform == "Trading212 ISA",
        Investment.symbol == "RR.L",
    ).one()
    assert rr.current_price == pytest.approx(13.72)
    assert rr.average_buy_price == pytest.approx(11.86)


def test_gia_connect_endpoint_syncs_and_saves_account(
    client, db, test_user_id, monkeypatch
):
    _mock_trading212(monkeypatch, account_id=4242, total_value=10.0)
    monkeypatch.setattr(
        "app.routers.holdings.require_remote_data_enabled",
        lambda: None,
    )

    response = client.post("/holdings/import/trading212", json={
        "api_key_id": "gia-key",
        "api_secret_key": "gia-secret",
        "account_type": "gia",
    })
    assert response.status_code == 200, response.text
    assert response.json()["platform"] == "Trading212 GIA"
    assert response.json()["account_id"] == "4242"

    status = client.get(
        "/holdings/config/trading212", params={"account_type": "gia"}
    )
    assert status.status_code == 200
    assert status.json() == {
        "enabled": True,
        "account_type": "gia",
        "platform": "Trading212 GIA",
        "account_id": "4242",
        "updated_at": status.json()["updated_at"],
    }
    assert status.json()["updated_at"]
