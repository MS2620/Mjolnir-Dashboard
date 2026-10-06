import os
import sys
import time
import traceback
import subprocess
import requests
import psutil
from threading import Event
from app_paths import config_dir, themes_dir
from settings import load_settings, save_settings
from sensors import SensorProvider
from services import ServiceMonitor
from theme_manager import ThemeManager

from usb_display import MjolnirDisplay

def get_base_path():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(__file__)

base = get_base_path()

if not os.path.isdir(os.path.join(base, "tools", "LibreHardwareMonitor")):
    base = os.path.abspath(os.path.join(base, ".."))

lhm_dir = os.path.join(base, "tools", "LibreHardwareMonitor")
LHM_EXE = os.path.join(lhm_dir, "LibreHardwareMonitor.exe")
LHM_URL = "http://localhost:8085/data.json"

LOG_PATH = os.path.join(os.getenv("TEMP", "."), "mjolnir_dashboard.log")

def log(*args):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(" ".join(str(x) for x in args) + "\n")

log("=== MjolnirDashboard start ===")
log("Python:", sys.executable)
log("Args:", sys.argv)
log("Base path:", base)
log("LHM dir:", lhm_dir)

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