"""Regras de adjudicacao: P1, P2, P3 (propulsao), O1, O2, O3 (origem) e montagem.

Linhas e versoes construidas; os nomes de modelo lembram os casos reais que
motivaram cada regra ou guarda, mas os dados aqui sao do teste.
"""

import pandas as pd

from comum import adjudicacao as adj
from comum import validacao_classificacao as validacao

CORTE = 2016


def _linha(**campos) -> pd.Series:
    base = {"posicao": 10, "marca": "M", "modelo": "X", "segmento": "automoveis",
            "vigencia_inicio": "2003-01", "vigencia_fim": "2026-08",
            "propulsao_oferecida": "flex", "origem_producao": "nacional",
            "confianca_origem": "media", "observacao": "", "pbe_situacao": "diverge",
            "pbe_diferenca": "", "pbe_anos": "", "pbe_nota": "", "unidades_na_vigencia": 1000}
    base.update(campos)
    return pd.Series(base)


def _versoes(*linhas) -> pd.DataFrame:
    """(ano, valor, nome, marcador)"""
    return pd.DataFrame([{"ano_pbe": str(a), "valor_taxonomia": v, "modelo_versao": n,
                          "marcador_nome": m} for a, v, n, m in linhas])


def _modelo(*linhas: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------- propulsao


def test_p1_acrescenta_o_que_o_pbe_mostra():
    linha = _linha(propulsao_oferecida="diesel", pbe_diferenca="so' no PBE: flex",
                   pbe_anos="2014-2018")
    versoes = _versoes((2014, "flex", "L200 TRITON", ""), (2014, "diesel", "L200", ""))
    r = adj.propulsao(linha, versoes, 2014, _modelo(linha), CORTE)
    assert not r.pendencias
    assert r.resolucoes[0]["regra"] == "P1"
    assert r.decisao == "propulsao_oferecida=flex+diesel; eletrificacao=nenhuma"


def test_p1_hev_com_hev_no_nome_e_p4_sem():
    """Decisao 1: sem HEV no nome, o Hibrido do PBE entra como hibrido_indefinido."""
    linha = _linha(propulsao_oferecida="flex+diesel", pbe_diferenca="so' no PBE: hev",
                   pbe_anos="2026")
    sem_nome = _versoes((2026, "hev", "RENEGADE SAHARA HYB", ""))
    r = adj.propulsao(linha, sem_nome, 2015, _modelo(linha), CORTE)
    assert not r.pendencias
    assert [x["regra"] for x in r.resolucoes] == ["P4"]
    assert r.decisao == ("propulsao_oferecida=flex+diesel+hibrido_indefinido; "
                         "eletrificacao=parcial")
    com_nome = _versoes((2026, "hev", "CARNIVAL HEV EX", "HEV"))
    r = adj.propulsao(linha, com_nome, 2015, _modelo(linha), CORTE)
    assert not r.pendencias and r.valor_apos_regras == "flex+diesel+hev"
    assert [x["regra"] for x in r.resolucoes] == ["P1"]


def test_p4_hibrido_indefinido_nunca_leva_a_total():
    linha = _linha(propulsao_oferecida="", pbe_diferenca="so' no PBE: hev", pbe_anos="2026")
    r = adj.propulsao(linha, _versoes((2026, "hev", "GS4 ELITE", "")), 2026, _modelo(linha),
                      CORTE)
    assert r.decisao == "propulsao_oferecida=hibrido_indefinido; eletrificacao=parcial"


def test_p3_hibrido_contra_mhev_vai_para_humano():
    linha = _linha(propulsao_oferecida="flex+mhev",
                   pbe_diferenca="so' no PBE: hev; so' na proposta: mhev", pbe_anos="2025")
    r = adj.propulsao(linha, _versoes((2025, "hev", "PULSE AUDACE HYB", "")), 2021,
                      _modelo(linha), CORTE)
    assert len(r.pendencias) == 1 and r.pendencias[0].startswith("P3 nao decide")


def test_p2_mantem_combustao_com_doze_meses_antes_do_primeiro_ano():
    linha = _linha(propulsao_oferecida="gasolina+flex+diesel",
                   pbe_diferenca="so' na proposta: diesel", pbe_anos="2011-2021",
                   vigencia_fim="2021-11")
    r = adj.propulsao(linha, _versoes((2011, "flex", "ECOSPORT", "")), 2011, _modelo(linha), CORTE)
    assert not r.pendencias
    assert r.resolucoes[0]["regra"] == "P2" and r.resolucoes[0]["ressalva"]
    curta = _linha(vigencia_inicio="2010-10", propulsao_oferecida="gasolina+flex",
                   pbe_diferenca="so' na proposta: gasolina", pbe_anos="2011-2019")
    r = adj.propulsao(curta, _versoes((2011, "flex", "FLUENCE", "")), 2011, _modelo(curta), CORTE)
    assert r.pendencias and "3 meses" in r.pendencias[0]


def test_p2_tipo_eletrificado_ausente_do_pbe_vai_para_humano():
    linha = _linha(vigencia_inicio="2015-04", propulsao_oferecida="flex+bev",
                   pbe_diferenca="so' na proposta: bev", pbe_anos="2015-2026")
    r = adj.propulsao(linha, _versoes((2015, "flex", "2008", "")), 2015, _modelo(linha), CORTE)
    assert r.pendencias and "eletrificado" in r.pendencias[0]


def test_p2_ausente_so_informa_a_partir_do_corte():
    """Decisao 3: antes do ano em que o PBE cobre 80% do volume, ausencia nao informa."""
    antiga = _linha(pbe_situacao="ausente", vigencia_fim="2008-12", propulsao_oferecida="diesel")
    r = adj.propulsao(antiga, None, None, _modelo(antiga), CORTE)
    assert not r.pendencias and r.resolucoes[0]["forca"] == "fraca"
    edge = _linha(pbe_situacao="ausente", vigencia_inicio="2009-01", vigencia_fim="2015-12",
                  propulsao_oferecida="gasolina")
    r = adj.propulsao(edge, None, 2017, _modelo(edge), CORTE)
    assert not r.pendencias and "2016" in r.resolucoes[0]["base"]
    nunca = _linha(pbe_situacao="ausente", vigencia_fim="2014-12")
    assert not adj.propulsao(nunca, None, None, _modelo(nunca), CORTE).pendencias
    captiva = _linha(pbe_situacao="ausente", vigencia_inicio="2008-07", vigencia_fim="2016-12",
                     propulsao_oferecida="gasolina")
    r = adj.propulsao(captiva, None, 2026, _modelo(captiva), CORTE)
    assert r.pendencias and "depois de 2016" in r.pendencias[0]


def test_p2_diverge_conta_meses_antes_do_corte_quando_o_modelo_entra_depois():
    linha = _linha(vigencia_inicio="2015-06", propulsao_oferecida="gasolina+flex",
                   pbe_diferenca="so' na proposta: gasolina", pbe_anos="2019-2021")
    r = adj.propulsao(linha, _versoes((2019, "flex", "X", "")), 2019, _modelo(linha), CORTE)
    assert r.pendencias and "7 meses antes de 2016" in r.pendencias[0]


def test_p1_nao_usa_ano_dividido_entre_vigencias():
    """Compass: o PBE de 2016 tem as duas geracoes e vai para a vigencia com mais meses."""
    velha = _linha(vigencia_fim="2016-08", propulsao_oferecida="gasolina",
                   pbe_diferenca="so' no PBE: diesel+flex", pbe_anos="2013-2016")
    nova = _linha(vigencia_inicio="2016-09", propulsao_oferecida="flex+diesel")
    versoes = _versoes((2013, "gasolina", "COMPASS", ""), (2016, "flex", "COMPASS", ""),
                       (2016, "diesel", "COMPASS", ""))
    r = adj.propulsao(velha, versoes, 2013, _modelo(velha, nova), CORTE)
    assert len(r.pendencias) == 2 and all("ano dividido" in p for p in r.pendencias)


def test_p1_nao_usa_combustao_das_tabelas_sem_coluna_contra_hibrido():
    """Prius: ate' 2020 o hibrido sem HYBRID no nome sai como gasolina."""
    linha = _linha(propulsao_oferecida="hev", pbe_diferenca="so' no PBE: gasolina",
                   pbe_anos="2013-2021")
    versoes = _versoes((2015, "gasolina", "PRIUS", ""), (2021, "hev", "PRIUS NGA", ""))
    r = adj.propulsao(linha, versoes, 2013, _modelo(linha), CORTE)
    assert r.pendencias and "sem coluna" in r.pendencias[0]


def test_p1_nao_usa_combustao_de_versao_que_se_diz_hibrida():
    linha = _linha(propulsao_oferecida="hev", pbe_diferenca="so' no PBE: gasolina",
                   pbe_anos="2026")
    versoes = _versoes((2026, "gasolina", "RAV4 SX HYBRID", "HYBRID"))
    r = adj.propulsao(linha, versoes, 2010, _modelo(linha), CORTE)
    assert r.pendencias and "nome diz hibrido" in r.pendencias[0]


# ------------------------------------------------------------------- origem


def _fontes(*linhas) -> pd.DataFrame:
    """(evento, data, tipo, confronto)"""
    return pd.DataFrame([{"evento": e, "origem_data_fonte": d, "tipo_fonte": t,
                          "confronto_com_proposta": c,
                          "origem_fonte_url": f"https://exemplo{i}.com/x"}
                         for i, (e, d, t, c) in enumerate(linhas)])


def test_o1_confirma_com_fonte_forte_e_o4_com_fonte_fraca():
    linha = _linha()
    forte = _fontes(("inicio_producao_local", "2016-09", "imprensa_especializada", "confirma"))
    r = adj.origem(linha, 0, forte, True, _modelo(linha))
    assert not r.pendencias and r.resolucoes[0]["regra"] == "O1"
    assert r.decisao == "origem_producao=nacional"
    fraca = _fontes(("inicio_producao_local", "2016-09", "blog_agregador", "confirma"))
    r = adj.origem(linha, 0, fraca, True, _modelo(linha))
    assert not r.pendencias and r.resolucoes[0]["regra"] == "O4"
    assert r.resolucoes[0]["forca"] == "fraca"


def test_o1_complementa_so_quando_a_fonte_cobre_a_vigencia():
    linha = _linha(vigencia_inicio="2025-11", origem_producao="")
    fonte = _fontes(("inicio_producao_local", "2025-09", "oficial", "complementa"))
    r = adj.origem(linha, 0, fonte, True, _modelo(linha))
    assert r.decisao == "origem_producao=nacional"
    cedo = _linha(vigencia_inicio="2025-08", origem_producao="")
    r = adj.origem(cedo, 0, fonte, True, _modelo(cedo))
    assert r.pendencias and r.pendencias[0].startswith("O1 nao decide")


def test_o2_move_a_fronteira_para_o_mes_da_fonte():
    importado = _linha(vigencia_inicio="2016-07", vigencia_fim="2017-04",
                       origem_producao="importado")
    nacional = _linha(vigencia_inicio="2017-05")
    modelo = _modelo(importado, nacional)
    fonte = _fontes(("inicio_producao_local", "2017-04", "imprensa_especializada", "ajusta_data"))
    assert adj.origem(importado, 0, fonte, True, modelo).decisao == "vigencia_fim=2017-03"
    assert adj.origem(nacional, 1, fonte, True, modelo).decisao == "vigencia_inicio=2017-04"


def test_o2_exige_mes_e_evento_efetivo():
    linha = _linha()
    so_ano = _fontes(("inicio_producao_local", "2013", "imprensa_especializada", "ajusta_data"))
    assert "data sem mes" in adj.origem(linha, 0, so_ano, True, _modelo(linha)).pendencias[0]
    plano = _fontes(("plano_producao_local", "2016-03", "imprensa_especializada", "ajusta_data"))
    assert "plano" in adj.origem(linha, 0, plano, True, _modelo(linha)).pendencias[0]


def test_o3_contradiz_sempre_humano_e_marca_fonte_unica_e_fraca():
    linha = _linha()
    forte = _fontes(("inicio_producao_local", "2015-01", "oficial", "contradiz"))
    r = adj.origem(linha, 0, forte, False, _modelo(linha))
    assert r.pendencias[0].startswith("O3") and "fraca" not in r.pendencias[0]
    fraca = _fontes(("producao_local_periodo", "2014/2018", "blog_agregador", "contradiz"))
    r = adj.origem(linha, 0, fraca, False, _modelo(linha))
    assert r.pendencias[0].endswith("fonte unica e fraca")


def test_fora_do_universo_de_origem_nada_muda():
    linha = _linha(confianca_origem="alta")
    fonte = _fontes(("producao_local_periodo", "2002/2014", "blog_agregador", "confirma"))
    assert adj.origem(linha, 0, fonte, False, _modelo(linha)) is None
    assert adj.origem(linha, 0, None, False, _modelo(linha)) is None


# ------------------------------------------------------------------ montagem


def test_montagem_tem_periodo_proprio_e_nao_se_aplica_para_importado():
    """Decisao 4: o modo so' vale no periodo que a fonte cobre; importado e' nao_se_aplica."""
    rascunho = pd.DataFrame([
        _linha(modelo="A", vigencia_inicio="2024-03", origem_producao="importado"),
        _linha(modelo="B", vigencia_inicio="2016-06", vigencia_fim="2017-03"),
        _linha(modelo="C", vigencia_inicio="2020-01", vigencia_fim="2020-12",
               origem_producao="importado"),
    ])
    fonte = {"segmento": "automoveis", "fonte_url": "u", "fonte_trecho": "t", "observacao": "",
             "marca": "M", "tipo_fonte": "imprensa_geral"}
    fontes = pd.DataFrame([
        {**fonte, "modelo": "A", "montagem_local": "skd", "onde": "brasil",
         "periodo_inicio": "2025-10", "periodo_fim": "2026-07"},
        {**fonte, "modelo": "B", "montagem_local": "ckd", "onde": "brasil",
         "periodo_inicio": "2016", "periodo_fim": ""},
        {**fonte, "modelo": "C", "montagem_local": "skd", "onde": "exterior",
         "periodo_inicio": "2022-06", "periodo_fim": "2022-06"},
    ])
    unidades = pd.DataFrame([{"marca": "M", "modelo": "B", "segmento": "automoveis",
                              "mes_ref": m, "unidades": 10}
                             for m in ("2016-06", "2016-12", "2017-01", "2017-03")])
    com, periodos = adj.periodos_montagem(rascunho, fontes, unidades)
    b = periodos[periodos["modelo"] == "B"]
    assert list(zip(b["montagem_inicio"], b["montagem_fim"], b["montagem_local"],
                    b["unidades"])) == [("2016-06", "2016-12", "ckd", 20),
                                        ("2017-01", "2017-03", "desconhecido", 20)]
    assert b["procedencia"].iloc[0] == "regra_fonte_fraca"
    assert list(com["montagem_por_periodo"]) == [
        "nao_se_aplica", "ckd 2016-06 a 2016-12; desconhecido 2017-01 a 2017-03",
        "nao_se_aplica"]
    a = periodos[periodos["modelo"] == "A"]
    assert a["montagem_local"].item() == "nao_se_aplica" and "skd" in a["observacao"].item()


def test_fonte_forte_vem_antes_da_fraca_salvo_contradicao():
    """A segunda fonte forte decide no lugar da primeira, fraca; contradiz sempre manda."""
    importado = _linha(vigencia_inicio="2015-05", vigencia_fim="2016-08",
                       origem_producao="importado")
    nacional = _linha(vigencia_inicio="2016-09")
    modelo = _modelo(importado, nacional)
    fontes = _fontes(("inicio_producao_local", "2016-08", "blog_agregador", "ajusta_data"),
                     ("inicio_producao_local", "2016-09", "imprensa_especializada", "confirma"))
    r = adj.origem(nacional, 1, fontes, True, modelo)
    assert r.resolucoes[0]["regra"] == "O1" and not r.pendencias
    com_contradicao = _fontes(("producao_local_periodo", "2014/2018", "blog_agregador",
                               "contradiz"),
                              ("inicio_producao_local", "2016-09", "oficial", "confirma"))
    r = adj.origem(nacional, 1, com_contradicao, True, modelo)
    assert r.pendencias[0].startswith("O3: fonte de origem contradiz")


def test_o3_diz_se_a_segunda_fonte_foi_buscada():
    fraca = _fontes(("inicio_producao_local", "2013", "blog_agregador", "ajusta_data"))
    antiga = _linha(vigencia_inicio="2012-01")
    assert "anterior a 2014" in adj.origem(antiga, 0, fraca, True, _modelo(antiga)).pendencias[0]
    nova = _linha(vigencia_inicio="2014-04")
    assert "ainda nao buscada" in adj.origem(nova, 0, fraca, True, _modelo(nova)).pendencias[0]
    busca = {"data_busca": "2026-10-01"}
    r = adj.origem(nova, 0, fraca, True, _modelo(nova), busca)
    assert "buscada em 2026-10-01 e nao achada" in r.pendencias[0]


# ---------------------------------------------------------------- procedencia


def test_procedencia_segue_a_precedencia_da_fase_2():
    """Decisao 6: humana, senao regra (forte ou fraca), senao proposta; pendente fica marcado."""
    linha = _linha(decisao_humana="")
    forte = adj.Resultado(resolucoes=[{"forca": "forte"}], decisao="x=y")
    fraca = adj.Resultado(resolucoes=[{"forca": "forte"}, {"forca": "fraca"}], decisao="x=y")
    pendente = adj.Resultado(pendencias=["O3: x"])
    assert adj._procedencia(linha, "origem_producao", forte, "") == "regra_fonte_forte"
    assert adj._procedencia(linha, "origem_producao", fraca, "") == "regra_fonte_fraca"
    assert adj._procedencia(linha, "origem_producao", pendente, "") == "pendente"
    assert adj._procedencia(linha, "origem_producao", None, "forte") == "regra_fonte_forte"
    assert adj._procedencia(linha, "origem_producao", None, "") == "proposta"
    so_propulsao = _linha(decisao_humana="propulsao_oferecida=flex")
    assert adj._procedencia(so_propulsao, "propulsao_oferecida", pendente, "") == "humana"
    assert adj._procedencia(so_propulsao, "origem_producao", pendente, "") == "pendente"
    assert adj._procedencia(_linha(decisao_humana="ok"), "origem_producao", pendente, "") == \
        "humana"


# ------------------------------------------------------------------ cobertura


def test_cobertura_do_pbe_por_ano_e_corte():
    painel = pd.DataFrame([
        {"ano": 2015, "marca": "M", "modelo": "A", "segmento": "s", "unidades": 70},
        {"ano": 2015, "marca": "M", "modelo": "B", "segmento": "s", "unidades": 30},
        {"ano": 2016, "marca": "M", "modelo": "A", "segmento": "s", "unidades": 85},
        {"ano": 2016, "marca": "M", "modelo": "B", "segmento": "s", "unidades": 15},
    ])
    casado = pd.DataFrame([
        {"ano_pbe": "2015", "marca": "M", "modelo": "A", "segmento": "s"},
        {"ano_pbe": "2016", "marca": "M", "modelo": "A", "segmento": "s"},
        {"ano_pbe": "2016", "marca": "", "modelo": "", "segmento": ""},
    ])
    versoes = pd.DataFrame({"ano_pbe": ["2015", "2016", "2016"]})
    cobertura = validacao.cobertura_por_ano(painel, versoes, casado)
    assert list(cobertura["cobertura_pct"]) == [70.0, 85.0]
    assert list(cobertura["versoes_na_tabela"]) == [1, 2]
    assert validacao.ano_de_corte(cobertura) == 2016


# ------------------------------------------------------------------- a conta


def test_conta_da_fila_saiu_ficou_entrou():
    k = ["marca", "modelo", "segmento", "vigencia_inicio"]
    antes = pd.DataFrame([("M", "A", "s", "2003-01"), ("M", "B", "s", "2003-01")], columns=k)
    com = pd.DataFrame([("M", "A", "s", "2003-01", "", "P1", 10),
                        ("M", "B", "s", "2003-01", "O3: x", "", 20),
                        ("M", "C", "s", "2003-01", "O3: y", "", 30)],
                       columns=k + ["pendencias", "regras_aplicadas", "unidades_na_vigencia"])
    resolvido = pd.DataFrame([{"regra": "P1", "unidades_na_vigencia": 10}])
    contas = adj.contas(antes, com, resolvido).set_index("conta")["linhas"]
    assert contas["saiu da fila por P1"] == 1
    assert contas["ficou na fila"] == 1
    assert contas["entrou na fila nesta rodada"] == 1
    assert contas["na fila depois das regras"] == 2
