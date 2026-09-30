"""Dimensao macro: encadeamento do IPCA e disciplina de lacuna.

A emenda de quatro tabelas do SIDRA e' onde mora o risco: contar a variacao de
um mes duas vezes desloca o indice inteiro dali para a frente, e em silencio.
"""

import pandas as pd

from comum import macro


def _variacoes(pares):
    return pd.DataFrame(
        [{"mes_ref": m, "variacao_pct": v, "tabela_sidra": t} for m, v, t in pares]
    )


def test_indice_encadeado_parte_da_base_declarada():
    saida = macro.encadear(
        _variacoes([("2003-01", 0.0, 655), ("2003-02", 10.0, 655),
                    ("2003-03", 10.0, 655)]), "2003-01")
    assert float(saida.loc[0, "indice"]) == 100.0
    assert round(float(saida.loc[1, "indice"]), 2) == 110.0
    assert round(float(saida.loc[2, "indice"]), 2) == 121.0


def test_base_no_meio_da_serie_normaliza_para_tras_e_para_frente():
    saida = macro.encadear(
        _variacoes([("2003-01", 10.0, 655), ("2003-02", 10.0, 655),
                    ("2003-03", 10.0, 655)]), "2003-02")
    assert round(float(saida.loc[1, "indice"]), 2) == 100.0
    assert round(float(saida.loc[0, "indice"]), 2) == 90.91
    assert round(float(saida.loc[2, "indice"]), 2) == 110.0


def test_mes_sem_variacao_nao_ganha_indice_inventado():
    # Lacuna e' lacuna (sec.9.2): nao se estende com o ultimo valor.
    saida = macro.encadear(
        _variacoes([("2003-01", 0.0, 655), ("2003-02", None, 655),
                    ("2003-03", 5.0, 655)]), "2003-01")
    assert pd.isna(saida.loc[1, "indice"])
    assert not pd.isna(saida.loc[2, "indice"])


def test_juncao_entre_tabelas_nao_conta_o_mes_duas_vezes():
    # As janelas se encaixam: jun/2006 fecha a 655, jul/2006 abre a 2938.
    emendas = macro.juncoes_das_tabelas(_variacoes([
        ("2006-05", 0.1, 655), ("2006-06", 0.2, 655),
        ("2006-07", -0.42, 2938), ("2006-08", 0.3, 2938),
    ]))
    assert len(emendas) == 1
    linha = emendas.iloc[0]
    assert linha["mes_anterior"] == "2006-06" and linha["tabela_anterior"] == 655
    assert linha["mes_ref"] == "2006-07" and linha["tabela_sidra"] == 2938
    assert int(linha["meses_duplicados"]) == 0


def test_mes_repetido_entre_tabelas_e_denunciado():
    # Se duas tabelas publicarem o mesmo mes, a emenda tem de acusar.
    emendas = macro.juncoes_das_tabelas(_variacoes([
        ("2006-06", 0.2, 655), ("2006-06", 0.25, 2938), ("2006-07", 0.3, 2938),
    ]))
    assert int(emendas.iloc[0]["meses_duplicados"]) == 1


def test_serie_vazia_nao_quebra():
    vazio = pd.DataFrame(columns=["mes_ref", "variacao_pct", "tabela_sidra"])
    assert macro.encadear(vazio, "2003-01").empty
    assert macro.juncoes_das_tabelas(vazio).empty


def test_catalogo_traz_fonte_e_unidade_em_toda_linha():
    # Mesma disciplina do mapa_grupos.csv: nenhuma serie sem procedencia.
    catalogo = macro.carregar_catalogo()
    assert catalogo, "config/series_macro.csv vazio"
    for linha in catalogo:
        assert linha["fonte"].strip(), f"{linha['codigo']} sem fonte"
        assert linha["unidade"].strip(), f"{linha['codigo']} sem unidade"
        assert linha["data_coleta"].strip(), f"{linha['codigo']} sem data de coleta"
        assert linha["situacao_da_serie"].strip(), f"{linha['codigo']} sem situacao"


def test_serie_que_comeca_depois_nao_ganha_emenda_de_inicio():
    # O automovel usado e' aceito pela tabela 655 mas vem como '...' nela toda.
    # A serie COMECA em 2006-07; nao ha' juncao 655 -> 2938 ali, e a tabela de
    # emendas nao pode afirmar uma juncao que nao aconteceu.
    emendas = macro.juncoes_das_tabelas(_variacoes([
        ("2006-05", None, 655), ("2006-06", None, 655),
        ("2006-07", -0.42, 2938), ("2006-08", 0.3, 2938),
        ("2011-12", 0.1, 2938), ("2012-01", -1.08, 1419),
    ]))
    assert list(emendas["mes_ref"]) == ["2012-01"]
    assert int(emendas.iloc[0]["tabela_anterior"]) == 2938


def test_base_efetiva_quando_a_serie_comeca_depois_da_declarada():
    variacoes = _variacoes([("2003-01", None, 655), ("2006-06", None, 655),
                            ("2006-07", -0.42, 2938)])
    assert macro.base_efetiva(variacoes, "2003-01") == "2006-06"


def test_base_efetiva_igual_a_declarada_quando_ha_dado_nela():
    variacoes = _variacoes([("2003-01", 0.1, 655), ("2003-02", 0.2, 655)])
    assert macro.base_efetiva(variacoes, "2003-01") == "2003-01"


def test_catalogo_traz_natureza_e_ressalvas_em_toda_linha():
    for linha in macro.carregar_catalogo():
        assert linha.get("natureza_e_ressalvas", "").strip(), \
            f"{linha['codigo']} sem natureza_e_ressalvas"


def test_usado_esta_declarado_como_indice_de_depreciacao():
    # Usar o subitem de usado como preco do bem substituto e' erro conceitual.
    # A ressalva tem de estar no catalogo, e nao so' em quem ja' sabe.
    usado = next(l for l in macro.carregar_catalogo() if l["codigo"] == "ipca_107654")
    assert "DEPRECIACAO" in usado["natureza_e_ressalvas"].upper()
