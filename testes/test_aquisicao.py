"""Catalogo da fonte e as correcoes curadas sobre ele."""

import csv
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import etapa01_aquisicao as etapa  # noqa: E402
from comum import config  # noqa: E402

CAMPOS = ["mes", "arquivo_fonte", "motivo", "fonte"]


def _correcoes(tmp_path, monkeypatch, linhas):
    caminho = tmp_path / "correcoes_catalogo.csv"
    with caminho.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(linhas)
    monkeypatch.setattr(config, "CORRECOES_CATALOGO", caminho)
    return caminho


def _catalogo():
    return {
        "2005-04": {"mes": "2005-04", "arquivo_fonte": "3_2005_05_2.pdf",
                    "url": "x", "descricao_fonte": "", "data_consulta": ""},
        "2005-05": {"mes": "2005-05", "arquivo_fonte": "4_2005_05_2.pdf",
                    "url": "y", "descricao_fonte": "", "data_consulta": ""},
    }


def test_correcao_troca_o_arquivo_do_mes(tmp_path, monkeypatch):
    """O catalogo da Fenabrave aponta 2005-04 para o informe de maio."""
    _correcoes(tmp_path, monkeypatch, [{
        "mes": "2005-04", "arquivo_fonte": "3_2005_04_2.pdf",
        "motivo": "catalogo aponta para a edicao de maio", "fonte": "Ed. 28",
    }])
    catalogo = _catalogo()
    aplicadas = etapa.aplicar_correcoes(catalogo, logging.getLogger("teste"))
    assert len(aplicadas) == 1
    assert catalogo["2005-04"]["arquivo_fonte"] == "3_2005_04_2.pdf"
    assert catalogo["2005-04"]["url"].endswith("3_2005_04_2.pdf")
    # os outros meses ficam intocados
    assert catalogo["2005-05"]["arquivo_fonte"] == "4_2005_05_2.pdf"


def test_correcao_que_ja_vale_nao_conta_como_mudanca(tmp_path, monkeypatch):
    _correcoes(tmp_path, monkeypatch, [{
        "mes": "2005-05", "arquivo_fonte": "4_2005_05_2.pdf",
        "motivo": "confirmacao", "fonte": "",
    }])
    assert etapa.aplicar_correcoes(_catalogo(), logging.getLogger("teste")) == []


def test_sem_arquivo_de_correcoes_nada_muda(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CORRECOES_CATALOGO", tmp_path / "nao_existe.csv")
    catalogo = _catalogo()
    assert etapa.aplicar_correcoes(catalogo, logging.getLogger("teste")) == []
    assert catalogo["2005-04"]["arquivo_fonte"] == "3_2005_05_2.pdf"


def test_linha_incompleta_e_ignorada(tmp_path, monkeypatch):
    _correcoes(tmp_path, monkeypatch, [
        {"mes": "", "arquivo_fonte": "x.pdf", "motivo": "", "fonte": ""},
        {"mes": "2005-04", "arquivo_fonte": "", "motivo": "", "fonte": ""},
    ])
    assert etapa.aplicar_correcoes(_catalogo(), logging.getLogger("teste")) == []


def test_o_arquivo_versionado_traz_motivo_e_fonte_em_toda_linha():
    """Correcao e' dado curado: sem justificativa nao entra."""
    if not config.CORRECOES_CATALOGO.exists():
        return
    with config.CORRECOES_CATALOGO.open(encoding="utf-8", newline="") as fluxo:
        linhas = list(csv.DictReader(fluxo))
    assert linhas, "o arquivo de correcoes existe mas esta' vazio"
    for linha in linhas:
        assert linha["motivo"].strip(), f"{linha['mes']}: sem motivo"
        assert linha["fonte"].strip(), f"{linha['mes']}: sem fonte"
