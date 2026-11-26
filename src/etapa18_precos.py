#!/usr/bin/env python3
"""Etapa 18 -- precos de combustiveis por UF e por municipio (ANP).

Le a serie historica por posto do Levantamento de Precos da ANP, guardada em
`dados/bruto/anp_precos/` (original de ate' 50 MB, ou bruto reduzido em parquet,
SHA-256 no manifesto; baixada por `src/coleta/anp_precos.py`), e grava:

- `dados/processado/precos_combustiveis_mensal.parquet` -- UF x mes x produto
  (gasolina comum, etanol hidratado, diesel S10, GNV): preco medio de revenda
  nominal (media simples das coletas do mes), preco real (deflacionado pelo IPCA
  de `macro_mensal`, em R$ do mes-base), numero de coletas e de postos
  pesquisados (CNPJ distintos), e a paridade etanol/gasolina da UF no mes;
- `dados/processado/precos_combustiveis_municipal_mensal.parquet` -- o mesmo por
  municipio (codigo IBGE de 7 digitos);
- `saidas/precos_combustiveis_validacao.csv` e
  `saidas/precos_combustiveis_conferencia_sintese.csv` -- a media calculada contra a
  sintese mensal por estado que a propria ANP publica, com as diferencas acima de 1%;
- `saidas/precos_combustiveis_mensal_dicionario.md`.

A serie por posto comeca em 2004-01; a sintese da ANP, em 2001-07. O produto sai
da serie por posto (e' o bruto que se reproduz) e comeca em 2004-01; 2003 fica
vazio. A sintese entra so' na conferencia.

Uso:
    python src/etapa18_precos.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coleta import anp_precos  # noqa: E402
from coleta import comum_coleta as cc  # noqa: E402
from comum import config, energia, log  # noqa: E402

ETAPA = "etapa18_precos"
FONTE = anp_precos.FONTE
PRODUTOS = {"GASOLINA": "gasolina_comum", "ETANOL": "etanol_hidratado",
            "DIESEL S10": "diesel_s10", "GNV": "gnv"}
PRODUTOS_SINTESE = {"GASOLINA COMUM": "gasolina_comum", "ETANOL HIDRATADO": "etanol_hidratado",
                    "OLEO DIESEL S10": "diesel_s10", "GNV": "gnv"}
TOLERANCIA_SINTESE = 0.01


def tabelas_por_posto():
    """(chave do manifesto, quadro) de cada arquivo por posto, do original ou do reduzido."""
    manifesto = cc.ler_manifesto(FONTE)
    for chave, linha in sorted(manifesto.items()):
        if not linha["observacao"].startswith("posto"):
            continue
        if linha["no_git"] == "sim":
            caminho = cc.caminho_do_original(FONTE, linha)
            if cc.sha256_arquivo(caminho) != linha["sha256"]:
                raise RuntimeError(f"{chave}: SHA-256 do original nao bate")
            tabela = anp_precos.ler_posto(caminho)
        else:
            caminho = cc.dir_fonte(FONTE) / linha["reduzido"]
            if cc.sha256_arquivo(caminho) != linha["sha256_reduzido"]:
                raise RuntimeError(f"{chave}: SHA-256 do reduzido nao bate")
            tabela = pd.read_parquet(caminho)
            yield chave, tabela
            continue
        yield chave, tabela.to_pandas()


def preparar(quadro: pd.DataFrame, chave: str) -> pd.DataFrame:
    data = pd.to_datetime(quadro["Data da Coleta"], format="%d/%m/%Y")
    preco = pd.to_numeric(quadro["Valor de Venda"].str.replace(",", ".", regex=False))
    return pd.DataFrame({
        "mes": data.dt.strftime("%Y-%m"), "uf": quadro["Estado - Sigla"].str.strip(),
        "municipio_fonte": quadro["Municipio"].str.strip(),
        "cnpj": quadro["CNPJ da Revenda"].str.strip(),
        "produto": quadro["Produto"].map(PRODUTOS), "preco": preco,
        "unidade_fonte": quadro["Unidade de Medida"].str.strip(), "arquivo_fonte": chave})


def agregar(coletas: pd.DataFrame, chave: list[str]) -> pd.DataFrame:
    return coletas.groupby(chave, as_index=False).agg(
        soma=("preco", "sum"), coletas=("preco", "size"), postos=("cnpj", "nunique"),
        unidade=("unidade_fonte", lambda s: " | ".join(sorted(set(s)))),
        arquivo_fonte=("arquivo_fonte", "first"))


def ler_sintese() -> pd.DataFrame:
    manifesto = cc.ler_manifesto(FONTE)
    partes = []
    for chave, linha in sorted(manifesto.items()):
        if not linha["observacao"].startswith("sintese"):
            continue
        bruto = pd.read_excel(cc.caminho_do_original(FONTE, linha), header=None, dtype=object)
        i = next(k for k in range(40) if str(bruto.iat[k, 0]).strip().upper() in ("MÊS", "MES"))
        corpo = bruto.iloc[i + 1:].copy()
        corpo.columns = [energia.chave_nome(c) for c in bruto.iloc[i]]
        corpo = corpo.dropna(subset=["MES"])
        partes.append(pd.DataFrame({
            "mes": pd.to_datetime(corpo["MES"]).dt.strftime("%Y-%m"),
            "uf": corpo["ESTADO"].map(energia.sigla_da_uf),
            "produto": corpo["PRODUTO"].map(lambda p: PRODUTOS_SINTESE.get(energia.chave_nome(p))),
            "preco_sintese": pd.to_numeric(corpo["PRECO MEDIO REVENDA"], errors="coerce"),
            "postos_sintese": pd.to_numeric(corpo["NUMERO DE POSTOS PESQUISADOS"],
                                            errors="coerce"),
            "arquivo_sintese": chave}))
    sintese = pd.concat(partes, ignore_index=True)
    return sintese.dropna(subset=["produto", "uf"])


def deflacionar(tabela: pd.DataFrame) -> pd.DataFrame:
    ipca = energia.indice_ipca().set_index("mes")["indice"]
    base = config.IPCA_BASE_PRECOS
    fator = ipca[base] / tabela["mes"].map(ipca)
    tabela["preco_real"] = tabela["preco_medio_revenda"] * fator
    tabela["base_real"] = base
    return tabela


def executar() -> int:
    logger = log.preparar(ETAPA)
    por_uf, por_municipio, n_linhas = [], [], 0
    for chave, quadro in tabelas_por_posto():
        coletas = preparar(quadro, chave)
        n_linhas += len(coletas)
        por_uf.append(agregar(coletas, ["mes", "uf", "produto"]))
        por_municipio.append(agregar(coletas, ["mes", "uf", "municipio_fonte", "produto"]))
        logger.info("%s: %d coletas", chave, len(coletas))
    uf = pd.concat(por_uf, ignore_index=True)
    municipio = pd.concat(por_municipio, ignore_index=True)
    repetidos = uf.duplicated(["mes", "uf", "produto"], keep=False)
    if repetidos.any():
        logger.error("o mesmo mes em dois arquivos por posto:\n%s",
                     uf[repetidos][["mes", "uf", "produto", "arquivo_fonte"]].head(20))
        return 1
    for t in (uf, municipio):
        t["preco_medio_revenda"] = t["soma"] / t["coletas"]
        t.rename(columns={"coletas": "n_coletas", "postos": "n_postos"}, inplace=True)
    uf = deflacionar(uf.drop(columns="soma"))
    municipio = deflacionar(municipio.drop(columns="soma"))
    largo = uf.pivot(index=["mes", "uf"], columns="produto", values="preco_medio_revenda")
    paridade = (largo["etanol_hidratado"] / largo["gasolina_comum"]).rename(
        "paridade_etanol_gasolina").reset_index()
    uf = uf.merge(paridade, on=["mes", "uf"], how="left")
    largo_m = municipio.pivot_table(index=["mes", "uf", "municipio_fonte"], columns="produto",
                                    values="preco_medio_revenda")
    paridade_m = (largo_m["etanol_hidratado"] / largo_m["gasolina_comum"]).rename(
        "paridade_etanol_gasolina").reset_index()
    municipio = municipio.merge(paridade_m, on=["mes", "uf", "municipio_fonte"], how="left")

    excecoes = (pd.read_csv(config.ANP_MUNICIPIOS, dtype=str, keep_default_na=False)
                if config.ANP_MUNICIPIOS.exists() else None)
    pares = municipio[["uf", "municipio_fonte"]].drop_duplicates()
    pares["cod_ibge_municipio"] = energia.casar_municipios(pares, "uf", "municipio_fonte",
                                                           excecoes)
    sem = pares[pares["cod_ibge_municipio"].isna()]
    if len(sem):
        logger.error("municipios da ANP sem codigo IBGE (%d); acrescente a "
                     "config/anp_municipios.csv:\n%s", len(sem), sem.to_string())
        return 1
    municipio = municipio.merge(pares, on=["uf", "municipio_fonte"], how="left")

    sintese = ler_sintese()
    conferencias, comparacao = conferir(uf, municipio, sintese)
    validacao = energia.gravar_validacao(config.PRECOS_VALIDACAO, conferencias)
    comparacao.to_csv(config.DIR_SAIDAS / "precos_combustiveis_conferencia_sintese.csv",
                      index=False)
    if int(validacao["falhas"].sum()):
        logger.error("conferencias dos precos com falha:\n%s", validacao.to_string())
        return 1
    colunas = ["mes", "uf", "produto", "preco_medio_revenda", "preco_real", "base_real",
               "paridade_etanol_gasolina", "n_postos", "n_coletas", "unidade", "arquivo_fonte"]
    uf = uf[colunas].sort_values(["mes", "uf", "produto"]).reset_index(drop=True)
    colunas_m = colunas[:2] + ["cod_ibge_municipio", "municipio_fonte"] + colunas[2:]
    municipio = municipio[colunas_m].sort_values(["mes", "uf", "cod_ibge_municipio",
                                                  "produto"]).reset_index(drop=True)
    uf.to_parquet(config.PRECOS_COMBUSTIVEIS, index=False)
    municipio.to_parquet(config.PRECOS_COMBUSTIVEIS_MUNICIPAL, index=False)
    escrever_dicionario(uf, municipio, comparacao)
    log.contagem(logger, coletas=n_linhas, linhas_uf=len(uf), linhas_municipio=len(municipio))
    logger.info("gravado %s", log.caminho_relativo(config.PRECOS_COMBUSTIVEIS))
    return 0


def conferir(uf, municipio, sintese) -> tuple[list[dict], pd.DataFrame]:
    comparacao = uf.merge(sintese, on=["mes", "uf", "produto"], how="inner")
    comparacao["diferenca_relativa"] = (comparacao["preco_medio_revenda"]
                                        / comparacao["preco_sintese"] - 1)
    acima = comparacao[comparacao["diferenca_relativa"].abs() > TOLERANCIA_SINTESE]
    meses = pd.period_range(uf["mes"].min(), uf["mes"].max(), freq="M").strftime("%Y-%m")
    sem_dado = {p: sorted(set(meses) - set(uf.loc[uf["produto"] == p, "mes"]))
                for p in PRODUTOS.values()}
    unidades = uf["unidade"].unique().tolist()
    linhas = [
        {"conferencia": "preco medio por UF e mes contra a sintese mensal da ANP: diferenca "
                        "acima de 1% (registrada, nao e' falha)",
         "casos": len(comparacao), "falhas": 0,
         "observacao": f"{len(acima)} casos acima de 1% "
                       f"({100 * len(acima) / max(len(comparacao), 1):.1f}%); mediana da "
                       f"|diferenca| {100 * comparacao['diferenca_relativa'].abs().median():.2f}%"},
        {"conferencia": "chave unica (mes, UF, produto)", "casos": len(uf),
         "falhas": int(uf.duplicated(["mes", "uf", "produto"]).sum()), "observacao": ""},
        {"conferencia": "chave unica (mes, municipio, produto)", "casos": len(municipio),
         "falhas": int(municipio.duplicated(["mes", "cod_ibge_municipio", "produto"]).sum()),
         "observacao": ""},
        {"conferencia": "preco positivo", "casos": len(uf),
         "falhas": int((uf["preco_medio_revenda"] <= 0).sum()), "observacao": ""},
        {"conferencia": "meses sem nenhuma coleta, por produto (lacuna, nao preenchida)",
         "casos": len(meses), "falhas": 0,
         "observacao": "; ".join(f"{p}: {', '.join(m[:12])}{' ...' if len(m) > 12 else ''}"
                                 f" ({len(m)})" for p, m in sem_dado.items() if m) or "nenhum"},
        {"conferencia": "unidades de medida no bruto", "casos": len(unidades), "falhas": 0,
         "observacao": "; ".join(unidades)},
    ]
    return linhas, comparacao


def escrever_dicionario(uf, municipio, comparacao) -> None:
    campos = [
        ("mes", "texto AAAA-MM", "Mes da coleta (`Data da Coleta` do bruto)."),
        ("uf", "sigla", "UF do posto."),
        ("cod_ibge_municipio", "7 digitos", "So' na tabela municipal: codigo IBGE do municipio "
         "do posto."),
        ("municipio_fonte", "texto", "So' na tabela municipal: municipio como a ANP escreve."),
        ("produto", "texto", "`gasolina_comum` (`GASOLINA` no bruto), `etanol_hidratado` "
         "(`ETANOL`), `diesel_s10` (`DIESEL S10`), `gnv` (`GNV`)."),
        ("preco_medio_revenda", "R$/litro; GNV em R$/m3", "Media simples dos precos de venda "
         "coletados no mes, nominal."),
        ("preco_real", "R$ do mes-base", "`preco_medio_revenda` x IPCA(base) / IPCA(mes), com o "
         "IPCA cheio (sgs_433) encadeado de `macro_mensal`. Vazio depois do ultimo mes do IPCA "
         "em `macro_mensal`."),
        ("base_real", "texto AAAA-MM", "Mes-base do preco real."),
        ("paridade_etanol_gasolina", "razao", "Preco medio do etanol / preco medio da gasolina "
         "comum, na UF (ou municipio) e mes; repetida nas linhas dos quatro produtos."),
        ("n_postos", "postos", "Postos pesquisados (CNPJ distintos) com coleta do produto no mes."),
        ("n_coletas", "coletas", "Coletas (posto x data) do produto no mes."),
        ("unidade", "texto", "`Unidade de Medida` do bruto."),
        ("arquivo_fonte", "texto", "Arquivo por posto em `dados/bruto/anp_precos/` de que o mes "
         "saiu."),
    ]
    acima = comparacao[comparacao["diferenca_relativa"].abs() > TOLERANCIA_SINTESE]
    energia.gravar_dicionario(
        config.PRECOS_DICIONARIO, "Dicionario -- precos_combustiveis_mensal (e a tabela municipal)",
        f"Tabela por UF: {len(uf):,} linhas, {uf['mes'].min()} a {uf['mes'].max()}. Tabela "
        f"municipal (`precos_combustiveis_municipal_mensal.parquet`): {len(municipio):,} linhas, "
        f"{municipio['cod_ibge_municipio'].nunique()} municipios. Gravadas pela etapa 18 a partir "
        "da serie historica por posto do Levantamento de Precos de Combustiveis (LPC) da ANP.",
        campos,
        ["**Comeca em 2004-01**: a serie por posto nao existe antes. A sintese da ANP tem "
         "2001-07 a 2003-12, mas nao entra no produto (ver QUESTOES_ABERTAS, rodada 13).",
         "**Amostra, nao censo:** o LPC pesquisa uma amostra de postos em uma amostra de "
         "municipios, que mudou ao longo do tempo (de 2017-07 a 2017-12 a cobertura caiu de 501 "
         "para 459 municipios; em 2018-05 a greve dos caminhoneiros reduziu as coletas; nao "
         "houve pesquisa de 18/8/2020 a 17/10/2020). Municipio fora da amostra nao tem linha.",
         "**Diesel S10 so' existe a partir de 2012-2013** no bruto; o diesel comum (S500) nao "
         "entra no recorte.",
         "**Media de coletas, nao de postos:** posto com mais coletas no mes pesa mais. A sintese "
         f"da ANP difere em mais de 1% em {len(acima)} de {len(comparacao)} casos (UF x mes x "
         "produto); a tabela de diferencas esta' em "
         "`saidas/precos_combustiveis_conferencia_sintese.csv`.",
         f"**Preco real em R$ de {config.IPCA_BASE_PRECOS}** (ultimo mes do IPCA em "
         "`macro_mensal`); os meses posteriores ficam com `preco_real` vazio."],
        "ANP, Serie historica de precos de combustiveis (dados abertos, por posto), "
        f"{anp_precos.PAGINA_DADOS}; sintese mensal por estado em {anp_precos.PAGINA_SINTESE}. "
        "URL, data e SHA-256 de cada arquivo no manifesto.")


if __name__ == "__main__":
    raise SystemExit(executar())
