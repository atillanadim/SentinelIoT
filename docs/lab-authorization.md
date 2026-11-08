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
- Internet a partir da VM de laboratório.
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
