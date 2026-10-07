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

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

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
    contra: tuple = ()                           # indices das fontes que contradizem


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
        resultado.contra = tuple(sorted(f["_i"] for f in com_vinculo if f["pais"] in fora))
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
                               "fontes_contra": m.contra,
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


def montagem_por_mes(montagem: pd.DataFrame) -> dict[tuple, str]:
    """(marca, modelo, segmento, vigencia_inicio, mes) -> montagem_local (a tabela de
    montagem tem periodo proprio dentro da vigencia)."""
    mont = {}
    for r in montagem.to_dict("records"):
        for mes in meses(r["montagem_inicio"], r["montagem_fim"]):
            mont[(r["marca"], r["modelo"], r["segmento"], r["vigencia_inicio"], mes)] = (
                r["montagem_local"])
    return mont


def _fontes_texto(indices: tuple, fabrica_modelos: pd.DataFrame, coluna: str) -> str:
    return JUNTA.join(dict.fromkeys(fabrica_modelos.loc[list(indices), coluna])) if indices else ""


def produto(classificacao: pd.DataFrame, montagem: pd.DataFrame, por_mes: pd.DataFrame,
            fabricas: pd.DataFrame, fabrica_modelos: pd.DataFrame) -> pd.DataFrame:
    """`classificacao_origem.parquet`: vigencia x periodo x pais, com fabrica, kit e fonte."""
    codigos = paises_comex()
    fab = fabricas.set_index("fabrica_id")
    mont = montagem_por_mes(montagem)
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


# --------------------------------------------------------------- validacoes

PASTAS = {"fabricas_paginas": config.FABRICAS_PAGINAS,
          "origem_paginas": config.DIR_BRUTO / "origem_paginas",
          "anfavea": config.ANFAVEA_LICENCIAMENTO}
MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
ANO_OU_MES = re.compile(r"^\d{4}(-(0[1-9]|1[0-2]))?$")


def manifestos() -> dict[str, pd.DataFrame]:
    return {p: _ler(d / "manifesto.csv") for p, d in PASTAS.items()
            if (d / "manifesto.csv").exists()}


def url_das_paginas(manif: dict[str, pd.DataFrame]) -> dict[str, str]:
    """'pasta/nome' -> URL do manifesto."""
    return {f"{p}/{n}": u for p, m in manif.items() for n, u in zip(m["nome"], m["url"])}


def paginas_citadas(fabricas: pd.DataFrame, fabrica_modelos: pd.DataFrame) -> set[str]:
    return (set(fabricas["pagina_salva"]) | set(fabricas["operacao_pagina"])
            | set(fabrica_modelos["pagina_salva"])) - {""}


def textos(paginas) -> dict[str, str]:
    """Texto normalizado de cada 'pasta/nome' que existe."""
    saida = {}
    for p in sorted(set(paginas)):
        pasta, _, nome = p.partition("/")
        if pasta in PASTAS and (PASTAS[pasta] / f"{nome}.txt").exists():
            saida[p] = normalizar((PASTAS[pasta] / f"{nome}.txt").read_text(encoding="utf-8"))
    return saida


def partes_ausentes(trecho: str, texto: str) -> list[str]:
    """Partes do trecho (separadas por " [...] ") que nao estao na pagina."""
    return [p for p in trecho.split(SEPARADOR) if normalizar(p) not in texto]


def problemas_das_paginas(manif: dict[str, pd.DataFrame], citadas: set[str]) -> list[str]:
    """Paginas de `fabricas_paginas/` e `anfavea/` (todas) e de `origem_paginas/` (as
    citadas): arquivo presente, SHA-256 do manifesto, primeira linha com a URL."""
    saida = []
    for pasta, m in manif.items():
        for r in m.itertuples():
            if pasta == "origem_paginas" and f"{pasta}/{r.nome}" not in citadas:
                continue
            arquivo = PASTAS[pasta] / f"{r.nome}.txt"
            if not arquivo.exists():
                saida.append(f"pagina {pasta}/{r.nome}: arquivo ausente")
                continue
            bruto = arquivo.read_bytes()
            if hashlib.sha256(bruto).hexdigest() != r.sha256_texto:
                saida.append(f"pagina {pasta}/{r.nome}: SHA-256 diferente do manifesto")
            if not bruto.decode("utf-8").startswith(f"URL: {r.url}\n"):
                saida.append(f"pagina {pasta}/{r.nome}: a primeira linha nao e' a URL")
    urls = url_das_paginas(manif)
    saida += [f"pagina citada fora dos manifestos: {p}" for p in sorted(citadas - set(urls))]
    return saida


