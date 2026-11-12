# Operação

**Versão:** 0.2 (MVP local)
**Estado:** CLI e runtime local implementados; firewall e container planejados.

## 1. Comandos disponíveis

```text
sentineliot start [--foreground]
sentineliot stop
sentineliot status
sentineliot scan
sentineliot honeypots available
sentineliot honeypots list
sentineliot honeypots add <perfil> [--port N] [--host IP] [--id NOME]
sentineliot honeypots remove <id>
sentineliot events list [--limit N] [--ip IP] [--type TIPO]
sentineliot events show <event_id-ou-prefixo>
sentineliot bans list [--status STATUS]
sentineliot bans show <ip>
sentineliot bans block|allow|ignore|reset <ip> [--note "motivo"]
sentineliot bans export [--format json|csv] [--output ARQUIVO]
sentineliot simulate [--ip IP]
sentineliot diagnostics
sentineliot version
sentineliot shell
```

No Windows com caminho contendo caracteres especiais, use
`.\sentineliot.cmd` no lugar de `sentineliot`. O launcher apenas garante o
`PYTHONPATH` correto para o Python 3.11.

Ainda não implementados: `setup`, `config validate`, `allowlist add/remove`,
`firewall status/dry-run/unblock` e `report export`.

## 1.1. Semântica das decisões

`bans block <ip>` registra a decisão no banco e na auditoria, mas **não altera
firewall**. O mesmo vale para `allow`, `ignore` e `reset`. A aplicação real da
decisão exige um adaptador homologado e o modo `enforce`, previsto para uma fase
posterior. Não trate a lista de ban como bloqueio efetivo de rede.

O comando `scan` lê o spool JSONL das iscas. Ele não faz varredura de portas,
não acessa hosts e não sonda a rede.

## 2. Ciclo operacional planejado

```text
Instalação
  -> validação de ambiente
  -> inicialização do agente
  -> inicialização da isca
  -> coleta de eventos
  -> avaliação da política
  -> registro
  -> notificação
  -> dry-run
  -> homologação do firewall
  -> enforce opcional e confirmado
  -> expiração/remoção da regra
  -> relatório
```

## 3. Inicialização segura

1. Validar configuração.
2. Confirmar que o modo é `observe`.
3. Confirmar que `enforce_enabled` é `false`.
4. Confirmar allowlist e faixas protegidas.
5. Verificar banco, spool e diretórios.
6. Iniciar as iscas em loopback ou rede host-only isolada.
7. Iniciar o agente.
8. Executar health check (`diagnostics`) e um evento de teste controlado.

## 4. Status

A saída de `status` mostra:

- versão do agente e autor;
- arquivo de configuração e modo de resposta;
- adaptador de firewall (sempre com o aviso de que nada é aplicado);
- estado do agente em segundo plano e PID;
- eventos totais e nas últimas 24 horas;
- IPs observados, pendentes e resumo das decisões;
- último evento;
- iscas configuradas e se estão ativas.

## 5. Eventos

`events list` mostra horário, IP de origem, isca, tipo, severidade, método e
caminho. `events show` detalha um evento e aceita prefixo do ID. Nunca são
exibidos segredos, corpo de requisição, query string ou payload. O corpo do
`POST` é drenado e descartado pela isca.

## 5.1. Lista de ban

`bans list` mostra os IPs que interagiram com as iscas, com contagem, severidade
máxima, decisão, primeira/última interação e último caminho. Use
`bans show <ip>` para ver os últimos eventos daquele IP. As decisões são
auditadas na tabela `audit_log`; o efeito de rede continua desabilitado.

## 6. Notificações

- O evento é persistido antes de qualquer envio.
- Falha do canal externo não pode apagar o evento.
- O log local é o canal padrão no MVP.
- O status do notificador deve aparecer em `status` e `diagnostics`.
- Repetição de alertas deve ser limitada para evitar spam.

## 7. Banco e retenção

- Banco SQLite em `data/sentineliot.db`.
- Permissões restritas ao usuário do agente.
- WAL habilitado.
- Retenção inicial de 90 dias.
- Rotina de descarte auditada.
- Backup testado antes de qualquer operação destrutiva.
- Nunca apagar o banco sem confirmação explícita.

## 8. Firewall

- `dry_run` é o padrão.
- `enforce` exige laboratório homologado, snapshot e confirmação.
- O adaptador só altera sua própria tabela/cadeia/conjunto.
- Não executar `nft flush ruleset`, `iptables -F` ou equivalentes.
- Toda regra deve ter ID e etiqueta do SentinelIoT.
- Se a confirmação falhar, registrar `block_failed` e não declarar sucesso.
- Desbloqueio manual deve ser possível pelo ID da regra/evento.
- A expiração deve continuar válida mesmo com reinício do agente.

## 9. Reinício e falha

- Reiniciar o agente não deve perder configuração.
- Bloqueios ativos devem ser reconciliados com o firewall.
- Regras órfãs do próprio SentinelIoT devem ser tratadas de forma auditada.
- Em falha do adaptador, não criar novos bloqueios.
- Em falha do notificador, manter o evento e registrar a falha.
- Em falha do container, registrar health degradado e não inventar eventos.

## 10. Diagnóstico

`diagnostics` deve verificar:

- versão e ambiente;
- configuração e allowlist;
- permissões de arquivos;
- banco e schema;
- estado do container;
- modo e adaptador;
- conectividade interna necessária;
- ausência de segredos em logs;
- espaço em disco e uso de recursos.

## 11. Incidente

1. Preservar eventos, logs e auditoria.
2. Não alterar o firewall sem necessidade e sem autorização.
3. Confirmar se o bloqueio foi realmente aplicado.
4. Registrar horário, ator, ação e resultado.
5. Notificar o responsável.
6. Reverter apenas regras do SentinelIoT.
7. Documentar lições aprendidas.

## 12. Desinstalação

- Remover somente recursos criados pelo SentinelIoT.
- Confirmar antes de apagar dados.
- Não remover regras de terceiros.
- Não apagar volumes ou bancos sem backup.
- Documentar o que foi removido.

## 13. Rollback

- Manter versão anterior disponível.
- Fazer backup do banco e da configuração.
- Restaurar snapshot da VM antes de testes de firewall.
- Validar o estado após o rollback.
- Registrar a causa e o resultado.
