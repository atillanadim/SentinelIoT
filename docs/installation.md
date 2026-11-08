# Instalação e preparação do ambiente

**Versão:** 0.1 (Fase 0)

Este documento descreve o ambiente planejado. Ele não afirma que a VM Linux já
foi provisionada. O provisionamento da VM é uma operação separada, que exige
autorização e snapshot.

## 1. Matriz de ambiente

| Ambiente | Sistema | Uso |
|---|---|---|
| Desenvolvimento | Windows 11 x86_64 | Edição, lint, mypy e testes unitários rápidos. |
| Laboratório | VM Linux x86_64 (Ubuntu 22.04/24.04 ou Debian 12) | Runtime oficial, Docker, integração, segurança e nftables. |
| Produção futura | Linux homologado | Instalação real, systemd, helper restrito. |

O Windows não é o runtime oficial do MVP.

## 2. Pré-requisitos no Windows

- Windows 11 x86_64.
- Git 2.49 ou superior.
- uv 0.12 ou superior.
- Python 3.11.16 (gerenciado pelo uv ou instalado localmente).
- Docker Desktop apenas para verificação opcional; não é o laboratório.
- VS Code ou editor equivalente.

Verificação:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_lab.ps1
```

O script apenas verifica ferramentas. Ele não inicia Docker, não altera firewall
e não cria rede.

## 3. Preparação do repositório no Windows

```powershell
git clone <repositorio> D:\Códigos\SentinelIoT
cd D:\Códigos\SentinelIoT
uv venv --python 3.11
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
```

O venv do Windows é para desenvolvimento. O runtime será validado na VM.

## 4. VM Linux de laboratório

### 4.1 Especificação sugerida

- 2 vCPU (4 se o host permitir).
- 4 GB de RAM dedicada; o host tem 16 GB e pode estar sob pressão.
- 20 GB de disco dinâmico.
- Ubuntu 22.04 LTS ou 24.04 LTS, ou Debian 12, x86_64.
- Rede host-only dedicada, sugerida 192.168.57.0/24.
- Sem bridge para a rede doméstica durante os testes iniciais.
- Snapshot limpo antes de instalar Docker e antes de testar firewall.

### 4.2 Rede host-only

Recomendação:

- Criar uma rede host-only nova, separada da rede 192.168.56.0/24 já usada por
  outras VMs.
- Conectar somente as VMs do laboratório SentinelIoT.
- Não conectar a VM à Wi-Fi doméstica em modo bridge.
- Documentar IPs, gateway e escopo em `docs/lab.md`.

A criação da rede e das VMs altera o VirtualBox e deve ser autorizada.

### 4.3 Instalação na VM

Ubuntu/Debian, comandos de referência (revisar antes de executar):

```bash
sudo apt update
sudo apt install -y git curl ca-certificates docker.io docker-compose-plugin
sudo usermod -aG docker "$USER"
# Sair e entrar novamente para aplicar o grupo.
```

Instalar uv conforme a documentação oficial, fixando a versão usada no projeto.

```bash
git clone <repositorio> ~/sentineliot
cd ~/sentineliot
uv venv --python 3.11
uv sync
uv run pytest
```

Verificar Docker:

```bash
docker info
docker run --rm hello-world
```

### 4.4 Verificação de isolamento

Antes de qualquer teste ofensivo:

- Confirmar que a VM não tem rota para a Internet.
- Confirmar que a VM não alcança a rede doméstica.
- Confirmar que outras VMs do laboratório estão na rede host-only correta.
- Registrar o snapshot e o procedimento de restauração.

## 5. Docker Desktop no Windows (opcional)

O Docker Desktop instalado neste host pode ser usado para uma verificação
rápida de CLI, mas não substitui o laboratório Linux. Iniciar o Docker Desktop
consome RAM e deve ser feito com autorização.

```powershell
# Iniciar somente com autorização.
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
docker info
docker run --rm hello-world
```

## 6. O que não fazer

- Não executar `nft flush ruleset`, `iptables -F` ou equivalentes.
- Não alterar regras de firewall do host ou do gateway.
- Não conectar a isca à rede doméstica de produção.
- Não escanear a Internet ou dispositivos reais.
- Não montar `/var/run/docker.sock` no honeypot.
- Não desabilitar o firewall do Windows para "facilitar" o laboratório.
- Não habilitar `enforce` durante a instalação.

## 7. Critérios de verificação

- `uv sync` reproduz o ambiente.
- `uv run pytest` executa o smoke test.
- `uv run ruff check .` e `uv run mypy src` passam.
- `docker info` responde na VM.
- A VM não tem rota não autorizada.
- A autorização do laboratório está registrada.
- Existe snapshot restaurável antes da Fase 5.

## 8. Limitações

- O provisionamento da VM ainda não foi executado nesta fase.
- O Docker Desktop no Windows foi validado apenas como ferramenta de
  desenvolvimento, não como ambiente de segurança.
- A compatibilidade de VirtualBox com WSL2/Hyper-V pode afetar desempenho.
- O caminho do projeto contém acento; montagens compartilhadas devem ser
  testadas antes de serem usadas no runtime.
