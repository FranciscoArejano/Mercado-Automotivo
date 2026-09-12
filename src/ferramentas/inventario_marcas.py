#!/usr/bin/env python3
"""Inventario das marcas observadas nas extracoes.

Nao decide nada: lista o que a fonte publicou antes da primeira barra, com
volume e periodo, para que `config/marcas.csv` seja curado com evidencia em
vez de memoria. Marca observada e ausente da lista curada aparece marcada.

Uso:
    python src/ferramentas/inventario_marcas.py [--csv CAMINHO]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import config, marcas  # noqa: E402


def inventariar() -> pd.DataFrame:
    arquivos = sorted(config.DIR_EXTRACAO.glob("*.csv"))
    if not arquivos:
        raise SystemExit("nenhuma extracao encontrada -- rode a etapa 02 antes.")
    blocos = [pd.read_csv(a, dtype=str, keep_default_na=False) for a in arquivos]
    bruto = pd.concat(blocos, ignore_index=True)
    bruto["unidades"] = pd.to_numeric(bruto["unidades_mes"])

    separacoes = [marcas.separar(n) for n in bruto["nome_completo_fonte"]]
    bruto["marca_fonte"] = [s.marca for s in separacoes]
    bruto["metodo"] = [s.metodo for s in separacoes]
    bruto["conhecida"] = [s.conhecida for s in separacoes]

    return (
        bruto.groupby(["marca_fonte", "metodo", "conhecida"], as_index=False)
        .agg(
            linhas=("unidades", "size"),
            unidades=("unidades", "sum"),
            modelos=("nome_completo_fonte", "nunique"),
            primeiro_mes=("mes", "min"),
            ultimo_mes=("mes", "max"),
            exemplo=("nome_completo_fonte", "first"),
        )
        .sort_values("unidades", ascending=False)
    )


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--csv", type=Path,
                            default=config.DIR_SAIDAS / "inventario_marcas.csv")
    args = analisador.parse_args()
    inventario = inventariar()
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    inventario.to_csv(args.csv, index=False)
    faltando = inventario[~inventario["conhecida"]]
    print(inventario.to_string(index=False))
    print(f"\n{len(inventario)} marcas observadas; {len(faltando)} fora de "
          f"config/marcas.csv ({int(faltando['unidades'].sum()):,} unidades).")
    print(f"gravado em {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
