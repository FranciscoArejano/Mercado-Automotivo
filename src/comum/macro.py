"""Dimensao macro mensal: Banco Central (SGS) e IBGE (SIDRA).

Tabela de fatos separada, unidade `mes_ref`, juncao trivial com o painel. **Nao
alarga `painel.parquet` nem `painel_bruto.parquet`** -- dimensao e' arquivo
separado, e a juncao e' do codigo de analise.

Duas regras herdadas da ESPEC valem aqui inteiras:

- **Lacuna e' lacuna** (sec.9.2). Serie que comeca depois de 2003-01 ou termina
  antes de 2026-08 fica com o mes vazio. Nao se preenche, nao se interpola, nao
  se estende com o ultimo valor.
- **Conferir a ordem de grandeza contra a unidade declarada** antes de gravar, e
  reportar o que nao bate em vez de assumir que o codigo esta' certo.

O IPCA por subitem vem repartido em quatro tabelas do SIDRA, que se encaixam sem
sobreposicao. A emenda guarda **as duas coisas**: a variacao mensal original de
cada tabela e o indice encadeado, em colunas separadas, para que a costura seja
auditavel linha a linha.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.request

import pandas as pd

from . import config

SGS = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
       "?formato=json&dataInicial={inicio}&dataFinal={fim}")
SIDRA = ("https://apisidra.ibge.gov.br/values/t/{tabela}/n1/1/v/63/p/all"
         "/c315/{subitem}?formato=json")

CAMPOS_SERIES = ["codigo", "nome", "fonte", "unidade", "janela_declarada",
                 "situacao_da_serie", "data_coleta", "observacao"]

# As quatro tabelas do IPCA por subitem, na ordem cronologica. Elas se encaixam
# sem sobreposicao: o primeiro mes de cada uma e' o mes seguinte ao ultimo da
# anterior, o que a emenda confere em vez de supor.
TABELAS_IPCA = (655, 2938, 1419, 7060)


def _buscar(url: str, tentativas: int = 4, espera: float = 2.0):
    ultimo = None
    for tentativa in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=120) as resposta:
                return json.load(resposta)
        except Exception as erro:  # rede instavel nao pode derrubar a coleta
            ultimo = erro
            if tentativa < tentativas - 1:
                time.sleep(espera * (2 ** tentativa))
    raise RuntimeError(f"falhou apos {tentativas} tentativas: {ultimo}") from ultimo


def carregar_catalogo() -> list[dict]:
    """As series a coletar, em config/series_macro.csv. O humano escreve."""
    if not config.SERIES_MACRO.exists():
        return []
    with config.SERIES_MACRO.open(encoding="utf-8", newline="") as fluxo:
        return [linha for linha in csv.DictReader(fluxo) if linha.get("codigo")]


def coletar_sgs(codigo: str, inicio: str, fim: str) -> pd.DataFrame:
    """Uma serie do SGS, ja' com `mes_ref` no formato do painel."""
    dados = _buscar(SGS.format(
        codigo=codigo,
        inicio=f"01/01/{inicio[:4]}",
        fim=f"31/12/{fim[:4]}",
    ))
    if not dados:
        return pd.DataFrame(columns=["mes_ref", "valor"])
    quadro = pd.DataFrame(dados)
    datas = pd.to_datetime(quadro["data"], format="%d/%m/%Y")
    return pd.DataFrame({
        "mes_ref": datas.dt.strftime("%Y-%m"),
        "valor": pd.to_numeric(quadro["valor"], errors="coerce"),
    }).dropna(subset=["valor"])


def coletar_ipca_subitem(subitem: str) -> pd.DataFrame:
    """A variacao mensal de um subitem, emendada pelas quatro tabelas.

    Devolve `mes_ref`, `variacao_pct`, `tabela_sidra` -- uma linha por mes, com
    a tabela de origem declarada. O encadeamento fica em `encadear`.
    """
    partes = []
    for tabela in TABELAS_IPCA:
        dados = _buscar(SIDRA.format(tabela=tabela, subitem=subitem))
        if len(dados) < 2:
            continue
        quadro = pd.DataFrame(dados[1:])
        partes.append(pd.DataFrame({
            "mes_ref": quadro["D3C"].str.slice(0, 4) + "-" + quadro["D3C"].str.slice(4, 6),
            "variacao_pct": pd.to_numeric(quadro["V"], errors="coerce"),
            "tabela_sidra": tabela,
        }))
        time.sleep(0.5)
    if not partes:
        return pd.DataFrame(columns=["mes_ref", "variacao_pct", "tabela_sidra"])
    junto = pd.concat(partes, ignore_index=True).sort_values("mes_ref")
    return junto.drop_duplicates(subset="mes_ref", keep="first").reset_index(drop=True)