def _fonte(rotulo: str, pagina: str, url: str, tipo: str, trecho: str, urls: dict,
           texto: dict, mapa: dict) -> list[str]:
    """Pagina no manifesto com a mesma URL, tipo da fonte pelo dominio, trecho literal."""
    saida = []
    if pagina not in urls:
        return [f"{rotulo}: pagina {pagina or '(vazia)'} fora dos manifestos"]
    if urls[pagina] != url:
        saida.append(f"{rotulo}: fonte_url difere da URL do manifesto")
    if not tipo or tipo != tipo_fonte.tipo_de(url, mapa):
        saida.append(f"{rotulo}: tipo_fonte '{tipo}' difere do dominio")
    if not trecho:
        saida.append(f"{rotulo}: trecho vazio")
    elif pagina in texto and partes_ausentes(trecho, texto[pagina]):
        saida.append(f"{rotulo}: trecho fora da pagina: {partes_ausentes(trecho, texto[pagina])}")
    return saida


def problemas_das_fabricas(fabricas: pd.DataFrame, urls: dict, texto: dict,
                           paises: dict | None = None, ibge: dict | None = None,
                           mapa: dict | None = None) -> list[str]:
    """Identificador unico; pais e codigo do Comex; no Brasil, municipio, UF e codigo IBGE da
    tabela do IBGE (fora, vazios); datas de operacao; fonte (quando ha') com trecho literal."""
    paises = paises if paises is not None else paises_comex()
    ibge = ibge if ibge is not None else municipios_ibge()
    mapa = mapa if mapa is not None else tipo_fonte.carregar_mapa()
    saida = []
    if (fabricas["fabrica_id"] == "").any() or fabricas["fabrica_id"].duplicated().any():
        saida.append("fabricas: fabrica_id vazio ou repetido")
    for r in fabricas.itertuples():
        rot = f"fabrica {r.fabrica_id}"
        if r.pais not in paises:
            saida.append(f"{rot}: pais '{r.pais}' fora da tabela do Comex")
        elif r.pais_codigo != paises[r.pais]:
            saida.append(f"{rot}: pais_codigo difere do Comex")
        if r.pais == BRASIL:
            if ibge.get((r.municipio, r.uf)) != r.cod_ibge_municipio or not r.cod_ibge_municipio:
                saida.append(f"{rot}: municipio/UF/codigo IBGE nao batem com a tabela do IBGE")
        elif r.uf or r.cod_ibge_municipio:
            saida.append(f"{rot}: UF ou codigo IBGE fora do Brasil")
        for campo in ("operacao_inicio", "operacao_fim"):
            valor = getattr(r, campo)
            if valor and not ANO_OU_MES.match(valor):
                saida.append(f"{rot}: {campo} '{valor}' fora do formato AAAA ou AAAA-MM")
        if r.operacao_inicio and r.operacao_fim and r.operacao_fim < r.operacao_inicio:
            saida.append(f"{rot}: operacao_fim antes do inicio")
        if r.pagina_salva:
            saida += _fonte(rot, r.pagina_salva, r.fonte_url, r.tipo_fonte, r.fonte_trecho,
                            urls, texto, mapa)
        elif r.fonte_url or r.fonte_trecho or not r.observacao:
            saida.append(f"{rot}: sem pagina, mas com URL ou trecho, ou sem observacao")
        if r.operacao_trecho:
            if r.operacao_pagina not in texto:
                saida.append(f"{rot}: operacao_pagina fora dos manifestos")
            elif partes_ausentes(r.operacao_trecho, texto[r.operacao_pagina]):
                saida.append(f"{rot}: operacao_trecho fora da pagina")
    return saida


