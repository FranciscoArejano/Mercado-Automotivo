"""Contrato entre o pipeline e as etapas."""

import importlib
import inspect
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import pipeline  # noqa: E402


@pytest.mark.parametrize("numero,modulo,descricao", pipeline.ETAPAS)
def test_etapa_e_chamavel_pelo_pipeline(numero, modulo, descricao):
    """O pipeline so' passa `inicio` e `fim`; o resto tem de ter valor padrao."""
    alvo = importlib.import_module(modulo)
    assinatura = inspect.signature(alvo.executar)
    sem_padrao = [
        nome for nome, parametro in assinatura.parameters.items()
        if parametro.default is inspect.Parameter.empty and nome not in ("inicio", "fim")
    ]
    assert not sem_padrao, f"{modulo}.executar exige {sem_padrao}, que o pipeline nao passa"


def test_toda_etapa_tem_script_e_esta_na_lista():
    scripts = sorted(p.stem for p in (RAIZ / "src").glob("etapa*.py"))
    assert scripts == sorted(modulo for _, modulo, _ in pipeline.ETAPAS)
