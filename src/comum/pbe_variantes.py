"""Versoes eletrificadas do PBE que nao casam com chave nenhuma, mas tem nome de chave.

O casamento (`validacao_classificacao.casar`) e' por prefixo do nome, com
fronteira de palavra. Ele perde a versao eletrica escrita de outro jeito: `E-208
GT` nao comeca com `208`, `AMG GLC43` nao comeca com `AMG GLC ` e `320 ESPRINTER`
nao comeca com `ESPRINTER 320`. Duas consequencias (rodada "pbe, comex e
calendario"): o tipo nao entra pela P1, e a ausencia aparente vira saida.

Aqui ficam:

- **a busca de candidatos**: versao eletrificada do PBE, de 2021 em diante, sem
  casamento, de marca que tem chave cujo nome ela contem, por palavra inteira (nao
  por substring: `TT` nao esta' em `QUATTRO`). A chave tem de estar viva no ano:
  unidades no painel entre o ano anterior e o seguinte ao da tabela;
- **o teste da planilha** (`teste_da_planilha`): nos meses em que
  `Vendas_Geral.xlsx` traz a variante a' parte, o painel-base e' a base mais a
  variante (`soma`) ou so' a base (`nao_soma`);
- **a guarda da saida** (`guardas`): ano e tipo em que ha' versao candidata sem
  decisao de casamento; ali a ausencia no PBE nao prova saida.

A decisao de cada nome fica em `config/pbe_modelos.csv` (`decisao` = `casa`,
`nao_casa` ou `sem_evidencia`), com a evidencia na observacao, pela ordem do
teste: chave propria, planilha soma, planilha nao soma, sem evidencia.
"""

from __future__ import annotations

import re

import pandas as pd

from . import config, pbe

CHAVE = ["marca", "modelo", "segmento"]
PRIMEIRO_ANO = 2021
ELETRIFICADOS = frozenset({"hev", "phev", "bev", "mhev", "hibrido_indefinido", "reev"})
DECISOES = ("casa", "nao_casa", "sem_evidencia")
RELACOES = ("mesmo_nome", "contem", "prefixo", "sufixo")
PREFIXOS_DE_VARIANTE = ("E", "I")
COLUNAS = ["ano_pbe", "marca_pbe", "modelo_versao", "valor_taxonomia", "marca", "modelo",
           "segmento", "relacao", "chave_viva", "prefixo_pbe", "decisao", "observacao"]


# ------------------------------------------------------------ nomes


def tokens(nome: str) -> list[str]:
    """Palavras do nome, sem hifen, sem o `AMG` do inicio e com o `E` solto colado
    a' palavra seguinte (`320 E SPRINTER` -> `320`, `ESPRINTER`)."""
    partes = [p.replace("-", "") for p in pbe.normalizar(nome).split(" ")]
    partes = [p for p in partes if p]
    if partes and partes[0] == "AMG":
        partes = partes[1:]
    saida: list[str] = []
    i = 0
    while i < len(partes):
        atual = partes[i]
        seguinte = partes[i + 1] if i + 1 < len(partes) else ""
        if atual == "E" and len(seguinte) >= 2 and seguinte[0].isalpha():
            saida.append(atual + seguinte)
            i += 2
            continue
        saida.append(atual)
        i += 1
    return saida


def _ngramas(palavras: list[str], maximo: int = 3) -> list[tuple[int, str]]:
    return [(i, "".join(palavras[i:j])) for i in range(len(palavras))
            for j in range(i + 1, min(len(palavras), i + maximo) + 1)]


def relacao(nome_pbe: str, modelo: str) -> str:
    """Como o nome do PBE contem o da chave, ou vazio.

    - `mesmo_nome`: o nome comeca com o da chave, a menos de espaco, hifen, `AMG` ou
      ordem das palavras (`CLA 200` e `CLA200`; `320 ESPRINTER` e `ESPRINTER 320`);
    - `contem`: o nome da chave aparece inteiro mais adiante (`G CHEROKEE 4XE`);
    - `prefixo`: `E` ou `I` colado na frente (`E-208`, `IX3`);
    - `sufixo`: letra colada depois de numero (`RAV4H`, `CLA45S`) ou numero colado
      depois de letra (`GLC43`, `GLC63S`) -- nunca letra depois de letra (`GLB` nao
      e' `GL`) nem numero depois de numero (`M60` nao e' `M6`).
    """
    palavras, chave = tokens(nome_pbe), tokens(modelo)
    alvo = "".join(chave)
    if len(alvo) < 2 or not palavras:
        return ""
    gramas = _ngramas(palavras)
    if any(i == 0 and g == alvo for i, g in gramas) or (
            len(chave) >= 2 and sorted(chave) == sorted(palavras[:len(chave)])):
        return "mesmo_nome"
    if any(g == alvo for _, g in gramas) or set(chave) <= set(palavras) and len(chave) >= 2:
        return "contem"
    if any(g in {p + alvo for p in PREFIXOS_DE_VARIANTE} for _, g in gramas):
        return "prefixo"
    for _, g in gramas:
        if g.startswith(alvo) and len(g) > len(alvo):
            resto = g[len(alvo):]
            if alvo[-1].isdigit() and len(resto) == 1 and resto.isalpha():
                return "sufixo"
            if alvo[-1].isalpha() and resto[0].isdigit() and len(resto) <= 3:
                return "sufixo"
    return ""


