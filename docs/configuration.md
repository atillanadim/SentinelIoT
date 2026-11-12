# Configuração

**Versão:** 0.2 (MVP local)
**Estado:** carregamento e validação implementados; schema evolui com o runtime.

## 1. Princípios

- Configuração legível em YAML.
- Validação estrita de tipos, intervalos e endereços IP/CIDR.
- Configuração inválida deve impedir a inicialização e, principalmente, o modo
  `enforce`.
- Nenhum segredo no repositório, nos exemplos ou nos logs.
- O modo inicial é `observe`.
- O bloqueio automático vem desabilitado.

## 2. Arquivos

- `config/config.example.yaml`: exemplo seguro, sem credenciais.
- `config/allowlist.example.yaml`: exemplo de allowlist estática.
- `config/config.yaml`: configuração local, ignorada pelo Git.
- `.env.example`: variáveis de ambiente de exemplo, sem segredos.

## 3. Estrutura proposta

### app

| Campo | Tipo | Padrão | Regra |
|---|---|---|---|
| `name` | string | `sentineliot` | Identificador fixo. |
| `environment` | string | `lab` | `lab` ou `production`; não altera a segurança por si só. |
| `log_level` | string | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

### agent

| Campo | Tipo | Padrão | Regra |
|---|---|---|---|
| `mode` | string | `observe` | `observe`, `dry_run` ou `enforce`. |
| `poll_interval_seconds` | int | `2` | Entre 1 e 60. |
| `data_dir` | path | `./data` | Diretório local com permissões restritas. |

### honeypot

| Campo | Tipo | Padrão | Regra |
|---|---|---|---|
| `enabled` | bool | `true` | Se falso, nenhuma isca é criada por padrão. |
| `profile` | string | `camera-http` | `camera-http`, `router-admin`, `ssh-banner` ou `telnet-iot`. |
| `container_name` | string | `sentineliot-camera-01` | Reservado ao runtime em container. |
| `image` | string | `sentineliot-honeypot:0.1.0` | Reservado ao runtime em container. |
| `listen_port` | int | `8080` | Porta de laboratório; validar disponibilidade. |
| `publish_host` | IP | `127.0.0.1` | No laboratório, usar o IP host-only da VM. |
| `cpu_limit` | string | `0.25` | Reservado ao runtime em container. |
| `memory_limit` | string | `128m` | Reservado ao runtime em container. |
| `pids_limit` | int | `64` | Reservado ao runtime em container. |
| `read_only` | bool | `true` | Reservado ao runtime em container. |

O MVP local usa apenas `enabled`, `profile`, `listen_port` e `publish_host`.
Aliases legados de `profile` (`camera_simulator`, `camera`, `router`, `ssh`,
`telnet`) são convertidos para o identificador novo ao carregar o estado das
iscas.

### detection

| Campo | Tipo | Padrão | Regra |
|---|---|---|---|
| `event_retention_days` | int | `90` | Entre 1 e 365; sujeito a revisão jurídica. |
| `rate_window_seconds` | int | `60` | Janela de frequência. |
| `max_events_per_source` | int | `20` | Limite por origem na janela. |

### firewall

| Campo | Tipo | Padrão | Regra |
|---|---|---|---|
| `adapter` | string | `dry_run` | `dry_run` ou `nftables`. |
| `enforce_enabled` | bool | `false` | Só pode ser verdadeiro com homologação. |
| `default_ttl_seconds` | int | `900` | Entre 60 e `max_ttl_seconds`. |
| `max_ttl_seconds` | int | `3600` | Teto absoluto. |
| `max_active_blocks` | int | `20` | Limite de regras ativas. |
| `max_new_blocks_per_hour` | int | `10` | Limite de novos bloqueios. |

### allowlist

Lista de IPs ou CIDRs. A allowlist do banco será gerenciada pela CLI nas fases
seguintes. A configuração estática deve conter, no mínimo, loopback e o endereço
administrativo do laboratório.

### notifications

| Campo | Tipo | Padrão | Regra |
|---|---|---|---|
| `local_enabled` | bool | `true` | Log local e saída da CLI. |
| `external_enabled` | bool | `false` | Canal externo desabilitado no MVP. |

## 4. Regras de validação

- `mode=enforce` exige `firewall.enforce_enabled=true`, adaptador homologado,
  allowlist válida e confirmação explícita.
- `adapter=dry_run` não pode criar regras reais.
- `default_ttl_seconds` não pode exceder `max_ttl_seconds`.
- `max_active_blocks` e `max_new_blocks_per_hour` devem ser maiores que zero.
- IPs e CIDRs inválidos rejeitam a configuração.
- O IP do agente, gateway, DNS, DHCP, VPN e administrador deve estar na
  allowlist ou em faixa protegida.
- O container não pode publicar em `0.0.0.0` por padrão; usar loopback no
  desenvolvimento e IP host-only no laboratório.
- Configuração inválida não pode resultar em bloqueio.

## 5. Exemplo mínimo

```yaml
app:
  name: sentineliot
  environment: lab
  log_level: INFO

agent:
  mode: observe
  poll_interval_seconds: 2
  data_dir: "./data"

honeypot:
  enabled: true
  profile: camera-http
  listen_port: 8080
  publish_host: "127.0.0.1"

detection:
  event_retention_days: 90
  rate_window_seconds: 60
  max_events_per_source: 20

firewall:
  adapter: dry_run
  enforce_enabled: false
  default_ttl_seconds: 900
  max_ttl_seconds: 3600
  max_active_blocks: 20
  max_new_blocks_per_hour: 10

allowlist:
  - "127.0.0.1/32"

notifications:
  local_enabled: true
  external_enabled: false
```

## 6. Segredos

- Não gravar tokens, senhas ou chaves no Git, nos logs ou nos exemplos.
- Usar `.env` local, com permissões restritas, ou um gerenciador de segredos na
  evolução do produto.
- Redigir valores sensíveis em logs e exportações.
- O MVP não precisa de credenciais de nuvem.

## 7. Estado de implementação

O carregamento YAML, os defaults seguros e a validação estrita já estão
implementados. Erros de validação interrompem a inicialização e são apresentados
como `ConfigurationError`. O modo `enforce` continua exigindo
`firewall.enforce_enabled=true`, e o adaptador `nftables` continua exigindo
habilitação explícita — mas nenhuma regra real de firewall é aplicada nesta
fase.

O diretório de dados pode ser alterado por `agent.data_dir`, pela opção
`--data-dir` ou pela variável `SENTINELIOT_DATA_DIR`. A variável
`SENTINELIOT_CONFIG` força um arquivo de configuração específico. A variável
`SENTINELIOT_LOG_DIR` altera o diretório do log do agente.

Nenhuma configuração atual deve ser considerada homologada para produção.
