import time
from pathlib import Path

from dashboard_renderer import DashboardRenderer


class ThemeManager:
    def __init__(self, themes_dir: Path, settings: dict):
        self.themes_dir = themes_dir
        self.settings = settings
        self.renderer = None
        self.active_theme = None
        self.next_rotation = 0.0

        self.set_theme(settings.get("activeTheme", "dark-neon"))

    def available_themes(self):
        return sorted(
            folder.name
            for folder in self.themes_dir.iterdir()
            if folder.is_dir() and (folder / "theme.json").exists()
        )

    def set_theme(self, name: str):
        path = self.themes_dir / name

        if not (path / "theme.json").exists():
            themes = self.available_themes()
            if not themes:
                raise RuntimeError("No valid themes found")
            name = themes[0]
            path = self.themes_dir / name

        if self.renderer:
            self.renderer.close()

        self.renderer = DashboardRenderer(str(path))
        self.active_theme = name
        self._schedule_rotation()

    def _schedule_rotation(self):
        rotation = self.settings.get("themeRotation", {})

        if not rotation.get("enabled", False):
            self.next_rotation = 0.0
            return

        minutes = max(float(rotation.get("intervalMinutes", 10)), 0.25)
        self.next_rotation = time.monotonic() + minutes * 60

    def maybe_rotate(self):
        if not self.next_rotation or time.monotonic() < self.next_rotation:
            return

        configured = self.settings.get("themeRotation", {}).get("themes", [])
        usable = [name for name in configured if (self.themes_dir / name / "theme.json").exists()]

        if len(usable) < 2:
            self._schedule_rotation()
            return

        current = usable.index(self.active_theme) if self.active_theme in usable else -1
        self.set_theme(usable[(current + 1) % len(usable)])

    def render(self, sensors: dict):
        self.maybe_rotate()
        return self.renderer.render(sensors)

    def close(self):
        if self.renderer:
            self.renderer.close()