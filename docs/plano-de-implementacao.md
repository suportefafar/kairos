# Kairos — implementação

Status: protótipo integrado em desenvolvimento. A intranet já tem migrações, API, páginas e capacidades; o agente Python tem captura, configuração, fila local e início automático. O ambiente Olympus de desenvolvimento foi atualizado a partir deste workspace.

## Arquitetura

- Agente privado em Python, empacotável com PyInstaller; configuração Windows protegida por DPAPI.
- Instalador preparado em `installer/Kairos.iss`, usando Inno Setup. O instalador não foi compilado.
- Intranet Rails 8.1 com PostgreSQL e Active Storage privado.
- Para Windows 7 SP1, o agente exige a linha Python 3.8. O suporte a essa versão terminou; considerar isso ao distribuir em computadores conectados à rede.
- Linux é suportado como ambiente local de desenvolvimento, com captura da sessão gráfica disponível.

## Fluxo

1. Administrador cadastra um computador em `/kairos/devices`; a intranet retorna uma credencial individual uma única vez.
2. Administrador adiciona horários recorrentes por dia, data de início e data final opcional.
3. Agente consulta `/api/v1/kairos/schedule` ao iniciar e a cada 30 minutos.
4. No horário, o agente captura todos os monitores, grava PNG e metadados na fila local e tenta enviar para `/api/v1/kairos/submissions`.
5. Se o envio falhar, preserva os arquivos e tenta novamente. Uma ocorrência repetida não cria outra submissão.
6. Usuário com `read_kairos_submission` pesquisa, pagina e abre a captura em `/kairos/submissions`.

## Acesso

- `manage_kairos`: cadastro de dispositivos e horários, concessão direta individual.
- `read_kairos_submission`: lista, perfil e imagem, concedida diretamente e independente da administração.
- API usa credencial de serviço individual com escopos `kairos:schedule:read` e `kairos:submissions:write`.
- Imagens são privadas e servidas por rota autenticada e autorizada.

## Teste local

Veja o [README](../README.md) para subir a intranet com `olymctl dev up intranet --no-pull`, configurar o agente Linux, cadastrar horários e validar uma submissão. O endpoint protegido redireciona para login sem sessão.

## Validações pendentes

- Fluxo autenticado completo: criar dispositivo, agendar, capturar, enviar e abrir imagem.
- Sessão Linux com X11 disponível para verificar ImageGrab.
- Construir o executável no Windows e validar em Windows 7 SP1 e Windows 10.
- Compilar o `.iss` no Inno Setup e revisar a instalação no escopo do usuário.
- Testar retentativas, suspensão, relógio/fuso e instalação em Windows 32/64 bits.
