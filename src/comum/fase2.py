"""Fase 2 da classificacao: do rascunho adjudicado a' dimensao gravada.

O rascunho (`saidas/classificacao_rascunho.xlsx`) e' a fonte de verdade da
adjudicacao: a fase 2 o le e ninguem edita o parquet a' mao. Por linha e por
atributo, nesta precedencia (decisao 6 das seis decisoes):

1. `decisao_humana`, se preenchida para o atributo (`ok` vale para todos;
   `atributo=pendente` deixa o atributo pendente de proposito);
2. senao, `decisao_por_regra`;
3. senao, a proposta original.

As decisoes do pesquisador ficam versionadas em `config/decisoes_humanas.csv`; o
gerador do rascunho as copia para `decisao_humana` (`aplicar_decisoes_humanas`).

Nenhuma linha e' descartada. Cada atributo leva a procedencia do valor:

- `humana` -- decidida pelo pesquisador;
- `regra_fonte_forte` -- decidida ou confirmada por regra com fonte oficial ou
  especializada;
- `regra_fonte_fraca` -- decidida por regra apoiada em fonte fraca, ou sem
  evidencia positiva;
- `proposta` -- proposta original, nunca tocada por checagem;
- `pendente` -- contestada e ainda nao decidida; o valor e' a proposta original.

Os modelos abaixo do piso de volume entram com atributos vazios e procedencia
`nao_classificado`: nenhuma chave do painel fica sem linha.

Na dimensao, a propulsao se chama `propulsao_na_vigencia` (e a eletrificacao,
`eletrificacao_na_vigencia`): e' o conjunto de tudo o que foi oferecido em algum
momento da vigencia, e nao serve para serie temporal -- para isso ha'
`classificacao_propulsao_anual` (`comum/propulsao_anual.py`). O rascunho mantem
`propulsao_oferecida`, e a decisao humana aceita os dois nomes.
"""

from __future__ import annotations

import re

import pandas as pd

from . import classificacao

CHAVE = ["marca", "modelo", "segmento"]
PROCEDENCIAS = ("humana", "regra_fonte_forte", "regra_fonte_fraca", "proposta", "pendente",
                "nao_classificado")
# atributo -> (coluna com o valor depois das regras, coluna de procedencia no rascunho)
ATRIBUTOS = {
    "propulsao_oferecida": ("propulsao_apos_regras", "procedencia_propulsao"),
    "carroceria": ("carroceria", "procedencia_carroceria"),
    "origem_producao": ("origem_apos_regras", "procedencia_origem"),
}
PROCEDENCIA_COLUNA = {"propulsao_oferecida": "procedencia_propulsao",
                      "carroceria": "procedencia_carroceria",
                      "origem_producao": "procedencia_origem"}
ORIGENS = ("nacional", "importado", "ambos")
# nome no rascunho -> nome na dimensao (rodada "propulsao no tempo")
NA_DIMENSAO = {"propulsao_oferecida": "propulsao_na_vigencia",
               "eletrificacao": "eletrificacao_na_vigencia"}
SINONIMOS = {v: k for k, v in NA_DIMENSAO.items()}
CAMPOS_DECISAO = set(ATRIBUTOS) | {"eletrificacao", "vigencia_inicio", "vigencia_fim"}
# `atributo=pendente`: o pesquisador decidiu outro atributo da linha e deixa este
# pendente de proposito (rodada "pbe, comex e calendario": o 2008 tem a propulsao
# decidida e a origem ainda contestada). Sem isso, decisao humana que deixa atributo
# pendente continua sendo erro.
PENDENTE_EXPLICITO = "pendente"
MES = re.compile(r"^\d{4}-\d{2}$")
COLUNAS = CHAVE + ["vigencia_inicio", "vigencia_fim", "propulsao_na_vigencia",
                   "eletrificacao_na_vigencia",
                   "procedencia_propulsao", "carroceria", "procedencia_carroceria",
                   "origem_producao", "procedencia_origem", "vigencia_ajustada_por",
                   "regras_aplicadas", "vigencia_inicio_rascunho"]


class DecisaoInvalida(ValueError):
    """Decisao que a fase 2 nao sabe aplicar sozinha: precisa ser reescrita no rascunho."""


