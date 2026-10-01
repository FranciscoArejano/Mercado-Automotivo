"""Fontes de origem: nada de citacao de memoria.

A regra da rodada de validacao: toda fonte registrada foi aberta, e o trecho
que sustenta a data vai copiado junto. Este teste e' a guarda: cada trecho
(as partes separadas por ' [...] ') tem de aparecer literalmente no texto da
pagina guardado em `dados/bruto/origem_paginas/`, e esse texto tem de bater
com o SHA-256 do manifesto. Um trecho parafraseado, ou uma URL que ninguem
abriu, quebra aqui.

As mesmas guardas valem para `dados/referencia/montagem_fontes.csv` (modo de
montagem local). E a coluna `tipo_fonte` tem de estar em dia com o mapeamento
de `config/tipo_fonte_dominio.csv`, que o pesquisador edita.
"""

import csv
import hashlib
import re

import pandas as pd
import pytest

from comum import config, tipo_fonte

DIR = config.DIR_BRUTO / "origem_paginas"
CONFRONTOS = {"confirma", "ajusta_data", "contradiz", "complementa", "inconclusivo"}
DATA = re.compile(r"^(\d{4}(-\d{2})?(-S[12])?)?(/\d{4}(-\d{2})?)?$")
MES = re.compile(r"^(\d{4}(-\d{2})?)?$")
MODOS = {"fabricacao", "ckd", "skd"}  # `desconhecido` e' o padrao, nao se registra


@pytest.fixture(scope="module")
def fontes():
    if not config.ORIGEM_FONTES.exists():
        pytest.skip("sem fontes de origem")
    return pd.read_csv(config.ORIGEM_FONTES, dtype=str, keep_default_na=False)


@pytest.fixture(scope="module")
def montagem():
    if not config.MONTAGEM_FONTES.exists():
        pytest.skip("sem fontes de montagem")
    return pd.read_csv(config.MONTAGEM_FONTES, dtype=str, keep_default_na=False)


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


def test_tipo_fonte_em_dia_com_o_mapeamento(fontes, montagem):
    mapa = tipo_fonte.carregar_mapa()
    assert set(mapa.values()) <= set(tipo_fonte.TIPOS)
    for quadro, coluna in ((fontes, "origem_fonte_url"), (montagem, "fonte_url")):
        primarias = quadro["fonte_primaria"] if "fonte_primaria" in quadro else [""] * len(quadro)
        calculado = [tipo_fonte.tipo_da_citacao(u, p, mapa)
                     for u, p in zip(quadro[coluna], primarias)]
        sem_tipo = sorted({tipo_fonte.dominio(u) for u, t in zip(quadro[coluna], calculado)
                           if not t})
        assert not sem_tipo, f"dominios sem tipo: {sem_tipo}"
        defasados = [u for u, a, b in zip(quadro[coluna], quadro["tipo_fonte"], calculado)
                     if a != b]
        assert not defasados, ("tipo_fonte defasado; rode origem_fonte.py --tipos", defasados)


def test_materia_que_repassa_vale_o_veiculo_original():
    mapa = {"motorshow.com.br": "imprensa_especializada", "autossegredos.com.br": "blog_agregador"}
    url = "https://motorshow.com.br/x"
    assert tipo_fonte.tipo_da_citacao(url, "", mapa) == "imprensa_especializada"
    assert tipo_fonte.tipo_da_citacao(url, "autossegredos.com.br", mapa) == "blog_agregador"


def test_dominio_mais_especifico_vence():
    mapa = {"gov.br": "oficial", "exemplo.gov.br": "imprensa_geral"}
    assert tipo_fonte.tipo_de("https://www.gov.br/x", mapa) == "oficial"
    assert tipo_fonte.tipo_de("https://antt.gov.br/x", mapa) == "oficial"
    assert tipo_fonte.tipo_de("https://exemplo.gov.br/x", mapa) == "imprensa_geral"
    assert tipo_fonte.tipo_de("https://naogov.br/x", mapa) == ""


def test_montagem_trecho_literal_e_pagina_no_manifesto(montagem, manifesto):
    faltando = []
    for _, linha in montagem.iterrows():
        assert linha["pagina_salva"] in manifesto, linha["pagina_salva"]
        assert linha["fonte_url"] == manifesto[linha["pagina_salva"]]["url"]
        arquivo = DIR / f"{linha['pagina_salva']}.txt"
        assert (hashlib.sha256(arquivo.read_bytes()).hexdigest()
                == manifesto[linha["pagina_salva"]]["sha256_texto"])
        texto = arquivo.read_text(encoding="utf-8")
        for parte in linha["fonte_trecho"].split(" [...] "):
            if parte not in texto:
                faltando.append(f"{linha['marca']}/{linha['modelo']}: {parte[:60]}")
    assert not faltando, faltando


def test_montagem_campos_validos(montagem):
    assert set(montagem["montagem_local"]) <= MODOS
    assert set(montagem["onde"]) <= {"brasil", "exterior"}
    for coluna in ("periodo_inicio", "periodo_fim", "data_fonte"):
        ruins = [d for d in montagem[coluna] if not MES.match(d)]
        assert not ruins, (coluna, ruins)
    assert (montagem["periodo_inicio"] != "").all()
    propostas = pd.read_csv(config.PROPOSTA_CLASSIFICACAO, dtype=str, keep_default_na=False)
    chaves = set(map(tuple, propostas[["marca", "modelo", "segmento"]].to_numpy()))
    orfas = [tuple(c) for c in montagem[["marca", "modelo", "segmento"]].to_numpy()
             if tuple(c) not in chaves]
    assert not orfas, orfas
