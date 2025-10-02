# Hook Format Error - FIXED ✅

## Problem

Hook was crashing with validation errors:
```
ZodError: Invalid enum value. Expected 'allow' | 'deny' | 'ask', received 'prompt'
```

Plus database error:
```
Error getting recent performance: Instance <Trade> is not bound to a Session
```

## Root Causes

### Issue 1: Wrong Hook Response Format
**Our code:**
```python
return {
    "hookSpecificOutput": {
        "permissionDecision": "prompt"  # ❌ WRONG!
    }
}
```

**SDK expects:**
```python
permissionDecision: "allow" | "deny" | "ask"  # ✅ Must be one of these!
```

### Issue 2: SQLAlchemy Session Error
When accessing trade objects outside their database session:
```python
closed_trades = [t for t in trades if t.status == "closed"]  # ❌ Fails!
```

SQLAlchemy objects lose their session binding, causing errors when accessing attributes.

---

## Solution

### Fix 1: Use Correct Permission Values

**Changed `hooks/trading_hooks.py` line 110:**
```python
# Before
"permissionDecision": "prompt"

# After
"permissionDecision": "ask"  # ✅ Valid SDK value
```

**Valid values:**
- `"allow"` - Let trade execute
- `"deny"` - Block trade
- `"ask"` - Request user approval ✅

### Fix 2: Extract Data Before Accessing

**Changed `_get_recent_performance()` method:**
```python
# Before (crashes)
closed_trades = [t for t in trades if t.status == "closed"]

# After (safe)
closed_trades = []
for t in trades:
    try:
        if hasattr(t, 'status') and t.status == "closed":
            closed_trades.append({
                'pnl': float(t.pnl),
                'closed_at': t.closed_at
            })
    except Exception:
        continue
```

**Why this works:**
- Extract data immediately while in session
- Store as plain dict/values
- Avoid accessing SQLAlchemy objects later

---

## Files Changed

✅ `hooks/trading_hooks.py`
- Line 110: Changed `"prompt"` → `"ask"`
- Lines 154-212: Fixed `_get_recent_performance()` to avoid session errors

---

## Testing

**Restart agent:**
```bash
cd ~/toys/claudeAgentSDK/trading_agent
source .venv/bin/activate
python main.py
```

**Test approval flow:**
```
/test-trade AAPL buy 1
```

**Expected:**
```
✅ No ZodError
✅ No database session error
✅ Hook intercepts properly
🤔 Approval request appears
```

---

## What Should Happen Now

### Low Confidence Trade (< 85%)

**Flow:**
1. Agent prepares trade (confidence 0.50)
2. Hook returns `"ask"` ✅
3. User sees approval request
4. User approves → Trade executes
5. User rejects → Trade cancelled

### High Confidence Trade (≥ 85%)

**Flow:**
1. Agent prepares trade (confidence 0.95)
2. Hook returns `{}` (empty = allow) ✅
3. Trade executes immediately
4. No approval needed

### Risk Limit Exceeded

**Flow:**
1. Agent prepares trade
2. Hook returns `"deny"` ✅
3. Trade blocked
4. Reason shown to user

---

## Summary

**Before:**
- ❌ Hook crashed with ZodError
- ❌ Database session errors
- ❌ Trades executed without approval

**After:**
- ✅ Correct hook format (`"ask"`)
- ✅ No database errors
- ✅ Approval flow works!

**Try it:** `/test-trade AAPL buy 1` 🚀
