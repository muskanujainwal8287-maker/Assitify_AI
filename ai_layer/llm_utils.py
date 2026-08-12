import json
import logging
import re
from typing import Any

from openai import APIError, OpenAI

from ai_layer.config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_openai_client() -> OpenAI | None:
    global _client
    if not settings.openai_api_key or not settings.llm_model:
        return None
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def is_openai_configured() -> bool:
    return bool(settings.openai_api_key and settings.llm_model)


def openai_config_status() -> dict[str, str | bool]:
    return {
        "openai_api_key_set": bool(settings.openai_api_key),
        "llm_model_set": bool(settings.llm_model),
        "llm_model": settings.llm_model or "(not set)",
        "ready": is_openai_configured(),
    }


def call_llm(prompt: str, *, json_mode: bool = False) -> tuple[str | None, str | None]:
    """Call OpenAI Responses API. Returns (output_text, error_message)."""
    client = get_openai_client()
    if client is None:
        if not settings.openai_api_key:
            return None, "OPENAI_API_KEY is not set in .env"
        return None, "LLM_MODEL is not set in .env"

    kwargs: dict[str, Any] = {"model": settings.llm_model, "input": prompt}
    if json_mode:
        kwargs["text"] = {"format": {"type": "json_object"}}

    try:
        response = client.responses.create(**kwargs)
        output_text = (getattr(response, "output_text", "") or "").strip()
        if not output_text:
            return None, "OpenAI returned an empty response"
        logger.info("OpenAI call succeeded (model=%s, json_mode=%s)", settings.llm_model, json_mode)
        return output_text, None
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        message = getattr(exc, "message", str(exc))
        error = f"OpenAI API error ({status}): {message}" if status else f"OpenAI API error: {message}"
        logger.warning(error)
        return None, error
    except Exception as exc:
        error = f"OpenAI call failed: {type(exc).__name__}: {exc}"
        logger.warning(error)
        return None, error


def extract_json_from_text(content: str) -> tuple[dict[str, Any] | None, str | None]:
    cleaned = content.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, flags=re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed, None
        return None, "OpenAI JSON response was not an object"
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed, None
            return None, "Extracted JSON block was not an object"
        except json.JSONDecodeError:
            return None, "OpenAI response was not valid JSON"

    return None, "OpenAI response did not contain parseable JSON"
