"""Emplacamento de autoveiculos nacionais e importados, dos anuarios da Anfavea.

So' registro e comparacao (rodada 12, sec. 2.4, uso-teste 2): nada do painel e'
reclassificado por estes numeros.

A serie mensal de licenciamento de nacionais e importados nao abriu (a pagina de
edicoes em Excel monta os links por script; ver o log da rodada 12). Os anuarios
abriram; deles, tres paginas guardadas em `dados/bruto/anfavea/` (URL e SHA-256 no
manifesto):

- `anuario2023_licenciamento_total`: tabela 2.3, licenciamento de autoveiculos novos,
  nacionais e importados, 1957-2022 (duas colunas de anos por linha);
- `anuario2023_licenciamento_importados`: tabela 2.7, importados, 1990-2022;
- `anuario2026_emplacamento_nacionais_importados`: tabelas 2.2.3 (nacionais),
  2.2.4 (importados) e 2.2.5 (importados por pais de origem), 2016-2025.

Ano presente nos dois anuarios usa o mais recente (2016-2022 vem do de 2026), como
na ADEFA. Cada linha lida guarda o seu trecho (a linha da tabela).
"""

from __future__ import annotations

import re

import pandas as pd

from . import config

NUM = r"(?:\d{1,3}(?:\.\d{3})*|-)"
SEGMENTOS = ("automoveis", "comerciais_leves", "caminhoes", "onibus")
PAGINA_TOTAL_2023 = "anfavea/anuario2023_licenciamento_total"
PAGINA_IMPORTADOS_2023 = "anfavea/anuario2023_licenciamento_importados"
PAGINA_2026 = "anfavea/anuario2026_emplacamento_nacionais_importados"
PAISES = {"CHINA": "China", "ARGENTINA": "Argentina", "ALEMANHA": "Alemanha",
          "MÉXICO": "México", "JAPÃO": "Japão", "SUÉCIA": "Suécia", "TAILÂNDIA": "Tailândia",
          "REINO UNIDO": "Reino Unido", "ESTADOS UNIDOS": "Estados Unidos",
          "COREIA DO SUL": "Coreia do Sul", "URUGUAI": "Uruguai", "ITÁLIA": "Itália",
          "FRANÇA": "França", "OUTROS": "Outros"}
BLOCOS_PAIS = ("automoveis", "comerciais_leves", "caminhoes", "onibus", "total")


def _n(valor: str) -> int:
    return 0 if valor == "-" else int(valor.replace(".", ""))


def texto(pagina: str) -> str:
    pasta, nome = pagina.split("/")
    return (config.ANFAVEA_LICENCIAMENTO / f"{nome}.txt").read_text(encoding="utf-8")


def _anos(trecho: str) -> list[dict]:
    """Linhas 'ANO automoveis comerciais_leves caminhoes onibus total' de um trecho de texto
    (a tabela 2.3 traz dois anos por linha)."""
    padrao = re.compile(rf"\b((?:19|20)\d\d) ({NUM}) ({NUM}) ({NUM}) ({NUM}) ({NUM})(?=\s|$)")
    saida = []
    for m in padrao.finditer(trecho):
        valores = [_n(v) for v in m.groups()[1:]]
        saida.append({"ano": int(m.group(1)), **dict(zip(SEGMENTOS, valores[:4])),
                      "total": valores[4], "trecho": m.group(0)})
    return saida


def _secao(texto_: str, inicio: str, fim: str | None) -> str:
    a = texto_.index(inicio)
    b = texto_.index(fim, a + len(inicio)) if fim else len(texto_)
    return texto_[a:b]


def series() -> pd.DataFrame:
    """Uma linha por ano e `tabela` (`total` ou `importados`), 2003-2025: unidades por
    segmento, total, pagina e trecho."""
    linhas = []
    t23 = texto(PAGINA_TOTAL_2023)
    for r in _anos(t23):
        if 2003 <= r["ano"] <= 2015:
            linhas.append({**r, "tabela": "total", "pagina_salva": PAGINA_TOTAL_2023})
    i23 = texto(PAGINA_IMPORTADOS_2023)
    for r in _anos(i23):
        if 2003 <= r["ano"] <= 2015:
            linhas.append({**r, "tabela": "importados", "pagina_salva": PAGINA_IMPORTADOS_2023})
    t26 = texto(PAGINA_2026)
    nacionais = _anos(_secao(t26, "2.2.3 Emplacamento", "2.2.4 Emplacamento"))
    importados = _anos(_secao(t26, "2.2.4 Emplacamento", "2.2.5 Emplacamento"))
    imp = {r["ano"]: r for r in importados}
    for r in nacionais:
        i = imp[r["ano"]]
        soma = {s: r[s] + i[s] for s in SEGMENTOS}
        linhas.append({"ano": r["ano"], **soma, "total": r["total"] + i["total"],
                       "trecho": f"{r['trecho']} [...] {i['trecho']}", "tabela": "total",
                       "pagina_salva": PAGINA_2026})
        linhas.append({**i, "tabela": "importados", "pagina_salva": PAGINA_2026})
    return (pd.DataFrame(linhas)[["ano", "tabela", *SEGMENTOS, "total", "pagina_salva",
                                  "trecho"]]
            .sort_values(["ano", "tabela"]).reset_index(drop=True))


