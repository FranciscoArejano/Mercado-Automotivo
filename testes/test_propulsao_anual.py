"""Propulsao por ano: o ano de entrada de cada tipo e a tabela anual.

Casos construidos para as regras de entrada (combustao pela vigencia; fonte
datada antes do PBE; PBE so' quando um ano com coluna mostrava o modelo sem o
tipo; senao, sem datacao; modelo so' eletrificado pela vigencia) e para a
tabela; os ultimos testes conferem a tabela versionada contra o painel e a
dimensao versionados.
"""

import pandas as pd
import pytest

from comum import config, propulsao_anual as pa

CHAVE = {"marca": "M", "modelo": "X", "segmento": "automoveis"}


def _vig(propulsao, inicio="2016-01", fim="2026-08", procedencia="regra_fonte_forte"):
    return pd.Series({**CHAVE, "vigencia_inicio": inicio, "vigencia_fim": fim,
                      "propulsao_na_vigencia": propulsao,
                      "eletrificacao_na_vigencia": "", "procedencia_propulsao": procedencia})


def _pbe(*linhas):
    return pd.DataFrame([{**CHAVE, "ano": a, "valor_taxonomia": v} for a, v in linhas],
                        columns=list(CHAVE) + ["ano", "valor_taxonomia"])


def _fontes(*linhas):
    return pd.DataFrame([{**CHAVE, "tipo_propulsao": t, "data_fonte": d, "tipo_data_fonte": k}
                         for t, d, k in linhas],
                        columns=list(CHAVE) + ["tipo_propulsao", "data_fonte",
                                               "tipo_data_fonte"])


def test_toro_o_hibrido_entra_no_ano_do_pbe_e_a_combustao_na_vigencia():
    pbe = _pbe((2016, "flex"), (2021, "diesel"), (2025, "flex"), (2026, "hev"))
    e = pa.entradas(_vig("flex+diesel+hibrido_indefinido"), pbe, _fontes())
    assert e == {"flex": (2016, "vigencia"), "diesel": (2016, "vigencia"),
                 "hibrido_indefinido": (2026, "pbe_ano")}


def test_marcador_antes_de_2021_nao_prova_ausencia():
    # o PBE de 2020 lista o modelo sem versao hibrida, e o hibrido aparece em 2021
    pbe = _pbe((2019, "gasolina"), (2020, "gasolina"), (2021, "phev"))
    e = pa.entradas(_vig("gasolina+phev"), pbe, _fontes())
    assert e["phev"] == (2016, "vigencia_sem_datacao")


def test_fonte_datada_manda_sobre_o_pbe_e_plano_nao_conta():
    pbe = _pbe((2021, "gasolina"), (2022, "phev"))
    assert pa.entradas(_vig("gasolina+phev"), pbe, _fontes(("phev", "2021-08", "lancamento"))
                       )["phev"] == (2021, "fonte_datada")
    assert pa.entradas(_vig("gasolina+phev"), pbe, _fontes(("phev", "2019", "plano"))
                       )["phev"] == (2022, "pbe_ano")


def test_fonte_anterior_a_vigencia_entra_no_inicio_e_posterior_nao_vale():
    fontes = _fontes(("bev", "2013-10", "presenca"), ("hev", "2030", "lancamento"))
    e = pa.entradas(_vig("flex+hev+bev"), _pbe(), fontes)
    assert e["bev"] == (2016, "fonte_datada")
    assert e["hev"] == (2016, "vigencia_sem_datacao")


def test_ano_com_coluna_mas_sem_o_modelo_nao_data():
    # vigencia de 2022; o modelo so' aparece no PBE em 2023, ja' hibrido
    e = pa.entradas(_vig("gasolina+hev", inicio="2022-01"), _pbe((2023, "hev")), _fontes())
    assert e["hev"] == (2022, "vigencia_sem_datacao")


def test_modelo_so_eletrificado_entra_pela_vigencia():
    e = pa.entradas(_vig("hev", inicio="2006-05"), _pbe((2021, "hev")), _fontes())
    assert e == {"hev": (2006, "vigencia")}
    e = pa.entradas(_vig("hev+phev", inicio="2020-01"),
                    _pbe((2021, "hev"), (2021, "gasolina"), (2023, "phev")), _fontes())
    assert e == {"hev": (2020, "vigencia"), "phev": (2023, "pbe_ano")}


