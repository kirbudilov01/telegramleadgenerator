import argparse
import asyncio
import json
import logging
import random
import re
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright, Page, BrowserContext

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
STATE_FILE = BASE_DIR / "state.json"
STORAGE_STATE_FILE = BASE_DIR / "threads_storage_state.json"
PERSONA_FILE = BASE_DIR / "persona.txt"
LOG_FILE = BASE_DIR / "autopilot.log"

PROFILE_PRESETS = {
    "safe": {
        "cycle_minutes": 30,
        "cycle_jitter_minutes": [2, 8],
        "max_replies_per_cycle": 1,
        "max_replies_per_day": 20,
        "reply_delay_seconds": [30, 120],
        "search_posts_per_keyword": 20,
        "llm_min_score": 0.78,
    },
    "balanced": {
        "cycle_minutes": 20,
        "cycle_jitter_minutes": [1, 6],
        "max_replies_per_cycle": 2,
        "max_replies_per_day": 40,
        "reply_delay_seconds": [20, 90],
        "search_posts_per_keyword": 30,
        "llm_min_score": 0.72,
    },
    "aggressive": {
        "cycle_minutes": 15,
        "cycle_jitter_minutes": [1, 4],
        "max_replies_per_cycle": 3,
        "max_replies_per_day": 60,
        "reply_delay_seconds": [15, 70],
        "search_posts_per_keyword": 40,
        "llm_min_score": 0.68,
    },
}


@dataclass
class CandidatePost:
    keyword: str
    post_url: str
    author_url: str
    author_handle: str
    text: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def setup_logging(verbose: bool) -> None:
    handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config() -> dict:
    cfg = read_json(CONFIG_FILE, None)
    if cfg is None:
        raise RuntimeError(
            f"Missing {CONFIG_FILE.name}. Copy config.example.json to config.json and fill values."
        )
    return cfg


def load_persona(path: Path) -> str:
    if not path.exists():
        return "You are a senior software engineer and product builder."
    return path.read_text(encoding="utf-8").strip()


def load_state() -> dict:
    state = read_json(
        STATE_FILE,
        {
            "seen_posts": [],
            "replied_posts": [],
            "daily_stats": {},
            "hourly_stats": {},
            "last_reply_ts": 0,
            "reply_history": [],
            "keyword_history": [],
            "liked_posts": [],
            "followed_authors": [],
        },
    )
    for key in ["seen_posts", "replied_posts", "reply_history", "keyword_history", "liked_posts", "followed_authors"]:
        if key not in state:
            state[key] = []
    if "daily_stats" not in state:
        state["daily_stats"] = {}
    if "hourly_stats" not in state:
        state["hourly_stats"] = {}
    if "last_reply_ts" not in state:
        state["last_reply_ts"] = 0
    return state


def save_state(state: dict) -> None:
    write_json(STATE_FILE, state)


def dedupe_keep_tail(items: list[str], max_items: int) -> list[str]:
    seen = set()
    result = []
    for item in reversed(items):
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return list(reversed(result))[-max_items:]


class OllamaClient:
    def __init__(self, host: str, model: str, timeout_seconds: int = 45):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def _chat(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2},
        }
        req = Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return raw.get("message", {}).get("content", "").strip()

    def classify(self, post_text: str, keyword: str) -> dict:
        prompt = f"""Classify if this post is a strong lead for AI/dev/automation services.
Return ONLY JSON: {{"relevant": bool, "score": 0-1, "reason": "short string"}}
Keyword: {keyword}\nPost:\n{post_text[:700]}"""
        try:
            out = self._chat(prompt)
        except Exception:
            return {"relevant": False, "score": 0.0, "reason": "ollama_unavailable"}
        m = re.search(r"\{.*\}", out, flags=re.DOTALL)
        if not m:
            return {"relevant": False, "score": 0.0, "reason": "llm_non_json"}
        try:
            data = json.loads(m.group(0))
            return {
                "relevant": bool(data.get("relevant", False)),
                "score": float(data.get("score", 0.0)),
                "reason": str(data.get("reason", ""))[:200],
            }
        except Exception:
            return {"relevant": False, "score": 0.0, "reason": "llm_parse_error"}

    def generate_keywords(self, base_keywords: list, persona: str, max_new: int) -> list:
        prompt = f"""Generate {max_new} Threads search keywords for lead generation. Return ONLY JSON array of strings.
Base: {json.dumps(base_keywords)}"""
        try:
            out = self._chat(prompt)
        except Exception:
            return []
        m = re.search(r"\[.*\]", out, flags=re.DOTALL)
        if not m:
            return []
        try:
            arr = json.loads(m.group(0))
            return [str(x).strip() for x in arr if isinstance(x, str) and str(x).strip()][:max_new]
        except Exception:
            return []

    def compose_reply(self, persona: str, post_text: str, author_handle: str, context_hint: str = "") -> str:
        prompt = f"""Write a short human Threads reply. Max 280 chars. No hashtags. Match post language.
Keep it specific, conversational, and non-promotional.

Context hint:
{context_hint}

Persona: {persona[:700]}
Author: {author_handle}
Post: {post_text[:700]}

Return only the reply."""
        try:
            out = self._chat(prompt)
        except Exception:
            return ""
        return re.sub(r"\s+", " ", out.strip().strip('"'))[:280]

    def _self_check_reply(self, reply_text: str, post_text: str) -> tuple:
        return True, 0.75


