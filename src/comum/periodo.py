"""Utilidades de periodo mensal (AAAA-MM)."""

from __future__ import annotations

import re
from datetime import date

_RE_MES = re.compile(r"^(\d{4})-(\d{2})$")

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "marco", 4: "abril", 5: "maio", 6: "junho",
    7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}


def partes(mes: str) -> tuple[int, int]:
    achado = _RE_MES.match(mes)
    if not achado:
        raise ValueError(f"mes fora do formato AAAA-MM: {mes!r}")
    ano, m = int(achado.group(1)), int(achado.group(2))
    if not 1 <= m <= 12:
        raise ValueError(f"mes invalido: {mes!r}")
    return ano, m


def para_indice(mes: str) -> int:
    """Numero sequencial de meses desde o ano 0. Facilita janelas e diferencas."""
    ano, m = partes(mes)
    return ano * 12 + (m - 1)


def de_indice(indice: int) -> str:
    ano, m = divmod(indice, 12)
    return f"{ano:04d}-{m + 1:02d}"


def intervalo(inicio: str, fim: str) -> list[str]:
    i, f = para_indice(inicio), para_indice(fim)
    if f < i:
        raise ValueError(f"periodo invertido: {inicio} > {fim}")
    return [de_indice(k) for k in range(i, f + 1)]


def para_data(mes: str) -> date:
    ano, m = partes(mes)
    return date(ano, m, 1)


def distancia(a: str, b: str) -> int:
    """Meses de a ate b (negativo se b for anterior)."""
    return para_indice(b) - para_indice(a)
