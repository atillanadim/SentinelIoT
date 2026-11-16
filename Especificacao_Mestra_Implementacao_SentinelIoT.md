# SENTINELIOT --- ESPECIFICAÇÃO MESTRA DE IMPLEMENTAÇÃO

## Documento de requisitos, arquitetura, plano de execução e instruções para agente de IA

**Versão:** 1.0\
**Tipo:** Especificação técnica para desenvolvimento do MVP\
**Responsável pelo produto:** s0ra\
**Produto:** SentinelIoT --- defesa proativa de redes IoT por Deception
Technology\
**Stack-base:** Python, Docker, SQLite no MVP, integração controlada com
firewall Linux (`nftables`/`iptables`)\
**Público inicial:** laboratório próprio e pilotos autorizados com redes
domésticas/pequenas empresas e MSPs

------------------------------------------------------------------------

# PARTE I --- INSTRUÇÕES AO AGENTE DE IA

## 1. Missão

Você atuará como engenheiro de software sênior, arquiteto de sistemas,
especialista em segurança defensiva, DevSecOps e QA. Sua missão é
projetar, implementar, testar e documentar o **SentinelIoT**,
respeitando esta especificação.

O SentinelIoT é um agente defensivo para redes domésticas e pequenas
empresas. Ele executa um serviço-isca (honeypot) que simula,
inicialmente, uma câmera IP. Quando um host interage com a isca, o
sistema registra o evento, aplica regras de validação, alerta o
administrador e, somente quando habilitado e suportado, solicita um
bloqueio temporário e auditável no firewall do gateway homologado.

O sistema deve ser desenvolvido em etapas pequenas, com testes e
documentação em cada etapa. Não implemente todas as funcionalidades de
uma só vez. Antes de alterar uma arquitetura já aprovada, explique a
necessidade e apresente impacto, risco e alternativa.

## 2. Regras obrigatórias de trabalho

1.  **Não invente resultados.** Nunca declare que um teste passou, que
    um IP foi bloqueado ou que uma integração funciona sem executar a
    verificação correspondente.
2.  **Trabalhe por etapas.** Ao concluir cada fase, apresente arquivos
    criados/alterados, comandos executados, testes, resultados,
    limitações e próxima etapa.
3.  **Não destrua o ambiente do usuário.** Não altere regras gerais do
    firewall, não execute `flush ruleset`, não limpe tabelas existentes
    e não modifique configurações do roteador sem autorização explícita.
4.  **Modo seguro por padrão.** A primeira execução deve operar em
    `observe`/`dry-run`. Bloqueio automático deve vir desabilitado.
5.  **Ambiente autorizado.** Desenvolva e teste somente em laboratório
    próprio ou redes para as quais exista autorização expressa. Não faça
    varredura da Internet, exploração de dispositivos reais, força bruta
    ou tentativa de acesso a câmeras reais.
6.  **Honeypot isolado.** O serviço-isca não deve ter rota de saída para
    a Internet ou para outros dispositivos da rede, salvo necessidade
    estrita, documentada e aprovada. A configuração padrão deve negar
    egress.
7.  **Privilégio mínimo.** O agente principal não deve executar como
    root. Se uma operação privilegiada for necessária, use um componente
    auxiliar restrito, com interface fechada e comandos permitidos
    explicitamente.
8.  **Sem comandos shell inseguros.** Não monte comandos concatenando
    dados de entrada. Prefira bibliotecas, argumentos separados e
    validação estrita de IP, interface e identificadores.
9.  **Proteção contra falso positivo.** Implemente allowlist, TTL de
    bloqueio, limite de bloqueios, auditoria e mecanismo de desbloqueio.
    Nunca bloquear gateway, DNS, DHCP, loopback, endereço do
    administrador ou ativos críticos configurados.
10. **Privacidade.** Colete apenas os dados necessários à segurança. Não
    capture conteúdo de tráfego, senhas reais ou payloads completos.
    Documente retenção e descarte.
11. **Dependências.** Fixe versões, mantenha inventário de dependências
    e verifique vulnerabilidades conhecidas antes de releases.
12. **Segredos.** Não grave tokens, senhas ou chaves no Git, nos logs ou
    em exemplos. Forneça `.env.example` sem credenciais reais.
13. **Compatibilidade.** Não prometa suporte universal a roteadores.
    Implemente primeiro um adaptador Linux homologado e documente
    limitações.
14. **Acessibilidade e simplicidade.** A interface do MVP deve ser
    simples, clara e utilizável por um administrador não especialista.
15. **Revisão humana.** Antes de ativar bloqueio automático em uma rede
    real, exigir configuração explícita e confirmação do administrador.

## 3. Como o agente deve iniciar

Antes de programar: - inspecione o repositório e identifique linguagem,
estrutura, dependências e testes existentes; - não sobrescreva arquivos
sem entender sua função; - apresente um plano de implementação em
fases; - registre dúvidas e premissas; - proponha uma arquitetura mínima
que cumpra os requisitos; - crie ou atualize `README.md`,
`docs/architecture.md`, `docs/threat-model.md` e `docs/decisions/`; -
aguarde aprovação humana antes de operações que alterem firewall, rede,
containers em execução ou dados existentes.

Se não houver repositório, crie a estrutura indicada na Parte III.

------------------------------------------------------------------------

# PARTE II --- VISÃO DO PRODUTO E LIMITES

## 4. Problema que o produto resolve

Redes domésticas e pequenas empresas possuem câmeras IP, lâmpadas
inteligentes, sensores, fechaduras e outros dispositivos IoT com
configurações heterogêneas. O administrador pode não perceber tentativas
de sondagem ou movimentação lateral dentro da rede. Scanners de
vulnerabilidade são úteis, mas normalmente representam uma avaliação
pontual e não substituem a observação contínua de interações suspeitas
com um ativo-isca.

O SentinelIoT pretende reduzir o tempo entre uma interação suspeita e a
resposta do administrador, oferecendo detecção local, registro, alerta e
contenção temporária quando tecnicamente possível.

**Limite da promessa:** um honeypot só detecta interações que chegam ao
serviço-isca. A ausência de alertas não prova que a rede está livre de
comprometimento. O produto é uma camada complementar, não substitui
firewall, atualização, antivírus/EDR, segmentação ou monitoramento
profissional.

