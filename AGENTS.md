# Repository Guidelines

## Project Structure & Module Organization
This repository is currently a flat Windows-focused Python project. The main application lives in `hikvision_pro_v42_app.py`, which contains the PySide6 UI, camera client, event parsing, and SQLite persistence. Build helpers are the `build_hikvision_pro_v41*.bat` and `build_hikvision_pro_v42_windows.bat` scripts. Release notes and operator instructions are in `README_hikvision_pro_v42.txt`.

Keep new modules small and focused. If the app grows, split reusable logic into files such as `camera_client.py`, `database.py`, and `ui/` instead of extending the single app file further.

## Build, Test, and Development Commands
Use Python 3. Example local workflow:

```bat
python -m pip install -r requirements_hikvision_pro_v4.txt
python hikvision_pro_v42_app.py
build_hikvision_pro_v42_windows.bat
```

`python hikvision_pro_v42_app.py` starts the desktop app for manual testing. `build_hikvision_pro_v42_windows.bat` installs dependencies, clears `build/` and `dist/`, and packages a Windows executable with PyInstaller.

## Coding Style & Naming Conventions
Follow existing Python style: 4-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and uppercase constants such as `APP_NAME`. Prefer type hints on new functions and keep helper functions near the code they support. Use standard library modules first, and keep UI strings and config keys consistent with the existing Portuguese-facing workflow.

## Testing Guidelines
There is no automated test suite in the current tree. For changes to parsing, persistence, or HTTP handling, add targeted `pytest` tests under a new `tests/` directory with names like `test_parse_event_xml.py`. Until that exists, verify changes manually by launching the app, exercising camera connection flows, and confirming event records are written correctly.

## Commit & Pull Request Guidelines
Local `.git` history is not available in this workspace, so no repository-specific commit convention could be verified. Use short, imperative commit subjects such as `Fix XML speed parsing` or `Add camera timeout validation`. Pull requests should include a summary, manual test notes, affected camera models or endpoints, and screenshots when the PySide6 UI changes.

## Security & Configuration Tips
Do not commit real camera IPs, usernames, passwords, or generated event data. Treat local config, snapshots, and SQLite files as environment-specific artifacts. If you add new configuration files, provide sanitized examples only.
