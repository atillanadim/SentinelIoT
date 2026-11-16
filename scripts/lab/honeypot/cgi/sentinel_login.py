#!/usr/bin/python3
"""Honeypot de login administrativo. Registra apenas metadados."""

from sentinel_common import log_event, read_form, respond

PAGE = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>SentinelCam - Acesso negado</title></head>
<body style="font-family:sans-serif;background:#111;color:#ddd">
<h1>401 - Credenciais inválidas</h1>
<p>O painel administrativo da câmera rejeitou a autenticação.</p>
<p><a href="/admin/" style="color:#4af">Voltar</a></p>
</body></html>
"""


def main() -> None:
    form = read_form()
    honeypot = form.get("honeypot", ["admin-portal"])[0][:64]
    log_event(
        honeypot=honeypot,
        event_type="credential_attempt",
        path="/cgi-bin/sentinel_login.py",
        method="POST",
        status=401,
        detail="tentativa de login (credenciais não armazenadas)",
    )
    respond(401, PAGE)


if __name__ == "__main__":
    main()
