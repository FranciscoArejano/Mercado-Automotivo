"""Validacao do rascunho contra fonte: mapeamento do PBE, casamento e comparacao."""

import pandas as pd
import pytest

from comum import validacao_classificacao as v


@pytest.fixture(scope="module")
def regras():
    return v.regras_propulsao()


@pytest.mark.parametrize("tipo,combustivel,marcador,motor,esperado", [
    ("HIBRIDO", "G", "MHEV", "1.0", "mhev"),      # Kia Stonic MHEV, 2021
    ("COMBUSTAO", "G", "MHEV", "2.0", "mhev"),    # Subaru XV MHEV, 2021: o nome manda
    ("PLUG-IN", "G", "REEV", "1.5", "reev"),      # Leapmotor C10 REEV, 2026
    ("HIBRIDO", "G", "PHEV", "2.0", "phev"),      # Range Rover PHEV, 2021: o nome manda
    ("HIBRIDO", "F", "", "1.8", "hev"),
    ("PLUG-IN", "G", "", "2.0", "phev"),
    ("ELETRICO", "E", "", "ELETRICO", "bev"),
    ("COMBUSTAO", "F", "", "1.0", "flex"),
    ("COMBUSTAO", "D", "", "2.8", "diesel"),
    ("COMBUSTAO", "E", "", "1.0", ""),            # so' etanol: sem valor na lista
    ("", "G", "HYBRID", "2.5", "hev"),            # ate' 2020, so' o nome diz
    ("", "G", "E-TRON", "1.4", ""),               # ambiguo sem a coluna
    ("", "E", "", "ELETRICO", "bev"),
    ("", "F", "", "1.6", "flex"),
])
def test_mapeamento_do_pbe(regras, tipo, combustivel, marcador, motor, esperado):
    valor, _ = v.mapear_propulsao(tipo, combustivel, marcador, motor, regras)
    assert valor == esperado


def _chaves(*modelos):
    return pd.DataFrame([dict(zip(v.CHAVE, m)) for m in modelos])


def _versao(marca, modelo_versao, ano="2024", valor="flex"):
    return {"ano_pbe": ano, "marca_pbe": marca, "modelo_versao": modelo_versao,
            "valor_taxonomia": valor}


def test_casamento_pelo_prefixo_mais_longo_e_com_fronteira_de_palavra():
    chaves = _chaves(("TOYOTA", "COROLLA", "automoveis"), ("TOYOTA", "COROLLA CROSS", "automoveis"),
                     ("HYUNDAI", "HB20", "automoveis"), ("HYUNDAI", "HB20S", "automoveis"))
    versoes = pd.DataFrame([_versao("TOYOTA", "COROLLA CROSS XRE"),
                            _versao("TOYOTA", "COROLLA ALTIS HV"),
                            _versao("HYUNDAI", "HB20S COMFORT"),
                            _versao("HYUNDAI", "HB20 SENSE")])
    casado = v.casar(versoes, chaves)
    assert list(casado["modelo"]) == ["COROLLA CROSS", "COROLLA", "HB20S", "HB20"]


def test_casamento_traduz_a_marca_e_tira_o_prefixo_novo():
    chaves = _chaves(("GM", "ONIX", "automoveis"), ("VW", "GOL", "automoveis"),
                     ("CHERY", "TIGGO 7", "automoveis"), ("CAOA CHERY", "TIGGO 7", "automoveis"))
    versoes = pd.DataFrame([_versao("CHEVROLET", "ONIX LT"), _versao("VOLKSWAGEN", "NOVO GOL"),
                            _versao("CAOA CHERY", "TIGGO 7 PRO"), _versao("CHEVROLET", "XYZ")])
    casado = v.casar(versoes, chaves)
    assert ("GM", "ONIX") in set(zip(casado["marca"], casado["modelo"]))
    assert ("VW", "GOL") in set(zip(casado["marca"], casado["modelo"]))
    # a mesma versao vai para as duas chaves da Chery
    assert {("CAOA CHERY", "TIGGO 7"), ("CHERY", "TIGGO 7")} <= set(zip(casado["marca"], casado["modelo"]))
    assert (casado["modelo_versao"] == "XYZ").sum() == 1
    assert casado.loc[casado["modelo_versao"] == "XYZ", "marca"].item() == ""


