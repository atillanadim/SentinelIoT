# Isca isolada em Docker (Fase 1)

Este diretorio entrega o runtime em container previsto na Fase 1. A isca roda
em um container sem root, com capabilities removidas, filesystem somente
leitura, limites de CPU/RAM/PIDs e sem rota de saida. O agente Sentinel continua
**fora** do container e apenas cria, observa e remove containers.

## Como as pecas se encaixam

```text
VM Linux de laboratorio (host-only)
  |
  |-- Agente SentinelIoT (non-root)
  |     |-- DockerHoneypotManager -> `docker run` da isca
  |     |-- le data/spool/honeypot.jsonl  <--+
  |     `-- SQLite / lista de ban            |
  |                                          |
  `-- Container (imagem sentineliot-honeypot) |
        |-- sem root, cap_drop ALL            |
        |-- read-only + tmpfs /tmp            |
        |-- rede interna (sem egress)         |
        `-- volume /spool --------------------+
```

O container escreve o **mesmo** spool JSONL consumido pelo coletor, portanto o
contrato de eventos, deduplicacao e lista de ban nao muda entre os runtimes
`local` e `docker`.

## Portas e rede

| Item | Valor padrao | Observacao |
|---|---|---|
| Porta publicada | `8080` | Igual a `honeypot.listen_port`. |
| Host de publicacao | `127.0.0.1` | No laboratorio, usar o IP host-only da VM. |
| Porta no container | mesma da publicada | Definida por `SENTINELIOT_HONEYPOT_PORT`. |
| Rede Docker | `sentineliot-lab` | Criada com `--internal` (sem egress). |
| Volume | `data/spool` -> `/spool` | Spool JSONL compartilhado com o agente. |

## Usando pelo agente

```yaml
honeypot:
  runtime: docker
  image: sentineliot-honeypot:0.1.0
  network: sentineliot-lab
  publish_host: "192.168.57.10"
  listen_port: 8080
  cpu_limit: "0.25"
  memory_limit: 128m
  pids_limit: 64
  read_only: true
```

```bash
# construir a imagem (contexto = raiz do repositorio)
docker build -f deploy/honeypot/Dockerfile -t sentineliot-honeypot:0.1.0 .

# subir a isca pelo agente
sentineliot start
sentineliot status
sentineliot scan
```

## Usando manualmente com Compose

```bash
docker compose -f deploy/honeypot/docker-compose.yml up -d --build
docker compose -f deploy/honeypot/docker-compose.yml ps
docker compose -f deploy/honeypot/docker-compose.yml logs -f
docker compose -f deploy/honeypot/docker-compose.yml down
```

## Teste de isolamento

```bash
# 1. O container nao roda como root.
docker inspect -f '{{.Config.User}}' sentineliot-camera-01

# 2. Sem capabilities e sem novos privilegios.
docker inspect -f '{{.HostConfig.CapDrop}} {{.HostConfig.SecurityOpt}}' sentineliot-camera-01

# 3. Sem acesso ao docker.sock.
docker inspect -f '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' sentineliot-camera-01

# 4. Sem egress: a rede e interna.
docker network inspect sentineliot-lab -f '{{.Internal}}'

# 5. Limites aplicados.
docker inspect -f '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}' sentineliot-camera-01
```

Resultado esperado: `User` nao vazio e diferente de `root`/`0`; `CapDrop=[ALL]`;
`SecurityOpt` contem `no-new-privileges`; nenhum mount aponta para
`/var/run/docker.sock`; `Internal=true`; limites de memoria, CPU e PIDs
diferentes de zero.

## Privacidade

A isca grava apenas metadados: IP e porta de origem, porta de destino, perfil,
tipo de evento, severidade, timestamp, metodo, caminho, status e User-Agent
truncado. Corpos, query strings, senhas e payloads nunca sao persistidos.

## Limitacoes

- Docker compartilha o kernel: nao e uma fronteira absoluta.
- A publicacao de porta na rede interna precisa ser revalidada no laboratorio
  (ver `docs/test-plan.md` e `docs/decisions/ADR-0004.md`).
- A imagem precisa ser construida (ou carregada com `docker save`/`docker load`)
  onde houver base disponivel; a VM offline exige pre-carregar a imagem base.
