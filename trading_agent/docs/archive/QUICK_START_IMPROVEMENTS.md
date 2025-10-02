# Quick Start: Trading Report Improvements

## ✅ What's Already Done

Your trading agent now has:

1. **Better Slack Formatting** - Reports render beautifully with proper headers, dividers, and structure
2. **Improved Report Structure** - Clear 5-section format with actionable insights
3. **AlphaVantage Integration Ready** - Code is ready to connect to AlphaVantage MCP server

## 🚀 How to Enable AlphaVantage Market Data

### Step 1: Get Free API Key (1 minute)

1. Go to: https://www.alphavantage.co/support/#api-key
2. Enter your email
3. Copy your API key (looks like: `ABC123XYZ456`)

### Step 2: Configure

**Option A: Environment Variable (Recommended)**
```bash
export ALPHAVANTAGE_API_KEY="your_actual_api_key_here"
```

**Option B: Config File**
```bash
# Edit config/config.yaml
cd trading_agent
nano config/config.yaml
```

Add or update:
```yaml
mcp_servers:
  alphavantage:
    enabled: true  # Change to true
    url: "https://mcp.alphavantage.co/mcp"
    api_key: "your_actual_api_key_here"  # Replace with your key
```

### Step 3: Restart Agent

```bash
cd trading_agent
python main.py
```

You should see:
```
🔌 Configuring MCP servers...
✅ Configured external MCP server: alphavantage
✅ 1 external MCP server(s) configured
```

### Step 4: Test

Generate a report in Slack:
```
/trading-report
```

Or from Python:
```python
# In your trading agent environment
agent.generate_daily_report()
```

## 📊 Expected Results

### Before
```
## 2. MARKET ANALYSIS
Data Limitations: Unable to access real-time market data
```

### After
```
━━━━━━━━━━━━━━━━━━━━
2. MARKET ANALYSIS

• Market Sentiment: Bullish (SPY +0.8%)
• S&P 500: $4,850.50 (+0.8%) - Above 50-day SMA
• Nasdaq: $17,200.30 (+1.2%) - Strong momentum
• Volatility: VIX at 14.2 (low)
• Key Level: SPY support at $4,820
```

## 🛠️ Troubleshooting

### "No external MCP servers enabled"
- Check that `enabled: true` in config.yaml
- Or set environment variable: `export ALPHAVANTAGE_API_KEY="..."`

### "API key not found"
- Verify your API key is correct
- Check: `echo $ALPHAVANTAGE_API_KEY`
- Make sure no quotes in environment variable

### Report still shows "Data Limitations"
- Check agent logs: `tail -f logs/trading_agent.log`
- Verify AlphaVantage is responding: `curl "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=SPY&apikey=YOUR_KEY"`
- You might have hit rate limit (25 calls/day on free tier)

### Rate Limit Errors
Free tier limits:
- 25 API calls per day
- 5 API calls per minute

**Solutions:**
- Wait until tomorrow
- Upgrade to premium ($50/month for 75 calls/min)
- Use daily reports only (not intraday)

## 📝 Files Modified

All improvements are already applied to:
- `trading_agent/messaging/slack_bot.py` - Better Slack formatting
- `trading_agent/agent/core.py` - Improved report structure + MCP integration
- `trading_agent/main.py` - External MCP server loader
- `trading_agent/config/config.example.yaml` - Config template

## 🎯 Next Steps

1. **Enable AlphaVantage** (follow steps above)
2. **Test the new report format** with `/trading-report`
3. **Monitor usage** - free tier is limited to 25 calls/day
4. **Consider premium** if you need more frequent updates

## 📚 Additional Resources

- Full details: `MARKET_DATA_SETUP.md`
- All improvements: `IMPROVEMENTS_SUMMARY.md`
- AlphaVantage docs: https://www.alphavantage.co/documentation/
- AlphaVantage MCP: https://mcp.alphavantage.co/

## ⚡ Pro Tips

1. **Cache market data** - Don't fetch SPY quote multiple times per report
2. **Use daily timeframes** - Intraday data costs more API calls
3. **Batch requests** - Get multiple symbols in one call when possible
4. **Monitor rate limits** - Track your usage to avoid hitting limits

## 🎉 That's It!

You're all set. The Slack formatting and report structure are already working.
Just add your AlphaVantage API key to get real market data!

Questions? Check the troubleshooting section or review the detailed docs.
