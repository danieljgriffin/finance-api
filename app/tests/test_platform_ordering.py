from app.models import PlatformCash
from app.services.holdings_service import HoldingsService
from app.services.net_worth_service import NetWorthService


def _seed_platform_cash(db, user_id):
    db.add_all([
        PlatformCash(user_id=user_id, platform="Cash", cash_balance=2550.0),
        PlatformCash(user_id=user_id, platform="Trading212 GIA", cash_balance=10.0),
        PlatformCash(user_id=user_id, platform="Other Brokerage", cash_balance=100.0),
    ])
    db.commit()


def test_portfolio_summary_keeps_cash_last_after_value_sort(db, test_user_id):
    _seed_platform_cash(db, test_user_id)

    platforms = HoldingsService(db, test_user_id).get_portfolio_summary()["platforms"]
    names = [item["name"] for item in platforms]
    non_cash_values = [
        item["total_value"] for item in platforms if item["name"] != "Cash"
    ]

    assert names[-1] == "Cash"
    assert names.index("Other Brokerage") < names.index("Trading212 GIA")
    assert names.index("Trading212 GIA") < names.index("Cash")
    assert non_cash_values == sorted(non_cash_values, reverse=True)


def test_dashboard_summary_keeps_cash_last_after_value_sort(db, test_user_id):
    _seed_platform_cash(db, test_user_id)

    platforms = NetWorthService(db, test_user_id).get_dashboard_summary()["platforms"]

    assert [item["platform"] for item in platforms] == [
        "Other Brokerage",
        "Trading212 GIA",
        "Cash",
    ]