## 5. Proposta de valor

-   Detectar interações suspeitas por meio de um serviço-isca local.
-   Registrar evidências mínimas e úteis para investigação.
-   Alertar o responsável de forma simples.
-   Permitir bloqueio temporário e reversível em gateway homologado.
-   Operar com baixo consumo e instalação simplificada.
-   Oferecer camada gratuita e plano Pro futuro.

## 6. Usuários e perfis

### 6.1 Administrador doméstico

-   Instala o agente em equipamento Linux compatível.
-   Visualiza estado do serviço, eventos e alertas.
-   Gerencia allowlist e política de resposta.
-   Não precisa conhecer detalhes internos de Docker ou firewall para
    tarefas comuns.

### 6.2 MSP / técnico de TI

-   Administra instalações autorizadas de clientes.
-   Precisa identificar qual rede gerou o evento.
-   Precisa de histórico, exportação e documentação de resposta.
-   No MVP, a gestão multi-tenant completa não será implementada.

### 6.3 Desenvolvedor / operador

-   Instala, configura, atualiza e diagnostica o agente.
-   Acessa logs técnicos.
-   Executa testes e restaura o ambiente.

## 7. Escopo do MVP

### 7.1 Obrigatório no MVP

1.  Agente local em Python.
2.  Um honeypot simulando um serviço de câmera IP, sem imitar marca real
    nem coletar credenciais verdadeiras.
3.  Execução isolada em Docker.
4.  Detecção de conexão e de tentativas de interação definidas para o
    serviço simulado.
5.  Registro de evento estruturado.
6.  Interface local mínima ou CLI para estado, eventos e configuração.
7.  Notificação local ou por canal simples configurável.
8.  Modo `observe` e `dry-run`.
9.  Adaptador de firewall Linux para ambiente de laboratório,
    inicialmente sem ativação automática.
10. Allowlist, TTL, limite de bloqueios e desbloqueio.
11. Testes automatizados e documentação de instalação.
12. Métricas de CPU, memória e latência.

### 7.2 Fora do MVP

-   Simulação de dez ou mais tipos de dispositivos.
-   Dashboard web sofisticado.
-   Aplicativo Android/iOS.
-   Gestão multi-tenant comercial completa.
-   Integração universal com roteadores.
-   IA/ML para classificar ataques.
-   Resposta automática sem política configurada.
-   Inspeção profunda de pacotes ou captura de payloads.
-   Serviço SOC 24x7.
-   Promessa de prevenção de todos os ataques IoT.

### 7.3 Evolução posterior

-   Segundo e terceiro perfis de honeypot.
-   Portal web seguro.
-   Gestão MSP com separação rigorosa por cliente.
-   Relatórios Pro.
-   Integrações adicionais com gateways homologados.
-   Assinatura, cobrança e gestão de licenças.
-   Alertas externos com controle de privacidade.

------------------------------------------------------------------------

# PARTE III --- ARQUITETURA E ESTRUTURA DO REPOSITÓRIO

## 8. Arquitetura lógica

O sistema deve conter os seguintes componentes:

1.  **Administrador:** configura o produto e consulta alertas.
2.  **Interface local:** CLI e, se viável, página local simples. Não
    deve ficar exposta à Internet.
3.  **Agente SentinelIoT:** coordena configuração, monitoramento,
    validação, armazenamento e alertas.
4.  **Honeypot Docker:** serviço simulado de câmera IP, isolado e com
    recursos limitados.
5.  **Event Collector:** recebe eventos do honeypot por canal interno
    controlado.
6.  **Policy Engine:** aplica allowlist, limiares, modo de operação e
    regras de decisão.
7.  **Firewall Adapter:** componente restrito que solicita
    inclusão/expiração de regra temporária no firewall homologado.
8.  **Storage:** SQLite local no MVP.
9.  **Notifier:** gera alerta local e, opcionalmente, envia notificação
    externa configurada.
10. **Health Monitor:** verifica disponibilidade, versão, uso de
    recursos e falhas.

### 8.1 Diagrama para Draw.io

Desenhe os blocos e setas abaixo:

`Administrador → CLI/Interface Local → Agente SentinelIoT`

A partir do agente, desenhe: - `Agente → Policy Engine` -
`Agente → Event Collector` - `Agente → SQLite` -
`Agente → Notifier → Administrador` -
`Agente → Firewall Adapter → Firewall do Gateway` -
`Agente → Docker Engine → Container Honeypot` -
`Container Honeypot → Event Collector`

Use setas diferentes para: - fluxo de configuração; - fluxo de
eventos; - fluxo de comando de bloqueio; - fluxo de notificação.

Acrescente uma borda de confiança ao redor do container e destaque que o
container não possui acesso irrestrito à rede nem à Internet.

## 9. Estrutura sugerida do repositório

``` text
sentineliot/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.lock
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile.agent
├── Dockerfile.honeypot
├── config/
│   ├── config.example.yaml
│   └── allowlist.example.yaml
├── src/
│   └── sentineliot/
│       ├── __init__.py
│       ├── main.py
│       ├── cli/
│       │   ├── commands.py
│       │   └── output.py
│       ├── core/
│       │   ├── agent.py
│       │   ├── config.py
│       │   ├── policy.py
│       │   └── lifecycle.py
│       ├── honeypot/
│       │   ├── manager.py
│       │   └── profiles/
│       │       └── camera_simulator.py
│       ├── events/
│       │   ├── models.py
│       │   ├── collector.py
│       │   └── normalizer.py
│       ├── firewall/
│       │   ├── base.py
│       │   ├── linux_nftables.py
│       │   ├── dry_run.py
│       │   └── privileged_helper.py
│       ├── notifications/
│       │   ├── base.py
│       │   └── local.py
│       ├── storage/
│       │   ├── database.py
│       │   └── repositories.py
│       ├── monitoring/
│       │   ├── health.py
│       │   └── metrics.py
│       └── security/
│           ├── validation.py
│           ├── secrets.py
│           └── audit.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   ├── performance/
│   └── fixtures/
├── scripts/
│   ├── setup_lab.sh
│   ├── run_tests.sh
│   └── cleanup_lab.sh
└── docs/
    ├── architecture.md
    ├── threat-model.md
    ├── installation.md
    ├── configuration.md
    ├── operations.md
    ├── privacy.md
    ├── test-plan.md
    └── decisions/
```

