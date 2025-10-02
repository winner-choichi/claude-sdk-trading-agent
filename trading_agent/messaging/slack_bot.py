"""
Slack bot integration for trading agent
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError

from .slack_formatter import format_for_slack, create_slack_blocks

logger = logging.getLogger(__name__)


class TradingSlackBot:
    """
    Slack bot for real-time trading agent control and monitoring
    """

    def __init__(self, trading_agent, config: Dict[str, Any]):
        """
        Initialize Slack bot

        Args:
            trading_agent: TradingAgent instance
            config: Slack configuration
        """
        self.agent = trading_agent
        self.config = config

        # Initialize Slack app
        self.app = AsyncApp(
            token=config.get("bot_token"),
            signing_secret=config.get("signing_secret")
        )

        # Channel for notifications
        self.channel_id = config.get("channel_id")

        # Register handlers
        self._register_commands()
        self._register_message_handlers()

    async def _send_formatted(self, say, text: str, **kwargs):
        """
        Send formatted message to Slack

        Args:
            say: Slack say function
            text: Text to format and send
            **kwargs: Additional arguments for say()
        """
        # Format markdown for Slack
        formatted_text = format_for_slack(text)

        # For long responses, use blocks
        if len(formatted_text) > 3000:
            blocks = create_slack_blocks(formatted_text)
            await say(text=formatted_text[:200] + "...", blocks=blocks, **kwargs)
        else:
            await say(formatted_text, **kwargs)

    def _register_commands(self) -> None:
        """Register Slack slash commands"""

        @self.app.command("/trading-report")
        async def handle_report_command(ack, command, say):
            """Generate daily report on demand"""
            await ack()
            logger.info("Received /trading-report command from user %s", command.get("user_id"))

            await say("📊 Generating trading report...")

            try:
                report = await self.agent.generate_daily_report()
                logger.debug("Report generated, length: %d chars", len(report))
                await say(text="📊 Daily Trading Report", blocks=self._format_report_blocks(report))
                logger.info("Trading report sent successfully")
            except Exception as e:
                logger.error("Error generating report: %s", e, exc_info=True)
                await say(f"❌ Error generating report: {str(e)}")

        @self.app.command("/portfolio")
        async def handle_portfolio_command(ack, command, say):
            """Get portfolio status"""
            await ack()
            logger.info("Received /portfolio command from user %s", command.get("user_id"))

            try:
                response = await self.agent.handle_user_query(
                    "Get current portfolio status with detailed positions and P&L",
                    user_id=command["user_id"]
                )
                await self._send_formatted(say, response)
                logger.info("Portfolio status sent successfully")
            except Exception as e:
                logger.error("Error fetching portfolio: %s", e, exc_info=True)
                await say(f"❌ Error fetching portfolio: {str(e)}")

        @self.app.command("/backtest")
        async def handle_backtest_command(ack, command, say):
            """Run a backtest"""
            await ack()
            logger.info("Received /backtest command from user %s", command.get("user_id"))

            # Parse command: /backtest AAPL,MSFT 2023-01-01 2023-12-31
            text = command.get("text", "")
            parts = text.split()

            if len(parts) < 3:
                logger.warning("Invalid /backtest command format: %s", text)
                await say("Usage: `/backtest SYMBOLS START_DATE END_DATE [STRATEGY]`\n"
                         "Example: `/backtest AAPL,MSFT 2023-01-01 2023-12-31`")
                return

            symbols = parts[0]
            start_date = parts[1]
            end_date = parts[2]
            strategy = parts[3] if len(parts) > 3 else "autonomous strategy"

            logger.info("Starting backtest: symbols=%s, start=%s, end=%s, strategy=%s",
                       symbols, start_date, end_date, strategy)
            await say(f"🔄 Running backtest for {symbols} from {start_date} to {end_date}...")

            try:
                query = f"""
