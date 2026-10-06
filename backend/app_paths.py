import os
import shutil
import sys
from pathlib import Path


APP_NAME = "MjolnirDashboard"


def bundled_path(*parts: str) -> Path:
    """Path to read-only bundled resources, or project root during development."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS, *parts)

    return Path(__file__).resolve().parent.parent.joinpath(*parts)


def app_root() -> Path:
    """Writable directory beside the packaged EXE, or project root in development."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def ensure_user_folder(name: str) -> Path:
    target = app_root() / name
    source = bundled_path(name)

    if not target.exists() and source.exists():
        shutil.copytree(source, target)

    target.mkdir(parents=True, exist_ok=True)
    return target


def themes_dir() -> Path:
    return ensure_user_folder("themes")


def config_dir() -> Path:
    return ensure_user_folder("config")


def logs_dir() -> Path:
    path = app_root() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path