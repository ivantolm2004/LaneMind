from __future__ import annotations

import json
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
            "model": model,
            "queued": False,
            "content": payload.get("message", {}).get("content", ""),
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