def problemas_de_fabrica_modelos(fm: pd.DataFrame, fabricas: pd.DataFrame, chaves: set,
                                 urls: dict, texto: dict, paises: dict | None = None,
                                 mapa: dict | None = None) -> list[str]:
    """Fabrica existente (com o mesmo pais) ou vazia so' quando a fonte nomeia so' o pais;
    chave do painel; vinculo e regra nas listas e coerentes com o pais e o periodo; datas
    AAAA-MM; pagina, URL, tipo e trecho literal."""
    paises = paises if paises is not None else paises_comex()
    mapa = mapa if mapa is not None else tipo_fonte.carregar_mapa()
    pais_da_fabrica = dict(zip(fabricas["fabrica_id"], fabricas["pais"]))
    saida = []
    for i, r in zip(fm.index, fm.itertuples()):
        rot = f"fabrica_modelos linha {i + 2} ({r.marca}|{r.modelo}, {r.periodo_inicio})"
        if r.fabrica_id:
            if r.fabrica_id not in pais_da_fabrica:
                saida.append(f"{rot}: fabrica {r.fabrica_id} fora de fabricas.csv")
            elif pais_da_fabrica[r.fabrica_id] != r.pais:
                saida.append(f"{rot}: pais difere do da fabrica")
        elif r.vinculo == "producao_no_exterior":
            saida.append(f"{rot}: producao_no_exterior sem fabrica")
        if r.pais not in paises:
            saida.append(f"{rot}: pais '{r.pais}' fora da tabela do Comex")
        if (r.marca, r.modelo, r.segmento) not in chaves:
            saida.append(f"{rot}: chave fora do painel")
        if r.vinculo not in VINCULOS:
            saida.append(f"{rot}: vinculo '{r.vinculo}' fora da lista")
        elif (r.vinculo == "producao_local") != (r.pais == BRASIL):
            saida.append(f"{rot}: vinculo {r.vinculo} com pais {r.pais}")
        if r.regra_periodo not in REGRAS_PERIODO:
            saida.append(f"{rot}: regra_periodo '{r.regra_periodo}' fora da lista")
        datas = (r.periodo_inicio, r.periodo_fim, r.data_fonte)
        if not all(MES.match(d) for d in datas):
            saida.append(f"{rot}: data fora do formato AAAA-MM")
            continue
        if r.periodo_fim < r.periodo_inicio:
            saida.append(f"{rot}: periodo_fim antes do inicio")
        if r.regra_periodo == "na_data_da_pagina" and r.periodo_inicio != r.periodo_fim:
            saida.append(f"{rot}: na_data_da_pagina com mais de um mes")
        if r.regra_periodo == "ano_da_tabela" and (
                r.periodo_inicio[5:] != "01" or r.periodo_fim != f"{r.periodo_inicio[:4]}-12"):
            saida.append(f"{rot}: ano_da_tabela que nao vai de janeiro a dezembro")
        if (r.regra_periodo in ("inicio_ate_a_pagina", "duracao_ate_a_pagina")
                and r.periodo_fim > r.data_fonte):
            saida.append(f"{rot}: {r.regra_periodo} terminando depois da data da pagina")
        saida += _fonte(rot, r.pagina_salva, r.fonte_url, r.tipo_fonte, r.fonte_trecho, urls,
                        texto, mapa)
    return saida


def meses_sem_proposta(vigencias: pd.DataFrame, proposta: pd.DataFrame) -> list[str]:
    """Vigencia classificada com algum mes que nenhuma linha da proposta cobre."""
    prop = _registros(proposta)
    saida = []
    for v in vigencias.to_dict("records"):
        p = prop.get(tuple(v[c] for c in CHAVE), [])
        faltam = [m for m in meses(v["vigencia_inicio"], v["vigencia_fim"])
                  if not any(x["periodo_inicio"] <= m <= x["periodo_fim"] for x in p)]
        if faltam:
            saida.append(f"{v['marca']}|{v['modelo']}|{v['segmento']} {v['vigencia_inicio']}: "
                         f"{len(faltam)} meses sem proposta ({faltam[0]} a {faltam[-1]})")
    return saida


def problemas_da_proposta(proposta: pd.DataFrame, fabricas: pd.DataFrame, vigencias: pd.DataFrame,
                          paises: dict | None = None) -> list[str]:
    """Pais (e pais do kit) da tabela do Comex; fabrica existente e do mesmo pais; periodos
    AAAA-MM; chave classificada; todo mes de vigencia classificada coberto."""
    paises = paises if paises is not None else paises_comex()
    pais_da_fabrica = dict(zip(fabricas["fabrica_id"], fabricas["pais"]))
    chaves = set(map(tuple, vigencias[CHAVE].values))
    saida = []
    for i, r in zip(proposta.index, proposta.itertuples()):
        rot = f"proposta linha {i + 2} ({r.marca}|{r.modelo}, {r.periodo_inicio})"
        if r.pais not in paises:
            saida.append(f"{rot}: pais '{r.pais}' fora da tabela do Comex")
        if r.pais_do_kit and (r.pais_do_kit not in paises or r.pais != BRASIL):
            saida.append(f"{rot}: pais_do_kit '{r.pais_do_kit}' invalido")
        if r.fabrica_id and pais_da_fabrica.get(r.fabrica_id) != r.pais:
            saida.append(f"{rot}: fabrica {r.fabrica_id} ausente ou de outro pais")
        if not (MES.match(r.periodo_inicio) and MES.match(r.periodo_fim)) or \
                r.periodo_fim < r.periodo_inicio:
            saida.append(f"{rot}: periodo invalido")
        if (r.marca, r.modelo, r.segmento) not in chaves:
            saida.append(f"{rot}: chave sem vigencia classificada")
    return saida + meses_sem_proposta(vigencias, proposta)