def encadear(variacoes: pd.DataFrame, base_mes: str, base_valor: float = 100.0
             ) -> pd.DataFrame:
    """Indice encadeado a partir das variacoes mensais, com base declarada.

    O indice do mes de base vale `base_valor`; cada mes seguinte aplica a
    propria variacao. A variacao original fica na coluna ao lado: a emenda e'
    auditavel, e nao substitui o dado da fonte.
    """
    quadro = variacoes.sort_values("mes_ref").reset_index(drop=True).copy()
    if quadro.empty:
        quadro["indice"] = []
        return quadro
    fator = (1 + quadro["variacao_pct"].fillna(0) / 100).cumprod()
    posicao = quadro.index[quadro["mes_ref"] == base_mes]
    divisor = fator.iloc[posicao[0]] if len(posicao) else fator.iloc[0]
    quadro["indice"] = (base_valor * fator / divisor).round(4)
    # Mes sem variacao publicada nao ganha indice inventado.
    quadro.loc[quadro["variacao_pct"].isna(), "indice"] = pd.NA
    return quadro


def base_efetiva(variacoes: pd.DataFrame, base_mes: str) -> str:
    """O mes em que o indice encadeado vale de fato 100.

    E' a base declarada quando a serie tem dado nela. Quando a serie comeca
    depois -- o automovel usado so' tem variacao a partir de 2006-07 --, a base
    declarada e' vazia: o indice vale 100 no mes anterior ao primeiro dado, e e'
    isso que tem de estar escrito, nao a base que nao existe.
    """
    com_dado = variacoes[variacoes["variacao_pct"].notna()].sort_values("mes_ref")
    if com_dado.empty:
        return ""
    primeiro = com_dado["mes_ref"].iloc[0]
    if primeiro <= base_mes:
        return base_mes
    return (pd.Period(primeiro, freq="M") - 1).strftime("%Y-%m")


def juncoes_das_tabelas(variacoes: pd.DataFrame) -> pd.DataFrame:
    """Os meses em que a serie troca de tabela do SIDRA.

    A validacao pede mostrar que a variacao do primeiro mes de cada tabela nova
    nao foi contada duas vezes. Como as janelas se encaixam sem sobreposicao,
    "nao contada duas vezes" e' `mes_ref` unico -- conferido aqui.
    """
    if variacoes.empty:
        return pd.DataFrame()
    # So' conta como emenda a troca entre duas tabelas que **publicam** o
    # subitem. O automovel usado e' aceito pela tabela 655 mas vem como '...'
    # nos 83 meses dela: a serie **comeca** em 2006-07, nao se emenda ali. Sem
    # este filtro a tabela registrava uma juncao 655 -> 2938 que nao aconteceu,
    # e a tabela de emendas e' justamente o que torna o encadeamento auditavel.
    quadro = (variacoes[variacoes["variacao_pct"].notna()]
              .sort_values("mes_ref").reset_index(drop=True))
    if quadro.empty:
        return pd.DataFrame()
    troca = quadro["tabela_sidra"] != quadro["tabela_sidra"].shift()
    juncoes = quadro[troca & (quadro.index > 0)].copy()
    anteriores = quadro.shift().loc[juncoes.index]
    juncoes["mes_anterior"] = anteriores["mes_ref"].values
    juncoes["tabela_anterior"] = anteriores["tabela_sidra"].values
    todos = variacoes[variacoes["variacao_pct"].notna()]
    juncoes["meses_duplicados"] = [
        int((todos["mes_ref"] == mes).sum() - 1) for mes in juncoes["mes_ref"]
    ]
    return juncoes[["mes_anterior", "tabela_anterior", "mes_ref", "tabela_sidra",
                    "variacao_pct", "meses_duplicados"]]