class OpenRouterClient:
    """OpenAI-compatible client. Works with OpenRouter, GitHub Models, or any compatible endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        persona: str = "",
        endpoint: str = "https://openrouter.ai/api/v1/chat/completions",
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.persona = persona
        self.endpoint = endpoint

    def _chat(self, prompt: str) -> str:
        system_msg = (
            f"You are Kirill's AI social selling copilot on Threads. Be concise, human, and structured.\n\n"
            f"Kirill's persona context:\n{self.persona[:1500]}"
            if self.persona
            else "You are an elite social selling copilot. Output concise, safe, structured results."
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_msg,
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        req = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        choices = raw.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "").strip()

    def classify(self, post_text: str, keyword: str) -> dict:
        prompt = f"""
You are classifying Threads posts to find leads for Kirill's ecosystem:
- want2view.com — YouTube analytics, niche research, content strategy, AI production
- atlasrepo.com — open-source AI tools, automation, app/MVP development, workflows
- fabricbotecosystem.com — Telegram shops, payments, Telegram Wallet, TON, partner/CPA mechanics

Return ONLY JSON with keys:
- relevant: boolean
- score: number between 0 and 1
- reason: short string (≤80 chars)

Score HIGH (0.75-1.0) when the post shows ANY of:
1. Building/launching a product, app, bot, or MVP — needs a developer/tech partner
2. Growing a YouTube/Telegram/social channel — needs analytics or content system
3. Wants to automate content creation, repurposing, or distribution
4. Selling or monetizing in Telegram — needs shop, payments, or partner mechanics
5. Looking for AI tools, agents, or open-source solutions
6. Asking how to go from idea to product
7. Hiring/looking for contractor: dev, AI, automation, content

Score LOW (0.0-0.35) when the post is:
- Just opinion/meme/news with no action intent
- Selling completely unrelated products (food, fashion, real estate)
- Pure personal venting

Keyword: {keyword}
Post text:
<<<POST>>>
{post_text[:900]}
<<<END_POST>>>
"""
        try:
            out = self._chat(prompt)
        except Exception:
            return {"relevant": False, "score": 0.0, "reason": "openrouter_unavailable"}
        m = re.search(r"\{.*\}", out, flags=re.DOTALL)
        if not m:
            return {"relevant": False, "score": 0.0, "reason": "llm_non_json"}
        try:
            data = json.loads(m.group(0))
            return {
                "relevant": bool(data.get("relevant", False)),
                "score": float(data.get("score", 0.0)),
                "reason": str(data.get("reason", ""))[:200],
            }
        except Exception:
            return {"relevant": False, "score": 0.0, "reason": "llm_parse_error"}

    def generate_keywords(self, base_keywords: list[str], persona: str, max_new: int) -> list[str]:
        prompt = f"""
Generate Threads search keywords that surface leads for this person:
- AI/automation/app/bot/MVP builders who need a technical partner
- Content creators (YouTube, Telegram, social) who need analytics or production
- Entrepreneurs wanting to monetize via Telegram shops or partner mechanics
- People looking for open-source AI tools or workflow automation

Return ONLY a JSON array of strings. Mix Russian and English. Max {max_new} items.
No duplicates with base list.

Base keywords:
{json.dumps(base_keywords, ensure_ascii=False)}

Context about Kirill:
{persona[:600]}
"""
        try:
            out = self._chat(prompt)
        except Exception:
            return []
        m = re.search(r"\[.*\]", out, flags=re.DOTALL)
        if not m:
            return []
        try:
            arr = json.loads(m.group(0))
            return [str(x).strip() for x in arr if isinstance(x, str) and str(x).strip()][:max_new]
        except Exception:
            return []

    def _self_check_reply(self, reply_text: str, post_text: str) -> tuple[bool, float]:
        """Second LLM pass: check the draft reply for spam signals and quality."""
        prompt = f"""
Rate this Threads reply on two criteria. Return ONLY JSON:
- passes: boolean — true if the reply sounds like a real human, not a bot or spam
- score: float 0-1 — overall quality (1=perfect human outreach, 0=obvious spam/generic)

Deduct heavily for:
- Starting with "I", "Great", "Interesting", "Love this", "Wow"
- Generic phrases like "happy to help", "feel free to reach out", "let me know"
- More than 1 emoji
- Sounding like a cold sales script
- Not referencing anything specific from the post

The post being replied to:
<<<POST>>>
{post_text[:400]}
<<<END>>>

The draft reply:
<<<REPLY>>>
{reply_text}
<<<END>>>
"""
        try:
            out = self._chat(prompt)
            m = re.search(r"\{.*\}", out, flags=re.DOTALL)
            if not m:
                return True, 0.75
            data = json.loads(m.group(0))
            return bool(data.get("passes", True)), float(data.get("score", 0.75))
        except Exception:
            return True, 0.75

    def compose_reply(self, persona: str, post_text: str, author_handle: str, context_hint: str = "") -> str:
        FEW_SHOT = """