O agente pode ajustar nomes e subdivisões se houver justificativa, mas
deve preservar a separação entre lógica de negócio, coleta de eventos,
firewall, armazenamento e interface.

## 10. Tecnologias e justificativas

  -----------------------------------------------------------------------
  Camada                  Tecnologia inicial      Justificativa
  ----------------------- ----------------------- -----------------------
  Linguagem               Python 3.11 ou versão   Rapidez de
                          estável compatível      desenvolvimento e
                                                  bibliotecas maduras

  Container               Docker Engine / Compose Isolamento e
                                                  reprodutibilidade

  Banco local             SQLite                  Simplicidade para
                                                  instalação individual

  Firewall                nftables                Controle de regras
                          preferencialmente;      temporárias no Linux
                          adaptador separado      

  Configuração            YAML validado por       Configuração legível e
                          schema                  verificável

  Logs                    logging estruturado     Auditoria e diagnóstico
                          JSON                    

  Testes                  pytest                  Testes unitários e
                                                  integração

  Qualidade               Ruff, mypy ou           Padronização e análise
                          equivalente             estática

  CI                      GitHub Actions ou       Testes em cada
                          equivalente             alteração

  Documentação            Markdown                Fácil manutenção
  -----------------------------------------------------------------------

Não introduzir Redis, Kubernetes, Kafka ou banco distribuído no MVP sem
necessidade medida.

------------------------------------------------------------------------

# PARTE IV --- REQUISITOS FUNCIONAIS E NÃO FUNCIONAIS

## 11. Requisitos funcionais

  -----------------------------------------------------------------------
  ID                      Requisito               Critério de aceite
  ----------------------- ----------------------- -----------------------
  RF01                    Instalar e iniciar o    Comando documentado
                          agente                  inicia o agente sem
                                                  erro em ambiente
                                                  homologado

  RF02                    Carregar configuração   Configuração inválida é
                                                  rejeitada com mensagem
                                                  clara

  RF03                    Iniciar honeypot de     Container inicia e
                          câmera simulada         expõe apenas as portas
                                                  definidas

  RF04                    Detectar conexão à isca Conexão de teste gera
                                                  evento com data/hora e
                                                  origem

  RF05                    Normalizar evento       Evento contém ID,
                                                  timestamp, IP, serviço,
                                                  tipo e severidade

  RF06                    Aplicar allowlist       Origem autorizada não
                                                  gera bloqueio

  RF07                    Operar em modo observe  Evento é registrado,
                                                  sem tentativa de
                                                  bloqueio

  RF08                    Operar em modo dry-run  Decisão de bloqueio é
                                                  simulada e registrada

  RF09                    Solicitar bloqueio      Em ambiente homologado
                          temporário              e após habilitação,
                                                  regra é aplicada com
                                                  TTL

  RF10                    Expirar bloqueio        Regra é removida ao
                                                  final do TTL

  RF11                    Desbloquear manualmente Administrador consegue
                                                  remover bloqueio pelo
                                                  identificador do
                                                  evento/regra

  RF12                    Notificar administrador Evento crítico gera
                                                  notificação configurada

  RF13                    Consultar histórico     CLI lista eventos com
                                                  paginação e filtros
                                                  básicos

  RF14                    Exportar eventos        Exportação JSON ou CSV
                                                  sem segredos

  RF15                    Verificar saúde         Comando mostra agente,
                                                  honeypot, banco e
                                                  adaptador de firewall
  -----------------------------------------------------------------------

## 12. Requisitos não funcionais

  -----------------------------------------------------------------------
  ID                      Requisito               Meta inicial /
                                                  verificação
  ----------------------- ----------------------- -----------------------
  RNF01                   Baixo consumo           CPU média em repouso
                                                  até 3% no equipamento
                                                  de referência

  RNF02                   Memória controlada      Agente + honeypot até
                                                  300 MB no cenário de
                                                  referência

  RNF03                   Resposta rápida         P95 até 2 segundos
                                                  entre evento local
                                                  recebido e decisão do
                                                  agente, em laboratório

  RNF04                   Segurança por padrão    Firewall em `observe`
                                                  ou `dry-run` após
                                                  instalação

  RNF05                   Isolamento              Container sem root,
                                                  capabilities mínimas,
                                                  filesystem read-only
                                                  quando possível e
                                                  egress negado

  RNF06                   Disponibilidade         Reinício do agente não
                                                  deve perder
                                                  configuração nem criar
                                                  regras órfãs

  RNF07                   Auditabilidade          Toda decisão e
                                                  alteração de firewall
                                                  deve ter registro

  RNF08                   Privacidade             Não armazenar senha,
                                                  payload completo ou
                                                  conteúdo de comunicação

  RNF09                   Manutenibilidade        Módulos independentes e
                                                  testes automatizados

  RNF10                   Portabilidade           Compatibilidade
                          controlada              declarada apenas para
                                                  sistemas e gateways
                                                  testados

  RNF11                   Recuperação             Falha do agente não
                                                  deve interromper
                                                  tráfego legítimo nem
                                                  declarar bloqueio não
                                                  confirmado

  RNF12                   Integridade             Configuração e
                                                  atualizações devem ser
                                                  verificáveis e
                                                  versionadas
  -----------------------------------------------------------------------

As metas são hipóteses de engenharia. O agente deve medir e documentar
os resultados, não afirmar conformidade sem evidência.

------------------------------------------------------------------------

# PARTE V --- MODELO DE DADOS E CONTRATOS

## 13. Modelo de evento

Todo evento deve possuir, no mínimo:

``` json
{
  "event_id": "UUID",
  "timestamp_utc": "ISO-8601",
  "source_ip": "IP_VALIDADO",
  "source_port": 0,
  "destination_service": "camera_simulator",
  "event_type": "connection_attempt",
  "severity": "low|medium|high",
  "decision": "observe|allowlisted|dry_run_block|block_requested|block_confirmed|block_failed",
  "honeypot_id": "camera-01",
  "rule_id": null,
  "correlation_id": "UUID"
}
```

