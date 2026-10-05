"""Propulsao por ano: os tipos que cada vigencia oferecia em cada ano.

`propulsao_na_vigencia` e' o conjunto de tudo o que foi oferecido em algum momento
da vigencia. Numa serie temporal ele infla o `parcial` dos anos anteriores a'
chegada da versao eletrificada (rodada "propulsao no tempo"). Aqui cada tipo de
cada vigencia ganha um intervalo de anos, em duas leituras (rodada "propulsao e
comex"):

**Entrada**

- combustao (gasolina, flex, diesel): o inicio da vigencia -- a P2 ja' decidiu o
  que valia antes do PBE, e a transicao flex segue sem data;
- eletrificado, nesta ordem:
  1. fonte datada em `dados/referencia/propulsao_fontes.csv` (lancamento,
     producao ou presenca; `plano` nao conta) -> `fonte_datada`; onde existe,
     manda sobre o ano do PBE;
  2. primeira tabela do PBE com uma versao daquele tipo -> `pbe_ano`, desde que
     um ano com coluna de propulsao (2021 em diante), dentro da vigencia e antes
     da primeira aparicao, mostre o modelo sem o tipo. O marcador no nome prova
     presenca, nao ausencia. A defasagem medida do PBE (`defasagem_pbe`) abre
     as duas leituras: com direcao dominante, a longa usa o ano mais cedo e a
     curta o mais tarde entre `pbe_ano` e `pbe_ano +- 1`; sem direcao, as duas
     ficam com `pbe_ano`;
  3. senao, o inicio da vigencia -> `vigencia_sem_datacao`;
- vigencia so' com tipos eletrificados: o primeiro a entrar, no inicio dela
  (`vigencia`) -- o modelo nao vende sem propulsao.

**Saida**, para todo tipo, com as mesmas fontes:

- presenca: o tipo numa tabela do PBE do ano (coluna de 2021 em diante; antes,
  so' o marcador no nome produz tipo eletrificado), fonte datada, ou o proprio
  ano de entrada;
- ausencia, so' de 2021 em diante: o modelo esta' no PBE do ano, sem o tipo, ou
  fonte datada de fim de venda ou de importacao (`fim`). Modelo ausente do PBE
  nao informa nada; tipo que some e volta e' lacuna, nao saida -- conta so' a
  ausencia depois da ultima presenca;
- **guarda** (rodada "pbe, comex e calendario"): ausencia no PBE nao prova saida
  no ano em que ha', sem casamento, versao da mesma marca e do mesmo tipo cujo
  nome contem o da chave e que nao tem decisao de casamento
  (`comum/pbe_variantes.py`): o `E-208 GT` fora da chave 208 nao tira o `bev`;
- **longa**: o tipo fica ate' o ano da primeira ausencia depois da ultima
  presenca (o estoque do ano-modelo anterior ainda vende) e sai no seguinte;
- **curta**: fica ate' o ano da ultima presenca e sai no seguinte. Na combustao,
  sem fonte datada de fim, a curta segue a longa ate' 2020: antes da coluna de
  propulsao, a ausencia de presenca no PBE nao data a saida;
- sem evidencia de ausencia, as duas mantem o tipo ate' o fim da vigencia.

Cada ano de PBE vale para a vigencia com mais meses nele. A tabela anual tem uma
linha por `(marca, modelo, segmento, vigencia_inicio, ano)`, com as unidades do
painel nos meses daquela vigencia naquele ano.
"""

from __future__ import annotations

import pandas as pd

from . import classificacao
from .fase2 import CHAVE, PROCEDENCIAS

