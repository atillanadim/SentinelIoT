# Laboratório isolado

**Versão:** 1.0 (laboratório provisionado)
**Estado:** VM `sentinel-lab` provisionada e isolada; snapshots `clean-os` e
`toolchain-ready` criados, com restauração testada.

## 1. Decisão

O runtime oficial do MVP será executado integralmente em uma VM Linux dedicada.
O Windows é usado apenas para edição, lint, mypy e testes unitários rápidos. O
Docker Desktop no Windows pode ser usado para verificação de CLI, mas não é o
ambiente de segurança do produto.

## 2. Topologia proposta

```text
Windows 11 host
  |-- VS Code / Git / uv / testes unitarios
  |
  |-- VirtualBox
        |-- VM sentinel-lab (Ubuntu 22.04/24.04 ou Debian 12)
        |     |-- agente SentinelIoT (non-root)
        |     |-- Docker Engine
        |     |-- honeypot container
        |     |-- SQLite
        |     `-- (Fase 5) nftables + helper restrito
        |
        `-- VM attacker (Kali ou Debian)
              `-- ferramentas de teste controladas
```

Rede host-only dedicada. Sem bridge para a rede doméstica durante os testes.

## 3. Especificação das VMs

### sentinel-lab

- 2 vCPU (4 se o host permitir).
- 4 GB de RAM.
- 20 GB de disco dinâmico.
- Ubuntu 22.04 LTS, Ubuntu 24.04 LTS ou Debian 12, x86_64.
- Docker Engine + Compose plugin.
- Python 3.11.16 e uv.
- Usuário não-root para o agente.
- Snapshot limpo antes de instalar Docker.
- Snapshot adicional antes de qualquer teste de nftables.

### attacker

- 1–2 vCPU.
- 2 GB de RAM.
- Kali Linux ou Debian com ferramentas mínimas.
- Sem acesso à Internet durante os testes, se possível.
- Usada somente para gerar conexões controladas à isca.

## 4. Plano de endereçamento sugerido

| Elemento | Endereço sugerido |
|---|---|
| Rede host-only | 192.168.57.0/24 |
| Gateway host-only | 192.168.57.1 |
| sentinel-lab | 192.168.57.10 |
| attacker | 192.168.57.20 |
| Porta da isca | 8080/tcp |
| Allowlist mínima | 192.168.57.1/32, 192.168.57.10/32, 127.0.0.1/32 |

A rede 192.168.56.0/24 já é usada por outras VMs do host. Recomenda-se não
reutilizá-la para evitar interferência entre experimentos.

### 4.1 Estado real do provisionamento (2026-11-08)

Já executado e verificado:

- Adaptador host-only novo criado no VirtualBox:
  `VirtualBox Host-Only Ethernet Adapter #2`,
  GUID `c8ab6a0c-8cec-4306-b445-94df7a08b939`.
- Endereço do host no adaptador: `192.168.57.1/24`.
- DHCP do adaptador: `192.168.57.100` a `192.168.57.254`, habilitado.
- Nenhuma VM em execução no momento da criação.
- VM `sentinel-lab` criada e registrada, UUID
  `ce1c93b3-22a2-4d39-a574-24a7edfe2dcc`, pasta `D:\VMs\sentinel-lab`.
- Disco VDI de 20 GB criado, UUID
  `8827a082-165c-4ffc-a6fa-d8c14f3133bf`.
- 2 vCPU, 4096 MB de RAM, áudio desabilitado, USB desabilitado.
- NIC 1 em modo host-only, conectada ao adaptador #2; sem NAT e sem bridge.
- ISO oficial `ubuntu-24.04.5-live-server-amd64.iso` baixada e validada:
  SHA-256 `97f3d7ffb032c3eb3b23d2c8be9cc76e60c2c1f2c0146ba5ba9fe01cafae0fd8`
  (confere com `SHA256SUMS` oficial).
- Bundle offline criado em `D:\VMs\sentinel-lab\offline-bundle` e empacotado
  como `D:\VMs\sentinel-lab\sentinel-bundle.iso` (257 MB, rótulo
  `SENTINELBUNDLE`):
  - repositório APT local com 93 pacotes (Git, curl, jq, iproute2, tcpdump,
    iptables, nftables, conntrack, openssl e dependências);
  - CPython 3.11.16 standalone, SHA-256
    `25844eb97cdc72cdc78addaad0969ce3b2133a4de54bfcfa4d57f8a6d095eaab`
    validado;
  - uv 0.12.5, Docker Engine 29.9.3 static, Compose v5.6.1;
  - imagem `hello-world` salva para teste sem rede;
  - 48 wheels `cp311`/manylinux das dependências do projeto;
  - cópia do código-fonte sem `.git` e sem `.venv`;
  - `install.sh` idempotente.
