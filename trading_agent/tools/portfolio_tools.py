"""
Portfolio analysis and performance tracking tools
"""

from datetime import datetime, timedelta
from typing import Any, Dict
import numpy as np
from claude_agent_sdk import tool

_database = None


def set_database(db):
    """Set database instance"""
    global _database
    _database = db


@tool(
    "analyze_performance",
    "Analyze trading performance over specified timeframe",
    {
        "timeframe": str,  # "short" (7 days), "medium" (30 days), "long" (90 days), "all"
        "metrics": list  # ["win_rate", "sharpe", "drawdown", "profit_factor", "avg_trade"]
    }
)
async def analyze_performance(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive performance metrics
    """
    try:
        timeframe = args.get("timeframe", "medium")
        requested_metrics = args.get("metrics", ["win_rate", "sharpe", "drawdown"])

        # Map timeframe to days
        days_map = {"short": 7, "medium": 30, "long": 90, "all": None}
        days = days_map.get(timeframe, 30)

        # Get trades
        if days:
            trades = _database.get_trades_by_timeframe(timeframe)
        else:
            trades = _database.get_recent_trades(limit=10000)

        # Filter closed trades
        closed_trades = [t for t in trades if t.status == "closed" and t.pnl is not None]

        if not closed_trades:
            return {
                "content": [{
                    "type": "text",
                    "text": f"No closed trades in {timeframe} timeframe"
                }]
            }

        # Calculate metrics
        metrics = {}

        # Win rate
        if "win_rate" in requested_metrics:
            wins = sum(1 for t in closed_trades if t.pnl > 0)
            metrics["win_rate"] = wins / len(closed_trades)

        # Total P&L
        total_pnl = sum(t.pnl for t in closed_trades)
        metrics["total_pnl"] = total_pnl

        # Average trade
        if "avg_trade" in requested_metrics:
            metrics["avg_trade_pnl"] = total_pnl / len(closed_trades)

        # Profit factor
        if "profit_factor" in requested_metrics:
            gross_profit = sum(t.pnl for t in closed_trades if t.pnl > 0)
            gross_loss = abs(sum(t.pnl for t in closed_trades if t.pnl < 0))
            metrics["profit_factor"] = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Sharpe ratio (simplified - using trade returns)
        if "sharpe" in requested_metrics:
            returns = [t.pnl_pct for t in closed_trades if t.pnl_pct is not None]
            if returns:
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                metrics["sharpe_ratio"] = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0

        # Max drawdown
        if "drawdown" in requested_metrics:
            cumulative_pnl = 0
            peak = 0
            max_dd = 0

            for trade in sorted(closed_trades, key=lambda t: t.closed_at):
                cumulative_pnl += trade.pnl
                if cumulative_pnl > peak:
                    peak = cumulative_pnl
                drawdown = (peak - cumulative_pnl) / peak if peak > 0 else 0
                if drawdown > max_dd:
                    max_dd = drawdown

            metrics["max_drawdown_pct"] = max_dd * 100

        # Format response
        response_text = f"Performance Analysis ({timeframe} timeframe):\n\n"
        response_text += f"Total Trades: {len(closed_trades)}\n"
        response_text += f"Total P&L: ${metrics['total_pnl']:,.2f}\n"

        if "win_rate" in metrics:
            response_text += f"Win Rate: {metrics['win_rate']:.1%}\n"
        if "avg_trade_pnl" in metrics:
            response_text += f"Average Trade: ${metrics['avg_trade_pnl']:,.2f}\n"
        if "profit_factor" in metrics:
            response_text += f"Profit Factor: {metrics['profit_factor']:.2f}\n"
        if "sharpe_ratio" in metrics:
            response_text += f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n"
        if "max_drawdown_pct" in metrics:
            response_text += f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%\n"

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
                "text": f"Error analyzing performance: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "store_feedback",
    "Store trade feedback for learning system",
    {
        "trade_id": str,
        "timeframe": str,  # "short", "medium", "long"
        "outcome": str,  # "win", "loss", "breakeven"
        "confidence_accurate": bool,
        "market_condition": dict,
        "insights": str
    }
)
async def store_feedback(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Store feedback about a trade for the learning system
    """
    try:
        trade_id = args["trade_id"]

        # Get the trade
        trade = _database.get_trade(trade_id)
        if not trade:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Trade {trade_id} not found"
                }],
                "is_error": True
            }

        # Calculate confidence accuracy
        if trade.pnl and trade.confidence:
            expected_pnl = trade.confidence * 100  # Simplified
            confidence_accuracy = 1.0 - abs((trade.pnl - expected_pnl) / expected_pnl) if expected_pnl != 0 else 0
        else:
            confidence_accuracy = 0

        # Save feedback
        feedback_data = {
            "trade_id": trade.id,
            "timeframe": args["timeframe"],
            "evaluated_at": datetime.utcnow(),
            "outcome": args["outcome"],
            "actual_pnl": trade.pnl,
            "expected_pnl": trade.confidence * 100 if trade.confidence else 0,
            "confidence_accuracy": confidence_accuracy,
            "market_condition": args.get("market_condition"),
            "insights": args.get("insights", "")
        }

        _database.save_trade_feedback(feedback_data)

        return {
            "content": [{
                "type": "text",
                "text": f"Feedback stored for trade {trade_id}\n"
                       f"Outcome: {args['outcome']}\n"
                       f"Confidence Accuracy: {confidence_accuracy:.2f}"
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error storing feedback: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "get_strategy_performance",
    "Get performance metrics for a specific strategy",
    {"strategy_name": str}
)
async def get_strategy_performance(args: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze performance of a specific strategy"""
    try:
        strategy_name = args["strategy_name"]

        strategy = _database.get_strategy(strategy_name)
        if not strategy:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Strategy '{strategy_name}' not found"
                }],
                "is_error": True
            }

        response_text = f"Strategy: {strategy_name}\n"
        response_text += f"Status: {strategy.status}\n"
        response_text += f"Total Trades: {strategy.total_trades}\n"

        if strategy.win_rate is not None:
            response_text += f"Win Rate: {strategy.win_rate:.1%}\n"
        if strategy.avg_pnl is not None:
            response_text += f"Average P&L: ${strategy.avg_pnl:.2f}\n"
        if strategy.sharpe_ratio is not None:
            response_text += f"Sharpe Ratio: {strategy.sharpe_ratio:.2f}\n"
        if strategy.max_drawdown is not None:
            response_text += f"Max Drawdown: {strategy.max_drawdown:.2f}%\n"

        response_text += f"\nCreated: {strategy.created_at.strftime('%Y-%m-%d')}\n"
        if strategy.last_used_at:
            response_text += f"Last Used: {strategy.last_used_at.strftime('%Y-%m-%d %H:%M')}\n"

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
                "text": f"Error fetching strategy performance: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "update_strategy_parameters",
    "Update strategy parameters based on learning",
    {
        "parameter_name": str,
        "new_value": float,
        "reason": str
    }
)
async def update_strategy_parameters(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a strategy parameter (e.g., confidence threshold)
    """
    try:
        param_name = args["parameter_name"]
        new_value = args["new_value"]
        reason = args["reason"]

        # Get old value
        old_value = _database.get_parameter(param_name)

        # Update parameter
        _database.update_parameter(param_name, new_value, reason)

        return {
            "content": [{
                "type": "text",
                "text": f"Parameter Updated:\n"
                       f"  Name: {param_name}\n"
                       f"  Old Value: {old_value}\n"
                       f"  New Value: {new_value}\n"
                       f"  Reason: {reason}"
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error updating parameter: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "get_current_parameters",
    "Get all current strategy parameters",
    {}
)
async def get_current_parameters(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all strategy parameters"""
    try:
        params = _database.get_all_parameters()

        response_text = "Current Strategy Parameters:\n\n"
        for name, value in params.items():
            response_text += f"  {name}: {value}\n"

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
                "text": f"Error fetching parameters: {str(e)}"
            }],
            "is_error": True
        }


# Export all tools
PORTFOLIO_TOOLS = [
    analyze_performance,
    store_feedback,
    get_strategy_performance,
    update_strategy_parameters,
    get_current_parameters
]