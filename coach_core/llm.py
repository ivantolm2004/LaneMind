from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable

from .runtime import runtime_status


class LocalModelProvider:
    """Ollama adapter with an unconditional Dota FPS safety gate."""

    def __init__(self, status_provider: Callable[[], dict[str, Any]] = runtime_status):
        self.status_provider = status_provider

    def generate(self, report: dict[str, Any], language: str = "ru") -> dict[str, Any]:
        status = self.status_provider()
        policy = status["policy"]
        if status["dota_active"] or policy["mode"] == "paused":
            return {
                "status": "deferred",
                "reason": "dota_active",
                "queued": True,
                "content": None,
            }
        if not status["ollama"]["available"]:
            return {
                "status": "unavailable",
                "reason": "ollama_unavailable",
                "queued": False,
                "content": None,
            }
        model = policy.get("model")
        if not model or not policy.get("model_installed"):
            return {
                "status": "unavailable",
                "reason": "model_not_installed",
                "recommended_model": policy.get("post_match_model"),
                "queued": False,
                "content": None,
            }

        prompt = {
            "language": language,
            "instruction": (
                "Explain the supplied Dota 2 coaching findings clearly. Use only supplied facts; "
                "never invent events, timings, items, or player actions. Return a concise summary."
            ),
            "report": report,
        }
        body = json.dumps(
            {
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You are a careful Dota 2 coaching assistant."},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                "options": {"temperature": 0.2},
                "keep_alive": "0",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
        return {
            "status": "complete",
            "reason": "local_model",
            "provider": "ollama",
            "model": model,
            "queued": False,
            "content": payload.get("message", {}).get("content", ""),
        }


class GeminiModelProvider:
    """Gemini adapter for post-match coaching with the same FPS safety gate."""

    DEFAULT_MODEL = "gemini-3.1-flash-lite"

    def __init__(
        self,
        status_provider: Callable[[], dict[str, Any]] = runtime_status,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.status_provider = status_provider
        self.api_key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
        self.model = (model or os.environ.get("LANEMIND_GEMINI_MODEL", self.DEFAULT_MODEL)).strip()

    @staticmethod
    def _render_report(payload: dict[str, Any], language: str) -> str:
        summary = str(payload.get("summary", "")).strip()
        priorities = payload.get("priorities", [])
        labels = {
            "ru": ("Почему", "Что делать", "Упражнение"),
            "en": ("Why", "Action", "Exercise"),
        }
        evidence_label, action_label, exercise_label = labels.get(language, labels["en"])
        sections = [summary] if summary else []
        for index, item in enumerate(priorities[:3], 1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            evidence = str(item.get("evidence", "")).strip()
            action = str(item.get("action", "")).strip()
            exercise = str(item.get("exercise", "")).strip()
            lines = [f"{index}. {title}" if title else f"{index}."]
            if evidence:
                lines.append(f"{evidence_label}: {evidence}")
            if action:
                lines.append(f"{action_label}: {action}")
            if exercise:
                lines.append(f"{exercise_label}: {exercise}")
            sections.append("\n".join(lines))
        return "\n\n".join(sections).strip()

    def generate(self, report: dict[str, Any], language: str = "ru") -> dict[str, Any]:
        status = self.status_provider()
        if status.get("dota_active"):
            return {
                "status": "deferred",
                "reason": "dota_active",
                "provider": "gemini",
                "queued": True,
                "content": None,
            }
        if not self.api_key:
            return {
                "status": "unavailable",
                "reason": "gemini_key_missing",
                "provider": "gemini",
                "queued": False,
                "content": None,
            }

        language_name = "Russian" if language == "ru" else "English"
        prompt = {
            "instruction": (
                f"Write the coaching report in {language_name}. Interpret patterns and priorities, but use only "
                "facts present in the supplied deterministic report. Do not invent timings, map positions, items, "
                "cooldowns, hero actions, or causes that are absent from the data. Explicitly acknowledge when "
                "summary-level data cannot prove a claim. Focus on the three highest-value changes."
            ),
            "report": report,
        }
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "priorities": {
                    "type": "array",
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "evidence": {"type": "string"},
                            "action": {"type": "string"},
                            "exercise": {"type": "string"},
                        },
                        "required": ["title", "evidence", "action", "exercise"],
                    },
                },
                "confidence": {"type": "number"},
            },
            "required": ["summary", "priorities", "confidence"],
        }
        body = json.dumps(
            {
                "systemInstruction": {
                    "parts": [
                        {
                            "text": (
                                "You are LaneMind, a careful Dota 2 post-match coach. Never present an inference "
                                "as an observed event. Your advice must be grounded in the provided report."
                            )
                        }
                    ]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": json.dumps(prompt, ensure_ascii=False)}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema,
                },
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                response_payload = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8", errors="replace"))
                message = error_payload.get("error", {}).get("message", str(exc))
            except (json.JSONDecodeError, AttributeError):
                message = str(exc)
            raise ValueError(f"Gemini API error: {message}") from exc

        candidates = response_payload.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(str(part.get("text", "")) for part in parts).strip()
        if not text:
            reason = candidates[0].get("finishReason", "empty_response") if candidates else "empty_response"
            raise ValueError(f"Gemini returned no coaching report ({reason})")
        try:
            structured = json.loads(text)
            content = self._render_report(structured, language)
        except json.JSONDecodeError:
            content = text
        usage = response_payload.get("usageMetadata", {})
        return {
            "status": "complete",
            "reason": "cloud_model",
            "provider": "gemini",
            "model": self.model,
            "queued": False,
            "content": content,
            "usage": {
                "input_tokens": usage.get("promptTokenCount", 0),
                "output_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
        }


def pull_model(model: str) -> dict[str, Any]:
    body = json.dumps({"model": model, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/pull",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=3600) as response:
        payload = json.load(response)
    return {"model": model, "status": payload.get("status", "success")}
