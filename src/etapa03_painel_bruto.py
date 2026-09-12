#!/usr/bin/env python3
"""Etapa 3 -- painel bruto (ESPEC.md sec.4).

Transcricao fiel da fonte. Nenhuma fusao, nenhuma limpeza semantica: so' a
separacao de marca e modelo (pela barra que a propria fonte usa) e a
normalizacao tipografica ja' aplicada na leitura. O nome cru fica em
`nome_completo_fonte`.

`painel_bruto.parquet` nunca e' sobrescrito (sec.9.3). Se o arquivo ja' existe:
- conteudo identico  -> mantido intocado (o pipeline e' idempotente, sec.1.3);
- conteudo diferente -> a etapa **para**, grava o novo ao lado com sufixo
  `.divergente.parquet` e descreve a diferenca. Substituir e' decisao humana,
  feita com --recriar.

Uso:
    python src/etapa03_painel_bruto.py [--inicio AAAA-MM] [--fim AAAA-MM] [--recriar]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, log, marcas, periodo  # noqa: E402

ETAPA = "etapa03_painel_bruto"

COLUNAS = [
    "mes_ref", "ano", "mes", "data", "segmento_fonte", "sub_segmento_fonte",
    "origem_tabela", "posicao_fonte", "marca_fonte", "modelo_fonte",
    "nome_completo_fonte", "metodo_separacao", "marca_conhecida", "unidades",
    "metodo_extracao", "arquivo_origem", "pagina_origem",
]


def _impressao(quadro: pd.DataFrame) -> str:
    """Assinatura estavel do conteudo, para decidir se algo mudou de fato."""
    ordenado = quadro.sort_values(
        ["mes_ref", "segmento_fonte", "sub_segmento_fonte", "nome_completo_fonte", "origem_tabela"]
    ).reset_index(drop=True)
    return hashlib.sha256(
        ordenado.to_csv(index=False, lineterminator="\n").encode("utf-8")
    ).hexdigest()


def montar(meses: list[str], logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    partes: list[pd.DataFrame] = []
    lidas = 0
    for mes in meses:
        caminho = config.DIR_EXTRACAO / f"{mes}.csv"
        if not caminho.exists():
            logger.warning("%s: sem extracao (%s)", mes, log.caminho_relativo(caminho))
            continue
        bloco = pd.read_csv(caminho, dtype=str, keep_default_na=False)
        lidas += len(bloco)
        if bloco.empty:
            logger.warning("%s: extracao vazia", mes)
            continue
        partes.append(bloco)
    if not partes:
        raise log.ErroDeParsing("nenhuma extracao encontrada -- rode a etapa 02 antes.")

    bruto = pd.concat(partes, ignore_index=True)
    logger.info("linhas lidas das extracoes: %d", lidas)

    separacoes = [marcas.separar(nome) for nome in bruto["nome_completo_fonte"]]
    bruto["marca_fonte"] = [s.marca for s in separacoes]
    bruto["modelo_fonte"] = [s.modelo for s in separacoes]
    bruto["metodo_separacao"] = [s.metodo for s in separacoes]
    bruto["marca_conhecida"] = [s.conhecida for s in separacoes]

    bruto["mes_ref"] = bruto["mes"]
    bruto["ano"] = bruto["mes_ref"].str.slice(0, 4).astype("int32")
    bruto["mes"] = bruto["mes_ref"].str.slice(5, 7).astype("int32")
    bruto["data"] = pd.to_datetime(bruto["mes_ref"] + "-01").dt.date
    bruto["unidades"] = pd.to_numeric(bruto["unidades_mes"]).astype("int64")
    bruto["pagina_origem"] = pd.to_numeric(bruto["pagina"]).astype("int32")
    bruto["posicao_fonte"] = pd.to_numeric(bruto["posicao_fonte"]).astype("int32")
    bruto = bruto.rename(columns={"segmento": "segmento_fonte"})

    painel = bruto[COLUNAS].copy()

    # Relatorio de nomes nao resolvidos e marcas fora da lista curada (sec.4).
    nao_mapeadas = (
        painel.loc[~painel["marca_conhecida"]]
        .groupby(["marca_fonte", "metodo_separacao"], as_index=False)
        .agg(
            linhas=("unidades", "size"),
            unidades=("unidades", "sum"),
            primeiro_mes=("mes_ref", "min"),
            ultimo_mes=("mes_ref", "max"),
            exemplo=("nome_completo_fonte", "first"),
        )
        .sort_values("unidades", ascending=False)
    )
    return painel, nao_mapeadas


def executar(inicio: str, fim: str, recriar: bool = False) -> int:
    logger = log.preparar(ETAPA)
    meses = periodo.intervalo(inicio, fim)
    painel, nao_mapeadas = montar(meses, logger)

    config.DIR_PROCESSADO.mkdir(parents=True, exist_ok=True)
    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    nao_mapeadas.to_csv(config.DIR_SAIDAS / "marcas_nao_mapeadas.csv", index=False)
    if not nao_mapeadas.empty:
        logger.warning(
            "%d marcas fora de config/marcas.csv (%d unidades) -- reportadas, nao adivinhadas: %s",
            len(nao_mapeadas), int(nao_mapeadas["unidades"].sum()),
            ", ".join(nao_mapeadas["marca_fonte"].head(15)),
        )

    if config.PAINEL_BRUTO.exists() and not recriar:
        anterior = pd.read_parquet(config.PAINEL_BRUTO)
        if _impressao(anterior) == _impressao(painel):
            logger.info("painel_bruto.parquet ja' existe com conteudo identico -- intocado")
            log.contagem(logger, linhas=len(painel), meses=painel["mes_ref"].nunique())
            return 0
        divergente = config.PAINEL_BRUTO.with_suffix(".divergente.parquet")
        painel.to_parquet(divergente, index=False)
        raise log.ErroMetodologico(
            "painel_bruto.parquet ja' existe com conteudo diferente e nao pode ser "
            f"sobrescrito (sec.9.3). Anterior: {len(anterior)} linhas, "
            f"{anterior['unidades'].sum():.0f} unidades. Novo: {len(painel)} linhas, "
            f"{painel['unidades'].sum():.0f} unidades, gravado em "
            f"{log.caminho_relativo(divergente)}. Compare os dois e, se a substituicao "
            "for a decisao correta, rode com --recriar."
        )

    painel.to_parquet(config.PAINEL_BRUTO, index=False)
    log.contagem(
        logger, linhas_escritas=len(painel), meses=painel["mes_ref"].nunique(),
        modelos=painel[["marca_fonte", "modelo_fonte", "segmento_fonte"]].drop_duplicates().shape[0],
        unidades=int(painel["unidades"].sum()),
        marcas_nao_mapeadas=len(nao_mapeadas),
    )
    logger.info("gravado %s", log.caminho_relativo(config.PAINEL_BRUTO))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--inicio", default=config.PERIODO_INICIO)
    analisador.add_argument("--fim", default=config.PERIODO_FIM)
    analisador.add_argument("--recriar", action="store_true",
                            help="autoriza substituir um painel_bruto.parquet divergente")
    args = analisador.parse_args()
    return executar(args.inicio, args.fim, args.recriar)


if __name__ == "__main__":
    raise SystemExit(main())
