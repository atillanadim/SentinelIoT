#!/usr/bin/env bash
# Remove apenas caches locais do projeto. Dados de eventos so sao removidos com
# --include-data. Nao remove containers, volumes, regras de firewall ou redes.

set -euo pipefail

include_data=0
if [ "${1:-}" = "--include-data" ]; then
    include_data=1
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

targets=(
    "${root}/.pytest_cache"
    "${root}/.mypy_cache"
    "${root}/.ruff_cache"
    "${root}/htmlcov"
    "${root}/.coverage"
)

if [ "$include_data" -eq 1 ]; then
    targets+=("${root}/data")
fi

for target in "${targets[@]}"; do
    if [ -e "$target" ]; then
        echo "Removendo ${target}"
        rm -rf "$target"
    fi
done

find "$root" -type d -name "__pycache__" -print0 2>/dev/null |
    while IFS= read -r -d "" directory; do
        echo "Removendo ${directory}"
        rm -rf "$directory"
    done

echo "Limpeza concluida. Nenhum recurso de Docker ou firewall foi alterado."
