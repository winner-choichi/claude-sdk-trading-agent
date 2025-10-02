# Market Data Setup Guide

This guide explains how to integrate AlphaVantage MCP server for better market data in your trading reports.

## Problem

The current trading report shows "Data Limitations: Unable to access real-time market data" because:
1. Alpaca free tier has limited market data access
2. SIP (Securities Information Processor) data requires subscription
3. Market analysis section fails without proper data sources

## Solution: AlphaVantage MCP Server

AlphaVantage provides a free MCP server with comprehensive market data including:
- Real-time and historical stock quotes
- Technical indicators (RSI, MACD, SMA, etc.)
- Market news and sentiment
- Economic indicators
- Options data
- Forex and cryptocurrency data

## Setup Instructions

### 1. Get AlphaVantage API Key

1. Visit https://www.alphavantage.co/support/#api-key
2. Sign up for a free API key (takes 1 minute)
3. Save your API key (example: `DEMO` for testing, but get a real one for production)

### 2. Update Configuration

Add the AlphaVantage MCP server configuration to your `config/config.yaml`:

```yaml
# Add this new section:
mcp_servers:
  alphavantage:
    url: "https://mcp.alphavantage.co/mcp"
    api_key: "YOUR_ALPHAVANTAGE_API_KEY"
    enabled: true
```

Or set as environment variable:
```bash
export ALPHAVANTAGE_API_KEY="your_key_here"
```

### 3. Available AlphaVantage Tools

Once integrated, your agent will have access to these additional tools:

**Core Stock APIs:**
- `TIME_SERIES_DAILY` - Daily stock prices
- `TIME_SERIES_INTRADAY` - Intraday prices (1min, 5min, 15min, 30min, 60min)
- `QUOTE_ENDPOINT` - Real-time quote
- `GLOBAL_QUOTE` - Current price and stats

**Technical Indicators:**
- `RSI` - Relative Strength Index
- `MACD` - Moving Average Convergence Divergence
- `SMA` / `EMA` - Simple/Exponential Moving Averages
- `BBANDS` - Bollinger Bands
- `STOCH` - Stochastic Oscillator
- And 50+ more indicators

**Fundamental Data:**
- `OVERVIEW` - Company information
- `EARNINGS` - Earnings data
- `INCOME_STATEMENT` - Financial statements
- `BALANCE_SHEET` - Balance sheet data

**Market Intelligence:**
- `NEWS_SENTIMENT` - News with AI sentiment analysis
- `MARKET_STATUS` - Market open/close status
- `SYMBOL_SEARCH` - Search for ticker symbols

**Economic Data:**
- `REAL_GDP` - GDP data
- `INFLATION` - Inflation rates
- `UNEMPLOYMENT` - Employment data

### 4. Code Integration

The trading agent will automatically detect and use AlphaVantage tools once configured. The report generation has been updated to:

1. Try AlphaVantage first for market data
2. Fall back to Alpaca if AlphaVantage is unavailable
3. Gracefully handle failures and note limitations

### 5. Testing

Test the integration by running:

```bash
# Generate a trading report
cd trading_agent
python -c "
import asyncio
from main import main, load_config
from agent.core import TradingAgent

async def test():
    config = load_config()
    # ... initialize agent ...
    report = await agent.generate_daily_report()
    print(report)

asyncio.run(test())
"
```

Or use Slack command: `/trading-report`

### 6. Rate Limits

**Free Tier:**
- 25 API calls per day
- 5 API calls per minute

**Optimization Tips:**
- Cache market data for multiple report sections
- Use daily reports rather than frequent intraday calls
- Consider upgrading to premium if you need more calls ($50/month for 75/min)

## Updated Report Format

With AlphaVantage integration, your reports will now show:

```
## 2. MARKET ANALYSIS
• Market Sentiment: Bullish (SPY +0.8%, QQQ +1.2%)
• S&P 500: $4,850.50 (+0.8%) - Above 50-day SMA
• Nasdaq: $17,200.30 (+1.2%) - Strong momentum
• Volatility: VIX at 14.2 (low) - Complacent market
• Key Level: SPY support at $4,820, resistance at $4,870
```

Instead of:
```
## 2. MARKET ANALYSIS
Data Limitations: Unable to access real-time market data
```

## Alternative: Financial Datasets MCP

If you prefer fundamental data, consider the Financial Datasets MCP server:

```yaml
mcp_servers:
  financial_datasets:
    url: "https://api.financialdatasets.ai/mcp"
    api_key: "YOUR_FD_API_KEY"
    enabled: true
```

Provides:
- Income statements
- Balance sheets
- Cash flow statements
- Detailed financial metrics

## Next Steps

1. Get your free AlphaVantage API key
2. Update `config/config.yaml` with the MCP server configuration
3. Restart your trading agent
4. Generate a new report with `/trading-report`
5. Enjoy comprehensive market analysis!

## Troubleshooting

**"API key not found" error:**
- Verify your API key is correct in config.yaml
- Check environment variable: `echo $ALPHAVANTAGE_API_KEY`

**"Rate limit exceeded" error:**
- You've hit the 25 calls/day limit
- Wait until tomorrow or upgrade to premium
- Consider caching data

**"No market data" in report:**
- Check if AlphaVantage MCP server is enabled
- Verify your API key is valid
- Check network connectivity
- Look at agent logs for detailed errors

## Support

- AlphaVantage Docs: https://www.alphavantage.co/documentation/
- AlphaVantage MCP: https://mcp.alphavantage.co/
- Issues: Check trading agent logs in `logs/trading_agent.log`