def ler_decisao(texto: str) -> dict:
    """`ok`, `atributo=valor; atributo=valor`, ou as duas coisas. Vazia -> {}.

    `dividir em AAAA-MM` e texto livre nao se aplicam sozinhos: levantam
    `DecisaoInvalida`, para a decisao ser reescrita na sintaxe estruturada (ou a
    vigencia dividida no proprio rascunho).
    """
    decisao: dict = {}
    for parte in (p.strip() for p in texto.split(";")):
        if not parte:
            continue
        if parte.lower() == "ok":
            decisao["ok"] = True
            continue
        if "=" not in parte:
            raise DecisaoInvalida(f"nao estruturada: {texto!r}")
        campo, valor = (x.strip() for x in parte.split("=", 1))
        campo = SINONIMOS.get(campo, campo)
        if campo not in CAMPOS_DECISAO:
            raise DecisaoInvalida(f"campo desconhecido {campo!r} em {texto!r}")
        _validar_valor(campo, valor, texto)
        decisao[campo] = valor
    return decisao


def _validar_valor(campo: str, valor: str, texto: str) -> None:
    if campo in ATRIBUTOS and valor == PENDENTE_EXPLICITO:
        return
    if campo == "propulsao_oferecida":
        tipos = [t for t in valor.split("+") if t]
        if not tipos or any(t not in classificacao.PROPULSOES for t in tipos):
            raise DecisaoInvalida(f"propulsao invalida {valor!r} em {texto!r}")
    elif campo == "carroceria" and valor not in classificacao.CARROCERIAS:
        raise DecisaoInvalida(f"carroceria invalida {valor!r} em {texto!r}")
    elif campo == "origem_producao" and valor not in ORIGENS:
        raise DecisaoInvalida(f"origem invalida {valor!r} em {texto!r}")
    elif campo.startswith("vigencia_") and not MES.match(valor):
        raise DecisaoInvalida(f"mes invalido {valor!r} em {texto!r}")


def hibrido_pela_p5(valor: str, linha: pd.Series) -> str:
    """Na decisao humana, `hibrido_indefinido` e' tipo nao decidido (rodada 12: o 2008
    fica `flex+hibrido_indefinido`, e "se houver fonte que declare o tipo, a P5 o
    resolve"). Se a P5 resolveu o tipo nesta linha, o rotulo dela entra no lugar."""
    tipos = [t for t in valor.split("+") if t]
    if ("hibrido_indefinido" not in tipos
            or "P5" not in str(linha.get("regras_aplicadas", "")).split("+")):
        return valor
    resolvido = set(str(linha.get("propulsao_apos_regras", "")).split("+")) & {"mhev", "hev"}
    if len(resolvido) != 1:
        return valor
    return classificacao.ordenar_propulsao(
        "+".join(set(tipos) - {"hibrido_indefinido"} | resolvido))