COMBUSTAO = frozenset({"gasolina", "flex", "diesel"})
LEVES = frozenset({"mhev", "hibrido_indefinido"})
PRIMEIRO_ANO_COLUNA = 2021  # o PBE tem coluna de propulsao a partir daqui
# tipo da classificacao -> valores do PBE que contam como versao daquele tipo
FAMILIA_PBE = {"hibrido_indefinido": {"hev", "mhev"}, "mhev": {"mhev", "hev"}}
DATAS_DE_PRESENCA = ("lancamento", "producao", "presenca")
DATA_DE_FIM = "fim"
# do mais fraco para o mais forte: a linha do ano leva a mais fraca entre os tipos
FONTES_TEMPORAIS = ("vigencia_sem_datacao", "pbe_ano", "fonte_datada", "vigencia")
LEITURAS = ("longa", "curta")
CHAVE_ANUAL = CHAVE + ["vigencia_inicio", "ano"]
COLUNAS = CHAVE_ANUAL + ["vigencia_fim", "unidades", "propulsao_no_ano",
                         "eletrificacao_no_ano", "propulsao_no_ano_curta",
                         "eletrificacao_no_ano_curta", "fonte_temporal", "entrada_dos_tipos",
                         "saida_dos_tipos", "procedencia_propulsao"]
COLUNAS_TIPOS = CHAVE + ["vigencia_inicio", "vigencia_fim", "tipo", "entrada_longa",
                         "entrada_curta", "fonte_temporal", "ultimo_ano_longo",
                         "ultimo_ano_curto", "fonte_saida", "anos_presenca", "anos_ausencia",
                         "anos_guardados"]


def _ano(mes: str) -> int:
    return int(mes[:4])


def _meses_no_ano(inicio: str, fim: str, ano: int) -> int:
    primeiro = max(_ano(inicio) * 12 + int(inicio[5:7]), ano * 12 + 1)
    ultimo = min(_ano(fim) * 12 + int(fim[5:7]), ano * 12 + 12)
    return max(0, ultimo - primeiro + 1)


def anos_da_vigencia(vigencia: pd.Series, outras: pd.DataFrame) -> set[int]:
    """Anos de PBE que valem para a vigencia: aqueles em que ela tem mais meses
    que qualquer outra vigencia do modelo (empate fica com a mais nova)."""
    saida = set()
    for ano in range(_ano(vigencia["vigencia_inicio"]), _ano(vigencia["vigencia_fim"]) + 1):
        meus = _meses_no_ano(vigencia["vigencia_inicio"], vigencia["vigencia_fim"], ano)
        deles = [_meses_no_ano(i, f, ano) for i, f in
                 zip(outras["vigencia_inicio"], outras["vigencia_fim"])
                 if i != vigencia["vigencia_inicio"]]
        maior = max(deles, default=0)
        if meus > maior or (meus == maior and meus > 0 and all(
                i < vigencia["vigencia_inicio"] for i in outras["vigencia_inicio"]
                if i != vigencia["vigencia_inicio"])):
            saida.add(ano)
    return saida


def _fontes_do_tipo(fontes: pd.DataFrame, tipo: str, tipos_data, inicio: int,
                    fim: int) -> list[int]:
    return sorted({_ano(d) for d, t, k in zip(fontes["data_fonte"], fontes["tipo_propulsao"],
                                               fontes["tipo_data_fonte"])
                   if t == tipo and k in tipos_data and inicio <= _ano(d) <= fim})


# ------------------------------------------------------- defasagem do PBE


