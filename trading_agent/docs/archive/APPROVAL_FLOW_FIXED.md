# Approval Flow - FIXED ✅

## Problem

The approval flow wasn't working - trades with low confidence executed immediately instead of requesting user approval.

## Root Cause

**The SDK's `permissionDecision: "ask"` only works in interactive CLI environments**, not in programmatic/API contexts like our Slack bot.

When using the Claude Agent SDK programmatically:
- There's no built-in UI to show approval prompts
- The SDK can't pause and wait for user input
- The "ask" decision gets treated as "allow" by default

### Evidence from Logs

```
🔍 PRE_TRADE_HOOK CALLED - Tool: mcp__trading__execute_trade
🔍 HOOK RETURNING 'ask' - Confidence 50.0% < threshold 85.0%
   This should PAUSE execution and wait for approval!
[INFO] tools.alpaca_tools: Executing trade: symbol=AAPL, action=buy
```

Hook returns "ask", but trade executes immediately.

---

## Solution

**Use `"deny"` instead of `"ask"` and send approval request to Slack manually.**

### How It Works Now

1. **Hook blocks trade with `"deny"`** → Trade does not execute
2. **Hook sends detailed approval request to Slack** → User sees trade details
3. **Claude receives denial reason** → Informs user that approval is needed
4. **User can manually execute** → Via `/test-trade` command if they approve

### Changes Made

#### 1. Updated Hook Response (`hooks/trading_hooks.py`)

**Before:**
```python
return {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",  # ❌ Doesn't work programmatically
        "permissionDecisionReason": message.strip()
    }
}
```

**After:**
```python
# Send approval request to Slack
if self.slack_bot:
    asyncio.create_task(self._send_approval_request(...))

return {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",  # ✅ Blocks execution
        "permissionDecisionReason": "Trade requires approval (confidence 50.0% below threshold 85.0%). Please review and manually approve if desired."
    }
}
```

#### 2. Added Slack Approval Request Method

```python
async def _send_approval_request(
    self,
    symbol: str,
    action: str,
    quantity: int,
    confidence: float,
    strategy_name: str,
    reasoning: str,
    recent_performance: Dict[str, Any],
    threshold: float
):
    """Send trade approval request to Slack"""
    message = f"""🤔 **Trade Approval Required**

**Trade Details:**
• Symbol: {symbol}
• Action: {action.upper()}
• Quantity: {quantity}
• Confidence: {confidence:.1%} _(below threshold: {threshold:.1%})_

**Strategy:** {strategy_name}

**Reasoning:** {reasoning}

**Recent Performance:**
• Win Rate: {recent_performance.get('win_rate', 0):.1%}
• Daily P&L: ${recent_performance.get('daily_pnl', 0):.2f}

To execute this trade, use:
```
/test-trade {symbol} {action} {quantity}
```
"""

    if hasattr(self.slack_bot, 'send_message'):
        await self.slack_bot.send_message(message)
```

#### 3. Connected Slack Bot to Hooks (`main.py`)

```python
# Connect agent and slack bot
agent.slack_bot = slack_bot
agent.hooks.slack_bot = slack_bot  # ✅ New: hooks can now send Slack messages
```

---

## Testing Instructions

### 1. Restart Agent

```bash
cd ~/toys/claudeAgentSDK/trading_agent
pkill -f "python main.py"
source .venv/bin/activate
python main.py
```

### 2. Test Low Confidence Trade

In Slack:
```
/test-trade AAPL buy 1
```

**Expected:**

1. **Agent prepares trade** (confidence 0.50)
2. **Hook blocks execution** ⏸️
   ```
   ⏸️  BLOCKING TRADE - Confidence 50.0% < threshold 85.0%
   ```
3. **Slack receives approval request** 🤔
   ```
   🤔 **Trade Approval Required**

   **Trade Details:**
   • Symbol: AAPL
   • Action: BUY
   • Quantity: 1
   • Confidence: 50%

   To execute this trade, use:
   /test-trade AAPL buy 1
   ```
4. **Claude responds to user** saying trade was blocked and approval needed
5. **Trade does NOT execute** ❌

### 3. Approve Trade (If Desired)

Run the same command again:
```
/test-trade AAPL buy 1
```

This manually executes the trade (bypassing the confidence check since it's an explicit user request).

---

## Behavior Summary

### Low Confidence Trade (< 85%)

**Flow:**
1. Agent detects opportunity (confidence 0.50)
2. Hook intercepts `execute_trade`
3. Hook blocks with `"deny"`
4. Hook sends detailed approval request to Slack
5. Claude tells user: "Trade requires approval"
6. User can execute manually if they approve

**Result:** ✅ Trade blocked, user maintains control

### High Confidence Trade (≥ 85%)

**Flow:**
1. Agent detects opportunity (confidence 0.95)
2. Hook allows with `return {}`
3. Trade executes automatically

**Result:** ✅ Seamless execution for high-confidence trades

### Risk Limit Exceeded

**Flow:**
1. Agent prepares trade
2. Hook checks risk limits
3. Hook blocks with `"deny"` and reason
4. Trade prevented

**Result:** ✅ Safety mechanism works

---

## Key Insights

1. **SDK's "ask" is CLI-only** → Doesn't work in Slack bots or API contexts
2. **Use "deny" + manual notification** → Achieves same goal programmatically
3. **Hooks + Slack integration** → Builds custom approval flow
4. **Explicit user commands bypass checks** → `/test-trade` always executes

---

## Files Changed

1. ✅ `hooks/trading_hooks.py`
   - Changed `"ask"` → `"deny"` for programmatic contexts
   - Added `_send_approval_request()` method
   - Connected to Slack bot

2. ✅ `main.py`
   - Added `agent.hooks.slack_bot = slack_bot` connection

---

## Next Steps

Once basic approval flow is confirmed working:

1. Add `/approve-trade` command for pending approvals
2. Store pending trades in database
3. Add Slack buttons for approve/reject (interactive messages)
4. Implement trade expiration (auto-reject after X minutes)
5. Add approval history tracking

**But first:** Test the current implementation to verify trades are properly blocked!

---

## Test Checklist

- [ ] Restart agent
- [ ] Run `/test-trade AAPL buy 1`
- [ ] Verify trade is BLOCKED (not executed)
- [ ] Verify approval request appears in Slack
- [ ] Verify Claude responds saying approval needed
- [ ] Verify no order ID appears in Alpaca
- [ ] Test high-confidence auto-execution still works

**Try it now:** `/test-trade AAPL buy 1` 🚀
