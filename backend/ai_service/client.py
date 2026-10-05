"""One bounded HTTP boundary. Model failures become visible, deterministic fallback."""

import json
import os
from urllib.parse import urlsplit

import httpx


class ModelUnavailable(ValueError):
    pass


MOCK_NOTICE = "Offline practice: deterministic mock, not semantic AI grading."
FALLBACK_NOTICE = "Model unavailable or invalid response: deterministic fallback used."


def complete_json(system, payload):
    base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise ModelUnavailable("not_configured")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ModelUnavailable("invalid_configuration")
    model = os.getenv("LLM_MODEL", "").strip()
    if not model:
        raise ModelUnavailable("missing_model")
    headers = {"Content-Type": "application/json"}
    key = os.getenv("LLM_API_KEY", "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        timeout = min(120.0, max(1.0, float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))))
        with httpx.Client(
            timeout=httpx.Timeout(timeout, connect=5), follow_redirects=False, trust_env=False
        ) as client:
            with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "temperature": 0,
                    "max_tokens": 2500,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                },
            ) as response:
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 150_000:
                        raise ModelUnavailable("oversized_response")
        envelope = json.loads(body)
        content = envelope["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ModelUnavailable("invalid_content")
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ModelUnavailable("invalid_object")
        return data
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise ModelUnavailable("provider_failure") from exc


def fallback_metadata():
    if os.getenv("LLM_BASE_URL", "").strip():
        return {"mode": "fallback", "notice": FALLBACK_NOTICE}
    return {"mode": "mock", "notice": MOCK_NOTICE}


def run_with_fallback(system, payload, validate, fallback):
    try:
        return validate(complete_json(system, payload)), {
            "mode": "live",
            "notice": "Real language model response.",
        }
    except (ModelUnavailable, ValueError, TypeError, KeyError, IndexError):
        return fallback(), fallback_metadata()
