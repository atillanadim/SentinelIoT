#!/usr/bin/python3
"""Honeypot de API JSON. Registra apenas metadados."""

import json

from sentinel_common import log_event, respond

PAGE = {
    "error": "unauthorized",
    "message": "device token invalid",
    "device": "sentinel-cam-01",
}


def main() -> None:
    log_event(
        honeypot="device-api",
        event_type="credential_attempt",
        path="/cgi-bin/sentinel_api.py",
        method="POST",
        status=401,
        detail="tentativa de autenticação na API (token não armazenado)",
    )
    respond(401, json.dumps(PAGE), content_type="application/json")


if __name__ == "__main__":
    main()
