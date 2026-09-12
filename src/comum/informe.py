"""Leitura de um informe mensal da Fenabrave (ESPEC.md sec.4).

A tabela que sustenta o painel e' a de *sub-segmentos* -- as paginas
"Modelos mais emplacados acumulado ate <Mes>/<Ano>", secoes AUTOMOVEIS e
COMERCIAIS LEVES. Cada linha traz, nesta ordem posicional:

    <posicao>o  <NOME COMPLETO>  <mes anterior>  <mes de referencia>  <acumulado>  <part.>%

A leitura e' **posicional**, contada da direita para a esquerda: os quatro
ultimos campos numericos sao os valores, e tudo o que sobra a' esquerda e' o
nome. Isso e' deliberado -- ver ESPEC.md sec.7, item 1: rotulo de cabecalho na
fonte pode estar errado; posicao de coluna, nao. O cabecalho e' usado apenas
como *conferencia*, nunca como chave.

A pagina "Ranking dos emplacamentos em <Mes>/<Ano>" (top 50 de cada segmento)
e' lida em separado e serve de verificacao independente dentro do proprio
arquivo: todo modelo do ranking tem de reaparecer nas tabelas de sub-segmento
com o mesmo numero. E' esse teste que pega a leitura da coluna errada.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

from .texto import eh_numero_br, normalizar_tipografia, numero_br

# --------------------------------------------------------------------- padroes
RE_ORDINAL = re.compile(r"^(\d{1,3})[º°]\s+(.*)$")
RE_ORDINAL_INTERNO = re.compile(r"(\d{1,3})[º°]\s+")
RE_EDICAO = re.compile(r"^Ed\.\s*(\d+)", re.IGNORECASE)
RE_ANO = re.compile(r"(19|20)\d{2}")

# Glifos de variacao que a fonte intercala entre as colunas.
MARCADORES = {"=", "▲", "▼", "↑", "↓", "–", "—", "-", "*"}

MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

SEGMENTO_POR_MARCADOR = {
    "AUTOMOVEIS": "automoveis",
    "COMERCIAIS LEVES": "comerciais_leves",
    "CAMINHOES": "fora_de_escopo",
    "CAMINOES": "fora_de_escopo",          # erro de grafia presente na fonte
    "ONIBUS": "fora_de_escopo",
    "MOTOS": "fora_de_escopo",
    "MOTOCICLETAS": "fora_de_escopo",
    "IMPLEMENTOS RODOVIARIOS": "fora_de_escopo",
}

PALAVRAS_CABECALHO = {
    "modelo", "modelos", "part", "acumulado", "quant", "var", "variacao",
    "sub", "segmento", "%",
}

RE_TITULO_SUBSEGMENTO = re.compile(r"^modelos mais emplacados acumulado", re.IGNORECASE)
RE_TITULO_RANKING = re.compile(r"^ranking dos emplacamentos em", re.IGNORECASE)
RE_TITULO_RESUMO = re.compile(r"^resumo mensal", re.IGNORECASE)
RE_LINHA_AUTOS = re.compile(r"^A\)\s*Autos\b", re.IGNORECASE)
RE_LINHA_LEVES = re.compile(r"^B\)\s*Com\.?\s*Leves\b", re.IGNORECASE)


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


# ----------------------------------------------------------------- estruturas
@dataclass
class LinhaModelo:
    segmento: str
    sub_segmento_fonte: str
    posicao_fonte: int
    nome_completo_fonte: str
    unidades_mes: float
    unidades_mes_anterior: float
    unidades_acumulado: float
    participacao_pct: float
    pagina: int


@dataclass
class LinhaRanking:
    segmento: str
    posicao_fonte: int
    nome_completo_fonte: str
    unidades_mes: float
    pagina: int


@dataclass
class Extracao:
    arquivo: str
    mes_declarado: str | None = None
    edicao: str | None = None
    paginas: int = 0
    paginas_sem_texto: list[int] = field(default_factory=list)
    total_publicado: dict[str, float] = field(default_factory=dict)
    subtotal_publicado: dict[tuple[str, str], float] = field(default_factory=dict)
    modelos: list[LinhaModelo] = field(default_factory=list)
    ranking: list[LinhaRanking] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


# -------------------------------------------------------------------- leitura
def _linha_modelo(linha: str) -> tuple[int, str, float, float, float, float] | None:
    """Le uma linha de modelo pela posicao dos campos, da direita para a esquerda."""
    achado = RE_ORDINAL.match(linha)
    if not achado:
        return None
    tokens = [t for t in achado.group(2).split(" ") if t and t not in MARCADORES]
    if len(tokens) < 4 or not tokens[-1].endswith("%"):
        return None
    percentual, valores = tokens[-1][:-1], tokens[-4:-1]
    if not eh_numero_br(percentual) or not all(eh_numero_br(v) for v in valores):
        return None
    nome = " ".join(tokens[:-4]).strip()
    if not nome:
        return None
    anterior, mes, acumulado = (numero_br(v) for v in valores)
    return int(achado.group(1)), nome, anterior, mes, acumulado, numero_br(percentual)


def _eh_ruido(linha: str) -> bool:
    """Linhas de moldura: cabecalho de pagina, cabecalho de coluna, rodape."""
    if not linha:
        return True
    simples = _sem_acento(linha).lower()
    if simples.startswith((
        "ed.", "informativo", "sao paulo", "www.fenabrave", "modelos mais emplacados",
        "ranking dos", "fonte:", "obs:",
    )):
        return True
    tokens = [t.strip(".:") for t in _sem_acento(linha).lower().split(" ") if t.strip(".:")]
    if not tokens:
        return True
    return all(
        t in PALAVRAS_CABECALHO
        or t in MESES_PT
        or re.fullmatch(r"(19|20)\d{2}", t)
        or t in {"total"}
        or eh_numero_br(t)
        or t.rstrip("%").replace(",", ".").replace(".", "").isdigit()
        for t in tokens
    )


def _subtotal(linha: str) -> float | None:
    """A linha 'Total ...' que a fonte publica ao pe' de cada sub-segmento."""
    simples = _sem_acento(linha).lower()
    if not simples.startswith("total"):
        return None
    tokens = [t for t in linha.split(" ")[1:] if t and t not in MARCADORES]
    # Layout antigo: Total <mes anterior> <mes> <acumulado> <100%>. O percentual
    # fecha a linha e nao entra na contagem posicional.
    numeros = [t for t in tokens if eh_numero_br(t)]
    if len(numeros) >= 3:
        return numero_br(numeros[1])
    return None


