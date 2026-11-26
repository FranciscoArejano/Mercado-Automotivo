#!/usr/bin/env python3
"""Etapa 15 -- fator medio mensal de emissao de CO2 do SIN (MCTI, inventarios).

Le a planilha guardada em `dados/bruto/mcti_fator/` (baixada por
`src/coleta/mcti_fator.py`, SHA-256 no manifesto) e grava:

- `dados/processado/fator_emissao_sin_mensal.parquet` -- uma linha por mes, desde
  o inicio da serie (2006-01): `mes`, `ano`, `fator_tco2_mwh` e, repetido em cada
  mes do ano, `fator_anual_publicado_tco2_mwh` (o fator anual que a propria
  planilha traz);
- `saidas/fator_emissao_sin_validacao.csv` -- conferencias;
- `saidas/fator_emissao_sin_mensal_dicionario.md`.

Falha (codigo 1) se faltar mes no meio da serie, se o SHA-256 nao bater, ou se um
fator sair do intervalo (0, 1) tCO2/MWh. A diferenca entre a media simples dos
meses e o fator anual publicado e' registrada, nao corrigida (na planilha de
2026-11 ela nao passa de 0,5% em nenhum ano: e' arredondamento a quatro casas).

Uso:
    python src/etapa15_fator_sin.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coleta import comum_coleta as cc  # noqa: E402
from comum import config, energia, log  # noqa: E402

ETAPA = "etapa15_fator_sin"
FONTE = "mcti_fator"
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
         "Setembro", "Outubro", "Novembro", "Dezembro"]


def arquivo_atual() -> tuple[Path, dict]:
    manifesto = cc.ler_manifesto(FONTE)
    if not manifesto:
        raise FileNotFoundError("manifesto do MCTI vazio: rode src/coleta/mcti_fator.py")
    linha = max(manifesto.values(), key=lambda l: l["data_download"])
    return cc.caminho_do_original(FONTE, linha), linha


def ler_planilha(caminho: Path) -> pd.DataFrame:
    """Blocos de cinco linhas por ano: rotulo, ano, nomes dos meses, valores."""
    bruto = pd.read_excel(caminho, header=None, dtype=object)
    linhas = []
    for i in range(len(bruto)):
        ano = bruto.iat[i, 0]
        if not (isinstance(ano, (int, float)) and 2000 <= float(ano) <= 2100):
            continue
        ano = int(ano)
        nomes = [str(bruto.iat[i + 1, j]).strip() for j in range(2, 14)]
        if nomes != MESES:
            raise RuntimeError(f"bloco de {ano}: meses fora do lugar ({nomes})")
        anual = bruto.iat[i + 1, 14]
        for j in range(12):
            valor = bruto.iat[i + 2, 2 + j]
            if valor is None or (isinstance(valor, float) and pd.isna(valor)):
                continue
            linhas.append({"mes": f"{ano}-{j + 1:02d}", "ano": ano, "fator_tco2_mwh": float(valor),
                           "fator_anual_publicado_tco2_mwh":
                               None if anual is None or pd.isna(anual) else float(anual)})
    return pd.DataFrame(linhas)


def conferir(serie: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
    meses = pd.period_range(serie["mes"].min(), serie["mes"].max(), freq="M").strftime("%Y-%m")
    faltando = sorted(set(meses) - set(serie["mes"]))
    fora = serie[(serie["fator_tco2_mwh"] <= 0) | (serie["fator_tco2_mwh"] >= 1)]
    por_ano = serie.groupby("ano").agg(meses=("mes", "size"),
                                       media_simples=("fator_tco2_mwh", "mean"),
                                       anual_publicado=("fator_anual_publicado_tco2_mwh",
                                                        "first")).reset_index()
    completos = por_ano[por_ano["meses"] == 12].copy()
    completos["diferenca"] = completos["media_simples"] - completos["anual_publicado"]
    completos["diferenca_pct"] = 100 * completos["diferenca"] / completos["anual_publicado"]
    acima = completos[completos["diferenca_pct"].abs() > 1]
    linhas = [
        {"conferencia": f"meses faltando entre {serie['mes'].min()} e {serie['mes'].max()}",
         "casos": len(meses), "falhas": len(faltando),
         "observacao": ", ".join(faltando) or "nenhum"},
        {"conferencia": "fator fora de (0, 1) tCO2/MWh", "casos": len(serie),
         "falhas": len(fora), "observacao": ""},
        {"conferencia": "ano completo com fator anual publicado", "casos": len(completos),
         "falhas": int(completos["anual_publicado"].isna().sum()), "observacao": ""},
        {"conferencia": "media simples dos 12 meses contra o fator anual publicado: "
                        "diferenca acima de 1% (registrada, nao e' falha)",
         "casos": len(completos), "falhas": 0,
         "observacao": "; ".join(f"{int(r.ano)}: {r.diferenca_pct:+.1f}%"
                                 for r in acima.itertuples()) or "nenhuma"},
    ]
    return linhas, por_ano.merge(completos[["ano", "diferenca", "diferenca_pct"]], on="ano",
                                 how="left")


CAMPOS = [
    ("mes", "texto AAAA-MM", "Mes de referencia."),
    ("ano", "inteiro", "Ano de `mes`."),
    ("fator_tco2_mwh", "tCO2/MWh", "Fator medio mensal de emissao de CO2 da geracao do SIN, "
     "metodo para inventarios (media de todas as usinas em operacao, nao a margem)."),
    ("fator_anual_publicado_tco2_mwh", "tCO2/MWh", "Fator medio anual que a mesma planilha "
     "publica para o ano, repetido nos meses do ano; vazio no ano corrente, que o MCTI so' "
     "fecha em dezembro."),
    ("arquivo_fonte", "texto", "Planilha de origem em `dados/bruto/mcti_fator/`."),
]


def executar() -> int:
    logger = log.preparar(ETAPA)
    caminho, linha = arquivo_atual()
    if cc.sha256_arquivo(caminho) != linha["sha256"]:
        logger.error("%s: SHA-256 nao bate com o manifesto", caminho.name)
        return 1
    serie = ler_planilha(caminho)
    serie["arquivo_fonte"] = caminho.name
    conferencias, por_ano = conferir(serie)
    tabela = energia.gravar_validacao(config.FATOR_SIN_VALIDACAO, conferencias)
    if int(tabela["falhas"].sum()):
        logger.error("conferencias do fator do SIN com falha:\n%s", tabela.to_string())
        return 1
    serie.to_parquet(config.FATOR_SIN, index=False)
    energia.gravar_dicionario(
        config.FATOR_SIN_DICIONARIO, "Dicionario -- fator_emissao_sin_mensal",
        f"Uma linha por mes, {serie['mes'].min()} a {serie['mes'].max()} ({len(serie)} meses). "
        "Gravado pela etapa 15 a partir da planilha do MCTI guardada em "
        "`dados/bruto/mcti_fator/` com SHA-256. A serie comeca em 2006-01: antes disso o "
        "MCTI nao publica o fator medio, e a janela 2003-2005 fica vazia.",
        CAMPOS,
        ["E' o fator de **inventario** (media), nao o de margem de operacao nem o combinado do "
         "MDL, que estao na mesma pagina e medem outra coisa (a emissao deslocada na margem).",
         "A media simples dos doze meses bate com o fator anual publicado: diferenca maxima de "
         f"{por_ano['diferenca_pct'].abs().max():.2f}% entre os anos completos, compativel com "
         "o arredondamento a quatro casas (ano a ano em "
         "`saidas/fator_emissao_sin_anual_conferencia.csv`). O ano corrente nao tem anual.",
         "Desde janeiro de 2025 o MCTI calcula com a base ampliada do ONS (novas usinas); a "
         "metodologia nao mudou, mas a base sim (nota tecnica NT_FE_jun25 na pagina).",
         "A planilha e' revisada pelo MCTI (houve correcao de nov/2012, jan/2013 e mar/2013, "
         "avisada na pagina). O SHA-256 no manifesto diz de qual versao o dado saiu."],
        "MCTI, Fatores de emissao de CO2 da geracao de energia eletrica no SIN -- fator medio "
        f"(inventarios corporativos), `{caminho.name}`, URL e data no manifesto.")
    pd.DataFrame(por_ano).to_csv(config.DIR_SAIDAS / "fator_emissao_sin_anual_conferencia.csv",
                                 index=False)
    log.contagem(logger, meses=len(serie), anos=serie["ano"].nunique())
    logger.info("gravado %s", log.caminho_relativo(config.FATOR_SIN))
    return 0


if __name__ == "__main__":
    raise SystemExit(executar())
