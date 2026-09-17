"""Chave do modelo e nomes que nao designam veiculo (rodada 2, D1 e D2).

**D1 -- caixa na chave.** A ESPEC sec.4 proibe uniformizar maiusculas *na
transcricao*: `nome_completo_fonte` e `modelo_fonte` guardam o que a fonte
escreveu, letra por letra. Mas a **chave** do painel e' outra coisa. A fonte
escreveu `MITSUBISHI/Outlander` de 2014-01 a 2022-07 (35.231 unidades) e
`MITSUBISHI/OUTLANDER` em 2022-12 (8 unidades): sem normalizar a chave, o mesmo
carro vira duas fichas, com uma saida e uma entrada fabricadas. E' o unico par
na janela atual, mas a retroacao a 2003 multiplica a chance de reincidencia.

Normalizar caixa **nao** e' fundir modelos: nao ha' decisao metodologica em
dizer que `Outlander` e `OUTLANDER` sao a mesma cadeia de caracteres. Fusao de
produtos distintos continua exigindo linha em `regras.csv`.

**D2 -- nomes que nao sao veiculos.** `FIAT/FIAT`, `FIAT/FAG`,
`FORD/ENGERAUTO SPARTAKUS`, `VW/ZILK`, `TOYOTA/RIBEIRAUTO` -- registro avulso,
encarrocador, erro de cadastro. Nada e' apagado do painel: ele ganha a coluna
`nome_suspeito`, e `saidas/nomes_suspeitos.csv` lista os candidatos a revisao.

A marcacao automatica cobre so' o caso objetivo -- **nome do modelo igual ao da
marca**. O resto vem de `config/nomes_nao_veiculo.csv`, lista curada com motivo
por linha, porque volume baixo nao basta como criterio nos dois sentidos:
`TOYOTA/RIBEIRAUTO` soma 67 unidades em 25 meses e escaparia de qualquer corte
de volume, enquanto `CITROEN/C4` e `DODGE/CHARGER` tem uma unidade so' e sao
carros de verdade.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache

import pandas as pd

from . import config
from .texto import normalizar_tipografia

CAMPOS_NAO_VEICULO = ["marca", "modelo", "motivo"]

_PONTUACAO = re.compile(r"[^A-Z0-9 ]+")
_ESPACOS = re.compile(r" +")


def chave(texto: str) -> str:
    """Forma canonica de marca ou modelo para uso como chave -- so' caixa e espaco."""
    return normalizar_tipografia(texto).upper()


@lru_cache(maxsize=1)
def nao_veiculos() -> tuple[tuple[str, str, str], ...]:
    """Lista curada de (marca, modelo, motivo).

    Marca vazia vale para qualquer marca; modelo vazio, para qualquer modelo
    daquela marca. Linha com os dois vazios e' ignorada.
    """
    if not config.NOMES_NAO_VEICULO.exists():
        return ()
    with config.NOMES_NAO_VEICULO.open(encoding="utf-8", newline="") as fluxo:
        return tuple(
            (chave(linha.get("marca", "")), chave(linha.get("modelo", "")),
             normalizar_tipografia(linha.get("motivo", "")))
            for linha in csv.DictReader(fluxo)
            if normalizar_tipografia(linha.get("modelo", ""))
            or normalizar_tipografia(linha.get("marca", ""))
        )


def motivo_nao_veiculo(marca: str, modelo: str) -> str:
    """Motivo pelo qual o nome nao designa veiculo; vazio quando designa."""
    marca_chave, modelo_chave = chave(marca), chave(modelo)
    if marca_chave and marca_chave == modelo_chave:
        return "nome do modelo igual ao da marca"
    for curada_marca, curada_modelo, motivo in nao_veiculos():
        casa_marca = curada_marca in ("", marca_chave)
        casa_modelo = curada_modelo in ("", modelo_chave)
        if casa_marca and casa_modelo:
            return motivo or "consta de config/nomes_nao_veiculo.csv"
    return ""


