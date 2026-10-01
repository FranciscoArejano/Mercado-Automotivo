#!/usr/bin/env python3
"""Extrai as linhas de veiculo das tabelas do PBE Veicular (dados/bruto/pbe/).

Produz `saidas/pbe_versoes.csv`, uma linha por linha de veiculo impressa na
tabela: ano da tabela, pagina, categoria, marca como o PBE escreve, modelo e
versao (juntos -- ver `comum/pbe.py`), motor, tipo de propulsao como impresso,
codigo de combustivel e o texto da linha inteira, para auditoria.

E' transcricao: nada e' mapeado aqui. O mapeamento para a taxonomia do projeto
e o casamento com o painel ficam em `src/comum/validacao_classificacao.py`.

Linha que tem motor e a trinca ar/direcao/combustivel mas nao foi lida vai
para `saidas/pbe_linhas_nao_lidas.csv` -- quase sempre marca que falta em
`config/pbe_marcas.csv`.

A parte lenta (o texto de cada pagina) e' guardada por ano em `logs/cache_pbe/`
e reaproveitada; interpretar o texto e' instantaneo. Uma interrupcao no meio
nao perde os anos ja' lidos; `--refazer` rele os PDFs.

Uso:
    python src/ferramentas/pbe_extracao.py [--anos 2024 2025] [--refazer]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import config, pbe  # noqa: E402

DIR_PBE = config.DIR_BRUTO / "pbe"
# Cache por ano em logs/, que e' ignorado (sec.10.2): o PDF versionado reconstitui.
CACHE = config.DIR_LOGS / "cache_pbe"
COLUNAS = ["ano_pbe", "arquivo", "pagina", "categoria", "marca_pbe", "modelo_versao",
           "motor", "tipo_propulsao", "marcador_nome", "combustivel", "texto_linha"]


def marcas_conhecidas() -> list[tuple[str, ...]]:
    tabela = pd.read_csv(config.PBE_MARCAS, dtype=str, keep_default_na=False)
    return sorted({tuple(pbe.normalizar(m).split()) for m in tabela["marca_pbe"]},
                  key=lambda t: -len(t))


def linhas_do_ano(arquivo: Path, ano: str, refazer: bool) -> pd.DataFrame:
    """Texto de cada linha de cada pagina -- a parte lenta, guardada em cache."""
    cache = CACHE / f"{ano}.linhas.csv"
    if cache.exists() and not refazer:
        return pd.read_csv(cache, dtype={"pagina": int, "linha": str}, keep_default_na=False)
    registros = []
    with pdfplumber.open(arquivo) as pdf:
        for numero, pagina in enumerate(pdf.pages, start=1):
            registros += [{"pagina": numero, "linha": t} for t in pbe.linhas_da_pagina(pagina)]
    quadro = pd.DataFrame(registros, columns=["pagina", "linha"])
    quadro.to_csv(cache, index=False)
    return quadro


def interpretar(linhas: pd.DataFrame, arquivo: str, ano: str, marcas):
    """Linhas de veiculo e linhas que pareciam de veiculo mas nao foram lidas."""
    lidas, nao_lidas = [], []
    for pagina, texto in zip(linhas["pagina"], linhas["linha"]):
        registro = pbe.ler_linha(texto, marcas)
        if registro:
            lidas.append({"ano_pbe": ano, "arquivo": arquivo, "pagina": pagina, **registro})
            continue
        palavras = texto.split(" ")
        if pbe._trinca(palavras, 1):
            nao_lidas.append({"ano_pbe": ano, "arquivo": arquivo, "pagina": pagina,
                              "texto_linha": texto})
    return (pd.DataFrame(lidas, columns=COLUNAS),
            pd.DataFrame(nao_lidas, columns=["ano_pbe", "arquivo", "pagina", "texto_linha"]))


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--anos", nargs="*", default=None)
    analisador.add_argument("--refazer", action="store_true",
                            help="reler os PDFs em vez de usar o texto guardado")
    args = analisador.parse_args()

    manifesto = pd.read_csv(DIR_PBE / "manifesto.csv", dtype=str)
    marcas = marcas_conhecidas()
    CACHE.mkdir(parents=True, exist_ok=True)
    todas, todas_nao_lidas = [], []
    for _, item in manifesto.iterrows():
        ano = item["ano_pbe"]
        if args.anos and ano not in args.anos:
            continue
        linhas = linhas_do_ano(DIR_PBE / item["arquivo"], ano, args.refazer)
        lidas, nao_lidas = interpretar(linhas, item["arquivo"], ano, marcas)
        todas.append(lidas)
        todas_nao_lidas.append(nao_lidas)
        print(f"{ano}: {len(lidas)} linhas de veiculo, {len(nao_lidas)} nao lidas", flush=True)
    if args.anos:
        return 0
    pd.concat(todas, ignore_index=True).to_csv(config.PBE_VERSOES, index=False)
    nao = pd.concat(todas_nao_lidas, ignore_index=True)
    nao.to_csv(config.DIR_SAIDAS / "pbe_linhas_nao_lidas.csv", index=False)
    print(f"gravado {config.PBE_VERSOES.relative_to(config.RAIZ)}: "
          f"{sum(len(t) for t in todas)} linhas; {len(nao)} nao lidas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
