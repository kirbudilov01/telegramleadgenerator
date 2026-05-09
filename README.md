# Telegram Lead Generator

Public Telegram lead-generation repository.

This repository keeps the Telegram-focused stack here. The newer companion social-agent stack has been split out into a separate local repo at `/Users/kirill/xautopilot` and should be treated as private/closed.

If you're only working on Telegram, ignore the companion repo and use the Telegram code in this repository.

**Status:** Telegram-focused public repo | **Built:** 2026 | **Last Updated:** 2026-05-09

---

## 🎯 What It Does

### Threads Agent (Lead Generation)
- **Keyword Search**: Monitors 20+ keywords on Threads (e.g., "need developer", "hire developer")
- **Post Classification**: Uses AI to identify high-intent, relevant leads
- **Smart Replies**: Generates contextual, helpful replies in your voice
- **Engagement Mix**: 58% replies, 22% likes, 12% follows, 8% browses
- **Safety Scores**: Only sends high-confidence replies; drafts others for review

### X Agent (Thought Leadership)
- **Topic Monitoring**: Tracks 14+ niche keywords (AI products, Telegram, YouTube, etc.)
- **Tweet Composition**: AI-generated, topical tweets in expert voice
- **Scheduled Posting**: 3-8 tweets/day by relevance
- **Engagement**: Automatic likes, retweets, replies to relevant discussions

---

## 🚀 Quick Start (5 Minutes)

```bash
# Clone repo
git clone https://github.com/kirbudilov01/telegramleadgenerator.git
cd "TELEGRAM : THREADS AGENT"

# One-time setup (installs dependencies)
./go.sh init

# Get GitHub token: https://github.com/settings/tokens (no scopes needed)
export GITHUB_TOKEN=ghp_your_token_here

# Login to both agents (manual auth, one-time)
./go.sh login

# Start both agents side-by-side
./go.sh start

# After 30 minutes, verify it works:
./go.sh doctor
```

**For detailed instructions**, see [SETUP.md](SETUP.md).

---

## 📂 Repository Structure

```
.
├── threads_autopilot/             # Threads lead generation agent (PRIMARY)
│   ├── autopilot.py              # Main agent + LLM logic
│   ├── config.json               # Configuration
│   ├── persona.md                # Kirill's persona (about3.md)
│   ├── chrome_profile/           # Persistent browser session
│   └── state.json                # Agent state (seen posts, stats)
│
├── go.sh                         # Unified launcher
├── .env.example                  # Environment variables template
├── SETUP.md                      # Complete setup guide
├── PREFLIGHT.md                  # 5-minute pre-run checklist
└── README.md                     # This file

X Agent (separate repo):
../X-ACTIONS-AGENT/
  ├── src/agents/                 # X agent code
  ├── data/agent-config.json     # X configuration
  ├── data/session.json           # X browser session
  └── logs/agent.log              # X execution log
```

---

## 🏗️ Architecture

### Multi-Repo Design
- **Threads Agent** (this repo): Full lead generation workflow
- **X Agent** (sibling repo): Twitter automation
- **Launcher** (`go.sh`): Runs both in tmux side-by-side

Both agents are independent with separate:
- Configurations (config.json vs. agent-config.json)
- Sessions (chrome_profile/ vs. data/session.json)
- LLM backends (GitHub Models vs. OpenRouter)
- Logging (autopilot.log vs. logs/agent.log)

### Supported Networks
✅ **Threads.net** (Lead generation + engagement)  
✅ **X/Twitter** (Thought leadership + engagement)  
❌ Facebook, Instagram, TikTok (Not currently supported)

### LLM Backend (Intelligent Fallback Chain)

| Priority | Service | Cost | Requires |
|----------|---------|------|----------|
| 1️⃣ **GitHub Models** | Free Claude API | $0/month | GitHub token |
| 2️⃣ OpenRouter | Anthropic via proxy | ~$0.003/reply | OpenRouter key |
| 3️⃣ Ollama Local | Local llama3.1 | $0 | ollama serve running |
| 4️⃣ Regex Fallback | Pattern-based rules | $0 | None (offline) |