def canonizar(quadro: pd.DataFrame, colunas: tuple[str, ...] = ("marca", "modelo")) -> pd.DataFrame:
    """Devolve o quadro com as colunas de chave em caixa canonica."""
    saida = quadro.copy()
    for coluna in colunas:
        if coluna in saida.columns:
            saida[coluna] = saida[coluna].map(chave)
    return saida


def colisoes_de_caixa(quadro: pd.DataFrame, colunas: tuple[str, ...]) -> pd.DataFrame:
    """Grafias que so' diferem por caixa e, sem normalizacao, virariam fichas separadas."""
    presentes = [c for c in colunas if c in quadro.columns]
    if not presentes:
        return pd.DataFrame()
    distintos = quadro[presentes].drop_duplicates()
    for coluna in presentes:
        distintos[f"{coluna}_chave"] = distintos[coluna].map(chave)
    chaves = [f"{c}_chave" for c in presentes]
    contagem = distintos.groupby(chaves)[presentes[0]].transform("size")
    return distintos[contagem > 1].sort_values(chaves)


def inventario(por_modelo: pd.DataFrame) -> pd.DataFrame:
    """Um registro por modelo, com volume, presenca e o motivo de suspeita."""
    chaves = ["marca", "modelo", "segmento"]
    ativos = por_modelo[por_modelo["unidades"] > 0]
    if ativos.empty:
        return pd.DataFrame()
    resumo = (
        ativos.groupby(chaves, as_index=False)
        .agg(unidades=("unidades", "sum"), meses=("mes_ref", "nunique"),
             primeiro_mes=("mes_ref", "min"), ultimo_mes=("mes_ref", "max"))
    )
    resumo["motivo"] = [
        motivo_nao_veiculo(linha.marca, linha.modelo) for linha in resumo.itertuples()
    ]
    resumo["nome_suspeito"] = resumo["motivo"] != ""
    resumo["volume_infimo"] = (
        (resumo["unidades"] <= config.SUSPEITO_VOLUME_MAXIMO)
        & (resumo["meses"] <= config.SUSPEITO_MESES_MAXIMO)
    )
    return resumo.sort_values(["nome_suspeito", "unidades"], ascending=[False, True])


def candidatos_a_revisao(inventario_modelos: pd.DataFrame) -> pd.DataFrame:
    """Ja' marcados, mais os de volume infimo que ainda ninguem olhou."""
    if inventario_modelos.empty:
        return inventario_modelos
    return inventario_modelos[
        inventario_modelos["nome_suspeito"] | inventario_modelos["volume_infimo"]
    ]


def chave_de_comparacao(texto: str) -> str:
    """Chave para confrontar o painel com um arquivo externo. **Nunca grava.**

    `chave` normaliza so' caixa, porque e' a chave do painel e a sec.4 e'
    restritiva sobre o que se pode uniformizar num dado que vai ser publicado.
    Esta aqui e' outra coisa: existe so' para o merge da etapa 7, onde os dois
    lados sao vocabularios diferentes descrevendo o mesmo carro. A planilha de
    controle escreve `up!`, `Doblò`, `Etios Sedã`; a fonte publica `UP`,
    `DOBLO`, `ETIOS SEDAN`. Sem dobrar acento e pontuacao, 2,6 milhoes de
    unidades apareceriam como "sem contraparte" e o truncamento ficaria
    superestimado por uma ordem de grandeza.

    Dobra acento, remove pontuacao e colapsa espaco. O painel nao ve nada disso:
    quem chama isto e' o comparador, e as grafias originais vao lado a lado no
    CSV de saida.
    """
    base = chave(texto)
    sem_acento = "".join(
        caractere for caractere in unicodedata.normalize("NFD", base)
        if unicodedata.category(caractere) != "Mn"
    )
    return _ESPACOS.sub(" ", _PONTUACAO.sub(" ", sem_acento)).strip()
