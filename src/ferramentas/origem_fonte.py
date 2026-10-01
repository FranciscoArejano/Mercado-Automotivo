#!/usr/bin/env python3
"""Abre uma pagina de fonte de origem, guarda o texto e mostra os trechos.

A regra da rodada de validacao: toda fonte de data de producao local tem de ter
sido **aberta nesta rodada**, com o trecho que sustenta a data copiado junto.
Esta ferramenta e' o "abrir": baixa a pagina, extrai o texto, grava em
`dados/bruto/origem_paginas/<nome>.txt` com SHA-256 e data no manifesto, e
imprime as frases que casam com a busca. O trecho registrado em
`dados/referencia/origem_fontes.csv` tem de aparecer literalmente no texto
guardado -- o teste `test_origem_fontes.py` confere. Assim a citacao continua
verificavel mesmo que a pagina mude ou saia do ar.

Com `--tipos`, nao abre nada: recalcula a coluna `tipo_fonte` de
`origem_fontes.csv` a partir de `config/tipo_fonte_dominio.csv` (depois de o
pesquisador editar o mapeamento).

Uso:
    python src/ferramentas/origem_fonte.py URL --nome slug --busca "regex"
    python src/ferramentas/origem_fonte.py --tipos
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from comum import config, tipo_fonte  # noqa: E402

DIR_PAGINAS = config.DIR_BRUTO / "origem_paginas"
MANIFESTO = DIR_PAGINAS / "manifesto.csv"
CAMPOS = ["nome", "url", "sha256_texto", "caracteres", "data_acesso"]
IGNORAR = {"script", "style", "noscript", "svg", "head", "nav", "footer", "form"}
BLOCO = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "tr", "section",
         "article", "header", "blockquote", "td"}


class _Texto(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []
        self.pulando = 0

    def handle_starttag(self, tag, attrs):
        if tag in IGNORAR:
            self.pulando += 1
        elif tag in BLOCO:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in IGNORAR and self.pulando:
            self.pulando -= 1
        elif tag in BLOCO:
            self.partes.append("\n")

    def handle_data(self, data):
        if not self.pulando:
            self.partes.append(data)


def texto_da_pagina(conteudo: str) -> str:
    leitor = _Texto()
    leitor.feed(conteudo)
    bruto = html.unescape("".join(leitor.partes)).replace("\xa0", " ")
    linhas = [re.sub(r"[ \t]+", " ", linha).strip() for linha in bruto.splitlines()]
    return "\n".join(linha for linha in linhas if linha)


def baixar(url: str) -> str:
    feito = subprocess.run(
        ["curl", "-sSL", "--compressed", "--max-time", "60", "-A",
         "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/124.0 Safari/537.36", url],
        capture_output=True, timeout=90)
    if feito.returncode != 0:
        raise RuntimeError(f"curl falhou ({feito.returncode}): {feito.stderr.decode()[:200]}")
    return feito.stdout.decode("utf-8", errors="replace")


def registrar(nome: str, url: str, texto: str) -> Path:
    DIR_PAGINAS.mkdir(parents=True, exist_ok=True)
    destino = DIR_PAGINAS / f"{nome}.txt"
    destino.write_text(f"URL: {url}\n\n{texto}\n", encoding="utf-8")
    linhas = []
    if MANIFESTO.exists():
        with MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
            linhas = [l for l in csv.DictReader(fluxo) if l["nome"] != nome]
    linhas.append({"nome": nome, "url": url,
                   "sha256_texto": hashlib.sha256(destino.read_bytes()).hexdigest(),
                   "caracteres": len(texto),
                   "data_acesso": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    with MANIFESTO.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(sorted(linhas, key=lambda l: l["nome"]))
    return destino


def regravar_tipos() -> int:
    fontes = pd.read_csv(config.ORIGEM_FONTES, dtype=str, keep_default_na=False)
    fontes = tipo_fonte.com_tipo(fontes, tipo_fonte.carregar_mapa())
    sem = sorted({tipo_fonte.dominio(u) for u, t in
                  zip(fontes["origem_fonte_url"], fontes["tipo_fonte"]) if not t})
    fontes.to_csv(config.ORIGEM_FONTES, index=False)
    print(fontes["tipo_fonte"].value_counts().to_string())
    if sem:
        print("dominios sem tipo em config/tipo_fonte_dominio.csv:", ", ".join(sem),
              file=sys.stderr)
        return 1
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("url", nargs="?")
    analisador.add_argument("--nome")
    analisador.add_argument("--busca", default="")
    analisador.add_argument("--tipos", action="store_true",
                            help="so' recalcular a coluna tipo_fonte de origem_fontes.csv")
    args = analisador.parse_args()

    if args.tipos:
        return regravar_tipos()
    if not args.url or not args.nome:
        analisador.error("URL e --nome sao obrigatorios (ou use --tipos)")

    if MANIFESTO.exists():
        with MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
            if any(l["nome"] == args.nome for l in csv.DictReader(fluxo)):
                print(f"{args.nome} ja' esta' no manifesto; escolha outro nome (uma pagina citada "
                      "nao pode ser sobrescrita)", file=sys.stderr)
                return 2
    texto = texto_da_pagina(baixar(args.url))
    if len(texto) < 300:
        print(f"texto curto demais ({len(texto)} caracteres): pagina bloqueada ou vazia; "
              "nada gravado", file=sys.stderr)
        return 2
    destino = registrar(args.nome, args.url, texto)
    print(f"gravado {destino.relative_to(config.RAIZ)} ({len(texto)} caracteres)")
    if args.busca:
        padrao = re.compile(args.busca, re.IGNORECASE)
        for linha in texto.splitlines():
            if padrao.search(linha):
                print("  >", linha[:600])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
