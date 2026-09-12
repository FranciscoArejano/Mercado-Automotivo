"""Normalizacao estritamente tipografica (sec.4).

Nao normalizar acentos, nao uniformizar maiusculas, nao corrigir grafia.
O nome cru fica preservado em `nome_completo_fonte`.
"""

from __future__ import annotations

import re

# Espaco nao separavel, espaco fino, espaco de largura zero e variantes.
_ESPACOS_EXOTICOS = dict.fromkeys(
    map(ord, "\xa0             　"),
    " ",
)
_INVISIVEIS = dict.fromkeys(map(ord, "​‌‍﻿­"), None)
_ESPACOS_DUPLOS = re.compile(r"[ \t]{2,}")


def normalizar_tipografia(texto: str) -> str:
    """Colapsa espacos exoticos/duplicados e apara as pontas. Nada mais."""
    if texto is None:
        return ""
    limpo = texto.translate(_ESPACOS_EXOTICOS).translate(_INVISIVEIS)
    limpo = _ESPACOS_DUPLOS.sub(" ", limpo)
    return limpo.strip()


_NUMERO_BR = re.compile(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$|^-?\d+(,\d+)?$")


def eh_numero_br(token: str) -> bool:
    return bool(_NUMERO_BR.match(token))


def numero_br(token: str) -> float:
    """Converte '44.272' -> 44272.0 e '0,00' -> 0.0. Levanta ValueError se nao for."""
    token = normalizar_tipografia(token)
    if not eh_numero_br(token):
        raise ValueError(f"nao e' numero no formato brasileiro: {token!r}")
    return float(token.replace(".", "").replace(",", "."))
