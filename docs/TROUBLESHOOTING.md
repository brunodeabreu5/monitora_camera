# Solução de Problemas - Hikvision Radar Pro

## Problemas Comuns

### Instalação e Setup

#### Erro: ModuleNotFoundError: No module named 'PySide6'

**Sintoma**: ImportError ao executar o aplicativo

**Solução**:
```bash
pip install PySide6
# ou
pip install -e .
```

#### Erro: cryptography não instalado

**Sintoma**: Erro ao criptografar senhas

**Solução**:
```bash
pip install cryptography
```

### Conexão com Câmeras

#### Erro: Connection Refused

**Sintoma**: Não consegue conectar à câmera

**Causas possíveis**:
1. IP/porta incorretos
2. Câmera desligada
3. Firewall bloqueando
4. Rede diferente

**Solução**:
1. Verificar IP e porta na configuração da câmera
2. Ping no IP da câmera: `ping 192.168.1.64`
3. Testar no navegador: `http://192.168.1.64`
4. Verificar firewall: permitir porta 80/443

#### Erro: Authentication Failed (401/403)

**Sintoma**: Câmera rejeita credenciais

**Causas possíveis**:
1. Usuário/senha incorretos
2. Conta bloqueada
3. Método de autenticação errado

**Solução**:
1. Verificar credenciais na interface web da câmera
2. Tentar Digest Auth vs Basic Auth
3. Resetar senha da câmera se necessário

#### Erro: timeout

**Sintoma**: Conexão demora muito e dá timeout

**Causas possíveis**:
1. Rede lenta
2. Câmera sobrecarregada
3. Timeout muito curto

**Solução**:
1. Aumentar timeout na configuração da câmera (padrão: 15s)
2. Verificar latência da rede: `ping -t 192.168.1.64`
3. Reduzir número de câmeras simultâneas

### Alert Stream

#### Erro: 500 Internal Server Error

**Sintoma**: Câmera retorna HTTP 500

**Causas possíveis**:
1. EventStream não habilitado
2. Firmware desatualizado
3. Modo de tráfego não configurado

**Solução**:
1. Habilitar EventStream na interface web da câmera
2. Atualizar firmware da câmera
3. Verificar se câmera suporta modo de tráfego

#### Erro: Unsupported Media Type

**Sintoma**: Câmera rejeita requisição

**Causa**: Headers incorretos

**Solução**: Verificar `Accept` header na requisição:
```python
headers={"Accept": "multipart/x-mixed-replace, text/xml, */*"}
```

### Snapshot

#### Erro: snapshot not supported

**Sintoma**: Não consegue obter snapshot

**Causas possíveis**:
1. URL incorreta
2. Permissões insuficientes
3. Câmera em modo errado

**Solução**:
1. Tentar múltiplas URLs (configurado automaticamente)
2. Verificar permissões do usuário
3. Testar com `ISAPI/Streaming/channels/1/picture`

### Database

#### Erro: Database is locked

**Sintoma**: SQLite não consegue escrever

**Causas possíveis**:
1. Múltiplas escritas simultâneas
2. Processo anterior não liberou lock
3. Arquivo corrompido

**Solução**:
1. Aumentar timeout de conexão
2. Verificar se não há outro processo usando o banco
3. Execitar `PRAGMA wal_mode=ON` para Write-Ahead Logging
4. Como último recurso, deletar lock file `.db-wal` e `.db-shm`

#### Erro: No such column

**Sintoma**: Query falha com coluna inexistente

**Causa**: Migração de schema não executada

**Solução**:
```python
db._ensure_event_columns()  # Adiciona colunas faltantes
```

### Evolution API

#### Erro: Connection refused

**Sintoma**: Não consegue conectar ao Evolution API

**Causas possíveis**:
1. URL incorreta
2. Servidor não rodando
3. Porta errada

**Solução**:
1. Verificar URL: `http://localhost:8080`
2. Testar no navegador ou curl: `curl http://localhost:8080`
3. Verificar logs do Evolution API

#### Erro: Invalid API Token

**Sintoma**: 401 Unauthorized

**Sausa**: Token incorreto ou expirado

**Solução**:
1. Regenerar token no Evolution API
2. Atualizar na configuração
3. Verificar se instância está correta

### Performance