Não inclua senha recebida, token, conteúdo de formulário, payload
integral ou dados pessoais desnecessários. Se for necessário registrar
uma tentativa de autenticação, armazene apenas o tipo de evento e
metadados mínimos; nunca persista o segredo digitado.

## 14. Entidades do banco

### `events`

-   `id` (UUID ou inteiro)
-   `timestamp_utc`
-   `source_ip`
-   `source_port`
-   `service`
-   `event_type`
-   `severity`
-   `decision`
-   `honeypot_id`
-   `correlation_id`

### `firewall_actions`

-   `id`
-   `event_id`
-   `source_ip`
-   `action`
-   `status`
-   `created_at`
-   `expires_at`
-   `gateway_adapter`
-   `error_code` (sem segredo ou comando sensível)

### `allowlist`

-   `id`
-   `value` (IP/CIDR)
-   `reason`
-   `created_at`
-   `created_by`

### `settings`

-   `key`
-   `value`
-   `updated_at`

### `audit_log`

-   `id`
-   `timestamp_utc`
-   `actor`
-   `action`
-   `target`
-   `result`

Criar índices por timestamp, IP e tipo de evento. Definir política de
retenção configurável; o valor inicial sugerido é 90 dias, sujeito à
validação jurídica e operacional.

## 15. Contratos internos

Defina interfaces abstratas para evitar dependência direta de
implementação:

-   `HoneypotManager.start()`, `stop()`, `status()`
-   `EventCollector.receive_event()`
-   `PolicyEngine.evaluate(event, config)`
-   `FirewallAdapter.block_ip(ip, ttl, reason)`, `unblock(rule_id)`,
    `list_managed_rules()`
-   `Notifier.send(notification)`
-   `EventRepository.save(event)`, `list(filters)`

O `FirewallAdapter` deve ter implementações `DryRunFirewallAdapter` e
`NftablesFirewallAdapter`. O padrão deve ser o adaptador dry-run.

------------------------------------------------------------------------

# PARTE VI --- POLÍTICA DE DETECÇÃO E RESPOSTA

## 16. Princípio de detecção

O MVP não deve tentar descobrir ou invadir dispositivos reais. O
honeypot é um serviço simulado e controlado, criado para receber
conexões de teste e interações suspeitas.

Tipos iniciais de evento: - conexão TCP ao serviço-isca; - requisição
HTTP ao endpoint simulado; - tentativa de autenticação simulada, sem
persistir credenciais; - sequência repetitiva de conexões em janela
curta; - comportamento incompatível com a política definida.

A classificação deve ser explicável. Não usar IA/ML no MVP. Cada regra
precisa ter nome, motivo e teste.

## 17. Política de resposta

Fluxo obrigatório:

1.  Receber evento.
2.  Validar formato e origem.
3.  Verificar se a origem está na allowlist.
4.  Verificar se o IP é endereço válido e não reservado para
    infraestrutura crítica.
5.  Verificar se o modo é `observe`, `dry-run` ou `enforce`.
6.  Aplicar limites de frequência e quantidade de bloqueios.
7.  Gerar decisão explicável.
8.  Se `observe`, apenas registrar.
9.  Se `dry-run`, registrar a ação simulada.
10. Se `enforce`, solicitar ao adaptador homologado um bloqueio
    temporário.
11. Confirmar a regra no firewall antes de registrar `block_confirmed`.
12. Agendar expiração e permitir remoção antecipada.
13. Notificar o administrador.

### 17.1 Modos

-   `observe`: coleta e registra; não sugere nem executa alteração.
-   `dry_run`: calcula a decisão e registra o que faria; não altera
    firewall.
-   `enforce`: executa bloqueio temporário somente após configuração
    explícita, gateway homologado e pré-checagens aprovadas.

### 17.2 Proteções obrigatórias

-   Allowlist para gateway, DNS, DHCP, VPN, administrador e ativos
    críticos.
-   Bloqueio com TTL curto e configurável.
-   Limite máximo de regras simultâneas.
-   Limite de bloqueios por janela de tempo.
-   Verificação de IP/CIDR e rejeição de entrada malformada.
-   Nunca bloquear o IP do próprio agente, gateway ou interface de
    gerenciamento.
-   Não aceitar IP de origem fornecido pelo usuário como se fosse evento
    verificado.
-   Toda regra criada deve ter identificador e etiqueta exclusiva do
    SentinelIoT.
-   O adaptador só pode alterar regras de sua própria cadeia/conjunto.
-   Nunca limpar regras de terceiros.
-   Em falha, não adicionar bloqueios novos.
-   Se não for possível confirmar a regra, registrar `block_failed`,
    alertar e não declarar sucesso.

## 18. Integração privilegiada com firewall

O agente principal deve rodar sem privilégios administrativos. Se o
firewall exigir privilégios, criar um helper mínimo separado.

O helper: - aceita somente operações predefinidas; - valida IP, TTL e
identificador; - não recebe comandos shell arbitrários; - não aceita
nomes de tabela/cadeia livres; - opera somente em cadeia/conjunto
próprio; - registra auditoria; - rejeita operações fora da allowlist de
comandos; - não expõe socket administrativo à rede; - usa socket Unix
local com permissões restritas ou mecanismo equivalente.

Começar com `DryRunFirewallAdapter`. O adaptador real deve ser
desenvolvido e testado apenas em máquina/roteador de laboratório, com
snapshot ou plano de restauração documentado.

**Não usar `iptables -F`, `nft flush ruleset` ou qualquer comando que
apague regras preexistentes.**

------------------------------------------------------------------------

# PARTE VII --- DOCKER E ISOLAMENTO

## 19. Requisitos do container honeypot

O container deve: - executar como usuário não-root; - usar imagem mínima
e dependências fixadas; - ter filesystem somente leitura quando
viável; - descartar capabilities não necessárias; - ativar
`no-new-privileges`; - possuir limites de CPU, memória e processos; -
não montar `/var/run/docker.sock`; - não montar diretórios sensíveis do
host; - não ter acesso a dispositivos do host; - não ter egress para a
Internet por padrão; - comunicar-se com o agente por canal interno
restrito; - não encaminhar tráfego para terceiros; - não funcionar como
proxy, túnel ou roteador.

