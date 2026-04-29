import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


SYSTEM_PROMPT = """You are a lead research assistant.
You analyze Telegram chat exports and answer in concise, practical sales language.
Always provide:
1) Short answer
2) Why (based on chat evidence)
3) Suggested next action
"""


def load_rows(csv_path: Path, max_rows: int) -> list[dict]:
    if not csv_path.exists():
        return []

    rows = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            rows.append(row)
    return rows


def build_context(results_dir: Path) -> str:
    top_priority = load_rows(results_dir / "top100_priority.csv", 80)
    all_chats = load_rows(results_dir / "all_chats.csv", 200)

    parts = []
    if top_priority:
        parts.append("Top priority leads:")
        for row in top_priority[:30]:
            parts.append(
                f"- {row.get('chat_name', 'n/a')} | priority={row.get('priority', 'n/a')} | "
                f"keywords={row.get('matched_keywords', '')} | last={row.get('last_messages', '')[:180]}"
            )

    if all_chats:
        parts.append("\nAdditional chats snapshot:")
        for row in all_chats[:40]:
            parts.append(
                f"- {row.get('chat_name', 'n/a')} | type={row.get('chat_type', 'n/a')} | "
                f"messages={row.get('message_count', 'n/a')} | intent={row.get('intent', 'n/a')}"
            )

    if not parts:
        return "No CSV context found. Ask generic questions only."

    return "\n".join(parts)


def ollama_chat(model: str, messages: list[dict]) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    message = result.get("message", {})
    return message.get("content", "No response returned.")


def openai_chat(model: str, messages: list[dict], api_key: str) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    choices = result.get("choices", [])
    if not choices:
        return "No response returned."
    return choices[0].get("message", {}).get("content", "No response returned.")


def anthropic_chat(model: str, messages: list[dict], api_key: str) -> str:
    system_text = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
    user_assistant_messages = [m for m in messages if m.get("role") in {"user", "assistant"}]

    payload = {
        "model": model,
        "max_tokens": 1000,
        "system": system_text,
        "messages": user_assistant_messages,
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    blocks = result.get("content", [])
    texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    return "\n".join(t for t in texts if t).strip() or "No response returned."


def dispatch_chat(provider: str, model: str, messages: list[dict]) -> str:
    provider = provider.lower()
    if provider == "ollama":
        return ollama_chat(model, messages)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return openai_chat(model, messages, api_key)

    if provider in {"anthropic", "claude"}:
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        return anthropic_chat(model, messages, api_key)

    raise RuntimeError(f"Unknown provider: {provider}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI chat over Telegram CSV results (Ollama / OpenAI / Anthropic)"
    )
    parser.add_argument(
        "--results-dir",
        default=".",
        help="Directory containing top100_priority.csv and all_chats.csv",
    )
    parser.add_argument(
        "--provider",
        default="ollama",
        choices=["ollama", "openai", "anthropic", "claude"],
        help="LLM provider",
    )
    parser.add_argument("--model", default="llama3.1", help="Model name for selected provider")
    args = parser.parse_args()

    results_dir = Path(args.results_dir).resolve()
    context = build_context(results_dir)

    print("\nAI Chat over your results")
    print(f"Provider: {args.provider}")
    print(f"Results folder: {results_dir}")
    print(f"Model: {args.model}")
    print("Type 'exit' to quit.\n")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Data context:\n{context}"},
    ]

    while True:
        try:
            user_text = input("Prompt> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit", "q"}:
            print("Bye.")
            return 0

        messages.append({"role": "user", "content": user_text})

        try:
            answer = dispatch_chat(args.provider, args.model, messages)
        except urllib.error.URLError:
            print("\nCould not connect to the selected provider endpoint.")
            if args.provider == "ollama":
                print("Install and run Ollama first: https://ollama.com")
                print("Then run: ollama pull llama3.1")
            return 1
        except RuntimeError as e:
            print(f"\nConfiguration error: {e}")
            if args.provider == "openai":
                print("Set key: export OPENAI_API_KEY='your_key'")
            elif args.provider in {"anthropic", "claude"}:
                print("Set key: export ANTHROPIC_API_KEY='your_key'")
            return 1
        except Exception as e:
            print(f"\nAI request failed: {e}")
            return 1

        print("\nAssistant:\n")
        print(answer)
        print("")

        messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    sys.exit(main())
