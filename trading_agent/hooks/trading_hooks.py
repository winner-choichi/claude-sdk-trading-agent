"""
Trading hooks for dynamic trade confirmation
"""

from typing import Dict, Any
from datetime import datetime


class TradingHooks:
    """
    Hooks for intercepting and controlling trade execution
    """

    def __init__(self, strategy_manager, database):
        """
        Initialize trading hooks

        Args:
            strategy_manager: AutonomousStrategyManager instance
            database: Database instance
        """
        self.strategy_manager = strategy_manager
        self.database = database
        self.slack_bot = None  # Will be set by agent
        self.pending_approvals = {}  # Store pending trade approvals

    async def pre_trade_hook(
        self,
        input_data: Dict[str, Any],
        tool_use_id: str | None,
        context: Any
    ) -> Dict[str, Any]:
        """
        Hook called before trade execution

        Decides whether to:
        - Auto-execute (high confidence + good recent performance)
        - Request user confirmation (medium confidence)
        - Block (insufficient funds, risk limits exceeded)

        Args:
            input_data: Tool input data
            tool_use_id: Tool use ID
            context: Hook context

        Returns:
            Hook response dict
        """
        # Only intercept execute_trade calls
        # Tool becomes "mcp__trading__execute_trade" when wrapped in MCP server
        tool_name = input_data.get("tool_name", "UNKNOWN")
        if tool_name not in ["execute_trade", "mcp__trading__execute_trade"]:
            return {}

        tool_input = input_data.get("tool_input", {})
        confidence = tool_input.get("confidence", 0)
        symbol = tool_input.get("symbol", "")
        action = tool_input.get("action", "")
        quantity = tool_input.get("quantity", 0)
        strategy_name = tool_input.get("strategy_name", "")
        reasoning = tool_input.get("reasoning", "")

        # Get recent performance
        recent_performance = self._get_recent_performance()

        # Check if should auto-execute
        should_auto = self.strategy_manager.should_auto_execute(
            confidence=confidence,
            recent_performance=recent_performance
        )

        # Check risk limits
        risk_check = self._check_risk_limits(tool_input, recent_performance)
        if not risk_check["allowed"]:
            # Block trade
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": risk_check["reason"]
                }
            }

        if should_auto:
            # Auto-execute - allow immediately
            print(f"✅ Auto-executing trade: {action.upper()} {quantity} {symbol} (confidence: {confidence:.1%})")
            return {}  # Empty dict = allow

        else:
            # Block trade and request user confirmation via Slack
            threshold = self.strategy_manager.get_auto_trade_threshold()

            message = f"""Trade requires approval (confidence {confidence:.1%} below threshold {threshold:.1%}).

Please review and manually approve if desired."""

            # Send detailed approval request to Slack
            if self.slack_bot:
                try:
                    # Hook is async, so we can await directly
                    await self._send_approval_request(
                        symbol=symbol,
                        action=action,
                        quantity=quantity,
                        confidence=confidence,
                        strategy_name=strategy_name,
                        reasoning=reasoning,
                        recent_performance=recent_performance,
                        threshold=threshold
                    )
                    print(f"✅ Approval request sent to Slack")
                except Exception as e:
                    print(f"⚠️  Error sending approval request: {e}")

            print(f"⏸️  BLOCKING TRADE - Confidence {confidence:.1%} < threshold {threshold:.1%}")

            # Return "deny" because "ask" doesn't work programmatically
            # The reason will be shown to Claude
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": message.strip()
                }
            }

    async def post_trade_hook(
        self,
        input_data: Dict[str, Any],
        tool_use_id: str | None,
        context: Any
    ) -> Dict[str, Any]:
        """
        Hook called after trade execution

        Logs the trade and updates strategy performance

        Args:
            input_data: Tool input data
            tool_use_id: Tool use ID
            context: Hook context

        Returns:
            Hook response dict
        """
        # Only process execute_trade calls
        tool_name = input_data.get("tool_name", "UNKNOWN")
        if tool_name not in ["execute_trade", "mcp__trading__execute_trade"]:
            return {}

        tool_input = input_data.get("tool_input", {})
        tool_output = input_data.get("tool_output", {})

        # Log trade execution
        print(f"📊 Trade executed: {tool_input.get('symbol')} - {tool_input.get('action').upper()}")

        # Update strategy performance tracking
        strategy_name = tool_input.get("strategy_name")
        if strategy_name:
            self.strategy_manager.update_strategy_performance(
                strategy_name=strategy_name,
                trade_result=tool_input
            )

        return {}

    async def _send_approval_request(
        self,
        symbol: str,
        action: str,
        quantity: int,
        confidence: float,
        strategy_name: str,
        reasoning: str,
        recent_performance: Dict[str, Any],
        threshold: float
    ):
        """Send trade approval request to Slack"""
        try:
            message = f"""🤔 **Trade Approval Required**

**Trade Details:**
• Symbol: {symbol}
• Action: {action.upper()}
• Quantity: {quantity}
• Order Type: Market
• Confidence: {confidence:.1%} _(below threshold: {threshold:.1%})_

**Strategy:** {strategy_name}

**Reasoning:** {reasoning}

**Recent Performance:**
• Win Rate: {recent_performance.get('win_rate', 0):.1%}
• Daily P&L: ${recent_performance.get('daily_pnl', 0):.2f}

**To approve and execute this trade:**
```
/test-trade {symbol} {action} {quantity} --force
```

**Alternatives:**
• Increase auto-trade threshold: `/update-threshold 0.50`
• Reject: Do nothing, trade will not execute
"""

            if hasattr(self.slack_bot, '_post_message'):
                await self.slack_bot._post_message(text=message)
        except Exception as e:
            print(f"⚠️  Failed to send approval request to Slack: {e}")

    def _get_recent_performance(self) -> Dict[str, Any]:
        """Get recent performance metrics"""
        try:
            # Get trades from last 7 days
            trades = self.database.get_trades_by_timeframe("short")

            # Convert to list and extract data (to avoid SQLAlchemy session issues)
            closed_trades = []
            for t in trades:
                try:
                    if hasattr(t, 'status') and t.status == "closed" and hasattr(t, 'pnl') and t.pnl is not None:
                        closed_trades.append({
                            'pnl': float(t.pnl),
                            'closed_at': t.closed_at if hasattr(t, 'closed_at') else None
                        })
                except Exception:
                    continue

            if not closed_trades:
                return {
                    "win_rate": 0.5,
                    "daily_pnl": 0.0,
                    "daily_pnl_pct": 0.0
                }

            # Calculate win rate
            wins = sum(1 for t in closed_trades if t['pnl'] > 0)
            win_rate = wins / len(closed_trades)

            # Get today's P&L
            from datetime import datetime
            today = datetime.utcnow().date()
            today_trades = [
                t for t in closed_trades
                if t['closed_at'] and t['closed_at'].date() == today
            ]
            daily_pnl = sum(t['pnl'] for t in today_trades)

            # Get latest snapshot for percentage
            try:
                snapshot = self.database.get_latest_snapshot()
                daily_pnl_pct = snapshot.daily_pnl_pct if snapshot and hasattr(snapshot, 'daily_pnl_pct') else 0.0
            except Exception:
                daily_pnl_pct = 0.0

            return {
                "win_rate": win_rate,
                "daily_pnl": daily_pnl,
                "daily_pnl_pct": daily_pnl_pct,
                "recent_trades": len(closed_trades)
            }

        except Exception as e:
            print(f"Error getting recent performance: {e}")
            return {
                "win_rate": 0.5,
                "daily_pnl": 0.0,
                "daily_pnl_pct": 0.0
            }

    def _check_risk_limits(
        self,
        tool_input: Dict[str, Any],
        recent_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if trade violates risk limits

        Args:
            tool_input: Trade parameters
            recent_performance: Recent performance data

        Returns:
            Dict with "allowed" (bool) and "reason" (str)
        """
        # Check daily loss limit
        daily_pnl_pct = recent_performance.get("daily_pnl_pct", 0)
        loss_limit = self.strategy_manager.get_parameter("daily_loss_limit_pct")

        if daily_pnl_pct < -loss_limit:
            return {
                "allowed": False,
                "reason": f"Daily loss limit exceeded ({daily_pnl_pct:.2f}% < -{loss_limit:.2f}%)"
            }

        # Additional checks could include:
        # - Max portfolio exposure
        # - Single position size limits
        # - Maximum trades per day
        # For now, just check the critical daily loss limit

        return {
            "allowed": True,
            "reason": "All risk checks passed"
        }

    def create_hook_config(self) -> Dict[str, Any]:
        """
        Create hook configuration for ClaudeAgentOptions

        Returns:
            Hooks dict ready for ClaudeAgentOptions
        """
        from claude_agent_sdk import HookMatcher

        # Match both the local tool name and the MCP-wrapped name
        config = {
            "PreToolUse": [
                HookMatcher(
                    matcher="execute_trade",
                    hooks=[self.pre_trade_hook]
                ),
                HookMatcher(
                    matcher="mcp__trading__execute_trade",
                    hooks=[self.pre_trade_hook]
                )
            ],
            "PostToolUse": [
                HookMatcher(
                    matcher="execute_trade",
                    hooks=[self.post_trade_hook]
                ),
                HookMatcher(
                    matcher="mcp__trading__execute_trade",
                    hooks=[self.post_trade_hook]
                )
            ]
        }

        return config