# Setup Guide: Threads + X Dual Autopilot

A production-ready dual social media autopilot that generates leads on Threads and thought leadership on X. Both agents run side-by-side in tmux with full persona injection.

---

## Quick Start (30 seconds)

```bash
# Clone the repo
git clone https://github.com/kirbudilov01/telegramleadgenerator.git
cd "TELEGRAM : THREADS AGENT"

# Initialize (one-time: installs deps, sets up venv, patches X agent)
./go.sh init

# Login to both agents (one-time: authenticates Threads + X)
./go.sh login

# Start both agents side-by-side in tmux
./go.sh start

# Attach if you close the window
./go.sh attach

# Stop gracefully
./go.sh stop
```

---

## Prerequisites

- **macOS or Linux** (tested on macOS 12+, Linux Ubuntu 20.04+)
- **Node.js** 18+ (for X agent)
- **Python** 3.10+ (for Threads autopilot)
- **tmux** (for side-by-side panes)
  - macOS: `brew install tmux`
  - Linux: `sudo apt-get install tmux`
- **Git**

---

## Full Setup (Step-by-Step)

### 1. Clone Both Repos

The Threads agent depends on the X agent, so they live in adjacent directories:

```bash
# Threads agent repo
git clone https://github.com/kirbudilov01/telegramleadgenerator.git \
  "TELEGRAM : THREADS AGENT"

cd "TELEGRAM : THREADS AGENT"

# X agent repo (as sibling)
git clone https://github.com/nirholas/XActions.git ../X-ACTIONS-AGENT
```

Or if you prefer different paths, update the `X_AGENT_DIR` in `go.sh`.

### 2. Run Doctor (Health Check)

```bash
./go.sh doctor
```

Expected output:
```
OK: required commands found
OK: Python venv exists
OK: Threads login artifacts exist
WARN: Threads github_token missing in config.json  ← YOU FIX THIS NEXT
WARN: X session missing (data/session.json)        ← YOU FIX THIS WITH ./go.sh login
OK: X dependencies installed
```

### 3. Get Your GitHub Token (REQUIRED)

The Threads autopilot uses **GitHub Models API** for free AI. No credit card needed.

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Name: `Threads Autopilot`
4. Scopes: Leave all unchecked (no scopes needed)
5. Click **"Generate token"**
6. Copy the token (starts with `ghp_`)

Then:

```bash
# Option A: Edit config directly
nano threads_autopilot/config.json
# Find: "github_token": "ВСТАВЬ_НОВЫЙ_ТОКЕН_СЮДА"
# Replace with your token: "github_token": "ghp_xxxx"

# Option B: Set environment variable (persists for this shell session)
export GITHUB_TOKEN=ghp_xxxx
```

### 4. Initialize Dependencies (One-Time)

```bash
./go.sh init
```

This:
- Creates Python venv + installs Playwright + browsers
- Installs npm deps for X agent
- Auto-patches X agent's browserDriver to recognize env vars
- Shows success/error for each step

### 5. Login to Threads

```bash
./go.sh login threads
```

You'll see:
1. A Chromium browser opens
2. You manually log into your Threads account
3. Once logged in, the agent saves your session (no need to repeat)
4. Close the browser when done

### 6. Login to X (Twitter)

```bash
./go.sh login x
```

You'll see:
1. A browser opens with X.com
2. You manually log in to your X account
3. The agent saves session to `../X-ACTIONS-AGENT/data/session.json`
4. Close the browser when done

### 7. Start Both Agents

```bash
./go.sh start
```

You'll see:
- **Left pane**: Threads autopilot running (scanning for leads, replying, following)
- **Right pane**: X agent running (finding relevant topics, composing tweets)
- **Both logs**: Real-time to files (`autopilot.log`, `../X-ACTIONS-AGENT/logs/agent.log`)

### 8. Attach/Detach

```bash
# Attach if you closed the window
./go.sh attach

# Stop both agents gracefully
./go.sh stop

# Restart both agents
./go.sh restart

# Check status
./go.sh status
```

---

## Configuration

### Threads Autopilot (threads_autopilot/config.json)

Key settings:

```json
{
  "profile": "safe",           // "safe" (slow, careful) or "aggressive"
  "headful": true,             // false = headless (faster, less visible)
  "llm_provider": "github_models",  // or "openrouter", "ollama"
  "github_token": "ghp_...",   // YOUR GitHub token
  "auto_send_min_score": 0.82, // Don't send if confidence < 82%
  "draft_min_score": 0.7,      // Draft if score 70-82%
  "keywords": [                // Searches to monitor
    "нужен разработчик",
    "ищу разработчика",
    "hire developer",
    ...
  ]
}
```

### X Agent (../X-ACTIONS-AGENT/data/agent-config.json)

Key settings:

```json
{
  "niche": {
    "name": "AI Products, Content Systems & Telegram Commerce",
    "searchTerms": [
      "AI products",
      "telegram mini app",
      "youtube analytics",
      ...
    ]
  },
  "persona": {
    "expertise": [...],
    "opinions": [...],
    "exampleTweets": [...]
  },
  "llm": {
    "provider": "openrouter",  // Free GitHub Models support coming
    "models": {
      "fast": "anthropic/claude-haiku-3-3b",
      "mid": "anthropic/claude-sonnet-4",
      "smart": "anthropic/claude-sonnet-4"
    }
  }
}
```

