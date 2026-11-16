"""Core prompt-building and response helpers for CodeSathi."""

from __future__ import annotations

import json
import re
from typing import Any

APP_NAME = "CodeSathi"

BASE_INSTRUCTIONS = """You are CodeSathi, a patient AI programming learning assistant.
Your job is to help learners understand programming rather than merely copy answers.
Be accurate, clear, encouraging, and practical. Adapt explanations to the learner's level.
Use Markdown headings and code fences where useful. Explain jargon when first introduced.
Never claim that code was executed or tested unless it actually was. Do not pretend to inspect
files that were not provided. If the prompt is ambiguous, state the assumption you are making.
When discussing code, mention important edge cases and likely pitfalls where relevant.
"""


def build_prompt(
    task: str,
    user_input: str,
    *,
    history: list[dict[str, str]] | None = None,
    learner_level: str = "Beginner",
    language: str = "Python",
    learning_style: str = "Hint-first (help me reason it out)",
) -> str:
    """Create one self-contained prompt so each API call is easy to reproduce."""
    context_lines: list[str] = []
    for item in (history or [])[-12:]:
        role = "Learner" if item.get("role") == "user" else "Assistant"
        content = str(item.get("content", "")).strip()
        if content:
            context_lines.append(f"{role}: {content[:5000]}")
    context = "\n\n".join(context_lines) or "(No previous conversation.)"

    return f"""{BASE_INSTRUCTIONS}

LEARNER PROFILE
- Current level: {learner_level}
- Main programming language: {language}
- Preferred learning style: {learning_style}

TASK
{task.strip()}

RECENT CONVERSATION
{context}

LATEST LEARNER INPUT
{user_input.strip()}

Respond to the latest input while using the conversation context where relevant.
"""


def parse_quiz_json(raw_text: str) -> list[dict[str, Any]]:
    """Parse and validate a model-generated multiple-choice quiz."""
    cleaned = (raw_text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        # A few models wrap the JSON with explanatory text. Try the outermost object.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The model did not return valid quiz JSON. Please generate the quiz again.")
        try:
            payload = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("The quiz response could not be parsed. Please generate it again.") from exc

    questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(questions, list) or not questions:
        raise ValueError("The response did not contain any quiz questions. Please generate it again.")

    validated: list[dict[str, Any]] = []
    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        options = item.get("options", {})
        answer = str(item.get("answer", "")).strip().upper()
        explanation = str(item.get("explanation", "")).strip()
        if isinstance(options, list):
            options = {chr(65 + i): str(option) for i, option in enumerate(options[:4])}
        if not isinstance(options, dict):
            continue
        normalized_options = {str(k).strip().upper(): str(v).strip() for k, v in options.items()}
        normalized_options = {k: v for k, v in normalized_options.items() if k in {"A", "B", "C", "D"} and v}
        if question and all(k in normalized_options for k in ("A", "B", "C", "D")) and answer in normalized_options:
            validated.append(
                {
                    "question": question,
                    "options": normalized_options,
                    "answer": answer,
                    "explanation": explanation or "Review the concept related to this question.",
                }
            )

    if not validated:
        raise ValueError("The generated quiz had an unexpected format. Please generate it again.")
    return validated
