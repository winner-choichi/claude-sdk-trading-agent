# Approval Flow - COMPLETE ✅

## What's Working Now

**The approval flow is fully functional!** Low-confidence trades are blocked and require manual approval.

### Test Results

✅ Trade blocked when confidence (50%) < threshold (85%)
✅ Approval request sent to Slack with trade details
✅ Claude explains why trade was blocked
✅ User can approve via `--force` flag

---

## How The Approval Flow Works

### 1. Low Confidence Trade (< 85%)

**User runs:**
```
/test-trade AAPL buy 1
```

**What happens:**
1. Agent prepares trade with confidence 50%
2. Hook intercepts `execute_trade`
3. Hook blocks trade (returns `"deny"`)
4. Hook sends approval request to Slack
5. Trade does NOT execute

**Messages you see:**

**Message 1: Approval Request** 🤔
```
🤔 **Trade Approval Required**

**Trade Details:**
• Symbol: AAPL
• Action: BUY
• Quantity: 1
• Confidence: 50% (below threshold: 85%)

**Strategy:** manual_test
**Reasoning:** Manual test trade

**Recent Performance:**
• Win Rate: 50%
• Daily P&L: $0.00

**To approve and execute this trade:**
/test-trade AAPL buy 1 --force

**Alternatives:**
• Increase auto-trade threshold: /update-threshold 0.50
• Reject: Do nothing
```

**Message 2: Claude's Response**
```
Test Trade Status: ⚠️ Awaiting Approval

The trade execution has been blocked as designed.

Why it was blocked:
The confidence level (50%) is below the auto-trade threshold (85%).

The trading flow is working correctly! ✅
```

### 2. Approve Trade (Force Execute)

**User runs:**
```
/test-trade AAPL buy 1 --force
```

**What happens:**
1. Agent prepares trade with confidence **95%** (forced high)
2. Hook allows trade (95% ≥ 85%)
3. Trade executes immediately
4. Order submitted to Alpaca

**Message you see:**
```
⚡ Testing trade execution: BUY 1 AAPL (FORCE)

✅ Trade executed successfully!
Order ID: abc-123-xyz
Status: filled
```

### 3. High Confidence Trade (≥ 85%)

If the agent autonomously detects a high-confidence opportunity:

1. Agent prepares trade with confidence ≥ 85%
2. Hook allows automatically
3. Trade executes without approval

---

## Available Commands

### `/test-trade SYMBOL ACTION QUANTITY [--force]`

Execute a test trade.

**Examples:**
```bash
/test-trade AAPL buy 1           # Medium confidence (50%) - requires approval
/test-trade AAPL buy 1 --force   # High confidence (95%) - auto-executes
/test-trade SPY sell 5 -f        # Short form of --force
```

### `/update-threshold [VALUE]`

Update the auto-trade confidence threshold.

**Examples:**
```bash
/update-threshold              # Show current threshold
/update-threshold 0.70         # Set to 70% (more trades require approval)
/update-threshold 0.90         # Set to 90% (fewer trades require approval)
```

**Effect:**
- Trades with confidence **≥ threshold** → Auto-execute
- Trades with confidence **< threshold** → Require approval

### Other Commands

```bash
/portfolio          # View current positions
/check-orders       # View recent orders
/parameters         # View strategy parameters
/status             # View agent status
```

---

## Three Ways to Handle Low-Confidence Trades

When you receive an approval request, you have 3 options:

### Option 1: Approve with `--force`
```
/test-trade AAPL buy 1 --force
```
Executes the trade immediately.

### Option 2: Lower the threshold
```
/update-threshold 0.50
```
Makes 50%+ confidence trades auto-execute.
**Caution:** This affects ALL future trades!

### Option 3: Reject (do nothing)
Simply ignore the approval request.
The trade will not execute.

---

## Configuration

### Current Settings

```yaml
auto_trade_threshold: 0.85  # 85%
```

### Modify Settings

**Via Slack:**
```
/update-threshold 0.75
```

**Via config file:**
```yaml
# config/config.yaml
strategy:
  auto_trade_threshold: 0.85  # Change this value
```

---

## Testing Checklist

- [x] Low confidence trade blocked
- [x] Approval request sent to Slack
- [x] Claude explains blockage
- [x] `--force` flag executes trade
- [x] `/update-threshold` command works
- [x] High confidence trades auto-execute

---

## Architecture

### Hook Flow

```
Agent → execute_trade tool
         ↓
    PreToolUse Hook
         ↓
   Check confidence
         ↓
   ┌────────────────┐
   │ < threshold?   │
   └────────────────┘
         ↓
    ┌────┴────┐
    ↓         ↓
   YES        NO
    ↓         ↓
  DENY      ALLOW
    ↓         ↓
 Blocked   Execute
    ↓
Send Slack
approval
request
```

### Permission Decision

The hook returns one of:

1. **`{}`** (empty) → Allow trade
2. **`{"permissionDecision": "deny"}`** → Block trade
3. **`{"permissionDecision": "allow"}`** → Force allow

We use **"deny"** for low-confidence trades because **"ask"** doesn't work programmatically (CLI-only feature).

---

## Key Files

1. **`hooks/trading_hooks.py`**
   - `pre_trade_hook()` - Intercepts trades
   - `_send_approval_request()` - Sends Slack message
   - `_get_recent_performance()` - Calculates win rate

2. **`messaging/slack_bot.py`**
   - `/test-trade` - Test trade execution
   - `/update-threshold` - Modify approval threshold

3. **`agent/autonomous_strategy.py`**
   - `get_auto_trade_threshold()` - Get threshold
   - `update_parameter()` - Update settings

---

## Next Enhancements

### 1. Interactive Buttons ⭐

Add Slack buttons for approve/reject:

```python
blocks = [
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Approve"},
                "value": "approve_trade_abc123",
                "action_id": "approve_trade"
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Reject"},
                "value": "reject_trade_abc123",
                "action_id": "reject_trade"
            }
        ]
    }
]
```

### 2. Pending Trades Database

Store pending approvals:

```python
pending_trades = {
    "trade_id": {
        "symbol": "AAPL",
        "action": "buy",
        "quantity": 1,
        "confidence": 0.50,
        "expires_at": "2025-10-01T23:30:00Z"
    }
}
```

### 3. Trade Expiration

Auto-reject after timeout:

```python
if time.now() > trade["expires_at"]:
    cancel_trade(trade_id)
```

### 4. Approval History

Track approval decisions:

```sql
CREATE TABLE approval_history (
    trade_id TEXT,
    approved BOOLEAN,
    approved_by TEXT,
    approved_at TIMESTAMP
);
```

---

## Summary

✅ **Approval flow works!**

**Low confidence (< 85%):**
1. Trade blocked
2. Approval request sent
3. User approves with `--force`

**High confidence (≥ 85%):**
1. Trade auto-executes
2. No approval needed

**Commands:**
- `/test-trade AAPL buy 1` → Blocked, needs approval
- `/test-trade AAPL buy 1 --force` → Approved, executes
- `/update-threshold 0.70` → Change threshold

**The basic plumbing is verified and working!** 🎉

You can now move forward with implementing actual trading strategies.
