import time
from pathlib import Path

import psutil
import pynvml
import requests


class SensorProvider:
    def __init__(self, lhm_url: str, log):
        self.lhm_url = lhm_url
        self.log = log

        self.last_net = psutil.net_io_counters()
        self.last_net_time = time.monotonic()

        try:
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception as error:
            self.gpu_handle = None
            self.log("NVML unavailable:", repr(error))

    def walk_sensors(self, node):
        if isinstance(node, dict):
            yield node
            for child in node.get("Children", []):
                yield from self.walk_sensors(child)

        elif isinstance(node, list):
            for child in node:
                yield from self.walk_sensors(child)

    def cpu_temp(self):
        try:
            response = requests.get(self.lhm_url, timeout=1.0)
            response.raise_for_status()

            self.log("LHM JSON sample:", response.text[:200])  # TEMP DEBUG

            fallback = None

            for sensor in self.walk_sensors(response.json()):
                if sensor.get("Type") != "Temperature":
                    continue

                value = sensor.get("Value")
                sensor_id = sensor.get("SensorId", "")

                if not value:
                    continue

                try:
                    temp = float(
                        value.replace("°C", "")
                        .replace(" C", "")
                        .strip()
                    )
                except (TypeError, ValueError):
                    continue

                # Ryzen 7800X3D preferred temperature
                if sensor_id == "/amdcpu/0/temperature/2":
                    return temp

                # CCD Tdie fallback
                if sensor_id == "/amdcpu/0/temperature/3":
                    fallback = temp

            self.log("CPU temp result:", fallback)
            return fallback

        except Exception as error:
            self.log("CPU temperature error:", repr(error))
            return None

    def gpu_stats(self):
        if self.gpu_handle is None:
            return {
                "temp": None,
                "load": None,
                "power_w": None,
                "memory_used_mb": None,
                "memory_total_mb": None,
                "clock_mhz": None,
            }

        try:
            utilization = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
            memory = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)

            try:
                power_w = pynvml.nvmlDeviceGetPowerUsage(self.gpu_handle) / 1000
            except Exception:
                power_w = None

            try:
                clock_mhz = pynvml.nvmlDeviceGetClockInfo(
                    self.gpu_handle,
                    pynvml.NVML_CLOCK_GRAPHICS,
                )
            except Exception:
                clock_mhz = None

            return {
                "temp": float(
                    pynvml.nvmlDeviceGetTemperature(
                        self.gpu_handle,
                        pynvml.NVML_TEMPERATURE_GPU,
                    )
                ),
                "load": utilization.gpu / 100.0,
                "power_w": power_w,
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_total_mb": memory.total / (1024 * 1024),
                "clock_mhz": clock_mhz,
            }

        except Exception as error:
            self.log("GPU sensor error:", repr(error))
            return {
                "temp": None,
                "load": None,
                "power_w": None,
                "memory_used_mb": None,
                "memory_total_mb": None,
                "clock_mhz": None,
            }

    def network_stats(self):
        now = time.monotonic()
        current = psutil.net_io_counters()

        elapsed = max(now - self.last_net_time, 0.001)
        download_bps = (current.bytes_recv - self.last_net.bytes_recv) / elapsed
        upload_bps = (current.bytes_sent - self.last_net.bytes_sent) / elapsed

        self.last_net = current
        self.last_net_time = now

        return {
            "download_bps": max(download_bps, 0),
            "upload_bps": max(upload_bps, 0),
        }

    def disk_stats(self):
        root = Path.home().anchor or "C:\\"

        try:
            usage = psutil.disk_usage(root)
            return {
                "used_gb": usage.used / (1024 ** 3),
                "total_gb": usage.total / (1024 ** 3),
                "load": usage.percent / 100.0,
            }
        except Exception:
            return {
                "used_gb": None,
                "total_gb": None,
                "load": None,
            }

    def snapshot(self):
        vm = psutil.virtual_memory()
        gpu = self.gpu_stats()

        snap = {
            "cpu": {
                "temp": self.cpu_temp(),
                "load": psutil.cpu_percent(interval=None) / 100.0,
                "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else None,
            },
            "gpu": gpu,
            "ram": {
                "used_gb": vm.used / (1024 ** 3),
                "total_gb": vm.total / (1024 ** 3),
                "load": vm.percent / 100.0,
            },
            "disk": self.disk_stats(),
            "network": self.network_stats(),
            "time": time.strftime("%H:%M"),
            "date": time.strftime("%a %d %b"),
        }

        self.log("Snapshot:", snap)  # TEMP DEBUG
        return snap