from __future__ import annotations

import ctypes
import json
import os
import platform
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GpuInfo:
    name: str
    vram_gb: float


@dataclass(frozen=True)
class HardwareProfile:
    cpu: str
    cpu_threads: int
    ram_gb: float
    gpus: list[GpuInfo]


def _windows_creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def _total_ram_gb() -> float:
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return round(status.total_physical / (1024**3), 1)
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / (1024**3), 1)
    except (AttributeError, ValueError, OSError):
        return 0.0


def _nvidia_gpus() -> list[GpuInfo]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            creationflags=_windows_creation_flags(),
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    gpus: list[GpuInfo] = []
    for line in result.stdout.splitlines():
        try:
            name, memory_mb = [part.strip() for part in line.rsplit(",", 1)]
            gpus.append(GpuInfo(name=name, vram_gb=round(float(memory_mb) / 1024, 1)))
        except (ValueError, TypeError):
            continue
    return gpus


def detect_hardware() -> HardwareProfile:
    cpu = platform.processor().strip() or os.environ.get("PROCESSOR_IDENTIFIER", "Unknown CPU")
    return HardwareProfile(
        cpu=cpu,
        cpu_threads=os.cpu_count() or 1,
        ram_gb=_total_ram_gb(),
        gpus=_nvidia_gpus(),
    )


def is_dota_running() -> bool:
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq dota2.exe", "/NH"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=2,
                creationflags=_windows_creation_flags(),
                check=False,
            )
            return "dota2.exe" in result.stdout.lower()
        result = subprocess.run(
            ["pgrep", "-x", "dota2"], capture_output=True, timeout=2, check=False
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def choose_model(profile: HardwareProfile, dota_active: bool) -> dict[str, Any]:
    if dota_active:
        return {
            "mode": "paused",
            "model": None,
            "reason": "dota_active",
            "queue_inference": True,
        }
    max_vram = max((gpu.vram_gb for gpu in profile.gpus), default=0.0)
    if max_vram >= 12 and profile.ram_gb >= 24:
        model = "qwen3:8b"
        tier = "quality"
    elif max_vram >= 5 or profile.ram_gb >= 16:
        model = "qwen3:4b"
        tier = "balanced"
    elif profile.ram_gb >= 8:
        model = "qwen3:1.7b"
        tier = "light"
    else:
        return {
            "mode": "disabled",
            "model": None,
            "reason": "insufficient_memory",
            "queue_inference": False,
        }
    return {
        "mode": "ready",
        "model": model,
        "tier": tier,
        "reason": "hardware_profile",
        "queue_inference": False,
    }


def ollama_models() -> dict[str, Any]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=0.8) as response:
            payload = json.load(response)
        names = [str(model.get("name")) for model in payload.get("models", []) if model.get("name")]
        return {"available": True, "models": names}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return {"available": False, "models": []}


def runtime_status() -> dict[str, Any]:
    profile = detect_hardware()
    dota_active = is_dota_running()
    policy = choose_model(profile, dota_active)
    post_match_policy = choose_model(profile, False)
    policy["post_match_model"] = post_match_policy.get("model")
    ollama = ollama_models()
    recommended = policy.get("model") or policy.get("post_match_model")
    policy["model_installed"] = bool(
        recommended
        and any(name == recommended or name.startswith(f"{recommended}-") for name in ollama["models"])
    )
    return {
        "hardware": {
            **asdict(profile),
            "gpus": [asdict(gpu) for gpu in profile.gpus],
        },
        "dota_active": dota_active,
        "fps_protection": True,
        "policy": policy,
        "ollama": ollama,
    }
