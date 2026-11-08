#requires -Version 5.1
<#
SentinelIoT - verificacao de pre-requisitos no Windows.
Este script apenas verifica ferramentas. Nao inicia Docker, nao altera firewall,
nao cria rede e nao modifica dados existentes.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Test-Tool {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Command
    )

    $found = Get-Command $Command -ErrorAction SilentlyContinue
    if ($null -eq $found) {
        Write-Host "[FALTA] $Name ($Command)" -ForegroundColor Yellow
        return $false
    }

    Write-Host "[OK]    $Name -> $($found.Source)" -ForegroundColor Green
    return $true
}

Write-Host "SentinelIoT - Fase 0 - verificacao de pre-requisitos (Windows)"
Write-Host ""

$missing = 0
if (-not (Test-Tool -Name "Git" -Command "git")) { $missing++ }
if (-not (Test-Tool -Name "uv" -Command "uv")) { $missing++ }
if (-not (Test-Tool -Name "Docker CLI" -Command "docker")) { $missing++ }

Write-Host ""
Write-Host "Versoes encontradas:"
& git --version
& uv --version
Write-Host "Python do projeto (venv):"
& uv run python --version
& docker --version

Write-Host ""
Write-Host "Runtime oficial: VM Linux dedicada com rede host-only."
Write-Host "Este host Windows e usado para edicao e testes rapidos."
Write-Host "Nenhuma alteracao de rede, firewall ou container foi feita por este script."

if ($missing -gt 0) {
    Write-Host ""
    Write-Host "Existem $missing ferramenta(s) ausente(s)." -ForegroundColor Yellow
    exit 1
}

exit 0
