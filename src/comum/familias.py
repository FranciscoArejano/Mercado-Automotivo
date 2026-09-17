"""Familia de modelo, e o colapso de variante que a barra no nome nao ve.

Rodada 2, sec.3. O teste de agregacao por barra (`MARCA/A/B`) encontra tres
casos no painel inteiro e conclui que a fonte quase nao agrega. Esta' errado:
a planilha de controle traz `Pajero TR4` (7.519), `Pajero HPE` (4.800) e
`Pajero Full` (2.429) -- tres veiculos distintos -- e o painel traz uma unica
ficha `MITSUBISHI/PAJERO`, sem barra nenhuma. A agregacao e' **invisivel** para
aquele teste.

O que a enxerga e' **cardinalidade de familia**: agrupar os dois lados pela
primeira palavra do nome do modelo e comparar quantas entradas cada um tem. Ali
onde a planilha tem mais, houve colapso de variante.

A familia e' heuristica de busca, nao classificacao: serve para **apontar onde
olhar**, e o que sai dela vai para revisao humana, nunca para o painel.
"""

from __future__ import annotations

import pandas as pd

from .nomes import chave

# Palavras que sozinhas nao identificam familia nenhuma.
GENERICAS = {"NEW", "ALL", "GRAND", "THE"}


def familia(modelo: str) -> str:
    """Primeira palavra util do nome do modelo. 'PAJERO TR4' -> 'PAJERO'."""
    palavras = [p for p in chave(modelo).replace("/", " ").split(" ") if p]
    if not palavras:
        return ""
    # 'NEW FIESTA' e 'FIESTA' sao a mesma placa de nome em geracoes diferentes,
    # e para uma busca de colapso interessa que caiam juntas.
    if len(palavras) > 1 and palavras[0] in GENERICAS:
        return palavras[1]
    return palavras[0]


def cardinalidade(quadro: pd.DataFrame, coluna_marca: str, coluna_modelo: str,
                  coluna_unidades: str) -> pd.DataFrame:
    """Quantas entradas distintas cada (marca, familia) tem, e quanto somam."""
    if quadro.empty:
        return pd.DataFrame(columns=["marca", "familia", "variantes", "unidades", "nomes"])
    dados = quadro.copy()
    dados["marca_chave"] = dados[coluna_marca].map(chave)
    dados["familia"] = dados[coluna_modelo].map(familia)
    dados["modelo_chave"] = dados[coluna_modelo].map(chave)
    return (
        dados.groupby(["marca_chave", "familia"], as_index=False)
        .agg(variantes=("modelo_chave", "nunique"),
             unidades=(coluna_unidades, "sum"),
             nomes=("modelo_chave", lambda s: " | ".join(sorted(set(s)))))
        .rename(columns={"marca_chave": "marca"})
    )


def colapsos(do_painel: pd.DataFrame, da_planilha: pd.DataFrame) -> pd.DataFrame:
    """Familias em que a planilha tem mais variantes que o painel.

    Cada linha e' um candidato a colapso de variante -- um caso em que o painel
    traz uma ficha so' para o que a planilha tratava como dois ou mais veiculos.
    """
    junto = do_painel.merge(
        da_planilha, on=["marca", "familia"], how="outer",
        suffixes=("_painel", "_planilha"),
    )
    for coluna in ("variantes_painel", "variantes_planilha"):
        junto[coluna] = junto[coluna].fillna(0).astype(int)
    junto["variantes_a_mais_na_planilha"] = (
        junto["variantes_planilha"] - junto["variantes_painel"])
    apertados = junto[junto["variantes_a_mais_na_planilha"] > 0].copy()
    apertados["unidades_planilha"] = apertados["unidades_planilha"].fillna(0).astype(int)
    apertados["unidades_painel"] = apertados["unidades_painel"].fillna(0).astype(int)

    # Duas coisas diferentes caem neste filtro, e confundi-las inverte a leitura:
    #
    # - familia que o painel **tem**, com menos variantes: candidata a colapso.
    #   MITSUBISHI/PAJERO e' uma ficha de 35.283 unidades contra cinco variantes
    #   de 35.356 na planilha -- mesmo volume, particao diferente.
    # - familia que o painel **nao tem**: nao houve colapso nenhum, o modelo
    #   simplesmente nao esta' la'. BMW "Serie", Lamborghini, Changan. Isso e'
    #   truncamento ou ausencia de marca, medido na secao anterior.
    #
    # A proximidade de volume e' o que separa as duas: colapso preserva o
    # volume, truncamento o perde.
    apertados["mecanismo"] = "colapso de variante"
    apertados.loc[apertados["variantes_painel"] == 0, "mecanismo"] = "ausente do painel"
    proximo = (
        (apertados["variantes_painel"] > 0)
        & (apertados["unidades_planilha"] > 0)
        & ((apertados["unidades_painel"] - apertados["unidades_planilha"]).abs()
           <= 0.05 * apertados["unidades_planilha"])
    )
    apertados.loc[proximo, "mecanismo"] = "colapso de variante (volume confere)"

    return apertados.sort_values(
        ["variantes_a_mais_na_planilha", "unidades_planilha"], ascending=[False, False]
    )[[
        "marca", "familia", "mecanismo", "variantes_painel", "variantes_planilha",
        "variantes_a_mais_na_planilha", "nomes_painel", "nomes_planilha",
        "unidades_painel", "unidades_planilha",
    ]]
