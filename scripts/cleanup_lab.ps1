#requires -Version 5.1
<#
Remove apenas caches locais do projeto. Dados de eventos so sao removidos com
-IncludeData. Este script nao remove containers, volumes, regras de firewall,
redes ou arquivos fora do repositorio.
#>

[CmdletBinding()]
param(
    [switch]$IncludeData
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$targets = @(
    (Join-Path $root ".pytest_cache"),
    (Join-Path $root ".mypy_cache"),
    (Join-Path $root ".ruff_cache"),
    (Join-Path $root "htmlcov"),
    (Join-Path $root ".coverage")
)

if ($IncludeData) {
    $targets += (Join-Path $root "data")
}

foreach ($target in $targets) {
    if (Test-Path $target) {
        Write-Host "Removendo $target"
        Remove-Item -Recurse -Force $target
    }
}

Get-ChildItem -Path $root -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Host "Removendo $($_.FullName)"
        Remove-Item -Recurse -Force $_.FullName
    }

Write-Host "Limpeza concluida. Nenhum recurso de Docker ou firewall foi alterado."
