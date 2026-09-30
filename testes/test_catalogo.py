"""`CATALOGO.md`: gerado do dado, completo e em dia.

O catalogo so' vale se nao mente em silencio. Tres guardas: todo produto e toda
serie tem texto de uso (senao aparece o marcador de falta); a tabela de fontes
candidatas traz as fontes mapeadas; e o arquivo versionado e' o que o script
produz hoje -- quem edita `config/catalogo_usos.csv` ou muda o dado sem rodar a
etapa 10 descobre aqui.
"""

import pandas as pd
import pytest

import etapa10_catalogo as catalogo
from comum import config

FONTES_MAPEADAS = [
    "Comex Stat", "Senatran", "Anfavea", "PBE Veicular", "FIPE",
    "Dados Regionais", "Calendário de política",
]


def _dados_presentes():
    return all(p.exists() for p in (config.PAINEL, config.PAINEL_BRUTO, config.PAINEL_CANAL,
                                    config.MACRO_MENSAL))


def test_toda_serie_macro_tem_texto_de_uso():
    usos = set(pd.read_csv(config.CATALOGO_USOS, dtype=str)["alvo"])
    series = set(pd.read_csv(config.SERIES_MACRO, dtype=str)["codigo"])
    assert series <= usos, f"series sem uso em catalogo_usos.csv: {sorted(series - usos)}"


def test_todo_produto_tem_texto_de_uso():
    usos = pd.read_csv(config.CATALOGO_USOS, dtype=str, keep_default_na=False)
    produtos = {"painel", "painel_bruto", "painel_canal", "macro_mensal", "classificacao"}
    presentes = usos[usos["sustenta"] != ""]["alvo"]
    assert produtos <= set(presentes)


def test_fontes_candidatas_trazem_as_mapeadas_com_estado():
    fontes = pd.read_csv(config.FONTES_CANDIDATAS, dtype=str, keep_default_na=False)
    assert (fontes["estado"] != "").all()
    for nome in FONTES_MAPEADAS:
        assert fontes["fonte"].str.contains(nome, regex=False).any(), nome


@pytest.mark.skipif(not _dados_presentes(), reason="produtos ausentes")
def test_catalogo_declara_o_commit_na_primeira_linha_e_nao_tem_falta():
    texto = catalogo.gerar()
    primeira = texto.splitlines()[0]
    assert primeira.startswith("# Catalogo do repositorio -- dado do commit `")
    assert catalogo.SEM_TEXTO not in texto


@pytest.mark.skipif(not _dados_presentes(), reason="produtos ausentes")
def test_catalogo_e_idempotente():
    assert catalogo.gerar() == catalogo.gerar()


@pytest.mark.skipif(not _dados_presentes() or not config.CATALOGO_REPOSITORIO.exists(),
                    reason="produtos ou catalogo ausentes")
def test_catalogo_versionado_esta_em_dia():
    """Tudo menos a primeira linha: o commit muda com o commit, o corpo nao."""
    versionado = config.CATALOGO_REPOSITORIO.read_text(encoding="utf-8").split("\n", 1)[1]
    atual = catalogo.gerar().split("\n", 1)[1]
    assert versionado == atual, "CATALOGO.md desatualizado: rode src/etapa10_catalogo.py"
