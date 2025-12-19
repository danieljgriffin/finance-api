from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date

# Investment Schemas
class InvestmentBase(BaseModel):
    platform: str
    name: str
    symbol: Optional[str] = None
    holdings: float = 0.0
    amount_spent: float = 0.0
    average_buy_price: float = 0.0
    current_price: float = 0.0

class InvestmentCreate(InvestmentBase):
    pass

class InvestmentUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    holdings: Optional[float] = None
    amount_spent: Optional[float] = None
    average_buy_price: Optional[float] = None
    current_price: Optional[float] = None

class Investment(InvestmentBase):
    id: int
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Platform Cash Schemas
class PlatformCashBase(BaseModel):
    platform: str
    cash_balance: float = 0.0

class PlatformCashUpdate(BaseModel):
    cash_balance: float

class PlatformCash(PlatformCashBase):
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True

# Portfolio Summary Schemas
class PlatformSummary(BaseModel):
    name: str
    total_value: float
    total_invested: float 
    total_pl: float
    total_pl_percent: float
    cash_balance: float
    investments: List[Investment]
    color: str

class PortfolioSummary(BaseModel):
    total_value: float
    total_invested: float
    total_pl: float
    total_pl_percent: float
    platforms: List[PlatformSummary]

# Net Worth Schemas
class NetWorthEntryBase(BaseModel):
    year: int
    month: str
    platform_data: Dict[str, Any]
    total_networth: float = 0.0

class NetWorthEntry(NetWorthEntryBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Goal Schemas
class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    target_amount: float
    target_date: date
    target_date: date
    status: str = 'active'
    is_primary: bool = False

class GoalCreate(GoalBase):
    pass

class Goal(GoalBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Cashflow Schemas
class ExpenseBase(BaseModel):
    name: str
    monthly_amount: float

class ExpenseCreate(ExpenseBase):
    pass

class Expense(ExpenseBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class IncomeDataBase(BaseModel):
    year: str
    income: float = 0.0
    investment: float = 0.0

class IncomeData(IncomeDataBase):
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
