"""Mapa explicito de sub-segmento para segmento (ESPEC.md sec.4, sec.9.6).

O informe marca a secao com um titulo ("AUTOMOVEIS", "COMERCIAIS LEVES"), mas
esse titulo nao e' confiavel: em Abr, Mai e Jun/2020 a fonte embutida sem
ToUnicode faz o 'O' de AUTOMOVEIS sair como 'I', o marcador nao casa e todos os
automoveis daquele mes cairiam em comerciais leves.

O nome do sub-segmento, esse sim, e' estavel e nao se repete entre segmentos.
Ele passa a ser a chave, com o marcador de secao como alternativa. A lista e'
explicita e versionada (config/sub_segmentos.csv): nome novo nao e' adivinhado.
"""

from __future__ import annotations

import csv
import unicodedata
from functools import lru_cache

from . import config
from .texto import normalizar_tipografia

CAMPOS = ["sub_segmento_fonte", "segmento", "observacao"]


def chave(nome: str) -> str:
    """Forma comparavel: sem acento, sem pontuacao, caixa alta."""
    simples = normalizar_tipografia(nome)
    simples = "".join(
        c for c in unicodedata.normalize("NFD", simples) if unicodedata.category(c) != "Mn"
    )
    return "".join(c for c in simples.upper() if c.isalnum() or c == " ").strip()


@lru_cache(maxsize=1)
def carregar() -> dict[str, str]:
    if not config.SUB_SEGMENTOS.exists():
        return {}
    with config.SUB_SEGMENTOS.open(encoding="utf-8", newline="") as fluxo:
        return {
            chave(linha["sub_segmento_fonte"]): normalizar_tipografia(linha["segmento"])
            for linha in csv.DictReader(fluxo)
            if normalizar_tipografia(linha.get("sub_segmento_fonte", ""))
        }


def segmento_de(sub_segmento: str) -> str | None:
    return carregar().get(chave(sub_segmento))
