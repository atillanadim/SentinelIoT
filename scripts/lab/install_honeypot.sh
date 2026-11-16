#!/bin/bash
# =============================================================================
# SentinelIoT - instala o honeypot Docker e o agente na VM sentinel-mint.
#
# Executar como root dentro da VM, a partir do diretorio extraido do pacote:
#     sudo bash install_honeypot.sh
#
# O honeypot roda em um container Apache. O agente Sentinel roda no host,
# le os logs pelo bind mount /var/log/sentinel e aplica o bloqueio no
# firewall do proprio Mint.
# =============================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "ERRO: execute como root (sudo bash install_honeypot.sh)" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DEBIAN_FRONTEND=noninteractive

echo "== 1. Pacotes base =="
apt-get update
apt-get install -y docker.io nftables iptables openssh-server curl

# Compose v2 e obrigatorio: o arquivo usa a especificacao moderna (sem version).
COMPOSE=()
if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1 \
    && docker-compose version 2>/dev/null | grep -q 'version v2'; then
    COMPOSE=(docker-compose)
else
    apt-get install -y docker-compose-v2 >/dev/null 2>&1 || true
    if docker compose version >/dev/null 2>&1; then
        COMPOSE=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE=(docker-compose)
    else
        echo "ERRO: Docker Compose v2 nao encontrado." >&2
        exit 1
    fi
fi
systemctl enable --now docker

echo "== 2. Usuario www-data e diretorios de log =="
# O Apache do container roda como www-data (uid/gid 33). O bind mount
# precisa pertencer ao mesmo uid/gid no host para o CGI escrever o spool.
if ! getent group www-data >/dev/null; then
    groupadd -g 33 www-data 2>/dev/null || true
fi
if ! id -u www-data >/dev/null 2>&1; then
    useradd -u 33 -g www-data -r -s /usr/sbin/nologin www-data 2>/dev/null || true
fi
if ! id -u www-data >/dev/null 2>&1; then
    echo "ERRO: nao foi possivel criar o usuario www-data (uid 33)." >&2
    exit 1
fi
install -d -m 0750 /opt/sentinel /etc/sentinel /var/lib/sentinel
install -d -o www-data -g www-data -m 0770 /var/log/sentinel
install -d -o www-data -g www-data -m 0770 /var/log/sentinel/apache

echo "== 3. Projeto Docker =="
# Desativa um Apache nativo, caso exista de uma tentativa anterior.
systemctl disable --now apache2 >/dev/null 2>&1 || true
install -d -m 0755 /opt/sentinel/docker /opt/sentinel/honeypot
cp -a "$SCRIPT_DIR/honeypot/." /opt/sentinel/honeypot/
cp -a "$SCRIPT_DIR/docker/." /opt/sentinel/docker/
if [ -f "$SCRIPT_DIR/.dockerignore" ]; then
    install -m 0644 "$SCRIPT_DIR/.dockerignore" /opt/sentinel/.dockerignore
fi
cd /opt/sentinel/docker

echo "== 4. Build e inicio do container =="
"${COMPOSE[@]}" build
"${COMPOSE[@]}" up -d
sleep 5
"${COMPOSE[@]}" ps

echo "== 5. Agente Sentinel (host) =="
install -m 0755 "$SCRIPT_DIR/sentinel_agent.py" /opt/sentinel/sentinel_agent.py
install -m 0640 "$SCRIPT_DIR/agent.json" /etc/sentinel/agent.json
install -m 0644 "$SCRIPT_DIR/sentinel-agent.service" \
    /etc/systemd/system/sentinel-agent.service
install -m 0644 "$SCRIPT_DIR/logrotate-sentinel" /etc/logrotate.d/sentinel
cat > /usr/local/bin/sentinel <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /opt/sentinel/sentinel_agent.py "$@"
EOF
chmod 0755 /usr/local/bin/sentinel
systemctl daemon-reload
systemctl enable --now sentinel-agent

echo "== 6. SSH =="
systemctl enable --now ssh
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
    ufw allow 80/tcp
fi
# Conveniencia de laboratorio: permite usar docker sem sudo.
usermod -aG docker sentinel >/dev/null 2>&1 || true

echo "== 7. Verificacao =="
sleep 2
systemctl is-active docker sentinel-agent
"${COMPOSE[@]}" ps
echo "-- endpoints --"
for path in / /admin/ /camera/ /api/ /server-status; do
    code=$(curl -sS --retry 10 --retry-connrefused --retry-delay 1 \
        -o /dev/null -w '%{http_code}' "http://127.0.0.1${path}" || echo 000)
    echo "  ${path} -> HTTP ${code}"
done
echo "-- gerando um evento de teste (login no honeypot) --"
curl -sS -o /dev/null -X POST \
    -d 'honeypot=admin-portal&username=admin&password=teste' \
    http://127.0.0.1/cgi-bin/sentinel_login.py || true
sleep 2
/usr/bin/python3 /opt/sentinel/sentinel_agent.py selftest
/usr/bin/python3 /opt/sentinel/sentinel_agent.py status

echo "== Concluido =="
echo "Container:  docker ps --filter name=sentinel-honeypot"
echo "Logs:       cd /opt/sentinel/docker && ${COMPOSE[*]} logs -f"
echo "Honeypots:  /admin/  /camera/  /api/  /server-status"
echo "Spool:      /var/log/sentinel/honeypot.jsonl"
echo "Agente:     sentinel status | sentinel run --mode enforce"
