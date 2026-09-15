"""Cobertura da fonte e o piso que D5 pede (ESPEC.md D5, QUESTOES_ABERTAS.md Q2).

D5 manda medir primeiro e so' entao fixar o piso. Esta rodada entrega a medida e
uma **recomendacao**; o piso nao e' aplicado ao painel, porque filtrar destroi
informacao de forma irreversivel e a escolha e' de analise, nao de construcao.

O problema que o piso resolve: o corte de publicacao da fonte sobe ao longo da
serie -- mediana de 99 unidades em 2022 para 396 em 2026 nos automoveis -- e com
ele a cobertura cai. Series construidas sob truncamentos diferentes nao sao
comparaveis entre anos. Impor um piso **unico** a todos os anos devolve a
comparabilidade, ao custo do volume que fica de fora.

A recomendacao e' o piso que deixa a fracao coberta mais parecida entre os anos:
minimiza a amplitude (maior menos menor) da cobertura anual. O relatorio mostra
a tabela inteira, para que a escolha continue sendo do pesquisador.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PISOS_CANDIDATOS = (0, 1, 5, 10, 25, 50, 100, 150, 200, 300, 400, 500, 750, 1000)


def por_mes(painel: pd.DataFrame, totais: pd.DataFrame) -> pd.DataFrame:
    """Total do painel contra o total publicado, mes a mes e por segmento."""
    do_painel = (
        painel.groupby(["mes_ref", "segmento"], as_index=False)["unidades"].sum()
        .rename(columns={"mes_ref": "mes", "unidades": "total_painel"})
    )
    junto = totais.merge(do_painel, on=["mes", "segmento"], how="outer")
    junto["cobertura_pct"] = (100 * junto["total_painel"] / junto["total_publicado"]).round(3)
    junto["diferenca"] = junto["total_painel"] - junto["total_publicado"]
    junto["diferenca_pct"] = (100 - junto["cobertura_pct"]).round(3)
    return junto


def tendencia(cobertura: pd.DataFrame) -> pd.DataFrame:
    """Cobertura por ano e segmento, com a variacao entre o primeiro e o ultimo."""
    por_ano = cobertura.assign(ano=cobertura["mes"].str.slice(0, 4).astype(int))
    por_ano = por_ano.groupby(["ano", "segmento"], as_index=False).agg(
        total_painel=("total_painel", "sum"), total_publicado=("total_publicado", "sum"))
    por_ano["cobertura_pct"] = (
        100 * por_ano["total_painel"] / por_ano["total_publicado"]
    ).round(2)
    return por_ano


def deriva(por_ano: pd.DataFrame) -> pd.DataFrame:
    """Quanto a cobertura de cada segmento andou do primeiro ao ultimo ano."""
    linhas = []
    for segmento, bloco in por_ano.groupby("segmento"):
        bloco = bloco.sort_values("ano")
        primeiro, ultimo = bloco.iloc[0], bloco.iloc[-1]
        linhas.append({
            "segmento": segmento,
            "primeiro_ano": int(primeiro["ano"]),
            "cobertura_primeiro": primeiro["cobertura_pct"],
            "ultimo_ano": int(ultimo["ano"]),
            "cobertura_ultimo": ultimo["cobertura_pct"],
            "variacao_pp": round(ultimo["cobertura_pct"] - primeiro["cobertura_pct"], 2),
            "amplitude_pp": round(
                bloco["cobertura_pct"].max() - bloco["cobertura_pct"].min(), 2),
        })
    return pd.DataFrame(linhas)


def recomendar_piso(painel: pd.DataFrame, totais: pd.DataFrame) -> pd.DataFrame:
    """Para cada piso candidato, a cobertura anual resultante e o que se perde."""
    publicado_por_ano = (
        totais.assign(ano=totais["mes"].str.slice(0, 4).astype(int))
        .groupby("ano")["total_publicado"].sum()
    )
    volume_total = painel["unidades"].sum()
    linhas = []
    for piso in PISOS_CANDIDATOS:
        acima = painel[painel["unidades"] >= piso]
        por_ano = acima.groupby("ano")["unidades"].sum()
        fracao = (100 * por_ano / publicado_por_ano).dropna()
        if fracao.empty:
            continue
        linhas.append({
            "piso_unidades_mes": piso,
            "cobertura_min_pct": round(float(fracao.min()), 2),
            "cobertura_max_pct": round(float(fracao.max()), 2),
            "amplitude_pp": round(float(fracao.max() - fracao.min()), 2),
            "desvio_padrao_pp": round(float(fracao.std(ddof=0)), 3),
            "linhas_descartadas": int((painel["unidades"] < piso).sum()),
            "volume_descartado": int(volume_total - acima["unidades"].sum()),
            "volume_descartado_pct": round(
                100 * (volume_total - acima["unidades"].sum()) / volume_total, 3),
        })
    quadro = pd.DataFrame(linhas)
    if quadro.empty:
        return quadro
    quadro["recomendado"] = quadro["amplitude_pp"] == quadro["amplitude_pp"].min()
    return quadro


def zeros_fragis(
    largo: pd.DataFrame, ciclos: pd.DataFrame, cortes: pd.DataFrame, limiar: float
) -> pd.DataFrame:
    """Meses em que a ausencia do modelo pode estar escondendo valor relevante.

    Um zero e' fragil quando o corte de publicacao que se aplica **aquele
    modelo** naquele mes -- o do sub-segmento em que ele seria listado, ver
    `comum/truncamento.py` -- esta' acima do limiar de D3 do proprio modelo.
    Nesse caso o modelo poderia estar em cima do seu limiar e mesmo assim nao
    ser listado, e a data de saida passaria a ser determinada por pratica
    editorial da fonte, nao pelo mercado.
    """
    if ciclos.empty or cortes.empty:
        return pd.DataFrame()
    registros = []
    for _, ficha in ciclos.iterrows():
        chave = (ficha["marca"], ficha["modelo"], ficha["segmento"])
        if chave not in largo.index or chave not in cortes.index:
            continue
        serie = largo.loc[chave]
        do_modelo = cortes.loc[chave]
        limite = limiar * ficha["pico"]
        for mes in serie.index:
            if not (ficha["entrada"] <= mes <= ficha["saida"]):
                continue
            valor = serie.loc[mes]
            if not np.isfinite(valor) or valor > 0:
                continue
            corte = do_modelo.get(mes)
            if corte is None or not np.isfinite(corte) or corte <= limite:
                continue
            registros.append({
                "marca": ficha["marca"], "modelo": ficha["modelo"],
                "segmento": ficha["segmento"], "mes_ref": mes,
                "corte_publicacao": int(corte),
                "limiar_d3_do_modelo": round(limite, 1),
                "pico": round(ficha["pico"], 1),
            })
    return pd.DataFrame(registros)


def imunes_ao_corte(
    ciclos: pd.DataFrame, cortes: pd.DataFrame, limiar: float
) -> pd.DataFrame:
    """Modelos cujo limiar de D3 supera o corte em todo mes da propria janela.

    Nesses o corte de publicacao nao morde: se o modelo some da fonte, e' porque
    caiu abaixo do proprio limiar, nao porque a fonte parou de lista-lo.
    """
    if ciclos.empty or cortes.empty:
        return ciclos.assign(imune_ao_corte=False) if not ciclos.empty else ciclos
    marcados = []
    for _, ficha in ciclos.iterrows():
        chave = (ficha["marca"], ficha["modelo"], ficha["segmento"])
        limite = limiar * ficha["pico"]
        if chave not in cortes.index:
            marcados.append(False)
            continue
        janela = cortes.loc[chave]
        janela = janela[(janela.index >= ficha["entrada"]) & (janela.index <= ficha["saida"])]
        marcados.append(bool(limite > janela.max()) if len(janela) else False)
    return ciclos.assign(imune_ao_corte=marcados)
