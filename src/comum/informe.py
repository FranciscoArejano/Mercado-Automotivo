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

from . import sub_segmentos
from .texto import eh_numero_br, normalizar_tipografia, numero_br

# ------------------------------------------------------- fontes sem ToUnicode
# Alguns informes (2020-04 a 2020-06, 2023-09, 2024-01, 2024-05) trazem fontes
# embutidas sem mapa ToUnicode. O pdfplumber devolve o codigo do glifo, no
# formato "(cid:82)", em vez do caractere. A estrutura do texto esta' intacta:
# falta so' a tabela de traducao. Os codigos seguem a ordem padrao de glifos
# TrueType (os 258 nomes padrao do Macintosh), em que o indice 3 e' o espaco e
# 3..97 correspondem a ASCII 32..126.
#
# Isto **nao** e' OCR: e' a mesma extracao de texto do pdfplumber, com o mapa
# que o arquivo omitiu. As tres verificacoes da etapa 02 (mes declarado,
# subtotais, ranking x sub-segmento) valem igual e denunciariam um mapa errado.
_GLIFOS_NAO_ASCII = (
    "\u00c4\u00c5\u00c7\u00c9\u00d1\u00d6\u00dc\u00e1\u00e0\u00e2\u00e4\u00e3\u00e5"
    "\u00e7\u00e9\u00e8\u00ea\u00eb\u00ed\u00ec\u00ee\u00ef\u00f1\u00f3\u00f2\u00f4"
    "\u00f6\u00f5\u00fa\u00f9\u00fb\u00fc\u2020\u00b0\u00a2\u00a3\u00a7\u2022\u00b6"
    "\u00df\u00ae\u00a9\u2122\u00b4\u00a8\u2260\u00c6\u00d8\u221e\u00b1\u2264\u2265"
    "\u00a5\u00b5\u2202\u2211\u220f\u03c0\u222b\u00aa\u00ba\u03a9\u00e6\u00f8\u00bf"
    "\u00a1\u00ac\u221a\u0192\u2248\u2206\u00ab\u00bb\u2026\u00a0\u00c0\u00c3\u00d5"
    "\u0152\u0153\u2013\u2014\u201c\u201d\u2018\u2019\u00f7\u25ca\u00ff\u0178\u2044"
    "\u00a4\u2039\u203a\ufb01\ufb02\u2021\u00b7\u201a\u201e\u2030\u00c2\u00ca\u00c1"
    "\u00cb\u00c8\u00cd\u00ce\u00cf\u00cc\u00d3\u00d4\uf8ff\u00d2\u00da\u00db\u00d9"
    "\u0131\u02c6\u02dc\u00af\u02d8\u02d9\u02da\u00b8\u02dd\u02db\u02c7\u0141\u0142"
    "\u0160\u0161\u017d\u017e\u00a6\u00d0\u00f0\u00dd\u00fd\u00de\u00fe\u2212\u00d7"
    "\u00b9\u00b2\u00b3\u00bd\u00bc\u00be\u20a3\u011e\u011f\u0130\u015e\u015f\u0106"
    "\u0107\u010c\u010d\u0111"
)
RE_CID = re.compile(r"\(cid:(\d+)\)")


def _glifo(codigo: int) -> str:
    if 3 <= codigo <= 97:
        return chr(codigo + 29)
    if 98 <= codigo < 98 + len(_GLIFOS_NAO_ASCII):
        return _GLIFOS_NAO_ASCII[codigo - 98]
    return ""


def decodificar_cids(texto: str) -> str:
    """Traduz '(cid:N)' pela ordem padrao de glifos. Devolve o texto inalterado
    quando nao ha' nenhum."""
    if "(cid:" not in texto:
        return texto
    return RE_CID.sub(lambda a: _glifo(int(a.group(1))), texto)


def tem_cids(texto: str) -> bool:
    return "(cid:" in texto


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
    metodo_extracao: str = "texto"


