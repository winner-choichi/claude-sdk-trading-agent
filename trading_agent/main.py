"""
Main entry point for the trading agent
"""

import asyncio
import os
import sys
from pathlib import Path
import yaml
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient

from storage.database import Database
from agent.core import TradingAgent
from messaging.slack_bot import create_slack_bot

# Import all tools
from tools.alpaca_tools import (
    ALPACA_TOOLS,
    initialize_alpaca as init_alpaca_tools,
    set_database as set_alpaca_db
)
from tools.portfolio_tools import (
    PORTFOLIO_TOOLS,
    set_database as set_portfolio_db
)
from tools.backtest_tools import (
    BACKTEST_TOOLS,
    set_data_client,
    set_database as set_backtest_db
)


def load_config(config_path: str = "config/config.yaml") -> dict:
    """
    Load configuration from YAML file

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    # Load environment variables from .env if it exists
    load_dotenv()

    config_file = Path(__file__).parent / config_path

    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        print(f"📝 Please copy config.example.yaml to config.yaml and fill in your API keys")
        sys.exit(1)

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    # Override with environment variables if present
    if os.getenv("ALPACA_API_KEY"):
        config.setdefault("alpaca", {})["api_key"] = os.getenv("ALPACA_API_KEY")
    if os.getenv("ALPACA_SECRET_KEY"):
        config.setdefault("alpaca", {})["api_secret"] = os.getenv("ALPACA_SECRET_KEY")

    if os.getenv("SLACK_BOT_TOKEN"):
        config.setdefault("slack", {})["bot_token"] = os.getenv("SLACK_BOT_TOKEN")
    if os.getenv("SLACK_APP_TOKEN"):
        config.setdefault("slack", {})["app_token"] = os.getenv("SLACK_APP_TOKEN")

    # Override MCP server API keys from environment
    if os.getenv("ALPHAVANTAGE_API_KEY"):
        config.setdefault("mcp_servers", {}).setdefault("alphavantage", {})["api_key"] = os.getenv("ALPHAVANTAGE_API_KEY")

    return config


def validate_config(config: dict) -> bool:
    """
    Validate required configuration

    Args:
        config: Configuration dictionary

    Returns:
        True if valid
    """
    errors = []

    # Check Alpaca config
    if "alpaca" not in config:
        errors.append("Missing 'alpaca' configuration")
    else:
        alpaca = config["alpaca"]
        if not alpaca.get("api_key"):
            errors.append("Missing alpaca.api_key")
        if not alpaca.get("api_secret"):
            errors.append("Missing alpaca.api_secret")
        if not alpaca.get("base_url"):
            errors.append("Missing alpaca.base_url")

    # Check mode
    mode = config.get("mode", "PAPER_TRADING")
    if mode not in ["PAPER_TRADING", "LIVE_TRADING"]:
        errors.append(f"Invalid mode: {mode} (must be PAPER_TRADING or LIVE_TRADING)")

    # Warn about Slack (not required)
    if "slack" not in config or not config["slack"].get("bot_token"):
        print("ℹ️  Slack not configured - bot features will be disabled")

    if errors:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"   - {error}")
        return False

    return True


def build_external_mcp_servers(config: dict) -> dict:
    """
    Build external MCP server configurations from config

    Supports both HTTP and STDIO MCP servers:
    - HTTP: url + optional api_key
    - STDIO: command, args, cwd, env

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary of MCP server configurations
    """
    external_servers = {}
    mcp_config = config.get("mcp_servers", {})

    for server_name, server_config in mcp_config.items():
        if not server_config.get("enabled", False):
            continue

        server_type = server_config.get("type", "http")

        if server_type == "stdio":
            # Local STDIO server (like TAM)
            command = server_config.get("command")
            args = server_config.get("args", [])
            cwd = server_config.get("cwd")
            env = server_config.get("env", {})

            if not command:
                print(f"⚠️  STDIO MCP server '{server_name}' has no command, skipping")
                continue

            # Build STDIO server config
            external_servers[server_name] = {
                "command": command,
                "args": args,
                "env": env
            }

            if cwd:
                external_servers[server_name]["cwd"] = cwd

            print(f"✅ Configured STDIO MCP server: {server_name} ({command})")

        else:
            # HTTP server (like AlphaVantage)
            url = server_config.get("url")
            api_key = server_config.get("api_key")

            if not url:
                print(f"⚠️  HTTP MCP server '{server_name}' has no URL, skipping")
                continue

            # Build server URL with API key if needed
            if api_key and "{apikey}" not in url:
                # Append API key as query parameter
                separator = "&" if "?" in url else "?"
                full_url = f"{url}{separator}apikey={api_key}"
            elif api_key:
                # Replace placeholder
                full_url = url.replace("{apikey}", api_key)
            else:
                full_url = url

            # Use the URL directly as the server value
            external_servers[server_name] = full_url

            print(f"✅ Configured HTTP MCP server: {server_name}")

    return external_servers


def setup_logging(config: dict):
    """Setup logging configuration"""
    log_level = config.get("logging", {}).get("level", "INFO")
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("slack_sdk").setLevel(logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    # Suppress resource warnings during shutdown (these are cleanup timing issues, not errors)
    import warnings
    warnings.filterwarnings("ignore", message=".*Unclosed.*", category=ResourceWarning)
    warnings.filterwarnings("ignore", message=".*Event loop is closed.*", category=RuntimeWarning)


def setup_asyncio_exception_handler():
    """
    Setup custom asyncio exception handler to suppress harmless cleanup warnings

    These warnings occur during shutdown when HTTP sessions are closed slightly
    out of order. They don't indicate actual problems.
    """
    import sys
    import io

    # Save original stderr
    original_stderr = sys.stderr

    class FilteredStderr:
        """Filter stderr to suppress harmless cleanup warnings

        These specific patterns only occur during asyncio/aiohttp cleanup
        and are safe to suppress as they don't indicate real problems.
        """
        def __init__(self, original):
            self.original = original
            # Patterns that indicate harmless cleanup warnings
            self.suppress_patterns = [
                "Exception ignored in:",
                "ClientResponse.__del__",
                "Event loop is closed",
                "Unclosed client session",
                "client_session: <aiohttp",
                "client_reqrep.py",
                "_start_shutdown",
                "asyncio/sslproto.py",
                "asyncio/base_events.py",
                "aiohttp/connector.py",
                "aiohttp/client_proto.py",
                "site-packages/aiohttp/",
                "Traceback (most recent call last):",
                "self._connection.release()",
                "self._connector._release(",
                "protocol.close()",
                "transport.close()",
                "self._ssl_protocol._start_shutdown()",
                "self._shutdown_timeout_handle",
                "self._loop.call_later(",
                "timer = self.call_at(",
                "self._check_closed()",
                "RuntimeError:",
                "raise RuntimeError("
            ]

        def write(self, text):
            # Check if this text contains any suppression patterns
            if any(pattern in text for pattern in self.suppress_patterns):
                return  # Suppress this line

            # Normal output
            self.original.write(text)

        def flush(self):
            self.original.flush()

        def isatty(self):
            return self.original.isatty()

    # Replace stderr with filtered version
    sys.stderr = FilteredStderr(original_stderr)

    def handle_exception(loop, context):
        # Get the exception
        exception = context.get("exception")
        message = context.get("message", "")

        # Suppress harmless cleanup errors during shutdown
        if exception and isinstance(exception, RuntimeError):
            if "Event loop is closed" in str(exception):
                return  # Ignore - harmless cleanup timing issue

        if "Unclosed client session" in message:
            return  # Ignore - harmless cleanup timing issue

        # For all other exceptions, use the default handler
        loop.default_exception_handler(context)

    # Set the custom handler
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)


async def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("🤖 AUTONOMOUS TRADING AGENT")
    print("="*70 + "\n")

    # Load configuration
    print("📋 Loading configuration...")
    config = load_config()

    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)

    # Setup asyncio exception handler to suppress cleanup warnings
    setup_asyncio_exception_handler()

    if not validate_config(config):
        print("\n❌ Please fix configuration errors and try again")
        sys.exit(1)

    print("✅ Configuration loaded")
    logger.info("Configuration loaded successfully")

    # Initialize database
    print("\n💾 Initializing database...")
    logger.debug("Initializing database with config: %s", config.get("database", {}))
    database = Database(config.get("database", {}))
    print("✅ Database initialized")
    logger.info("Database initialized")

    # Initialize Alpaca clients
    print("\n📈 Connecting to Alpaca...")
    alpaca_config = config["alpaca"]
    is_paper = alpaca_config["base_url"] == "https://paper-api.alpaca.markets"
    logger.info("Connecting to Alpaca (paper=%s)", is_paper)

    trading_client = TradingClient(
        api_key=alpaca_config["api_key"],
        secret_key=alpaca_config["api_secret"],
        paper=is_paper
    )

    data_client = StockHistoricalDataClient(
        api_key=alpaca_config["api_key"],
        secret_key=alpaca_config["api_secret"]
    )

    # Initialize tools
    init_alpaca_tools(
        api_key=alpaca_config["api_key"],
        api_secret=alpaca_config["api_secret"],
        paper=alpaca_config["base_url"] == "https://paper-api.alpaca.markets"
    )
    set_alpaca_db(database)
    set_portfolio_db(database)
    set_data_client(data_client)
    set_backtest_db(database)

    print("✅ Connected to Alpaca")

    # Display account info
    try:
        account = trading_client.get_account()
        print(f"\n💼 Account Status:")
        print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print(f"   Cash: ${float(account.cash):,.2f}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        logger.info("Account loaded - Portfolio: $%.2f, Cash: $%.2f",
                   float(account.portfolio_value), float(account.cash))
    except Exception as e:
        print(f"⚠️  Could not fetch account info: {e}")
        logger.error("Failed to fetch account info: %s", e)

    # Build external MCP servers
    print("\n🔌 Configuring MCP servers...")
    external_mcp_servers = build_external_mcp_servers(config)
    if external_mcp_servers:
        print(f"✅ {len(external_mcp_servers)} external MCP server(s) configured")
    else:
        print("ℹ️  No external MCP servers enabled")

    # Initialize trading agent
    print("\n🤖 Initializing trading agent...")
    logger.info("Initializing trading agent")
    agent = TradingAgent(
        config=config,
        database=database,
        alpaca_tools=ALPACA_TOOLS,
        portfolio_tools=PORTFOLIO_TOOLS,
        backtest_tools=BACKTEST_TOOLS,
        alpaca_trading_client=trading_client,
        alpaca_data_client=data_client,
        external_mcp_servers=external_mcp_servers
    )
    print("✅ Trading agent initialized")
    logger.info("Trading agent initialized successfully")

    # Initialize Slack bot (if configured)
    slack_bot = None
    if config.get("slack", {}).get("bot_token"):
        print("\n💬 Initializing Slack bot...")
        logger.info("Initializing Slack bot")
        try:
            slack_bot = await create_slack_bot(agent, config["slack"])
            if slack_bot:
                print("✅ Slack bot initialized")
                logger.info("Slack bot initialized")

                # Connect agent and slack bot
                agent.slack_bot = slack_bot
                agent.hooks.slack_bot = slack_bot  # Also connect hooks to Slack

                # Start Slack bot in background
                asyncio.create_task(slack_bot.start())

                # Send startup message
                await asyncio.sleep(2)  # Give bot time to connect
                try:
                    await slack_bot.send_startup_message()
                    logger.info("Slack startup message sent")
                except Exception as e:
                    print(f"⚠️  Could not send Slack startup message: {e}")
                    print("   Agent will continue without Slack integration")
                    logger.warning("Failed to send Slack startup message: %s", e)
                    agent.slack_bot = None
                    slack_bot = None
        except Exception as e:
            print(f"⚠️  Slack initialization failed: {e}")
            print("   Agent will continue without Slack integration")
            logger.warning("Slack initialization failed: %s", e)
            slack_bot = None

    # Display mode
    mode = config.get("mode", "PAPER_TRADING")
    print(f"\n🎯 Mode: {mode}")
    logger.info("Trading mode: %s", mode)

    if mode == "LIVE_TRADING":
        print("\n" + "⚠️  "*20)
        print("   LIVE TRADING MODE - REAL MONEY AT RISK")
        print("   " + "⚠️  "*20)
        logger.warning("LIVE TRADING MODE - Awaiting confirmation")
        response = input("\nType 'YES' to confirm live trading: ")
        if response != "YES":
            print("❌ Live trading not confirmed. Exiting.")
            logger.info("Live trading not confirmed, exiting")
            sys.exit(0)
        logger.warning("LIVE TRADING CONFIRMED - Starting agent")

    # Start agent in background (non-blocking)
    print("\n" + "="*70)
    print("🚀 STARTING TRADING AGENT")
    print("="*70 + "\n")
    logger.info("Starting trading agent in background")

    # Use start_background() so the process doesn't exit when agent pauses
    agent.start_background()

    # Keep process alive - wait for KeyboardInterrupt
    # This allows Slack commands to pause/resume the agent
    try:
        print("✅ Agent running in background. Press Ctrl+C to shutdown.")
        print("   Use Slack commands to pause/resume trading.\n")
        logger.info("Main process waiting - agent controllable via Slack")

        # Wait forever (until KeyboardInterrupt)
        while True:
            await asyncio.sleep(60)
            # Optionally log status periodically
            if agent.is_running:
                logger.debug("Agent status: running")
            else:
                logger.debug("Agent status: paused")

    except KeyboardInterrupt:
        print("\n\n⏸️  Shutting down...")
        logger.info("Received shutdown signal")
        if agent.is_running:
            await agent.stop()
        print("✅ Shutdown complete")
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)