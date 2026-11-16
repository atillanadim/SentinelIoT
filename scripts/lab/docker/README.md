# Honeypot em Docker — laboratório SentinelIoT

Este diretório é a versão **Docker** do honeypot Apache do laboratório. Ela
segue a arquitetura do produto: o honeypot é um container descartável e o
agente Sentinel roda no host, lendo os logs e decidindo o bloqueio.

## Como as peças se encaixam

```text
Kali (10.10.10.20)
   |  HTTP :80
   v
Mint (10.10.10.10)
   |-- Docker: container sentinel-honeypot (Apache + páginas falsas + CGI)
   |      |-- publica 80:80
   |      `-- grava em /var/log/sentinel (bind mount)
   |
   `-- agente Sentinel (host, systemd)
          |-- lê /var/log/sentinel/apache/sentinel-access.log
          |-- lê /var/log/sentinel/honeypot.jsonl
          `-- modo observe/dry_run/enforce -> nftables
```

O container **não** tem acesso ao firewall do host. Quem bloqueia é o agente,
executando como root no Mint. Isso evita dar `NET_ADMIN` ao honeypot.

## Comandos do dia a dia

Tudo abaixo é executado no Mint, dentro de `/opt/sentinel/docker`.

```bash
# subir / reconstruir
docker compose up -d --build

# ver o container e a saúde
docker compose ps
docker ps --filter name=sentinel-honeypot

# acompanhar o Apache do honeypot
docker compose logs -f

# entrar no container para inspecionar
docker compose exec honeypot bash
docker compose exec honeypot tail -f /var/log/sentinel/apache/sentinel-access.log

# parar tudo (os logs do host continuam)
docker compose down

# apagar também o container e a imagem
docker compose down --rmi local
```

## Roteiro de aprendizado

1. **Observe sem bloquear.** O agente começa em `observe`:
   ```bash
   sentinel status
   tail -f /var/log/sentinel/honeypot.jsonl
   ```
2. **Gere tráfego do Kali.**
   ```bash
   curl -s http://10.10.10.10/admin/
   curl -s -A 'sqlmap/1.8' http://10.10.10.10/api/
   ```
3. **Veja a decisão sem aplicar.** Pare o serviço e rode em `dry_run`:
   ```bash
   sudo systemctl stop sentinel-agent
   sudo sentinel run --mode dry_run
   ```
   O log mostra `DECISÃO ... block`, mas o firewall não muda.
4. **Aplique o bloqueio.** Em outra aba:
   ```bash
   sudo systemctl start sentinel-agent
   sudo sentinel status
   sudo nft list table inet sentinel_lab
   ```
   No modo `enforce`, o IP de origem entra no set `blocked_v4` e cai na hora.
5. **Desfaça manualmente.**
   ```bash
   sudo sentinel unblock 10.10.10.20
   ```

## Roteiro do ataque (Kali)

```bash
curl -O http://10.10.10.1/attack_demo.sh
bash attack_demo.sh
```

O script faz reconhecimento com `nmap`, enumeração HTTP, tentativas de login e
injeção — sempre contra `10.10.10.10`. Ele se recusa a rodar com outro alvo.

## Trocar de modo

```bash
# modo temporário em primeiro plano (Ctrl+C para sair)
sudo systemctl stop sentinel-agent
sudo sentinel run --mode enforce

# voltar ao serviço normal (observe)
sudo systemctl start sentinel-agent

# modo permanente: editar e reiniciar
sudo nano /etc/sentinel/agent.json
sudo systemctl restart sentinel-agent
```

## Onde ficam os arquivos

| Caminho no Mint | O que é |
|---|---|
| `/opt/sentinel/docker/docker-compose.yml` | definição do container |
| `/opt/sentinel/honeypot/` | site falso e CGIs copiados para a imagem |
| `/var/log/sentinel/apache/sentinel-access.log` | log HTTP do Apache |
| `/var/log/sentinel/honeypot.jsonl` | metadados dos CGIs |
| `/var/log/sentinel/agent.log` | decisões do agente |
| `/var/lib/sentinel/sentinel.db` | SQLite com eventos e bloqueios |

## Por que o agente também bloqueia `forward`

Quando o Docker publica `80:80`, o pacote que chega do Kali é DNAT'ado e passa
pela cadeia **forward**, não pela `input`. Por isso o agente cria a regra de
drop nas duas cadeias (`input` e `forward`). Sem isso, o bloqueio pareceria
funcionar no `nft list` mas o atacante continuaria acessando o container.

## Privacidade

Os CGIs gravam apenas metadados: IP, porta, caminho, método, status e
User-Agent truncado. Senhas, corpos de requisição, query strings e payloads
não são persistidos.