Examples of good replies (Kirill's voice):

Post: "Trying to build a Telegram mini app for my store but no clue where to start technically"
Reply: "Built a few of these — the stack really depends on whether you need TON payments or just cards. What's the product?"

Post: "Spend 6 hours a week manually repurposing my YouTube videos to other platforms, there must be a better way"
Reply: "There is — pipeline takes ~20 min to set up. Curious: are you reposting raw cuts or also rewriting the narrative per platform?"

Post: "Ищу кого-то кто поможет с аналитикой YouTube канала, не понимаю почему просмотры падают"
Reply: "Обычно это или смена аудитории, или тайтлы перестали работать — можно быстро посмотреть по данным. Какая ниша?"

Post: "Looking for an AI engineer to help build internal automation tools, budget ~$3k"
Reply: "Automation scope and stack matter a lot here. Is this mostly data pipelines or user-facing workflows?"
"""
        prompt = f"""
You are writing a short Threads reply in Kirill's voice.

WHO KIRILL IS:
{persona[:800]}

{FEW_SHOT}

RULES:
- Max 280 chars
- No hashtags, no links, no emojis (max 1 if very natural)
- Never start with "I", "Great", "Love", "Interesting", "Wow"
- Reference something SPECIFIC from the post — not generic
- End with one natural open question that invites a real response
- Match language of the post (Russian post → Russian reply, English → English)
- Sound like a peer / practitioner, not a vendor

CONTEXT HINT:
{context_hint}

Author: {author_handle}
Post:
<<<POST>>>
{post_text[:900]}
<<<END_POST>>>

Return ONLY the final reply text.
"""
        try:
            draft = self._chat(prompt).strip().strip('"')
            draft = re.sub(r"\s+", " ", draft)[:280]
        except Exception:
            return ""

        if not draft:
            return ""

        # Self-check: if reply looks spammy, try once more with stricter temperature
        passes, quality = self._self_check_reply(draft, post_text)
        if not passes or quality < 0.6:
            stricter_prompt = prompt + "\n\nPREVIOUS DRAFT WAS REJECTED (too generic/spammy). Write a completely different, more specific reply."
            try:
                draft2 = self._chat(stricter_prompt).strip().strip('"')
                draft2 = re.sub(r"\s+", " ", draft2)[:280]
                if draft2:
                    draft = draft2
            except Exception:
                pass

        return draft


def simple_relevance_rule(text: str) -> dict:
    txt = text.lower()
    intent = [
        "ищу", "нужен", "нужна", "требуется", "looking for", "need", "hire", "hiring",
        "задача", "подрядчик", "фриланс", "в штат",
    ]
    domain = [
        "it", "ии", "ai", "app", "web", "telegram", "телеграм", "бот", "developer",
        "разработчик", "программист", "приложение", "сайт", "mvp", "automation",
    ]
    ok = any(w in txt for w in intent) and any(w in txt for w in domain)
    return {"relevant": ok, "score": 0.65 if ok else 0.05, "reason": "rule_filter"}


def normalize_handle(author_url: str) -> str:
    if not author_url:
        return ""
    m = re.search(r"threads\.net/@([^/?#]+)", author_url)
    if not m:
        return ""
    return "@" + m.group(1)


def make_post_id(post_url: str, text: str) -> str:
    if post_url:
        m = re.search(r"threads\.net(/[^?#]+)", post_url)
        if m:
            return m.group(1)
    return text[:120].strip().lower()


def _parse_hhmm(value: str, fallback_h: int, fallback_m: int) -> tuple[int, int]:
    try:
        h, m = value.split(":", 1)
        return int(h), int(m)
    except Exception:
        return fallback_h, fallback_m


def in_active_window(cfg: dict) -> bool:
    active = cfg.get("active_hours", {})
    if not active:
        return True

    timezones = cfg.get("target_timezones", ["America/New_York"])
    for tz_name in timezones:
        try:
            now_tz = datetime.now(ZoneInfo(tz_name))
        except Exception:
            continue

        is_weekend = now_tz.weekday() >= 5
        window = active.get("weekend" if is_weekend else "weekday", ["09:00", "19:00"])
        if not isinstance(window, list) or len(window) != 2:
            continue

        sh, sm = _parse_hhmm(str(window[0]), 9, 0)
        eh, em = _parse_hhmm(str(window[1]), 19, 0)
        start_minutes = sh * 60 + sm
        end_minutes = eh * 60 + em
        now_minutes = now_tz.hour * 60 + now_tz.minute

        if start_minutes <= now_minutes <= end_minutes:
            return True

    return False


def get_behavior_context(cfg: dict, state: dict) -> dict[str, Any]:
    timezones = cfg.get("target_timezones", ["America/New_York"])
    now_tz = datetime.now(timezone.utc)
    tz_name = "UTC"
    for candidate in timezones:
        try:
            now_tz = datetime.now(ZoneInfo(candidate))
            tz_name = candidate
            break
        except Exception:
            continue

    hour = now_tz.hour
    if 6 <= hour < 10:
        phase = "morning"
    elif 10 <= hour < 14:
        phase = "midday"
    elif 14 <= hour < 19:
        phase = "afternoon"
    else:
        phase = "evening"

    recent = state.get("reply_history", [])[-12:]
    action_counts = Counter(str(item.get("action", "")) for item in recent)
    recent_replies = [str(item.get("reply", "")).strip() for item in recent if item.get("action") == "reply" and str(item.get("reply", "")).strip()]

    return {
        "timezone": tz_name,
        "hour": hour,
        "phase": phase,
        "recent_action_counts": action_counts,
        "recent_replies": recent_replies[-3:],
        "recent_reply_count": action_counts.get("reply", 0),
        "recent_follow_count": action_counts.get("follow", 0),
        "recent_like_count": action_counts.get("like", 0),
        "recent_browse_count": action_counts.get("browse", 0),
    }


def build_reply_context(cfg: dict, state: dict, behavior: dict[str, Any], post: CandidatePost) -> str:
    keyword_history = state.get("keyword_history", [])[-6:]
    recent_replies = behavior.get("recent_replies", [])
    phase = behavior.get("phase", "midday")
    tone_hint = {
        "morning": "slightly warmer and curious",
        "midday": "practical and concise",
        "afternoon": "balanced, peer-to-peer",
        "evening": "shorter and more direct",
    }.get(phase, "practical and concise")

    return (
        f"Local time phase: {phase} ({behavior.get('timezone', 'UTC')}).\n"
        f"Desired tone: {tone_hint}.\n"
        f"Recent keywords explored: {', '.join(keyword_history) if keyword_history else 'none'}\n"
        f"Recent replies already used: {(' | '.join(recent_replies) if recent_replies else 'none')}.\n"
        f"Avoid repeating the same angle; make this reply feel fresh and specific to the post author.\n"
        f"Target post author: {post.author_handle or 'unknown'}"
    )


def get_scroll_depth_range(cfg: dict, behavior: dict[str, Any]) -> list[int]:
    base = cfg.get("scroll_depth_range", [3, 8])
    if not isinstance(base, list) or len(base) != 2:
        return [3, 8]

    low = max(1, int(base[0]))
    high = max(low, int(base[1]))
    phase = behavior.get("phase", "midday")

    if phase == "morning":
        high += 1
    elif phase == "evening":
        low = max(2, low - 1)
        high = max(low + 1, high - 1)

    if int(behavior.get("recent_reply_count", 0)) >= 2:
        high = max(low + 1, high - 1)

    if int(behavior.get("recent_follow_count", 0)) >= 2:
        low = min(low + 1, high)

    return [low, high]


def choose_action(action_mix: dict[str, float], state: dict | None = None, behavior: dict[str, Any] | None = None) -> str:
    defaults = {"reply": 0.6, "like": 0.2, "follow": 0.12, "browse": 0.08}
    mix = {**defaults, **(action_mix or {})}

    if state:
        recent = state.get("reply_history", [])[-12:]
        recent_counts = Counter(str(item.get("action", "")) for item in recent)
        if recent_counts.get("reply", 0) >= 2:
            mix["reply"] = max(0.08, float(mix.get("reply", 0.0)) - 0.12)
            mix["browse"] = float(mix.get("browse", 0.0)) + 0.08
        if recent_counts.get("follow", 0) >= 2:
            mix["follow"] = max(0.03, float(mix.get("follow", 0.0)) - 0.06)
            mix["like"] = float(mix.get("like", 0.0)) + 0.03

    if behavior:
        phase = behavior.get("phase")
        if phase in {"morning", "midday"}:
            mix["browse"] = float(mix.get("browse", 0.0)) + 0.05
            mix["follow"] = float(mix.get("follow", 0.0)) + 0.02
        elif phase == "evening":
            mix["reply"] = float(mix.get("reply", 0.0)) + 0.05
            mix["browse"] = max(0.03, float(mix.get("browse", 0.0)) - 0.03)

    total = sum(max(0.0, float(v)) for v in mix.values())
    if total <= 0:
        return "reply"

    threshold = random.uniform(0, total)
    current = 0.0
    for action, weight in mix.items():
        current += max(0.0, float(weight))
        if current >= threshold:
            return action
    return "reply"


def can_act_this_hour(state: dict, cap: int) -> bool:
    if cap <= 0:
        return True
    hour_key = datetime.now().strftime("%Y-%m-%d-%H")
    hourly = state.get("hourly_stats", {})
    return int(hourly.get(hour_key, 0)) < cap


def increase_hour_counter(state: dict) -> None:
    hour_key = datetime.now().strftime("%Y-%m-%d-%H")
    hourly = state.setdefault("hourly_stats", {})
    hourly[hour_key] = int(hourly.get(hour_key, 0)) + 1
    # Keep only last ~3 days of hour buckets.
    if len(hourly) > 100:
        for key in sorted(hourly.keys())[:-72]:
            hourly.pop(key, None)


AGENT_PROFILE_DIR = BASE_DIR / "chrome_profile"


async def build_context(cfg: dict, headful_override: bool | None = None) -> tuple[Any, BrowserContext]:
    """
    Launch browser using a persistent Chrome profile stored in chrome_profile/.
    This avoids login walls — once set up via --setup-login, the session persists
    in the profile directory itself (no separate storage_state.json needed).
    Falls back to storage_state.json if persistent profile not yet initialised.
    """
    headful = cfg.get("headful", True) if headful_override is None else headful_override
    use_chrome_channel = bool(cfg.get("use_chrome_channel", True))
    window = cfg.get("window", {"x": 0, "y": 0, "width": 960, "height": 1080})
    win_x = int(os.getenv("THREADS_WIN_X", window.get("x", 0)))
    win_y = int(os.getenv("THREADS_WIN_Y", window.get("y", 0)))
    win_w = int(os.getenv("THREADS_WIN_WIDTH", window.get("width", 960)))
    win_h = int(os.getenv("THREADS_WIN_HEIGHT", window.get("height", 1080)))

    args = [
        f"--window-position={win_x},{win_y}",
        f"--window-size={win_w},{win_h}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
    ]

    pw = await async_playwright().start()

    # Persistent profile survives restarts and keeps login state.
    AGENT_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    launch_kwargs = {
        "user_data_dir": str(AGENT_PROFILE_DIR),
        "headless": not headful,
        "args": args,
        "viewport": {"width": win_w, "height": win_h},
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    }
    if use_chrome_channel:
        try:
            context = await pw.chromium.launch_persistent_context(channel="chrome", **launch_kwargs)
            logging.info("Browser launched via Chrome channel")
            return pw, context
        except Exception as exc:
            logging.warning("Failed to launch Chrome channel (%s); fallback to bundled Chromium", exc)

    context = await pw.chromium.launch_persistent_context(**launch_kwargs)
    logging.info("Browser launched via Chromium")
    return pw, context


async def setup_login(cfg: dict) -> None:
    logging.info("Opening Chrome for one-time Threads login (profile saved to chrome_profile/)...")
    pw, context = await build_context(cfg, headful_override=True)
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto("https://www.threads.net/login", wait_until="domcontentloaded")
    print("\nLog in to Threads in the opened Chrome window, then press Enter here.")
    input()
    # Also save storage state as backup
    await context.storage_state(path=str(STORAGE_STATE_FILE))
    await context.close()
    await pw.stop()
    logging.info("Login saved to chrome_profile/ and %s", STORAGE_STATE_FILE)


async def scrape_posts_for_keyword(page: Page, keyword: str, max_posts: int, scroll_depth_range: list[int] | None = None) -> list[CandidatePost]:
    search_url = f"https://www.threads.net/search?q={quote(keyword)}&serp_type=default"
    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
        if "login" in page.url.lower():
            logging.warning("Threads redirected to login wall. Re-run --setup-login to refresh session.")
            return []
        depth_range = scroll_depth_range
        if not depth_range or len(depth_range) != 2:
            scroll_depth = random.randint(3, 8)
        else:
            scroll_depth = random.randint(int(depth_range[0]), int(depth_range[1]))

        for i in range(scroll_depth):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(random.randint(1200, 2200))
            if i > 1 and random.random() < 0.18:
                await page.mouse.move(random.randint(120, 860), random.randint(200, 740), steps=random.randint(8, 20))
            if i > 2 and random.random() < 0.12:
                await page.evaluate("window.scrollBy(0, -Math.floor(window.innerHeight * 0.6))")
                await page.wait_for_timeout(random.randint(700, 1400))
            if i > 1 and random.random() < 0.08:
                break

        raw = await page.evaluate(
            """() => {
                const out = [];
                const seen = new Set();
                const blocks = document.querySelectorAll('article, [role="article"]');
                for (const block of blocks) {
                  const textEl = block.querySelector('[dir="auto"]');
                  const text = textEl ? textEl.innerText.trim() : '';
                  if (!text || text.length < 25) continue;
                  const postLink = block.querySelector('a[href*="/post/"]');
                  const authorLink = block.querySelector('a[href*="/@"]');
                  const postUrl = postLink ? postLink.href : '';
                  const authorUrl = authorLink ? authorLink.href : '';
                  const key = postUrl || text.slice(0, 100);
                  if (seen.has(key)) continue;
                  seen.add(key);
                  out.push({postUrl, authorUrl, text});
                }
                return out;
            }"""
        )
    except Exception as exc:
        logging.warning("Search failed for keyword '%s': %s", keyword, exc)
        return []

    candidates: list[CandidatePost] = []
    for item in raw[:max_posts]:
        post_url = item.get("postUrl", "")
        author_url = item.get("authorUrl", "")
        text = item.get("text", "")
        candidates.append(
            CandidatePost(
                keyword=keyword,
                post_url=post_url,
                author_url=author_url,
                author_handle=normalize_handle(author_url),
                text=text,
            )
        )
    return candidates


async def browse_post_naturally(page: Page, post: CandidatePost, behavior: dict[str, Any]) -> None:
    await page.goto(post.post_url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(random.randint(1200, 2400))
    for _ in range(random.randint(1, 2)):
        await page.evaluate("window.scrollBy(0, Math.floor(window.innerHeight * 0.55))")
        await page.wait_for_timeout(random.randint(800, 1700))
    if post.author_url and random.random() < 0.6:
        await page.goto(post.author_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(random.randint(1000, 2200))
        if random.random() < 0.5:
            await page.evaluate("window.scrollBy(0, Math.floor(window.innerHeight * 0.35))")
            await page.wait_for_timeout(random.randint(700, 1400))
    if behavior.get("phase") in {"morning", "afternoon"} and random.random() < 0.3:
        await page.mouse.move(random.randint(140, 920), random.randint(220, 760), steps=random.randint(6, 14))


async def post_reply(page: Page, post_url: str, reply_text: str) -> tuple[bool, str]:
    try:
        await page.goto(post_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(random.randint(1200, 2500))

        reply_button_selectors = [
            "button:has-text('Reply')",
            "div[role='button']:has-text('Reply')",
            "div[aria-label*='Reply']",
        ]
        clicked = False
        for sel in reply_button_selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                await loc.first.click(timeout=3000)
                clicked = True
                break
        if not clicked:
            return False, "reply_button_not_found"

        await page.wait_for_timeout(random.randint(800, 1800))
        box_selectors = [
            "div[role='textbox']",
            "textarea",
            "div[contenteditable='true']",
        ]
        typed = False
        for sel in box_selectors:
            box = page.locator(sel)
            if await box.count() > 0:
                await box.first.click()
                await page.wait_for_timeout(random.randint(220, 650))
                for ch in reply_text:
                    await page.keyboard.type(ch)
                    await page.wait_for_timeout(random.randint(45, 120))
                typed = True
                break
        if not typed:
            return False, "reply_box_not_found"

        await page.wait_for_timeout(random.randint(900, 1800))
        send_selectors = [
            "button:has-text('Post')",
            "div[role='button']:has-text('Post')",
            "button:has-text('Reply')",
        ]
        sent = False
        for sel in send_selectors:
            btn = page.locator(sel)
            if await btn.count() > 0:
                await btn.first.click(timeout=4000)
                sent = True
                break
        if not sent:
            return False, "send_button_not_found"

        await page.wait_for_timeout(random.randint(1800, 3000))
        return True, "ok"
    except Exception as exc:
        return False, f"exception:{exc}"


async def like_post(page: Page, post_url: str) -> tuple[bool, str]:
    try:
        await page.goto(post_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(random.randint(900, 1900))
        selectors = [
            "div[role='button'][aria-label*='Like']",
            "button[aria-label*='Like']",
            "div[data-testid='like']",
        ]
        for sel in selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                await loc.first.click(timeout=3500)
                await page.wait_for_timeout(random.randint(700, 1300))
                return True, "ok"
        return False, "like_button_not_found"
    except Exception as exc:
        return False, f"exception:{exc}"


async def follow_author(page: Page, author_url: str) -> tuple[bool, str]:
    try:
        if not author_url:
            return False, "author_url_empty"
        await page.goto(author_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(random.randint(1200, 2200))
        selectors = [
            "button:has-text('Follow')",
            "div[role='button']:has-text('Follow')",
            "button[aria-label*='Follow']",
        ]
        for sel in selectors:
            loc = page.locator(sel)
            if await loc.count() > 0:
                await loc.first.click(timeout=3500)
                await page.wait_for_timeout(random.randint(900, 1600))
                return True, "ok"
        return False, "follow_button_not_found"
    except Exception as exc:
        return False, f"exception:{exc}"


def resolve_keywords(cfg: dict, persona: str, ollama: OllamaClient | None, state: dict) -> list[str]:
    base = [k.strip() for k in cfg.get("keywords", []) if k.strip()]
    if not base:
        base = ["it", "ai", "web", "app", "telegram", "телеграм", "ии"]

    result = list(base)
    if cfg.get("auto_keyword_generation", True) and ollama:
        max_new = int(cfg.get("generated_keywords", 6))
        generated = ollama.generate_keywords(base, persona, max_new=max_new)
        result.extend(generated)

    result = dedupe_keep_tail(result, int(cfg.get("keyword_limit", 20)))
    state["keyword_history"] = dedupe_keep_tail(state.get("keyword_history", []) + result, 500)
    return result


def can_reply_today(state: dict, max_replies_day: int) -> bool:
    day = datetime.now().strftime("%Y-%m-%d")
    day_count = int(state.get("daily_stats", {}).get(day, 0))
    return day_count < max_replies_day


def increase_day_counter(state: dict) -> None:
    day = datetime.now().strftime("%Y-%m-%d")
    if "daily_stats" not in state:
        state["daily_stats"] = {}
    state["daily_stats"][day] = int(state["daily_stats"].get(day, 0)) + 1


def seconds_until_next_cycle(cycle_minutes: int, jitter_range: list[int]) -> int:
    jitter = random.randint(int(jitter_range[0]), int(jitter_range[1])) if jitter_range else 0
    return max(60, (cycle_minutes + jitter) * 60)


async def run_cycle(cfg: dict, profile: dict, state: dict, ollama: OllamaClient | None, persona: str, dry_run: bool) -> dict:
    logging.info("Starting cycle")

    if not in_active_window(cfg):
        logging.info("Outside active US windows, skipping cycle")
        return {"checked_posts": 0, "relevant_posts": 0, "replies_sent": 0, "likes_sent": 0, "follows_sent": 0, "browse_only": 0, "keywords": []}

    behavior = get_behavior_context(cfg, state)
    logging.info(
        "Behavior context: tz=%s phase=%s recent_reply=%s recent_follow=%s recent_like=%s",
        behavior.get("timezone"),
        behavior.get("phase"),
        behavior.get("recent_reply_count", 0),
        behavior.get("recent_follow_count", 0),
        behavior.get("recent_like_count", 0),
    )

    seen = set(state.get("seen_posts", []))
    replied = set(state.get("replied_posts", []))
    liked = set(state.get("liked_posts", []))
    followed = set(state.get("followed_authors", []))
    keywords = resolve_keywords(cfg, persona, ollama, state)
    action_mix = cfg.get("action_mix", {})
    hourly_cap = int(cfg.get("hourly_action_cap", 8))

    max_replies_cycle = int(profile["max_replies_per_cycle"])
    max_replies_day = int(profile["max_replies_per_day"])
    min_score = float(profile["llm_min_score"])
    auto_send_min_score = float(cfg.get("auto_send_min_score", 0.82))
    draft_min_score = float(cfg.get("draft_min_score", 0.7))
    search_per_kw = int(profile["search_posts_per_keyword"])

    stats = {
        "checked_posts": 0,
        "relevant_posts": 0,
        "replies_sent": 0,
        "likes_sent": 0,
        "follows_sent": 0,
        "browse_only": 0,
        "draft_only": 0,
        "keywords": keywords,
    }

    pw, context = await build_context(cfg)
    page = await context.new_page()

    try:
        for keyword in keywords:
            if stats["replies_sent"] >= max_replies_cycle:
                break
            if not can_reply_today(state, max_replies_day):
                logging.info("Daily reply limit reached")
                break

            logging.info("Search keyword: %s", keyword)
            # Recover page if context closed mid-cycle (e.g. Threads redirected to login wall)
            try:
                await page.evaluate("1+1")
            except Exception:
                logging.warning("Page closed mid-cycle, recreating...")
                try:
                    page = await context.new_page()
                except Exception:
                    logging.error("Browser context dead, ending keyword loop early")
                    break
            posts = await scrape_posts_for_keyword(
                page,
                keyword,
                max_posts=search_per_kw,
                scroll_depth_range=get_scroll_depth_range(cfg, behavior),
            )
            logging.info("Found posts: %s", len(posts))

            for post in posts:
                if stats["replies_sent"] >= max_replies_cycle:
                    break
                if not can_reply_today(state, max_replies_day):
                    break

                post_id = make_post_id(post.post_url, post.text)
                if post_id in seen:
                    continue
                seen.add(post_id)
                stats["checked_posts"] += 1

                if post_id in replied:
                    continue

                if ollama:
                    cls = ollama.classify(post.text, post.keyword)
                    if cls.get("reason") == "ollama_unavailable":
                        cls = simple_relevance_rule(post.text)
                else:
                    cls = simple_relevance_rule(post.text)

                is_relevant = bool(cls.get("relevant", False)) and float(cls.get("score", 0.0)) >= min_score
                if not is_relevant:
                    continue

                stats["relevant_posts"] += 1

                confidence = float(cls.get("score", 0.0))
                if confidence < draft_min_score:
                    continue

                if not can_act_this_hour(state, hourly_cap):
                    logging.info("Hourly cap reached, pausing action attempts")
                    break

                action = choose_action(action_mix, state=state, behavior=behavior)
                ok = False
                reason = ""
                reply_text = ""

                if action == "reply" and confidence < auto_send_min_score:
                    stats["draft_only"] += 1
                    reason = "draft_gate"
                    ok = True
                    action = "draft"

                if action == "browse":
                    stats["browse_only"] += 1
                    reason = "browse_only"
                    ok = True
                    await browse_post_naturally(page, post, behavior)

                elif action == "like":
                    if post_id in liked:
                        continue
                    if dry_run:
                        ok, reason = True, "dry_run_like"
                    else:
                        ok, reason = await like_post(page, post.post_url)
                    if ok:
                        liked.add(post_id)
                        stats["likes_sent"] += 1
                        increase_hour_counter(state)

                elif action == "follow":
                    author_key = post.author_handle or post.author_url
                    if author_key in followed:
                        continue
                    if dry_run:
                        ok, reason = True, "dry_run_follow"
                    else:
                        ok, reason = await follow_author(page, post.author_url)
                    if ok:
                        followed.add(author_key)
                        stats["follows_sent"] += 1
                        increase_hour_counter(state)

                elif action == "reply":
                    reply_context = build_reply_context(cfg, state, behavior, post)
                    if ollama:
                        reply_text = ollama.compose_reply(persona, post.text, post.author_handle or "", context_hint=reply_context)
                    else:
                        reply_text = "Interesting ask. I build IT/AI/app/web/telegram solutions and can help quickly. Want to continue in DM?"

                    if not reply_text.strip():
                        reply_text = "Interesting ask. I build IT/AI/app/web/telegram solutions and can help quickly. Want to continue in DM?"

                    if not reply_text.strip():
                        continue

                    if dry_run:
                        ok, reason = True, "dry_run_reply"
                    else:
                        ok, reason = await post_reply(page, post.post_url, reply_text)

                    if ok:
                        replied.add(post_id)
                        state["last_reply_ts"] = int(time.time())
                        increase_day_counter(state)
                        stats["replies_sent"] += 1
                        increase_hour_counter(state)
                        logging.info("Reply sent to %s | %s", post.author_handle, post.post_url)

                else:
                    # Draft action: keep decision and proposed reply in history without posting.
                    reply_context = build_reply_context(cfg, state, behavior, post)
                    if ollama:
                        reply_text = ollama.compose_reply(persona, post.text, post.author_handle or "", context_hint=reply_context)
                    if not reply_text:
                        reply_text = "Draft: concise value-first response needed"

                state["reply_history"].append(
                    {
                        "ts": now_iso(),
                        "keyword": post.keyword,
                        "post_url": post.post_url,
                        "author": post.author_handle,
                        "action": action,
                        "decision": cls,
                        "reply": reply_text,
                        "status": "sent" if ok else "failed",
                        "reason": reason,
                    }
                )

                if not ok:
                    logging.warning("Reply failed: %s", reason)

                delay_rng = profile.get("reply_delay_seconds", [25, 90])
                await asyncio.sleep(random.randint(int(delay_rng[0]), int(delay_rng[1])))

    finally:
        try:
            await context.storage_state(path=str(STORAGE_STATE_FILE))
        except Exception:
            pass
        try:
            await context.close()
        except Exception:
            pass
        try:
            await pw.stop()
        except Exception:
            pass

    state["seen_posts"] = dedupe_keep_tail(list(seen), 8000)
    state["replied_posts"] = dedupe_keep_tail(list(replied), 5000)
    state["liked_posts"] = dedupe_keep_tail(list(liked), 5000)
    state["followed_authors"] = dedupe_keep_tail(list(followed), 5000)
    state["reply_history"] = state.get("reply_history", [])[-4000:]

    logging.info(
        "Cycle done. checked=%s relevant=%s replies=%s",
        stats["checked_posts"],
        stats["relevant_posts"],
        stats["replies_sent"],
    )
    return stats


async def run_agent(args: argparse.Namespace) -> None:
    cfg = load_config()
    state = load_state()
    persona = load_persona(BASE_DIR / cfg.get("persona_file", PERSONA_FILE.name))

    # Enrich persona with full about3.md identity document if configured
    about3_path_str = cfg.get("persona_about3_path", "")
    if about3_path_str:
        about3_path = Path(about3_path_str)
        if about3_path.exists():
            try:
                persona = about3_path.read_text(encoding="utf-8").strip()
                logging.info("Loaded persona from about3.md (%d chars)", len(persona))
            except Exception as e:
                logging.warning("Could not load about3.md: %s", e)

    profile_name = args.profile or cfg.get("profile", "safe")
    if profile_name not in PROFILE_PRESETS:
        raise RuntimeError(f"Unknown profile: {profile_name}")

    profile = dict(PROFILE_PRESETS[profile_name])
    profile.update(cfg.get("profile_overrides", {}))

    ollama = None
    llm_provider = str(cfg.get("llm_provider", "ollama")).lower()

    if llm_provider == "github_models":
        key_env = str(cfg.get("github_token_env", "GITHUB_TOKEN"))
        # config.json value takes priority over env var (file is gitignored)
        api_key = str(cfg.get("github_token", "") or os.getenv(key_env, "")).strip()
        model = str(cfg.get("github_model", "claude-3-5-sonnet-20241022"))
        if api_key:
            ollama = OpenRouterClient(
                api_key=api_key,
                model=model,
                timeout_seconds=int(cfg.get("openrouter_timeout_seconds", 60)),
                persona=persona,
                endpoint="https://models.inference.ai.azure.com/chat/completions",
            )
            logging.info("Using GitHub Models model=%s", model)
        else:
            logging.warning("GitHub Models selected but token not found in env var %s", key_env)

    elif llm_provider == "openrouter":
        key_env = str(cfg.get("openrouter_api_key_env", "OPENROUTER_API_KEY"))
        api_key = os.getenv(key_env, "").strip()
        model = str(cfg.get("openrouter_model", "anthropic/claude-sonnet-4"))
        if api_key:
            ollama = OpenRouterClient(
                api_key=api_key,
                model=model,
                timeout_seconds=int(cfg.get("openrouter_timeout_seconds", 60)),
                persona=persona,
            )
            logging.info("Using OpenRouter model=%s", model)
        else:
            logging.warning("OpenRouter selected but API key not found in %s; fallback to Ollama", key_env)

    if ollama is None and cfg.get("use_ollama", True):
        ollama = OllamaClient(
            host=cfg.get("ollama_host", "http://127.0.0.1:11434"),
            model=cfg.get("ollama_model", "llama3.1"),
            timeout_seconds=int(cfg.get("ollama_timeout_seconds", 45)),
        )

    logging.info("Agent profile=%s dry_run=%s", profile_name, args.dry_run)
    if args.once:
        await run_cycle(cfg, profile, state, ollama, persona, dry_run=args.dry_run)
        save_state(state)
        return

    while True:
        try:
            await run_cycle(cfg, profile, state, ollama, persona, dry_run=args.dry_run)
            save_state(state)
        except Exception as exc:
            logging.exception("Cycle error: %s", exc)

        wait_seconds = seconds_until_next_cycle(
            int(profile["cycle_minutes"]),
            profile.get("cycle_jitter_minutes", [1, 5]),
        )
        logging.info("Sleeping %s seconds", wait_seconds)
        await asyncio.sleep(wait_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Threads autopilot: find leads, filter, and reply")
    parser.add_argument("--setup-login", action="store_true", help="Open browser and save Threads login state")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Do not post replies, only simulate")
    parser.add_argument("--profile", choices=list(PROFILE_PRESETS.keys()), help="Run preset profile")
    parser.add_argument("--verbose", action="store_true", help="Verbose logs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    try:
        cfg = load_config()
    except Exception as exc:
        print(exc)
        return

    if args.setup_login:
        asyncio.run(setup_login(cfg))
        return

    asyncio.run(run_agent(args))


if __name__ == "__main__":
    main()
