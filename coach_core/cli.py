from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .analysis import analyze_match, build_training_plan
from .demo import DEMO_MATCH
from .llm import GeminiModelProvider, LocalModelProvider, pull_model
from .runtime import MODEL_CATALOG, runtime_status
from .store import Store


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "LaneMind/0.1"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def normalize_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "players" in payload:
        return [payload]
    if isinstance(payload, dict) and isinstance(payload.get("matches"), list):
        return payload["matches"]
    if isinstance(payload, list):
        return payload
    raise ValueError("Unsupported JSON format: expected an OpenDota match or a list of matches")


def app_runtime_status(store: Store) -> dict[str, Any]:
    selected_model = store.get_setting("selected_model", "auto") or "auto"
    provider = store.get_setting("ai_provider", "local") or "local"
    status = runtime_status(selected_model)
    status["ai_provider"] = provider
    status["gemini"] = {
        "configured": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
        "model": os.environ.get("LANEMIND_GEMINI_MODEL", GeminiModelProvider.DEFAULT_MODEL),
    }
    return status


def process(store: Store, request: dict[str, Any]) -> Any:
    action = request.get("action")
    if action == "runtime_status":
        return app_runtime_status(store)
    if action == "set_ai_provider":
        provider = str(request.get("provider", "local"))
        if provider not in {"gemini", "local", "off"}:
            raise ValueError(f"Unsupported AI provider: {provider}")
        store.set_setting("ai_provider", provider)
        return app_runtime_status(store)
    if action == "set_model":
        model = str(request.get("model", "auto"))
        valid_models = {"auto", "off", *(item["id"] for item in MODEL_CATALOG)}
        if model not in valid_models:
            raise ValueError(f"Unsupported model: {model}")
        store.set_setting("selected_model", model)
        return app_runtime_status(store)
    if action == "pull_model":
        model = str(request["model"])
        if model not in {item["id"] for item in MODEL_CATALOG}:
            raise ValueError(f"Unsupported model: {model}")
        status = app_runtime_status(store)
        if status["dota_active"]:
            return {"status": "deferred", "reason": "dota_active", "model": model}
        if not status["ollama"]["available"]:
            raise ValueError("Ollama is not running. Install or start Ollama before downloading a model.")
        result = pull_model(model)
        return {**result, "runtime": app_runtime_status(store)}
    if action == "generate_summary":
        match_id = str(request["match_id"])
        language = str(request.get("language", "ru"))
        report = store.report(match_id)
        if not report:
            raise ValueError(f"Unknown match: {match_id}")
        selected = store.get_setting("selected_model", "auto") or "auto"
        provider_name = store.get_setting("ai_provider", "local") or "local"
        if provider_name == "off":
            return {"status": "unavailable", "reason": "ai_disabled", "queued": False, "content": None}
        if provider_name == "gemini":
            provider = GeminiModelProvider(lambda: runtime_status(selected))
        else:
            provider = LocalModelProvider(lambda: runtime_status(selected))
        result = provider.generate(report, language)
        if result["status"] == "complete":
            store.save_ai_summary(match_id, result["model"], language, result["content"])
        return result
    if action == "status":
        reports = store.reports()
        return {"version": "0.3.0", "reports": reports, "plan": build_training_plan(reports)}
    if action == "demo":
        report = analyze_match(DEMO_MATCH, 123456789)
        store.save_match(DEMO_MATCH, report, 123456789, "demo")
        reports = store.reports()
        return {"report": report, "reports": reports, "plan": build_training_plan(reports)}
    if action == "sync_player":
        account_id = int(request["account_id"])
        count = min(max(int(request.get("count", 10)), 1), 20)
        summaries = fetch_json(f"https://api.opendota.com/api/players/{account_id}/recentMatches")[:count]
        imported = []
        errors = []
        for summary in summaries:
            match_id = summary.get("match_id")
            try:
                match = fetch_json(f"https://api.opendota.com/api/matches/{match_id}")
                report = analyze_match(match, account_id)
                store.save_match(match, report, account_id, "opendota")
                imported.append(report)
            except Exception as exc:
                errors.append({"match_id": str(match_id), "error": str(exc)})
        reports = store.reports()
        return {"imported": imported, "errors": errors, "reports": reports, "plan": build_training_plan(reports)}
    if action == "import_json":
        payload = json.loads(str(request["content"]))
        account_id = int(request["account_id"]) if request.get("account_id") else None
        imported = []
        for match in normalize_payload(payload):
            report = analyze_match(match, account_id)
            store.save_match(match, report, account_id, "json")
            imported.append(report)
        reports = store.reports()
        return {"imported": imported, "reports": reports, "plan": build_training_plan(reports)}
    if action == "import_replay":
        replay_path = Path(str(request["path"]))
        if replay_path.suffix.lower() != ".dem":
            raise ValueError("Expected a .dem replay file")
        raise ValueError(
            "Replay detected. Native .dem parsing is the next milestone; export the match JSON from OpenDota for this prototype."
        )
    raise ValueError(f"Unknown action: {action}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    store = Store(args.db)
    try:
        request = json.load(sys.stdin)
        data = process(store, request)
        print(json.dumps({"ok": True, "data": data}, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"Unexpected core error: {exc}"}, ensure_ascii=False))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
