"""Calendario de politicas (2003-2026): atos oficiais, aliquotas e tabela mensal.

Duas tabelas de referencia, montadas a' mao por `ferramentas/politicas_referencia.py`
a partir das paginas oficiais guardadas em `dados/bruto/politicas_paginas/` (texto
com SHA-256 no manifesto):

- `dados/referencia/politicas_atos.csv` -- um ato por linha, com as datas, o ato que
  ele altera, o sentido e o trecho literal da pagina;
- `dados/referencia/politicas_aliquotas.csv` -- em formato longo, so' as aliquotas
  que o proprio ato fixa (IPI de automovel, Ex-tarifarios de eletrificados no
  imposto de importacao, IOF diario do credito a pessoa fisica). A NCM tem os pontos
  da TIPI; os digitos sem os pontos sao prefixo da NCM do Comex Stat.

Daqui sai `dados/processado/politicas_mensal.parquet`: uma linha por mes e ato em
vigor, para juntar ao painel pelo mes. Data vazia em `vigencia_fim` quer dizer que o
fim nao foi confirmado em pagina oficial aberta (ou que o ato segue em vigor): na
tabela mensal o ato vai ate' o ultimo mes.

O uso-teste nao estima efeito: poe a serie em volta da data de cada ato e marca onde
a data nao casa com movimento nenhum -- e' o lugar de conferir a data.
"""

from __future__ import annotations

import calendar
import csv
import hashlib
import re
from datetime import date
from pathlib import Path

import pandas as pd

from . import config, periodo, tipo_fonte

COLUNAS_ATOS = ["id", "tema", "instrumento", "numero", "data_ato", "data_publicacao",
                "vigencia_inicio", "vigencia_fim", "altera_id", "sentido", "alcance",
                "fonte_url", "tipo_fonte", "pagina_salva", "fonte_trecho", "observacao"]
COLUNAS_ALIQUOTAS = ["tributo", "ncm", "categoria", "categoria_ipi", "vigencia_inicio",
                     "vigencia_fim", "aliquota_pct", "aliquota_efetiva_habilitada", "ato_id",
                     "pagina_salva", "fonte_trecho", "reducao_ato_id", "reducao_pagina",
                     "reducao_trecho", "derivada", "observacao"]
# categorias principais do IPI: cada uma precisa de aliquota em todos os meses em que existe
CATEGORIAS_IPI = {
    "g1": "ate 1.000 cm3, gasolina", "f1": "ate 1.000 cm3, flex ou alcool",
    "g2": "1.000 a 1.500 cm3, gasolina", "f2": "1.000 a 1.500 cm3, flex ou alcool",
    "g3": "1.500 a 2.000 cm3, gasolina", "f3": "1.500 a 2.000 cm3, flex ou alcool",
    "g4": "acima de 2.000 cm3, gasolina", "f4": "acima de 2.000 cm3, flex ou alcool",
    "e40": "8703.40 (hibrido sem recarga externa)", "e60": "8703.60 (hibrido com recarga externa)",
    "e80": "8703.80 (eletrico)"}
# desde quando cada categoria existe na janela (as de combustao, desde o inicio do painel)
INICIO_CATEGORIA = {**{k: None for k in ("g1", "f1", "g2", "f2", "g3", "f3", "g4", "f4")},
                    "e40": "2018-11-01", "e60": "2018-11-01", "e80": "2018-11-01"}
# periodo em que a TIPI inclui os 30 pontos e a empresa habilitada tem reducao
PERIODO_HABILITADA = ("2011-12-16", "2017-12-31")
REDUCAO_HABILITADA = 30
COLUNAS_MENSAL = ["mes_ref", "ano", "mes", "ato_id", "tema", "sentido", "instrumento",
                  "numero", "vigencia_inicio", "vigencia_fim", "comeca_no_mes",
                  "termina_no_mes", "dias_em_vigor", "fracao_do_mes"]
TEMAS = ("ipi", "regime_automotivo", "imposto_importacao", "acordo_automotivo", "credito",
         "programa_desconto", "regulacao")
SENTIDOS = ("cria", "reduz", "aumenta", "prorroga", "encerra", "regulamenta")
TRIBUTOS = ("ipi", "ii", "iof")
INSTRUMENTOS = ("lei", "medida provisoria", "decreto", "resolucao", "circular", "portaria")
SEPARADOR = " [...] "
DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# NCM com os pontos da TIPI (4, 6 ou 8 digitos) e, se houver, o Ex
NCM = re.compile(r"^\d{4}(\.\d{2}(\.\d{2})?)?( Ex \d{2,3})?$")

