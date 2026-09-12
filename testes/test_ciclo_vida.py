"""Regra de saida D3 e censura."""

import numpy as np
import pandas as pd

from comum import ciclo_vida


def serie(valores, inicio="2014-01"):
    ano, mes = int(inicio[:4]), int(inicio[5:])
    indice = []
    for _ in valores:
        indice.append(f"{ano:04d}-{mes:02d}")
        mes += 1
        if mes == 13:
            ano, mes = ano + 1, 1
    return pd.Series(valores, index=indice, dtype="float64")


def test_saida_e_o_ultimo_mes_acima_do_limiar():
    # patamar de 1000, depois cauda longa e minuscula
    s = serie([1000] * 12 + [500, 200, 60, 40, 10, 5, 3, 2, 1, 1, 1, 1])
    ciclo = ciclo_vida.calcular(s, 0.05, s.index[0], s.index[-1], modo="max_movel")
    assert ciclo.pico == 1000.0
    assert ciclo.saida == "2015-03"          # ultimo mes com >= 50 unidades
    assert s.loc["2015-04"] == 40            # unidades posteriores existem...
    assert ciclo.unidades_totais == s.sum()  # ...e continuam somando no volume


def test_unidades_posteriores_nao_deslocam_a_data():
    s = serie([1000] * 12 + [10] * 12)
    a = ciclo_vida.calcular(s, 0.05, s.index[0], s.index[-1], modo="max_movel")
    s2 = s.copy()
    s2.iloc[-1] = 10
    b = ciclo_vida.calcular(s2, 0.05, s2.index[0], s2.index[-1], modo="max_movel")
    assert a.saida == b.saida == "2014-12"


def test_as_duas_leituras_de_pico_movel_podem_divergir():
    # um mes isolado de pico: a media movel amortece, o maximo movel nao
    s = serie([10] * 6 + [1000] + [10] * 6 + [4] * 6)
    media = ciclo_vida.pico_movel(s, modo="media_movel")
    maximo = ciclo_vida.pico_movel(s, modo="max_movel")
    assert maximo == 1000.0
    assert media < maximo
    por_media = ciclo_vida.calcular(s, 0.05, s.index[0], s.index[-1], modo="media_movel")
    por_max = ciclo_vida.calcular(s, 0.05, s.index[0], s.index[-1], modo="max_movel")
    assert por_media.saida != por_max.saida


def test_censura_e_marcada_nas_duas_pontas():
    s = serie([100] * 24)
    ciclo = ciclo_vida.calcular(s, 0.05, s.index[0], s.index[-1])
    assert ciclo.censura_esquerda and ciclo.censura_direita


def test_lacuna_nao_vira_zero():
    valores = [100.0] * 12
    s = serie(valores)
    s.iloc[5] = np.nan
    ciclo = ciclo_vida.calcular(s, 0.05, s.index[0], s.index[-1])
    assert ciclo.meses_ativos == 11
    assert ciclo.unidades_totais == 1100.0


def test_serie_vazia_nao_tem_ciclo():
    s = serie([0] * 12)
    ciclo = ciclo_vida.calcular(s, 0.05, s.index[0], s.index[-1])
    assert ciclo.entrada is None and ciclo.saida is None
