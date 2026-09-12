#!/usr/bin/env python3
"""Etapa 6 -- relatorio de validacao (ESPEC.md sec.6).

Gera saidas/validacao.md a cada execucao. O invariante central falha a
execucao; o resto e' medido e reportado.

Uso:
    python src/etapa06_validacao.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import ciclo_vida, config, grupos, log, meses as mod_meses, periodo  # noqa: E402

ETAPA = "etapa06_validacao"

# Numeros da planilha de controle (ESPEC.md sec.7), em unidades.
REFERENCIA_SEC7 = {
    2014: {"total": 3_325_627, "modelos": 310, "hhi_marca": 1_297},
    2016: {"total": 1_986_502, "modelos": 301, "hhi_marca": 1_055},
    2020: {"total": 1_949_892, "modelos": 299, "hhi_marca": 1_146},
    2022: {"total": 1_952_794, "modelos": 270, "hhi_marca": 1_208},
}


def _tabela(quadro: pd.DataFrame, maximo: int | None = None) -> str:
    if quadro.empty:
        return "_(vazio)_\n"
    recorte = quadro if maximo is None else quadro.head(maximo)
    texto = recorte.to_markdown(index=False)
    if maximo is not None and len(quadro) > maximo:
        texto += f"\n\n_({len(quadro) - maximo} linhas restantes omitidas; ver CSV correspondente.)_"
    return texto + "\n"


def _hhi(bloco: pd.DataFrame, chave: str) -> float:
    total = bloco["unidades"].sum()
    if total <= 0:
        return float("nan")
    partes = bloco.groupby(chave)["unidades"].sum() / total
    return float((partes.pow(2).sum()) * 10_000)


def _coerencia_entre_meses(meses_uteis: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Usa a redundancia da propria fonte para conferir a leitura.

    Cada linha das tabelas de sub-segmento traz tres numeros: o mes anterior, o
    mes de referencia e o acumulado do ano. Isso da' duas identidades que tem de
    valer sem que nenhuma delas dependa da nossa interpretacao:

    - `unidades_mes_anterior(M)` = `unidades_mes(M-1)`;
    - `acumulado(M) - acumulado(M-1)` = `unidades_mes(M)`, dentro do mesmo ano
      (em janeiro, `acumulado` = `unidades_mes`).

    Divergencia aqui e' erro de leitura de coluna ou inconsistencia da fonte --
    nos dois casos, coisa para reportar.
    """
    arquivos = sorted(config.DIR_EXTRACAO.glob("*.csv"))
    if not arquivos:
        return pd.DataFrame(), pd.DataFrame()
    bruto = pd.concat(
        [pd.read_csv(a, dtype=str, keep_default_na=False) for a in arquivos], ignore_index=True
    )
    bruto = bruto[bruto["origem_tabela"] == "sub_segmento"]
    if bruto.empty:
        return pd.DataFrame(), pd.DataFrame()
    for coluna in ("unidades_mes", "unidades_mes_anterior", "unidades_acumulado"):
        bruto[coluna] = pd.to_numeric(bruto[coluna], errors="coerce")
    chave = ["mes", "segmento", "nome_completo_fonte"]
    dados = bruto.groupby(chave, as_index=False)[
        ["unidades_mes", "unidades_mes_anterior", "unidades_acumulado"]
    ].sum()

    dados["mes_anterior"] = dados["mes"].map(
        lambda m: periodo.de_indice(periodo.para_indice(m) - 1)
    )
    anterior = dados[["mes", "segmento", "nome_completo_fonte", "unidades_mes",
                      "unidades_acumulado"]].rename(columns={
        "mes": "mes_anterior", "unidades_mes": "mes_anterior_observado",
        "unidades_acumulado": "acumulado_anterior",
    })
    junto = dados.merge(anterior, on=["mes_anterior", "segmento", "nome_completo_fonte"],
                        how="left")
    # So' faz sentido comparar quando os dois meses foram extraidos.
    junto = junto[junto["mes_anterior"].isin(meses_uteis) & junto["mes"].isin(meses_uteis)]

    coluna = junto[junto["mes_anterior_observado"].notna()].copy()
    coluna["diferenca"] = coluna["unidades_mes_anterior"] - coluna["mes_anterior_observado"]
    coluna = coluna[coluna["diferenca"] != 0][
        ["mes", "segmento", "nome_completo_fonte", "unidades_mes_anterior",
         "mes_anterior_observado", "diferenca"]
    ].sort_values("diferenca", key=abs, ascending=False)

    janeiro = junto["mes"].str.endswith("-01")
    acumulado = junto.copy()
    acumulado["acumulado_esperado"] = acumulado["unidades_mes"] + acumulado[
        "acumulado_anterior"
    ].where(~janeiro, 0.0)
    acumulado = acumulado[acumulado["acumulado_esperado"].notna()]
    acumulado["diferenca"] = acumulado["unidades_acumulado"] - acumulado["acumulado_esperado"]
    acumulado = acumulado[acumulado["diferenca"] != 0][
        ["mes", "segmento", "nome_completo_fonte", "unidades_acumulado",
         "acumulado_esperado", "diferenca"]
    ].sort_values("diferenca", key=abs, ascending=False)
    return coluna, acumulado


