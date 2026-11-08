# SentinelIoT

Agente defensivo local para redes domésticas e pequenas empresas. O produto
executa um serviço-isca (honeypot) que simula uma câmera IP genérica, registra
interações suspeitas, aplica políticas explicáveis e, somente quando habilitado
e homologado, solicita bloqueio temporário e reversível no firewall de um
gateway Linux de laboratório.

**Status atual: Fase 0 concluída no host de desenvolvimento.**
O runtime oficial será provisionado em uma VM Linux dedicada antes da Fase 1.

Não há honeypot, agente funcional, banco de eventos ou adaptador de firewall
implementados ainda. O repositório contém apenas a estrutura, a documentação,
a configuração de exemplo e a base de desenvolvimento.

## Aviso de segurança

- Use somente em laboratório próprio ou rede com autorização expressa.
- Não execute varreduras na Internet, não acesse câmeras reais e não teste em
  redes de terceiros.
- O modo padrão é `observe`. O bloqueio automático é desabilitado.
- Nunca limpe regras de firewall existentes.
- A isca só detecta o tráfego que chega até ela. Ausência de alertas não prova
  que a rede está livre de comprometimento.
- O container reduz a superfície de risco, mas não é uma fronteira de segurança
  absoluta.

## O que o projeto é

- Uma camada complementar de detecção por deception.
- Um agente local em Python com CLI em texto simples.
- Um honeypot de câmera IP simulada em container isolado.
- Um registro mínimo de eventos em SQLite.
- Um motor de políticas com allowlist, TTL e limites.
- Um adaptador de firewall inicialmente em `dry_run`.

## O que o projeto não é

- Um substituto de firewall, EDR, segmentação, atualização de firmware ou SOC.
- Um scanner de vulnerabilidades ou uma ferramenta de intrusão.
- Um produto com suporte universal a roteadores.
- Uma solução com IA/ML no MVP.
- Uma promessa de prevenção de todos os ataques IoT.

## Arquitetura resumida

O runtime oficial do MVP roda em uma VM Linux dedicada, com rede host-only
isolada. O Windows é usado apenas para edição e verificações rápidas.

```text
Administrador -> CLI local -> Agente SentinelIoT (non-root)
                                  |-> Policy Engine
                                  |-> SQLite
                                  |-> Notifier local
                                  |-> Health/Metrics
                                  |-> FirewallAdapter (DryRun por padrão)
                                  |     Fase 5: helper restrito -> nftables
                                  |-> Docker Engine -> Honeypot (não-root,
                                        read-only, sem egress, sem docker.sock)
                                        -> spool JSONL -> Event Collector
VM de teste (host-only) --TCP--> porta publicada do honeypot
```

Consulte [docs/architecture.md](docs/architecture.md) para os fluxos completos,
bordas de confiança e decisões.

## Estrutura do repositório

```text
config/            configuração de exemplo, sem segredos
docs/              arquitetura, ameaças, instalação, operação, privacidade e ADRs
scripts/           verificações e utilitários de laboratório
src/sentineliot/   pacote Python (esqueleto na Fase 0)
tests/             testes unitários, integração, segurança e desempenho
```

## Pré-requisitos

Desenvolvimento no Windows:

- Windows 11 x86_64.
- Python 3.11.16 (o repositório fixa 3.11).
- uv.
- Git.
- Docker Desktop apenas para verificação opcional; o laboratório oficial é a VM.

Runtime e laboratório:

- VM Linux dedicada (Ubuntu 22.04/24.04 ou Debian 12), x86_64.
- Docker Engine e Docker Compose na VM.
- Rede host-only isolada, por exemplo 192.168.57.0/24.
- Snapshot da VM antes de qualquer teste de firewall.
- Autorização de laboratório registrada em `docs/lab-authorization.md`.

## Desenvolvimento (Windows)

```powershell
uv venv --python 3.11
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
```

O venv do Windows serve para edição e testes rápidos. O venv de runtime será
criado dentro da VM Linux. O arquivo `.venv/` não é versionado.

## Laboratório (VM Linux)

O provisionamento da VM e da rede host-only é uma etapa separada da Fase 0 e
deve ser executado com autorização. O roteiro está em
[docs/installation.md](docs/installation.md) e [docs/lab.md](docs/lab.md).

## Documentação

- [Arquitetura](docs/architecture.md)
- [Modelo de ameaças](docs/threat-model.md)
- [Instalação](docs/installation.md)
- [Configuração](docs/configuration.md)
- [Operação](docs/operations.md)
- [Privacidade](docs/privacy.md)
- [Plano de testes](docs/test-plan.md)
- [Progresso](docs/progress.md)
- [Relatório da Fase 0](docs/phase-0-report.md)
- [Laboratório](docs/lab.md)
- [Decisões arquiteturais](docs/decisions/)

## Licença

A licença ainda não foi definida. O arquivo `LICENSE` será adicionado quando a
decisão for tomada. Até lá, não presuma permissão de uso, cópia ou distribuição.
