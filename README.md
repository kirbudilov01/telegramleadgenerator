<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2AABEE,100:1a7bbf&height=200&section=header&text=Telegram%20Lead%20Generator&fontSize=38&fontColor=ffffff&fontAlignY=40&desc=Find%20your%20hottest%20leads%20across%20thousands%20of%20chats%20in%20minutes&descAlignY=60&descSize=15" width="100%"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Telegram](https://img.shields.io/badge/Telegram-MTProto-2AABEE?style=for-the-badge&logo=telegram&logoColor=white)](https://my.telegram.org)
[![macOS](https://img.shields.io/badge/macOS-12+-000000?style=for-the-badge&logo=apple&logoColor=white)](https://apple.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![FABRICBOT](https://img.shields.io/badge/FABRICBOT-ECOSYSTEM-FF6B35?style=for-the-badge)](https://github.com/kirbudilov01)
[![One-Click Start](https://img.shields.io/badge/One--Click-START.command-2ea44f?style=for-the-badge)](#-one-click-start-for-beginners)

<br/>

**Parses your full Telegram history → PostgreSQL → Priority-ranked CSV reports on your Desktop**

[Quick Start](#-quick-start-one-command) · [Before You Begin](#-before-you-begin) · [How It Works](#%EF%B8%8F-how-it-works) · [CSV Format](#-csv-output-format)

<br/>

> Part of the **[FABRICBOT ECOSYSTEM](https://github.com/kirbudilov01)** — open-source tools for sales automation & lead generation

</div>

---

## ✨ What It Does

| | |
|---|---|
| 📥 | Downloads **full message history** from all your personal chats (5000+ dialogs) |
| 🤖 | Automatically filters out **bots, channels, and spam** |
| 🔍 | Scans for **keywords**: AI, marketing, development, YouTube, pricing, etc. |
| 📊 | Assigns **priority scores 1–5** based on activity and conversation topics |
| 🖥️ | Saves **analysis CSVs + full raw history CSV** to your Desktop |

---

## ⚡ Quick Start (one command)

> **Prerequisites:** macOS 12+, internet connection, Telegram account
> The installer will guide you through everything else — including where to get API keys.

```bash
git clone https://github.com/kirbudilov01/telegramleadgenerator.git && cd telegramleadgenerator && bash setup.sh
```

Then run the collector:

```bash
bash run.sh
```

That's it. CSV reports will appear on your Desktop automatically.

---

## 🟢 One-Click Start (for beginners)

After cloning the repository, you can run everything with one launcher:

```bash
chmod +x start.command && ./start.command
```

What this launcher does:
- Runs setup automatically if this is your first run
- Opens an interactive menu with simple button-like choices
- Starts collection + analysis
- Saves result files to Desktop, including full raw history CSV
- Optionally opens local AI chat (Ollama)

---

## 📋 Before You Begin

Before running setup, you'll need **3 things** from Telegram:

### 1. Get your API credentials (free, takes 2 min)

1. Open **[my.telegram.org](https://my.telegram.org)** in your browser
2. Sign in with your Telegram phone number
3. Click **"API development tools"**
4. Create a new app — any name works (e.g. `MyApp`)
5. Copy **`App api_id`** and **`App api_hash`**

> The setup script will ask for these values interactively — no need to edit any files manually.

### 2. Your phone number

Format: `+19991234567` (country code + number, no spaces)

### 3. Access to your Telegram account

During setup, Telegram will send you a confirmation code.
Open your Telegram app and enter the code when prompted.

---

## 🚀 Step-by-Step Setup

```bash
# Step 1 — Clone the repo
git clone https://github.com/kirbudilov01/telegramleadgenerator.git
cd telegramleadgenerator

# Step 2 — Run the installer (installs everything automatically)
bash setup.sh
```

The installer will walk you through each step in the terminal:

```
[1/8] Homebrew          → installs if missing
[2/8] Python 3.11       → installs if missing
[3/8] PostgreSQL 18     → installs and starts
[4/8] Dependencies      → pip install -r requirements.txt
[5/8] Database          → creates telegram_export
[6/8] API_ID            → shows where to get it, asks in terminal
[7/8] API_HASH + Phone  → same
[8/8] Telegram auth     → sends code to your phone
```

```bash
# Step 3 — Collect and analyze
bash run.sh
```

The terminal will ask two questions:

```
Choose collection profile:
     1) Smart Filter (recommended)  personal only, no bots/channels
     2) Custom selection            choose groups/bots/channels yourself

Run mode?
  1) Full collection          (first time)
  2) New messages only        (already collected)

Custom mode then asks:
     - Include group chats? [y/N]
     - Include bot dialogs? [y/N]
     - Include channels? [y/N]
```

After completion, a folder `telegram_analysis_DATE/` appears on your Desktop.

---

## 📂 Output Files

| File | Contents |
|------|---------|
| `top100_priority.csv` | ⭐ Top 100 by importance — **start here** |
| `top100_by_activity.csv` | Top 100 by message count |
| `all_chats.csv` | All analyzed chats |
| `full_history_raw.csv` | Full raw CSV of the entire collected history |

---

## 🤖 Optional Local AI Chat

After each run, you can open a local AI chat over your generated CSV results.

The script asks:

```
Launch local AI chat now? [y/N]

Choose AI provider:
     1) Ollama (local)
     2) OpenAI API
     3) Anthropic Claude API
```

Requirements:
- Install Ollama: https://ollama.com
- Pull model once: `ollama pull llama3.1`
- For OpenAI: set `OPENAI_API_KEY`
- For Claude: set `ANTHROPIC_API_KEY`

Default models:
- Ollama: `llama3.1`
- OpenAI: `gpt-4o-mini`
- Anthropic: `claude-3-5-sonnet-latest`

Then you can type prompts like:
- "Show the top 10 warm leads in fintech"
- "Which contacts discussed AI automation budgets?"
- "Who should I follow up with this week and why?"

---

## ⚙️ How It Works

```
Telegram API
     │
     ▼
Telethon (MTProto)
     │  fetches full history of all dialogs
     ▼
PostgreSQL
     │  stores chats + messages locally
     ▼
Analyzer
     │  filters spam / bots / channels
     │  keyword matching
     │  priority scoring
     ▼
CSV on Desktop
```

**Priority scoring algorithm:**
- `priority = 5` — 200+ messages + 3+ keywords matched → **hot lead**
- `priority = 3` — 50+ messages or 3+ keywords → **warm**
- `priority = 1` — everything else

---

## 📋 CSV Output Format

| Column | Description |
|--------|---------|
| `chat_name` | Username or chat title |
| `chat_type` | `personal` / `group` |
| `message_count` | Total messages in the dialog |
| `priority` | 5 = hot, 3 = warm, 1 = cold |
| `intent` | `interest` = discussed tasks/deals; `neutral` = casual chat |
| `matched_keywords` | Keywords found in conversation |
| `last_messages` | Last 5 messages (quick context preview) |

---

## 🔧 Advanced

**Collect groups too:**
```bash
python main.py load --groups
```

**Re-run analysis without re-collecting:**
```bash
python analyze.py
```

**Check database stats:**
```bash
python main.py stats
```

---

## 📦 Requirements

- **macOS 12+** (Apple Silicon & Intel)
- Telegram account
- API credentials from [my.telegram.org](https://my.telegram.org) *(free)*

---

## 🔒 Privacy & Security

- `.env` and `*.session` files are in `.gitignore` — **never committed to git**
- All data is stored **locally on your machine only**
- Nothing is sent to third-party servers

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first.

---

## 🌐 FABRICBOT Links

- YouTube: https://www.youtube.com/@fabricbotecosystem
- X (Twitter): https://x.com/kirillfbc
- Community: https://kirbudilov01.github.io/reposearchengine/

---

<div align="center">

**Built with ❤️ as part of the [FABRICBOT ECOSYSTEM](https://github.com/kirbudilov01)**

*Open-source tools for sales automation, lead generation & Telegram data analysis*

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a7bbf,100:2AABEE&height=100&section=footer" width="100%"/>

</div>
