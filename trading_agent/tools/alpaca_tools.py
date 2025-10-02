"""
Alpaca trading platform integration tools
These are MCP tools that Claude will use for market data and trading
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
from claude_agent_sdk import tool
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame

logger = logging.getLogger(__name__)


# Global clients (will be initialized with config)
_trading_client: TradingClient | None = None
_data_client: StockHistoricalDataClient | None = None
_database = None


def initialize_alpaca(api_key: str, api_secret: str, paper: bool = True):
    """Initialize Alpaca clients"""
    global _trading_client, _data_client
    _trading_client = TradingClient(api_key, api_secret, paper=paper)
    _data_client = StockHistoricalDataClient(api_key, api_secret)


def set_database(db):
    """Set database instance"""
    global _database
    _database = db


@tool(
    "get_market_data",
    "Fetch real-time market data for symbols including price, volume, and technical indicators",
    {
        "symbols": list,  # List of stock symbols
        "timeframe": str,  # "1min", "5min", "1hour", "1day"
        "limit": int  # Number of bars to fetch
    }
)
async def get_market_data(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch market data from Alpaca

    Returns price data, volume, and calculated indicators
    """
    try:
        symbols = args["symbols"]
        timeframe_str = args.get("timeframe", "1day")
        limit = args.get("limit", 100)

        logger.debug("Fetching market data: symbols=%s, timeframe=%s, limit=%d",
                    symbols, timeframe_str, limit)

        # Map timeframe string to Alpaca TimeFrame
        timeframe_map = {
            "1min": TimeFrame.Minute,
            "5min": TimeFrame(5, "Min"),
            "15min": TimeFrame(15, "Min"),
            "1hour": TimeFrame.Hour,
            "1day": TimeFrame.Day
        }
        timeframe = timeframe_map.get(timeframe_str, TimeFrame.Day)

        # Calculate start time
        now = datetime.now()
        if timeframe == TimeFrame.Day:
            start = now - timedelta(days=limit)
        elif timeframe == TimeFrame.Hour:
            start = now - timedelta(hours=limit)
        else:
            start = now - timedelta(minutes=limit * 5)

        # Fetch bar data
        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=timeframe,
            start=start
        )
        bars = _data_client.get_stock_bars(request)

        # Format response
        result = {}
        for symbol in symbols:
            if symbol in bars:
                symbol_bars = bars[symbol]
                result[symbol] = {
                    "symbol": symbol,
                    "data": [
                        {
                            "timestamp": bar.timestamp.isoformat(),
                            "open": float(bar.open),
                            "high": float(bar.high),
                            "low": float(bar.low),
                            "close": float(bar.close),
                            "volume": int(bar.volume)
                        }
                        for bar in symbol_bars[-limit:]
                    ],
                    "latest_price": float(symbol_bars[-1].close) if symbol_bars else None,
                    "volume": int(symbol_bars[-1].volume) if symbol_bars else None
                }

        return {
            "content": [{
                "type": "text",
                "text": f"Market data fetched for {len(symbols)} symbols:\n{str(result)}"
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error fetching market data: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "get_latest_quote",
    "Get the latest quote (bid/ask) for symbols",
    {"symbols": list}
)
async def get_latest_quote(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get real-time quotes"""
    try:
        symbols = args["symbols"]

        request = StockLatestQuoteRequest(symbol_or_symbols=symbols)
        quotes = _data_client.get_stock_latest_quote(request)

        result = {}
        for symbol in symbols:
            if symbol in quotes:
                quote = quotes[symbol]
                result[symbol] = {
                    "bid_price": float(quote.bid_price),
                    "ask_price": float(quote.ask_price),
                    "bid_size": int(quote.bid_size),
                    "ask_size": int(quote.ask_size),
                    "timestamp": quote.timestamp.isoformat()
                }

        return {
            "content": [{
                "type": "text",
                "text": f"Latest quotes:\n{str(result)}"
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error fetching quotes: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "execute_trade",
    "Execute a trade order with confidence scoring",
    {
        "symbol": str,
        "action": str,  # "buy" or "sell"
        "quantity": float,
        "order_type": str,  # "market" or "limit"
        "confidence": float,  # 0-1 confidence score
        "strategy_name": str,
        "reasoning": str,  # Explanation for the trade
        "limit_price": float  # Optional, for limit orders
    }
)
async def execute_trade(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a trade via Alpaca

    This function will be intercepted by hooks for confirmation logic
    """
    try:
        symbol = args["symbol"]
        action = args["action"].lower()
        quantity = int(args["quantity"])
        order_type = args.get("order_type", "market")
        confidence = args["confidence"]
        strategy_name = args["strategy_name"]
        reasoning = args["reasoning"]

        logger.info("Executing trade: symbol=%s, action=%s, qty=%d, confidence=%.2f, strategy=%s",
                   symbol, action, quantity, confidence, strategy_name)

        # Determine order side
        side = OrderSide.BUY if action == "buy" else OrderSide.SELL

        # Create order request
        if order_type == "market":
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.DAY
            )
        else:
            limit_price = args.get("limit_price")
            if not limit_price:
                raise ValueError("limit_price required for limit orders")

            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price
            )

        # Submit order to Alpaca
        order = _trading_client.submit_order(order_data)

        # Save trade to database
        trade_id = str(uuid.uuid4())
        trade_data = {
            "trade_id": trade_id,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": float(order.filled_avg_price) if order.filled_avg_price else 0.0,
            "value": float(order.filled_avg_price or 0) * quantity,
            "executed_at": datetime.utcnow(),
            "order_type": order_type,
            "execution_mode": "live",
            "confidence": confidence,
            "strategy_name": strategy_name,
            "reasoning": reasoning,
            "status": "open" if action == "buy" else "closed"
        }

        if _database:
            _database.save_trade(trade_data)

        logger.info("Trade executed successfully: order_id=%s, symbol=%s, status=%s",
                   order.id, symbol, order.status)

        return {
            "content": [{
                "type": "text",
                "text": f"Trade executed successfully:\n"
                       f"Order ID: {order.id}\n"
                       f"Symbol: {symbol}\n"
                       f"Action: {action.upper()}\n"
                       f"Quantity: {quantity}\n"
                       f"Status: {order.status}\n"
                       f"Confidence: {confidence:.1%}"
            }]
        }

    except Exception as e:
        logger.error("Failed to execute trade: %s", e, exc_info=True)
        return {
            "content": [{
                "type": "text",
                "text": f"Error executing trade: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "get_portfolio",
    "Get current portfolio status including positions, P&L, and cash balance",
    {}
)
async def get_portfolio(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get portfolio information from Alpaca"""
    try:
        logger.debug("Fetching portfolio information")

        # Get account info
        account = _trading_client.get_account()

        # Get all positions
        positions = _trading_client.get_all_positions()

        # Format account info
        account_info = {
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "equity": float(account.equity),
            "last_equity": float(account.last_equity),
            "long_market_value": float(account.long_market_value),
            "short_market_value": float(account.short_market_value)
        }

        # Calculate P&L
        pnl = float(account.equity) - float(account.last_equity)
        pnl_pct = (pnl / float(account.last_equity)) * 100 if float(account.last_equity) > 0 else 0

        account_info["daily_pnl"] = pnl
        account_info["daily_pnl_pct"] = pnl_pct

        # Format positions
        positions_data = []
        for position in positions:
            pos_pnl = float(position.unrealized_pl)
            pos_pnl_pct = float(position.unrealized_plpc) * 100

            positions_data.append({
                "symbol": position.symbol,
                "quantity": int(position.qty),
                "avg_entry_price": float(position.avg_entry_price),
                "current_price": float(position.current_price),
                "market_value": float(position.market_value),
                "unrealized_pnl": pos_pnl,
                "unrealized_pnl_pct": pos_pnl_pct,
                "cost_basis": float(position.cost_basis)
            })

        logger.info("Portfolio fetched: value=$%.2f, positions=%d, daily_pnl=$%.2f",
                   account_info['portfolio_value'], len(positions_data), account_info['daily_pnl'])

        return {
            "content": [{
                "type": "text",
                "text": f"Portfolio Status:\n\n"
                       f"Account:\n"
                       f"  Total Value: ${account_info['portfolio_value']:,.2f}\n"
                       f"  Cash: ${account_info['cash']:,.2f}\n"
                       f"  Equity: ${account_info['equity']:,.2f}\n"
                       f"  Daily P&L: ${account_info['daily_pnl']:,.2f} ({account_info['daily_pnl_pct']:.2f}%)\n\n"
                       f"Positions ({len(positions_data)}):\n" +
                       "\n".join([
                           f"  {p['symbol']}: {p['quantity']} shares @ ${p['current_price']:.2f} "
                           f"(P&L: ${p['unrealized_pnl']:,.2f}, {p['unrealized_pnl_pct']:.2f}%)"
                           for p in positions_data
                       ])
            }]
        }

    except Exception as e:
        logger.error("Failed to fetch portfolio: %s", e, exc_info=True)
        return {
            "content": [{
                "type": "text",
                "text": f"Error fetching portfolio: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "get_account_activity",
    "Get recent account activity and trade history",
    {"limit": int}
)
async def get_account_activity(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get account activity from Alpaca"""
    try:
        limit = args.get("limit", 20)

        # Get recent orders
        orders = _trading_client.get_orders(limit=limit)

        activity = []
        for order in orders:
            activity.append({
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side.value,
                "qty": int(order.qty),
                "type": order.type.value,
                "status": order.status.value,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None
            })

        return {
            "content": [{
                "type": "text",
                "text": f"Recent Activity ({len(activity)} orders):\n" +
                       "\n".join([
                           f"{a['submitted_at']}: {a['side']} {a['qty']} {a['symbol']} @ "
                           f"${a['filled_avg_price']:.2f if a['filled_avg_price'] else 'N/A'} - {a['status']}"
                           for a in activity[:10]
                       ])
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error fetching activity: {str(e)}"
            }],
            "is_error": True
        }


@tool(
    "cancel_order",
    "Cancel a pending order",
    {"order_id": str}
)
async def cancel_order(args: Dict[str, Any]) -> Dict[str, Any]:
    """Cancel an order"""
    try:
        order_id = args["order_id"]
        _trading_client.cancel_order_by_id(order_id)

        return {
            "content": [{
                "type": "text",
                "text": f"Order {order_id} cancelled successfully"
            }]
        }

    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error cancelling order: {str(e)}"
            }],
            "is_error": True
        }


# Export all tools for MCP server creation
ALPACA_TOOLS = [
    get_market_data,
    get_latest_quote,
    execute_trade,
    get_portfolio,
    get_account_activity,
    cancel_order
]