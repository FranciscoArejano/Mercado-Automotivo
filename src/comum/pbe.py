"""Leitura das tabelas do PBE Veicular (Inmetro), 2009 a 2026.

Dezoito tabelas, quatro diagramacoes, corpo de letra de 8 pt a 1,8 pt. Os
rotulos do cabecalho nao servem de guia: sao centralizados em uns anos,
rotacionados em outros, e a ordem das colunas muda (Motor vem antes de Versao
de 2014 a 2020). O leitor se apoia no que toda linha de veiculo tem:

- a **marca**, de uma lista em `config/pbe_marcas.csv` (o que vem antes dela e'
  a categoria);
- o **motor**, a primeira palavra depois da marca com cara de cilindrada
  (`1.0-8V`, `2,0L-16V`, `1.6`) ou escrita `ELETRICO`/`N.A.`. O que fica entre
  a marca e o motor e' modelo e versao, juntos -- a fronteira entre os dois nao
  e' recuperavel de forma confiavel nas dezoito diagramacoes, e o casamento com
  o painel e' por prefixo de modelo, entao nao precisa dela;
- a **sequencia de codigos** depois da transmissao: ar-condicionado (S/N),
  direcao (H/E/M/E-H) e combustivel (G/E/F/D), nessa ordem;
- a **palavra de propulsao** (Combustao, Hibrido, Eletrico, Plug-In), escrita
  numa coluna propria a partir de 2021. Antes disso a tabela nao tem a coluna,
  e o leitor so' registra o que estiver escrito na linha.

Duas tabelas tem texto sobreimpresso (cada letra desenhada varias vezes, para
simular negrito); `dedupe_chars` resolve. As tolerancias de agrupamento sao
proporcionais ao corpo -- com o padrao do pdfplumber (3 pt), na tabela de 2026
(1,8 pt) linhas vizinhas se misturam.

Nada aqui interpreta a propulsao: o leitor transcreve. O mapeamento para a
taxonomia do projeto fica em `config/pbe_propulsao.csv`.
"""

from __future__ import annotations

import collections
import re
import unicodedata

# Valores da coluna de propulsao (a partir de 2021), normalizados.
PROPULSAO = {"COMBUSTAO", "HIBRIDO", "ELETRICO", "PLUG-IN", "PLUGIN", "HIBRIDO PLUG-IN"}
# Marcadores que a fabricante poe no NOME da versao. Nao sao a coluna de
# propulsao: o Kia Stonic MHEV de 2021 tem "MHEV" no nome e "Combustao" na
# coluna. Ficam numa coluna propria, `marcador_nome`.
MARCADORES_NOME = re.compile(
    r"\b(MHEV|HEV|PHEV|BEV|REEV|EV|HYBRID|HIBRIDO|PLUG-?IN|E-HYBRID|ELECTRIC|ELETRICO|E-TRON)\b")
CODIGOS_AR = {"S", "N"}
CODIGOS_DIRECAO = {"H", "E", "M", "E-H", "EH", "H-E"}
COMBUSTIVEIS = {"G", "E", "F", "D"}
MOTOR = re.compile(r"^(\d[.,]\d|(TF|T)\d{3}$)")  # 1.0-8V, 2,0L-16V; TF200, T270 (Fiat)
MOTOR_ELETRICO = {"ELETRICO", "N.A.", "NA"}
TRANSMISSAO = re.compile(
    r"^(M|A|AT|MT|MTA|AMT|ASG|DCT|DSG|CVT|ECVT|E-CVT|IVT|ASM|AM|S-TRONIC|TIPTRONIC)"
    r"(-?\d{1,2}|-)?$")  # "A- 9": a marcha as vezes quebra


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto)
                   if not unicodedata.combining(c))


def normalizar(texto: str) -> str:
    """Caixa alta, sem acento, hifens tipograficos unificados, espacos simples."""
    for traco in ("­", "‐", "‑", "–", "—"):
        texto = texto.replace(traco, "-")
    return re.sub(r"\s+", " ", _sem_acento(texto).upper()).strip()


def _corpo(chars) -> float:
    tamanhos = collections.Counter(round(c["size"], 1) for c in chars if c["text"].strip())
    return tamanhos.most_common(1)[0][0] if tamanhos else 5.0


