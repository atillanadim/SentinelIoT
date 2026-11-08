# Relatório da Fase 0

**Data:** 2026-11-08
**Ambiente de desenvolvimento:** Windows 11 Home 10.0.26200, x86_64
**Runtime planejado:** VM Linux dedicada com rede host-only

## 1. Objetivo

Preparar o ambiente, criar o repositório, documentar a arquitetura e reduzir
incertezas antes de implementar o honeypot.

## 2. Entregáveis

- Repositório Git local com estrutura inicial.
- `README.md` com escopo, avisos e instruções.
- Arquitetura, modelo de ameaças e plano de testes.
- 12 ADRs e índice de decisões.
- Configuração de exemplo sem segredos.
- Projeto Python 3.11.16 com dependências fixadas.
- Smoke test e ferramentas de qualidade.
- Topologia de laboratório documentada.
- Modelo de autorização de laboratório.

## 3. Comandos executados

```powershell
uv venv --python 3.11
uv add --bounds exact pydantic PyYAML psutil
uv add --dev --bounds exact pytest pytest-cov ruff mypy types-PyYAML pip-audit
uv export --format requirements.txt --no-hashes --no-emit-project -o requirements.lock
uv sync --frozen --dry-run
uv sync --frozen
uv run pytest
uv run ruff check .
uv run mypy src
uv run pip-audit
docker info --format '{{.ServerVersion}}'
docker run --rm hello-world
```

## 4. Resultados reais

- Python: 3.11.16.
- `uv sync --frozen --dry-run`: 49 pacotes, nenhuma alteração.
- `pytest`: 1 teste aprovado.
- `ruff`: nenhuma violação.
- `mypy`: nenhum erro em 11 arquivos.
- `pip-audit`: nenhuma vulnerabilidade conhecida; o projeto local não existe no
  PyPI e não foi auditado.
- Docker Desktop: servidor 29.9.2; `hello-world` executado com sucesso.
- Lockfile de requisitos gerado.

O Docker Desktop foi parado após a validação para liberar recursos. Ele não é o
runtime oficial do laboratório.

## 5. O que não foi feito

- Nenhum honeypot foi criado.
- Nenhum agente funcional foi criado.
- Nenhum banco de eventos foi criado.
- Nenhuma regra de firewall foi alterada.
- Nenhuma rede host-only foi criada.
- Nenhuma VM Linux foi provisionada.
- Nenhum dispositivo real foi acessado.
- Nenhuma varredura foi executada.

## 6. Limitações

- A validação do Docker no Windows não homologa o laboratório Linux.
- A VM Linux e a rede host-only continuam pendentes.
- O workflow de CI foi criado, mas não executado por falta de remote autenticado.
- A licença não foi definida.
- As metas de desempenho ainda não foram medidas.

## 7. Critério de saída

A Fase 0 está concluída no que se refere a repositório, documentação, toolchain
e validação do Docker no host. O provisionamento da VM Linux é pré-requisito
para a Fase 1 e depende de autorização específica.

## 8. Próxima fase

Fase 1 — Honeypot isolado: criar a imagem Docker mínima, o perfil
`camera_simulator`, a rede interna, os limites de recursos e os testes de
isolamento na VM Linux.