- Instalação não assistida iniciada em 2026-11-08 com autoinstall próprio
  (IP fixo `192.168.57.10/24`, sem gateway padrão, `shutdown: poweroff`).
- IP fixo da VM: `192.168.57.10/24`, **sem gateway padrão**.
- SSH habilitado somente na rede host-only. O acesso real foi por **senha**;
  a chave em `D:\VMs\sentinel-lab\id_ed25519` foi configurada no autoinstall,
  mas não foi aplicada pelo instalador (autenticação por chave falhou).
- Credenciais locais em `D:\VMs\sentinel-lab\credentials.txt` (fora do
  controle de versão).

Concluído e verificado em 2026-11-08:

- Ubuntu 24.04.5 LTS instalado via autoinstall; a VM liga com
  `192.168.57.10/24` e **sem rota padrão**.
- `install.sh` do bundle executado como root; todas as etapas concluídas.
- Versões reais na VM: Python 3.11.16, uv 0.12.5, Git 2.43.0,
  Docker 29.9.3 (static) e Compose v5.6.1.
- Docker ativo com `driver=overlayfs` e `cgroup=systemd`; imagem
  `hello-world` executada sem rede.
- Projeto validado dentro da VM: `pytest` 1 passed, `ruff` sem violações e
  `mypy` sem erros em 11 arquivos.
- Isolamento revalidado: DNS externo indisponível, Internet bloqueada e
  `192.168.1.1` inacessível.
- Snapshot `clean-os` com UUID `077990be-a08d-47e5-b0eb-e0bca653df00`.
- Snapshot `toolchain-ready` com UUID
  `c0d814a5-65db-462b-8b0d-efca1d042c5d`.
- Restauração de `clean-os` testada: sem Docker, uv, Python 3.11 ou projeto
  (apenas o Git do SO base).
- Restauração de `toolchain-ready` testada: Docker, `hello-world`, `pytest`,
  `ruff` e `mypy` novamente aprovados.
- ISO do bundle regenerado com o `install.sh` final: 256,8 MB, SHA-256
  `5453307164041e5948f6c5e5d32ff35bc6a51e6ccc9421d85e764bda876b30e4`.
- DVD do bundle desanexado; ordem de boot `disk` e depois `dvd`.

## 5. Sequência de preparação

1. Registrar autorização em `docs/lab-authorization.md`.
2. Criar rede host-only dedicada no VirtualBox (requer autorização).
3. Criar as VMs e instalar o sistema.
4. Atualizar o sistema e instalar Docker, Git, Python 3.11 e uv.
5. Criar snapshot limpo.
6. Clonar o repositório ou montar uma pasta compartilhada.
7. Executar `scripts/setup_lab.sh`.
8. Executar `uv sync` e os testes da fase.
9. Validar que não há rota para a rede doméstica ou Internet.
10. Registrar evidências em `docs/progress.md`.

## 6. Teste de isolamento

Antes de qualquer teste ofensivo:

```bash
ip route
ip addr
getent hosts example.com || true
curl --max-time 3 http://example.com || true
```

O esperado é que a VM não tenha rota não autorizada. Se houver rota, corrigir a
configuração de rede ou desconectar o adaptador antes de continuar.

Também verificar:

```bash
docker inspect sentineliot-camera-01 --format '{{.Config.User}}'
docker inspect sentineliot-camera-01 --format '{{json .HostConfig.CapDrop}}'
docker inspect sentineliot-camera-01 --format '{{json .HostConfig.SecurityOpt}}'
```

Os comandos acima só fazem sentido depois da Fase 1.

## 7. O que o laboratório não é

- Não é a rede doméstica de produção.
- Não é um ambiente de teste de dispositivos reais.
- Não é um gateway de produção.
- Não é autorização para escanear terceiros.
- Não é uma fronteira de segurança absoluta.

## 8. Limitações

- A VM e os dois snapshots já existem; qualquer experimento deve partir de
  `toolchain-ready` e ser descartado restaurando esse snapshot.
- A toolchain é instalada a partir de um ISO offline; atualizações exigem
  regenerar o bundle.
- A criação de rede host-only altera o VirtualBox e exige autorização.
- VirtualBox e WSL2/Hyper-V podem coexistir com custo de desempenho.
- O host tem 16 GB de RAM; executar VMs e Docker ao mesmo tempo exige
  monitoramento.
- O caminho do projeto contém acento; pastas compartilhadas devem ser testadas.

## 9. Critérios de saída

- Autorização registrada.
- Rede host-only dedicada criada e documentada.
- VM Linux provisionada e atualizada.
- Docker funcional.
- Nenhuma rota não autorizada.
- Snapshot restaurável.
- `scripts/setup_lab.sh` e testes da fase executados com evidência.
