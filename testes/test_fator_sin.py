"""Fator medio de emissao do SIN (MCTI): leitura da planilha e produto versionado."""

import pandas as pd
import pytest

import etapa15_fator_sin as etapa
from coleta import comum_coleta as cc
from comum import config


def _presente():
    return bool(cc.ler_manifesto("mcti_fator")) and config.FATOR_SIN.exists()


@pytest.mark.skipif(not _presente(), reason="bruto ou produto ausente")
def test_bruto_bate_com_o_manifesto():
    caminho, linha = etapa.arquivo_atual()
    assert cc.sha256_arquivo(caminho) == linha["sha256"]
    assert linha["no_git"] == "sim"


@pytest.mark.skipif(not _presente(), reason="bruto ou produto ausente")
def test_produto_e_o_que_a_planilha_da():
    caminho, _ = etapa.arquivo_atual()
    lida = etapa.ler_planilha(caminho)
    gravada = pd.read_parquet(config.FATOR_SIN)
    pd.testing.assert_frame_equal(lida, gravada.drop(columns="arquivo_fonte"))


@pytest.mark.skipif(not _presente(), reason="bruto ou produto ausente")
def test_serie_comeca_em_2006_sem_buraco_e_com_valores_conhecidos():
    serie = pd.read_parquet(config.FATOR_SIN).set_index("mes")
    assert serie.index.min() == "2006-01"
    assert serie.index.is_unique
    meses = pd.period_range("2006-01", serie.index.max(), freq="M").strftime("%Y-%m")
    assert list(serie.index) == list(meses)
    # tres celulas lidas a' mao na planilha de 2026-11
    assert serie.loc["2006-01", "fator_tco2_mwh"] == pytest.approx(0.0322)
    assert serie.loc["2012-11", "fator_tco2_mwh"] == pytest.approx(0.1247)
    assert serie.loc["2024-10", "fator_tco2_mwh"] == pytest.approx(0.1127)
    assert serie.loc["2014-06", "fator_anual_publicado_tco2_mwh"] == pytest.approx(0.1355)


def test_conferencia_registra_buraco_como_falha():
    serie = pd.DataFrame({"mes": ["2006-01", "2006-03"], "ano": [2006, 2006],
                          "fator_tco2_mwh": [0.03, 0.04],
                          "fator_anual_publicado_tco2_mwh": [None, None]})
    linhas, _ = etapa.conferir(serie)
    assert linhas[0]["falhas"] == 1 and "2006-02" in linhas[0]["observacao"]
