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

class PlatformCash(PlatformCashBase):
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True

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
    status: str = 'active'

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
