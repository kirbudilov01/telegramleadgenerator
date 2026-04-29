<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2AABEE,100:1a7bbf&height=180&section=header&text=Telegram%20Lead%20Generator&fontSize=36&fontColor=ffffff&fontAlignY=38&desc=Найди%20горячие%20контакты%20среди%20тысяч%20чатов&descAlignY=60&descSize=16" width="100%"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Telegram](https://img.shields.io/badge/Telegram-MTProto-2AABEE?style=for-the-badge&logo=telegram&logoColor=white)](https://my.telegram.org)
[![macOS](https://img.shields.io/badge/macOS-12+-000000?style=for-the-badge&logo=apple&logoColor=white)](https://apple.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<br/>

**Парсит всю историю Telegram → PostgreSQL → CSV с приоритетами на рабочем столе**

[Быстрый старт](#-быстрый-старт) · [Как это работает](#-как-это-работает) · [Структура данных](#-структура-csv)

</div>

---

## ✨ Что делает

| | |
|---|---|
| 📥 | Скачивает **всю историю** личных чатов (5000+ диалогов) |
| 🤖 | Автоматически удаляет **ботов, каналы, спам** |
| 🔍 | Ищет **ключевые слова**: AI, маркетинг, разработка, YouTube и др. |
| 📊 | Расставляет **приоритеты 1–5** по активности и теме диалога |
| 🖥️ | Кладёт **3 CSV-файла на Рабочий стол** — готовы к работе |

---

## 🚀 Быстрый старт

### Шаг 1 — Клонируй репозиторий

```bash
git clone https://github.com/kirbudilov/telegramleadgenerator.git
cd telegramleadgenerator
```

### Шаг 2 — Запусти установку

```bash
bash setup.sh
```

Скрипт сам спросит всё необходимое прямо в терминале:

```
[1/8] Homebrew          → устанавливает если нет
[2/8] Python 3.11       → устанавливает если нет
[3/8] PostgreSQL        → устанавливает и запускает
[4/8] Зависимости       → pip install -r requirements.txt
[5/8] База данных       → создаёт telegram_export
[6/8] API_ID            → подскажет где взять, спросит в терминале
[7/8] API_HASH + Phone  → то же самое
[8/8] Telegram auth     → пришлёт код на телефон
```

> **Где взять API ключи:**
> 1. Открой [my.telegram.org](https://my.telegram.org) → войди по номеру телефона
> 2. Нажми **API development tools**
> 3. Создай приложение (название — любое)
> 4. Скопируй `App api_id` и `App api_hash` — вставишь в терминал по запросу

### Шаг 3 — Запусти сбор данных

```bash
bash run.sh
```

После завершения на **Рабочем столе** появится папка `telegram_analysis_ДАТА/`:

| Файл | Содержание |
|------|-----------|
| `top100_priority.csv` | ⭐ Топ-100 по важности — начинай отсюда |
| `top100_by_messages.csv` | Топ-100 по активности |
| `analysis_all.csv` | Все проанализированные чаты |

---

## ⚙️ Как это работает

```
Telegram API
     │
     ▼
Telethon (MTProto)
     │  скачивает историю всех диалогов
     ▼
PostgreSQL
     │  chats + messages
     ▼
Анализатор
     │  фильтрация спама/ботов
     │  поиск ключевых слов
     │  scoring приоритетов
     ▼
CSV на Рабочем столе
```

**Алгоритм приоритетов:**
- `priority = 5` — 200+ сообщений + 3+ ключевых слова → **горячий контакт**
- `priority = 3` — 50+ сообщений или 3+ ключевых слова → **тёплый**
- `priority = 1` — всё остальное

---

## 📋 Структура CSV

| Колонка | Описание |
|---------|---------|
| `chat_name` | Username или название чата |
| `chat_type` | `personal` / `group` |
| `message_count` | Всего сообщений в диалоге |
| `priority` | 5 = горячий, 3 = средний, 1 = слабый |
| `intent` | `interest` — обсуждали задачи; `neutral` — просто общение |
| `matched_keywords` | Найденные ключевые слова |
| `last_messages` | Последние 5 сообщений (для быстрого контекста) |

---

## 🔧 Дополнительно

**Включить группы** (по умолчанию только личные чаты):
```bash
python main.py load --groups
```

**Только анализ без повторного сбора:**
```bash
python analyze.py
```

**Статистика базы:**
```bash
python main.py stats
```

---

## 📋 Требования

- **macOS 12+** (Apple Silicon и Intel)
- Telegram аккаунт
- API ключи с [my.telegram.org](https://my.telegram.org) (бесплатно)

---

## 🔒 Безопасность

- `.env` и `*.session` **не попадают в git** (защищены `.gitignore`)
- Все данные хранятся **только локально** на твоём компьютере
- Никакие данные не передаются на сторонние серверы

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:1a7bbf,100:2AABEE&height=100&section=footer" width="100%"/>

</div>


## Features

- **Full History Export**: Load all messages from personal 1-on-1 chats
- **Real-time Sync**: Continuously sync new messages as they arrive
- **Database Storage**: PostgreSQL with SQLAlchemy ORM
- **Metadata Extraction**: Message text, timestamps, media references (file IDs)
- **Export Formats**: JSON and CSV export support
- **Rate Limiting**: Automatic rate limiting to avoid Telegram flood control
- **Resume Capable**: Save progress and resume interrupted exports

## Prerequisites

1. **PostgreSQL 14+** - Running locally or remotely
2. **Python 3.10+**
3. **Telegram Account** with API credentials from https://my.telegram.org

## Setup

### 1. Clone and Install Dependencies

```bash
cd telegram-export
pip install -r requirements.txt
```

### 2. Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Sign in with your account
3. Go to "API development tools"
4. Create an app and note your `API_ID` and `API_HASH`

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
API_ID=your_api_id
API_HASH=your_api_hash
TELEGRAM_PHONE=+your_phone_number
DATABASE_URL=postgresql://user:password@localhost:5432/telegram_export
```

### 4. Create PostgreSQL Database

```bash
createdb telegram_export
```

## Usage

### Initialize Database Schema

```bash
python main.py init-db
```

### Load All Messages (First Run)

This will enumerate all your personal dialogs and load their complete message history into the database. Depending on the number of dialogs and messages, this may take a few hours.

```bash
python main.py load
```

**First time running**: You'll be prompted to enter a verification code sent to your Telegram account.

### Real-time Synchronization

After the initial load, start real-time synchronization to continuously sync new messages:

```bash
python main.py sync
```

This will keep running in the background. Press `Ctrl+C` to stop.

### Export Messages

Export your messages to JSON or CSV:

```bash
# Export to JSON
python main.py export json

# Export to CSV
python main.py export csv
```

Files are saved in `./exports/` directory.

### View Statistics

```bash
python main.py stats
```

## Project Structure

```
telegram-export/
├── config.py              # Configuration and settings
├── main.py                # CLI entry point
├── export.py              # Export functionality (JSON/CSV)
├── db/
│   ├── models.py         # SQLAlchemy ORM models
│   ├── session.py        # Database session management
│   └── __init__.py
├── parser/
│   ├── client.py         # Telethon client manager
│   ├── loader.py         # Message history loader
│   ├── syncer.py         # Real-time message syncer
│   ├── utils.py          # Helper utilities
│   └── __init__.py
├── requirements.txt
├── .env.example
└── README.md
```

## Database Schema

### accounts
- `telegram_id`: Your Telegram user ID
- `phone_number`: Your account phone
- `username`: Telegram username
- `created_at`: Account creation timestamp
- `last_synced`: Last synchronization time

### contacts
- `telegram_id`: Contact's Telegram ID
- `username`: Contact's username
- `first_name`: Contact's first name
- `phone_number`: Contact's phone (if available)

### chats
- `chat_id`: Telegram chat ID
- `contact_username`: Linked contact
- `last_message_id`: Last loaded message ID
- `last_synced`: Last sync timestamp

### messages
- `message_id`: Telegram message ID
- `text`: Message text content
- `timestamp`: Message date/time
- `sender_id`: Who sent the message
- `media_type`: Type of media (photo, document, video, etc.)
- `media_file_id`: Telegram file ID for media
- `is_edited`: Whether message was edited
- `is_forwarded`: Whether message is forwarded
- `reply_to_msg_id`: ID of message being replied to

## Notes

- **Media Files**: Only metadata (file IDs) is stored, not actual media files
- **Groups/Channels**: Only personal 1-on-1 chats are exported, groups and channels are skipped
- **Rate Limiting**: Automatic rate limiting prevents Telegram flood control
- **Resume**: If export is interrupted, it can resume from the last checkpoint
- **Real-time Sync**: The syncer listens for new messages and automatically stores them

## Performance Tips

- Start with a small test account first to verify setup
- For large histories (100k+ messages), initial load may take 2-8 hours
- Consider running the loader during off-peak hours
- Real-time syncer can run continuously with minimal resource usage

## Troubleshooting

**"Flood wait" errors**: Telegram is rate limiting. The script will automatically backoff and retry.

**Session file errors**: Delete `telegram_session.session` and re-authenticate.

**Database connection errors**: Verify PostgreSQL is running and connection string is correct.

**Media not showing**: Media file IDs are stored but actual files aren't downloaded. Use the file_ids to fetch media as needed.

## License

Private use for personal Telegram data export.