# uso-teste: janela de tres meses de cada lado e o limiar de movimento, declarado
JANELA = 3
LIMIAR_PONTOS = 10.0
# pais parceiro de cada acordo, como o Comex Stat o escreve
PARCEIRO = {"mex": "México", "arg": "Argentina"}


def normalizar(texto: str) -> str:
    """Espacos colapsados: a conferencia do trecho nao depende da quebra de linha."""
    return " ".join(texto.split())


def ncm_digitos(ncm: str) -> str:
    """'8703.23.10 Ex 01' -> '87032310' (prefixo da NCM do Comex Stat)."""
    return ncm.split(" Ex ")[0].replace(".", "")


# ------------------------------------------------------------------ leitura


def _ler(caminho: Path) -> pd.DataFrame:
    return pd.read_csv(caminho, dtype=str, keep_default_na=False)


def carregar_atos(caminho: Path | None = None) -> pd.DataFrame:
    return _ler(caminho or config.POLITICAS_ATOS)


def carregar_aliquotas(caminho: Path | None = None) -> pd.DataFrame:
    return _ler(caminho or config.POLITICAS_ALIQUOTAS)


def carregar_manifesto(pasta: Path | None = None) -> pd.DataFrame:
    return _ler((pasta or config.POLITICAS_PAGINAS) / "manifesto.csv")


def paginas_citadas(atos: pd.DataFrame, aliquotas: pd.DataFrame) -> set[str]:
    return (set(atos["pagina_salva"]) | set(aliquotas["pagina_salva"])
            | (set(aliquotas["reducao_pagina"]) - {""}))


def textos(paginas, pasta: Path | None = None) -> dict[str, str]:
    """Texto normalizado de cada pagina guardada."""
    pasta = pasta or config.POLITICAS_PAGINAS
    return {p: normalizar((pasta / f"{p}.txt").read_text(encoding="utf-8"))
            for p in sorted(set(paginas)) if (pasta / f"{p}.txt").exists()}


# --------------------------------------------------------------- validacoes


def partes_ausentes(trecho: str, texto: str) -> list[str]:
    """Partes do trecho (separadas por " [...] ") que nao estao na pagina."""
    return [p for p in trecho.split(SEPARADOR) if normalizar(p) not in texto]


def problemas_das_paginas(manifesto: pd.DataFrame, pasta: Path | None = None) -> list[str]:
    """Cada pagina do manifesto existe, comeca pela sua URL e tem o SHA-256 anotado."""
    pasta = pasta or config.POLITICAS_PAGINAS
    saida = []
    for r in manifesto.itertuples():
        arquivo = pasta / f"{r.nome}.txt"
        if not arquivo.exists():
            saida.append(f"pagina {r.nome}: arquivo ausente")
            continue
        bruto = arquivo.read_bytes()
        if hashlib.sha256(bruto).hexdigest() != r.sha256_texto:
            saida.append(f"pagina {r.nome}: SHA-256 diferente do manifesto")
        if not bruto.decode("utf-8").startswith(f"URL: {r.url}\n"):
            saida.append(f"pagina {r.nome}: a primeira linha nao e' a URL do manifesto")
    return saida


