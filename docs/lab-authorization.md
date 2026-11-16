# Autorização de laboratório

**Estado:** autorização registrada em conversa em 2026-11-08; assinatura formal
pendente se o laboratório for compartilhado com terceiros.

Este documento deve ser mantido fora do controle de versão se contiver dados
pessoais. Uma cópia assinada ou registrada deve existir antes de qualquer teste
em ambiente de terceiros.

## 1. Identificação

- Responsável pelo laboratório: Sora (responsável pelo host local)
- Organização: uso pessoal / laboratório próprio
- Contato: operador local
- Data de início: 2026-11-08
- Data de término: enquanto durar o desenvolvimento do MVP, sujeito a revisão
- Ambiente físico ou virtual: VM Linux dedicada em VirtualBox, no host Windows
  `desktop-2qnl9e4`

## 2. Escopo autorizado

- Rede/sub-rede de laboratório: `192.168.57.0/24` (host-only do VirtualBox)
- Faixa de IPs: `192.168.57.10` (sentinel-lab), `192.168.57.20` (attacker,
  futura), `192.168.57.1` (host/gateway host-only)
- VMs autorizadas: `sentinel-lab`; futura VM `attacker` somente se necessária
- Gateway/roteador de laboratório: host-only do VirtualBox, sem NAT
- Portas autorizadas: `8080/tcp` para a isca; `22/tcp` para SSH administrativo
  somente na rede host-only
- Testes permitidos: conexões controladas à isca, validação de isolamento,
  testes de persistência e de política em `observe`/`dry_run`
- Ferramentas permitidas: cliente HTTP, SSH, Docker, git, Python, uv e
  ferramentas de diagnóstico do sistema

## 3. Fora de escopo

- Rede doméstica de produção `192.168.1.0/24`.
- Dispositivos IoT reais.
- Redes de terceiros.
- Internet a partir da VM de laboratório (exceto a janela de provisionamento
  da emenda de 2026-11-09, seção 9).
- Varredura de portas em ativos não listados.
- Exploração de vulnerabilidades reais.
- Captura de credenciais reais.
- Alteração de regras de firewall fora da tabela do SentinelIoT.
- Uso do laboratório para atacar qualquer sistema fora do escopo acima.

## 4. Janela de execução

- Horário permitido: conforme disponibilidade do responsável
- Duração máxima: por sessão de desenvolvimento
- Responsável presente: sim, o operador local
- Procedimento de interrupção: desligar a VM e restaurar o snapshot; nenhuma
  alteração deve ser feita na rede doméstica

## 5. Snapshot e reversão

- Snapshot criado em: 2026-11-08
- Identificador do snapshot: `clean-os`
  (`077990be-a08d-47e5-b0eb-e0bca653df00`) e `toolchain-ready`
  (`c0d814a5-65db-462b-8b0d-efca1d042c5d`)
- Procedimento de restauração: `VBoxManage snapshot sentinel-lab restore <nome>`
- Responsável pela restauração: Sora
- Teste de restauração realizado em: 2026-11-08, nos dois snapshots

## 6. Dados e privacidade

- Dados coletados: metadados mínimos de conexão (IP, porta, serviço, tipo de
  evento, severidade, timestamp e identificadores técnicos)
- Retenção: 90 dias, sujeita a revisão
- Responsável pelo descarte: Sora
- Tratamento de dados pessoais: minimização, acesso local restrito, sem
  telemetria para nuvem
- Canal para solicitações: responsável pelo laboratório

## 7. Declaração

Declaro que sou responsável pelo ambiente listado, que os testes são autorizados
e que o escopo acima será respeitado. Entendo que o SentinelIoT é uma camada
complementar e que nenhum resultado deve ser interpretado como garantia de
segurança.

- Nome: Sora
- Assinatura: ______________________ (pendente)
- Data: 2026-11-08

## 8. Registro de testes

| Data | Teste | Autorizado por | Resultado | Evidência |
|---|---|---|---|---|
| 2026-11-08 | Criação da rede host-only `192.168.57.0/24` | Sora | Concluído | `VBoxManage list hostonlyifs` / `list dhcpservers` |
| 2026-11-08 | Criação do esqueleto da VM `sentinel-lab` | Sora | Concluído | `VBoxManage showvminfo sentinel-lab` |
| 2026-11-08 | Instalação do Ubuntu 24.04.5 | Sora | Concluído | `lsb_release -ds`; SHA-256 da ISO |
| 2026-11-08 | Provisionamento offline da toolchain | Sora | Concluído | `python3.11 --version`, `uv --version`, `docker info` |
| 2026-11-08 | Teste de isolamento (sem Internet / sem `192.168.1.0/24`) | Sora | Concluído | `ip route`, `getent hosts`, `curl` |
| 2026-11-08 | Snapshot limpo (`clean-os`) | Sora | Concluído | `VBoxManage snapshot list` |
| 2026-11-08 | Snapshot com toolchain (`toolchain-ready`) | Sora | Concluído | `VBoxManage snapshot list` |
| 2026-11-08 | Restauração de `clean-os` | Sora | Concluído | Sem Docker, uv, Python 3.11 ou projeto |
| 2026-11-08 | Restauração de `toolchain-ready` | Sora | Concluído | `pytest` 1 passed; `ruff`; `mypy`; `hello-world` |

## 9. Emenda 2026-11-09 — laboratório de pentest

Autorização adicional registrada em conversa com o responsável:

