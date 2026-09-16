"""A marca que a fonte atribui a um modelo, mes a mes.

O informe de Nov/2013 publica `PONTIAC/MONTANA` (3.901 unidades), `FORD/KOMBI`,
`VW/RANGER`, `FORD/MASTER`, `THINK/CITY` e `/ELANTRA` -- sem marca nenhuma. Nao
e' erro de leitura: sao palavras unicas no PDF, e o extrator as devolve como
estao. E' a **fonte** que trocou a coluna de marca naquela edicao.

O efeito no painel e' pior que um numero errado: cada troca cria uma marca
fantasma, com uma entrada e uma saida, e tira o volume da marca certa naquele
mes. Nada disso e' corrigido aqui -- a ESPEC sec.9.4 e' explicita: reportar e
seguir. O que esta' aqui e' a deteccao.

O teste usa a redundancia da propria serie: um nome de modelo aparece sob a
mesma marca em quase todos os meses. Quando um mes o publica sob outra, e' esse
mes que esta' errado, e o quanto ele destoa e' medida.
"""

from __future__ import annotations

import pandas as pd

MINIMO_MESES = 6          # so' opina sobre modelo com historico
DOMINIO_MINIMO = 0.9      # a marca dominante tem de mandar em 90% dos meses


def divergencias(painel: pd.DataFrame, coluna_marca: str = "marca",
                 coluna_modelo: str = "modelo") -> pd.DataFrame:
    """Meses em que um modelo aparece sob marca diferente da sua marca dominante."""
    if painel.empty:
        return pd.DataFrame()
    dados = painel[[coluna_marca, coluna_modelo, "segmento", "mes_ref", "unidades"]].copy()
    dados = dados.rename(columns={coluna_marca: "marca", coluna_modelo: "modelo"})

    por_mes = dados.groupby(["modelo", "segmento", "marca"], as_index=False).agg(
        meses=("mes_ref", "nunique"), unidades=("unidades", "sum"))
    total = por_mes.groupby(["modelo", "segmento"], as_index=False).agg(
        meses_totais=("meses", "sum"))
    junto = por_mes.merge(total, on=["modelo", "segmento"])
    junto["dominio"] = junto["meses"] / junto["meses_totais"]

    dominantes = (
        junto.sort_values("meses", ascending=False)
        .drop_duplicates(subset=["modelo", "segmento"])
        .query("meses_totais >= @MINIMO_MESES and dominio >= @DOMINIO_MINIMO")
        [["modelo", "segmento", "marca", "meses_totais", "dominio"]]
        .rename(columns={"marca": "marca_dominante", "dominio": "dominio_da_marca"})
    )
    if dominantes.empty:
        return pd.DataFrame()

    suspeitas = dados.merge(dominantes, on=["modelo", "segmento"])
    suspeitas = suspeitas[suspeitas["marca"] != suspeitas["marca_dominante"]]
    return suspeitas.sort_values("unidades", ascending=False)[[
        "mes_ref", "segmento", "modelo", "marca", "marca_dominante",
        "unidades", "meses_totais", "dominio_da_marca",
    ]]


def meses_afetados(divergentes: pd.DataFrame) -> pd.DataFrame:
    """Resumo por mes: quantos modelos destoam e quanto volume esta' em jogo."""
    if divergentes.empty:
        return pd.DataFrame()
    return (
        divergentes.groupby("mes_ref", as_index=False)
        .agg(modelos=("modelo", "nunique"), unidades=("unidades", "sum"),
             marcas_fantasma=("marca", "nunique"),
             exemplos=("modelo", lambda s: ", ".join(sorted(set(s))[:5])))
        .sort_values("unidades", ascending=False)
    )
