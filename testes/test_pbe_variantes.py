"""Versoes eletrificadas do PBE sem casamento: busca, teste da planilha e decisoes.

Casos construidos para a busca por palavra inteira e para o teste da planilha; os
ultimos testes conferem as decisoes de `config/pbe_modelos.csv` contra a planilha
versionada e a lista de candidatos versionada.
"""

import pandas as pd
import pytest

from comum import config, pbe_variantes as pv


@pytest.mark.parametrize("nome,modelo,esperado", [
    ("E-208 GT", "208", "prefixo"),
    ("IX3 50 XDRIVE MSP", "X3", "prefixo"),
    ("E-TRANSIT 350 F", "TRANSIT", "prefixo"),
    ("E-TRANSIT 350 F", "ETRANSIT", "mesmo_nome"),
    ("E-TRON GT -", "E TRON GT", "mesmo_nome"),
    ("CLA 200 AMG LINE", "CLA200", "mesmo_nome"),
    ("AMG CLA35 4M", "CLA35", "mesmo_nome"),
    ("320 ESPRINTER C", "ESPRINTER 320", "mesmo_nome"),
    ("320 E SPRINTER CHASSI", "ESPRINTER 320", "mesmo_nome"),
    ("320 E SPRINTER CHASSI", "SPRINTER", "prefixo"),
    ("G CHEROKEE 4XE", "CHEROKEE", "contem"),
    ("AMG GLC43 COUPE (2025)", "GLC", "sufixo"),
    ("AMG GLC63S EP", "GLC", "sufixo"),
    ("RAV4H S AWD CNT", "RAV4", "sufixo"),
    ("ES300H -", "ES300", "sufixo"),
    # palavra inteira, nao substring
    ("A4 QUATTRO", "TT", ""),
    ("AMG GLB 35 4M", "GL", ""),
    ("IX M60", "M6", ""),
    ("ONIX PLUS", "ON", ""),
])
def test_relacao_por_palavra_inteira(nome, modelo, esperado):
    assert pv.relacao(nome, modelo) == esperado


def _decisoes(*linhas):
    return pd.DataFrame([{"marca_painel": m, "modelo_painel": n, "prefixo_pbe": p,
                          "decisao": d, "observacao": o} for m, n, p, d, o in linhas])


def test_casa_vale_com_fronteira_de_palavra_e_as_outras_por_prefixo():
    decisoes = _decisoes(("M.BENZ", "GLC", "AMG GLC", "casa", "a"),
                         ("M.BENZ", "GLC", "AMG GLC43", "sem_evidencia", "b"))
    assert pv.decisao_da_versao("M.BENZ", "GLC", "AMG GLC 43 4M", decisoes)[0] == "casa"
    assert pv.decisao_da_versao("M.BENZ", "GLC", "AMG GLC43 COUPE", decisoes)[:2] == (
        "sem_evidencia", "AMG GLC43")
    assert pv.decisao_da_versao("M.BENZ", "GLC", "AMG GLC63S EP", decisoes)[0] == ""


def _cruzada(*linhas):
    """(mes, marca do painel, modelo, unidades no painel, marca da planilha, unidades
    na planilha)."""
    return pd.DataFrame([{"mes_ref": m, "marca": mp, "modelo": mo, "unidades_painel": up,
                          "marca_planilha_grafia": ml, "unidades_planilha": ul}
                         for m, mp, mo, up, ml, ul in linhas])


def test_planilha_soma_nao_soma_e_contraditoria():
    soma = _cruzada(("2023-02", "PEUGEOT", "208", 1163, "Peugeot", 1160),
                    ("2023-02", "", "E 208", 0, "Peugeot", 3))
    teste = pv.teste_da_planilha(soma, "208", "E 208", {"PEUGEOT"}, {"Peugeot"})
    assert teste["resultado"].tolist() == ["soma"] and pv.veredito(teste) == "soma"
    nao = _cruzada(("2023-02", "PEUGEOT", "2008", 91, "Peugeot", 91),
                   ("2023-02", "", "E 2008", 0, "Peugeot", 9))
    assert pv.veredito(pv.teste_da_planilha(nao, "2008", "E 2008", {"PEUGEOT"},
                                            {"Peugeot"})) == "nao_soma"
    mista = pd.concat([soma, nao.assign(mes_ref="2023-03", modelo=["208", "E 208"])])
    assert pv.veredito(pv.teste_da_planilha(mista, "208", "E 208", {"PEUGEOT"},
                                            {"Peugeot"})) == "contraditorio"


# ------------------------------------------------------- dado versionado


@pytest.fixture(scope="module")
def cruzada():
    caminho = config.DIR_SAIDAS / "referencia_cruzada.csv"
    if not caminho.exists():
        pytest.skip("sem referencia cruzada")
    return pd.read_csv(caminho, dtype={"mes_ref": str})


@pytest.mark.parametrize("base,variante,marcas_painel,marcas_planilha,esperado", [
    ("208", "E 208", {"PEUGEOT"}, {"Peugeot"}, "soma"),
    ("2008", "E 2008", {"PEUGEOT"}, {"Peugeot"}, "nao_soma"),
    ("X3", "IX3", {"BMW"}, {"BMW"}, "nao_soma"),
    ("ARRIZO 5", "ARRIZO 5E", {"CHERY", "CAOA CHERY"}, {"CAOA Chery"}, "contraditorio"),
])
def test_decisoes_pela_planilha_batem_com_a_planilha(cruzada, base, variante, marcas_painel,
                                                       marcas_planilha, esperado):
    teste = pv.teste_da_planilha(cruzada, base, variante, marcas_painel, marcas_planilha)
    assert pv.veredito(teste) == esperado


def test_toda_variante_viva_tem_decisao_valida():
    decisoes = pv.carregar_decisoes()
    assert set(decisoes["decisao"]) <= set(pv.DECISOES)
    nao_casa = decisoes[decisoes["decisao"] != "casa"]
    assert (nao_casa["observacao"] != "").all(), "decisao sem evidencia na observacao"
    candidatos = pv.ler_candidatos()
    if candidatos.empty:
        pytest.skip("candidatos ainda nao gravados")
    sem = candidatos[candidatos["chave_viva"] & (candidatos["decisao"] == "")]
    assert sem.empty, sem[["marca", "modelo", "modelo_versao"]].to_string()
    # `casa` some da lista: a versao passa a casar
    assert not (candidatos["decisao"] == "casa").any()


def test_lista_sem_evidencia_cobre_os_candidatos_sem_decisao_de_casamento():
    if not config.PBE_VARIANTES_SEM_EVIDENCIA.exists():
        pytest.skip("lista ainda nao gravada")
    lista = pd.read_csv(config.PBE_VARIANTES_SEM_EVIDENCIA, dtype=str, keep_default_na=False)
    candidatos = pv.ler_candidatos()
    abertos = candidatos[candidatos["chave_viva"]
                         & ~candidatos["decisao"].isin(["casa", "nao_casa"])]
    esperado = set(map(tuple, abertos[["marca", "modelo", "valor_taxonomia"]].to_numpy()))
    assert set(map(tuple, lista[["marca", "modelo", "valor_taxonomia"]].to_numpy())) == esperado
