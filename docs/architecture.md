# Arquitetura do Hikvision Radar Pro V4.2

## Visão Geral

O Hikvision Radar Pro é um sistema de monitoramento de tráfego desenvolvido em Python com interface gráfica PySide6/Qt6. O sistema detecta violações de velocidade usando câmeras Hikvision iDS-TCM403-GIR e envia alertas via WhatsApp através da Evolution API.

## Stack Tecnológico

- **Linguagem**: Python 3.10+
- **Interface Gráfica**: PySide6 (Qt6)
- **Banco de Dados**: SQLite3
- **Processamento de Imagem**: OpenCV, NumPy, Pillow
- **HTTP/Networking**: Requests
- **Segurança**: Cryptography (AES-256-GCM)

## Estrutura do Projeto

```
hikvision-radar-pro/
├── src/                          # Código fonte principal
│   ├── core/                     # Módulos centrais
│   │   ├── config.py            # Configuração e helpers
│   │   ├── database.py          # Banco de dados SQLite
│   │   ├── camera_client.py     # Cliente HTTP/RTSP para câmeras
│   │   ├── crypto.py            # Criptografia de senhas
│   │   ├── event_manager.py     # Sistema de eventos pub/sub
│   │   ├── exceptions.py        # Exceções customizadas
│   │   ├── logging_config.py    # Configuração de logging
│   │   ├── validators.py        # Validadores de entrada
│   │   ├── container.py         # Container de DI
│   │   ├── cache.py             # Sistema de cache com TTL
│   │   └── types.py             # Definições de tipos
│   ├── repositories/             # Repository Pattern
│   │   ├── event_repository.py  # Operações de eventos
│   │   ├── camera_repository.py # Operações de câmeras
│   │   └── user_repository.py   # Operações de usuários
│   ├── detection/                # Módulos de detecção
│   │   └── car_detector.py      # Detecção de veículos
│   └── app.py                    # Aplicação principal
├── ui/                           # Interface do usuário
│   ├── tabs/                     # Abas da interface
│   │   ├── dashboard_tab.py     # Dashboard principal
│   │   ├── cameras_tab.py       # Gerenciamento de câmeras
│   │   ├── monitor_tab.py       # Monitoramento em tempo real
│   │   ├── history_tab.py       # Histórico de eventos
│   │   ├── report_tab.py        # Relatório de excessos
│   │   ├── users_tab.py         # Gerenciamento de usuários
│   │   └── evolution_tab.py     # Configuração Evolution API
│   ├── widgets.py                # Widgets customizados
│   ├── workers.py                # Worker threads
│   ├── qt_imports.py             # Importações centralizadas Qt
│   ├── first_run_wizard.py       # Wizard de primeira execução
│   └── event_integration.py      # Integração de eventos
├── tests/                        # Suíte de testes
│   ├── unit/                     # Testes unitários
│   ├── integration/              # Testes de integração
│   ├── fixtures/                 # Fixtures de teste
│   └── conftest.py               # Configuração pytest
├── scripts/                      # Scripts utilitários
│   ├── test_alertstream.py       # Teste de alert stream
│   └── test_snapshot_manual.py   # Teste manual de snapshot
├── docs/                         # Documentação
│   ├── architecture.md           # Este arquivo
│   ├── DEVELOPMENT.md            # Guia de desenvolvimento
│   └── TROUBLESHOOTING.md        # Solução de problemas
├── main.py                       # Entry point
├── pyproject.toml                # Configuração do projeto
└── README.md                     # Documentação principal
```

## Camadas da Arquitetura

### 1. Camada de Apresentação (UI)

**Responsabilidade**: Interface com o usuário, exibição de dados, captura de entrada.

**Componentes principais**:
- `MainWindow`: Janela principal que orquestra todas as abas
- `DashboardTab`: Visão geral do sistema
- `CamerasTab`: CRUD de câmeras
- `MonitorTab`: Monitoramento em tempo real
- `HistoryTab`/`ReportTab`: Consultas e relatórios
- `UsersTab`: Gerenciamento de usuários
- `EvolutionTab`: Configuração de alertas WhatsApp

**Características**:
- Usa PySide6/Qt6 para widgets
- Implementa `EventAwareMixin` para comunicação via eventos
- Workers em threads separadas para não bloquear UI

### 2. Camada de Negócio

**Responsabilidade**: Lógica de domínio, regras de negócio, coordenação.

**Componentes principais**:
- `MainWindow`: Orquestra lógica entre abas
- Repositories: Encapsulam lógica de acesso a dados
- Validators: Garantem integridade de dados
- EventManager: Comunicação desacoplada

**Características**:
- Usa Repository Pattern para abstrair acesso a dados
- Implementa injeção de dependências via container
- Validação centralizada de entrada

### 3. Camada de Acesso a Dados