def test_hibrido_indefinido_e_mhev_contam_hev_e_mhev_do_pbe():
    pbe = _pbe((2021, "flex"), (2023, "mhev"))
    assert pa.entradas(_vig("flex+hibrido_indefinido"), pbe, _fontes()
                       )["hibrido_indefinido"] == (2023, "pbe_ano")


def _painel(*linhas):
    return pd.DataFrame([{**CHAVE, "mes_ref": m, "unidades": u} for m, u in linhas])


def test_tabela_anual_une_vigencias_do_ano_e_leva_a_procedencia_mais_fraca():
    dim = pd.DataFrame([_vig("gasolina", "2015-01", "2019-05", "pendente"),
                        _vig("hev", "2019-06", "2026-08")])
    entradas = pa.tabela_de_entradas(dim, _pbe().assign(ano_pbe="2021"), _fontes())
    painel = _painel(("2018-03", 10), ("2019-02", 5), ("2019-07", 7), ("2020-01", 3))
    t = pa.anual(dim, entradas, painel).set_index("ano")
    assert t.loc[2018, ["propulsao_no_ano", "eletrificacao_no_ano"]].tolist() == [
        "gasolina", "nenhuma"]
    assert t.loc[2019, ["propulsao_no_ano", "eletrificacao_no_ano", "unidades",
                        "procedencia_propulsao", "vigencias"]].tolist() == [
        "gasolina+hev", "parcial", 12, "pendente", "2015-01;2019-06"]
    assert t.loc[2020, "eletrificacao_no_ano"] == "total"
    assert pa.problemas(t.reset_index(), dim, painel) == []


def test_problemas_acusa_tipo_que_some_e_unidades_diferentes():
    dim = pd.DataFrame([_vig("flex+hev", "2015-01", "2017-12")])
    tabela = pd.DataFrame([
        {**CHAVE, "ano": 2016, "unidades": 5, "propulsao_no_ano": "flex+hev",
         "vigencias": "2015-01"},
        {**CHAVE, "ano": 2017, "unidades": 9, "propulsao_no_ano": "flex",
         "vigencias": "2015-01"}])
    painel = _painel(("2016-01", 5), ("2017-01", 8))
    erros = pa.problemas(tabela, dim, painel)
    assert any("some em 2017" in e for e in erros)
    assert any("unidades diferem" in e for e in erros)
    assert any("ultimo ano" in e for e in erros)


@pytest.fixture(scope="module")
def versionados():
    if not config.CLASSIFICACAO_PROPULSAO_ANUAL.exists():
        pytest.skip("tabela anual ainda nao gravada")
    return (pd.read_parquet(config.CLASSIFICACAO_PROPULSAO_ANUAL),
            pd.read_parquet(config.CLASSIFICACAO),
            pd.read_parquet(config.PAINEL, columns=list(CHAVE) + ["mes_ref", "unidades"]))


def test_tabela_versionada_bate_com_painel_e_dimensao(versionados):
    tabela, dim, painel = versionados
    assert pa.problemas(tabela, dim, painel) == []
    assert set(tabela["fonte_temporal"]) <= set(pa.FONTES_TEMPORAIS) | {""}


def test_toro_compass_e_renegade_nao_sao_parciais_antes_do_hibrido(versionados):
    tabela = versionados[0].set_index(["marca", "modelo", "segmento", "ano"])
    for chave, chegada in ((("FIAT", "TORO", "comerciais_leves"), 2026),
                           (("JEEP", "COMPASS", "automoveis"), 2022),
                           (("JEEP", "RENEGADE", "automoveis"), 2026)):
        assert tabela.loc[chave + (2018,), "eletrificacao_no_ano"] == "nenhuma"
        assert tabela.loc[chave + (chegada - 1,), "eletrificacao_no_ano"] == "nenhuma"
        assert tabela.loc[chave + (chegada,), "eletrificacao_no_ano"] == "parcial"
