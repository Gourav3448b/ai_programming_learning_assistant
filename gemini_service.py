"""Small wrapper around Google's official Gen AI Python SDK."""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types


class GeminiServiceError(RuntimeError):
    """An actionable error raised for a failed Gemini request."""


def call_gemini(
    prompt: str,
    *,
    api_key: str,
    model: str,
    json_mode: bool = False,
    temperature: float = 0.45,
    max_output_tokens: int = 4096,
) -> str:
    if not api_key.strip():
        raise GeminiServiceError("A Gemini API key is required. Add it in settings or your .env file.")

    config_kwargs: dict[str, Any] = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    try:
        with genai.Client(api_key=api_key.strip()) as client:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
    except Exception as exc:
        raise GeminiServiceError(f"Gemini request failed: {exc}") from exc

    result = getattr(response, "text", None)
    if not result or not str(result).strip():
        raise GeminiServiceError("Gemini returned an empty response. Please try again with a shorter prompt.")
    return str(result).strip()