O agente deve documentar as limitações de isolamento do Docker e não
tratar container como fronteira de segurança absoluta.

## 20. Rede de laboratório

Criar uma rede de laboratório separada da rede doméstica de produção.
Usar VMs ou equipamentos de teste. A demonstração deve ocorrer em
segmento controlado, com IPs de teste.

O honeypot precisa ser alcançável pelo segmento autorizado que se deseja
observar, mas isso não significa que seja invisível. Descreva-o como
**discreto e não anunciado**, com acesso controlado.

------------------------------------------------------------------------

# PARTE VIII --- INTERFACE E EXPERIÊNCIA DO USUÁRIO

## 21. Interface mínima do MVP

Priorizar CLI clara. Comandos propostos:

``` text
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

Os comandos que alteram configuração devem solicitar confirmação quando
necessário. `firewall enforce` não deve ser ativado por um comando
genérico sem checagens e confirmação explícita.

### 21.1 Tela/saída de status

Exibir: - versão do agente; - estado do agente; - estado do container; -
modo de resposta atual; - adaptador de firewall; - último evento; -
quantidade de eventos nas últimas 24 horas; - bloqueios ativos e seus
horários de expiração; - saúde do banco e do serviço de notificação.

### 21.2 Tela/saída de eventos

Exibir: - horário; - IP de origem; - serviço-isca; - tipo de evento; -
severidade; - decisão; - status do bloqueio, se houver.

Não exibir segredos ou conteúdo sensível.

------------------------------------------------------------------------

# PARTE IX --- INSTALAÇÃO, CONFIGURAÇÃO E OPERAÇÃO

## 22. Configuração de exemplo

Criar `config.example.yaml` com valores não sensíveis:

``` yaml
app:
  name: sentineliot
  environment: lab
  log_level: INFO

agent:
  mode: observe
  poll_interval_seconds: 2

honeypot:
  enabled: true
  profile: camera_simulator
  container_name: sentineliot-camera-01
  cpu_limit: "0.25"
  memory_limit: "128m"

detection:
  event_retention_days: 90
  rate_window_seconds: 60
  max_events_per_source: 20

firewall:
  adapter: dry_run
  enforce_enabled: false
  default_ttl_seconds: 900
  max_active_blocks: 20
  max_new_blocks_per_hour: 10

allowlist:
  - "127.0.0.1/32"
  # Adicionar gateway, DNS, DHCP, VPN e IP administrativo no ambiente de teste.

notifications:
  local_enabled: true
  external_enabled: false
