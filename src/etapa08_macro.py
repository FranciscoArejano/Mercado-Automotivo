#!/usr/bin/env python3
"""Etapa 8 -- dimensao macro mensal.

Tabela de fatos separada, unidade `mes_ref`. **Nao alarga o painel**: a juncao e'
do codigo de analise, e por isso a dimensao pode ter janela diferente sem
contaminar nada.

Duas fontes:

- **BCB/SGS**, as series de `config/series_macro.csv` -- credito de veiculos,
  cambio, Selic, IPCA, IGP-DI, IBC-Br, massa salarial.
- **IBGE/SIDRA**, IPCA por subitem (automovel novo e usado, gasolina, etanol,
  motocicleta), repartido em quatro tabelas que a etapa emenda num indice
  encadeado com base declarada, guardando tambem a variacao original.

Serie que comeca depois de 2003-01 ou termina antes de 2026-08 fica com o mes
**vazio**. Lacuna e' lacuna (sec.9.2).

Uso:
    python src/etapa08_macro.py [--inicio AAAA-MM] [--fim AAAA-MM] [--sem-rede]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, log, macro, periodo  # noqa: E402

ETAPA = "etapa08_macro"

SUBITENS_IPCA = {
    "7641": "automovel_novo",
    "107654": "automovel_usado",
    "7657": "gasolina",
    "7658": "etanol",
    "7654": "motocicleta",
}


def executar(inicio: str | None = None, fim: str | None = None) -> int:
    logger = log.preparar(ETAPA)
    inicio = inicio or config.PERIODO_INICIO
    fim = fim or config.PERIODO_FIM
    meses = periodo.intervalo(inicio, fim)
    painel = pd.DataFrame({"mes_ref": meses})

    catalogo = macro.carregar_catalogo()
    if not catalogo:
        raise log.ErroDeParsing(
            f"{log.caminho_relativo(config.SERIES_MACRO)} ausente ou vazio -- "
            "o codigo le', o humano escreve."
        )

    resumo: list[dict] = []

    # ------------------------------------------------------------ BCB / SGS
    for linha in catalogo:
        codigo, nome = linha["codigo"], linha["nome"]
        coluna = f"sgs_{codigo}"
        try:
            serie = macro.coletar_sgs(codigo, inicio, fim)
        except Exception as erro:
            logger.error("SGS %s (%s): %s", codigo, nome, erro)
            resumo.append({"serie": coluna, "nome": nome, "fonte": "BCB/SGS",
                           "situacao": f"falhou: {erro}"})
            continue
        no_periodo = serie[serie["mes_ref"].isin(meses)]
        painel = painel.merge(
            no_periodo.rename(columns={"valor": coluna}), on="mes_ref", how="left")
        resumo.append({
            "serie": coluna, "nome": nome, "fonte": "BCB/SGS",
            "unidade": linha.get("unidade", ""),
            "situacao_da_serie": linha.get("situacao_da_serie", ""),
            "janela_declarada": linha.get("janela_declarada", ""),
            "janela_efetiva": (f"{no_periodo['mes_ref'].min()}..{no_periodo['mes_ref'].max()}"
                               if not no_periodo.empty else "vazia"),
            "observacoes": len(no_periodo),
            "meses_do_painel_cobertos": int(no_periodo["mes_ref"].nunique()),
            "minimo": None if no_periodo.empty else float(no_periodo["valor"].min()),
            "maximo": None if no_periodo.empty else float(no_periodo["valor"].max()),
        })
        logger.info("SGS %s (%s): %d observacoes no periodo", codigo, nome, len(no_periodo))

    # --------------------------------------------------------- IBGE / SIDRA
    juncoes: list[pd.DataFrame] = []
    for subitem, apelido in SUBITENS_IPCA.items():
        try:
            variacoes = macro.coletar_ipca_subitem(subitem)
        except Exception as erro:
            logger.error("SIDRA c315/%s (%s): %s", subitem, apelido, erro)
            resumo.append({"serie": f"ipca_{apelido}", "nome": apelido,
                           "fonte": "IBGE/SIDRA", "situacao": f"falhou: {erro}"})
            continue
        encadeada = macro.encadear(variacoes, config.BASE_INDICE_IPCA)
        emendas = macro.juncoes_das_tabelas(variacoes)
        if not emendas.empty:
            emendas.insert(0, "subitem", apelido)
            juncoes.append(emendas)

        no_periodo = encadeada[encadeada["mes_ref"].isin(meses)]
        painel = painel.merge(
            no_periodo[["mes_ref", "variacao_pct", "indice"]].rename(columns={
                "variacao_pct": f"ipca_{apelido}_var_pct",
                "indice": f"ipca_{apelido}_indice",
            }),
            on="mes_ref", how="left")
        resumo.append({
            "serie": f"ipca_{apelido}", "nome": f"IPCA subitem {subitem} -- {apelido}",
            "fonte": "IBGE/SIDRA", "unidade": "% a.m. e indice encadeado",
            "situacao_da_serie": "ativa",
            "janela_declarada": "1999-08..2026-08 (quatro tabelas)",
            "janela_efetiva": (f"{no_periodo['mes_ref'].min()}..{no_periodo['mes_ref'].max()}"
                               if not no_periodo.empty else "vazia"),
            "observacoes": len(no_periodo),
            "meses_do_painel_cobertos": int(no_periodo["mes_ref"].nunique()),
            "minimo": None if no_periodo.empty else float(no_periodo["variacao_pct"].min()),
            "maximo": None if no_periodo.empty else float(no_periodo["variacao_pct"].max()),
        })
        logger.info("SIDRA c315/%s (%s): %d meses no periodo",
                    subitem, apelido, len(no_periodo))

    # ------------------------------------------------------------- gravacao
    config.DIR_PROCESSADO.mkdir(parents=True, exist_ok=True)
    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    if painel["mes_ref"].duplicated().any():
        raise log.ErroMetodologico("macro_mensal tem mes repetido -- a chave e' `mes_ref`.")
    faltando = set(meses) - set(painel["mes_ref"])
    if faltando:
        raise log.ErroMetodologico(f"macro_mensal sem os meses: {sorted(faltando)[:8]}")

    painel.to_parquet(config.MACRO_MENSAL, index=False)
    quadro_resumo = pd.DataFrame(resumo)
    quadro_resumo.to_csv(config.DIR_SAIDAS / "macro_series.csv", index=False)
    if juncoes:
        pd.concat(juncoes, ignore_index=True).to_csv(
            config.DIR_SAIDAS / "macro_emendas_ipca.csv", index=False)

    log.contagem(logger, meses=len(painel), series=len(quadro_resumo),
                 colunas=len(painel.columns) - 1)
    logger.info("gravado %s", log.caminho_relativo(config.MACRO_MENSAL))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--inicio", default=config.PERIODO_INICIO)
    analisador.add_argument("--fim", default=config.PERIODO_FIM)
    argumentos = analisador.parse_args()
    return executar(argumentos.inicio, argumentos.fim)


if __name__ == "__main__":
    raise SystemExit(main())
