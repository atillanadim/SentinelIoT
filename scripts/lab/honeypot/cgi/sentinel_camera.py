#!/usr/bin/python3
"""Honeypot de configuração da câmera. Registra apenas metadados."""

from sentinel_common import log_event, read_form, respond

PAGE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>SentinelCam - Configuração</title></head>
<body style="font-family:sans-serif;background:#111;color:#ddd">
<h1>403 - Configuração bloqueada</h1>
<p>A alteração de configuração exige autenticação de fábrica.</p>
<p><a href="/camera/" style="color:#4af">Voltar</a></p>
</body></html>
"""


def main() -> None:
    form = read_form()
    honeypot = form.get("honeypot", ["camera-config"])[0][:64]
    log_event(
        honeypot=honeypot,
        event_type="config_attempt",
        path="/cgi-bin/sentinel_camera.py",
        method="POST",
        status=403,
        detail="tentativa de alteração de configuração (valores não armazenados)",
    )
    respond(403, PAGE)


if __name__ == "__main__":
    main()
