"""Propulsao por ano: entrada e saida de cada tipo, nas leituras longa e curta.

Casos construidos para as regras (combustao pela vigencia; fonte datada antes do
PBE; PBE so' quando um ano com coluna mostrava o modelo sem o tipo; saida pela
primeira ausencia depois da ultima presenca; lacuna nao e' saida; versao de tipo
fora da vigencia nao prova ausencia); os ultimos testes conferem a tabela
versionada contra o painel e a dimensao versionados.
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
    """(ano, valor) -- uma versao por linha."""
    return pd.DataFrame([{**CHAVE, "ano": a, "ano_pbe": str(a), "valor_taxonomia": v}
                         for a, v in linhas],
                        columns=list(CHAVE) + ["ano", "ano_pbe", "valor_taxonomia"])


def _fontes(*linhas):
    return pd.DataFrame([{**CHAVE, "tipo_propulsao": t, "data_fonte": d, "tipo_data_fonte": k}
                         for t, d, k in linhas],
                        columns=list(CHAVE) + ["tipo_propulsao", "data_fonte",
                                               "tipo_data_fonte"])


def _tipos(vigencia, pbe=None, fontes=None, direcao=0):
    linhas = pa.tipos_da_vigencia(vigencia, pd.DataFrame([vigencia]),
                                  _pbe() if pbe is None else pbe,
                                  _fontes() if fontes is None else fontes, direcao)
    return {l["tipo"]: l for l in linhas}


def test_toro_o_hibrido_entra_no_ano_do_pbe_e_a_combustao_na_vigencia():
    pbe = _pbe((2016, "flex"), (2021, "diesel"), (2021, "flex"), (2025, "flex"),
               (2025, "diesel"), (2026, "hev"), (2026, "flex"), (2026, "diesel"))
    t = _tipos(_vig("flex+diesel+mhev"), pbe)
    assert (t["flex"]["entrada_longa"], t["mhev"]["entrada_longa"],
            t["mhev"]["fonte_temporal"]) == (2016, 2026, "pbe_ano")
    assert t["diesel"]["ultimo_ano_longo"] == t["diesel"]["ultimo_ano_curto"] == 2026


def test_marcador_antes_de_2021_nao_prova_ausencia():
    pbe = _pbe((2019, "gasolina"), (2020, "gasolina"), (2021, "phev"), (2021, "gasolina"))
    assert _tipos(_vig("gasolina+phev"), pbe)["phev"]["fonte_temporal"] == "vigencia_sem_datacao"


def test_fonte_datada_manda_sobre_o_pbe_e_plano_nao_conta():
    pbe = _pbe((2021, "gasolina"), (2022, "phev"), (2022, "gasolina"))
    assert _tipos(_vig("gasolina+phev"), pbe, _fontes(("phev", "2021-08", "lancamento"))
                  )["phev"]["entrada_longa"] == 2021
    t = _tipos(_vig("gasolina+phev"), pbe, _fontes(("phev", "2019", "plano")))["phev"]
    assert (t["entrada_longa"], t["fonte_temporal"]) == (2022, "pbe_ano")


def test_saida_longa_na_primeira_ausencia_e_curta_na_ultima_presenca():
    # XC40: gasolina e phev no PBE de 2021; em 2022 so' o eletrico
    pbe = _pbe((2021, "gasolina"), (2021, "phev"), (2021, "bev"), (2022, "bev"), (2023, "bev"))
    t = _tipos(_vig("gasolina+phev+bev", inicio="2018-06", fim="2024-03"), pbe)
    assert (t["gasolina"]["ultimo_ano_longo"], t["gasolina"]["ultimo_ano_curto"]) == (2022, 2021)
    assert t["gasolina"]["fonte_saida"] == "pbe"
    assert t["bev"]["ultimo_ano_longo"] == t["bev"]["ultimo_ano_curto"] == 2024


def test_fonte_de_fim_e_ausencia_e_presenca_datada_conta():
    # Outlander: phev produzido de 2014 a 2016; o PBE de 2021 o mostra sem phev
    fontes = _fontes(("phev", "2014", "producao"), ("phev", "2016", "presenca"))
    pbe = _pbe((2021, "gasolina"), (2021, "diesel"))
    t = _tipos(_vig("gasolina+diesel+phev", inicio="2007-06", fim="2022-12"), pbe,
               fontes)["phev"]
    assert (t["entrada_longa"], t["ultimo_ano_curto"], t["ultimo_ano_longo"]) == (
        2014, 2016, 2021)
    fim = _tipos(_vig("gasolina+bev", inicio="2018-01", fim="2024-12"), _pbe(),
                 _fontes(("gasolina", "2022", "fim")))["gasolina"]
    assert (fim["ultimo_ano_longo"], fim["ultimo_ano_curto"], fim["fonte_saida"]) == (
        2022, 2018, "fonte")


def test_tipo_que_some_e_volta_e_lacuna():
    pbe = _pbe((2021, "flex"), (2021, "diesel"), (2022, "flex"), (2023, "flex"),
               (2023, "diesel"))
    t = _tipos(_vig("flex+diesel"), pbe)["diesel"]
    assert t["ultimo_ano_longo"] == t["ultimo_ano_curto"] == 2026 and t["fonte_saida"] == ""


def test_versao_de_tipo_fora_da_vigencia_nao_prova_ausencia():
    # Tank 300: a vigencia diz hev; o PBE so' lista PHEV
    pbe = _pbe((2025, "phev"), (2026, "phev"))
    t = _tipos(_vig("hev", inicio="2025-05"), pbe)["hev"]
    assert t["ultimo_ano_curto"] == 2026


def test_modelo_so_eletrificado_entra_pela_vigencia():
    t = _tipos(_vig("hev", inicio="2006-05", fim="2021-02"), _pbe((2021, "hev")))
    assert (t["hev"]["entrada_longa"], t["hev"]["fonte_temporal"]) == (2006, "vigencia")


def test_defasagem_mede_so_casos_comparaveis():
    fontes = pd.DataFrame([
        {**CHAVE, "modelo": m, "tipo_propulsao": "hev", "data_fonte": d,
         "tipo_data_fonte": "lancamento"} for m, d in (("A", "2021"), ("B", "2022"),
                                                       ("C", "2017"))])
    casado = pd.DataFrame([{**CHAVE, "modelo": m, "ano_pbe": a, "valor_taxonomia": "hev"}
                           for m, a in (("A", "2022"), ("B", "2023"), ("C", "2021"))])
    tabela, direcao = pa.defasagem_pbe(fontes, casado)
    assert tabela.set_index("modelo")["diferenca"].to_dict() == {"A": 1, "B": 1, "C": 4}
    assert direcao == 1
    t = _tipos(_vig("flex+hev"), _pbe((2021, "flex"), (2023, "hev"), (2023, "flex")),
               direcao=1)["hev"]
    assert (t["entrada_longa"], t["entrada_curta"]) == (2022, 2023)


def _painel(*linhas):
    return pd.DataFrame([{**CHAVE, "mes_ref": m, "unidades": u} for m, u in linhas])


def test_tabela_anual_tem_uma_linha_por_vigencia_ano():
    dim = pd.DataFrame([_vig("gasolina", "2015-01", "2019-05", "pendente"),
                        _vig("hev", "2019-06", "2026-08")])
    tipos = pa.tabela_de_tipos(dim, _pbe().assign(marca="M"), _fontes())
    painel = _painel(("2018-03", 10), ("2019-02", 5), ("2019-07", 7), ("2020-01", 3))
    t = pa.anual(dim, tipos, painel).set_index(["vigencia_inicio", "ano"])
    assert t.loc[("2015-01", 2019), ["propulsao_no_ano", "unidades",
                                     "procedencia_propulsao"]].tolist() == [
        "gasolina", 5, "pendente"]
    assert t.loc[("2019-06", 2019), ["eletrificacao_no_ano", "unidades"]].tolist() == [
        "total", 7]
    assert pa.problemas(t.reset_index(), dim, tipos, painel) == []


def test_banda_tira_so_leve_e_so_mhev():
    tabela = pd.DataFrame([
        {"ano": 2025, "unidades": u, "propulsao_no_ano": p, "eletrificacao_no_ano": e,
         "propulsao_no_ano_curta": p, "eletrificacao_no_ano_curta": e}
        for u, p, e in ((50, "flex", "nenhuma"), (20, "flex+mhev", "parcial"),
                        (10, "flex+hibrido_indefinido", "parcial"),
                        (15, "flex+hev", "parcial"), (5, "bev", "total"))])
    b = pa.banda(tabela, _painel(("2025-12", 1))).set_index("leitura").loc["longa"]
    assert (b["piso"], b["teto"], b["teto_sem_mhev"], b["teto_estrito"]) == (5, 50, 30, 20)


@pytest.fixture(scope="module")
def versionados():
    if not config.CLASSIFICACAO_PROPULSAO_ANUAL.exists():
        pytest.skip("tabela anual ainda nao gravada")
    return (pd.read_parquet(config.CLASSIFICACAO_PROPULSAO_ANUAL),
            pd.read_parquet(config.CLASSIFICACAO),
            pd.read_csv(config.CLASSIFICACAO_PROPULSAO_TIPOS, keep_default_na=False),
            pd.read_parquet(config.PAINEL, columns=list(CHAVE) + ["mes_ref", "unidades"]))


def test_tabela_versionada_bate_com_painel_e_dimensao(versionados):
    tabela, dim, tipos, painel = versionados
    assert pa.problemas(tabela, dim, tipos, painel) == []
    assert set(tabela["fonte_temporal"]) <= set(pa.FONTES_TEMPORAIS) | {""}


def test_toro_compass_e_renegade_nao_sao_parciais_antes_do_hibrido(versionados):
    tabela = versionados[0].groupby(["marca", "modelo", "segmento", "ano"]).first()
    for chave, chegada in ((("FIAT", "TORO", "comerciais_leves"), 2026),
                           (("JEEP", "COMPASS", "automoveis"), 2022),
                           (("JEEP", "RENEGADE", "automoveis"), 2026)):
        assert tabela.loc[chave + (2018,), "eletrificacao_no_ano"] == "nenhuma"
        assert tabela.loc[chave + (chegada - 1,), "eletrificacao_no_ano"] == "nenhuma"
        assert tabela.loc[chave + (chegada,), "eletrificacao_no_ano"] == "parcial"
