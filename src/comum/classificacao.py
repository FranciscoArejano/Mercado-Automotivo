"""Dimensao de classificacao de modelo -- fase 1, rascunho para adjudicacao.

Nada aqui grava fato. O modulo combina tres fontes de proposta, cada uma com a
sua confianca, e entrega uma linha por modelo-vigencia para o pesquisador
decidir:

1. **Regra sobre a fonte** (`config/regras_classificacao.csv`, ids `S..`): a
   carroceria sai do sub-segmento em que a propria Fenabrave listou o modelo.
2. **Regra por nome** (ids `N..`): marcadores de propulsao que a fabricante pos
   no nome comercial (`E-JS1`, `EX5 EM-I`, `330E`, `EX30`). Implementadas aqui,
   uma funcao por id; o teste confere que codigo e CSV tem os mesmos ids e que o
   exemplo de cada linha do CSV dispara a regra.
3. **Conhecimento do assistente** (`dados/referencia/classificacao_proposta_
   assistente.csv`): o resto, sempre com confianca por atributo e marcado como
   proposta.

O que nenhuma das tres resolve fica vazio, com confianca `baixa`.

A fonte nao separa unidades por versao: um modelo vendido em flex e em hibrido
e' um numero so'. Por isso `propulsao_oferecida` e' conjunto, e `eletrificacao`
diz se o conjunto e' so' eletrificado, misto ou so' combustao -- nunca quantas
unidades foram de cada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from . import config

CHAVE = ["marca", "modelo", "segmento"]

# `mhev` (hibrido leve) e `reev` (eletrico com extensor) entraram por decisao do
# pesquisador em 2026-10-01, assim como `caminhao_leve` na carroceria.
# `hibrido_indefinido` (decisao 1 da rodada das seis decisoes): o PBE diz Hibrido
# e nem o nome da versao nem fonte dizem se e' leve ou pleno.
PROPULSOES = ("gasolina", "flex", "diesel", "mhev", "hibrido_indefinido", "hev", "phev", "reev",
              "bev")
# Tracao eletrica: o modelo so' com estas e' `total`.
ELETRIFICADAS = frozenset({"hev", "phev", "reev", "bev"})
# Contam para `parcial` mas nunca para `total`: o hibrido leve nao roda em modo
# eletrico, entao sempre vem com combustao. O `hibrido_indefinido` conta como
# `mhev`, de proposito: `total` exige evidencia positiva de hibrido pleno, plug-in
# ou eletrico.
ELETRIFICACAO_PARCIAL = frozenset({"mhev", "hibrido_indefinido"})
CARROCERIAS = ("hatch", "sedan", "suv", "picape", "minivan", "furgao", "caminhao_leve",
               "perua", "esportivo")
# Carroceria da fonte que o conhecimento pode REFINAR, nao contradizer (regra
# S11): a fonte poe caminhao leve em Furgoes porque nao tem a categoria.
REFINAMENTOS = {("furgao", "caminhao_leve")}
ORIGENS = ("nacional", "importado", "ambos")
NIVEIS = ("alta", "media", "baixa")

# Segunda carroceria com esta fracao do volume da vigencia rebaixa a proposta.
FRACAO_SEGUNDA_CARROCERIA = 0.10
# Abaixo desta fracao de unidades com sub-segmento de carroceria, a fonte
# classificou o modelo em poucos meses: a carroceria dela vale, mas com cautela.
COBERTURA_MINIMA_SUB_SEGMENTO = 0.10

NAO_CLASSIFICADO = "nao_classificado"

FONTE_SUB_SEGMENTO = "sub-segmento da fonte"
FONTE_NOME = "regra por nome"
FONTE_CONHECIMENTO = "conhecimento do assistente (proposta, nao fato)"
FONTE_NENHUMA = "sem proposta"


# ---------------------------------------------------------------- regras


def carregar_regras() -> pd.DataFrame:
    return pd.read_csv(config.REGRAS_CLASSIFICACAO, dtype=str, keep_default_na=False)


def mapa_sub_segmento(regras: pd.DataFrame) -> dict[str, str]:
    """Sub-segmento da fonte -> carroceria, lido das regras `S..` do CSV.

    Valor `(nenhum)` quer dizer que o sub-segmento nao e' carroceria (S09,
    Veiculos de Entrada, e' faixa de preco) e fica fora da conta.
    """
    mapa: dict[str, str] = {}
    for _, regra in regras[regras["tipo"] == "sub_segmento_da_fonte"].iterrows():
        condicao = regra["condicao"]
        lista = re.search(r"in \((.*)\)", condicao)
        igual = re.search(r"= (.*)$", condicao)
        nomes = lista.group(1).split("; ") if lista else [igual.group(1)] if igual else []
        if not nomes:
            raise ValueError(f"regra {regra['id']}: condicao ilegivel: {condicao!r}")
        for nome in nomes:
            if nome in mapa:
                raise ValueError(f"sub-segmento {nome!r} em duas regras")
            mapa[nome.strip()] = regra["valor"]
    return mapa


def _n01(marca: str, modelo: str) -> bool:
    return modelo.startswith("E-")


def _n02(marca: str, modelo: str) -> bool:
    return "EM-I" in modelo or "DM-I" in modelo


def _n03(marca: str, modelo: str) -> bool:
    return marca == "BMW" and re.fullmatch(r"\d{3}E", modelo) is not None


def _n04(marca: str, modelo: str) -> bool:
    return marca == "VOLVO" and re.match(r"E[XC]\d", modelo) is not None


# id -> (teste, propulsao). O texto, o exemplo e a justificativa ficam no CSV.
REGRAS_NOME = {
    "N01": (_n01, "bev"),
    "N02": (_n02, "phev"),
    "N03": (_n03, "phev"),
    "N04": (_n04, "bev"),
}


def propulsao_por_nome(marca: str, modelo: str) -> tuple[str, str] | None:
    """(id da regra, propulsao) da primeira regra por nome que casa, ou None."""
    for ident, (teste, valor) in REGRAS_NOME.items():
        if teste(marca, modelo):
            return ident, valor
    return None


# ------------------------------------------------------------- derivacoes


def eletrificacao(propulsao: str) -> str:
    """`total` so' tracao eletrica, `parcial` mistura, `nenhuma` so' combustao.

    Hibrido leve (`mhev`) conta como `parcial`, mesmo sem outra eletrificada ao
    lado: juntar a `hev` superestimaria, omitir subestimaria. `hibrido_indefinido`
    conta como `mhev`.
    """
    conjunto = {p for p in propulsao.split("+") if p}
    if not conjunto:
        return ""
    eletricas = conjunto & ELETRIFICADAS
    if eletricas == conjunto:
        return "total"
    return "parcial" if eletricas or conjunto & ELETRIFICACAO_PARCIAL else "nenhuma"


def ordenar_propulsao(propulsao: str) -> str:
    conjunto = {p for p in propulsao.split("+") if p}
    return "+".join(p for p in PROPULSOES if p in conjunto)


def menor_confianca(*niveis: str) -> str:
    """O pior dos niveis; nivel vazio conta como `baixa`."""
    return max((n or "baixa" for n in niveis), key=NIVEIS.index, default="baixa")


# ------------------------------------------------------------------ escopo


def totais_por_modelo(painel: pd.DataFrame) -> pd.DataFrame:
    """Volume, primeiro e ultimo mes com unidades, por modelo, maior primeiro."""
    # Oito chaves do painel so' tem linhas com zero unidades; ficam na lista,
    # com volume zero e sem meses, para que nenhum modelo suma da conta.
    totais = painel.groupby(CHAVE, as_index=False)["unidades"].sum().rename(
        columns={"unidades": "unidades_totais"})
    positivas = painel[painel["unidades"] > 0]
    janelas = positivas.groupby(CHAVE, as_index=False).agg(
        primeiro_mes=("mes_ref", "min"), ultimo_mes=("mes_ref", "max"))
    totais = totais.merge(janelas, on=CHAVE, how="left")
    totais[["primeiro_mes", "ultimo_mes"]] = totais[["primeiro_mes", "ultimo_mes"]].fillna("")
    totais = totais.sort_values(["unidades_totais"] + CHAVE,
                                ascending=[False, True, True, True], ignore_index=True)
    totais["posicao"] = totais.index + 1
    return totais


def escopo(totais: pd.DataFrame, piso: int) -> pd.Series:
    """Mascara dos modelos a classificar: volume total **acima** do piso."""
    return totais["unidades_totais"] > piso


# ------------------------------------------------------------- vigencias


@dataclass
class Vigencia:
    inicio: str
    fim: str
    proposta: dict


def vigencias_do_modelo(modelo: pd.Series, propostas: pd.DataFrame) -> list[Vigencia]:
    """As vigencias propostas para um modelo, validadas contra a janela dele.

    Linha sem vigencia cobre a vida inteira do modelo. Vigencias nao podem se
    sobrepor nem deixar de fora um mes com unidades -- buraco sem unidades e'
    permitido (GM/SONIC tem onze anos entre dois produtos).
    """
    if propostas.empty:
        return [Vigencia(modelo["primeiro_mes"], modelo["ultimo_mes"], {})]
    lista = []
    for _, linha in propostas.iterrows():
        inicio = linha["vigencia_inicio"] or modelo["primeiro_mes"]
        fim = linha["vigencia_fim"] or modelo["ultimo_mes"]
        if inicio > fim:
            raise ValueError(f"{_nome(modelo)}: vigencia invertida {inicio}..{fim}")
        lista.append(Vigencia(inicio, fim, linha.to_dict()))
    lista.sort(key=lambda v: v.inicio)
    for anterior, seguinte in zip(lista, lista[1:]):
        if seguinte.inicio <= anterior.fim:
            raise ValueError(f"{_nome(modelo)}: vigencias sobrepostas "
                             f"{anterior.inicio}..{anterior.fim} e {seguinte.inicio}..{seguinte.fim}")
    return lista


def conferir_cobertura(modelo: pd.Series, vigencias: list[Vigencia], meses: pd.Series) -> None:
    """Todo mes com unidades do modelo cai em alguma vigencia."""
    fora = sorted(m for m in meses if not any(v.inicio <= m <= v.fim for v in vigencias))
    if fora:
        raise ValueError(f"{_nome(modelo)}: meses com unidades fora de qualquer vigencia: "
                         f"{fora[:5]}{' ...' if len(fora) > 5 else ''}")


def _nome(modelo: pd.Series) -> str:
    return f"{modelo['marca']}/{modelo['modelo']} [{modelo['segmento']}]"


# ------------------------------------------------------------- atributos


def carroceria_da_fonte(linhas: pd.DataFrame, mapa: dict[str, str]) -> dict:
    """Carroceria dominante nos sub-segmentos da fonte dentro de uma vigencia."""
    total = int(linhas["unidades"].sum())
    por_sub = (linhas[linhas["sub_segmento_fonte"].fillna("") != ""]
               .groupby("sub_segmento_fonte")["unidades"].sum()
               .sort_values(ascending=False))
    descricao = "; ".join(
        f"{sub} {100 * u / total:.0f}%" for sub, u in por_sub.items() if u > 0) if total else ""
    corpos = {}
    for sub, unidades in por_sub.items():
        if sub not in mapa:
            raise ValueError(f"sub-segmento {sub!r} sem regra em regras_classificacao.csv")
        corpo = mapa[sub]
        if corpo != "(nenhum)" and unidades > 0:
            corpos[corpo] = corpos.get(corpo, 0) + int(unidades)
    classificadas = sum(corpos.values())
    resultado = {"sub_segmentos_fonte": descricao, "carroceria": "", "confianca": "",
                 "nota": "", "cobertura": classificadas / total if total else 0.0}
    if not classificadas:
        return resultado
    ordem = sorted(corpos.items(), key=lambda kv: -kv[1])
    resultado["carroceria"] = ordem[0][0]
    resultado["confianca"] = "alta"
    notas = []
    if len(ordem) > 1 and ordem[1][1] / classificadas >= FRACAO_SEGUNDA_CARROCERIA:
        resultado["confianca"] = "media"
        notas.append("Fonte divide: " + ", ".join(
            f"{c} {100 * u / classificadas:.0f}%" for c, u in ordem))
    if resultado["cobertura"] < COBERTURA_MINIMA_SUB_SEGMENTO:
        resultado["confianca"] = "media"
        notas.append(f"So' {100 * resultado['cobertura']:.1f}% das unidades aparecem em "
                     "sub-segmento de carroceria")
    resultado["nota"] = "; ".join(notas)
    return resultado


def classificar(painel: pd.DataFrame, propostas: pd.DataFrame, regras: pd.DataFrame,
                piso: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(rascunho, nao_classificados).

    `rascunho` tem uma linha por modelo-vigencia dos modelos acima do piso,
    ordenada por volume total decrescente. `nao_classificados` lista o resto.
    """
    _validar_propostas(propostas)
    mapa = mapa_sub_segmento(regras)
    totais = totais_por_modelo(painel)
    dentro = escopo(totais, piso)

    chaves_escopo = set(map(tuple, totais.loc[dentro, CHAVE].to_numpy()))
    orfas = set(map(tuple, propostas[CHAVE].to_numpy())) - chaves_escopo
    if orfas:
        raise ValueError(f"propostas para modelos fora do escopo: {sorted(orfas)[:5]}")

    positivas = painel[painel["unidades"] > 0]
    linhas_por_modelo = dict(tuple(positivas.groupby(CHAVE)))
    propostas_por_modelo = dict(tuple(propostas.groupby(CHAVE)))

    saida = []
    for _, modelo in totais[dentro].iterrows():
        chave = tuple(modelo[c] for c in CHAVE)
        linhas = linhas_por_modelo[chave]
        vigencias = vigencias_do_modelo(modelo, propostas_por_modelo.get(chave, propostas.iloc[0:0]))
        conferir_cobertura(modelo, vigencias, linhas["mes_ref"])
        for vigencia in vigencias:
            dentro_vig = linhas[(linhas["mes_ref"] >= vigencia.inicio)
                                & (linhas["mes_ref"] <= vigencia.fim)]
            saida.append(_linha(modelo, vigencia, dentro_vig, mapa))

    rascunho = pd.DataFrame(saida)
    fora = totais[~dentro].copy()
    fora["classificacao"] = NAO_CLASSIFICADO
    return rascunho, fora[["posicao"] + CHAVE + ["unidades_totais", "primeiro_mes",
                                                  "ultimo_mes", "classificacao"]]