# ------------------------------------------------------------ decisoes


def carregar_decisoes() -> pd.DataFrame:
    tabela = pd.read_csv(config.PBE_MODELOS, dtype=str, keep_default_na=False)
    if "decisao" not in tabela.columns:
        tabela["decisao"] = "casa"
    tabela["decisao"] = tabela["decisao"].replace("", "casa")
    return tabela


def _com_fronteira(texto: str, prefixo: str) -> bool:
    return texto == prefixo or texto.startswith(prefixo + " ") or texto.startswith(prefixo + "-")


def decisao_da_versao(marca: str, modelo: str, nome_pbe: str,
                      decisoes: pd.DataFrame) -> tuple[str, str, str]:
    """(decisao, prefixo, observacao) da linha de `config/pbe_modelos.csv` que trata
    desta versao para esta chave: o prefixo mais longo. `casa` vale com fronteira de
    palavra (como no casamento); `nao_casa` e `sem_evidencia`, por prefixo simples."""
    texto = pbe.normalizar(nome_pbe)
    linhas = decisoes[(decisoes["marca_painel"] == marca) & (decisoes["modelo_painel"] == modelo)]
    achadas = []
    for _, d in linhas.iterrows():
        prefixo = pbe.normalizar(d["prefixo_pbe"])
        casa = (_com_fronteira(texto, prefixo) if d["decisao"] == "casa"
                else texto.startswith(prefixo))
        if casa:
            achadas.append((len(prefixo), d["decisao"], d["prefixo_pbe"], d["observacao"]))
    if not achadas:
        return "", "", ""
    _, decisao, prefixo, observacao = max(achadas, key=lambda a: a[0])
    return decisao, prefixo, observacao


# ------------------------------------------------------------ candidatos


def anos_vivos(painel: pd.DataFrame) -> dict[tuple, set[int]]:
    """Chave -> anos com unidades no painel."""
    vendas = painel[painel["unidades"] > 0]
    return {k: set(g["mes_ref"].str[:4].astype(int))
            for k, g in vendas.groupby(CHAVE)}


