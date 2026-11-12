"""Servidores-isca locais: HTTP falso, banner SSH e prompt Telnet."""

from __future__ import annotations

import logging
import socketserver
import threading
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast

from sentineliot.core.errors import HoneypotError
from sentineliot.events.classification import classify_http
from sentineliot.events.models import Event, utc_now
from sentineliot.honeypot.profiles import HoneypotProfile
from sentineliot.honeypot.spool import SpoolWriter
from sentineliot.honeypot.state import HoneypotInstance
from sentineliot.security.validation import safe_text

LOGGER = logging.getLogger("sentineliot.honeypot")
MAX_BODY_BYTES = 65_536
MAX_LINE_BYTES = 512
SOCKET_TIMEOUT = 5.0


@dataclass(frozen=True)
class RunningHoneypot:
    id: str
    profile: str
    host: str
    port: int
    protocol: str


CAMERA_PAGES: dict[str, tuple[int, str, str]] = {
    "/": (
        200,
        """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>SentinelCam - Live</title></head>
<body style="background:#111;color:#ddd;font-family:sans-serif">
<h1>SentinelCam IP-100</h1><p>Stream principal: online</p>
<p>Firmware 1.4.2 | dispositivo sentinel-cam-01</p>
<ul><li><a href="/admin/" style="color:#4af">Administracao</a></li>
<li><a href="/camera/" style="color:#4af">Configuracao</a></li></ul>
</body></html>""",
        "text/html; charset=utf-8",
    ),
    "/admin/": (
        200,
        """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>SentinelCam - Login</title></head>
<body style="background:#111;color:#ddd;font-family:sans-serif">
<h1>Administracao</h1><form method="post" action="/cgi-bin/sentinel_login.py">
<p>Usuario: <input name="username"></p><p>Senha: <input type="password" name="password"></p>
<p><button type="submit">Entrar</button></p></form></body></html>""",
        "text/html; charset=utf-8",
    ),
    "/camera/": (
        200,
        """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>SentinelCam - Configuracao</title></head>
<body style="background:#111;color:#ddd;font-family:sans-serif">
<h1>Configuracao da camera</h1><p>Resolucao, rede e gravacao exigem autenticacao.</p>
<form method="post" action="/cgi-bin/sentinel_camera.py">
<p>Hostname: <input name="hostname"></p><p><button type="submit">Salvar</button></p></form>
</body></html>""",
        "text/html; charset=utf-8",
    ),
    "/api/": (
        401,
        '{"error":"unauthorized","message":"device token invalid","device":"sentinel-cam-01"}',
        "application/json",
    ),
    "/server-status": (
        200,
        "<html><body><h1>Status</h1><p>uptime=42d requests=1337</p></body></html>",
        "text/html; charset=utf-8",
    ),
    "/robots.txt": (200, "User-agent: *\nDisallow: /admin/\nDisallow: /camera/\n", "text/plain"),
}

ROUTER_PAGES: dict[str, tuple[int, str, str]] = {
    "/": (
        200,
        """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>SentinelRouter - Login</title></head><body style="font-family:sans-serif;background:#eef">
<h1>SentinelRouter</h1><form method="post" action="/login">
<p>Usuario: <input name="username"></p><p>Senha: <input type="password" name="password"></p>
<p><button type="submit">Entrar</button></p></form></body></html>""",
        "text/html; charset=utf-8",
    ),
    "/login": (
        200,
        """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>SentinelRouter - Login</title></head><body style="font-family:sans-serif;background:#eef">
<h1>SentinelRouter</h1><form method="post" action="/login">
<p>Usuario: <input name="username"></p><p>Senha: <input type="password" name="password"></p>
<p><button type="submit">Entrar</button></p></form></body></html>""",
        "text/html; charset=utf-8",
    ),
    "/admin/": (401, "<h1>401 - Autenticacao obrigatoria</h1>", "text/html; charset=utf-8"),
    "/api/": (401, '{"error":"unauthorized"}', "application/json"),
}


