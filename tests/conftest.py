"""Configuracao compartilhada dos testes.

Os testes que exigirem Docker, Linux ou firewall devem ser marcados e ignorados
quando o ambiente nao oferecer o recurso, em vez de simular sucesso.
"""

from __future__ import annotations
