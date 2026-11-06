from math import isfinite
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models import FinancePlan
from app.schemas import Investment, InvestmentCreate
from app.services.holdings_service import HoldingsService
from app.utils.price_fetcher import PriceFetcher
from app.utils.portfolio import is_standalone_cash_platform
from app.utils.runtime import is_local_or_demo_runtime

router = APIRouter(prefix="/finance-plan", tags=["finance-plan"])

Pence = Annotated[int, Field(strict=True, ge=0, le=10_000_000_000)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Platform = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Symbol = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class PlanItem(BaseModel):
    name: Name
    amount_pence: Pence


class PlannedBill(PlanItem):
    frequency: Literal["monthly", "annual"] = "monthly"


class InstrumentReference(BaseModel):
    symbol: Symbol
    isin: Optional[Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]] = None
    type: Optional[str] = Field(default=None, max_length=25)
    exchange: Optional[str] = Field(default=None, max_length=80)
    currency: Optional[str] = Field(default=None, max_length=10)


class PlannedInvestment(PlanItem):
    instrument: Optional[InstrumentReference] = None


class FinancePlanAllocation(BaseModel):
    platform: Platform
    amount_pence: Pence
    funds: list[PlannedInvestment] = Field(default_factory=list, max_length=100)


class FinancePlanDetails(BaseModel):
    take_home_monthly_pence: Pence = 0
    bills: list[PlannedBill] = Field(default_factory=list, max_length=100)
    allocations: list[FinancePlanAllocation] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_platforms(self):
        platforms = [row.platform.casefold() for row in self.allocations]
        if any(is_standalone_cash_platform(name) for name in platforms):
            raise ValueError("Choose an investment platform for each planned investment.")
        if len(platforms) != len(set(platforms)):
            raise ValueError("Enter each platform once.")
        return self


@router.get("", response_model=Optional[FinancePlanDetails], response_model_exclude_none=True)
def read_plan(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    saved = db.get(FinancePlan, user_id)
    return saved.details if saved else None


@router.put("", response_model=FinancePlanDetails, response_model_exclude_none=True)
def save_plan(
    plan: FinancePlanDetails,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    saved = db.get(FinancePlan, user_id)
    if saved is None:
        saved = FinancePlan(user_id=user_id)
        db.add(saved)
    saved.details = plan.model_dump(exclude_none=True)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="The plan changed while saving. Reload and try again.")
    return plan


class PlannedPurchase(BaseModel):
    platform: Platform
    symbol: Symbol
    holdings: float = Field(gt=0, allow_inf_nan=False)
    amount_spent: float = Field(gt=0, allow_inf_nan=False)


@router.post("/purchase", response_model=Investment)
def record_purchase(
    purchase: PlannedPurchase,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    saved = db.get(FinancePlan, user_id)
    plan = FinancePlanDetails.model_validate(saved.details) if saved else FinancePlanDetails()
    fund = next((
        fund
        for allocation in plan.allocations if allocation.platform == purchase.platform
        for fund in allocation.funds
        if fund.instrument and fund.instrument.symbol == purchase.symbol
    ), None)
    service = HoldingsService(db, user_id)
    if fund is None or purchase.platform not in service.get_investments_by_platform():
        raise HTTPException(status_code=404, detail="This investment or account is no longer linked to your plan.")

    cost_per_unit = purchase.amount_spent / purchase.holdings
    if not isfinite(cost_per_unit) or cost_per_unit <= 0:
        raise HTTPException(status_code=422, detail="Enter a valid cost and unit quantity.")
    price = None
    if settings.ENABLE_REMOTE_DATA or not is_local_or_demo_runtime():
        price = PriceFetcher().get_price(
            purchase.symbol, use_previous_close=purchase.platform == "InvestEngine ISA",
        )

    return service.add_investment(purchase.platform, InvestmentCreate(
        platform=purchase.platform,
        name=fund.name,
        symbol=purchase.symbol,
        holdings=purchase.holdings,
        amount_spent=purchase.amount_spent,
        average_buy_price=cost_per_unit,
        current_price=price if price and isfinite(price) and price > 0 else cost_per_unit,
    ), match_symbol=True)