def problemas_do_produto(prod: pd.DataFrame, vigencias: pd.DataFrame,
                         fabricas: pd.DataFrame) -> list[str]:
    """Cada mes de vigencia classificada tem pais; periodos de um mesmo pais nao se
    sobrepoem e ficam na vigencia; codigo do pais; procedencia na lista; regra com fonte;
    fabrica so' no Brasil, com a UF da fabrica; kit so' em ckd/skd no Brasil; origem
    derivada coerente com os paises."""
    saida = []
    classif = prod[prod["procedencia"] != "nao_classificado"]
    uf = dict(zip(fabricas["fabrica_id"], fabricas["uf"]))
    for k, g in classif.groupby(CHAVE + ["vigencia_inicio"]):
        rot = f"produto {'|'.join(k[:3])} {k[3]}"
        vig = meses(k[3], g["vigencia_fim"].iloc[0])
        cobertos = set()
        for pais, h in g.groupby("pais_producao"):
            ms = [m for r in h.itertuples() for m in meses(r.periodo_inicio, r.periodo_fim)]
            if len(ms) != len(set(ms)):
                saida.append(f"{rot}: periodos de {pais} se sobrepoem")
            cobertos |= set(ms)
        if cobertos != set(vig):
            saida.append(f"{rot}: meses sem pais ou fora da vigencia")
        esperada = origem_de(g["pais_producao"])
        if (g["origem_vigencia_derivada"] != esperada).any():
            saida.append(f"{rot}: origem_vigencia_derivada incoerente com os paises")
    chaves = set(map(tuple, vigencias[CHAVE + ["vigencia_inicio"]].values))
    faltam = chaves - set(map(tuple, classif[CHAVE + ["vigencia_inicio"]].values))
    saida += [f"produto: vigencia classificada sem linha: {k}" for k in sorted(faltam)]
    for i, r in zip(classif.index, classif.itertuples()):
        rot = f"produto linha {i} ({r.marca}|{r.modelo}, {r.periodo_inicio}, {r.pais_producao})"
        if not r.pais_codigo:
            saida.append(f"{rot}: sem codigo do pais")
        if r.procedencia not in PROCEDENCIAS:
            saida.append(f"{rot}: procedencia '{r.procedencia}' fora da lista")
        if r.procedencia.startswith("regra") and not (r.fonte_trecho and r.pagina_salva):
            saida.append(f"{rot}: regra sem fonte")
        if r.pais_producao == BRASIL:
            for f in [x for x in r.fabrica_id.split("+") if x]:
                if uf.get(f, "") not in r.uf.split("+"):
                    saida.append(f"{rot}: UF da fabrica {f} ausente")
        elif r.fabrica_id or r.uf or r.cod_ibge_municipio:
            saida.append(f"{rot}: fabrica brasileira em pais estrangeiro")
        if r.pais_do_kit and not (r.pais_producao == BRASIL
                                  and r.montagem_local in ("ckd", "skd")):
            saida.append(f"{rot}: pais_do_kit fora de ckd/skd no Brasil")
        if r.origem_no_periodo not in ("nacional", "importado", "ambos"):
            saida.append(f"{rot}: origem_no_periodo vazia")
    nc = prod[prod["procedencia"] == "nao_classificado"]
    if (nc["pais_producao"] != "").any():
        saida.append("produto: vigencia nao classificada com pais")
    return saida


