"""Leitura das tabelas de canal de venda: venda direta e varejo.

Os informes trazem, desde 2003-01, as vendas separadas em **venda direta** -- o
que a montadora negocia com frotista e locadora, mais taxi, produtor rural e
PCD -- e **varejo**, o resto. A definicao e' da propria fonte.

Tres granularidades existem na fonte, e so' uma entra no painel de canal:

- **Tabelas por modelo** (top-50 por segmento, por canal): texto, com unidades,
  nos 281 meses em que a estrutura existe. E' o que este modulo le'.
- **Ranking por marca**: grafico de barras com rotulo rotacionado, em
  percentual. **Nao extraido, de proposito** -- ver QUESTOES_ABERTAS.md.
- **Participacao agregada**: pizza, com os percentuais em texto so' a partir de
  2024-04. Lida como **amostra de calibracao**, nao como serie.

A atribuicao dos percentuais da pizza **nao le' o grafico**. A ordem dos
numeros no texto muda de pizza para pizza (em 2026-08, venda direta vem primeiro
em automoveis e segundo em comerciais leves), entao ela e' decidida por duas
restricoes aritmeticas: a identidade de media ponderada entre os segmentos e os
limites que as proprias tabelas por modelo impoem a' participacao verdadeira.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import permutations, product
from pathlib import Path

import pdfplumber

from . import informe

# Os tipos de tabela, pelo titulo que a propria fonte usa.
TIPOS = {
    "participacao_mes": re.compile(
        r"participa[çc][ãa]o de venda direta e (venda )?varejo\s+\w+/\d{4}", re.I),
    "participacao_acumulado": re.compile(
        r"participa[çc][ãa]o de venda direta e varejo acumulado", re.I),
    "marca_varejo_mes": re.compile(
        r"ranking por marca de emplac\w*\.? varejo\s+\w+/\d{4}", re.I),
    "marca_varejo_acumulado": re.compile(
        r"ranking por marca de emplac\w*\.? varejo acumulado", re.I),
    "marca_direta_mes": re.compile(
        r"ranking por marca de emplac\w*\.? venda direta\s+\w+/\d{4}", re.I),
    "marca_direta_acumulado": re.compile(
        r"ranking por marca de emplac\w*\.? venda direta acumulado", re.I),
    "modelo_direta_mes": re.compile(
        r"modelos mais emplacados venda direta\s+\w+/\d{4}", re.I),
    "modelo_varejo_mes": re.compile(
        r"modelos mais emplacados venda varejo\s+\w+/\d{4}", re.I),
    "modelo_direta_acumulado": re.compile(
        r"modelos mais emplac\w*\.? venda direta acumulado", re.I),
    "modelo_varejo_acumulado": re.compile(
        r"modelos mais emplac\w*\.? venda varejo acumulado", re.I),
}

# O painel de canal usa so' as tabelas do mes. As acumuladas existem na fonte,
# mas a chave do painel nao tem dimensao de periodo, e mistura-las criaria
# duas linhas para o mesmo (mes, segmento, canal, modelo).
TABELAS_DO_PAINEL = {"modelo_direta_mes": "direta", "modelo_varejo_mes": "varejo"}

# Uma entrada por linha dentro de uma coluna ja' recortada. O nome pode ter
# digito (`GM/S10`, `RAM/3500`), entao as unidades sao o ultimo numero da linha.
RE_ENTRADA = re.compile(r"^(\d{1,3})\s*[ºo°]\s+(\S.*?)\s+(\d{1,3}(?:\.\d{3})*|\d+)$")
RE_PERCENTUAL = re.compile(r"^(\d{1,3}(?:[.,]\d+)?)%$")


@dataclass
class Entrada:
    segmento: str
    canal: str
    posicao: int
    nome: str
    unidades: int
    pagina: int
    origem_tabela: str
    metodo: str


@dataclass
class Leitura:
    paginas: dict[str, int] = field(default_factory=dict)
    entradas: list[Entrada] = field(default_factory=list)
    pizzas: list[tuple[float, float]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _texto(pagina) -> tuple[str, str]:
    """Texto da pagina, com glifos traduzidos quando a fonte nao tem ToUnicode."""
    texto = pagina.extract_text() or ""
    if informe.tem_cids(texto):
        return informe.decodificar_cids(texto), "texto_glifos"
    return texto, "texto"


def _tipo_da_pagina(pagina) -> tuple[str | None, str, str]:
    texto, metodo = _texto(pagina)
    cabecalho = "\n".join(texto.splitlines()[:6])
    for tipo, padrao in TIPOS.items():
        if padrao.search(cabecalho):
            return tipo, texto, metodo
    return None, texto, metodo


RE_MARCADOR = re.compile(r"^\d{1,3}[ºo°]$")


def _divisa_das_colunas(pagina) -> float:
    """O x que separa automoveis de comerciais leves.

    Usa os proprios marcadores de posicao (`12º`), nao o cabecalho: em 2026-08 o
    cabecalho `COMERCIAIS` comeca em x=336 e os marcadores da mesma coluna em
    x=330, entao cortar pelo cabecalho deixava o primeiro digito da posicao da
    direita grudado no fim de cada linha da esquerda -- `VW/POLO 6.933 1`, lido
    como 1 unidade. A divisa e' o menor x dos marcadores da metade direita.
    """
    meio = float(pagina.width) / 2
    direita = [float(palavra["x0"]) for palavra in pagina.extract_words()
               if RE_MARCADOR.match(palavra["text"]) and float(palavra["x0"]) > meio]
    if direita:
        return min(direita) - 3
    for palavra in pagina.extract_words():
        if palavra["text"].upper().startswith("COMERCIAIS"):
            return float(palavra["x0"]) - 12
    return meio


def _entradas_da_coluna(pagina, x0: float, x1: float) -> tuple[list[tuple], str]:
    recorte = pagina.crop((x0, 0, x1, pagina.height))
    texto, metodo = _texto(recorte)
    achados = []
    for linha in texto.splitlines():
        casado = RE_ENTRADA.match(linha.strip())
        if casado:
            posicao, nome, valor = casado.groups()
            achados.append((int(posicao), " ".join(nome.split()),
                            int(valor.replace(".", ""))))
    return achados, metodo


def ler_tabela_de_modelo(pagina, numero: int, tipo: str) -> list[Entrada]:
    canal = TABELAS_DO_PAINEL[tipo]
    divisa = _divisa_das_colunas(pagina)
    saida = []
    for segmento, (x0, x1) in (("automoveis", (0, divisa)),
                               ("comerciais_leves", (divisa, float(pagina.width)))):
        achados, metodo = _entradas_da_coluna(pagina, x0, x1)
        saida.extend(
            Entrada(segmento, canal, posicao, nome, unidades, numero, tipo, metodo)
            for posicao, nome, unidades in achados
        )
    return saida


def ler_pizzas(pagina) -> list[tuple[float, float]]:
    """Os tres pares de percentuais da pagina de participacao, de cima para baixo.

    Agrupa pelos dois maiores saltos verticais: as tres pizzas sao empilhadas, e
    a distancia entre elas e' bem maior que entre os dois rotulos de uma mesma.
    Devolve [] quando os numeros nao sao texto -- o caso de 2003-01 a 2024-03.
    """
    valores = []
    for palavra in pagina.extract_words():
        casado = RE_PERCENTUAL.match(palavra["text"])
        if casado:
            valores.append((float(palavra["top"]), float(casado.group(1).replace(",", "."))))
    if len(valores) != 6:
        return []
    valores.sort()
    saltos = sorted(range(1, 6), key=lambda i: valores[i][0] - valores[i - 1][0])[-2:]
    cortes = sorted(saltos)
    grupos = [valores[:cortes[0]], valores[cortes[0]:cortes[1]], valores[cortes[1]:]]
    if any(len(grupo) != 2 for grupo in grupos):
        return []
    return [(grupo[0][1], grupo[1][1]) for grupo in grupos]


def ler(caminho: Path, dicas: dict[str, int] | None = None) -> Leitura:
    """Le' as tabelas de canal de um informe.

    `dicas` sao numeros de pagina ja' conhecidos (do diagnostico da fase 1).
    Cada dica e' **conferida pelo titulo**; se nao bater, a leitura varre o
    informe inteiro. A dica so' economiza tempo, nunca decide nada.
    """
    leitura = Leitura()
    procurados = set(TABELAS_DO_PAINEL) | {"participacao_mes"}
    with pdfplumber.open(caminho) as pdf:
        def examinar(numero: int) -> None:
            pagina = pdf.pages[numero - 1]
            tipo, _, _ = _tipo_da_pagina(pagina)
            if tipo not in procurados or tipo in leitura.paginas:
                return
            leitura.paginas[tipo] = numero
            if tipo in TABELAS_DO_PAINEL:
                leitura.entradas.extend(ler_tabela_de_modelo(pagina, numero, tipo))
            else:
                leitura.pizzas = ler_pizzas(pagina)

        for tipo, numero in (dicas or {}).items():
            if tipo in procurados and numero and 1 <= int(numero) <= len(pdf.pages):
                examinar(int(numero))
        if not procurados <= set(leitura.paginas):
            if dicas:
                leitura.avisos.append("dica de pagina nao conferiu; varredura completa")
            for numero in range(1, len(pdf.pages) + 1):
                if procurados <= set(leitura.paginas):
                    break
                if numero not in leitura.paginas.values():
                    examinar(numero)
    return leitura


# ------------------------------------------------------------ participacao
@dataclass
class Atribuicao:
    automoveis: float
    comerciais_leves: float
    combinado: float
    ordem_das_pizzas: str       # qual pizza e' qual segmento, de cima para baixo
    direta_em_primeiro: str     # em cada pizza, se venda direta era o 1o numero


# A ordem das pizzas na pagina, de cima para baixo. E' propriedade do LAYOUT,
# conferida de dois jeitos: os titulos em texto das pizzas do meio e de baixo
# ("Comercial Leve", "Automoveis + Comercial Leve"), e a busca livre sobre as 6
# ordens, que sempre que da' solucao unica da' esta. Fixa-la resolve a unica
# ambiguidade que a aritmetica nao resolve: automoveis pesa ~82% do conjunto,
# entao a pizza de automoveis e a do conjunto ficam proximas, e troca-las as
# vezes ainda fecha a identidade dentro da tolerancia (2026-06).
ORDEM_DO_LAYOUT = (0, 1, 2)


def atribuir_participacao(pizzas, total_automoveis, total_leves,
                          limites_automoveis, limites_leves,
                          tolerancia_identidade=0.6, tolerancia_limite=0.5,
                          ordens=None) -> list[Atribuicao]:
    """Qual numero de qual pizza e' a venda direta de qual segmento.

    Nao le' o grafico. Testa as 48 combinacoes (3! ordens de pizza x 2^3
    escolhas de numero) contra duas restricoes que so' dependem de aritmetica:

    1. **identidade ponderada**: a venda direta do conjunto tem de ser a media
       das de automoveis e comerciais leves, pesada pelos totais publicados;
    2. **limites das tabelas**: a participacao verdadeira da venda direta nao
       pode ser menor que `direta_top50 / total`, nem maior que
       `1 - varejo_top50 / total`. Em comerciais leves, com cobertura de ~100%,
       esse intervalo tem largura de decimos de ponto e decide sozinho.

    Os limites so' escolhem o lado (x ou 100-x). O **valor** publicado continua
    sendo o da fonte, e e' ele que a calibracao compara -- nao ha' circularidade.

    Devolve todas as solucoes. Uma so' e' o esperado; zero ou mais de uma e'
    reportado, nunca resolvido no chute.
    """
    if len(pizzas) != 3 or not (total_automoveis and total_leves):
        return []
    peso = total_automoveis + total_leves
    rotulos = ("automoveis", "comerciais_leves", "combinado")
    solucoes = []
    for ordem in (ordens if ordens is not None else permutations(range(3))):
        for escolha in product((0, 1), repeat=3):
            a = pizzas[ordem[0]][escolha[0]]
            l = pizzas[ordem[1]][escolha[1]]
            c = pizzas[ordem[2]][escolha[2]]
            if abs((total_automoveis * a + total_leves * l) / peso - c) > tolerancia_identidade:
                continue
            if not (limites_automoveis[0] - tolerancia_limite <= a
                    <= limites_automoveis[1] + tolerancia_limite):
                continue
            if not (limites_leves[0] - tolerancia_limite <= l
                    <= limites_leves[1] + tolerancia_limite):
                continue
            por_pizza = {ordem[i]: rotulos[i] for i in range(3)}
            primeiro = {ordem[i]: escolha[i] == 0 for i in range(3)}
            solucoes.append(Atribuicao(
                automoveis=a, comerciais_leves=l, combinado=c,
                ordem_das_pizzas=" / ".join(por_pizza[i] for i in range(3)),
                direta_em_primeiro=" / ".join(
                    "sim" if primeiro[i] else "nao" for i in range(3)),
            ))
    return solucoes
