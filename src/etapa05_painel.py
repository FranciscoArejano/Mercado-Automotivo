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

from comum import config, dicionario, grupos, log, nomes, truncamento  # noqa: E402
from comum import regras as mod_regras  # noqa: E402
from comum import recuperacao_marca as mod_recuperacao  # noqa: E402

ETAPA = "etapa05_painel"

COLUNAS = [
    "mes_ref", "ano", "mes", "data", "segmento", "marca", "modelo",
    "sub_segmento_fonte", "grupo_economico", "grupo_mapeado", "unidades",
    "corte_publicacao", "nome_suspeito", "motivo_nome_suspeito",
    "modelo_fonte", "grafias_fonte", "nome_completo_fonte",
    "marca_publicada_fonte", "marca_recuperada",
    "houve_rebatismo", "data_rebatismo", "cadeia_rebatismo",
    "reclassificacao", "conta_entrada_saida", "origem_tabela", "arquivos_origem",
]


def aplicar(bruto: pd.DataFrame, regras: list[mod_regras.Regra], logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    # 1. Uma linha por (mes, segmento, marca, modelo, sub-segmento). O
    #    sub-segmento fica **na linha, fora da chave** (QUESTOES_ABERTAS.md Q4):
    #    quando a fonte publica o mesmo nome em dois sub-segmentos no mesmo mes
    #    -- NISSAN/VERSA em "Sedans Pequenos" com a geracao antiga e em "Sedans
    #    Compactos" com a nova -- as duas linhas ficam separadas. E' a unica
    #    pista de geracao que a fonte da'. A soma por modelo e' visao
    #    (comum/visoes.py), nao esquema.
    # D1: a chave e' canonizada em caixa antes de agrupar. A fonte escreveu
    # MITSUBISHI/Outlander por oito anos e MITSUBISHI/OUTLANDER num mes, e sem
    # isto o mesmo carro vira duas fichas, com uma saida e uma entrada
    # fabricadas. `modelo_fonte` e `nome_completo_fonte` guardam a grafia crua.
    bruto = bruto.copy()
    bruto["marca_chave"] = bruto["marca_fonte"].map(nomes.chave)
    bruto["modelo_chave"] = bruto["modelo_fonte"].map(nomes.chave)
    colisoes = nomes.colisoes_de_caixa(
        bruto.rename(columns={"marca_fonte": "marca", "modelo_fonte": "modelo",
                              "segmento_fonte": "segmento"}),
        ("marca", "modelo", "segmento"),
    )
    if not colisoes.empty:
        logger.warning(
            "%d grafias unificadas por caixa na chave: %s",
            len(colisoes),
            "; ".join(f"{linha.marca}/{linha.modelo}" for linha in colisoes.itertuples()),
        )
        colisoes.to_csv(config.DIR_SAIDAS / "colisoes_de_caixa.csv", index=False)

    # D4: edicao que saiu com a coluna de marca trocada. O valor nao muda -- so'
    # a quem ele e' atribuido --, e a nova atribuicao vem da mesma fonte
    # republicando o mes na coluna de mes anterior do informe seguinte, a rota
    # ja' validada em 2023-09. `marca_fonte` segue intacta na linha ao lado.
    bruto["marca_publicada_fonte"] = bruto["marca_chave"]
    bruto["marca_recuperada"] = False
    recuperacoes = mod_recuperacao.recuperacoes(
        bruto.rename(columns={"marca_chave": "marca", "modelo_chave": "modelo",
                              "segmento_fonte": "segmento"})
    )
    if not recuperacoes.empty:
        recuperacoes.to_csv(config.DIR_SAIDAS / "marca_recuperada.csv", index=False)
        aplicadas = recuperacoes[recuperacoes["marca_recuperada"] != ""]
        for _, linha in aplicadas.iterrows():
            alvo_linhas = (
                (bruto["mes_ref"] == linha["mes_ref"])
                & (bruto["modelo_chave"] == linha["modelo"])
                & (bruto["segmento_fonte"] == linha["segmento"])
            )
            bruto.loc[alvo_linhas, "marca_chave"] = nomes.chave(linha["marca_recuperada"])
            bruto.loc[alvo_linhas, "marca_recuperada"] = True
        duplicatas = mod_recuperacao.duplicatas_apos_recuperacao(bruto)
        if not duplicatas.empty:
            duplicatas.to_csv(config.DIR_SAIDAS / "duplicatas_de_marca_trocada.csv",
                              index=False)
            logger.warning(
                "D4: %d linhas do ranking repetem uma de sub-segmento depois da "
                "recuperacao (%d unidades contadas duas vezes pela fonte). NADA foi "
                "descartado -- ver saidas/duplicatas_de_marca_trocada.csv",
                len(duplicatas), int(duplicatas["unidades_ranking"].sum()),
            )
        logger.warning(
            "D4: %d de %d modelos com marca trocada recuperados pelo informe seguinte "
            "(%s); %d sem rota",
            len(aplicadas), len(recuperacoes),
            ", ".join(sorted(recuperacoes["mes_ref"].unique())),
            len(recuperacoes) - len(aplicadas),
        )

    chaves = ["mes_ref", "ano", "mes", "data", "segmento_fonte", "marca_chave",
              "modelo_chave", "sub_segmento_fonte"]
    agregado = (
        bruto.groupby(chaves, as_index=False)
        .agg(
            unidades=("unidades", "sum"),
            grafias_fonte=("modelo_fonte", lambda s: "+".join(sorted(set(s)))),
            nome_completo_fonte=("nome_completo_fonte", lambda s: "+".join(sorted(set(s)))),
            origem_tabela=("origem_tabela", lambda s: "+".join(sorted(set(s)))),
            marca_publicada_fonte=("marca_publicada_fonte",
                                   lambda s: "+".join(sorted(set(s)))),
            marca_recuperada=("marca_recuperada", "max"),
            arquivos_origem=("arquivo_origem", lambda s: "+".join(sorted(set(s)))),
        )
        .rename(columns={"segmento_fonte": "segmento", "marca_chave": "marca",
                         "modelo_chave": "modelo_fonte"})
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

    # 4. Grupo economico datado (D4). Nunca retroativo, nunca adivinhado. Marca
    #    sem linha vigente vira grupo unitario com o proprio nome, para nao
    #    distorcer o indice de concentracao; `grupo_mapeado` guarda o aviso.
    vigentes = [
        grupos.grupo_vigente(marca, mes)
        for marca, mes in zip(agregado["marca"], agregado["mes_ref"])
    ]
    agregado["grupo_economico"] = [g for g, _ in vigentes]
    agregado["grupo_mapeado"] = [m for _, m in vigentes]

    painel = (
        agregado.groupby(
            ["mes_ref", "ano", "mes", "data", "segmento", "marca", "modelo",
             "sub_segmento_fonte"], as_index=False
        )
        .agg(
            grupo_economico=("grupo_economico", "first"),
            grupo_mapeado=("grupo_mapeado", "min"),
            unidades=("unidades", "sum"),
            modelo_fonte=("modelo_fonte", lambda s: "+".join(sorted(set(s)))),
            grafias_fonte=("grafias_fonte", lambda s: "+".join(sorted(set(s)))),
            nome_completo_fonte=("nome_completo_fonte", lambda s: "+".join(sorted(set(s)))),
            houve_rebatismo=("houve_rebatismo", "max"),
            data_rebatismo=("data_rebatismo", lambda s: next((v for v in s if v), "")),
            cadeia_rebatismo=("cadeia_rebatismo", lambda s: next((v for v in s if v), "")),
            reclassificacao=("reclassificacao", "max"),
            conta_entrada_saida=("conta_entrada_saida", "min"),
            origem_tabela=("origem_tabela", lambda s: "+".join(sorted(set(s)))),
            arquivos_origem=("arquivos_origem", lambda s: "+".join(sorted(set(s)))),
            marca_publicada_fonte=("marca_publicada_fonte",
                                   lambda s: "+".join(sorted(set(s)))),
            marca_recuperada=("marca_recuperada", "max"),
        )
    )
    # 5. Corte de publicacao (QUESTOES_ABERTAS.md Q5). Nao e' o menor valor do
    #    mes: a fonte trunca por **numero fixo de linhas por sub-segmento**, e o
    #    corte que vale para uma linha e' o do bloco em que ela esta', quando o
    #    bloco esta' no teto. Ver comum/truncamento.py.
    blocos = truncamento.por_bloco(bruto)[
        ["mes_ref", "segmento", "sub_segmento_fonte", "corte"]
    ].rename(columns={"corte": "corte_publicacao"})
    painel = painel.merge(
        blocos, on=["mes_ref", "segmento", "sub_segmento_fonte"], how="left")
    painel["corte_publicacao"] = painel["corte_publicacao"].fillna(0).astype("int64")

    # 6. D2: nome que nao designa veiculo. Nada e' apagado -- o painel ganha a
    #    marca e o relatorio lista os candidatos a revisao humana.
    motivos = [
        nomes.motivo_nao_veiculo(marca, modelo)
        for marca, modelo in zip(painel["marca"], painel["modelo"])
    ]
    painel["motivo_nome_suspeito"] = motivos
    painel["nome_suspeito"] = [bool(m) for m in motivos]
    suspeitos = painel.loc[painel["nome_suspeito"], ["marca", "modelo"]].drop_duplicates()
    if not suspeitos.empty:
        logger.info(
            "%d nomes marcados como provavelmente nao-veiculo (%d linhas, %d unidades)",
            len(suspeitos), int(painel["nome_suspeito"].sum()),
            int(painel.loc[painel["nome_suspeito"], "unidades"].sum()),
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
        linhas_sem_grupo_no_mapa=int((~painel["grupo_mapeado"]).sum()),
    )
    logger.info("gravado %s", log.caminho_relativo(config.PAINEL))
    return 0


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    return executar()


if __name__ == "__main__":
    raise SystemExit(main())