def divergencias(prod: pd.DataFrame, por_mes: pd.DataFrame,
                 fabrica_modelos: pd.DataFrame) -> pd.DataFrame:
    """O que vai ao rascunho: (1) vigencia cuja origem derivada difere da atual de
    `classificacao.parquet`; (2) periodo `pendente`, em que fonte com vinculo ao Brasil
    nomeia pais fora da proposta (com a fonte que contradiz)."""
    linhas = []
    vig = (prod[prod["diverge_da_atual"] == "sim"]
           .groupby(CHAVE + ["vigencia_inicio", "vigencia_fim"], as_index=False)
           .agg(paises=("pais_producao", lambda s: "+".join(sorted(set(s)))),
                derivada=("origem_vigencia_derivada", "first"),
                atual=("origem_vigencia_atual", "first"),
                procedencias=("procedencia", lambda s: "+".join(sorted(set(s))))))
    for r in vig.to_dict("records"):
        linhas.append({"tipo": "origem_derivada_difere_da_atual", **{c: r[c] for c in CHAVE},
                       "vigencia_inicio": r["vigencia_inicio"], "vigencia_fim": r["vigencia_fim"],
                       "periodo_inicio": r["vigencia_inicio"], "periodo_fim": r["vigencia_fim"],
                       "paises_propostos": r["paises"], "origem_derivada": r["derivada"],
                       "origem_atual": r["atual"], "procedencias": r["procedencias"],
                       "detalhe": f"origem derivada dos paises ({r['paises']}) = {r['derivada']}; "
                                  f"classificacao.parquet = {r['atual']}",
                       "fonte_contra_url": "", "fonte_contra_trecho": "",
                       "fonte_contra_pagina": ""})
    pend = por_mes[por_mes["contradicao"] != ""]
    if len(pend):
        base = pend.groupby(CHAVE + ["vigencia_inicio", "vigencia_fim", "mes_ref"],
                            as_index=False).agg(
            paises=("pais_producao", lambda s: "+".join(sorted(set(s)))),
            contradicao=("contradicao", "first"), contra=("fontes_contra", "first"))
        periodos = em_periodos(base.rename(columns={"paises": "pais_producao"}))
        for r in periodos.to_dict("records"):
            idx = list(r["contra"])
            linhas.append({
                "tipo": "fonte_contradiz_proposta", **{c: r[c] for c in CHAVE},
                "vigencia_inicio": r["vigencia_inicio"], "vigencia_fim": r["vigencia_fim"],
                "periodo_inicio": r["periodo_inicio"], "periodo_fim": r["periodo_fim"],
                "paises_propostos": r["pais_producao"], "origem_derivada": "", "origem_atual": "",
                "procedencias": "pendente", "detalhe": r["contradicao"],
                "fonte_contra_url": JUNTA.join(dict.fromkeys(fabrica_modelos.loc[idx, "fonte_url"])),
                "fonte_contra_trecho": JUNTA.join(dict.fromkeys(
                    fabrica_modelos.loc[idx, "fonte_trecho"])),
                "fonte_contra_pagina": JUNTA.join(dict.fromkeys(
                    fabrica_modelos.loc[idx, "pagina_salva"]))})
    colunas = ["tipo", *CHAVE, "vigencia_inicio", "vigencia_fim", "periodo_inicio", "periodo_fim",
               "paises_propostos", "origem_derivada", "origem_atual", "procedencias", "detalhe",
               "fonte_contra_url", "fonte_contra_trecho", "fonte_contra_pagina"]
    return (pd.DataFrame(linhas, columns=colunas)
            .sort_values(["tipo", *CHAVE, "periodo_inicio"]).reset_index(drop=True))


# ---------------------------------------------------------------- uso-teste


def unidades_por_pais(por_mes: pd.DataFrame, painel: pd.DataFrame,
                      montagem: pd.DataFrame) -> pd.DataFrame:
    """Unidades do painel por ano e pais, a partir dos paises de cada mes classificado.

    `unidades_so_pais`: meses em que a chave tem um pais so'. `unidades_compartilhadas`: meses
    com mais de um pais (a divisao e' desconhecida; cada pais recebe o mes inteiro, teto).
    `unidades_kit`: meses montados no Brasil em ckd/skd com kit do pais."""
    u = unidades_por_mes(painel)
    base = por_mes[CHAVE + ["vigencia_inicio", "mes_ref", "pais_producao", "paises_no_mes",
                            "pais_do_kit"]].merge(u, on=CHAVE + ["mes_ref"])
    base["ano"] = base["mes_ref"].str[:4].astype(int)
    base["n"] = base["paises_no_mes"].str.count(r"\+") + 1
    mont = montagem_por_mes(montagem)
    base["montagem_local"] = [mont.get(k, "") for k in zip(
        base["marca"], base["modelo"], base["segmento"], base["vigencia_inicio"], base["mes_ref"])]
    so = base[base["n"] == 1].groupby(["ano", "pais_producao"])["unidades"].sum()
    comp = base[base["n"] > 1].groupby(["ano", "pais_producao"])["unidades"].sum()
    kits = base[(base["pais_producao"] == BRASIL) & base["montagem_local"].isin(["ckd", "skd"])
                & (base["pais_do_kit"] != "")]
    kit = kits.groupby(["ano", "pais_do_kit"])["unidades"].sum()
    kit.index.names = ["ano", "pais_producao"]
    saida = pd.concat({"unidades_so_pais": so, "unidades_compartilhadas": comp,
                       "unidades_kit": kit}, axis=1).fillna(0).astype(int).reset_index()
    return saida.rename(columns={"pais_producao": "pais"})


