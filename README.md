# Kairos

Agente privado de capturas para Windows e Linux de desenvolvimento, integrado à intranet FAFAR. A intranet agenda horários por computador; o agente consulta a programação a cada 30 minutos, salva imagens localmente e as envia à API autenticada.

## Componentes

- `kairos_agent.py`: configuração, captura, fila de envio, bandeja e início automático no login.
- `../intranet`: cadastro de computadores/horários, API, capacidades e páginas para consultar submissões.
- `requirements.txt`: dependências com versões fixadas.
- `build_windows.bat`: empacota o agente com PyInstaller no Windows.
- `installer/Kairos.iss`: receita do Inno Setup. O instalador não é produzido automaticamente.

O agente usa Python 3.8 para manter a possibilidade de execução no Windows 7 SP1. Python 3.8 encerrou o suporte de segurança; o Windows 7 também está fora do suporte regular. Para Windows 10, o empacotamento ainda usa a mesma linha compatível até a validação de ambos os sistemas. A documentação do Python indica a linha 3.8 para Windows 7 ([referência oficial](https://docs.python.org/3.10/using/windows.html#supported-windows-versions)).

## Testar no Linux local

### Subir a intranet de desenvolvimento

Na raiz `fafar`, execute:

```bash
(cd olympus && ./olymctl dev up intranet --no-pull)
```

A intranet usa o PostgreSQL de desenvolvimento e monta o checkout local. As migrações do Kairos já foram aplicadas em `intranet_development` neste ambiente.

### Preparar o agente

Use Python 3.8–3.11 no Linux de desenvolvimento com este conjunto fixo de dependências. Em Python 3.8, o Pillow fica fixado na série 7 para manter a compatibilidade pretendida com Windows 7; nas versões mais novas do Python usa-se Pillow 10. Em sistemas sem sessão gráfica, o agente pode consultar e enviar capturas já existentes, mas a captura da tela exige uma sessão X11 acessível.

```bash
cd kairos
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python kairos_agent.py --configure
```

Na intranet, entre com uma conta autorizada e abra `/kairos/devices`. Cadastre o computador de teste. A resposta da criação contém `token` e `api_url`; copie esses valores para a janela de configuração do Kairos. Cadastre também um horário alguns minutos à frente. Se o certificado local do Caddy não estiver no repositório de certificados do Python, exporte o certificado público da CA do proxy com `docker cp olympus-reverse-proxy-1:/data/caddy/pki/authorities/local/root.crt /tmp/kairos-dev-root.crt` e informe esse caminho no campo opcional de CA local.

O agente guarda credenciais e capturas sob `~/.local/share/Kairos` no Linux. A configuração recebe permissão `0600`. Ele cria uma entrada de início automático no login gráfico. Execute `python kairos_agent.py` para iniciar a bandeja e a sincronização. A captura usa os monitores disponíveis e produz PNG.

Conceda `read_kairos_submission` a uma conta de consulta e abra `/kairos/submissions`. Pesquise pelo nome do computador ou pelo ID; o botão **Ver** abre a imagem e os metadados.

### Encerrar e remover o início automático no Linux

Feche pelo menu da bandeja. Para desativar o início automático, remova `~/.config/autostart/kairos.desktop`. As capturas e a fila ficam em `~/.local/share/Kairos`.

## Gerar o aplicativo Windows (sem compilar o instalador)

Em Windows 7 SP1 ou Windows 10 de 64 bits com Python 3.8 e Inno Setup 6 instalados, execute `build_windows.bat`. O script gera `dist\Kairos.exe` e compila `installer\output\Kairos-Setup.exe`. O instalador é por usuário; o agente configura a inicialização automática no primeiro uso após informar o token.

No Windows, o token é protegido pelo DPAPI do usuário. Para configurar, abra o aplicativo e informe a URL retornada pela intranet e o token emitido para aquele computador. A captura depende de uma sessão interativa desbloqueada; o aplicativo não captura a tela de login.

## API e segurança

- `GET /api/v1/kairos/schedule`: recebe horários futuros do dispositivo autenticado.
- `POST /api/v1/kairos/submissions`: envia PNG e metadados multipart, com ocorrência idempotente por dispositivo, horário e data.
- `read_kairos_submission`: permite abrir listagem, perfil e imagem.
- `manage_kairos`: permite cadastrar computadores e horários; não concede acesso às capturas.

As imagens ficam no armazenamento privado da intranet e só são servidas pela rota autenticada. Não compartilhe tokens entre computadores.

Na página de computadores, **Remover dispositivo** revoga a credencial e desativa seus horários. **Remover horário** desativa apenas aquele horário. Itens removidos saem da lista ativa e aparecem em **Lixeira**; as submissões anteriores continuam preservadas.

## Estado e validação

As migrações foram aplicadas no banco local `intranet_development`. Em 11/11/2026, validei no Linux com X11 o agente, autenticação, programação, captura, envio, listagem, perfil e imagem; as páginas e rotas Rails também foram verificadas. Ainda falta empacotar e validar no Windows 7 SP1/10. O arquivo Inno Setup está preparado, mas o instalador não foi gerado.
