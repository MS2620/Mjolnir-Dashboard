import os
import sys
import time
import traceback
import subprocess
import requests
import psutil
import wmi
import threading
from dashboard_renderer import DashboardRenderer
from threading import Event
from app_paths import config_dir, themes_dir
from settings import load_settings, save_settings
from sensors import SensorProvider
from services import ServiceMonitor
from theme_manager import ThemeManager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from usb_display import MjolnirDisplay

def get_base_path():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    # When running from source, base is the backend folder
    return os.path.dirname(__file__)


base = get_base_path()

# In the bundle we have:
#   backend/...   (this script and usb_display.py)
#   frontend/...
#   tools/LibreHardwareMonitor/...
#
# When running from source (backend/main.py), we need to go up one level:
if not os.path.isdir(os.path.join(base, "frontend")):
    # Running from backend/main.py in dev
    base = os.path.abspath(os.path.join(base, ".."))

frontend_path = os.path.join(base, "frontend")
lhm_dir = os.path.join(base, "tools", "LibreHardwareMonitor")
LHM_EXE = os.path.join(lhm_dir, "LibreHardwareMonitor.exe")
LHM_URL = "http://localhost:8085/data.json"
THEMES_DIR = os.path.join(frontend_path, "themes")

# NVIDIA GPU
import pynvml
pynvml.nvmlInit()
device_count = pynvml.nvmlDeviceGetCount()
handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(device_count)]

# WMI object (kept but not used for CPU temp now)
wmi_obj = wmi.WMI()


LOG_PATH = os.path.join(os.getenv("TEMP", "."), "mjolnir_dashboard.log")

def log(*args):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(" ".join(str(x) for x in args) + "\n")

log("=== MjolnirDashboard start ===")
log("Python:", sys.executable)
log("Args:", sys.argv)
log("Base path:", base)
log("Frontend path:", frontend_path)
log("LHM dir:", lhm_dir)


# --- FastAPI app: metrics + static frontend ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend folder under /static
app.mount("/static", StaticFiles(directory=frontend_path, html=True), name="static")

lhm_proc = None

def lhm_is_ready():
    try:
        response = requests.get(LHM_URL, timeout=0.5)
        return response.ok and response.content.strip().startswith(b"{")
    except requests.RequestException:
        return False
    
def start_lhm():
    global lhm_proc

    # Reuse an existing elevated LHM instance if it is already serving data.
    if lhm_is_ready():
        print("LibreHardwareMonitor is already running.")
        log("LHM already running; reusing existing sensor endpoint.")
        return

    if not os.path.exists(LHM_EXE):
        message = f"LibreHardwareMonitor.exe not found at {LHM_EXE}"
        print(message)
        log(message)
        return

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE

    try:
        lhm_proc = subprocess.Popen(
            [LHM_EXE],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print(f"LibreHardwareMonitor started (PID: {lhm_proc.pid})")
        log("LHM started, PID:", lhm_proc.pid)

    except OSError as error:
        if error.winerror == 740:
            message = (
                "LibreHardwareMonitor needs administrator privileges. "
                "Run this terminal as Administrator, or start the packaged "
                "MjolnirDashboard.exe which has the admin manifest."
            )
            print(message)
            log(message)
            raise RuntimeError(message) from error
        raise

def walk_sensors(node):
    if isinstance(node, dict):
        yield node

        for child in node.get("Children", []):
            yield from walk_sensors(child)

    elif isinstance(node, list):
        for item in node:
            yield from walk_sensors(item)

def get_cpu_temp():
    try:
        response = requests.get(LHM_URL, timeout=1.0)
        response.raise_for_status()
        root = response.json()

        fallback = None

        for sensor in walk_sensors(root):
            if sensor.get("Type") != "Temperature":
                continue

            value = sensor.get("Value")
            sensor_id = sensor.get("SensorId", "")
            text = sensor.get("Text", "").lower()

            if value is None:
                continue

            try:
                temperature = float(
                    value.replace("°C", "")
                         .replace(" C", "")
                         .strip()
                )
            except (TypeError, ValueError):
                continue

            # Prefer CPU package / Tdie
            if sensor_id == "/amdcpu/0/temperature/2":
                return temperature

            if sensor_id == "/amdcpu/0/temperature/3":
                fallback = temperature

            if "cpu" in text or "tdie" in text:
                fallback = temperature

        return fallback

    except Exception as error:
        log("get_cpu_temp error:", repr(error))
        return None

def get_cpu_load():
    return psutil.cpu_percent(interval=None) / 100.0

def get_gpu_stats():
    if not handles:
        return None, None
    h = handles[0]
    try:
        temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
        util = pynvml.nvmlDeviceGetUtilizationRates(h).gpu
        return float(temp), float(util) / 100.0
    except Exception as e:
        log("get_gpu_stats error:", e)
        return None, None

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/sensors")
async def get_sensors():
    cpu_temp = get_cpu_temp()
    cpu_load = get_cpu_load()
    gpu_temp, gpu_load = get_gpu_stats()
    return {
        "cpu_temp": cpu_temp,
        "gpu_temp": gpu_temp,
        "cpu_load": cpu_load,
        "gpu_load": gpu_load,
    }

@app.get("/themes")
async def list_themes():
    if not os.path.isdir(THEMES_DIR):
        return []
    names = [
        d for d in os.listdir(THEMES_DIR)
        if os.path.isdir(os.path.join(THEMES_DIR, d))
    ]
    return sorted(names)

def run_api():
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")

def get_all_sensors():
    cpu_temp = get_cpu_temp()
    cpu_load = get_cpu_load()
    gpu_temp, gpu_load = get_gpu_stats()

    return {
        "cpu_temp": cpu_temp,
        "gpu_temp": gpu_temp,
        "cpu_load": cpu_load,
        "gpu_load": gpu_load,
    }


def native_render_and_stream():
    settings = load_settings()
    stop_event = Event()

    provider = SensorProvider(
        lhm_url=LHM_URL,
        log=log,
    )

    manager = ThemeManager(
        themes_dir=themes_dir(),
        settings=settings,
    )

    service_monitor = ServiceMonitor(
        config_dir() / "services.json",
    )

    display = MjolnirDisplay()
    display.jpeg_quality = settings["display"].get("jpegQuality", 85)

    try:
        display.open()

        # Add tray here after basic testing:
        # start_tray(manager, settings, save_settings, themes_dir(), config_dir(), stop_event)

        sensor_interval = settings.get("sensorIntervalSeconds", 1.0)
        next_sensor_update = 0.0
        snapshot = {}

        while not stop_event.is_set():
            now = time.monotonic()

            if now >= next_sensor_update:
                snapshot = provider.snapshot()

                if settings["modules"].get("services"):
                    snapshot["services"] = service_monitor.update_if_due()

                if settings["modules"].get("homeAssistant"):
                    snapshot["home_assistant"] = home_assistant.snapshot()

                next_sensor_update = now + sensor_interval

            image = manager.render(snapshot)
            display.send_frame(image)

            fps = max(int(settings.get("targetFps", 15)), 1)
            time.sleep(1 / fps)

    finally:
        manager.close()
        display.close()

def main():
    try:
        log("Entering main()")
        start_lhm()
        time.sleep(2.0)

        t_api = threading.Thread(target=run_api, daemon=True)
        t_api.start()
        log("API thread started")

        time.sleep(2.0)

        # No visible browser window is opened.
        native_render_and_stream()

    except Exception as e:
        log("Fatal error:")
        log(traceback.format_exc())
        input("Fatal error occurred. Press Enter to exit...")
        raise

if __name__ == "__main__":
    main()