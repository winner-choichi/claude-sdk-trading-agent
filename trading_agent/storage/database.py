"""
Database management and operations
"""

import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, desc, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from .models import (
    Base, Trade, TradeFeedback, Strategy, PerformanceSnapshot,
    StrategyParameter, BacktestResult, LearningInsight
)


class Database:
    """Database interface for trading agent"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database connection

        Args:
            config: Database configuration from config.yaml
        """
        self.config = config
        db_type = config.get("type", "sqlite")

        if db_type == "sqlite":
            db_path = config.get("path", "data/trading_agent.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.engine = create_engine(f"sqlite:///{db_path}")
        else:
            # PostgreSQL connection
            host = config.get("host", "localhost")
            port = config.get("port", 5432)
            database = config.get("database", "trading_agent")
            username = config.get("username")
            password = config.get("password")
            connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            self.engine = create_engine(connection_string)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ============ Trade Operations ============

    def save_trade(self, trade_data: Dict[str, Any]) -> Trade:
        """Save a new trade"""
        with self.get_session() as session:
            trade = Trade(**trade_data)
            session.add(trade)
            session.flush()
            return trade

    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get a trade by ID"""
        with self.get_session() as session:
            return session.query(Trade).filter(Trade.trade_id == trade_id).first()

    def get_recent_trades(self, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        with self.get_session() as session:
            return session.query(Trade).order_by(desc(Trade.executed_at)).limit(limit).all()

    def get_open_positions(self) -> List[Trade]:
        """Get all open positions"""
        with self.get_session() as session:
            return session.query(Trade).filter(Trade.status == "open").all()

    def update_trade_pnl(self, trade_id: str, pnl: float, pnl_pct: float, current_price: float) -> None:
        """Update trade P&L"""
        with self.get_session() as session:
            trade = session.query(Trade).filter(Trade.trade_id == trade_id).first()
            if trade:
                trade.pnl = pnl
                trade.pnl_pct = pnl_pct

    def close_trade(self, trade_id: str, close_price: float, pnl: float, pnl_pct: float) -> None:
        """Close a trade"""
        with self.get_session() as session:
            trade = session.query(Trade).filter(Trade.trade_id == trade_id).first()
            if trade:
                trade.status = "closed"
                trade.closed_at = datetime.utcnow()
                trade.pnl = pnl
                trade.pnl_pct = pnl_pct

                # Calculate holding period
                if trade.executed_at:
                    delta = trade.closed_at - trade.executed_at
                    trade.holding_period_hours = delta.total_seconds() / 3600

    # ============ Strategy Operations ============

    def save_strategy(self, strategy_data: Dict[str, Any]) -> Strategy:
        """Save a new strategy"""
        with self.get_session() as session:
            strategy = Strategy(**strategy_data)
            session.add(strategy)
            session.flush()
            return strategy

    def get_strategy(self, name: str) -> Optional[Strategy]:
        """Get a strategy by name"""
        with self.get_session() as session:
            return session.query(Strategy).filter(Strategy.name == name).first()

    def get_active_strategies(self) -> List[Strategy]:
        """Get all active strategies"""
        with self.get_session() as session:
            return session.query(Strategy).filter(Strategy.status == "active").all()

    def update_strategy_performance(self, name: str, metrics: Dict[str, float]) -> None:
        """Update strategy performance metrics"""
        with self.get_session() as session:
            strategy = session.query(Strategy).filter(Strategy.name == name).first()
            if strategy:
                for key, value in metrics.items():
                    setattr(strategy, key, value)
                strategy.last_used_at = datetime.utcnow()

    # ============ Performance Tracking ============

    def save_performance_snapshot(self, snapshot_data: Dict[str, Any]) -> PerformanceSnapshot:
        """Save daily performance snapshot"""
        with self.get_session() as session:
            snapshot = PerformanceSnapshot(**snapshot_data)
            session.add(snapshot)
            session.flush()
            return snapshot

    def get_performance_history(self, days: int = 30) -> List[PerformanceSnapshot]:
        """Get performance history"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        with self.get_session() as session:
            return session.query(PerformanceSnapshot).filter(
                PerformanceSnapshot.date >= cutoff_date
            ).order_by(PerformanceSnapshot.date).all()

    def get_latest_snapshot(self) -> Optional[PerformanceSnapshot]:
        """Get most recent performance snapshot"""
        with self.get_session() as session:
            return session.query(PerformanceSnapshot).order_by(
                desc(PerformanceSnapshot.date)
            ).first()

    # ============ Strategy Parameters ============

    def get_parameter(self, name: str) -> Optional[float]:
        """Get a strategy parameter value"""
        with self.get_session() as session:
            param = session.query(StrategyParameter).filter(
                StrategyParameter.parameter_name == name
            ).first()
            return param.parameter_value if param else None

    def update_parameter(self, name: str, value: float, reason: str) -> None:
        """Update a strategy parameter"""
        with self.get_session() as session:
            param = session.query(StrategyParameter).filter(
                StrategyParameter.parameter_name == name
            ).first()

            if param:
                param.previous_value = param.parameter_value
                param.parameter_value = value
                param.updated_at = datetime.utcnow()
                param.change_reason = reason
                param.trades_since_change = 0
                param.performance_since_change = 0.0
            else:
                param = StrategyParameter(
                    parameter_name=name,
                    parameter_value=value,
                    change_reason=reason
                )
                session.add(param)

    def get_all_parameters(self) -> Dict[str, float]:
        """Get all strategy parameters"""
        with self.get_session() as session:
            params = session.query(StrategyParameter).all()
            return {p.parameter_name: p.parameter_value for p in params}

    # ============ Backtesting ============

    def save_backtest_result(self, result_data: Dict[str, Any]) -> BacktestResult:
        """Save backtest results"""
        with self.get_session() as session:
            result = BacktestResult(**result_data)
            session.add(result)
            session.flush()
            return result

    def get_backtest(self, backtest_id: str) -> Optional[BacktestResult]:
        """Get backtest by ID"""
        with self.get_session() as session:
            return session.query(BacktestResult).filter(
                BacktestResult.backtest_id == backtest_id
            ).first()

    def get_recent_backtests(self, limit: int = 20) -> List[BacktestResult]:
        """Get recent backtests"""
        with self.get_session() as session:
            return session.query(BacktestResult).order_by(
                desc(BacktestResult.executed_at)
            ).limit(limit).all()

    # ============ Learning & Feedback ============

    def save_trade_feedback(self, feedback_data: Dict[str, Any]) -> TradeFeedback:
        """Save trade feedback for learning"""
        with self.get_session() as session:
            feedback = TradeFeedback(**feedback_data)
            session.add(feedback)
            session.flush()
            return feedback

    def save_learning_insight(self, insight_data: Dict[str, Any]) -> LearningInsight:
        """Save a learning insight"""
        with self.get_session() as session:
            insight = LearningInsight(**insight_data)
            session.add(insight)
            session.flush()
            return insight

    def get_active_insights(self) -> List[LearningInsight]:
        """Get active learning insights"""
        with self.get_session() as session:
            return session.query(LearningInsight).filter(
                LearningInsight.status == "active"
            ).all()

    # ============ Analytics ============

    def calculate_win_rate(self, timeframe_days: int = 30) -> float:
        """Calculate win rate over timeframe"""
        cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)

        with self.get_session() as session:
            trades = session.query(Trade).filter(
                and_(
                    Trade.status == "closed",
                    Trade.closed_at >= cutoff_date
                )
            ).all()

            if not trades:
                return 0.0

            wins = sum(1 for t in trades if t.pnl and t.pnl > 0)
            return wins / len(trades)

    def calculate_total_pnl(self, timeframe_days: Optional[int] = None) -> float:
        """Calculate total P&L"""
        with self.get_session() as session:
            query = session.query(Trade).filter(Trade.status == "closed")

            if timeframe_days:
                cutoff_date = datetime.utcnow() - timedelta(days=timeframe_days)
                query = query.filter(Trade.closed_at >= cutoff_date)

            trades = query.all()
            return sum(t.pnl for t in trades if t.pnl)

    def get_trades_by_timeframe(self, timeframe: str = "short") -> List[Trade]:
        """
        Get trades by timeframe for learning

        Args:
            timeframe: short (7 days), medium (30 days), long (90 days)
        """
        days_map = {"short": 7, "medium": 30, "long": 90}
        days = days_map.get(timeframe, 30)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with self.get_session() as session:
            return session.query(Trade).filter(
                Trade.executed_at >= cutoff_date
            ).all()