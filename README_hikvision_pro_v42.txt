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
