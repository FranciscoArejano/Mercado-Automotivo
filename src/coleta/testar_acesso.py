#!/usr/bin/env python3
"""Teste de acesso das cinco fontes da rodada 13 (energia, frota e emissoes).

Para cada fonte, pede as paginas e APIs de entrada e registra o que abriu e o que
nao abriu (codigo HTTP ou erro de conexao), sem contornar bloqueio: 403, desafio
de robo ou conexao recusada se registram e a fonte fica de fora. O resultado vai
para `dados/bruto/acesso_fontes_energia.csv` (uma linha por tentativa; as
tentativas anteriores ficam, para que a historia do acesso nao se perca).

Uso:
    python src/coleta/testar_acesso.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coleta.comum_coleta import agora  # noqa: E402
from comum import config  # noqa: E402

CAMPOS = ["data_teste", "fonte", "metodo", "url", "resultado", "bytes", "observacao"]

SONDAS = [
    ("aneel_gd", "GET", "https://dadosabertos.aneel.gov.br/api/3/action/package_show"
     "?id=relacao-de-empreendimentos-de-geracao-distribuida", None),
    ("aneel_gd", "GET", "https://www.aneel.gov.br/", None),
    ("aneel_tarifas", "GET", "https://dadosabertos.aneel.gov.br/api/3/action/package_show"
     "?id=tarifas-distribuidoras-energia-eletrica", None),
    ("aneel_tarifas", "GET", "https://portalrelatorios.aneel.gov.br/", None),
    ("senatran_frota", "GET", "https://www.gov.br/transportes/pt-br/assuntos/transito/"
     "conteudo-Senatran/estatisticas-frota-de-veiculos-senatran", None),
    ("anp_precos", "GET", "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
     "serie-historica-de-precos-de-combustiveis", None),
    ("anp_precos", "GET", "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-"
     "concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/"
     "serie-historica-do-levantamento-de-precos", None),
    ("seeg", "GET", "https://seeg.eco.br/dados/", None),
    ("seeg", "HEAD", "https://seeg.obass.haus/wp-content/uploads/2026/11/Dados-nacionais-14.0.xlsx",
     None),
    ("seeg", "GET", "https://plataforma.seeg.eco.br/", None),
    ("seeg", "POST", "https://api.plataforma.seeg.eco.br/graphql",
     {"query": "query { collectionVersion }"}),
    ("mcti_fator", "GET", "https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/sirene/"
     "dados-e-ferramentas/fatores-de-emissao", None),
]


def sondar(metodo: str, url: str, corpo: dict | None, timeout: float) -> tuple[str, int, str]:
    cabecalho = {"User-Agent": config.USER_AGENT}
    try:
        if metodo == "HEAD":
            r = requests.head(url, headers=cabecalho, timeout=timeout, allow_redirects=True)
        elif metodo == "POST":
            r = requests.post(url, json=corpo, headers=cabecalho, timeout=timeout)
        else:
            r = requests.get(url, headers=cabecalho, timeout=timeout)
    except requests.RequestException as excecao:
        return "erro de conexao", 0, f"{type(excecao).__name__}: {str(excecao)[:200]}"
    texto = r.text[:4000].lower()
    nota = ""
    if "cloudflare" in texto and r.status_code == 403:
        nota = "bloqueio do Cloudflare ('Sorry, you have been blocked')"
    elif "cloudfront" in texto and r.status_code == 403:
        nota = "bloqueio do CloudFront ('Request blocked')"
    elif "tspd" in texto and len(r.content) < 100_000:
        nota = "desafio de robo (TSPD) em vez da pagina"
    return f"HTTP {r.status_code}", len(r.content), nota


def main(timeout: float = 90) -> int:
    destino = config.ACESSO_FONTES_ENERGIA
    linhas = []
    if destino.exists():
        with destino.open(encoding="utf-8", newline="") as fluxo:
            linhas = list(csv.DictReader(fluxo))
    for fonte, metodo, url, corpo in SONDAS:
        resultado, tamanho, nota = sondar(metodo, url, corpo, timeout)
        print(f"{fonte:15} {resultado:18} {tamanho:>8} {url[:80]} {nota}")
        linhas.append({"data_teste": agora(), "fonte": fonte, "metodo": metodo, "url": url,
                       "resultado": resultado, "bytes": tamanho, "observacao": nota})
    with destino.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(linhas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
