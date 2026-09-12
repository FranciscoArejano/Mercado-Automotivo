#!/usr/bin/env python3
"""Etapa 7 -- referencia cruzada com a planilha existente (ESPEC.md sec.7).

`Vendas_Geral.xlsx` **nao e' fonte**: e' controle independente, montado a' mao,
cobrindo 2013-2023. Depois de reconstruir o periodo do zero, comparamos modelo
a modelo e mes a mes e reportamos as divergencias -- elas revelam erro de
parsing de um lado ou do outro.

Dois fatos conhecidos sobre a planilha, usados como teste do proprio leitor:

1. Os rotulos de mes dizem `jan/23` em todas as abas, residuo de copia. A ordem
   das colunas esta' correta; o rotulo, nao. Por isso este leitor usa **posicao
   de coluna** e ignora o rotulo -- e reporta quando o rotulo confirma o erro.
2. A aba 2013 traz so' o top-50 anual, sem mensal. Fica **de fora**: misturada,
   criaria entrada fantasma em 2014.

A planilha e' opcional. Ausente, a etapa reporta a ausencia e sai sem falhar --
ela e' controle, nao insumo.

Uso:
    python src/etapa07_referencia_cruzada.py [--planilha CAMINHO]
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, log, marcas  # noqa: E402

ETAPA = "etapa07_referencia_cruzada"
ANOS_COMPARAVEIS = range(2014, 2024)
RE_ROTULO_MES = re.compile(r"^([a-zA-Z]{3})[/\-]?(\d{2,4})$")


def _tabela(quadro: pd.DataFrame, maximo: int = 40) -> str:
    if quadro.empty:
        return "_(vazio)_\n"
    texto = quadro.head(maximo).to_markdown(index=False)
    if len(quadro) > maximo:
        texto += f"\n\n_({len(quadro) - maximo} linhas restantes omitidas.)_"
    return texto + "\n"


def ler_planilha(caminho: Path, logger) -> tuple[pd.DataFrame, list[str]]:
    """Le a planilha por posicao de coluna. Devolve (longo, observacoes)."""
    livro = pd.read_excel(caminho, sheet_name=None, header=None)
    observacoes: list[str] = []
    registros: list[dict] = []

    for aba, bruto in livro.items():
        achado = re.search(r"(20\d{2})", str(aba))
        if not achado:
            observacoes.append(f"aba `{aba}` ignorada: nome nao contem um ano")
            continue
        ano = int(achado.group(1))
        if ano == 2013:
            observacoes.append(
                "aba `2013` deixada de fora: a planilha traz so' o top-50 anual, sem mensal "
                "(sec.7, item 2). Misturada, criaria entrada fantasma em 2014."
            )
            continue
        if ano not in ANOS_COMPARAVEIS:
            observacoes.append(f"aba `{aba}` fora de 2014-2023, ignorada")
            continue

        # Cabecalho: primeira linha que traz pelo menos tres rotulos de mes.
        linha_cabecalho = None
        for indice in range(min(10, len(bruto))):
            rotulos = [str(v) for v in bruto.iloc[indice].tolist()]
            if sum(bool(RE_ROTULO_MES.match(r.strip())) for r in rotulos) >= 3:
                linha_cabecalho = indice
                break
        if linha_cabecalho is None:
            observacoes.append(f"aba `{aba}`: cabecalho de meses nao encontrado -- aba ignorada")
            continue

        rotulos = [str(v).strip() for v in bruto.iloc[linha_cabecalho].tolist()]
        colunas_mes = [i for i, r in enumerate(rotulos) if RE_ROTULO_MES.match(r)]
        distintos = {rotulos[i].lower() for i in colunas_mes}
        if len(distintos) == 1:
            observacoes.append(
                f"aba `{aba}`: os {len(colunas_mes)} rotulos de mes sao todos "
                f"`{rotulos[colunas_mes[0]]}` -- residuo de copia confirmado (sec.7, item 1). "
                "Colunas lidas por posicao."
            )
        colunas_mes = colunas_mes[:12]

        corpo = bruto.iloc[linha_cabecalho + 1:]
        coluna_nome = next(
            (i for i in range(len(rotulos)) if i not in colunas_mes
             and corpo.iloc[:, i].astype(str).str.contains("/").any()),
            0,
        )
        for _, linha in corpo.iterrows():
            nome = str(linha.iloc[coluna_nome]).strip()
            if not nome or nome.lower() in {"nan", "total", "modelo"}:
                continue
            for posicao, coluna in enumerate(colunas_mes, start=1):
                valor = pd.to_numeric(linha.iloc[coluna], errors="coerce")
                if pd.isna(valor):
                    continue
                separacao = marcas.separar(nome)
                registros.append({
                    "mes_ref": f"{ano}-{posicao:02d}",
                    "marca": separacao.marca,
                    "modelo": separacao.modelo,
                    "nome_planilha": nome,
                    "unidades_planilha": float(valor),
                })
        logger.info("aba %s: %d colunas de mes, %d linhas de modelo", aba, len(colunas_mes), len(corpo))

    return pd.DataFrame(registros), observacoes


def executar(caminho: Path = config.VENDAS_GERAL) -> int:
    logger = log.preparar(ETAPA)
    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    cabecalho = (
        "# Referencia cruzada com `Vendas_Geral.xlsx`\n\n"
        f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC).\n\n"
        "A planilha e' **controle independente**, nao fonte (ESPEC.md sec.7). "
        "Divergencia aqui nao decide nada sozinha: ela aponta onde olhar.\n\n"
    )

    if not caminho.exists():
        texto = (
            cabecalho
            + f"## Situacao: planilha ausente\n\n"
            f"Esperada em `{log.caminho_relativo(caminho)}` e nao encontrada. A comparacao "
            "nao foi feita. Isto **nao** invalida o painel: a planilha e' controle, nao "
            "insumo.\n\nPara rodar o confronto, coloque o arquivo nesse caminho (ou passe "
            "`--planilha CAMINHO`) e execute:\n\n```\npython src/etapa07_referencia_cruzada.py\n```\n"
        )
        config.REFERENCIA_CRUZADA.write_text(texto, encoding="utf-8")
        logger.warning("planilha de controle ausente em %s -- comparacao nao realizada",
                       log.caminho_relativo(caminho))
        return 0

    if not config.PAINEL.exists():
        raise log.ErroDeParsing(
            f"{log.caminho_relativo(config.PAINEL)} nao existe -- rode as etapas anteriores."
        )

    planilha, observacoes = ler_planilha(caminho, logger)
    painel = pd.read_parquet(config.PAINEL)
    painel = painel[painel["ano"].isin(ANOS_COMPARAVEIS)]
    reconstruido = (
        painel.groupby(["mes_ref", "marca", "modelo"], as_index=False)["unidades"].sum()
        .rename(columns={"unidades": "unidades_painel"})
    )

    comparacao = reconstruido.merge(planilha, on=["mes_ref", "marca", "modelo"], how="outer")
    comparacao["unidades_painel"] = comparacao["unidades_painel"].fillna(0)
    comparacao["unidades_planilha"] = comparacao["unidades_planilha"].fillna(0)
    comparacao["diferenca"] = comparacao["unidades_painel"] - comparacao["unidades_planilha"]
    comparacao["situacao"] = "igual"
    comparacao.loc[comparacao["diferenca"] != 0, "situacao"] = "diverge"
    comparacao.loc[comparacao["unidades_planilha"] == 0, "situacao"] = "so_no_painel"
    comparacao.loc[comparacao["unidades_painel"] == 0, "situacao"] = "so_na_planilha"
    comparacao.sort_values(["mes_ref", "marca", "modelo"]).to_csv(
        config.DIR_SAIDAS / "referencia_cruzada.csv", index=False)

    mensal = comparacao.groupby("mes_ref", as_index=False).agg(
        painel=("unidades_painel", "sum"), planilha=("unidades_planilha", "sum"))
    mensal["diferenca"] = mensal["painel"] - mensal["planilha"]
    mensal["diferenca_pct"] = (100 * mensal["diferenca"] / mensal["planilha"].replace(0, pd.NA)).round(3)

    anual = comparacao.assign(ano=comparacao["mes_ref"].str.slice(0, 4).astype(int))
    anual = anual.groupby("ano", as_index=False).agg(
        painel=("unidades_painel", "sum"), planilha=("unidades_planilha", "sum"))
    anual["diferenca"] = anual["painel"] - anual["planilha"]
    anual["diferenca_pct"] = (100 * anual["diferenca"] / anual["planilha"].replace(0, pd.NA)).round(3)

    piores = (
        comparacao[comparacao["situacao"] != "igual"]
        .assign(magnitude=lambda q: q["diferenca"].abs())
        .sort_values("magnitude", ascending=False)
        .drop(columns=["magnitude"])
    )

    texto = cabecalho
    texto += "## Observacoes do leitor da planilha\n\n"
    texto += "".join(f"- {o}\n" for o in observacoes) or "_(nenhuma)_\n"
    texto += "\n## Total por ano\n\n" + _tabela(anual)
    texto += "\n## Total por mes\n\n" + _tabela(mensal, 200)
    texto += (
        f"\n## Divergencias modelo a modelo\n\n{len(piores)} pares (mes x modelo) divergentes "
        f"de {len(comparacao)} comparados. Lista completa em "
        "`saidas/referencia_cruzada.csv`.\n\n" + _tabela(piores, 60)
    )
    config.REFERENCIA_CRUZADA.write_text(texto, encoding="utf-8")

    log.contagem(logger, linhas_planilha=len(planilha), linhas_painel=len(reconstruido),
                 comparadas=len(comparacao), divergentes=len(piores))
    logger.info("gravado %s", log.caminho_relativo(config.REFERENCIA_CRUZADA))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--planilha", type=Path, default=config.VENDAS_GERAL)
    args = analisador.parse_args()
    return executar(args.planilha)


if __name__ == "__main__":
    raise SystemExit(main())
