# Autonomous Trading Agent 🤖📈

A fully autonomous, self-evolving trading agent powered by Claude Code SDK. The agent manages its own trading strategies, risk parameters, and learning process - truly autonomous AI trading.

> **📚 [Complete Documentation](docs/README.md)** | [Quick Start](docs/setup/QUICKSTART.md) | [Approval Flow](docs/APPROVAL_FLOW.md) | [Roadmap](docs/development/IMPROVEMENT_ROADMAP.md)

## 🌟 Key Features

### 1. **Fully Autonomous Operation**
- No hardcoded strategies - agent creates and evolves its own approaches
- Self-manages risk parameters based on performance
- Adjusts confidence thresholds dynamically
- Learns how to learn (meta-learning)

### 2. **Dynamic Trade Confirmation**
- **High confidence + good performance** → Auto-executes immediately
- **Medium confidence** → Requests Slack approval
- **Low confidence or risk limits** → Blocks trade

### 3. **Backtesting System**
- Test strategies on historical data before deploying
- Walk-forward validation
- Performance metrics (Sharpe, drawdown, win rate)
- Slack-controlled via `/backtest` command

### 4. **Self-Evolution**
- Analyzes performance across short/medium/long timeframes
- Adjusts own learning rate and strategy parameters
- Calibrates confidence scoring
- Weekly evolution cycles

### 5. **Real-time Slack Control**
- Monitor trades and performance from anywhere
- Approve/reject trades interactively
- Run backtests and analyze performance
- Emergency stop button

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│         Slack Interface             │
│  (Commands, Alerts, Approvals)      │
└─────────────┬───────────────────────┘
              │
     ┌────────┴────────┐
     │                 │
┌────▼─────┐   ┌──────▼───────┐
│  Agent   │   │    Hooks     │
│  Core    │   │ (Confirmation)│
└────┬─────┘   └──────────────┘
     │
  ┌──┴──┐
  │     │
┌─▼──┐ ┌▼────────┐
│MCP │ │Evolution│
│Tools│ │ System  │
└────┘ └─────────┘
```

## 📦 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ (for Claude Code CLI)
- Alpaca account (free paper trading)
- Slack workspace (optional but recommended)

### Setup

1. **Clone the repository**
   ```bash
   cd trading_agent
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Claude Code CLI**
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

4. **Configure the agent**
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

   Edit `config/config.yaml` and add:
   - Alpaca API keys (get from alpaca.markets)
   - Slack tokens (optional, see setup guide)
   - Adjust safety limits and parameters

5. **Set up Slack bot** (optional)
   Follow the detailed guide: `config/slack_bot_setup.md`

## 🚀 Usage

### Start the Agent

```bash
python main.py
```

The agent will:
- Initialize database and connect to Alpaca
- Start monitoring markets
- Make autonomous trading decisions
- Send alerts via Slack (if configured)

### Slack Commands

Once running, control via Slack:

```
# Trading & Testing
/test-trade AAPL buy 1           # Test trade (requires approval)
/test-trade AAPL buy 1 --force   # Force execute (bypasses approval)
/update-threshold 0.70           # Update auto-trade threshold

# Monitoring
/portfolio                       # View positions and P&L
/check-orders                    # View recent orders
/status                          # Agent status
/parameters                      # View current parameters
/performance [timeframe]         # Analyze performance

# Analysis
/trading-report                  # Generate daily report
/backtest AAPL,MSFT 2023-01-01 2024-01-01  # Run backtest

# Control
/pause-trading                   # Emergency stop
/resume-trading                  # Resume operations
/evolve                          # Trigger evolution cycle
```

### Natural Language Queries

Mention the bot in Slack:
```
@Trading Agent what's the market looking like today?
@Trading Agent should I add more AAPL?
@Trading Agent analyze my recent performance
```

## 🔧 Configuration

### Trading Mode

```yaml
mode: PAPER_TRADING  # or LIVE_TRADING
```

**Always start with paper trading!**

### Safety Limits

```yaml
limits:
  max_trades_per_day: 100
  max_position_size_pct: 10.0  # Max % per position
  daily_loss_limit_pct: 2.0    # Stop if lose 2%
  max_portfolio_exposure_pct: 80.0
```

### Initial Strategy Parameters

```yaml
strategy:
  initial_confidence_threshold: 0.95  # Very conservative
  learning_rate: "moderate"
  optimization_target: "total_value"
```

The agent will evolve these over time!

## 📊 How It Works

### 1. Autonomous Strategy Creation

The agent isn't limited to pre-programmed strategies. It:
- Analyzes market conditions
- Identifies patterns and opportunities
- Creates strategies based on observations
- Tests them via backtesting
- Deploys successful ones
- Retires underperforming ones

### 2. Dynamic Risk Management

Position sizing adapts to:
- Trade confidence
- Recent performance
- Current portfolio exposure
- Market volatility

### 3. Meta-Learning

The agent learns **how to learn**:
- Analyzes confidence calibration
- Adjusts learning aggressiveness
- Optimizes strategy parameters
- Improves decision-making over time

### 4. Trade Approval Flow

