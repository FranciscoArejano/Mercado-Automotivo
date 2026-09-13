"""Quais meses tem dado utilizavel, e quais sao lacuna.

Distincao que importa para D3: um mes **sem informe legivel** e' lacuna e sai
das janelas (nunca vira zero, sec.9.2); um mes com informe em que o modelo nao
aparece e' zero, porque a fonte publicou aquele mes e nao listou o modelo.
"""

from __future__ import annotations

import csv

from . import config

CAMPOS = ["mes", "linhas", "situacao", "metodo_predominante", "arquivo_origem"]


def registrar(linhas: list[dict]) -> None:
    caminho = config.DIR_PROCESSADO / "meses_extraidos.csv"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=CAMPOS)
        escritor.writeheader()
        for linha in sorted(linhas, key=lambda item: item["mes"]):
            escritor.writerow({campo: linha.get(campo, "") for campo in CAMPOS})


def uteis() -> set[str]:
    """Meses cuja extracao produziu linhas. Base para separar zero de lacuna."""
    caminho = config.DIR_PROCESSADO / "meses_extraidos.csv"
    if caminho.exists():
        with caminho.open(encoding="utf-8", newline="") as fluxo:
            return {
                l["mes"] for l in csv.DictReader(fluxo)
                if l["situacao"] in ("ok", "ok_reconstruido")
            }
    # Sem o registro da etapa 02, cai para o que foi baixado.
    if config.MANIFESTO.exists():
        with config.MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
            return {l["mes"] for l in csv.DictReader(fluxo)}
    return set()


def lacunas() -> list[dict]:
    """Meses baixados cuja extracao nao produziu nada, mais os nao baixados."""
    caminho = config.DIR_PROCESSADO / "meses_extraidos.csv"
    registros: list[dict] = []
    if caminho.exists():
        with caminho.open(encoding="utf-8", newline="") as fluxo:
            registros = [
                l for l in csv.DictReader(fluxo)
                if l["situacao"] not in ("ok", "ok_reconstruido")
            ]
    if config.LACUNAS.exists():
        with config.LACUNAS.open(encoding="utf-8", newline="") as fluxo:
            for linha in csv.DictReader(fluxo):
                registros.append({
                    "mes": linha["mes"], "linhas": "0",
                    "situacao": linha.get("motivo", "sem_informe"),
                    "metodo_predominante": "", "arquivo_origem": "",
                })
    return sorted(registros, key=lambda item: item["mes"])
