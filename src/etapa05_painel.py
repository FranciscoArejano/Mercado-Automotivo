#!/usr/bin/env python3
"""Etapa 5 -- painel harmonizado (ESPEC.md sec.6).

Aplica regras.csv sobre painel_bruto.parquet e escreve painel.parquet.

Unidade de observacao (D1): a variante comercial, identificada por
(marca, modelo, segmento). Onix e Onix Plus sao dois produtos. O segmento entra
na chave porque a fonte publica o mesmo nome comercial nos dois segmentos --
RENAULT/KWID aparece em automoveis e em comerciais leves no mesmo mes -- e
juntar os dois somaria produtos diferentes. Migracao de segmento e' tratada
como caso para regras.csv, nao resolvida aqui (ver QUESTOES_ABERTAS.md, Q4).

Invariante central: a soma de unidades por mes tem de ser identica a' do painel
bruto. Harmonizacao redistribui rotulos; nao cria nem destroi unidades.
Qualquer diferenca e' bug e falha a execucao.

Uso:
    python src/etapa05_painel.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, dicionario, grupos, log, regras as mod_regras  # noqa: E402

ETAPA = "etapa05_painel"

COLUNAS = [
    "mes_ref", "ano", "mes", "data", "segmento", "marca", "modelo",
    "grupo_economico", "unidades", "modelo_fonte", "nome_completo_fonte",
    "houve_rebatismo", "data_rebatismo", "cadeia_rebatismo",
    "reclassificacao", "conta_entrada_saida", "origem_tabela", "arquivos_origem",
]


def aplicar(bruto: pd.DataFrame, regras: list[mod_regras.Regra], logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    # 1. Uma linha por (mes, segmento, marca, modelo). A fonte pode listar o
    #    mesmo nome em dois sub-segmentos (NISSAN/VERSA em 2026); sao veiculos
    #    distintos e somam.
    chaves = ["mes_ref", "ano", "mes", "data", "segmento_fonte", "marca_fonte", "modelo_fonte"]
    agregado = (
        bruto.groupby(chaves, as_index=False)
        .agg(
            unidades=("unidades", "sum"),
            nome_completo_fonte=("nome_completo_fonte", "first"),
            origem_tabela=("origem_tabela", lambda s: "+".join(sorted(set(s)))),
            arquivos_origem=("arquivo_origem", lambda s: "+".join(sorted(set(s)))),
        )
        .rename(columns={"segmento_fonte": "segmento", "marca_fonte": "marca"})
    )

    # 2. Rebatismo (D2): funde origem e destino numa serie continua.
    destinos, datas, cadeias = [], [], []
    for marca, modelo in zip(agregado["marca"], agregado["modelo_fonte"]):
        (marca_final, modelo_final), eventos = mod_regras.resolver_destino((marca, modelo), regras)
        destinos.append(modelo_final)
        datas.append(eventos[0] if eventos else "")
        cadeias.append(" -> ".join(eventos))
    agregado["modelo"] = destinos
    agregado["data_rebatismo"] = datas
    agregado["cadeia_rebatismo"] = cadeias
    agregado["houve_rebatismo"] = [bool(c) for c in cadeias]

    # 3. Reclassificacao (D1): marca o desdobramento e suprime a contagem de
    #    entrada/saida naquele ponto. Nao funde nada.
    reclassificacoes = [r for r in regras if r.tipo == "reclassificacao"]
    marcados = set()
    suprimidos: list[dict] = []
    for regra in reclassificacoes:
        for modelo in (regra.modelo_origem, regra.modelo_destino):
            marcados.add((regra.marca, modelo))
            suprimidos.append({
                "marca": regra.marca, "modelo": modelo, "mes_evento": regra.data_evento,
                "motivo": "reclassificacao", "regra_linha": regra.linha,
                "observacao": regra.observacao,
            })
    agregado["reclassificacao"] = [
        (m, mo) in marcados for m, mo in zip(agregado["marca"], agregado["modelo"])
    ]
    agregado["conta_entrada_saida"] = ~agregado["reclassificacao"]

    # 4. Grupo economico datado (D4). Nunca retroativo, nunca adivinhado.
    agregado["grupo_economico"] = [
        grupos.grupo_de(marca, mes) for marca, mes in zip(agregado["marca"], agregado["mes_ref"])
    ]

    painel = (
        agregado.groupby(
            ["mes_ref", "ano", "mes", "data", "segmento", "marca", "modelo"], as_index=False
        )
        .agg(
            grupo_economico=("grupo_economico", "first"),
            unidades=("unidades", "sum"),
            modelo_fonte=("modelo_fonte", lambda s: "+".join(sorted(set(s)))),
            nome_completo_fonte=("nome_completo_fonte", lambda s: "+".join(sorted(set(s)))),
            houve_rebatismo=("houve_rebatismo", "max"),
            data_rebatismo=("data_rebatismo", lambda s: next((v for v in s if v), "")),
            cadeia_rebatismo=("cadeia_rebatismo", lambda s: next((v for v in s if v), "")),
            reclassificacao=("reclassificacao", "max"),
            conta_entrada_saida=("conta_entrada_saida", "min"),
            origem_tabela=("origem_tabela", lambda s: "+".join(sorted(set(s)))),
            arquivos_origem=("arquivos_origem", lambda s: "+".join(sorted(set(s)))),
        )
    )
    logger.info(
        "regras aplicadas: %d rebatismos, %d reclassificacoes, %d substituicoes, %d ignorar",
        sum(1 for r in regras if r.tipo == "rebatismo"),
        len(reclassificacoes),
        sum(1 for r in regras if r.tipo == "substituicao"),
        sum(1 for r in regras if r.tipo == "ignorar"),
    )
    return painel[COLUNAS], pd.DataFrame(suprimidos)


def conferir_invariante(bruto: pd.DataFrame, painel: pd.DataFrame) -> pd.DataFrame:
    antes = bruto.groupby("mes_ref")["unidades"].sum()
    depois = painel.groupby("mes_ref")["unidades"].sum()
    comparacao = pd.DataFrame({"painel_bruto": antes, "painel": depois}).fillna(0)
    comparacao["diferenca"] = comparacao["painel"] - comparacao["painel_bruto"]
    return comparacao


def executar() -> int:
    logger = log.preparar(ETAPA)
    if not config.PAINEL_BRUTO.exists():
        raise log.ErroDeParsing(
            f"{log.caminho_relativo(config.PAINEL_BRUTO)} nao existe -- rode a etapa 03 antes."
        )
    bruto = pd.read_parquet(config.PAINEL_BRUTO)
    regras = mod_regras.carregar()
    logger.info("painel bruto: %d linhas, %d regras", len(bruto), len(regras))

    painel, suprimidos = aplicar(bruto, regras, logger)

    comparacao = conferir_invariante(bruto, painel)
    quebras = comparacao[comparacao["diferenca"] != 0]
    config.DIR_PROCESSADO.mkdir(parents=True, exist_ok=True)
    comparacao.to_csv(config.DIR_PROCESSADO / "invariante_mensal.csv")
    if not quebras.empty:
        raise log.ErroMetodologico(
            "INVARIANTE CENTRAL QUEBRADO: harmonizacao alterou o total mensal em "
            f"{len(quebras)} meses. Primeiros casos:\n{quebras.head(10).to_string()}"
        )
    logger.info("invariante central: soma mensal identica em %d meses", len(comparacao))

    painel.to_parquet(config.PAINEL, index=False)
    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    dicionario.escrever(painel)
    if not suprimidos.empty:
        suprimidos.to_csv(config.DIR_SAIDAS / "eventos_suprimidos.csv", index=False)

    log.contagem(
        logger, linhas_lidas=len(bruto), linhas_escritas=len(painel),
        modelos=painel[["marca", "modelo", "segmento"]].drop_duplicates().shape[0],
        unidades=int(painel["unidades"].sum()),
        grupos_nao_mapeados=int((painel["grupo_economico"] == grupos.NAO_MAPEADO).sum()),
    )
    logger.info("gravado %s", log.caminho_relativo(config.PAINEL))
    return 0


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    return executar()


if __name__ == "__main__":
    raise SystemExit(main())
