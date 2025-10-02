# Trading Agent Documentation

Complete documentation for the Autonomous Trading Agent.

---

## 📚 Quick Navigation

### Getting Started
- [**Quick Start Guide**](setup/QUICKSTART.md) - Get up and running in 5 minutes
- [**Setup Complete Guide**](setup/SETUP_COMPLETE.md) - Detailed installation instructions

### Core Features
- [**Approval Flow**](APPROVAL_FLOW.md) - How trade approval and confidence thresholds work

### Setup Guides
- [**Market Data Setup**](setup/MARKET_DATA_SETUP.md) - Configure market data sources
- [**TAM MCP Integration**](setup/TAM_MCP_SETUP.md) - Set up TAM MCP server
- [**TAM Integration Complete**](setup/TAM_INTEGRATION_COMPLETE.md) - Verify TAM setup
- [**Slack Commands**](setup/SLACK_COMMAND_SETUP.md) - Configure Slack slash commands
- [**Slack Bot Setup**](setup/slack_bot_setup.md) - Complete Slack integration guide

### Development
- [**Improvement Roadmap**](development/IMPROVEMENT_ROADMAP.md) - Future enhancements and strategy development
- [**Implementation Status**](development/IMPLEMENTATION_STATUS.md) - Current feature status
- [**Basic Testing Plan**](development/BASIC_TESTING_PLAN.md) - Testing strategy and checklist

### Historical / Archive
- [Bug fixes and debugging history](archive/) - Historical troubleshooting documentation

---

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   ```bash
   cp config/config.example.yaml config/config.yaml
   # Edit config.yaml with your API keys
   ```

3. **Run the agent:**
   ```bash
   python main.py
   ```

4. **Test in Slack:**
   ```
   /test-trade AAPL buy 1
   ```

---

## 📖 Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── APPROVAL_FLOW.md            # Trade approval system
├── setup/                      # Setup and installation guides
│   ├── QUICKSTART.md
│   ├── SETUP_COMPLETE.md
│   ├── MARKET_DATA_SETUP.md
│   ├── TAM_MCP_SETUP.md
│   ├── TAM_INTEGRATION_COMPLETE.md
│   ├── SLACK_COMMAND_SETUP.md
│   └── slack_bot_setup.md
├── development/                # Development roadmap and planning
│   ├── IMPROVEMENT_ROADMAP.md
│   ├── IMPLEMENTATION_STATUS.md
│   └── BASIC_TESTING_PLAN.md
└── archive/                    # Historical debugging docs
    ├── HOOK_FORMAT_FIX.md
    ├── MARKET_DATA_FIX_COMPLETE.md
    ├── RATE_LIMIT_FIX.md
    ├── THREE_ISSUES_FIXED.md
    ├── APPROVAL_FLOW_FIXED.md
    └── ...
```

---

## 🔧 Key Features

### ✅ Working Features

- **Autonomous Trading** - Agent monitors markets and executes trades
- **Confidence-Based Approval** - Low-confidence trades require human approval
- **Slack Integration** - Control and monitor via Slack commands
- **Multi-Source Data** - Alpaca + TAM MCP (AlphaVantage, FRED, World Bank)
- **Risk Management** - Daily loss limits, position sizing
- **Portfolio Tracking** - Real-time P&L and performance metrics
- **Meta-Learning** - Strategy parameters evolve based on performance

### 🎯 Trade Approval Flow

**Low Confidence (< 85%):**
1. Trade blocked
2. Approval request sent to Slack
3. User approves with `/test-trade SYMBOL ACTION QTY --force`

**High Confidence (≥ 85%):**
1. Trade executes automatically
2. No approval needed

**Commands:**
- `/test-trade AAPL buy 1` - Test trade (blocked if low confidence)
- `/test-trade AAPL buy 1 --force` - Force execute
- `/update-threshold 0.70` - Adjust approval threshold
- `/portfolio` - View positions
- `/parameters` - View strategy settings

---

## 🛠️ Common Tasks

### Adjust Auto-Trade Threshold

```bash
# Show current threshold
/update-threshold

# Set to 70% (more trades require approval)
/update-threshold 0.70

# Set to 90% (fewer trades require approval)
/update-threshold 0.90
```

### Test Approval Flow

```bash
# Low confidence - will be blocked
/test-trade AAPL buy 1

# Force execute - bypasses approval
/test-trade AAPL buy 1 --force
```

### Check System Status

```bash
/status              # Agent status
/portfolio           # Current positions
/check-orders        # Recent orders
/parameters          # Strategy settings
```

---

## 🐛 Troubleshooting

### Issue: Trade Not Executing

**Check:**
1. Confidence level vs threshold (`/parameters`)
2. Risk limits not exceeded
3. Sufficient buying power (`/portfolio`)

### Issue: Slack Commands Not Working

**Check:**
1. Commands registered in Slack app settings
2. Bot invited to channel
3. Agent running (`/status`)

### Issue: Market Data Errors

**Check:**
1. TAM MCP server running
2. AlphaVantage API key configured
3. Network connectivity

**See:** [Historical bug fixes](archive/) for detailed troubleshooting

---

## 📝 Next Steps

1. **Verify Setup** - Run through [QUICKSTART.md](setup/QUICKSTART.md)
2. **Test Approval Flow** - Follow [APPROVAL_FLOW.md](APPROVAL_FLOW.md)
3. **Review Roadmap** - See [IMPROVEMENT_ROADMAP.md](development/IMPROVEMENT_ROADMAP.md)
4. **Implement Strategies** - Build on the verified foundation

---

## 🤝 Contributing

When adding new features:
1. Update relevant documentation in `docs/`
2. Add tests to verify functionality
3. Update [IMPLEMENTATION_STATUS.md](development/IMPLEMENTATION_STATUS.md)

---

## 📚 Additional Resources

- [Claude Agent SDK Docs](https://docs.claude.com/en/docs/claude-code/sdk)
- [Alpaca API Docs](https://alpaca.markets/docs/)
- [Slack API Docs](https://api.slack.com/)
- [TAM MCP Server](https://github.com/TAMServer/tam-mcp)

---

**Last Updated:** October 2, 2025