@dataclass
class LinhaRanking:
    segmento: str
    posicao_fonte: int
    nome_completo_fonte: str
    unidades_mes: float
    pagina: int
    metodo_extracao: str = "texto"


@dataclass
class Extracao:
    arquivo: str
    mes_declarado: str | None = None
    edicao: str | None = None
    paginas: int = 0
    paginas_sem_texto: list[int] = field(default_factory=list)
    paginas_com_cid: list[int] = field(default_factory=list)
    paginas_com_ocr: list[int] = field(default_factory=list)
    sub_segmentos_novos: list[str] = field(default_factory=list)
    divergencias_de_secao: list[str] = field(default_factory=list)
    sem_segmento: list[str] = field(default_factory=list)
    total_publicado: dict[str, float] = field(default_factory=dict)
    # Coluna (B) do Resumo Mensal: o total do mes anterior, republicado. E'
    # ela que permite recuperar o total de um mes cujo informe nao e' legivel.
    total_publicado_anterior: dict[str, float] = field(default_factory=dict)
    subtotal_publicado: dict[tuple[str, str], float] = field(default_factory=dict)
    modelos: list[LinhaModelo] = field(default_factory=list)
    ranking: list[LinhaRanking] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


# -------------------------------------------------------------------- leitura
def _desdobrar(linha: str) -> str:
    """Desfaz o desenho duplicado de caractere ("DDeezz JJaann" -> "Dez Jan").

    Alguns informes desenham a mesma linha duas vezes com meio ponto de
    deslocamento, e o extrator devolve cada caractere em dobro. Observado no
    cabecalho de coluna de Jan/2022, que sem isto viraria nome de sub-segmento.
    So' age quando **todos** os tokens da linha estao dobrados, para nao
    estragar nome legitimo.
    """
    tokens = [t for t in linha.split(" ") if t]
    if len(tokens) < 2 or any(len(t) < 4 or len(t) % 2 or t[0::2] != t[1::2] for t in tokens):
        return linha
    return " ".join(t[0::2] for t in tokens)


def _linha_modelo(
    linha: str, tolerar_glifo_solto: bool = False
) -> tuple[int, str, float, float, float, float] | None:
    """Le uma linha de modelo pela posicao dos campos, da direita para a esquerda.

    `tolerar_glifo_solto` vale para paginas vindas de OCR, em que a seta de
    variacao entre as colunas e' reconhecida como uma letra avulsa ("A", "v",
    "W"). Fora do OCR nao se descarta nada: uma letra solta ali seria sinal de
    leitura errada.
    """
    achado = RE_ORDINAL.match(linha)
    if not achado:
        return None
    tokens = [t for t in achado.group(2).split(" ") if t and t not in MARCADORES]
    if tolerar_glifo_solto and len(tokens) > 4:
        tokens = tokens[:1] + [t for t in tokens[1:] if not (len(t) == 1 and t.isalpha())]
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


def _totais_do_resumo(linhas: list[str]) -> dict[str, list[float]]:
    """Colunas numericas de 'A) Autos' e 'B) Com. Leves' no Resumo Mensal.

    A ordem e' posicional: (A) mes de referencia, (B) mes anterior, (C) acumulado
    do ano, (D) mesmo mes do ano anterior, (E) acumulado do ano anterior. Devolve
    a lista inteira; quem chama escolhe a coluna. A (B) importa porque permite
    recuperar o total publicado de um mes cujo proprio informe nao e' legivel.

    Em algumas edicoes (Abr, Nov e Dez/2017, Jan e Fev/2018) o extrator devolve a
    linha de numeros **antes** do rotulo. Por isso, rotulo sem numeros procura na
    linha imediatamente anterior, desde que ela seja so' numeros.
    """
    totais: dict[str, list[float]] = {}
    for posicao, linha in enumerate(linhas):
        alvo = None
        if RE_LINHA_AUTOS.match(linha):
            alvo = "automoveis"
        elif RE_LINHA_LEVES.match(linha):
            alvo = "comerciais_leves"
        if alvo is None or alvo in totais:
            continue
        numeros = [t for t in linha.split(" ") if eh_numero_br(t)]
        if not numeros and posicao:
            anterior = [t for t in linhas[posicao - 1].split(" ") if t]
            if anterior and all(eh_numero_br(t) for t in anterior):
                numeros = anterior
        if numeros:
            totais[alvo] = [numero_br(t) for t in numeros]
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
            texto = normalizar_tipografia(decodificar_cids(
                " ".join(p["text"] for p in sorted(mapa[topo], key=lambda p: p["x0"]))
            ))
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


