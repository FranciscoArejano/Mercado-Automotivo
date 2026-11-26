#!/usr/bin/env python3
"""ANP: Levantamento de Precos de Combustiveis -- serie historica por posto e sintese.

Duas paginas (gov.br/anp):

- **dados abertos** (`.../dados-abertos/serie-historica-de-precos-de-combustiveis`):
  um arquivo por semestre de combustiveis automotivos (`ca-AAAA-0S.csv`, e `.zip`
  desde 2022), de 2004-01 ao ultimo semestre fechado; o semestre 2022-01 esta' em
  `precos-semestrais-ca.zip`, listado a' parte. Depois do ultimo semestre, os
  arquivos mensais (`dsan/AAAA/MM-...gasolina-etanol.csv` e `...diesel-gnv.csv`);
- **sintese** (`.../serie-historica-do-levantamento-de-precos`): medias mensais por
  estado publicadas pela ANP (2001-2012 e desde 2013), usadas so' na conferencia.

Guarda: arquivo de ate' 50 MB vai para o git como veio; acima, o original fica
em `fora_do_git/` e o reduzido em `reduzido/<arquivo>.parquet`, com as colunas que
o produto usa (`COLUNAS`) e as linhas dos quatro produtos (`PRODUTOS`), celulas
como texto, sem conta nem renomeacao. A codificacao do CSV muda: com BOM e'
UTF-8, sem BOM e' Latin-1 (testado nos arquivos de 2004 a 2026).

Uso:
    python src/coleta/anp_precos.py
"""

from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coleta import comum_coleta as cc  # noqa: E402
from comum import config  # noqa: E402

FONTE = "anp_precos"
PAGINA_DADOS = ("https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
                "serie-historica-de-precos-de-combustiveis")
PAGINA_SINTESE = ("https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/"
                  "precos/precos-revenda-e-de-distribuicao-combustiveis/"
                  "serie-historica-do-levantamento-de-precos")
SINTESES = ("mensal-estados-2001-a-2012.xlsx", "mensal-estados-desde-jan2013.xlsx")
COLUNAS = ["Estado - Sigla", "Municipio", "CNPJ da Revenda", "Produto", "Data da Coleta",
           "Valor de Venda", "Unidade de Medida"]
PRODUTOS = ("GASOLINA", "ETANOL", "DIESEL S10", "GNV")


def links() -> pd.DataFrame:
    """Arquivos por posto (semestrais e mensais finais) e sinteses, com o periodo."""
    cabecalho = {"User-Agent": config.USER_AGENT}
    dados = requests.get(PAGINA_DADOS, headers=cabecalho, timeout=120).text
    sintese = requests.get(PAGINA_SINTESE, headers=cabecalho, timeout=120).text
    linhas = []
    for url in sorted(set(re.findall(r'href="([^"]+/shpc/dsas/ca/[^"]+)"', dados))):
        nome = url.rsplit("/", 1)[-1]
        m = re.match(r"ca-(\d{4})-0([12])\.(csv|zip)$", nome)
        if m:
            linhas.append({"arquivo": nome, "url": url, "tipo": "posto_semestral",
                           "periodo": f"{m.group(1)}-S{m.group(2)}"})
        elif nome == "precos-semestrais-ca.zip":
            linhas.append({"arquivo": nome, "url": url, "tipo": "posto_semestral",
                           "periodo": "2022-S1"})  # conteudo: precos-semestrais-ca-2022-01.csv
    for url in sorted(set(re.findall(r'href="([^"]+/shpc/dsan/(\d{4})/[^"]+\.csv)"', dados))):
        url = url[0]
        ano = re.search(r"/dsan/(\d{4})/", url).group(1)
        nome = url.rsplit("/", 1)[-1]
        mes = re.match(r"(?:precos-[a-z-]+-)?(\d{2})", nome.replace("precos-gasolina-etanol-", "")
                       .replace("precos-diesel-gnv-", "").replace("precos-glp-", ""))
        if "glp" in nome or not mes:
            continue
        linhas.append({"arquivo": f"dsan-{ano}-{nome}", "url": url, "tipo": "posto_mensal",
                       "periodo": f"{ano}-{mes.group(1)}"})
    for nome in SINTESES:
        url = re.search(rf'href="([^"]+/{re.escape(nome)})"', sintese)
        if url:
            linhas.append({"arquivo": nome, "url": url.group(1), "tipo": "sintese_estados",
                           "periodo": ""})
    tabela = pd.DataFrame(linhas)
    # mensal so' depois do ultimo semestre: o semestral ja' traz os meses dele
    semestres = tabela[tabela["tipo"] == "posto_semestral"]["periodo"]
    ultimo = max(semestres)
    fim = f"{ultimo[:4]}-{'06' if ultimo.endswith('S1') else '12'}"
    mensal = tabela["tipo"] == "posto_mensal"
    tabela = tabela[~mensal | (tabela["periodo"] > fim)]
    return tabela.reset_index(drop=True)


