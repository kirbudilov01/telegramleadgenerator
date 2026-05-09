"""
Threads keyword monitor → пересылает Мише в Telegram новые посты по ключевикам.

Первый запуск (сохранить сессию — один раз):
    python threads_monitor.py --login

Обычный запуск:
    python threads_monitor.py                         # дефолтные ключевики, бесконечный режим
    python threads_monitor.py --once                  # один прогон и выход
    python threads_monitor.py --keywords "ассистент,помощник,ищу va"
    python threads_monitor.py --target @username      # кому слать (дефолт: @Mikekosarev)
    python threads_monitor.py --interval 120          # пауза между прогонами в секундах

Как работает:
    1. При --login открывает видимый браузер для ручного входа в Threads → сохраняет сессию.
    2. Последующие запуски используют сохранённую сессию (headless).
    3. Playwright scrapes Threads Search по каждому ключевику.
    4. Новые посты (не виденные ранее) отправляются в Telegram получателю.
    5. seen_posts.json хранит уже отправленные ID чтобы не дублировать.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright
from telethon import TelegramClient
from config import settings

SEEN_FILE = Path(__file__).parent / "seen_threads_posts.json"
SESSION_FILE = Path(__file__).parent / "threads_session.json"

DEFAULT_KEYWORDS = [
    "ищу ассистента",
    "нужен помощник",
    "ищу va",
    "ищу личного ассистента",
    "нужен ассистент",
    "ищу сотрудника",
    "hiring assistant",
]

DEFAULT_TARGET = "mikekosarev"


def load_seen() -> set:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return set()


def save_seen(seen: set):
    SEEN_FILE.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=2), encoding="utf-8")


def make_post_id(url: str, text: str) -> str:
    """Stable dedup key from URL or first 120 chars of text."""
    if url and "threads.net" in url:
        # extract post path e.g. /@user/post/ABC123
        m = re.search(r"threads\.net(/[^\?#]+)", url)
        if m:
            return m.group(1)
    return text[:120].strip()


async def login_and_save_session():
    """Open a visible browser, let the user log in manually, then save the session."""
    print("[LOGIN] Открываю браузер — войди в Threads вручную, потом нажми Enter в терминале.")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.threads.net/login", wait_until="domcontentloaded")
        print("[LOGIN] Залогинься в браузере, затем нажми Enter здесь...")
        input()
        await context.storage_state(path=str(SESSION_FILE))
        print(f"[LOGIN] Сессия сохранена в {SESSION_FILE}")
        await browser.close()


async def make_browser_context(pw):
    """Create browser context — with saved session if available, otherwise plain."""
    browser = await pw.chromium.launch(headless=True)
    if SESSION_FILE.exists():
        context = await browser.new_context(
            storage_state=str(SESSION_FILE),
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
    else:
        print("[WARN] Сессия не найдена — поиск может не работать. Запусти: python threads_monitor.py --login")
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
    return browser, context


async def scrape_keyword(page, keyword: str) -> list[dict]:
    """Return list of {url, text, author} for given keyword search."""
    results = []
    encoded = quote(keyword)
    url = f"https://www.threads.net/search?q={encoded}&serp_type=default"

    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # Extract posts
        posts = await page.evaluate("""() => {
            const results = [];
            // Threads renders posts in article or div with role=article
            const articles = document.querySelectorAll('article, [role="article"]');
            for (const art of articles) {
                const textEl = art.querySelector('[dir="auto"]');
                const text = textEl ? textEl.innerText.trim() : '';
                if (!text) continue;
                const linkEl = art.querySelector('a[href*="/post/"]');
                const url = linkEl ? linkEl.href : '';
                const authorEl = art.querySelector('a[href*="/@"]');
                const author = authorEl ? authorEl.href : '';
                results.push({ text, url, author });
            }
            return results;
        }""")

        for p in posts:
            if p.get("text"):
                results.append(p)
    except Exception as e:
        print(f"[WARN] scrape failed for '{keyword}': {e}")

    return results


def format_message(keyword: str, post: dict) -> str:
    author = post.get("author", "").replace("https://www.threads.net/@", "@").split("?")[0] or "неизвестен"
    url = post.get("url", "")
    text = post.get("text", "")[:600]
    return (
        f"🔍 Ключевик: {keyword}\n"
        f"👤 Автор: {author}\n\n"
        f"{text}\n\n"
        f"{'🔗 ' + url if url else ''}"
    ).strip()


async def run_once(keywords: list[str], target: str, tg_client) -> int:
    seen = load_seen()
    new_count = 0

    async with async_playwright() as pw:
        browser, context = await make_browser_context(pw)
        page = await context.new_page()

        for kw in keywords:
            print(f"[INFO] Searching: {kw}")
            posts = await scrape_keyword(page, kw)
            print(f"[INFO]   found {len(posts)} posts")

            for post in posts:
                pid = make_post_id(post.get("url", ""), post.get("text", ""))
                if pid in seen:
                    continue

                msg = format_message(kw, post)
                try:
                    entity = await tg_client.get_entity(target)
                    await tg_client.send_message(entity, msg)
                    seen.add(pid)
                    new_count += 1
                    print(f"[SENT] {pid[:60]}")
                    await asyncio.sleep(1.5)  # avoid flood
                except Exception as e:
                    print(f"[ERROR] send failed: {e}")

            await asyncio.sleep(2)

        await browser.close()

    save_seen(seen)
    print(f"[INFO] Done. Sent {new_count} new posts.")
    return new_count


async def main():
    parser = argparse.ArgumentParser(description="Threads keyword monitor → Telegram")
    parser.add_argument("--login", action="store_true", help="Open browser for manual Threads login, save session")
    parser.add_argument("--keywords", default="", help="Comma-separated keywords")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="Telegram username to notify")
    parser.add_argument("--interval", type=int, default=180, help="Seconds between runs (default 180)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    keywords = (
        [k.strip() for k in args.keywords.split(",") if k.strip()]
        if args.keywords
        else DEFAULT_KEYWORDS
    )
    target = args.target.lstrip("@")

    if args.login:
        await login_and_save_session()
        return

    print(f"[INFO] Keywords: {keywords}")
    print(f"[INFO] Target: @{target}")
    print(f"[INFO] Interval: {args.interval}s")

    tg_client = TelegramClient("telegram_session", settings.api_id, settings.api_hash)
    await tg_client.connect()
    if not await tg_client.is_user_authorized():
        print("[ERROR] Telegram session not authorized. Run: python auth.py")
        sys.exit(1)

    try:
        if args.once:
            await run_once(keywords, target, tg_client)
        else:
            while True:
                await run_once(keywords, target, tg_client)
                print(f"[INFO] Sleeping {args.interval}s...")
                await asyncio.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[INFO] Stopped.")
    finally:
        await tg_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
