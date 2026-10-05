"""Comercio exterior de veiculos (Comex Stat, MDIC): leitura do bruto e regras.

O bruto (`dados/bruto/comex/`, baixado por `ferramentas/comex_baixar.py`) tem uma
resposta da API por fluxo x posicao x ano, com e sem pais. Aqui ficam a leitura
dessas respostas, as regras da tabela de NCMs (`config/ncm_veiculos.csv`) e as
conferencias.

As unidades publicadas ficam em `unidades`. Em `unidades_ajustadas`, as linhas com
menos de 500 kg por unidade tem a quantidade estimada pelo peso
(`ajustar_unidades`): nelas valor e peso sao de carro, e a quantidade nao.

Duas coisas que a NCM nao diz, e que o dicionario repete:

- **onde cai o hibrido leve** -- pode estar em 8703.40 ou nas NCMs de combustao;
- **que a unidade e' um carro pronto** -- kit SKD ou CKD de um veiculo entra na
  NCM do veiculo completo (regra geral 2a do SH): a importacao pode incluir kits
  para montagem local. Isso se registra, nao se separa.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from . import config

DIR = config.DIR_BRUTO / "comex"
NOME = re.compile(r"^(importacao|exportacao)_(8703|8704)_(\d{4})_(pais|total)\.json$")
UNIDADE = "NUMERO (UNIDADE)"
GRUPOS = ("centelha", "diesel", "hev", "phev", "bev", "outros", "sem_separacao")
COLUNAS = ["mes_ref", "ano", "mes", "fluxo", "ncm", "pais", "fob_usd", "kg", "unidades",
           "unidades_ajustadas", "ajuste_unidades"]
AJUSTES = ("publicada", "estimada_pelo_peso")
# fora do agregado de carros: 8703.10 (neve, golfe e semelhantes) e o 8704 que nao e'
# leve ou cujo peso a descricao nao da'
FORA_DO_AGREGADO = ("870310",)

# prefixo da NCM -> grupo de propulsao, pelo texto oficial da subposicao (SH 2017 em
# 8703, SH 2022 em 8704). Ordem: o prefixo mais longo vence.
GRUPO_POR_PREFIXO = {
    "870310": "outros",      # neve, golfe e semelhantes
    "870321": "centelha", "870322": "centelha", "870323": "centelha", "870324": "centelha",
    "870331": "diesel", "870332": "diesel", "870333": "diesel",
    "870340": "hev",         # centelha + eletrico, sem recarga externa
    "870350": "hev",         # diesel + eletrico, sem recarga externa
    "870360": "phev",        # centelha + eletrico, com recarga externa
    "870370": "phev",        # diesel + eletrico, com recarga externa
    "870380": "bev",         # so' motor eletrico
    "870390": "outros",
    "870410": "outros",      # dumpers
    "870421": "diesel", "870422": "diesel", "870423": "diesel",
    "870431": "centelha", "870432": "centelha",
    "870441": "hev", "870442": "hev", "870443": "hev",   # diesel + eletrico (SH 2022)
    "870451": "hev", "870452": "hev",                    # centelha + eletrico (SH 2022)
    "870460": "bev",
    "870490": "outros",
}
# subposicoes que separam o eletrificado em cada posicao: o primeiro mes com dado
# de qualquer uma delas e' a data da separacao
SUBPOSICOES_ELETRIFICADAS = {"8703": ("870340", "870350", "870360", "870370", "870380"),
                             "8704": ("870441", "870442", "870443", "870451", "870452",
                                      "870460")}


def grupo_da_ncm(ncm: str) -> str:
    candidatos = [p for p in GRUPO_POR_PREFIXO if ncm.startswith(p)]
    return GRUPO_POR_PREFIXO[max(candidatos, key=len)] if candidatos else "outros"


def leve_da_ncm(ncm: str, descricao: str) -> str:
    """8704: `sim` se a descricao limita o peso em carga maxima a 5 t; `nao` se o
    passa de 5 t ou e' dumper; `indeterminado` no residual sem limite. 8703: vazio."""
    if not ncm.startswith("8704"):
        return ""
    texto = descricao.lower()
    if ncm.startswith("870410") or "dumper" in texto:
        return "nao"
    acima = [int(n) for n in re.findall(r"(?<!não )(?<!nao )superior a (\d+)", texto)]
    acima += [int(n) for n in re.findall(r"(?<![<=])>\s*(\d+)", texto)]
    acima += [int(n) for n in re.findall(r"(\d+)\s*t\w*\s*<", texto)]
    acima += [int(n) for n in re.findall(r"(?:entre|maior que) (\d+)", texto)]
    if any(n >= 5 for n in acima):
        return "nao"
    if re.search(r"(<=|não superior a|nao superior a)\s*5\b", texto):
        return "sim"
    return "indeterminado"


