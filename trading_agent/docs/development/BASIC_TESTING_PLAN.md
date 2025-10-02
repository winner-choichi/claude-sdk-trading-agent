# Basic Trading Flow - Testing & Verification Plan

## Current Status Analysis

### ✅ What's Already Implemented

1. **Order Execution** (`tools/alpaca_tools.py`)
   - ✅ `execute_trade()` - submits orders to Alpaca
   - ✅ Supports market & limit orders
   - ✅ Saves trades to database
   - ✅ Returns order confirmation

2. **Hook System** (`hooks/trading_hooks.py`)
   - ✅ `pre_trade_hook()` - intercepts trades before execution
   - ✅ Auto-execute logic (high confidence)
   - ✅ Request approval logic (medium confidence)
   - ✅ Risk checks (daily loss limit)
   - ✅ `post_trade_hook()` - logs after execution

3. **Slack Bot** (`messaging/slack_bot.py`)
   - ✅ `/portfolio` - get portfolio status
   - ✅ `/trading-report` - generate daily report
   - ✅ Message handling

### ❓ What Needs Testing

1. **Does the approval flow work in Slack?**
   - When agent wants to trade, does Slack show approval request?
   - Can user approve/reject via Slack?
   - Does agent proceed correctly after approval?

2. **Does order status get reported back?**
   - After trade executes, does Slack show confirmation?
   - Are order fills tracked?
   - Are errors reported properly?

3. **Does the full lifecycle work?**
   ```
   Opportunity Detected → Hook Intercepts → Slack Approval Request
   → User Approves → Order Submitted → Order Filled → Slack Confirmation
   ```

---

## Testing Plan

### Test 1: Manual Trade Command (Simplest)

**Goal:** Verify basic order execution works

**Create a simple test command:**

```python
# Add to messaging/slack_bot.py

@self.app.command("/test-trade")
async def handle_test_trade(ack, command, say):
    """Test a simple trade execution"""
    await ack()

    # Parse command: /test-trade AAPL buy 1
    parts = command["text"].split()
    if len(parts) < 3:
        await say("Usage: /test-trade SYMBOL ACTION QUANTITY")
        return

    symbol, action, quantity = parts[0], parts[1], parts[2]

    await say(f"🧪 Testing trade: {action.upper()} {quantity} {symbol}")

    try:
        # Call agent's execute_trade directly
        response = await self.agent.handle_user_query(
            f"Execute a test trade: {action} {quantity} shares of {symbol} "
            f"with confidence 0.50 (test trade), strategy 'manual_test', "
            f"reasoning 'Manual test via Slack command'",
            user_id=command["user_id"]
        )

        await say(f"✅ Response:\n{response}")

    except Exception as e:
        await say(f"❌ Trade failed: {str(e)}")
```

**Expected Results:**
1. ✅ Hook intercepts trade (confidence 0.50 = medium)
2. ✅ Slack shows approval request
3. ❌ **PROBLEM**: User can't approve yet (no approval buttons)

---

### Test 2: Check if Approval Mechanism Exists

**The Issue:**
The hook shows approval messages, but I don't see Slack buttons/interactions for approval.

**What we need:**
```python
# When hook returns "prompt", we need:
1. Send Slack message with approve/reject buttons
2. Wait for user response
3. Pass decision back to agent
```

**Check if this exists:**
```bash
grep -r "approve" trading_agent/messaging/
grep -r "Block" trading_agent/messaging/  # Slack buttons use "Block Kit"
grep -r "actions" trading_agent/messaging/
```

---

### Test 3: Order Status Tracking

**Test if Alpaca orders are monitored:**

```python
# Add to messaging/slack_bot.py

@self.app.command("/check-orders")
async def handle_check_orders(ack, command, say):
    """Check status of recent orders"""
    await ack()

    await say("📋 Checking recent orders...")

    try:
        response = await self.agent.handle_user_query(
            "Get my recent account activity and check status of any pending orders",
            user_id=command["user_id"]
        )

        await say(response)

    except Exception as e:
        await say(f"❌ Error: {str(e)}")
```

