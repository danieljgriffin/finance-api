from datetime import date, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    IncomeData,
    Investment,
    MonthlyInvestment,
    MonthlyFinancialRecord,
    PlatformCash,
    PortfolioCashFlow,
    TrackerEntry,
)


@pytest.fixture
def performance_data(db, test_user_id):
    today = date.today()
    month_start = date(today.year, today.month, 1)
    year_start = date(today.year, 1, 1)

    db.add(Investment(
        user_id=test_user_id,
        platform="Brokerage",
        name="Test Fund",
        symbol="TEST",
        holdings=100.0,
        amount_spent=8000.0,
        average_buy_price=80.0,
        current_price=100.0,
    ))
    db.add(PlatformCash(
        user_id=test_user_id,
        platform="Brokerage",
        cash_balance=500.0,
    ))
    db.add(PlatformCash(
        user_id=test_user_id,
        platform="cAsH",
        cash_balance=5000.0,
    ))

    year_breakdown = {"Brokerage": 8000.0, "Cash": 3000.0}
    month_breakdown = {"Brokerage": 9000.0, "CASH": 4000.0}
    db.add(MonthlyFinancialRecord(
        user_id=test_user_id,
        period_date=year_start,
        net_worth=sum(year_breakdown.values()),
        details=year_breakdown,
    ))
    if month_start != year_start:
        db.add(MonthlyFinancialRecord(
            user_id=test_user_id,
            period_date=month_start,
            net_worth=sum(month_breakdown.values()),
            details=month_breakdown,
        ))
    db.add(IncomeData(
        user_id=test_user_id,
        year=str(today.year),
        income=50000.0,
        investment=8988.0,
    ))
    db.commit()

    return {
        "today": today,
        "month_start_value": 9000.0 if month_start != year_start else 8000.0,
    }


def _dashboard(client):
    response = client.get("/net-worth/dashboard-summary")
    assert response.status_code == 200, response.text
    return response.json()


def _raise_annual_total(client, today: date):
    response = client.post(
        "/cashflow/income",
        params={
            "year": str(today.year),
            "income": 50000,
            "investment": 10788,
            "effective_date": today.isoformat(),
        },
    )
    assert response.status_code == 200, response.text


def test_baseline_uses_8988_without_month_event_and_excludes_cash(
    client, db, performance_data
):
    data = _dashboard(client)
    month = data["portfolio_performance"]["month"]
    year = data["portfolio_performance"]["year"]

    assert data["total_networth"] == pytest.approx(15500.0)
    assert month["current_value"] == pytest.approx(10500.0)
    assert month["start_value"] == pytest.approx(performance_data["month_start_value"])
    assert month["contributions"] == 0
    assert year["contributions"] == pytest.approx(8988.0)
    assert db.query(PortfolioCashFlow).count() == 0


def test_annual_total_increase_logs_one_1800_mtd_contribution(
    client, db, performance_data
):
    _raise_annual_total(client, performance_data["today"])
    _raise_annual_total(client, performance_data["today"])

    events = db.query(PortfolioCashFlow).filter(
        PortfolioCashFlow.flow_type == "contribution"
    ).all()
    assert len(events) == 1
    assert events[0].amount == pytest.approx(1800.0)
    assert events[0].previous_invested_total == pytest.approx(8988.0)
    assert events[0].new_invested_total == pytest.approx(10788.0)
    assert events[0].event_key

    month = _dashboard(client)["portfolio_performance"]["month"]
    assert month["contributions"] == pytest.approx(1800.0)
    assert month["current_value"] == pytest.approx(10500.0)


def test_withdrawal_adjusts_gain(client, performance_data):
    _raise_annual_total(client, performance_data["today"])
    response = client.post("/cashflow/movements", json={
        "effective_date": performance_data["today"].isoformat(),
        "amount": 300.0,
        "flow_type": "withdrawal",
        "source_platform": "Brokerage",
        "note": "Demo withdrawal",
    })
    assert response.status_code == 200, response.text

    month = _dashboard(client)["portfolio_performance"]["month"]
    expected_gain = (
        10500.0
        - performance_data["month_start_value"]
        - 1800.0
        + 300.0
    )
    assert month["withdrawals"] == pytest.approx(300.0)
    assert month["amount"] == pytest.approx(expected_gain)


