from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models import Goal
from app.schemas import GoalCreate, Goal as GoalSchema
from datetime import datetime

router = APIRouter(
    prefix="/goals",
    tags=["goals"]
)

@router.get("/", response_model=List[GoalSchema])
def get_goals(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    return db.query(Goal).filter(Goal.user_id == user_id).all()

@router.post("/", response_model=GoalSchema)
def create_goal(
    goal: GoalCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    db_goal = Goal(
        user_id=user_id,
        title=goal.title,
        description=goal.description,
        target_amount=goal.target_amount,
        target_date=goal.target_date,
        status=goal.status
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.patch("/{goal_id}", response_model=GoalSchema)
def update_goal(
    goal_id: int,
    updates: dict,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    db_goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    for key, value in updates.items():
        if hasattr(db_goal, key):
            setattr(db_goal, key, value)
    
    db_goal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    db_goal = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    db.delete(db_goal)
    db.commit()
    return None
