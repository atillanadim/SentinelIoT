# Modelo de ameaças inicial

**Versão:** 0.1 (Fase 0)
**Escopo:** MVP em laboratório, com runtime em VM Linux dedicada.

Este documento é uma hipótese de engenharia. Ele deve ser revisado a cada fase
e antes de qualquer piloto autorizado.

## 1. Ativos

- Disponibilidade e integridade da rede monitorada.
- Credenciais administrativas do agente e do gateway.
- Banco SQLite com eventos e auditoria.
- Configuração, allowlist e política de resposta.
- Regras de firewall do laboratório.
- Integridade das imagens Docker e das dependências.
- Privacidade dos metadados de conexão.
- Confiança do administrador nos alertas.

## 2. Atores

- Administrador doméstico ou técnico de laboratório.
- Operador que instala e diagnostica o agente.
- Atacante interno ou dispositivo comprometido na rede monitorada.
- Processo ou container comprometido dentro do honeypot.
- Fornecedor de dependências ou imagem.
- Usuário interno com acesso indevido ao host.

## 3. Bordas de confiança

1. VM de teste/atacante -> porta publicada do honeypot.
2. Container do honeypot -> spool JSONL -> agente.
3. Agente -> Docker Engine.
4. Agente -> helper privilegiado -> nftables.
5. CLI -> banco e configuração.
6. Dependências e imagens externas -> build/execução.
7. Logs/banco -> administrador e eventuais exportações.

O container não é uma fronteira absoluta. Docker compartilha kernel e depende
de configuração correta do host.

## 4. Ameaças e mitigações

| ID | Ameaça | Impacto | Mitigação | Fase |
|---|---|---|---|---|
| T01 | Container comprometido usado para atacar outros ativos | Movimento lateral | Non-root, cap_drop ALL, no-new-privileges, read-only, limites, rede interna, egress negado, sem docker.sock | 1 |
| T02 | Falso positivo bloqueia usuário ou serviço legítimo | Indisponibilidade | Allowlist, observe/dry-run, TTL, limites, desbloqueio, confirmação | 3–5 |
| T03 | Roubo de credencial administrativa | Alteração indevida de firewall | Privilégio mínimo, segredo fora do Git/logs, confirmação, auditoria, MFA futura | 5–7 |
| T04 | Exposição de logs ou banco | Vazamento de metadados | Minimização, permissões restritas, retenção, redaction, exportação controlada | 2–4 |
| T05 | Falha do agente | Perda de alerta ou estado inconsistente | Health check, reconciliação, não criar bloqueios em falha, TTL no firewall | 2–7 |
| T06 | API de roteador vulnerável | Controle indevido do gateway | Apenas adaptadores homologados, sem API exposta à Internet, credenciais restritas | 5 |
| T07 | Atualização ou dependência maliciosa | Comprometimento do agente | Versões fixadas, lockfile, origem verificada, revisão, pip-audit, rollback | 0–7 |
| T08 | Abuso por usuário interno | Bloqueio malicioso | Auditoria, limites, confirmação, permissões por função no futuro | 3–7 |
| T09 | Evento forjado ou replay | Decisão incorreta | IP de origem vem do socket, validação de schema, deduplicação por event_id, autoria auditada | 2–3 |
| T10 | Rajada de eventos | Consumo de recursos ou bloqueio em massa | Janela de frequência, limite por origem, limite de bloqueios, fila limitada | 2–5 |
| T11 | Path traversal ou injeção no honeypot | Execução indevida no container | Não executar arquivos do usuário, sem shell, validação, resposta genérica, superfície mínima | 1 |
| T12 | Captura de credenciais reais | Violação de privacidade | Nunca persistir senha, corpo, query ou payload; registrar apenas tipo de evento | 1–2 |
| T13 | Escape do container | Comprometimento da VM | Imagem mínima, non-root, capabilities mínimas, sem dispositivos, sem montagens sensíveis, host atualizado | 1 |
| T14 | Regra de firewall órfã | Bloqueio persistente | IDs, etiqueta própria, TTL no nftables, reconciliação e desbloqueio | 5 |
| T15 | Deleção ou alteração de regras de terceiros | Interrupção de rede | Somente tabela/cadeia própria; proibição de flush; validação de escopo | 5 |
| T16 | Exportação com segredo | Vazamento | Exportação only de campos permitidos; revisão e redaction | 4–7 |
| T17 | Interface administrativa exposta | Acesso não autorizado | CLI local, sem listener de rede; nenhuma exposição à Internet | 2–6 |
| T18 | Falha de notificação silenciosa | Alerta perdido | Evento persistido antes do envio; status do notificador; retry limitado; log local | 4 |

## 5. Riscos residuais

- Docker compartilha o kernel; uma vulnerabilidade de kernel ou configuração
  incorreta pode reduzir o isolamento.
- A VM Linux e o VirtualBox dependem da segurança do Windows host.
- Um atacante com acesso root à VM pode alterar o agente, o banco ou o helper.
- A isca não vê tráfego que não chega até ela.
- O bloqueio em toda a rede depende de o tráfego passar pelo gateway integrado.
- O MVP não tem MFA, multi-tenant, SLA ou resposta 24x7.
- A qualidade dos alertas depende da calibração da política e do ambiente.

## 6. Segurança do laboratório

- Usar somente VM e rede host-only dedicadas.
- Não usar a rede doméstica 192.0.2.0/24 para testes (faixa de exemplo, RFC 5737).
- Não acessar câmeras ou dispositivos IoT reais.
- Criar snapshot antes de qualquer teste de firewall.
- Registrar autorização em `docs/lab-authorization.md`.
- Não executar `nft flush ruleset`, `iptables -F` ou comandos equivalentes.
- Não montar `/var/run/docker.sock` no honeypot.
- Não montar diretórios sensíveis do host.
- Não permitir egress por padrão.
- Revisar logs antes de compartilhar evidências.

## 7. Privacidade

IPs e metadados de conexão podem ser dados pessoais quando relacionados a pessoa
identificável. O agente deve coletar o mínimo, documentar a finalidade, limitar
a retenção, restringir o acesso e permitir exportação/exclusão controladas.
Não há telemetria para nuvem por padrão. A avaliação jurídica é
responsabilidade do operador antes de uso comercial.

## 8. Revisão

Revisar este modelo:

- ao final de cada fase;
- antes de habilitar `dry_run` em ambiente novo;
- antes de qualquer teste de nftables;
- antes de um piloto autorizado;
- após incidente ou mudança relevante de arquitetura.
