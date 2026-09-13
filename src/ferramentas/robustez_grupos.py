#!/usr/bin/env python3
"""Teste de robustez do mapa de grupos (QUESTOES_ABERTAS.md Q3).

Hyundai e Kia entram como grupo unico por convencao -- participacao cruzada
desde 1998 --, e convencao merece teste. Este script recalcula a concentracao
com as duas leituras lado a lado e mostra quanto a escolha move o HHI.

Aceita qualquer variante na linha de comando, no formato `MARCA=GRUPO`, para
que outras convencoes discutiveis (CAOA Chery, Omoda/Jaecoo, a alianca
Renault-Nissan-Mitsubishi) possam ser testadas do mesmo jeito.

Uso:
    python src/ferramentas/robustez_grupos.py                    # Kia separada
    python src/ferramentas/robustez_grupos.py NISSAN=ALIANCA RENAULT=ALIANCA
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import concentracao, config, visoes  # noqa: E402

VARIANTE_PADRAO = {"KIA": "KIA"}


def comparar(variante: dict[str, str]) -> pd.DataFrame:
    painel = pd.read_parquet(config.PAINEL)
    por_modelo = visoes.por_modelo(painel)
    base = concentracao.por_ano(por_modelo)[
        ["ano", "mes_referencia_do_grupo", "hhi_marca", "hhi_grupo_particao_fixa"]
    ].rename(columns={"hhi_grupo_particao_fixa": "hhi_grupo_mapa_atual"})

    alterado = por_modelo.copy()
    alterado["grupo_economico"] = [
        variante.get(marca.upper(), grupo)
        for marca, grupo in zip(alterado["marca"], alterado["grupo_economico"])
    ]
    outra = concentracao.por_ano(alterado)[["ano", "hhi_grupo_particao_fixa"]].rename(
        columns={"hhi_grupo_particao_fixa": "hhi_grupo_variante"})

    junto = base.merge(outra, on="ano")
    junto["diferenca"] = (junto["hhi_grupo_variante"] - junto["hhi_grupo_mapa_atual"]).round(1)
    junto["diferenca_pct"] = (
        100 * junto["diferenca"] / junto["hhi_grupo_mapa_atual"]).round(2)
    return junto


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("pares", nargs="*", metavar="MARCA=GRUPO",
                            help="marcas a remapear na variante (padrao: KIA=KIA)")
    args = analisador.parse_args()
    variante = dict(par.split("=", 1) for par in args.pares) if args.pares else VARIANTE_PADRAO
    variante = {marca.upper(): grupo for marca, grupo in variante.items()}

    quadro = comparar(variante)
    destino = config.DIR_SAIDAS / "robustez_grupos.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    quadro.to_csv(destino, index=False)
    print(f"variante testada: {variante}\n")
    print(quadro.to_string(index=False))
    print(f"\nmaior efeito: {quadro['diferenca'].abs().max():.1f} pontos de HHI "
          f"({quadro['diferenca_pct'].abs().max():.2f}%)")
    print(f"gravado em {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
