from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

from .config import DATA_DIR, HISTORY_FILE


@dataclass
class Message:
    role: str
    content: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Conversation:
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[Message] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_title(messages: list[Message]) -> str:
    for msg in messages:
        if msg.role == "user" and msg.content.strip():
            text = msg.content.strip().replace("\n", " ")
            return text[:32] + ("..." if len(text) > 32 else "")
    return "New chat"


def ensure_unique_title(desired_title: str, existing_titles: list[str], current_title: str | None = None) -> str:
    base = desired_title.strip() or "New chat"
    used = {title for title in existing_titles if title != current_title}
    if base not in used:
        return base

    suffix = 2
    while True:
        candidate = f"{base} ({suffix})"
        if candidate not in used:
            return candidate
        suffix += 1


def _conversation_from_legacy(raw: list[dict]) -> list[Conversation]:
    messages: list[Message] = []
    for item in raw:
        if isinstance(item, dict):
            messages.append(
                Message(
                    role=str(item.get("role", "assistant")),
                    content=str(item.get("content", "")),
                    created_at=str(item.get("created_at", "")) or _now(),
                )
            )
    now = _now()
    return [
        Conversation(
            id=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            title=_make_title(messages),
            created_at=now,
            updated_at=now,
            messages=messages,
        )
    ]


def load_conversations() -> list[Conversation]:
    if not HISTORY_FILE.exists():
        return [create_conversation()]
    try:
        raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return [create_conversation()]
    if isinstance(raw, list):
        return _conversation_from_legacy(raw)
    if isinstance(raw, dict):
        if "conversations" in raw:
            conversations: list[Conversation] = []
            for item in raw.get("conversations", []):
                if not isinstance(item, dict):
                    continue
                messages: list[Message] = []
                for msg in item.get("messages", []):
                    if isinstance(msg, dict):
                        messages.append(
                            Message(
                                role=str(msg.get("role", "assistant")),
                                content=str(msg.get("content", "")),
                                created_at=str(msg.get("created_at", "")) or _now(),
                            )
                        )
                conversations.append(
                    Conversation(
                        id=str(item.get("id", _now())),
                        title=str(item.get("title", "")) or _make_title(messages),
                        created_at=str(item.get("created_at", "")) or _now(),
                        updated_at=str(item.get("updated_at", "")) or _now(),
                        messages=messages,
                    )
                )
            if conversations:
                return conversations
        if "messages" in raw:
            return _conversation_from_legacy(raw.get("messages", []))
    return [create_conversation()]


def create_conversation() -> Conversation:
    now = _now()
    return Conversation(id=now.replace(":", "").replace("-", "").replace(".", ""), title="New chat", created_at=now, updated_at=now)


def save_conversations(conversations: list[Conversation]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps({"conversations": [asdict(conv) for conv in conversations]}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