def agregado_carros(ncm: str, leve: str) -> str:
    """`sim` se a NCM entra no agregado de carros: 8703 menos 8703.10, e 8704 leve."""
    if ncm.startswith(FORA_DO_AGREGADO):
        return "nao"
    if ncm.startswith("8703"):
        return "sim"
    return "sim" if leve == "sim" else "nao"


def grupo_no_mes(grupo: str, separa_desde: str, mes_ref: str) -> str:
    """Antes de existirem as subposicoes de eletrificados da posicao, nenhuma NCM
    separa o eletrificado: o grupo e' `sem_separacao`."""
    return "sem_separacao" if not separa_desde or mes_ref < separa_desde else grupo


def ler_bruto(diretorio: Path = DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(com pais, sem pais): uma linha por fluxo x NCM x mes (x pais)."""
    partes = {"pais": [], "total": []}
    for arquivo in sorted(diretorio.glob("*.json")):
        casado = NOME.match(arquivo.name)
        if not casado:
            continue
        fluxo, posicao, _, versao = casado.groups()
        for r in json.loads(arquivo.read_bytes())["data"]["list"]:
            partes[versao].append({
                "fluxo": fluxo, "posicao": posicao, "ncm": r["coNcm"],
                "descricao": r["ncm"], "mes_ref": f"{r['year']}-{r['monthNumber']}",
                "pais": r.get("country", ""), "fob_usd": int(r["metricFOB"]),
                "kg": int(r["metricKG"]), "quantidade": int(float(r["metricStatistic"]))})
    return pd.DataFrame(partes["pais"]), pd.DataFrame(partes["total"])


def unidades_das_ncms(diretorio: Path = DIR) -> dict[str, tuple[str, str]]:
    """NCM -> (descricao longa, unidade estatistica), de `tables/ncm`."""
    saida = {}
    for arquivo in sorted(diretorio.glob("ncm_*.json")):
        for r in json.loads(arquivo.read_bytes())["data"]["list"]:
            saida[r["coNcm"]] = (r["noNCM"], r["unit"])
    return saida


def tabela_de_ncms(com_pais: pd.DataFrame, unidades: dict[str, tuple[str, str]]
                   ) -> pd.DataFrame:
    """Uma linha por NCM de 8 digitos: descricao, unidade, periodo e as duas
    colunas de classificacao (`leve`, `grupo_propulsao_ncm`)."""
    periodo = com_pais.groupby("ncm").agg(posicao=("posicao", "first"),
                                          descricao_curta=("descricao", "last"),
                                          primeiro_mes=("mes_ref", "min"),
                                          ultimo_mes=("mes_ref", "max")).reset_index()
    separa = {}
    for posicao, prefixos in SUBPOSICOES_ELETRIFICADAS.items():
        meses = periodo.loc[periodo["ncm"].str[:6].isin(prefixos), "primeiro_mes"]
        separa[posicao] = meses.min() if len(meses) else ""
    linhas = []
    for _, r in periodo.iterrows():
        descricao, unidade = unidades.get(r["ncm"], (r["descricao_curta"], ""))
        linhas.append({
            "ncm": r["ncm"], "posicao": r["posicao"], "descricao": descricao,
            "unidade_estatistica": unidade, "primeiro_mes": r["primeiro_mes"],
            "ultimo_mes": r["ultimo_mes"], "leve": leve_da_ncm(r["ncm"], descricao + " "
                                                               + r["descricao_curta"]),
            "grupo_propulsao_ncm": grupo_da_ncm(r["ncm"]),
            "separa_eletrificados_desde": separa[r["posicao"]]})
        linhas[-1]["agregado_carros"] = agregado_carros(r["ncm"], linhas[-1]["leve"])
    tabela = pd.DataFrame(linhas)
    # NCM que so' existiu antes da separacao nunca separou nada
    antes = (tabela["separa_eletrificados_desde"] != "") & (
        tabela["ultimo_mes"] < tabela["separa_eletrificados_desde"])
    tabela.loc[antes, "grupo_propulsao_ncm"] = "sem_separacao"
    return tabela.sort_values("ncm").reset_index(drop=True)


def produto(com_pais: pd.DataFrame, ncms: pd.DataFrame) -> pd.DataFrame:
    """`comex_veiculos.parquet`: unidades so' onde a unidade estatistica e' unidade, e
    as unidades ajustadas pelo peso (`ajustar_unidades`)."""
    unidade = dict(zip(ncms["ncm"], ncms["unidade_estatistica"]))
    saida = com_pais.assign(
        ano=com_pais["mes_ref"].str[:4].astype(int),
        mes=com_pais["mes_ref"].str[5:7].astype(int),
        unidades=[q if unidade.get(n) == UNIDADE else pd.NA
                  for n, q in zip(com_pais["ncm"], com_pais["quantidade"])])
    saida["unidades"] = saida["unidades"].astype("Int64")
    saida = ajustar_unidades(saida)
    return saida[COLUNAS].sort_values(["fluxo", "mes_ref", "ncm", "pais"]).reset_index(drop=True)


def referencias_de_peso(dados: pd.DataFrame) -> dict[str, dict]:
    """kg por unidade de referencia, nas linhas plausiveis (`KG_MINIMO` ou mais por
    unidade): por (fluxo, NCM, ano), por (fluxo, NCM) em todos os anos e por NCM nos
    dois fluxos. Media ponderada: kg somados sobre unidades somadas."""
    unidades = dados["unidades"].astype("float")
    plausivel = dados[(unidades > 0) & (dados["kg"] / unidades >= KG_MINIMO)].assign(
        u=lambda d: d["unidades"].astype("float"))
    def media(chaves):
        g = plausivel.groupby(chaves)[["kg", "u"]].sum()
        return (g["kg"] / g["u"]).to_dict()
    return {"ano": media(["fluxo", "ncm", "ano"]), "ncm": media(["fluxo", "ncm"]),
            "ncm_dois_fluxos": media(["ncm"])}


def ajustar_unidades(dados: pd.DataFrame) -> pd.DataFrame:
    """`unidades_ajustadas` e `ajuste_unidades` (decisao do pesquisador, rodada "pbe,
    comex e calendario").

    Nas linhas com menos de `KG_MINIMO` kg por unidade publicada, valor e peso sao de
    carro e a quantidade nao: a unidade ajustada e' o peso dividido pelo kg por
    unidade de referencia da mesma NCM, no mesmo fluxo e ano (linhas plausiveis),
    arredondado para inteiro. Sem referencia no ano, a da NCM em todos os anos; sem
    ela, a da NCM nos dois fluxos; sem nenhuma, fica a publicada. Nas demais linhas, a
    ajustada e' a publicada. `unidades` continua como publicada.
    """
    saida = dados.copy()
    refs = referencias_de_peso(saida)
    baixo = peso_baixo(saida)
    ajustadas, ajuste = [], []
    for (fluxo, ncm, ano, kg, publicada, b) in zip(
            saida["fluxo"], saida["ncm"], saida["ano"], saida["kg"], saida["unidades"], baixo):
        if not b:
            ajustadas.append(publicada)
            ajuste.append("publicada" if not pd.isna(publicada) else "")
            continue
        ref = (refs["ano"].get((fluxo, ncm, ano)) or refs["ncm"].get((fluxo, ncm))
               or refs["ncm_dois_fluxos"].get(ncm))
        if ref is None:
            ajustadas.append(publicada)
            ajuste.append("publicada")
            continue
        ajustadas.append(int(kg / ref + 0.5))
        ajuste.append("estimada_pelo_peso")
    saida["unidades_ajustadas"] = pd.array(ajustadas, dtype="Int64")
    saida["ajuste_unidades"] = ajuste
    return saida


def conferencia_paises(com_pais: pd.DataFrame, sem_pais: pd.DataFrame) -> pd.DataFrame:
    """Soma sobre paises contra a consulta sem pais, por fluxo x NCM x ano."""
    def por_ano(quadro):
        return (quadro.assign(ano=quadro["mes_ref"].str[:4])
                .groupby(["fluxo", "ncm", "ano"])[["fob_usd", "kg", "quantidade"]].sum())
    a, b = por_ano(com_pais), por_ano(sem_pais)
    juntos = a.join(b, how="outer", lsuffix="_paises", rsuffix="_total").fillna(0)
    for m in ("fob_usd", "kg", "quantidade"):
        juntos[f"{m}_diferenca"] = juntos[f"{m}_paises"] - juntos[f"{m}_total"]
    return juntos.reset_index()


def meses_faltando(com_pais: pd.DataFrame, primeiro: str, ultimo: str) -> pd.DataFrame:
    """Meses sem nenhuma linha, por fluxo x posicao, na janela."""
    janela = [str(p) for p in pd.period_range(primeiro, ultimo, freq="M")]
    linhas = []
    for (fluxo, posicao), grupo in com_pais.groupby(["fluxo", "posicao"]):
        presentes = set(grupo["mes_ref"])
        linhas += [{"fluxo": fluxo, "posicao": posicao, "mes_ref": m}
                   for m in janela if m not in presentes]
    return pd.DataFrame(linhas, columns=["fluxo", "posicao", "mes_ref"])


KG_MINIMO = 500  # abaixo disso por unidade, a linha nao pesa como veiculo completo


def peso_baixo(dados: pd.DataFrame) -> pd.Series:
    """Linhas (NCM x pais x mes) com menos de `KG_MINIMO` kg por unidade publicada.

    O carro mais leve passa de 800 kg, entao a linha abaixo disso nao descreve
    veiculo completo. O pesquisador conferiu as maiores: valor e peso sao de carro,
    a quantidade e' que esta' errada (na India, em 2019, a quantidade e' o peso).
    Por isso `ajustar_unidades` estima a quantidade pelo peso.
    """
    unidades = dados["unidades"].astype("float")
    return (unidades > 0) & (dados["kg"] / unidades < KG_MINIMO)