def linha_final(linha: pd.Series) -> dict:
    """A linha da dimensao a partir de uma linha do rascunho, pela precedencia."""
    humana = ler_decisao(linha["decisao_humana"])
    regra = ler_decisao(linha["decisao_por_regra"])
    saida = {c: linha[c] for c in CHAVE}
    for atributo, (apos_regras, coluna_proc) in ATRIBUTOS.items():
        if humana.get(atributo) == PENDENTE_EXPLICITO:
            if linha[coluna_proc] != "pendente":
                raise DecisaoInvalida(
                    f"{linha['marca']}/{linha['modelo']} {linha['vigencia_inicio']}: "
                    f"{atributo}=pendente numa linha em que o atributo nao esta' pendente")
            valor, procedencia = linha[atributo], "pendente"
        elif atributo in humana:
            valor, procedencia = humana[atributo], "humana"
            if atributo == "propulsao_oferecida":
                valor = hibrido_pela_p5(valor, linha)
        elif humana.get("ok"):
            valor, procedencia = linha[apos_regras], "humana"
        elif atributo in regra:
            valor, procedencia = regra[atributo], linha[coluna_proc]
        else:
            valor, procedencia = linha[atributo], linha[coluna_proc]
        saida[NA_DIMENSAO.get(atributo, atributo)] = valor
        saida[PROCEDENCIA_COLUNA[atributo]] = procedencia
    if "eletrificacao" in humana:
        saida["eletrificacao_na_vigencia"] = humana["eletrificacao"]
    else:
        saida["eletrificacao_na_vigencia"] = classificacao.eletrificacao(
            saida["propulsao_na_vigencia"])
    ajustada = ""
    for limite in ("vigencia_inicio", "vigencia_fim"):
        if limite in humana:
            saida[limite], ajustada = humana[limite], "humana"
        elif limite in regra:
            saida[limite] = regra[limite]
            ajustada = ajustada or "regra"
        else:
            saida[limite] = linha[limite]
    pendentes = [a for a, c in PROCEDENCIA_COLUNA.items()
                 if saida[c] == "pendente" and humana.get(a) != PENDENTE_EXPLICITO]
    if humana and pendentes:
        raise DecisaoInvalida(
            f"{linha['marca']}/{linha['modelo']} {linha['vigencia_inicio']}: a decisao humana "
            f"{linha['decisao_humana']!r} deixa pendente {', '.join(pendentes)} -- use `ok` ou "
            "decida cada atributo pendente")
    saida["vigencia_ajustada_por"] = ajustada
    saida["regras_aplicadas"] = linha["regras_aplicadas"]
    saida["vigencia_inicio_rascunho"] = linha["vigencia_inicio"]
    return saida


def dimensao(rascunho: pd.DataFrame, nao_classificados: pd.DataFrame,
             painel: pd.DataFrame | None = None) -> pd.DataFrame:
    """A dimensao inteira: linhas classificadas pela precedencia, e as do piso.

    Modelo do piso sem mes com unidades (so' linhas de zero no painel) leva a
    vigencia do primeiro ao ultimo mes em que a chave aparece no painel.
    """
    linhas = [linha_final(linha) for _, linha in rascunho.iterrows()]
    meses = ({} if painel is None else
             {k: (g.min(), g.max()) for k, g in painel.groupby(CHAVE)["mes_ref"]})
    for _, modelo in nao_classificados.iterrows():
        inicio, fim = modelo["primeiro_mes"], modelo["ultimo_mes"]
        if not inicio:
            inicio, fim = meses.get(tuple(modelo[CHAVE]), ("", ""))
        linhas.append({
            **{c: modelo[c] for c in CHAVE}, "vigencia_inicio": inicio, "vigencia_fim": fim,
            "propulsao_na_vigencia": "", "eletrificacao_na_vigencia": "",
            "procedencia_propulsao": "nao_classificado", "carroceria": "",
            "procedencia_carroceria": "nao_classificado", "origem_producao": "",
            "procedencia_origem": "nao_classificado", "vigencia_ajustada_por": "",
            "regras_aplicadas": "", "vigencia_inicio_rascunho": ""})
    return (pd.DataFrame(linhas, columns=COLUNAS)
            .sort_values(CHAVE + ["vigencia_inicio"]).reset_index(drop=True))


# --------------------------------------------------------------- validacoes


def _mes(texto: str) -> int:
    return int(texto[:4]) * 12 + int(texto[5:7]) - 1


def problemas_de_cobertura(periodos: pd.DataFrame, painel: pd.DataFrame,
                           inicio: str = "vigencia_inicio", fim: str = "vigencia_fim"
                           ) -> list[str]:
    """Toda chave do painel coberta em todo mes com unidades, sem sobreposicao."""
    problemas = []
    por_chave = {k: g.sort_values(inicio) for k, g in periodos.groupby(CHAVE)}
    for chave, grupo in por_chave.items():
        anteriores = list(grupo[fim])[:-1]
        for fim_anterior, inicio_seguinte in zip(anteriores, list(grupo[inicio])[1:]):
            if inicio_seguinte <= fim_anterior:
                problemas.append(f"{'/'.join(chave)}: {inicio_seguinte} sobrepoe {fim_anterior}")
        for i, f in zip(grupo[inicio], grupo[fim]):
            if not MES.match(i) or not MES.match(f):
                problemas.append(f"{'/'.join(chave)}: periodo sem mes ({i!r} a {f!r})")
            elif f < i:
                problemas.append(f"{'/'.join(chave)}: periodo invertido {i} a {f}")
    meses = painel[painel["unidades"] > 0].groupby(CHAVE)["mes_ref"].unique()
    for chave, lista in meses.items():
        grupo = por_chave.get(chave)
        if grupo is None:
            problemas.append(f"{'/'.join(chave)}: chave do painel sem linha")
            continue
        intervalos = list(zip(grupo[inicio], grupo[fim]))
        fora = [m for m in lista if not any(i <= m <= f for i, f in intervalos)]
        if fora:
            problemas.append(f"{'/'.join(chave)}: {len(fora)} meses com unidades sem linha "
                             f"(ex.: {sorted(fora)[0]})")
    return problemas