def test_casamento_usa_a_linha_de_cima_so_quando_o_nome_nao_casa():
    """PBE 2017: NOVO ONIX numa linha, CHEVROLET 1.0MT LS ... na seguinte."""
    chaves = _chaves(("GM", "ONIX", "automoveis"), ("GM", "PRISMA", "automoveis"))
    versoes = pd.DataFrame([{**_versao("CHEVROLET", "LS"), "linha_acima": "NOVO ONIX"},
                            {**_versao("CHEVROLET", "PRISMA LT"), "linha_acima": "NOVO ONIX"},
                            {**_versao("CHEVROLET", "LS"), "linha_acima": "(MY17)"}])
    casado = v.casar(versoes, chaves)
    assert list(zip(casado["modelo"], casado["casou_por"])) == [
        ("ONIX", "linha_acima"), ("PRISMA", "nome"), ("", "")]


def _rascunho(*linhas):
    colunas = ["posicao", "marca", "modelo", "segmento", "vigencia_inicio", "vigencia_fim",
               "propulsao_oferecida", "unidades_na_vigencia", "observacao", "origem_producao",
               "confianca_origem"]
    return pd.DataFrame([dict(zip(colunas, linha)) for linha in linhas])


def _casado(*versoes):
    return pd.DataFrame([{"marca": m, "modelo": n, "segmento": "automoveis", "ano_pbe": a,
                          "valor_taxonomia": val} for m, n, a, val in versoes])


def test_comparacao_concorda_diverge_ausente():
    rascunho = _rascunho(
        (1, "T", "A", "automoveis", "2015-01", "2024-12", "flex", 100, "", "nacional", "alta"),
        (2, "T", "B", "automoveis", "2015-01", "2024-12", "flex", 90, "", "nacional", "alta"),
        (3, "T", "C", "automoveis", "2015-01", "2024-12", "flex", 80, "", "nacional", "alta"),
    )
    casado = _casado(("T", "A", "2020", "flex"), ("T", "B", "2021", "flex"),
                     ("T", "B", "2022", "hev"))
    saida = v.comparar_pbe(rascunho, casado).set_index("modelo")
    assert saida.loc["A", "pbe_situacao"] == "concorda"
    assert saida.loc["B", "pbe_situacao"] == "diverge"
    assert saida.loc["B", "pbe_diferenca"] == "so' no PBE: hev"
    assert saida.loc["B", "pbe_anos"] == "2021-2022"
    assert saida.loc["C", "pbe_situacao"] == "ausente"   # ausencia nao vira combustao
    assert saida.loc["C", "pbe_propulsao"] == ""


def test_gasolina_da_transicao_flex_nao_e_divergencia():
    rascunho = _rascunho(
        (1, "VW", "GOL", "automoveis", "2003-01", "2020-12", "gasolina+flex", 100, "",
         "nacional", "alta"))
    saida = v.comparar_pbe(rascunho, _casado(("VW", "GOL", "2012", "flex")))
    assert saida.loc[0, "pbe_situacao"] == "concorda"
    assert "transicao flex" in saida.loc[0, "pbe_nota"]


def test_ano_do_pbe_vai_para_a_vigencia_com_mais_meses_nele():
    rascunho = _rascunho(
        (1, "T", "COROLLA", "automoveis", "2003-01", "2019-09", "flex", 100, "", "nacional", "alta"),
        (1, "T", "COROLLA", "automoveis", "2019-10", "2026-08", "flex+hev", 50, "", "nacional", "media"),
    )
    casado = _casado(("T", "COROLLA", "2019", "flex"), ("T", "COROLLA", "2020", "flex"),
                     ("T", "COROLLA", "2020", "hev"))
    saida = v.comparar_pbe(rascunho, casado)
    assert list(saida["pbe_anos"]) == ["2019", "2020"]
    assert list(saida["pbe_situacao"]) == ["concorda", "concorda"]


def test_origem_anexada_sem_tocar_na_proposta_e_vai_para_adjudicacao():
    rascunho = _rascunho(
        (100, "BYD", "DOLPHIN MINI", "automoveis", "2024-03", "2026-08", "bev", 1000,
         "China.", "importado", "media"))
    rascunho = v.comparar_pbe(rascunho, _casado(("BYD", "DOLPHIN MINI", "2025", "bev")))
    rascunho["decisao_humana"] = ""
    fontes = pd.DataFrame([{"marca": "BYD", "modelo": "DOLPHIN MINI", "segmento": "automoveis",
                            "evento": "inicio_producao_local", "origem_data_fonte": "2025-10",
                            "origem_fonte_url": "https://exemplo", "origem_fonte_trecho": "t",
                            "confronto_com_proposta": "contradiz"}])
    saida = v.anexar_origem(rascunho, fontes)
    assert saida.loc[0, "origem_producao"] == "importado"     # proposta intacta
    assert saida.loc[0, "origem_situacao"] == "com_fonte_datada"
    fila = v.a_adjudicar(saida, top=241)
    assert len(fila) == 1 and "fonte de origem contradiz" in fila.iloc[0]["motivo"]
