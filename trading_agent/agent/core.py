"""
Core Trading Agent
Main agent that coordinates all components
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, create_sdk_mcp_server, AssistantMessage, TextBlock

from .autonomous_strategy import AutonomousStrategyManager
from .meta_learning import MetaLearningSystem
from hooks.trading_hooks import TradingHooks

logger = logging.getLogger(__name__)


class TradingAgent:
    """
    Main autonomous trading agent

    Integrates:
    - Market data and trading (Alpaca)
    - Portfolio management
    - Backtesting
    - Autonomous strategy management
    - Meta-learning
    - Dynamic hooks
    """

    def __init__(
        self,
        config: Dict[str, Any],
        database,
        alpaca_tools: list,
        portfolio_tools: list,
        backtest_tools: list,
        alpaca_trading_client,
        alpaca_data_client,
        external_mcp_servers: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize trading agent

        Args:
            config: Configuration dict
            database: Database instance
            alpaca_tools: List of Alpaca MCP tools
            portfolio_tools: List of portfolio MCP tools
            backtest_tools: List of backtest MCP tools
            alpaca_trading_client: Alpaca trading client
            alpaca_data_client: Alpaca data client
            external_mcp_servers: External MCP server configurations
        """
        logger.info("Initializing TradingAgent")
        self.config = config
        self.database = database
        self.trading_client = alpaca_trading_client
        self.data_client = alpaca_data_client
        self.external_mcp_servers = external_mcp_servers or {}

        # Initialize components
        logger.debug("Initializing strategy manager")
        self.strategy_manager = AutonomousStrategyManager(
            database=database,
            initial_params=config.get("strategy", {})
        )

        logger.debug("Initializing meta-learning system")
        self.meta_learning = MetaLearningSystem(
            database=database,
            strategy_manager=self.strategy_manager
        )

        logger.debug("Initializing trading hooks")
        self.hooks = TradingHooks(
            strategy_manager=self.strategy_manager,
            database=database
        )

        # Create MCP server with all tools
        total_tools = len(alpaca_tools) + len(portfolio_tools) + len(backtest_tools)
        logger.debug("Creating MCP server with %d tools", total_tools)
        self.mcp_server = create_sdk_mcp_server(
            name="trading",
            version="1.0.0",
            tools=alpaca_tools + portfolio_tools + backtest_tools
        )

        # User sessions for Slack
        self.user_sessions: Dict[str, ClaudeSDKClient] = {}

        # Agent state
        self.is_running = False
        self.mode = config.get("mode", "PAPER_TRADING")
        self._background_tasks: list = []  # Track background tasks for cancellation
        self.slack_bot = None  # Will be set externally if Slack is configured
        logger.info("TradingAgent initialized (mode=%s)", self.mode)

    def _build_system_prompt(self) -> str:
        """
        Build dynamic system prompt with current state

        Returns:
            System prompt string
        """
        base_prompt = """
You are an autonomous trading agent with full control over your trading strategies and learning process.

YOUR PRIMARY GOAL: Maximize total account value while managing risk appropriately.

CURRENT MODE: {mode}

{strategy_context}

CAPABILITIES:
- Analyze market data and identify trading opportunities
- Execute trades with confidence scoring
- Create and evolve trading strategies
- Adjust your own risk parameters based on performance
- Learn from outcomes and optimize your decision-making
- Run backtests to validate strategies
- Manage portfolio positions and risk

MARKET DATA TOOLS (via TAM MCP Server):
- alphaVantage_getCompanyOverview - Get company fundamentals and overview
- alphaVantage_searchSymbols - Search for stock symbols
- get_latest_quote - Get current prices (from Alpaca)
- get_portfolio - View your current portfolio
- fred_getSeriesObservations - Economic indicators
- market_forecasting - Market trend predictions

TRADING WORKFLOW:
1. Analyze market conditions using TAM tools (alphaVantage_getCompanyOverview, get_latest_quote)
2. Identify opportunities based on your strategies
3. Assess risk/reward and determine confidence
4. Execute trades using execute_trade (with confidence score)
   - High confidence (>= threshold): Auto-executes
   - Lower confidence: Requests user confirmation
5. Monitor positions and adjust as needed
6. Learn from outcomes using store_feedback

AUTONOMOUS EVOLUTION:
- You can adjust your confidence thresholds using update_strategy_parameters
- Create new strategies when you identify patterns
- Retire underperforming strategies
- Modify learning aggressiveness based on results

DECISION MAKING:
- Always provide clear reasoning for your decisions
- Be conservative initially, build confidence through good performance
- Adapt to changing market conditions
- Consider risk management in every trade
- Learn from both wins and losses

Remember: You have autonomy, but transparency is key. Explain your thinking.
"""

        strategy_context = self.strategy_manager.get_system_prompt_context()

        return base_prompt.format(
            mode=self.mode,
            strategy_context=strategy_context
        )

    def _create_agent_options(self) -> ClaudeAgentOptions:
        """
        Create ClaudeAgentOptions with all configurations

        Returns:
            ClaudeAgentOptions instance
        """
        # Get Claude config
        claude_config = self.config.get("claude", {})

        # Build MCP servers dict (internal + external)
        mcp_servers = {"trading": self.mcp_server}

        # Add external MCP servers
        if self.external_mcp_servers:
            logger.info("Configuring %d external MCP server(s)", len(self.external_mcp_servers))
            for name, server_config in self.external_mcp_servers.items():
                mcp_servers[name] = server_config
                logger.info("Added external MCP server: %s", name)

        # Build allowed tools list
        allowed_tools = [
            # Alpaca tools
            "mcp__trading__get_market_data",
            "mcp__trading__get_latest_quote",
            "mcp__trading__execute_trade",
            "mcp__trading__get_portfolio",
            "mcp__trading__get_account_activity",
            "mcp__trading__cancel_order",
            # Portfolio tools
            "mcp__trading__analyze_performance",
            "mcp__trading__store_feedback",
            "mcp__trading__get_strategy_performance",
            "mcp__trading__update_strategy_parameters",
            "mcp__trading__get_current_parameters",
            # Backtest tools
            "mcp__trading__run_backtest",
            "mcp__trading__get_backtest_results",
            "mcp__trading__list_recent_backtests",
            "mcp__trading__compare_backtests"
        ]

        # Add external MCP server tools (using wildcard for all tools)
        for server_name in self.external_mcp_servers.keys():
            allowed_tools.append(f"mcp__{server_name}__*")
            logger.info("Allowed all tools from MCP server: %s", server_name)

        # Create hooks config
        hooks_config = self.hooks.create_hook_config()
        logger.info("Creating ClaudeAgentOptions with hooks: %s", list(hooks_config.keys()))

        options = ClaudeAgentOptions(
            # MCP servers (internal + external)
            mcp_servers=mcp_servers,

            # Allowed tools
            allowed_tools=allowed_tools,

            # Dynamic system prompt
            system_prompt=self._build_system_prompt(),

            # Hooks for trade confirmation
            hooks=hooks_config,

            # Claude model config
            model=claude_config.get("model", "claude-sonnet-4-5"),
            max_turns=claude_config.get("max_turns", 50),

            # Use default permission mode (enables hooks)
            # Options: acceptEdits, bypassPermissions, default, plan
            permission_mode="default"
        )

        logger.info("ClaudeAgentOptions created with permission_mode=%s", "default")
        return options

    async def generate_daily_report(self) -> str:
        """
        Generate comprehensive daily report

        Returns:
            Report text
        """
        logger.info("Generating daily report")
        options = self._create_agent_options()

        try:
            async with ClaudeSDKClient(options=options) as client:
                report_prompt = """
IMPORTANT: Output ONLY the report itself. Do not include any preamble, explanation, or commentary.
Start directly with the markdown report.

Generate a comprehensive daily trading report formatted for Slack.

Use markdown headers (# for main title, ## for sections) and structure the report as follows:

# 📊 DAILY TRADING REPORT

## 1. PORTFOLIO STATUS
Use get_portfolio to retrieve:
• Total portfolio value and cash balance
• Active positions with current P&L
• Today's total P&L (percentage and dollar amount)
• Portfolio allocation breakdown

Format as bullet points, use clear numbers.

## 2. MARKET ANALYSIS
Use get_market_data for major indices (SPY, QQQ, DIA):
• Current market sentiment (bullish/bearish/neutral)
• Major index performance today
• Sector rotation trends
• Volatility levels (VIX if available)
• Key support/resistance levels

Note: If get_market_data fails, try alternative data sources or note data limitations.

## 3. RECENT PERFORMANCE
Use analyze_performance for last 7 days:
• Number of trades executed
• Win rate and average P/L per trade
• Best performing strategy
• Worst performing strategy
• Confidence score accuracy

## 4. ACTIVE STRATEGIES
Use get_current_parameters:
• List active strategies and their status
• Current confidence threshold
• Risk parameters (max position size, daily loss limit)
• Any recent parameter adjustments

## 5. OPPORTUNITIES & RECOMMENDATIONS
Based on analysis:
• Top 2-3 trading opportunities (with symbols and setups)
• Risk assessment for today
• Suggested parameter adjustments
• Market conditions to watch

Keep each section concise (3-5 bullet points max). Use emojis sparingly.
If any tool fails, note the limitation and continue with available data.
                """

                await client.query(report_prompt)

                report = ""
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                report += block.text

                # Clean up report - remove any preamble before the actual report
                # The report should start with "# 📊 DAILY TRADING REPORT" or similar
                if '#' in report:
                    # Find first markdown header and start from there
                    first_header = report.find('#')
                    if first_header > 0:
                        report = report[first_header:]

                logger.info("Daily report generated successfully, length=%d chars", len(report))
                return report
        except Exception as e:
            logger.error("Error generating daily report: %s", e, exc_info=True)
            raise

    async def trading_loop(self) -> None:
        """
        Main trading loop - continuously monitor and trade

        This runs in the background and makes autonomous trading decisions
        """
        logger.info("Starting autonomous trading loop")
        options = self._create_agent_options()

        try:
            async with ClaudeSDKClient(options=options) as client:
                # Initial portfolio check
                await client.query("""
You are now in continuous trading mode. Your task:

1. Monitor markets using get_market_data for interesting symbols
2. Analyze opportunities based on your strategies
3. When you find good setups, use execute_trade with appropriate confidence
4. Track your open positions with get_portfolio
5. Manage risk appropriately

This is a long-running session. Check markets periodically,
make decisions when you see opportunities, and always explain your reasoning.

Start by getting current portfolio status and market overview.
                """)

                # Process initial response
                response_text = ""
                async for message in client.receive_response():
                    if not self.is_running:
                        break
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                response_text += block.text

                if response_text:
                    logger.info("Initial market analysis: %s", response_text[:200])

                # Continuous monitoring loop
                # Increased from 5 min to 30 min to avoid API rate limits
                check_interval = self.config.get("trading", {}).get("check_interval_seconds", 1800)  # 30 min default

                while self.is_running:
                    await asyncio.sleep(check_interval)

                    if not self.is_running:
                        break

                    # Check if during market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
                    from datetime import datetime
                    import pytz

                    et_tz = pytz.timezone('US/Eastern')
                    now_et = datetime.now(et_tz)

                    # Skip if weekend
                    if now_et.weekday() >= 5:  # Saturday = 5, Sunday = 6
                        logger.info("Skipping market check (weekend)")
                        continue

                    # Skip if outside market hours (9:30 AM - 4:00 PM ET)
                    market_open = now_et.replace(hour=9, minute=30, second=0)
                    market_close = now_et.replace(hour=16, minute=0, second=0)

                    if now_et < market_open or now_et > market_close:
                        logger.info("Skipping market check (outside market hours: %s ET)", now_et.strftime("%H:%M"))
                        continue

                    # Periodic market check (only during market hours)
                    logger.info("Performing periodic market check (%s ET)", now_et.strftime("%H:%M"))
                    await client.query("""
Check current market conditions and your portfolio:

1. Use get_portfolio to see current positions
2. Use get_latest_quote to check prices for SPY, QQQ, and any positions you hold
3. If you find a good opportunity with high confidence, execute a trade
4. Otherwise, just report your findings in 2-3 sentences

Be VERY concise - just key findings. Remember: Use TAM tools (alphaVantage) for analysis if needed.
                    """)

                    # Process response and log findings
                    response_text = ""
                    async for message in client.receive_response():
                        if not self.is_running:
                            break
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, TextBlock):
                                    response_text += block.text

                    if response_text:
                        logger.info("Market check: %s", response_text[:300])

        except asyncio.CancelledError:
            logger.debug("Trading loop cancelled, cleaning up")
            await asyncio.sleep(0.1)
            raise
        finally:
            logger.debug("Trading loop exiting")

    async def handle_user_query(self, query: str, user_id: str = "default") -> str:
        """
        Handle a user query in conversational mode

        Args:
            query: User's question or command
            user_id: User identifier (for maintaining context)

        Returns:
            Agent's response
        """
        logger.info("Handling user query from user_id=%s: %s", user_id, query[:100])

        # Get or create user session
        if user_id not in self.user_sessions:
            logger.debug("Creating new session for user_id=%s", user_id)
            options = self._create_agent_options()
            self.user_sessions[user_id] = ClaudeSDKClient(options=options)
            await self.user_sessions[user_id].connect()

        client = self.user_sessions[user_id]

        # Send query
        await client.query(query)

        # Collect response
        response = ""
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response += block.text

        logger.info("Query handled, response length=%d chars", len(response))
        return response

    async def run_evolution_cycle(self) -> None:
        """
        Run meta-learning evolution cycle

        Should be called periodically (e.g., weekly)
        """
        logger.info("Starting evolution cycle")
        print("\n" + "="*60)
        print("EVOLUTION CYCLE STARTING")
        print("="*60 + "\n")

        options = self._create_agent_options()

        async with ClaudeSDKClient(options=options) as client:
            await self.meta_learning.analyze_and_evolve(client)

        logger.info("Evolution cycle complete")
        print("\n" + "="*60)
        print("EVOLUTION CYCLE COMPLETE")
        print("="*60 + "\n")

    def start_background(self) -> None:
        """
        Start the trading agent in the background (non-blocking)

        Use this when starting from Slack commands or other contexts
        where you don't want to block.
        """
        if self.is_running:
            logger.warning("Agent already running, ignoring start request")
            print("Agent already running")
            return

        self.is_running = True
        logger.info("Trading agent starting in background (mode=%s)", self.mode)
        print(f"\n🤖 Trading Agent Starting [{self.mode}]")
        print("="*60)

        # Create background tasks
        self._background_tasks = [
            asyncio.create_task(self._trading_task()),
            asyncio.create_task(self._scheduled_tasks())
        ]

        logger.info("Background tasks created: %d tasks", len(self._background_tasks))

    async def start(self) -> None:
        """
        Start the trading agent and wait for completion

        Runs multiple concurrent tasks:
        - Trading loop (continuous monitoring)
        - Scheduled reports
        - Periodic evolution

        This method blocks until the agent is stopped. Use start_background()
        for non-blocking start from Slack commands.
        """
        if self.is_running:
            logger.warning("Agent already running, ignoring start request")
            print("Agent already running")
            return

        self.is_running = True
        logger.info("Trading agent starting (mode=%s)", self.mode)
        print(f"\n🤖 Trading Agent Starting [{self.mode}]")
        print("="*60)

        # Create background tasks
        self._background_tasks = [
            asyncio.create_task(self._trading_task()),
            asyncio.create_task(self._scheduled_tasks())
        ]

        logger.info("Starting concurrent tasks: trading loop and scheduled tasks")

        # Wait for tasks (this will run until stopped or KeyboardInterrupt)
        try:
            await asyncio.gather(*self._background_tasks)
        except asyncio.CancelledError:
            logger.info("Background tasks cancelled")
            pass

    async def _trading_task(self) -> None:
        """Continuous trading loop"""
        # Check if autonomous mode is enabled
        autonomous_mode = self.config.get("trading", {}).get("autonomous_mode", True)

        if not autonomous_mode:
            logger.info("Autonomous trading mode disabled - agent will only respond to Slack commands")
            # Just wait and do nothing
            while self.is_running:
                await asyncio.sleep(60)
            return

        logger.info("Trading task started (autonomous mode enabled)")
        try:
            while self.is_running:
                try:
                    await self.trading_loop()
                except asyncio.CancelledError:
                    logger.info("Trading task cancelled")
                    raise
                except Exception as e:
                    logger.error("Error in trading loop: %s", e, exc_info=True)
                    print(f"Error in trading loop: {e}")
                    await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Trading task stopping")
            pass

    async def _scheduled_tasks(self) -> None:
        """Run scheduled tasks (reports, evolution)"""
        logger.info("Scheduled tasks started")
        try:
            while self.is_running:
                now = datetime.now()

                # Daily report (configured time, e.g., 9 AM KST)
                report_time = self.config.get("slack", {}).get("daily_report_time", "09:00")
                report_hour, report_min = map(int, report_time.split(":"))

                if now.hour == report_hour and now.minute == report_min:
                    logger.info("Triggering scheduled daily report")
                    try:
                        report = await self.generate_daily_report()
                        print(f"\n📊 DAILY REPORT:\n{report}\n")

                        # Send to Slack if available
                        if hasattr(self, 'slack_bot') and self.slack_bot:
                            try:
                                await self.slack_bot.send_alert({
                                    "type": "daily_report",
                                    "report": report
                                })
                                logger.info("Daily report sent to Slack")
                            except Exception as slack_err:
                                logger.warning("Failed to send report to Slack: %s", slack_err)

                    except Exception as e:
                        logger.error("Error generating daily report: %s", e, exc_info=True)
                        print(f"Error generating daily report: {e}")

                # Weekly evolution (every Friday at midnight)
                if now.weekday() == 4 and now.hour == 0 and now.minute == 0:  # Friday
                    logger.info("Triggering scheduled evolution cycle (Friday)")
                    try:
                        await self.run_evolution_cycle()
                    except Exception as e:
                        logger.error("Error in evolution cycle: %s", e, exc_info=True)
                        print(f"Error in evolution cycle: {e}")

                # Sleep for a minute
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Scheduled tasks stopping")
            pass

    async def stop(self) -> None:
        """Stop the trading agent"""
        logger.info("Stopping trading agent")
        self.is_running = False
        print("\n🛑 Trading Agent Stopping")

        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete cancellation (with exceptions suppressed)
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Give more time for HTTP sessions to close properly
        await asyncio.sleep(0.5)

        self._background_tasks = []
        logger.info("All background tasks stopped")

        # Close user sessions gracefully
        for user_id, client in list(self.user_sessions.items()):
            try:
                await client.disconnect()
                logger.debug("Closed session for user %s", user_id)
            except Exception as e:
                logger.warning("Error closing session for user %s: %s", user_id, e)

        self.user_sessions.clear()
        logger.info("All sessions closed")

        # Final cleanup delay for any remaining resources
        await asyncio.sleep(0.2)
        print("Trading Agent Stopped")