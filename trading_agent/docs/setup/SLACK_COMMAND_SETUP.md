# Slack Command Setup - New Commands

## Commands to Add

We added 2 new commands that need to be registered in your Slack app:

### 1. `/test-trade`
- **Command:** `/test-trade`
- **Request URL:** Your bot's URL (same as other commands)
- **Short Description:** `Test trade execution flow`
- **Usage Hint:** `SYMBOL ACTION QUANTITY (e.g., AAPL buy 1)`

### 2. `/check-orders`
- **Command:** `/check-orders`
- **Request URL:** Your bot's URL (same as other commands)
- **Short Description:** `Check recent orders and positions`
- **Usage Hint:** (leave empty)

---

## How to Register Commands in Slack

### Step 1: Go to Slack App Settings
1. Go to https://api.slack.com/apps
2. Click on your trading agent app
3. Click **"Slash Commands"** in left sidebar

### Step 2: Add `/test-trade` Command
1. Click **"Create New Command"**
2. Fill in:
   - **Command:** `/test-trade`
   - **Request URL:** `https://your-ngrok-url.ngrok.io/slack/events` (or your bot's URL)
   - **Short Description:** `Test trade execution flow`
   - **Usage Hint:** `SYMBOL ACTION QUANTITY`
3. Click **"Save"**

### Step 3: Add `/check-orders` Command
1. Click **"Create New Command"** again
2. Fill in:
   - **Command:** `/check-orders`
   - **Request URL:** `https://your-ngrok-url.ngrok.io/slack/events` (same URL)
   - **Short Description:** `Check recent orders and positions`
   - **Usage Hint:** (leave empty)
3. Click **"Save"**

### Step 4: Reinstall App (if needed)
If Slack asks you to reinstall the app:
1. Click **"Reinstall App"** button
2. Authorize the changes
3. Done!

---

## Quick Check - All Your Commands

After setup, you should have these commands available:

### Existing Commands (Already Working)
- `/trading-report` - Generate daily trading report
- `/portfolio` - Get portfolio status
- `/backtest` - Run historical backtest
- `/parameters` - View strategy parameters
- `/performance` - Analyze performance
- `/status` - Check agent status
- `/pause-trading` - Pause the agent
- `/resume-trading` - Resume trading
- `/evolve` - Trigger strategy evolution

### New Commands (Just Added)
- `/test-trade` - Test trade execution ⭐ NEW
- `/check-orders` - Check order status ⭐ NEW

---

## Alternative: Test Without Registering (Quick Method)

If you want to test RIGHT NOW without setting up Slack commands:

**Option A: Direct Message to Agent**
Just message your bot directly:
```
@trading-agent execute a test trade: buy 1 share of AAPL with confidence 0.50, strategy 'manual_test', reasoning 'testing the flow'
```

**Option B: Use Existing Command**
Use the `/portfolio` command and ask it to check orders:
```
/portfolio
```
Then follow up:
```
@trading-agent also check my recent account activity and any pending orders
```

---

## After You Register

Once commands are registered in Slack:

1. **Restart your agent** (if running):
   ```bash
   # Ctrl+C to stop
   python main.py
   ```

2. **Test in Slack:**
   ```
   /test-trade AAPL buy 1
   ```

3. **Expected Response:**
   ```
   🧪 Testing trade execution: BUY 1 AAPL

   🤔 Trade Confirmation Requested
   Symbol: AAPL
   Action: BUY
   Quantity: 1
   Confidence: 50.0%
   Strategy: manual_test

   Reasoning: Manual test trade via /test-trade Slack command

   Recent Performance:
     Win Rate: N/A
     Daily P&L: $0.00

   Approve this trade?
   ```

4. **Then check orders:**
   ```
   /check-orders
   ```

---

## Troubleshooting

### "Command not found"
- Command not registered in Slack app yet
- Go to https://api.slack.com/apps → Your App → Slash Commands → Add

### "Request failed"
- Agent not running (start with `python main.py`)
- Wrong Request URL (check your ngrok/server URL)

### "No response"
- Check agent logs: `logs/trading_agent.log`
- Verify bot token is correct in config.yaml
- Check network connectivity

---

## Do You Want to:

**Option 1: Register commands properly** (5 minutes)
- Follow steps above
- Test with `/test-trade`
- Professional setup

**Option 2: Test with direct messages** (right now)
- No setup needed
- Just message the bot
- Quick and dirty

Which would you prefer? I can walk you through either option! 🚀