def defasagem_pbe(fontes: pd.DataFrame, casado: pd.DataFrame
                  ) -> tuple[pd.DataFrame, int]:
    """Tabela `pbe_ano - ano da fonte` dos tipos eletrificados que tem fonte datada
    e ano de PBE, e a direcao dominante (-1, 0 ou +1).

    A direcao sai so' dos casos comparaveis: fonte de 2021 em diante, quando o PBE
    ja' tinha coluna de propulsao. Antes disso, o primeiro ano de PBE de um tipo sem
    marcador e' 2021 por construcao (a tabela nao o via), e a diferenca mede a
    cegueira do PBE, nao a defasagem. Ha' direcao quando mais da metade dos casos
    comparaveis tem o mesmo sinal.
    """
    pbe = casado[casado["marca"] != ""].assign(ano=lambda c: c["ano_pbe"].astype(int))
    datas = fontes[fontes["tipo_data_fonte"].isin(DATAS_DE_PRESENCA)
                   & ~fontes["tipo_propulsao"].isin(COMBUSTAO)]
    linhas = []
    for (marca, modelo, segmento, tipo), grupo in datas.groupby(CHAVE + ["tipo_propulsao"]):
        ano_fonte = min(_ano(d) for d in grupo["data_fonte"])
        vistos = pbe[(pbe["marca"] == marca) & (pbe["modelo"] == modelo)
                     & (pbe["segmento"] == segmento)
                     & pbe["valor_taxonomia"].isin(FAMILIA_PBE.get(tipo, {tipo}))]["ano"]
        if vistos.empty:
            continue
        primeiro = int(vistos.min())
        linhas.append({"marca": marca, "modelo": modelo, "segmento": segmento, "tipo": tipo,
                       "ano_fonte": ano_fonte, "pbe_ano": primeiro,
                       "diferenca": primeiro - ano_fonte,
                       "comparavel": ano_fonte >= PRIMEIRO_ANO_COLUNA})
    tabela = pd.DataFrame(linhas, columns=["marca", "modelo", "segmento", "tipo", "ano_fonte",
                                           "pbe_ano", "diferenca", "comparavel"])
    comparaveis = tabela.loc[tabela["comparavel"], "diferenca"]
    direcao = 0
    if len(comparaveis):
        if (comparaveis > 0).sum() > len(comparaveis) / 2:
            direcao = 1
        elif (comparaveis < 0).sum() > len(comparaveis) / 2:
            direcao = -1
    return tabela, direcao


# ------------------------------------------------------------- por tipo