def linhas_da_pagina(pagina) -> list[str]:
    limpa = pagina.dedupe_chars(tolerance=0.5)
    corpo = _corpo(limpa.chars)
    texto = limpa.extract_text(x_tolerance=0.2 * corpo, y_tolerance=0.3 * corpo) or ""
    return [normalizar(linha) for linha in texto.splitlines() if linha.strip()]


def _achar_marca(palavras: list[str], marcas: list[tuple[str, ...]]) -> tuple[int, int] | None:
    """(inicio, fim) da marca na linha; a primeira ocorrencia, a mais longa."""
    for i in range(len(palavras)):
        for marca in marcas:  # ordenadas da mais longa para a mais curta
            if tuple(palavras[i:i + len(marca)]) == marca:
                return i, i + len(marca)
    return None


def _trinca(palavras: list[str], desde: int) -> tuple[int, tuple[str, str, str]] | None:
    """(posicao, (ar, direcao, combustivel)) da primeira trinca em sequencia.

    Ar S/N, direcao H/E/M/E-H, combustivel G/E/F/D. A palavra de propulsao pode
    cair no meio (diagramacao de 2021: `S E COMBUSTAO F`) e e' pulada. Procurar a
    trinca, e nao a transmissao, evita tomar por transmissao um `AT` que esta' no
    nome da versao (KIA STINGER GT 3.3 AT).
    """
    for i in range(desde, len(palavras) - 2):
        if palavras[i] not in CODIGOS_AR or palavras[i + 1] not in CODIGOS_DIRECAO:
            continue
        seguinte = [p for p in palavras[i + 2:i + 5] if p not in PROPULSAO]
        if seguinte and seguinte[0] in COMBUSTIVEIS:
            return i, (palavras[i], palavras[i + 1], seguinte[0])
    return None


def ler_linha(linha: str, marcas: list[tuple[str, ...]]) -> dict | None:
    """Uma linha de veiculo, ou None se a linha nao tem marca e a trinca."""
    palavras = linha.split(" ")
    achada = _achar_marca(palavras, marcas)
    if not achada:
        return None
    inicio, fim = achada
    resto = palavras[fim:]
    trinca = _trinca(resto, 1)
    if trinca is None:
        return None
    posicao_trinca, (_, _, combustivel) = trinca
    antes = resto[:posicao_trinca]

    # O motor e' a primeira palavra com cara de cilindrada ANTES da trinca (depois
    # dela vem os numeros de emissao, que tambem tem virgula). Pode ser a primeira
    # depois da marca quando o nome do modelo quebrou para outra linha da celula.
    motor = next((i for i, p in enumerate(antes)
                  if MOTOR.match(p) or p in MOTOR_ELETRICO), None)
    if motor is not None:
        modelo_versao, texto_motor, depois = " ".join(antes[:motor]), antes[motor], motor + 1
    else:
        # A celula do motor quebrou para outra linha (comum em 2017-2019 e 2026):
        # o modelo vai ate' a transmissao ou a palavra de propulsao, e o motor
        # fica vazio. LEAPMOTOR C10 REEV PLUG-IN A-1 S E G ... (2026).
        corte = next((i for i, p in enumerate(antes) if i > 0
                      and (TRANSMISSAO.match(p) or p in PROPULSAO)), None)
        if corte is None:
            return None
        modelo_versao, texto_motor, depois = " ".join(antes[:corte]), "", corte

    # A palavra de propulsao vem depois do motor (o motor dos eletricos tambem
    # se escreve ELETRICO, e e' pulado).
    propulsao = ""
    for i in range(depois, len(resto)):
        dupla = " ".join(resto[i:i + 2])
        if dupla in PROPULSAO:
            propulsao = dupla
            break
        if resto[i] in PROPULSAO:
            propulsao = resto[i]
            break

    return {
        "categoria": " ".join(palavras[:inicio]),
        "marca_pbe": " ".join(palavras[inicio:fim]),
        "modelo_versao": modelo_versao,
        "motor": texto_motor,
        "tipo_propulsao": propulsao,
        "marcador_nome": "+".join(dict.fromkeys(MARCADORES_NOME.findall(modelo_versao))),
        "combustivel": combustivel,
        "texto_linha": linha,
    }
