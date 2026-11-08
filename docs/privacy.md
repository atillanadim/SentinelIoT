# Privacidade e proteção de dados

**Versão:** 0.1 (Fase 0)

Este documento descreve o tratamento planejado. Não é parecer jurídico e não
afirma conformidade automática com a LGPD.

## 1. Dados coletados

O MVP deve coletar apenas o mínimo necessário:

- endereço IP de origem;
- porta de origem;
- porta de destino;
- serviço-isca;
- tipo de evento;
- severidade;
- decisão;
- timestamp UTC;
- identificadores técnicos (`event_id`, `correlation_id`, `honeypot_id`);
- metadados HTTP mínimos, quando indispensáveis, sem corpo, query string,
  credenciais ou payload.

Não coletar:

- senhas ou tokens;
- conteúdo de formulários;
- corpo de requisições;
- payload completo;
- conteúdo de comunicação;
- dados pessoais desnecessários;
- telemetria para nuvem por padrão.

## 2. Finalidade

- Detectar interações suspeitas com a isca.
- Registrar evidências mínimas para investigação.
- Alertar o administrador.
- Permitir decisão e auditoria de contenção temporária.
- Medir saúde e desempenho do sistema.

A base legal e a finalidade devem ser avaliadas pelo responsável pelo tratamento
antes de uso em produção.

## 3. Retenção e descarte

- Retenção inicial: 90 dias, configurável.
- Prazo sujeito a validação jurídica e operacional.
- Descarte auditado.
- Exportação controlada.
- Backup com proteção adequada.
- Exclusão sob solicitação, quando aplicável, com registro.

## 4. Acesso

- Banco e configuração com permissões restritas ao usuário do agente.
- CLI local, sem exposição à Internet.
- Logs sem segredos.
- Acesso administrativo limitado ao operador autorizado.
- Exportações revisadas antes de compartilhamento.

## 5. Compartilhamento

- Nenhum envio automático para nuvem.
- Canal externo desabilitado por padrão.
- Se um canal externo for habilitado no futuro, documentar finalidade,
  destinatários, base legal e controles.
- Em MSP, definir responsabilidades entre prestador e cliente.

## 6. Segurança dos dados

- Minimização.
- Redaction de campos sensíveis.
- Controle de acesso.
- Retenção limitada.
- Integridade e backup.
- Revisão de dependências e vulnerabilidades.
- Nenhum segredo no Git.

## 7. Direitos e solicitações

O operador deve documentar como atender solicitações de acesso, correção,
exportação e exclusão, quando aplicável. O MVP deve permitir localizar eventos
por IP e período para apoiar esse processo.

## 8. Limitações

- IP e metadados podem ser dados pessoais em determinados contextos.
- A avaliação jurídica é externa ao escopo do MVP.
- A retenção de 90 dias é uma hipótese inicial.
- O produto não garante anonimização.
- O produto não deve ser usado para vigilância não autorizada.
