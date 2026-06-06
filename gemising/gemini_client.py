from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import MODEL_NAME, OLLAMA_DEFAULT_MODEL


class GeminiAPIError(RuntimeError):
    pass


def _build_tools(enable_google_search: bool, enable_url_context: bool) -> list[dict[str, dict]]:
    tools: list[dict[str, dict]] = []
    if enable_google_search:
        tools.append({"google_search": {}})
    if enable_url_context:
        tools.append({"url_context": {}})
    return tools


def generate_reply(
    api_key: str,
    messages: list[dict[str, str]],
    *,
    enable_google_search: bool = False,
    enable_url_context: bool = False,
) -> str:
    if not api_key.strip():
        raise GeminiAPIError("Missing API key.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL_NAME}:generateContent?key={api_key.strip()}"
    )
    payload = {
        "contents": [
            {
                "role": msg["role"],
                "parts": [{"text": msg["content"]}],
            }
            for msg in messages
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "maxOutputTokens": 2048,
        },
    }
    tools = _build_tools(enable_google_search, enable_url_context)
    if tools:
        payload["tools"] = tools
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise GeminiAPIError(f"HTTP {exc.code}: {body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise GeminiAPIError(f"Network error: {exc.reason}") from exc

    candidates = data.get("candidates") or []
    if not candidates:
        raise GeminiAPIError("No response content returned by Gemini.")
    content = candidates[0].get("content", {})
    parts = content.get("parts") or []
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise GeminiAPIError("Empty response returned by Gemini.")
    return text.strip()


class OllamaAPIError(RuntimeError):
    pass


def generate_ollama_reply(
    base_url: str,
    messages: list[dict[str, str]],
    *,
    model: str = OLLAMA_DEFAULT_MODEL,
) -> str:
    base = base_url.rstrip("/")
    url = f"{base}/api/chat"
    payload = {
        "model": model.strip() or OLLAMA_DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise OllamaAPIError(f"HTTP {exc.code}: {body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise OllamaAPIError(f"Network error: {exc.reason}") from exc

    message = data.get("message") or {}
    text = str(message.get("content", "")).strip()
    if not text:
        raise OllamaAPIError("Empty response returned by Ollama.")
    return text