def _data_ok(valor: str, vazia: bool = False) -> bool:
    if not valor:
        return vazia
    if not DATA.match(valor):
        return False
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def problemas_dos_atos(atos: pd.DataFrame, manifesto: pd.DataFrame,
                       texto: dict[str, str], mapa: dict[str, str] | None = None
                       ) -> list[str]:
    """Campos, datas, cadeia de alteracoes, pagina, URL, tipo da fonte e trecho."""
    mapa = mapa if mapa is not None else tipo_fonte.carregar_mapa()
    url_da_pagina = dict(zip(manifesto["nome"], manifesto["url"]))
    saida = []
    if list(atos.columns) != COLUNAS_ATOS:
        return [f"colunas de politicas_atos.csv: {list(atos.columns)}"]
    repetidos = atos["id"][atos["id"].duplicated()].tolist()
    if repetidos:
        saida.append(f"id repetido: {repetidos}")
    ids = set(atos["id"])
    for r in atos.itertuples():
        for campo, valores in (("tema", TEMAS), ("sentido", SENTIDOS),
                               ("instrumento", INSTRUMENTOS)):
            if getattr(r, campo) not in valores:
                saida.append(f"{r.id}: {campo} {getattr(r, campo)!r} fora da lista")
        if not _data_ok(r.data_ato) or not _data_ok(r.vigencia_inicio):
            saida.append(f"{r.id}: data_ato ou vigencia_inicio invalida")
        for campo in ("data_publicacao", "vigencia_fim"):
            if not _data_ok(getattr(r, campo), vazia=True):
                saida.append(f"{r.id}: {campo} invalida")
        if r.vigencia_fim and r.vigencia_fim < r.vigencia_inicio:
            saida.append(f"{r.id}: vigencia_fim antes de vigencia_inicio")
        if r.data_publicacao and r.data_publicacao < r.data_ato:
            saida.append(f"{r.id}: publicado antes da data do ato")
        if r.altera_id and r.altera_id not in ids:
            saida.append(f"{r.id}: altera_id {r.altera_id} nao existe")
        if r.altera_id == r.id:
            saida.append(f"{r.id}: altera a si mesmo")
        if r.pagina_salva not in url_da_pagina:
            saida.append(f"{r.id}: pagina {r.pagina_salva} fora do manifesto")
            continue
        if r.fonte_url != url_da_pagina[r.pagina_salva]:
            saida.append(f"{r.id}: fonte_url diferente da URL da pagina guardada")
        if r.tipo_fonte != "oficial" or tipo_fonte.tipo_de(r.fonte_url, mapa) != "oficial":
            saida.append(f"{r.id}: fonte nao e' oficial")
        if not r.fonte_trecho:
            saida.append(f"{r.id}: sem trecho")
        elif r.pagina_salva in texto:
            for parte in partes_ausentes(r.fonte_trecho, texto[r.pagina_salva]):
                saida.append(f"{r.id}: trecho fora da pagina: {parte[:80]!r}")
        else:
            saida.append(f"{r.id}: pagina {r.pagina_salva} sem texto")
    return saida


def problemas_das_aliquotas(aliquotas: pd.DataFrame, atos: pd.DataFrame,
                            manifesto: pd.DataFrame, texto: dict[str, str]) -> list[str]:
    """Campos, ato existente, pagina, trecho literal e uma aliquota por periodo."""
    saida = []
    if list(aliquotas.columns) != COLUNAS_ALIQUOTAS:
        return [f"colunas de politicas_aliquotas.csv: {list(aliquotas.columns)}"]
    ids = set(atos["id"])
    paginas = set(manifesto["nome"])
    for n, r in enumerate(aliquotas.itertuples(), start=2):
        rotulo = f"aliquota linha {n} ({r.ato_id} {r.ncm})"
        if r.tributo not in TRIBUTOS:
            saida.append(f"{rotulo}: tributo {r.tributo!r} fora da lista")
        if r.ato_id not in ids:
            saida.append(f"{rotulo}: ato inexistente")
        if r.tributo == "iof":
            if r.ncm:
                saida.append(f"{rotulo}: IOF nao tem NCM")
        elif not NCM.match(r.ncm):
            saida.append(f"{rotulo}: NCM fora do formato da TIPI")
        if not _data_ok(r.vigencia_inicio) or not _data_ok(r.vigencia_fim, vazia=True):
            saida.append(f"{rotulo}: data invalida")
        elif r.vigencia_fim and r.vigencia_fim < r.vigencia_inicio:
            saida.append(f"{rotulo}: fim antes do inicio")
        if not re.match(r"^\d+(,\d+)?$", r.aliquota_pct):
            saida.append(f"{rotulo}: aliquota {r.aliquota_pct!r} fora do formato")
        if r.derivada not in ("sim", "nao"):
            saida.append(f"{rotulo}: derivada {r.derivada!r}")
        if r.derivada == "sim" and not r.observacao:
            saida.append(f"{rotulo}: aliquota derivada sem a regra na observacao")
        if r.tributo == "ipi":
            saida += _problemas_do_ipi(r, rotulo, ids, paginas, texto)
        elif r.categoria_ipi or r.aliquota_efetiva_habilitada or r.reducao_ato_id:
            saida.append(f"{rotulo}: campos do IPI fora do IPI")
        if r.pagina_salva not in paginas:
            saida.append(f"{rotulo}: pagina fora do manifesto")
        elif r.pagina_salva not in texto:
            saida.append(f"{rotulo}: pagina sem texto")
        else:
            for parte in partes_ausentes(r.fonte_trecho, texto[r.pagina_salva]):
                saida.append(f"{rotulo}: trecho fora da pagina: {parte[:80]!r}")
    saida += sobreposicoes(aliquotas)
    return saida


