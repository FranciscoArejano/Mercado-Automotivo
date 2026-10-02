"""Fase 2: do rascunho adjudicado a' dimensao de classificacao.

Linhas construidas para as regras de precedencia e as validacoes; o ultimo
teste confere a dimensao versionada contra o painel versionado.
"""

import pandas as pd
import pytest

from comum import config, fase2


def _linha(**campos) -> pd.Series:
    base = {"marca": "M", "modelo": "X", "segmento": "automoveis", "vigencia_inicio": "2015-01",
            "vigencia_fim": "2020-12", "propulsao_oferecida": "flex", "carroceria": "hatch",
            "origem_producao": "nacional", "propulsao_apos_regras": "flex",
            "origem_apos_regras": "nacional", "procedencia_propulsao": "regra_fonte_forte",
            "procedencia_carroceria": "regra_fonte_forte", "procedencia_origem": "proposta",
            "decisao_por_regra": "", "decisao_humana": "", "regras_aplicadas": "",
            "pendencias": ""}
    base.update(campos)
    return pd.Series(base)


def test_precedencia_humana_regra_proposta():
    linha = _linha(propulsao_apos_regras="flex+hibrido_indefinido",
                   decisao_por_regra="propulsao_oferecida=flex+hibrido_indefinido; "
                                     "eletrificacao=parcial",
                   decisao_humana="origem_producao=importado")
    final = fase2.linha_final(linha)
    assert (final["origem_producao"], final["procedencia_origem"]) == ("importado", "humana")
    assert final["propulsao_na_vigencia"] == "flex+hibrido_indefinido"
    assert final["procedencia_propulsao"] == "regra_fonte_forte"
    assert final["eletrificacao_na_vigencia"] == "parcial"
    assert (final["carroceria"], final["procedencia_carroceria"]) == ("hatch", "regra_fonte_forte")


def test_pendente_mostra_a_proposta_original():
    linha = _linha(propulsao_oferecida="flex+mhev", propulsao_apos_regras="flex+mhev+phev",
                   procedencia_propulsao="pendente", pendencias="P3 nao decide: x")
    final = fase2.linha_final(linha)
    assert (final["propulsao_na_vigencia"], final["procedencia_propulsao"]) == ("flex+mhev",
                                                                                "pendente")


def test_ok_aceita_o_valor_depois_das_regras():
    linha = _linha(propulsao_oferecida="flex+mhev", propulsao_apos_regras="flex+mhev+phev",
                   procedencia_propulsao="pendente", decisao_humana="ok")
    final = fase2.linha_final(linha)
    assert final["propulsao_na_vigencia"] == "flex+mhev+phev"
    assert {final["procedencia_propulsao"], final["procedencia_origem"]} == {"humana"}


def test_decisao_aceita_o_nome_da_dimensao():
    assert fase2.ler_decisao("propulsao_na_vigencia=flex+hev") == {
        "propulsao_oferecida": "flex+hev"}
    final = fase2.linha_final(_linha(decisao_humana="propulsao_na_vigencia=flex+hev"))
    assert (final["propulsao_na_vigencia"], final["eletrificacao_na_vigencia"]) == (
        "flex+hev", "parcial")
    assert "propulsao_oferecida" not in final and "eletrificacao" not in final


def test_recusa_pendente_em_linha_com_decisao_humana():
    linha = _linha(procedencia_propulsao="pendente", decisao_humana="origem_producao=ambos")
    with pytest.raises(fase2.DecisaoInvalida, match="pendente"):
        fase2.linha_final(linha)


@pytest.mark.parametrize("texto", ["dividir em 2018-03", "acho que e' nacional",
                                   "origem_producao=chinesa", "propulsao_oferecida=flex+vapor",
                                   "cor=azul", "vigencia_fim=2018"])
def test_decisao_que_a_fase_2_nao_aplica_sozinha(texto):
    with pytest.raises(fase2.DecisaoInvalida):
        fase2.ler_decisao(texto)


def test_regra_move_a_vigencia():
    final = fase2.linha_final(_linha(decisao_por_regra="vigencia_inicio=2015-03",
                                     procedencia_origem="regra_fonte_forte"))
    assert (final["vigencia_inicio"], final["vigencia_ajustada_por"],
            final["vigencia_inicio_rascunho"]) == ("2015-03", "regra", "2015-01")


def test_nao_classificado_tem_linha_e_procedencia_propria():
    fora = pd.DataFrame([{"marca": "M", "modelo": "Y", "segmento": "automoveis",
                          "primeiro_mes": "2010-01", "ultimo_mes": "2012-06"}])
    dim = fase2.dimensao(pd.DataFrame([_linha()]), fora)
    y = dim[dim["modelo"] == "Y"].iloc[0]
    assert (y["vigencia_inicio"], y["vigencia_fim"], y["procedencia_origem"]) == (
        "2010-01", "2012-06", "nao_classificado")


