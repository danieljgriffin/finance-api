import asyncio

import pytest

from app.models import Investment, PlatformCash, User
from app.services.holdings_service import HoldingsService
from app.services.trading212_service import Trading212Service
from app.utils.price_fetcher import PriceFetcher


def _mock_trading212(
    monkeypatch,
    *,
    account_id=9002,
    total_value=10.0,
    investment_value=0.0,
    cash_value=None,
    portfolio=None,
):
    if cash_value is None:
        cash_value = total_value - investment_value
    monkeypatch.setattr(
        Trading212Service,
        "fetch_account_summary",
        lambda self: {
            "id": account_id,
            "currency": "GBP",
            "totalValue": total_value,
            "cash": {
                "availableToTrade": cash_value,
                "inPies": 0.0,
                "reservedForOrders": 0.0,
            },
            "investments": {
                "currentValue": investment_value,
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


def test_current_positions_api_is_preferred_and_normalized(
    monkeypatch,
):
    service = Trading212Service("key", "secret")

    def fake_fetch(endpoint_path, description):
        assert endpoint_path == "/equity/positions"
        return [{
            "instrument": {
                "ticker": "AAPL_US_EQ",
                "name": "Apple",
                "currency": "USD",
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
    assert position["currency"] == "USD"
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
        investment_value=100.0,
        cash_value=30.0,
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


def test_legacy_gbx_sync_updates_existing_market_price_after_validation(
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
        current_price=99.0,
    ))
    db.commit()
    _mock_trading212(
        monkeypatch,
        total_value=810.0,
        investment_value=809.48,
        cash_value=0.52,
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


def test_mixed_pence_gia_prices_are_normalized_without_ticker_rules(
    db, test_user_id, monkeypatch
):
    portfolio = [
        {
            "ticker": "GLDWl_EQ",
            "name": "WisdomTree Gold",
            "quantity": 1.27360142,
            "averagePrice": 314.0700015865,
            "currentPrice": 31414.03,
            "currency": "",
        },
        {
            "ticker": "FWRGl_EQ",
            "name": "Invesco All-World",
            "quantity": 55.44005544,
            "averagePrice": 7.215,
            "currentPrice": 721.2,
            "currency": "",
        },
        {
            "ticker": "VUAGl_EQ",
            "name": "Vanguard S&P 500",
            "quantity": 4.37981779,
            "averagePrice": 114.16000025,
            "currentPrice": 114.043,
            "currency": "",
        },
    ]
    expected_value = (
        portfolio[0]["quantity"] * 314.1403
        + portfolio[1]["quantity"] * 7.212
        + portfolio[2]["quantity"] * 114.043
    )
    _mock_trading212(
        monkeypatch,
        total_value=expected_value,
        investment_value=expected_value,
        cash_value=0.0,
        portfolio=portfolio,
    )

    service = HoldingsService(db, test_user_id)
    asyncio.run(service.sync_trading212_investments(
        "gia-key", "gia-secret", account_type="gia"
    ))

    prices = {
        investment.symbol: investment.current_price
        for investment in db.query(Investment).filter(
            Investment.user_id == test_user_id,
            Investment.platform == "Trading212 GIA",
        )
    }
    assert prices == pytest.approx({
        "GLDW.L": 314.1403,
        "FWRG.L": 7.212,
        "VUAG.L": 114.043,
    })


def test_failed_account_validation_keeps_every_saved_value(
    db, test_user_id, monkeypatch
):
    existing = Investment(
        user_id=test_user_id,
        platform="Trading212 GIA",
        name="Existing holding",
        symbol="OLD.L",
        holdings=2.0,
        amount_spent=20.0,
        average_buy_price=10.0,
        current_price=11.0,
    )
    cash = PlatformCash(
        user_id=test_user_id,
        platform="Trading212 GIA",
        cash_balance=5.0,
    )
    db.add_all([existing, cash])
    db.commit()
    _mock_trading212(
        monkeypatch,
        total_value=405.0,
        investment_value=400.0,
        cash_value=5.0,
        portfolio=[{
            "ticker": "FWRGl_EQ",
            "name": "Invesco All-World",
            "quantity": 55.44,
            "averagePrice": 7.215,
            "currentPrice": 72120.0,
            "currency": "",
        }],
    )

    service = HoldingsService(db, test_user_id)
    with pytest.raises(ValueError, match="validation failed"):
        asyncio.run(service.sync_trading212_investments(
            "gia-key", "gia-secret", account_type="gia"
        ))

    db.expire_all()
    saved = db.query(Investment).filter(
        Investment.user_id == test_user_id,
        Investment.platform == "Trading212 GIA",
    ).all()
    assert [(item.symbol, item.current_price) for item in saved] == [("OLD.L", 11.0)]
    assert db.query(PlatformCash).filter(
        PlatformCash.user_id == test_user_id,
        PlatformCash.platform == "Trading212 GIA",
    ).one().cash_balance == pytest.approx(5.0)


def test_general_price_refresh_does_not_touch_trading212(
    db, test_user_id, monkeypatch
):
    db.add_all([
        Investment(
            user_id=test_user_id,
            platform="Trading212 GIA",
            name="GIA holding",
            symbol="FWRG.L",
            holdings=1.0,
            amount_spent=7.0,
            average_buy_price=7.0,
            current_price=7.2,
        ),
        Investment(
            user_id=test_user_id,
            platform="Degiro",
            name="Other holding",
            symbol="OTHER",
            holdings=1.0,
            amount_spent=10.0,
            average_buy_price=10.0,
            current_price=10.0,
        ),
    ])
    db.commit()

    async def fake_prices(self, symbols, use_previous_close=False):
        assert "FWRG.L" not in symbols
        return {"OTHER": 12.0}

    monkeypatch.setattr(PriceFetcher, "get_multiple_prices_async", fake_prices)
    service = HoldingsService(db, test_user_id)
    asyncio.run(service.update_all_prices_async())

    db.expire_all()
    gia = db.query(Investment).filter(Investment.symbol == "FWRG.L").one()
    other = db.query(Investment).filter(Investment.symbol == "OTHER").one()
    assert gia.current_price == pytest.approx(7.2)
    assert other.current_price == pytest.approx(12.0)


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