def chave_da_aliquota(r) -> tuple:
    """A linha que um ato posterior substitui: no IPI, a mesma categoria (principal e a
    faixa); fora dele, a mesma NCM e categoria."""
    if r["tributo"] == "ipi" and r["categoria_ipi"]:
        return (r["tributo"], r["categoria_ipi"], r["categoria"])
    return (r["tributo"], r["ncm"], r["categoria"])


def _numero(valor: str) -> float:
    return float(valor.replace(",", "."))


def _problemas_do_ipi(r, rotulo: str, ids: set, paginas: set, texto: dict) -> list[str]:
    """Categoria principal, aliquota efetiva da habilitada e o trecho da reducao."""
    saida = []
    if r.categoria_ipi not in CATEGORIAS_IPI.values():
        saida.append(f"{rotulo}: categoria_ipi {r.categoria_ipi!r} fora da lista")
    if not re.match(r"^\d+(,\d+)?$", r.aliquota_efetiva_habilitada):
        return saida + [f"{rotulo}: aliquota efetiva {r.aliquota_efetiva_habilitada!r}"]
    ini, fim = PERIODO_HABILITADA
    dentro = ini <= r.vigencia_inicio and (r.vigencia_fim or "9999") <= fim
    nominal, efetiva = _numero(r.aliquota_pct), _numero(r.aliquota_efetiva_habilitada)
    if dentro:
        if not (r.reducao_ato_id and r.reducao_trecho):
            saida.append(f"{rotulo}: periodo dos 30 pontos sem a reducao da habilitada")
        elif abs(efetiva - max(nominal - REDUCAO_HABILITADA, 0)) > 1e-9:
            saida.append(f"{rotulo}: efetiva {efetiva} nao e' a nominal menos 30")
        if r.reducao_ato_id and r.reducao_ato_id not in ids:
            saida.append(f"{rotulo}: reducao de ato inexistente")
        if r.reducao_pagina not in paginas:
            saida.append(f"{rotulo}: pagina da reducao fora do manifesto")
        elif r.reducao_pagina in texto:
            for parte in partes_ausentes(r.reducao_trecho, texto[r.reducao_pagina]):
                saida.append(f"{rotulo}: trecho da reducao fora da pagina: {parte[:60]!r}")
    else:
        if r.reducao_ato_id or abs(efetiva - nominal) > 1e-9:
            saida.append(f"{rotulo}: fora de {ini}..{fim} a efetiva e' a nominal, sem reducao")
        if r.vigencia_inicio < ini <= (r.vigencia_fim or "9999"):
            saida.append(f"{rotulo}: periodo cruza o inicio dos 30 pontos")
    return saida


def lacunas_do_ipi(aliquotas: pd.DataFrame, primeiro: str, ultimo: str) -> list[dict]:
    """Periodos sem aliquota em cada categoria principal, de `primeiro` (ou do inicio da
    categoria) ao fim de `ultimo` (AAAA-MM)."""
    from datetime import timedelta
    ipi = aliquotas[aliquotas["tributo"] == "ipi"]
    fim_janela = date.fromisoformat(f"{ultimo}-{_dias(ultimo):02d}")
    saida = []
    for chave, rotulo in CATEGORIAS_IPI.items():
        inicio = date.fromisoformat(INICIO_CATEGORIA[chave] or f"{primeiro}-01")
        linhas = ipi[ipi["categoria_ipi"] == rotulo]
        periodos = sorted((date.fromisoformat(i), date.fromisoformat(f) if f else fim_janela)
                          for i, f in zip(linhas["vigencia_inicio"], linhas["vigencia_fim"]))
        coberto = inicio - timedelta(days=1)
        for i, f in periodos:
            if i > coberto + timedelta(days=1) and coberto < fim_janela:
                saida.append({"categoria": rotulo, "de": str(coberto + timedelta(days=1)),
                              "ate": str(min(i - timedelta(days=1), fim_janela))})
            coberto = max(coberto, f)
        if coberto < fim_janela:
            saida.append({"categoria": rotulo, "de": str(coberto + timedelta(days=1)),
                          "ate": str(fim_janela)})
    return saida


