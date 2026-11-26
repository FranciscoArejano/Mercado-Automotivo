"""Emissoes por UF (SEEG): leitura, gas e unidade, conferencia do total Brasil."""

import pandas as pd
import pytest

import etapa16_emissoes as etapa
from comum import config


@pytest.mark.parametrize("fonte,gas,unidade", [
    ("CO2e (t) GWP-AR5", "CO2e_GWP_AR5", "t CO2e (GWP-AR5)"), ("CO2 (t)", "CO2", "t"),
    ("CF4 (PFC-14) (t)", "CF4 (PFC-14)", "t"), ("HFC-134a (t)", "HFC-134a", "t")])
def test_gas_e_unidade(fonte, gas, unidade):
    assert etapa.gas_e_unidade(fonte) == (gas, unidade)


def test_construir_soma_as_colunas_finas_e_separa_o_nao_alocado():
    base = {"Emissão/Remoção/Bunker": "Emissão", "Gás": "CO2e (t) GWP-AR5",
            "Setor de emissão": "Energia", "Categoria emissora": "Transportes",
            "Sub-categoria emissora": "Rodoviário", "Produto ou sistema": "Diesel de petróleo",
            "Detalhamento": "x", "Recorte": "y", "Atividade geral": "z", "Bioma": "b"}
    dados = pd.DataFrame([dict(base, Estado="São Paulo", Bioma="Cerrado", **{"2024": 1.0}),
                          dict(base, Estado="São Paulo", Bioma="Mata Atlântica",
                               **{"2024": 2.0}),
                          dict(base, Estado="Não Alocado", **{"2024": 5.0})])
    produto = etapa.construir(dados)
    sp = produto[produto["uf"] == "SP"]
    assert len(sp) == 1 and sp["valor"].iloc[0] == 3.0
    assert produto[produto["estado_fonte"] == "Não Alocado"]["uf"].isna().all()


@pytest.mark.skipif(not config.EMISSOES_UF_ANUAL.exists(), reason="produto ausente")
def test_produto_versionado_confere_com_o_total_do_seeg():
    produto = pd.read_parquet(config.EMISSOES_UF_ANUAL)
    linhas, comparacao = etapa.conferir(produto, etapa.ler_reduzido("serie_historica"))
    assert sum(l["falhas"] for l in linhas) == 0
    assert set(comparacao["setor"]) == set(etapa.SETORES) | {"Total Geral"}
    assert produto["colecao_seeg"].unique().tolist() == ["14.0"]
    assert produto["ano"].min() == 2003


@pytest.mark.skipif(not config.EMISSOES_UF_ANUAL.exists(), reason="produto ausente")
def test_produto_e_o_que_o_reduzido_da():
    gravado = pd.read_parquet(config.EMISSOES_UF_ANUAL)
    refeito = etapa.construir(etapa.ler_reduzido("dados"))
    pd.testing.assert_frame_equal(gravado, refeito)