Run a backtest with these parameters:
- Symbols: {symbols}
- Start Date: {start_date}
- End Date: {end_date}
- Strategy: {strategy}
- Initial Capital: $100,000

Use the run_backtest tool and provide comprehensive results.
                """

                response = await self.agent.handle_user_query(
                    query,
                    user_id=command["user_id"]
                )

                await say(response)
                logger.info("Backtest completed successfully")
            except Exception as e:
                logger.error("Error running backtest: %s", e, exc_info=True)
                await say(f"❌ Error running backtest: {str(e)}")

        @self.app.command("/parameters")
        async def handle_parameters_command(ack, command, say):
            """Get current strategy parameters"""
            await ack()

            try:
                response = await self.agent.handle_user_query(
                    "Show current strategy parameters using get_current_parameters tool",
                    user_id=command["user_id"]
                )
                await say(response)
            except Exception as e:
                await say(f"❌ Error fetching parameters: {str(e)}")

        @self.app.command("/performance")
        async def handle_performance_command(ack, command, say):
            """Analyze performance"""
            await ack()

            timeframe = command.get("text", "medium").strip() or "medium"

            try:
                response = await self.agent.handle_user_query(
                    f"Analyze {timeframe} term performance with detailed metrics",
                    user_id=command["user_id"]
                )
                await say(response)
            except Exception as e:
                await say(f"❌ Error analyzing performance: {str(e)}")

        @self.app.command("/test-trade")
        async def handle_test_trade_command(ack, command, say):
            """Test trade execution flow"""
            await ack()
            logger.info("Received /test-trade command from user %s", command.get("user_id"))

            # Parse command: /test-trade AAPL buy 1 [--force]
            text = command.get("text", "").strip()
            parts = text.split()

            if len(parts) < 3:
                await say("Usage: `/test-trade SYMBOL ACTION QUANTITY [--force]`\n"
                         "Example: `/test-trade AAPL buy 1`\n"
                         "Example: `/test-trade SPY sell 5 --force`\n"
                         "Add `--force` to bypass approval and execute immediately")
                return

            symbol, action, quantity = parts[0].upper(), parts[1].lower(), parts[2]

            if action not in ["buy", "sell"]:
                await say("❌ Action must be 'buy' or 'sell'")
                return

            try:
                quantity = int(quantity)
            except ValueError:
                await say("❌ Quantity must be a number")
                return

            # Check for --force flag
            force = "--force" in parts or "-f" in parts
            confidence = 0.95 if force else 0.50  # High confidence bypasses approval

            status_emoji = "⚡" if force else "🧪"
            await say(f"{status_emoji} Testing trade execution: {action.upper()} {quantity} {symbol}{' (FORCE)' if force else ''}")

            try:
                query = f"""
Execute a TEST trade with these parameters:
- Symbol: {symbol}
- Action: {action}
- Quantity: {quantity}
- Order Type: market
- Confidence: {confidence} ({'HIGH - auto-execute' if force else 'medium - will trigger approval flow'})
- Strategy: manual_test
- Reasoning: Manual test trade via /test-trade Slack command{' (FORCE-EXECUTED)' if force else ''}

This is a test to verify the trading flow works correctly.
                """

                response = await self.agent.handle_user_query(
                    query,
                    user_id=command["user_id"]
                )

                # Format response for Slack
                await self._send_formatted(say, response)
                logger.info("Test trade completed successfully")

            except Exception as e:
                logger.error("Error executing test trade: %s", e, exc_info=True)
                await say(f"❌ Test trade failed: {str(e)}")

        @self.app.command("/check-orders")
        async def handle_check_orders_command(ack, command, say):
            """Check status of recent orders"""
            await ack()
            logger.info("Received /check-orders command from user %s", command.get("user_id"))

            await say("📋 Checking recent orders and positions...")

            try:
                query = """
Please check:
1. My current portfolio positions using get_portfolio
2. Recent account activity using get_account_activity
3. Summary of any pending or recently filled orders

