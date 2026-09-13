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


def _variacao_do_mercado(bruto: pd.DataFrame, meses: list[str]) -> dict[tuple[str, str], float]:
    """Variacao do total do segmento de um mes para o outro, em fracao.

    Serve de contexto para o detector de queda abrupta: em Abr/2020 o mercado
    inteiro caiu mais de 70% num mes, e praticamente todo modelo dispara o
    detector. A coluna nao filtra nada -- deixa visivel que a queda foi do
    mercado, nao do produto.
    """
    total = bruto.pivot_table(
        index="mes_ref", columns="segmento", values="unidades", aggfunc="sum", fill_value=0
    ).reindex(meses)
    variacao = total.pct_change()
    return {
        (segmento, mes): float(valor)
        for segmento in variacao.columns
        for mes, valor in variacao[segmento].items()
        if pd.notna(valor)
    }


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


def _passagem_de_bastao(fichas: pd.DataFrame, largo: pd.DataFrame, meses: list[str],
                        mercado: dict[tuple[str, str], float]) -> list[dict]:
    pares = []
    por_marca = {marca: bloco for marca, bloco in fichas.groupby("marca")}
    for _, saindo in fichas.iterrows():
        # A censura que descarta o modelo que SAI e' a da direita: saida no
        # ultimo mes da amostra nao e' saida, e' fim de janela. A censura a'
        # esquerda vale para o modelo que ENTRA, e e' aplicada no laco de baixo.
        if saindo["censura_direita"]:
            continue
        saida = periodo.para_indice(saindo["saida"])
        candidatos = por_marca.get(saindo["marca"])
        if candidatos is None:
            continue
        for _, entrando in candidatos.iterrows():
            if entrando["modelo"] == saindo["modelo"]:
                # Mesmo nome comercial nos dois segmentos nao e' sucessao: e' o
                # caso da QUESTOES_ABERTAS.md Q4, reportado em aba propria.
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
                "variacao_mercado_no_mes": mercado.get(
                    (saindo["segmento"], saindo["saida"]), float("nan")),
                "unidades_origem": saindo["unidades_totais"],
                "unidades_destino": entrando["unidades_totais"],
                "volume_em_jogo": min(saindo["unidades_totais"], entrando["unidades_totais"]),
                "volume_somado": saindo["unidades_totais"] + entrando["unidades_totais"],
                "decisao": "",
                "observacao_humana": "",
            })
    return pares


def _quedas_abruptas(
    largo: pd.DataFrame, meses: list[str], mercado: dict[tuple[str, str], float]
) -> dict[tuple, list[str]]:
    """Meses em que a serie cai abruptamente **mais do que o mercado**.

    Tres condicoes, todas necessarias (QUESTOES_ABERTAS.md Q9):

    1. a queda supera 80% depois de descontada a variacao do proprio segmento no
       mes -- em Abr/2020 o segmento caiu 73% e sem o desconto quase todo modelo
       disparava o detector;
    2. o mes anterior nao vinha ja' caindo, senao e' declinio, nao ruptura;
    3. a serie tinha ao menos `config.QUEDA_VOLUME_MINIMO` unidades antes da
       queda, para nao marcar serie de tres unidades.

    Calculado de uma vez para todos os modelos.
    """
    valores = largo[meses].to_numpy(dtype="float64")
    atual = valores[:, 2:]
    antes = valores[:, 1:-1]
    antes_de_antes = valores[:, :-2]

    # Quanto o mercado sozinho ja' explicaria da queda, mes a mes e por segmento.
    segmentos = [chave[2] for chave in largo.index]
    fator = np.ones_like(atual)
    if config.QUEDA_DESCONTAR_MERCADO:
        for coluna, mes in enumerate(meses[2:]):
            variacao = np.array(
                [mercado.get((segmento, mes), 0.0) for segmento in segmentos], dtype="float64"
            )
            fator[:, coluna] = np.clip(1.0 + variacao, 0.05, None)

    with np.errstate(invalid="ignore", divide="ignore"):
        esperado = antes * fator
        queda = (esperado - atual) / esperado
        vinha_caindo = antes < antes_de_antes * 0.9
    sinalizado = (
        np.isfinite(antes) & np.isfinite(atual)
        & (antes >= config.QUEDA_VOLUME_MINIMO)
        & (queda > config.QUEDA_ABRUPTA)
        & ~(np.isfinite(antes_de_antes) & (antes_de_antes > 0) & vinha_caindo)
    )
    achados: dict[tuple, list[str]] = {}
    linhas, colunas = np.nonzero(sinalizado)
    for linha, coluna in zip(linhas, colunas):
        achados.setdefault(largo.index[linha], []).append(meses[coluna + 2])
    return achados


def _queda_abrupta(fichas: pd.DataFrame, largo: pd.DataFrame, meses: list[str],
                   mercado: dict[tuple[str, str], float]) -> list[dict]:
    """Perda > 80% num unico mes, sem declinio previo, com entrada adjacente.

    E' o detector de rebatismo puro: o nome antigo desaparece de um mes para o
    outro e um nome novo da mesma marca aparece ao lado.
    """
    pares = []
    entradas_por_marca: dict[str, list] = {}
    for _, ficha in fichas.iterrows():
        if ficha["censura_esquerda"]:
            continue
        entradas_por_marca.setdefault(ficha["marca"], []).append(ficha)

    quedas = _quedas_abruptas(largo, meses, mercado)
    for _, saindo in fichas.iterrows():
        chave = (saindo["marca"], saindo["modelo"], saindo["segmento"])
        serie = largo.loc[chave]
        for mes_queda in quedas.get(chave, []):
            for entrando in entradas_por_marca.get(saindo["marca"], []):
                if entrando["modelo"] == saindo["modelo"]:
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
                    "variacao_mercado_no_mes": mercado.get(
                        (saindo["segmento"], mes_queda), float("nan")),
                    "unidades_origem": saindo["unidades_totais"],
                    "unidades_destino": entrando["unidades_totais"],
                    "volume_em_jogo": min(saindo["unidades_totais"],
                                          entrando["unidades_totais"]),
                    "volume_somado": saindo["unidades_totais"] + entrando["unidades_totais"],
                    "decisao": "",
                    "observacao_humana": "",
                })
    return pares