def _linha(modelo: pd.Series, vigencia: Vigencia, linhas: pd.DataFrame,
           mapa: dict[str, str]) -> dict:
    proposta = vigencia.proposta
    notas = []

    # propulsao: regra por nome > conhecimento > vazio
    por_nome = propulsao_por_nome(modelo["marca"], modelo["modelo"])
    conhecida = ordenar_propulsao(proposta.get("propulsao_oferecida", ""))
    if por_nome:
        ident, valor = por_nome
        propulsao, conf_prop, fonte_prop = valor, "alta", f"{FONTE_NOME} {ident}"
        if conhecida and conhecida != valor:
            conf_prop = "media"
            notas.append(f"Conhecimento propunha {conhecida}, a regra {ident} da' {valor}")
    elif conhecida:
        propulsao, conf_prop, fonte_prop = (
            conhecida, proposta.get("confianca_propulsao") or "baixa", FONTE_CONHECIMENTO)
    else:
        propulsao, conf_prop, fonte_prop = "", "baixa", FONTE_NENHUMA

    # carroceria: sub-segmento da fonte > conhecimento > vazio. Conhecimento ao
    # lado da fonte e' sinalizacao: pode rebaixar a confianca, nao trocar o valor.
    fonte_sub = carroceria_da_fonte(linhas, mapa)
    conhecida_corpo = proposta.get("carroceria", "")
    conf_corpo_conhecida = proposta.get("confianca_carroceria", "")
    if fonte_sub["carroceria"]:
        carroceria = fonte_sub["carroceria"]
        conf_corpo = menor_confianca(fonte_sub["confianca"], conf_corpo_conhecida or "alta")
        fonte_corpo = f"{FONTE_SUB_SEGMENTO} ({100 * fonte_sub['cobertura']:.0f}% das unidades)"
        if fonte_sub["nota"]:
            notas.append(fonte_sub["nota"])
        if (carroceria, conhecida_corpo) in REFINAMENTOS:
            carroceria = conhecida_corpo
            conf_corpo = conf_corpo_conhecida or "baixa"
            fonte_corpo += f"; refinada por {FONTE_CONHECIMENTO} (S11)"
        elif conhecida_corpo and conhecida_corpo != carroceria:
            conf_corpo = "media"
            notas.append(f"Conhecimento propoe {conhecida_corpo}; fica o valor da fonte")
        elif conf_corpo_conhecida and not conhecida_corpo:
            fonte_corpo += "; sinalizada pelo assistente"
    elif conhecida_corpo:
        carroceria, conf_corpo, fonte_corpo = (
            conhecida_corpo, conf_corpo_conhecida or "baixa", FONTE_CONHECIMENTO)
    else:
        carroceria, conf_corpo, fonte_corpo = "", "baixa", FONTE_NENHUMA

    # origem: so' conhecimento
    origem = proposta.get("origem_producao", "")
    if origem:
        conf_origem, fonte_origem = proposta.get("confianca_origem") or "baixa", FONTE_CONHECIMENTO
    else:
        conf_origem, fonte_origem = "baixa", FONTE_NENHUMA

    if proposta.get("observacao"):
        notas.insert(0, proposta["observacao"])

    return {
        "posicao": int(modelo["posicao"]),
        "marca": modelo["marca"],
        "modelo": modelo["modelo"],
        "segmento": modelo["segmento"],
        "vigencia_inicio": vigencia.inicio,
        "vigencia_fim": vigencia.fim,
        "propulsao_oferecida": propulsao,
        "eletrificacao": eletrificacao(propulsao),
        "carroceria": carroceria,
        "origem_producao": origem,
        "confianca": menor_confianca(conf_prop, conf_corpo, conf_origem),
        "confianca_propulsao": conf_prop,
        "confianca_carroceria": conf_corpo,
        "confianca_origem": conf_origem,
        "fonte_da_proposta": (f"propulsao: {fonte_prop} | carroceria: {fonte_corpo} | "
                              f"origem: {fonte_origem}"),
        "unidades_totais": int(modelo["unidades_totais"]),
        "unidades_na_vigencia": int(linhas["unidades"].sum()),
        "primeiro_mes": modelo["primeiro_mes"],
        "ultimo_mes": modelo["ultimo_mes"],
        "sub_segmentos_fonte": fonte_sub["sub_segmentos_fonte"],
        "observacao": " ".join(n if n.endswith(".") else n + "." for n in notas),
        "decisao_humana": "",
    }


