"""
Backtesting tools for Claude agent
"""

import uuid
from datetime import datetime
from typing import Any, Dict
from claude_agent_sdk import tool
from agent.backtest_engine import BacktestEngine

_data_client = None
_database = None


def set_data_client(client):
    """Set Alpaca data client"""
    global _data_client
    _data_client = client


def set_database(db):
    """Set database instance"""
    global _database
    _database = db


@tool(
    "run_backtest",
    "Run a backtest for a trading strategy on historical data",
    {
        "strategy_description": str,
        "symbols": list,
        "start_date": str,  # YYYY-MM-DD
        "end_date": str,  # YYYY-MM-DD
        "initial_capital": float,
        "timeframe": str  # "1day", "1hour", etc.
    }
)
async def run_backtest(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a full backtest

    The agent should describe the strategy in strategy_description,
    and this tool will simulate it on historical data.

    Note: This is a simplified version. In practice, the agent would
    need to make trading decisions for each time period.
    """
    try:
        strategy_desc = args["strategy_description"]
        symbols = args["symbols"]
        start_date = args["start_date"]
        end_date = args["end_date"]
        initial_capital = args.get("initial_capital", 100000.0)
        timeframe = args.get("timeframe", "1day")

        # Create backtest engine
        engine = BacktestEngine(
            initial_capital=initial_capital,
            start_date=start_date,
            end_date=end_date,
            commission=0.0,
            slippage_pct=0.1,
            data_client=_data_client,
            database=_database
        )

        # Load historical data
        engine.load_historical_data(symbols, timeframe)

        # Generate unique backtest ID
        backtest_id = f"bt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Run backtest simulation
        # Current implementation: Simple momentum strategy (buy on 5-day lows, sell on 5-day highs)
        # Future enhancement: Allow Claude to make trading decisions at each step based on strategy description
        _simulate_simple_strategy(engine, symbols)

        # Generate report
        report = engine.generate_report()

        # Save results
        engine.save_results(
            backtest_id=backtest_id,
            strategy_name="Custom Strategy",
            strategy_description=strategy_desc,
            symbols=symbols
        )

        # Format response
        response_text = f"""
Backtest Complete: {backtest_id}

Strategy: {strategy_desc}
Symbols: {', '.join(symbols)}
Period: {start_date} to {end_date}

Performance:
  Initial Capital: ${report['initial_capital']:,.2f}
  Final Value: ${report['final_value']:,.2f}
  Total Return: ${report['total_return']:,.2f} ({report['total_return_pct']:.2f}%)

Metrics:
  Sharpe Ratio: {report['sharpe_ratio']:.2f}
  Max Drawdown: {report['max_drawdown']:.2f}%
  Win Rate: {report['win_rate']:.1%}
  Profit Factor: {report['profit_factor']:.2f}

Trading Activity:
  Total Trades: {report['total_trades']}
  Average Trade P&L: ${report['avg_trade_pnl']:.2f}
  Trading Days: {report['trading_days']}
"""

        return {
            "content": [{
                "type": "text",
                "text": response_text
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error running backtest: {str(e)}"
            }],
            "is_error": True
        }


def _simulate_simple_strategy(engine: BacktestEngine, symbols: list) -> None:
    """
    Simulate a simple momentum strategy for demonstration

    In production, Claude would make these decisions via the trading loop
    """
    # Get all dates from first symbol
    if not symbols or not engine.price_data:
        return

    first_symbol = symbols[0]
    if first_symbol not in engine.price_data:
        return

    dates = engine.price_data[first_symbol].index.tolist()

    # Simple strategy: Buy on 5-day lows, sell on 5-day highs
    for i, date in enumerate(dates):
        if i < 5:  # Need lookback period
            continue

        engine.record_equity(date)

        for symbol in symbols:
            if symbol not in engine.price_data:
                continue

            df = engine.price_data[symbol]
            if date not in df.index:
                continue

            # Get recent prices
            recent = df.loc[:date].tail(5)
            current_price = df.loc[date, "close"]

            # Check if we have a position
            has_position = symbol in engine.positions

            # Simple momentum: buy if at 5-day low, sell if at 5-day high
            if not has_position and current_price <= recent["low"].min():
                # Buy signal
                max_shares = int((engine.cash * 0.1) / current_price)  # 10% of cash
                if max_shares > 0:
                    engine.simulate_trade(
                        symbol=symbol,
                        action="buy",
                        quantity=max_shares,
                        timestamp=date,
                        confidence=0.7,
                        strategy_name="Simple Momentum",
                        reasoning="Price at 5-day low"
                    )

            elif has_position and current_price >= recent["high"].max():
                # Sell signal
                quantity = engine.positions.get(symbol, 0)
                if quantity > 0:
                    engine.simulate_trade(
                        symbol=symbol,
                        action="sell",
                        quantity=quantity,
                        timestamp=date,
                        confidence=0.7,
                        strategy_name="Simple Momentum",
                        reasoning="Price at 5-day high"
                    )

    # Record final equity
    if dates:
        engine.record_equity(dates[-1])


@tool(
    "get_backtest_results",
    "Get results from a previous backtest",
    {"backtest_id": str}
)
async def get_backtest_results(args: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve backtest results from database"""
    try:
        backtest_id = args["backtest_id"]

        if not _database:
            return {
                "content": [{
                    "type": "text",
                    "text": "Database not initialized"
                }],
                "is_error": True
            }

        result = _database.get_backtest(backtest_id)

        if not result:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Backtest {backtest_id} not found"
                }],
                "is_error": True
            }

        response_text = f"""
Backtest: {result.backtest_id}
Strategy: {result.strategy_name}
Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}

Performance:
  Total Return: {result.total_return_pct:.2f}%
  Sharpe Ratio: {result.sharpe_ratio:.2f}
  Max Drawdown: {result.max_drawdown:.2f}%
  Win Rate: {result.win_rate:.1%}
  Profit Factor: {result.profit_factor:.2f}
  Total Trades: {result.total_trades}
"""

        return {
            "content": [{
                "type": "text",
                "text": response_text
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error retrieving backtest: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "list_recent_backtests",
    "List recent backtest results",
    {"limit": int}
)
async def list_recent_backtests(args: Dict[str, Any]) -> Dict[str, Any]:
    """List recent backtests"""
    try:
        limit = args.get("limit", 10)

        if not _database:
            return {
                "content": [{
                    "type": "text",
                    "text": "Database not initialized"
                }],
                "is_error": True
            }

        backtests = _database.get_recent_backtests(limit)

        if not backtests:
            return {
                "content": [{
                    "type": "text",
                    "text": "No backtests found"
                }]
            }

        response_text = f"Recent Backtests ({len(backtests)}):\n\n"

        for bt in backtests:
            response_text += f"ID: {bt.backtest_id}\n"
            response_text += f"  Strategy: {bt.strategy_name}\n"
            response_text += f"  Return: {bt.total_return_pct:.2f}%\n"
            response_text += f"  Sharpe: {bt.sharpe_ratio:.2f}\n"
            response_text += f"  Trades: {bt.total_trades}\n"
            response_text += f"  Date: {bt.executed_at.strftime('%Y-%m-%d %H:%M')}\n\n"

        return {
            "content": [{
                "type": "text",
                "text": response_text
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error listing backtests: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "compare_backtests",
    "Compare performance of multiple backtests",
    {"backtest_ids": list}
)
async def compare_backtests(args: Dict[str, Any]) -> Dict[str, Any]:
    """Compare multiple backtest results"""
    try:
        backtest_ids = args["backtest_ids"]

        if not _database:
            return {
                "content": [{
                    "type": "text",
                    "text": "Database not initialized"
                }],
                "is_error": True
            }

        results = []
        for bt_id in backtest_ids:
            result = _database.get_backtest(bt_id)
            if result:
                results.append(result)

        if not results:
            return {
                "content": [{
                    "type": "text",
                    "text": "No backtests found"
                }],
                "is_error": True
            }

        # Create comparison table
        response_text = "Backtest Comparison:\n\n"
        response_text += f"{'Strategy':<30} {'Return':<12} {'Sharpe':<10} {'Drawdown':<12} {'Win Rate':<12}\n"
        response_text += "-" * 80 + "\n"

        for result in results:
            response_text += f"{result.strategy_name[:28]:<30} "
            response_text += f"{result.total_return_pct:>10.2f}%  "
            response_text += f"{result.sharpe_ratio:>8.2f}  "
            response_text += f"{result.max_drawdown:>10.2f}%  "
            response_text += f"{result.win_rate:>10.1%}\n"

        # Find best performer
        best = max(results, key=lambda r: r.sharpe_ratio)
        response_text += f"\nBest Performer (by Sharpe): {best.strategy_name}\n"

        return {
            "content": [{
                "type": "text",
                "text": response_text
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error comparing backtests: {str(e)}"
            }],
            "is_error": True
        }


# Export all tools
BACKTEST_TOOLS = [
    run_backtest,
    get_backtest_results,
    list_recent_backtests,
    compare_backtests
]