```

O agente deve validar o schema, tipos, intervalos e endereços IP ao
iniciar. Valores inválidos devem impedir o modo enforce.

## 23. Processo de instalação

1.  Verificar sistema operacional e versão.
2.  Verificar disponibilidade de Docker.
3.  Verificar permissões necessárias.
4.  Criar diretórios com permissões restritas.
5.  Gerar configuração inicial.
6.  Validar configuração e allowlist.
7.  Baixar/construir imagens com versões fixadas.
8.  Iniciar honeypot em modo de laboratório.
9.  Iniciar agente em `observe`.
10. Executar teste de saúde.
11. Exibir limitações e instruções para avançar ao `dry_run`.

Não habilitar bloqueio automático durante a instalação inicial.

## 24. Processo operacional

`Instalação → Validação de ambiente → Inicialização do agente → Inicialização da isca → Coleta de eventos → Avaliação da política → Registro → Notificação → Dry-run → Homologação do firewall → Enforce opcional → Expiração/remoção da regra → Relatório`

O sistema deve manter logs claros em cada transição. O relatório deve
diferenciar: - evento detectado; - decisão sugerida; - bloqueio
solicitado; - bloqueio confirmado; - bloqueio expirado; - bloqueio
removido manualmente; - falha na operação.

------------------------------------------------------------------------

# PARTE X --- SEGURANÇA, PRIVACIDADE E CONTINUIDADE

## 25. Modelo de ameaças inicial

  ------------------------------------------------------------------------
  Ameaça                  Impacto                 Mitigação
  ----------------------- ----------------------- ------------------------
  Container comprometido  Uso do honeypot para    Não-root, capabilities
                          atingir outros ativos   mínimas, egress
                                                  deny-by-default, limites
                                                  e imagem mínima

  Falso positivo          Bloqueio de usuário ou  Allowlist, modo observe,
                          serviço legítimo        dry-run, TTL, limites e
                                                  desbloqueio

  Roubo de credencial     Alteração indevida de   Privilégio mínimo, MFA
  administrativa          firewall                em eventual gestão
                                                  remota, rotação e
                                                  armazenamento seguro

  Exposição de logs       Vazamento de metadados  Minimização,
                                                  criptografia, controle
                                                  de acesso e retenção
                                                  limitada

  Falha do agente         Perda de alerta ou      Health check, watchdog,
                          estado inconsistente    backup e recuperação
                                                  segura

  API de roteador         Controle indevido do    Adaptadores homologados,
  vulnerável              gateway                 credenciais restritas e
                                                  nenhuma API exposta à
                                                  Internet

  Atualização maliciosa   Comprometimento do      Dependências fixadas,
                          agente                  origem verificada,
                                                  assinatura/integridade e
                                                  rollback

  Abuso por usuário       Bloqueio malicioso      Auditoria, limites,
  interno                                         confirmação e permissões
                                                  por função
  ------------------------------------------------------------------------

## 26. Privacidade e LGPD

O produto pode processar endereço IP e metadados de conexão, que podem
ser dados pessoais quando relacionados a pessoa identificada ou
identificável. O agente deve: - documentar finalidade e base legal a
serem avaliadas pelo responsável pelo tratamento; - coletar apenas o
mínimo necessário; - definir prazo de retenção e descarte; - proteger
dados em trânsito e repouso; - restringir acesso a logs; - documentar
exportação e exclusão; - esclarecer responsabilidades entre MSP e
cliente; - não enviar telemetria à nuvem por padrão sem
consentimento/configuração clara.

Não afirmar conformidade legal automática. Antes de operação comercial,
solicitar revisão jurídica adequada.

## 27. Continuidade e recuperação

-   Reinício automático controlado do agente.
-   Health check do container e banco.
-   Backup criptografado da configuração e dos eventos necessários.
-   Teste periódico de restauração.
-   Atualização com versão anterior disponível para rollback.
-   Em falha do agente, não aplicar novos bloqueios.
-   Expiração de regras deve continuar funcionando de forma segura,
    mesmo se o processo principal reiniciar.
-   Ao desinstalar, remover somente recursos criados pelo SentinelIoT e
    confirmar antes de apagar dados.

------------------------------------------------------------------------

# PARTE XI --- TESTES E CRITÉRIOS DE ACEITE

## 28. Plano de testes

### 28.1 Testes unitários

-   validação de configuração;
-   validação de IP/CIDR;
-   allowlist;
-   classificação de eventos;
-   cálculo de TTL;
-   limites de bloqueio;
-   serialização de logs;
-   expiração e reversão;
-   tratamento de exceções.

### 28.2 Testes de integração

-   agente inicia e encerra;
-   container inicia e encerra;
-   evento chega ao collector;
-   evento é persistido no SQLite;
-   notificação é gerada;
-   dry-run produz decisão sem alterar firewall;
-   helper rejeita parâmetros inválidos;
-   adaptador de laboratório cria e remove somente regras gerenciadas
    pelo SentinelIoT.

### 28.3 Testes de segurança

-   container não executa como root;
-   container não acessa Docker socket;
-   container não alcança destinos externos não autorizados;
-   entrada malformada não causa comando arbitrário;
-   IP da allowlist nunca é bloqueado;
-   IP do gateway nunca é bloqueado;
-   limite de bloqueios é respeitado;
-   segredo não aparece nos logs;
-   falha do firewall não é registrada como sucesso.

### 28.4 Testes de desempenho

-   medir CPU em repouso;
-   medir memória total do agente e honeypot;
-   medir latência de recepção e decisão;
-   medir comportamento com rajadas controladas de eventos;
-   verificar crescimento do banco e limpeza por retenção.

## 29. Metas de aceitação do protótipo

  -----------------------------------------------------------------------
  Teste                   Procedimento            Critério proposto
  ----------------------- ----------------------- -----------------------
  Detecção                Gerar 100 interações    Detectar pelo menos 95
                          controladas com a isca  eventos previstos

  Falso positivo          Gerar 100 interações    Nenhum bloqueio
                          benignas definidas      indevido

  Decisão                 Medir recepção até      P95 até 2 segundos no
                          decisão local           laboratório

  Isolamento              Testar rotas de saída   Nenhuma saída não
                          não permitidas          autorizada

  Recursos                Medir em equipamento de CPU média em repouso
                          referência              até 3%; memória até 300
                                                  MB

  Recuperação             Reiniciar agente e      Estado consistente;
                          simular falha de        nenhuma falsa
                          notificação             confirmação de bloqueio

  Expiração               Criar bloqueio          Regra removida ao fim
                          temporário em           do TTL
                          laboratório             

  Auditoria               Consultar histórico de  Toda ação possui
                          ações                   evento, horário,
                                                  resultado e
                                                  identificador
  -----------------------------------------------------------------------

Essas metas precisam ser ajustadas ao equipamento de referência e ao
ambiente. Se não forem atingidas, registrar resultado real, causa
provável e plano de correção.

------------------------------------------------------------------------

# PARTE XII --- PLANO DE IMPLEMENTAÇÃO POR FASES

## 30. Fase 0 --- Preparação e análise

**Objetivo:** preparar ambiente e reduzir incertezas.

Tarefas: 1. Inspecionar computador e sistema operacional de
desenvolvimento. 2. Definir ambiente de laboratório isolado. 3. Instalar
Python, Docker e Git. 4. Criar repositório. 5. Criar ambiente virtual e
fixar dependências. 6. Criar documentação inicial. 7. Elaborar diagrama
de arquitetura e modelo de ameaças.

Entregáveis: - repositório criado; - README; - arquitetura; - threat
model; - plano de testes; - lista de pré-requisitos.

Critério de saída: ambiente reproduzível e arquitetura revisada.

## 31. Fase 1 --- Honeypot isolado

**Objetivo:** executar uma única isca simulada.

Tarefas: 1. Criar serviço HTTP/RTSP simulado, escolhendo primeiro HTTP
se simplificar o MVP. 2. Criar imagem Docker mínima. 3. Configurar
usuário não-root. 4. Limitar CPU, memória e processos. 5. Negar egress
por padrão. 6. Expor apenas a porta de laboratório necessária. 7. Gerar
eventos simulados sem armazenar credenciais.

Entregáveis: - Dockerfile; - Compose; - perfil `camera_simulator`; -
documentação de portas e rede; - teste de isolamento.

Critério de saída: isca inicia, recebe conexão de laboratório e não
alcança destinos externos não autorizados.

## 32. Fase 2 --- Agente Python e coleta de eventos

**Objetivo:** receber e registrar eventos.

Tarefas: 1. Criar entrypoint do agente. 2. Criar configuração YAML
validada. 3. Criar modelo de evento. 4. Implementar collector. 5.
Implementar normalizador. 6. Persistir no SQLite. 7. Criar comandos
`status` e `events list`. 8. Implementar logging estruturado.

Entregáveis: - agente funcional; - banco inicializado; - eventos
consultáveis; - testes unitários e de integração.

Critério de saída: conexão de teste gera evento persistido e
consultável.

## 33. Fase 3 --- Motor de políticas

**Objetivo:** decidir se o evento exige alerta ou contenção.

Tarefas: 1. Implementar allowlist. 2. Implementar classificação
explicável. 3. Implementar janela de frequência. 4. Implementar limites
de eventos. 5. Implementar `observe`. 6. Implementar `dry_run`. 7. Criar
testes de IP inválido, IP permitido e evento repetitivo.

Entregáveis: - Policy Engine; - regras documentadas; - testes de
decisão; - trilha de auditoria.

Critério de saída: decisões corretas em cenários de teste e nenhum
bloqueio real.

## 34. Fase 4 --- Notificações e consulta

**Objetivo:** informar o administrador.

Tarefas: 1. Criar interface de notificação. 2. Implementar notificação
local. 3. Criar template de alerta com horário, origem, serviço e
decisão. 4. Implementar consulta de eventos. 5. Implementar exportação
JSON/CSV. 6. Tratar indisponibilidade de notificador.

Entregáveis: - alerta funcional; - histórico; - exportação; - testes de
falha.

Critério de saída: evento crítico gera alerta e fica consultável mesmo
se o canal externo falhar.

## 35. Fase 5 --- Firewall em laboratório

**Objetivo:** integrar bloqueio temporário com segurança.

Tarefas: 1. Criar interface abstrata do adaptador. 2. Implementar
`DryRunFirewallAdapter`. 3. Definir cadeia/conjunto exclusivo do
produto. 4. Implementar helper privilegiado restrito. 5. Implementar
validação de IP e TTL. 6. Implementar criação, consulta, expiração e
remoção de regra. 7. Implementar allowlist e limite de bloqueios. 8.
Testar em VM ou gateway de laboratório. 9. Documentar rollback e
recuperação.

Entregáveis: - adaptador dry-run; - adaptador real de laboratório; -
helper; - testes; - procedimento de restauração.

Critério de saída: bloquear e desbloquear apenas IP de teste, sem
modificar regras preexistentes e com auditoria completa.

## 36. Fase 6 --- Interface e experiência mínima

**Objetivo:** facilitar a operação.

Tarefas: 1. Melhorar CLI. 2. Criar saída de status. 3. Criar consulta
filtrada de eventos. 4. Criar gestão de allowlist. 5. Criar diagnóstico.
6. Exibir modo de operação e avisos de risco. 7. Não expor interface de
administração à Internet.

Entregáveis: - CLI documentada; - exemplos de uso; - mensagens de erro
compreensíveis.

Critério de saída: usuário consegue iniciar, verificar, consultar e
diagnosticar sem editar código.

## 37. Fase 7 --- Endurecimento e validação do MVP

**Objetivo:** comprovar os requisitos.

Tarefas: 1. Executar toda a suíte de testes. 2. Executar testes de
isolamento. 3. Medir CPU, RAM e latência. 4. Simular reinício e falha.
5. Verificar retenção e descarte. 6. Revisar logs e segredos. 7.
Corrigir vulnerabilidades encontradas. 8. Produzir relatório de
resultados.

Entregáveis: - relatório de testes; - matriz de requisitos atendidos; -
limitações conhecidas; - versão candidata do MVP.

Critério de saída: requisitos críticos testados, falhas conhecidas
documentadas e nenhuma ativação de bloqueio em ambiente real sem
autorização.

## 38. Fase 8 --- Piloto autorizado

**Objetivo:** validar utilidade e operação com poucos usuários.

Pré-condições: - MVP estável; - autorização formal do responsável pela
rede; - gateway homologado; - modo observe/dry-run testado; - política
de privacidade e retenção definida; - procedimento de reversão
disponível.

Escopo inicial recomendado: - 3 a 5 redes autorizadas; - uma isca por
rede; - suporte em horário útil; - acompanhamento manual; - bloqueio
automático desabilitado no início do piloto.

Métricas: - eventos por rede; - eventos relevantes; - falsos
positivos; - tempo de detecção; - tempo de decisão; - quantidade de
alertas úteis; - chamados de suporte; - consumo de recursos; - intenção
de continuar usando; - disposição de pagamento.

Critério de saída: relatório de piloto e decisão documentada de
corrigir, manter ou ampliar.

## 39. Fase 9 --- Preparação comercial (fora do MVP acadêmico)

Somente depois do piloto: - avaliar portal web; - avaliar gestão MSP
multi-tenant; - implementar autenticação forte e controle por função; -
implementar cobrança; - criar plano Free e Pro; - implementar
relatórios; - estabelecer suporte, SLA e processo de atualização; -
revisar LGPD, contratos e responsabilidades; - recalcular custos e ponto
de equilíbrio com dados reais.

Preço de referência do plano de negócio: Freemium e Pro a R\$ 29,90 por
rede/mês. Esse preço é hipótese comercial a validar, não requisito
técnico obrigatório do MVP.

------------------------------------------------------------------------

# PARTE XIII --- PLANO DE TRABALHO INDIVIDUAL

## 40. Organização do trabalho

Como o projeto será desenvolvido por uma única pessoa, o planejamento
deve evitar paralelismo excessivo e limitar o escopo.

  -----------------------------------------------------------------------
  Etapa                   Atividade principal     Entregável
  ----------------------- ----------------------- -----------------------
  Semana 1                Preparação, requisitos  Repositório,
                          e arquitetura           arquitetura e threat
                                                  model

  Semana 2                Honeypot Docker isolado Isca simulada funcional

  Semana 3                Agente e armazenamento  Eventos persistidos

  Semana 4                Policy Engine e         Decisões em
                          allowlist               observe/dry-run

  Semana 5                Alertas e CLI           Operação básica
                                                  utilizável

  Semana 6                Adaptador de firewall   Bloqueio temporário
                          em laboratório          testado

  Semana 7                Segurança, desempenho e Relatório de testes
                          recuperação             

  Semana 8                Documentação e          MVP documentado e
                          demonstração            demonstrável
  -----------------------------------------------------------------------

O prazo é uma estimativa para planejamento acadêmico. Se houver
dificuldade na integração com gateway, priorizar a demonstração completa
em `dry-run` e documentar o bloqueio real como extensão técnica, sem
simular sucesso.

## 41. Controle de progresso

Manter um arquivo `docs/progress.md` com: - fase atual; - tarefas
concluídas; - tarefas pendentes; - decisões tomadas; - bugs
conhecidos; - testes executados; - evidências; - riscos em aberto; -
próximo passo.

Não marcar tarefa como concluída sem evidência reproduzível.

------------------------------------------------------------------------

# PARTE XIV --- DOCUMENTAÇÃO E ENTREGA ACADÊMICA

## 42. Documentos obrigatórios do repositório

1.  `README.md`: objetivo, requisitos, instalação e execução.
2.  `docs/architecture.md`: arquitetura e fluxos.
3.  `docs/threat-model.md`: ameaças e mitigação.
4.  `docs/installation.md`: instalação do laboratório.
5.  `docs/configuration.md`: parâmetros e exemplos.
6.  `docs/operations.md`: iniciar, parar, consultar e recuperar.
7.  `docs/privacy.md`: dados coletados, retenção e descarte.
8.  `docs/test-plan.md`: testes, resultados e limitações.
9.  `docs/progress.md`: andamento individual.
10. `docs/decisions/`: decisões técnicas relevantes.

## 43. Evidências para apresentação

Preparar: - diagrama de arquitetura; - print ou gravação do status do
agente; - demonstração de inicialização do container; - evento de
conexão de teste; - evento registrado no SQLite; - alerta gerado; -
demonstração de `dry-run`; - bloqueio e expiração apenas se testados em
laboratório; - medição de CPU e memória; - resultado da suíte de
testes; - limitações e próximos passos.

A demonstração deve usar máquinas e IPs de laboratório, sem expor redes
de terceiros.

------------------------------------------------------------------------

# PARTE XV --- DEFINIÇÃO DE PRONTO

## 44. Definition of Done do MVP

O MVP só será considerado concluído quando:

-   [ ] O agente Python inicia e encerra corretamente.
-   [ ] A configuração é validada.
-   [ ] O honeypot de câmera simulada executa em Docker.
-   [ ] O container tem privilégios mínimos e egress restrito.
-   [ ] Uma interação de teste gera evento estruturado.
-   [ ] O evento é salvo no SQLite.
-   [ ] O administrador consegue consultar eventos.
-   [ ] O sistema opera em `observe` e `dry_run`.
-   [ ] Allowlist é aplicada antes de qualquer decisão de bloqueio.
-   [ ] O adaptador de firewall não altera regras de terceiros.
-   [ ] TTL, expiração e desbloqueio são testados em laboratório.
-   [ ] Falhas não são reportadas como sucesso.
-   [ ] Logs não contêm segredos.
-   [ ] CPU, RAM e latência foram medidos.
-   [ ] Testes unitários, integração e segurança foram executados.
-   [ ] README e documentação de instalação estão completos.
-   [ ] Limitações e riscos remanescentes estão documentados.

------------------------------------------------------------------------

# PARTE XVI --- PROMPT DE EXECUÇÃO PARA O AGENTE

Copie o texto abaixo e forneça ao agente de IA junto com este documento:

> Você é o engenheiro responsável pela implementação do SentinelIoT.
> Leia integralmente a especificação antes de editar ou criar arquivos.
>
> Seu objetivo é construir o MVP em fases, sem pular etapas. Comece
> inspecionando o ambiente e o repositório. Se não existir projeto, crie
> a estrutura indicada. Em seguida, apresente um plano curto com a ordem
> dos arquivos e funcionalidades que serão implementados.
>
> Implemente primeiro o honeypot simulado e isolado em Docker; depois o
> agente Python e o armazenamento; em seguida o motor de políticas,
> allowlist, modos observe/dry-run, notificações e CLI. Somente depois
> de testes e aprovação humana implemente o adaptador de firewall de
> laboratório.
>
> O padrão de segurança é não executar bloqueios reais. Não altere
> firewall do host ou roteador sem autorização explícita. Nunca limpe
> regras existentes. Não execute varreduras na Internet nem tente
> acessar dispositivos reais. Use apenas laboratório autorizado.
>
> O agente principal deve operar sem root. Operações privilegiadas devem
> ser isoladas em helper restrito, com validação rigorosa e comandos
> predefinidos. O honeypot deve ser não-root, sem Docker socket, com
> capabilities mínimas, limites de recursos e egress negado por padrão.
>
> Para cada fase, entregue: (1) resumo do que foi feito; (2) arquivos
> criados/alterados; (3) comandos para executar; (4) testes executados e
> resultados reais; (5) riscos ou limitações; (6) critério de aceite;
> (7) próxima fase sugerida. Não avance para uma fase que dependa de
> teste ou aprovação ainda pendente.
>
> Não invente métricas, compatibilidade, resultados de testes ou
> segurança. Quando algo não puder ser comprovado no ambiente atual,
> marque como pendente e explique como validar.
>
> Comece pela Fase 0 --- Preparação e análise. Não implemente
> funcionalidades fora do MVP sem solicitar aprovação.

------------------------------------------------------------------------

# ANEXO A --- DECISÕES TÉCNICAS QUE DEVEM SER REGISTRADAS

O agente deve criar um registro de decisão (ADR) para cada escolha
relevante:

-   Sistema operacional e versão suportada.
-   Protocolo e portas do honeypot inicial.
-   Modelo de comunicação entre honeypot e agente.
-   Estratégia de isolamento e egress.
-   Banco local e política de retenção.
-   Adaptador de firewall inicial.
-   Mecanismo de helper privilegiado.
-   Canal de notificação.
-   Política de atualização e rollback.
-   Critérios de ativação do modo enforce.

Cada ADR deve conter: contexto, alternativas, decisão, justificativa,
consequências, riscos e data.

# ANEXO B --- LIMITAÇÕES CONHECIDAS A DOCUMENTAR

1.  A isca só observa tráfego que alcança o serviço-isca.
2.  A instalação em um host comum não garante visibilidade de toda a
    rede.
3.  O bloqueio em toda a rede depende de integração efetiva com o
    gateway pelo qual o tráfego passa.
4.  Roteadores domésticos podem não oferecer API adequada.
5.  O container reduz a superfície de risco, mas não elimina todos os
    riscos de escape ou configuração incorreta.
6.  O produto não substitui firewall, segmentação, atualização de
    firmware ou monitoramento profissional.
7.  A versão MVP não oferece SLA 24x7 nem gestão comercial multi-tenant.
8.  O preço e a demanda devem ser validados com usuários reais.

# ANEXO C --- RESULTADO ESPERADO

Ao final do projeto, deve existir um protótipo demonstrável em
laboratório que: 1. execute uma câmera IP simulada em container isolado;
2. receba uma conexão controlada; 3. gere e armazene evento estruturado;
4. classifique o evento com regras transparentes; 5. mostre alerta ao
administrador; 6. simule a decisão de bloqueio em `dry-run`; 7. permita
testar bloqueio temporário e reversão em gateway de laboratório
homologado, caso a integração seja concluída; 8. apresente medições,
testes, documentação e limitações.

**Prioridade final:** entregar um MVP pequeno, seguro, reproduzível e
comprovável é mais importante do que entregar muitas funcionalidades
incompletas.