def importacao_comex(comex: pd.DataFrame, ncms: pd.DataFrame, fim: str) -> pd.DataFrame:
    """Importacao do agregado de carros (unidades ajustadas) por ano e pais, ate' `fim`."""
    carros = set(ncms.loc[ncms["agregado_carros"] == "sim", "ncm"])
    imp = comex[(comex["fluxo"] == "importacao") & comex["ncm"].isin(carros)
                & (comex["mes_ref"] <= fim)]
    return (imp.assign(ano=imp["mes_ref"].str[:4].astype(int))
            .groupby(["ano", "pais"], as_index=False)["unidades_ajustadas"].sum()
            .rename(columns={"unidades_ajustadas": "comex_unidades_ajustadas"}))


def uso_teste_comex(por_pais: pd.DataFrame, comex_ano: pd.DataFrame, inicio: int,
                    fim: int) -> pd.DataFrame:
    """Por ano e pais (fora o Brasil): importacao do Comex contra unidades do painel feitas
    no pais mais as montadas aqui com kit dele. `razao` = Comex / painel; `distancia` =
    Comex - painel (positiva: o Comex traz mais do que o painel atribui ao pais)."""
    pp = por_pais[por_pais["pais"] != BRASIL]
    j = pp.merge(comex_ano[comex_ano["pais"] != BRASIL], on=["ano", "pais"],
                 how="outer").fillna(0)
    j = j[(j["ano"] >= inicio) & (j["ano"] <= fim)].copy()
    for c in ("unidades_so_pais", "unidades_compartilhadas", "unidades_kit",
              "comex_unidades_ajustadas"):
        j[c] = j[c].astype(int)
    j["painel_unidades"] = j["unidades_so_pais"] + j["unidades_kit"]
    j["razao_comex_painel"] = [round(c / p, 2) if p else None
                               for c, p in zip(j["comex_unidades_ajustadas"], j["painel_unidades"])]
    j["distancia"] = j["comex_unidades_ajustadas"] - j["painel_unidades"]
    j["ano"] = j["ano"].astype(int)
    colunas = ["ano", "pais", "comex_unidades_ajustadas", "painel_unidades", "unidades_so_pais",
               "unidades_kit", "unidades_compartilhadas", "razao_comex_painel", "distancia"]
    return j[colunas].sort_values(["ano", "comex_unidades_ajustadas"],
                                  ascending=[True, False]).reset_index(drop=True)


def _modelos(g: pd.DataFrame, n: int = 3) -> str:
    top = (g.groupby(CHAVE + ["procedencia"], as_index=False)["unidades"].sum()
           .sort_values("unidades", ascending=False).head(n))
    return "; ".join(f"{r.marca} {r.modelo} ({r.unidades:,}, {r.procedencia})"
                     for r in top.itertuples())


