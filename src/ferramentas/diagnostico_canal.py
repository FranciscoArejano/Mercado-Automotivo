#!/usr/bin/env python3
"""Fase 1 da dimensao de canal: medir antes de construir.

Os informes separam **venda direta** de **varejo** em cinco tabelas. Antes de
extrair qualquer coisa, esta ferramenta mede, nos 284 informes:

1. em quais meses cada tabela existe, e desde quando;
2. a profundidade das tabelas por modelo -- quantas linhas, e se o numero e' fixo;
3. se o corte e' por segmento ou agregado;
4. se `direta + varejo` reconcilia com o total do mes publicado pela fonte.

**So' diagnostica**: nao escreve nada em `dados/processado/`.

Uso:
    python src/ferramentas/diagnostico_canal.py [--inicio AAAA-MM] [--fim AAAA-MM]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import config, log, periodo  # noqa: E402

ETAPA = "diagnostico_canal"

# Os cinco tipos de tabela, pelo titulo que a propria fonte usa.
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

# "12º VW/POLO 6.933" -- posicao, nome, unidades. Duas colunas por pagina.
# O nome PODE conter digito (`GM/S10`, `RAM/3500`, `BYD/DOLPHIN MINI`), entao as
# unidades sao o ultimo numero antes da proxima posicao ou do fim da linha --
# nao "o primeiro numero depois de um nome sem digitos", que perdia 1 em 10.
RE_LINHA_MODELO = re.compile(
    r"(\d{1,3})[ºo°]\s+(\S.*?)\s+([\d.]+)(?=\s+\d{1,3}[ºo°]\s|\s*$)")
RE_PCT = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*%")


def _numero(texto: str) -> int | None:
    limpo = texto.replace(".", "").strip()
    return int(limpo) if limpo.isdigit() else None


def _linhas_de_modelo(texto: str) -> list[dict]:
    """Uma linha por modelo listado, com a coluna (1a = automoveis, 2a = leves)."""
    achados = []
    for linha in texto.splitlines():
        pares = RE_LINHA_MODELO.findall(linha)
        for coluna, (posicao, nome, valor) in enumerate(pares):
            unidades = _numero(valor)
            if unidades is None:
                continue
            achados.append({
                "posicao": int(posicao),
                "nome": " ".join(nome.split()),
                "unidades": unidades,
                "coluna": coluna,
            })
    return achados


def _participacao(texto: str) -> list[float]:
    return [float(p.replace(",", ".")) for p in RE_PCT.findall(texto)]


def diagnosticar(mes: str, caminho: Path) -> dict:
    achado: dict = {"mes": mes, "arquivo": caminho.name}
    if not caminho.exists():
        achado["situacao"] = "pdf ausente"
        return achado
    paginas_por_tipo: dict[str, int] = {}
    modelos: dict[str, list[dict]] = defaultdict(list)
    percentuais: list[float] = []
    try:
        with pdfplumber.open(caminho) as pdf:
            achado["paginas"] = len(pdf.pages)
            for numero, pagina in enumerate(pdf.pages, 1):
                texto = pagina.extract_text() or ""
                if not texto:
                    continue
                cabecalho = "\n".join(texto.splitlines()[:6])
                for tipo, padrao in TIPOS.items():
                    if tipo in paginas_por_tipo or not padrao.search(cabecalho):
                        continue
                    paginas_por_tipo[tipo] = numero
                    if tipo.startswith("modelo_") and tipo.endswith("_mes"):
                        modelos[tipo] = _linhas_de_modelo(texto)
                    if tipo == "participacao_mes":
                        percentuais = _participacao(texto)
    except Exception as erro:
        achado["situacao"] = f"erro de leitura: {erro}"
        return achado

    achado["situacao"] = "ok" if paginas_por_tipo else "sem tabela de canal"
    for tipo in TIPOS:
        achado[f"pg_{tipo}"] = paginas_por_tipo.get(tipo, "")
    achado["tipos_presentes"] = len(paginas_por_tipo)

    for tipo in ("modelo_direta_mes", "modelo_varejo_mes"):
        linhas = modelos.get(tipo, [])
        curto = tipo.replace("modelo_", "").replace("_mes", "")
        autos = [l for l in linhas if l["coluna"] == 0]
        leves = [l for l in linhas if l["coluna"] == 1]
        achado[f"{curto}_linhas_automoveis"] = len(autos)
        achado[f"{curto}_linhas_leves"] = len(leves)
        achado[f"{curto}_unidades_automoveis"] = sum(l["unidades"] for l in autos)
        achado[f"{curto}_unidades_leves"] = sum(l["unidades"] for l in leves)
        achado[f"{curto}_ultima_posicao"] = max((l["posicao"] for l in linhas), default=0)

    achado["participacao_pct"] = "; ".join(f"{p:g}" for p in percentuais)
    achado["participacao_pares_fecham_100"] = sum(
        1 for i in range(0, len(percentuais) - 1, 2)
        if abs(percentuais[i] + percentuais[i + 1] - 100) <= 0.6
    )
    return achado


def executar(inicio: str, fim: str) -> int:
    logger = log.preparar(ETAPA)
    if not config.MANIFESTO.exists():
        raise SystemExit("manifesto ausente -- rode a etapa 01.")
    with config.MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
        manifesto = {linha["mes"]: linha for linha in csv.DictReader(fluxo)}

    linhas = []
    for mes in periodo.intervalo(inicio, fim):
        registro = manifesto.get(mes)
        if registro is None:
            linhas.append({"mes": mes, "situacao": "sem informe baixado"})
            continue
        achado = diagnosticar(mes, config.RAIZ / registro["arquivo_local"])
        linhas.append(achado)
        logger.info("%s: %s, %d tipos de tabela", mes, achado.get("situacao"),
                    achado.get("tipos_presentes", 0))

    detalhe = pd.DataFrame(linhas)
    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    detalhe.to_csv(config.DIR_SAIDAS / "diagnostico_canal.csv", index=False)
    log.contagem(logger, meses=len(detalhe),
                 com_canal=int((detalhe.get("tipos_presentes", 0) > 0).sum()))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--inicio", default=config.PERIODO_INICIO)
    analisador.add_argument("--fim", default=config.PERIODO_FIM)
    return executar(analisador.parse_args().inicio, analisador.parse_args().fim)


if __name__ == "__main__":
    raise SystemExit(main())
