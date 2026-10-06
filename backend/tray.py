import os
import threading

import pystray
from PIL import Image, ImageDraw


def make_icon():
    icon = Image.new("RGBA", (64, 64), (7, 15, 25, 255))
    draw = ImageDraw.Draw(icon)

    draw.rounded_rectangle(
        (8, 8, 56, 56),
        radius=10,
        outline=(0, 234, 255, 255),
        width=3,
    )
    draw.text((20, 18), "M", fill=(0, 234, 255, 255))

    return icon


class TrayApp:
    def __init__(self, theme_manager, settings, save_settings, themes_dir, config_dir, stop_event):
        self.theme_manager = theme_manager
        self.settings = settings
        self.save_settings = save_settings
        self.themes_dir = themes_dir
        self.config_dir = config_dir
        self.stop_event = stop_event
        self.icon = None

    def _set_theme(self, name):
        def action(icon, item):
            self.theme_manager.set_theme(name)
            self.settings["activeTheme"] = name
            self.save_settings(self.settings)
        return action

    def _theme_items(self):
        return [
            pystray.MenuItem(
                name,
                self._set_theme(name),
                checked=lambda item, n=name: self.theme_manager.active_theme == n,
            )
            for name in self.theme_manager.available_themes()
        ]

    def _toggle_rotation(self, icon, item):
        rotation = self.settings.setdefault("themeRotation", {})
        rotation["enabled"] = not rotation.get("enabled", False)
        self.save_settings(self.settings)
        self.theme_manager.settings = self.settings

    def _open_folder(self, folder):
        def action(icon, item):
            os.startfile(folder)
        return action

    def _exit(self, icon, item):
        self.stop_event.set()
        icon.stop()

    def run(self):
        self.icon = pystray.Icon(
            "MjolnirDashboard",
            make_icon(),
            "Mjolnir Dashboard",
            menu=pystray.Menu(
                pystray.MenuItem(
                    "Themes",
                    pystray.Menu(lambda: self._theme_items()),
                ),
                pystray.MenuItem(
                    "Rotate themes",
                    self._toggle_rotation,
                    checked=lambda item: self.settings.get("themeRotation", {}).get("enabled", False),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Open themes folder", self._open_folder(str(self.themes_dir))),
                pystray.MenuItem("Open config folder", self._open_folder(str(self.config_dir))),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", self._exit),
            ),
        )

        self.icon.run()


def start_tray(*args):
    tray = TrayApp(*args)
    thread = threading.Thread(target=tray.run, daemon=True)
    thread.start()
    return tray