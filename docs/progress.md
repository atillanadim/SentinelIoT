# Progresso do projeto

**Fase atual:** 0 — Preparação e análise (concluída no host Windows; VM Linux pendente)
**Última atualização:** 2026-11-08

## 1. Decisões do responsável

- Fase 0 completa, incluindo validação do Docker.
- Runtime oficial: VM Linux dedicada, com paridade de produção desde o início.
- Licença: adiada; não criar `LICENSE` por enquanto.
- Python: 3.11.16.

## 2. Concluído

- Leitura integral da especificação mestre.
- Inspeção do ambiente Windows, ferramentas, rede, Docker, WSL e VirtualBox.
- Definição da arquitetura e da topologia de laboratório.
- Criação do repositório Git local e da estrutura inicial.
- Configuração do projeto Python 3.11 com dependências fixadas.
- Documentação inicial, modelo de ameaças, plano de testes e 12 ADRs.
- Smoke test, lint, tipagem e auditoria de dependências.
- Validação do Docker Desktop com `hello-world`.

## 3. Pendente

- Provisionar a VM Linux dedicada e a rede host-only (requer autorização).
- Executar o ambiente na VM e registrar evidências de isolamento.
- Iniciar a Fase 1: honeypot isolado em Docker.
- Definir licença antes de distribuição.

## 4. Fora de escopo nesta fase

- Honeypot funcional.
- Agente funcional.
- Banco de eventos.
- CLI funcional.
- Notificações.
- Adaptador de firewall.
- Qualquer alteração de firewall, rede ou dispositivo real.

## 5. Testes e evidências reais

Ambiente: Windows 11, Python 3.11.16 (uv), Docker Desktop 29.9.2.

| Verificação | Comando | Resultado |
|---|---|---|
| Python | `uv run python --version` | Python 3.11.16 |
| Dependências | `uv sync --frozen --dry-run` | 49 pacotes; nenhuma alteração |
| Sync real | `uv sync --frozen` | 49 pacotes checados; nenhuma alteração |
| Smoke test | `uv run pytest` | 1 passed em 0,26 s |
| Lint | `uv run ruff check .` | All checks passed |
| Tipagem | `uv run mypy src` | Success: no issues em 11 arquivos |
| Vulnerabilidades | `uv run pip-audit` | Nenhuma vulnerabilidade conhecida; projeto local não auditável no PyPI |
| Docker daemon | `docker info --format '{{.ServerVersion}}'` | 29.9.2 |
| Docker execução | `docker run --rm hello-world` | Hello from Docker! (sucesso) |
| Lockfile | `uv export --format requirements.txt --no-hashes --no-emit-project -o requirements.lock` | Arquivo gerado |

O Docker Desktop foi parado após a validação, para restaurar o estado inicial e
liberar memória. Ele não é o runtime oficial do laboratório.

## 6. Riscos em aberto

- VM Linux ainda não provisionada.
- RAM do host limitada no momento da inspeção (aprox. 1,9 GiB livres).
- Caminho com acento e diferenças de line ending.
- CI sem remote autenticado; workflow criado, não executado.
- Licença não definida.
- Necessidade de autorização formal do laboratório.
- Validação de rede interna do Docker e publicação de porta pendente para a Fase 1.

## 7. Próximo passo

Revisar a entrega da Fase 0. Com aprovação, provisionar a VM Linux dedicada e a
rede host-only. Só depois iniciar a Fase 1 (honeypot isolado em Docker).

## 8. Regra de evidência

Nenhuma tarefa será marcada como concluída sem comando reproduzível, saída real
e registro neste arquivo. Resultados de Docker no Windows não serão tratados
como homologação do laboratório Linux.