```
Agent identifies opportunity
  ↓
Calculates confidence score
  ↓
Hooks intercept trade
  ↓
  ├─ Confidence >= threshold + good performance
  │    ↓
  │  Auto-execute ✅
  │
  └─ Confidence < threshold OR risk limits
       ↓
     Request approval via Slack 🔔
       ↓
     ├─ Approved → Execute
     └─ Rejected → Cancel
```

### 5. Evolution Cycle

**Weekly (automatic):**
1. Analyze short/medium/long-term performance
2. Check confidence calibration
3. Assess strategy effectiveness
4. Adjust parameters autonomously
5. Generate insights report

## 📈 Performance Monitoring

### Daily Reports (9 AM KST)

Automatic Slack report with:
- Portfolio status and P&L
- Market analysis
- Recent trade review
- Strategy performance
- Action suggestions
- Risk assessment

### Real-time Alerts

- Trade opportunities (with approve/reject)
- Trade executions
- Parameter adjustments
- Risk warnings
- System errors

## 🧪 Backtesting

Test strategies before deploying:

```
/backtest AAPL,MSFT,GOOGL 2023-01-01 2024-01-01
```

The agent will:
1. Simulate strategy on historical data
2. Calculate performance metrics
3. Generate equity curve
4. Report results to Slack

**Metrics calculated:**
- Total return %
- Sharpe ratio
- Maximum drawdown
- Win rate
- Profit factor
- Trade statistics

## 🔐 Security

### API Key Management

**Never commit API keys to git!**

```bash
# Add to .gitignore
config/config.yaml
.env
```

**Use environment variables in production:**
```bash
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
```

### Safety Features

1. **Paper trading default** - No real money at risk initially
2. **Confirmation required** - Trades need approval (initially)
3. **Loss limits** - Auto-stops at daily loss threshold
4. **Position limits** - Max size per position enforced
5. **Emergency stop** - `/pause-trading` command
6. **Full audit trail** - All decisions logged to database

## 📁 Project Structure

```
trading_agent/
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
├── config/
│   ├── config.yaml           # Your configuration
│   ├── config.example.yaml   # Template
│   └── slack_bot_setup.md   # Slack setup guide
├── agent/
│   ├── core.py               # Main trading agent
│   ├── autonomous_strategy.py # Strategy manager
│   ├── meta_learning.py      # Meta-learning system
│   └── backtest_engine.py    # Backtesting engine
├── tools/
│   ├── alpaca_tools.py       # Market data & trading
│   ├── portfolio_tools.py    # Portfolio analysis
│   └── backtest_tools.py     # Backtesting tools
├── storage/
│   ├── models.py             # Database models
│   └── database.py           # Database operations
├── messaging/
│   └── slack_bot.py          # Slack integration
└── hooks/
    └── trading_hooks.py      # Trade confirmation hooks
```

## 🐳 Docker Deployment

```bash
docker build -t trading-agent .
docker run -d \
  -e ALPACA_API_KEY=your_key \
  -e ALPACA_SECRET_KEY=your_secret \
  -e SLACK_BOT_TOKEN=your_token \
  -e SLACK_APP_TOKEN=your_token \
  --name trading-agent \
  trading-agent
```

## 🔍 Database

SQLite database stores:
- Trade history
- Strategy definitions
- Performance snapshots
- Backtest results
- Learning insights
- Parameter evolution

**Location:** `data/trading_agent.db`

**View data:**
```bash
sqlite3 data/trading_agent.db
sqlite> SELECT * FROM trades LIMIT 10;
```

## 📝 Logs

Logs are written to:
- Console (stdout)
- `logs/trading_agent.log` (if configured)

## 🤝 Contributing

This is a personal project, but ideas are welcome! The agent's autonomous nature means you can teach it new strategies simply by providing examples and feedback.

## ⚠️ Disclaimer

**IMPORTANT:** This software is for educational purposes only.

- Trading involves substantial risk of loss
- Past performance does not guarantee future results
- The agent makes autonomous decisions - monitor closely
- Start with paper trading and small amounts
- Never risk money you can't afford to lose
- The developers are not responsible for trading losses

**You are solely responsible for your trading decisions.**

## 🆘 Troubleshooting

### Agent not starting
- Check config.yaml is properly formatted
- Verify API keys are correct
- Ensure all dependencies are installed

### Slack bot not responding
- Verify Socket Mode is enabled
- Check bot tokens in config
- Review Slack setup guide
- Invite bot to channel: `/invite @Trading Agent`

### Trades not executing
- Check daily loss limit hasn't been hit
- Verify account has buying power
- Review hooks.log for blocks
- Check Alpaca API status

### Database errors
- Delete `data/trading_agent.db` to reset (loses history)
- Check disk space
- Verify write permissions

## 📚 Further Reading

- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code/overview)
- [Agent SDK Reference](https://docs.claude.com/en/api/agent-sdk/overview)
- [Alpaca API Docs](https://alpaca.markets/docs/)
- [Slack API Docs](https://api.slack.com/docs)

## 📜 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built with [Claude Code SDK](https://github.com/anthropics/claude-code)
- Trading via [Alpaca Markets](https://alpaca.markets/)
- Messaging via [Slack](https://slack.com/)

---

**Built with Claude Code SDK - Truly autonomous AI trading** 🤖✨