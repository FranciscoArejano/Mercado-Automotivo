"""Onde a fonte corta a cauda, e quanto isso morde (QUESTOES_ABERTAS.md I3, Q5).

A truncagem da Fenabrave nao e' um piso de unidades: e' **numero fixo de linhas
por sub-segmento**. "Suv's" traz exatamente 40 modelos em todos os 151 meses
medidos; "Furgoes", 7; "Sedans Grandes", 12; "Sports", 9. Sub-segmento que tem
menos modelos que o teto -- Monocab, Sw Grandes -- nao trunca nada.

Disso sai a medida certa do corte de publicacao:

- um bloco esta' **no teto** quando o numero de linhas iguala o maior que aquele
  sub-segmento ja' mostrou;
- num bloco no teto, o corte e' o **menor valor listado ali**: qualquer modelo
  abaixo disso teria ficado de fora;
- bloco fora do teto nao corta nada, e o corte e' zero.

Isso substitui a leitura ingenua de "menor valor publicado no mes", que mede o
tamanho do menor modelo da fonte inteira, nao a truncagem. E funciona em todo o
periodo, inclusive nos anos recentes, em que a fonte deixou de publicar a linha
`Total` de cada sub-segmento e a cauda nao pode mais ser medida por diferenca.
"""

from __future__ import annotations

import pandas as pd

CHAVE_BLOCO = ["mes_ref", "segmento", "sub_segmento_fonte"]


def _padronizar(bruto: pd.DataFrame) -> pd.DataFrame:
    colunas = {"segmento_fonte": "segmento", "marca_fonte": "marca", "modelo_fonte": "modelo"}
    return bruto.rename(columns={k: v for k, v in colunas.items() if k in bruto.columns})


def por_bloco(bruto: pd.DataFrame) -> pd.DataFrame:
    """Corte de publicacao de cada bloco (mes x segmento x sub-segmento)."""
    dados = _padronizar(bruto)
    dados = dados[
        (dados["origem_tabela"] == "sub_segmento") & (dados["sub_segmento_fonte"] != "")
    ]
    if dados.empty:
        return pd.DataFrame(columns=CHAVE_BLOCO + ["linhas", "teto", "no_teto", "corte"])
    blocos = dados.groupby(CHAVE_BLOCO, as_index=False).agg(
        linhas=("unidades", "size"), menor_listado=("unidades", "min"))
    blocos["teto"] = blocos.groupby("sub_segmento_fonte")["linhas"].transform("max")
    blocos["no_teto"] = blocos["linhas"] == blocos["teto"]
    blocos["corte"] = blocos["menor_listado"].where(blocos["no_teto"], 0)
    return blocos


def por_modelo_e_mes(bruto: pd.DataFrame, meses: list[str]) -> pd.DataFrame:
    """Corte que se aplica a cada modelo em cada mes, pelo sub-segmento dele.

    Modelo ausente do mes herda o sub-segmento que ocupou por ultimo (ou o
    primeiro que vier a ocupar, no comeco da serie): e' a melhor informacao
    disponivel sobre onde ele teria sido listado.
    """
    dados = _padronizar(bruto)
    dados = dados[
        (dados["origem_tabela"] == "sub_segmento") & (dados["sub_segmento_fonte"] != "")
    ]
    if dados.empty:
        return pd.DataFrame()
    chave = ["marca", "modelo", "segmento"]
    onde = (
        dados.sort_values("mes_ref")
        .drop_duplicates(subset=chave + ["mes_ref"], keep="last")
        .pivot_table(index=chave, columns="mes_ref", values="sub_segmento_fonte",
                     aggfunc="first")
        .reindex(columns=meses)
        .ffill(axis=1)
        .bfill(axis=1)
    )
    blocos = por_bloco(bruto)
    mapa = {
        (linha.mes_ref, linha.segmento, linha.sub_segmento_fonte): linha.corte
        for linha in blocos.itertuples()
    }
    cortes = pd.DataFrame(index=onde.index, columns=meses, dtype="float64")
    for mes in meses:
        segmentos = onde.index.get_level_values("segmento")
        cortes[mes] = [
            mapa.get((mes, segmento, sub), 0.0) if isinstance(sub, str) else 0.0
            for segmento, sub in zip(segmentos, onde[mes])
        ]
    return cortes


def resumo_anual(blocos: pd.DataFrame) -> pd.DataFrame:
    """Quanto a truncagem morde, ano a ano."""
    if blocos.empty:
        return blocos
    com_ano = blocos.assign(ano=blocos["mes_ref"].str.slice(0, 4).astype(int))
    return (
        com_ano.groupby(["ano", "segmento"], as_index=False)
        .agg(
            blocos=("no_teto", "size"),
            blocos_no_teto=("no_teto", "sum"),
            corte_mediano=("corte", lambda s: float(s[s > 0].median()) if (s > 0).any() else 0.0),
            corte_maximo=("corte", "max"),
        )
        .round(1)
    )


def edicoes_abreviadas(bruto: pd.DataFrame, fracao_minima: float = 0.5) -> pd.DataFrame:
    """Meses em que a fonte publicou uma edicao curta do informe.

    A tabela por modelo tem 17 sub-segmentos no informe normal. Duas edicoes da
    serie -- 2003-10 (Ed. 10) e 2005-03 (Ed. 27) -- sairam com 10 paginas em vez
    de 44 e trazem **um** sub-segmento: ali o painel e' carregado quase inteiro
    pelo ranking mensal, que nao tem sub-segmento nem cauda. O total do mes
    continua batendo com o publicado -- o ranking cobre o topo --, mas o elenco
    de modelos fica pela metade, e um modelo que vende pouco some por um mes sem
    ter saido do mercado.

    Nao se conserta nada aqui (sec.9.4): mede-se e reporta-se. O mes fica no
    painel como a fonte o publicou.
    """
    dados = _padronizar(bruto)
    por_mes = dados.groupby("mes_ref").agg(
        linhas_total=("unidades", "size"),
        linhas_sub_segmento=("origem_tabela", lambda s: int((s == "sub_segmento").sum())),
    )
    sub_por_mes = (
        dados[dados["origem_tabela"] == "sub_segmento"]
        .groupby("mes_ref")["sub_segmento_fonte"].nunique()
        .rename("sub_segmentos")
    )
    quadro = por_mes.join(sub_por_mes).fillna({"sub_segmentos": 0})
    quadro["sub_segmentos"] = quadro["sub_segmentos"].astype(int)
    if quadro.empty:
        return quadro.reset_index()
    tipico = int(quadro["sub_segmentos"].median())
    quadro["sub_segmentos_tipicos"] = tipico
    quadro["fracao_do_tipico"] = (quadro["sub_segmentos"] / tipico).round(3) if tipico else 1.0
    reconstruidos = set(
        dados.loc[dados["origem_tabela"] == "mes_anterior", "mes_ref"].unique()
    )
    quadro["situacao"] = [
        "mes recuperado do informe seguinte" if mes in reconstruidos
        else "edicao curta do informe"
        for mes in quadro.index
    ]
    abreviadas = quadro[quadro["fracao_do_tipico"] < fracao_minima]
    return abreviadas.reset_index().sort_values("mes_ref")
