#!/usr/bin/env python3
"""Senatran: estatisticas de frota por municipio e tipo, por municipio e combustivel,
e por UF e tipo (esta so' para conferencia).

Recorte do pesquisador para volume grande: **todos os meses desde 2020-01 e
dezembro de cada ano antes disso** (2003 a 2019). De 2003 a 2012 a Senatran
publica um zip por ano com as doze planilhas; o zip vai inteiro para o git, como
veio, e o produto le' so' dezembro. Desde 2013, uma planilha por mes e tipo.

Escolha do arquivo quando a pagina traz mais de um para o mesmo mes e tipo
(registrada em `inventario_links.csv`, coluna `escolhido`): o original antes da
copia `copy_of_` do portal; depois xlsx, xls, csv, zip, rar; depois a ordem
alfabetica.

Todos os arquivos ficam abaixo de 50 MB: vao para o git como vieram, em
`dados/bruto/senatran_frota/<ano>/`, com SHA-256 no manifesto. Arquivo ja' no
manifesto e no disco nao e' baixado de novo (retomada).

Uso:
    python src/coleta/senatran_frota.py
    python src/coleta/senatran_frota.py --so-inventario
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coleta import comum_coleta as cc  # noqa: E402
from coleta import senatran_inventario as inv  # noqa: E402

FONTE = "senatran_frota"
PRIMEIRO_ANO_MENSAL = 2020
PRIMEIRO_ANO = 2003
TIPOS = ("municipio_tipo", "municipio_combustivel", "uf_tipo")
PREFERENCIA_EXT = {"xlsx": 0, "xls": 1, "csv": 2, "zip": 3, "rar": 4}


def no_recorte(ano: int, mes: int) -> bool:
    return ano >= PRIMEIRO_ANO_MENSAL or mes == 12


def inventario(ultimo_ano: int) -> pd.DataFrame:
    linhas = []
    for ano, caminho in inv.ZIPS_ANUAIS.items():
        linhas.append({"ano": ano, "arquivo": f"frota{ano}.zip",
                       "url": inv.BASE + caminho + ("" if "resolveuid" in caminho
                                                    else "/@@download/file"),
                       "tipo": "zip_anual", "mes": 12, "copia": False})
    for ano in range(2013, ultimo_ano + 1):
        linhas += inv.links_do_ano(ano)
    tabela = pd.DataFrame(linhas)
    tabela["ext"] = tabela["arquivo"].str.extract(r"\.([A-Za-z0-9]+)$")[0].str.lower()
    tabela["escolhido"] = False
    candidatos = tabela[tabela["tipo"].isin(TIPOS + ("zip_anual",)) & tabela["mes"].notna()]
    for _, grupo in candidatos.groupby(["ano", "mes", "tipo"]):
        ordem = grupo.assign(p=grupo["ext"].map(PREFERENCIA_EXT).fillna(9)).sort_values(
            ["copia", "p", "arquivo"])
        tabela.loc[ordem.index[0], "escolhido"] = True
    tabela["no_recorte"] = [no_recorte(int(a), int(m)) if pd.notna(m) else False
                            for a, m in zip(tabela["ano"], tabela["mes"])]
    return tabela


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--so-inventario", action="store_true")
    analisador.add_argument("--ultimo-ano", type=int, default=2026)
    args = analisador.parse_args()
    tabela = inventario(args.ultimo_ano)
    destino = cc.dir_fonte(FONTE)
    destino.mkdir(parents=True, exist_ok=True)
    tabela.drop(columns=["ext"]).to_csv(destino / "inventario_links.csv", index=False)
    if args.so_inventario:
        return 0
    manifesto = cc.ler_manifesto(FONTE)
    alvo = tabela[tabela["escolhido"] & tabela["no_recorte"]]
    for _, linha in alvo.iterrows():
        nome = f"{int(linha['ano'])}/{linha['arquivo']}"
        if nome in manifesto and cc.caminho_do_original(FONTE, manifesto[nome]).exists():
            continue
        conteudo = cc.baixar(linha["url"])
        cc.registrar(FONTE, manifesto, nome, linha["url"], conteudo,
                     observacao=f"{linha['tipo']} {int(linha['ano'])}-{int(linha['mes']):02d}")
        print(f"{nome}: {len(conteudo)} bytes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