def _validar_propostas(propostas: pd.DataFrame) -> None:
    problemas = []
    for i, linha in propostas.iterrows():
        onde = f"linha {i + 2} ({linha['marca']}/{linha['modelo']})"
        for p in filter(None, linha["propulsao_oferecida"].split("+")):
            if p not in PROPULSOES:
                problemas.append(f"{onde}: propulsao {p!r}")
        if linha["carroceria"] and linha["carroceria"] not in CARROCERIAS:
            problemas.append(f"{onde}: carroceria {linha['carroceria']!r}")
        if linha["origem_producao"] and linha["origem_producao"] not in ORIGENS:
            problemas.append(f"{onde}: origem {linha['origem_producao']!r}")
        for coluna in ("confianca_propulsao", "confianca_carroceria", "confianca_origem"):
            if linha[coluna] and linha[coluna] not in NIVEIS:
                problemas.append(f"{onde}: {coluna} {linha[coluna]!r}")
        for coluna in ("vigencia_inicio", "vigencia_fim"):
            if linha[coluna] and not re.fullmatch(r"\d{4}-\d{2}", linha[coluna]):
                problemas.append(f"{onde}: {coluna} {linha[coluna]!r}")
    if problemas:
        raise ValueError("propostas invalidas:\n  " + "\n  ".join(problemas))


