from fastapi.testclient import TestClient
from datetime import date

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_and_get_goal(client: TestClient):
    # Create a goal
    goal_data = {
        "title": "Retire Early",
        "description": "Save enough to retire by 40",
        "target_amount": 1000000.0,
        "target_date": str(date(2040, 1, 1)),
        "status": "active"
    }
    response = client.post("/goals/", json=goal_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == goal_data["title"]
    assert "id" in data
    
    # Get goals
    response = client.get("/goals/")
    assert response.status_code == 200
    goals = response.json()
    assert len(goals) > 0
    assert goals[0]["title"] == "Retire Early"

def test_holdings_flow(client: TestClient):
    # Add an investment
    inv_data = {
        "platform": "Fidelity",
        "name": "S&P 500 ETF",
        "symbol": "VOO",
        "holdings": 10.0,
        "amount_spent": 3500.0,
        "average_buy_price": 350.0,
        "current_price": 400.0
    }
    response = client.post("/holdings/", json=inv_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "S&P 500 ETF"
    assert data["platform"] == "Fidelity"
    
    # Verify it appears in the grouped holdings
    response = client.get("/holdings/")
    assert response.status_code == 200
    holdings = response.json()
    assert "Fidelity" in holdings
    assert len(holdings["Fidelity"]) >= 1
    assert holdings["Fidelity"][0]["symbol"] == "VOO"
    
    # Add cash to the platform
    response = client.post("/holdings/cash/Fidelity?amount=500.0")
    assert response.status_code == 200
    cash_data = response.json()
    assert cash_data["platform"] == "Fidelity"
    assert cash_data["cash_balance"] == 500.0

def test_net_worth_summary(client: TestClient, test_user_id):
    # The fixture 'test_user_id' ensures a user exists.
    # We already added an investment worth 10 * 400 = 4000 in 'test_holdings_flow' 
    # BUT tests are isolated by function scope in conftest.py, so we need to add data again here.
    
    # 1. Add Investment: 10 shares @ $100 = $1000
    inv_data = {
        "platform": "Robinhood",
        "name": "Tesla",
        "symbol": "TSLA",
        "holdings": 10.0,
        "amount_spent": 800.0,
        "average_buy_price": 80.0,
        "current_price": 100.0
    }
    client.post("/holdings/", json=inv_data)

    # 2. Add Cash: $200
    client.post("/holdings/cash/Robinhood?amount=200.0")
    
    # 3. Check Net Worth
    # Total should be 1000 (investments) + 200 (cash) = 1200
    response = client.get("/net-worth/summary")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_networth"] == 1200.0
    assert data["platform_breakdown"]["Robinhood"] == 1200.0
