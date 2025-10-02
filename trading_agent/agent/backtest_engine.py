"""
Backtesting engine for strategy validation
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame


class BacktestEngine:
    """
    Run trading strategies against historical data
    """

    def __init__(
        self,
        initial_capital: float,
        start_date: str,
        end_date: str,
        commission: float = 0.0,
        slippage_pct: float = 0.1,
        data_client: Optional[StockHistoricalDataClient] = None,
        database=None
    ):
        """
        Initialize backtest engine

        Args:
            initial_capital: Starting cash
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)
            commission: Commission per trade (Alpaca is 0)
            slippage_pct: Slippage percentage (default 0.1%)
            data_client: Alpaca data client
            database: Database instance for storing results
        """
        self.initial_capital = initial_capital
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.commission = commission
        self.slippage = slippage_pct / 100.0

        self.data_client = data_client
        self.database = database

        # Simulated account state
        self.cash = initial_capital
        self.positions: Dict[str, float] = {}  # symbol -> quantity
        self.trade_history: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []

        # Current simulation time
        self.current_time: Optional[datetime] = None

        # Historical data cache
        self.price_data: Dict[str, pd.DataFrame] = {}

    def load_historical_data(self, symbols: List[str], timeframe: str = "1day") -> None:
        """
        Load historical data for symbols

        Args:
            symbols: List of stock symbols
            timeframe: Data timeframe (1day, 1hour, etc.)
        """
        if not self.data_client:
            raise ValueError("Data client not initialized")

        # Map timeframe string
        timeframe_map = {
            "1min": TimeFrame.Minute,
            "5min": TimeFrame(5, "Min"),
            "15min": TimeFrame(15, "Min"),
            "1hour": TimeFrame.Hour,
            "1day": TimeFrame.Day
        }
        tf = timeframe_map.get(timeframe, TimeFrame.Day)

        # Fetch data
        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=tf,
            start=self.start_date,
            end=self.end_date
        )

        bars = self.data_client.get_stock_bars(request)

        # Convert to DataFrame for each symbol
        for symbol in symbols:
            if symbol in bars:
                symbol_bars = bars[symbol]
                df = pd.DataFrame([
                    {
                        "timestamp": bar.timestamp,
                        "open": float(bar.open),
                        "high": float(bar.high),
                        "low": float(bar.low),
                        "close": float(bar.close),
                        "volume": int(bar.volume)
                    }
                    for bar in symbol_bars
                ])
                df.set_index("timestamp", inplace=True)
                self.price_data[symbol] = df

    def get_price(self, symbol: str, timestamp: datetime, price_type: str = "close") -> Optional[float]:
        """
        Get price at specific timestamp

        Args:
            symbol: Stock symbol
            timestamp: Time to get price
            price_type: "open", "high", "low", "close"

        Returns:
            Price or None if not available
        """
        if symbol not in self.price_data:
            return None

        df = self.price_data[symbol]

        # Find closest timestamp
        try:
            # Get exact match or nearest
            if timestamp in df.index:
                return df.loc[timestamp, price_type]
            else:
                # Get nearest past price
                past_prices = df[df.index <= timestamp]
                if not past_prices.empty:
                    return past_prices.iloc[-1][price_type]
        except Exception:
            pass

        return None

    def simulate_trade(
        self,
        symbol: str,
        action: str,
        quantity: float,
        timestamp: datetime,
        confidence: float = 1.0,
        strategy_name: str = "backtest",
        reasoning: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Simulate a trade execution

        Args:
            symbol: Stock symbol
            action: "buy" or "sell"
            quantity: Number of shares
            timestamp: Execution time
            confidence: Trade confidence (0-1)
            strategy_name: Strategy that generated this trade
            reasoning: Explanation

        Returns:
            Trade result dict or None if failed
        """
        # Get price
        price = self.get_price(symbol, timestamp, "close")
        if not price:
            return None

        # Apply slippage
        if action == "buy":
            fill_price = price * (1 + self.slippage)
        else:
            fill_price = price * (1 - self.slippage)

        # Calculate trade value
        trade_value = fill_price * quantity + self.commission

        # Execute trade
        if action == "buy":
            if trade_value > self.cash:
                return None  # Insufficient funds

            self.cash -= trade_value
            self.positions[symbol] = self.positions.get(symbol, 0) + quantity

            trade_record = {
                "trade_id": str(uuid.uuid4()),
                "timestamp": timestamp,
                "symbol": symbol,
                "action": "buy",
                "quantity": quantity,
                "price": fill_price,
                "value": trade_value,
                "confidence": confidence,
                "strategy_name": strategy_name,
                "reasoning": reasoning,
                "cash_after": self.cash
            }

            self.trade_history.append(trade_record)
            return trade_record

        elif action == "sell":
            if symbol not in self.positions or self.positions[symbol] < quantity:
                return None  # Insufficient shares

            proceeds = (fill_price * quantity) - self.commission
            self.cash += proceeds
            self.positions[symbol] -= quantity

            if self.positions[symbol] == 0:
                del self.positions[symbol]

            trade_record = {
                "trade_id": str(uuid.uuid4()),
                "timestamp": timestamp,
                "symbol": symbol,
                "action": "sell",
                "quantity": quantity,
                "price": fill_price,
                "value": proceeds,
                "confidence": confidence,
                "strategy_name": strategy_name,
                "reasoning": reasoning,
                "cash_after": self.cash
            }

            self.trade_history.append(trade_record)
            return trade_record

        return None

    def calculate_portfolio_value(self, timestamp: datetime) -> float:
        """
        Calculate total portfolio value at timestamp

        Args:
            timestamp: Time to calculate value

        Returns:
            Total portfolio value
        """
        total = self.cash

        for symbol, quantity in self.positions.items():
            price = self.get_price(symbol, timestamp, "close")
            if price:
                total += price * quantity

        return total

    def record_equity(self, timestamp: datetime) -> None:
        """
        Record equity at timestamp

        Args:
            timestamp: Time to record
        """
        equity = self.calculate_portfolio_value(timestamp)
        self.equity_curve.append({
            "timestamp": timestamp,
            "equity": equity,
            "cash": self.cash,
            "positions_value": equity - self.cash
        })

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive backtest report

        Returns:
            Performance metrics dictionary
        """
        if not self.equity_curve:
            return {}

        # Final value
        final_value = self.equity_curve[-1]["equity"]
        total_return = final_value - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100

        # Calculate metrics from equity curve
        equity_series = pd.Series([point["equity"] for point in self.equity_curve])

        # Returns
        returns = equity_series.pct_change().dropna()

        # Sharpe ratio (annualized, assuming 252 trading days)
        if len(returns) > 1 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0

        # Maximum drawdown
        cummax = equity_series.cummax()
        drawdown = (equity_series - cummax) / cummax
        max_drawdown = drawdown.min() * 100  # As percentage

        # Trade statistics
        closed_trades = self._calculate_closed_trades()
        total_trades = len(closed_trades)

        if total_trades > 0:
            winning_trades = [t for t in closed_trades if t["pnl"] > 0]
            losing_trades = [t for t in closed_trades if t["pnl"] < 0]

            win_rate = len(winning_trades) / total_trades
            avg_trade_pnl = sum(t["pnl"] for t in closed_trades) / total_trades

            # Profit factor
            gross_profit = sum(t["pnl"] for t in winning_trades)
            gross_loss = abs(sum(t["pnl"] for t in losing_trades))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        else:
            win_rate = 0.0
            avg_trade_pnl = 0.0
            profit_factor = 0.0

        # Compile report
        report = {
            "initial_capital": self.initial_capital,
            "final_value": final_value,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": total_trades,
            "avg_trade_pnl": avg_trade_pnl,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
            "trading_days": len(self.equity_curve),
            "equity_curve": [
                {
                    "date": point["timestamp"].strftime("%Y-%m-%d"),
                    "equity": point["equity"]
                }
                for point in self.equity_curve
            ],
            "trade_history": self.trade_history
        }

        return report

    def _calculate_closed_trades(self) -> List[Dict[str, Any]]:
        """
        Calculate P&L for closed trades (matched buy/sell pairs)

        Returns:
            List of closed trades with P&L
        """
        closed = []
        positions_tracker = {}  # symbol -> [(buy_price, quantity), ...]

        for trade in self.trade_history:
            symbol = trade["symbol"]
            action = trade["action"]
            quantity = trade["quantity"]
            price = trade["price"]

            if action == "buy":
                if symbol not in positions_tracker:
                    positions_tracker[symbol] = []
                positions_tracker[symbol].append({
                    "buy_price": price,
                    "quantity": quantity,
                    "timestamp": trade["timestamp"]
                })

            elif action == "sell":
                if symbol in positions_tracker and positions_tracker[symbol]:
                    # Match with oldest buy (FIFO)
                    remaining = quantity
                    while remaining > 0 and positions_tracker[symbol]:
                        buy = positions_tracker[symbol][0]
                        matched_qty = min(remaining, buy["quantity"])

                        # Calculate P&L
                        pnl = (price - buy["buy_price"]) * matched_qty
                        pnl_pct = ((price - buy["buy_price"]) / buy["buy_price"]) * 100

                        closed.append({
                            "symbol": symbol,
                            "quantity": matched_qty,
                            "buy_price": buy["buy_price"],
                            "sell_price": price,
                            "pnl": pnl,
                            "pnl_pct": pnl_pct,
                            "entry_time": buy["timestamp"],
                            "exit_time": trade["timestamp"]
                        })

                        # Update remaining
                        remaining -= matched_qty
                        buy["quantity"] -= matched_qty

                        if buy["quantity"] <= 0:
                            positions_tracker[symbol].pop(0)

        return closed

    def save_results(self, backtest_id: str, strategy_name: str, strategy_description: str, symbols: List[str]) -> None:
        """
        Save backtest results to database

        Args:
            backtest_id: Unique backtest ID
            strategy_name: Name of strategy
            strategy_description: Strategy description
            symbols: Symbols tested
        """
        if not self.database:
            return

        report = self.generate_report()

        result_data = {
            "backtest_id": backtest_id,
            "strategy_name": strategy_name,
            "strategy_description": strategy_description,
            "symbols": symbols,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "final_value": report["final_value"],
            "total_return": report["total_return"],
            "total_return_pct": report["total_return_pct"],
            "sharpe_ratio": report["sharpe_ratio"],
            "max_drawdown": report["max_drawdown"],
            "win_rate": report["win_rate"],
            "profit_factor": report["profit_factor"],
            "total_trades": report["total_trades"],
            "avg_trade_pnl": report["avg_trade_pnl"],
            "trading_days": report["trading_days"],
            "equity_curve": report["equity_curve"],
            "trade_history": self.trade_history,
            "executed_at": datetime.utcnow(),
            "status": "completed"
        }

        self.database.save_backtest_result(result_data)