def test_transfer_is_canonical_and_has_zero_performance_effect(
    client, performance_data
):
    before = _dashboard(client)["portfolio_performance"]["month"]
    response = client.post("/cashflow/movements", json={
        "effective_date": performance_data["today"].isoformat(),
        "amount": 500.0,
        "flow_type": "transfer",
        "source_platform": "Brokerage",
        "destination_platform": "Pension",
        "note": "Internal move",
    })
    assert response.status_code == 200, response.text
    assert response.json()["flow_type"] == "transfer"

    after = _dashboard(client)["portfolio_performance"]["month"]
    assert after == before

    rejected = client.post("/cashflow/movements", json={
        "effective_date": performance_data["today"].isoformat(),
        "amount": 500.0,
        "flow_type": "transfer",
        "source_platform": "Cash",
        "destination_platform": "Brokerage",
    })
    assert rejected.status_code == 400


def test_tracker_entry_keeps_exact_dates_and_rolls_up_month_and_year(
    client, db, performance_data
):
    today = performance_data["today"]
    income_date = date(today.year, today.month, 1)
    investment_date = date(today.year, today.month, min(today.day, 10))

    response = client.post("/cashflow/tracker-entries", json={
        "entry_key": "september-pay-and-investment",
        "income_amount": 2500.0,
        "income_date": income_date.isoformat(),
        "investment_amount": 1800.0,
        "investment_date": investment_date.isoformat(),
        "destination_platform": "Brokerage",
    })
    assert response.status_code == 200, response.text
    assert response.json()["income_date"] == income_date.isoformat()
    assert response.json()["investment_date"] == investment_date.isoformat()

    annual = db.query(IncomeData).filter(
        IncomeData.year == str(today.year)
    ).one()
    assert annual.income == pytest.approx(52500.0)
    assert annual.investment == pytest.approx(10788.0)

    monthly = db.query(MonthlyInvestment).filter(
        MonthlyInvestment.year == today.year,
        MonthlyInvestment.month == today.month,
    ).one()
    assert monthly.income_received == pytest.approx(2500.0)
    assert monthly.amount_invested == pytest.approx(1800.0)

    contribution = db.query(PortfolioCashFlow).filter(
        PortfolioCashFlow.flow_type == "contribution"
    ).one()
    assert contribution.effective_date == investment_date
    assert contribution.amount == pytest.approx(1800.0)
    assert contribution.previous_invested_total == pytest.approx(8988.0)
    assert contribution.new_invested_total == pytest.approx(10788.0)


def test_separate_income_and_investment_entries_share_month_rollup(
    client, db, performance_data
):
    today = performance_data["today"]
    income_date = date(today.year, today.month, 1)
    investment_date = date(today.year, today.month, min(today.day, 10))

    income = client.post("/cashflow/tracker-entries", json={
        "entry_key": "separate-income",
        "income_amount": 2500.0,
        "income_date": income_date.isoformat(),
    })
    assert income.status_code == 200, income.text

    investment = client.post("/cashflow/tracker-entries", json={
        "entry_key": "separate-investment",
        "investment_amount": 1800.0,
        "investment_date": investment_date.isoformat(),
        "destination_platform": "Brokerage",
    })
    assert investment.status_code == 200, investment.text

    monthly_response = client.get(
        "/cashflow/monthly-activity", params={"year": today.year}
    )
    assert monthly_response.status_code == 200
    monthly_rows = monthly_response.json()
    assert len(monthly_rows) == 1
    assert monthly_rows[0]["year"] == today.year
    assert monthly_rows[0]["month"] == today.month
    assert monthly_rows[0]["month_name"] == today.strftime("%B")
    assert monthly_rows[0]["income_received"] == pytest.approx(2500.0)
    assert monthly_rows[0]["amount_invested"] == pytest.approx(1800.0)


