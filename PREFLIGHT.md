# Pre-Run Checklist (5 Minutes)

Before starting agents overnight, verify everything is ready:

## 1. GitHub Token ✓

```bash
# Check if token is set
grep "github_token" threads_autopilot/config.json | head -1
```

Should show something like:
```
"github_token": "ghp_xxxx..."
```

If it shows `ВСТАВЬ_НОВЫЙ_ТОКЕН_СЮДА` → **YOU NEED TO SET IT**

**Fix:**
```bash
# Get a token: https://github.com/settings/tokens
# Then set it:
export GITHUB_TOKEN=ghp_your_token_here
```

---

## 2. Threads Session ✓

```bash
./go.sh doctor | grep -i threads
```

Should show:
```
OK: Threads login artifacts exist
```

If it says WARN → **RUN SETUP AGAIN**

```bash
./go.sh login threads
# Browser opens, log in to Threads manually, close when done
```

---

## 3. X Session ✓

```bash
./go.sh doctor | grep -i "X session"
```

Should show:
```
OK: X dependencies installed
```

If it says "X session missing" → **RUN LOGIN ONCE**

```bash
./go.sh login x
# Browser opens, log in to X manually, close when done
```

---

## 4. Run Dry-Run (30 Seconds)

```bash
./go.sh start
```

Watch both panes for 30 seconds:
- **Threads (left)**: Should see "Searching for keywords...", post classifications
- **X (right)**: Should see "Scanning niche topics...", tweet composition

Both should be running without errors.

```bash
./go.sh stop
# Stop when satisfied
```

---

## 5. Check Logs ✓

```bash
# Threads log
tail -20 autopilot.log

# X log
tail -20 ../X-ACTIONS-AGENT/logs/agent.log
```

Look for:
- ❌ ERROR, FAIL, CRITICAL → **DON'T RUN OVERNIGHT**
- ✓ "Starting...", "Processing...", "Posted" → **SAFE TO RUN**

---

## 6. Final Sanity Checks ✓

```bash
# All components running?
./go.sh doctor
```

Expected output:
```
OK: required commands found
OK: Python venv exists
OK: Threads login artifacts exist
✓ OK: Threads github_token present (if set in env or config.json)
✓ OK: X session exists
OK: X dependencies installed
```

---

## 7. You're Good! 🚀

```bash
# Start for real
./go.sh start

# Leave it running. Monitor:
# - Check logs every 2-3 hours first time
# - Both agents should post 5-15 items/day total
# - No errors in logs = healthy

# When done:
./go.sh stop
```

---

## If Something Breaks

### "Token not found"
```bash
export GITHUB_TOKEN=ghp_your_token  # Get from: https://github.com/settings/tokens
./go.sh start
```

### "Threads browser won't load"
```bash
./go.sh init  # Rebuild venv + Playwright
./go.sh login threads
```

### "X won't authenticate"
```bash
./go.sh login x
# If still broken, check:
ls -la ../X-ACTIONS-AGENT/data/session.json
```

### "Both agents running but no posts"
- Threads: Check `auto_send_min_score` in `config.json` (default 0.82 is conservative)
- X: Check if OpenRouter key is set: `echo $OPENROUTER_API_KEY`

---

## Running Schedule Recommendation

**Safe mode (default):**
- Threads: 2-5 leads/day
- X: 3-8 tweets/day
- Safe for: 24/7 running

**Aggressive mode:**
- Threads: Edit `config.json`: `"profile": "aggressive"`
- Results: 10-15 leads/day, higher false-positive rate
- Safe for: 2-4 hours, then review manually

---

## Quick Command Reference

```bash
./go.sh doctor              # Health check
./go.sh init                # Install deps
./go.sh login [threads|x]   # Login to specific agent
./go.sh start               # Start both agents
./go.sh attach              # Attach if window closed
./go.sh stop                # Stop gracefully
./go.sh restart             # Restart both
./go.sh status              # Show running pids + tails
```

---

**Last Check Before Sleeping:**
1. `./go.sh doctor` → No WAINGs (except maybe optional ones)
2. `tail -5 autopilot.log` → No ERRORs
3. `tail -5 ../X-ACTIONS-AGENT/logs/agent.log` → No ERRORs
4. `./go.sh start` → Both panes show activity
5. `./go.sh stop` → Both agents shut down cleanly

**Then:** Sleep well, agents are working for you 😴
