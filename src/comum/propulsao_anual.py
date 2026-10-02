"""Propulsao por ano: os tipos que cada modelo oferecia em cada ano.

`propulsao_na_vigencia` e' o conjunto de tudo o que foi oferecido em algum momento
da vigencia. Numa serie temporal ele infla o `parcial` dos anos anteriores a'
chegada da versao eletrificada: o Toro de 2016 a 2025 sai `parcial` por causa do
hibrido de 2026. Aqui cada tipo ganha um ano de entrada (rodada "propulsao no
tempo"):

- **combustao** (gasolina, flex, diesel): o inicio da vigencia, como sempre -- a
  P2 ja' decidiu o que valia antes do PBE, e a transicao flex segue sem data;
- **eletrificado**, nesta ordem:
  1. fonte datada em `dados/referencia/propulsao_fontes.csv` (lancamento,
     producao ou presenca; `plano` nao conta) -> `fonte_datada`. Onde existe,
     manda sobre o ano do PBE;
  2. primeira tabela do PBE com uma versao daquele tipo para o modelo ->
     `pbe_ano`, desde que o PBE pudesse ter visto o tipo antes: um ano com coluna
     de propulsao (2021 em diante), dentro da vigencia e antes da primeira
     aparicao, em que o modelo esta' na tabela sem o tipo. O marcador no nome
     prova presenca, nao ausencia -- a tabela de 2020 lista so' "CAYENNE (19MY)"
     quando o Cayenne S E-Hybrid ja' era vendido;
  3. senao, o inicio da vigencia -> `vigencia_sem_datacao`;
- vigencia so' com tipos eletrificados: o primeiro a entrar entra no inicio da
  vigencia (`vigencia`) -- o modelo nao vende sem propulsao (Prius, Dolphin).

O tipo entra no ano e fica ate' o fim da vigencia: a saida de um tipo nao e'
modelada. A resolucao e' o ano; o ano de PBE se aproxima do ano-modelo e pode
estar um ano a' frente da chegada ao mercado.
"""

from __future__ import annotations

import pandas as pd

from . import classificacao
from .fase2 import CHAVE, PROCEDENCIAS

COMBUSTAO = frozenset({"gasolina", "flex", "diesel"})
PRIMEIRO_ANO_COLUNA = 2021  # o PBE tem coluna de propulsao a partir daqui
# tipo da classificacao -> valores do PBE que contam como versao daquele tipo
FAMILIA_PBE = {"hibrido_indefinido": {"hev", "mhev"}, "mhev": {"mhev", "hev"}}
DATAS_ACEITAS = ("lancamento", "producao", "presenca")
# do mais fraco para o mais forte: a linha do ano leva a mais fraca entre os tipos
FONTES_TEMPORAIS = ("vigencia_sem_datacao", "pbe_ano", "fonte_datada", "vigencia")
COLUNAS = CHAVE + ["ano", "unidades", "propulsao_no_ano", "eletrificacao_no_ano",
                   "fonte_temporal", "entrada_dos_tipos", "procedencia_propulsao",
                   "vigencias"]


def _ano(mes: str) -> int:
    return int(mes[:4])


def _fonte_datada(fontes: pd.DataFrame, tipo: str, inicio: int, fim: int) -> int | None:
    """Ano mais antigo das fontes aceitas para o tipo que cai ate' o fim da vigencia."""
    anos = [_ano(d) for d, t, v in zip(fontes["data_fonte"], fontes["tipo_propulsao"],
                                       fontes["tipo_data_fonte"])
            if t == tipo and v in DATAS_ACEITAS and _ano(d) <= fim]
    return max(min(anos), inicio) if anos else None


def entradas(vigencia: pd.Series, pbe: pd.DataFrame, fontes: pd.DataFrame) -> dict:
    """{tipo: (ano_de_entrada, fonte_temporal)} para os tipos da vigencia.

    `pbe`: linhas do casamento PBE->painel da chave (`ano`, `valor_taxonomia`);
    `fontes`: linhas de `propulsao_fontes.csv` da chave.
    """
    inicio, fim = _ano(vigencia["vigencia_inicio"]), _ano(vigencia["vigencia_fim"])
    tipos = [t for t in vigencia["propulsao_na_vigencia"].split("+") if t]
    anos_na_tabela = set(pbe["ano"])
    saida = {}
    for tipo in tipos:
        if tipo in COMBUSTAO:
            saida[tipo] = (inicio, "vigencia")
            continue
        datada = _fonte_datada(fontes, tipo, inicio, fim)
        if datada is not None:
            saida[tipo] = (datada, "fonte_datada")
            continue
        vistos = pbe.loc[pbe["valor_taxonomia"].isin(FAMILIA_PBE.get(tipo, {tipo})), "ano"]
        primeiro = int(vistos.min()) if len(vistos) else None
        if primeiro is not None and primeiro <= inicio:
            saida[tipo] = (inicio, "pbe_ano")
        elif primeiro is not None and primeiro <= fim and any(
                inicio <= a < primeiro and a >= PRIMEIRO_ANO_COLUNA for a in anos_na_tabela):
            saida[tipo] = (primeiro, "pbe_ano")
        else:
            saida[tipo] = (inicio, "vigencia_sem_datacao")
    if saida and not set(saida) & COMBUSTAO:
        primeiro = min(a for a, _ in saida.values())
        saida.update({t: (inicio, "vigencia") for t, (a, _) in saida.items() if a == primeiro})
    return saida