Provide a clear status update.
                """

                response = await self.agent.handle_user_query(
                    query,
                    user_id=command["user_id"]
                )

                await self._send_formatted(say, response)
                logger.info("Order check completed successfully")

            except Exception as e:
                logger.error("Error checking orders: %s", e, exc_info=True)
                await say(f"❌ Error checking orders: {str(e)}")

        @self.app.command("/pause-trading")
        async def handle_pause_command(ack, command, say):
            """Emergency pause trading"""
            await ack()
            logger.info("Received /pause-trading command from user %s", command.get("user_id"))

            await say("⏸️  Pausing trading agent...")

            try:
                await self.agent.stop()
                await say("✅ Trading agent paused. Use `/resume-trading` to restart.")
                logger.info("Trading agent paused successfully")
            except Exception as e:
                logger.error("Error pausing agent: %s", e, exc_info=True)
                await say(f"❌ Error pausing agent: {str(e)}")

        @self.app.command("/resume-trading")
        async def handle_resume_command(ack, command, say):
            """Resume trading"""
            await ack()
            logger.info("Received /resume-trading command from user %s", command.get("user_id"))

            await say("▶️  Resuming trading agent...")

            try:
                # Start agent in background (non-blocking)
                self.agent.start_background()
                await say("✅ Trading agent resumed.")
                logger.info("Trading agent resumed successfully")
            except Exception as e:
                logger.error("Error resuming agent: %s", e, exc_info=True)
                await say(f"❌ Error resuming agent: {str(e)}")

        @self.app.command("/status")
        async def handle_status_command(ack, command, say):
            """Check agent status"""
            await ack()
            logger.info("Received /status command from user %s", command.get("user_id"))

            try:
                status = "🟢 Running" if self.agent.is_running else "🔴 Paused"
                mode = self.agent.mode
                tasks_count = len(self.agent._background_tasks)

                await say(
                    f"**Trading Agent Status**\n"
                    f"Status: {status}\n"
                    f"Mode: {mode}\n"
                    f"Background Tasks: {tasks_count}"
                )
            except Exception as e:
                logger.error("Error fetching status: %s", e, exc_info=True)
                await say(f"❌ Error fetching status: {str(e)}")

        @self.app.command("/evolve")
        async def handle_evolve_command(ack, command, say):
            """Manually trigger evolution cycle"""
            await ack()
            logger.info("Received /evolve command from user %s", command.get("user_id"))

            await say("🧬 Starting evolution cycle...")

            try:
                await self.agent.run_evolution_cycle()
                await say("✅ Evolution cycle complete. Check parameters for changes.")
                logger.info("Evolution cycle completed successfully")
            except Exception as e:
                logger.error("Error in evolution cycle: %s", e, exc_info=True)
                await say(f"❌ Error in evolution cycle: {str(e)}")

        @self.app.command("/update-threshold")
        async def handle_update_threshold_command(ack, command, say):
            """Update auto-trade confidence threshold"""
            await ack()
            logger.info("Received /update-threshold command from user %s", command.get("user_id"))

            text = command.get("text", "").strip()

            if not text:
                current_threshold = self.agent.strategy_manager.get_auto_trade_threshold()
                await say(f"📊 **Current Auto-Trade Threshold:** {current_threshold:.1%}\n\n"
                         f"Usage: `/update-threshold VALUE`\n"
                         f"Example: `/update-threshold 0.70` (70%)\n"
                         f"Example: `/update-threshold 0.90` (90%)")
                return

            try:
                new_threshold = float(text)

                if new_threshold < 0 or new_threshold > 1:
                    await say("❌ Threshold must be between 0 and 1 (e.g., 0.85 = 85%)")
                    return

                old_threshold = self.agent.strategy_manager.get_auto_trade_threshold()
                self.agent.strategy_manager.update_parameter("auto_trade_threshold", new_threshold)

                await say(f"✅ **Auto-Trade Threshold Updated**\n\n"
                         f"Old: {old_threshold:.1%}\n"
                         f"New: {new_threshold:.1%}\n\n"
                         f"Trades with confidence ≥ {new_threshold:.1%} will now auto-execute.\n"
                         f"Trades below {new_threshold:.1%} require approval.")

                logger.info("Updated auto-trade threshold: %.2f -> %.2f", old_threshold, new_threshold)

            except ValueError:
                await say("❌ Invalid threshold value. Use a decimal between 0 and 1.\n"
                         "Example: `/update-threshold 0.85`")
            except Exception as e:
                logger.error("Error updating threshold: %s", e, exc_info=True)
                await say(f"❌ Error updating threshold: {str(e)}")

    def _register_message_handlers(self) -> None:
        """Register message handlers for natural language queries"""

        @self.app.message("trading")
        async def handle_trading_message(message, say):
            """Handle messages mentioning 'trading'"""
            user_id = message["user"]
            text = message["text"]

            try:
                response = await self.agent.handle_user_query(text, user_id=user_id)
                await say(response)
            except Exception as e:
                await say(f"❌ Error: {str(e)}")

        @self.app.event("app_mention")
        async def handle_mention(event, say):
            """Handle @mentions of the bot"""
            user_id = event["user"]
            text = event["text"]

            # Remove bot mention from text
            text = text.split(">", 1)[-1].strip()

            try:
                response = await self.agent.handle_user_query(text, user_id=user_id)
                await say(response)
            except Exception as e:
                await say(f"❌ Error: {str(e)}")

    async def send_alert(self, alert: Dict[str, Any]) -> None:
        """
        Send alert to Slack channel

        Args:
            alert: Alert data dictionary
        """
        alert_type = alert.get("type")
        logger.debug("Sending alert: type=%s", alert_type)

        if alert_type == "trade_opportunity":
            await self._send_trade_opportunity(alert)
        elif alert_type == "trade_executed":
            await self._send_trade_executed(alert)
        elif alert_type == "daily_report":
            await self._send_daily_report(alert)
        elif alert_type == "parameter_change":
            await self._send_parameter_change(alert)
        elif alert_type == "error":
            await self._send_error_alert(alert)
        else:
            logger.warning("Unknown alert type: %s", alert_type)

    async def _send_trade_opportunity(self, alert: Dict[str, Any]) -> None:
        """Send trade opportunity alert with approval buttons"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🎯 Trading Opportunity"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Symbol:*\n{alert.get('symbol')}"},
                    {"type": "mrkdwn", "text": f"*Action:*\n{alert.get('action', '').upper()}"},
                    {"type": "mrkdwn", "text": f"*Quantity:*\n{alert.get('quantity')}"},
                    {"type": "mrkdwn", "text": f"*Confidence:*\n{alert.get('confidence', 0):.1%}"},
                    {"type": "mrkdwn", "text": f"*Strategy:*\n{alert.get('strategy_name')}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reasoning:*\n{alert.get('reasoning', 'N/A')}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Approve"},
                        "style": "primary",
                        "action_id": "approve_trade",
                        "value": alert.get("trade_id", "")
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Reject"},
                        "style": "danger",
                        "action_id": "reject_trade",
                        "value": alert.get("trade_id", "")
                    }
                ]
            }
        ]

        await self._post_message(blocks=blocks)

    async def _send_trade_executed(self, alert: Dict[str, Any]) -> None:
        """Send trade execution notification"""
        mode = alert.get("mode", "manual")
        emoji = "🤖" if mode == "auto" else "👤"

        text = f"{emoji} **Trade Executed** ({mode})\n"
        text += f"Symbol: {alert.get('symbol')}\n"
        text += f"Action: {alert.get('action', '').upper()}\n"
        text += f"Quantity: {alert.get('quantity')}\n"
        text += f"Price: ${alert.get('price', 0):.2f}\n"
        text += f"Confidence: {alert.get('confidence', 0):.1%}"

        await self._post_message(text=text)

    async def _post_message(self, *, text: Optional[str] = None, blocks: Optional[list] = None) -> None:
        """Safely send messages to Slack without failing the agent."""
        if not self.channel_id:
            logger.warning("Slack channel_id not configured; skipping message")
            print("❌ Slack channel_id not configured; skipping message")
            return

        try:
            logger.debug("Posting message to Slack channel %s", self.channel_id)
            await self.app.client.chat_postMessage(
                channel=self.channel_id,
                text=text,
                blocks=blocks
            )
            logger.debug("Message posted successfully")
        except SlackApiError as error:
            api_error = error.response.get("error") if error.response else str(error)
            if api_error == "channel_not_found":
                logger.error("Slack channel not found: %s", self.channel_id)
                print(
                    "❌ Slack channel not found. Confirm the bot is invited and the channel_id is correct: "
                    f"{self.channel_id}"
                )
            else:
                logger.error("Slack API error: %s", api_error)
                print(f"❌ Slack API error sending message: {api_error}")
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Unexpected Slack error: %s", exc, exc_info=True)
            print(f"❌ Unexpected Slack error: {exc}")

    async def _send_daily_report(self, alert: Dict[str, Any]) -> None:
        """Send daily report"""
        report = alert.get("report", "")

        blocks = self._format_report_blocks(report)

        await self._post_message(blocks=blocks)

    async def _send_parameter_change(self, alert: Dict[str, Any]) -> None:
        """Send parameter change notification"""
        text = f"🔧 **Parameter Updated**\n"
        text += f"Parameter: {alert.get('parameter')}\n"
        text += f"Old Value: {alert.get('old_value')}\n"
        text += f"New Value: {alert.get('new_value')}\n"
        text += f"Reason: {alert.get('reason')}"

        await self._post_message(text=text)

    async def _send_error_alert(self, alert: Dict[str, Any]) -> None:
        """Send error alert"""
        text = f"🚨 **ERROR**\n{alert.get('message')}"

        await self._post_message(text=text)

    def _convert_markdown_to_slack(self, text: str) -> str:
        """
        Convert markdown syntax to Slack mrkdwn format

        Args:
            text: Text with markdown formatting

        Returns:
            Text with Slack mrkdwn formatting
        """
        import re

        # Convert **bold** to *bold*
        text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)

        # Convert emoji shortcuts (:emoji:) - already compatible
        # Convert --- or === to nothing (we use dividers instead)
        text = re.sub(r'^[\-=]{3,}$', '', text, flags=re.MULTILINE)

        return text

    def _format_report_blocks(self, report: str) -> list:
        """
        Format report as Slack blocks with proper visual hierarchy
        Converts markdown-style report to native Slack blocks
        """
        blocks = []

        # Convert markdown bold (**text**) to Slack bold (*text*)
        report = self._convert_markdown_to_slack(report)

        # Parse report into sections
        sections = self._parse_report_sections(report)

        for section in sections:
            section_type = section.get("type")

            if section_type == "header":
                # Main header
                blocks.append({
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": section["text"],
                        "emoji": True
                    }
                })

            elif section_type == "section_header":
                # Section headers with dividers
                blocks.append({"type": "divider"})
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{section['text']}*"
                    }
                })

            elif section_type == "fields":
                # Key-value pairs as fields
                fields = []
                for key, value in section["data"].items():
                    fields.append({
                        "type": "mrkdwn",
                        "text": f"*{key}*\n{value}"
                    })

                # Slack allows max 10 fields per block
                for i in range(0, len(fields), 10):
                    blocks.append({
                        "type": "section",
                        "fields": fields[i:i+10]
                    })

            elif section_type == "text":
                # Regular text content
                text = section["text"]
                # Slack has 3000 char limit per block
                if len(text) <= 3000:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": text
                        }
                    })
                else:
                    # Split long text
                    chunks = self._split_text(text, 3000)
                    for chunk in chunks:
                        blocks.append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": chunk
                            }
                        })

        # Add timestamp footer
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":clock1: Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })

        return blocks

    def _parse_report_sections(self, report: str) -> list:
        """
        Parse markdown-style report into structured sections

        Returns:
            List of section dicts with type and content
        """
        sections = []
        lines = report.split('\n')

        current_section = None
        current_text = []

        for line in lines:
            # Main header (# TITLE)
            if line.startswith('# '):
                if current_section:
                    sections.append(current_section)
                sections.append({
                    "type": "header",
                    "text": line[2:].strip()
                })
                current_section = None
                current_text = []

            # Section header (## TITLE)
            elif line.startswith('## '):
                if current_section:
                    if current_text:
                        current_section["text"] = '\n'.join(current_text)
                    sections.append(current_section)

                current_section = {
                    "type": "section_header",
                    "text": line[3:].strip()
                }
                current_text = []

            # Bullet points or regular text
            elif line.strip():
                current_text.append(line)
            elif current_text:
                # Empty line - save accumulated text
                if current_section and current_section.get("type") == "section_header":
                    sections.append(current_section)
                    current_section = None

                sections.append({
                    "type": "text",
                    "text": '\n'.join(current_text)
                })
                current_text = []

        # Add final section
        if current_text:
            if current_section:
                sections.append(current_section)
            sections.append({
                "type": "text",
                "text": '\n'.join(current_text)
            })
        elif current_section:
            sections.append(current_section)

        return sections

    def _split_text(self, text: str, max_length: int) -> list:
        """Split text into chunks at newlines, respecting max_length"""
        chunks = []
        current_chunk = ""

        for line in text.split('\n'):
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    async def start(self) -> None:
        """Start the Slack bot"""
        print("🚀 Starting Slack bot...")
        logger.info("Starting Slack bot with Socket Mode")

        app_token = self.config.get("app_token")
        if not app_token:
            logger.error("Slack app_token not configured")
            print("❌ Slack app_token not configured")
            return

        handler = AsyncSocketModeHandler(self.app, app_token)
        logger.info("Socket Mode handler created, starting async listener")
        await handler.start_async()

    async def send_startup_message(self) -> None:
        """Send startup notification"""
        mode = self.agent.mode
        text = f"🤖 **Trading Agent Started**\n"
        text += f"Mode: {mode}\n"
        text += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"\nAvailable commands:\n"
        text += "`/trading-report` - Daily report\n"
        text += "`/portfolio` - Portfolio status\n"
        text += "`/test-trade SYMBOL ACTION QTY` - Test trade execution\n"
        text += "`/check-orders` - Check recent orders\n"
        text += "`/backtest` - Run backtest\n"
        text += "`/parameters` - View parameters\n"
        text += "`/performance` - Analyze performance\n"
        text += "`/status` - Check agent status\n"
        text += "`/pause-trading` - Pause agent\n"
        text += "`/resume-trading` - Resume agent\n"
        text += "`/evolve` - Trigger evolution"

        await self.app.client.chat_postMessage(
            channel=self.channel_id,
            text=text
        )


async def create_slack_bot(trading_agent, config: Dict[str, Any]) -> Optional[TradingSlackBot]:
    """
    Create and initialize Slack bot

    Args:
        trading_agent: TradingAgent instance
        config: Slack configuration

    Returns:
        TradingSlackBot instance or None if not configured
    """
    bot_token = config.get("bot_token")
    app_token = config.get("app_token")

    if not bot_token or not app_token:
        print("ℹ️  Slack not configured, skipping bot initialization")
        return None

    bot = TradingSlackBot(trading_agent, config)
    return bot
