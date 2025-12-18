from app.database import SessionLocal
from app.models import Goal

def debug_goals():
    db = SessionLocal()
    try:
        goals = db.query(Goal).all()
        print(f"Found {len(goals)} goals:")
        for g in goals:
            print(f"ID: {g.id}, Title: '{g.title}', Status: '{g.status}', Target: {g.target_amount}, Date: {g.target_date}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_goals()
