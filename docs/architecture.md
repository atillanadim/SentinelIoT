# Arquitetura do SentinelIoT

**Versão:** 0.3 (runtimes local e em container)
**Escopo:** arquitetura-alvo em container; o runtime local em Python e o runtime
em container compartilham o mesmo contrato de eventos, spool e banco.

> O runtime local descrito em [ADR-0014](decisions/ADR-0014.md) executa iscas
> HTTP, SSH e Telnet diretamente no host, em loopback, sem Docker e sem firewall.
> O runtime em container ([ADR-0015](decisions/ADR-0015.md)) executa as mesmas
> iscas isoladas, com o mesmo spool JSONL e a mesma lista de ban. Os dois são
> selecionados por `honeypot.runtime` (`local` ou `docker`).

## 1. Contexto e limites

O SentinelIoT é uma camada complementar de detecção por deception. Ele executa
uma isca que simula uma câmera IP genérica, registra interações mínimas e aplica
uma política explicável. O bloqueio temporário é opcional, desabilitado por
padrão e só pode ser habilitado em laboratório homologado.

Limites da promessa:

- A isca só observa o tráfego que chega até ela.
- A ausência de eventos não prova ausência de comprometimento.
- O container reduz a superfície de risco, mas não é uma fronteira absoluta.
- O produto não substitui firewall, segmentação, atualização de firmware,
  EDR ou monitoramento profissional.
- O MVP não oferece gestão multi-tenant, SLA 24x7 nem suporte universal a
  roteadores.

## 2. Decisões estruturantes

1. O runtime oficial roda em uma **VM Linux dedicada**, com rede host-only
   isolada. O Windows é usado para edição e verificações rápidas.
2. O agente roda sem privilégios administrativos.
3. O honeypot roda em Docker, sem root, sem docker.sock, com capabilities
   mínimas, filesystem somente leitura quando possível e egress negado.
4. O canal de eventos inicial é um **spool JSONL em volume**, sem expor um
   listener de rede adicional.
5. O armazenamento é SQLite em modo WAL, com retenção inicial de 90 dias.
6. O adaptador padrão é `DryRunFirewallAdapter`. O adaptador nftables só será
   implementado e testado na Fase 5, em laboratório.
7. A CLI usa `argparse` e saída em texto simples. Rich/ANSI não são
   dependências do MVP.

As decisões estão registradas em `docs/decisions/`.

## 3. Componentes

| Componente | Módulos propostos | Responsabilidade |
|---|---|---|
| CLI | `cli/commands.py`, `cli/output.py` | Comandos locais, texto simples, confirmação e diagnóstico. |
| Core | `core/agent.py`, `core/config.py`, `core/policy.py`, `core/lifecycle.py` | Orquestração, configuração validada, política e ciclo de vida. |
| Honeypot | `honeypot/manager.py`, `honeypot/docker_manager.py`, `honeypot/container.py`, `honeypot/profiles/catalog.py` | Lifecycle local ou em container e perfil HTTP da câmera. |
| Events | `events/models.py`, `events/collector.py`, `events/normalizer.py` | Modelo, leitura do spool, validação e normalização. |
| Firewall | `firewall/base.py`, `firewall/dry_run.py`, `firewall/linux_nftables.py`, `firewall/privileged_helper.py` | Interface, simulação, adaptador real e helper restrito. |
| Notifications | `notifications/base.py`, `notifications/local.py` | Interface e notificação local. |
| Storage | `storage/database.py`, `storage/repositories.py` | SQLite, schema, consultas, retenção e auditoria. |
| Monitoring | `monitoring/health.py`, `monitoring/metrics.py` | Saúde, CPU, memória e latência. |
| Security | `security/validation.py`, `security/secrets.py`, `security/audit.py` | IP/CIDR, redaction e auditoria. |
| Web | `web/server.py`, `web/snapshot.py`, `web/demo.py`, `web/assets.py` | Dashboard local somente leitura, payloads JSON e cenário de demonstração. |

## 4. Topologia de execução

O diagrama abaixo representa o laboratório oficial. O host Windows não faz
parte do caminho de runtime.

```text
+---------------------------- VM Linux dedicada (host-only) ----------------------------+
|                                                                                        |
|  Administrador                                                                         |
|      | CLI local (sem listener de rede)                                                |
|      v                                                                                 |
|  +------------------------------ Agente SentinelIoT (non-root) ----------------------+ |
|  | lifecycle | config | policy | collector | storage | notifier | health | audit     | |
|  +-----+----------+---------+----------+---------+---------+----------+-------------+ |
|        |          |         |          |         |         |          |               |
|        |          |         |          v         v         v          |               |
|        |          |         |       SQLite    local log   metrics      |               |
|        |          |         |                                          |               |
|        |          +---------+--> FirewallAdapter (DryRun padrão)       |               |
|        |                           |  Fase 5: Unix socket              |               |
|        |                           v                                   |               |
|        |                    Helper restrito (root) -> nftables          |               |
|        |                    tabela/cadeia própria, sem flush            |               |
|        |                                                               |               |
|        +--> Docker Engine (comandos permitidos) -> Honeypot container  |               |
|                                                   non-root             |               |
|                                                   cap_drop ALL         |               |
|                                                   read-only + tmpfs    |               |
|                                                   limites CPU/RAM/PIDs |               |
|                                                   rede interna         |               |
|                                                   sem egress           |               |
|                                                   sem docker.sock      |               |
|                                                   | JSONL spool         |               |
|                                                   v                     |               |
|                                              Event Collector          |               |
+----------------------------------------------------------------------------------------+
          ^
          | TCP para a porta publicada (IP host-only da VM)
          |
   VM de teste/atacante (host-only, laboratório autorizado)
```

