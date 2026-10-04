#!/usr/bin/env python3
"""Baixa do Comex Stat (MDIC) a importacao e a exportacao de veiculos, mes a mes.

API `https://api-comexstat.mdic.gov.br/general` (POST, JSON). Uma consulta por
fluxo (importacao, exportacao) x posicao (8703 automoveis, 8704 veiculos de
carga) x ano, de 1997 ao ultimo mes publicado, em duas versoes:

- com `ncm` e `country` nos `details` (o produto);
- so' com `ncm` (a conferencia: a soma sobre paises tem de bater com ela).

Duas armadilhas da API, testadas pelo pesquisador: a quantidade
(`metricStatistic`) so' vem com `ncm` nos `details` (sem ele, erro 400); e o
periodo filtra ano e mes separadamente -- por isso cada consulta e' de um ano,
de `-01` a `-12`.

Cada resposta vai crua para `dados/bruto/comex/<fluxo>_<posicao>_<ano>_<versao>.json`,
com SHA-256, tamanho, linhas e a consulta no manifesto
(`dados/bruto/comex/manifesto.csv`). Tambem guarda a tabela de NCMs (descricao e
unidade estatistica, `tables/ncm`) e a data da ultima atualizacao. Arquivo ja'
baixado e no manifesto nao e' baixado de novo (retomada).

Uso:
    python src/ferramentas/comex_baixar.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import config  # noqa: E402

API = "https://api-comexstat.mdic.gov.br"
DIR = config.DIR_BRUTO / "comex"
MANIFESTO = DIR / "manifesto.csv"
CAMPOS = ["arquivo", "consulta", "sha256", "bytes", "linhas", "data_acesso"]
FLUXOS = {"import": "importacao", "export": "exportacao"}
POSICOES = ("8703", "8704")
PRIMEIRO_ANO = 1997
METRICAS = ["metricFOB", "metricKG", "metricStatistic"]


def _curl(argumentos: list[str], tentativas: int = 8) -> bytes:
    """A API limita o ritmo (HTTP 429): espera crescente, comecando em 30 s."""
    espera = 30
    for tentativa in range(tentativas):
        feito = subprocess.run(["curl", "-sS", "--max-time", "180", "-f", *argumentos],
                               capture_output=True, timeout=240)
        if feito.returncode == 0 and feito.stdout:
            return feito.stdout
        if tentativa < tentativas - 1:
            time.sleep(espera)
            espera = min(espera * 2, 600)
    raise RuntimeError(f"curl falhou ({feito.returncode}): {feito.stderr.decode()[:300]}")


def post(consulta: dict) -> bytes:
    return _curl(["-X", "POST", f"{API}/general", "-H", "Content-Type: application/json",
                  "-d", json.dumps(consulta)])


def get(caminho: str) -> bytes:
    return _curl([f"{API}/{caminho}"])


def consulta(fluxo: str, posicao: str, ano: int, com_pais: bool) -> dict:
    return {"flow": fluxo, "monthDetail": True,
            "period": {"from": f"{ano}-01", "to": f"{ano}-12"},
            "filters": [{"filter": "heading", "values": [posicao]}],
            "details": ["ncm", "country"] if com_pais else ["ncm"],
            "metrics": METRICAS}


def carregar_manifesto() -> dict[str, dict]:
    if not MANIFESTO.exists():
        return {}
    with MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
        return {linha["arquivo"]: linha for linha in csv.DictReader(fluxo)}


def gravar_manifesto(linhas: dict[str, dict]) -> None:
    with MANIFESTO.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(sorted(linhas.values(), key=lambda l: l["arquivo"]))


def guardar(nome: str, conteudo: bytes, descricao: str, manifesto: dict[str, dict]) -> int:
    corpo = json.loads(conteudo)
    if not corpo.get("success", False):
        raise RuntimeError(f"{nome}: a API respondeu sem sucesso: {corpo.get('message')}")
    dados = corpo.get("data")
    linhas = len(dados["list"]) if isinstance(dados, dict) and "list" in dados else (
        len(dados) if isinstance(dados, list) else 1)
    (DIR / nome).write_bytes(conteudo)
    manifesto[nome] = {"arquivo": nome, "consulta": descricao,
                       "sha256": hashlib.sha256(conteudo).hexdigest(), "bytes": len(conteudo),
                       "linhas": linhas,
                       "data_acesso": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    gravar_manifesto(manifesto)
    return linhas


def main() -> int:
    DIR.mkdir(parents=True, exist_ok=True)
    manifesto = carregar_manifesto()
    atualizado = json.loads(get("general/dates/updated"))["data"]
    ultimo_ano = int(atualizado["year"])
    print(f"ultimo mes publicado: {atualizado['year']}-{atualizado['monthNumber']} "
          f"(atualizado em {atualizado['updated']})")
    guardar("ultima_atualizacao.json", get("general/dates/updated"), "GET general/dates/updated",
            manifesto)
    ncms: set[str] = set()
    for fluxo, nome_fluxo in FLUXOS.items():
        for posicao in POSICOES:
            for ano in range(PRIMEIRO_ANO, ultimo_ano + 1):
                for com_pais in (True, False):
                    nome = f"{nome_fluxo}_{posicao}_{ano}_{'pais' if com_pais else 'total'}.json"
                    pedido = consulta(fluxo, posicao, ano, com_pais)
                    if nome in manifesto and (DIR / nome).exists():
                        conteudo = (DIR / nome).read_bytes()
                    else:
                        conteudo = post(pedido)
                        linhas = guardar(nome, conteudo, "POST general " + json.dumps(pedido),
                                         manifesto)
                        print(f"{nome}: {linhas} linhas")
                        time.sleep(3)
                    ncms |= {r["coNcm"] for r in json.loads(conteudo)["data"]["list"]}
    for ncm in sorted(ncms):
        nome = f"ncm_{ncm}.json"
        if nome not in manifesto or not (DIR / nome).exists():
            guardar(nome, get(f"tables/ncm?search={ncm}"), f"GET tables/ncm?search={ncm}",
                    manifesto)
            time.sleep(1)
    print(f"{len(manifesto)} arquivos no manifesto; {len(ncms)} NCMs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