def _ranking_do_texto(linhas: list[str], numero_pagina: int) -> list[LinhaRanking]:
    """Ranking a partir de texto, com as duas colunas concatenadas na mesma linha.

    Cada linha traz "<n>o <NOME> <valor>" de automoveis seguido do mesmo de
    comerciais leves. Sem coordenadas, o segmento e' atribuido pela posicao
    esperada: cada coluna sabe qual e' o proximo lugar do seu ranking, e uma
    linha com um unico ordinal vai para a coluna que o esperava.
    """
    achados: list[LinhaRanking] = []
    proxima = {"automoveis": 1, "comerciais_leves": 1}
    for linha in linhas:
        cortes = [achado.start() for achado in RE_ORDINAL_INTERNO.finditer(linha)]
        if not cortes:
            continue
        pedacos = [linha[i:j].strip() for i, j in zip(cortes, cortes[1:] + [len(linha)])]
        for pedaco in pedacos:
            achado = RE_ORDINAL.match(pedaco)
            if not achado:
                continue
            posicao = int(achado.group(1))
            tokens = [t for t in achado.group(2).split(" ") if t and t not in MARCADORES]
            if len(tokens) < 2 or not eh_numero_br(tokens[-1]):
                continue
            nome = " ".join(tokens[:-1]).strip()
            if "/" not in nome:
                continue
            segmento = next(
                (s for s in ("automoveis", "comerciais_leves") if proxima[s] == posicao), None
            )
            if segmento is None:
                continue
            proxima[segmento] = posicao + 1
            achados.append(LinhaRanking(
                segmento=segmento, posicao_fonte=posicao, nome_completo_fonte=nome,
                unidades_mes=numero_br(tokens[-1]), pagina=numero_pagina,
                metodo_extracao="ocr",
            ))
    return achados


def _ocr_das_paginas_sem_texto(caminho: Path, extracao: Extracao) -> dict[int, str]:
    """Roda OCR so' nas paginas em que a extracao de texto nao devolveu nada."""
    from . import ocr as mod_ocr

    disponivel, detalhe = mod_ocr.disponivel()
    if not disponivel:
        extracao.avisos.append(f"OCR pedido mas indisponivel ({detalhe})")
        return {}
    with pdfplumber.open(caminho) as pdf:
        vazias = [
            numero for numero, pagina in enumerate(pdf.pages, start=1)
            if not (pagina.extract_text() or "").strip()
        ]
    if not vazias:
        return {}
    textos = mod_ocr.texto_das_paginas(caminho, vazias)
    limpos = {numero: mod_ocr.limpar(texto) for numero, texto in textos.items() if texto.strip()}
    extracao.paginas_com_ocr.extend(sorted(limpos))
    extracao.avisos.append(f"OCR aplicado em {len(limpos)} paginas ({detalhe})")
    return limpos


