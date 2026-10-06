"""Origem por pais e por fabrica (rodada 12, sec. 2).

Tres tabelas de referencia e um produto:

- `dados/referencia/fabricas.csv`: uma linha por fabrica -- empresa, pais (nome e
  codigo da tabela de paises do Comex Stat), municipio, UF e codigo IBGE quando no
  Brasil, inicio e fim de operacao quando a fonte os da', e a fonte (trecho literal de
  pagina guardada). Fabrica no exterior que a fonte nao identifica (a ADEFA e o INEGI
  dao a empresa, nao a planta) fica com o nome da empresa no pais.
- `dados/referencia/fabrica_modelos.csv`: que modelo (chave do painel) cada fabrica
  produziu, em que periodo, segundo que fonte. O `vinculo` diz o que a fonte afirma:
  `producao_local` (fabrica brasileira produz o modelo), `abastece_o_brasil` (fabrica
  no exterior manda o modelo ao Brasil: exportacao ao Brasil do INEGI, materia que diz
  de onde vem o importado) ou `producao_no_exterior` (a fonte so' diz que o modelo e'
  feito la', como a producao por modelo da ADEFA). A `regra_periodo` diz como o
  periodo saiu do texto.
- `dados/referencia/origem_pais_proposta.csv`: o pais (e a fabrica, no Brasil) que o
  assistente propoe para cada chave classificada, por periodo. E' conhecimento, nao
  fonte; o que nao tiver fonte fica com ele, marcado `proposta`.

A derivacao, mes a mes dentro de cada vigencia classificada (`derivar_meses`):

1. P = paises propostos para o mes.
2. Paises com vinculo ao Brasil pelas fontes: Brasil, se alguma fonte de
   `producao_local` cobre o mes; cada pais de fonte `abastece_o_brasil` que cobre o mes.
3. Fonte `producao_no_exterior` so' confirma pais que ja' esta' em P: producao num
   pais nao prova que o carro vendido aqui venha de la'.
4. Se as fontes com vinculo nomeiam pais fora de P, e' contradicao: o mes fica
   `pendente`, com os paises propostos (o valor de `pendente` e' a proposta, como na
   fase 2), e vai ao rascunho.
5. Senao, cada pais de P confirmado por fonte fica `regra_fonte_forte` (fonte oficial
   ou de imprensa especializada) ou `regra_fonte_fraca`; os demais, `proposta`.

A fonte vale para o periodo que ela trata (regra da fase 2): fora dos meses que uma
fonte cobre, a proposta. Meses iguais em seguida viram um periodo; dois paises no mesmo
periodo sao duas linhas. `origem_producao` passa a ser derivada do pais (Brasil ->
nacional; outro -> importado; os dois no mesmo periodo -> ambos); na vigencia, ambos se
algum periodo tiver Brasil e algum tiver outro pais.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pandas as pd

from . import config, tipo_fonte

CHAVE = ["marca", "modelo", "segmento"]
BRASIL = "Brasil"
VINCULOS = ("producao_local", "abastece_o_brasil", "producao_no_exterior")
REGRAS_PERIODO = ("declarado", "inicio_ate_a_pagina", "duracao_ate_a_pagina",
                  "na_data_da_pagina", "ano_da_tabela", "meses_da_tabela")
PROCEDENCIAS = ("regra_fonte_forte", "regra_fonte_fraca", "proposta", "pendente",
                "nao_classificado")
SEPARADOR = " [...] "
JUNTA = " | "

COLUNAS_FABRICAS = ["fabrica_id", "empresa", "fabrica", "pais", "pais_codigo", "municipio",
                    "uf", "cod_ibge_municipio", "operacao_inicio", "operacao_fim", "fonte_url",
                    "tipo_fonte", "fonte_trecho", "pagina_salva", "operacao_trecho",
                    "operacao_pagina", "observacao"]
COLUNAS_FABRICA_MODELOS = ["fabrica_id", "pais", "marca", "modelo", "segmento",
                           "periodo_inicio", "periodo_fim", "vinculo", "regra_periodo",
                           "data_fonte", "fonte_url", "tipo_fonte", "fonte_trecho",
                           "pagina_salva", "observacao"]
COLUNAS_PROPOSTA = ["marca", "modelo", "segmento", "periodo_inicio", "periodo_fim", "pais",
                    "fabrica_id", "pais_do_kit", "observacao"]
COLUNAS_PRODUTO = ["marca", "modelo", "segmento", "vigencia_inicio", "vigencia_fim",
                   "periodo_inicio", "periodo_fim", "pais_producao", "pais_codigo",
                   "origem_no_periodo", "fabrica_id", "fabrica", "municipio", "uf",
                   "cod_ibge_municipio", "fabrica_procedencia", "montagem_local",
                   "pais_do_kit", "procedencia", "vinculo", "fonte_url", "tipo_fonte",
                   "fonte_trecho", "pagina_salva", "origem_vigencia_derivada",
                   "origem_vigencia_atual", "diverge_da_atual", "observacao"]


# ------------------------------------------------------------------ leitura


def _ler(caminho) -> pd.DataFrame:
    return pd.read_csv(caminho, dtype=str, keep_default_na=False)


def carregar_fabricas() -> pd.DataFrame:
    return _ler(config.FABRICAS)


def carregar_fabrica_modelos() -> pd.DataFrame:
    return _ler(config.FABRICA_MODELOS)


def carregar_proposta() -> pd.DataFrame:
    return _ler(config.ORIGEM_PAIS_PROPOSTA)


def paises_comex() -> dict[str, str]:
    """nome -> codigo, da tabela de paises do Comex Stat guardada em `dados/bruto/comex/`."""
    dados = json.loads(config.PAISES_COMEX.read_text(encoding="utf-8"))["data"]["list"]
    return {p["text"]: p["id"] for p in dados}


def municipios_ibge() -> dict[tuple[str, str], str]:
    """(municipio, UF) -> codigo IBGE, da tabela guardada em `dados/bruto/ibge/`."""
    dados = json.loads(config.MUNICIPIOS_IBGE.read_text(encoding="utf-8"))
    return {(m["municipio-nome"], m["UF-sigla"]): str(m["municipio-id"]) for m in dados}


def normalizar(texto: str) -> str:
    return " ".join(texto.split())


def origem_de(paises) -> str:
    paises = set(paises) - {""}
    if not paises:
        return ""
    if paises == {BRASIL}:
        return "nacional"
    return "ambos" if BRASIL in paises else "importado"


def meses(inicio: str, fim: str) -> list[str]:
    if not inicio or not fim or fim < inicio:
        return []
    return [p.strftime("%Y-%m") for p in pd.period_range(inicio, fim, freq="M")]


# ---------------------------------------------------------------- derivacao


@dataclass
class Mes:
    """O que vale num mes de uma vigencia: um registro por pais."""
    paises: dict = field(default_factory=dict)   # pais -> dict de campos
    contradicao: str = ""


def _registros(quadro: pd.DataFrame) -> dict[tuple, list[dict]]:
    """Linhas por chave, como dicionarios (com o indice original em `_i`)."""
    saida: dict[tuple, list[dict]] = {}
    for i, r in zip(quadro.index, quadro.to_dict("records")):
        saida.setdefault(tuple(r[c] for c in CHAVE), []).append({**r, "_i": i})
    return saida


def _forca(fontes: list[dict]) -> str:
    return ("regra_fonte_forte" if any(f["tipo_fonte"] in tipo_fonte.FORTES for f in fontes)
            else "regra_fonte_fraca")


def derivar_mes(proposta: list[dict], fontes: list[dict], mes: str) -> Mes:
    """Aplica a regra do modulo a um mes de uma chave (`proposta` e `fontes` ja' da chave)."""
    prop = [p for p in proposta if p["periodo_inicio"] <= mes <= p["periodo_fim"]]
    fon = [f for f in fontes if f["periodo_inicio"] <= mes <= f["periodo_fim"]]
    propostos = list(dict.fromkeys(p["pais"] for p in prop))
    com_vinculo = [f for f in fon if f["vinculo"] != "producao_no_exterior"]
    confirmam = com_vinculo + [f for f in fon if f["vinculo"] == "producao_no_exterior"
                               and f["pais"] in propostos]
    resultado = Mes()
    fora = sorted({f["pais"] for f in com_vinculo} - set(propostos))
    if fora:
        resultado.contradicao = (f"fonte com vinculo ao Brasil nomeia {', '.join(fora)}; "
                                 f"proposta: {', '.join(propostos) or '(nenhuma)'}")
    for pais in propostos:
        p_pais = [p for p in prop if p["pais"] == pais]
        f_pais = [f for f in confirmam if f["pais"] == pais]
        if resultado.contradicao:
            procedencia = "pendente"
        elif f_pais:
            procedencia = _forca(f_pais)
        else:
            procedencia = "proposta"
        fabricas, fabrica_proc = [], "proposta"
        if pais == BRASIL and f_pais and not resultado.contradicao:
            fabricas = sorted({f["fabrica_id"] for f in f_pais} - {""})
            fabrica_proc = "fonte"
        if not fabricas:
            fabricas, fabrica_proc = sorted({p["fabrica_id"] for p in p_pais} - {""}), "proposta"
        usadas = f_pais if procedencia.startswith("regra") else [f for f in fon
                                                                 if f["pais"] == pais]
        resultado.paises[pais] = {
            "fabricas": tuple(fabricas), "fabrica_procedencia": fabrica_proc if fabricas else "",
            "pais_do_kit": "+".join(sorted({p["pais_do_kit"] for p in p_pais} - {""})),
            "procedencia": procedencia,
            "fontes": tuple(sorted(f["_i"] for f in usadas)),
            "observacao": " ".join(dict.fromkeys(p["observacao"] for p in p_pais
                                                 if p["observacao"])),
        }
    return resultado


def derivar_meses(vigencias: pd.DataFrame, proposta: pd.DataFrame,
                  fabrica_modelos: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por vigencia classificada x mes x pais (os meses da vigencia inteira)."""
    prop_k, fon_k = _registros(proposta), _registros(fabrica_modelos)
    linhas = []
    for v in vigencias.to_dict("records"):
        k = tuple(v[c] for c in CHAVE)
        p, f = prop_k.get(k, []), fon_k.get(k, [])
        for mes in meses(v["vigencia_inicio"], v["vigencia_fim"]):
            m = derivar_mes(p, f, mes)
            for pais, campos in m.paises.items():
                linhas.append({**{c: v[c] for c in CHAVE},
                               "vigencia_inicio": v["vigencia_inicio"],
                               "vigencia_fim": v["vigencia_fim"], "mes_ref": mes,
                               "pais_producao": pais, "contradicao": m.contradicao,
                               "paises_no_mes": "+".join(sorted(m.paises)), **campos})
    return pd.DataFrame(linhas)


def em_periodos(por_mes: pd.DataFrame) -> pd.DataFrame:
    """Meses seguidos com o mesmo conteudo viram um periodo."""
    if por_mes.empty:
        return por_mes.assign(periodo_inicio=[], periodo_fim=[])
    campos = [c for c in por_mes.columns if c != "mes_ref"]
    ordenado = por_mes.sort_values(CHAVE + ["vigencia_inicio", "pais_producao", "mes_ref"])
    linhas, atual, ultimo = [], None, None
    for r in ordenado.to_dict("records"):
        assinatura = tuple(r[c] for c in campos)
        continua = (atual is not None and assinatura == atual[0]
                    and pd.Period(r["mes_ref"], "M") == pd.Period(ultimo, "M") + 1)
        if continua:
            atual[1]["periodo_fim"] = r["mes_ref"]
        else:
            if atual is not None:
                linhas.append(atual[1])
            atual = (assinatura, {**{c: r[c] for c in campos},
                                  "periodo_inicio": r["mes_ref"], "periodo_fim": r["mes_ref"]})
        ultimo = r["mes_ref"]
    if atual is not None:
        linhas.append(atual[1])
    return pd.DataFrame(linhas)


# ----------------------------------------------------------------- produto


def _fontes_texto(indices: tuple, fabrica_modelos: pd.DataFrame, coluna: str) -> str:
    return JUNTA.join(dict.fromkeys(fabrica_modelos.loc[list(indices), coluna])) if indices else ""


def produto(classificacao: pd.DataFrame, montagem: pd.DataFrame, por_mes: pd.DataFrame,
            fabricas: pd.DataFrame, fabrica_modelos: pd.DataFrame) -> pd.DataFrame:
    """`classificacao_origem.parquet`: vigencia x periodo x pais, com fabrica, kit e fonte."""
    codigos = paises_comex()
    fab = fabricas.set_index("fabrica_id")
    # montagem do mes (a tabela de montagem tem periodo proprio)
    mont = {}
    for _, r in montagem.iterrows():
        for mes in meses(r["montagem_inicio"], r["montagem_fim"]):
            mont[(r["marca"], r["modelo"], r["segmento"], r["vigencia_inicio"], mes)] = (
                r["montagem_local"])
    base = por_mes.copy()
    base["montagem_local"] = [mont.get((a, b, c, d, e), "") for a, b, c, d, e in zip(
        base["marca"], base["modelo"], base["segmento"], base["vigencia_inicio"],
        base["mes_ref"])]
    kit_vale = base["montagem_local"].isin(["ckd", "skd"]) & (base["pais_producao"] == BRASIL)
    base["pais_do_kit"] = base["pais_do_kit"].where(kit_vale, "")
    periodos = em_periodos(base)
    # origem da vigencia: derivada dos paises de todos os meses
    derivada = (por_mes.groupby(CHAVE + ["vigencia_inicio"])["pais_producao"]
                .agg(lambda s: origem_de(s)).rename("origem_vigencia_derivada"))
    atual = classificacao.set_index(CHAVE + ["vigencia_inicio"])["origem_producao"]
    linhas = []
    for _, r in periodos.iterrows():
        k = tuple(r[c] for c in CHAVE) + (r["vigencia_inicio"],)
        fabs = list(r["fabricas"])
        no_brasil = r["pais_producao"] == BRASIL
        info = [fab.loc[f] for f in fabs if f in fab.index] if no_brasil else []
        linhas.append({
            **{c: r[c] for c in CHAVE}, "vigencia_inicio": r["vigencia_inicio"],
            "vigencia_fim": r["vigencia_fim"], "periodo_inicio": r["periodo_inicio"],
            "periodo_fim": r["periodo_fim"], "pais_producao": r["pais_producao"],
            "pais_codigo": codigos.get(r["pais_producao"], ""),
            "origem_no_periodo": origem_de(r["paises_no_mes"].split("+")),
            "fabrica_id": "+".join(fabs) if no_brasil else "",
            "fabrica": JUNTA.join(i["fabrica"] for i in info),
            "municipio": JUNTA.join(i["municipio"] for i in info),
            "uf": "+".join(dict.fromkeys(i["uf"] for i in info)),
            "cod_ibge_municipio": "+".join(i["cod_ibge_municipio"] for i in info),
            "fabrica_procedencia": r["fabrica_procedencia"] if no_brasil else "",
            "montagem_local": r["montagem_local"], "pais_do_kit": r["pais_do_kit"],
            "procedencia": r["procedencia"],
            "vinculo": _fontes_texto(r["fontes"], fabrica_modelos, "vinculo"),
            "fonte_url": _fontes_texto(r["fontes"], fabrica_modelos, "fonte_url"),
            "tipo_fonte": _fontes_texto(r["fontes"], fabrica_modelos, "tipo_fonte"),
            "fonte_trecho": _fontes_texto(r["fontes"], fabrica_modelos, "fonte_trecho"),
            "pagina_salva": _fontes_texto(r["fontes"], fabrica_modelos, "pagina_salva"),
            "origem_vigencia_derivada": derivada.get(k, ""),
            "origem_vigencia_atual": atual.get(k, ""),
            "observacao": "; ".join(x for x in (r["contradicao"], r["observacao"]) if x),
        })
    saida = pd.DataFrame(linhas, columns=[c for c in COLUNAS_PRODUTO if c != "diverge_da_atual"])
    # vigencias fora da classificacao (abaixo do piso): uma linha, sem pais
    fora = classificacao[classificacao["procedencia_origem"] == "nao_classificado"]
    nc = pd.DataFrame({**{c: fora[c] for c in CHAVE},
                       "vigencia_inicio": fora["vigencia_inicio"],
                       "vigencia_fim": fora["vigencia_fim"],
                       "periodo_inicio": fora["vigencia_inicio"],
                       "periodo_fim": fora["vigencia_fim"],
                       "procedencia": "nao_classificado",
                       "origem_vigencia_atual": fora["origem_producao"]})
    saida = pd.concat([saida, nc], ignore_index=True).fillna("")
    saida["diverge_da_atual"] = [
        "sim" if p != "nao_classificado" and d != a else "nao"
        for p, d, a in zip(saida["procedencia"], saida["origem_vigencia_derivada"],
                           saida["origem_vigencia_atual"])]
    return (saida[COLUNAS_PRODUTO].sort_values(CHAVE + ["vigencia_inicio", "periodo_inicio",
                                                        "pais_producao"])
            .reset_index(drop=True))


# ---------------------------------------------------------------- cobertura


def unidades_por_mes(painel: pd.DataFrame) -> pd.DataFrame:
    return painel.groupby(CHAVE + ["mes_ref"], as_index=False)["unidades"].sum()


def cobertura_anual(por_mes: pd.DataFrame, painel: pd.DataFrame,
                    fabrica_modelos: pd.DataFrame) -> pd.DataFrame:
    """Por ano: unidades do painel, as classificadas e as cobertas por fonte forte (todos
    os paises do mes `regra_fonte_forte`); ao lado, a parte que depende so' de fonte de
    `producao_no_exterior` (a que confirma pais proposto sem dizer que abastece o Brasil),
    a fraca, a proposta e a pendente."""
    u = unidades_por_mes(painel)
    total = u.assign(ano=u["mes_ref"].str[:4]).groupby("ano")["unidades"].sum()
    vinc = fabrica_modelos["vinculo"]
    estado = (por_mes.groupby(CHAVE + ["mes_ref"])
              .agg(procs=("procedencia", lambda s: set(s)),
                   fontes=("fontes", lambda s: set().union(*map(set, s))))
              .reset_index())

    def classe(procs: set, fontes: set) -> str:
        if procs == {"regra_fonte_forte"}:
            so_exterior = fontes and all(vinc.loc[i] == "producao_no_exterior" for i in fontes)
            return "forte_so_producao_no_exterior" if so_exterior else "forte"
        if "pendente" in procs:
            return "pendente"
        if procs <= {"regra_fonte_forte", "regra_fonte_fraca"}:
            return "fraca"
        if procs & {"regra_fonte_forte", "regra_fonte_fraca"}:
            return "parcial"
        return "proposta"

    estado["classe"] = [classe(p, f) for p, f in zip(estado["procs"], estado["fontes"])]
    juntos = u.merge(estado[CHAVE + ["mes_ref", "classe"]], on=CHAVE + ["mes_ref"])
    juntos["ano"] = juntos["mes_ref"].str[:4]
    tab = juntos.pivot_table(index="ano", columns="classe", values="unidades", aggfunc="sum",
                             fill_value=0)
    linhas = []
    for ano in sorted(total.index):
        t = tab.loc[ano] if ano in tab.index else pd.Series(dtype=int)
        g = {c: int(t.get(c, 0)) for c in ("forte", "forte_so_producao_no_exterior", "fraca",
                                           "parcial", "proposta", "pendente")}
        tot = int(total[ano])
        forte = g["forte"] + g["forte_so_producao_no_exterior"]
        linhas.append({"ano": int(ano), "unidades_painel": tot,
                       "unidades_classificadas": sum(g.values()),
                       "unidades_fonte_forte": forte,
                       "pct_fonte_forte": round(100 * forte / tot, 1) if tot else 0.0,
                       "unidades_forte_so_producao_no_exterior":
                           g["forte_so_producao_no_exterior"],
                       "unidades_fonte_fraca": g["fraca"],
                       "unidades_parcial": g["parcial"],
                       "unidades_proposta": g["proposta"],
                       "unidades_pendente": g["pendente"],
                       "atinge_meta_80": "sim" if tot and forte / tot >= 0.8 else "nao"})
    return pd.DataFrame(linhas)
