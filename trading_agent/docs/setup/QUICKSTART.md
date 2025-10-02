# Quick Start Guide 🚀

Get your autonomous trading agent running in 10 minutes!

## Step 1: Install Dependencies (2 min)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code
```

## Step 2: Get Alpaca API Keys (3 min)

1. Go to https://alpaca.markets
2. Sign up for a free account
3. Navigate to **Paper Trading** section
4. Generate API keys:
   - API Key ID
   - Secret Key

**Don't use real trading yet!** Paper trading is free and risk-free.

## Step 3: Configure the Agent (2 min)

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit with your API keys
nano config/config.yaml  # or use your preferred editor
```

**Minimum required config:**
```yaml
mode: PAPER_TRADING

alpaca:
  api_key: "YOUR_ALPACA_KEY"
  api_secret: "YOUR_ALPACA_SECRET"
  base_url: "https://paper-api.alpaca.markets"
```

**Leave Slack empty for now** - you can add it later.

## Step 4: Start the Agent (1 min)

```bash
python main.py
```

You should see:
```
🤖 AUTONOMOUS TRADING AGENT
====================================================================

📋 Loading configuration...
✅ Configuration loaded

💾 Initializing database...
✅ Database initialized

📈 Connecting to Alpaca...
✅ Connected to Alpaca

💼 Account Status:
   Portfolio Value: $100,000.00
   Cash: $100,000.00

🤖 Initializing trading agent...
✅ Trading agent initialized

🎯 Mode: PAPER_TRADING

====================================================================
🚀 STARTING TRADING AGENT
====================================================================
```

## Step 5: Test It Out (2 min)

The agent will start monitoring markets. Watch the console for activity!

### What the Agent Does Automatically:

1. **Analyzes markets** using get_market_data
2. **Identifies opportunities** based on its strategies
3. **Calculates confidence** for each trade
4. **Requests approval** (initially, confidence threshold is high)
5. **Learns from outcomes** and evolves

### Initial Behavior:

- **Very conservative** - confidence threshold starts at 95%
- **Most trades will request approval** via console
- **No Slack yet** - approvals happen in terminal

## What to Expect

### First Hour:
- Agent explores market data
- May identify a few opportunities
- Will ask for your approval (since threshold is high)
- Learning about market conditions

### First Day:
- More trade opportunities identified
- Begins building performance history
- Confidence calibration starts

### First Week:
- Evolution cycle runs (Friday)
- Parameters may adjust based on performance
- Strategies refine
- Confidence threshold may lower if performance is good

## Common First-Time Questions

### "Is it actually trading?"
Yes, but only on Alpaca's paper trading (simulated). No real money.

### "How do I approve trades?"
Without Slack, you'll see prompts in the console. With Slack, you get interactive buttons.

### "Can I speed up the learning?"
Edit config.yaml:
```yaml
strategy:
  initial_confidence_threshold: 0.85  # Lower = more aggressive
  learning_rate: "aggressive"
```

### "How do I add Slack?"
Follow `config/slack_bot_setup.md` - takes about 10 minutes to set up.

### "What if I want to stop it?"
Press `Ctrl+C` in the terminal. The agent will shut down gracefully.

## Next Steps

### 1. Add Slack Control (Recommended)
Follow `config/slack_bot_setup.md` to enable:
- Remote monitoring and control
- Interactive trade approvals
- Daily reports
- Performance analysis

### 2. Run Your First Backtest
Once agent is running, test a strategy:
```
# In agent console or via Slack
/backtest AAPL 2023-01-01 2023-12-31
```

### 3. Monitor Performance
Check the database:
```bash
sqlite3 data/trading_agent.db
sqlite> SELECT * FROM trades ORDER BY executed_at DESC LIMIT 10;
```

### 4. Adjust Parameters
As you build trust, you can:
- Lower confidence threshold
- Increase position sizes
- Adjust learning rate
- Modify risk limits

### 5. Plan for Live Trading
**Only after weeks of successful paper trading:**
1. Verify consistent profitability
2. Test with small amounts first
3. Change config:
   ```yaml
   mode: LIVE_TRADING
   alpaca:
     base_url: "https://api.alpaca.markets"
   ```
4. Fund your Alpaca account
5. Start with minimal capital

## Troubleshooting

### "Config file not found"
Make sure you copied `config.example.yaml` to `config/config.yaml`

### "Invalid API keys"
Double-check you copied the keys correctly from Alpaca

### "Connection refused"
Check your internet connection and Alpaca API status

### "Database error"
Delete `data/trading_agent.db` to start fresh (loses history)

### "Agent not making trades"
This is normal! Initially it's very conservative. Give it time to learn.

## Tips for Success

1. **Start conservative** - Default settings are intentionally cautious
2. **Let it run for at least a week** - Learning takes time
3. **Monitor the evolution cycles** - Friday's evolution often shows insights
4. **Use paper trading extensively** - Minimum 30 days before live
5. **Review trade reasoning** - Agent explains its decisions
6. **Check confidence calibration** - High confidence trades should perform better
7. **Be patient** - AI learns from experience

## Support

- Check `README.md` for detailed documentation
- Review `TRADING_AGENT_PLAN.md` for architecture details
- See `IMPLEMENTATION_STATUS.md` for system status
- Slack setup: `config/slack_bot_setup.md`

---

**Happy Trading! Remember: Start with paper trading and be patient with the learning process.** 🤖📈