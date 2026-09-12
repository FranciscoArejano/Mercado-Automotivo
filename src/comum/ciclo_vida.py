"""Entrada, saida e pico de um modelo (ESPEC.md D3).

D3, na letra: "Ultimo mes em que o modelo atinge >= 5% do seu pico movel de 12
meses. Unidades posteriores continuam somando no volume, mas nao deslocam a
data."

Duas leituras cabem em "pico movel de 12 meses" e elas nao dao a mesma data.
O codigo nao escolhe por conta propria: implementa as duas, usa a que
config.PICO_MOVEL_MODO indicar (padrao `media_movel`) e a etapa de validacao
publica as duas lado a lado. Ver QUESTOES_ABERTAS.md, Q1.

- `media_movel`: pico = max_t( media das unidades na janela [t-11, t] ).
  Um mes isolado de pico nao define o patamar; e' a leitura que trata "movel"
  como suavizacao. Escala mensal, comparavel com unidades(t).
- `max_movel`:   pico = max_t( maior valor na janela [t-11, t] ), que para uma
  serie completa e' o pico global do modelo.

Meses sem informe (lacunas) entram como ausentes e sao excluidos da janela --
lacuna nao vira zero (sec.9.2). Meses com informe em que o modelo nao aparece
entram como zero: a fonte publicou aquele mes e nao listou o modelo. A ressalva
e' que as tabelas da fonte sao truncadas, entao "zero" quer dizer "abaixo do
corte de publicacao daquele mes"; a etapa 06 reporta esse corte mes a mes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CicloDeVida:
    entrada: str | None
    saida: str | None
    pico: float
    pico_mes: str | None
    unidades_totais: float
    meses_ativos: int
    censura_esquerda: bool
    censura_direita: bool
    limiar_usado: float


def pico_movel(serie: pd.Series, janela: int = 12, modo: str = "media_movel") -> float:
    """Pico da serie mensal, suavizado (ou nao) por janela movel de `janela` meses."""
    if serie.dropna().empty:
        return 0.0
    if modo == "max_movel":
        movel = serie.rolling(janela, min_periods=1).max()
    elif modo == "media_movel":
        movel = serie.rolling(janela, min_periods=1).mean()
    else:
        raise ValueError(f"modo de pico desconhecido: {modo!r}")
    return float(np.nanmax(movel.to_numpy(dtype="float64")))


def calcular(
    serie: pd.Series,
    limiar: float,
    primeiro_mes_amostra: str,
    ultimo_mes_amostra: str,
    janela: int = 12,
    modo: str = "media_movel",
) -> CicloDeVida:
    """`serie` indexada por AAAA-MM, ordenada, com NaN nos meses sem informe."""
    positivos = serie[serie.fillna(0) > 0]
    if positivos.empty:
        return CicloDeVida(None, None, 0.0, None, 0.0, 0, False, False, limiar)

    entrada = str(positivos.index[0])
    pico = pico_movel(serie, janela=janela, modo=modo)
    pico_mes = str(serie.idxmax()) if serie.notna().any() else None
    corte = limiar * pico

    acima = serie[serie.fillna(-1.0) >= corte]
    saida = str(acima.index[-1]) if not acima.empty else entrada

    return CicloDeVida(
        entrada=entrada,
        saida=saida,
        pico=pico,
        pico_mes=pico_mes,
        unidades_totais=float(serie.fillna(0).sum()),
        meses_ativos=int((serie.fillna(0) > 0).sum()),
        censura_esquerda=entrada == primeiro_mes_amostra,
        censura_direita=saida == ultimo_mes_amostra,
        limiar_usado=limiar,
    )


def grade(
    painel: pd.DataFrame,
    coluna_chave: list[str],
    meses: list[str],
    meses_com_informe: set[str],
) -> pd.DataFrame:
    """Serie mensal completa por modelo: 0 onde houve informe, NaN nas lacunas."""
    largo = (
        painel.pivot_table(
            index=coluna_chave, columns="mes_ref", values="unidades",
            aggfunc="sum", fill_value=0,
        )
        .reindex(columns=meses, fill_value=0)
        .astype("float64")
    )
    for mes in meses:
        if mes not in meses_com_informe:
            largo[mes] = np.nan
    return largo
