"""A marca que a fonte atribui a um modelo, mes a mes (sec.9.4).

Nov/2013 publica `PONTIAC/MONTANA` e `FORD/KOMBI`. O teste detecta a troca pela
redundancia da serie e **nao corrige nada**: o painel guarda o que a fonte
publicou.
"""

import pandas as pd

from comum import marca_do_modelo


def _serie(marca, modelo, meses, unidades=1000, segmento="automoveis"):
    return [
        {"marca": marca, "modelo": modelo, "segmento": segmento,
         "mes_ref": mes, "unidades": unidades}
        for mes in meses
    ]


def _meses(ano, quantos):
    return [f"{ano}-{m:02d}" for m in range(1, quantos + 1)]


def test_mes_isolado_sob_outra_marca_e_apontado():
    # MONTANA e' GM em onze meses e sai como PONTIAC num so'.
    linhas = _serie("GM", "MONTANA", _meses(2013, 11))
    linhas += _serie("PONTIAC", "MONTANA", ["2013-12"], unidades=3901)
    divergentes = marca_do_modelo.divergencias(pd.DataFrame(linhas))
    assert len(divergentes) == 1
    achado = divergentes.iloc[0]
    assert achado["mes_ref"] == "2013-12"
    assert achado["marca"] == "PONTIAC"
    assert achado["marca_dominante"] == "GM"
    assert achado["unidades"] == 3901


def test_modelo_sem_historico_nao_rende_opiniao():
    # Menos de MINIMO_MESES: a serie nao tem redundancia para decidir quem manda.
    linhas = _serie("GM", "MONTANA", _meses(2013, 3))
    linhas += _serie("PONTIAC", "MONTANA", ["2013-04"])
    assert marca_do_modelo.divergencias(pd.DataFrame(linhas)).empty


def test_marca_dividida_ao_meio_nao_e_divergencia():
    # 50/50 nao e' troca de coluna: e' nome de modelo usado por duas marcas.
    linhas = _serie("GM", "CLASSICO", _meses(2013, 6))
    linhas += _serie("CHEVROLET", "CLASSICO", _meses(2014, 6))
    assert marca_do_modelo.divergencias(pd.DataFrame(linhas)).empty


def test_troca_real_de_marca_tambem_aparece_a_leitura_e_humana():
    # TIGGO 7 sob CHERY antes e CAOA CHERY depois: o teste aponta, nao decide.
    linhas = _serie("CAOA CHERY", "TIGGO 7", _meses(2021, 12))
    linhas += _serie("CHERY", "TIGGO 7", ["2020-01"], unidades=181)
    divergentes = marca_do_modelo.divergencias(pd.DataFrame(linhas))
    assert list(divergentes["marca"]) == ["CHERY"]
    assert list(divergentes["marca_dominante"]) == ["CAOA CHERY"]


def test_segmentos_sao_contados_em_separado():
    # Mesmo nome em automoveis e comerciais leves: um nao contamina o outro.
    linhas = _serie("VW", "SAVEIRO", _meses(2016, 12), segmento="comerciais_leves")
    linhas += _serie("VW", "SAVEIRO", _meses(2016, 12), segmento="automoveis")
    linhas += _serie("FIAT", "SAVEIRO", ["2017-01"], segmento="automoveis", unidades=4)
    divergentes = marca_do_modelo.divergencias(pd.DataFrame(linhas))
    assert list(divergentes["segmento"]) == ["automoveis"]


def test_resumo_por_mes_soma_volume_e_conta_marcas_fantasma():
    linhas = _serie("GM", "MONTANA", _meses(2013, 11))
    linhas += _serie("PONTIAC", "MONTANA", ["2013-12"], unidades=3901)
    linhas += _serie("VW", "KOMBI", _meses(2013, 11), segmento="comerciais_leves")
    linhas += _serie("FORD", "KOMBI", ["2013-12"], unidades=2464,
                     segmento="comerciais_leves")
    resumo = marca_do_modelo.meses_afetados(
        marca_do_modelo.divergencias(pd.DataFrame(linhas)))
    assert len(resumo) == 1
    assert resumo.iloc[0]["mes_ref"] == "2013-12"
    assert resumo.iloc[0]["modelos"] == 2
    assert resumo.iloc[0]["marcas_fantasma"] == 2
    assert resumo.iloc[0]["unidades"] == 3901 + 2464


def test_painel_vazio_nao_quebra():
    assert marca_do_modelo.divergencias(pd.DataFrame()).empty
    assert marca_do_modelo.meses_afetados(pd.DataFrame()).empty
