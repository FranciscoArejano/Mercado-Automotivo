"""Taxas de entrada e saida, e o ruido de cadastro que as domina (rodada 2, sec.1).

O achado que manda nesta secao: **207 dos 647 modelos do painel somam 3.512
unidades em treze anos** -- 0,01% do volume -- e cada um deles conta como uma
entrada e uma saida. Sao registros avulsos, conversoes de encarrocador e erros
de cadastro da fonte: `FIAT/FIAT`, `FORD/ENGERAUTO SPARTAKUS`, `VW/ZILK`. Eles
respondem por 40% a 50% de toda a rotatividade medida.

Por isso as taxas saem sob **pisos de volume total do modelo no periodo**. O
piso entra no numerador e no denominador: restringe quem pode entrar ou sair
**e** quem conta como ativo. Nao filtra o painel -- a regra da Parte 0 continua
valendo, nada e' apagado --, so' decompoe a medida.

Nenhuma leitura substantiva de rotatividade deve sair da coluna "todos".
"""

from __future__ import annotations

import pandas as pd

CHAVE_MODELO = ["marca", "modelo", "segmento"]


def _sem_zero(serie: pd.Series) -> pd.Series:
    """Denominador com zero virando NaN, sem trocar o dtype.

    Ano sem nenhuma entrada ou saida da' denominador zero. `replace(0, pd.NA)`
    devolveria serie de objetos e o `.round()` seguinte estouraria.
    """
    return serie.where(serie != 0)


def volume_por_modelo(por_modelo: pd.DataFrame) -> pd.Series:
    """Volume total de cada modelo no periodo inteiro."""
    return por_modelo.groupby(CHAVE_MODELO)["unidades"].sum()


def pico_por_modelo(por_modelo: pd.DataFrame) -> pd.Series:
    """Maior venda mensal de cada modelo no periodo inteiro.

    Segunda familia de piso, e ela existe porque a primeira **nao e' neutra
    quanto a' longevidade**. Volume total e' venda mensal media vezes meses de
    vida, entao um piso sobre ele descarta preferencialmente modelo de vida
    curta -- que sao justamente os que contribuem com uma entrada e uma saida, a
    variavel que se quer medir. Um piso sobre o pico mensal nao tem esse vies:
    um modelo que vendeu 500 num mes so' passa, e um que vendeu 3 por mes
    durante dez anos nao.

    Se as conclusoes sobrevivem as duas familias de piso, elas nao sao artefato
    da escolha do piso.
    """
    return por_modelo.groupby(CHAVE_MODELO)["unidades"].max()


def distribuicao(volume: pd.Series, faixas) -> pd.DataFrame:
    """Quantos modelos e quantas unidades em cada faixa de volume total."""
    linhas = []
    total_modelos, total_unidades = len(volume), float(volume.sum()) or 1.0
    for inferior, superior in faixas:
        if superior is None:
            recorte = volume[volume >= inferior]
            rotulo = f"acima de {inferior - 1:,}".replace(",", ".")
        else:
            recorte = volume[(volume >= inferior) & (volume <= superior)]
            rotulo = (f"ate {superior:,}".replace(",", ".") if inferior <= 1
                      else f"{inferior:,} a {superior:,}".replace(",", "."))
        linhas.append({
            "faixa_de_volume": rotulo,
            "modelos": len(recorte),
            "pct_dos_modelos": round(100 * len(recorte) / total_modelos, 1),
            "unidades": int(recorte.sum()),
            "pct_das_unidades": round(100 * recorte.sum() / total_unidades, 3),
        })
    return pd.DataFrame(linhas)


def participacao_dos_pequenos(ciclos: pd.DataFrame, volume: pd.Series, piso: int) -> pd.DataFrame:
    """Quanto das entradas e saidas de cada ano vem de modelos ate' `piso` unidades."""
    if ciclos.empty:
        return pd.DataFrame()
    marcado = ciclos.copy()
    marcado["volume_total"] = [
        float(volume.get((linha.marca, linha.modelo, linha.segmento), 0.0))
        for linha in marcado.itertuples()
    ]
    marcado["pequeno"] = marcado["volume_total"] <= piso

    entradas = marcado[~marcado["censura_esquerda"]].assign(
        ano=lambda q: q["entrada"].str.slice(0, 4).astype(int))
    saidas = marcado[~marcado["censura_direita"]].assign(
        ano=lambda q: q["saida"].str.slice(0, 4).astype(int))

    tabela = pd.DataFrame({
        "entradas": entradas.groupby("ano").size(),
        f"entradas_ate_{piso}": entradas[entradas["pequeno"]].groupby("ano").size(),
        "saidas": saidas.groupby("ano").size(),
        f"saidas_ate_{piso}": saidas[saidas["pequeno"]].groupby("ano").size(),
    }).fillna(0).astype(int)
    tabela[f"pct_entradas_ate_{piso}"] = (
        100 * tabela[f"entradas_ate_{piso}"] / _sem_zero(tabela["entradas"])).round(0)
    tabela[f"pct_saidas_ate_{piso}"] = (
        100 * tabela[f"saidas_ate_{piso}"] / _sem_zero(tabela["saidas"])).round(0)
    return tabela.reset_index()


def acima_do_piso(quadro: pd.DataFrame, volume: pd.Series, piso: int) -> pd.DataFrame:
    """Restringe um quadro com chave de modelo aos modelos acima do piso."""
    if piso <= 0:
        return quadro
    mantidos = set(volume[volume > piso].index)
    if quadro.empty:
        return quadro
    chaves = list(zip(*(quadro[coluna] for coluna in CHAVE_MODELO)))
    return quadro[[chave in mantidos for chave in chaves]]
