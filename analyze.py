"""
Chat Analyzer — скрипт для сегментации 4700+ чатов в 50–200 релевантных.
Запуск:  python analyze.py
Результат: exports/analysis_all.csv, exports/top100_by_messages.csv, exports/top100_by_priority.csv
"""

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import psycopg2
from config import settings

# ─── Настройки ───────────────────────────────────────────────────────────────

LAST_MESSAGES_N = 15        # сколько последних сообщений брать на анализ
MIN_MESSAGES    = 3         # минимум сообщений, чтобы чат попал в анализ

# Ключевые слова (регистр не важен)
KEYWORDS = [
    # YouTube / контент
    "youtube", "ютуб", "канал", "видео", "контент", "просмотры", "ролик",
    "шортс", "shorts", "reels",
    # AI / автоматизация
    "ai", "ии", "gpt", "chatgpt", "агент", "automation", "автоматизация",
    # Маркетинг
    "маркетинг", "marketing", "продвижение", "реклама", "трафик", "лиды", "воронка",
    # Разработка
    "разработка", "dev", "разработчик", "app", "приложение", "сайт", "web", "saas",
    # Действия / запуск
    "сделать", "создать", "собрать", "запуск", "запускать",
    # Деньги / сроки
    "стоимость", "цена", "сколько", "бюджет", "сроки", "дедлайн",
]

# Признаки спама/рекламы в тексте
SPAM_PHRASES = [
    "предлагаем вам", "рассылка", "подпишитесь", "скидка", "акция", "купите",
    "заработок без вложений", "продвижение вашего бизнеса", "мы можем вам предложить",
]

URL_RE = re.compile(r'https?://\S+|t\.me/\S+', re.I)

OUTPUT_DIR = Path("exports")
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── Подключение к БД ─────────────────────────────────────────────────────────

def get_conn():
    """Прямое подключение psycopg2 (DATABASE_URL из .env)"""
    url = settings.database_url
    # postgresql://user:pass@host:port/db  →  psycopg2 dsn
    # Простейший парсинг без зависимостей
    try:
        from urllib.parse import urlparse
        u = urlparse(url)
        return psycopg2.connect(
            host=u.hostname or "localhost",
            port=u.port or 5432,
            dbname=u.path.lstrip("/"),
            user=u.username or "",
            password=u.password or "",
        )
    except Exception as e:
        print(f"[ERR] DB connect failed: {e}")
        sys.exit(1)

# ─── Вспомогательные функции ──────────────────────────────────────────────────

def is_spam(texts: list[str], my_telegram_id: int, sender_ids: list[int]) -> bool:
    """
    True если чат выглядит как входящая реклама.
    Критерии:
    - текст содержит спам-фразу, ИЛИ
    - 2+ ссылки хотя бы в одном сообщении, ИЛИ
    - 80%+ сообщений пишет собеседник (не я)
    """
    combined = " ".join(t for t in texts if t).lower()
    for phrase in SPAM_PHRASES:
        if phrase in combined:
            return True

    for t in texts:
        if t and len(URL_RE.findall(t)) >= 2:
            return True

    if sender_ids and my_telegram_id:
        other_count = sum(1 for sid in sender_ids if sid != my_telegram_id)
        ratio = other_count / len(sender_ids)
        if ratio >= 0.8 and any(p in combined for p in ["предлагаем", "предложение", "услуг"]):
            return True

    return False


def find_keywords(texts: list[str]) -> list[str]:
    combined = " ".join(t for t in texts if t).lower()
    found = []
    for kw in KEYWORDS:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, combined, re.I):
            found.append(kw)
    return found


def calc_priority(msg_count: int, keywords: list[str]) -> int:
    """
    5 = много сообщений + ключевые слова
    3 = среднее
    1 = слабый сигнал
    """
    kw_score = len(keywords)

    if msg_count >= 200 and kw_score >= 3:
        return 5
    if msg_count >= 50 and kw_score >= 2:
        return 5
    if msg_count >= 50 or kw_score >= 3:
        return 3
    if msg_count >= 10 or kw_score >= 1:
        return 3
    return 1


def calc_intent(keywords: list[str], texts: list[str]) -> str:
    combined = " ".join(t for t in texts if t).lower()
    # Признаки обсуждения задач/услуг
    work_signals = [
        "сделать", "создать", "помоги", "нужен", "нужна", "хочу", "можешь",
        "сколько", "стоимость", "цена", "бюджет", "сроки", "предложи",
        "разработать", "запуск", "задача", "проект",
    ]
    work_hits = sum(1 for w in work_signals if w in combined)
    if keywords and work_hits >= 2:
        return "interest"
    return "neutral"


def volume_bucket(n: int) -> str:
    if n <= 10:
        return "3-10"
    if n <= 50:
        return "10-50"
    if n <= 200:
        return "50-200"
    return "200+"