def _mes_do_titulo(titulo: str) -> str | None:
    """'Resumo Mensal Agosto de 2026' -> '2026-08'. Conferencia, nunca chave."""
    simples = _sem_acento(titulo).lower()
    ano = None
    for achado in RE_ANO.finditer(simples):
        ano = achado.group(0)
    if ano is None:
        return None
    for nome, numero in MESES_PT.items():
        if len(nome) > 3 and re.search(rf"\b{nome}\b", simples):
            return f"{ano}-{numero:02d}"
    for nome, numero in MESES_PT.items():
        if len(nome) == 3 and re.search(rf"\b{nome}\b", simples):
            return f"{ano}-{numero:02d}"
    return None


def _totais_do_resumo(linhas: list[str]) -> dict[str, float]:
    """Primeira coluna numerica de 'A) Autos' e 'B) Com. Leves' = mes de referencia."""
    totais: dict[str, float] = {}
    for linha in linhas:
        alvo = None
        if RE_LINHA_AUTOS.match(linha):
            alvo = "automoveis"
        elif RE_LINHA_LEVES.match(linha):
            alvo = "comerciais_leves"
        if alvo is None or alvo in totais:
            continue
        numeros = [t for t in linha.split(" ") if eh_numero_br(t)]
        if numeros:
            totais[alvo] = numero_br(numeros[0])
    return totais


