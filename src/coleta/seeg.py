#!/usr/bin/env python3
"""SEEG (Observatorio do Clima): tabela geral de emissoes por estado, setor e gas.

Fonte: pagina https://seeg.eco.br/dados/ ("Tabela geral: planilha contendo todos
os dados de emissoes do SEEG desagregados por estados e biomas"), que aponta para
`Dados-nacionais-<colecao>.xlsx`. A colecao (versao) fica no nome do arquivo e no
manifesto: ela revisa os anos anteriores, entao o produto declara de qual saiu.

O original tem ~206 MB, acima do limite de 50 MB: fica em
`dados/bruto/seeg/fora_do_git/` e o git guarda o bruto reduzido:

- `reduzido/seeg_<colecao>_dados.parquet` -- a aba `Dados`, so' as linhas cujo
  `Gás` e' um gas fisico (t do gas) ou `CO2e (t) GWP-AR5`; as outras metricas de
  CO2e (GWP-AR2, AR4, AR6, GTP) ficam de fora. Colunas: as onze de dimensao e os
  anos de 2003 em diante. Valores como a planilha os traz, sem conta;
- `reduzido/seeg_<colecao>_serie_historica.parquet` -- a aba `Consulta Série
  Histórica` (tabela dinamica do proprio SEEG: total Brasil por setor e ano, em
  CO2e GWP-AR5), celula por celula, como texto; serve a' conferencia.

Uso:
    python src/coleta/seeg.py               # baixa (se faltar) e refaz o reduzido
    python src/coleta/seeg.py --so-reduzir  # so' refaz o reduzido a partir do original
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import openpyxl
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coleta import comum_coleta as cc  # noqa: E402

FONTE = "seeg"
COLECAO = "14.0"
NOME = f"Dados-nacionais-{COLECAO}.xlsx"
URL = f"https://seeg.obass.haus/wp-content/uploads/2026/11/{NOME}"
PAGINA = "https://seeg.eco.br/dados/"
PRIMEIRO_ANO = 2003
METRICA_CO2E = "CO2e (t) GWP-AR5"
DIMENSOES = ["Emissão/Remoção/Bunker", "Gás", "Setor de emissão", "Categoria emissora",
             "Sub-categoria emissora", "Produto ou sistema", "Detalhamento", "Recorte",
             "Atividade geral", "Estado", "Bioma"]
ABA_DADOS = "Dados"
ABA_SERIE = "Consulta Série Histórica"


def nome_reduzido(parte: str) -> str:
    return f"seeg_{COLECAO}_{parte}.parquet"


def linha_entra(gas: str) -> bool:
    """Gas fisico (t do gas) ou a metrica CO2e escolhida; as outras CO2e ficam de fora."""
    return gas == METRICA_CO2E or not str(gas).startswith("CO2e")


def ler_dados(caminho: Path) -> pa.Table:
    livro = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    aba = livro[ABA_DADOS]
    linhas = aba.iter_rows(values_only=True)
    cabecalho = list(next(linhas))
    if [str(c) for c in cabecalho[:len(DIMENSOES)]] != DIMENSOES:
        raise RuntimeError(f"cabecalho inesperado na aba Dados: {cabecalho[:12]}")
    anos = [(i, int(c)) for i, c in enumerate(cabecalho) if isinstance(c, (int, float))
            and int(c) >= PRIMEIRO_ANO]
    colunas = {d: [] for d in DIMENSOES}
    colunas.update({str(a): [] for _, a in anos})
    i_gas = DIMENSOES.index("Gás")
    for linha in linhas:
        if linha is None or linha[0] is None:
            continue
        if not linha_entra(linha[i_gas]):
            continue
        for j, d in enumerate(DIMENSOES):
            colunas[d].append(None if linha[j] is None else str(linha[j]))
        for i, a in anos:
            v = linha[i]
            colunas[str(a)].append(None if v is None or v == "" else float(v))
    livro.close()
    campos = [pa.field(d, pa.string()) for d in DIMENSOES] + [
        pa.field(str(a), pa.float64()) for _, a in anos]
    return pa.table(colunas, schema=pa.schema(campos))


def ler_serie_historica(caminho: Path) -> pa.Table:
    livro = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    aba = livro[ABA_SERIE]
    linhas = [list(l) for l in aba.iter_rows(values_only=True)]
    livro.close()
    largura = max(len(l) for l in linhas)
    colunas = {f"c{j:02d}": [None if j >= len(l) or l[j] is None else str(l[j])
                             for l in linhas] for j in range(largura)}
    return pa.table(colunas)


def reduzir(manifesto: dict) -> None:
    original = cc.caminho_do_original(FONTE, manifesto[NOME])
    if cc.sha256_arquivo(original) != manifesto[NOME]["sha256"]:
        raise RuntimeError(f"{original}: SHA-256 nao bate com o manifesto")
    for parte, ler in (("dados", ler_dados), ("serie_historica", ler_serie_historica)):
        tabela = ler(original)
        destino = cc.dir_fonte(FONTE) / "reduzido" / nome_reduzido(parte)
        conteudo = cc.gravar_reduzido(tabela, destino)
        chave = NOME if parte == "dados" else f"{NOME}#{ABA_SERIE}"
        if chave not in manifesto:
            manifesto[chave] = dict(manifesto[NOME], arquivo=chave,
                                    observacao=f"aba '{ABA_SERIE}' do mesmo original")
        cc.registrar_reduzido(FONTE, manifesto, chave, destino, conteudo)
        print(f"{destino.name}: {tabela.num_rows} linhas, {len(conteudo)} bytes")


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--so-reduzir", action="store_true")
    args = analisador.parse_args()
    manifesto = cc.ler_manifesto(FONTE)
    if not args.so_reduzir and (NOME not in manifesto or not cc.caminho_do_original(
            FONTE, manifesto[NOME]).exists()):
        conteudo = cc.baixar(URL)
        cc.registrar(FONTE, manifesto, NOME, URL, conteudo,
                     observacao=f"colecao {COLECAO}; link da pagina {PAGINA} (tabela geral)")
    reduzir(manifesto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
