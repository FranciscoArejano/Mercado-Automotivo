"""Validacao do rascunho de classificacao contra fonte.

Dois atributos do rascunho saiam quase so' do conhecimento do assistente:
propulsao (99,9% do volume) e origem da producao (98,7%). Aqui eles sao
confrontados com fonte, **sem sobrescrever a proposta**:

- **Propulsao contra o PBE Veicular.** As tabelas do Inmetro listam, por versao,
  o tipo de propulsao (coluna propria desde 2021) e o combustivel. O casamento
  com o painel e' por marca e prefixo do nome do modelo, versao ignorada: so' se
  quer o conjunto de propulsoes oferecidas por modelo e ano. O mapeamento para a
  taxonomia do projeto esta' em `config/pbe_propulsao.csv`.
- **Origem contra fontes datadas** (`dados/referencia/origem_fontes.csv`), cada
  uma aberta na rodada de validacao, com o trecho que sustenta a data.

Ausencia nao e' evidencia: modelo que nao aparece no PBE fica `ausente`, nunca
vira combustao por omissao.
"""

from __future__ import annotations

import re

import pandas as pd

from . import config, pbe

CHAVE = ["marca", "modelo", "segmento"]
PRIMEIRO_ANO_PBE = 2009
PREFIXOS_DESCARTAVEIS = ("THE NEW ", "ALL NEW ", "NOVO ", "NOVA ", "NEW ")
# Anos sem coluna de propulsao: o hibrido so' aparece se o nome disser.
ULTIMO_ANO_SEM_COLUNA = 2020

ORDEM_CONFRONTO = ("contradiz", "ajusta_data", "inconclusivo", "complementa", "confirma")
# Decisao 3: ausencia no PBE so' informa a partir do ano em que ele cobre esta
# fracao do volume do painel.
LIMIAR_COBERTURA = 80.0


# ------------------------------------------------------------- propulsao


def regras_propulsao() -> pd.DataFrame:
    return pd.read_csv(config.PBE_PROPULSAO, dtype=str, keep_default_na=False)


def _casa(valor: str, padrao: str) -> bool:
    return padrao == "*" or valor == padrao


def mapear_propulsao(tipo: str, combustivel: str, marcador: str, motor: str,
                     regras: pd.DataFrame) -> tuple[str, str]:
    """(valor da taxonomia, ordem da regra). Valor vazio = sem mapeamento."""
    marcadores = set(marcador.split("+")) if marcador else set()
    if not tipo and motor == "ELETRICO":
        tipo = "(motor ELETRICO)"
    for _, regra in regras.iterrows():
        if not _casa(tipo, regra["tipo_propulsao"]):
            continue
        if not _casa(combustivel, regra["combustivel"]):
            continue
        if regra["marcador_nome"] != "*" and regra["marcador_nome"] not in marcadores:
            continue
        return regra["valor"], regra["ordem"]
    return "", ""


def marcas_pbe() -> dict[str, list[str]]:
    tabela = pd.read_csv(config.PBE_MARCAS, dtype=str, keep_default_na=False)
    return {pbe.normalizar(m): [x for x in p.split(";") if x]
            for m, p in zip(tabela["marca_pbe"], tabela["marcas_painel"])}


def nomes_do_painel(chaves: pd.DataFrame) -> dict[str, list[tuple[str, tuple]]]:
    """marca do painel -> [(nome normalizado, chave)], com apelidos.

    Nome com barra (FOX/CROSS FOX) vale por cada parte. Apelidos explicitos,
    para nomes que o PBE escreve de outro jeito, ficam em `config/pbe_modelos.csv`.
    """
    nomes: dict[str, list[tuple[str, tuple]]] = {}
    for marca, modelo, segmento in chaves[CHAVE].itertuples(index=False):
        chave = (marca, modelo, segmento)
        formas = {pbe.normalizar(modelo)} | {pbe.normalizar(p) for p in modelo.split("/") if p}
        for forma in formas:
            nomes.setdefault(marca, []).append((forma, chave))
    if config.PBE_MODELOS.exists():
        apelidos = pd.read_csv(config.PBE_MODELOS, dtype=str, keep_default_na=False)
        for _, a in apelidos.iterrows():
            alvo = chaves[(chaves["marca"] == a["marca_painel"])
                          & (chaves["modelo"] == a["modelo_painel"])]
            for chave in map(tuple, alvo[CHAVE].to_numpy()):
                nomes.setdefault(a["marca_painel"], []).append(
                    (pbe.normalizar(a["prefixo_pbe"]), chave))
    for marca in nomes:  # o mais longo primeiro: COROLLA CROSS antes de COROLLA
        nomes[marca].sort(key=lambda par: -len(par[0]))
    return nomes


