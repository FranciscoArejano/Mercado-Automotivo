"""Origem por pais e por fabrica (rodada 12, sec. 2): fontes com trecho literal, pais do
Comex, municipio do IBGE, proposta completa e a regra de derivacao.

Guardas sobre as tabelas versionadas (`dados/referencia/fabricas.csv`,
`fabrica_modelos.csv`, `origem_pais_proposta.csv`): cada trecho (partes separadas por
' [...] ') esta' literalmente na pagina guardada, o texto bate com o SHA-256 do manifesto,
a URL e' a da pagina, o tipo da fonte vem do dominio. E a regra mes a mes, com casos
pequenos.
"""

import hashlib

import pandas as pd
import pytest

from comum import anfavea, config, tipo_fonte
from comum import origem_pais as op


@pytest.fixture(scope="module")
def fabricas():
    return op.carregar_fabricas()


@pytest.fixture(scope="module")
def fm():
    return op.carregar_fabrica_modelos()


@pytest.fixture(scope="module")
def proposta():
    return op.carregar_proposta()


@pytest.fixture(scope="module")
def manif():
    return op.manifestos()


@pytest.fixture(scope="module")
def urls(manif):
    return op.url_das_paginas(manif)


@pytest.fixture(scope="module")
def textos(fabricas, fm):
    return op.textos(op.paginas_citadas(fabricas, fm))


@pytest.fixture(scope="module")
def classificacao():
    if not config.CLASSIFICACAO.exists():
        pytest.skip("sem classificacao.parquet")
    return pd.read_parquet(config.CLASSIFICACAO)


@pytest.fixture(scope="module")
def vigencias(classificacao):
    return classificacao[classificacao["procedencia_origem"] != "nao_classificado"]


# ------------------------------------------------------- tabelas versionadas


def test_paginas_batem_com_o_manifesto(manif, fabricas, fm):
    citadas = op.paginas_citadas(fabricas, fm)
    assert op.problemas_das_paginas(manif, citadas) == []
    for pasta in ("fabricas_paginas", "anfavea"):
        for r in manif[pasta].itertuples():
            bruto = (op.PASTAS[pasta] / f"{r.nome}.txt").read_bytes()
            assert hashlib.sha256(bruto).hexdigest() == r.sha256_texto, r.nome


def test_trecho_de_cada_linha_esta_na_pagina(fabricas, fm, textos):
    for r in fm.itertuples():
        assert r.fonte_trecho, (r.marca, r.modelo, r.periodo_inicio)
        assert op.partes_ausentes(r.fonte_trecho, textos[r.pagina_salva]) == [], \
            (r.marca, r.modelo, r.periodo_inicio)
    for r in fabricas[fabricas["pagina_salva"] != ""].itertuples():
        assert op.partes_ausentes(r.fonte_trecho, textos[r.pagina_salva]) == [], r.fabrica_id


def test_url_e_a_da_pagina_e_o_tipo_vem_do_dominio(fabricas, fm, urls):
    mapa = tipo_fonte.carregar_mapa()
    linhas = pd.concat([fm[["pagina_salva", "fonte_url", "tipo_fonte"]],
                        fabricas.loc[fabricas["pagina_salva"] != "",
                                     ["pagina_salva", "fonte_url", "tipo_fonte"]]])
    for r in linhas.itertuples():
        assert urls[r.pagina_salva] == r.fonte_url, r.pagina_salva
        assert r.tipo_fonte and r.tipo_fonte == tipo_fonte.tipo_de(r.fonte_url, mapa), r.fonte_url


def test_fabricas_sem_problema(fabricas, urls, textos):
    assert op.problemas_das_fabricas(fabricas, urls, textos) == []


