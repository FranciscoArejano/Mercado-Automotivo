"""Precos de combustiveis (ANP): leitura do bruto, agregacao, deflator e produto."""

import pandas as pd
import pytest

import etapa18_precos as etapa
from coleta import anp_precos
from comum import config


def test_le_latin1_sem_bom_e_utf8_com_bom(tmp_path):
    cab = ";".join(["Regiao - Sigla"] + anp_precos.COLUNAS + ["Bandeira"])
    linha = "SE;SP;SÃO PAULO;12.345.678/0001-90;GASOLINA;03/01/2022;6,99;R$ / litro;X"
    outra = "SE;SP;SÃO PAULO;12.345.678/0001-90;GASOLINA ADITIVADA;03/01/2022;7,19;R$ / litro;X"
    (tmp_path / "a.csv").write_bytes(("\n".join([cab, linha, outra])).encode("latin-1"))
    (tmp_path / "b.csv").write_bytes(b"\xef\xbb\xbf" + "\n".join([cab, linha]).encode("utf-8"))
    for nome in ("a.csv", "b.csv"):
        t = anp_precos.ler_posto(tmp_path / nome).to_pandas()
        assert t["Municipio"].tolist() == ["SÃO PAULO"]  # so' os quatro produtos ficam
        assert t["Valor de Venda"].tolist() == ["6,99"]  # celula como texto, sem conta


def test_agregar_media_de_coletas_e_postos_distintos():
    q = pd.DataFrame({"Estado - Sigla": ["SP"] * 3, "Municipio": ["X"] * 3,
                      "CNPJ da Revenda": ["a", "a", "b"], "Produto": ["ETANOL"] * 3,
                      "Data da Coleta": ["01/01/2024", "08/01/2024", "01/01/2024"],
                      "Valor de Venda": ["3,00", "4,00", "5,00"],
                      "Unidade de Medida": ["R$ / litro"] * 3})
    a = etapa.agregar(etapa.preparar(q, "x"), ["mes", "uf", "produto"])
    assert a["soma"].item() == 12.0 and a["coletas"].item() == 3 and a["postos"].item() == 2


@pytest.mark.skipif(not config.PRECOS_COMBUSTIVEIS.exists(), reason="produto ausente")
def test_produto_versionado():
    uf = pd.read_parquet(config.PRECOS_COMBUSTIVEIS)
    assert uf["mes"].min() == "2004-05"
    assert not uf.duplicated(["mes", "uf", "produto"]).any()
    assert set(uf["produto"]) == {"gasolina_comum", "etanol_hidratado", "diesel_s10", "gnv"}
    base = uf[uf["mes"] == config.IPCA_BASE_PRECOS]
    assert (base["preco_real"] - base["preco_medio_revenda"]).abs().max() < 1e-9
    gas = uf[uf["produto"] == "etanol_hidratado"].set_index(["mes", "uf"])
    g = uf[uf["produto"] == "gasolina_comum"].set_index(["mes", "uf"])["preco_medio_revenda"]
    par = (gas["preco_medio_revenda"] / g.reindex(gas.index)).dropna()
    assert (par - gas.loc[par.index, "paridade_etanol_gasolina"]).abs().max() < 1e-12
    municipal = pd.read_parquet(config.PRECOS_COMBUSTIVEIS_MUNICIPAL)
    assert municipal["cod_ibge_municipio"].str.fullmatch(r"\d{7}").all()
    assert pd.read_csv(config.PRECOS_VALIDACAO)["falhas"].sum() == 0
