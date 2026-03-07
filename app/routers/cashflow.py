from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models import IncomeData
from app.schemas import IncomeData as IncomeDataSchema

router = APIRouter(
    prefix="/cashflow",
    tags=["cashflow"]
)

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
