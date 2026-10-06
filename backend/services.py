import json
import time
from pathlib import Path

import requests


class ServiceMonitor:
    def __init__(self, config_path: Path, interval_seconds: float = 30):
        self.config_path = config_path
        self.interval_seconds = interval_seconds
        self.services = []
        self.last_check = 0.0
        self.status = {}

        self.reload()

    def reload(self):
        if not self.config_path.exists():
            self.services = []
            return

        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.services = [
            service
            for service in data.get("services", [])
            if service.get("enabled", True)
        ]

    def update_if_due(self):
        if time.monotonic() - self.last_check < self.interval_seconds:
            return self.status

        self.last_check = time.monotonic()
        results = {}

        for service in self.services:
            name = service.get("name", "Unknown")
            url = service.get("url", "")

            try:
                start = time.monotonic()
                response = requests.get(url, timeout=5, allow_redirects=True)
                elapsed_ms = round((time.monotonic() - start) * 1000)

                results[name] = {
                    "online": 200 <= response.status_code < 500,
                    "status_code": response.status_code,
                    "latency_ms": elapsed_ms,
                }
            except requests.RequestException:
                results[name] = {
                    "online": False,
                    "status_code": None,
                    "latency_ms": None,
                }

        self.status = results
        return self.status