"""Frota da Senatran: leitura dos tres formatos, harmonizacao de rotulos e produto."""

import io

import pandas as pd
import pytest

import etapa17_frota as etapa
from comum import config, frota


def _xlsx(linhas):
    buffer = io.BytesIO()
    pd.DataFrame(linhas).to_excel(buffer, header=False, index=False)
    return buffer.getvalue()


def test_municipio_tipo_com_glossario_cabecalho_repetido_e_traco():
    conteudo = _xlsx([["Frota de veiculos", None, None, None, None],
                      [None, None, 15, None, None],
                      ["UF", "MUNICIPIO", "TOTAL", "AUTOMOVEL", "MOTOCICLETA"],
                      ["UF", "MUNICIPIO", "TOTAL", "AUTOMOVEL", "MOTOCICLETA"],
                      ["AC", "ACRELANDIA", 10, 7, 3],
                      ["AC", "ASSIS BRASIL", 5, " -   ", 5]])
    quadro, info = frota.ler_municipio_tipo("x.xlsx", conteudo)
    assert info["total_publicado"] == 15 and info["tracos_zero"] == 1
    assert quadro["veiculos"].sum() == 15
    assert set(quadro["rotulo"]) == {"AUTOMOVEL", "MOTOCICLETA"}


def test_uf_tipo_ignora_regioes_e_le_brasil():
    conteudo = _xlsx([["Frota", None, None],
                      ["Grandes Regiões e\nUnidades da Federação", "TOTAL", "AUTOMÓVEL"],
                      ["Brasil", 30, 20], ["Norte", 30, 20], ["Acre ", 10, 5],
                      ["Rondônia", 20, 15]])
    q = frota.ler_uf_tipo("x.xlsx", conteudo)
    assert set(q["uf"]) == {"BR", "AC", "RO"}
    assert q[(q["uf"] == "RO") & (q["rotulo"] == "AUTOMÓVEL")]["veiculos"].item() == 15


def test_combustivel_com_uf_por_extenso():
    conteudo = _xlsx([["UF", "Município", "Combustível Veículo", "Qtd. Veículos"],
                      ["ACRE", "ACRELANDIA", "ALCOOL", 59],
                      ["SAO PAULO", "SANTOS", "ELETRICO/FONTE EXTERNA", 3]])
    q = frota.ler_municipio_combustivel("x.xlsx", conteudo)
    assert q["uf"].tolist() == ["AC", "SP"] and q["veiculos"].tolist() == [59, 3]


@pytest.mark.parametrize("nome,ano,dez", [
    ("Frota_Mun_Dez_03t.xls", 2003, True), ("Frota Munic 122005 Internet.xls", 2005, True),
    ("Frota Munic 112005 Internet.xls", 2005, False), ("12Frota_UF_Dez_04.xls", 2004, True),
    ("1Frota_UF_Jan_04.xls", 2004, False), ("Frota Munic DEZ2010.xls", 2010, True)])
def test_dezembro_dentro_do_zip(nome, ano, dez):
    assert frota.e_dezembro(nome, ano) is dez


def test_rotulo_fora_dos_anos_da_tabela_e_falta():
    rotulos = pd.DataFrame({"dimensao": ["tipo"], "rotulo_original": ["AUTOMOVEL"],
                            "rotulo_harmonizado": ["automovel"], "ano_inicial": [2003],
                            "ano_final": [2025], "observacao": [""]})
    quadro = pd.DataFrame({"mes": ["2025-12", "2026-01", "2026-01"], "recorte": ["tipo"] * 3,
                           "rotulo": ["AUTOMOVEL", "AUTOMOVEL", "MOTO"]})
    harmonizado, faltas = etapa.harmonizar(quadro, rotulos)
    assert harmonizado.iloc[0] == "automovel" and harmonizado.iloc[1:].isna().all()
    assert len(faltas) == 2


def test_tabela_de_rotulos_sem_duplicata_nem_buraco():
    rotulos = pd.read_csv(config.FROTA_ROTULOS, keep_default_na=False)
    assert not rotulos.duplicated(["dimensao", "rotulo_original"]).any()
    assert (rotulos["ano_inicial"] <= rotulos["ano_final"]).all()
    assert set(rotulos["dimensao"]) <= {"tipo", "combustivel"}
    assert (rotulos["rotulo_harmonizado"] != "").all()


@pytest.mark.skipif(not config.FROTA_MUNICIPAL.exists(), reason="produto ausente")
def test_produto_versionado():
    produto = pd.read_parquet(config.FROTA_MUNICIPAL)
    assert produto["cod_ibge_municipio"].str.fullmatch(r"\d{7}").all()
    assert not produto.duplicated(["mes", "cod_ibge_municipio", "recorte", "tipo_veiculo",
                                   "combustivel"]).any()
    tipo = produto[produto["recorte"] == "tipo"]
    assert (tipo["combustivel"] == "todos").all()
    meses = set(tipo["mes"])
    assert {f"{a}-12" for a in range(2003, 2020)} <= meses
    assert {"2020-01", "2023-07", "2026-01"} <= meses
    assert produto[produto["recorte"] == "combustivel"]["mes"].min() == "2013-12"
    validacao = pd.read_csv(config.FROTA_VALIDACAO)
    assert validacao["falhas"].sum() == 0
