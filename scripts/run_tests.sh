#!/usr/bin/env bash
# SentinelIoT - qualidade e testes na VM Linux.

set -euo pipefail

echo "SentinelIoT - qualidade e testes"
uv run ruff check .
uv run mypy src
uv run pytest
echo "OK"
