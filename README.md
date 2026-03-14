# Hikvision Radar Pro V4.2

Windows desktop application for monitoring speed violations using Hikvision radar cameras (specifically tested with iDS-TCM403-GIR).

## Features

- **Real-time Event Monitoring**: Connects to Hikvision cameras via RTSP streams and XML event notifications
- **Speed Violation Detection**: Configurable speed limits per camera with visual and alert notifications
- **WhatsApp Integration**: Sends alerts via Evolution API when speed violations are detected
- **Event Database**: SQLite database for persistent event storage with filtering and reporting
- **Live Video View**: RTSP video streaming with snapshot fallback
- **CSV Export**: Export event history and overspeed reports to CSV
- **User Management**: Multi-user support with role-based access (Administrator/Operator)

## Screenshots

*(Add screenshots here when available)*

## Requirements

- **OS**: Windows 10 or later
- **Python**: 3.13+ (or compatible version)
- **Dependencies**: See `configs/requirements_hikvision_pro_v4.txt`

## Installation

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/brunodeabreu5/monitora_camera.git
   cd monitora_camera
   ```

2. Install dependencies:
   ```bash
   python -m pip install -r configs/requirements_hikvision_pro_v4.txt
   ```

3. Create configuration:
   ```bash
   cp configs/hikvision_pro_v42_config.example.json hikvision_pro_v42_config.json
   # Edit hikvision_pro_v42_config.json with your settings
   ```

4. Run the application:
   ```bash
   python main.py
   ```

### From Executable

Download the latest release from [Releases](https://github.com/brunodeabreu5/monitora_camera/releases) and run `HikvisionRadarProV42.exe`.

## Configuration

### Application Structure

```
monitora_camera/
├── src/              # Application source code
│   ├── app.py       # Main window (552 lines)
│   └── core/        # Core modules
├── ui/              # User interface
│   ├── tabs/        # Tab implementations
│   ├── widgets.py   # Reusable widgets
│   └── workers.py   # Background workers
├── docs/            # Documentation
├── scripts/         # Build scripts
├── configs/         # Configuration files
└── tests/           # Test suite
```

### Configuration File

The application uses `hikvision_pro_v42_config.json` for runtime configuration (not versioned). Use `configs/hikvision_pro_v42_config.example.json` as a template.

**Key Configuration Sections:**

- **speed_limit**: Global speed limit (km/h)
- **cameras**: Array of camera configurations
- **evolution_api**: Evolution API settings for WhatsApp
- **users**: User accounts and credentials

### Camera Configuration

Each camera requires:

- **name**: Display name
- **camera_ip**: Camera IP address
- **camera_port**: HTTP port (default: 80)
- **camera_user**: Username
- **camera_pass**: Password
- **channel**: Video channel (default: 101 for iDS-TCM403-GIR)
- **camera_mode**: "traffic" or "auto" recommended for iDS-TCM403-GIR
- **speed_limit_value**: Per-camera speed limit (optional)
- **rtsp_enabled**: Enable live video view
- **enabled**: Enable monitoring

### Evolution API Setup

To enable WhatsApp alerts:

1. Configure Evolution API instance
2. Add API credentials to config:
   - `base_url`: Evolution API URL
   - `api_token`: API authentication token
   - `instance_name`: WhatsApp instance name
3. Configure recipient numbers
4. Enable per-camera: Set `evolution_enabled: true`

See [docs/SECURITY.md](docs/SECURITY.md) for security guidelines.

## Usage

### First Login

1. Default credentials: **admin** / **admin**
2. You'll be prompted to change the password on first login
3. Configure cameras in the "Cameras" tab
4. Start monitoring in the "Monitor" tab

### Monitoring

1. Go to the **Monitor** tab
2. Click **"Iniciar todas"** to start monitoring all enabled cameras
3. View real-time events in the "Eventos recentes" table
4. Check "Estado das cameras" for connection status

### Viewing Reports

1. **History** tab: View all events with filters
   - Filter by camera, plate, date, minimum speed
   - Double-click rows to view event details/images

2. **Excesso de velocidade** tab: View overspeed events
   - Apply speed limit and filter by camera/date
   - Export to CSV

## Development

### Project Structure

The application follows a modular architecture:

- **src/core/**: Business logic modules (config, database, camera client, etc.)
- **ui/tabs/**: UI tab implementations (dashboard, users, history, report, cameras, evolution, monitor)
- **ui/widgets.py**: Reusable UI components
- **ui/workers.py**: Background worker threads

### Building from Source

```bash
# Install build dependencies
python -m pip install pyinstaller

# Build executable
python scripts/build_hikvision_pro_v42_windows.bat
```

The executable will be created in `dist/HikvisionRadarProV42.exe`.

### Running Tests

```bash
python -m pytest tests/
```

## Troubleshooting

### Camera Connection Issues

1. **Verify network connectivity**: Ping the camera IP
2. **Check credentials**: Ensure username/password are correct
3. **Test connection**: Use "Testar conexao" button in Cameras tab
4. **Check camera mode**: Use "traffic" or "auto" for iDS-TCM403-GIR

### No Events Received

1. **Verify event stream**: Check event stream URL in camera configuration
2. **Check camera firmware**: Ensure event notifications are enabled
3. **Review logs**: Check "Atividade do sistema" in Dashboard tab

### Live Video Not Working

1. **Check RTSP settings**: Verify RTSP port and credentials
2. **Try snapshot mode**: Set "Fallback live" to "snapshot"
3. **Check firewall**: Ensure RTSP port (default: 554) is not blocked

### Evolution API Not Working

1. **Verify API credentials**: Test API connection in Evolution tab
2. **Check instance status**: QR code should be displayed
3. **Verify recipient numbers**: Format as country code + number (e.g., 5511999999999)

## Documentation

- [README_hikvision_pro_v42.txt](docs/README_hikvision_pro_v42.txt) - Original project documentation
- [SECURITY.md](docs/SECURITY.md) - Security guidelines and best practices
- [AGENTS.md](docs/AGENTS.md) - AI agent instructions
- [CLAUDE.md](docs/CLAUDE.md) - Claude Code project instructions

## Version History

See [CHANGELOG.md](CHANGELOG.md) (to be created) for version history.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Specify your license here]

## Support

For issues and questions:

- Create an issue on GitHub
- Review documentation in `docs/`
- Check existing issues for similar problems

## Acknowledgments

- **Hikvision**: For the iDS-TCM403-GIR radar camera
- **Evolution API**: For WhatsApp integration
- **PySide6**: For the Qt6 Python bindings
- **Community**: For feedback and testing

---

**Hikvision Radar Pro V4.2** - Speed violation monitoring for Hikvision radar cameras

**Version:** 4.2.0
**Last Updated:** 2026-03-14