def _painel(*linhas):
    return pd.DataFrame([{"marca": m, "modelo": n, "segmento": "automoveis", "mes_ref": mes,
                          "unidades": u} for m, n, mes, u in linhas])


def test_cobertura_acusa_buraco_sobreposicao_e_chave_sem_linha():
    dim = pd.DataFrame([
        {"marca": "M", "modelo": "X", "segmento": "automoveis", "vigencia_inicio": "2015-01",
         "vigencia_fim": "2016-12"},
        {"marca": "M", "modelo": "X", "segmento": "automoveis", "vigencia_inicio": "2016-06",
         "vigencia_fim": "2018-12"},
    ])
    painel = _painel(("M", "X", "2019-03", 5), ("M", "Z", "2015-01", 1), ("M", "X", "2015-02", 3))
    problemas = fase2.problemas_de_cobertura(dim, painel)
    assert any("sobrepoe" in p for p in problemas)
    assert any("M/X/automoveis: 1 meses" in p for p in problemas)
    assert any("M/Z/automoveis: chave do painel sem linha" in p for p in problemas)


def test_fidelidade_acusa_valor_de_regra_diferente_do_rascunho():
    rascunho = pd.DataFrame([_linha(decisao_por_regra="origem_producao=ambos",
                                    origem_apos_regras="ambos",
                                    procedencia_origem="regra_fonte_forte")])
    dim = fase2.dimensao(rascunho, pd.DataFrame(columns=["marca", "modelo", "segmento",
                                                         "primeiro_mes", "ultimo_mes"]))
    assert fase2.problemas_de_fidelidade(dim, rascunho) == []
    dim.loc[0, "origem_producao"] = "nacional"
    assert fase2.problemas_de_fidelidade(dim, rascunho)


def test_volume_por_procedencia_soma_o_painel():
    dim = fase2.dimensao(pd.DataFrame([_linha()]), pd.DataFrame(
        [{"marca": "M", "modelo": "Y", "segmento": "automoveis", "primeiro_mes": "2015-01",
          "ultimo_mes": "2015-12"}]))
    painel = _painel(("M", "X", "2016-01", 30), ("M", "Y", "2015-05", 10))
    volume = fase2.volume_por_procedencia(dim, painel).set_index(["atributo", "procedencia"])
    assert volume.loc[("origem", "proposta"), "pct_do_volume"] == 75.0
    assert volume.loc[("origem", "nao_classificado"), "pct_do_volume"] == 25.0


def test_montagem_com_fonte_igual_ao_rascunho_mes_a_mes():
    periodo = {"marca": "M", "modelo": "X", "segmento": "automoveis",
               "montagem_inicio": "2016-06", "montagem_fim": "2016-12", "montagem_local": "ckd"}
    rascunho = pd.DataFrame([periodo])
    assert fase2.problemas_de_montagem(pd.DataFrame([periodo]), rascunho) == []
    outro = pd.DataFrame([{**periodo, "montagem_fim": "2016-08"}])
    assert len(fase2.problemas_de_montagem(outro, rascunho)) == 4


def test_dimensao_versionada_cobre_o_painel_e_tem_procedencias_validas():
    if not config.CLASSIFICACAO.exists():
        pytest.skip("dimensao ainda nao gravada")
    dim = pd.read_parquet(config.CLASSIFICACAO)
    painel = pd.read_parquet(config.PAINEL, columns=fase2.CHAVE + ["mes_ref", "unidades"])
    assert fase2.problemas_de_cobertura(dim, painel) == []
    for coluna in ("procedencia_propulsao", "procedencia_carroceria", "procedencia_origem"):
        assert set(dim[coluna]) <= set(fase2.PROCEDENCIAS)
    montagem = pd.read_parquet(config.CLASSIFICACAO_MONTAGEM)
    assert fase2.problemas_de_cobertura(montagem, painel, "montagem_inicio", "montagem_fim") == []


def test_modelo_so_com_zeros_leva_os_meses_do_painel():
    fora = pd.DataFrame([{"marca": "M", "modelo": "Z", "segmento": "automoveis",
                          "primeiro_mes": "", "ultimo_mes": ""}])
    painel = _painel(("M", "Z", "2004-02", 0), ("M", "Z", "2004-07", 0))
    dim = fase2.dimensao(pd.DataFrame(columns=_linha().index), fora, painel)
    assert (dim.iloc[0]["vigencia_inicio"], dim.iloc[0]["vigencia_fim"]) == ("2004-02", "2004-07")
    sem = fase2.dimensao(pd.DataFrame(columns=_linha().index), fora)
    assert any("sem mes" in p for p in fase2.problemas_de_cobertura(sem, painel))