def truncate(text: str, max_len: int = 120) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    return text[:max_len] + ("…" if len(text) > max_len else "")

# ─── Основная логика ──────────────────────────────────────────────────────────

def main():
    conn = get_conn()
    cur = conn.cursor()

    # Получаем telegram_id нашего аккаунта
    cur.execute("SELECT telegram_id FROM accounts LIMIT 1")
    row = cur.fetchone()
    my_telegram_id = row[0] if row else None

    print(f"[INFO] Account telegram_id: {my_telegram_id}")
    print("[INFO] Loading chats from DB...")

    # Все чаты с количеством сообщений
    # is_user=True → личный чат, is_user=False → группа
    cur.execute("""
        SELECT c.id, c.chat_id, c.contact_username,
               COUNT(m.id) AS msg_count,
               COALESCE(c.is_user, TRUE) AS is_personal
        FROM chats c
        LEFT JOIN messages m ON m.chat_id = c.id
        GROUP BY c.id, c.chat_id, c.contact_username, c.is_user
        HAVING COUNT(m.id) >= %s
        ORDER BY msg_count DESC
    """, (MIN_MESSAGES,))

    chats = cur.fetchall()
    print(f"[INFO] Chats with >= {MIN_MESSAGES} messages: {len(chats)}")

    results = []
    skipped_spam = 0
    skipped_bot = 0

    for i, (chat_pk, chat_id, username, msg_count, is_personal) in enumerate(chats):
        if i % 200 == 0:
            print(f"  [{i}/{len(chats)}] processing...", flush=True)

        uname = (username or "").lower()
        chat_type = "personal" if is_personal else "group"

        # Пропускаем боты по username
        if uname.endswith("bot") or uname.endswith("_bot"):
            skipped_bot += 1
            continue

        # Берём последние N сообщений
        cur.execute("""
            SELECT text, sender_id
            FROM messages
            WHERE chat_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (chat_pk, LAST_MESSAGES_N))
        rows = cur.fetchall()
        texts = [r[0] for r in rows]
        sender_ids = [r[1] for r in rows]

        # Спам-фильтр
        if is_spam(texts, my_telegram_id, sender_ids):
            skipped_spam += 1
            continue

        keywords = find_keywords(texts)
        priority = calc_priority(msg_count, keywords)
        intent = calc_intent(keywords, texts)
        bucket = volume_bucket(msg_count)

        # last_messages — последние 5 сообщений одной строкой
        last_preview = " | ".join(
            truncate(t) for t in reversed(texts[:5]) if t
        )

        results.append({
            "chat_id":          chat_id,
            "chat_name":        username or f"id:{chat_id}",
            "chat_type":        chat_type,
            "message_count":    msg_count,
            "volume_bucket":    bucket,
            "matched_keywords": ", ".join(keywords),
            "intent":           intent,
            "priority":         priority,
            "last_messages":    last_preview,
        })

    cur.close()
    conn.close()

    print(f"\n[INFO] Total results: {len(results)}")
    print(f"[INFO] Skipped spam:   {skipped_spam}")
    print(f"[INFO] Skipped bots:   {skipped_bot}")

    # ─── Экспорт CSV ─────────────────────────────────────────────────────────

    fieldnames = [
        "chat_name", "chat_id", "chat_type", "message_count", "volume_bucket",
        "matched_keywords", "priority", "intent", "last_messages",
    ]

    def write_csv(path: Path, rows: list[dict]):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: r[k] for k in fieldnames})
        print(f"[OUT] {path}  ({len(rows)} rows)")

    # Все результаты (по приоритету desc)
    all_sorted = sorted(results, key=lambda x: (-x["priority"], -x["message_count"]))
    write_csv(OUTPUT_DIR / "analysis_all.csv", all_sorted)

    # TOP 100 по message_count
    top_by_msg = sorted(results, key=lambda x: -x["message_count"])[:100]
    write_csv(OUTPUT_DIR / "top100_by_messages.csv", top_by_msg)

    # TOP 100 по priority
    top_by_prio = sorted(results, key=lambda x: (-x["priority"], -x["message_count"]))[:100]
    write_csv(OUTPUT_DIR / "top100_by_priority.csv", top_by_prio)

    # Сводка по бакетам
    print("\n── Сводка по объёму ──────────────────────────")
    bucket_counts = defaultdict(int)
    for r in results:
        bucket_counts[r["volume_bucket"]] += 1
    for b in ["3-10", "10-50", "50-200", "200+"]:
        print(f"  {b:8s}: {bucket_counts[b]} чатов")

    print("\n── Сводка по приоритету ──────────────────────")
    for p in [5, 3, 1]:
        n = sum(1 for r in results if r["priority"] == p)
        print(f"  priority={p}: {n} чатов")

    print(f"\n✓ Готово. Файлы в ./exports/")


if __name__ == "__main__":
    main()
