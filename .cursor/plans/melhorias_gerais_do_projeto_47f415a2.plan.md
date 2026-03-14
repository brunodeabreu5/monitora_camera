---
name: Melhorias gerais do projeto
overview: "Plano de melhorias identificadas após análise do projeto monitora_camera: dependências, testes, documentação, UX, robustez e boas práticas."
todos: []
isProject: false
---

# Análise do projeto e melhorias sugeridas

## Visão geral do projeto

O app **Hikvision Radar Pro V4.2** é uma aplicação desktop (PySide6) para monitoramento de câmeras Hikvision (radar/ANPR), com fluxo de eventos via XML, limite de velocidade, integração Evolution API (WhatsApp), SQLite e várias abas (dashboard, monitor, câmeras, evolution, histórico, relatório, usuários). A estrutura está organizada em [src/](src/) (core + app), [ui/](ui/) (tabs, widgets, workers), [tests/](tests/) (um único arquivo de testes), [scripts/](scripts/) e [docs/](docs/).

---

## 1. Dependências e setup

**Situação:** As dependências estão apenas em [configs/requirements_hikvision_pro_v4.txt](configs/requirements_hikvision_pro_v4.txt). Quem clona e roda `pip install -r requirements.txt` na raiz não encontra arquivo.

**Melhoria:**

- Criar **requirements.txt na raiz** que inclua ou referencie `configs/requirements_hikvision_pro_v4.txt` (por exemplo, com `-r configs/requirements_hikvision_pro_v4.txt`), ou copiar o conteúdo e manter os dois em sync.
- Opcional: adicionar **pyproject.toml** com `[project]` e dependências para instalação moderna (`pip install -e .`).

---

## 2. Testes

**Situação:** Há um único arquivo de testes, [tests/test_hikvision_pro_v42_app.py](tests/test_hikvision_pro_v42_app.py), com cerca de 35 métodos cobrindo config, camera_client, evolution_client, parsing, worker, database e main window. Não há testes dedicados para as abas de UI (history, report, dashboard, users), nem para [ui/widgets.py](ui/widgets.py) (exceto PasswordField) ou para [src/detection/](src/detection/).

**Melhorias:**

- **Testes unitários adicionais:** Cobrir `format_datetime_br` (formato BR e fallback), `CameraClient.download_snapshot` com Basic auth e resposta vazia, e edge cases de parsing (XML com namespace, tags inesperadas).
- **Testes de integração opcionais:** Um teste que carrega config de exemplo, inicia workers com mock do `alertStream` e verifica fluxo até `event_received` (sem rede real).
- **Organização:** Manter um único arquivo é aceitável; se crescer, separar por módulo (ex.: `test_config.py`, `test_parsing.py`, `test_camera_client.py`) e um `test_integration.py` para fluxos maiores.
- **Execução:** Documentar no README como rodar testes (`python -m pytest tests/` ou `python -m unittest discover tests`), garantindo que funcione com `QT_QPA_PLATFORM=offscreen` já usado no código.

---

## 3. .gitignore e artefatos

**Situação:** [.gitignore](.gitignore) cobre `output/`, `*.db`, `hikvision_pro_v42_config.json`, build, IDE, etc. Arquivos `test_config_*.json` (gerados por testes) podem acabar no repositório se criados na raiz.

**Melhoria:**

- Adicionar ao `.gitignore`: `test_config_*.json` (e, se existir, `output/` já está).

---

## 4. Documentação

**Situação:** [README.md](README.md) está bom (features, instalação, configuração, uso). Há placeholder "Add screenshots here when available". [docs/SECURITY.md](docs/SECURITY.md) e [docs/AGENTS.md](docs/AGENTS.md) existem.

**Melhorias:**

- **Screenshots:** Quando houver, adicionar ao README (login, monitor, último evento, Evolution).
- **CHANGELOG:** Criar `CHANGELOG.md` (ou seção "Releases" no README) com versões e mudanças relevantes para facilitar upgrades e troubleshooting.
- **Versão no app:** Expor número de versão no título da janela ou em "Sobre" (constante em [src/core/config.py](src/core/config.py) ou em `main.py`) para suporte e logs.

---

## 5. UX e consistência da interface

