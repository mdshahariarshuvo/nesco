import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

AI_AGENT_PROVIDER = os.getenv("AI_AGENT_PROVIDER", "huggingface").lower()
AI_AGENT_ENABLED = os.getenv("AI_AGENT_ENABLED", "false").lower() == "true"
AI_AGENT_KEY = os.getenv("AI_AGENT_KEY")

if os.getenv("AI_AGENT_MODEL"):
    AI_AGENT_MODEL = os.getenv("AI_AGENT_MODEL") or ""
else:
    AI_AGENT_MODEL = (
        "gemini-1.5-flash" if AI_AGENT_PROVIDER == "gemini" else "mistralai/Mistral-7B-Instruct"
    )

if os.getenv("AI_AGENT_URL"):
    AI_AGENT_URL = os.getenv("AI_AGENT_URL") or ""
else:
    if AI_AGENT_PROVIDER == "gemini":
        AI_AGENT_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{AI_AGENT_MODEL}:generateContent"
    else:
        AI_AGENT_URL = f"https://api-inference.huggingface.co/models/{AI_AGENT_MODEL}"

AI_AGENT_TIMEOUT = int(os.getenv("AI_AGENT_TIMEOUT", "40"))
AI_AGENT_TEMPERATURE = float(os.getenv("AI_AGENT_TEMPERATURE", "0.2"))

SYSTEM_PROMPT = (
    "You route user messages for the NESCO Meter Helper bot.\n"
    "Always return pure JSON with these fields: \n"
    "intent: one of [START, HELP, LIST_METERS, CHECK_BALANCES, TOGGLE_REMINDER, SMALL_TALK, UNKNOWN].\n"
    "meter_name: optional string; meter_number: optional string; response: optional reply text.\n"
    "If user asks to check balance or similar, intent=CHECK_BALANCES.\n"
    "If they want to list meters, intent=LIST_METERS.\n"
    "If greeting or casual chat, intent=SMALL_TALK and add friendly response text.\n"
    "If unsure, intent=UNKNOWN.\n"
)


def _build_prompt(user_text: str, meter_context: Optional[List[Dict[str, Any]]]) -> str:
    context_block = ""
    if meter_context:
        summary = ", ".join(
            f"{m.get('name')} ({m.get('number')})" for m in meter_context[:5]
        )
        context_block = f"Known meters: {summary}.\n"
    return f"{SYSTEM_PROMPT}{context_block}User: {user_text}\nJSON:"  # noqa: E501


def _extract_generated_text(payload: Any) -> str:
    if isinstance(payload, list) and payload:
        candidate = payload[0]
        if isinstance(candidate, dict):
            return candidate.get("generated_text", "") or candidate.get("text", "")
    if isinstance(payload, dict):
        if "choices" in payload:
            choices = payload["choices"]
            if choices:
                return choices[0].get("message", {}).get("content", "")
        return payload.get("generated_text", "") or payload.get("text", "")
    return ""


def _extract_gemini_text(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    candidates = payload.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        for part in parts:
            text = part.get("text") if isinstance(part, dict) else None
            if text:
                return text
    return ""


def _call_huggingface(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {AI_AGENT_KEY}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 256,
            "temperature": AI_AGENT_TEMPERATURE,
            "return_full_text": False,
        },
        "model": AI_AGENT_MODEL,
    }
    response = requests.post(
        AI_AGENT_URL,
        headers=headers,
        json=payload,
        timeout=AI_AGENT_TIMEOUT,
    )
    response.raise_for_status()
    return _extract_generated_text(response.json())


def _call_gemini(prompt: str) -> str:
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {
            "temperature": AI_AGENT_TEMPERATURE,
            "maxOutputTokens": 512,
        },
    }
    response = requests.post(
        AI_AGENT_URL,
        params={"key": AI_AGENT_KEY},
        json=payload,
        timeout=AI_AGENT_TIMEOUT,
    )
    response.raise_for_status()
    return _extract_gemini_text(response.json())


def _parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def interpret_message(user_text: str, meter_context: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    if not (AI_AGENT_ENABLED and AI_AGENT_URL and AI_AGENT_KEY):
        return None

    prompt = _build_prompt(user_text, meter_context)

    try:
        if AI_AGENT_PROVIDER == "gemini":
            generated_text = _call_gemini(prompt)
        else:
            generated_text = _call_huggingface(prompt)
        parsed = _parse_json_block(generated_text)
        if not parsed:
            logger.warning("AI agent returned unparsable payload: %s", generated_text)
            return None
        return parsed
    except requests.RequestException as exc:
        logger.error("AI agent request failed: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("AI agent unexpected error: %s", exc)
    return None


def ai_enabled() -> bool:
    return AI_AGENT_ENABLED and AI_AGENT_URL is not None and AI_AGENT_KEY is not None
