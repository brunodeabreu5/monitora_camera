HIKVISION RADAR PRO V4.2

Esta versao foi ajustada especificamente para evitar o endpoint:
- /ISAPI/Traffic/channels/1/vehicleDetect/alertStream

Mudancas:
- usa apenas /ISAPI/Event/notification/alertStream para eventos
- mantem fallback para camera traffic no teste
- snapshot continua opcional e nao derruba o monitor
- corrige o erro de bytes/str no stream

Recomendacao para sua iDS-TCM403-GIR:
- Modo da camera: traffic
- Canal: 101
- Teste primeiro com snapshot automatico ligado
- Se nao vier imagem, desligue snapshot automatico e foque nos eventos

Gere o EXE com:
build_hikvision_pro_v42_windows.bat

CONFIGURACAO E CREDENCIAIS
- O arquivo hikvision_pro_v42_config.json nao e versionado (esta no .gitignore).
- Use hikvision_pro_v42_config.example.json como modelo: copie para hikvision_pro_v42_config.json e preencha.
- Se o config com credenciais ja foi commitado no passado, troque a senha da camera e o token da Evolution API.
