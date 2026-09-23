from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any, Literal
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
    completed_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Income Schemas
class IncomeDataBase(BaseModel):
    year: str
    income: float = 0.0
    investment: float = 0.0

class IncomeData(IncomeDataBase):
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TrackerEntryCreate(BaseModel):
    entry_key: str = Field(min_length=1, max_length=100)
    income_amount: float = Field(default=0.0, ge=0)
    income_date: Optional[date] = None
    investment_amount: float = Field(default=0.0, ge=0)
    investment_date: Optional[date] = None
    destination_platform: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def validate_entry(self):
        if self.income_amount <= 0 and self.investment_amount <= 0:
            raise ValueError('enter an income amount, an investment amount, or both')
        if self.income_amount > 0 and self.income_date is None:
            raise ValueError('income_date is required when recording income')
        if self.investment_amount > 0 and self.investment_date is None:
            raise ValueError('investment_date is required when recording an investment')
        return self

class TrackerEntry(BaseModel):
    id: int
    user_id: int
    entry_key: str
    income_amount: float
    income_date: Optional[date] = None
    investment_amount: float
    investment_date: Optional[date] = None
    destination_platform: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class MonthlyInvestment(BaseModel):
    id: int
    year: int
    month: int
    month_name: str
    income_received: float
    amount_invested: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Portfolio Cash Flow Schemas
class PortfolioCashFlowCreate(BaseModel):
    effective_date: date = Field(default_factory=date.today)
    amount: float = Field(gt=0)
    flow_type: Literal['withdrawal', 'transfer', 'correction']
    source_platform: Optional[str] = None
    destination_platform: Optional[str] = None
    previous_invested_total: Optional[float] = None
    new_invested_total: Optional[float] = None
    note: Optional[str] = None
    source: Optional[str] = 'manual'
    event_key: Optional[str] = Field(default=None, max_length=255)

    @model_validator(mode='after')
    def validate_movement(self):
        if self.flow_type == 'withdrawal' and not self.source_platform:
            raise ValueError('source_platform is required for withdrawals')
        if self.flow_type == 'transfer':
            if not self.source_platform or not self.destination_platform:
                raise ValueError('source_platform and destination_platform are required for transfers')
            if self.source_platform.strip().casefold() == self.destination_platform.strip().casefold():
                raise ValueError('transfer platforms must be different')
        if self.flow_type == 'correction' and not self.note:
            raise ValueError('note is required for corrections')
        return self

class PortfolioCashFlow(BaseModel):
    id: int
    user_id: int
    effective_date: date
    amount: float
    flow_type: str
    source_platform: Optional[str] = None
    destination_platform: Optional[str] = None
    previous_invested_total: Optional[float] = None
    new_invested_total: Optional[float] = None
    note: Optional[str] = None
    source: Optional[str] = None
    event_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