def _response(profile_id: str, path: str, method: str) -> tuple[int, str, str]:
    pages = CAMERA_PAGES if profile_id == "camera-http" else ROUTER_PAGES
    if method == "POST":
        if path == "/cgi-bin/sentinel_login.py":
            return 401, "<h1>401 - Credenciais invalidas</h1>", "text/html; charset=utf-8"
        if path == "/cgi-bin/sentinel_camera.py":
            return 403, "<h1>403 - Configuracao bloqueada</h1>", "text/html; charset=utf-8"
        if path == "/cgi-bin/sentinel_api.py":
            return (
                401,
                '{"error":"unauthorized","message":"device token invalid"}',
                "application/json",
            )
        if path == "/login":
            return 401, "<h1>401 - Credenciais invalidas</h1>", "text/html; charset=utf-8"
    page = pages.get(path)
    if page is not None:
        return page
    return (
        404,
        "<html><body><h1>404 - Not Found</h1></body></html>",
        "text/html; charset=utf-8",
    )


class HoneypotHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        instance: HoneypotInstance,
        profile: HoneypotProfile,
        writer: SpoolWriter,
    ) -> None:
        self.instance = instance
        self.profile = profile
        self.writer = writer
        super().__init__(address, HoneypotHTTPHandler)


class HoneypotHTTPHandler(BaseHTTPRequestHandler):
    """Registra metodo, caminho e user-agent; nunca corpo ou query string."""

    server_version = "lighttpd/1.4.59"
    sys_version = ""

    @property
    def app_server(self) -> HoneypotHTTPServer:
        return cast(HoneypotHTTPServer, self.server)

    def do_GET(self) -> None:
        self._handle()

    def do_HEAD(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def _handle(self) -> None:
        method = self.command or "GET"
        target = self.path or "/"
        path = target.split("?", 1)[0]
        user_agent = safe_text(self.headers.get("User-Agent", ""), 200)
        self._drain_body()
        status, body, content_type = _response(self.app_server.instance.profile, path, method)
        signals = classify_http(
            target=target,
            method=method,
            user_agent=user_agent,
            status=status,
            is_post=method == "POST",
        )
        for signal in signals:
            self._record(
                event_type=signal.event_type,
                detail=signal.detail,
                status=status,
                method=method,
                path=path,
                user_agent=user_agent,
            )
        self._send(status, body, content_type)

    def _drain_body(self) -> None:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = max(0, min(int(raw_length), MAX_BODY_BYTES))
        except ValueError:
            length = 0
        if length:
            _ = self.rfile.read(length)

    def _record(
        self,
        *,
        event_type: str,
        detail: str,
        status: int,
        method: str,
        path: str,
        user_agent: str,
    ) -> None:
        server = self.app_server
        event = Event(
            source_ip=self.client_address[0],
            source_port=self.client_address[1],
            honeypot_id=server.instance.id,
            profile=server.instance.profile,
            protocol="http",
            event_type=event_type,
            timestamp_utc=utc_now(),
            event_id=uuid.uuid4().hex[:20],
            method=method,
            path=safe_text(path, 256),
            status=status,
            user_agent=user_agent,
            detail=detail,
        )
        server.writer.write(event)

    def _send(self, status: int, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


class HoneypotTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        instance: HoneypotInstance,
        profile: HoneypotProfile,
        writer: SpoolWriter,
    ) -> None:
        self.instance = instance
        self.profile = profile
        self.writer = writer
        super().__init__(address, HoneypotTCPHandler)


class HoneypotTCPHandler(socketserver.BaseRequestHandler):
    @property
    def app_server(self) -> HoneypotTCPServer:
        return cast(HoneypotTCPServer, self.server)

    def handle(self) -> None:
        settings = self.app_server
        profile = settings.profile
        try:
            self.request.settimeout(SOCKET_TIMEOUT)
            if profile.protocol == "ssh":
                self._handle_ssh(settings)
            elif profile.protocol == "telnet":
                self._handle_telnet(settings)
            else:
                self._record(settings, "connection", "conexao TCP recebida")
        except (OSError, ValueError):
            return

    def _handle_ssh(self, server: HoneypotTCPServer) -> None:
        self.request.sendall((server.profile.banner + "\r\n").encode("utf-8"))
        payload = self._read_chunk()
        if payload.startswith(b"SSH-"):
            self._record(server, "connection", "handshake SSH recebido")
        elif payload:
            self._record(server, "probe", "payload inesperado apos banner SSH")
        else:
            self._record(server, "connection", "conexao sem dados")

    def _handle_telnet(self, server: HoneypotTCPServer) -> None:
        self.request.sendall(server.profile.banner.encode("utf-8"))
        username = self._read_line()
        if not username:
            self._record(server, "connection", "conexao Telnet sem login")
            return
        self.request.sendall(b"Password: ")
        password = self._read_line()
        detail = "tentativa de login Telnet (credenciais nao armazenadas)"
        if not password:
            detail = "tentativa de login Telnet sem senha (credenciais nao armazenadas)"
        self._record(server, "credential_attempt", detail)
        self.request.sendall(b"\r\nLogin incorrect\r\n")

    def _read_chunk(self) -> bytes:
        try:
            return cast(bytes, self.request.recv(MAX_LINE_BYTES))
        except OSError:
            return b""

    def _read_line(self) -> bytes:
        buffer = bytearray()
        while len(buffer) < MAX_LINE_BYTES:
            try:
                chunk = cast(bytes, self.request.recv(64))
            except OSError:
                break
            if not chunk:
                break
            buffer.extend(chunk)
            if b"\n" in chunk:
                break
        return bytes(buffer)

    def _record(self, server: HoneypotTCPServer, event_type: str, detail: str) -> None:
        event = Event(
            source_ip=self.client_address[0],
            source_port=self.client_address[1],
            honeypot_id=server.instance.id,
            profile=server.instance.profile,
            protocol=server.profile.protocol,
            event_type=event_type,
            timestamp_utc=utc_now(),
            event_id=uuid.uuid4().hex[:20],
            detail=detail,
        )
        server.writer.write(event)


class ServerHandle:
    instance: HoneypotInstance
    profile: HoneypotProfile

    def start(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    @property
    def running(self) -> RunningHoneypot:
        raise NotImplementedError


class HTTPHoneypot(ServerHandle):
    def __init__(
        self,
        instance: HoneypotInstance,
        profile: HoneypotProfile,
        writer: SpoolWriter,
    ) -> None:
        self.instance = instance
        self.profile = profile
        self.writer = writer
        self._server: HoneypotHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        try:
            server = HoneypotHTTPServer(
                (self.instance.host, self.instance.port), self.instance, self.profile, self.writer
            )
        except OSError as exc:
            raise HoneypotError(
                f"nao foi possivel abrir {self.instance.host}:{self.instance.port}: {exc}"
            ) from exc
        thread = threading.Thread(
            target=server.serve_forever,
            name=f"honeypot-{self.instance.id}",
            daemon=True,
        )
        thread.start()
        self._server = server
        self._thread = thread
        LOGGER.info(
            "honeypot %s (%s) escutando em %s",
            self.instance.id,
            self.profile.id,
            self.instance.endpoint,
        )

    def stop(self) -> None:
        server = self._server
        self._server = None
        self._thread = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        LOGGER.info("honeypot %s parado", self.instance.id)

    @property
    def running(self) -> RunningHoneypot:
        return RunningHoneypot(
            id=self.instance.id,
            profile=self.profile.id,
            host=self.instance.host,
            port=self.instance.port,
            protocol=self.profile.protocol,
        )


class TCPHoneypot(ServerHandle):
    def __init__(
        self,
        instance: HoneypotInstance,
        profile: HoneypotProfile,
        writer: SpoolWriter,
    ) -> None:
        self.instance = instance
        self.profile = profile
        self.writer = writer
        self._server: HoneypotTCPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        try:
            server = HoneypotTCPServer(
                (self.instance.host, self.instance.port), self.instance, self.profile, self.writer
            )
        except OSError as exc:
            raise HoneypotError(
                f"nao foi possivel abrir {self.instance.host}:{self.instance.port}: {exc}"
            ) from exc
        thread = threading.Thread(
            target=server.serve_forever,
            name=f"honeypot-{self.instance.id}",
            daemon=True,
        )
        thread.start()
        self._server = server
        self._thread = thread
        LOGGER.info(
            "honeypot %s (%s) escutando em %s",
            self.instance.id,
            self.profile.id,
            self.instance.endpoint,
        )

    def stop(self) -> None:
        server = self._server
        self._server = None
        self._thread = None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        LOGGER.info("honeypot %s parado", self.instance.id)

    @property
    def running(self) -> RunningHoneypot:
        return RunningHoneypot(
            id=self.instance.id,
            profile=self.profile.id,
            host=self.instance.host,
            port=self.instance.port,
            protocol=self.profile.protocol,
        )


def build_server(
    instance: HoneypotInstance, profile: HoneypotProfile, writer: SpoolWriter
) -> ServerHandle:
    if profile.protocol == "http":
        return HTTPHoneypot(instance, profile, writer)
    return TCPHoneypot(instance, profile, writer)
