from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship

from datetime import datetime
import json
from app.database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON, default={})

    investments = relationship("Investment", back_populates="user")
    platform_cash = relationship("PlatformCash", back_populates="user")
    monthly_financial_records = relationship("MonthlyFinancialRecord", back_populates="user")
    expenses = relationship("Expense", back_populates="user")
    monthly_commitments = relationship("MonthlyCommitment", back_populates="user")
    income_data = relationship("IncomeData", back_populates="user")
    monthly_breakdown = relationship("MonthlyBreakdown", back_populates="user")
    monthly_investments = relationship("MonthlyInvestment", back_populates="user")
    goals = relationship("Goal", back_populates="user")
    net_worth_snapshots = relationship("NetWorthSnapshot", back_populates="user")

class Investment(Base):
    __tablename__ = 'investments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    platform = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    symbol = Column(String(50))
    holdings = Column(Float, default=0.0)
    amount_spent = Column(Float, default=0.0)
    average_buy_price = Column(Float, default=0.0)
    current_price = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="investments")
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'name': self.name,
            'symbol': self.symbol,
            'holdings': self.holdings,
            'amount_spent': self.amount_spent,
            'average_buy_price': self.average_buy_price,
            'current_price': self.current_price,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class PlatformCash(Base):
    __tablename__ = 'platform_cash'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    platform = Column(String(100), nullable=False)
    cash_balance = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="platform_cash")
    
    __table_args__ = (UniqueConstraint('user_id', 'platform', name='unique_user_platform_cash'),)

    def to_dict(self):
        return {
            'platform': self.platform,
            'cash_balance': self.cash_balance,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class MonthlyFinancialRecord(Base):
    """
    Replaces "NetworthEntry". 
    Represents the closed books or summary for a specific month.
    """
    __tablename__ = 'monthly_financial_records'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    period_date = Column(Date, nullable=False) # First day of the month, e.g., 2024-01-01
    
    net_worth = Column(Float, default=0.0)
    total_income = Column(Float, default=0.0)
    total_expenses = Column(Float, default=0.0)
    total_invested = Column(Float, default=0.0)
    
    details = Column(JSON, default={}) # Flexible breakdown
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="monthly_financial_records")

    # Unique constraint for period per user
    __table_args__ = (UniqueConstraint('user_id', 'period_date', name='unique_user_period_record'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'period_date': self.period_date.isoformat() if self.period_date else None,
            'net_worth': self.net_worth,
            'total_income': self.total_income,
            'total_expenses': self.total_expenses,
            'total_invested': self.total_invested,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Expense(Base):
    __tablename__ = 'expenses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(200), nullable=False)
    monthly_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="expenses")
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'monthly_amount': self.monthly_amount,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class MonthlyCommitment(Base):
    __tablename__ = 'monthly_commitments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    platform = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    monthly_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="monthly_commitments")
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'name': self.name,
            'monthly_amount': self.monthly_amount,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class IncomeData(Base):
    __tablename__ = 'income_data'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    year = Column(String(20), nullable=False)
    income = Column(Float, default=0.0)
    investment = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="income_data")

    # Unique constraint for year per user
    __table_args__ = (UniqueConstraint('user_id', 'year', name='unique_user_year_income'),)
    
    def to_dict(self):
        return {
            'year': self.year,
            'income': self.income,
            'investment': self.investment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class MonthlyBreakdown(Base):
    __tablename__ = 'monthly_breakdown'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    monthly_income = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="monthly_breakdown")
    
    def to_dict(self):
        return {
            'monthly_income': self.monthly_income,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class MonthlyInvestment(Base):
    __tablename__ = 'monthly_investments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    month_name = Column(String(20), nullable=False)  # "January", "February", etc.
    income_received = Column(Float, default=0.0)
    amount_invested = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="monthly_investments")

    # Unique constraint for year+month combination per user
    __table_args__ = (UniqueConstraint('user_id', 'year', 'month', name='unique_user_year_month_investment'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'year': self.year,
            'month': self.month,
            'month_name': self.month_name,
            'income_received': self.income_received,
            'amount_invested': self.amount_invested,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Goal(Base):
    __tablename__ = 'goals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    target_amount = Column(Float, nullable=False)
    target_date = Column(Date, nullable=False)
    status = Column(String(20), default='active')  # active, completed, paused
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="goals")
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'target_amount': self.target_amount,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class NetWorthSnapshot(Base):
    """
    Replaces "HistoricalNetWorth" and "DailyHistoricalNetWorth".
    Stores point-in-time snapshots of total net worth and asset breakdown.
    """
    __tablename__ = 'net_worth_snapshots'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    total_amount = Column(Float, nullable=False)
    assets_breakdown = Column(JSON, nullable=False, default={}) # {"Vanguard": 1000, "Cash": 500}
    currency = Column(String(3), default='GBP')
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="net_worth_snapshots")
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'total_amount': self.total_amount,
            'assets_breakdown': self.assets_breakdown,
            'currency': self.currency,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
