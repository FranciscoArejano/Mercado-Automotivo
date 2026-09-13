"""Indices de concentracao, e a armadilha do mapa datado.

Agrupar marcas so' pode **aumentar** o HHI: para uma particao fixa,
`sum (a+b)^2 = sum a^2 + sum b^2 + 2ab >= sum a^2 + sum b^2`. Logo
`hhi_grupo >= hhi_marca` e' identidade -- **desde que a particao seja a mesma
para todas as observacoes somadas**.

Num painel anual com mapa de propriedade datado ela nao e'. Em 2014 a FIAT
aparece no grupo `FIAT` de janeiro a setembro e no grupo `FCA` de outubro em
diante: o volume anual da marca se parte em dois grupos, e o HHI de grupo pode
ficar **abaixo** do de marca. Foi exatamente o que aconteceu -- 1.169,5 contra
1.317,4, o unico ano da serie que inverte, e os unicos tres casos sao FIAT,
JEEP e DODGE, cuja propriedade muda em outubro de 2014.

Dai as duas leituras oferecidas aqui:

- `mensal`: dentro de um mes a particao e' fixa, entao a identidade vale e pode
  ser exigida. E' o teste de sanidade.
- `anual com particao fixa`: o grupo de cada marca e' o vigente num **mes de
  referencia** declarado (o ultimo mes do ano no painel). A identidade volta a
  valer, ao custo de atribuir o ano inteiro ao dono do fim do ano.
"""

from __future__ import annotations

import pandas as pd

from . import grupos


def hhi(bloco: pd.DataFrame, chave: str, coluna: str = "unidades") -> float:
    """Herfindahl-Hirschman em pontos (0 a 10.000)."""
    total = bloco[coluna].sum()
    if total <= 0:
        return float("nan")
    partes = bloco.groupby(chave)[coluna].sum() / total
    return float(partes.pow(2).sum() * 10_000)


def grupo_na_referencia(painel: pd.DataFrame, mes_referencia: str) -> pd.Series:
    """Grupo de cada marca segundo um unico mes -- particao fixa.

    A atribuicao sai do proprio painel, do que ele registra naquele mes, e nao
    de uma releitura do mapa: assim qualquer variante de agrupamento aplicada ao
    painel (teste de robustez, sobreposicao por artigo) e' respeitada aqui.
    Marca ausente do mes de referencia cai no mapa datado.
    """
    do_mes = painel.loc[painel["mes_ref"] == mes_referencia]
    mapa = dict(zip(do_mes["marca"], do_mes["grupo_economico"]))
    for marca in painel["marca"].unique():
        if marca not in mapa:
            mapa[marca] = grupos.grupo_vigente(marca, mes_referencia)[0]
    return painel["marca"].map(mapa)


def por_ano(painel: pd.DataFrame) -> pd.DataFrame:
    """HHI de marca e de grupo por ano, com particao de grupo fixa no ano."""
    linhas = []
    for ano, bloco in painel.groupby("ano"):
        referencia = max(bloco["mes_ref"])
        fixo = bloco.assign(grupo_fixo=grupo_na_referencia(bloco, referencia))
        marcas_que_mudam = (
            bloco.groupby("marca")["grupo_economico"].nunique().pipe(lambda s: s[s > 1]).index
        )
        linhas.append({
            "ano": int(ano),
            "mes_referencia_do_grupo": referencia,
            "hhi_marca": round(hhi(bloco, "marca"), 1),
            "hhi_grupo_particao_fixa": round(hhi(fixo, "grupo_fixo"), 1),
            "hhi_grupo_datado": round(hhi(bloco, "grupo_economico"), 1),
            "marcas_que_mudam_de_grupo_no_ano": len(marcas_que_mudam),
            "volume_dessas_marcas": int(
                bloco.loc[bloco["marca"].isin(marcas_que_mudam), "unidades"].sum()
            ),
        })
    return pd.DataFrame(linhas)


def por_mes(painel: pd.DataFrame) -> pd.DataFrame:
    """HHI mensal. Dentro do mes a particao e' fixa: a identidade tem de valer."""
    linhas = []
    for mes, bloco in painel.groupby("mes_ref"):
        marca = hhi(bloco, "marca")
        grupo = hhi(bloco, "grupo_economico")
        linhas.append({
            "mes_ref": mes,
            "hhi_marca": round(marca, 1),
            "hhi_grupo": round(grupo, 1),
            "diferenca": round(grupo - marca, 1),
        })
    return pd.DataFrame(linhas)
