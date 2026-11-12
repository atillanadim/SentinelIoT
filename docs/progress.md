# Progresso do projeto

**Fase atual:** MVP local concluído; Fase 1 (runtime em container) pendente.
**Última atualização:** 2026-11-12

## MVP local (concluído em 2026-11-12)

Entrega de um ciclo funcional de demonstração e operação assistida no host de
desenvolvimento, sem Docker e sem alterar firewall. Decisão registrada em
[ADR-0014](decisions/ADR-0014.md).

Implementado:

- CLI com banner ASCII (projeto, autor `s0ra` e versão) e shell interativo.
- Perfis `camera-http`, `router-admin`, `ssh-banner` e `telnet-iot`.
- Estado persistido das iscas e inclusão/remoção em tempo de execução.
- Agente em segundo plano com reconciliação dinâmica das iscas.
- Servidores HTTP, SSH e Telnet falsos, sem armazenar corpos ou credenciais.
- Spool JSONL append-only e coletor incremental com deduplicação por evento.
- SQLite com eventos, suspeitos/lista de ban, auditoria e configurações.
- Decisões `pending`, `blocked`, `allowed`, `ignored` e `allowlisted`.
- Exportação da lista de ban em JSON e CSV.
- Comandos `simulate`, `scan`, `diagnostics`, `status`, `start` e `stop`.

Evidências (Windows 11, Python 3.11.16, uv):

| Verificação | Comando | Resultado |
|---|---|---|
| Testes | `uv run pytest -q` | 50 passed |
| Lint | `uv run ruff check src tests` | All checks passed |
| Tipagem | `uv run mypy src` | Success: no issues em 34 arquivos |
| Versão | `.\sentineliot.cmd version` | `SentinelIoT 0.1.0`, autor `s0ra` |
| Shell/banner | `.\sentineliot.cmd --no-color shell` | banner ASCII e prompt `sentineliot>` |
| Início | `.\sentineliot.cmd --data-dir data/e2e start` | daemon e `camera-01` ativos |
| Interação HTTP | `GET /server-status` com UA `nikto` | 200 e dois eventos classificados |
| Coleta | `.\sentineliot.cmd --data-dir data/e2e scan` | 2 eventos novos, 1 IP novo |
| Lista de ban | `.\sentineliot.cmd --data-dir data/e2e bans list` | IP observado com severidade `high` |
| Parada | `.\sentineliot.cmd --data-dir data/e2e stop` | agente encerrado e spool coletado |

Limitações conhecidas desta etapa:

- `bans block` não aplica firewall; apenas registra a decisão.
- O runtime local não substitui o isolamento do container previsto na Fase 1.
- Em caminhos Windows com acentos, `uv run sentineliot` falha porque o Python
  3.11 lê o arquivo `.pth` do uv com `cp1252`. O launcher `sentineliot.cmd`
  contorna o problema com `PYTHONPATH`.

## 0. Laboratório Linux (concluído)

Autorização registrada em `docs/lab-authorization.md`. Escopo: rede host-only
`192.168.57.0/24`, VM `sentinel-lab` e, se necessário, VM `attacker`. A rede
doméstica `192.168.1.0/24` e a Internet não fazem parte dos testes.

Já executado:

- Adaptador `VirtualBox Host-Only Ethernet Adapter #2` criado.
- IP do host no adaptador: `192.168.57.1/24`.
- DHCP host-only: `192.168.57.100`–`192.168.57.254`, habilitado.
- VM `sentinel-lab` criada (UUID `ce1c93b3-22a2-4d39-a574-24a7edfe2dcc`).
- Disco VDI de 20 GB criado (UUID `8827a082-165c-4ffc-a6fa-d8c14f3133bf`).
- 2 vCPU, 4096 MB de RAM, áudio e USB desabilitados.
- NIC 1 host-only no adaptador #2; sem NAT e sem bridge.
- ISO oficial Ubuntu 24.04.5 Server baixada e validada: SHA-256
  `97f3d7ffb032c3eb3b23d2c8be9cc76e60c2c1f2c0146ba5ba9fe01cafae0fd8`.
- Template de autoinstall com SSH e IP fixo em
  `D:\VMs\sentinel-lab\autoinstall_user_data`.
- Bundle offline criado (`D:\VMs\sentinel-lab\offline-bundle`) e empacotado em
  `sentinel-bundle.iso`:
  repositório APT local com 93 pacotes, CPython 3.11.16 (SHA-256 validado),
  uv 0.12.5, Docker static 29.9.3, Compose v5.6.1, imagem `hello-world`,
  48 wheels `cp311` e `install.sh`.
- Ubuntu 24.04.5 instalado via autoinstall; VM liga com
  `192.168.57.10/24` e **sem rota padrão**.
- Provisionamento offline executado como root; `pytest`, `ruff` e `mypy`
  aprovados dentro da VM.
- Snapshots `clean-os` e `toolchain-ready` criados.
- Restauração dos dois snapshots testada com sucesso.
- Isolamento revalidado após cada restauração.
- ISO regenerado com o `install.sh` final e verificado por hash.

Pendente:

- Nada nesta etapa. A Fase 1 pode ser iniciada.

## 1. Decisões do responsável

- Fase 0 completa, incluindo validação do Docker.
- Runtime oficial: VM Linux dedicada, com paridade de produção desde o início.
- Licença: adiada; não criar `LICENSE` por enquanto.
- Python: 3.11.16.

## 2. Concluído

