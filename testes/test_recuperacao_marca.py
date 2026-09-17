"""Recuperacao da marca de uma edicao com a coluna trocada (D4).

Novembro/2013 saiu com 12 modelos sob marca trocada. O informe de dezembro
republica novembro na coluna de mes anterior com as marcas certas e os mesmos
valores -- e e' a coincidencia exata do valor que autoriza a recuperacao.
"""

import csv

import pandas as pd
import pytest

from comum import config, recuperacao_marca

CAMPOS = ["mes", "segmento", "origem_tabela", "sub_segmento_fonte", "posicao_fonte",
          "nome_completo_fonte", "unidades_mes", "unidades_mes_anterior",
          "unidades_acumulado", "participacao_pct", "pagina", "metodo_extracao",
          "arquivo_origem"]


def _escrever(caminho, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=CAMPOS)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({c: linha.get(c, "") for c in CAMPOS})


def _linha(nome, mes_atual, anterior, origem="sub_segmento", pagina="18"):
    return {"mes": "2013-12", "segmento": "comerciais_leves", "origem_tabela": origem,
            "sub_segmento_fonte": "Pick-up's Pequenas", "posicao_fonte": "1",
            "nome_completo_fonte": nome, "unidades_mes": mes_atual,
            "unidades_mes_anterior": anterior, "unidades_acumulado": "",
            "participacao_pct": "", "pagina": pagina, "metodo_extracao": "texto",
            "arquivo_origem": "2013-12.pdf"}


def _divergentes(linhas):
    return pd.DataFrame(linhas)


def _divergente(modelo, marca, unidades, mes="2013-11", segmento="comerciais_leves"):
    return {"mes_ref": mes, "segmento": segmento, "modelo": modelo, "marca": marca,
            "marca_dominante": "?", "unidades": unidades}


@pytest.fixture
def dezembro(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DIR_EXTRACAO", tmp_path / "extracao")
    monkeypatch.setattr(config, "MESES_COM_MARCA_TROCADA", tmp_path / "meses.csv")
    return tmp_path


def test_valor_identico_recupera_a_marca(dezembro):
    _escrever(config.DIR_EXTRACAO / "2013-12.csv", [_linha("GM/MONTANA", "3733", "3901")])
    saida = recuperacao_marca.recuperar(
        "2013-11", _divergentes([_divergente("MONTANA", "PONTIAC", 3901)]))
    assert saida.iloc[0]["marca_recuperada"] == "GM"
    assert saida.iloc[0]["situacao"].startswith("recuperado")


def test_valor_diferente_nao_recupera_nada(dezembro):
    # A coincidencia exata e' a validacao. Sem ela, nao ha' o que autorizar.
    _escrever(config.DIR_EXTRACAO / "2013-12.csv", [_linha("GM/MONTANA", "3733", "3900")])
    saida = recuperacao_marca.recuperar(
        "2013-11", _divergentes([_divergente("MONTANA", "PONTIAC", 3901)]))
    assert saida.iloc[0]["marca_recuperada"] == ""
    assert "nao confere" in saida.iloc[0]["situacao"]


def test_modelo_so_no_ranking_nao_tem_rota(dezembro):
    # O ranking mensal nao traz coluna de mes anterior: 4 dos 12 pararam aqui.
    _escrever(config.DIR_EXTRACAO / "2013-12.csv",
              [_linha("M.BENZ/SPRINTER", "82", "", origem="ranking", pagina="6")])
    saida = recuperacao_marca.recuperar(
        "2013-11", _divergentes([_divergente("SPRINTER", "DODGE", 66)]))
    assert saida.iloc[0]["marca_recuperada"] == ""
    assert "ranking mensal" in saida.iloc[0]["situacao"]


def test_modelo_ausente_do_informe_seguinte(dezembro):
    _escrever(config.DIR_EXTRACAO / "2013-12.csv", [_linha("GM/MONTANA", "3733", "3901")])
    saida = recuperacao_marca.recuperar(
        "2013-11", _divergentes([_divergente("ZILK", "VW", 1)]))
    assert saida.iloc[0]["situacao"] == "sem contraparte no informe seguinte"


def test_so_recupera_mes_declarado_no_config(dezembro):
    # TIGGO 7 sob CHERY ate' 2020 e CAOA CHERY depois e' troca REAL de marca.
    # Recupera-la destruiria o dado -- por isso o escopo vem do config.
    _escrever(config.DIR_EXTRACAO / "2020-02.csv", [_linha("CAOA CHERY/TIGGO 7", "300", "290")])
    painel = pd.DataFrame([
        {"marca": "CHERY", "modelo": "TIGGO 7", "segmento": "automoveis",
         "mes_ref": "2020-01", "unidades": 290},
    ] + [
        {"marca": "CAOA CHERY", "modelo": "TIGGO 7", "segmento": "automoveis",
         "mes_ref": f"2021-{m:02d}", "unidades": 300} for m in range(1, 13)
    ])
    config.MESES_COM_MARCA_TROCADA.write_text("mes_ref,motivo,fonte\n", encoding="utf-8")
    assert recuperacao_marca.recuperacoes(painel).empty


def test_duplicata_apos_recuperacao_e_apontada_e_nao_removida():
    # Recuperada a marca, a linha do ranking passa a repetir a de sub-segmento.
    # A funcao mede; descartar mudaria o total do mes e e' decisao humana.
    bruto = pd.DataFrame([
        {"mes_ref": "2013-11", "segmento_fonte": "comerciais_leves", "marca_chave": "GM",
         "modelo_chave": "MONTANA", "origem_tabela": "sub_segmento", "unidades": 3901,
         "marca_recuperada": False, "marca_publicada_fonte": "GM"},
        {"mes_ref": "2013-11", "segmento_fonte": "comerciais_leves", "marca_chave": "GM",
         "modelo_chave": "MONTANA", "origem_tabela": "ranking", "unidades": 3901,
         "marca_recuperada": True, "marca_publicada_fonte": "PONTIAC"},
    ])
    saida = recuperacao_marca.duplicatas_apos_recuperacao(bruto)
    assert len(saida) == 1
    assert bool(saida.iloc[0]["valor_identico"])
    assert saida.iloc[0]["marca_publicada_fonte"] == "PONTIAC"