---

## ⚙️ Configuration

### Threads Agent (`threads_autopilot/config.json`)

```json
{
  "profile": "safe",                  // or "balanced", "aggressive"
  "llm_provider": "github_models",    // Primary LLM
  "github_token": "ghp_...",          // Your GitHub token
  "auto_send_min_score": 0.82,        // Only auto-send if confidence ≥ 82%
  "draft_min_score": 0.7,             // Draft if confidence 70-82%
  "keywords": [22 targeted keywords],
  "action_mix": {                     // Behavioral mix
    "reply": 0.58,  "like": 0.22,
    "follow": 0.12, "browse": 0.08
  }
}
```

### X Agent (`../X-ACTIONS-AGENT/data/agent-config.json`)

```json
{
  "niche": {
    "name": "AI Products, Content Systems & Telegram Commerce",
    "searchTerms": [14 niche keywords]
  },
  "persona": { /* Kirill's expertise, opinions, example tweets */ },
  "llm": {
    "provider": "openrouter",
    "models": { /* fast, mid, smart tiers */ }
  }
}
```

---

## 🔧 Commands Reference

```bash
./go.sh doctor              # Health check (before everything)
./go.sh init                # Install dependencies (one-time)
./go.sh login [threads|x]   # Authenticate agents
./go.sh start               # Launch both side-by-side
./go.sh attach              # Reattach closed window
./go.sh stop                # Stop gracefully
./go.sh restart             # Restart both
./go.sh status              # Show status + logs
```

---

## 📊 Expected Performance

### Threads Agent (Safe Profile)
- **Posts Found:** 15-30/day per keyword
- **Replies Sent:** 2-5/day
- **Engagement Rate:** 2-5%
- **False Positives:** ~5-10%

### X Agent
- **Tweets Posted:** 3-8/day
- **Engagement:** 5-15 likes per tweet
- **New Followers:** 10-30/month

---

## 🛠️ Troubleshooting

### "GitHub token not found"
```bash
export GITHUB_TOKEN=ghp_your_token
./go.sh start
```

### "Threads browser won't authenticate"
```bash
./go.sh login threads  # Opens browser for manual login
```

### "X agent not tweeting"
```bash
tail -20 ../X-ACTIONS-AGENT/logs/agent.log
# Check for: OpenRouter key, session expired, no matching topics
```

See [PREFLIGHT.md](PREFLIGHT.md) for 5-minute checklist before running overnight.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [SETUP.md](SETUP.md) | Complete setup (clone → init → login → start) |
| [PREFLIGHT.md](PREFLIGHT.md) | 5-minute pre-run checklist |
| [.env.example](.env.example) | Environment variables |

---

## 🔐 Security

- ✅ Secrets in `.gitignore` (config.json, .env, sessions)
- ✅ GitHub token via env var or config (user chooses)
- ✅ Browser profiles persist locally (no cloud)
- ✅ No external tracking or logging

---

## 📈 Next Steps

### First Time (Today)
1. `./go.sh doctor` → check readiness
2. `./go.sh init` → install deps
3. `export GITHUB_TOKEN=ghp_...` → set token
4. `./go.sh login` → authenticate both agents
5. `./go.sh start` → run for 30 min to verify

### Optimization (This Week)
1. Review logs (autopilot.log, agent.log)
2. Adjust keywords if needed
3. Tweak scoring thresholds
4. Change profile: safe → balanced → aggressive

### Production (Next Week)
1. Run `./go.sh start` overnight
2. Monitor logs every 2-3 hours first time
3. Safe to run 24/7 once confident

---

## 📞 Help

```bash
# Real-time logs
tail -50 threads_autopilot/autopilot.log
tail -50 ../X-ACTIONS-AGENT/logs/agent.log

# Both in one view
./go.sh attach  # then: Ctrl-B → arrow keys to switch panes
```

---

**Built with:** Python (Playwright, AsyncIO) | Node.js (Puppeteer) | AI (Claude 3.5 Sonnet)  
**License:** MIT  
**Status:** ✅ Production Ready
