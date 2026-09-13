"""Mapa datado de grupo economico (ESPEC.md D4).

Duas chaves de vendedor: `marca` e `grupo_economico`. O mapa e' *datado*: cada
linha de config/mapa_grupos.csv vale de `vigencia_inicio` a `vigencia_fim`
(vazio = em aberto). Stellantis so' existe a partir de 2021-01; antes disso FCA
e PSA sao grupos separados. Propriedade nunca e' aplicada para tras (sec.9.5).

Marca sem linha vigente no mes recebe 'NAO_MAPEADO' e entra no relatorio.
Nao ha' heuristica de fallback: adivinhar dono e' decisao metodologica.
"""

from __future__ import annotations

import csv
from functools import lru_cache

from . import config, periodo
from .texto import normalizar_tipografia

NAO_MAPEADO = "NAO_MAPEADO"
CAMPOS = ["marca_fonte", "grupo_economico", "vigencia_inicio", "vigencia_fim",
          "fonte", "observacao"]


@lru_cache(maxsize=1)
def carregar() -> tuple[dict, ...]:
    if not config.MAPA_GRUPOS.exists():
        return ()
    linhas = []
    with config.MAPA_GRUPOS.open(encoding="utf-8", newline="") as fluxo:
        for bruta in csv.DictReader(fluxo):
            marca = normalizar_tipografia(bruta.get("marca_fonte", "")).upper()
            grupo = normalizar_tipografia(bruta.get("grupo_economico", ""))
            if not marca or not grupo:
                continue
            inicio = normalizar_tipografia(bruta.get("vigencia_inicio", "")) or config.FONTE_PRIMEIRO_MES
            fim = normalizar_tipografia(bruta.get("vigencia_fim", ""))
            linhas.append({
                "marca": marca,
                "grupo": grupo,
                "inicio": periodo.para_indice(inicio),
                "fim": periodo.para_indice(fim) if fim else None,
                "fonte": normalizar_tipografia(bruta.get("fonte", "")),
            })
    return tuple(linhas)


def grupo_de(marca: str, mes: str) -> str:
    """Grupo economico vigente para a marca naquele mes."""
    alvo = normalizar_tipografia(marca).upper()
    indice = periodo.para_indice(mes)
    for linha in carregar():
        if linha["marca"] != alvo:
            continue
        if indice < linha["inicio"]:
            continue
        if linha["fim"] is not None and indice > linha["fim"]:
            continue
        return linha["grupo"]
    return NAO_MAPEADO


def marcas_mapeadas() -> set[str]:
    return {linha["marca"] for linha in carregar()}


def grupo_vigente(marca: str, mes: str) -> tuple[str, bool]:
    """Grupo economico do mes, com marca nao mapeada virando grupo unitario.

    Para indice de concentracao, marca sem linha vigente **nao** pode cair num
    balde `NAO_MAPEADO` comum nem sumir do calculo: as duas coisas distorcem o
    HHI em direcoes opostas. Ela entra como grupo de uma marca so', com o
    proprio nome. O segundo valor devolvido diz se o mapa cobria o caso, para
    que o relatorio conte quantas sao e quanto volume representam.
    """
    grupo = grupo_de(marca, mes)
    if grupo == NAO_MAPEADO:
        return normalizar_tipografia(marca).upper(), False
    return grupo, True