def _ciclos(painel: pd.DataFrame, meses: list[str], limiar: float) -> pd.DataFrame:
    largo = ciclo_vida.grade(painel, ["marca", "modelo", "segmento"], meses, mod_meses.uteis())
    primeiro, ultimo = meses[0], meses[-1]
    registros = []
    for chave, serie in largo.iterrows():
        ciclo = ciclo_vida.calcular(
            serie, limiar, primeiro, ultimo,
            janela=config.JANELA_PICO_MESES, modo=config.PICO_MOVEL_MODO,
        )
        if ciclo.entrada is None:
            continue
        registros.append({
            "marca": chave[0], "modelo": chave[1], "segmento": chave[2],
            "entrada": ciclo.entrada, "saida": ciclo.saida, "pico": ciclo.pico,
            "unidades_totais": ciclo.unidades_totais,
            "censura_esquerda": ciclo.censura_esquerda,
            "censura_direita": ciclo.censura_direita,
        })
    return pd.DataFrame(registros)


def _taxas(ciclos: pd.DataFrame, painel: pd.DataFrame, limiar: float) -> pd.DataFrame:
    ativos = (
        painel[painel["unidades"] > 0]
        .groupby("ano")[["marca", "modelo", "segmento"]]
        .apply(lambda b: b.drop_duplicates().shape[0])
        .rename("ativos")
    )
    entradas = (
        ciclos[~ciclos["censura_esquerda"]]
        .assign(ano=lambda q: q["entrada"].str.slice(0, 4).astype(int))
        .groupby("ano").size().rename("entradas")
    )
    saidas = (
        ciclos[~ciclos["censura_direita"]]
        .assign(ano=lambda q: q["saida"].str.slice(0, 4).astype(int))
        .groupby("ano").size().rename("saidas")
    )
    tabela = pd.concat([ativos, entradas, saidas], axis=1).fillna(0).astype(int)
    tabela[f"taxa_entrada_{limiar:.0%}"] = (tabela["entradas"] / tabela["ativos"]).round(4)
    tabela[f"taxa_saida_{limiar:.0%}"] = (tabela["saidas"] / tabela["ativos"]).round(4)
    return tabela.rename(columns={
        "entradas": f"entradas_{limiar:.0%}", "saidas": f"saidas_{limiar:.0%}",
    })


