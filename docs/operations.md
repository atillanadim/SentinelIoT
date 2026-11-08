# Operação

**Versão:** 0.1 (Fase 0)
**Estado:** procedimentos planejados; a CLI funcional será implementada nas
Fases 2 a 6.

## 1. Comandos previstos

```text
sentineliot setup
sentineliot start
sentineliot stop
sentineliot status
sentineliot events list
sentineliot events show <event_id>
sentineliot config validate
sentineliot allowlist list
sentineliot allowlist add <IP-ou-CIDR> --reason "<motivo>"
sentineliot allowlist remove <id>
sentineliot firewall status
sentineliot firewall dry-run
sentineliot firewall unblock <rule_id>
sentineliot report export --format json
sentineliot diagnostics
```

Nenhum desses comandos está implementado na Fase 0.

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
5. Verificar Docker, banco e diretórios.
6. Iniciar o honeypot em rede isolada.
7. Iniciar o agente.
8. Executar health check e um evento de teste controlado.

## 4. Status

A saída planejada de `status` deve mostrar:

- versão do agente;
- estado do agente;
- estado do container;
- modo de resposta atual;
- adaptador de firewall;
- último evento;
- eventos nas últimas 24 horas;
- bloqueios ativos e expiração;
- saúde do banco e do notificador.

## 5. Eventos

A saída planejada de `events list` deve mostrar horário, IP de origem, serviço,
tipo, severidade, decisão e status do bloqueio. Nunca exibir segredos, corpo de
requisição, query string ou payload.

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
