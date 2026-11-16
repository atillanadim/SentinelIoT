# syntax=docker/dockerfile:1
#
# Imagem minima da isca SentinelIoT.
#
# O contexto de build e a raiz do repositorio (ver deploy/honeypot/README.md).
# O container roda sem root, sem capabilities, com filesystem somente leitura
# e sem acesso ao docker.sock. A isca escreve o spool JSONL em /spool, que o
# agente monta como volume.

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SENTINELIOT_SPOOL_FILE=/spool/honeypot.jsonl

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --no-compile . \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin sentinel

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import os, socket; socket.create_connection(('127.0.0.1', int(os.environ['SENTINELIOT_HONEYPOT_PORT'])), 3).close()"

ENTRYPOINT ["python", "-m", "sentineliot.honeypot.container"]