def tabela_de_entradas(dim: pd.DataFrame, casado: pd.DataFrame,
                       fontes: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (vigencia, tipo): o ano de entrada e de onde ele vem."""
    pbe = casado.assign(ano=casado["ano_pbe"].astype(int))
    pbe_por_chave = {k: g for k, g in pbe.groupby(CHAVE)}
    fontes_por_chave = {k: g for k, g in fontes.groupby(CHAVE)}
    vazio_pbe = pbe.iloc[0:0]
    vazio_fontes = fontes.iloc[0:0]
    linhas = []
    for _, vigencia in dim[dim["propulsao_na_vigencia"] != ""].iterrows():
        chave = tuple(vigencia[CHAVE])
        resultado = entradas(vigencia, pbe_por_chave.get(chave, vazio_pbe),
                             fontes_por_chave.get(chave, vazio_fontes))
        for tipo, (ano, fonte) in resultado.items():
            linhas.append({**{c: vigencia[c] for c in CHAVE},
                           "vigencia_inicio": vigencia["vigencia_inicio"],
                           "vigencia_fim": vigencia["vigencia_fim"], "tipo": tipo,
                           "ano_entrada": ano, "fonte_temporal": fonte})
    return pd.DataFrame(linhas, columns=CHAVE + ["vigencia_inicio", "vigencia_fim", "tipo",
                                                 "ano_entrada", "fonte_temporal"])


def _pior(valores, ordem) -> str:
    """O mais fraco dos valores; `ordem` vai do mais fraco ao mais forte."""
    return min(valores, key=ordem.index) if valores else ""


def anual(dim: pd.DataFrame, entradas_: pd.DataFrame, painel: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (chave, ano) com unidades no painel.

    O ano junta as vigencias que tem mes com unidades nele: os tipos sao a uniao
    dos que ja' tinham entrado em cada uma; a procedencia e a fonte temporal, a
    mais fraca entre elas.
    """
    meses = (painel[painel["unidades"] > 0]
             .groupby(CHAVE + ["mes_ref"], as_index=False)["unidades"].sum())
    juntos = meses.merge(dim[CHAVE + ["vigencia_inicio", "vigencia_fim",
                                      "procedencia_propulsao"]], on=CHAVE)
    juntos = juntos[(juntos["mes_ref"] >= juntos["vigencia_inicio"])
                    & (juntos["mes_ref"] <= juntos["vigencia_fim"])]
    if juntos["unidades"].sum() != meses["unidades"].sum():
        raise AssertionError("a juncao com o painel perdeu ou duplicou unidades")
    juntos["ano"] = juntos["mes_ref"].str[:4].astype(int)
    por_vigencia = {k: g for k, g in entradas_.groupby(CHAVE + ["vigencia_inicio"])}
    procedencias = list(reversed(PROCEDENCIAS))  # da mais fraca para a mais forte
    linhas = []
    for (marca, modelo, segmento, ano), grupo in juntos.groupby(CHAVE + ["ano"]):
        tipos: dict[str, tuple[int, str]] = {}
        for inicio in sorted(set(grupo["vigencia_inicio"])):
            tipos_vig = por_vigencia.get((marca, modelo, segmento, inicio))
            if tipos_vig is None:
                continue
            for _, t in tipos_vig[tipos_vig["ano_entrada"] <= ano].iterrows():
                tipos.setdefault(t["tipo"], (int(t["ano_entrada"]), t["fonte_temporal"]))
        propulsao = classificacao.ordenar_propulsao("+".join(tipos))
        eletrificados = [f for t, (_, f) in tipos.items() if t not in COMBUSTAO]
        linhas.append({
            "marca": marca, "modelo": modelo, "segmento": segmento, "ano": ano,
            "unidades": int(grupo["unidades"].sum()), "propulsao_no_ano": propulsao,
            "eletrificacao_no_ano": classificacao.eletrificacao(propulsao),
            "fonte_temporal": (_pior(eletrificados, list(FONTES_TEMPORAIS))
                               or ("vigencia" if tipos else "")),
            "entrada_dos_tipos": "; ".join(
                f"{t}={tipos[t][0]} {tipos[t][1]}" for t in propulsao.split("+") if t),
            "procedencia_propulsao": _pior(set(grupo["procedencia_propulsao"]), procedencias),
            "vigencias": ";".join(sorted(set(grupo["vigencia_inicio"])))})
    return pd.DataFrame(linhas, columns=COLUNAS)


# --------------------------------------------------------------- validacoes


def problemas(tabela: pd.DataFrame, dim: pd.DataFrame, painel: pd.DataFrame) -> list[str]:
    """Uma linha por chave-ano com unidades, unidades iguais ao painel, tipos so'
    da vigencia, nada some dentro da vigencia, e o ultimo ano da vigencia com o
    conjunto inteiro."""
    saida = []
    com = painel[painel["unidades"] > 0].assign(ano=lambda p: p["mes_ref"].str[:4].astype(int))
    esperado = com.groupby(CHAVE + ["ano"])["unidades"].sum()
    obtido = tabela.set_index(CHAVE + ["ano"])["unidades"]
    if obtido.index.duplicated().any():
        saida.append("chave-ano repetida")
    faltam = esperado.index.difference(obtido.index)
    sobram = obtido.index.difference(esperado.index)
    saida += [f"{'/'.join(map(str, k))}: chave-ano do painel sem linha" for k in faltam[:20]]
    saida += [f"{'/'.join(map(str, k))}: linha sem unidades no painel" for k in sobram[:20]]
    comuns = esperado.index.intersection(obtido.index)
    diferentes = comuns[esperado[comuns].to_numpy() != obtido[comuns].to_numpy()]
    saida += [f"{'/'.join(map(str, k))}: unidades diferem do painel" for k in diferentes[:20]]
    por_chave = {k: g.sort_values("ano") for k, g in tabela.groupby(CHAVE)}
    for _, v in dim[dim["propulsao_na_vigencia"] != ""].iterrows():
        linhas = por_chave.get(tuple(v[CHAVE]))
        if linhas is None:
            continue
        anos = linhas[linhas["vigencias"].str.split(";").apply(
            lambda vs, i=v["vigencia_inicio"]: i in vs)]
        conjunto = set(v["propulsao_na_vigencia"].split("+"))
        nome = f"{v['marca']}/{v['modelo']} {v['vigencia_inicio']}"
        anteriores: set[str] = set()
        for _, linha in anos.iterrows():
            atuais = set(filter(None, linha["propulsao_no_ano"].split("+")))
            if not atuais:
                saida.append(f"{nome}: {linha['ano']} sem propulsao")
            if linha["vigencias"] == v["vigencia_inicio"]:
                if not atuais <= conjunto:
                    saida.append(f"{nome}: {linha['ano']} com tipo fora da vigencia")
                if not anteriores <= atuais:
                    saida.append(f"{nome}: tipo some em {linha['ano']}")
                anteriores = atuais
        ultimo = anos[anos["ano"] == _ano(v["vigencia_fim"])]
        if len(ultimo) and not conjunto <= set(ultimo.iloc[0]["propulsao_no_ano"].split("+")):
            saida.append(f"{nome}: o ultimo ano nao tem o conjunto inteiro da vigencia")
    return saida


NIVEIS = ("nenhuma", "parcial", "total", "nao_classificado")


def _participacao(unidades: pd.DataFrame, coluna: str) -> pd.DataFrame:
    t = unidades.assign(nivel=unidades[coluna].replace("", "nao_classificado"))
    largura = t.pivot_table(index="ano", columns="nivel", values="unidades", aggfunc="sum",
                            fill_value=0).reindex(columns=list(NIVEIS), fill_value=0)
    return (100 * largura.div(largura.sum(axis=1), axis=0)).round(2)


def uso_teste(dim: pd.DataFrame, tabela: pd.DataFrame, painel: pd.DataFrame,
              inicio: int = 2015) -> pd.DataFrame:
    """A serie mais obvia que um artigo faria com a classificacao: participacao de
    cada nivel de eletrificacao nas unidades, por ano (%), lado a lado -- pelo
    conjunto da vigencia (`vigencia`, o uso errado) e pela tabela anual (`anual`).
    """
    meses = (painel[painel["unidades"] > 0]
             .groupby(CHAVE + ["mes_ref"], as_index=False)["unidades"].sum())
    juntos = meses.merge(dim[CHAVE + ["vigencia_inicio", "vigencia_fim",
                                      "eletrificacao_na_vigencia"]], on=CHAVE)
    juntos = juntos[(juntos["mes_ref"] >= juntos["vigencia_inicio"])
                    & (juntos["mes_ref"] <= juntos["vigencia_fim"])]
    juntos = juntos.assign(ano=juntos["mes_ref"].str[:4].astype(int))
    vigencia = _participacao(juntos[juntos["ano"] >= inicio], "eletrificacao_na_vigencia")
    ano = _participacao(tabela[tabela["ano"] >= inicio], "eletrificacao_no_ano")
    meses_no_ultimo = juntos.loc[juntos["ano"] == juntos["ano"].max(), "mes_ref"].nunique()
    linhas = []
    for a in ano.index:
        for nivel in NIVEIS:
            linhas.append({"ano": a, "meses": 12 if a < ano.index.max() else meses_no_ultimo,
                           "nivel": nivel, "pct_pela_vigencia": vigencia.loc[a, nivel],
                           "pct_anual": ano.loc[a, nivel]})
    return pd.DataFrame(linhas)