def problemas_de_fidelidade(dim: pd.DataFrame, rascunho: pd.DataFrame) -> list[str]:
    """Nenhum valor `humana` ou `regra_*` difere do que o rascunho diz para a linha."""
    origem = rascunho.set_index(CHAVE + ["vigencia_inicio"])
    problemas = []
    for _, final in dim[dim["vigencia_inicio_rascunho"] != ""].iterrows():
        linha = origem.loc[tuple(final[CHAVE]) + (final["vigencia_inicio_rascunho"],)]
        humana = ler_decisao(linha["decisao_humana"])
        regra = ler_decisao(linha["decisao_por_regra"])
        for atributo, (apos_regras, coluna_proc) in ATRIBUTOS.items():
            procedencia = final[PROCEDENCIA_COLUNA[atributo]]
            if procedencia == "humana":
                esperado = humana.get(atributo, linha[apos_regras])
                if atributo == "propulsao_oferecida" and atributo in humana:
                    esperado = hibrido_pela_p5(esperado, linha)
            elif humana.get(atributo) == PENDENTE_EXPLICITO:
                esperado = linha[atributo]
            elif procedencia.startswith("regra_"):
                if linha[coluna_proc] != procedencia:
                    problemas.append(f"{'/'.join(final[CHAVE])}: {atributo} {procedencia} no "
                                     f"dado, {linha[coluna_proc]} no rascunho")
                esperado = regra.get(atributo, linha[atributo])
            else:
                continue
            coluna = NA_DIMENSAO.get(atributo, atributo)
            if final[coluna] != esperado:
                problemas.append(f"{'/'.join(final[CHAVE])} {final['vigencia_inicio']}: "
                                 f"{coluna} {final[coluna]!r} no dado, {esperado!r} no "
                                 "rascunho")
    return problemas


def volume_por_procedencia(dim: pd.DataFrame, painel: pd.DataFrame) -> pd.DataFrame:
    """Juncao de teste com o painel: fracao do volume em cada procedencia, por atributo."""
    unidades = painel.groupby(CHAVE + ["mes_ref"], as_index=False)["unidades"].sum()
    juntos = unidades.merge(dim, on=CHAVE, how="left")
    juntos = juntos[(juntos["mes_ref"] >= juntos["vigencia_inicio"])
                    & (juntos["mes_ref"] <= juntos["vigencia_fim"])]
    if juntos["unidades"].sum() != unidades["unidades"].sum():
        raise AssertionError("a juncao com o painel perdeu ou duplicou unidades")
    total = juntos["unidades"].sum()
    linhas = []
    for atributo, coluna in (("propulsao", "procedencia_propulsao"),
                             ("carroceria", "procedencia_carroceria"),
                             ("origem", "procedencia_origem")):
        soma = juntos.groupby(coluna)["unidades"].sum()
        for procedencia in PROCEDENCIAS:
            valor = int(soma.get(procedencia, 0))
            linhas.append({"atributo": atributo, "procedencia": procedencia, "unidades": valor,
                           "pct_do_volume": round(100 * valor / total, 2)})
    return pd.DataFrame(linhas)


