"""Onde a fonte corta a cauda (I3, Q5).

A truncagem e' numero fixo de linhas por sub-segmento, nao piso de unidades.
"""

import pandas as pd

from comum import truncamento


def _bruto(linhas):
    quadro = pd.DataFrame(linhas)
    quadro["origem_tabela"] = quadro.get("origem_tabela", "sub_segmento")
    return quadro


def _bloco(mes, sub, valores, segmento="automoveis", marca="X"):
    return [
        {"mes_ref": mes, "segmento_fonte": segmento, "sub_segmento_fonte": sub,
         "marca_fonte": marca, "modelo_fonte": f"{sub}-{i}", "unidades": v,
         "origem_tabela": "sub_segmento"}
        for i, v in enumerate(valores)
    ]


def test_bloco_no_teto_corta_no_menor_listado():
    # "SUVS" mostra 3 linhas nos dois meses: esta' no teto, e o corte e' o menor
    bruto = _bruto(_bloco("2020-01", "SUVS", [500, 300, 120])
                   + _bloco("2020-02", "SUVS", [480, 260, 90]))
    blocos = truncamento.por_bloco(bruto).set_index("mes_ref")
    assert blocos.loc["2020-01", "no_teto"]
    assert blocos.loc["2020-01", "corte"] == 120
    assert blocos.loc["2020-02", "corte"] == 90


def test_bloco_fora_do_teto_nao_corta_nada():
    # em fevereiro o bloco tem menos linhas que o teto: nao truncou
    bruto = _bruto(_bloco("2020-01", "SUVS", [500, 300, 120])
                   + _bloco("2020-02", "SUVS", [480, 260]))
    blocos = truncamento.por_bloco(bruto).set_index("mes_ref")
    assert not blocos.loc["2020-02", "no_teto"]
    assert blocos.loc["2020-02", "corte"] == 0


def test_o_corte_e_do_bloco_e_nao_do_mes_inteiro():
    """Um bloco pequeno lista ate' 1 unidade sem que isso solte o bloco cheio."""
    bruto = _bruto(_bloco("2020-01", "SUVS", [500, 300, 120])
                   + _bloco("2020-01", "MONOCAB", [40, 1]))
    blocos = truncamento.por_bloco(bruto).set_index("sub_segmento_fonte")
    assert blocos.loc["SUVS", "corte"] == 120
    # o menor valor do mes inteiro e' 1, e nao contamina o corte dos SUVs
    assert bruto["unidades"].min() == 1


def test_corte_por_modelo_segue_o_sub_segmento_do_modelo():
    bruto = _bruto(
        _bloco("2020-01", "SUVS", [500, 300, 120])
        + _bloco("2020-01", "MONOCAB", [40, 1])
        + _bloco("2020-02", "SUVS", [480, 260, 90])
        + _bloco("2020-02", "MONOCAB", [35, 2])
    )
    cortes = truncamento.por_modelo_e_mes(bruto, ["2020-01", "2020-02"])
    assert cortes.loc[("X", "SUVS-0", "automoveis"), "2020-01"] == 120
    assert cortes.loc[("X", "MONOCAB-0", "automoveis"), "2020-01"] == 1


def test_modelo_ausente_herda_o_proprio_sub_segmento():
    """Some em fevereiro: o corte que vale e' o do bloco em que ele estaria."""
    bruto = _bruto(
        _bloco("2020-01", "SUVS", [500, 300, 120])
        + _bloco("2020-02", "SUVS", [480, 260, 90])
    )
    # o modelo SUVS-2 existe so' em janeiro
    bruto = bruto[~((bruto.mes_ref == "2020-02") & (bruto.modelo_fonte == "SUVS-2"))]
    bruto = pd.concat([bruto, pd.DataFrame(_bloco("2020-02", "SUVS", [70]))], ignore_index=True)
    cortes = truncamento.por_modelo_e_mes(bruto, ["2020-01", "2020-02"])
    assert cortes.loc[("X", "SUVS-2", "automoveis"), "2020-02"] > 0


def test_linhas_do_ranking_nao_entram_no_calculo():
    """O ranking nao tem sub-segmento, entao nao diz nada sobre truncagem."""
    bruto = _bruto(_bloco("2020-01", "SUVS", [500, 300, 120]))
    do_ranking = pd.DataFrame([{
        "mes_ref": "2020-01", "segmento_fonte": "automoveis", "sub_segmento_fonte": "",
        "marca_fonte": "X", "modelo_fonte": "SO NO RANKING", "unidades": 3,
        "origem_tabela": "ranking",
    }])
    blocos = truncamento.por_bloco(pd.concat([bruto, do_ranking], ignore_index=True))
    assert len(blocos) == 1
    assert blocos.iloc[0]["corte"] == 120


def _mes_normal(mes, sub_segmentos=17, linhas_por_bloco=4):
    linhas = []
    for indice in range(sub_segmentos):
        linhas += _bloco(mes, f"SUB{indice}", list(range(100, 100 + linhas_por_bloco)))
    return linhas


def test_edicao_curta_e_apontada_pelo_numero_de_sub_segmentos():
    # 2003-10 e 2005-03 sairam com 10 paginas: um sub-segmento em vez de 17.
    bruto = _bruto(_mes_normal("2003-09") + _mes_normal("2003-11")
                   + _mes_normal("2003-12")
                   + _bloco("2003-10", "SUB0", [100, 90, 80]))
    curtas = truncamento.edicoes_abreviadas(bruto)
    assert list(curtas["mes_ref"]) == ["2003-10"]
    assert curtas.iloc[0]["sub_segmentos"] == 1
    assert curtas.iloc[0]["sub_segmentos_tipicos"] == 17
    assert curtas.iloc[0]["situacao"] == "edicao curta do informe"


def test_mes_reconstruido_e_separado_da_edicao_curta():
    # 2023-09 vem inteiro da coluna de mes anterior: nao tem sub-segmento, mas
    # nao e' edicao curta -- e' segunda publicacao do mesmo numero.
    recuperado = [
        {"mes_ref": "2023-09", "segmento_fonte": "automoveis", "sub_segmento_fonte": "",
         "marca_fonte": "GM", "modelo_fonte": f"M{i}", "unidades": 10 * i,
         "origem_tabela": "mes_anterior"}
        for i in range(1, 6)
    ]
    bruto = _bruto(_mes_normal("2023-08") + _mes_normal("2023-10")
                   + _mes_normal("2023-11") + recuperado)
    curtas = truncamento.edicoes_abreviadas(bruto)
    assert list(curtas["mes_ref"]) == ["2023-09"]
    assert curtas.iloc[0]["situacao"] == "mes recuperado do informe seguinte"


def test_serie_sem_edicao_curta_nao_aponta_nada():
    bruto = _bruto(_mes_normal("2020-01") + _mes_normal("2020-02")
                   + _mes_normal("2020-03"))
    assert truncamento.edicoes_abreviadas(bruto).empty
