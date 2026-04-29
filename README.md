# Telegram Chat Analyzer

Собирает все личные переписки (и опционально группы) из Telegram в базу данных и формирует приоритизированные CSV-отчёты — чтобы за 5 минут найти горячие контакты среди тысяч чатов.

**Что делает:**
- Парсит всю историю личных чатов (и групп при флаге `--groups`)
- Удаляет ботов, каналы, спам, рекламные рассылки
- Ищет ключевые слова (AI, маркетинг, разработка, YouTube и др.)
- Расставляет приоритеты и кладёт 3 CSV-файла на рабочий стол

---

## Быстрый старт (macOS)

### 1. Установи всё одной командой

```bash
git clone https://github.com/YOUR_USERNAME/telegram-chat-analyzer.git
cd telegram-chat-analyzer
bash setup.sh
```

Скрипт автоматически установит:
- Homebrew (если нет)
- Python 3.11
- PostgreSQL 18
- Все Python-зависимости
- Создаст базу данных и авторизует Telegram-сессию

> При запросе введи код подтверждения из Telegram.

### 2. Получи Telegram API ключи

1. Зайди на [https://my.telegram.org](https://my.telegram.org)
2. Войди в свой аккаунт
3. Открой **API development tools**
4. Создай приложение — скопируй `API_ID` и `API_HASH`
5. Вставь в файл `.env`:

```
API_ID=1234567
API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+79991234567
DATABASE_URL=postgresql://localhost:5432/telegram_export
```

### 3. Запусти сбор и анализ

```bash
bash run.sh
```

После завершения на рабочем столе появится папка `telegram_analysis_ДАТА/` с тремя файлами:

| Файл | Содержание |
|------|-----------|
| `top100_priority.csv` | Топ-100 чатов по важности (с этого начинать) |
| `top100_by_activity.csv` | Топ-100 по числу сообщений |
| `all_chats.csv` | Все проанализированные чаты |

---

## Включить группы

По умолчанию собираются только личные чаты. Чтобы добавить группы:

```bash
# В run.sh замени строку:
python -u main.py load
# На:
python -u main.py load --groups
```

---

## Структура CSV

| Колонка | Описание |
|---------|---------|
| `chat_name` | username или название |
| `chat_type` | `personal` / `group` |
| `message_count` | Всего сообщений |
| `priority` | 5 = горячий, 3 = средний, 1 = слабый |
| `intent` | `interest` = обсуждали задачи, `neutral` = общение |
| `matched_keywords` | Найденные ключевые слова |
| `last_messages` | Последние 5 сообщений |

---

## Требования

- macOS 12+ (для других ОС нужна ручная установка PostgreSQL)
- Telegram аккаунт с API ключами

---

## Безопасность

- `.env` и `*.session` файлы **не попадают в git** (в `.gitignore`)
- Данные хранятся только локально на твоём компьютере
- Никакие данные не отправляются на сторонние серверы


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