def _texto_csv(conteudo: bytes) -> str:
    if conteudo.startswith(b"\xef\xbb\xbf"):
        return conteudo.decode("utf-8-sig")
    return conteudo.decode("latin-1")


def _csvs(caminho: Path) -> list[bytes]:
    # zip pelos bytes iniciais, nao pela extensao: ca-2014-01.csv e' um zip com nome de csv
    with caminho.open("rb") as fluxo:
        zipado = fluxo.read(2) == b"PK"
    if zipado:
        with zipfile.ZipFile(caminho) as z:
            return [z.read(n) for n in sorted(z.namelist()) if n.lower().endswith(".csv")]
    return [caminho.read_bytes()]


def ler_posto(caminho: Path) -> pa.Table:
    """As colunas e linhas que o produto usa, celulas como texto (o reduzido)."""
    partes = []
    for conteudo in _csvs(caminho):
        quadro = pd.read_csv(io.StringIO(_texto_csv(conteudo)), sep=";", dtype=str,
                             keep_default_na=False, usecols=COLUNAS)
        partes.append(quadro[quadro["Produto"].isin(PRODUTOS)][COLUNAS])
    quadro = pd.concat(partes, ignore_index=True)
    return pa.Table.from_pandas(quadro, preserve_index=False,
                                schema=pa.schema([pa.field(c, pa.string()) for c in COLUNAS]))


def redutores() -> dict:
    manifesto = cc.ler_manifesto(FONTE)
    return {chave: ler_posto for chave, linha in manifesto.items()
            if linha["observacao"].startswith("posto")}


TRABALHADORES = 3  # tres downloads por vez: cada conexao do gov.br fica em ~0,8 MB/s


def main() -> int:
    import threading
    from concurrent.futures import ThreadPoolExecutor

    tabela = links()
    destino = cc.dir_fonte(FONTE)
    destino.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino / "inventario_links.csv", index=False)
    manifesto = cc.ler_manifesto(FONTE)
    trava = threading.Lock()

    def um(linha) -> None:
        nome = linha["arquivo"]
        with trava:
            presente = nome in manifesto and cc.caminho_do_original(
                FONTE, manifesto[nome]).exists()
        if not presente:
            conteudo = cc.baixar(linha["url"])
            with trava:
                cc.registrar(FONTE, manifesto, nome, linha["url"], conteudo,
                             observacao=f"{linha['tipo']} {linha['periodo']}".strip())
            print(f"{nome}: {len(conteudo)} bytes", flush=True)
            del conteudo
        with trava:
            falta_reduzir = (manifesto[nome]["no_git"] == "nao"
                             and not manifesto[nome].get("sha256_reduzido"))
            original = cc.caminho_do_original(FONTE, manifesto[nome])
        if falta_reduzir:
            reduzido = destino / "reduzido" / (Path(nome).stem + ".parquet")
            conteudo = cc.gravar_reduzido(ler_posto(original), reduzido)
            with trava:
                cc.registrar_reduzido(FONTE, manifesto, nome, reduzido, conteudo)
            print(f"  reduzido {reduzido.name}: {len(conteudo)} bytes", flush=True)

    with ThreadPoolExecutor(TRABALHADORES) as executor:
        for resultado in executor.map(um, [l for _, l in tabela.iterrows()]):
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
