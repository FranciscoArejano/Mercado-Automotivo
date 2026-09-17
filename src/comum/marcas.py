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
CAMPOS_MARCAS_PLANILHA = ["marca_planilha", "marca_painel", "observacao"]


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


@lru_cache(maxsize=1)
def carregar_apelidos_da_planilha() -> tuple[tuple[str, str], ...]:
    """Marcas que a planilha de controle escreve diferente da fonte (sec.7).

    A planilha e' controle independente, montado a' mao, e escreve a marca por
    extenso -- "Volkswagen Gol" onde a Fenabrave publica "VW/GOL". Sem esta
    tabela, 3,9 milhoes de unidades ficariam sem contraparte e a comparacao
    acusaria divergencia onde nao ha' nenhuma.

    Isto **nao** e' harmonizacao do painel: o painel nao e' tocado, e `regras.csv`
    segue vazio. E' vocabulario de um arquivo de controle sendo traduzido para o
    vocabulario da fonte, so' para a comparacao. O humano escreve; o codigo le'.

    Devolve pares (prefixo_normalizado, marca_no_painel), mais longos primeiro.
    """
    if not config.MARCAS_PLANILHA.exists():
        return ()
    with config.MARCAS_PLANILHA.open(encoding="utf-8", newline="") as fluxo:
        pares = [
            (normalizar_tipografia(linha["marca_planilha"]).upper(),
             normalizar_tipografia(linha["marca_painel"]).upper())
            for linha in csv.DictReader(fluxo)
            if normalizar_tipografia(linha.get("marca_planilha", ""))
        ]
    return tuple(sorted(pares, key=lambda par: (-len(par[0]), par[0])))


def separar_da_planilha(nome: str) -> Separacao:
    """Separa um nome da planilha de controle, honrando os apelidos.

    Os apelidos vem antes da lista de marcas do painel, e e' deliberado:
    "Chevrolet Onix" casaria com a marca `CHEVROLET` do painel, que existe mas e'
    variante rara da fonte (169 unidades). A marca certa e' `GM`.
    """
    limpo = normalizar_tipografia(nome)
    alvo = limpo.upper()
    for prefixo, marca_painel in carregar_apelidos_da_planilha():
        if alvo == prefixo:
            return Separacao(marca_painel, "", "apelido_da_planilha", True)
        if alvo.startswith(prefixo + " "):
            return Separacao(marca_painel, normalizar_tipografia(limpo[len(prefixo):]),
                             "apelido_da_planilha", True)
    return separar(limpo)
