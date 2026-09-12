"""Separacao de marca e modelo (ESPEC.md sec.4).

A fonte publica o nome comercial como `MARCA/MODELO` ("VW/GOL",
"CAOA CHERY/TIGGO 5X", "VW TRUCK E BUS/EXPRESS"). A barra e' o delimitador que
a *propria fonte* usa, entao ela vem primeiro. So' quando ela falta e' que se
recorre a' lista explicita de marcas conhecidas, por maior prefixo -- nunca
pelo primeiro espaco, que quebraria "Land Rover", "Alfa Romeo", "Great Wall".

Nome nao resolvido nao e' adivinhado: fica registrado para o humano decidir.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache

from . import config
from .texto import normalizar_tipografia

CAMPOS_MARCAS = ["marca_fonte", "observacao"]


@dataclass(frozen=True)
class Separacao:
    marca: str
    modelo: str
    metodo: str        # 'barra' | 'lista_de_marcas' | 'nao_resolvido'
    conhecida: bool    # a marca consta de config/marcas.csv


@lru_cache(maxsize=1)
def carregar_marcas() -> tuple[str, ...]:
    """Lista curada de marcas, em config/marcas.csv. O codigo le'; o humano escreve."""
    if not config.MARCAS.exists():
        return ()
    with config.MARCAS.open(encoding="utf-8", newline="") as fluxo:
        marcas = {
            normalizar_tipografia(linha["marca_fonte"]).upper()
            for linha in csv.DictReader(fluxo)
            if normalizar_tipografia(linha.get("marca_fonte", ""))
        }
    # Mais longas primeiro: "CAOA CHERY" tem de vencer "CAOA".
    return tuple(sorted(marcas, key=lambda m: (-len(m), m)))


def separar(nome_completo_fonte: str) -> Separacao:
    nome = normalizar_tipografia(nome_completo_fonte)
    conhecidas = carregar_marcas()

    if "/" in nome:
        marca, _, modelo = nome.partition("/")
        marca = normalizar_tipografia(marca)
        modelo = normalizar_tipografia(modelo)
        return Separacao(marca, modelo, "barra", marca.upper() in conhecidas)

    alvo = nome.upper()
    for marca in conhecidas:
        if alvo == marca:
            return Separacao(nome, "", "lista_de_marcas", True)
        if alvo.startswith(marca + " "):
            return Separacao(nome[: len(marca)], normalizar_tipografia(nome[len(marca):]),
                             "lista_de_marcas", True)
    return Separacao("", nome, "nao_resolvido", False)
