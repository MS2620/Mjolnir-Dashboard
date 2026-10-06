# Contributing to Mjolnir Dashboard

Thanks for considering a contribution.

## Before you start

- Search existing issues and pull requests before creating a new one.
- Keep changes focused. One pull request should address one feature or fix.
- Do not commit generated files such as `dist/`, `build/`, `__pycache__/`, logs, or `.venv/`.
- Do not commit credentials, API tokens, device dumps containing personal information, or private videos/themes.

## Development setup

```bat
git clone [https://github.com/MS2620/mjolnir-dashboard.git](https://github.com/MS2620/mjolnir-dashboard.git)
cd mjolnir-dashboard

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
cd backend
python main.py
```

## Changes

Please:

1. Create a branch from `main`.
2. Make and test your change from source before building an EXE.
3. Keep formatting consistent with the existing code.
4. Update the README when behaviour, configuration, setup, or supported hardware changes.
5. Add or update theme examples for visual changes.
6. Explain how you tested the change in your pull request.

## Hardware-related changes

For USB/protocol changes, include:

- Device make/model
- USB VID:PID
- Endpoint details, if relevant
- Whether the change was tested on real hardware
- Any known risks or compatibility limitations

Do not merge unverified destructive USB commands.

## Pull request format

Please include:

- What changed
- Why it changed
- How it was tested
- Screenshots or photos for theme/layout changes, where possible
- Hardware and Windows version, if relevant

## Code of conduct

Be respectful, constructive, and patient. Harassment, discriminatory behaviour, or hostile conduct is not welcome.