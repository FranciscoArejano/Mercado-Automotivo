"""Comercio exterior (Comex Stat): regras da tabela de NCMs e conferencias.

Casos construidos para as regras; os ultimos testes conferem o produto e a tabela
de NCMs versionados contra o bruto versionado.
"""

import hashlib
import csv

import pandas as pd
import pytest

from comum import comex, config


@pytest.mark.parametrize("ncm,grupo", [
    ("87032310", "centelha"), ("87033290", "diesel"), ("87034000", "hev"),
    ("87035000", "hev"), ("87036000", "phev"), ("87037000", "phev"), ("87038000", "bev"),
    ("87039000", "outros"), ("87031000", "outros"), ("87042110", "diesel"),
    ("87043190", "centelha"), ("87046000", "bev"), ("87049000", "outros")])
def test_grupo_pelo_texto_da_subposicao(ncm, grupo):
    assert comex.grupo_da_ncm(ncm) == grupo


@pytest.mark.parametrize("ncm,descricao,leve", [
    ("87042110", "Chassis com motor diesel e cabina, para carga <= 5 toneladas", "sim"),
    ("87043110", "de peso em carga máxima não superior a 5 toneladas", "sim"),
    ("87042210", "Chassis com motor diesel e cabina, 5 toneladas < carga <= 20 toneladas", "nao"),
    ("87043290", "Outros veículos automóveis com motor a explosão, carga > 5 toneladas", "nao"),
    ("87041010", "Dumpers para transporte de mercadoria", "nao"),
    ("87042290", "Outros com motor diesel, capacidade de carga entre 5 e 20 toneladas", "nao"),
    ("87042330", "frigoríficos com motor diesel, capacidade de carga maior que 20 toneladas",
     "nao"),
    ("87049000", "Outros veículos automóveis para transporte de mercadorias", "indeterminado"),
    ("87032310", "Automóveis com motor explosão", "")])
def test_leve_pela_descricao(ncm, descricao, leve):
    assert comex.leve_da_ncm(ncm, descricao) == leve


def test_antes_da_separacao_o_mes_e_sem_separacao():
    assert comex.grupo_no_mes("centelha", "2017-01", "2016-12") == "sem_separacao"
    assert comex.grupo_no_mes("centelha", "2017-01", "2017-01") == "centelha"


def _linhas(*itens, pais=True):
    return pd.DataFrame([{"fluxo": "importacao", "posicao": "8703", "ncm": n, "mes_ref": m,
                          "pais": p if pais else "", "fob_usd": v, "kg": v, "quantidade": v,
                          "descricao": "x"} for n, m, p, v in itens])


def test_conferencia_acusa_soma_sobre_paises_diferente():
    com = _linhas(("87038000", "2025-01", "China", 10), ("87038000", "2025-02", "Japao", 5))
    certo = _linhas(("87038000", "2025-01", "", 10), ("87038000", "2025-02", "", 5), pais=False)
    errado = _linhas(("87038000", "2025-01", "", 10), pais=False)
    assert (comex.conferencia_paises(com, certo)["quantidade_diferenca"] == 0).all()
    assert (comex.conferencia_paises(com, errado)["quantidade_diferenca"] != 0).any()


def test_meses_faltando_na_janela():
    com = _linhas(("87038000", "2025-01", "China", 1), ("87038000", "2025-03", "China", 1))
    falta = comex.meses_faltando(com, "2025-01", "2025-03")
    assert falta["mes_ref"].tolist() == ["2025-02"]


def test_ncm_que_so_existiu_antes_da_separacao_e_sem_separacao():
    com = _linhas(("87039000", "2010-01", "Japao", 1), ("87038000", "2017-02", "China", 1),
                  ("87032100", "2003-01", "Japao", 1))
    com.loc[2, "ncm"] = "87032990"  # codigo hipotetico que acaba antes de 2017
    tabela = comex.tabela_de_ncms(com, {}).set_index("ncm")
    assert tabela.loc["87038000", "separa_eletrificados_desde"] == "2017-02"
    assert tabela.loc["87032990", "grupo_propulsao_ncm"] == "sem_separacao"


@pytest.fixture(scope="module")
def versionados():
    if not config.COMEX_VEICULOS.exists():
        pytest.skip("comex ainda nao gravado")
    return (pd.read_parquet(config.COMEX_VEICULOS),
            pd.read_csv(config.NCM_VEICULOS, dtype=str, keep_default_na=False))


def test_bruto_bate_com_o_manifesto():
    with (comex.DIR / "manifesto.csv").open(encoding="utf-8", newline="") as fluxo:
        manifesto = list(csv.DictReader(fluxo))
    assert manifesto
    for linha in manifesto:
        conteudo = (comex.DIR / linha["arquivo"]).read_bytes()
        assert hashlib.sha256(conteudo).hexdigest() == linha["sha256"], linha["arquivo"]


def test_produto_e_tabela_batem_com_o_bruto(versionados):
    dados, ncms = versionados
    com_pais, sem_pais = comex.ler_bruto()
    assert len(dados) == len(com_pais)
    conferencia = comex.conferencia_paises(com_pais, sem_pais)
    assert (conferencia[["fob_usd_diferenca", "kg_diferenca",
                         "quantidade_diferenca"]] == 0).all().all()
    calculada = comex.tabela_de_ncms(com_pais, comex.unidades_das_ncms())
    assert set(calculada["ncm"]) == set(ncms["ncm"])
    assert set(ncms["grupo_propulsao_ncm"]) <= set(comex.GRUPOS)
    fora = set(ncms.loc[ncms["unidade_estatistica"] != comex.UNIDADE, "ncm"])
    assert dados.loc[dados["ncm"].isin(fora), "unidades"].isna().all()
