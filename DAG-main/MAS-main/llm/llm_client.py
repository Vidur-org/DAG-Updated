import os
import json
import logging
from typing import Any, Dict, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

logger = logging.getLogger(__name__)


def _get_api_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY")

# Enable mock responses for local testing by setting LLM_MOCK=1 or true
_MOCK_MODE = os.getenv("LLM_MOCK", "0").lower() in ("1", "true", "yes")
_client: Optional[OpenAI] = None


def _build_client() -> Optional[OpenAI]:
    """Lazily construct and cache the OpenAI client if credentials are available."""
    global _client
    if _client is not None:
        return _client
    if OpenAI is None:
        return None
    api_key = _get_api_key()
    if not api_key:
        return None
    _client = OpenAI(api_key=api_key)
    return _client


def _ensure_client(allow_mock: bool = True) -> None:
    """Raise a helpful error if the client cannot be created.

    When `allow_mock` is True and mock mode is enabled, this will not raise.
    """
    if _MOCK_MODE and allow_mock:
        logger.info("LLM_MOCK is enabled; using mock responses")
        return

    reasons = []
    if OpenAI is None:
        reasons.append("install the `openai` package (pip install openai)")
    if not _get_api_key():
        reasons.append("set the `OPENAI_API_KEY` environment variable")

    if _build_client() is None:
        hint = " and ".join(reasons) if reasons else "ensure the OpenAI client can be constructed"
        raise RuntimeError(
            "OpenAI client not initialized: please {}. For local tests set `LLM_MOCK=1` to use mock responses.\n"
            "PowerShell examples:\n  temporary: $env:OPENAI_API_KEY = 'sk-...'\n  persistent: setx OPENAI_API_KEY 'sk-...'\n  mock mode: $env:LLM_MOCK = '1'"
            .format(hint)
        )


def _mock_response(system: str, user: str) -> str:
    logger.warning("LLM mock mode active; returning deterministic mock JSON")
    return json.dumps({"mock": True, "system": system[:120], "user": user[:120]})


def call_llm(system: str, user: str) -> str:
    """Call the LLM and return the raw text response.

    If `LLM_MOCK` is enabled, returns a deterministic JSON string useful for tests.
    """
    if _MOCK_MODE:
        return _mock_response(system, user)

    _ensure_client()
    client = _build_client()
    if client is None:
        # _ensure_client should have raised, but double-check
        raise RuntimeError("OpenAI client not available; check logs and environment variables")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception("Error calling LLM: %s", exc)
        raise


def call_llm_json(system: str, user: str, retries: int = 3) -> Dict[str, Any]:
    """Call the LLM and parse JSON output, retrying on parse errors."""
    for _ in range(retries):
        response = call_llm(system, user)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            continue
    raise ValueError("LLM failed to return valid JSON")


__all__ = ["call_llm", "call_llm_json"]
