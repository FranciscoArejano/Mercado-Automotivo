"""Regras de adjudicacao: P1, P2, P3 (propulsao), O1, O2, O3 (origem) e montagem.

Linhas e versoes construidas; os nomes de modelo lembram os casos reais que
motivaram cada regra ou guarda, mas os dados aqui sao do teste.
"""

import pandas as pd

from comum import adjudicacao as adj


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
    r = adj.propulsao(linha, versoes, 2014, _modelo(linha))
    assert not r.pendencias
    assert r.resolucoes[0]["regra"] == "P1"
    assert r.decisao == "propulsao_oferecida=flex+diesel; eletrificacao=nenhuma"


def test_p1_hibrido_so_entra_com_hev_no_nome():
    linha = _linha(propulsao_oferecida="flex+diesel", pbe_diferenca="so' no PBE: hev",
                   pbe_anos="2026")
    sem_nome = _versoes((2026, "hev", "RENEGADE SAHARA HYB", ""))
    r = adj.propulsao(linha, sem_nome, 2015, _modelo(linha))
    assert r.pendencias and r.pendencias[0].startswith("P1 nao decide")
    assert not r.decisao
    literal = adj.propulsao(linha, sem_nome, 2015, _modelo(linha), p1_literal=True)
    assert literal.valor_apos_regras == "flex+diesel+hev" and not literal.pendencias
    com_nome = _versoes((2026, "hev", "CARNIVAL HEV EX", "HEV"))
    r = adj.propulsao(linha, com_nome, 2015, _modelo(linha))
    assert not r.pendencias and r.valor_apos_regras == "flex+diesel+hev"


def test_p3_hibrido_contra_mhev_vai_para_humano():
    linha = _linha(propulsao_oferecida="flex+mhev",
                   pbe_diferenca="so' no PBE: hev; so' na proposta: mhev", pbe_anos="2025")
    r = adj.propulsao(linha, _versoes((2025, "hev", "PULSE AUDACE HYB", "")), 2021,
                      _modelo(linha))
    assert len(r.pendencias) == 1 and r.pendencias[0].startswith("P3 nao decide")


def test_p2_mantem_combustao_com_doze_meses_antes_do_primeiro_ano():
    linha = _linha(propulsao_oferecida="gasolina+flex+diesel",
                   pbe_diferenca="so' na proposta: diesel", pbe_anos="2011-2021",
                   vigencia_fim="2021-11")
    r = adj.propulsao(linha, _versoes((2011, "flex", "ECOSPORT", "")), 2011, _modelo(linha))
    assert not r.pendencias
    assert r.resolucoes[0]["regra"] == "P2" and r.resolucoes[0]["ressalva"]
    curta = _linha(vigencia_inicio="2010-10", propulsao_oferecida="gasolina+flex",
                   pbe_diferenca="so' na proposta: gasolina", pbe_anos="2011-2019")
    r = adj.propulsao(curta, _versoes((2011, "flex", "FLUENCE", "")), 2011, _modelo(curta))
    assert r.pendencias and "3 meses" in r.pendencias[0]


def test_p2_tipo_eletrificado_ausente_do_pbe_vai_para_humano():
    linha = _linha(vigencia_inicio="2015-04", propulsao_oferecida="flex+bev",
                   pbe_diferenca="so' na proposta: bev", pbe_anos="2015-2026")
    r = adj.propulsao(linha, _versoes((2015, "flex", "2008", "")), 2015, _modelo(linha))
    assert r.pendencias and "eletrificado" in r.pendencias[0]


def test_p2_ausente_antes_do_pbe_ou_do_primeiro_ano():
    antiga = _linha(pbe_situacao="ausente", vigencia_fim="2008-12", propulsao_oferecida="diesel")
    r = adj.propulsao(antiga, None, None, _modelo(antiga))
    assert not r.pendencias and r.resolucoes[0]["ressalva"] == ""
    depois = _linha(pbe_situacao="ausente", vigencia_inicio="2008-07", vigencia_fim="2016-12",
                    propulsao_oferecida="gasolina")
    r = adj.propulsao(depois, None, 2026, _modelo(depois))
    assert not r.pendencias and "ja' existia" in r.resolucoes[0]["ressalva"]
    nunca = _linha(pbe_situacao="ausente", vigencia_fim="2014-12")
    r = adj.propulsao(nunca, None, None, _modelo(nunca))
    assert r.pendencias and "nao aparece no PBE" in r.pendencias[0]


