# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hikvision Radar Pro V4.2 is a Windows desktop application for monitoring speed violations using Hikvision radar cameras (specifically tested with iDS-TCM403-GIR). The app connects to cameras via RTSP streams and XML event notifications, stores events in SQLite, and can send WhatsApp alerts via the Evolution API.

**Important v4.2 Change**: This version intentionally avoids the `/ISAPI/Traffic/channels/1/vehicleDetect/alertStream` endpoint and only uses `/ISAPI/Event/notification/alertStream` for events, fixing a bytes/str decoding issue.

## Development Commands

```bat
# Install dependencies
python -m pip install -r requirements_hikvision_pro_v4.txt

# Run the application (for manual testing)
python hikvision_pro_v42_app.py

# Build Windows executable
build_hikvision_pro_v42_windows.bat

# Run tests (if test suite exists)
python -m pytest tests/test_hikvision_pro_v42_app.py
```

The build script locates Python (tries Python 3.13, `python`, or `py`), upgrades pip, installs dependencies, cleans `build/` and `dist/`, and creates `dist/HikvisionRadarProV42.exe` using PyInstaller with `--onefile --windowed`.

## Architecture

The application follows a **single-file desktop application pattern** with all code in `hikvision_pro_v42_app.py`. Key classes:

- **MainWindow** (line ~1095): PySide6 QMainWindow that manages the UI, camera threads, event processing, and real-time video display
- **CameraClient** (line ~519): HTTP client for camera communication, connection testing, RTSP URL building, event stream handling, and snapshot capture
- **Database** (line ~380): SQLite wrapper for event persistence with migration support
- **AppConfig**: JSON configuration management with camera CRUD operations and user authentication

### Data Flow

1. Configuration loaded from JSON → AppConfig
2. CameraClient connects via HTTP to cameras
3. Events received as XML → parsed → stored in Database → UI updates
4. Speed violations validated → Evolution API calls (if enabled)

### Thread Management

- Multi-threaded camera monitoring with separate threads per camera
- Event processing in background threads
- UI thread protection for database operations (PySide6 signals)

## Configuration

- **`hikvision_pro_v42_config.json`**: Runtime configuration (NOT versioned, in .gitignore)
- **`hikvision_pro_v42_config.example.json`**: Template with all options

Configuration includes global speed limit, multiple camera configurations (IP, port, credentials, channel, RTSP settings, speed limits), Evolution API settings, and user accounts with password hashing.

**Camera setup recommendation**: Mode "traffic", Channel 101. Start with snapshot enabled; if no image arrives, disable snapshot and rely on events only.

## Coding Conventions

- **Indentation**: 4 spaces
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants
- **Localization**: UI strings and configuration keys in Portuguese (application serves Brazilian users)
- **Type hints**: Add to new functions for better code clarity
- **Module organization**: Keep new modules small and focused. If the app grows, consider splitting into `camera_client.py`, `database.py`, and `ui/` directory

## Security

- **NEVER commit** real camera IPs, usernames, passwords, Evolution API tokens, or generated event data
- Local config files, snapshots, and SQLite databases are environment-specific artifacts
- If credentials were committed in the past, change camera passwords and rotate API tokens
- Only commit sanitized example configurations

## Key Functions

- **`parse_event_xml()`**: Parses camera event notifications from XML
- **`looks_like_complete_event_xml()`**: Validates XML chunks in the stream
- **`test_connection()`**: Validates camera health and connectivity
- **`render_event_message()`**: Formats alert messages for Evolution API

## Dependencies

- **PySide6** (>=6.6, <7): Qt6 GUI framework
- **requests** (>=2.31, <3): HTTP client for camera and Evolution APIs
- **PyInstaller** (>=6.0, <7): Windows executable generation