**Expected Results:**
1. ✅ Shows recent orders
2. ✅ Shows order status (filled, pending, cancelled)
3. ❓ Are filled orders reported to Slack automatically?

---

### Test 4: Full Lifecycle Test

**Scenario:** Agent autonomously detects opportunity and requests approval

**What should happen:**
```
1. Agent analyzes market
   ↓
2. Detects opportunity: "SPY looks oversold, RSI = 28"
   ↓
3. Prepares trade: BUY 10 SPY, confidence 0.75
   ↓
4. Hook intercepts (0.75 < threshold 0.85)
   ↓
5. Slack message: "Trade Confirmation Requested..." with buttons
   ↓
6. User clicks "Approve"
   ↓
7. Order submitted to Alpaca
   ↓
8. Order fills
   ↓
9. Slack confirmation: "✅ Trade executed: BUY 10 SPY @ $589.43"
```

**Current Problems:**
- ❌ No automatic opportunity detection running
- ❌ No Slack approval buttons
- ❌ No automatic fill notifications

---

## What Needs to be Built

### Priority 1: Slack Approval Buttons ⚠️ CRITICAL

**Problem:** Hook requests approval but user can't respond

**Solution:** Add Slack Block Kit buttons

```python
# In messaging/slack_bot.py

async def request_trade_approval(
    self,
    trade_params: dict,
    approval_message: str
) -> bool:
    """
    Send trade approval request to Slack with buttons

    Returns:
        True if approved, False if rejected
    """
    import asyncio

    # Create a future to wait for response
    approval_future = asyncio.Future()

    # Store in pending approvals dict
    approval_id = str(uuid.uuid4())
    self.pending_approvals[approval_id] = {
        "future": approval_future,
        "trade_params": trade_params
    }

    # Send message with buttons
    try:
        await self.app.client.chat_postMessage(
            channel=self.channel_id,
            text=approval_message,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": approval_message
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ Approve"},
                            "style": "primary",
                            "value": approval_id,
                            "action_id": "approve_trade"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "❌ Reject"},
                            "style": "danger",
                            "value": approval_id,
                            "action_id": "reject_trade"
                        }
                    ]
                }
            ]
        )

        # Wait for user response (with 60s timeout)
        approved = await asyncio.wait_for(approval_future, timeout=60.0)
        return approved

    except asyncio.TimeoutError:
        await self.app.client.chat_postMessage(
            channel=self.channel_id,
            text=f"⏱️ Trade approval timed out - REJECTED for safety"
        )
        return False


# Add button handlers
@self.app.action("approve_trade")
async def handle_approve_trade(ack, body, say):
    """Handle trade approval"""
    await ack()

    approval_id = body["actions"][0]["value"]

    if approval_id in self.pending_approvals:
        # Resolve the future with True
        self.pending_approvals[approval_id]["future"].set_result(True)

        await say("✅ Trade approved - executing now...")

        del self.pending_approvals[approval_id]


@self.app.action("reject_trade")
async def handle_reject_trade(ack, body, say):
    """Handle trade rejection"""
    await ack()

    approval_id = body["actions"][0]["value"]

    if approval_id in self.pending_approvals:
        # Resolve the future with False
        self.pending_approvals[approval_id]["future"].set_result(False)

        await say("❌ Trade rejected by user")

        del self.pending_approvals[approval_id]
```

**Integration with Hook System:**

The challenge: Hook runs synchronously but Slack approval is async. We need to bridge them.

**Option A:** Make hook async-aware
**Option B:** Use callback mechanism
**Option C:** Simplify - just log to Slack, require manual `/approve` command

---

### Priority 2: Automatic Fill Notifications

**After trade executes, notify Slack:**

```python
# In post_trade_hook or after execute_trade

async def notify_trade_executed(self, trade_result: dict):
    """Send trade execution notification to Slack"""
    if not self.slack_bot:
        return

    await self.slack_bot.send_trade_notification(
        symbol=trade_result["symbol"],
        action=trade_result["action"],
        quantity=trade_result["quantity"],
        price=trade_result["price"],
        order_id=trade_result["order_id"],
        status=trade_result["status"]
    )
```

