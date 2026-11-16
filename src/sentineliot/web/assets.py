"""HTML, CSS e JavaScript embutidos do dashboard local.

Manter os assets no pacote evita dependencia de servidor estatico externo e
garante que o wheel tenha tudo o que precisa para a demonstracao.
"""

# ruff: noqa: E501

from __future__ import annotations

DASHBOARD_HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>SentinelIoT - console local</title>
<style>
  :root {
    color-scheme: dark;
    --bg: #080c12;
    --bg-soft: #0c121b;
    --panel: #111926;
    --panel-2: #0e1520;
    --border: #1e2b3d;
    --border-soft: #182233;
    --text: #e8eef7;
    --muted: #8ea0b8;
    --muted-2: #64748b;
    --accent: #35e0c8;
    --accent-soft: rgba(53, 224, 200, .12);
    --blue: #5aa9ff;
    --green: #4ade80;
    --amber: #fbbf24;
    --red: #fb7185;
    --purple: #c084fc;
    --radius: 16px;
    --shadow: 0 18px 40px rgba(0, 0, 0, .35);
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    min-height: 100vh;
    background:
      radial-gradient(900px 420px at 12% -12%, rgba(53, 224, 200, .12), transparent 60%),
      radial-gradient(800px 400px at 100% 0%, rgba(90, 169, 255, .10), transparent 55%),
      var(--bg);
    color: var(--text);
    font-family: "Segoe UI", system-ui, -apple-system, Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.45;
  }
  a { color: var(--accent); text-decoration: none; }
  .layout { max-width: 1380px; margin: 0 auto; padding: 20px 22px 40px; }

  header.top {
    position: sticky;
    top: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 0 16px;
    backdrop-filter: blur(14px);
    background: linear-gradient(to bottom, rgba(8, 12, 18, .94), rgba(8, 12, 18, .72));
    border-bottom: 1px solid var(--border-soft);
  }
  .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
  .brand-mark {
    width: 42px; height: 42px; flex: 0 0 42px;
    display: grid; place-items: center;
    border-radius: 12px;
    background: linear-gradient(145deg, rgba(53, 224, 200, .22), rgba(90, 169, 255, .10));
    border: 1px solid rgba(53, 224, 200, .35);
    box-shadow: 0 0 24px rgba(53, 224, 200, .16) inset;
  }
  .brand-mark svg { width: 24px; height: 24px; }
  .brand h1 { margin: 0; font-size: 19px; letter-spacing: .2px; }
  .brand p { margin: 0; color: var(--muted); font-size: 12px; }
  .top-spacer { flex: 1; }
  .top-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
  .pill {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 6px 11px; border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--panel-2);
    color: var(--muted);
    font-size: 12px; font-weight: 600;
    white-space: nowrap;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted-2); }
  .dot.live { background: var(--green); box-shadow: 0 0 0 4px rgba(74, 222, 128, .14); }
  .dot.down { background: var(--red); box-shadow: 0 0 0 4px rgba(251, 113, 133, .14); }
  .pill.live { color: var(--green); border-color: rgba(74, 222, 128, .35); }
  .pill.down { color: var(--red); border-color: rgba(251, 113, 133, .35); }
  .mode-observe { color: var(--blue); border-color: rgba(90, 169, 255, .32); }
  .mode-dry_run { color: var(--amber); border-color: rgba(251, 191, 36, .32); }
  .mode-enforce { color: var(--red); border-color: rgba(251, 113, 133, .32); }

  .banner {
    display: none;
    margin: 14px 0 0;
    padding: 11px 14px;
    border-radius: 12px;
    border: 1px solid rgba(251, 113, 133, .35);
    background: rgba(251, 113, 133, .08);
    color: #ffc2cb;
    font-size: 13px;
  }
  .banner.show { display: block; }

  section.kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin: 20px 0 16px;
  }
  .card {
    background: linear-gradient(180deg, var(--panel), var(--panel-2));
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
  }
  .kpi { padding: 15px 16px 14px; position: relative; overflow: hidden; }
  .kpi::after {
    content: ""; position: absolute; inset: auto -30% -60% auto;
    width: 150px; height: 150px; border-radius: 50%;
    background: radial-gradient(circle, var(--accent-soft), transparent 70%);
  }
  .kpi .label { color: var(--muted); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; }
  .kpi .value { font-size: 30px; font-weight: 750; letter-spacing: -.02em; margin-top: 4px; font-variant-numeric: tabular-nums; }
  .kpi .hint { color: var(--muted-2); font-size: 12px; margin-top: 2px; }
  .kpi.alert .value { color: var(--amber); }

  section.grid {
    display: grid;
    grid-template-columns: repeat(12, minmax(0, 1fr));
    gap: 14px;
  }
  .panel { padding: 16px; min-width: 0; }
  .panel h2 {
    margin: 0 0 2px;
    font-size: 14px; letter-spacing: .02em;
    display: flex; align-items: center; gap: 8px;
  }
  .panel h2 .count {
    color: var(--muted); font-weight: 600; font-size: 12px;
    border: 1px solid var(--border); border-radius: 999px; padding: 1px 8px;
  }
  .panel .sub { color: var(--muted-2); font-size: 12px; margin: 0 0 12px; }
  .span-8 { grid-column: span 8; }
  .span-4 { grid-column: span 4; }
  .span-6 { grid-column: span 6; }
  .span-12 { grid-column: span 12; }

  .panel-head { display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
  .panel-head .grow { flex: 1; }
  .toolbar { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .chip-btn {
    appearance: none; cursor: pointer;
    border: 1px solid var(--border);
    background: var(--panel-2);
    color: var(--muted);
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 12px; font-weight: 600;
  }
  .chip-btn:hover { color: var(--text); border-color: #2a3c53; }
  .chip-btn.active { color: var(--accent); border-color: rgba(53, 224, 200, .45); background: var(--accent-soft); }
  .search {
    background: var(--panel-2);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: 999px;
    padding: 5px 12px;
    font-size: 12px;
    min-width: 180px;
    outline: none;
  }
  .search:focus { border-color: rgba(53, 224, 200, .5); }

  table.events { width: 100%; border-collapse: collapse; }
  table.events th {
    text-align: left; color: var(--muted-2);
    font-size: 11px; text-transform: uppercase; letter-spacing: .08em;
    padding: 0 8px 8px; border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  table.events td {
    padding: 9px 8px;
    border-bottom: 1px solid var(--border-soft);
    white-space: nowrap;
    font-size: 13px;
    font-variant-numeric: tabular-nums;
  }
  table.events tr.clickable { cursor: pointer; }
  table.events tr.clickable:hover td { background: rgba(53, 224, 200, .05); }
  table.events tr:last-child td { border-bottom: 0; }
  td.ip { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; color: #cfe3ff; }
  td.path { color: var(--muted); max-width: 220px; overflow: hidden; text-overflow: ellipsis; }
  td.type { color: var(--muted); }
  .sev {
    display: inline-flex; align-items: center;
    border-radius: 999px; padding: 2px 8px;
    font-size: 11px; font-weight: 700; letter-spacing: .02em;
    border: 1px solid transparent;
  }
  .sev-critical { color: #ffd0d8; background: rgba(251, 113, 133, .16); border-color: rgba(251, 113, 133, .4); }
  .sev-high { color: #ffb4a2; background: rgba(251, 146, 60, .14); border-color: rgba(251, 146, 60, .38); }
  .sev-medium { color: #ffe7a3; background: rgba(251, 191, 36, .13); border-color: rgba(251, 191, 36, .34); }
  .sev-low { color: #a7f3d0; background: rgba(74, 222, 128, .12); border-color: rgba(74, 222, 128, .3); }
  .empty { color: var(--muted-2); padding: 22px 8px; text-align: center; font-size: 13px; }

  .suspect { display: flex; gap: 10px; padding: 10px 2px; border-bottom: 1px solid var(--border-soft); align-items: flex-start; }
  .suspect:last-child { border-bottom: 0; }
  .suspect .who { flex: 1; min-width: 0; }
  .suspect .who .ip { font-size: 13px; font-weight: 700; }
  .suspect .who .meta { color: var(--muted-2); font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .suspect .side { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
  .status {
    border-radius: 999px; padding: 2px 8px; font-size: 11px; font-weight: 700;
    border: 1px solid var(--border); color: var(--muted); background: var(--panel-2);
  }
  .status-pending { color: var(--amber); border-color: rgba(251, 191, 36, .34); background: rgba(251, 191, 36, .08); }
  .status-blocked { color: var(--red); border-color: rgba(251, 113, 133, .36); background: rgba(251, 113, 133, .08); }
  .status-allowed { color: var(--green); border-color: rgba(74, 222, 128, .32); background: rgba(74, 222, 128, .08); }
  .status-ignored { color: var(--muted); }
  .status-allowlisted { color: var(--blue); border-color: rgba(90, 169, 255, .32); background: rgba(90, 169, 255, .08); }
  .hits { color: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }

  .chart { display: flex; align-items: flex-end; gap: 4px; height: 120px; padding-top: 8px; }
  .chart .bar-wrap { flex: 1; display: flex; flex-direction: column; justify-content: flex-end; height: 100%; gap: 5px; }
  .chart .bar {
    width: 100%; min-height: 3px; border-radius: 4px 4px 2px 2px;
    background: linear-gradient(180deg, var(--accent), rgba(53, 224, 200, .35));
    opacity: .85;
  }
  .chart .bar.zero { background: var(--border); opacity: 1; }
  .chart .bar-wrap:hover .bar { opacity: 1; box-shadow: 0 0 14px rgba(53, 224, 200, .25); }
  .chart .tick { color: var(--muted-2); font-size: 9px; text-align: center; height: 11px; }
  .chart-foot { display: flex; justify-content: space-between; color: var(--muted-2); font-size: 11px; margin-top: 8px; }

  .type-row { display: grid; grid-template-columns: 130px 1fr 34px; gap: 8px; align-items: center; margin: 7px 0; font-size: 12px; }
  .type-row .name { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .type-row .track { background: var(--border-soft); border-radius: 999px; height: 7px; overflow: hidden; }
  .type-row .fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--blue), var(--purple)); }
  .type-row .n { color: var(--text); text-align: right; font-variant-numeric: tabular-nums; }

  .honeypots { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
  .hp {
    border: 1px solid var(--border); border-radius: 12px;
    padding: 11px 12px; background: var(--panel-2);
    display: flex; flex-direction: column; gap: 3px;
  }
  .hp .row { display: flex; align-items: center; gap: 8px; justify-content: space-between; }
  .hp .name { font-weight: 700; font-size: 13px; }
  .hp .endpoint { color: var(--muted); font-size: 12px; font-family: ui-monospace, Consolas, monospace; }
  .hp .proto { color: var(--muted-2); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }
  .up { color: var(--green); }
  .down { color: var(--muted-2); }

  ul.warnings { margin: 6px 0 0; padding: 0; list-style: none; display: grid; gap: 7px; }
  ul.warnings li { color: var(--muted); font-size: 12px; display: flex; gap: 8px; }
  ul.warnings li::before { content: "!"; color: var(--amber); font-weight: 800; }

  footer {
    margin-top: 20px; padding-top: 14px; border-top: 1px solid var(--border-soft);
    color: var(--muted-2); font-size: 12px;
    display: flex; gap: 12px; flex-wrap: wrap; justify-content: space-between;
  }

  dialog {
    border: 1px solid var(--border); border-radius: 16px;
    background: var(--panel); color: var(--text);
    width: min(560px, calc(100vw - 32px));
    padding: 0; box-shadow: 0 30px 70px rgba(0, 0, 0, .55);
  }
  dialog::backdrop { background: rgba(3, 6, 10, .72); backdrop-filter: blur(3px); }
  .dialog-head { display: flex; align-items: center; gap: 10px; padding: 16px 18px; border-bottom: 1px solid var(--border); }
  .dialog-head h3 { margin: 0; font-size: 15px; flex: 1; }
  .dialog-body { padding: 16px 18px 18px; }
  .dialog-body dl { display: grid; grid-template-columns: 130px 1fr; gap: 8px 12px; margin: 0; }
  .dialog-body dt { color: var(--muted-2); font-size: 12px; }
  .dialog-body dd { margin: 0; font-size: 13px; word-break: break-word; }
  .dialog-note { margin-top: 14px; color: var(--muted-2); font-size: 11px; }
  .x {
    appearance: none; border: 1px solid var(--border); background: var(--panel-2);
    color: var(--muted); width: 30px; height: 30px; border-radius: 9px; cursor: pointer;
    font-size: 16px; line-height: 1;
  }
  .x:hover { color: var(--text); }
  .mono { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }

  @media (max-width: 1100px) {
    .span-8, .span-4, .span-6 { grid-column: span 12; }
    section.kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  @media (max-width: 640px) {
    .layout { padding: 14px 12px 30px; }
    section.kpis { grid-template-columns: 1fr; }
    .brand p { display: none; }
    table.events th:nth-child(5), table.events td:nth-child(5) { display: none; }
  }
</style>
</head>
<body>
<div class="layout">
  <header class="top">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="#35e0c8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 3l7 3v5c0 4.6-3 8.4-7 10-4-1.6-7-5.4-7-10V6l7-3z"/>
          <path d="M9.5 12.2l1.8 1.8 3.4-3.6"/>
        </svg>
      </div>
      <div>
        <h1>SentinelIoT</h1>
        <p>console local de deception &middot; autor s0ra</p>
      </div>
    </div>
    <div class="top-spacer"></div>
    <div class="top-meta">
      <span class="pill" id="mode-pill">modo <strong id="mode-label">observe</strong></span>
      <span class="pill" id="runtime-pill">runtime <strong id="runtime-label">local</strong></span>
      <span class="pill" id="agent-pill"><span class="dot" id="agent-dot"></span><span id="agent-label">verificando</span></span>
      <span class="pill" id="conn-pill"><span class="dot" id="conn-dot"></span><span id="conn-label">conectando</span></span>
      <span class="pill mono" id="clock">--:--:--</span>
    </div>
  </header>

  <div class="banner" id="banner"></div>

  <section class="kpis">
    <div class="card kpi">
      <div class="label">Eventos registrados</div>
      <div class="value" id="kpi-events">0</div>
      <div class="hint" id="kpi-events-hint">nenhuma interacao coletada</div>
    </div>
    <div class="card kpi">
      <div class="label">Ultimas 24 horas</div>
      <div class="value" id="kpi-24h">0</div>
      <div class="hint">janela movel de deteccao</div>
    </div>
    <div class="card kpi">
      <div class="label">IPs observados</div>
      <div class="value" id="kpi-ips">0</div>
      <div class="hint" id="kpi-ips-hint">lista de ban local</div>
    </div>
    <div class="card kpi alert">
      <div class="label">Pendentes de decisao</div>
      <div class="value" id="kpi-pending">0</div>
      <div class="hint">revisao do administrador</div>
    </div>
  </section>

  <section class="grid">
    <article class="card panel span-8">
      <div class="panel-head">
        <div class="grow">
          <h2>Fluxo de eventos <span class="count" id="events-count">0</span></h2>
          <p class="sub">Clique em um evento para ver os metadados coletados.</p>
        </div>
        <div class="toolbar">
          <input class="search" id="search" type="search" placeholder="filtrar ip, tipo ou caminho" aria-label="Filtrar eventos">
          <button class="chip-btn active" data-sev="all" type="button">todos</button>
          <button class="chip-btn" data-sev="high" type="button">alto+</button>
          <button class="chip-btn" data-sev="medium" type="button">medio</button>
          <button class="chip-btn" id="pause" type="button">pausar</button>
        </div>
      </div>
      <div style="overflow-x:auto">
        <table class="events">
          <thead>
            <tr>
              <th>quando</th><th>origem</th><th>isca</th><th>tipo</th><th>sev</th><th>caminho</th>
            </tr>
          </thead>
          <tbody id="event-rows"></tbody>
        </table>
      </div>
      <div class="empty" id="events-empty">Nenhum evento ainda. Rode <span class="mono">sentineliot simulate</span> ou inicie com <span class="mono">serve --demo</span>.</div>
    </article>

    <article class="card panel span-4">
      <h2>IPs observados <span class="count" id="suspects-count">0</span></h2>
      <p class="sub">Ordenados por severidade e ultima interacao.</p>
      <div id="suspect-list"></div>
      <div class="empty" id="suspects-empty">Nenhum IP observado ate agora.</div>
    </article>

    <article class="card panel span-8">
      <h2>Atividade nas ultimas 24 horas</h2>
      <p class="sub">Eventos coletados por hora local. Amostra maxima de 24 horas.</p>
      <div class="chart" id="timeline" aria-label="Grafico de eventos por hora"></div>
      <div class="chart-foot"><span id="timeline-total">0 eventos</span><span>agora &larr; hora local</span></div>
    </article>

    <article class="card panel span-4">
      <h2>Tipos de evento</h2>
      <p class="sub">Distribuicao acumulada do banco local.</p>
      <div id="type-list"></div>
      <div class="empty" id="types-empty">Sem dados para distribuir.</div>
    </article>

    <article class="card panel span-8">
      <h2>Honeypots configurados <span class="count" id="hp-count">0</span></h2>
      <p class="sub">Estado conforme o arquivo de runtime do agente.</p>
      <div class="honeypots" id="honeypot-list"></div>
      <div class="empty" id="honeypots-empty">Nenhuma isca configurada.</div>
    </article>

    <article class="card panel span-4">
      <h2>Postura e avisos</h2>
      <p class="sub">Limites conhecidos desta versao.</p>
      <ul class="warnings" id="warning-list"></ul>
      <div class="type-row" style="margin-top:14px; grid-template-columns: 96px 1fr;">
        <span class="name">banco</span><span class="mono" id="db-meta" style="font-size:11px;color:var(--muted)">-</span>
      </div>
      <div class="type-row" style="grid-template-columns: 96px 1fr;">
        <span class="name">spool</span><span class="mono" id="spool-meta" style="font-size:11px;color:var(--muted)">-</span>
      </div>
    </article>
  </section>

  <footer>
    <span>SentinelIoT <strong id="version">0.1.0</strong> &middot; interface local somente leitura, restrita a loopback.</span>
    <span>Sem corpos, query strings, senhas ou payloads no banco.</span>
  </footer>
</div>

<dialog id="event-dialog">
  <div class="dialog-head">
    <h3>Evento <span class="mono" id="dialog-id"></span></h3>
    <button class="x" id="dialog-close" type="button" aria-label="Fechar">&times;</button>
  </div>
  <div class="dialog-body">
    <dl>
      <dt>Quando</dt><dd id="dialog-when">-</dd>
      <dt>Origem</dt><dd class="mono" id="dialog-source">-</dd>
      <dt>Isca</dt><dd id="dialog-honeypot">-</dd>
      <dt>Tipo</dt><dd id="dialog-type">-</dd>
      <dt>Severidade</dt><dd id="dialog-severity">-</dd>
      <dt>Metodo</dt><dd class="mono" id="dialog-method">-</dd>
      <dt>Caminho</dt><dd class="mono" id="dialog-path">-</dd>
      <dt>HTTP</dt><dd id="dialog-status">-</dd>
      <dt>User-Agent</dt><dd id="dialog-ua">-</dd>
      <dt>Detalhe</dt><dd id="dialog-detail">-</dd>
    </dl>
    <p class="dialog-note">Somente metadados minimos. Nenhum corpo, query string, senha ou payload e armazenado.</p>
  </div>
</dialog>

<script>
const REFRESH_MS = __REFRESH_MS__;
const state = { paused: false, severity: "all", search: "", data: null };

const SEVERITY_LABEL = { critical: "critica", high: "alta", medium: "media", low: "baixa" };
const STATUS_LABEL = {
  pending: "pendente", blocked: "bloqueado", allowed: "permitido",
  ignored: "ignorado", allowlisted: "allowlist"
};
const TYPE_LABEL = {
  attack_tool: "ferramenta de ataque", injection_attempt: "injecao",
  credential_attempt: "credencial", config_attempt: "configuracao",
  auth_failure: "falha de auth", honeypot_probe: "sondagem",
  probe: "probe", connection: "conexao", request: "requisicao"
};

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}
function fmtTime(iso) {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return String(iso).slice(11, 19);
  return date.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
function fmtHour(iso) {
  const date = new Date(iso);
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}
function fmtBytes(bytes) {
  if (typeof bytes !== "number" || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes, index = 0;
  while (value >= 1024 && index < units.length - 1) { value /= 1024; index += 1; }
  return value.toFixed(index === 0 ? 0 : 1) + " " + units[index];
}
function plural(count, singular, plural) {
  return count === 1 ? singular : plural;
}

function setConnection(ok, detail) {
  const pill = document.getElementById("conn-pill");
  pill.classList.toggle("live", ok);
  pill.classList.toggle("down", !ok);
  document.getElementById("conn-dot").className = "dot " + (ok ? "live" : "down");
  setText("conn-label", ok ? "ao vivo" : "sem conexao");
  const banner = document.getElementById("banner");
  if (ok) {
    banner.classList.remove("show");
    banner.textContent = "";
  } else {
    banner.classList.add("show");
    banner.textContent = "Falha ao atualizar o dashboard" + (detail ? ": " + detail : "") + ". Tentando novamente...";
  }
}

function render(data) {
  state.data = data;
  state.severity = state.severity === "high" ? "high" : state.severity;
  setText("version", data.app.version);
  setText("mode-label", data.app.mode);
  setText("runtime-label", data.app.runtime);
  const modePill = document.getElementById("mode-pill");
  modePill.className = "pill mode-" + data.app.mode;
  setText("runtime-label", data.app.runtime);
  const agent = data.agent;
  setText("agent-label", agent.running ? "agente ativo" + (agent.pid ? " (pid " + agent.pid + ")" : "") : "agente parado");
  document.getElementById("agent-dot").className = "dot " + (agent.running ? "live" : "down");
  document.getElementById("agent-pill").classList.toggle("live", !!agent.running);

  const stats = data.stats;
  setText("kpi-events", stats.events_total);
  setText("kpi-24h", stats.events_24h);
  setText("kpi-ips", stats.suspects_total);
  setText("kpi-pending", stats.pending);
  setText("kpi-events-hint", stats.events_total ? "spool processado no banco local" : "nenhuma interacao coletada");
  setText("kpi-ips-hint", stats.suspects_total + " na lista de ban");

  renderEvents();
  renderSuspects();
  renderTimeline();
  renderTypes();
  renderHoneypots();
  renderWarnings();

  setText("db-meta", data.database.exists ? fmtBytes(data.database.size_bytes) : "ausente");
  setText("spool-meta", data.spool.exists ? fmtBytes(data.spool.size_bytes) : "ausente");
}

function filteredEvents() {
  const events = (state.data && state.data.events) || [];
  const term = state.search.trim().toLowerCase();
  return events.filter(function (event) {
    if (state.severity === "high" && event.severity !== "high" && event.severity !== "critical") return false;
    if (state.severity === "medium" && event.severity !== "medium") return false;
    if (!term) return true;
    return [event.source_ip, event.event_type, event.path, event.honeypot_id, event.user_agent, event.detail]
      .join(" ").toLowerCase().includes(term);
  });
}

function renderEvents() {
  const body = document.getElementById("event-rows");
  body.replaceChildren();
  const events = filteredEvents();
  setText("events-count", events.length + "/" + ((state.data && state.data.events.length) || 0));
  for (const event of events) {
    const row = node("tr", "clickable");
    row.addEventListener("click", function () { openEvent(event.event_id); });
    row.appendChild(node("td", "", fmtTime(event.timestamp_utc)));
    row.appendChild(node("td", "ip", event.source_ip));
    row.appendChild(node("td", "", event.honeypot_id));
    row.appendChild(node("td", "type", TYPE_LABEL[event.event_type] || event.event_type));
    const severityCell = node("td");
    const badge = node("span", "sev sev-" + event.severity, SEVERITY_LABEL[event.severity] || event.severity);
    severityCell.appendChild(badge);
    row.appendChild(severityCell);
    row.appendChild(node("td", "path mono", event.path || event.method || "-"));
    body.appendChild(row);
  }
  document.getElementById("events-empty").hidden = events.length > 0;
}

function renderSuspects() {
  const list = document.getElementById("suspect-list");
  list.replaceChildren();
  const suspects = (state.data && state.data.suspects) || [];
  setText("suspects-count", suspects.length);
  for (const suspect of suspects) {
    const row = node("div", "suspect");
    const who = node("div", "who");
    const ip = node("div", "ip mono", suspect.source_ip);
    ip.style.cursor = "pointer";
    ip.title = "filtrar eventos deste IP";
    ip.addEventListener("click", function () {
      state.search = suspect.source_ip;
      document.getElementById("search").value = suspect.source_ip;
      renderEvents();
    });
    who.appendChild(ip);
    who.appendChild(node("div", "meta", (suspect.last_path || "-") + " | " + fmtTime(suspect.last_seen)));
    const side = node("div", "side");
    const status = node("span", "status status-" + suspect.status, STATUS_LABEL[suspect.status] || suspect.status);
    side.appendChild(status);
    const hits = node("span", "hits", suspect.hits + " " + plural(suspect.hits, "hit", "hits") + " | " + (SEVERITY_LABEL[suspect.max_severity] || suspect.max_severity));
    side.appendChild(hits);
    row.appendChild(who);
    row.appendChild(side);
    list.appendChild(row);
  }
  document.getElementById("suspects-empty").hidden = suspects.length > 0;
}

function renderTimeline() {
  const container = document.getElementById("timeline");
  container.replaceChildren();
  const series = (state.data && state.data.timeline) || [];
  const max = Math.max(1, ...series.map(function (item) { return item.count; }));
  const total = series.reduce(function (sum, item) { return sum + item.count; }, 0);
  setText("timeline-total", total + " " + plural(total, "evento", "eventos"));
  series.forEach(function (item, index) {
    const wrap = node("div", "bar-wrap");
    wrap.title = fmtHour(item.hour_utc) + " - " + item.count + " " + plural(item.count, "evento", "eventos");
    const bar = node("div", "bar" + (item.count === 0 ? " zero" : ""));
    bar.style.height = item.count === 0 ? "3px" : Math.max(6, Math.round((item.count / max) * 100)) + "%";
    wrap.appendChild(bar);
    const tick = node("div", "tick", index % 6 === 0 ? fmtHour(item.hour_utc) : "");
    wrap.appendChild(tick);
    container.appendChild(wrap);
  });
}

function renderTypes() {
  const container = document.getElementById("type-list");
  container.replaceChildren();
  const types = (state.data && state.data.stats.types) || {};
  const entries = Object.entries(types);
  setText("types-empty", "Sem dados para distribuir.");
  const max = Math.max(1, ...entries.map(function (entry) { return entry[1]; }));
  for (const entry of entries) {
    const row = node("div", "type-row");
    row.appendChild(node("span", "name", TYPE_LABEL[entry[0]] || entry[0]));
    const track = node("div", "track");
    const fill = node("div", "fill");
    fill.style.width = Math.max(4, Math.round((entry[1] / max) * 100)) + "%";
    track.appendChild(fill);
    row.appendChild(track);
    row.appendChild(node("span", "n", String(entry[1])));
    container.appendChild(row);
  }
  document.getElementById("types-empty").hidden = entries.length > 0;
}

function renderHoneypots() {
  const container = document.getElementById("honeypot-list");
  container.replaceChildren();
  const honeypots = (state.data && state.data.honeypots) || [];
  setText("hp-count", honeypots.length);
  for (const hp of honeypots) {
    const card = node("div", "hp");
    const first = node("div", "row");
    first.appendChild(node("span", "name", hp.id));
    first.appendChild(node("span", hp.running ? "up" : "down", hp.running ? "ATIVO" : "parado"));
    card.appendChild(first);
    card.appendChild(node("span", "endpoint", hp.endpoint));
    card.appendChild(node("span", "proto", hp.protocol + " | " + hp.profile));
    container.appendChild(card);
  }
  document.getElementById("honeypots-empty").hidden = honeypots.length > 0;
}

function renderWarnings() {
  const list = document.getElementById("warning-list");
  list.replaceChildren();
  const warnings = (state.data && state.data.warnings) || [];
  for (const warning of warnings) list.appendChild(node("li", "", warning));
}

async function openEvent(eventId) {
  try {
    const response = await fetch("/api/events/" + encodeURIComponent(eventId), { cache: "no-store" });
    if (!response.ok) return;
    const data = await response.json();
    const event = data.event;
    setText("dialog-id", event.event_id);
    setText("dialog-when", fmtTime(event.timestamp_utc));
    setText("dialog-source", event.source_ip + (event.source_port ? ":" + event.source_port : ""));
    setText("dialog-honeypot", event.honeypot_id + " (" + event.profile + "/" + event.protocol + ")");
    setText("dialog-type", TYPE_LABEL[event.event_type] || event.event_type);
    setText("dialog-severity", SEVERITY_LABEL[event.severity] || event.severity);
    setText("dialog-method", event.method || "-");
    setText("dialog-path", event.path || "-");
    setText("dialog-status", event.status || "-");
    setText("dialog-ua", event.user_agent || "-");
    setText("dialog-detail", event.detail || "-");
    document.getElementById("event-dialog").showModal();
  } catch (error) {
    console.warn("evento indisponivel", error);
  }
}

async function refresh() {
  if (state.paused) return;
  try {
    const response = await fetch("/api/summary", { cache: "no-store" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    render(await response.json());
    setConnection(true);
  } catch (error) {
    setConnection(false, error && error.message ? error.message : "");
  }
}

document.querySelectorAll("[data-sev]").forEach(function (button) {
  button.addEventListener("click", function () {
    state.severity = button.dataset.sev;
    document.querySelectorAll("[data-sev]").forEach(function (other) {
      other.classList.toggle("active", other === button);
    });
    renderEvents();
  });
});
document.getElementById("search").addEventListener("input", function (event) {
  state.search = event.target.value;
  renderEvents();
});
document.getElementById("pause").addEventListener("click", function (event) {
  state.paused = !state.paused;
  event.target.classList.toggle("active", state.paused);
  event.target.textContent = state.paused ? "retomar" : "pausar";
  if (!state.paused) refresh();
});
document.getElementById("dialog-close").addEventListener("click", function () {
  document.getElementById("event-dialog").close();
});
document.getElementById("event-dialog").addEventListener("click", function (event) {
  if (event.target === event.currentTarget) event.currentTarget.close();
});

setInterval(function () {
  setText("clock", new Date().toLocaleTimeString("pt-BR"));
}, 1000);
setInterval(refresh, REFRESH_MS);
refresh();
</script>
</body>
</html>
"""