def _prefixo(texto: str, nome: str) -> bool:
    return texto == nome or texto.startswith(nome + " ") or texto.startswith(nome + "-")


def _achar(texto: str, marcas_painel: list[str], nomes: dict) -> list[tuple]:
    achadas: list[tuple] = []
    for marca_painel in marcas_painel:
        candidatos = nomes.get(marca_painel, [])
        for tentativa in [texto] + [texto[len(p):] for p in PREFIXOS_DESCARTAVEIS
                                    if texto.startswith(p)]:
            melhor = next((len(n) for n, _ in candidatos if _prefixo(tentativa, n)), None)
            if melhor is not None:
                achadas += [c for n, c in candidatos if len(n) == melhor and _prefixo(tentativa, n)]
                break
    return list(dict.fromkeys(achadas))


def casar(versoes: pd.DataFrame, chaves: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (versao do PBE, chave do painel) casadas; sem casamento, chave vazia.

    `casou_por` diz como: pelo nome da propria linha, ou -- so' quando ele nao casa
    -- pela linha de cima mais o nome (`linha_acima`, a celula quebrada de 2017-2019).
    """
    marcas = marcas_pbe()
    nomes = nomes_do_painel(chaves)
    saida = []
    for registro in versoes.to_dict("records"):
        marcas_painel = marcas.get(registro["marca_pbe"], [])
        achadas = _achar(registro["modelo_versao"], marcas_painel, nomes)
        casou_por = "nome" if achadas else ""
        acima = registro.get("linha_acima", "")
        if not achadas and acima:
            achadas = _achar(f"{acima} {registro['modelo_versao']}".strip(), marcas_painel, nomes)
            casou_por = "linha_acima" if achadas else ""
        if not achadas:
            saida.append({**registro, "casou_por": "", "marca": "", "modelo": "", "segmento": ""})
        for marca, modelo, segmento in achadas:
            saida.append({**registro, "casou_por": casou_por, "marca": marca, "modelo": modelo,
                          "segmento": segmento})
    return pd.DataFrame(saida)


def _meses_no_ano(inicio: str, fim: str, ano: int) -> int:
    i = max(int(inicio[:4]) * 12 + int(inicio[5:7]), ano * 12 + 1)
    f = min(int(fim[:4]) * 12 + int(fim[5:7]), ano * 12 + 12)
    return max(0, f - i + 1)


def _anos_compactos(anos: list[int]) -> str:
    if not anos:
        return ""
    anos = sorted(set(anos))
    faixas, inicio, anterior = [], anos[0], anos[0]
    for ano in anos[1:] + [None]:
        if ano is not None and ano == anterior + 1:
            anterior = ano
            continue
        faixas.append(str(inicio) if inicio == anterior else f"{inicio}-{anterior}")
        if ano is not None:
            inicio = anterior = ano
    return ", ".join(faixas)


def comparar_pbe(rascunho: pd.DataFrame, casado: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta pbe_propulsao, pbe_anos, pbe_situacao e pbe_diferenca."""
    saida = rascunho.copy()
    por_chave = {k: g for k, g in casado[casado["marca"] != ""].groupby(CHAVE)}
    colunas: dict[str, dict] = {c: {} for c in ("pbe_propulsao", "pbe_anos", "pbe_situacao",
                                                 "pbe_diferenca", "pbe_nota")}
    for chave, linhas_modelo in saida.groupby(CHAVE, sort=False):
        versoes = por_chave.get(chave)
        vigencias = list(linhas_modelo[["vigencia_inicio", "vigencia_fim"]].itertuples(
            index=False, name=None))
        # cada ano do PBE vai para a vigencia com mais meses naquele ano
        ano_para_vigencia: dict[int, int] = {}
        if versoes is not None:
            for ano in sorted(versoes["ano_pbe"].astype(int).unique()):
                meses = [_meses_no_ano(i, f, ano) for i, f in vigencias]
                if max(meses) > 0:
                    ano_para_vigencia[ano] = meses.index(max(meses))
        for posicao, (indice, linha) in enumerate(linhas_modelo.iterrows()):
            anos = [a for a, v in ano_para_vigencia.items() if v == posicao]
            proposta = {p for p in linha["propulsao_oferecida"].split("+") if p}
            notas = []
            if not anos:
                situacao, achado, diferenca = "ausente", set(), ""
                if linha["vigencia_fim"] < f"{PRIMEIRO_ANO_PBE}-01":
                    notas.append(f"vigencia anterior ao PBE ({PRIMEIRO_ANO_PBE})")
                elif versoes is not None:
                    notas.append("no PBE so' em anos fora desta vigencia")
            else:
                deste = versoes[versoes["ano_pbe"].astype(int).isin(anos)]
                achado = {v for v in deste["valor_taxonomia"] if v}
                if not achado:
                    situacao, diferenca = "ausente", ""
                    notas.append("so' versoes sem mapeamento para a taxonomia")
                else:
                    so_pbe, so_proposta = achado - proposta, proposta - achado
                    if ("gasolina" in so_proposta and "flex" in proposta and "flex" in achado
                            and linha["vigencia_inicio"] < f"{PRIMEIRO_ANO_PBE}-01"):
                        so_proposta.discard("gasolina")
                        notas.append("gasolina anterior ao PBE (transicao flex, decisao de "
                                     "2026-10-01)")
                    situacao = "concorda" if not so_pbe and not so_proposta else "diverge"
                    partes = []
                    if so_pbe:
                        partes.append("so' no PBE: " + "+".join(sorted(so_pbe)))
                    if so_proposta:
                        partes.append("so' na proposta: " + "+".join(sorted(so_proposta)))
                    diferenca = "; ".join(partes)
                    if max(anos) <= ULTIMO_ANO_SEM_COLUNA and so_proposta & {"hev", "phev", "mhev"}:
                        notas.append("tabelas ate' 2020 nao tem coluna de propulsao: hibrido "
                                     "sem marcador no nome sai como combustao")
            colunas["pbe_propulsao"][indice] = "+".join(
                p for p in ("gasolina", "flex", "diesel", "mhev", "hev", "phev", "reev", "bev")
                if p in achado)
            colunas["pbe_anos"][indice] = _anos_compactos(anos)
            colunas["pbe_situacao"][indice] = situacao
            colunas["pbe_diferenca"][indice] = diferenca
            colunas["pbe_nota"][indice] = "; ".join(notas)
    for nome, valores in colunas.items():
        saida[nome] = pd.Series(valores)
    return saida


def cobertura_por_ano(painel: pd.DataFrame, versoes: pd.DataFrame,
                      casado: pd.DataFrame) -> pd.DataFrame:
    """Por ano, a fracao do volume do painel cujo modelo aparece na tabela do PBE daquele ano.

    Cobertura por modelo, nao por versao: o modelo conta inteiro se uma versao
    dele esta' na tabela. Depende do casamento -- modelo que o PBE escreve de um
    jeito que o casamento nao reconhece conta como ausente.
    """
    no_pbe = casado.loc[casado["marca"] != "", ["ano_pbe"] + CHAVE].drop_duplicates()
    no_pbe = no_pbe.assign(ano=no_pbe["ano_pbe"].astype(int), no_pbe=True).drop(columns="ano_pbe")
    volume = painel.groupby(["ano"] + CHAVE, as_index=False)["unidades"].sum()
    juntos = volume.merge(no_pbe, on=["ano"] + CHAVE, how="left")
    juntos["no_pbe"] = juntos["no_pbe"].eq(True)
    tabela = versoes.groupby(versoes["ano_pbe"].astype(int)).size()
    linhas = []
    for ano, grupo in juntos.groupby("ano"):
        dentro = grupo[grupo["no_pbe"]]
        linhas.append({
            "ano": int(ano), "versoes_na_tabela": int(tabela.get(ano, 0)),
            "modelos_do_painel": len(grupo), "modelos_na_tabela": len(dentro),
            "unidades_painel": int(grupo["unidades"].sum()),
            "unidades_modelo_na_tabela": int(dentro["unidades"].sum()),
            "cobertura_pct": round(100 * dentro["unidades"].sum() / grupo["unidades"].sum(), 1),
        })
    return pd.DataFrame(linhas)


def ano_de_corte(cobertura: pd.DataFrame, limiar: float = LIMIAR_COBERTURA) -> int:
    """Primeiro ano em que a cobertura do PBE atinge o limiar."""
    atingem = cobertura.loc[cobertura["cobertura_pct"] >= limiar, "ano"]
    if atingem.empty:
        raise ValueError(f"o PBE nunca cobre {limiar}% do volume")
    return int(atingem.min())


# ---------------------------------------------------------------- origem


def carregar_fontes_origem() -> pd.DataFrame:
    if not config.ORIGEM_FONTES.exists():
        return pd.DataFrame(columns=CHAVE)
    return pd.read_csv(config.ORIGEM_FONTES, dtype=str, keep_default_na=False)


def anexar_origem(rascunho: pd.DataFrame, fontes: pd.DataFrame) -> pd.DataFrame:
    """Fontes datadas de origem por modelo, sem tocar em `origem_producao`."""
    saida = rascunho.copy()
    por_chave = {k: g for k, g in fontes.groupby(CHAVE)} if not fontes.empty else {}
    urls, trechos, datas, confrontos, situacoes = [], [], [], [], []
    for linha in saida[CHAVE].itertuples(index=False, name=None):
        grupo = por_chave.get(linha)
        if grupo is None:
            urls.append(""); trechos.append(""); datas.append("")
            confrontos.append(""); situacoes.append("sem_fonte")
            continue
        urls.append(" | ".join(dict.fromkeys(grupo["origem_fonte_url"])))
        trechos.append(" | ".join(grupo["origem_fonte_trecho"]))
        datas.append("; ".join(f"{e} {d}".strip() for e, d in
                               zip(grupo["evento"], grupo["origem_data_fonte"])))
        confrontos.append(min(grupo["confronto_com_proposta"], key=ORDEM_CONFRONTO.index))
        situacoes.append("com_fonte_datada" if (grupo["origem_data_fonte"] != "").any()
                         else "fonte_sem_data")
    saida["origem_fonte_url"] = urls
    saida["origem_fonte_trecho"] = trechos
    saida["origem_data_fonte"] = datas
    saida["origem_confronto"] = confrontos
    saida["origem_situacao"] = situacoes
    return saida


TROCA_SEM_DATA = re.compile(r"nao datad|aproximad|Datas|Fronteira", re.IGNORECASE)
FALA_DE_ORIGEM = re.compile(
    r"producao|importad|nacional|Camacari|Iracemapolis|Araquari|Catalao|Anapolis|Resende|"
    r"Itatiaia|Jacarei|Sao Jose dos Pinhais|Horizonte|Mexico|Argentina|Fronteira|montag",
    re.IGNORECASE)


def casos_de_origem(rascunho: pd.DataFrame, top: int) -> pd.Series:
    """Linhas que a rodada de validacao manda buscar fonte de origem.

    Troca de origem nao datada ou datada so' aproximadamente, ou origem `media`
    ou `baixa` entre os `top` maiores modelos.
    """
    troca = (rascunho["observacao"].str.contains(TROCA_SEM_DATA)
             & rascunho["observacao"].str.contains(FALA_DE_ORIGEM)) | (
        rascunho["origem_producao"] == "ambos")
    fraca = (rascunho["posicao"] <= top) & rascunho["confianca_origem"].isin(["media", "baixa"])
    return troca | fraca


# ------------------------------------------------------------ adjudicacao


def a_adjudicar(rascunho: pd.DataFrame, top: int) -> pd.DataFrame:
    """So' o que ainda precisa de decisao humana, maior volume primeiro."""
    casos = casos_de_origem(rascunho, top)
    motivos = []
    for (_, linha), caso in zip(rascunho.iterrows(), casos):
        m = []
        if linha["pbe_situacao"] == "diverge":
            m.append("PBE diverge")
        if linha["pbe_situacao"] == "ausente" and linha["posicao"] <= top:
            m.append("ausente no PBE")
        if linha["origem_confronto"] in ("contradiz", "ajusta_data"):
            m.append(f"fonte de origem {linha['origem_confronto'].replace('_', ' ')}")
        elif caso and linha["origem_situacao"] != "com_fonte_datada":
            m.append("origem sem fonte datada")
        motivos.append("; ".join(m))
    marcadas = rascunho.assign(motivo=motivos)
    marcadas = marcadas[marcadas["motivo"] != ""]
    colunas = ["motivo", "posicao", "marca", "modelo", "segmento", "vigencia_inicio",
               "vigencia_fim", "unidades_na_vigencia", "propulsao_oferecida", "pbe_propulsao",
               "pbe_anos", "pbe_diferenca", "pbe_nota", "origem_producao", "confianca_origem",
               "origem_confronto", "origem_data_fonte", "origem_fonte_url", "observacao",
               "decisao_humana"]
    return marcadas.sort_values("unidades_na_vigencia", ascending=False)[colunas]


def resumo_validacao(rascunho: pd.DataFrame, volume_painel: int, top: int) -> pd.DataFrame:
    blocos = []
    total = rascunho["unidades_na_vigencia"].sum()
    for situacao in ("concorda", "diverge", "ausente"):
        parte = rascunho[rascunho["pbe_situacao"] == situacao]
        blocos.append({"quadro": "propulsao contra o PBE", "nivel": situacao,
                       "modelo_vigencias": len(parte),
                       "modelos": parte[CHAVE].drop_duplicates().shape[0],
                       "unidades": int(parte["unidades_na_vigencia"].sum()),
                       "pct_do_classificado": round(100 * parte["unidades_na_vigencia"].sum()
                                                    / total, 2)})
    casos = rascunho[casos_de_origem(rascunho, top)]
    for nivel, parte in [
        ("casos de origem (troca sem data, ou media/baixa entre os maiores)", casos),
        ("... com fonte datada", casos[casos["origem_situacao"] == "com_fonte_datada"]),
        ("... fonte confirma", casos[casos["origem_confronto"] == "confirma"]),
        ("... fonte complementa", casos[casos["origem_confronto"] == "complementa"]),
        ("... fonte ajusta a data", casos[casos["origem_confronto"] == "ajusta_data"]),
        ("... fonte contradiz", casos[casos["origem_confronto"] == "contradiz"]),
        ("... fonte inconclusiva", casos[casos["origem_confronto"] == "inconclusivo"]),
        ("... sem fonte", casos[casos["origem_situacao"] == "sem_fonte"]),
    ]:
        blocos.append({"quadro": "origem contra fonte datada", "nivel": nivel,
                       "modelo_vigencias": len(parte),
                       "modelos": parte[CHAVE].drop_duplicates().shape[0],
                       "unidades": int(parte["unidades_na_vigencia"].sum()),
                       "pct_do_classificado": round(100 * parte["unidades_na_vigencia"].sum()
                                                    / total, 2)})
    return pd.DataFrame(blocos)