def montagem_final(dim: pd.DataFrame, rascunho: pd.DataFrame, montagem_fontes: pd.DataFrame,
                   unidades: pd.DataFrame, periodos_montagem) -> pd.DataFrame:
    """Periodos de montagem sobre as vigencias finais, com procedencia propria.

    `periodos_montagem` e' a funcao das regras (adjudicacao.periodos_montagem),
    passada aqui para este modulo nao depender das regras. Modelo abaixo do piso:
    um periodo, montagem vazia, `nao_classificado`.
    """
    classificadas = dim[dim["vigencia_inicio_rascunho"] != ""].copy()
    pendencias = rascunho.set_index(CHAVE + ["vigencia_inicio"])["pendencias"]
    classificadas["pendencias"] = [
        pendencias.get(tuple(r[CHAVE]) + (r["vigencia_inicio_rascunho"],), "")
        for _, r in classificadas.iterrows()]
    classificadas["origem_apos_regras"] = classificadas["origem_producao"]
    _, periodos = periodos_montagem(classificadas, montagem_fontes, unidades)
    fora = dim[dim["vigencia_inicio_rascunho"] == ""]
    extras = pd.DataFrame([{
        **{c: r[c] for c in CHAVE}, "vigencia_inicio": r["vigencia_inicio"],
        "vigencia_fim": r["vigencia_fim"], "origem_producao": "",
        "montagem_inicio": r["vigencia_inicio"], "montagem_fim": r["vigencia_fim"],
        "montagem_local": "", "unidades": 0, "fonte_url": "", "tipo_fonte": "",
        "procedencia": "nao_classificado", "observacao": ""} for _, r in fora.iterrows()])
    juntos = pd.concat([periodos, extras], ignore_index=True)
    return juntos.drop(columns="unidades").sort_values(CHAVE + ["montagem_inicio"]) \
        .reset_index(drop=True)


def problemas_de_montagem(final: pd.DataFrame, rascunho_periodos: pd.DataFrame) -> list[str]:
    """Os modos com fonte (fabricacao, ckd, skd) sao os mesmos do rascunho, mes a mes."""
    def meses_com_modo(periodos):
        saida = {}
        for _, p in periodos[periodos["montagem_local"].isin(["fabricacao", "ckd", "skd"])] \
                .iterrows():
            for m in range(_mes(p["montagem_inicio"]), _mes(p["montagem_fim"]) + 1):
                saida[tuple(p[CHAVE]) + (m,)] = p["montagem_local"]
        return saida
    no_rascunho, no_dado = meses_com_modo(rascunho_periodos), meses_com_modo(final)
    return [f"{'/'.join(k[:3])} mes {k[3]}: {no_rascunho.get(k)} no rascunho, {no_dado.get(k)} "
            "no dado" for k in set(no_rascunho) | set(no_dado)
            if no_rascunho.get(k) != no_dado.get(k)]


# ----------------------------------------------------- decisoes versionadas

COLUNAS_DECISOES = CHAVE + ["vigencia_inicio", "decisao_humana", "data_decisao", "origem",
                            "observacao"]


def carregar_decisoes_humanas(caminho=None) -> pd.DataFrame:
    from . import config
    caminho = caminho or config.DECISOES_HUMANAS
    if not caminho.exists():
        return pd.DataFrame(columns=COLUNAS_DECISOES)
    return pd.read_csv(caminho, dtype=str, keep_default_na=False)


def aplicar_decisoes_humanas(rascunho: pd.DataFrame, decisoes: pd.DataFrame) -> pd.DataFrame:
    """Copia cada decisao versionada para `decisao_humana` da linha do rascunho (chave e
    `vigencia_inicio` do rascunho). Decisao sem linha, repetida ou fora da sintaxe e'
    erro: o rascunho mudou e a decisao precisa ser revista."""
    saida = rascunho.copy()
    indice = {tuple(k): i for i, k in zip(saida.index,
                                          saida[CHAVE + ["vigencia_inicio"]].to_numpy())}
    vistas = set()
    for _, d in decisoes.iterrows():
        chave = tuple(d[CHAVE + ["vigencia_inicio"]])
        if chave in vistas:
            raise DecisaoInvalida(f"decisao repetida para {'/'.join(chave)}")
        vistas.add(chave)
        if chave not in indice:
            raise DecisaoInvalida(f"decisao para {'/'.join(chave)}, que nao e' linha do rascunho")
        ler_decisao(d["decisao_humana"])
        saida.at[indice[chave], "decisao_humana"] = d["decisao_humana"]
    return saida
