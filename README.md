# Mjolnir Dashboard

A native Windows dashboard for the Thermalright Mjolnir Vision AIO LCD.

It renders live CPU and GPU metrics directly to the AIO display using Pillow and OpenCV. It does not use Chromium, Playwright, browser capture, desktop capture, or a visible browser window.

> **Status:** Windows-focused personal hardware project. Contributions and device testing are welcome.

## Features

- Native 640×480 rendering for the Mjolnir Vision display
- CPU temperature through LibreHardwareMonitor
- GPU temperature and utilisation through NVIDIA NVML
- CPU, GPU, RAM, disk, and network sensor collection
- Local MP4 video backgrounds
- Theme JSON files editable without rebuilding the application
- Multiple layouts:
  - Four-card hardware monitor
  - Minimal clock
  - Hero CPU/GPU temperatures
- Theme switching and optional automatic rotation
- Windows system-tray controls
- Single-file PyInstaller build
- Automatically starts LibreHardwareMonitor when launched with administrator privileges

## Requirements

- Windows 10 or Windows 11
- Thermalright Mjolnir Vision / compatible USB display
- NVIDIA GPU for NVML GPU metrics
- Python 3.11+ for development
- Administrator privileges when using the bundled LibreHardwareMonitor launcher

The current device implementation targets a USB display identified as:

```text
VID:PID 87ad:70db
```

Other Thermalright display models may use different protocols and may require changes to `backend/usb_display.py`.

## Install from a release

1. Open the repository's **Releases** page.
2. Download `MjolnirDashboard.exe`.
3. Place it in a folder where you have write access, for example:

   ```text
   C:\Users\<your-user>\Documents\MjolnirDashboard
   ```

4. Run `MjolnirDashboard.exe`.
5. Accept the UAC prompt if you want the application to start LibreHardwareMonitor automatically.
6. Use the tray icon to switch themes, toggle rotation, or open the themes/config folders.

On first run, the app creates writable `themes`, `config`, and `logs` folders beside the EXE.

## Run from source

```bat
git clone [https://github.com/MS2620/mjolnir-dashboard.git](https://github.com/MS2620/mjolnir-dashboard.git)
cd mjolnir-dashboard

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
cd backend
python main.py
```

## Build

Run from the repository root:

```bat
.venv\Scripts\activate

pyinstaller --onefile --noconsole ^
  --name MjolnirDashboard ^
  --manifest=mjolnir.manifest ^
  --add-data "backend;backend" ^
  --add-data "themes;themes" ^
  --add-data "config;config" ^
  --add-data "tools\LibreHardwareMonitor;tools\LibreHardwareMonitor" ^
  backend\main.py
```

The generated application is:

```text
dist\MjolnirDashboard.exe
```

For debugging, remove `--noconsole`.

## Themes

Themes are directories under `themes/` containing a `theme.json` file:

```text
themes/
  dark-neon/
    theme.json
  minimal/
    theme.json
  cyberpunk/
    theme.json
    background.mp4
```

Theme layout options currently include:

```json
"layout": "four-cards"
```

```json
"layout": "minimal-clock"
```

```json
"layout": "hero-temperatures"
```

Example theme configuration:

```json
{
  "name": "Dark Neon",
  "layout": "four-cards",
  "background": {
    "type": "solid",
    "color": "#080b10"
  },
  "text": {
    "font": "C:/Windows/Fonts/segoeuib.ttf",
    "labelSize": 14,
    "valueSize": 28,
    "normalColor": "#00eaff"
  }
}
```

For portable custom fonts, place the `.ttf` file in the theme directory and use a relative path:

```text
themes/cyberpunk/
  theme.json
  Orbitron-SemiBold.ttf
```

```json
"text": {
  "font": "Orbitron-SemiBold.ttf"
}
```

## Configuration

Runtime settings live in:

```text
config/settings.json
```

Example:

```json
{
  "activeTheme": "dark-neon",
  "targetFps": 15,
  "sensorIntervalSeconds": 1.0,
  "themeRotation": {
    "enabled": false,
    "intervalMinutes": 10,
    "themes": ["dark-neon", "cyberpunk", "minimal"]
  },
  "display": {
    "width": 640,
    "height": 480,
    "jpegQuality": 85
  }
}
```

## Contributing

Contributions are welcome, especially:

- Testing with other Thermalright AIO display models
- USB protocol research and compatibility improvements
- New themes and layouts
- Sensor improvements
- Documentation and packaging improvements
- Windows startup/installer support

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Safety and support

This project communicates directly with a USB display device. Use it at your own risk.

Before reporting a bug, include:

- Windows version
- Python version, if running from source
- Device model and USB VID:PID
- GPU model
- Dashboard log from `logs/` or `%TEMP%\mjolnir_dashboard.log`
- Reproduction steps

## Licence

This project is licensed under the [MIT License](LICENSE).