def sobreposicoes(aliquotas: pd.DataFrame) -> list[str]:
    """Uma aliquota por periodo: a mesma chave (`chave_da_aliquota`) nao tem dois periodos
    que se cruzam (cronograma que outro ato substituiu antes de valer fica fora)."""
    saida = []
    chaves = aliquotas.apply(chave_da_aliquota, axis=1)
    for (tributo, ncm, categoria), g in aliquotas.groupby(chaves):
        g = g.sort_values("vigencia_inicio")
        anterior = None
        for r in g.itertuples():
            if anterior is not None and (not anterior.vigencia_fim
                                         or anterior.vigencia_fim >= r.vigencia_inicio):
                saida.append(f"{tributo} {ncm} ({categoria}): {anterior.ato_id} "
                             f"{anterior.vigencia_inicio}..{anterior.vigencia_fim or 'aberto'} "
                             f"cruza {r.ato_id} {r.vigencia_inicio}")
            anterior = r
    return saida


# ----------------------------------------------------------------- mensal


def _dias(mes: str) -> int:
    ano, m = periodo.partes(mes)
    return calendar.monthrange(ano, m)[1]


def mensal(atos: pd.DataFrame, primeiro: str, ultimo: str) -> pd.DataFrame:
    """Uma linha por mes (de `primeiro` a `ultimo`, AAAA-MM) e ato em vigor."""
    linhas = []
    for r in atos.itertuples():
        inicio = r.vigencia_inicio[:7]
        fim = r.vigencia_fim[:7] if r.vigencia_fim else ultimo
        if max(inicio, primeiro) > min(fim, ultimo):
            continue  # ato antecedente (acaba antes da janela) ou posterior a ela
        for mes in periodo.intervalo(max(inicio, primeiro), min(fim, ultimo)):
            total = _dias(mes)
            dia_ini = int(r.vigencia_inicio[8:]) if mes == inicio else 1
            dia_fim = int(r.vigencia_fim[8:]) if r.vigencia_fim and mes == fim else total
            dias = dia_fim - dia_ini + 1
            ano, m = periodo.partes(mes)
            linhas.append({"mes_ref": mes, "ano": ano, "mes": m, "ato_id": r.id,
                           "tema": r.tema, "sentido": r.sentido,
                           "instrumento": r.instrumento, "numero": r.numero,
                           "vigencia_inicio": r.vigencia_inicio,
                           "vigencia_fim": r.vigencia_fim,
                           "comeca_no_mes": mes == inicio,
                           "termina_no_mes": bool(r.vigencia_fim) and mes == fim,
                           "dias_em_vigor": dias, "fracao_do_mes": round(dias / total, 4)})
    saida = pd.DataFrame(linhas, columns=COLUNAS_MENSAL)
    return saida.sort_values(["mes_ref", "tema", "ato_id"]).reset_index(drop=True)


# -------------------------------------------------------------- uso-teste


def eventos(atos: pd.DataFrame, aliquotas: pd.DataFrame) -> pd.DataFrame:
    """As datas de efeito: o inicio de cada ato e cada data em que uma aliquota do
    proprio ato muda depois dele (degraus, retorno da aliquota cheia)."""
    linhas = [{"ato_id": r.id, "tema": r.tema, "data": r.vigencia_inicio,
               "evento": "inicio do ato"} for r in atos.itertuples()]
    inicio = dict(zip(atos["id"], atos["vigencia_inicio"]))
    for (ato, data), _ in aliquotas.groupby(["ato_id", "vigencia_inicio"]):
        if data > inicio[ato]:
            tema = atos.loc[atos["id"] == ato, "tema"].iloc[0]
            linhas.append({"ato_id": ato, "tema": tema, "data": data,
                           "evento": "mudanca de aliquota fixada pelo ato"})
    return pd.DataFrame(linhas).sort_values(["data", "ato_id"]).reset_index(drop=True)


