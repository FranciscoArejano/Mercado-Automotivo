"""Pecas comuns das bases de energia, frota e emissoes (rodada 13).

- chaves comuns: `mes` (AAAA-MM), `uf` (sigla), `cod_ibge_municipio` (7 digitos, da
  tabela do IBGE em `dados/bruto/ibge/municipios.json`, a mesma das fabricas);
- casamento de nome de municipio com o IBGE (so' normalizacao tipografica: caixa,
  acento, pontuacao e espaco; o resto vai para `config/frota_municipios.csv`);
- deflator pelo IPCA de `macro_mensal` (sgs_433);
- dicionario e tabela de conferencias no formato das outras etapas.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import config

MESES_PT = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
            "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
            "dezembro": 12}
MESES_ABREV = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7,
               "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto))
                   if not unicodedata.combining(c))


def chave_nome(texto: str) -> str:
    """Normalizacao tipografica para casar nome de municipio: caixa, acento, pontuacao."""
    t = sem_acento(texto).upper()
    t = re.sub(r"[`´'’‘\"]", "", t)
    t = re.sub(r"[^A-Z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def municipios_ibge() -> pd.DataFrame:
    dados = json.loads(config.MUNICIPIOS_IBGE.read_bytes())
    tabela = pd.DataFrame({
        "cod_ibge_municipio": [str(d["municipio-id"]) for d in dados],
        "municipio_ibge": [d["municipio-nome"] for d in dados],
        "uf": [d["UF-sigla"] for d in dados],
        "uf_nome": [d["UF-nome"] for d in dados],
    })
    tabela["chave"] = tabela["municipio_ibge"].map(chave_nome)
    return tabela


def ufs() -> pd.DataFrame:
    """Sigla, nome e codigo das 27 UFs."""
    dados = json.loads(config.MUNICIPIOS_IBGE.read_bytes())
    vistas = {}
    for d in dados:
        vistas[d["UF-sigla"]] = (d["UF-nome"], str(d["UF-id"]))
    return pd.DataFrame([(s, n, c) for s, (n, c) in sorted(vistas.items())],
                        columns=["uf", "uf_nome", "cod_ibge_uf"])


def sigla_da_uf(nome: str) -> str | None:
    """Nome da UF por extenso (com ou sem acento, qualquer caixa) ou sigla -> sigla."""
    tabela = ufs()
    mapa = {chave_nome(n): s for s, n in zip(tabela["uf"], tabela["uf_nome"])}
    mapa.update({s: s for s in tabela["uf"]})
    return mapa.get(chave_nome(nome))


def casar_municipios(quadro: pd.DataFrame, col_uf: str, col_nome: str,
                     excecoes: pd.DataFrame | None = None) -> pd.Series:
    """Codigo IBGE de cada linha por (UF, nome normalizado); vazio se nao casar.

    `excecoes` (colunas uf, nome_fonte, cod_ibge_municipio) traz os casos em que o
    nome da fonte difere do IBGE alem da tipografia -- cada um com motivo.
    """
    ibge = municipios_ibge()
    mapa = {(u, k): c for u, k, c in zip(ibge["uf"], ibge["chave"], ibge["cod_ibge_municipio"])}
    if excecoes is not None and len(excecoes):
        for u, n, c in zip(excecoes["uf"], excecoes["nome_fonte"],
                           excecoes["cod_ibge_municipio"]):
            mapa[(u, chave_nome(n))] = str(c)
    chaves = list(zip(quadro[col_uf], quadro[col_nome].map(chave_nome)))
    return pd.Series([mapa.get(k) for k in chaves], index=quadro.index, dtype="object")


def indice_ipca() -> pd.DataFrame:
    """Indice encadeado do IPCA cheio (sgs_433 de macro_mensal), com o mes-base."""
    macro = pd.read_parquet(config.MACRO_MENSAL, columns=["mes_ref", "sgs_433"])
    macro = macro.sort_values("mes_ref").dropna(subset=["sgs_433"]).reset_index(drop=True)
    indice = (1 + macro["sgs_433"] / 100).cumprod()
    return pd.DataFrame({"mes": macro["mes_ref"], "indice": indice})


def gravar_validacao(caminho: Path, linhas: list[dict]) -> pd.DataFrame:
    tabela = pd.DataFrame(linhas, columns=["conferencia", "casos", "falhas", "observacao"])
    tabela.to_csv(caminho, index=False)
    return tabela


def gravar_dicionario(caminho: Path, titulo: str, introducao: str,
                      campos: list[tuple[str, str, str]], ressalvas: list[str],
                      fonte: str) -> None:
    texto = [f"# {titulo}\n\n", introducao.strip() + "\n\n",
             f"**Fonte:** {fonte}\n\n",
             "| coluna | unidade | descricao |\n|---|---|---|\n"]
    for nome, unidade, descricao in campos:
        texto.append(f"| `{nome}` | {unidade} | {descricao.replace('|', '/')} |\n")
    texto.append("\n## Ressalvas\n\n")
    texto += [f"- {r}\n" for r in ressalvas]
    caminho.write_text("".join(texto), encoding="utf-8")


def tamanho_no_repositorio(*caminhos: Path) -> int:
    """Bytes que a base ocupa no git (arquivos versionados, sem `fora_do_git/`)."""
    total = 0
    for caminho in caminhos:
        if caminho.is_file():
            total += caminho.stat().st_size
        elif caminho.is_dir():
            total += sum(p.stat().st_size for p in caminho.rglob("*")
                         if p.is_file() and "fora_do_git" not in p.parts)
    return total
