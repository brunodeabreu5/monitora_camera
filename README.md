# Hikvision Radar Pro V4.2

<div align="center">

**Sistema completo de monitoramento de tráfego com detecção de violações de velocidade usando câmeras Hikvision iDS-TCM403-GIR**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Features](#features) •
[Installation](#installation) •
[Configuration](#configuration) •
[Usage](#usage) •
[Development](#development) •
[Security](#security)

</div>

---

## 🚀 Sobre o Projeto

O **Hikvision Radar Pro V4.2** é uma aplicação desktop completa para monitoramento automático de tráfego e detecção de violações de velocidade, desenvolvida com Python e PySide6/Qt6. O sistema conecta-se a câmeras Hikvision com radar (iDS-TCM403-GIR) para capturar eventos em tempo real, identificar placas de veículos e detectar excessos de velocidade, com alertas automáticos via WhatsApp.

### ✨ Principais Funcionalidades

#### 🔍 Monitoramento em Tempo Real
- Conexão simultânea com múltiplas câmeras Hikvision
- Eventos em tempo real via HTTP alert stream
- Detecção de placas (ANPR) e velocidade
- Visualização ao vivo via RTSP ou snapshot HTTP

#### ⚠️ Detecção de Excessos
- Limites de velocidade configuráveis por câmera
- Alertas visuais e sonoros instantâneos
- Registro automático de infrações
- Relatórios detalhados de excessos

#### 📱 Integração WhatsApp
- Alertas automáticos via Evolution API
- Envio de fotos das infrações
- Mensagens customizáveis por template
- Múltiplos destinatários

#### 🗄️ Gerenciamento de Dados
- Banco SQLite persistente
- Filtros avançados (câmera, placa, data, velocidade)
- Exportação CSV
- Dashboard com estatísticas

#### 👥 Controle de Acesso
- Múltiplos usuários com autenticação
- Roles: Administrador e Operador
- Senhas criptografadas (AES-256-GCM)
- Auditoria de operações

#### 🔐 Segurança (FASE 1 - Implementada)
- ✅ Criptografia AES-256-GCM para senhas de câmeras
- ✅ Senhas de usuários com SHA-256 + salt
- ✅ Suporte a verificação SSL/TLS
- ✅ Sem credenciais hardcoded
- ✅ Wizard de primeira execução

#### 🏗️ Arquitetura (FASE 3 - Implementada)
- ✅ Repository Pattern para acesso a dados
- ✅ Event-driven com pub/sub
- ✅ Dependency Injection
- ✅ Validação centralizada
- ✅ Sistema de cache com TTL

## 📋 Requisitos de Sistema

### Mínimos
- **SO**: Windows 10 ou superior / Linux (Ubuntu 20.04+)
- **Python**: 3.10 ou superior
- **RAM**: 4 GB mínimo (8 GB recomendado)
- **Processador**: Dual-core 2.0 GHz
- **Rede**: Ethernet 100 Mbps (recomendado Gigabit)
- **Armazenamento**: 500 MB livres + espaço para imagens

### Recomendados
- **SO**: Windows 11 / Ubuntu 22.04 LTS
- **RAM**: 16 GB
- **Processador**: Quad-core 3.0 GHz
- **GPU**: Para aceleração de decode de vídeo (opcional)

## 📦 Instalação

### Método 1: Via pip (Recomendado)

```bash
# Clonar repositório
git clone https://github.com/brunodeabreu5/monitora_camera.git
cd monitora_camera

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar dependências
pip install -e ".[dev]"

# Executar
python main.py
```

### Método 2: Executável

Baixe a versão mais recente em [Releases](https://github.com/brunodeabreu5/monitora_camera/releases) e execute `HikvisionRadarProV42.exe`.

### Dependências

As dependências principais são instaladas automaticamente:

```
PySide6>=6.6.0           # Interface Qt6
requests>=2.31.0         # HTTP client
cryptography>=41.0.0     # Criptografia
Pillow>=10.0.0           # Processamento de imagem
opencv-python>=4.8.0      # OpenCV (opcional)
numpy>=1.24.0            # Processamento numérico
```

Para desenvolvimento:

```bash
pip install -e ".[dev]"
```

Instala: pytest, black, flake8, mypy, pre-commit, etc.

## ⚙️ Configuração

### Primeira Execução

Ao executar pela primeira vez, o **Wizard de Configuração Inicial** será exibido:

1. **Criar Administrador**
   - Nome de usuário (mínimo 3 caracteres)
   - Senha forte (mínimo 8 caracteres, maiúscula, minúscula, números)
   - Confirmação de senha

2. **Configurar Câmeras** (opcional)
   - Nome da câmera
   - Endereço IP
   - Porta HTTP (padrão: 80)
   - Credenciais de acesso

3. **Configurar Evolution API** (opcional)
   - URL do servidor
   - Token de API
   - Nome da instância
   - Números dos destinatários

### Arquivo de Configuração

O arquivo `hikvision_pro_v42_config.json` contém todas as configurações:

```json
{
  "speed_limit": 60,
  "cameras": [
    {
      "name": "Camera 1",
      "enabled": true,
      "camera_ip": "192.168.1.64",
      "camera_port": 80,
      "camera_user": "admin",
      "camera_pass": {
        "encrypted": "base64_encrypted_password",
        "nonce": "base64_nonce"
      },
      "channel": 101,
      "timeout": 15,
      "speed_limit_value": 60,
      "verify_ssl": false
    }
  ],
  "evolution_api": {
    "enabled": false,
    "base_url": "http://localhost:8080",
    "api_token": "your_token_here",
    "instance_name": "instance_name",
    "recipient_numbers": ["5511999999999"]
  },
  "users": [
    {
      "username": "admin",
      "password_hash": "hash",
      "password_salt": "salt",
      "role": "Administrador"
    }
  ]
}
```

> ⚠️ **Importante**: Senhas de câmeras são automaticamente criptografadas. Nunca edite manualmente o campo `camera_pass`.

### Variáveis de Ambiente (Opcional)

```bash
# Desabilitar aceleração de hardware para decode de vídeo
export QT_FFMPEG_DECODING_HW_DEVICE_TYPES=  # vazio = software

# Reduzir logs do FFmpeg (Linux/Mac)
export AV_LOG_LEVEL=quiet

# Reduzir logs do FFmpeg (Windows)
set AV_LOG_LEVEL=-8
```

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

## 💻 Desenvolvimento

### Estrutura do Projeto

```
monitora_camera/
├── src/                        # Código fonte
│   ├── core/                   # Módulos centrais
│   │   ├── config.py          # Configuração (AppConfig, helpers)
│   │   ├── database.py        # Banco SQLite (Database)
│   │   ├── camera_client.py   # Cliente HTTP/RTSP
│   │   ├── crypto.py          # Criptografia AES-256-GCM
│   │   ├── event_manager.py   # Pub/sub events
│   │   ├── exceptions.py      # Exceções customizadas
│   │   ├── logging_config.py  # Logging estruturado
│   │   ├── validators.py      # Validação de entrada
│   │   ├── container.py       # Dependency Injection
│   │   ├── cache.py           # Cache com TTL
│   │   └── types.py           # Type aliases
│   ├── repositories/           # Repository Pattern
│   │   ├── event_repository.py
│   │   ├── camera_repository.py
│   │   └── user_repository.py
│   ├── detection/              # Detecção
│   │   └── car_detector.py    # Detecção de veículos
│   └── app.py                  # Aplicação principal
├── ui/                         # Interface
│   ├── tabs/                   # Abas
│   │   ├── dashboard_tab.py
│   │   ├── cameras_tab.py
│   │   ├── monitor_tab.py
│   │   ├── history_tab.py
│   │   ├── report_tab.py
│   │   ├── users_tab.py
│   │   └── evolution_tab.py
│   ├── widgets.py              # Widgets customizados
│   ├── workers.py              # Background threads
│   ├── qt_imports.py           # Imports centralizados Qt
│   ├── first_run_wizard.py     # Wizard primeira execução
│   └── event_integration.py    # Integração de eventos
├── tests/                      # Suíte de testes
│   ├── unit/                   # Testes unitários
│   ├── integration/            # Testes integração
│   └── conftest.py             # Config pytest
├── docs/                       # Documentação
│   ├── architecture.md         # Arquitetura detalhada
│   ├── DEVELOPMENT.md          # Guia de desenvolvimento
│   └── TROUBLESHOOTING.md      # Solução de problemas
├── scripts/                    # Scripts utilitários
├── main.py                     # Entry point
├── pyproject.toml              # Config do projeto
└── README.md                   # Este arquivo
```

### Configuração do Ambiente

```bash
# Clonar
git clone https://github.com/brunodeabreu5/monitora_camera.git
cd monitora_camera

# Ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instalar dependências de desenvolvimento
pip install -e ".[dev]"

# Instalar pre-commit hooks
pre-commit install
```

### Executar Testes

```bash
# Todos os testes com coverage
pytest --cov=src --cov-report=html

# Apenas testes unitários
pytest tests/unit/ -v

# Testes específicos
pytest tests/unit/test_validators.py -v

# Excluir testes lentos
pytest -m "not slow"
```

### Código Quality

```bash
# Formatar código
black src/ tests/

# Verificar lint
flake8 src/ tests/

# Organizar imports
isort src/ tests/

# Verificar tipos
mypy src/

# Executar pre-commit manualmente
pre-commit run --all-files
```

### Build Executável

```bash
# Windows
python -m PyInstaller --onefile --windowed --icon=app.ico main.py

# Linux
python -m PyInstaller --onefile --windowed main.py

# Com Nuitka (melhor performance)
python -m nuitka --standalone --onefile main.py
```

## 🔐 Segurança

### Melhorias Implementadas (FASE 1)

#### Criptografia de Senhas
- ✅ **Senhas de câmeras**: AES-256-GCM
  - Chave derivada de hardware ID
  - Nonce único por criptografia
  - Armazenamento seguro em JSON

- ✅ **Senhas de usuários**: SHA-256 + Salt
  - Salt único por usuário
  - Iterações PBKDF2 (100.000)
  - Validação de força obrigatória

#### Verificação SSL/TLS
- ✅ Suporte a `verify_ssl` por câmera
- ✅ Suporte a fingerprints de cert autoassinado
- ✅ Warnings claros quando SSL desabilitado

#### Controle de Acesso
- ✅ Sem credenciais hardcoded
- ✅ Wizard de primeira execução
- ✅ Validação de força de senha
- ✅ Troca obrigatória na primeira execução

### Boas Práticas

1. **Nunca** commitar `hikvision_pro_v42_config.json` com senhas reais
2. Usar `.gitignore` para evitar commits acidentais
3. Rotacionar senhas periodicamente
4. Usar HTTPS para Evolution API
5. Manter sistema atualizado

## 📚 Documentação

- **[architecture.md](docs/architecture.md)**: Arquitetura detalhada do sistema
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)**: Guia completo de desenvolvimento
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**: Solução de problemas comuns

## 🛠️ Troubleshooting

### Conexão com Câmeras

**Erro: Connection Refused**
- Verificar IP/porta
- Ping na câmera: `ping 192.168.1.64`
- Testar no navegador: `http://192.168.1.64`

**Erro: Authentication Failed (401/403)**
- Verificar usuário/senha
- Tentar Digest Auth vs Basic Auth
- Resetar senha na câmera

### Vídeo RTSP

**Erro: "RTP: missed packets"**
- Usar `RTSP = tcp` na configuração
- Verificar estabilidade da rede
- Considerar `Fallback live = snapshot`

### Evolution API

**Erro: Invalid API Token**
- Regenerar token no Evolution
- Verificar URL base
- Testar com curl: `curl http://localhost:8080`

Veja [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) para mais detalhes.

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

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o repositório
2. Crie um branch para sua feature (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'feat: adicionar nova funcionalidade'`)
4. Push para o branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

### Convenções de Commit

Seguir [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: nova funcionalidade
fix: correção de bug
docs: atualização de documentação
style: formatação de código
refactor: refatoração
test: adicionar testes
chore: atualização de dependências
perf: melhoria de performance
security: correção de segurança
```

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 🙏 Agradecimentos

- **Hikvision**: Pela câmera iDS-TCM403-GIR e documentação ISAPI
- **Evolution API**: Pela integração WhatsApp
- **PySide6/Qt**: Pelo excelente framework GUI
- **Comunidade Python**: Por bibliotecas excepcionais

## 📞 Suporte

Para questões e problemas:

- 📧 Abrir uma [issue no GitHub](https://github.com/brunodeabreu5/monitora_camera/issues)
- 📖 Consultar documentação em [docs/](docs/)
- 🔍 Verificar [issues existentes](https://github.com/brunodeabreu5/monitora_camera/issues?q=is%3Aissue)

---

<div align="center">

**Hikvision Radar Pro V4.2**

*Sistema completo de monitoramento de tráfego com câmeras Hikvision*

**Versão**: 4.2.0 | **Última atualização**: Março 2026

[⬆ Voltar ao topo](#hikvision-radar-pro-v42)

</div>
