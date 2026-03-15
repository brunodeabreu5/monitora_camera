# Teste de Nome da Câmera

## Problema Reportado

O erro 500 no alertStream só acontece quando o nome da câmera é personalizado.

## Investigação Realizada

1. **URL do alertStream não usa o nome da câmera**
   - URL: `http://{ip}:{port}/ISAPI/Event/notification/alertStream`
   - O nome da câmera é usado apenas para logs e nomes de arquivos

2. **Código não valida o nome da câmera**
   - O nome da câmera é usado apenas em:
     - Logs de status
     - Nomes de arquivos de snapshot (`.jpg`)
     - Nomes de arquivos XML (`.xml`)
     - Nomes de arquivos JSON (`.json`)

## Possíveis Causas

### 1. Caracteres Especiais no Nome

Caracteres como `/`, `\`, `:`, `?`, `*`, `"`, `<`, `>`, `|`, espaços excessivos podem causar problemas:

```python
# Problema com espaços
"Rua 1" → "Rua 1.jpg" (OK)
"Rua 1 Teste" → "Rua 1 Teste.jpg" (OK)

# Problema com caracteres especiais
"Teste/Camera" → Não pode ser usado em nome de arquivo
"Teste\Camera" → Windows não suporta \ em nomes de arquivos
```

### 2. Encoding UTF-8

Nomes com acentos (ex: "Câmera 1", "Médico") podem causar problemas em:
- Windows (compatibilidade de nomes de arquivos)
- Logs
- Banco de dados

### 3. Câmera com Nome Não Padrão

A câmera pode ter regras de validação que bloqueiam nomes não padrão.

## Solução

### Opção 1: Usar Nome Simples

Use nomes sem caracteres especiais:

✅ **Recomendado:**
- "Camera 1"
- "Rua 1"
- "Camera A"

❌ **Evite:**
- "Teste/Camera"
- "Teste\Camera"
- "Teste:Camera"
- "Câmera 1"
- "Rua 1 (Teste)"

### Opção 2: Sanitizar Nomes

O aplicativo já tenta sanitizar nomes de arquivos, mas você pode tentar manualmente:

```python
import re

def sanitize_camera_name(name: str) -> str:
    # Remove caracteres inválidos
    name = re.sub(r'[<>:"|?*\\]', '', name)
    # Remove espaços excessivos
    name = re.sub(r'\s+', '_', name)
    # Limita tamanho
    name = name[:50]
    return name

# Exemplos:
sanitize_camera_name("Teste/Camera") → "TesteCamera"
sanitize_camera_name("Rua 1 Teste") → "Rua_1_Teste"
sanitize_camera_name("Câmera 1") → "Cmera_1" (acento removido)
```

### Opção 3: Usar IP da Câmera

Em vez de nome personalizado, use o IP na configuração:

- Campo "Nome": "Rua 1" (apenas para visualização)
- Campo "IP": "192.168.1.64" (usado na conexão)

## Teste

1. Altere o nome da câmera para algo simples
   ```
   Antes: "Rua 1 Teste"
   Depois: "Camera 1"
   ```

2. Salve e reinicie o monitoramento

3. Verifique se o erro 500 ainda acontece

## Diagnosticar Nome Problemático

Use este script para verificar se o nome da câmera tem caracteres problemáticos:

```python
import re
import json

def test_camera_name(name: str):
    issues = []
    
    # Caracteres inválidos para nomes de arquivos
    invalid_chars = r'[<>:"|?*\\]'
    if re.search(invalid_chars, name):
        issues.append("Contém caracteres inválidos para nomes de arquivos")
    
    # Caracteres problemáticos para Windows
    problematic_chars = ['/', '\\', ':']
    for char in problematic_chars:
        if char in name:
            issues.append(f"Contém caractere problemático: '{char}'")
    
    # Nome muito longo
    if len(name) > 50:
        issues.append(f"Nome muito longo ({len(name)} caracteres)")
    
    # Nome muito curto
    if len(name) < 2:
        issues.append("Nome muito curto")
    
    # Acentos
    if any(ord(c) > 127 for c in name):
        issues.append("Contém caracteres acentuados")
    
    return issues

# Teste com diferentes nomes
test_names = [
    "Camera 1",
    "Rua 1 Teste",
    "Teste/Camera",
    "Teste\\Camera",
    "Teste:Camera",
    "Câmera 1"
]

for name in test_names:
    issues = test_camera_name(name)
    print(f"\nNome: '{name}'")
    if issues:
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ Nome OK")
```

## Conclusão

Se o erro 500 desaparecer ao usar um nome simples (ex: "Camera 1"), o problema é caracteres especiais no nome da câmera.

Tente usar nomes padrão como:
- "Camera 1"
- "Camera 2"
- "Camera A"
- "Rua 1"

Se o erro persistir mesmo com nomes simples, o problema pode estar em outro lugar (configuração da câmera, firmware, etc.).