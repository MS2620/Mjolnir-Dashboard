import json
import os
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont


WIDTH = 640
HEIGHT = 480


def hex_to_rgba(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)

    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)

    return red, green, blue, alpha


class VideoBackground:
    def __init__(self, path: str | None):
        self.path = path
        self.capture = None

        if path and os.path.isfile(path):
            self.capture = cv2.VideoCapture(path)

    def read(self) -> Image.Image | None:
        if self.capture is None:
            return None

        ok, frame = self.capture.read()

        if not ok:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.capture.read()

        if not ok or frame is None:
            return None

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame)
        return cover_resize(image, WIDTH, HEIGHT)

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None


def cover_resize(image: Image.Image, width: int, height: int) -> Image.Image:
    source_width, source_height = image.size
    scale = max(width / source_width, height / source_height)

    resized_width = round(source_width * scale)
    resized_height = round(source_height * scale)

    image = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)

    left = (resized_width - width) // 2
    top = (resized_height - height) // 2

    return image.crop((left, top, left + width, top + height))


class DashboardRenderer:
    def __init__(self, theme_dir: str):
        self.theme_dir = Path(theme_dir)
        self.theme = self._load_theme()

        background = self.theme.get("background", {})
        video_file = background.get("file")
        video_path = self.theme_dir / video_file if video_file else None

        self.video = VideoBackground(str(video_path) if video_path else None)
        self.fonts = self._load_fonts()

    def _load_theme(self) -> dict:
        path = self.theme_dir / "theme.json"

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _load_fonts(self) -> dict:
        text = self.theme["text"]
        font_path = text.get("font", r"C:\Windows\Fonts\segoeuib.ttf")

        return {
            "label": ImageFont.truetype(font_path, text.get("labelSize", 14)),
            "value": ImageFont.truetype(font_path, text.get("valueSize", 28)),
        }

    def render(self, sensors: dict) -> Image.Image:
        background_config = self.theme.get("background", {})
        video_frame = self.video.read()

        if video_frame is not None:
            brightness = float(background_config.get("brightness", 1.0))
            base = self._adjust_brightness(video_frame, brightness)
        else:
            base = Image.new("RGB", (WIDTH, HEIGHT), "#080b10")

        overlay_config = self.theme.get("overlay", {})
        overlay_color = hex_to_rgba(
            overlay_config.get("color", "#000000"),
            round(float(overlay_config.get("opacity", 0.0)) * 255),
        )

        frame = base.convert("RGBA")
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), overlay_color)
        frame = Image.alpha_composite(frame, overlay)

        self._draw_four_cards(frame, sensors)
        return frame.convert("RGB")

    def _adjust_brightness(self, image: Image.Image, brightness: float) -> Image.Image:
        if brightness >= 0.999:
            return image

        overlay_alpha = round((1.0 - brightness) * 255)
        darkener = Image.new("RGBA", image.size, (0, 0, 0, overlay_alpha))
        return Image.alpha_composite(image.convert("RGBA"), darkener).convert("RGB")

    def _draw_four_cards(self, frame: Image.Image, sensors: dict):
        draw = ImageDraw.Draw(frame, "RGBA")

        cards = self.theme["cards"]
        text = self.theme["text"]
        thresholds = self.theme.get("thresholds", {})

        padding = int(cards.get("padding", 16))
        gap = int(cards.get("gap", 12))
        radius = int(cards.get("radius", 10))

        card_width = (WIDTH - padding * 2 - gap) // 2
        card_height = (HEIGHT - padding * 2 - gap) // 2

        values = [
            ("CPU Temp", sensors.get("cpu_temp"), "temperature", thresholds.get("cpuWarning", 80), thresholds.get("cpuCritical", 90)),
            ("GPU Temp", sensors.get("gpu_temp"), "temperature", thresholds.get("gpuWarning", 80), thresholds.get("gpuCritical", 90)),
            ("CPU Load", sensors.get("cpu_load"), "load", None, None),
            ("GPU Load", sensors.get("gpu_load"), "load", None, None),
        ]

        positions = [
            (padding, padding),
            (padding + card_width + gap, padding),
            (padding, padding + card_height + gap),
            (padding + card_width + gap, padding + card_height + gap),
        ]

        card_fill = hex_to_rgba(
            cards.get("background", "#081522"),
            round(float(cards.get("opacity", 0.65)) * 255),
        )
        border = hex_to_rgba(
            cards.get("border", "#2cb9da"),
            round(float(cards.get("borderOpacity", 0.25)) * 255),
        )

        for ((label, value, kind, warning, critical), (x, y)) in zip(values, positions):
            box = (x, y, x + card_width, y + card_height)

            draw.rounded_rectangle(
                box,
                radius=radius,
                fill=card_fill,
                outline=border,
                width=1,
            )

            if kind == "temperature":
                display = "-- °C" if value is None else f"{value:.1f} °C"
                color = self._temperature_color(value, warning, critical)
            else:
                display = "-- %" if value is None else f"{value * 100:.0f} %"
                color = hex_to_rgba(text.get("normalColor", "#00eaff"))

            self._centered_text(
                draw,
                label,
                x + card_width // 2,
                y + card_height // 2 - 24,
                self.fonts["label"],
                hex_to_rgba(text.get("labelColor", "#a6b5c4")),
            )

            self._glow_text(
                frame,
                display,
                x + card_width // 2,
                y + card_height // 2 + 10,
                self.fonts["value"],
                color,
                enabled=bool(text.get("glow", True)),
            )

    def _temperature_color(self, value, warning, critical):
        text = self.theme["text"]

        if value is not None and critical is not None and value >= critical:
            return hex_to_rgba(text.get("criticalColor", "#ff5e69"))

        if value is not None and warning is not None and value >= warning:
            return hex_to_rgba(text.get("warningColor", "#ffe44d"))

        return hex_to_rgba(text.get("normalColor", "#00eaff"))

    def _centered_text(self, draw, value, center_x, center_y, font, color):
        box = draw.textbbox((0, 0), value, font=font)
        x = center_x - (box[2] - box[0]) / 2
        y = center_y - (box[3] - box[1]) / 2
        draw.text((x, y), value, font=font, fill=color)

    def _glow_text(self, frame, value, center_x, center_y, font, color, enabled=True):
        draw = ImageDraw.Draw(frame, "RGBA")
        box = draw.textbbox((0, 0), value, font=font)
        x = center_x - (box[2] - box[0]) / 2
        y = center_y - (box[3] - box[1]) / 2

        if enabled:
            glow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow, "RGBA")
            glow_draw.text((x, y), value, font=font, fill=(color[0], color[1], color[2], 155))
            glow = glow.filter(ImageFilter.GaussianBlur(6))
            frame.alpha_composite(glow)

        draw.text((x, y), value, font=font, fill=color)

    def close(self):
        self.video.close()