Borda de confiança: o container é tratado como não confiável. Ele não recebe
credenciais, não monta diretórios sensíveis, não acessa o docker.sock e não
possui rota de saída. O agente e o banco ficam fora do container.

## 5. Fluxo de evento

1. Uma origem de laboratório conecta à porta publicada.
2. O honeypot extrai apenas metadados: IP e porta de origem, porta de destino,
   serviço, tipo de evento, severidade, timestamp, `honeypot_id` e
   `correlation_id`.
3. O honeypot grava uma linha JSON no spool. Senhas, corpos, query strings e
   payloads nunca são persistidos.
4. O collector lê o spool, valida o JSON, deduplica por `event_id` e normaliza.
5. O Policy Engine valida o IP de origem, consulta a allowlist e as faixas
   protegidas, verifica o modo, a janela de frequência e os limites.
6. A decisão explicável é persistida com trilha de auditoria.
7. O notificador local gera o alerta.
8. Em `observe`, apenas registra. Em `dry_run`, registra a ação simulada. Em
   `enforce`, solicita bloqueio ao adaptador.
9. O adaptador confirma a regra antes de registrar `block_confirmed`; se não
   confirmar, registra `block_failed` e alerta.
10. O TTL agenda a expiração; o desbloqueio manual é permitido; a expiração
    continua válida mesmo se o agente reiniciar.
11. Saúde e métricas registram estado, CPU, memória, latência e falhas.

## 6. Modelo de dados

Tabelas iniciais:

- `events`: `id`, `timestamp_utc`, `source_ip`, `source_port`, `service`,
  `event_type`, `severity`, `decision`, `honeypot_id`, `correlation_id`,
  `rule_id` opcional.
- `firewall_actions`: `id`, `event_id`, `source_ip`, `action`, `status`,
  `created_at`, `expires_at`, `gateway_adapter`, `error_code`.
- `allowlist`: `id`, `value` (IP/CIDR), `reason`, `created_at`, `created_by`.
- `settings`: `key`, `value`, `updated_at`.
- `audit_log`: `id`, `timestamp_utc`, `actor`, `action`, `target`, `result`,
  detalhes redigidos.

Índices por timestamp, IP de origem e tipo de evento. SQLite em WAL,
`foreign_keys=ON`, `busy_timeout` e versão de schema via `PRAGMA user_version`.
Retenção inicial de 90 dias, configurável e auditada.

## 7. Contratos internos

```text
HoneypotManager.start() / stop() / status()
EventCollector.receive_event(event)
PolicyEngine.evaluate(event, config) -> Decision
FirewallAdapter.block_ip(ip, ttl, reason) -> ActionResult
FirewallAdapter.unblock(rule_id) -> ActionResult
FirewallAdapter.list_managed_rules() -> list[ManagedRule]
Notifier.send(notification) -> NotificationResult
EventRepository.save(event) / list(filters)
```

As interfaces serão abstratas para permitir `DryRunFirewallAdapter` e
`NftablesFirewallAdapter` sem acoplar o núcleo à implementação.

## 8. Modos de operação

- `observe`: coleta e registra; não sugere nem executa alteração.
- `dry_run`: calcula a decisão e registra o que faria; não altera firewall.
- `enforce`: executa bloqueio temporário somente após configuração explícita,
  gateway homologado, allowlist válida e pré-checagens aprovadas.

O modo inicial é `observe`. `enforce_enabled` é `false`. A ativação exige
confirmação explícita do administrador e evidências de laboratório.

## 9. Proteções obrigatórias

- Allowlist para gateway, DNS, DHCP, VPN, administrador e ativos críticos.
- Faixas protegidas: loopback, link-local, multicast, broadcast e indefinidos.
- TTL curto e configurável; limite de regras ativas e de novos bloqueios por
  janela.
- Validação estrita de IP/CIDR; rejeição de entrada malformada.
- Nunca bloquear o próprio agente, o gateway ou a interface de gerenciamento.
- Toda regra tem identificador e etiqueta exclusiva do SentinelIoT.
- O adaptador só altera sua própria tabela/cadeia/conjunto.
- Nunca limpar regras de terceiros.
- Em falha, não criar novos bloqueios.
- Sem confirmação da regra, registrar `block_failed`, nunca sucesso.
- Auditoria de toda decisão, alteração, expiração e desbloqueio.

## 10. Perfis de execução

| Perfil | Ambiente | Uso |
|---|---|---|
| Desenvolvimento | Windows 11 + venv 3.11 | Edição, lint, testes unitários rápidos. |
| Laboratório | VM Linux dedicada + host-only | Runtime oficial, Docker, integração, nftables e testes de segurança. |
| Produção futura | Host Linux homologado + systemd | Instalação real, com helper restrito e política revisada. |

## 11. Falhas e recuperação

- Reinício do agente não perde configuração nem cria regras órfãs.
- O agente reconcilia bloqueios ativos no banco com o firewall ao iniciar.
- Se o firewall falhar, o agente não adiciona novos bloqueios.
- A expiração de regras deve continuar válida mesmo com o processo principal
  parado, usando timeout no próprio nftables e reconciliação posterior.
- Backup e restauração serão documentados e testados na Fase 7.

## 12. Decisões e documentos relacionados

- `docs/threat-model.md`
- `docs/test-plan.md`
- `docs/lab.md`
- `docs/decisions/ADR-0001.md` a `ADR-0012.md`
- `docs/progress.md`
