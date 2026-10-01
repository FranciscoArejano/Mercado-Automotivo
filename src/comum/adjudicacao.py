"""Regras de adjudicacao aplicadas ao rascunho de classificacao.

O pesquisador aprova regras (`config/regras_adjudicacao.csv`); este modulo as
aplica; o que elas nao decidem fica para decisao humana. Nada e' sobrescrito: a
proposta fica intacta e o que a regra decidiu vai em `decisao_por_regra`, na
sintaxe de `decisao_humana`. Cada decisao vai para a aba `resolvido_por_regra`
com o id da regra e o valor antes e depois. Nada some.

Propulsao, contra o PBE (so' nas linhas que divergem dele, ou que estao ausentes
dele entre os maiores modelos):

- **P1** -- tipo que o PBE mostra e a proposta nao tem entra no conjunto. O
  `Hibrido` do PBE so' entra como `hev` quando o nome da versao diz HEV: o PBE
  rotula hibrido leve como Hibrido (Stonic MHEV, Forester MHEV, Sportage TMHEV
  estao la' com o nome dizendo), entao sem o nome o rotulo nao escolhe entre
  `hev` e `mhev`, e a linha vai para decisao humana. Tres artefatos conhecidos do
  PBE tambem vao para decisao humana em vez de entrar: tipo que so' aparece num
  ano dividido entre duas vigencias do modelo (cada ano vai para a vigencia com
  mais meses nele -- o Compass de 2016 e' das duas geracoes); combustao que so'
  aparece nas tabelas sem coluna de propulsao (ate' 2020), quando a proposta tem
  eletrificado (o Prius sem HYBRID no nome sai como gasolina); e combustao de
  versao cujo nome diz HYBRID (RAV4 S HYBRID esta' em Combustao em 2026).
- **P2** -- tipo que a proposta tem e o PBE nao mostra fica se e' anterior ao
  primeiro ano do modelo no PBE. A proposta nao data cada tipo; a regra usa
  a vigencia: inteira antes do primeiro ano (ou antes de 2009, quando o PBE
  nao existia) mantem tudo; com pelo menos `MESES_ANTES_P2` meses antes do
  primeiro ano mantem os tipos de combustao, com ressalva (condicao necessaria,
  nao prova). Tipo eletrificado ausente do PBE vai sempre para decisao humana.
- **P3** -- `Hibrido` do PBE contra `mhev` da proposta: fica `mhev` se o nome da
  versao declara hibrido leve (o mapeamento ja' faz isso, e essas linhas nem
  divergem); senao, decisao humana.

Origem, contra fontes datadas (nas linhas que a rodada de validacao mandou
buscar fonte, e nas que tem fonte que contradiz ou ajusta a data):

- **O1** -- leitura `confirma` ou `complementa` apoiada em fonte forte
  (`tipo_fonte.FORTES`): aceita. `complementa` so' quando a fonte cobre a
  vigencia inteira.
- **O2** -- leitura `ajusta_data` apoiada em fonte forte: a fronteira da
  vigencia vai para o mes da fonte. Exige mes e evento efetivo (inicio, fim ou
  periodo de producao local); plano ou anuncio nao basta.
- **O3** -- `contradiz` e `inconclusivo` vao sempre para decisao humana; leitura
  apoiada so' em fonte fraca tambem.

A leitura de uma linha e' a pior entre as fontes do modelo (`ORDEM_CONFRONTO`).

Montagem local (`montagem_local`): `desconhecido` por padrao; so' muda onde
`dados/referencia/montagem_fontes.csv` traz uma fonte, com trecho copiado, que
declara o modo para um periodo que toca a vigencia, e a linha nao e'
`importado` (montagem no exterior, como a dos furgoes do Uruguai, nao e' local).
`montagem_cobertura` diz se a fonte cobre a vigencia inteira ou so' parte dela.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from . import classificacao, config, tipo_fonte
from .validacao_classificacao import (CHAVE, ORDEM_CONFRONTO, PRIMEIRO_ANO_PBE,
                                      ULTIMO_ANO_SEM_COLUNA, _meses_no_ano, casos_de_origem)

COMBUSTAO = frozenset({"gasolina", "flex", "diesel"})
ELETRIFICADAS = frozenset({"mhev", "hev", "phev", "reev", "bev"})
# Marcador de nome que desmente uma linha de Combustao (RAV4 S HYBRID em 2026).
MARCADOR_ELETRIFICADO = frozenset({"MHEV", "HEV", "PHEV", "BEV", "REEV", "EV", "HYBRID",
                                   "HIBRIDO", "PLUG-IN", "PLUGIN", "E-HYBRID", "ELECTRIC",
                                   "ELETRICO", "E-TRON"})
MESES_ANTES_P2 = 12
EVENTOS_EFETIVOS = frozenset({"inicio_producao_local", "fim_producao_local",
                              "producao_local_periodo"})
MES = re.compile(r"^\d{4}-\d{2}$")
LOCAL = frozenset({"nacional", "ambos"})
MODOS_MONTAGEM = ("fabricacao", "ckd", "skd", "desconhecido")


def carregar_regras() -> pd.DataFrame:
    return pd.read_csv(config.REGRAS_ADJUDICACAO, dtype=str, keep_default_na=False)


def carregar_fontes(mapa: dict[str, str] | None = None) -> pd.DataFrame:
    """Fontes de origem com `tipo_fonte` recalculado pelo mapa dado.

    O mapa padrao e' o de `config/tipo_fonte_dominio.csv`; outro mapa serve ao
    teste de sensibilidade.
    """
    fontes = pd.read_csv(config.ORIGEM_FONTES, dtype=str, keep_default_na=False)
    return tipo_fonte.com_tipo(fontes, mapa if mapa is not None else tipo_fonte.carregar_mapa())


# ------------------------------------------------------------- utilitarios


def _mes(texto: str) -> int:
    return int(texto[:4]) * 12 + int(texto[5:7]) - 1


def _texto_mes(n: int) -> str:
    return f"{n // 12}-{n % 12 + 1:02d}"


def _anos(texto: str) -> list[int]:
    anos: list[int] = []
    for parte in filter(None, texto.split(", ")):
        inicio, _, fim = parte.partition("-")
        anos += range(int(inicio), int(fim or inicio) + 1)
    return anos


def _diferenca(texto: str) -> tuple[set[str], set[str]]:
    """(so' no PBE, so' na proposta) a partir de `pbe_diferenca`."""
    so_pbe: set[str] = set()
    so_proposta: set[str] = set()
    for parte in filter(None, texto.split("; ")):
        rotulo, _, tipos = parte.partition(": ")
        if rotulo == "so' no PBE":
            so_pbe = set(tipos.split("+"))
        elif rotulo == "so' na proposta":
            so_proposta = set(tipos.split("+"))
    return so_pbe, so_proposta


def _ordenados(tipos) -> list[str]:
    return [p for p in classificacao.PROPULSOES if p in set(tipos)]


def _exemplos(nomes, n: int = 3) -> str:
    nomes = list(dict.fromkeys(nomes))
    return ", ".join(nomes[:n]) + (f" e mais {len(nomes) - n}" if len(nomes) > n else "")


@dataclass
class Resultado:
    """O que as regras fizeram com um atributo de uma linha."""
    resolucoes: list[dict] = field(default_factory=list)  # (regra, antes, depois, base, ressalva)
    pendencias: list[str] = field(default_factory=list)   # motivos para decisao humana
    decisao: str = ""                                     # `atributo=valor`, se decidido inteiro
    valor_apos_regras: str = ""


# ---------------------------------------------------------------- propulsao


def _versoes(casado_chave: pd.DataFrame | None, anos: list[int], valor: str) -> pd.DataFrame:
    if casado_chave is None:
        return pd.DataFrame(columns=["ano_pbe", "modelo_versao", "marcador_nome"])
    return casado_chave[casado_chave["ano_pbe"].astype(int).isin(anos)
                        & (casado_chave["valor_taxonomia"] == valor)]


def _anos_divididos(linha: pd.Series, linhas_modelo: pd.DataFrame, anos: list[int]) -> set[int]:
    """Anos do PBE desta vigencia que ela divide com outra vigencia do mesmo modelo."""
    outras = linhas_modelo[linhas_modelo["vigencia_inicio"] != linha["vigencia_inicio"]]
    return {ano for ano in anos
            if _meses_no_ano(linha["vigencia_inicio"], linha["vigencia_fim"], ano) < 12
            and any(_meses_no_ano(i, f, ano) for i, f in
                    zip(outras["vigencia_inicio"], outras["vigencia_fim"]))}


def _guarda_p1(tipo: str, versoes: pd.DataFrame, divididos: set[int],
               proposta: set[str]) -> str:
    """Motivo para P1 nao decidir este tipo, ou vazio se a evidencia serve."""
    if tipo in COMBUSTAO:
        desmentidas = versoes["marcador_nome"].str.split("+").apply(
            lambda m: bool(set(m) & MARCADOR_ELETRIFICADO))
        if len(versoes) and desmentidas.all():
            return (f"o PBE poe {tipo} em versao cujo nome diz hibrido "
                    f"({_exemplos(versoes['modelo_versao'])})")
        versoes = versoes[~desmentidas]
    anos = set(versoes["ano_pbe"].astype(int))
    if anos and anos <= divididos:
        return (f"{tipo} so' aparece em {', '.join(map(str, sorted(anos)))}, ano dividido com "
                f"outra vigencia do modelo ({_exemplos(versoes['modelo_versao'])})")
    if (tipo in COMBUSTAO and anos and max(anos) <= ULTIMO_ANO_SEM_COLUNA
            and proposta & ELETRIFICADAS):
        return (f"{tipo} so' aparece nas tabelas sem coluna de propulsao (ate' "
                f"{ULTIMO_ANO_SEM_COLUNA}), onde hibrido sem HYBRID no nome sai como combustao "
                f"({_exemplos(versoes['modelo_versao'])})")
    return ""


def propulsao(linha: pd.Series, casado_chave: pd.DataFrame | None, primeiro_ano: int | None,
              linhas_modelo: pd.DataFrame, p1_literal: bool = False) -> Resultado:
    """P1, P2 e P3 numa linha que diverge do PBE ou esta' ausente dele.

    `p1_literal` aplica P1 tambem ao Hibrido sem HEV no nome (contrafactual
    para o log; o padrao e' mandar para decisao humana).
    """
    if linha["pbe_situacao"] == "ausente":
        return _ausente(linha, primeiro_ano)
    proposta = {p for p in linha["propulsao_oferecida"].split("+") if p}
    texto_proposta = linha["propulsao_oferecida"] or "(vazia)"
    so_pbe, so_proposta = _diferenca(linha["pbe_diferenca"])
    anos = _anos(linha["pbe_anos"])
    divididos = _anos_divididos(linha, linhas_modelo, anos)
    r = Resultado()
    acrescentados: list[tuple[str, str]] = []

    for tipo in _ordenados(so_pbe):
        versoes = _versoes(casado_chave, anos, tipo)
        nomes = _exemplos(versoes["modelo_versao"])
        if tipo == "hev" and "mhev" in proposta:
            r.pendencias.append(
                f"P3 nao decide: o PBE diz Hibrido sem declarar hibrido leve no nome ({nomes}); "
                "a proposta diz mhev")
            continue
        if tipo == "hev" and not p1_literal:
            sem_hev = versoes[~versoes["marcador_nome"].str.split("+").apply(
                lambda m: "HEV" in m)]
            if len(versoes) == 0 or len(sem_hev):
                r.pendencias.append(
                    "P1 nao decide: o Hibrido do PBE sem HEV no nome pode ser hibrido leve "
                    f"({_exemplos(sem_hev['modelo_versao'])}); hev ou mhev?")
                continue
        guarda = _guarda_p1(tipo, versoes, divididos, proposta)
        if guarda:
            r.pendencias.append(f"P1 nao decide: {guarda}")
            continue
        acrescentados.append((tipo, nomes))

    if acrescentados:
        novo = _ordenados(proposta | {t for t, _ in acrescentados})
        ressalvas = []
        if not proposta:
            ressalvas.append("proposta vazia: o conjunto vem so' do PBE")
        if any(t == "hev" for t, _ in acrescentados) and p1_literal:
            ressalvas.append("hev de Hibrido sem HEV no nome (leitura literal)")
        r.resolucoes.append({
            "regra": "P1", "antes": texto_proposta, "depois": "+".join(novo),
            "base": "; ".join(f"{t}: PBE {linha['pbe_anos']} ({n})" for t, n in acrescentados),
            "ressalva": "; ".join(ressalvas)})
        proposta = set(novo)

    meses_antes = 0
    if primeiro_ano is not None:
        meses_antes = max(0, min(_mes(f"{primeiro_ano}-01"), _mes(linha["vigencia_fim"]) + 1)
                          - _mes(linha["vigencia_inicio"]))
    mantidos = []
    for tipo in _ordenados(so_proposta):
        if tipo == "mhev" and "hev" in so_pbe:
            continue  # ja' anotado em P3
        if tipo in COMBUSTAO and meses_antes >= MESES_ANTES_P2:
            mantidos.append(tipo)
        elif tipo in COMBUSTAO:
            r.pendencias.append(
                f"P2 nao decide: {tipo} so' na proposta; a vigencia tem {meses_antes} meses antes "
                f"de {primeiro_ano}, primeiro ano do modelo no PBE (minimo {MESES_ANTES_P2})")
        else:
            r.pendencias.append(
                f"P2 nao decide: {tipo} so' na proposta; tipo eletrificado ausente do PBE vai "
                "para decisao humana")
    if mantidos:
        r.resolucoes.append({
            "regra": "P2", "antes": "+".join(_ordenados(proposta)),
            "depois": "+".join(_ordenados(proposta)),
            "base": f"mantem {'+'.join(mantidos)}: a vigencia tem {meses_antes} meses antes de "
                    f"{primeiro_ano}, primeiro ano do modelo no PBE",
            "ressalva": "condicao necessaria, nao prova: a proposta nao data o tipo; conferir"})

    r.valor_apos_regras = "+".join(_ordenados(proposta))
    if not r.pendencias:
        r.decisao = _decisao_propulsao(r.valor_apos_regras)
    return r


def _ausente(linha: pd.Series, primeiro_ano: int | None) -> Resultado:
    r = Resultado(valor_apos_regras=linha["propulsao_oferecida"])
    proposta = linha["propulsao_oferecida"]
    if not proposta:
        r.pendencias.append("propulsao sem proposta e modelo ausente do PBE nesta vigencia")
        return r
    ressalva = ""
    if linha["vigencia_fim"] < f"{PRIMEIRO_ANO_PBE}-01":
        base = f"vigencia inteira anterior ao PBE ({PRIMEIRO_ANO_PBE})"
    elif primeiro_ano is not None and linha["vigencia_fim"] < f"{primeiro_ano}-01":
        base = f"vigencia inteira anterior a {primeiro_ano}, primeiro ano do modelo no PBE"
        ressalva = (f"o PBE ja' existia em parte da vigencia (desde {PRIMEIRO_ANO_PBE}) e nao "
                    "listou o modelo: P2 mantem pelo texto da regra, mas a razao dela (o PBE nao "
                    "tinha como registrar) nao vale aqui")
    else:
        if primeiro_ano is None:
            detalhe = "o modelo nao aparece no PBE em ano nenhum"
        else:
            detalhe = f"o modelo aparece no PBE desde {primeiro_ano}, mas nao nos anos desta vigencia"
        if linha.get("pbe_nota"):
            detalhe += f" ({linha['pbe_nota']})"
        r.pendencias.append(f"ausente no PBE: {detalhe}")
        return r
    r.resolucoes.append({"regra": "P2", "antes": proposta, "depois": proposta,
                         "base": f"mantem tudo: {base}", "ressalva": ressalva})
    r.decisao = _decisao_propulsao(proposta)
    return r


def _decisao_propulsao(valor: str) -> str:
    return f"propulsao_oferecida={valor}; eletrificacao={classificacao.eletrificacao(valor)}"


# ------------------------------------------------------------------- origem


def _descrever(fontes: pd.DataFrame) -> str:
    return ", ".join(f"{t or 'sem tipo'} ({tipo_fonte.dominio(u)})"
                     for t, u in dict.fromkeys(zip(fontes["tipo_fonte"],
                                                   fontes["origem_fonte_url"])))


def _periodo_fonte(evento: str, data: str) -> tuple[int | None, int | None]:
    """(primeiro mes, ultimo mes) de producao local -- ou de importacao -- que a fonte cobre."""
    inicio, _, fim = data.partition("/")

    def limite(texto: str, primeiro: bool) -> int | None:
        if MES.match(texto):
            return _mes(texto)
        if re.fullmatch(r"\d{4}", texto):
            return _mes(f"{texto}-01") if primeiro else _mes(f"{texto}-12")
        return None

    if evento == "inicio_producao_local":
        return limite(inicio, True), None
    if evento in ("producao_local_periodo", "importacao_confirmada", "producao_argentina_periodo"):
        return limite(inicio, True), limite(fim or inicio, False)
    if evento == "producao_local_confirmada":
        return limite(inicio, True), limite(inicio, False)
    return None, None


def _valor_indicado(fonte: pd.Series) -> str:
    if fonte["evento"] in ("inicio_producao_local", "producao_local_periodo",
                           "producao_local_confirmada"):
        return "nacional"
    if fonte["evento"] == "importacao_confirmada":
        return "importado"
    return ""


def _fronteiras(linhas_modelo: pd.DataFrame, evento: str, data: str) -> dict[int, tuple] | None:
    """Mudancas de vigencia que a data da fonte pede: {indice: (atributo, antes, depois)}.

    Inicio da producao local em M: a vigencia nao local que precede a primeira
    local termina em M-1, e a local comeca em M. Fim em M: a local termina em M e a
    seguinte comeca em M+1. None quando o modelo nao tem a fronteira esperada.
    """
    ordenadas = linhas_modelo.sort_values("vigencia_inicio")
    pares = list(zip(ordenadas.index[:-1], ordenadas.index[1:]))
    local = ordenadas["origem_producao"].isin(LOCAL)
    inicio, _, fim = data.partition("/")
    pedidos = []
    if evento == "inicio_producao_local":
        pedidos.append(("entra", inicio))
    elif evento == "fim_producao_local":
        pedidos.append(("sai", inicio))
    elif evento == "producao_local_periodo":
        pedidos += [("entra", inicio), ("sai", fim)]
    mudancas: dict[int, tuple] = {}
    for sentido, mes in pedidos:
        if sentido == "entra":
            par = next(((a, b) for a, b in pares if not local[a] and local[b]), None)
        else:
            par = next(((a, b) for a, b in pares if local[a] and not local[b]), None)
        if par is None:
            if sentido == "entra" and ordenadas.iloc[0]["vigencia_inicio"] >= mes and local.iloc[0]:
                continue  # a producao local ja' comeca com o modelo
            return None
        a, b = par
        m = _mes(mes)
        novo_fim, novo_inicio = (m - 1, m) if sentido == "entra" else (m, m + 1)
        if _texto_mes(novo_fim) != ordenadas.at[a, "vigencia_fim"]:
            mudancas[a] = ("vigencia_fim", ordenadas.at[a, "vigencia_fim"], _texto_mes(novo_fim))
        if _texto_mes(novo_inicio) != ordenadas.at[b, "vigencia_inicio"]:
            mudancas[b] = ("vigencia_inicio", ordenadas.at[b, "vigencia_inicio"],
                           _texto_mes(novo_inicio))
    return mudancas


def origem(linha: pd.Series, indice: int, fontes_chave: pd.DataFrame | None, caso: bool,
           linhas_modelo: pd.DataFrame) -> Resultado | None:
    """O1, O2 e O3 numa linha. None quando a linha esta' fora do universo de origem."""
    valor = linha["origem_producao"]
    if fontes_chave is None or fontes_chave.empty:
        if not caso:
            return None
        return Resultado(pendencias=["origem sem fonte"], valor_apos_regras=valor)
    leitura = min(fontes_chave["confronto_com_proposta"], key=ORDEM_CONFRONTO.index)
    if not caso and leitura not in ("contradiz", "ajusta_data"):
        return None
    r = Resultado(valor_apos_regras=valor)
    de_leitura = fontes_chave[fontes_chave["confronto_com_proposta"] == leitura]
    fortes = de_leitura[de_leitura["tipo_fonte"].isin(tipo_fonte.FORTES)]

    if leitura in ("contradiz", "inconclusivo"):
        nota = "" if len(fortes) else " -- fonte unica e fraca" if len(de_leitura) == 1 else \
            " -- so' fonte fraca"
        r.pendencias.append(f"O3: fonte de origem {leitura.replace('_', ' ')} "
                            f"({_descrever(de_leitura)}){nota}")
        return r
    if fortes.empty:
        r.pendencias.append(f"O3: leitura '{leitura.replace('_', ' ')}' apoiada so' em fonte "
                            f"fraca ({_descrever(de_leitura)})")
        return r

    if leitura == "ajusta_data":
        utilizaveis = [f for _, f in fortes.iterrows() if f["evento"] in EVENTOS_EFETIVOS
                       and all(MES.match(p) for p in f["origem_data_fonte"].split("/"))]
        if not utilizaveis:
            motivo = ("plano ou anuncio, nao evento efetivo"
                      if not fortes["evento"].isin(EVENTOS_EFETIVOS).any()
                      else "data sem mes")
            r.pendencias.append(f"O2 nao decide: {motivo} ({_descrever(fortes)}, "
                                f"{'; '.join(fortes['origem_data_fonte'].replace('', 'sem data'))})")
            return r
        fonte = utilizaveis[0]
        mudancas = _fronteiras(linhas_modelo, fonte["evento"], fonte["origem_data_fonte"])
        if mudancas is None:
            r.pendencias.append("O2 nao decide: a data da fonte nao corresponde a uma fronteira "
                                "de origem nas vigencias propostas")
            return r
        base = (f"{fonte['evento']} {fonte['origem_data_fonte']} "
                f"({fonte['tipo_fonte']}, {tipo_fonte.dominio(fonte['origem_fonte_url'])})")
        if indice in mudancas:
            atributo, antes, depois = mudancas[indice]
            r.resolucoes.append({"regra": "O2", "antes": f"{atributo}={antes}",
                                 "depois": f"{atributo}={depois}", "base": base, "ressalva": ""})
            r.decisao = f"{atributo}={depois}"
        else:
            r.resolucoes.append({"regra": "O2", "antes": f"origem_producao={valor}",
                                 "depois": f"origem_producao={valor}",
                                 "base": base + "; a fronteira ajustada nao toca esta vigencia",
                                 "ressalva": ""})
            r.decisao = f"origem_producao={valor}"
        return r

    base = _descrever(fortes)
    if leitura == "confirma":
        if not valor:
            r.pendencias.append("O1 nao decide: a fonte confirma, mas a proposta nao tem origem")
            return r
        r.resolucoes.append({"regra": "O1", "antes": f"origem_producao={valor}",
                             "depois": f"origem_producao={valor}", "base": f"confirma: {base}",
                             "ressalva": ""})
        r.decisao = f"origem_producao={valor}"
        return r

    # complementa: so' quando a fonte forte cobre a vigencia inteira
    v_inicio, v_fim = _mes(linha["vigencia_inicio"]), _mes(linha["vigencia_fim"])
    for _, fonte in fortes.iterrows():
        indicado = _valor_indicado(fonte)
        p_inicio, p_fim = _periodo_fonte(fonte["evento"], fonte["origem_data_fonte"])
        if not indicado or p_inicio is None or p_inicio > v_inicio:
            continue
        if p_fim is not None and p_fim < v_fim:
            continue
        if valor and valor != indicado:
            continue
        r.resolucoes.append({"regra": "O1", "antes": f"origem_producao={valor or '(vazia)'}",
                             "depois": f"origem_producao={indicado}",
                             "base": f"complementa: {fonte['evento']} "
                                     f"{fonte['origem_data_fonte']} ({base})",
                             "ressalva": ""})
        r.decisao = f"origem_producao={indicado}"
        r.valor_apos_regras = indicado
        return r
    r.pendencias.append(f"O1 nao decide: a fonte forte complementa ({base}), mas nao cobre a "
                        f"vigencia inteira ({linha['vigencia_inicio']} a {linha['vigencia_fim']})")
    return r


# ---------------------------------------------------------------- aplicacao


def aplicar(rascunho: pd.DataFrame, casado: pd.DataFrame, fontes: pd.DataFrame, top: int,
            p1_literal: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(rascunho com colunas de regra, resolvido_por_regra).

    Colunas novas no rascunho: `regras_aplicadas`, `pendencias`,
    `propulsao_apos_regras`, `origem_apos_regras`, `origem_tipos_fonte` e
    `decisao_por_regra`.
    """
    saida = rascunho.copy()
    no_pbe = casado[casado["marca"] != ""]
    por_chave = {k: g for k, g in no_pbe.groupby(CHAVE)}
    primeiro = {k: int(g["ano_pbe"].astype(int).min()) for k, g in por_chave.items()}
    fontes_por_chave = {k: g for k, g in fontes.groupby(CHAVE)} if not fontes.empty else {}
    modelos = {k: g for k, g in saida.groupby(CHAVE, sort=False)}
    casos = casos_de_origem(saida, top)

    resolvidos, colunas = [], {c: {} for c in ("regras_aplicadas", "pendencias",
                                                "propulsao_apos_regras", "origem_apos_regras",
                                                "origem_tipos_fonte", "decisao_por_regra")}
    for indice, linha in saida.iterrows():
        chave = tuple(linha[CHAVE])
        resultados: list[tuple[str, Resultado]] = []
        if linha["pbe_situacao"] == "diverge" or (linha["pbe_situacao"] == "ausente"
                                                  and linha["posicao"] <= top):
            resultados.append(("propulsao_oferecida", propulsao(
                linha, por_chave.get(chave), primeiro.get(chave), modelos[chave], p1_literal)))
        fontes_chave = fontes_por_chave.get(chave)
        r_origem = origem(linha, indice, fontes_chave, bool(casos[indice]), modelos[chave])
        if r_origem is not None:
            resultados.append(("origem_producao", r_origem))

        pendencias = [p for _, r in resultados for p in r.pendencias]
        for atributo, r in resultados:
            for res in r.resolucoes:
                resolvidos.append({
                    "regra": res["regra"], "atributo": atributo,
                    "situacao_da_linha": "resolvida" if not pendencias else "parcial",
                    **{c: linha[c] for c in ("posicao", "marca", "modelo", "segmento",
                                             "vigencia_inicio", "vigencia_fim",
                                             "unidades_na_vigencia")},
                    "antes": res["antes"], "depois": res["depois"], "base": res["base"],
                    "ressalva": res["ressalva"]})
        colunas["regras_aplicadas"][indice] = "+".join(dict.fromkeys(
            res["regra"] for _, r in resultados for res in r.resolucoes))
        colunas["pendencias"][indice] = " | ".join(pendencias)
        colunas["propulsao_apos_regras"][indice] = next(
            (r.valor_apos_regras for a, r in resultados if a == "propulsao_oferecida"),
            linha["propulsao_oferecida"])
        colunas["origem_apos_regras"][indice] = next(
            (r.valor_apos_regras for a, r in resultados if a == "origem_producao"),
            linha["origem_producao"])
        colunas["origem_tipos_fonte"][indice] = "" if fontes_chave is None else \
            "+".join(t for t in tipo_fonte.TIPOS if t in set(fontes_chave["tipo_fonte"]))
        colunas["decisao_por_regra"][indice] = "; ".join(r.decisao for _, r in resultados
                                                         if r.decisao)
    for nome, valores in colunas.items():
        saida[nome] = pd.Series(valores)
    resolvido = pd.DataFrame(resolvidos, columns=[
        "regra", "atributo", "situacao_da_linha", "posicao", "marca", "modelo", "segmento",
        "vigencia_inicio", "vigencia_fim", "unidades_na_vigencia", "antes", "depois", "base",
        "ressalva"])
    return saida, resolvido


def a_adjudicar(com_regras: pd.DataFrame, fila_antes: pd.DataFrame) -> pd.DataFrame:
    """So' o que as regras nao decidem, maior volume primeiro."""
    antes = set(map(tuple, fila_antes[CHAVE + ["vigencia_inicio"]].to_numpy()))
    fila = com_regras[com_regras["pendencias"] != ""].copy()
    fila["na_fila_antes"] = ["sim" if tuple(k) in antes else "nao, entrou nesta rodada"
                             for k in fila[CHAVE + ["vigencia_inicio"]].to_numpy()]
    fila = fila.rename(columns={"pendencias": "motivo"})
    colunas = ["motivo", "na_fila_antes", "regras_aplicadas", "posicao", "marca", "modelo",
               "segmento", "vigencia_inicio", "vigencia_fim", "unidades_na_vigencia",
               "propulsao_oferecida", "propulsao_apos_regras", "pbe_propulsao", "pbe_anos",
               "pbe_diferenca", "pbe_nota", "origem_producao", "origem_apos_regras",
               "confianca_origem", "origem_confronto", "origem_tipos_fonte", "origem_data_fonte",
               "origem_fonte_url", "montagem_local", "observacao", "decisao_por_regra",
               "decisao_humana"]
    return fila.sort_values("unidades_na_vigencia", ascending=False, kind="stable")[colunas]


def contas(fila_antes: pd.DataFrame, com_regras: pd.DataFrame, resolvido: pd.DataFrame
           ) -> pd.DataFrame:
    """A conta da rodada: quantas linhas sairam da fila, por regra, e quantas ficaram."""
    chave = CHAVE + ["vigencia_inicio"]
    antes = set(map(tuple, fila_antes[chave].to_numpy()))
    depois = set(map(tuple, com_regras.loc[com_regras["pendencias"] != "", chave].to_numpy()))
    saiu = antes - depois
    regras_da_linha = {tuple(k): r for k, r in zip(com_regras[chave].to_numpy(),
                                                   com_regras["regras_aplicadas"])}
    unidades = {tuple(k): u for k, u in zip(com_regras[chave].to_numpy(),
                                            com_regras["unidades_na_vigencia"])}
    linhas = [{"conta": "na fila antes das regras", "linhas": len(antes),
               "unidades": int(sum(unidades[k] for k in antes))}]
    por_combinacao: dict[str, list] = {}
    for k in saiu:
        por_combinacao.setdefault(regras_da_linha[k] or "(nenhuma)", []).append(k)
    for regras, ks in sorted(por_combinacao.items(), key=lambda par: -len(par[1])):
        linhas.append({"conta": f"saiu da fila por {regras}", "linhas": len(ks),
                       "unidades": int(sum(unidades[k] for k in ks))})
    ficou = antes & depois
    entrou = depois - antes
    linhas += [
        {"conta": "saiu da fila (total)", "linhas": len(saiu),
         "unidades": int(sum(unidades[k] for k in saiu))},
        {"conta": "ficou na fila", "linhas": len(ficou),
         "unidades": int(sum(unidades[k] for k in ficou))},
        {"conta": "... com parte resolvida por regra", "linhas": sum(
            1 for k in ficou if regras_da_linha[k]),
         "unidades": int(sum(unidades[k] for k in ficou if regras_da_linha[k]))},
        {"conta": "entrou na fila nesta rodada", "linhas": len(entrou),
         "unidades": int(sum(unidades[k] for k in entrou))},
        {"conta": "na fila depois das regras", "linhas": len(depois),
         "unidades": int(sum(unidades[k] for k in depois))},
    ]
    for regra in ("P1", "P2", "P3", "O1", "O2"):
        parte = resolvido[resolvido["regra"] == regra]
        linhas.append({"conta": f"decisoes da regra {regra} (linhas, inclusive parciais)",
                       "linhas": len(parte), "unidades": int(parte["unidades_na_vigencia"].sum())})
    return pd.DataFrame(linhas)


# ------------------------------------------------------------ montagem local


def carregar_montagem() -> pd.DataFrame:
    if not config.MONTAGEM_FONTES.exists():
        return pd.DataFrame(columns=CHAVE + ["montagem_local", "onde", "periodo_inicio",
                                             "periodo_fim", "fonte_url"])
    return pd.read_csv(config.MONTAGEM_FONTES, dtype=str, keep_default_na=False)


def _periodo_montagem(inicio: str, fim: str) -> tuple[int, int]:
    """Meses que a fonte de montagem cobre. Ano sozinho vale o ano; fim vazio, so' o inicio."""
    primeiro = _mes(inicio) if MES.match(inicio) else _mes(f"{inicio}-01")
    if fim:
        ultimo = _mes(fim) if MES.match(fim) else _mes(f"{fim}-12")
    else:
        ultimo = primeiro if MES.match(inicio) else _mes(f"{inicio}-12")
    return primeiro, ultimo


def anexar_montagem(rascunho: pd.DataFrame, montagem: pd.DataFrame
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(rascunho com `montagem_local` e `montagem_cobertura`, casos com fonte)."""
    saida = rascunho.copy()
    saida["montagem_local"] = "desconhecido"
    saida["montagem_cobertura"] = ""
    saida["montagem_fonte_url"] = ""
    casos = []
    for _, fonte in montagem.iterrows():
        chave = tuple(fonte[CHAVE])
        linhas = saida[(saida["marca"] == chave[0]) & (saida["modelo"] == chave[1])
                       & (saida["segmento"] == chave[2])]
        p_inicio, p_fim = _periodo_montagem(fonte["periodo_inicio"], fonte["periodo_fim"])
        periodo = f"{_texto_mes(p_inicio)} a {_texto_mes(p_fim)}"
        base = {"marca": chave[0], "modelo": chave[1], "segmento": chave[2],
                "modo_na_fonte": fonte["montagem_local"], "onde": fonte["onde"],
                "periodo_da_fonte": periodo, "tipo_fonte": fonte.get("tipo_fonte", ""),
                "fonte_url": fonte["fonte_url"], "fonte_trecho": fonte["fonte_trecho"],
                "observacao": fonte["observacao"]}
        if fonte["onde"] != "brasil":
            casos.append({**base, "vigencia": "", "origem_producao": "",
                          "montagem_local": "", "aplicado": "nao: montagem no exterior; para o "
                          "Brasil o modelo e' importado inteiro"})
            continue
        tocadas = 0
        for indice, linha in linhas.iterrows():
            v_inicio, v_fim = _mes(linha["vigencia_inicio"]), _mes(linha["vigencia_fim"])
            if p_fim < v_inicio or p_inicio > v_fim:
                continue
            tocadas += 1
            origem_linha = linha.get("origem_apos_regras", linha["origem_producao"])
            if origem_linha == "importado":
                casos.append({**base, "vigencia": f"{linha['vigencia_inicio']} a "
                                                  f"{linha['vigencia_fim']}",
                              "origem_producao": origem_linha, "montagem_local": "desconhecido",
                              "aplicado": "nao: a linha e' importado; o modo so' vale para a "
                                          "parte de producao local"})
                continue
            inteira = p_inicio <= v_inicio and p_fim >= v_fim
            cobertura = "vigencia inteira" if inteira else (
                f"parcial: a fonte cobre {periodo}; vigencia {linha['vigencia_inicio']} a "
                f"{linha['vigencia_fim']}")
            atual = saida.at[indice, "montagem_local"]
            if atual not in ("desconhecido", fonte["montagem_local"]):
                saida.at[indice, "montagem_local"] = "desconhecido"
                cobertura = f"fontes divergem ({atual} e {fonte['montagem_local']})"
            else:
                saida.at[indice, "montagem_local"] = fonte["montagem_local"]
            saida.at[indice, "montagem_cobertura"] = cobertura
            saida.at[indice, "montagem_fonte_url"] = fonte["fonte_url"]
            casos.append({**base, "vigencia": f"{linha['vigencia_inicio']} a "
                                              f"{linha['vigencia_fim']}",
                          "origem_producao": linha["origem_producao"],
                          "montagem_local": saida.at[indice, "montagem_local"],
                          "aplicado": cobertura})
        if not tocadas:
            casos.append({**base, "vigencia": "", "origem_producao": "", "montagem_local": "",
                          "aplicado": "nao: o periodo da fonte nao toca vigencia nenhuma"})
    return saida, pd.DataFrame(casos)


def resumo_montagem(com_montagem: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    total = com_montagem["unidades_na_vigencia"].sum()
    for rotulo, filtro in [
        ("todas as linhas", slice(None)),
        ("origem nacional ou ambos", com_montagem["origem_producao"].isin(LOCAL)),
        ("origem importado", com_montagem["origem_producao"] == "importado"),
        ("origem sem proposta", com_montagem["origem_producao"] == ""),
    ]:
        parte = com_montagem[filtro] if not isinstance(filtro, slice) else com_montagem
        for modo in MODOS_MONTAGEM:
            sub = parte[parte["montagem_local"] == modo]
            linhas.append({"recorte": rotulo, "montagem_local": modo,
                           "modelo_vigencias": len(sub),
                           "unidades": int(sub["unidades_na_vigencia"].sum()),
                           "pct_do_classificado": round(100 * sub["unidades_na_vigencia"].sum()
                                                        / total, 2)})
    return pd.DataFrame(linhas)
