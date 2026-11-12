"""SentinelIoT: defesa proativa de redes IoT por deception.

O pacote concentra a CLI, o runtime local das iscas, a coleta de interacoes e
o armazenamento SQLite. O bloqueio real de firewall permanece desabilitado por
padrao: as decisoes sobre IPs sao registradas para analise do administrador.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "s0ra"

__all__ = ["__author__", "__version__"]