def participacao_importados(serie: pd.DataFrame) -> pd.DataFrame:
    """Por ano: automoveis + comerciais leves, total e importados, e a participacao."""
    leves = serie.assign(leves=serie["automoveis"] + serie["comerciais_leves"])
    tab = leves.pivot(index="ano", columns="tabela", values="leves")
    return pd.DataFrame({
        "ano": tab.index, "anfavea_leves_total": tab["total"].values,
        "anfavea_leves_importados": tab["importados"].values,
        "anfavea_pct_importado": (100 * tab["importados"] / tab["total"]).round(1).values})


def _linhas_de_pais(bloco: str) -> list[tuple[str, list[int], str]]:
    """(nome PT, 10 valores, trecho) de cada linha de pais de um bloco da tabela 2.2.5. Nome
    partido em duas linhas ('REINO UNIDO /', numeros, 'United Kingdom') e' juntado."""
    linhas = [l.strip() for l in bloco.splitlines()]
    numeros = re.compile(rf"^((?:{NUM} ){{9}}{NUM})$")
    com_nome = re.compile(rf"^(.+?) / .+? ((?:{NUM} ){{9}}{NUM})$")
    saida = []
    for i, linha in enumerate(linhas):
        m = com_nome.match(linha)
        if m:
            saida.append((m.group(1), [_n(v) for v in m.group(2).split()], linha))
        elif linha.endswith(" /") and i + 1 < len(linhas) and numeros.match(linhas[i + 1]):
            saida.append((linha[:-2], [_n(v) for v in linhas[i + 1].split()],
                          f"{linha} {linhas[i + 1]}"))
    return saida


def por_pais() -> pd.DataFrame:
    """Tabela 2.2.5: uma linha por bloco (segmento ou total), pais e ano, 2016-2025. A linha
    TOTAL de cada bloco fica com `pais` = 'TOTAL'."""
    t26 = texto(PAGINA_2026)
    secao = t26[t26.index("2.2.5 Emplacamento"):]
    cabecalho = " ".join(str(a) for a in range(2016, 2026))
    blocos = secao.split(cabecalho)[1:]
    if len(blocos) != len(BLOCOS_PAIS):
        raise ValueError(f"tabela 2.2.5: {len(blocos)} blocos, esperados {len(BLOCOS_PAIS)}")
    linhas = []
    for nome_bloco, bloco in zip(BLOCOS_PAIS, blocos):
        for nome, valores, trecho in _linhas_de_pais(bloco):
            pais = "TOTAL" if nome.startswith("TOTAL") else PAISES.get(nome.strip(), "")
            for ano, v in zip(range(2016, 2026), valores):
                linhas.append({"bloco": nome_bloco, "pais_anfavea": nome.strip(), "pais": pais,
                               "ano": ano, "unidades": v, "pagina_salva": PAGINA_2026,
                               "trecho": trecho})
    return pd.DataFrame(linhas)


def problemas(serie: pd.DataFrame, paises: pd.DataFrame) -> list[str]:
    """Conferencias da leitura: segmentos somam o total; anos 2003-2025 completos; trecho na
    pagina; blocos da 2.2.5 somam a sua linha TOTAL e batem com a 2.2.4; pais conhecido."""
    saida = []
    for r in serie.itertuples():
        if sum(getattr(r, s) for s in SEGMENTOS) != r.total:
            saida.append(f"anfavea {r.tabela} {r.ano}: segmentos nao somam o total")
        normal = " ".join(texto(r.pagina_salva).split())
        for parte in r.trecho.split(" [...] "):
            if " ".join(parte.split()) not in normal:
                saida.append(f"anfavea {r.tabela} {r.ano}: trecho fora da pagina")
    for tabela in ("total", "importados"):
        anos = set(serie.loc[serie["tabela"] == tabela, "ano"])
        faltam = sorted(set(range(2003, 2026)) - anos)
        if faltam:
            saida.append(f"anfavea {tabela}: faltam os anos {faltam}")
    if serie.duplicated(["ano", "tabela"]).any():
        saida.append("anfavea: ano repetido na mesma tabela")
    imp = serie[serie["tabela"] == "importados"].set_index("ano")
    for bloco, g in paises.groupby("bloco"):
        for ano, h in g.groupby("ano"):
            total = h.loc[h["pais"] == "TOTAL", "unidades"].sum()
            if h.loc[h["pais"] != "TOTAL", "unidades"].sum() != total:
                saida.append(f"anfavea 2.2.5 {bloco} {ano}: paises nao somam a linha TOTAL")
            if bloco in SEGMENTOS and ano in imp.index and imp.loc[ano, bloco] != total:
                saida.append(f"anfavea 2.2.5 {bloco} {ano}: TOTAL difere da tabela 2.2.4")
    desconhecidos = sorted(set(paises.loc[paises["pais"] == "", "pais_anfavea"]))
    if desconhecidos:
        saida.append(f"anfavea 2.2.5: pais sem nome do Comex: {desconhecidos}")
    return saida
