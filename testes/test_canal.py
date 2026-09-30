"""Canal de venda: leitura das pizzas, atribuicao e conferencias.

O risco desta dimensao nao esta' no parser das tabelas, que e' conferido contra
o painel principal (98% de identidade unidade a unidade). Esta' em decidir qual
numero da pizza e' a venda direta: a ordem muda de pizza para pizza, e errar
inverte o sinal do vies que a calibracao mede.
"""

import pandas as pd

from comum import canal


# 2026-08, como a fonte publicou: venda direta e' o 1o numero em automoveis,
# o 2o em comerciais leves e o 1o no conjunto.
PIZZAS_2026_08 = [(43.4, 56.6), (37.8, 62.2), (47.0, 53.0)]
TOTAIS_2026_08 = (212_876, 50_178)
LIMITES_2026_08 = ((42.14, 49.37), (62.17, 62.26))


def test_atribuicao_acha_a_venda_direta_mesmo_com_ordem_trocada():
    solucoes = canal.atribuir_participacao(
        PIZZAS_2026_08, *TOTAIS_2026_08, *LIMITES_2026_08,
        ordens=[canal.ORDEM_DO_LAYOUT])
    assert len(solucoes) == 1
    s = solucoes[0]
    assert (s.automoveis, s.comerciais_leves, s.combinado) == (43.4, 62.2, 47.0)
    assert s.direta_em_primeiro == "sim / nao / sim"


def test_limite_apertado_de_leves_decide_o_lado_sozinho():
    # Com cobertura de ~100%, o intervalo de leves tem decimos de ponto: 37,8
    # nao cabe, 62,2 cabe. Isso fixa o lado sem olhar o grafico.
    solucoes = canal.atribuir_participacao(
        PIZZAS_2026_08, *TOTAIS_2026_08, (0.0, 100.0), (62.17, 62.26),
        ordens=[canal.ORDEM_DO_LAYOUT])
    assert {s.comerciais_leves for s in solucoes} == {62.2}


def test_identidade_ponderada_descarta_combinacao_incoerente():
    # Automoveis 56,6 com leves 62,2 da' conjunto ~57,7 -- nenhum par publicado.
    solucoes = canal.atribuir_participacao(
        PIZZAS_2026_08, *TOTAIS_2026_08, (0.0, 100.0), (62.17, 62.26),
        ordens=[canal.ORDEM_DO_LAYOUT])
    assert all(s.automoveis == 43.4 for s in solucoes)


def test_sem_solucao_quando_nada_fecha():
    solucoes = canal.atribuir_participacao(
        [(10.0, 90.0), (20.0, 80.0), (30.0, 70.0)], *TOTAIS_2026_08,
        *LIMITES_2026_08, ordens=[canal.ORDEM_DO_LAYOUT])
    assert solucoes == []


def test_pizzas_saem_da_ordem_do_texto_nos_dois_layouts():
    # 2024-04 traz o titulo antes de cada par; 2026-08, os rotulos embaralhados.
    # Nos dois, os seis numeros saem em pares consecutivos.
    texto_2024 = ("Participacao de venda direta e venda varejo Abril/2024\nAutomoveis\n"
                  "55.99%\n44.01%\nComercial Leve\n38.43%\n61.57%\n"
                  "Automoveis + Comercial Leve\n52.30%\n47.70%")
    texto_2026 = ("Comercial Leve\nAutomoveAisutomoveis\nVenda Direta\nVarejo\n43.4%\n56.6%\n"
                  "Comercial Leve\nVenda Direta\nVarejo\n37.8%\n62.2%\n"
                  "Automoveis + Comercial Leve\n47%\n53%")
    assert canal.ler_pizzas(texto_2024) == [(55.99, 44.01), (38.43, 61.57), (52.3, 47.7)]
    assert canal.ler_pizzas(texto_2026) == PIZZAS_2026_08


def test_pizza_em_grafico_nao_rende_numero():
    # De 2003-01 a 2024-03 os percentuais sao desenho: a pagina so' tem os rotulos.
    assert canal.ler_pizzas("Automoveis\nComercial Leve\nAutomoveis + Comercial Leve") == []


def test_par_que_nao_fecha_100_e_rejeitado():
    assert canal.ler_pizzas("40%\n40%\n30%\n70%\n50%\n50%") == []


def test_par_com_arredondamento_da_fonte_passa():
    # A fonte arredonda cada numero por conta propria: 45,1 + 55 = 100,1.
    assert canal.ler_pizzas("45.1%\n55%\n34.8%\n65.2%\n49.8%\n50.2%") != []


def _calibracao(vieses, segmento="automoveis"):
    return pd.DataFrame([{
        "mes_ref": f"2025-{i + 1:02d}" if i < 12 else f"2026-{i - 11:02d}",
        "segmento": segmento, "vies_pp": v, "cobertura_varejo_pct": 95 - i * 0.2,
        "cobertura_total_pct": 96 - i * 0.1,
    } for i, v in enumerate(vieses)])


def test_vies_que_dobra_nao_e_estavel():
    resumo = canal.resumo_calibracao(_calibracao([1.0] * 6 + [1.5] * 6 + [2.0] * 6))
    assert not bool(resumo.iloc[0]["estavel"])


def test_vies_nulo_e_estavel():
    resumo = canal.resumo_calibracao(_calibracao([0.02, 0.03, 0.01] * 6, "comerciais_leves"))
    assert bool(resumo.iloc[0]["estavel"])


def test_ranking_contiguo_nao_tem_furo():
    import etapa09_canal
    painel = pd.DataFrame([{"mes_ref": "2026-08", "segmento": "automoveis",
                            "canal": "direta", "posicao_fonte": p} for p in range(1, 51)])
    assert etapa09_canal.posicoes_com_furo(painel).empty


def test_posicao_que_falta_no_ranking_e_denunciada():
    import etapa09_canal
    painel = pd.DataFrame([{"mes_ref": "2026-08", "segmento": "automoveis",
                            "canal": "direta", "posicao_fonte": p}
                           for p in range(1, 51) if p != 37])
    furos = etapa09_canal.posicoes_com_furo(painel)
    assert list(furos["posicoes_faltando"]) == ["37"]
