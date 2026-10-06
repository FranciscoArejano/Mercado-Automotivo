"""Calendario de politicas: so' fonte oficial, trecho literal, uma aliquota por periodo.

Guardas sobre as tabelas versionadas (`dados/referencia/politicas_atos.csv` e
`politicas_aliquotas.csv`): cada trecho (partes separadas por ' [...] ') esta'
literalmente na pagina guardada em `dados/bruto/politicas_paginas/`, o texto bate
com o SHA-256 do manifesto, a URL e' a da pagina, o dominio e' oficial. E as regras
da tabela mensal e do uso-teste, com casos pequenos.
"""

import hashlib

import pandas as pd
import pytest

from comum import config, politicas, tipo_fonte


@pytest.fixture(scope="module")
def atos():
    if not config.POLITICAS_ATOS.exists():
        pytest.skip("sem tabela de atos")
    return politicas.carregar_atos()


@pytest.fixture(scope="module")
def aliquotas():
    return politicas.carregar_aliquotas()


@pytest.fixture(scope="module")
def manifesto():
    return politicas.carregar_manifesto()


@pytest.fixture(scope="module")
def textos(atos, aliquotas):
    return politicas.textos(set(atos["pagina_salva"]) | set(aliquotas["pagina_salva"]))


# ------------------------------------------------------- tabelas versionadas


def test_paginas_batem_com_o_manifesto(manifesto):
    assert politicas.problemas_das_paginas(manifesto) == []
    for r in manifesto.itertuples():
        bruto = (config.POLITICAS_PAGINAS / f"{r.nome}.txt").read_bytes()
        assert hashlib.sha256(bruto).hexdigest() == r.sha256_texto, r.nome


def test_trecho_de_cada_ato_esta_na_pagina(atos, textos):
    for r in atos.itertuples():
        assert r.fonte_trecho, r.id
        assert politicas.partes_ausentes(r.fonte_trecho, textos[r.pagina_salva]) == [], r.id


def test_trecho_de_cada_aliquota_esta_na_pagina(aliquotas, textos):
    for r in aliquotas.itertuples():
        assert politicas.partes_ausentes(r.fonte_trecho, textos[r.pagina_salva]) == [], \
            (r.ato_id, r.ncm, r.vigencia_inicio)


def test_url_e_a_da_pagina_e_a_fonte_e_oficial(atos, manifesto):
    url = dict(zip(manifesto["nome"], manifesto["url"]))
    mapa = tipo_fonte.carregar_mapa()
    for r in atos.itertuples():
        assert r.fonte_url == url[r.pagina_salva], r.id
        assert r.tipo_fonte == "oficial" == tipo_fonte.tipo_de(r.fonte_url, mapa), r.id


def test_atos_e_aliquotas_sem_problema(atos, aliquotas, manifesto, textos):
    assert politicas.problemas_dos_atos(atos, manifesto, textos) == []
    assert politicas.problemas_das_aliquotas(aliquotas, atos, manifesto, textos) == []


def test_ipi_completo_e_efetiva_da_habilitada(aliquotas):
    """Cada categoria principal tem aliquota em todos os meses; de 16/12/2011 a 31/12/2017 a
    efetiva da habilitada e' a nominal menos 30, com o trecho da reducao; fora, igual."""
    assert politicas.lacunas_do_ipi(aliquotas, config.PERIODO_INICIO, config.PERIODO_FIM) == []
    ipi = aliquotas[aliquotas["tributo"] == "ipi"]
    assert set(ipi["categoria_ipi"]) == set(politicas.CATEGORIAS_IPI.values())
    for r in ipi.itertuples():
        nominal = float(r.aliquota_pct.replace(",", "."))
        efetiva = float(r.aliquota_efetiva_habilitada.replace(",", "."))
        if "2011-12-16" <= r.vigencia_inicio <= "2017-12-31":
            assert efetiva == nominal - 30 and r.reducao_trecho, (r.ato_id, r.ncm)
        else:
            assert efetiva == nominal and not r.reducao_ato_id, (r.ato_id, r.ncm)
    # o 1.000 cm3 a gasolina em meados de 2012: 30% na TIPI, zero para a habilitada
    meio_2012 = ipi[(ipi["categoria_ipi"] == politicas.CATEGORIAS_IPI["g1"])
                    & (ipi["vigencia_inicio"] == "2012-05-22")]
    assert meio_2012[["aliquota_pct", "aliquota_efetiva_habilitada"]].values.tolist() == [["30", "0"]]
    derivadas = ipi[ipi["derivada"] == "sim"]
    assert set(derivadas["ato_id"]) == {"ipi_2022_dec10979"} and derivadas["observacao"].all()