def _ranking_da_pagina(pagina, numero_pagina: int) -> list[LinhaRanking]:
    """A pagina de ranking tem duas colunas lado a lado; separa por posicao em x."""
    palavras = pagina.extract_words(use_text_flow=False, keep_blank_chars=False)
    if not palavras:
        return []
    meio = (pagina.width or 0) / 2
    colunas: dict[str, dict[float, list]] = {"automoveis": {}, "comerciais_leves": {}}
    for palavra in palavras:
        lado = "automoveis" if palavra["x0"] < meio else "comerciais_leves"
        chave = round(palavra["top"], 1)
        # Junta linhas cujo topo difere por menos de 2 pontos (mesma linha visual).
        destino = next((k for k in colunas[lado] if abs(k - chave) < 2.0), chave)
        colunas[lado].setdefault(destino, []).append(palavra)

    linhas: list[LinhaRanking] = []
    for segmento, mapa in colunas.items():
        for topo in sorted(mapa):
            texto = normalizar_tipografia(
                " ".join(p["text"] for p in sorted(mapa[topo], key=lambda p: p["x0"]))
            )
            achado = RE_ORDINAL.match(texto)
            if not achado:
                continue
            tokens = [t for t in achado.group(2).split(" ") if t and t not in MARCADORES]
            if len(tokens) < 2 or not eh_numero_br(tokens[-1]):
                continue
            nome = " ".join(tokens[:-1]).strip()
            if not nome:
                continue
            linhas.append(LinhaRanking(
                segmento=segmento,
                posicao_fonte=int(achado.group(1)),
                nome_completo_fonte=nome,
                unidades_mes=numero_br(tokens[-1]),
                pagina=numero_pagina,
            ))
    return linhas


def ler(caminho: Path) -> Extracao:
    """Extrai de um informe tudo o que as etapas seguintes precisam."""
    extracao = Extracao(arquivo=caminho.name)
    segmento_corrente: str | None = None

    with pdfplumber.open(caminho) as pdf:
        extracao.paginas = len(pdf.pages)
        for numero, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text() or ""
            if not texto.strip():
                extracao.paginas_sem_texto.append(numero)
                continue
            linhas = [normalizar_tipografia(l) for l in texto.split("\n")]

            for linha in linhas:
                marcador = _sem_acento(linha).upper().strip()
                if marcador in SEGMENTO_POR_MARCADOR:
                    segmento_corrente = SEGMENTO_POR_MARCADOR[marcador]

            titulo = next(
                (l for l in linhas[:8] if RE_TITULO_SUBSEGMENTO.match(_sem_acento(l))
                 or RE_TITULO_RANKING.match(_sem_acento(l))
                 or RE_TITULO_RESUMO.match(_sem_acento(l))),
                "",
            )
            if extracao.edicao is None:
                for linha in linhas[:4]:
                    achado = RE_EDICAO.match(linha)
                    if achado:
                        extracao.edicao = achado.group(1)
                        break

            if RE_TITULO_RESUMO.match(_sem_acento(titulo)):
                if extracao.mes_declarado is None:
                    extracao.mes_declarado = _mes_do_titulo(titulo)
                for chave, valor in _totais_do_resumo(linhas).items():
                    extracao.total_publicado.setdefault(chave, valor)
                continue

            if RE_TITULO_RANKING.match(_sem_acento(titulo)):
                extracao.ranking.extend(_ranking_da_pagina(pagina, numero))
                continue

            if not RE_TITULO_SUBSEGMENTO.match(_sem_acento(titulo)):
                continue
            if segmento_corrente not in ("automoveis", "comerciais_leves"):
                continue

            sub_segmento = ""
            for linha in linhas:
                lido = _linha_modelo(linha)
                if lido is not None:
                    posicao, nome, anterior, mes, acumulado, percentual = lido
                    if not sub_segmento:
                        extracao.avisos.append(
                            f"p{numero}: linha de modelo sem sub-segmento identificado: {linha!r}"
                        )
                    extracao.modelos.append(LinhaModelo(
                        segmento=segmento_corrente,
                        sub_segmento_fonte=sub_segmento,
                        posicao_fonte=posicao,
                        nome_completo_fonte=nome,
                        unidades_mes=mes,
                        unidades_mes_anterior=anterior,
                        unidades_acumulado=acumulado,
                        participacao_pct=percentual,
                        pagina=numero,
                    ))
                    continue
                subtotal = _subtotal(linha)
                if subtotal is not None:
                    if sub_segmento:
                        extracao.subtotal_publicado[(segmento_corrente, sub_segmento)] = subtotal
                    continue
                marcador = _sem_acento(linha).upper().strip()
                if marcador in SEGMENTO_POR_MARCADOR or _eh_ruido(linha):
                    continue
                sub_segmento = linha

    return extracao
