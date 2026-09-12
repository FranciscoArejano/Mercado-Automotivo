"""Log em arquivo, com contagem de linhas lidas e escritas por etapa (sec.8)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from . import config


class ErroMetodologico(RuntimeError):
    """Ambiguidade nao coberta pela ESPEC: descrever o caso e parar (sec.9.6)."""


class ErroDeParsing(RuntimeError):
    """Divergencia acima da tolerancia, ou tabela nao reconhecida (sec.4)."""


def preparar(etapa: str) -> logging.Logger:
    """Devolve um logger que escreve em logs/<etapa>.log e no stderr."""
    config.DIR_LOGS.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(etapa)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formato = logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # Reescrito a cada execucao: o pipeline e' idempotente, o log tambem (sec.1.3).
    arquivo = logging.FileHandler(config.DIR_LOGS / f"{etapa}.log", mode="w", encoding="utf-8")
    arquivo.setFormatter(formato)
    logger.addHandler(arquivo)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formato)
    logger.addHandler(console)
    return logger


def contagem(logger: logging.Logger, **quantidades: int) -> None:
    """Registra contagens de linhas lidas/escritas de uma etapa."""
    partes = ", ".join(f"{chave}={valor}" for chave, valor in quantidades.items())
    logger.info("contagem: %s", partes)


def caminho_relativo(caminho: Path) -> str:
    try:
        return str(caminho.relative_to(config.RAIZ))
    except ValueError:
        return str(caminho)