LEIA_ME = [
    ("O que e' este arquivo",
     "Evidencia para adjudicacao humana (ESPEC.md sec.5). Nada aqui foi fundido, e "
     "nesta rodada regras.csv fica vazio de proposito: a base vem primeiro, a "
     "harmonizacao depois."),
    ("Como usar",
     "Preencha a coluna 'decisao' da aba 'pares' com um de: rebatismo, "
     "reclassificacao, substituicao, ignorar. Depois transcreva as linhas "
     "decididas para regras.csv na raiz do repositorio."),
    ("regras.csv",
     "Colunas: tipo, marca, modelo_origem, modelo_destino, data_evento, observacao. "
     "data_evento e' obrigatoria para rebatismo (AAAA-MM) -- e' o campo que D2 manda "
     "registrar."),
    ("Ordenacao",
     "A aba 'pares' vem ordenada por volume_em_jogo = MENOR das duas series, nao pela "
     "soma. E' o menor que limita quanta substituicao o par pode explicar: um Gol de "
     "775 mil unidades pareado com um destino de duas nao e' um par grande, e a soma "
     "o colocaria no topo. A soma continua na coluna volume_somado."),
    ("Sinal esperado da correlacao",
     "NEGATIVO. Sucessao e' um caindo enquanto o outro sobe, entao correlacao_12m "
     "negativa e' o sinal a favor do par, nao contra. Quem filtrar por correlacao "
     "positiva descarta justamente os casos reais -- Palio->Argo tem -0,81, "
     "Prisma->Onix Plus tem -0,75."),
    ("Censura",
     "Sao duas exclusoes com alvos diferentes. Entrada no primeiro mes da amostra "
     "invalida a ENTRADA, entao descarta o modelo no papel de sucessor. Saida no "
     "ultimo mes invalida a SAIDA, entao descarta o modelo no papel de quem sai. Um "
     "modelo vivo no primeiro mes continua podendo sair: e' o caso do Prisma."),
    ("Detector de queda abrupta",
     "Exige que a queda supere 80% DEPOIS de descontada a variacao do proprio "
     "segmento no mes, e que a serie tivesse ao menos 100 unidades antes da queda. "
     "Sem o desconto, Abr/2020 -- quando o mercado caiu 73% num mes -- enchia a lista "
     "de pares em que nada aconteceu com o produto."),
    ("Aba mesmo_nome_dois_segmentos",
     "Nome comercial que a fonte publica em automoveis e em comerciais leves. "
     "Nao e' sucessao: e' a questao de unidade de observacao (QUESTOES_ABERTAS.md Q4). "
     "Estes pares foram deliberadamente mantidos fora da aba 'pares'."),
    ("Similaridade de nome",
     "Nao usada, por decisao da ESPEC sec.5: produz falsos pares e nao encontra "
     "Prisma -> Onix Plus."),
    ("Limitacao declarada",
     "Troca de geracao e' invisivel na fonte na maior parte dos casos -- nao em "
     "todos. Onde a fonte separa geracoes em sub-segmentos diferentes (NISSAN/VERSA "
     "em 'Sedans Pequenos' e 'Sedans Compactos' no mesmo mes), o painel preserva as "
     "linhas separadas. Fora desses casos, 'sobrevivencia do modelo' significa "
     "sobrevivencia do nome comercial."),
]


def executar(limiar: float = config.LIMIAR_SAIDA) -> int:
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

    mercado = _variacao_do_mercado(bruto, meses)
    pares = (_passagem_de_bastao(fichas, largo, meses, mercado)
             + _queda_abrupta(fichas, largo, meses, mercado))
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

    # Mesmo nome comercial publicado nos dois segmentos: nao e' sucessao, e' a
    # questao de unidade de observacao (QUESTOES_ABERTAS.md, Q4). Vai em aba
    # propria para que o pesquisador decida a chave, nao como par candidato.
    dois_segmentos = pd.DataFrame()
    if not fichas.empty:
        contagem = fichas.groupby(["marca", "modelo"])["segmento"].nunique()
        repetidos = contagem[contagem > 1].index
        if len(repetidos):
            dois_segmentos = (
                fichas.set_index(["marca", "modelo"]).loc[repetidos].reset_index()
                .sort_values("unidades_totais", ascending=False)
            )

    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(config.CANDIDATOS, engine="xlsxwriter") as escritor:
        pd.DataFrame(LEIA_ME, columns=["topico", "texto"]).to_excel(
            escritor, sheet_name="leia_me", index=False)
        (quadro_pares if not quadro_pares.empty
         else pd.DataFrame(columns=["detector", "marca", "modelo_origem", "decisao"])
         ).to_excel(escritor, sheet_name="pares", index=False)
        fichas.sort_values("unidades_totais", ascending=False).to_excel(
            escritor, sheet_name="fichas", index=False)
        (dois_segmentos if not dois_segmentos.empty
         else pd.DataFrame(columns=["marca", "modelo", "segmento"])
         ).to_excel(escritor, sheet_name="mesmo_nome_dois_segmentos", index=False)
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
