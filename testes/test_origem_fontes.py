"""Fontes de origem: nada de citacao de memoria.

A regra da rodada de validacao: toda fonte registrada foi aberta, e o trecho
que sustenta a data vai copiado junto. Este teste e' a guarda: cada trecho
(as partes separadas por ' [...] ') tem de aparecer literalmente no texto da
pagina guardado em `dados/bruto/origem_paginas/`, e esse texto tem de bater
com o SHA-256 do manifesto. Um trecho parafraseado, ou uma URL que ninguem
abriu, quebra aqui.
"""

import csv
import hashlib
import re

import pandas as pd
import pytest

from comum import config

DIR = config.DIR_BRUTO / "origem_paginas"
CONFRONTOS = {"confirma", "ajusta_data", "contradiz", "complementa", "inconclusivo"}
DATA = re.compile(r"^(\d{4}(-\d{2})?(-S[12])?)?(/\d{4}(-\d{2})?)?$")


@pytest.fixture(scope="module")
def fontes():
    if not config.ORIGEM_FONTES.exists():
        pytest.skip("sem fontes de origem")
    return pd.read_csv(config.ORIGEM_FONTES, dtype=str, keep_default_na=False)


@pytest.fixture(scope="module")
def manifesto():
    with (DIR / "manifesto.csv").open(encoding="utf-8", newline="") as fluxo:
        return {linha["nome"]: linha for linha in csv.DictReader(fluxo)}


def test_todo_trecho_aparece_literalmente_na_pagina_guardada(fontes):
    faltando = []
    for _, linha in fontes.iterrows():
        texto = (DIR / f"{linha['pagina_salva']}.txt").read_text(encoding="utf-8")
        for parte in linha["origem_fonte_trecho"].split(" [...] "):
            if parte not in texto:
                faltando.append(f"{linha['marca']}/{linha['modelo']}: {parte[:60]}")
    assert not faltando, faltando


def test_pagina_guardada_bate_com_o_manifesto_e_com_a_url(fontes, manifesto):
    for nome in set(fontes["pagina_salva"]):
        assert nome in manifesto, nome
        arquivo = DIR / f"{nome}.txt"
        assert hashlib.sha256(arquivo.read_bytes()).hexdigest() == manifesto[nome]["sha256_texto"]
        primeira = arquivo.read_text(encoding="utf-8").splitlines()[0]
        assert primeira == f"URL: {manifesto[nome]['url']}"
    for _, linha in fontes.iterrows():
        assert linha["origem_fonte_url"] == manifesto[linha["pagina_salva"]]["url"]


def test_campos_validos(fontes):
    assert set(fontes["confronto_com_proposta"]) <= CONFRONTOS
    ruins = [d for d in fontes["origem_data_fonte"] if not DATA.match(d)]
    assert not ruins, ruins


def test_toda_fonte_aponta_para_um_modelo_do_rascunho(fontes):
    propostas = pd.read_csv(config.PROPOSTA_CLASSIFICACAO, dtype=str, keep_default_na=False)
    chaves = set(map(tuple, propostas[["marca", "modelo", "segmento"]].to_numpy()))
    orfas = [tuple(c) for c in fontes[["marca", "modelo", "segmento"]].to_numpy()
             if tuple(c) not in chaves]
    assert not orfas, orfas
