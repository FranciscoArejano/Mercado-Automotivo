#!/usr/bin/env python3
"""Etapa 4 -- relatorio de candidatos (ESPEC.md sec.5).

Esta etapa existe para **produzir evidencia de decisao**, nao para decidir.
Nada aqui funde, renomeia ou agrupa nada: a saida e' `saidas/candidatos.xlsx`,
com uma coluna `decisao` vazia para o humano preencher e transportar para
regras.csv.

Dois detectores, ambos restritos a modelos da mesma marca:

1. *Passagem de bastao* -- B entra em [saida(A) - 6, saida(A) + 6], com pico
   entre 0,4x e 3,0x o pico de A, excluindo B cuja serie ja' existia antes de
   saida(A) - 12. Reporta a correlacao das duas series mensais na janela de
   +-12 meses em torno de saida(A).
2. *Queda abrupta* -- A perde mais de 80% num unico mes, sem declinio previo,
   e ha' uma entrada da mesma marca no mesmo mes ou no adjacente. E' o detector
   de rebatismo puro.

Armadilha tratada, censura a' esquerda (sec.5): entrada que coincide com o
primeiro mes da amostra e saida que coincide com o ultimo sao excluidas do
teste. Sem isso, um modelo que sai perto do inicio casa com dezenas de falsos
candidatos -- na base anterior, 14 so' para o Chevrolet Agile.

Proibido e nao implementado: fundir ou sugerir fusao por similaridade de nome
(sec.5). Na base anterior o casamento aproximado produziu 204 pares, quase
todos falsos, e nao encontrou Prisma -> Onix Plus.

Uso:
    python src/etapa04_candidatos.py [--limiar 0.05]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import ciclo_vida, config, log, meses as mod_meses, periodo  # noqa: E402

ETAPA = "etapa04_candidatos"


def _fichas(largo: pd.DataFrame, meses: list[str], limiar: float) -> pd.DataFrame:
    primeiro, ultimo = meses[0], meses[-1]
    registros = []
    for chave, serie in largo.iterrows():
        ciclo = ciclo_vida.calcular(
            serie, limiar, primeiro, ultimo,
            janela=config.JANELA_PICO_MESES, modo=config.PICO_MOVEL_MODO,
        )
        if ciclo.entrada is None:
            continue
        marca, modelo, segmento = chave
        registros.append({
            "marca": marca, "modelo": modelo, "segmento": segmento,
            "entrada": ciclo.entrada, "saida": ciclo.saida,
            "pico": ciclo.pico, "pico_mes": ciclo.pico_mes,
            "unidades_totais": ciclo.unidades_totais,
            "meses_ativos": ciclo.meses_ativos,
            "censura_esquerda": ciclo.censura_esquerda,
            "censura_direita": ciclo.censura_direita,
            "ultimo_mes_com_unidades": str(serie[serie.fillna(0) > 0].index[-1]),
        })
    return pd.DataFrame(registros)


def _correlacao(serie_a: pd.Series, serie_b: pd.Series, centro: str, meses: list[str]) -> float:
    indice = periodo.para_indice(centro)
    janela = [
        m for m in meses
        if abs(periodo.para_indice(m) - indice) <= config.JANELA_CORRELACAO_MESES
    ]
    a = serie_a.reindex(janela).astype("float64")
    b = serie_b.reindex(janela).astype("float64")
    valido = a.notna() & b.notna()
    if valido.sum() < 3 or a[valido].std() == 0 or b[valido].std() == 0:
        return float("nan")
    return float(np.corrcoef(a[valido], b[valido])[0, 1])


def _passagem_de_bastao(fichas: pd.DataFrame, largo: pd.DataFrame, meses: list[str]) -> list[dict]:
    pares = []
    por_marca = {marca: bloco for marca, bloco in fichas.groupby("marca")}
    for _, saindo in fichas.iterrows():
        if saindo["censura_direita"] or saindo["censura_esquerda"]:
            continue
        saida = periodo.para_indice(saindo["saida"])
        candidatos = por_marca.get(saindo["marca"])
        if candidatos is None:
            continue
        for _, entrando in candidatos.iterrows():
            if (entrando["modelo"], entrando["segmento"]) == (saindo["modelo"], saindo["segmento"]):
                continue
            if entrando["censura_esquerda"]:
                continue  # entrada no primeiro mes da amostra e' artefato
            entrada = periodo.para_indice(entrando["entrada"])
            if abs(entrada - saida) > config.JANELA_BASTAO_MESES:
                continue
            if entrada < saida - config.PRE_EXISTENCIA_MESES:
                continue  # ja' existia antes: nao e' sucessor novo
            if not saindo["pico"]:
                continue
            razao = entrando["pico"] / saindo["pico"]
            if not config.RAZAO_PICO_MIN <= razao <= config.RAZAO_PICO_MAX:
                continue
            correlacao = _correlacao(
                largo.loc[(saindo["marca"], saindo["modelo"], saindo["segmento"])],
                largo.loc[(entrando["marca"], entrando["modelo"], entrando["segmento"])],
                saindo["saida"], meses,
            )
            pares.append({
                "detector": "passagem_de_bastao",
                "marca": saindo["marca"],
                "modelo_origem": saindo["modelo"],
                "segmento_origem": saindo["segmento"],
                "modelo_destino": entrando["modelo"],
                "segmento_destino": entrando["segmento"],
                "saida_origem": saindo["saida"],
                "entrada_destino": entrando["entrada"],
                "defasagem_meses": entrada - saida,
                "pico_origem": saindo["pico"],
                "pico_destino": entrando["pico"],
                "razao_picos": razao,
                "correlacao_12m": correlacao,
                "unidades_origem": saindo["unidades_totais"],
                "unidades_destino": entrando["unidades_totais"],
                "volume_em_jogo": saindo["unidades_totais"] + entrando["unidades_totais"],
                "decisao": "",
                "observacao_humana": "",
            })
    return pares


def _queda_abrupta(fichas: pd.DataFrame, largo: pd.DataFrame, meses: list[str]) -> list[dict]:
    """Perda > 80% num unico mes, sem declinio previo, com entrada adjacente."""
    pares = []
    entradas_por_marca: dict[str, list] = {}
    for _, ficha in fichas.iterrows():
        if ficha["censura_esquerda"]:
            continue
        entradas_por_marca.setdefault(ficha["marca"], []).append(ficha)

    for _, saindo in fichas.iterrows():
        if saindo["censura_esquerda"]:
            continue
        serie = largo.loc[(saindo["marca"], saindo["modelo"], saindo["segmento"])]
        valores = serie.astype("float64")
        for posicao in range(2, len(meses)):
            anterior, atual = valores.iloc[posicao - 1], valores.iloc[posicao]
            se_antes = valores.iloc[posicao - 2]
            if not np.isfinite(anterior) or not np.isfinite(atual) or anterior <= 0:
                continue
            if (anterior - atual) / anterior <= config.QUEDA_ABRUPTA:
                continue
            # "sem declinio previo": o mes anterior nao vinha ja' caindo
            if np.isfinite(se_antes) and se_antes > 0 and anterior < se_antes * 0.9:
                continue
            mes_queda = meses[posicao]
            for entrando in entradas_por_marca.get(saindo["marca"], []):
                if (entrando["modelo"], entrando["segmento"]) == (saindo["modelo"], saindo["segmento"]):
                    continue
                if abs(periodo.distancia(mes_queda, entrando["entrada"])) > 1:
                    continue
                correlacao = _correlacao(
                    serie,
                    largo.loc[(entrando["marca"], entrando["modelo"], entrando["segmento"])],
                    mes_queda, meses,
                )
                pares.append({
                    "detector": "queda_abrupta",
                    "marca": saindo["marca"],
                    "modelo_origem": saindo["modelo"],
                    "segmento_origem": saindo["segmento"],
                    "modelo_destino": entrando["modelo"],
                    "segmento_destino": entrando["segmento"],
                    "saida_origem": mes_queda,
                    "entrada_destino": entrando["entrada"],
                    "defasagem_meses": periodo.distancia(mes_queda, entrando["entrada"]),
                    "pico_origem": saindo["pico"],
                    "pico_destino": entrando["pico"],
                    "razao_picos": (entrando["pico"] / saindo["pico"]) if saindo["pico"] else np.nan,
                    "correlacao_12m": correlacao,
                    "unidades_origem": saindo["unidades_totais"],
                    "unidades_destino": entrando["unidades_totais"],
                    "volume_em_jogo": saindo["unidades_totais"] + entrando["unidades_totais"],
                    "decisao": "",
                    "observacao_humana": "",
                })
    return pares


LEIA_ME = [
    ("O que e' este arquivo",
     "Evidencia para adjudicacao humana (ESPEC.md sec.5). Nada aqui foi fundido."),
    ("Como usar",
     "Preencha a coluna 'decisao' da aba 'pares' com um de: rebatismo, "
     "reclassificacao, substituicao, ignorar. Depois transcreva as linhas "
     "decididas para regras.csv na raiz do repositorio."),
    ("regras.csv",
     "Colunas: tipo, marca, modelo_origem, modelo_destino, data_evento, observacao. "
     "data_evento e' obrigatoria para rebatismo (AAAA-MM) -- e' o campo que D2 manda registrar."),
    ("Ordenacao", "A aba 'pares' vem ordenada por volume_em_jogo (origem + destino)."),
    ("Censura a' esquerda",
     "Entradas no primeiro mes da amostra e saidas no ultimo foram excluidas dos "
     "detectores; elas sao artefato do recorte, nao evento de mercado."),
    ("Similaridade de nome",
     "Nao usada, por decisao da ESPEC sec.5: produz falsos pares e nao encontra "
     "Prisma -> Onix Plus."),
    ("Limitacao declarada",
     "Troca de geracao e' invisivel na fonte. 'Sobrevivencia do modelo' significa "
     "sobrevivencia do nome comercial, nao do produto fisico."),
]


def executar(limiar: float) -> int:
    logger = log.preparar(ETAPA)
    if not config.PAINEL_BRUTO.exists():
        raise log.ErroDeParsing(
            f"{log.caminho_relativo(config.PAINEL_BRUTO)} nao existe -- rode a etapa 03 antes."
        )
    bruto = pd.read_parquet(config.PAINEL_BRUTO)
    bruto = bruto.rename(columns={
        "marca_fonte": "marca", "modelo_fonte": "modelo", "segmento_fonte": "segmento",
    })
    meses = sorted(bruto["mes_ref"].unique())
    largo = ciclo_vida.grade(bruto, ["marca", "modelo", "segmento"], meses, mod_meses.uteis())
    logger.info("%d modelos x %d meses", len(largo), len(meses))

    fichas = _fichas(largo, meses, limiar)
    logger.info("fichas montadas: %d modelos com serie nao vazia", len(fichas))

    pares = _passagem_de_bastao(fichas, largo, meses) + _queda_abrupta(fichas, largo, meses)
    quadro_pares = pd.DataFrame(pares)
    if not quadro_pares.empty:
        quadro_pares = (
            quadro_pares.sort_values(["volume_em_jogo", "detector"], ascending=[False, True])
            .drop_duplicates(
                subset=["marca", "modelo_origem", "segmento_origem",
                        "modelo_destino", "segmento_destino", "detector"]
            )
            .reset_index(drop=True)
        )

    envolvidos = set()
    if not quadro_pares.empty:
        for _, par in quadro_pares.iterrows():
            envolvidos.add((par["marca"], par["modelo_origem"], par["segmento_origem"]))
            envolvidos.add((par["marca"], par["modelo_destino"], par["segmento_destino"]))
    series = largo.loc[largo.index.isin(envolvidos)].reset_index() if envolvidos else pd.DataFrame()

    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(config.CANDIDATOS, engine="xlsxwriter") as escritor:
        pd.DataFrame(LEIA_ME, columns=["topico", "texto"]).to_excel(
            escritor, sheet_name="leia_me", index=False)
        (quadro_pares if not quadro_pares.empty
         else pd.DataFrame(columns=["detector", "marca", "modelo_origem", "decisao"])
         ).to_excel(escritor, sheet_name="pares", index=False)
        fichas.sort_values("unidades_totais", ascending=False).to_excel(
            escritor, sheet_name="fichas", index=False)
        (series if not series.empty else pd.DataFrame(columns=["marca", "modelo", "segmento"])
         ).to_excel(escritor, sheet_name="series", index=False)

    saindo = fichas[~fichas["censura_direita"]] if not fichas.empty else fichas
    log.contagem(
        logger, modelos=len(fichas), modelos_que_saem=len(saindo),
        pares=len(quadro_pares),
        pares_passagem_de_bastao=int((quadro_pares["detector"] == "passagem_de_bastao").sum())
        if not quadro_pares.empty else 0,
        pares_queda_abrupta=int((quadro_pares["detector"] == "queda_abrupta").sum())
        if not quadro_pares.empty else 0,
    )
    logger.info("gravado %s", log.caminho_relativo(config.CANDIDATOS))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--limiar", type=float, default=config.LIMIAR_SAIDA)
    args = analisador.parse_args()
    return executar(args.limiar)


if __name__ == "__main__":
    raise SystemExit(main())
