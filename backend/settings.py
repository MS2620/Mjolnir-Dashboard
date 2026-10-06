import json
from copy import deepcopy
from pathlib import Path

from app_paths import config_dir


DEFAULT_SETTINGS = {
    "activeTheme": "dark-neon",
    "targetFps": 15,
    "sensorIntervalSeconds": 1.0,
    "themeRotation": {
        "enabled": False,
        "intervalMinutes": 10,
        "themes": [],
    },
    "display": {
        "width": 640,
        "height": 480,
        "jpegQuality": 85,
    },
    "modules": {
        "cpu": True,
        "gpu": True,
        "ram": True,
        "network": True,
        "disks": True,
        "services": False,
        "homeAssistant": False,
    },
    "homeAssistant": {
        "enabled": False,
        "url": "",
        "token": "",
        "entities": [],
    },
}


def deep_merge(default: dict, custom: dict) -> dict:
    merged = deepcopy(default)

    for key, value in custom.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def settings_path() -> Path:
    return config_dir() / "settings.json"


def load_settings() -> dict:
    path = settings_path()

    if not path.exists():
        save_settings(DEFAULT_SETTINGS)
        return deepcopy(DEFAULT_SETTINGS)

    try:
        custom = json.loads(path.read_text(encoding="utf-8"))
        return deep_merge(DEFAULT_SETTINGS, custom)
    except (json.JSONDecodeError, OSError):
        return deepcopy(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    settings_path().write_text(
        json.dumps(settings, indent=2),
        encoding="utf-8",
    )