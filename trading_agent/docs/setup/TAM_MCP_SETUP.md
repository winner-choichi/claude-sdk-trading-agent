# TAM-MCP-Server Setup for AlphaVantage

This guide shows how to set up the TAM (Technical Analysis & Market Data) MCP Server for real market data access.

## What is TAM-MCP-Server?

A local MCP server that provides:
- AlphaVantage market data integration
- Technical analysis tools
- Stock quotes and market information
- Works as a localhost MCP server

## Installation

### 1. Install TAM-MCP-Server

```bash
# Navigate to your projects directory
cd ~/projects  # or wherever you keep projects

# Clone the repository
git clone https://github.com/gvaibhav/TAM-MCP-Server.git
cd TAM-MCP-Server

# Install dependencies
npm install
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your AlphaVantage API key
nano .env
```

Add your AlphaVantage API key:
```
ALPHA_VANTAGE_API_KEY=your_actual_key_here
```

### 3. Start the Server

```bash
# Start in HTTP mode
npm run start:http
```

The server will run on `http://localhost:3000` (or the port specified in your config).

## Configure Trading Agent

### Option 1: Using Claude Desktop Config (Recommended)

Add to `~/.claude/config.json`:

```json
{
  "mcpServers": {
    "tam": {
      "command": "node",
      "args": ["/full/path/to/TAM-MCP-Server/dist/index.js"],
      "env": {
        "ALPHA_VANTAGE_API_KEY": "your_key_here"
      }
    }
  }
}
```

### Option 2: Direct Connection (if SDK supports it later)

In your `trading_agent/config/config.yaml`:

```yaml
mcp_servers:
  tam:
    enabled: true
    type: "stdio"
    command: "node"
    args:
      - "/full/path/to/TAM-MCP-Server/dist/index.js"
    env:
      ALPHA_VANTAGE_API_KEY: "your_key_here"
```

## Available Tools

Once TAM-MCP-Server is running, you'll have access to:

### Stock Data
- `get_stock_quote` - Real-time stock quotes
- `get_stock_data` - Historical price data
- `get_company_overview` - Company information

### Technical Indicators
- `get_sma` - Simple Moving Average
- `get_ema` - Exponential Moving Average
- `get_rsi` - Relative Strength Index
- `get_macd` - MACD indicator
- `get_bbands` - Bollinger Bands

### Market Analysis
- `get_market_status` - Check if market is open
- `search_symbol` - Search for stock symbols
- `get_news_sentiment` - News with sentiment analysis

## Testing

### Test the MCP Server

```bash
# In the TAM-MCP-Server directory
npm test
```

### Test with Claude Desktop

1. Restart Claude Desktop (to reload config)
2. In a conversation, try: "Get me the current price of AAPL"
3. Claude should use the TAM MCP tools

### Test with Trading Agent

```bash
# In your trading agent
cd ~/toys/claudeAgentSDK/trading_agent
python main.py
```

Then generate a report:
```
/trading-report
```

## Troubleshooting

### Server won't start

**Error: "Cannot find module"**
```bash
# Rebuild the project
npm run build
```

**Error: "Port already in use"**
```bash
# Kill existing process
lsof -ti:3000 | xargs kill -9

# Or change port in .env
PORT=3001
```

### No API key error

Make sure your `.env` file has the API key:
```bash
cat .env | grep ALPHA_VANTAGE_API_KEY
```

Should output your key (not just the variable name).

### Rate limit errors

Free tier limits:
- 25 requests per day
- 5 requests per minute

**Solutions:**
- Space out your requests
- Cache market data
- Upgrade to premium AlphaVantage

## Integration Status

**Current Status:** The TAM-MCP-Server needs to be configured in Claude Desktop's config, as the trading agent SDK doesn't yet support stdio MCP servers in the runtime configuration.

**Workaround:**
1. Install TAM-MCP-Server locally
2. Configure in `~/.claude/config.json`
3. Use Claude Desktop to access market data
4. Manually provide market context to trading agent

**Future:** Once SDK supports stdio MCP servers or we create custom AlphaVantage tools, full integration will be possible.

## Alternative: Create Custom Tools

Instead of using TAM-MCP-Server, you could create custom AlphaVantage tools directly in your trading agent:

```python
# In trading_agent/tools/alphavantage_tools.py
import requests

def get_stock_quote(symbol: str, api_key: str):
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key
    }
    response = requests.get(url, params=params)
    return response.json()
```

This approach gives you full control and avoids MCP server complexity.

## Next Steps

Choose your approach:

1. **TAM-MCP-Server** (best for reusability)
   - Follow installation above
   - Configure in Claude Desktop
   - Use for multiple projects

2. **Custom Tools** (best for integration)
   - Create AlphaVantage tools in `tools/alphavantage_tools.py`
   - Register with trading agent MCP server
   - Full control over implementation

3. **Manual Context** (simplest for now)
   - Use external tools to check markets
   - Provide market context to agent in Slack
   - Agent makes decisions with your input

## Resources

- TAM-MCP-Server: https://github.com/gvaibhav/TAM-MCP-Server
- AlphaVantage API Docs: https://www.alphavantage.co/documentation/
- MCP Protocol: https://modelcontextprotocol.io/
