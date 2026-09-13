"""Sub-segmento na linha (Q4), grupo unitario e a identidade do HHI (B1)."""

import pandas as pd

from comum import concentracao, grupos, visoes


def _painel(linhas):
    quadro = pd.DataFrame(linhas)
    quadro["ano"] = quadro["mes_ref"].str.slice(0, 4).astype(int)
    quadro["mes"] = quadro["mes_ref"].str.slice(5, 7).astype(int)
    quadro["data"] = pd.to_datetime(quadro["mes_ref"] + "-01").dt.date
    return quadro


def test_por_modelo_soma_os_sub_segmentos_e_preserva_a_origem():
    """NISSAN/VERSA aparece em dois sub-segmentos no mesmo mes: geracoes diferentes."""
    painel = _painel([
        {"mes_ref": "2026-08", "segmento": "automoveis", "marca": "NISSAN",
         "modelo": "VERSA", "sub_segmento_fonte": "Sedans Pequenos", "unidades": 0},
        {"mes_ref": "2026-08", "segmento": "automoveis", "marca": "NISSAN",
         "modelo": "VERSA", "sub_segmento_fonte": "Sedans Compactos", "unidades": 533},
    ])
    agregado = visoes.por_modelo(painel)
    assert len(agregado) == 1
    assert agregado.iloc[0]["unidades"] == 533
    # a pista de geracao nao se perde: fica listada na visao
    assert agregado.iloc[0]["sub_segmentos"] == "Sedans Compactos+Sedans Pequenos"


def test_o_painel_guarda_as_duas_linhas():
    painel = _painel([
        {"mes_ref": "2026-08", "segmento": "automoveis", "marca": "NISSAN",
         "modelo": "VERSA", "sub_segmento_fonte": "Sedans Pequenos", "unidades": 0},
        {"mes_ref": "2026-08", "segmento": "automoveis", "marca": "NISSAN",
         "modelo": "VERSA", "sub_segmento_fonte": "Sedans Compactos", "unidades": 533},
    ])
    assert painel["sub_segmento_fonte"].nunique() == 2


def test_marca_sem_grupo_vira_grupo_unitario_com_o_proprio_nome():
    grupo, mapeado = grupos.grupo_vigente("MARCA QUE NAO EXISTE", "2020-01")
    assert grupo == "MARCA QUE NAO EXISTE"
    assert mapeado is False
    # e uma marca mapeada continua indo para o grupo dela
    assert grupos.grupo_vigente("FIAT", "2021-01") == ("STELLANTIS", True)


def test_hhi_de_grupo_nunca_fica_abaixo_do_de_marca_com_particao_fixa():
    painel = _painel([
        {"mes_ref": "2020-01", "segmento": "automoveis", "marca": m,
         "modelo": m, "sub_segmento_fonte": "", "unidades": u,
         "grupo_economico": g, "grupo_mapeado": True}
        for m, g, u in [("FIAT", "FCA", 400), ("JEEP", "FCA", 300),
                        ("VW", "VOLKSWAGEN", 200), ("AUDI", "VOLKSWAGEN", 100)]
    ])
    marca = concentracao.hhi(painel, "marca")
    grupo = concentracao.hhi(painel, "grupo_economico")
    assert grupo > marca


def test_mapa_datado_pode_inverter_o_hhi_anual_e_a_particao_fixa_conserta():
    """Em 2014 a FIAT muda de grupo em outubro: o volume anual se parte em dois."""
    linhas = []
    for mes in range(1, 13):
        grupo = "FIAT" if mes <= 9 else "FCA"
        linhas.append({"mes_ref": f"2014-{mes:02d}", "segmento": "automoveis",
                       "marca": "FIAT", "modelo": "PALIO", "sub_segmento_fonte": "",
                       "unidades": 500, "grupo_economico": grupo, "grupo_mapeado": True})
        linhas.append({"mes_ref": f"2014-{mes:02d}", "segmento": "automoveis",
                       "marca": "VW", "modelo": "GOL", "sub_segmento_fonte": "",
                       "unidades": 500, "grupo_economico": "VOLKSWAGEN",
                       "grupo_mapeado": True})
    painel = _painel(linhas)
    anual = concentracao.por_ano(painel)
    linha = anual.iloc[0]
    assert linha["marcas_que_mudam_de_grupo_no_ano"] == 1
    # o datado inverte...
    assert linha["hhi_grupo_datado"] < linha["hhi_marca"]
    # ...e a particao fixa devolve a identidade
    assert linha["hhi_grupo_particao_fixa"] >= linha["hhi_marca"]


def test_hhi_mensal_respeita_a_identidade_mesmo_em_ano_de_transicao():
    linhas = []
    for mes in range(1, 13):
        grupo = "FIAT" if mes <= 9 else "FCA"
        linhas.append({"mes_ref": f"2014-{mes:02d}", "segmento": "automoveis",
                       "marca": "FIAT", "modelo": "PALIO", "sub_segmento_fonte": "",
                       "unidades": 500, "grupo_economico": grupo, "grupo_mapeado": True})
        linhas.append({"mes_ref": f"2014-{mes:02d}", "segmento": "automoveis",
                       "marca": "JEEP", "modelo": "RENEGADE", "sub_segmento_fonte": "",
                       "unidades": 300, "grupo_economico": grupo, "grupo_mapeado": True})
        linhas.append({"mes_ref": f"2014-{mes:02d}", "segmento": "automoveis",
                       "marca": "VW", "modelo": "GOL", "sub_segmento_fonte": "",
                       "unidades": 500, "grupo_economico": "VOLKSWAGEN",
                       "grupo_mapeado": True})
    mensal = concentracao.por_mes(_painel(linhas))
    assert (mensal["diferenca"] >= -1e-6).all()


def test_hhi_de_bloco_vazio_nao_explode():
    vazio = pd.DataFrame({"marca": [], "unidades": []})
    assert pd.isna(concentracao.hhi(vazio, "marca"))