def test_formato_das_ncms(aliquotas):
    for r in aliquotas.itertuples():
        if r.tributo == "iof":
            assert r.ncm == ""
        else:
            assert politicas.NCM.match(r.ncm), r.ncm
            assert politicas.ncm_digitos(r.ncm).startswith(("8703", "8704"))


def test_mensal_cobre_cada_ato(atos):
    mensal = politicas.mensal(atos, config.PERIODO_INICIO, config.PERIODO_FIM)
    antecedentes = set(atos.loc[(atos["vigencia_fim"] != "")
                                & (atos["vigencia_fim"] < f"{config.PERIODO_INICIO}-01"), "id"])
    assert set(mensal["ato_id"]) == set(atos["id"]) - antecedentes
    assert not mensal.duplicated(["mes_ref", "ato_id"]).any()
    for r in atos[~atos["id"].isin(antecedentes)].itertuples():
        meses = mensal.loc[mensal["ato_id"] == r.id, "mes_ref"]
        assert meses.min() == max(r.vigencia_inicio[:7], config.PERIODO_INICIO), r.id
        fim = r.vigencia_fim[:7] if r.vigencia_fim else config.PERIODO_FIM
        assert meses.max() == min(fim, config.PERIODO_FIM), r.id


# ---------------------------------------------------------------- regras


def _atos(*linhas):
    base = {c: "" for c in politicas.COLUNAS_ATOS}
    return pd.DataFrame([{**base, **l} for l in linhas], columns=politicas.COLUNAS_ATOS)


def _aliquotas(*linhas):
    base = {c: "" for c in politicas.COLUNAS_ALIQUOTAS}
    return pd.DataFrame([{**base, **l} for l in linhas], columns=politicas.COLUNAS_ALIQUOTAS)


def test_partes_do_trecho_com_espacos_normalizados():
    texto = politicas.normalizar("Art. 1o Ficam\nalteradas   as aliquotas [...] Art. 4o vigor")
    assert politicas.partes_ausentes("Ficam alteradas [...] Art. 4o vigor", texto) == []
    assert politicas.partes_ausentes("Ficam alteradas [...] Art. 5o", texto) == ["Art. 5o"]


def test_ncm_digitos():
    assert politicas.ncm_digitos("8703.23.10 Ex 01") == "87032310"
    assert politicas.ncm_digitos("8703.80.00 Ex 007") == "87038000"
    assert politicas.ncm_digitos("8703.22") == "870322"


def test_mensal_conta_dias_do_primeiro_e_do_ultimo_mes():
    atos = _atos({"id": "a", "tema": "ipi", "sentido": "reduz",
                  "vigencia_inicio": "2012-05-22", "vigencia_fim": "2012-08-31"},
                 {"id": "b", "tema": "credito", "sentido": "aumenta",
                  "vigencia_inicio": "2015-01-22", "vigencia_fim": ""})
    m = politicas.mensal(atos, "2003-01", "2015-03")
    a = m[m["ato_id"] == "a"].set_index("mes_ref")
    assert list(a.index) == ["2012-05", "2012-06", "2012-07", "2012-08"]
    assert a.loc["2012-05", "dias_em_vigor"] == 10 and a.loc["2012-05", "comeca_no_mes"]
    assert a.loc["2012-08", "termina_no_mes"] and a.loc["2012-08", "fracao_do_mes"] == 1
    b = m[m["ato_id"] == "b"]
    assert list(b["mes_ref"]) == ["2015-01", "2015-02", "2015-03"]
    assert not b["termina_no_mes"].any()


def test_lacuna_de_categoria_e_apontada():
    rotulo = politicas.CATEGORIAS_IPI["g1"]
    linhas = []
    for chave, cat in politicas.CATEGORIAS_IPI.items():
        ini = politicas.INICIO_CATEGORIA[chave] or "2003-01-01"
        if cat == rotulo:
            linhas += [{"tributo": "ipi", "categoria_ipi": cat, "vigencia_inicio": ini,
                        "vigencia_fim": "2009-03-31"},
                       {"tributo": "ipi", "categoria_ipi": cat, "vigencia_inicio": "2009-05-01",
                        "vigencia_fim": ""}]
        else:
            linhas.append({"tributo": "ipi", "categoria_ipi": cat, "vigencia_inicio": ini,
                           "vigencia_fim": ""})
    lacunas = politicas.lacunas_do_ipi(_aliquotas(*linhas), "2003-01", "2026-08")
    assert lacunas == [{"categoria": rotulo, "de": "2009-04-01", "ate": "2009-04-30"}]