def candidatos(casado: pd.DataFrame, chaves: pd.DataFrame, painel: pd.DataFrame,
               marcas: dict[str, list[str]], decisoes: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (versao eletrificada sem casamento, chave cujo nome ela contem)."""
    soltas = casado[(casado["marca"] == "")
                    & (casado["ano_pbe"].astype(int) >= PRIMEIRO_ANO)
                    & casado["valor_taxonomia"].isin(ELETRIFICADOS)]
    por_marca: dict[str, list[tuple]] = {}
    for marca, modelo, segmento in chaves[CHAVE].drop_duplicates().itertuples(index=False):
        por_marca.setdefault(marca, []).append((marca, modelo, segmento))
    vivos = anos_vivos(painel)
    linhas = []
    for r in soltas.itertuples(index=False):
        ano = int(r.ano_pbe)
        for marca_painel in marcas.get(r.marca_pbe, []):
            for chave in por_marca.get(marca_painel, []):
                partes = [chave[1]] + [p for p in chave[1].split("/") if p and p != chave[1]]
                achada = next((x for x in (relacao(r.modelo_versao, p) for p in partes) if x), "")
                if not achada:
                    continue
                viva = bool(vivos.get(chave, set()) & {ano - 1, ano, ano + 1})
                decisao, prefixo, observacao = decisao_da_versao(
                    chave[0], chave[1], r.modelo_versao, decisoes)
                linhas.append({"ano_pbe": r.ano_pbe, "marca_pbe": r.marca_pbe,
                               "modelo_versao": r.modelo_versao,
                               "valor_taxonomia": r.valor_taxonomia,
                               **dict(zip(CHAVE, chave)), "relacao": achada,
                               "chave_viva": viva, "prefixo_pbe": prefixo,
                               "decisao": decisao, "observacao": observacao})
    return (pd.DataFrame(linhas, columns=COLUNAS)
            .sort_values(CHAVE + ["ano_pbe", "modelo_versao"]).reset_index(drop=True))


def guardas(tabela: pd.DataFrame) -> pd.DataFrame:
    """Ano e tipo do PBE, por chave, em que ha' versao candidata viva sem decisao de
    casamento (`sem_evidencia` ou nenhuma): ali a ausencia nao prova saida."""
    abertas = tabela[tabela["chave_viva"] & ~tabela["decisao"].isin(["casa", "nao_casa"])]
    return (abertas.assign(ano=abertas["ano_pbe"].astype(int))
            [CHAVE + ["ano", "valor_taxonomia", "modelo_versao"]]
            .drop_duplicates().reset_index(drop=True))


# ------------------------------------------------------------ planilha


def teste_da_planilha(cruzada: pd.DataFrame, base: str, variante: str,
                      marcas_painel: set[str], marcas_planilha: set[str]) -> pd.DataFrame:
    """Meses em que a planilha traz a variante a' parte: painel-base contra base da
    planilha, com e sem a variante. `cruzada` e' `saidas/referencia_cruzada.csv`."""
    na_planilha = cruzada["marca_planilha_grafia"].fillna("").str.upper().isin(
        {m.upper() for m in marcas_planilha})
    var = cruzada[na_planilha & (cruzada["modelo"] == variante)
                  & (cruzada["unidades_planilha"] > 0)]
    linhas = []
    for mes, v in var.groupby("mes_ref"):
        do_mes = cruzada[(cruzada["mes_ref"] == mes) & (cruzada["modelo"] == base)]
        painel = do_mes.loc[do_mes["marca"].isin(marcas_painel), "unidades_painel"].sum()
        planilha = do_mes.loc[do_mes["marca_planilha_grafia"].fillna("").str.upper().isin(
            {m.upper() for m in marcas_planilha}), "unidades_planilha"].sum()
        variante_u = v["unidades_planilha"].sum()
        if painel == 0 or planilha == 0:
            resultado = "sem_base"
        elif painel == planilha + variante_u and painel != planilha:
            resultado = "soma"
        elif painel == planilha and painel != planilha + variante_u:
            resultado = "nao_soma"
        else:
            resultado = "inconclusivo"
        linhas.append({"mes_ref": mes, "base": base, "variante": variante,
                       "painel_base": int(painel), "planilha_base": int(planilha),
                       "planilha_variante": int(variante_u), "resultado": resultado})
    return pd.DataFrame(linhas, columns=["mes_ref", "base", "variante", "painel_base",
                                         "planilha_base", "planilha_variante", "resultado"])


def veredito(teste: pd.DataFrame) -> str:
    """`soma`, `nao_soma`, `contraditorio` ou `sem_evidencia`, sobre os meses com base."""
    resultados = set(teste["resultado"]) - {"sem_base", "inconclusivo"}
    if resultados == {"soma"}:
        return "soma"
    if resultados == {"nao_soma"}:
        return "nao_soma"
    if resultados:
        return "contraditorio"
    return "sem_evidencia"


def ler_candidatos(caminho=None) -> pd.DataFrame:
    caminho = caminho or config.PBE_VARIANTES_CANDIDATOS
    if not caminho.exists():
        return pd.DataFrame(columns=COLUNAS)
    tabela = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    tabela["chave_viva"] = tabela["chave_viva"] == "True"
    return tabela


def sem_evidencia(tabela: pd.DataFrame, tipos: pd.DataFrame,
                  familia: dict[str, set[str]]) -> pd.DataFrame:
    """A lista do item 4: por chave e familia de versoes sem decisao de casamento
    (`sem_evidencia` ou nenhuma), os anos do PBE e os anos de ausencia que a guarda
    descartou (`ausencia_descartada`, por tipo e vigencia: ali o tipo nao sai).

    `tipos`: a tabela de tipos da propulsao anual (`anos_guardados`); `familia`:
    tipo da classificacao -> valores do PBE que contam como versao dele.
    """
    abertas = tabela[tabela["chave_viva"] & ~tabela["decisao"].isin(["casa", "nao_casa"])]
    linhas = []
    for (marca, modelo, segmento, prefixo, valor), g in abertas.groupby(
            CHAVE + ["prefixo_pbe", "valor_taxonomia"]):
        da_chave = tipos[(tipos["marca"] == marca) & (tipos["modelo"] == modelo)
                         & (tipos["segmento"] == segmento) & (tipos["anos_guardados"] != "")]
        segurou = [f"{t['tipo']} {t['vigencia_inicio']}: {t['anos_guardados'].replace(';', ', ')}"
                   for _, t in da_chave.iterrows()
                   if valor in familia.get(t["tipo"], {t["tipo"]})]
        linhas.append({"marca": marca, "modelo": modelo, "segmento": segmento,
                       "valor_taxonomia": valor, "prefixo_pbe": prefixo,
                       "versoes": "; ".join(sorted(set(g["modelo_versao"]))),
                       "anos_pbe": ", ".join(sorted(set(g["ano_pbe"]))),
                       "relacao": "+".join(sorted(set(g["relacao"]))),
                       "decisao": g["decisao"].iloc[0] or "sem_decisao",
                       "ausencia_descartada": "; ".join(segurou),
                       "observacao": g["observacao"].iloc[0]})
    return pd.DataFrame(linhas, columns=["marca", "modelo", "segmento", "valor_taxonomia",
                                         "prefixo_pbe", "versoes", "anos_pbe", "relacao",
                                         "decisao", "ausencia_descartada", "observacao"])
