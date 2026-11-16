"""Servidor HTTP local do dashboard (somente leitura).

Nao existe endpoint de escrita: eventos, decisoes e firewall continuam sendo
operados pela CLI. O servidor escuta em loopback por padrao e responde apenas
com os dados do banco, do spool e do runtime do agente.
"""

from __future__ import annotations

import json
import socket
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from sentineliot.core.errors import SentinelError
from sentineliot.security.validation import safe_text, validate_ip
from sentineliot.storage.database import SUSPECT_STATUSES
from sentineliot.web.assets import DASHBOARD_HTML
from sentineliot.web.snapshot import WebDataService

SEVERITIES = ("low", "medium", "high", "critical")
MAX_QUERY_LENGTH = 64


class DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class DashboardHTTPServerV6(DashboardHTTPServer):
    address_family = socket.AF_INET6


def _first(query: dict[str, list[str]], name: str) -> str:
    values = query.get(name)
    if not values:
        return ""
    return values[0].strip()


def _int_param(query: dict[str, list[str]], name: str, default: int) -> int:
    raw = _first(query, name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"parametro {name} invalido") from exc


def _optional_text(query: dict[str, list[str]], name: str) -> str | None:
    raw = _first(query, name)
    if not raw:
        return None
    cleaned = safe_text(raw, MAX_QUERY_LENGTH)
    return cleaned or None


def make_handler(service: WebDataService, refresh_seconds: int) -> type[BaseHTTPRequestHandler]:
    """Cria o handler HTTP com o servico e o intervalo de atualizacao fixados."""

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "SentinelIoT"
        sys_version = ""

        def do_GET(self) -> None:
            self._handle(head_only=False)

        def do_HEAD(self) -> None:
            self._handle(head_only=True)

        def do_POST(self) -> None:
            self._read_only()

        def do_PUT(self) -> None:
            self._read_only()

        def do_PATCH(self) -> None:
            self._read_only()

        def do_DELETE(self) -> None:
            self._read_only()

        def _read_only(self) -> None:
            self._error(
                HTTPStatus.METHOD_NOT_ALLOWED,
                "o dashboard e somente leitura; use a CLI para decisoes e configuracao",
                head_only=False,
            )

        def log_message(self, format: str, *args: object) -> None:
            # O dashboard e local e atualiza a cada poucos segundos; nao poluir o log.
            return

        def _handle(self, *, head_only: bool) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)
            try:
                if path in {"/", "/index.html"}:
                    html = DASHBOARD_HTML.replace(
                        "__REFRESH_MS__", str(max(1, refresh_seconds) * 1000)
                    )
                    self._html(html, head_only=head_only)
                elif path == "/api/summary":
                    self._json(service.summary(), head_only=head_only)
                elif path == "/api/events":
                    self._json(self._events(query), head_only=head_only)
                elif path.startswith("/api/events/"):
                    self._event(unquote(path[len("/api/events/") :]), head_only=head_only)
                elif path == "/api/suspects":
                    self._json(self._suspects(query), head_only=head_only)
                elif path in {"/healthz", "/api/health"}:
                    payload = service.health()
                    status = (
                        HTTPStatus.OK
                        if payload.get("status") == "ok"
                        else HTTPStatus.SERVICE_UNAVAILABLE
                    )
                    self._json(payload, status=status, head_only=head_only)
                else:
                    self._error(HTTPStatus.NOT_FOUND, "rota nao encontrada", head_only=head_only)
            except (SentinelError, ValueError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc), head_only=head_only)
            except Exception:
                self._error(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    "erro interno ao montar a resposta do dashboard",
                    head_only=head_only,
                )

        def _events(self, query: dict[str, list[str]]) -> dict[str, object]:
            source_ip = _optional_text(query, "ip")
            if source_ip is not None:
                source_ip = validate_ip(source_ip)
            severity = _optional_text(query, "severity")
            if severity is not None and severity not in SEVERITIES:
                raise ValueError("severidade invalida: use low, medium, high ou critical")
            return service.events(
                limit=_int_param(query, "limit", 50),
                source_ip=source_ip,
                event_type=_optional_text(query, "type"),
                severity=severity,
            )

        def _suspects(self, query: dict[str, list[str]]) -> dict[str, object]:
            status = _optional_text(query, "status")
            if status is not None and status != "all" and status not in SUSPECT_STATUSES:
                raise ValueError(
                    "status invalido: use all, " + ", ".join(SUSPECT_STATUSES)
                )
            return service.suspects(
                status=None if status in (None, "all") else status,
                limit=_int_param(query, "limit", 100),
            )

        def _event(self, event_id: str, *, head_only: bool) -> None:
            payload = service.event(event_id)
            if payload is None:
                self._error(HTTPStatus.NOT_FOUND, "evento nao encontrado", head_only=head_only)
                return
            self._json(payload, head_only=head_only)

        def _headers(
            self,
            status: HTTPStatus,
            content_type: str,
            length: int,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data:; "
                "style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()

        def _json(
            self,
            payload: object,
            *,
            status: HTTPStatus = HTTPStatus.OK,
            head_only: bool,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            self._headers(status, "application/json; charset=utf-8", len(body))
            if not head_only:
                self.wfile.write(body)

        def _html(self, text: str, *, head_only: bool) -> None:
            body = text.encode("utf-8")
            self._headers(HTTPStatus.OK, "text/html; charset=utf-8", len(body))
            if not head_only:
                self.wfile.write(body)

        def _error(self, status: HTTPStatus, message: str, *, head_only: bool) -> None:
            body = json.dumps(
                {"error": message, "status": int(status)}, ensure_ascii=False
            ).encode("utf-8")
            self._headers(status, "application/json; charset=utf-8", len(body))
            if not head_only:
                self.wfile.write(body)

    return DashboardHandler


class DashboardServer:
    """Ciclo de vida do servidor HTTP do dashboard."""

    def __init__(
        self,
        service: WebDataService,
        *,
        host: str = "127.0.0.1",
        port: int = 8787,
        refresh_seconds: int = 3,
    ) -> None:
        self.service = service
        self.host = host
        self.port = port
        self.refresh_seconds = max(1, min(60, refresh_seconds))

    @property
    def url(self) -> str:
        host = self.host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"http://{host}:{self.port}/"

    def build(self) -> DashboardHTTPServer:
        handler = make_handler(self.service, self.refresh_seconds)
        server_class = DashboardHTTPServerV6 if ":" in self.host else DashboardHTTPServer
        try:
            server = server_class((self.host, self.port), handler)
        except OSError as exc:
            raise SentinelError(
                f"nao foi possivel abrir o dashboard em {self.host}:{self.port}: {exc}"
            ) from exc
        self.port = int(server.server_address[1])
        return server

    def run(self, *, open_browser: bool = False) -> int:
        server = self.build()
        url = self.url
        print("SentinelIoT - dashboard local somente leitura")
        print(f"  url    : {url}")
        print(f"  refresh: {self.refresh_seconds}s | Ctrl+C para encerrar")
        print("  aviso  : a interface nao expoe acoes de escrita, bloqueio ou firewall")
        if open_browser:
            threading.Timer(0.6, webbrowser.open, args=(url,)).start()
        try:
            server.serve_forever(poll_interval=0.4)
        except KeyboardInterrupt:
            print()
        finally:
            server.server_close()
        print("dashboard encerrado")
        return 0