#### Aplicação travando

**Sintoma**: UI não responde

**Causas possíveis**:
1. Operação pesada na thread principal
2. Muitas câmeras simultâneas
3. Memory leak

**Solução**:
1. Mover operações pesadas para worker threads
2. Reduzir número de câmeras simultâneas
3. Monitorar uso de memória: verificar com `top` ou Gerenciador de Tarefas
4. Reiniciar aplicação periodicamente

#### Uso elevado de CPU

**Sintoma**: CPU constantemente alta

**Causas possíveis**:
1. Polling muito frequente
2. Processamento de imagem pesado
3. Loop sem sleep

**Solução**:
1. Aumentar intervalo entre polls
2. Otimizar detecção de veículos
3. Adicionar `time.sleep()` em loops

### Interface Gráfica

#### Erro: QWidget: Must construct a QApplication before

**Sintoma**: Crash ao iniciar

**Causa**: QApplication não criado

**Solução**:
```python
from PySide6.QtWidgets import QApplication

app = QApplication([])
# Depois criar widgets
```

#### Erro: Segmentation fault

**Sintoma**: Crash abrupto

**Causas possíveis**:
1. Objeto Qt deletado prematuramente
2. Problema com threads Qt
3. Biblioteca faltando

**Solução**:
1. Manter referência a widgets Qt
2. Usar signals/slots em vez de chamadas diretas entre threads
3. Reinstalar PySide6

## Debugging

### Ativar Logging Detalhado

```python
from src.core.logging_config import setup_logging

logger = setup_logging(log_level='DEBUG', log_to_file=True, log_to_console=True)
```

### Ver Logs

```bash
# Linux/Mac
tail -f hikvision_pro_v42.log

# Windows PowerShell
Get-Content hikvision_pro_v42.log -Wait
```

### Modo Verbose

```bash
# Executar com verbose
python main.py --verbose --debug
```

### Testar Conexão Manualmente

```python
from src.core.camera_client import CameraClient

camera_config = {
    "camera_ip": "192.168.1.64",
    "camera_port": 80,
    "camera_user": "admin",
    "camera_pass": "password",
    "timeout": 15
}

client = CameraClient(camera_config)
success, status, message = client.test_connection()
print(f"Success: {success}, Status: {status}, Message: {message}")
```

## Manutenção Preventiva

### Backup de Configuração

```bash
# Backup manual
cp hikvision_pro_v42_config.json config_backup_$(date +%Y%m%d).json

# Backup de banco
cp events_v42.db events_backup_$(date +%Y%m%d).db
```

### Limpeza de Logs Antigos

```python
import os
from pathlib import Path
from datetime import datetime, timedelta

log_dir = Path(".")
cutoff = datetime.now() - timedelta(days=30)

for log_file in log_dir.glob("*.log.*"):
    if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
        log_file.unlink()
```

### Otimizar Database

```sql
-- Rebuild database
VACUUM;

-- Analisar para otimizar queries
ANALYZE;

-- Reconstruir índices
REINDEX;
```

### Limpar Cache

```python
from src.core.cache import cleanup_all_expired_caches

removed = cleanup_all_expired_caches()
print(f"Removidas {sum(removed.values())} entradas expiradas")
```

## Suporte

### Informar Bug

Ao informar um bug, incluir:

1. Versão do Python: `python --version`
2. Versão do Hikvision Radar Pro: ver no arquivo `config.py`
3. Sistema operacional
4. Mensagem de erro completa
5. Passos para reproduzir
6. Logs relevantes

### Pedir Feature

Ao solicitar uma nova funcionalidade:

1. Descrever o problema que resolve
2. Propor solução
3. Justificar benefícios
4. Considerar impacto em outras partes do sistema

## Recursos Externos

### Documentação de Câmeras Hikvision

- [Hikvision iDS-TCM403](https://www.hikvision.com/en/products/)
- [ISAPI Reference](https://open.hikvision.com/)
- [RTSP Setup Guide](https://www.hikvision.com/en/

### Evolution API

- [Documentation](https://doc.evolution-api.com/)
- [GitHub](https://github.com/EvolutionAPI/evolution_api)

### Comunidades

- Stack Overflow (tag: python, pyside6)
- Reddit r/Python
- Fórum Qt