def test_pais_do_comex_e_municipio_do_ibge(fabricas, fm, proposta):
    paises = op.paises_comex()
    ibge = op.municipios_ibge()
    assert set(fabricas["pais"]) | set(fm["pais"]) | set(proposta["pais"]) <= set(paises)
    assert set(proposta["pais_do_kit"]) - {""} <= set(paises)
    br = fabricas[fabricas["pais"] == op.BRASIL]
    for r in br.itertuples():
        assert ibge[(r.municipio, r.uf)] == r.cod_ibge_municipio, r.fabrica_id


def test_fabrica_modelos_sem_problema(fm, fabricas, classificacao, urls, textos):
    chaves = set(map(tuple, classificacao[op.CHAVE].values))
    assert op.problemas_de_fabrica_modelos(fm, fabricas, chaves, urls, textos) == []


def test_proposta_cobre_todo_mes_classificado(proposta, fabricas, vigencias):
    assert op.problemas_da_proposta(proposta, fabricas, vigencias) == []


def test_anfavea_lida_e_conferida():
    serie, paises = anfavea.series(), anfavea.por_pais()
    assert anfavea.problemas(serie, paises) == []
    assert set(paises["pais"]) - {"TOTAL", "Outros"} <= set(op.paises_comex())
    # 2025, importados: automoveis 356.094, comerciais leves 135.808 (tabela 2.2.4)
    imp = serie[(serie["ano"] == 2025) & (serie["tabela"] == "importados")].iloc[0]
    assert (imp["automoveis"], imp["comerciais_leves"]) == (356094, 135808)


# ------------------------------------------------------------------ produto


def test_produto_gravado_sem_problema(vigencias, fabricas):
    if not config.CLASSIFICACAO_ORIGEM.exists():
        pytest.skip("sem classificacao_origem.parquet")
    prod = pd.read_parquet(config.CLASSIFICACAO_ORIGEM)
    assert list(prod.columns) == op.COLUNAS_PRODUTO
    assert op.problemas_do_produto(prod, vigencias, fabricas) == []


# ------------------------------------------------------------ casos pequenos


def _p(pais, ini="2010-01", fim="2010-12", fab="", kit="", obs=""):
    return {"marca": "X", "modelo": "Y", "segmento": "automoveis", "periodo_inicio": ini,
            "periodo_fim": fim, "pais": pais, "fabrica_id": fab, "pais_do_kit": kit,
            "observacao": obs}


def _f(pais, vinculo, ini="2010-01", fim="2010-12", fab="", tipo="imprensa_especializada",
       i=0):
    return {"marca": "X", "modelo": "Y", "segmento": "automoveis", "periodo_inicio": ini,
            "periodo_fim": fim, "pais": pais, "fabrica_id": fab, "vinculo": vinculo,
            "tipo_fonte": tipo, "_i": i}


def test_producao_local_confirma_o_brasil_e_da_a_fabrica():
    m = op.derivar_mes([_p("Brasil", fab="a")], [_f("Brasil", "producao_local", fab="b")],
                       "2010-05")
    assert m.paises["Brasil"]["procedencia"] == "regra_fonte_forte"
    assert m.paises["Brasil"]["fabricas"] == ("b",)
    assert m.paises["Brasil"]["fabrica_procedencia"] == "fonte"


def test_fonte_vale_so_no_periodo_que_trata():
    m = op.derivar_mes([_p("Brasil", fab="a")],
                       [_f("Brasil", "producao_local", ini="2010-01", fim="2010-03")], "2010-05")
    assert m.paises["Brasil"]["procedencia"] == "proposta"
    assert m.paises["Brasil"]["fabricas"] == ("a",)


def test_producao_no_exterior_so_confirma_pais_proposto():
    m = op.derivar_mes([_p("Argentina")], [_f("Argentina", "producao_no_exterior", fab="ar")],
                       "2010-05")
    assert m.paises["Argentina"]["procedencia"] == "regra_fonte_forte"
    m = op.derivar_mes([_p("Brasil")], [_f("Argentina", "producao_no_exterior", fab="ar")],
                       "2010-05")
    assert m.contradicao == "" and m.paises["Brasil"]["procedencia"] == "proposta"


