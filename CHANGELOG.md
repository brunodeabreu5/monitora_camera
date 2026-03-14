# Changelog

All notable changes to the Hikvision Radar Pro V4.2 project are documented here.

## [4.2.0] - 2026-03-14

### Added

- Requirements file in project root (`requirements.txt`) referencing `configs/requirements_hikvision_pro_v4.txt`
- Unit tests for `format_datetime_br`, `download_snapshot` (empty response and next-URL fallback), and parsing with unknown XML tags
- Validation when saving camera: IP/hostname and HTTP port (1–65535)
- Validation when saving Evolution API: URL, token, and instance name required when integration is enabled
- Placeholder for date filter in History and Report tabs: "DD/MM/AAAA ou AAAA-MM-DD"
- Version displayed in main window title (e.g. "Hikvision Radar Pro V4.2 v4.2.0")
- This CHANGELOG

### Changed

- `.gitignore`: added `test_config_*.json` for test artifacts
- Test module adds project root to `sys.path` so tests run from any working directory
- `test_connection` returns 401 immediately on auth failure (no longer falls through to 500 after trying all URLs)
- Histórico e Relatório: limite de consulta explícito (`MAX_EVENTS_QUERY = 1000` em `database.py`) para evitar sobrecarga com muitos eventos
- Logs: mensagens de erro passam por sanitização para não gravar senhas em URLs (ex.: `http://user:senha@host` vira `http://user:***@host`) no arquivo de log e no stderr

### Fixed

- (Existing fixes from prior work: ANPR XML parsing by root closing tag, snapshot Basic auth fallback, date format BR, monitor tab QPixmap import, etc.)

---

Format inspired by [Keep a Changelog](https://keepachangelog.com/).