def tipos_da_vigencia(vigencia: pd.Series, outras: pd.DataFrame, pbe: pd.DataFrame,
                      fontes: pd.DataFrame, direcao: int = 0,
                      guardados: set[tuple[int, str]] | None = None) -> list[dict]:
    """Uma linha por tipo da vigencia: entrada e ultimo ano, nas duas leituras.

    `outras`: as vigencias do modelo (para repartir os anos de PBE); `pbe`: linhas
    do casamento da chave, com `ano`; `fontes`: linhas de `propulsao_fontes.csv` da
    chave; `direcao`: a de `defasagem_pbe`; `guardados`: (ano, valor do PBE) em que
    ha' versao candidata sem decisao de casamento (`pbe_variantes.guardas`).
    """
    guardados = guardados or set()
    inicio, fim = _ano(vigencia["vigencia_inicio"]), _ano(vigencia["vigencia_fim"])
    tipos = [t for t in vigencia["propulsao_na_vigencia"].split("+") if t]
    # a entrada olha o modelo inteiro no PBE (o tipo visto antes da vigencia entra no
    # inicio dela); presenca e ausencia, so' os anos de PBE desta vigencia
    anos_do_modelo = set(pbe["ano"])
    meus = pbe[pbe["ano"].isin(anos_da_vigencia(vigencia, outras))]
    na_tabela = set(meus["ano"])
    entrada: dict[str, tuple[int, int, str]] = {}
    for tipo in tipos:
        if tipo in COMBUSTAO:
            entrada[tipo] = (inicio, inicio, "vigencia")
            continue
        datada = _fontes_do_tipo(fontes, tipo, DATAS_DE_PRESENCA, -1, fim)
        if datada:
            ano = max(datada[0], inicio)
            entrada[tipo] = (ano, ano, "fonte_datada")
            continue
        vistos = pbe.loc[pbe["valor_taxonomia"].isin(FAMILIA_PBE.get(tipo, {tipo})), "ano"]
        primeiro = int(vistos.min()) if len(vistos) else None
        if primeiro is not None and primeiro <= inicio:
            entrada[tipo] = (inicio, inicio, "pbe_ano")
        elif primeiro is not None and primeiro <= fim and any(
                inicio <= a < primeiro and a >= PRIMEIRO_ANO_COLUNA for a in anos_do_modelo):
            outro = primeiro - 1 if direcao > 0 else primeiro + 1 if direcao < 0 else primeiro
            longa, curta = sorted((primeiro, outro))
            entrada[tipo] = (max(longa, inicio), min(max(curta, inicio), fim), "pbe_ano")
        else:
            entrada[tipo] = (inicio, inicio, "vigencia_sem_datacao")
    if entrada and not set(entrada) & COMBUSTAO:
        primeiro = min(e[0] for e in entrada.values())
        entrada.update({t: (inicio, inicio, "vigencia") for t, e in entrada.items()
                        if e[0] == primeiro})

    linhas = []
    for tipo in tipos:
        entrada_longa, entrada_curta, fonte = entrada[tipo]
        familia = FAMILIA_PBE.get(tipo, {tipo})
        com_tipo = set(meus.loc[meus["valor_taxonomia"].isin(familia), "ano"])
        presenca = com_tipo | set(_fontes_do_tipo(fontes, tipo, DATAS_DE_PRESENCA, inicio, fim))
        presenca.add(entrada_curta)
        # "com outras versoes": o modelo esta' no PBE do ano com versao de outro tipo da
        # vigencia; versao so' de tipo que a vigencia nao tem contradiz a vigencia, nao
        # informa ausencia (o Tank 300 `hev` da proposta aparece no PBE so' como PHEV)
        outras_familias = set().union(*(FAMILIA_PBE.get(u, {u}) for u in tipos if u != tipo))
        com_outro = set(meus.loc[meus["valor_taxonomia"].isin(outras_familias), "ano"])
        ausencia = {a for a in na_tabela if a >= PRIMEIRO_ANO_COLUNA and a not in com_tipo
                    and a in com_outro}
        guardado = {a for a in ausencia if any((a, v) in guardados for v in familia)}
        ausencia -= guardado
        fim_fonte = set(_fontes_do_tipo(fontes, tipo, (DATA_DE_FIM,), inicio, fim))
        ausencia |= fim_fonte
        ultima = max(presenca)
        depois = sorted(a for a in ausencia if a > ultima)
        if depois:
            ultimo_longo, ultimo_curto = depois[0], ultima
            origem = "+".join(o for o, anos in (("pbe", ausencia - fim_fonte),
                                                 ("fonte", fim_fonte))
                              if anos & set(depois))
        else:
            ultimo_longo = ultimo_curto = fim
            origem = ""
        if tipo in COMBUSTAO and not fim_fonte:
            # antes da coluna de propulsao o PBE nao data a saida da combustao
            ultimo_curto = max(ultimo_curto, min(ultimo_longo, PRIMEIRO_ANO_COLUNA - 1))
        linhas.append({
            **{c: vigencia[c] for c in CHAVE}, "vigencia_inicio": vigencia["vigencia_inicio"],
            "vigencia_fim": vigencia["vigencia_fim"], "tipo": tipo,
            "entrada_longa": entrada_longa, "entrada_curta": entrada_curta,
            "fonte_temporal": fonte, "ultimo_ano_longo": min(ultimo_longo, fim),
            "ultimo_ano_curto": min(ultimo_curto, fim), "fonte_saida": origem,
            "anos_presenca": ";".join(map(str, sorted(presenca))),
            "anos_ausencia": ";".join(map(str, sorted(ausencia))),
            "anos_guardados": ";".join(map(str, sorted(guardado)))})
    return linhas


def tabela_de_tipos(dim: pd.DataFrame, casado: pd.DataFrame, fontes: pd.DataFrame,
                    direcao: int = 0, guardas: pd.DataFrame | None = None) -> pd.DataFrame:
    """Uma linha por (vigencia, tipo), com entrada e ultimo ano nas duas leituras.
    `guardas`: `pbe_variantes.guardas` (chave, ano, valor_taxonomia)."""
    pbe = casado[casado["marca"] != ""].assign(ano=lambda c: c["ano_pbe"].astype(int))
    pbe_por_chave = {k: g for k, g in pbe.groupby(CHAVE)}
    guardados: dict[tuple, set] = {}
    if guardas is not None:
        for r in guardas.itertuples(index=False):
            guardados.setdefault((r.marca, r.modelo, r.segmento), set()).add(
                (int(r.ano), r.valor_taxonomia))
    fontes_por_chave = {k: g for k, g in fontes.groupby(CHAVE)}
    classificadas = dim[dim["propulsao_na_vigencia"] != ""]
    vigencias_por_chave = {k: g for k, g in classificadas.groupby(CHAVE)}
    linhas = []
    for _, vigencia in classificadas.iterrows():
        chave = tuple(vigencia[CHAVE])
        linhas += tipos_da_vigencia(vigencia, vigencias_por_chave[chave],
                                    pbe_por_chave.get(chave, pbe.iloc[0:0]),
                                    fontes_por_chave.get(chave, fontes.iloc[0:0]), direcao,
                                    guardados.get(chave, set()))
    return pd.DataFrame(linhas, columns=COLUNAS_TIPOS)


