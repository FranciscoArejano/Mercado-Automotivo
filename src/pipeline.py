#!/usr/bin/env python3
"""Encadeia as sete etapas (ESPEC.md sec.8).

Cada etapa tambem roda isolada. Aqui elas correm na ordem, e a primeira que
falhar interrompe a corrida -- nenhuma etapa sobrescreve a anterior, entao o
que ja' foi produzido continua valido.

Uso:
    python src/pipeline.py                      # tudo
    python src/pipeline.py --de 3 --ate 6       # so' um trecho
    python src/pipeline.py --pular 1            # sem rebaixar os PDFs
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, log  # noqa: E402

ETAPAS = [
    (1, "etapa01_aquisicao", "aquisicao dos informes"),
    (2, "etapa02_parsing", "parsing dos PDFs"),
    (3, "etapa03_painel_bruto", "painel bruto"),
    (4, "etapa04_candidatos", "relatorio de candidatos"),
    (5, "etapa05_painel", "painel harmonizado"),
    (6, "etapa06_validacao", "validacao"),
    (7, "etapa07_referencia_cruzada", "referencia cruzada"),
]


def _chamar(modulo, inicio: str, fim: str) -> int:
    alvo = importlib.import_module(modulo)
    executar = alvo.executar
    nomes = executar.__code__.co_varnames[: executar.__code__.co_argcount]
    argumentos: dict = {}
    if "inicio" in nomes:
        argumentos["inicio"] = inicio
    if "fim" in nomes:
        argumentos["fim"] = fim
    return executar(**argumentos) or 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--inicio", default=config.PERIODO_INICIO)
    analisador.add_argument("--fim", default=config.PERIODO_FIM)
    analisador.add_argument("--de", type=int, default=1)
    analisador.add_argument("--ate", type=int, default=7)
    analisador.add_argument("--pular", type=int, nargs="*", default=[])
    args = analisador.parse_args()

    logger = log.preparar("pipeline")
    logger.info("periodo %s..%s | etapas %d..%d | pulando %s",
                args.inicio, args.fim, args.de, args.ate, args.pular or "nada")
    for numero, modulo, descricao in ETAPAS:
        if numero < args.de or numero > args.ate or numero in args.pular:
            continue
        logger.info("--- etapa %d: %s ---", numero, descricao)
        marca = time.monotonic()
        codigo = _chamar(modulo, args.inicio, args.fim)
        logger.info("etapa %d concluida em %.1fs (codigo %d)", numero, time.monotonic() - marca, codigo)
        if codigo != 0:
            logger.error("etapa %d retornou %d -- pipeline interrompido", numero, codigo)
            return codigo
    logger.info("pipeline concluido")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
