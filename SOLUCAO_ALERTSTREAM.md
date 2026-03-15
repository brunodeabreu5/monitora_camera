# Solução do Erro 500 no AlertStream

## Problema Detectado

As câmeras estão retornando erro 500 ao tentar conectar ao alertStream (ISAPI/Event/notification/alertStream). Isso impede o monitoramento em tempo real.

## Causas Possíveis

1. **Câmera não suporta alertStream** - Câmeras antigas ou modelos diferentes podem não suportar o endpoint de notificação de eventos
2. **AlertStream não configurado na câmera** - A função de notificação de eventos pode estar desabilitada na câmera
3. **Firmware desatualizado** - A câmera pode estar com firmware antigo que não suporta alertStream
4. **Modo de câmera incorreto** - A câmera pode estar em modo "normal" quando deveria estar em "traffic" ou "auto"

## Solução 1: Configurar Modo Traffic na Câmera (Recomendado)

### Para câmeras Hikvision iDS-TCM403-GIR:

1. Acesse a câmera via navegador (ex: http://192.168.1.64)
2. Navegue até **ISAPI > Traffic > TrafficDetection**
3. Ative **"TrafficDetection"** ou **"Enable"**
4. Configure os parâmetros necessários (zona de detecção, sensibilidade, etc.)
5. Nas câmeras com radar, configure **"Traffic Mode"** como **"Traffic"** ou **"Auto"**
6. Acesse **ISAPI > System > Events > Event Notification**
7. Configure o **"Alert Stream"** para **"Enable"**
8. Teste a conexão pelo aplicativo

### Sobre alertStream:

O alertStream é um stream HTTP de eventos em tempo real da câmera. Ele envia XML com dados de eventos como:
- Detecção de veículo
- ANPR (reconhecimento de placa)
- Excesso de velocidade
- Alarmes

Se a câmera não suportar alertStream, o aplicativo usa **modo snapshot** para monitoramento visual, mas não detecta eventos automaticamente.

## Solução 2: Usar Modo Snapshot (Fallback)

Se a câmera não suportar alertStream:

1. Vá na aba **Câmeras** no aplicativo
2. Selecione a câmera problemática
3. Na aba de configurações da câmera:
   - Habilite **"Habilitar monitoramento visual"**
   - Configure **"Fallback live"** como **"snapshot"**
   - Configure **"Preferencia RTSP"** como **"tcp"** (reduz problemas de vídeo)
4. Salve a configuração
5. Reinicie o monitoramento com **"Iniciar todas"**

O modo snapshot baixa uma imagem a cada 1.5 segundos, permitindo visualização ao vivo, mas **não detecta eventos automaticamente**.

## Solução 3: Atualizar Firmware

1. Entre na câmera via navegador
2. Navegue até **System > Maintenance > Firmware**
3. Baixe e instale o firmware mais recente
4. Reinicie a câmera após a atualização
5. Repita a configuração de alertStream

## Teste de Conexão

Para testar a conexão com a câmera manualmente:

```bash
python scripts/test_alertstream.py --url http://IP_DA_CAMERA --user admin --password SUA_SENHA
```

Substitua:
- `IP_DA_CAMERA` pelo IP da sua câmera
- `SUA_SENHA` pela senha da câmera

O script testará a conexão com alertStream e mostrará se há erro 500 ou se funciona corretamente.

## Verificar Modo da Câmera

O aplicativo detecta automaticamente se a câmera está em modo "traffic" ou "normal":

- **Modo Traffic**: Suporta alertStream e detecção de tráfego
- **Modo Normal**: Não suporta alertStream (use modo snapshot)

Se o modo for detectado como "normal" quando você espera "traffic", significa que a câmera não suporta o modo de tráfego ou não está configurado corretamente.

## Diagnóstico com Logs

O aplicativo exibe informações detalhadas na aba **Estado e atividade**:

1. Abra a aba **Monitor**
2. Veja a seção **Estado e atividade**
3. Clique na câmera problemática
4. O log mostrará:
   - Estado da conexão ("Conectada" / "Desconectada")
   - Detalhes do erro (se houver)
   - Mensagem de solução sugerida

## Resumo

| Cenário | Solução |
|---------|---------|
| Câmera não detecta modo traffic | Configure TrafficDetection em ISAPI |
| AlertStream retornou 500 | Verifique configuração de eventos na câmera |
| Firmware antigo | Atualize para a versão mais recente |
| Não há opção de alertStream | Use modo snapshot no aplicativo |

## Recursos Adicionais

- **Documentação ISAPI Hikvision**: http://www.hikvision.com/support/download-drivers-and-firmware
- **Tabela de compatibilidade iDS-TCM403-GIR**: Verifique se sua versão suporta alertStream
- **Suporte Hikvision**: http://www.hikvision.com/support