# ------------------------------------------------------------------ resumo


def resumo_por_confianca(rascunho: pd.DataFrame, volume_painel: int) -> pd.DataFrame:
    """Modelo-vigencias, modelos e volume em cada nivel, por atributo.

    As vigencias de um modelo particionam as unidades dele, entao o volume por
    nivel soma o volume classificado. Um modelo com duas vigencias em niveis
    diferentes conta nos dois -- por isso a coluna de modelos nao soma.
    """
    blocos = []
    classificado = rascunho["unidades_na_vigencia"].sum()
    for atributo in ("confianca", "confianca_propulsao", "confianca_carroceria",
                     "confianca_origem"):
        for nivel in NIVEIS:
            parte = rascunho[rascunho[atributo] == nivel]
            blocos.append({
                "atributo": atributo.replace("confianca_", "") if atributo != "confianca"
                else "geral (o pior dos tres)",
                "nivel": nivel,
                "modelo_vigencias": len(parte),
                "modelos": parte[CHAVE].drop_duplicates().shape[0],
                "unidades": int(parte["unidades_na_vigencia"].sum()),
                "pct_do_classificado": round(100 * parte["unidades_na_vigencia"].sum()
                                             / classificado, 2),
                "pct_do_painel": round(100 * parte["unidades_na_vigencia"].sum()
                                       / volume_painel, 2),
            })
    return pd.DataFrame(blocos)