# ------------------------------------------------------------ tabela anual


def _pior(valores, ordem) -> str:
    """O mais fraco dos valores; `ordem` vai do mais fraco ao mais forte."""
    return min(valores, key=ordem.index) if valores else ""


def unidades_por_vigencia_ano(dim: pd.DataFrame, painel: pd.DataFrame) -> pd.DataFrame:
    """Unidades do painel nos meses de cada vigencia, por ano."""
    meses = (painel[painel["unidades"] > 0]
             .groupby(CHAVE + ["mes_ref"], as_index=False)["unidades"].sum())
    juntos = meses.merge(dim[CHAVE + ["vigencia_inicio", "vigencia_fim",
                                      "procedencia_propulsao"]], on=CHAVE)
    juntos = juntos[(juntos["mes_ref"] >= juntos["vigencia_inicio"])
                    & (juntos["mes_ref"] <= juntos["vigencia_fim"])]
    if juntos["unidades"].sum() != meses["unidades"].sum():
        raise AssertionError("a juncao com o painel perdeu ou duplicou unidades")
    juntos = juntos.assign(ano=juntos["mes_ref"].str[:4].astype(int))
    return (juntos.groupby(CHAVE_ANUAL + ["vigencia_fim", "procedencia_propulsao"],
                           as_index=False)["unidades"].sum())


