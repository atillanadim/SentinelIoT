#!/usr/bin/env bash
# SentinelIoT - verificacao de pre-requisitos na VM Linux.
# Apenas verifica ferramentas. Nao instala pacotes, nao altera firewall,
# nao cria rede e nao inicia containers.

set -euo pipefail

echo "SentinelIoT - Fase 0 - verificacao de pre-requisitos (Linux)"
echo

missing=0

check_tool() {
    local name="$1"
    local command="$2"
    if command -v "$command" >/dev/null 2>&1; then
        echo "[OK]    ${name} -> $(command -v "$command")"
    else
        echo "[FALTA] ${name} (${command})"
        missing=$((missing + 1))
    fi
}

check_tool "Git" "git"
check_tool "uv" "uv"
check_tool "Python 3.11" "python3.11"
check_tool "Docker" "docker"

echo
echo "Versoes encontradas:"
git --version || true
uv --version || true
python3.11 --version || true
docker --version || true

echo
echo "Requisitos de laboratorio:"
echo "- VM Linux dedicada, sem uso de rede domestica de producao."
echo "- Rede host-only isolada e autorizada."
echo "- Snapshot antes de qualquer teste de firewall."
echo "- Nenhuma regra de firewall sera alterada por este script."

if [ "$missing" -gt 0 ]; then
    echo
    echo "Existem ${missing} ferramenta(s) ausente(s)."
    exit 1
fi

exit 0
