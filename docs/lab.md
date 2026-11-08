# Laboratório isolado

**Versão:** 0.1 (Fase 0)
**Estado:** topologia definida; provisionamento pendente de autorização.

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

- As VMs ainda não foram criadas nesta fase.
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
