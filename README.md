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

### Limite de velocidade e alertas no WhatsApp

Para receber eventos e fotos no WhatsApp quando um veículo passar acima da velocidade configurada:

1. **Limite global (padrão)**  
   - Na aba **Excesso de velocidade**, altere o campo **Limite (km/h)** e clique em **Aplicar** para gravar o limite global na configuração.  
   - Ou edite `hikvision_pro_v42_config.json`: `"speed_limit": 60` (valor em km/h).

2. **Limite por câmera**  
   - Aba **Câmeras** → selecione a câmera → marque **Habilitar aviso de velocidade** e informe **Limite veloc. (km/h)**.  
   - Salve a câmera. Se o aviso por câmera estiver desligado, o limite global é usado.

3. **Evolution API (envio WhatsApp)**  
   - Aba **Evolution API** → **Configuração**: marque **Habilitar integracao Evolution API**, preencha URL, Token e Instância, e os **Numeros** (ex.: 5511999999999).  
   - Marque **Enviar imagem com legenda** para enviar a foto do evento junto com o texto.  
   - Na subaba **Template** você pode personalizar a mensagem (variáveis: `{camera}`, `{plate}`, `{speed}`, `{limit}`, `{ts}`, etc.).  
   - Salve.

4. **Habilitar envio por câmera**  
   - Aba **Câmeras** → na câmera desejada, marque **Enviar excesso pela Evolution API** e salve.

5. **Foto no evento**  
   - Na mesma câmera, deixe **Salvar snapshot no evento** marcado para que a imagem seja gravada e enviada no alerta.

Quando um carro passar acima do limite configurado, o app grava o evento no banco, salva a foto em `output/images/` e envia pelo Evolution API para os números configurados (texto + foto, se disponível).

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

From the project root (with dependencies installed):

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

The test file sets `QT_QPA_PLATFORM=offscreen` so the GUI tests run without a display. Optional: install pytest and run `python -m pytest tests/ -v`.

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

**Eventos do alertStream (Hikvision)**

A aplicação recebe eventos via HTTP GET em `/ISAPI/Event/notification/alertStream`. O stream envia blocos de XML; cada bloco é um evento completo. Tipos de XML suportados:

- **EventNotificationAlert** – notificações genéricas (alarme, travamento, etc.)
- **ANPR** – reconhecimento de placa (ANPR) com dados de veículo
- **VehicleDetectEvent** – detecção de veículo (radar, velocidade, faixa)

Em todos eles o parser extrai, quando presentes nas tags: **placa** (`licensePlate`, `plateNo`, `vehiclePlate`, etc.), **velocidade** (`speed`, `vehicleSpeed`, `speedValueKmh`, etc.), **faixa** (`laneNo`, `driveLane`), **direção** (`direction`, `driveDirection`), **data/hora** (`dateTime`, `captureTime`, `occurTime`) e **tipo de evento** (`eventType`, `eventDescription`, `alarmType`, etc.). O resultado é gravado no banco e, se configurado, gera alerta no WhatsApp (Evolution API).

Para testar o stream sem abrir o app, use o script:

```bash
python scripts/test_alertstream.py
```

Opções: `--url`, `--user`, `--password` ou config em `hikvision_pro_v42_config.json`. O script imprime cada XML recebido e o resultado do parse (placa, velocidade, ts). Para detalhes oficiais dos eventos, consulte a documentação ISAPI da Hikvision (Event Notification Alert, ANPR, Traffic).

### Live Video Not Working

1. **Check RTSP settings**: Verify RTSP port and credentials.
2. **Try snapshot mode**: In the **Cameras** tab, set **Fallback live** to **snapshot**. The app will show periodic HTTP snapshots instead of the RTSP stream (avoids decoder and network issues).
3. **Use RTSP over TCP**: In the **Cameras** tab, set **Preferencia RTSP** to **tcp**. The app appends `?rtsp_transport=tcp` to the URL, which reduces packet loss and "RTP: missed packets" on unstable networks.
4. **Check firewall**: Ensure RTSP port (default: 554) is not blocked.

**Erro no terminal: "Failed setup for format d3d11" / "corrupted macroblock"**

- O player usa Qt Multimedia (FFmpeg). No Windows, o app **desativa por padrão** a aceleração por hardware na decodificação (variável `QT_FFMPEG_DECODING_HW_DEVICE_TYPES`), para evitar esse erro. O vídeo usa decodificação em software.
- Se o erro ainda aparecer, use **Fallback live = snapshot** (aba Câmeras). Para vídeo contínuo, use **Preferencia RTSP = tcp**. Para tentar aceleração por hardware (D3D12), defina antes de iniciar: `set QT_FFMPEG_DECODING_HW_DEVICE_TYPES=d3d12va`.

**Mensagens no terminal: "RTP: missed packets" / "cbp too large" / "error while decoding MB"**

- Essas mensagens indicam **perda de pacotes** na rede ou **quadros H.264 corrompidos** (o decoder "concealing" erros). **Soluções:** use **Preferencia RTSP = tcp** (aba Câmeras) e, se ainda aparecerem muitos avisos ou o vídeo travar, use **Fallback live = snapshot**. O app define por padrão `AV_LOG_LEVEL=-8` para reduzir a quantidade de mensagens do FFmpeg no terminal; se a build do Qt/FFmpeg respeitar essa variável, os avisos ficam suprimidos. Para forçar manualmente antes de iniciar: `set AV_LOG_LEVEL=-8` (Windows) ou `export AV_LOG_LEVEL=quiet` (Linux).

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

See [CHANGELOG.md](CHANGELOG.md) for version history.

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