def serie_do_evento(ato: pd.Series, aliquotas: pd.DataFrame) -> tuple[str, dict]:
    """Qual serie olhar: vendas do painel, ou a importacao afetada (unidades
    ajustadas) -- as NCMs do proprio ato no imposto de importacao, o pais parceiro
    no acordo automotivo."""
    if ato["tema"] == "imposto_importacao":
        prefixos = sorted({ncm_digitos(n) for n in
                           aliquotas.loc[aliquotas["ato_id"] == ato["id"], "ncm"]})
        return ("importacao das NCMs do ato (" + ", ".join(prefixos) + "), unidades ajustadas",
                {"prefixos": prefixos})
    if ato["tema"] == "acordo_automotivo":
        pais = PARCEIRO[ato["id"].split("_")[2]]
        return (f"importacao do agregado de carros vinda de {pais}, unidades ajustadas",
                {"pais": pais})
    return "vendas do painel (automoveis e comerciais leves)", {}


def serie_importacao(comex: pd.DataFrame, ncms: pd.DataFrame, prefixos=None,
                     pais=None) -> pd.Series:
    """Importacao mensal em unidades ajustadas: das NCMs com os prefixos dados, ou do
    agregado de carros vinda do pais."""
    imp = comex[comex["fluxo"] == "importacao"]
    if prefixos:
        imp = imp[imp["ncm"].str.startswith(tuple(prefixos))]
    if pais:
        carros = set(ncms.loc[ncms["agregado_carros"] == "sim", "ncm"])
        imp = imp[imp["ncm"].isin(carros) & (imp["pais"] == pais)]
    return imp.groupby("mes_ref")["unidades_ajustadas"].sum()


def _janela(serie: pd.Series, mes: str) -> tuple[float | None, float | None, float | None]:
    antes = [periodo.de_indice(periodo.para_indice(mes) - k) for k in range(JANELA, 0, -1)]
    depois = [periodo.de_indice(periodo.para_indice(mes) + k) for k in range(1, JANELA + 1)]
    if not all(m in serie.index for m in antes + depois + [mes]):
        return None, None, None
    return (float(serie[antes].mean()), float(serie[mes]), float(serie[depois].mean()))


def _var(a, b):
    return round(100 * (b / a - 1), 1) if a else None


def comparar(serie: pd.Series, data: str) -> dict:
    """Media dos tres meses antes, o mes do ato e a media dos tres depois; as mesmas
    janelas um ano antes, que dao o movimento sazonal. `movimento` diz se a variacao
    do mes do ato ou dos tres seguintes, contra os tres anteriores, difere da do ano
    anterior em `LIMIAR_PONTOS` pontos ou mais. Nao e' estimativa de efeito."""
    mes = data[:7]
    antes, no_mes, depois = _janela(serie, mes)
    a0, m0, d0 = _janela(serie, f"{int(mes[:4]) - 1}{mes[4:]}")
    saida = {"media_3m_antes": antes, "mes_do_ato": no_mes, "media_3m_depois": depois,
             "var_mes_pct": _var(antes, no_mes), "var_depois_pct": _var(antes, depois),
             "var_mes_ano_anterior_pct": _var(a0, m0),
             "var_depois_ano_anterior_pct": _var(a0, d0)}
    difs = [abs(saida[a] - saida[b]) for a, b in (("var_mes_pct", "var_mes_ano_anterior_pct"),
                                                  ("var_depois_pct", "var_depois_ano_anterior_pct"))
            if saida[a] is not None and saida[b] is not None]
    if antes is None:
        saida["movimento"] = "fora da serie"
    elif not difs:
        saida["movimento"] = "sem ano anterior"
    else:
        saida["movimento"] = "sim" if max(difs) >= LIMIAR_PONTOS else "nao"
    for chave in ("media_3m_antes", "mes_do_ato", "media_3m_depois"):
        if saida[chave] is not None:
            saida[chave] = round(saida[chave])
    return saida


def uso_teste(atos: pd.DataFrame, aliquotas: pd.DataFrame, vendas: pd.Series,
              comex: pd.DataFrame, ncms: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por data de efeito, com a serie em volta dela."""
    por_id = atos.set_index("id")
    linhas = []
    for ev in eventos(atos, aliquotas).itertuples():
        ato = por_id.loc[ev.ato_id].copy()
        ato["id"] = ev.ato_id
        descricao, filtro = serie_do_evento(ato, aliquotas)
        serie = vendas if not filtro else serie_importacao(comex, ncms, **filtro)
        linhas.append({"ato_id": ev.ato_id, "tema": ev.tema, "instrumento": ato["instrumento"],
                       "numero": ato["numero"], "data": ev.data, "evento": ev.evento,
                       "serie": descricao, **comparar(serie, ev.data)})
    return pd.DataFrame(linhas)