def ler(caminho: Path, usar_ocr: bool = False) -> Extracao:
    """Extrai de um informe tudo o que as etapas seguintes precisam."""
    extracao = Extracao(arquivo=caminho.name)
    segmento_corrente: str | None = None
    textos_ocr: dict[int, str] = {}

    if usar_ocr:
        textos_ocr = _ocr_das_paginas_sem_texto(caminho, extracao)

    with pdfplumber.open(caminho) as pdf:
        extracao.paginas = len(pdf.pages)
        for numero, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text() or ""
            if tem_cids(texto):
                if numero not in extracao.paginas_com_cid:
                    extracao.paginas_com_cid.append(numero)
                texto = decodificar_cids(texto)
            if not texto.strip() and numero in textos_ocr:
                texto = textos_ocr[numero]
            if not texto.strip():
                extracao.paginas_sem_texto.append(numero)
                continue
            linhas = [_desdobrar(normalizar_tipografia(l)) for l in texto.split("\n")]

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
                for chave, colunas in _totais_do_resumo(linhas).items():
                    extracao.total_publicado.setdefault(chave, colunas[0])
                    if len(colunas) > 1:
                        extracao.total_publicado_anterior.setdefault(chave, colunas[1])
                continue

            if RE_TITULO_RANKING.match(_sem_acento(titulo)):
                if numero in extracao.paginas_com_ocr:
                    # Pagina de ranking vinda de OCR: as duas colunas ja' chegam
                    # coladas na mesma linha, sem coordenadas para separar.
                    extracao.ranking.extend(_ranking_do_texto(linhas, numero))
                else:
                    extracao.ranking.extend(_ranking_da_pagina(pagina, numero))
                continue

            if not RE_TITULO_SUBSEGMENTO.match(_sem_acento(titulo)):
                continue
            if segmento_corrente not in ("automoveis", "comerciais_leves"):
                continue

            sub_segmento = ""
            segmento_do_bloco = segmento_corrente
            de_ocr = numero in extracao.paginas_com_ocr
            metodo = ("ocr" if de_ocr
                      else "texto_glifos" if numero in extracao.paginas_com_cid
                      else "texto")
            for linha in linhas:
                lido = _linha_modelo(linha, tolerar_glifo_solto=de_ocr)
                if lido is not None:
                    posicao, nome, anterior, mes, acumulado, percentual = lido
                    if not sub_segmento:
                        extracao.avisos.append(
                            f"p{numero}: linha de modelo sem sub-segmento identificado: {linha!r}"
                        )
                    if segmento_do_bloco is None:
                        extracao.sem_segmento.append(f"p{numero} '{sub_segmento}': {nome}")
                        continue
                    if (sub_segmentos.segmento_de(sub_segmento) is None
                            and sub_segmento not in extracao.sub_segmentos_novos):
                        # Nome fora de config/sub_segmentos.csv que de fato carrega
                        # modelos: caso para curadoria humana, nao para adivinhacao.
                        extracao.sub_segmentos_novos.append(sub_segmento)
                    extracao.modelos.append(LinhaModelo(
                        segmento=segmento_do_bloco,
                        sub_segmento_fonte=sub_segmento,
                        posicao_fonte=posicao,
                        nome_completo_fonte=nome,
                        unidades_mes=mes,
                        unidades_mes_anterior=anterior,
                        unidades_acumulado=acumulado,
                        participacao_pct=percentual,
                        pagina=numero,
                        metodo_extracao=metodo,
                    ))
                    continue
                subtotal = _subtotal(linha)
                if subtotal is not None:
                    if sub_segmento and segmento_do_bloco:
                        extracao.subtotal_publicado[(segmento_do_bloco, sub_segmento)] = subtotal
                    continue
                marcador = _sem_acento(linha).upper().strip()
                if marcador in SEGMENTO_POR_MARCADOR or _eh_ruido(linha):
                    continue
                sub_segmento = linha
                # O nome do sub-segmento manda; o marcador de secao e' alternativa.
                # Em Abr-Jun/2020 o marcador vem corrompido pela fonte sem
                # ToUnicode e mandaria os automoveis inteiros para comerciais leves.
                pelo_nome = sub_segmentos.segmento_de(sub_segmento)
                if pelo_nome is None:
                    segmento_do_bloco = segmento_corrente
                else:
                    if segmento_corrente is not None and pelo_nome != segmento_corrente:
                        extracao.divergencias_de_secao.append(
                            f"p{numero}: '{sub_segmento}' e' de {pelo_nome}, mas o marcador "
                            f"da secao dizia {segmento_corrente}"
                        )
                    segmento_do_bloco = pelo_nome

    return extracao