def test_fonte_com_vinculo_fora_da_proposta_e_pendente():
    m = op.derivar_mes([_p("Tailândia")], [_f("China", "abastece_o_brasil", i=7)], "2010-05")
    assert "China" in m.contradicao
    assert m.contra == (7,)
    assert list(m.paises) == ["Tailândia"]
    assert m.paises["Tailândia"]["procedencia"] == "pendente"


def test_fonte_fraca_e_dois_paises_no_mes():
    m = op.derivar_mes([_p("Brasil"), _p("China")],
                       [_f("China", "abastece_o_brasil", tipo="imprensa_geral")], "2010-05")
    assert m.paises["China"]["procedencia"] == "regra_fonte_fraca"
    assert m.paises["Brasil"]["procedencia"] == "proposta"
    assert op.origem_de(m.paises) == "ambos"


def test_meses_iguais_viram_um_periodo():
    vig = pd.DataFrame([{"marca": "X", "modelo": "Y", "segmento": "automoveis",
                         "vigencia_inicio": "2010-01", "vigencia_fim": "2010-06"}])
    prop = pd.DataFrame([_p("Brasil", "2010-01", "2010-06")])
    fon = pd.DataFrame([_f("Brasil", "producao_local", "2010-03", "2010-04")]).drop(columns="_i")
    per = op.em_periodos(op.derivar_meses(vig, prop, fon))
    assert list(zip(per["periodo_inicio"], per["periodo_fim"], per["procedencia"])) == [
        ("2010-01", "2010-02", "proposta"), ("2010-03", "2010-04", "regra_fonte_forte"),
        ("2010-05", "2010-06", "proposta")]


def test_regra_de_periodo_incoerente_e_apontada(fabricas):
    linha = {"fabrica_id": "", "pais": "Brasil", "marca": "X", "modelo": "Y",
             "segmento": "automoveis", "periodo_inicio": "2010-01", "periodo_fim": "2010-03",
             "vinculo": "producao_local", "regra_periodo": "na_data_da_pagina",
             "data_fonte": "2010-01", "fonte_url": "u", "tipo_fonte": "oficial",
             "fonte_trecho": "inventado", "pagina_salva": "fabricas_paginas/nao_existe",
             "observacao": ""}
    problemas = op.problemas_de_fabrica_modelos(pd.DataFrame([linha]), fabricas,
                                                {("X", "Y", "automoveis")}, {}, {})
    assert any("na_data_da_pagina" in p for p in problemas)
    assert any("fora dos manifestos" in p for p in problemas)


def test_trecho_inventado_e_recusado():
    assert op.partes_ausentes("existe [...] inventado", "o texto existe aqui") == ["inventado"]


def test_fora_de_operacao_com_ano_ou_mes():
    assert op._fora_de_operacao("2019-05", "2020", "")
    assert not op._fora_de_operacao("2020-01", "2020", "")
    assert op._fora_de_operacao("2021-02", "", "2021-01")
    assert not op._fora_de_operacao("2021-12", "", "2021")


def test_aba_origem_pais_do_rascunho_e_fiel_as_divergencias():
    if not (config.ORIGEM_DIVERGENCIAS.exists() and config.CLASSIFICACAO_RASCUNHO.exists()):
        pytest.skip("sem divergencias ou rascunho")
    div = pd.read_csv(config.ORIGEM_DIVERGENCIAS, dtype=str, keep_default_na=False)
    aba = pd.read_excel(config.CLASSIFICACAO_RASCUNHO, sheet_name="origem_pais", dtype=str,
                        keep_default_na=False)
    assert list(aba.columns) == list(div.columns) + ["decisao_humana"]
    pd.testing.assert_frame_equal(aba[div.columns].reset_index(drop=True), div)