def test_p1_nao_usa_ano_dividido_entre_vigencias():
    """Compass: o PBE de 2016 tem as duas geracoes e vai para a vigencia com mais meses."""
    velha = _linha(vigencia_fim="2016-08", propulsao_oferecida="gasolina",
                   pbe_diferenca="so' no PBE: diesel+flex", pbe_anos="2013-2016")
    nova = _linha(vigencia_inicio="2016-09", propulsao_oferecida="flex+diesel")
    versoes = _versoes((2013, "gasolina", "COMPASS", ""), (2016, "flex", "COMPASS", ""),
                       (2016, "diesel", "COMPASS", ""))
    r = adj.propulsao(velha, versoes, 2013, _modelo(velha, nova))
    assert len(r.pendencias) == 2 and all("ano dividido" in p for p in r.pendencias)


def test_p1_nao_usa_combustao_das_tabelas_sem_coluna_contra_hibrido():
    """Prius: ate' 2020 o hibrido sem HYBRID no nome sai como gasolina."""
    linha = _linha(propulsao_oferecida="hev", pbe_diferenca="so' no PBE: gasolina",
                   pbe_anos="2013-2021")
    versoes = _versoes((2015, "gasolina", "PRIUS", ""), (2021, "hev", "PRIUS NGA", ""))
    r = adj.propulsao(linha, versoes, 2013, _modelo(linha))
    assert r.pendencias and "sem coluna" in r.pendencias[0]


def test_p1_nao_usa_combustao_de_versao_que_se_diz_hibrida():
    linha = _linha(propulsao_oferecida="hev", pbe_diferenca="so' no PBE: gasolina",
                   pbe_anos="2026")
    versoes = _versoes((2026, "gasolina", "RAV4 SX HYBRID", "HYBRID"))
    r = adj.propulsao(linha, versoes, 2010, _modelo(linha))
    assert r.pendencias and "nome diz hibrido" in r.pendencias[0]


# ------------------------------------------------------------------- origem


def _fontes(*linhas) -> pd.DataFrame:
    """(evento, data, tipo, confronto)"""
    return pd.DataFrame([{"evento": e, "origem_data_fonte": d, "tipo_fonte": t,
                          "confronto_com_proposta": c,
                          "origem_fonte_url": f"https://exemplo{i}.com/x"}
                         for i, (e, d, t, c) in enumerate(linhas)])


def test_o1_confirma_com_fonte_forte_e_o3_com_fonte_fraca():
    linha = _linha()
    forte = _fontes(("inicio_producao_local", "2016-09", "imprensa_especializada", "confirma"))
    r = adj.origem(linha, 0, forte, True, _modelo(linha))
    assert not r.pendencias and r.resolucoes[0]["regra"] == "O1"
    assert r.decisao == "origem_producao=nacional"
    fraca = _fontes(("inicio_producao_local", "2016-09", "blog_agregador", "confirma"))
    r = adj.origem(linha, 0, fraca, True, _modelo(linha))
    assert r.pendencias[0].startswith("O3") and not r.resolucoes


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


def test_montagem_so_em_linha_local_e_com_cobertura():
    rascunho = pd.DataFrame([
        _linha(modelo="A", vigencia_inicio="2024-03", origem_producao="importado"),
        _linha(modelo="B", vigencia_inicio="2016-06"),
        _linha(modelo="C", origem_producao="importado"),
    ])
    fontes = pd.DataFrame([
        {"marca": "M", "modelo": "A", "segmento": "automoveis", "montagem_local": "skd",
         "onde": "brasil", "periodo_inicio": "2025-10", "periodo_fim": "2026-07",
         "fonte_url": "u", "fonte_trecho": "t", "observacao": ""},
        {"marca": "M", "modelo": "B", "segmento": "automoveis", "montagem_local": "ckd",
         "onde": "brasil", "periodo_inicio": "2016", "periodo_fim": "",
         "fonte_url": "u", "fonte_trecho": "t", "observacao": ""},
        {"marca": "M", "modelo": "C", "segmento": "automoveis", "montagem_local": "skd",
         "onde": "exterior", "periodo_inicio": "2022-06", "periodo_fim": "2022-06",
         "fonte_url": "u", "fonte_trecho": "t", "observacao": ""},
    ])
    com, casos = adj.anexar_montagem(rascunho, fontes)
    assert list(com["montagem_local"]) == ["desconhecido", "ckd", "desconhecido"]
    assert com.loc[1, "montagem_cobertura"].startswith("parcial")
    assert casos["aplicado"].str.startswith("nao").sum() == 2


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
