@echo off
setlocal
rem Launcher para caminhos com caracteres nao-ASCII no Windows.
rem O uv grava o caminho do projeto em um arquivo .pth que o Python 3.11
rem le com o encoding do sistema; por isso usamos PYTHONPATH explicitamente.
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
set "PYTHONIOENCODING=utf-8"
uv run python -m sentineliot %*
exit /b %ERRORLEVEL%
