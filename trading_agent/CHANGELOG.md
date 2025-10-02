# Changelog

All notable changes to the Autonomous Trading Agent.

---

## [1.0.0] - 2025-10-02

### ✅ Completed - Approval Flow & Basic Plumbing

#### Added
- **Trade Approval Flow**
  - Confidence-based approval system
  - Low-confidence trades (< 85%) blocked and require approval
  - High-confidence trades (≥ 85%) auto-execute
  - Slack notifications for approval requests

- **Slack Commands**
  - `/test-trade SYMBOL ACTION QTY [--force]` - Test trade execution
  - `/update-threshold VALUE` - Adjust auto-trade threshold
  - `/check-orders` - View recent orders
  - Enhanced `/portfolio` with Slack formatting

- **Force Execute Flag**
  - `--force` or `-f` flag bypasses approval
  - Sets confidence to 95% for immediate execution

#### Fixed
- **Hook System**
  - Fixed tool name matching (local vs MCP-wrapped)
  - Changed from `"ask"` to `"deny"` for programmatic contexts
  - Added async Slack notification in hooks
  - Connected hooks to Slack bot for approval messages

- **Slack Formatting**
  - Created `slack_formatter.py` for markdown conversion
  - Fixed markdown tables displaying as raw text
  - Proper bold/header formatting for Slack

- **Market Data Access**
  - Switched from Alpaca to TAM MCP for market data
  - Bypassed subscription restrictions
  - 28 data tools available (AlphaVantage, FRED, World Bank)

- **Rate Limiting**
  - Reduced Claude API usage by 95.5%
  - Increased check interval: 5 min → 30 min
  - Added market hours check (9:30 AM - 4:00 PM ET, Mon-Fri)
  - Added `autonomous_mode` config toggle

#### Changed
- **Permission Mode**
  - Set to `"default"` (was `None`)
  - Enables hook-based permission system

- **Documentation**
  - Reorganized all docs into `docs/` directory
  - Created comprehensive documentation index
  - Separated setup, development, and archive docs
  - Updated README with current commands

#### Verified
- ✅ Trade execution to Alpaca works
- ✅ Approval flow blocks low-confidence trades
- ✅ Force execution bypasses approval
- ✅ Slack integration fully functional
- ✅ Risk controls operational
- ✅ Basic plumbing complete

---

## [0.9.0] - 2025-10-01

### Added - TAM MCP Integration

- **External MCP Server Support**
  - STDIO MCP server configuration
  - HTTP MCP server support
  - Environment variable handling

- **TAM MCP Tools** (28 tools)
  - AlphaVantage (quotes, fundamentals, indicators)
  - FRED economic data
  - World Bank indicators
  - Market forecasting

### Fixed
- **Market Data Subscription Limits**
  - Updated system prompts to use TAM tools
  - Guided agent to use `alphaVantage_getCompanyOverview`
  - Fixed working directory for STDIO servers

---

## [0.8.0] - 2025-09-30

### Initial Release

- **Core Trading Agent**
  - Autonomous strategy management
  - Meta-learning system
  - Backtesting engine

- **Alpaca Integration**
  - Paper trading support
  - Market data access
  - Order execution

- **Portfolio Management**
  - Position tracking
  - P&L calculation
  - Performance analytics

- **Slack Integration**
  - Command handlers
  - Alert system
  - Natural language queries

---

## Upcoming

See [IMPROVEMENT_ROADMAP.md](docs/development/IMPROVEMENT_ROADMAP.md) for planned features.

### Phase 1: Pattern Recognition
- Technical indicators (RSI, MACD, Bollinger Bands)
- Price patterns (support/resistance, breakouts)
- Volume analysis
- Correlation detection

### Phase 2: Market Context
- Economic indicators
- Sector rotation
- Market regime detection

### Phase 3: Strategy Development
- Multiple strategy types
- Strategy confidence scoring
- Portfolio allocation

---

## Version History

- **v1.0.0** - Approval flow complete, basic plumbing verified
- **v0.9.0** - TAM MCP integration, market data fixes
- **v0.8.0** - Initial release with core features

---

**Last Updated:** October 2, 2025
