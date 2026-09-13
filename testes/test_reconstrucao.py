"""Recuperacao de mes ilegivel pela coluna de mes anterior (B2)."""

import csv

import pytest

from comum import config, reconstrucao

CAMPOS = [
    "mes", "segmento", "origem_tabela", "sub_segmento_fonte", "posicao_fonte",
    "nome_completo_fonte", "unidades_mes", "unidades_mes_anterior",
    "unidades_acumulado", "participacao_pct", "pagina", "metodo_extracao",
    "arquivo_origem",
]
CAMPOS_TOTAIS = ["mes", "segmento", "total_publicado", "total_publicado_mes_anterior",
                 "origem", "arquivo_origem", "edicao"]


def _escrever(caminho, campos, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=campos)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({c: linha.get(c, "") for c in campos})


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DIR_PROCESSADO", tmp_path)
    monkeypatch.setattr(config, "DIR_EXTRACAO", tmp_path / "extracao")

    def linha(mes, nome, mes_atual, anterior, acumulado, origem="sub_segmento"):
        return {
            "mes": mes, "segmento": "automoveis", "origem_tabela": origem,
            "sub_segmento_fonte": "Hatch Pequenos", "posicao_fonte": "1",
            "nome_completo_fonte": nome, "unidades_mes": mes_atual,
            "unidades_mes_anterior": anterior, "unidades_acumulado": acumulado,
            "participacao_pct": "10.0", "pagina": "11", "metodo_extracao": "texto",
            "arquivo_origem": f"{mes}.pdf",
        }

    # agosto: acumulado ate' agosto = 800
    _escrever(config.DIR_EXTRACAO / "2023-08.csv", CAMPOS,
              [linha("2023-08", "GM/ONIX", "100", "90", "800")])
    # outubro: mes anterior (setembro) = 120, acumulado ate' outubro = 1070
    _escrever(config.DIR_EXTRACAO / "2023-10.csv", CAMPOS,
              [linha("2023-10", "GM/ONIX", "150", "120", "1070")])
    _escrever(config.DIR_PROCESSADO / "totais" / "2023-10.csv", CAMPOS_TOTAIS, [{
        "mes": "2023-10", "segmento": "automoveis", "total_publicado": "163134",
        "total_publicado_mes_anterior": "145676", "origem": "resumo_mensal",
        "arquivo_origem": "2023-10.pdf", "edicao": "250",
    }])
    return tmp_path


def test_recupera_o_mes_pela_coluna_de_mes_anterior(ambiente):
    resultado = reconstrucao.reconstruir("2023-09")
    assert resultado is not None
    assert len(resultado.linhas) == 1
    linha = resultado.linhas[0]
    assert linha["mes"] == "2023-09"
    assert linha["unidades_mes"] == "120"
    assert linha["origem_tabela"] == "mes_anterior"
    assert linha["metodo_extracao"] == "reconstruido"
    # acumulado de setembro = acumulado de outubro menos o mes de outubro
    assert linha["unidades_acumulado"] == "920"


def test_a_rota_do_acumulado_confirma(ambiente):
    # 920 (acum set) - 800 (acum ago) = 120, igual a' coluna de mes anterior
    resultado = reconstrucao.reconstruir("2023-09")
    assert resultado.conferidos == 1
    assert resultado.divergentes == 0
    assert resultado.divergencia_absoluta == 0


def test_a_rota_do_acumulado_denuncia_divergencia(ambiente, monkeypatch):
    _escrever(config.DIR_EXTRACAO / "2023-10.csv", CAMPOS, [{
        "mes": "2023-10", "segmento": "automoveis", "origem_tabela": "sub_segmento",
        "sub_segmento_fonte": "Hatch Pequenos", "posicao_fonte": "1",
        "nome_completo_fonte": "GM/ONIX", "unidades_mes": "150",
        "unidades_mes_anterior": "120", "unidades_acumulado": "1100",
        "participacao_pct": "10.0", "pagina": "11", "metodo_extracao": "texto",
        "arquivo_origem": "2023-10.pdf",
    }])
    resultado = reconstrucao.reconstruir("2023-09")
    assert resultado.divergentes == 1
    assert resultado.divergencia_absoluta == 30  # 950 - 800 = 150, contra 120


def test_recupera_tambem_o_total_publicado(ambiente):
    resultado = reconstrucao.reconstruir("2023-09")
    assert resultado.totais[0]["total_publicado"] == "145676"
    assert "2023-10" in resultado.totais[0]["origem"]


def test_sem_informe_seguinte_nao_inventa_nada(ambiente):
    assert reconstrucao.reconstruir("2026-08") is None