**Responsabilidade**: Persistência, consultas, transações.

**Componentes principais**:
- `Database`: Wrapper de SQLite3
- Repositories: Abstração de queries
- Cache: Otimização de consultas frequentes

**Características**:
- Thread-safe com locks
- Queries parametrizadas (previne SQL injection)
- Índices para performance

### 4. Camada de Infraestrutura

**Responsabilidade**: Serviços técnicos, integrações externas.

**Componentes principais**:
- `CameraClient`: Comunicação com câmeras Hikvision
- `EvolutionApiClient`: Envio de mensagens WhatsApp
- `CryptoModule`: Criptografia de senhas
- `LoggingConfig`: Registro estruturado de eventos

## Padrões de Arquitetura

### Repository Pattern

**Objetivo**: Separar lógica de acesso a dados da lógica de negócio.

```python
# Em vez de:
events = db.conn.execute("SELECT * FROM events").fetchall()

# Usar:
repo = EventRepository(db)
events = repo.find_filtered(camera_name="Camera 1", limit=100)
```

**Benefícios**:
- Testabilidade: Fácil mock de repositories
- Manutenibilidade: Queries centralizadas
- Flexibilidade: Fácil mudar implementação

### Event-Driven Architecture (Pub/Sub)

**Objetivo**: Desacoplar componentes através de eventos.

```python
# Publisher
event_manager.camera_updated.emit(camera_data)

# Subscriber
event_manager.camera_updated.connect(self.on_camera_updated)
```

**Benefícios**:
- Baixo acoplamento entre componentes
- Fácil adicionar novos subscribers
- Comunicação explícita e documentada

### Dependency Injection

**Objetivo**: Inverter controle de dependências.

```python
# Configurar container
container = DIContainer()
container.register_singleton(Database, lambda: Database(db_path))

# Usar
db = container.get(Database)
```

**Benefícios**:
- Testabilidade com mocks
- Configuração centralizada
- Ciclo de vida controlado

## Fluxo de Dados

### 1. Detecção de Evento

```
Câmera Hikvision
    ↓ (alert stream HTTP)
CameraClient
    ↓ (XML parse)
EventWorker (thread)
    ↓
EventManager.event_detected.emit()
    ↓
MonitorTab (atualiza UI)
    ↓
Database (persiste)
    ↓
EvolutionApiClient (envia WhatsApp se configurado)
```

### 2. Login de Usuário

```
LoginDialog (UI)
    ↓ (credentials)
UserRepository.authenticate()
    ↓ (hash compare)
AppConfig (valida)
    ↓ (se OK)
MainWindow (abre)
    ↓
EventManager.user_logged_in.emit()
```

### 3. Configuração de Câmera

```
CamerasTab (UI)
    ↓ (dados)
Validators (valida)
    ↓ (se válido)
CameraRepository.save()
    ↓
AppConfig (persiste JSON)
    ↓
EventManager.camera_updated.emit()
    ↓
Outras tabs (recebem evento e atualizam)
```

## Segurança

### Criptografia

- **Senhas de câmeras**: AES-256-GCM com chave derivada de hardware ID
- **Senhas de usuários**: SHA-256 com salt único por usuário
- **Tráfego HTTPS**: Suporte a verificação SSL/TLS

### Controle de Acesso

- Autenticação obrigatória
- Roles: Administrador (acesso total), Operador (limitado)
- Senha forte obrigatória na primeira execução

## Performance

### Otimizações Implementadas

1. **Cache com TTL**: Configurações e queries frequentes
2. **Worker Threads**: Operações de longa duração não bloqueiam UI
3. **Índices de Banco**: Queries otimizadas
4. **Lazy Loading**: Abas carregam dados sob demanda

### Monitoramento

- Estatísticas de cache disponíveis
- Logging de performance em operações críticas
- Métricas de hit/miss de cache

## Escalabilidade

### Vertical

- Aumentar número de câmeras por instância
- Upgrade de hardware (CPU, RAM)

### Horizontal

- Instâncias múltiplas monitorando câmeras diferentes
- Banco de dados centralizado compartilhado
- Balanceamento de carga de Evolution API

## Manutenibilidade

### Logging

- Estruturado com níveis (DEBUG, INFO, WARNING, ERROR)
- Rotation por tamanho e data
- Filtro automático de dados sensíveis

### Testes

- Testes unitários com pytest
- Fixtures reutilizáveis
- Mock de dependências externas

### Documentação

- Docstrings Google style em todos os métodos públicos
- Type hints em toda codebase
- Diagramas de arquitetura

## Próximas Melhorias

1. **Migração para PostgreSQL**: Para maior escalabilidade
2. **API REST**: Para integração com sistemas externos
3. **Docker**: Para facilidade de deployment
4. **Monitoramento**: Prometheus + Grafana
5. **CI/CD**: GitHub Actions para testes automáticos