def anual(dim: pd.DataFrame, tipos: pd.DataFrame, painel: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (chave, vigencia_inicio, ano) com unidades no painel."""
    base = unidades_por_vigencia_ano(dim, painel)
    por_vigencia = {k: g for k, g in tipos.groupby(CHAVE + ["vigencia_inicio"])}
    linhas = []
    for _, r in base.iterrows():
        ano = int(r["ano"])
        t = por_vigencia.get((r["marca"], r["modelo"], r["segmento"], r["vigencia_inicio"]))
        if t is None:
            longa = curta = pd.DataFrame(columns=COLUNAS_TIPOS)
        else:
            longa = t[(t["entrada_longa"] <= ano) & (t["ultimo_ano_longo"] >= ano)]
            curta = t[(t["entrada_curta"] <= ano) & (t["ultimo_ano_curto"] >= ano)]
        propulsao = classificacao.ordenar_propulsao("+".join(longa["tipo"]))
        propulsao_curta = classificacao.ordenar_propulsao("+".join(curta["tipo"]))
        if propulsao and not propulsao_curta:
            # o modelo vende no ano: a leitura curta nao pode deixa-lo sem tipo (lacuna
            # do PBE entre a ultima presenca de um tipo e a entrada do seguinte)
            propulsao_curta = propulsao
        eletrificados = longa[~longa["tipo"].isin(COMBUSTAO)]
        saem = (t[(t["ultimo_ano_longo"] < _ano(r["vigencia_fim"]))
                  | (t["ultimo_ano_curto"] < _ano(r["vigencia_fim"]))]
                if t is not None else pd.DataFrame(columns=COLUNAS_TIPOS))
        linhas.append({
            **{c: r[c] for c in CHAVE_ANUAL}, "vigencia_fim": r["vigencia_fim"],
            "unidades": int(r["unidades"]), "propulsao_no_ano": propulsao,
            "eletrificacao_no_ano": classificacao.eletrificacao(propulsao),
            "propulsao_no_ano_curta": propulsao_curta,
            "eletrificacao_no_ano_curta": classificacao.eletrificacao(propulsao_curta),
            "fonte_temporal": (_pior(list(eletrificados["fonte_temporal"]),
                                     list(FONTES_TEMPORAIS))
                               or ("vigencia" if len(longa) else "")),
            "entrada_dos_tipos": "; ".join(
                f"{x['tipo']}={x['entrada_longa']}"
                + (f"/{x['entrada_curta']}" if x["entrada_curta"] != x["entrada_longa"] else "")
                + f" {x['fonte_temporal']}"
                for _, x in longa.sort_values("tipo", key=lambda s: s.map(
                    classificacao.PROPULSOES.index)).iterrows()),
            "saida_dos_tipos": "; ".join(
                f"{x['tipo']}: longa {x['ultimo_ano_longo']}, curta {x['ultimo_ano_curto']} "
                f"({x['fonte_saida']})" for _, x in saem.iterrows()),
            "procedencia_propulsao": r["procedencia_propulsao"]})
    return (pd.DataFrame(linhas, columns=COLUNAS)
            .sort_values(CHAVE_ANUAL).reset_index(drop=True))


# --------------------------------------------------------------- validacoes


def problemas(tabela: pd.DataFrame, dim: pd.DataFrame, tipos: pd.DataFrame,
              painel: pd.DataFrame) -> list[str]:
    """Uma linha por vigencia-ano com unidades, unidades iguais ao painel nos meses
    da vigencia, tipos so' da vigencia, leitura curta contida na longa, nenhum ano
    sem propulsao, e o intervalo de cada tipo continuo e dentro da vigencia."""
    saida = []
    esperado = unidades_por_vigencia_ano(dim, painel).set_index(CHAVE_ANUAL)["unidades"]
    obtido = tabela.set_index(CHAVE_ANUAL)["unidades"]
    if obtido.index.duplicated().any():
        saida.append("vigencia-ano repetida")
    faltam = esperado.index.difference(obtido.index)
    sobram = obtido.index.difference(esperado.index)
    saida += [f"{'/'.join(map(str, k))}: vigencia-ano do painel sem linha" for k in faltam[:20]]
    saida += [f"{'/'.join(map(str, k))}: linha sem unidades no painel" for k in sobram[:20]]
    comuns = esperado.index.intersection(obtido.index)
    diferentes = comuns[esperado[comuns].to_numpy() != obtido[comuns].to_numpy()]
    saida += [f"{'/'.join(map(str, k))}: unidades diferem do painel" for k in diferentes[:20]]
    conjuntos = {tuple(r[CHAVE + ["vigencia_inicio"]]): set(r["propulsao_na_vigencia"].split("+"))
                 for _, r in dim[dim["propulsao_na_vigencia"] != ""].iterrows()}
    for _, linha in tabela.iterrows():
        chave = tuple(linha[CHAVE + ["vigencia_inicio"]])
        if chave not in conjuntos:
            continue
        nome = f"{'/'.join(chave)} {linha['ano']}"
        longa = set(filter(None, linha["propulsao_no_ano"].split("+")))
        curta = set(filter(None, linha["propulsao_no_ano_curta"].split("+")))
        if not longa or not curta:
            saida.append(f"{nome}: ano sem propulsao numa leitura")
        if not longa <= conjuntos[chave]:
            saida.append(f"{nome}: tipo fora da vigencia")
        if not curta <= longa:
            saida.append(f"{nome}: leitura curta com tipo que a longa nao tem")
    for _, t in tipos.iterrows():
        inicio, fim = _ano(t["vigencia_inicio"]), _ano(t["vigencia_fim"])
        nome = f"{t['marca']}/{t['modelo']} {t['vigencia_inicio']} {t['tipo']}"
        if not (inicio <= t["entrada_longa"] <= t["entrada_curta"] <= fim):
            saida.append(f"{nome}: entradas fora de ordem ou da vigencia")
        if not (t["ultimo_ano_curto"] <= t["ultimo_ano_longo"] <= fim):
            saida.append(f"{nome}: saidas fora de ordem ou da vigencia")
        if t["ultimo_ano_longo"] < t["entrada_longa"]:
            saida.append(f"{nome}: sai antes de entrar")
    return saida


# ---------------------------------------------------------- uso-teste e banda

NIVEIS = ("nenhuma", "parcial", "total", "nao_classificado")
TETOS = ("piso", "teto", "teto_sem_mhev", "teto_estrito")


def _meses_no_ultimo(painel: pd.DataFrame) -> tuple[int, int]:
    ultimo = painel["mes_ref"].max()
    return int(ultimo[:4]), int(ultimo[5:7])


def _participacao(unidades: pd.DataFrame, coluna: str) -> pd.DataFrame:
    t = unidades.assign(nivel=unidades[coluna].replace("", "nao_classificado"))
    largura = t.pivot_table(index="ano", columns="nivel", values="unidades", aggfunc="sum",
                            fill_value=0).reindex(columns=list(NIVEIS), fill_value=0)
    return (100 * largura.div(largura.sum(axis=1), axis=0)).round(2)


def uso_teste(dim: pd.DataFrame, tabela: pd.DataFrame, painel: pd.DataFrame,
              inicio: int = 2015) -> pd.DataFrame:
    """Participacao de cada nivel de eletrificacao nas unidades, por ano (%): pelo
    conjunto da vigencia (o uso errado) e pela tabela anual nas duas leituras."""
    base = unidades_por_vigencia_ano(dim, painel).merge(
        dim[CHAVE + ["vigencia_inicio", "eletrificacao_na_vigencia"]],
        on=CHAVE + ["vigencia_inicio"])
    leituras = {"vigencia": _participacao(base[base["ano"] >= inicio],
                                          "eletrificacao_na_vigencia"),
                "longa": _participacao(tabela[tabela["ano"] >= inicio], "eletrificacao_no_ano"),
                "curta": _participacao(tabela[tabela["ano"] >= inicio],
                                       "eletrificacao_no_ano_curta")}
    ultimo_ano, meses = _meses_no_ultimo(painel)
    linhas = []
    for leitura, quadro in leituras.items():
        for ano in quadro.index:
            for nivel in NIVEIS:
                linhas.append({"ano": ano, "meses": meses if ano == ultimo_ano else 12,
                               "leitura": leitura, "nivel": nivel,
                               "pct": quadro.loc[ano, nivel]})
    return pd.DataFrame(linhas)


def _eletrificados(propulsao: str) -> set[str]:
    return {t for t in propulsao.split("+") if t} - COMBUSTAO


def banda(tabela: pd.DataFrame, painel: pd.DataFrame, inicio: int = 2015) -> pd.DataFrame:
    """Piso e tres tetos da eletrificacao, por ano e leitura (% das unidades do painel).

    `piso`: `total`; `teto`: `total` + `parcial`; `teto_sem_mhev`: tira do
    `parcial` a vigencia-ano cujo unico tipo eletrificado e' `mhev`;
    `teto_estrito`: tira a vigencia-ano cujos tipos eletrificados sao so' `mhev` ou
    `hibrido_indefinido`.
    """
    ultimo_ano, meses = _meses_no_ultimo(painel)
    linhas = []
    for leitura, sufixo in (("longa", ""), ("curta", "_curta")):
        t = tabela[tabela["ano"] >= inicio]
        eletrificacao, propulsao = t[f"eletrificacao_no_ano{sufixo}"], t[f"propulsao_no_ano{sufixo}"]
        tipos = propulsao.map(_eletrificados)
        so_mhev = tipos.map(lambda e: e == {"mhev"})
        so_leve = tipos.map(lambda e: bool(e) and e <= LEVES)
        total = t["unidades"].groupby(t["ano"]).sum()
        partes = {
            "piso": eletrificacao == "total",
            "teto": eletrificacao.isin(["total", "parcial"]),
            "teto_sem_mhev": eletrificacao.isin(["total", "parcial"]) & ~so_mhev,
            "teto_estrito": eletrificacao.isin(["total", "parcial"]) & ~so_leve}
        for ano in sorted(total.index):
            linha = {"ano": ano, "meses": meses if ano == ultimo_ano else 12, "leitura": leitura}
            for nome, mascara in partes.items():
                linha[nome] = round(100 * t.loc[mascara & (t["ano"] == ano), "unidades"].sum()
                                    / total[ano], 2)
            linhas.append(linha)
    return pd.DataFrame(linhas, columns=["ano", "meses", "leitura", *TETOS])
