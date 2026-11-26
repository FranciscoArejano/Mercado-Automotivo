"""Guarda dos brutos da rodada 13 (energia, frota e emissoes).

Para cada fonte com manifesto:
- arquivo que vai para o git existe e bate com o SHA-256 do manifesto, e tem ate'
  50 MB;
- arquivo acima de 50 MB fica fora do git, e o reduzido existe, tem ate' 50 MB e
  bate com o SHA-256 do manifesto;
- quando o original grande esta' presente, o SHA-256 dele bate, e refazer o
  reduzido a partir dele da' exatamente os mesmos bytes (o reduzido e' fiel ao
  original e o produto se reproduz a partir do que esta' no git).
"""

import os
import subprocess

import pytest

from coleta import comum_coleta as cc
from comum import config

FONTES = [f for f in config.FONTES_ENERGIA if cc.caminho_manifesto(f).exists()]
REDUTORES = {}


def _redutores(fonte):
    if fonte not in REDUTORES:
        if fonte == "seeg":
            from coleta import seeg
            REDUTORES[fonte] = seeg.redutores()
        elif fonte == "anp_precos":
            from coleta import anp_precos
            REDUTORES[fonte] = anp_precos.redutores()
        else:
            REDUTORES[fonte] = {}
    return REDUTORES[fonte]


def _linhas():
    for fonte in FONTES:
        for chave, linha in sorted(cc.ler_manifesto(fonte).items()):
            yield pytest.param(fonte, chave, linha, id=f"{fonte}:{chave}")


@pytest.mark.parametrize("fonte,chave,linha", list(_linhas()))
def test_bruto_guardado_bate_com_o_manifesto(fonte, chave, linha):
    if linha["no_git"] == "sim":
        caminho = cc.caminho_do_original(fonte, linha)
        assert caminho.exists(), caminho
        assert int(linha["bytes"]) <= config.LIMITE_GIT_BYTES
        assert cc.sha256_arquivo(caminho) == linha["sha256"]
    else:
        assert int(linha["bytes"]) > config.LIMITE_GIT_BYTES
        reduzido = cc.dir_fonte(fonte) / linha["reduzido"]
        assert reduzido.exists(), reduzido
        assert reduzido.stat().st_size <= config.LIMITE_GIT_BYTES
        assert cc.sha256_arquivo(reduzido) == linha["sha256_reduzido"]


def _amostra():
    """Todos os reduzidos com TESTE_REDUZIDO_TODOS=1; senao, os dois primeiros de cada fonte
    (refazer os ~40 da ANP leva ~20 minutos). O SHA-256 do original e' conferido em todos."""
    todos = os.environ.get("TESTE_REDUZIDO_TODOS") == "1"
    vistos: dict[str, int] = {}
    for p in _linhas():
        fonte, _, linha = p.values
        if linha["no_git"] != "nao":
            continue
        vistos[fonte] = vistos.get(fonte, 0) + 1
        yield pytest.param(*p.values, todos or vistos[fonte] <= 2, id=p.id)


@pytest.mark.parametrize("fonte,chave,linha,refazer", list(_amostra()))
def test_reduzido_refeito_do_original_da_os_mesmos_bytes(fonte, chave, linha, refazer):
    original = cc.caminho_do_original(fonte, linha)
    if not original.exists():
        pytest.skip("original fora do git e ausente nesta copia (baixe com src/coleta/)")
    assert cc.sha256_arquivo(original) == linha["sha256"]
    if not refazer:
        return
    refeito = cc.bytes_parquet(_redutores(fonte)[chave](original))
    assert cc.sha256_bytes(refeito) == linha["sha256_reduzido"]


def test_original_grande_nao_esta_no_git():
    rastreados = subprocess.run(["git", "ls-files", "dados/bruto"], cwd=config.RAIZ,
                                capture_output=True, text=True).stdout.splitlines()
    assert not [r for r in rastreados if "/fora_do_git/" in r]
