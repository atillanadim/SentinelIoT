# Plano de testes

**Versão:** 0.1 (Fase 0)

## 1. Objetivo

Comprovar, com evidências reproduzíveis, que o MVP atende aos requisitos
críticos sem declarar sucesso sem teste. O plano será atualizado a cada fase.

## 2. Ambientes

| Ambiente | Uso | Observação |
|---|---|---|
| Windows 11 + venv 3.11 | Lint, mypy, testes unitários rápidos | Não é o runtime oficial. |
| VM Linux dedicada 1 | Agente, Docker, SQLite, integração | Rede host-only. |
| VM Linux gateway | nftables + helper restrito | Fase 5; snapshot obrigatório. |
| VM de teste/atacante | Gerar interações controladas | Somente laboratório autorizado. |

## 3. Camadas de teste

### 3.1 Unitários

- validação de configuração;
- validação de IP/CIDR;
- allowlist e faixas protegidas;
- classificação de eventos;
- cálculo de TTL;
- limites de bloqueio;
- serialização de logs JSON;
- expiração e reversão;
- tratamento de exceções;
- redaction de segredos.

### 3.2 Integração

- agente inicia e encerra;
- container inicia e encerra;
- evento chega ao collector;
- evento é persistido no SQLite;
- notificação é gerada;
- dry-run produz decisão sem alterar firewall;
- helper rejeita parâmetros inválidos;
- adaptador cria e remove somente regras gerenciadas pelo SentinelIoT.

### 3.3 Segurança

- container não executa como root;
- container não acessa o docker.sock;
- container não alcança destinos externos não autorizados;
- entrada malformada não causa comando arbitrário;
- IP da allowlist nunca é bloqueado;
- IP do gateway nunca é bloqueado;
- limite de bloqueios é respeitado;
- segredo não aparece nos logs;
- falha do firewall não é registrada como sucesso;
- path traversal e injeção no honeypot não executam comandos.

### 3.4 Desempenho

- CPU em repouso;
- memória total do agente e do honeypot;
- latência de recepção e decisão;
- comportamento com rajadas controladas;
- crescimento do banco e limpeza por retenção.

## 4. Casos iniciais

| ID | Caso | Pré-condição | Resultado esperado | Fase |
|---|---|---|---|---|
| UT-001 | Importar pacote | venv | Versão 0.1.0 | 0 |
| UT-002 | Configuração inválida | schema implementado | Rejeição clara | 2 |
| UT-003 | IP inválido | validação implementada | Rejeição sem comando | 3 |
| UT-004 | IP na allowlist | política implementada | Decisão `allowlisted` | 3 |
| UT-005 | TTL acima do teto | política implementada | Rejeição ou clamp documentado | 3 |
| IT-001 | Container inicia | Docker na VM | Container saudável | 1 |
| IT-002 | Conexão de teste | isca ativa | Evento normalizado | 2 |
| IT-003 | Persistência | banco inicializado | Evento consultável | 2 |
| IT-004 | Dry-run | modo dry_run | Nenhuma regra real | 3/5 |
| ST-001 | Container non-root | Docker | UID não zero | 1 |
| ST-002 | Sem docker.sock | Docker | Socket ausente | 1 |
| ST-003 | Sem egress | Docker | Destino externo inalcançável | 1 |
| ST-004 | Allowlist nunca bloqueada | política | Nenhum bloqueio | 3 |
| ST-005 | Falha do firewall | adaptador simulado | `block_failed`, sem sucesso | 5 |
| PT-001 | CPU em repouso | laboratório | Medir e registrar | 7 |
| PT-002 | P95 de decisão | laboratório | Medir e registrar | 7 |

## 5. Metas de aceitação

- Detecção: pelo menos 95 de 100 interações controladas previstas.
- Falso positivo: nenhum bloqueio indevido em 100 interações benignas.
- Decisão: P95 de até 2 segundos entre recepção e decisão local.
- Isolamento: nenhuma saída não autorizada.
- Recursos: CPU média em repouso até 3%; memória total até 300 MB.
- Recuperação: estado consistente após reinício; nenhuma falsa confirmação.
- Expiração: regra removida ao fim do TTL.
- Auditoria: toda ação com evento, horário, resultado e identificador.

As metas são hipóteses. Se não forem atingidas, registrar resultado real, causa
provável e plano de correção.

## 6. Evidências

- Saída dos comandos de teste.
- Versões de Python, Docker, sistema e dependências.
- Logs estruturados sem segredos.
- Consultas ao SQLite.
- Captura de status e diagnóstico.
- Medições de CPU, RAM e latência.
- Snapshot e rollback da VM.
- Relatório de falhas conhecidas.

## 7. Execução na Fase 0

Comandos executados e resultados reais serão registrados em
`docs/progress.md`. A Fase 0 cobre apenas o smoke test e as ferramentas de
qualidade. Testes de Docker, integração e firewall ficam pendentes.

## 8. Limitações

- Testes de firewall não podem ser executados no Windows.
- Testes de isolamento no Docker Desktop não substituem a VM Linux.
- Métricas de desempenho só valem para o equipamento de referência.
- Nenhum teste deve usar rede de terceiros ou dispositivo real.