---

## Multi-Monitor / Linux Resolution

If you're on a different screen size or Linux, override window/viewport sizes via `.env`:

```bash
# Copy template
cp .env.example .env

# Edit for your screen
nano .env
```

Example for **Linux 1920x1080 (split screen)**:

```bash
DUAL_TMUX_WIDTH=240
DUAL_TMUX_HEIGHT=60
THREADS_WIN_WIDTH=940
THREADS_WIN_HEIGHT=1040
X_BROWSER_X=960
X_BROWSER_WIDTH=940
X_BROWSER_HEIGHT=1040
```

Then start:

```bash
./go.sh start
```

The env vars override defaults in `config.json` + `agent-config.json`.

---

## Troubleshooting

### "GitHub token missing"

```bash
# Either:
export GITHUB_TOKEN=ghp_xxxxx
./go.sh start

# Or edit config.json directly:
nano threads_autopilot/config.json
```

### "X session missing"

Run `./go.sh login x` to authenticate. Session persists afterwards.

### "Python venv broken"

```bash
./go.sh init
# Rebuilds venv from scratch
```

### "Threads browser won't load"

Check if Playwright browsers are installed:

```bash
source threads_autopilot/venv/bin/activate  # or venv/bin/activate
playwright install chromium
```

### "X agent not tweeting"

Check `../X-ACTIONS-AGENT/logs/agent.log` for errors. Common:
- OpenRouter key invalid → add `OPENROUTER_API_KEY` to `.env`
- Session expired → run `./go.sh login x` again
- No matching topics → check `niche.searchTerms` in `agent-config.json`

### "Tmux panes too small"

Adjust in `.env`:

```bash
DUAL_TMUX_WIDTH=280  # Increase columns
DUAL_TMUX_HEIGHT=70  # Increase rows
```

Or set screen-specific defaults (see `.env.example`).

---

## Running Overnight

Before you leave agents running:

1. **Verify login works**:
   ```bash
   ./go.sh login threads
   ./go.sh login x
   ```

2. **Check dry-run**:
   ```bash
   ./go.sh start --dry-run  # See what agents will do without posting
   ```

3. **Monitor first hour**:
   ```bash
   ./go.sh attach
   # Watch both panes, ensure no errors
   ```

4. **Then safe to leave**:
   - Threads: ~2-5 leads/day in safe mode, 5-15 in aggressive
   - X: ~3-8 tweets/day, scheduled by relevance

5. **Stop gracefully**:
   ```bash
   ./go.sh stop
   ```

---

## Commands Reference

| Command | Purpose |
|---------|---------|
| `./go.sh doctor` | Check readiness (tools, tokens, sessions) |
| `./go.sh init` | Install all dependencies |
| `./go.sh login` | Interactive: authenticate both agents |
| `./go.sh login threads` | Authenticate Threads only |
| `./go.sh login x` | Authenticate X only |
| `./go.sh start` | Launch both agents side-by-side in tmux |
| `./go.sh attach` | Attach to running tmux session |
| `./go.sh stop` | Stop both agents gracefully |
| `./go.sh restart` | Restart both agents |
| `./go.sh status` | Show running processes + log tails |

---

## Architecture

```
Threads Agent (Python):
  ├── autopilot.py          Main loop: keyword search → classify posts → reply/like/follow
  ├── config.json           Keywords, window size, LLM settings
  ├── persona.md            About3.md (Kirill's bio, injected into all replies)
  ├── chrome_profile/       Persistent browser profile (login survives restarts)
  └── threads_storage_state.json  Backup session state

X Agent (Node.js):
  ├── src/agents/agent.js          Main loop: find topics → compose tweets → post
  ├── data/agent-config.json       Niche, persona, LLM config
  ├── data/session.json            Browser session (cookies)
  └── logs/agent.log               Execution log

Launcher:
  └── go.sh                 Unified interface for doctor/init/login/start/stop/restart/status
```

---

## How It Works

### Threads Autopilot (Lead Generation)

1. **Keyword Search**: Scans Threads for keywords (e.g., "need developer")
2. **Post Classification**: Uses AI to determine if post is relevant + high-intent
3. **Reply Generation**: If relevant, composes a helpful reply in Kirill's voice
4. **Quality Check**: If confidence < 0.82, drafts instead of sending
5. **Action Mix**: 58% replies, 22% likes, 12% follows, 8% browses

### X Agent (Thought Leadership)

1. **Topic Monitoring**: Scans Twitter for niche keywords (AI products, Telegram, YouTube, etc.)
2. **Tweet Composition**: Uses AI to write topical, expert-level tweets
3. **Scheduled Posting**: Posts on schedule (3-8/day by relevance)
4. **Engagement**: Likes/retweets related content

---

## Next Steps

1. **Run setup once**: `./go.sh init && ./go.sh login`
2. **Monitor dry-run**: `./go.sh start` for 1 hour, watch logs
3. **Adjust config**: Tweak keywords, auto_send_min_score, action_mix as needed
4. **Leave running**: Safe to leave overnight once you're confident

Questions? Check logs:
- Threads: `tail -f autopilot.log`
- X: `tail -f ../X-ACTIONS-AGENT/logs/agent.log`

Good luck! 🚀
