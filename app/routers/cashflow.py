from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Literal
from datetime import date, datetime
from decimal import Decimal
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models import IncomeData, MonthlyInvestment, PortfolioCashFlow, TrackerEntry
from app.schemas import (
    IncomeData as IncomeDataSchema,
    MonthlyInvestment as MonthlyInvestmentSchema,
    PortfolioCashFlow as PortfolioCashFlowSchema,
    PortfolioCashFlowCreate,
    TrackerEntry as TrackerEntrySchema,
    TrackerEntryCreate,
)
from app.utils.portfolio import is_standalone_cash_platform

router = APIRouter(
    prefix="/cashflow",
    tags=["cashflow"]
)

def _number_token(value: float) -> str:
    """Stable representation for idempotent annual-total event keys."""
    return format(Decimal(str(value)).normalize(), 'f')

def _annual_change_event_key(user_id: int, year: str, previous: float, new: float) -> str:
    return (
        f'income_annual_total:{user_id}:{year}:'
        f'{_number_token(previous)}:{_number_token(new)}'
    )

def _get_or_create_annual_row(db: Session, user_id: int, year: int) -> IncomeData:
    row = db.query(IncomeData).filter(
        IncomeData.user_id == user_id,
        IncomeData.year == str(year),
    ).with_for_update().first()
    if row is None:
        row = IncomeData(
            user_id=user_id,
            year=str(year),
            income=0.0,
            investment=0.0,
        )
        db.add(row)
        db.flush()
    return row

def _get_or_create_month_row(db: Session, user_id: int, entry_date: date) -> MonthlyInvestment:
    row = db.query(MonthlyInvestment).filter(
        MonthlyInvestment.user_id == user_id,
        MonthlyInvestment.year == entry_date.year,
        MonthlyInvestment.month == entry_date.month,
    ).with_for_update().first()
    if row is None:
        row = MonthlyInvestment(
            user_id=user_id,
            year=entry_date.year,
            month=entry_date.month,
            month_name=entry_date.strftime('%B'),
            income_received=0.0,
            amount_invested=0.0,
        )
        db.add(row)
        db.flush()
    return row