def test_sobreposicao_de_aliquotas_e_apontada():
    tabela = _aliquotas(
        {"tributo": "ipi", "ncm": "8703.22", "categoria": "flex", "ato_id": "x",
         "vigencia_inicio": "2011-12-16", "vigencia_fim": "2012-12-31"},
        {"tributo": "ipi", "ncm": "8703.22", "categoria": "flex", "ato_id": "y",
         "vigencia_inicio": "2012-05-22", "vigencia_fim": "2012-08-31"},
        {"tributo": "ipi", "ncm": "8703.22", "categoria": "gasolina", "ato_id": "z",
         "vigencia_inicio": "2012-05-22", "vigencia_fim": ""})
    problemas = politicas.sobreposicoes(tabela)
    assert len(problemas) == 1 and "x" in problemas[0] and "y" in problemas[0]


def test_ato_com_campo_fora_da_lista_e_trecho_inventado():
    manifesto = pd.DataFrame([{"nome": "p", "url": "https://www.planalto.gov.br/d.htm"}])
    atos = _atos({"id": "a", "tema": "ipi", "instrumento": "decreto", "sentido": "corta",
                  "data_ato": "2012-05-21", "vigencia_inicio": "2012-05-22",
                  "altera_id": "nenhum", "fonte_url": "https://www.planalto.gov.br/d.htm",
                  "tipo_fonte": "oficial", "pagina_salva": "p",
                  "fonte_trecho": "texto que ninguem leu"})
    problemas = politicas.problemas_dos_atos(atos, manifesto, {"p": "outro texto"},
                                             {"gov.br": "oficial"})
    assert any("sentido" in p for p in problemas)
    assert any("altera_id" in p for p in problemas)
    assert any("trecho fora da pagina" in p for p in problemas)


def test_fonte_nao_oficial_e_recusada():
    manifesto = pd.DataFrame([{"nome": "p", "url": "https://www.jornal.com.br/n"}])
    atos = _atos({"id": "a", "tema": "ipi", "instrumento": "decreto", "sentido": "reduz",
                  "data_ato": "2012-05-21", "vigencia_inicio": "2012-05-22",
                  "fonte_url": "https://www.jornal.com.br/n", "tipo_fonte": "oficial",
                  "pagina_salva": "p", "fonte_trecho": "reduz"})
    problemas = politicas.problemas_dos_atos(atos, manifesto, {"p": "reduz"},
                                             {"gov.br": "oficial"})
    assert problemas == ["a: fonte nao e' oficial"]


def test_comparar_usa_o_ano_anterior_como_movimento_sazonal():
    meses = [f"{a}-{m:02d}" for a in (2011, 2012) for m in range(1, 13)]
    # mesmo padrao nos dois anos: sem movimento
    serie = pd.Series([100, 100, 100, 100, 120, 120, 120, 120, 100, 100, 100, 100] * 2,
                      index=meses, dtype=float)
    r = politicas.comparar(serie, "2012-05-22")
    assert r["media_3m_antes"] == 100 and r["mes_do_ato"] == 120
    assert r["var_mes_pct"] == r["var_mes_ano_anterior_pct"] == 20.0
    assert r["movimento"] == "nao"
    # salto so' em 2012: movimento
    serie["2012-05":"2012-08"] = 160
    assert politicas.comparar(serie, "2012-05-22")["movimento"] == "sim"
    # janela fora da serie
    assert politicas.comparar(serie, "2012-11-01")["movimento"] == "fora da serie"


def test_eventos_incluem_degraus_do_proprio_ato():
    atos = _atos({"id": "g", "tema": "imposto_importacao", "vigencia_inicio": "2024-01-01"})
    tabela = _aliquotas(
        {"tributo": "ii", "ncm": "8703.80.00 Ex 001", "ato_id": "g",
         "vigencia_inicio": "2024-01-01"},
        {"tributo": "ii", "ncm": "8703.80.00 Ex 001", "ato_id": "g",
         "vigencia_inicio": "2024-07-01"})
    ev = politicas.eventos(atos, tabela)
    assert list(ev["data"]) == ["2024-01-01", "2024-07-01"]
    assert list(ev["evento"]) == ["inicio do ato", "mudanca de aliquota fixada pelo ato"]
