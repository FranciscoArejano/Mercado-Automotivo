"""Visoes sobre o painel.

O painel guarda o sub-segmento **na linha**, fora da chave (QUESTOES_ABERTAS.md
Q4): quando a fonte publica o mesmo `(marca, modelo, segmento)` em dois
sub-segmentos no mesmo mes -- `NISSAN/VERSA` em "Sedans Pequenos" com a geracao
antiga e em "Sedans Compactos" com a nova --, as duas linhas ficam separadas.
E' a unica pista de geracao que a fonte oferece, e descartada nao volta.

A soma acontece aqui, na hora de olhar o modelo como serie unica. Quem precisa
da serie por modelo (D3, detectores da sec.5, taxas de entrada e saida) chama
`por_modelo`; quem precisa da geracao vai direto ao painel.
"""

from __future__ import annotations

import pandas as pd

CHAVE_MODELO = ["marca", "modelo", "segmento"]

_PRIMEIRO = (
    "grupo_economico", "grupo_mapeado", "houve_rebatismo", "data_rebatismo",
    "cadeia_rebatismo", "reclassificacao", "conta_entrada_saida",
)


def por_modelo(painel: pd.DataFrame) -> pd.DataFrame:
    """Soma os sub-segmentos: uma linha por (mes, marca, modelo, segmento)."""
    chaves = ["mes_ref", "ano", "mes", "data"] + CHAVE_MODELO
    agregacoes = {"unidades": ("unidades", "sum")}
    for coluna in _PRIMEIRO:
        if coluna in painel.columns:
            agregacoes[coluna] = (coluna, "max" if painel[coluna].dtype == bool else "first")
    if "sub_segmento_fonte" in painel.columns:
        agregacoes["sub_segmentos"] = (
            "sub_segmento_fonte", lambda s: "+".join(sorted({v for v in s if v})),
        )
    if "origem_tabela" in painel.columns:
        agregacoes["origem_tabela"] = (
            "origem_tabela", lambda s: "+".join(sorted({v for v in s if v})),
        )
    return painel.groupby(chaves, as_index=False).agg(**agregacoes)