---

### Priority 3: Order Status Monitoring

**Poll Alpaca for order updates:**

```python
# Background task to monitor orders

async def monitor_orders(self):
    """Monitor pending orders and notify when filled"""
    while self.is_running:
        try:
            # Get all pending orders
            orders = self.trading_client.get_orders(status="open")

            for order in orders:
                # Check if order is new (not in our tracking)
                if order.id not in self.tracked_orders:
                    self.tracked_orders[order.id] = {
                        "symbol": order.symbol,
                        "status": order.status,
                        "notified": False
                    }

            # Check for filled orders
            for order_id, info in list(self.tracked_orders.items()):
                # Refresh order status
                current_order = self.trading_client.get_order_by_id(order_id)

                if current_order.status == "filled" and not info["notified"]:
                    # Notify Slack
                    await self.slack_bot.send_fill_notification(current_order)
                    info["notified"] = True

                # Clean up closed orders after notification
                if current_order.status in ["filled", "cancelled"] and info["notified"]:
                    del self.tracked_orders[order_id]

        except Exception as e:
            logger.error(f"Error monitoring orders: {e}")

        # Check every 10 seconds
        await asyncio.sleep(10)
```

---

## Simplified Approach (Recommendation)

Instead of complex async approval flow, start simpler:

### Approach A: Manual Approval Commands
```
Agent: "🤔 Trade opportunity: BUY 10 SPY (confidence 0.75)"
User: /approve
Agent: ✅ Executing trade...
```

### Approach B: Confidence Threshold Only
```
- Confidence > 0.90 → Auto-execute
- Confidence < 0.90 → Log to Slack but don't execute
- User can manually trigger: /execute-last-suggestion
```

### Approach C: Review Before Market Open
```
- Agent analyzes overnight
- Generates list of potential trades
- Posts to Slack in morning
- User approves selected trades
- Agent executes during market hours
```

---

## Testing Checklist

### Basic Trade Execution
- [ ] Agent can detect a trade opportunity
- [ ] Trade parameters are correct (symbol, qty, price)
- [ ] Order successfully submits to Alpaca
- [ ] Order ID is returned and saved
- [ ] Trade appears in database

### Risk Management
- [ ] Daily loss limit is checked
- [ ] Max position size is enforced
- [ ] Portfolio exposure limit works
- [ ] Trades blocked when limits exceeded

### Approval Flow (If Implemented)
- [ ] Low confidence trades request approval
- [ ] Approval request appears in Slack
- [ ] User can approve via Slack
- [ ] User can reject via Slack
- [ ] Agent proceeds after approval
- [ ] Agent stops after rejection

### Order Monitoring
- [ ] Pending orders are tracked
- [ ] Fill notifications appear in Slack
- [ ] Failed orders are reported
- [ ] Order status updates correctly

### Slack Integration
- [ ] `/test-trade` command works
- [ ] `/check-orders` command works
- [ ] Trade confirmations appear
- [ ] Error messages are clear
- [ ] Format is readable

---

## Next Steps - Recommendations

### Option 1: Full Implementation (3-4 hours)
1. Build Slack approval buttons
2. Integrate with hook system
3. Add order monitoring
4. Test full flow

### Option 2: Simplified Flow (1-2 hours)
1. Add `/test-trade` command
2. Add `/approve-last` command for manual approval
3. Add order fill notifications
4. Focus on reliability over automation

### Option 3: Verify Current State First (30 mins)
1. Start the agent
2. Try `/trading-report`
3. Manually ask agent to analyze a stock
4. See what happens when it wants to trade
5. Document what works and what doesn't

---

## Which approach do you prefer?

1. **Full automated approval system** - Most sophisticated but complex
2. **Simple manual commands** - Quick to build, reliable
3. **Test current state first** - See what actually works before building

I recommend **Option 3** first, then **Option 2** for quick wins.

Want me to help test the current state?
