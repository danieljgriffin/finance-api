from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models import Expense, IncomeData
from app.schemas import ExpenseCreate, Expense as ExpenseSchema, IncomeData as IncomeDataSchema

router = APIRouter(
    prefix="/cashflow",
    tags=["cashflow"]
)

@router.get("/expenses", response_model=List[ExpenseSchema])
def get_expenses(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    return db.query(Expense).filter(Expense.user_id == user_id).all()

@router.post("/expenses", response_model=ExpenseSchema)
def add_expense(
    expense: ExpenseCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    db_expense = Expense(
        user_id=user_id,
        name=expense.name,
        monthly_amount=expense.monthly_amount
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.get("/income", response_model=List[IncomeDataSchema])
def get_income_data(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    # Auto-create current year if it doesn't exist
    from datetime import datetime
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
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    entry = db.query(IncomeData).filter(
        IncomeData.user_id == user_id,
        IncomeData.year == year
    ).first()
    
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
    
    db.commit()
    db.refresh(entry)
    return entry