- **Novo escopo de rede:** `10.10.10.0/24` (LAB-LAN), `203.0.113.0/24`
  (LAB-WAN) e `192.168.57.0/24` (gerência host-only).
- **Alvo autorizado:** `10.10.10.10` (VM `sentinel-mint`, honeypot Docker).
  Nenhum outro endereço pode ser atacado.
- **Atacante autorizado:** VM `kali`, endereços `10.10.10.20` e
  `203.0.113.20`.
- **Testes autorizados:** reconhecimento com `nmap`, enumeração HTTP,
  tentativas controladas de login, tentativas de injeção contra o honeypot e
  demonstração de detecção/bloqueio pelo agente Sentinel.
- **Internet temporária:** autorizada via NIC4 em NAT no `sentinel-router`
  apenas para instalar pacotes e imagens. Deve ser desligada antes dos testes
  ofensivos. O roteador bloqueia `10.0.0.0/8`, `192.168.0.0/16`,
  `172.16.0.0/12` e `169.254.0.0/16` no forward, com exceção de
  `10.0.2.0/24` (gateway/DNS do NAT), impedindo acesso à rede real
  `192.168.1.0/24`.
- **Dados:** apenas metadados; senhas, corpos, query strings e payloads não
  são persistidos.
- **Interrupção:** desligar as VMs, desconectar a NIC4 (`setlinkstate4 off`) e
  restaurar o snapshot do laboratório.
- **Proibição mantida:** bridge para a rede doméstica e qualquer ataque fora de
  `10.10.10.0/24`.

- Nome: Sora
- Data: 2026-11-09
- Assinatura: ______________________ (pendente)

## 10. Emenda 2026-11-10 — honeypot de câmera IP + bloqueio no router

Autorização registrada em conversa com o responsável, seguindo o
`SentinelIoT_Lab_Guia_Agente.md` com OpenWrt 25.12.6.

- **Topologia (redes internas do VirtualBox, sem bridge):**
  - `lab-servidores` = `192.168.57.0/24` (LAN do router);
  - `lab-atacante` = `192.168.58.0/24` (WAN do router).
- **VMs autorizadas:** `router` (OpenWrt), `alvoDebian` (honeypot + agente) e
  `kali-linux-2025.4-virtualbox-amd64` (atacante).
- **Endereços:** router `192.168.57.1` (LAN) e `192.168.58.1` (WAN); Debian
  `192.168.57.10`; Kali `192.168.58.50`; IP de admin protegido `192.168.58.2`.
- **Portas do honeypot:** `23/tcp`, `80/tcp` e `554/tcp`, alcançáveis apenas a
  partir de `lab-atacante` através da regra de firewall
  `Atacante-para-honeypot`.
- **SSH:** Dropbear do router apenas na LAN (`192.168.57.1:22`, confirmado sem
  bind na WAN); SSH do Debian apenas em `lab-servidores`.
- **Bloqueio:** tabela nftables própria `inet sentinel`, nunca as regras do
  `fw4`, TTL padrão `900` s, escopo `192.168.58.0/24`, allowlist
  `192.168.58.1/32`, `192.168.58.2/32` e `192.168.57.0/24`, limite de 50
  bloqueios ativos. O agente inicia em `mode = "observe"`.
- **Fora de escopo:** `192.168.1.0/24` (rede doméstica), Internet a partir das
  VMs do lab, bridge para a rede física, câmeras e dispositivos reais.
- **NICs em bridge:** as NICs em bridge existentes (`router` NIC3 e
  `alvoDebian` NIC2, além da NIC2 do Kali) foram **desligadas**
  (`cableconnected off`) em 2026-11-10 e devem permanecer desligadas. Modo
  promíscuo = `deny` em todas as NICs do lab.
- **Consola do router:** o OpenWrt arranca com `ttylogin=0`, ou seja, acesso
  físico à janela da VM dá shell de root sem password. O isolamento depende de
  esse acesso ficar restrito ao host.
- **Snapshot:** `openwrt-base`, UUID `9bcb10c3-f87b-450e-ac10-ff200a50fffb`,
  tirado com o router desligado após a configuração do router (Parte 4 do
  guia). Reversão: `VBoxManage snapshot router restore openwrt-base`.
- **Interrupção:** desligar as VMs (`VBoxManage controlvm <vm> acpipowerbutton`),
  manter as NICs bridge desligadas e, se necessário, restaurar o snapshot.
- **Proibição mantida:** qualquer ataque fora de `192.168.58.0/24` e
  `192.168.57.0/24`, e qualquer tráfego para a rede real `192.168.1.0/24`.
- **Credenciais:** a password de root do OpenWrt não é versionada; deve ser
  guardada fora do repositório.

Evidência da configuração do router (verificações reais por consola série):

| Verificação | Comando | Resultado |
|---|---|---|
| LAN | `ip -o -4 a` | `br-lan 192.168.57.1/24` |
| WAN | `ip -o -4 a` | `eth1 192.168.58.1/24` |
| Rota padrão | `ip route` | ausente |
| SSH só na LAN | `netstat -lntp \| grep :22` | apenas `192.168.57.1:22` |
| Regra do honeypot | `nft list ruleset \| grep honeypot` | `ip daddr 192.168.57.10 tcp dport { 23, 80, 554 } jump accept_to_lan` |
| Regras pré-existentes | `uci show firewall` | 9 antes, 10 depois (só a nova) |
| Persistência | reboot + repetir | tudo mantido |

- Nome: Sora
- Data: 2026-11-10
- Assinatura: ______________________ (pendente)
