"""
Database models for trading agent
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, Column, Integer, Float, String,
    DateTime, Boolean, JSON, Text, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()


class Trade(Base):
    """Record of executed trades"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(100), unique=True, nullable=False, index=True)

    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    action = Column(String(10), nullable=False)  # buy, sell
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    value = Column(Float, nullable=False)

    # Execution details
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    order_type = Column(String(20), default="market")  # market, limit
    execution_mode = Column(String(20))  # auto, manual, backtest

    # Decision context
    confidence = Column(Float)  # Agent's confidence (0-1)
    strategy_name = Column(String(100))
    reasoning = Column(Text)  # Agent's explanation

    # Performance tracking
    pnl = Column(Float)  # Profit/loss (calculated on close)
    pnl_pct = Column(Float)  # P&L percentage
    holding_period_hours = Column(Float)  # Time between open and close

    # Status
    status = Column(String(20), default="open")  # open, closed
    closed_at = Column(DateTime)

    # Relationships
    feedbacks = relationship("TradeFeedback", back_populates="trade")

    def to_dict(self):
        return {
            "id": self.id,
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "value": self.value,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "confidence": self.confidence,
            "strategy_name": self.strategy_name,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "status": self.status
        }


class TradeFeedback(Base):
    """Performance feedback for learning"""
    __tablename__ = "trade_feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)

    # Feedback timeframe
    timeframe = Column(String(20), nullable=False)  # short, medium, long
    evaluated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Outcome metrics
    outcome = Column(String(20))  # win, loss, breakeven
    actual_pnl = Column(Float)
    expected_pnl = Column(Float)
    confidence_accuracy = Column(Float)  # Was confidence justified?

    # Market context
    market_condition = Column(JSON)  # Volatility, trend, etc.

    # Learning insights
    insights = Column(Text)

    # Relationships
    trade = relationship("Trade", back_populates="feedbacks")


class Strategy(Base):
    """Trading strategies (evolving)"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    # Strategy definition
    description = Column(Text, nullable=False)
    parameters = Column(JSON)  # Strategy-specific parameters

    # Lifecycle
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    status = Column(String(20), default="active")  # active, retired, testing

    # Performance metrics
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float)
    avg_pnl = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)

    # Evolution tracking
    parent_strategy_id = Column(Integer, ForeignKey("strategies.id"))
    version = Column(Integer, default=1)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "status": self.status,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "sharpe_ratio": self.sharpe_ratio
        }


class PerformanceSnapshot(Base):
    """Daily performance snapshots"""
    __tablename__ = "performance_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)

    # Portfolio metrics
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)

    # Performance
    daily_pnl = Column(Float)
    daily_pnl_pct = Column(Float)
    total_return = Column(Float)
    total_return_pct = Column(Float)

    # Risk metrics
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    volatility = Column(Float)

    # Trading activity
    trades_today = Column(Integer, default=0)
    win_rate = Column(Float)


class StrategyParameter(Base):
    """Current strategy parameters (evolving)"""
    __tablename__ = "strategy_parameters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parameter_name = Column(String(100), unique=True, nullable=False, index=True)
    parameter_value = Column(Float, nullable=False)

    # Evolution tracking
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    previous_value = Column(Float)
    change_reason = Column(Text)

    # Performance since change
    trades_since_change = Column(Integer, default=0)
    performance_since_change = Column(Float)


class BacktestResult(Base):
    """Backtest execution results"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    backtest_id = Column(String(100), unique=True, nullable=False, index=True)

    # Backtest configuration
    strategy_name = Column(String(100), nullable=False)
    strategy_description = Column(Text)
    symbols = Column(JSON)  # List of symbols
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, nullable=False)

    # Results
    final_value = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    total_return_pct = Column(Float, nullable=False)

    # Performance metrics
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    total_trades = Column(Integer)
    avg_trade_pnl = Column(Float)

    # Time info
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    trading_days = Column(Integer)

    # Detailed data (stored as JSON)
    equity_curve = Column(JSON)  # [{date, equity}, ...]
    trade_history = Column(JSON)  # [{date, symbol, action, ...}, ...]

    # Status
    status = Column(String(20), default="completed")  # completed, deployed, retired
    deployed_at = Column(DateTime)

    def to_dict(self):
        return {
            "backtest_id": self.backtest_id,
            "strategy_name": self.strategy_name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "total_return_pct": self.total_return_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades
        }


class LearningInsight(Base):
    """Meta-learning insights"""
    __tablename__ = "learning_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Insight details
    insight_type = Column(String(50), nullable=False)  # strategy, risk, timing, etc.
    description = Column(Text, nullable=False)
    confidence = Column(Float)

    # Evidence
    supporting_data = Column(JSON)

    # Impact
    action_taken = Column(Text)  # What the agent did with this insight
    result = Column(Text)  # Outcome of the action

    # Status
    status = Column(String(20), default="active")  # active, validated, invalidated