def distancias_comex(uso: pd.DataFrame, por_mes: pd.DataFrame, painel: pd.DataFrame,
                     fabrica_modelos: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """As `n` maiores distancias absolutas de cada ano, com os modelos que as explicariam.

    Painel acima do Comex: os maiores modelos que o painel atribui ao pais no ano (atribuicao
    a conferir, ou importacao de anos anteriores em estoque). Comex acima do painel: os
    modelos que alguma fonte poe no pais no ano (producao, exportacao ao Brasil) e que o
    painel atribui a outro pais -- inclusive os pendentes, em que a fonte contradiz a
    proposta."""
    u = unidades_por_mes(painel)
    base = por_mes.merge(u, on=CHAVE + ["mes_ref"])
    base["ano"] = base["mes_ref"].str[:4].astype(int)
    fontes_ano: dict[tuple, set] = {}
    for r in fabrica_modelos.to_dict("records"):
        for a in range(int(r["periodo_inicio"][:4]), int(r["periodo_fim"][:4]) + 1):
            fontes_ano.setdefault((a, r["pais"]), set()).add(
                (r["marca"], r["modelo"], r["segmento"]))
    linhas = []
    for ano, g in uso.groupby("ano"):
        top = g.reindex(g["distancia"].abs().sort_values(ascending=False).index).head(n)
        doano = base[base["ano"] == ano]
        for posicao, r in enumerate(top.itertuples(), 1):
            if r.distancia < 0:
                explica = _modelos(doano[doano["pais_producao"] == r.pais])
                leitura = "painel acima do Comex"
            else:
                com_fonte = fontes_ano.get((ano, r.pais), set())
                fora = doano[(doano["pais_producao"] != r.pais)
                             & (doano["paises_no_mes"].str.split("+").map(
                                 lambda ps, p=r.pais: p not in ps))]
                fora = fora[[k in com_fonte for k in map(tuple, fora[CHAVE].values)]]
                explica = _modelos(fora)
                leitura = "Comex acima do painel"
            linhas.append({"ano": ano, "posicao": posicao, "pais": r.pais,
                           "comex_unidades_ajustadas": r.comex_unidades_ajustadas,
                           "painel_unidades": r.painel_unidades, "distancia": r.distancia,
                           "leitura": leitura,
                           "modelos_que_explicariam": explica or "nenhum modelo do painel com "
                                                                 "fonte no pais no ano"})
    return pd.DataFrame(linhas)


def participacao_importado_painel(por_mes: pd.DataFrame, painel: pd.DataFrame) -> pd.DataFrame:
    """Por ano: unidades do painel (automoveis e comerciais leves) nacionais, importadas,
    com os dois no mes, e nao classificadas; participacao do importado (minima: so' os meses
    de pais estrangeiro; maxima: somando os meses com os dois e as nao classificadas)."""
    u = unidades_por_mes(painel)
    u = u[u["segmento"].isin(config.SEGMENTOS)]
    origem = (por_mes.groupby(CHAVE + ["mes_ref"])["paises_no_mes"].first()
              .map(lambda p: origem_de(p.split("+"))).rename("origem").reset_index())
    j = u.merge(origem, on=CHAVE + ["mes_ref"], how="left").fillna({"origem": "nao_classificado"})
    j["ano"] = j["mes_ref"].str[:4].astype(int)
    tab = j.pivot_table(index="ano", columns="origem", values="unidades", aggfunc="sum",
                        fill_value=0)
    for c in ("nacional", "importado", "ambos", "nao_classificado"):
        if c not in tab:
            tab[c] = 0
    total = tab[["nacional", "importado", "ambos", "nao_classificado"]].sum(axis=1)
    return pd.DataFrame({
        "ano": tab.index, "painel_leves_total": total.values,
        "painel_nacional": tab["nacional"].values, "painel_importado": tab["importado"].values,
        "painel_ambos": tab["ambos"].values,
        "painel_nao_classificado": tab["nao_classificado"].values,
        "painel_pct_importado": (100 * tab["importado"] / total).round(1).values,
        "painel_pct_importado_max": (100 * (tab["importado"] + tab["ambos"]
                                            + tab["nao_classificado"]) / total).round(1).values})


def uso_teste_anfavea(part_painel: pd.DataFrame, part_anfavea: pd.DataFrame,
                      por_pais: pd.DataFrame, anf_paises: pd.DataFrame) -> pd.DataFrame:
    """So' registro e comparacao. Duas tabelas empilhadas (`tabela`): `participacao` por ano
    (Anfavea x painel) e `por_pais` (2016-2025, emplacamento de importados automoveis +
    comerciais leves por pais de origem x unidades do painel atribuidas so' ao pais)."""
    a = part_painel.merge(part_anfavea, on="ano", how="inner")
    a["diferenca_pp"] = (a["painel_pct_importado"] - a["anfavea_pct_importado"]).round(1)
    a["tabela"] = "participacao"
    leves = anf_paises[anf_paises["bloco"].isin(["automoveis", "comerciais_leves"])
                       & (anf_paises["pais"] != "TOTAL")]
    anf = leves.groupby(["ano", "pais"], as_index=False)["unidades"].sum().rename(
        columns={"unidades": "anfavea_emplacamento_importados"})
    pp = por_pais[por_pais["pais"] != BRASIL][["ano", "pais", "unidades_so_pais"]]
    b = anf.merge(pp, on=["ano", "pais"], how="left").fillna({"unidades_so_pais": 0})
    outros = set(b["pais"]) - {"Outros"}
    resto = pp[(~pp["pais"].isin(outros)) & pp["ano"].between(2016, 2025)].groupby("ano")[
        "unidades_so_pais"].sum()
    b.loc[b["pais"] == "Outros", "unidades_so_pais"] = b.loc[b["pais"] == "Outros", "ano"].map(
        resto).fillna(0)
    b["unidades_so_pais"] = b["unidades_so_pais"].astype(int)
    b["razao_painel_anfavea"] = [round(p / x, 2) if x else None for p, x in
                                 zip(b["unidades_so_pais"], b["anfavea_emplacamento_importados"])]
    b["tabela"] = "por_pais"
    b = b.rename(columns={"unidades_so_pais": "painel_unidades_so_pais"})
    return pd.concat([a, b], ignore_index=True)[
        ["tabela", "ano", "pais", "anfavea_leves_total", "anfavea_leves_importados",
         "anfavea_pct_importado", "painel_leves_total", "painel_nacional", "painel_importado",
         "painel_ambos", "painel_nao_classificado", "painel_pct_importado",
         "painel_pct_importado_max", "diferenca_pp", "anfavea_emplacamento_importados",
         "painel_unidades_so_pais", "razao_painel_anfavea"]]


def _fora_de_operacao(mes: str, inicio: str, fim: str) -> bool:
    """O mes cai antes do inicio ou depois do fim de operacao (datas AAAA ou AAAA-MM)."""
    if inicio and (mes < inicio if len(inicio) == 7 else mes[:4] < inicio):
        return True
    return bool(fim) and (mes > fim if len(fim) == 7 else mes[:4] > fim)


def mapa_uf(por_mes: pd.DataFrame, painel: pd.DataFrame,
            fabricas: pd.DataFrame) -> pd.DataFrame:
    """Unidades do painel por UF de producao e ano (meses com o Brasil como unico pais; com
    fabricas em mais de uma UF, a UF fica 'A+B'). `alerta` marca o implausivel: fabrica da UF
    fora do seu periodo de operacao, ou variacao forte de participacao."""
    u = unidades_por_mes(painel)
    br = por_mes[(por_mes["pais_producao"] == BRASIL) & (por_mes["paises_no_mes"] == BRASIL)]
    uf = dict(zip(fabricas["fabrica_id"], fabricas["uf"]))
    ini = dict(zip(fabricas["fabrica_id"], fabricas["operacao_inicio"]))
    fim = dict(zip(fabricas["fabrica_id"], fabricas["operacao_fim"]))
    j = br[CHAVE + ["mes_ref", "fabricas"]].merge(u, on=CHAVE + ["mes_ref"])
    j["ano"] = j["mes_ref"].str[:4].astype(int)
    j["uf"] = [("+".join(sorted({uf.get(f, "") for f in fs} - {""})) or "sem_fabrica")
               for fs in j["fabricas"]]
    j["fabrica_fora_de_operacao"] = [
        "+".join(f for f in fs if _fora_de_operacao(mes, ini.get(f, ""), fim.get(f, "")))
        for fs, mes in zip(j["fabricas"], j["mes_ref"])]
    tab = j.groupby(["ano", "uf"], as_index=False).agg(
        unidades=("unidades", "sum"),
        unidades_fabrica_fora_de_operacao=("unidades", lambda s: int(
            s[j.loc[s.index, "fabrica_fora_de_operacao"] != ""].sum())),
        fabricas_fora=("fabrica_fora_de_operacao",
                       lambda s: "+".join(sorted(set("+".join(s).split("+")) - {""}))))
    tab["participacao_pct"] = (100 * tab["unidades"] / tab.groupby("ano")["unidades"]
                               .transform("sum")).round(1)
    tab = tab.sort_values(["uf", "ano"])
    tab["participacao_ano_anterior"] = tab.groupby("uf")["participacao_pct"].shift(1)
    alertas = []
    for r in tab.itertuples():
        a = []
        if r.unidades_fabrica_fora_de_operacao:
            a.append(f"fabrica fora do periodo de operacao: {r.fabricas_fora}")
        if pd.notna(r.participacao_ano_anterior) and abs(
                r.participacao_pct - r.participacao_ano_anterior) >= 5:
            a.append(f"participacao muda {r.participacao_ano_anterior:.1f} -> "
                     f"{r.participacao_pct:.1f}")
        if r.uf == "sem_fabrica":
            a.append("mes brasileiro sem fabrica na proposta nem na fonte")
        alertas.append("; ".join(a))
    tab["alerta"] = alertas
    return tab.sort_values(["ano", "unidades"], ascending=[True, False]).reset_index(drop=True)
