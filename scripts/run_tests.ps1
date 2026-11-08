#requires -Version 5.1

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param([Parameter(Mandatory = $true)][scriptblock]$Command)

    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Comando falhou com codigo $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "SentinelIoT - qualidade e testes"
Invoke-Checked { uv run ruff check . }
Invoke-Checked { uv run mypy src }
Invoke-Checked { uv run pytest }
Write-Host "OK"
