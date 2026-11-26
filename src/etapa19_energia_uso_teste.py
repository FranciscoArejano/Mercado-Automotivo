#!/usr/bin/env python3
"""Etapa 19 -- uso-teste das bases de energia, frota e emissoes (rodada 13, sec.3).

So' tabelas descritivas, sem regressao: mostram se as bases conversam entre si e
com o painel. Grava `saidas/uso_teste_energia_*.csv`:

1. `frota_vendas` -- Brasil, ano a ano desde 2012: frota eletrica e hibrida da
   Senatran (dezembro; todos os tipos de veiculo, porque a fonte nao cruza tipo com
   combustivel), vendas acumuladas de eletrificados (piso e teto da banda de
   `saidas/eletrificacao_banda.csv` aplicados ao total anual do painel, e a serie
   da ABVE) e a razao frota / vendas acumuladas;
2. `paridade` -- por UF e ano, a fracao dos meses com paridade etanol/gasolina
   abaixo de 0,7; e `paridade_resumo`, a fracao na janela inteira;
3. `uf_2025` -- por UF em 2025: potencia de GD solar residencial por mil habitantes
   (vazia: a ANEEL nao abriu), frota eletrica por mil habitantes (dez/2025), preco
   real medio da gasolina no ano e tarifa de energia (vazia: idem). Populacao: IBGE,
   SIDRA tabela 6579 (estimativa de 2025), em `dados/bruto/ibge/`;
4. `emissoes_transporte` -- participacao do transporte rodoviario nas emissoes
   brutas (CO2e GWP-AR5, tipo Emissão) de cada UF em 2005, 2015 e no ultimo ano do
   SEEG.

Uso:
    python src/etapa19_energia_uso_teste.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, energia, log  # noqa: E402

ETAPA = "etapa19_energia_uso_teste"
ELETRICO = ("eletrico",)
HIBRIDO = ("hibrido", "hibrido_plug_in")
LIMIAR_PARIDADE = 0.7
QUASE_SEMPRE = 0.9


def saida(nome: str) -> Path:
    return config.DIR_SAIDAS / f"uso_teste_energia_{nome}.csv"


def frota_contra_vendas() -> pd.DataFrame:
    frota = pd.read_parquet(config.FROTA_MUNICIPAL, columns=["mes", "recorte", "combustivel",
                                                             "veiculos"],
                            filters=[("recorte", "==", "combustivel")])
    dez = frota[frota["mes"].str.endswith("-12")].copy()
    dez["ano"] = dez["mes"].str[:4].astype(int)
    largo = dez.groupby(["ano", "combustivel"])["veiculos"].sum().unstack(fill_value=0)
    anos = pd.Index(range(2012, 2026), name="ano")
    tabela = pd.DataFrame(index=anos)
    tabela["frota_eletrica"] = largo.reindex(anos)[list(ELETRICO)].sum(axis=1, min_count=1)
    tabela["frota_eletrico_fonte_interna"] = largo.reindex(anos).get("eletrico_fonte_interna")
    tabela["frota_hibrida"] = largo.reindex(anos)[[c for c in HIBRIDO if c in largo]].sum(
        axis=1, min_count=1)
    tabela["frota_eletrificada"] = tabela[["frota_eletrica", "frota_hibrida"]].sum(
        axis=1, min_count=2)
    painel = pd.read_parquet(config.PAINEL, columns=["mes_ref", "unidades"])
    vendas = painel.groupby(painel["mes_ref"].str[:4].astype(int))["unidades"].sum()
    banda = pd.read_csv(config.ELETRIFICACAO_BANDA)
    banda = banda[banda["leitura"] == "longa"].set_index("ano")
    for coluna in ("piso", "teto"):
        anual = (banda[coluna] / 100 * vendas.reindex(banda.index)).reindex(anos)
        tabela[f"vendas_ano_{coluna}_banda"] = anual
        tabela[f"vendas_acum_{coluna}_banda"] = anual.cumsum()
    abve = pd.read_csv(config.DIR_DADOS / "referencia" / "abve_serie_anual.csv").set_index("ano")
    tabela["vendas_ano_abve"] = abve["eletrificados_leves"].reindex(anos)
    tabela["vendas_acum_abve"] = tabela["vendas_ano_abve"].cumsum()
    tabela["razao_frota_acum_teto_banda"] = (tabela["frota_eletrificada"]
                                             / tabela["vendas_acum_teto_banda"])
    tabela["razao_frota_acum_abve"] = tabela["frota_eletrificada"] / tabela["vendas_acum_abve"]
    tabela["frota_acima_do_teto"] = tabela["frota_eletrificada"] > tabela["vendas_acum_teto_banda"]
    tabela["frota_acima_da_abve"] = tabela["frota_eletrificada"] > tabela["vendas_acum_abve"]
    tabela["nota"] = ""
    tabela.loc[tabela.index < 2013, "nota"] = "sem combustivel na Senatran antes de 2013-12"
    tabela.loc[tabela.index < 2015, "nota"] += "; banda comeca em 2015"
    tabela.loc[tabela.index < 2016, "nota"] += "; ABVE registrada desde 2016"
    tabela["nota"] = tabela["nota"].str.strip("; ")
    return tabela.reset_index()


def paridade() -> tuple[pd.DataFrame, pd.DataFrame]:
    precos = pd.read_parquet(config.PRECOS_COMBUSTIVEIS,
                             columns=["mes", "uf", "produto", "paridade_etanol_gasolina"])
    p = precos[precos["produto"] == "gasolina_comum"].dropna(subset=["paridade_etanol_gasolina"])
    p = p.assign(ano=p["mes"].str[:4].astype(int),
                 abaixo=p["paridade_etanol_gasolina"] < LIMIAR_PARIDADE)
    por_ano = p.groupby(["uf", "ano"]).agg(meses=("mes", "size"),
                                           meses_abaixo_0_7=("abaixo", "sum")).reset_index()
    por_ano["fracao_abaixo_0_7"] = por_ano["meses_abaixo_0_7"] / por_ano["meses"]
    resumo = p.groupby("uf").agg(meses=("mes", "size"), meses_abaixo_0_7=("abaixo", "sum"),
                                 paridade_mediana=("paridade_etanol_gasolina", "median"),
                                 primeiro_mes=("mes", "min"), ultimo_mes=("mes", "max"))
    resumo["fracao_abaixo_0_7"] = resumo["meses_abaixo_0_7"] / resumo["meses"]
    resumo["etanol_quase_sempre_vantajoso"] = resumo["fracao_abaixo_0_7"] >= QUASE_SEMPRE
    return por_ano, resumo.sort_values("fracao_abaixo_0_7", ascending=False).reset_index()


def populacao() -> pd.Series:
    dados = json.loads(config.POPULACAO_IBGE.read_bytes())[1:]
    return pd.Series({energia.sigla_da_uf(d["D1N"]): int(d["V"]) for d in dados},
                     name="populacao_2025")


def uf_2025() -> pd.DataFrame:
    frota = pd.read_parquet(config.FROTA_MUNICIPAL, filters=[("mes", "==", "2025-12"),
                                                             ("recorte", "==", "combustivel")])
    eletrica = frota[frota["combustivel"].isin(ELETRICO)].groupby("uf")["veiculos"].sum()
    precos = pd.read_parquet(config.PRECOS_COMBUSTIVEIS)
    gasolina = precos[(precos["produto"] == "gasolina_comum") & precos["mes"].str.startswith(
        "2025")].groupby("uf").agg(preco_real_gasolina_2025=("preco_real", "mean"),
                                   meses_com_preco=("mes", "size"))
    tabela = pd.concat([populacao(), eletrica.rename("frota_eletrica_dez_2025"), gasolina],
                       axis=1)
    tabela.index.name = "uf"
    tabela["gd_solar_residencial_kw_por_mil_hab"] = pd.NA
    tabela["frota_eletrica_por_mil_hab"] = 1000 * tabela["frota_eletrica_dez_2025"] / tabela[
        "populacao_2025"]
    tabela["tarifa_b1_r_kwh"] = pd.NA
    tabela["base_preco_real"] = config.IPCA_BASE_PRECOS
    tabela["nota"] = ("GD e tarifa vazias: ANEEL bloqueada nesta rodada; ordenado pela frota "
                      "eletrica por mil habitantes, nao pela potencia solar")
    tabela["fonte_populacao"] = "IBGE, SIDRA tabela 6579, variavel 9324, 2025"
    return tabela.sort_values("frota_eletrica_por_mil_hab", ascending=False).reset_index()


def emissoes_transporte() -> pd.DataFrame:
    e = pd.read_parquet(config.EMISSOES_UF_ANUAL)
    e = e[(e["tipo"] == "Emissão") & (e["gas"] == "CO2e_GWP_AR5")]
    ultimo = int(e["ano"].max())
    e = e[e["ano"].isin([2005, 2015, ultimo])].copy()
    e["uf"] = e["uf"].fillna("nao_alocado")
    total = e.groupby(["uf", "ano"])["valor"].sum()
    rod = e[e["subcategoria"] == "Rodoviário"].groupby(["uf", "ano"])["valor"].sum()
    brasil_total = e.groupby("ano")["valor"].sum()
    brasil_rod = e[e["subcategoria"] == "Rodoviário"].groupby("ano")["valor"].sum()
    t = pd.DataFrame({"emissoes_total_t_co2e": total, "rodoviario_t_co2e": rod}).fillna(0)
    t["participacao_rodoviario_pct"] = 100 * t["rodoviario_t_co2e"] / t["emissoes_total_t_co2e"]
    largo = t["participacao_rodoviario_pct"].unstack("ano")
    largo.columns = [f"pct_{c}" for c in largo.columns]
    br = (100 * brasil_rod / brasil_total).to_frame().T
    br.columns = [f"pct_{c}" for c in br.columns]
    br.index = ["BR"]
    saida_ = pd.concat([largo, br])
    saida_.index.name = "uf"
    saida_["colecao_seeg"] = pd.read_parquet(config.EMISSOES_UF_ANUAL,
                                             columns=["colecao_seeg"])["colecao_seeg"].iloc[0]
    saida_["metrica"] = "CO2e GWP-AR5, emissoes brutas (tipo Emissão)"
    return saida_.reset_index()


def executar() -> int:
    logger = log.preparar(ETAPA)
    frota_contra_vendas().to_csv(saida("frota_vendas"), index=False)
    por_ano, resumo = paridade()
    por_ano.to_csv(saida("paridade"), index=False)
    resumo.to_csv(saida("paridade_resumo"), index=False)
    uf_2025().to_csv(saida("uf_2025"), index=False)
    emissoes_transporte().to_csv(saida("emissoes_transporte"), index=False)
    logger.info("gravados saidas/uso_teste_energia_*.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(executar())