def test_tracker_entry_retry_is_idempotent(client, db, performance_data):
    payload = {
        "entry_key": "retry-safe-entry",
        "investment_amount": 1800.0,
        "investment_date": performance_data["today"].isoformat(),
    }
    first = client.post("/cashflow/tracker-entries", json=payload)
    second = client.post("/cashflow/tracker-entries", json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]
    assert db.query(TrackerEntry).count() == 1
    assert db.query(PortfolioCashFlow).filter(
        PortfolioCashFlow.flow_type == "contribution"
    ).count() == 1

    annual = db.query(IncomeData).filter(
        IncomeData.year == str(performance_data["today"].year)
    ).one()
    assert annual.investment == pytest.approx(10788.0)


def test_default_movements_hide_corrections_and_baselines(
    client, db, performance_data, test_user_id
):
    _raise_annual_total(client, performance_data["today"])
    for payload in (
        {
            "amount": 100.0,
            "flow_type": "withdrawal",
            "source_platform": "Brokerage",
        },
        {
            "amount": 200.0,
            "flow_type": "transfer",
            "source_platform": "Brokerage",
            "destination_platform": "Pension",
        },
        {
            "amount": 50.0,
            "flow_type": "correction",
            "note": "Correcting imported metadata",
        },
    ):
        response = client.post("/cashflow/movements", json={
            "effective_date": performance_data["today"].isoformat(),
            **payload,
        })
        assert response.status_code == 200, response.text

    db.add(PortfolioCashFlow(
        user_id=test_user_id,
        effective_date=performance_data["today"],
        amount=1.0,
        flow_type="baseline",
        note="Internal baseline",
        source="test",
    ))
    db.commit()

    response = client.get("/cashflow/movements")
    assert response.status_code == 200
    assert {item["flow_type"] for item in response.json()} == {
        "contribution", "withdrawal", "transfer"
    }

    corrections = client.get(
        "/cashflow/movements", params={"flow_type": "correction"}
    )
    assert corrections.status_code == 200
    assert [item["flow_type"] for item in corrections.json()] == ["correction"]


def test_future_effective_dates_are_rejected(client, db, performance_data):
    future_date = performance_data["today"] + timedelta(days=1)
    annual = client.post(
        "/cashflow/income",
        params={
            "year": str(performance_data["today"].year),
            "income": 50000,
            "investment": 10788,
            "effective_date": future_date.isoformat(),
        },
    )
    assert annual.status_code == 400

    movement = client.post("/cashflow/movements", json={
        "effective_date": future_date.isoformat(),
        "amount": 100.0,
        "flow_type": "withdrawal",
        "source_platform": "Brokerage",
    })
    assert movement.status_code == 400

    db.expire_all()
    stored = db.query(IncomeData).filter(
        IncomeData.year == str(performance_data["today"].year)
    ).one()
    assert stored.investment == pytest.approx(8988.0)
    assert db.query(PortfolioCashFlow).count() == 0


def test_stale_integrity_conflict_returns_409(
    client, db, monkeypatch, performance_data
):
    original_commit = db.commit

    def fail_commit():
        raise IntegrityError("INSERT", {}, Exception("simulated duplicate"))

    monkeypatch.setattr(db, "commit", fail_commit)
    response = client.post(
        "/cashflow/income",
        params={
            "year": str(performance_data["today"].year),
            "income": 50000,
            "investment": 10788,
            "effective_date": performance_data["today"].isoformat(),
        },
    )
    monkeypatch.setattr(db, "commit", original_commit)

    assert response.status_code == 409
    assert "not persisted" in response.json()["detail"]


def test_remote_data_actions_are_blocked_in_testing(client):
    refresh = client.post("/holdings/refresh-prices")
    assert refresh.status_code == 403

    trading212 = client.post("/holdings/import/trading212", json={
        "api_key_id": "demo",
        "api_secret_key": "demo",
    })
    assert trading212.status_code == 403

    crypto_sync = client.post("/crypto/123/sync")
    assert crypto_sync.status_code == 403

    crypto_connect = client.post("/crypto/connect-investment", json={
        "platform_id": "Crypto",
        "name": "Demo wallet",
        "xpub": "not-a-real-xpub",
        "user_id": 1,
    })
    assert crypto_connect.status_code == 403