**Situação:** Interface em português com alguns termos em inglês (ex.: "snapshot"). Labels e mensagens estão majoritariamente em PT. Filtros de data em Histórico e Relatório são campos de texto livre.

**Melhorias:**

- **Filtro de data:** Na aba Histórico e na de Relatório, adicionar placeholder ou hint no campo Data (ex.: "DD/MM/AAAA ou AAAA-MM-DD") para alinhar ao formato BR usado no app ([format_datetime_br](src/core/config.py)).
- **Validação de configuração:** Ao salvar câmera, validar IP (formato básico ou hostname) e porta numérica; ao salvar Evolution, validar URL base e, se possível, token/instância não vazios quando integração estiver habilitada. Mostrar QMessageBox com erro claro em caso de falha.
- **Mensagens de erro:** Revisar mensagens genéricas (ex.: "Snapshot nao suportado nesse firmware") para incluir sugestão (usar URL de snapshot customizada, verificar usuário/senha, TCP).

---

## 6. Robustez e tratamento de erros

**Situação:** Há uso de `log_runtime_error`, `append_log` e QMessageBox em vários pontos. Workers e Evolution já tratam exceções e emitem status.

**Melhorias:**

- **Evolution:** Em [src/core/evolution_client.py](src/core/evolution_client.py), em falha de envio de mídia já existe fallback para texto; garantir que a mensagem de status final (ex.: "sem foto: ative Salvar snapshot...") seja clara quando não houver imagem.
- **EventWorker:** Em [ui/workers.py](ui/workers.py), em exceção não tratada no loop do stream, garantir que o status emitido indique "reconectando" ou "erro" e que o worker não saia silenciosamente; já existe `except Exception` no `run` – revisar se todos os caminhos reemitem ou reconectam de forma visível.
- **Banco de dados:** Em [src/core/database.py](src/core/database.py), operações já usam lock; em disco cheio ou SQLite travado, considerar tratar exceções e retornar mensagem amigável em vez de propagar traceback cru.

---

## 7. Segurança

**Situação:** Config com credenciais não versionada (.gitignore). Senhas de usuário do app são hasheadas (hash_password). Senhas de câmera e token Evolution ficam em texto plano no JSON.

**Melhorias (opcionais, maior escopo):**

- Documentar claramente em README/SECURITY que o arquivo de config contém credenciais em texto plano e deve ter permissões restritas.
- Não logar trechos de config (URL com user/pass, token) em `append_log` ou em arquivos de log; já parece não haver log de senha – apenas confirmar e evitar log de `evolution_cfg` ou `camera_cfg` completos.

---

## 8. Performance e escalabilidade

**Situação:** Histórico e Relatório carregam eventos via [Database.filtered_events](src/core/database.py) e [recent_events_with_speed](src/core/database.py) sem paginação explícita; a tabela de "Eventos recentes" no Monitor é preenchida por eventos em tempo real (tamanho limitado pelo uso).

**Melhoria (opcional):**

- Se o número de eventos for muito grande (milhares), considerar **paginação ou limite** na aba Histórico e no Relatório (ex.: LIMIT 500 + "Carregar mais" ou página anterior/próxima) para evitar travamentos e uso excessivo de memória.

---

## 9. Resumo prioritizado


| Prioridade | Melhoria                                                                          |
| ---------- | --------------------------------------------------------------------------------- |
| Alta       | requirements.txt na raiz (ou pyproject.toml) para setup imediato                  |
| Alta       | .gitignore: test_config_*.json                                                    |
| Média      | Testes: format_datetime_br, download_snapshot (Basic + vazio), parsing edge cases |
| Média      | Validação ao salvar câmera (IP, porta) e Evolution (URL quando habilitado)        |
| Média      | Placeholder/hint no filtro de data (Histórico e Relatório)                        |
| Baixa      | README: screenshots quando disponíveis, como rodar testes                         |
| Baixa      | CHANGELOG ou seção de releases; versão visível no app                             |
| Baixa      | Revisar mensagens de erro (snapshot, Evolution) para serem mais acionáveis        |
| Opcional   | Paginação ou limite em Histórico/Relatório para muitos eventos                    |
| Opcional   | Revisar logs para não expor credenciais                                           |


Nenhuma mudança obrigatória na arquitetura atual; as melhorias são incrementais e podem ser implementadas em partes.