def executar() -> int:
    logger = log.preparar(ETAPA)
    for exigido in (config.PAINEL_BRUTO, config.PAINEL):
        if not exigido.exists():
            raise log.ErroDeParsing(
                f"{log.caminho_relativo(exigido)} nao existe -- rode as etapas anteriores."
            )
    bruto = pd.read_parquet(config.PAINEL_BRUTO)
    painel = pd.read_parquet(config.PAINEL)
    meses = sorted(painel["mes_ref"].unique())
    partes: list[str] = []
    falhas: list[str] = []

    partes.append(
        "# Validacao do painel de vendas de veiculos 0 km\n\n"
        f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='seconds')} "
        f"(UTC) por `src/{ETAPA}.py`.\n\n"
        f"- Periodo do painel: **{meses[0]} a {meses[-1]}** ({len(meses)} meses)\n"
        f"- Linhas: painel bruto {len(bruto):,} / painel {len(painel):,}\n"
        f"- Unidades: {int(painel['unidades'].sum()):,}\n"
        f"- Modelos (marca x modelo x segmento): "
        f"{painel[['marca', 'modelo', 'segmento']].drop_duplicates().shape[0]:,}\n"
        f"- Leitura de \"pico movel de 12 meses\" em uso: `{config.PICO_MOVEL_MODO}` "
        "(ver QUESTOES_ABERTAS.md, Q1)\n"
    )

    # ------------------------------------------------------ invariante central
    antes = bruto.groupby("mes_ref")["unidades"].sum()
    depois = painel.groupby("mes_ref")["unidades"].sum()
    invariante = pd.DataFrame({"painel_bruto": antes, "painel": depois}).fillna(0)
    invariante["diferenca"] = invariante["painel"] - invariante["painel_bruto"]
    quebras = invariante[invariante["diferenca"] != 0]
    partes.append("\n## 1. Invariante central\n\n"
                  "A soma de unidades por mes tem de ser identica nos dois paineis. "
                  "Harmonizacao redistribui rotulos; nao cria nem destroi unidades.\n\n")
    if quebras.empty:
        partes.append(f"**OK** -- identica nos {len(invariante)} meses.\n")
    else:
        falhas.append(f"invariante central quebrado em {len(quebras)} meses")
        partes.append("**FALHOU**\n\n" + _tabela(quebras.reset_index(), 20))

    # -------------------------------------------------- sanidade temporal
    mensal = painel.groupby("mes_ref")["unidades"].sum()
    partes.append("\n## 2. Sanidade temporal\n\n"
                  "Dois fatos conhecidos do mercado brasileiro. Se falharem, a atribuicao "
                  "de mes esta' errada -- provavelmente por leitura de cabecalho (sec.7).\n\n")

    faixa = [m for m in meses if "2014-01" <= m <= "2023-12"]
    if faixa:
        menor = mensal.loc[faixa].idxmin()
        ok = menor == "2020-04"
        partes.append(f"- Menor mes de 2014-2023: **{menor}** "
                      f"({int(mensal.loc[menor]):,} unidades) -- esperado `2020-04`: "
                      f"{'OK' if ok else 'FALHOU'}\n")
        if not ok:
            falhas.append(f"menor mes de 2014-2023 e' {menor}, nao 2020-04")
    desde = [m for m in meses if m >= "2019-01"]
    if desde:
        maior = mensal.loc[desde].idxmax()
        ok = maior == "2023-07"
        partes.append(f"- Maior mes desde 2019: **{maior}** "
                      f"({int(mensal.loc[maior]):,} unidades) -- esperado `2023-07`: "
                      f"{'OK' if ok else 'FALHOU'}\n")
        if not ok:
            falhas.append(f"maior mes desde 2019 e' {maior}, nao 2023-07")

    # --------------------------------------------------------- cobertura (D5)
    partes.append("\n## 3. Cobertura da fonte (D5)\n\n"
                  "Total do painel contra o total que o proprio informe publica, mes a mes. "
                  "E' este confronto que fecha D5. A diferenca e' estrutural, nao erro de "
                  "leitura: as tabelas por modelo da fonte tem numero fixo de linhas por "
                  "sub-segmento e truncam a cauda (ver QUESTOES_ABERTAS.md, Q2).\n\n")
    caminho_totais = config.DIR_PROCESSADO / "extracao_totais.csv"
    if caminho_totais.exists():
        totais = pd.read_csv(caminho_totais)
        totais = totais[totais["total_publicado"].notna()]
        painel_seg = (
            painel.groupby(["mes_ref", "segmento"], as_index=False)["unidades"].sum()
            .rename(columns={"mes_ref": "mes", "unidades": "total_painel"})
        )
        cobertura = totais.merge(painel_seg, on=["mes", "segmento"], how="outer")
        cobertura["diferenca"] = cobertura["total_painel"] - cobertura["total_publicado"]
        cobertura["cobertura_pct"] = (
            100 * cobertura["total_painel"] / cobertura["total_publicado"]
        ).round(3)
        cobertura["diferenca_pct"] = (100 - cobertura["cobertura_pct"]).round(3)
        cobertura.sort_values(["mes", "segmento"]).to_csv(config.COBERTURA, index=False)

        resumo = (
            cobertura.groupby("segmento")["cobertura_pct"]
            .agg(["min", "mean", "median", "max"]).round(2).reset_index()
        )
        por_ano = cobertura.assign(ano=cobertura["mes"].str.slice(0, 4).astype(int))
        por_ano = (
            por_ano.groupby(["ano", "segmento"], as_index=False)
            .agg(total_painel=("total_painel", "sum"), total_publicado=("total_publicado", "sum"))
        )
        por_ano["cobertura_pct"] = (
            100 * por_ano["total_painel"] / por_ano["total_publicado"]
        ).round(2)
        partes.append("Resumo por segmento (percentual do total publicado que o painel cobre):\n\n")
        partes.append(_tabela(resumo))
        partes.append("\nPor ano:\n\n")
        partes.append(_tabela(por_ano))
        partes.append(f"\nTabela mes a mes completa em `{log.caminho_relativo(config.COBERTURA)}`.\n")
    else:
        partes.append("_Totais publicados nao disponiveis: rode a etapa 02._\n")

    # ---------------------------------------------- corte de publicacao
    partes.append("\n## 4. Corte de publicacao por mes\n\n"
                  "Menor valor que a fonte lista em cada mes. Um modelo ausente do painel "
                  "naquele mes esta' abaixo deste corte -- e' o que limita a leitura de "
                  "\"zero\" nas series (ver dicionario de dados).\n\n")
    corte = (
        painel[painel["unidades"] > 0].groupby(["ano", "segmento"], as_index=False)["unidades"]
        .agg(corte_min="min", corte_mediano="median")
    )
    partes.append(_tabela(corte))

    # ------------------------------------------------- contagem de modelos
    partes.append("\n## 5. Contagem de modelos por ano\n\n"
                  "A fonte nao publica uma contagem de modelos, entao nao ha' numero do "
                  "informe para confrontar diretamente: a contagem abaixo e' a do painel, "
                  "que por construcao e' a dos modelos listados nos informes. A coluna de "
                  "referencia vem da planilha de controle da sec.7, que **nao e' fonte**.\n\n")
    contagem = (
        painel[painel["unidades"] > 0]
        .groupby("ano")
        .apply(lambda b: pd.Series({
            "modelos": b[["marca", "modelo", "segmento"]].drop_duplicates().shape[0],
            "marcas": b["marca"].nunique(),
            "unidades": int(b["unidades"].sum()),
            "hhi_marca": round(_hhi(b, "marca"), 1),
            "hhi_grupo": round(_hhi(b, "grupo_economico"), 1),
        }), include_groups=False)
        .reset_index()
    )
    contagem["ref_modelos_sec7"] = contagem["ano"].map(
        lambda a: REFERENCIA_SEC7.get(a, {}).get("modelos"))
    contagem["ref_total_sec7"] = contagem["ano"].map(
        lambda a: REFERENCIA_SEC7.get(a, {}).get("total"))
    contagem["ref_hhi_sec7"] = contagem["ano"].map(
        lambda a: REFERENCIA_SEC7.get(a, {}).get("hhi_marca"))
    partes.append(_tabela(contagem))

    # ----------------------------------------------------------- ausencias
    partes.append("\n## 6. Ausencias\n\n")
    negativos = painel[painel["unidades"] < 0]
    partes.append(f"- Linhas com unidades negativas: **{len(negativos)}** "
                  f"({'OK' if negativos.empty else 'FALHOU'})\n")
    if not negativos.empty:
        falhas.append(f"{len(negativos)} linhas com unidades negativas")
    soma_modelo = painel.groupby(["marca", "modelo", "segmento"])["unidades"].sum()
    nulos = soma_modelo[soma_modelo == 0]
    partes.append(f"- Modelos com serie integralmente nula: **{len(nulos)}** "
                  f"({'OK' if nulos.empty else 'revisar'})\n")
    nao_resolvidos = bruto[bruto["metodo_separacao"] == "nao_resolvido"]
    partes.append(f"- Nomes sem marca resolvida: **{len(nao_resolvidos)}** linhas\n")
    fora_da_lista = bruto[~bruto["marca_conhecida"]]["marca_fonte"].dropna().unique()
    partes.append(f"- Marcas fora de `config/marcas.csv`: **{len(fora_da_lista)}** "
                  f"(ver `saidas/marcas_nao_mapeadas.csv`)\n")
    sem_grupo = painel[painel["grupo_economico"] == grupos.NAO_MAPEADO]
    partes.append(
        f"- Linhas sem grupo economico vigente (D4): **{len(sem_grupo)}** "
        f"({int(sem_grupo['unidades'].sum()):,} unidades, "
        f"{100 * sem_grupo['unidades'].sum() / painel['unidades'].sum():.2f}% do total)\n"
    )
    if not sem_grupo.empty:
        pendentes = (
            sem_grupo.groupby("marca", as_index=False)["unidades"].sum()
            .sort_values("unidades", ascending=False)
        )
        pendentes.to_csv(config.DIR_SAIDAS / "grupos_nao_mapeados.csv", index=False)
        partes.append("\n" + _tabela(pendentes, 25))

    partes.append("\n### Lacunas de mes\n\n")
    if config.LACUNAS.exists():
        lacunas = pd.read_csv(config.LACUNAS)
        partes.append(f"{len(lacunas)} lacunas registradas.\n\n" + _tabela(lacunas, 40))
    else:
        partes.append("_Arquivo `dados/bruto/lacunas.csv` ausente._\n")

    esperados = periodo.intervalo(meses[0], meses[-1])
    faltantes = [m for m in esperados if m not in set(meses)]
    partes.append(f"\nMeses do intervalo sem nenhuma linha no painel: **{len(faltantes)}**"
                  + (f" ({', '.join(faltantes)})" if faltantes else "") + "\n")

    # ----------------------------------------- taxas de entrada e saida (D3)
    partes.append("\n## 7. Taxas de entrada e saida por ano (D3)\n\n"
                  "Tres limiares lado a lado, como manda a sec.6. Modelos censurados "
                  "(vivos no primeiro mes da amostra, ou ainda vivos no ultimo) ficam fora "
                  "da contagem de entrada e de saida respectivamente.\n\n")
    tabelas = []
    for limiar in config.LIMIARES_SAIDA:
        ciclos = _ciclos(painel[painel["conta_entrada_saida"]], meses, limiar)
        tabelas.append(_taxas(ciclos, painel, limiar))
    juntas = pd.concat(
        [tabelas[0][["ativos"]]] + [t.drop(columns=["ativos"]) for t in tabelas], axis=1
    ).reset_index()
    partes.append(_tabela(juntas))

    colunas_saida = [f"taxa_saida_{l:.0%}" for l in config.LIMIARES_SAIDA]
    ordens = {c: juntas.set_index("ano")[c].rank(ascending=False, method="min") for c in colunas_saida}
    ordenacao = pd.DataFrame(ordens)
    instaveis = ordenacao[ordenacao.nunique(axis=1) > 1]
    partes.append("\n### Estabilidade da ordenacao entre limiares\n\n")
    if instaveis.empty:
        partes.append("A ordenacao dos anos por taxa de saida e' **identica** nos tres limiares.\n")
    else:
        partes.append(
            f"**Achado metodologico:** {len(instaveis)} de {len(ordenacao)} anos mudam de "
            "posicao no ranking de taxa de saida conforme o limiar. A escolha do limiar "
            "nao e' inocua para esses anos.\n\n" + _tabela(instaveis.reset_index())
        )

    # -------------------------------------------- coerencia entre meses
    partes.append("\n## 8. Coerencia entre meses\n\n"
                  "Cada linha da fonte traz o mes anterior, o mes de referencia e o "
                  "acumulado do ano. Duas identidades tem de valer sem depender de "
                  "interpretacao nossa: a coluna de mes anterior de M tem de repetir o mes "
                  "de M-1, e a diferenca de acumulados tem de dar o mes. E' a conferencia "
                  "que independe de cabecalho.\n\n")
    coluna_anterior, acumulados = _coerencia_entre_meses(mod_meses.uteis())
    if coluna_anterior.empty and acumulados.empty:
        partes.append("_Sem dados de extracao para conferir._\n")
    else:
        pares_comparados = len(pd.concat([coluna_anterior, acumulados])) if not (
            coluna_anterior.empty and acumulados.empty) else 0
        coluna_anterior.to_csv(config.DIR_SAIDAS / "coerencia_mes_anterior.csv", index=False)
        acumulados.to_csv(config.DIR_SAIDAS / "coerencia_acumulado.csv", index=False)
        partes.append(
            f"- Coluna de mes anterior divergente do mes observado: **{len(coluna_anterior)}** "
            "pares (mes x modelo)\n"
            f"- Acumulado divergente da soma do mes com o acumulado anterior: "
            f"**{len(acumulados)}** pares\n\n"
            f"_({pares_comparados} divergencias no total; listas completas em "
            "`saidas/coerencia_mes_anterior.csv` e `saidas/coerencia_acumulado.csv`.)_\n\n"
        )
        partes.append("Maiores divergencias na coluna de mes anterior:\n\n")
        partes.append(_tabela(coluna_anterior, 15))
        partes.append("\nMaiores divergencias de acumulado:\n\n")
        partes.append(_tabela(acumulados, 15))

    # ------------------------------------------------ divergencias da fonte
    partes.append("\n## 9. Divergencias internas da fonte\n\n"
                  "Modelos em que o ranking mensal e a tabela de sub-segmento do **mesmo** "
                  "informe trazem numeros diferentes. Sao inconsistencias da fonte, "
                  "reportadas e mantidas (sec.9.4); o painel usa o valor da tabela de "
                  "sub-segmento.\n\n")
    caminho_div = config.DIR_SAIDAS / "divergencias_fonte.csv"
    if caminho_div.exists():
        divergencias = pd.read_csv(caminho_div)
        partes.append(f"{len(divergencias)} divergencias.\n\n" + _tabela(divergencias, 25))
    else:
        partes.append("_Nao disponivel._\n")

    # -------------------------------------------------------------- fecho
    partes.append("\n## 10. Situacao\n\n")
    if falhas:
        partes.append("**Validacao FALHOU:**\n\n" + "".join(f"- {f}\n" for f in falhas))
    else:
        partes.append("Todas as verificacoes obrigatorias passaram.\n")

    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    config.VALIDACAO.write_text("".join(partes), encoding="utf-8")
    logger.info("gravado %s", log.caminho_relativo(config.VALIDACAO))
    log.contagem(logger, linhas_painel=len(painel), meses=len(meses), falhas=len(falhas))
    if falhas:
        for falha in falhas:
            logger.error("validacao: %s", falha)
        return 1
    return 0


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    return executar()


if __name__ == "__main__":
    raise SystemExit(main())