- Leitura integral da especificação mestre.
- Inspeção do ambiente Windows, ferramentas, rede, Docker, WSL e VirtualBox.
- Definição da arquitetura e da topologia de laboratório.
- Criação do repositório Git local e da estrutura inicial.
- Configuração do projeto Python 3.11 com dependências fixadas.
- Documentação inicial, modelo de ameaças, plano de testes e 12 ADRs.
- Smoke test, lint, tipagem e auditoria de dependências.
- Validação do Docker Desktop com `hello-world`.

## 3. Pendente

- Iniciar a Fase 1: migrar as iscas locais para o runtime isolado em Docker.
- Manter o mesmo contrato de spool JSONL, eventos e banco entre os runtimes.
- Validar publicação de porta e rede interna do Docker na Fase 1.
- Definir licença antes de distribuição.

## 4. Fora de escopo da Fase 0

- Honeypot funcional (coberto depois pelo MVP local).
- Agente funcional (coberto depois pelo MVP local).
- Banco de eventos (coberto depois pelo MVP local).
- CLI funcional (coberto depois pelo MVP local).
- Notificações.
- Adaptador de firewall.
- Qualquer alteração de firewall, rede ou dispositivo real.

## 5. Testes e evidências reais

Ambiente: Windows 11, Python 3.11.16 (uv), Docker Desktop 29.9.2.

| Verificação | Comando | Resultado |
|---|---|---|
| Python | `uv run python --version` | Python 3.11.16 |
| Dependências | `uv sync --frozen --dry-run` | 49 pacotes; nenhuma alteração |
| Sync real | `uv sync --frozen` | 49 pacotes checados; nenhuma alteração |
| Smoke test | `uv run pytest` | 1 passed em 0,26 s |
| Lint | `uv run ruff check .` | All checks passed |
| Tipagem | `uv run mypy src` | Success: no issues em 11 arquivos |
| Vulnerabilidades | `uv run pip-audit` | Nenhuma vulnerabilidade conhecida; projeto local não auditável no PyPI |
| Docker daemon | `docker info --format '{{.ServerVersion}}'` | 29.9.2 |
| Docker execução | `docker run --rm hello-world` | Hello from Docker! (sucesso) |
| Lockfile | `uv export --format requirements.txt --no-hashes --no-emit-project -o requirements.lock` | Arquivo gerado |

O Docker Desktop foi parado após a validação, para restaurar o estado inicial e
liberar memória. Ele não é o runtime oficial do laboratório.

### VM `sentinel-lab`

Ambiente: Ubuntu 24.04.5 LTS (kernel 6.8.0-139), Python 3.11.16,
Docker 29.9.3 static, sem rota padrão.

| Verificação | Comando | Resultado |
|---|---|---|
| Instalação | `lsb_release -ds` | Ubuntu 24.04.5 LTS |
| Endereço | `ip -brief -4 addr` | `192.168.57.10/24` em `enp0s3` |
| Rota padrão | `ip route` | Ausente (apenas `192.168.57.0/24`) |
| Python | `/usr/local/bin/python3.11 --version` | Python 3.11.16 |
| uv | `uv --version` | 0.12.5 |
| Git | `git --version` | 2.43.0 |
| Docker | `docker --version` | 29.9.3, build 5457199 |
| Compose | `docker compose version` | v5.6.1 |
| Docker daemon | `docker info` | `driver=overlayfs cgroup=systemd` |
| Docker execução | `docker run --rm hello-world` | Hello from Docker! |
| Smoke test | `.venv/bin/python -m pytest -q` | 1 passed em 0,03 s |
| Lint | `.venv/bin/python -m ruff check .` | All checks passed |
| Tipagem | `.venv/bin/python -m mypy` | Success: no issues em 11 arquivos |
| DNS externo | `getent hosts example.com` | Não resolve |
| Internet | `curl --max-time 5 http://example.com` | Bloqueado |
| Rede doméstica | `curl --max-time 5 http://192.168.1.1` | Inacessível |
| Snapshot | `VBoxManage snapshot sentinel-lab list` | `clean-os` e `toolchain-ready` |
| Restauração `clean-os` | restaurar e consultar binários | Sem Docker, uv, Python 3.11 ou projeto |
| Restauração `toolchain-ready` | restaurar e repetir testes | Docker, `hello-world`, `pytest`, `ruff` e `mypy` ok |
| ISO do bundle | `Get-FileHash sentinel-bundle.iso` | `5453307164041e5948f6c5e5d32ff35bc6a51e6ccc9421d85e764bda876b30e4` |

## 6. Riscos em aberto

- RAM do host limitada: a VM usa 4 GB; executar VM e Docker Desktop ao mesmo
  tempo pode exigir fechar aplicativos.
- Caminho com acento e diferenças de line ending.
- CI sem remote autenticado; workflow criado, não executado.
- Licença não definida.
- Assinatura formal da autorização do laboratório pendente.
- Validação de rede interna do Docker e publicação de porta pendente para a Fase 1.
- O bundle offline precisa ser regenerado quando versões mudarem.

## 7. Próximo passo

Iniciar a Fase 1: honeypot isolado em Docker dentro da VM `sentinel-lab`,
partindo do snapshot `toolchain-ready` e registrando as evidências de rede,
porta e isolamento do container.

## 8. Regra de evidência

Nenhuma tarefa será marcada como concluída sem comando reproduzível, saída real
e registro neste arquivo. Resultados de Docker no Windows não serão tratados
como homologação do laboratório Linux.