@router.get("/income", response_model=List[IncomeDataSchema])
def get_income_data(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # Auto-create current year if it doesn't exist
    current_year = str(datetime.now().year)
    
    exists = db.query(IncomeData).filter(
        IncomeData.user_id == user_id,
        IncomeData.year == current_year
    ).first()
    
    if not exists:
        new_entry = IncomeData(
            user_id=user_id,
            year=current_year,
            income=0,
            investment=0
        )
        db.add(new_entry)
        db.commit()
    
    return db.query(IncomeData).filter(IncomeData.user_id == user_id).all()

@router.post("/income", response_model=IncomeDataSchema)
def update_income(
    year: str,
    income: float,
    investment: float,
    effective_date: Optional[date] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    if investment < 0:
        raise HTTPException(status_code=400, detail="investment total cannot be negative")
    if effective_date and effective_date > date.today():
        raise HTTPException(status_code=400, detail="effective_date cannot be in the future")

    entry = db.query(IncomeData).filter(
        IncomeData.user_id == user_id,
        IncomeData.year == year
    ).first()

    previous_investment = float(entry.investment or 0.0) if entry else 0.0

    if entry:
        entry.income = income
        entry.investment = investment
    else:
        entry = IncomeData(
            user_id=user_id,
            year=year,
            income=income,
            investment=investment
        )
        db.add(entry)

    new_investment = float(investment)
    if new_investment != previous_investment:
        current_year = str(date.today().year)
        event_type = (
            'contribution'
            if year == current_year and new_investment > previous_investment
            else 'correction'
        )
        event_date = effective_date or date.today()
        if event_type == 'contribution' and event_date.year != int(year):
            raise HTTPException(
                status_code=400,
                detail="effective_date for a current-year contribution must be in that year",
            )

        event = PortfolioCashFlow(
            user_id=user_id,
            effective_date=event_date,
            amount=abs(new_investment - previous_investment),
            flow_type=event_type,
            previous_invested_total=previous_investment,
            new_invested_total=new_investment,
            note=(
                f'Annual invested total updated for {year}'
                if event_type == 'contribution'
                else f'Excluded correction to annual invested total for {year}'
            ),
            source='income_annual_total',
            event_key=_annual_change_event_key(
                user_id, year, previous_investment, new_investment
            ),
        )
        db.add(event)

    try:
        db.commit()
    except IntegrityError:
        # Concurrent retries can race after reading the same previous total.
        # The deterministic unique event key makes the write idempotent.
        db.rollback()
        entry = db.query(IncomeData).filter(
            IncomeData.user_id == user_id,
            IncomeData.year == year,
        ).first()
        persisted_investment = float(entry.investment or 0.0) if entry else None
        if entry is None or persisted_investment != new_investment:
            raise HTTPException(
                status_code=409,
                detail="income update conflicted and the requested investment total was not persisted",
            )

    db.refresh(entry)
    return entry

@router.get("/monthly-activity", response_model=List[MonthlyInvestmentSchema])
def get_monthly_activity(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = db.query(MonthlyInvestment).filter(MonthlyInvestment.user_id == user_id)
    if year is not None:
        query = query.filter(MonthlyInvestment.year == year)
    return query.order_by(MonthlyInvestment.year, MonthlyInvestment.month).all()

@router.post("/tracker-entries", response_model=TrackerEntrySchema)
def create_tracker_entry(
    tracker_entry: TrackerEntryCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    dated_values = (
        (tracker_entry.income_amount, tracker_entry.income_date, 'income_date'),
        (tracker_entry.investment_amount, tracker_entry.investment_date, 'investment_date'),
    )
    for amount, effective_date, field_name in dated_values:
        if amount > 0 and effective_date and effective_date > date.today():
            raise HTTPException(status_code=400, detail=f"{field_name} cannot be in the future")

    existing = db.query(TrackerEntry).filter(
        TrackerEntry.user_id == user_id,
        TrackerEntry.entry_key == tracker_entry.entry_key,
    ).first()
    if existing:
        return existing

    entry = TrackerEntry(
        user_id=user_id,
        entry_key=tracker_entry.entry_key,
        income_amount=tracker_entry.income_amount,
        income_date=tracker_entry.income_date,
        investment_amount=tracker_entry.investment_amount,
        investment_date=tracker_entry.investment_date,
        destination_platform=tracker_entry.destination_platform,
        note=tracker_entry.note,
    )
    db.add(entry)

    if tracker_entry.income_amount > 0 and tracker_entry.income_date:
        annual_income = _get_or_create_annual_row(
            db, user_id, tracker_entry.income_date.year
        )
        annual_income.income = float(annual_income.income or 0.0) + tracker_entry.income_amount

        monthly_income = _get_or_create_month_row(
            db, user_id, tracker_entry.income_date
        )
        monthly_income.income_received = (
            float(monthly_income.income_received or 0.0) + tracker_entry.income_amount
        )

    if tracker_entry.investment_amount > 0 and tracker_entry.investment_date:
        annual_investment = _get_or_create_annual_row(
            db, user_id, tracker_entry.investment_date.year
        )
        previous_total = float(annual_investment.investment or 0.0)
        new_total = previous_total + tracker_entry.investment_amount
        annual_investment.investment = new_total

        monthly_investment = _get_or_create_month_row(
            db, user_id, tracker_entry.investment_date
        )
        monthly_investment.amount_invested = (
            float(monthly_investment.amount_invested or 0.0)
            + tracker_entry.investment_amount
        )

        db.add(PortfolioCashFlow(
            user_id=user_id,
            effective_date=tracker_entry.investment_date,
            amount=tracker_entry.investment_amount,
            flow_type='contribution',
            destination_platform=tracker_entry.destination_platform,
            previous_invested_total=previous_total,
            new_invested_total=new_total,
            note=tracker_entry.note or 'Investment recorded from Tracker',
            source='tracker_entry',
            event_key=f'tracker_entry:{tracker_entry.entry_key}:investment',
        ))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(TrackerEntry).filter(
            TrackerEntry.user_id == user_id,
            TrackerEntry.entry_key == tracker_entry.entry_key,
        ).first()
        if existing:
            return existing
        raise HTTPException(status_code=409, detail="tracker entry conflicted; please refresh and try again")

    db.refresh(entry)
    return entry

@router.get("/movements", response_model=List[PortfolioCashFlowSchema])
def get_movements(
    flow_type: Optional[Literal['contribution', 'withdrawal', 'transfer', 'correction', 'baseline']] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    query = db.query(PortfolioCashFlow).filter(PortfolioCashFlow.user_id == user_id)
    if flow_type:
        query = query.filter(PortfolioCashFlow.flow_type == flow_type)
    else:
        query = query.filter(PortfolioCashFlow.flow_type.in_((
            'contribution', 'withdrawal', 'transfer'
        )))
    if start_date:
        query = query.filter(PortfolioCashFlow.effective_date >= start_date)
    if end_date:
        query = query.filter(PortfolioCashFlow.effective_date <= end_date)
    return query.order_by(
        PortfolioCashFlow.effective_date.desc(),
        PortfolioCashFlow.id.desc(),
    ).all()

@router.post("/movements", response_model=PortfolioCashFlowSchema)
def create_movement(
    movement: PortfolioCashFlowCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    if movement.effective_date > date.today():
        raise HTTPException(status_code=400, detail="effective_date cannot be in the future")
    if movement.flow_type in {'withdrawal', 'transfer'} and is_standalone_cash_platform(movement.source_platform):
        raise HTTPException(
            status_code=400,
            detail="standalone Cash is outside portfolio performance",
        )
    if movement.flow_type == 'transfer' and is_standalone_cash_platform(movement.destination_platform):
        raise HTTPException(
            status_code=400,
            detail="transfers involving standalone Cash must be recorded as a contribution or withdrawal",
        )
    if movement.event_key:
        existing = db.query(PortfolioCashFlow).filter(
            PortfolioCashFlow.user_id == user_id,
            PortfolioCashFlow.event_key == movement.event_key,
        ).first()
        if existing:
            return existing

    event = PortfolioCashFlow(
        user_id=user_id,
        effective_date=movement.effective_date,
        amount=movement.amount,
        flow_type=movement.flow_type,
        source_platform=movement.source_platform,
        destination_platform=movement.destination_platform,
        previous_invested_total=movement.previous_invested_total,
        new_invested_total=movement.new_invested_total,
        note=movement.note,
        source=movement.source or 'manual',
        event_key=movement.event_key,
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if movement.event_key:
            existing = db.query(PortfolioCashFlow).filter(
                PortfolioCashFlow.user_id == user_id,
                PortfolioCashFlow.event_key == movement.event_key,
            ).first()
            if existing:
                return existing
        raise HTTPException(status_code=409, detail="movement conflicted; please refresh and try again")
    db.refresh(event)
    return event

@router.delete("/movements/{movement_id}")
def delete_movement(
    movement_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    event = db.query(PortfolioCashFlow).filter(
        PortfolioCashFlow.id == movement_id,
        PortfolioCashFlow.user_id == user_id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="movement not found")
    db.delete(event)
    db.commit()
    return {"status": "success", "deleted_id": movement_id}
