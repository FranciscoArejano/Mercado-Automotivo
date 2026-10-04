"""Regras de adjudicacao aplicadas ao rascunho de classificacao.

O pesquisador aprova regras (`config/regras_adjudicacao.csv`); este modulo as
aplica; o que elas nao decidem fica para decisao humana. Nada e' sobrescrito: a
proposta fica intacta e o que a regra decidiu vai em `decisao_por_regra`, na
sintaxe de `decisao_humana`. Cada decisao vai para a aba `resolvido_por_regra`
com o id da regra e o valor antes e depois. Nada some.

Propulsao, contra o PBE (so' nas linhas que divergem dele, ou que estao ausentes
dele entre os maiores modelos):

- **P1** -- tipo que o PBE mostra e a proposta nao tem entra no conjunto. O
  `Hibrido` do PBE so' entra como `hev` quando o nome da versao diz HEV. Tres
  artefatos conhecidos do PBE vao para decisao humana em vez de entrar: tipo que
  so' aparece num
  ano dividido entre duas vigencias do modelo (cada ano vai para a vigencia com
  mais meses nele -- o Compass de 2016 e' das duas geracoes); combustao que so'
  aparece nas tabelas sem coluna de propulsao (ate' 2020), quando a proposta tem
  eletrificado (o Prius sem HYBRID no nome sai como gasolina); e combustao de
  versao cujo nome diz HYBRID (RAV4 S HYBRID esta' em Combustao em 2026).
- **P4** -- `Hibrido` do PBE sem HEV no nome entra como `hibrido_indefinido`
  (decisao 1 da rodada das seis decisoes). O PBE rotula hibrido leve como
  Hibrido (Stonic MHEV, Forester MHEV, Sportage TMHEV estao la' com o nome
  dizendo), entao o rotulo nao escolhe entre `hev` e `mhev`; na eletrificacao o
  valor conta como `mhev` e nunca leva a `total`.
- **P5** -- fonte que declara o tipo do hibrido (rodada propulsao e comex):
  `hibrido_indefinido` vira `mhev` quando fonte forte (oficial ou especializada)
  da vigencia declara hibrido leve ("MHEV", "hibrido leve", 12 V ou 48 V com
  motor-gerador), e `hev` quando declara hibrido pleno. So' fonte fraca, fontes
  que se contradizem ou sistema ambiguo (48 V que tambem roda so' no eletrico):
  fica `hibrido_indefinido` e a linha vai a `a_adjudicar` como aviso, sem virar
  `pendente`. Fontes em `dados/referencia/hibrido_fontes.csv`. O ano de entrada
  do tipo nao muda.
- **P2** -- tipo que a proposta tem e o PBE nao mostra fica se e' anterior ao
  momento em que o PBE podia registra-lo. Desde a decisao 3, esse momento e' o
  `corte`: o primeiro ano em que o PBE cobre `LIMIAR_COBERTURA`% do volume do
  painel (`validacao_classificacao.cobertura_por_ano`). Antes dele, ausencia no
  PBE nao informa. Linha ausente do PBE: vigencia inteira antes do corte mantem
  tudo; senao, decisao humana. Linha que diverge: com pelo menos
  `MESES_ANTES_P2` meses antes do primeiro ano do modelo no PBE e do corte
  (o que vier antes), mantem os tipos de combustao, com ressalva (condicao
  necessaria, nao prova). Tipo eletrificado ausente do PBE vai sempre para
  decisao humana.
- **P3** -- `Hibrido` do PBE contra `mhev` da proposta: fica `mhev` se o nome da
  versao declara hibrido leve (o mapeamento ja' faz isso, e essas linhas nem
  divergem). Senao, desde a resposta 4 da fase 2, a mesma logica da P4: entra
  `hibrido_indefinido`, e o `mhev` da proposta -- conhecimento, nao fonte -- sai, a
  menos que o PBE o declare no nome de outra versao da vigencia.

Origem, contra fontes datadas (nas linhas que a rodada de validacao mandou
buscar fonte, e nas que tem fonte que contradiz ou ajusta a data):

- **O1** -- leitura `confirma` ou `complementa` apoiada em fonte forte
  (`tipo_fonte.FORTES`): aceita. `complementa` so' quando a fonte cobre a
  vigencia inteira.
- **O2** -- leitura `ajusta_data` apoiada em fonte forte: a fronteira da
  vigencia vai para o mes da fonte. Exige mes e evento efetivo (inicio, fim ou
  periodo de producao local); plano ou anuncio nao basta.
- **O3** -- `contradiz` e `inconclusivo` vao sempre para decisao humana; leitura
  `complementa` ou `ajusta_data` apoiada so' em fonte fraca tambem. Para essas,
  em vigencia de 2014 em diante, busca-se segunda fonte (decisao 5); o registro
  das buscas esta' em `dados/referencia/segunda_fonte_buscas.csv`.
- **O4** -- leitura `confirma` apoiada so' em fonte fraca: aceita, marcada
  `fonte_fraca` (decisao 5). Proposta e pagina da web nao sao evidencia
  independente -- o conhecimento que gerou a proposta vem em parte da mesma web
  --, por isso a marcacao acompanha o valor.

Cada decisao leva a `forca` da evidencia: `forte` (PBE; fonte oficial ou de
imprensa especializada) ou `fraca` (P2, que decide sem evidencia positiva; O4).
Dela sai a procedencia que a fase 2 vai carregar (decisao 6).

A leitura de uma linha e' a pior entre as fontes do modelo (`ORDEM_CONFRONTO`): se
alguma contradiz ou e' inconclusiva, essa; senao, a pior entre as fontes fortes,
quando ha' alguma -- a segunda fonte forte decide no lugar da primeira, fraca.

Montagem local: tabela de periodos propria (`periodos_montagem`, decisao 4).
O modo (`fabricacao`, `ckd`, `skd`) so' vale dentro do periodo que uma fonte de
`dados/referencia/montagem_fontes.csv`, com trecho copiado, declara; fora dele,
`desconhecido`; em vigencia `importado`, `nao_se_aplica` (a montagem dos furgoes
no Uruguai e' do pais de origem, nao local).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from . import classificacao, config, tipo_fonte
from .validacao_classificacao import (CHAVE, LIMIAR_COBERTURA, ORDEM_CONFRONTO,
                                      PRIMEIRO_ANO_PBE, ULTIMO_ANO_SEM_COLUNA, _meses_no_ano,
                                      casos_de_origem, fontes_por_linha)

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
MODOS_MONTAGEM = ("fabricacao", "ckd", "skd", "desconhecido", "nao_se_aplica")
# Janela dos artigos de tarifa e eletrificacao: so' na vigencia que a toca se busca
# segunda fonte (resposta 6 da fase 2: tocar, nao comecar).
INICIO_JANELA_SEGUNDA_FONTE = "2014-01"


def carregar_regras() -> pd.DataFrame:
    return pd.read_csv(config.REGRAS_ADJUDICACAO, dtype=str, keep_default_na=False)


def carregar_fontes() -> pd.DataFrame:
    """Fontes de origem com `tipo_fonte` recalculado de `config/tipo_fonte_dominio.csv`."""
    fontes = pd.read_csv(config.ORIGEM_FONTES, dtype=str, keep_default_na=False)
    return tipo_fonte.com_tipo(fontes, tipo_fonte.carregar_mapa())


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
    # vao ao rascunho para revisao sem tornar o atributo `pendente` (P5 que nao decide:
    # o valor fica o das outras regras)
    avisos: list[str] = field(default_factory=list)
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
              linhas_modelo: pd.DataFrame, corte: int) -> Resultado:
    """P1, P2, P3 e P4 numa linha que diverge do PBE ou esta' ausente dele.

    `corte` e' o primeiro ano em que o PBE cobre `LIMIAR_COBERTURA`% do volume.
    """
    if linha["pbe_situacao"] == "ausente":
        return _ausente(linha, primeiro_ano, corte)
    proposta = {p for p in linha["propulsao_oferecida"].split("+") if p}
    texto_proposta = linha["propulsao_oferecida"] or "(vazia)"
    so_pbe, so_proposta = _diferenca(linha["pbe_diferenca"])
    anos = _anos(linha["pbe_anos"])
    divididos = _anos_divididos(linha, linhas_modelo, anos)
    r = Resultado()
    acrescentados: list[tuple[str, str]] = []
    indefinidos = ""
    p3 = ""

    for tipo in _ordenados(so_pbe):
        versoes = _versoes(casado_chave, anos, tipo)
        nomes = _exemplos(versoes["modelo_versao"])
        if versoes.empty:
            r.pendencias.append(f"P1 nao decide: {tipo} sem versao do PBE nos anos da vigencia")
            continue
        guarda = _guarda_p1(tipo, versoes, divididos, proposta)
        if tipo == "hev" and "mhev" in proposta:
            com_hev = versoes["marcador_nome"].str.split("+").apply(lambda m: "HEV" in m)
            if guarda or com_hev.any():
                r.pendencias.append(
                    f"P3 nao decide: {guarda or 'o PBE diz HEV no nome'} ({nomes}); a proposta "
                    "diz mhev")
                continue
            p3 = nomes
            continue
        if guarda:
            r.pendencias.append(f"P1 nao decide: {guarda}")
            continue
        if tipo == "hev":
            com_hev = versoes["marcador_nome"].str.split("+").apply(lambda m: "HEV" in m)
            if com_hev.any():
                acrescentados.append(("hev", _exemplos(versoes.loc[com_hev, "modelo_versao"])))
            if (~com_hev).any():
                indefinidos = _exemplos(versoes.loc[~com_hev, "modelo_versao"])
            continue
        acrescentados.append((tipo, nomes))

    if acrescentados:
        novo = _ordenados(proposta | {t for t, _ in acrescentados})
        r.resolucoes.append({
            "regra": "P1", "forca": "forte", "antes": texto_proposta, "depois": "+".join(novo),
            "base": "; ".join(f"{t}: PBE {linha['pbe_anos']} ({n})" for t, n in acrescentados),
            "ressalva": "proposta vazia: o conjunto vem so' do PBE" if not proposta else ""})
        proposta = set(novo)
    if p3:
        # resposta 4 da fase 2: o mhev da proposta e' conhecimento, nao fonte; fica so' se
        # o PBE declara hibrido leve no nome de alguma versao desta vigencia
        sem_fonte = "mhev" in so_proposta
        novo = _ordenados((proposta - ({"mhev"} if sem_fonte else set()))
                          | {"hibrido_indefinido"})
        r.resolucoes.append({
            "regra": "P3", "forca": "forte", "antes": "+".join(_ordenados(proposta)),
            "depois": "+".join(novo),
            "base": (f"Hibrido no PBE {linha['pbe_anos']} sem marcador de hibrido leve ({p3}); "
                     + ("o mhev da proposta nao tem fonte e sai" if sem_fonte
                        else "o mhev fica: o PBE o declara no nome de outra versao")),
            "ressalva": "sobe para mhev se uma fonte declarar hibrido leve"})
        proposta = set(novo)
    if indefinidos:
        novo = _ordenados(proposta | {"hibrido_indefinido"})
        r.resolucoes.append({
            "regra": "P4", "forca": "forte", "antes": "+".join(_ordenados(proposta)) or "(vazia)",
            "depois": "+".join(novo),
            "base": f"Hibrido no PBE {linha['pbe_anos']} sem HEV no nome ({indefinidos})",
            "ressalva": ""})
        proposta = set(novo)

    limite = min(a for a in (primeiro_ano, corte) if a is not None)
    meses_antes = max(0, min(_mes(f"{limite}-01"), _mes(linha["vigencia_fim"]) + 1)
                      - _mes(linha["vigencia_inicio"]))
    referencia = (f"{limite}, primeiro ano do modelo no PBE" if limite == primeiro_ano
                  else f"{limite}, ano em que o PBE passou a cobrir {LIMIAR_COBERTURA:.0f}% do "
                       "volume")
    mantidos = []
    for tipo in _ordenados(so_proposta):
        if tipo == "mhev" and "hev" in so_pbe:
            continue  # ja' anotado em P3
        if tipo in COMBUSTAO and meses_antes >= MESES_ANTES_P2:
            mantidos.append(tipo)
        elif tipo in COMBUSTAO:
            r.pendencias.append(
                f"P2 nao decide: {tipo} so' na proposta; a vigencia tem {meses_antes} meses antes "
                f"de {referencia} (minimo {MESES_ANTES_P2})")
        else:
            r.pendencias.append(
                f"P2 nao decide: {tipo} so' na proposta; tipo eletrificado ausente do PBE vai "
                "para decisao humana")
    if mantidos:
        r.resolucoes.append({
            "regra": "P2", "forca": "fraca", "antes": "+".join(_ordenados(proposta)),
            "depois": "+".join(_ordenados(proposta)),
            "base": f"mantem {'+'.join(mantidos)}: a vigencia tem {meses_antes} meses antes de "
                    f"{referencia}",
            "ressalva": "condicao necessaria, nao prova: a proposta nao data o tipo; conferir"})

    r.valor_apos_regras = "+".join(_ordenados(proposta))
    if not r.pendencias:
        r.decisao = _decisao_propulsao(r.valor_apos_regras)
    return r


def _ausente(linha: pd.Series, primeiro_ano: int | None, corte: int) -> Resultado:
    r = Resultado(valor_apos_regras=linha["propulsao_oferecida"])
    proposta = linha["propulsao_oferecida"]
    if not proposta:
        r.pendencias.append("propulsao sem proposta e modelo ausente do PBE nesta vigencia")
        return r
    if linha["vigencia_fim"] < f"{PRIMEIRO_ANO_PBE}-01":
        base = f"vigencia inteira anterior ao PBE ({PRIMEIRO_ANO_PBE})"
    elif linha["vigencia_fim"] < f"{corte}-01":
        base = (f"vigencia inteira anterior a {corte}, ano em que o PBE passou a cobrir "
                f"{LIMIAR_COBERTURA:.0f}% do volume: ausencia nao informativa")
    else:
        if primeiro_ano is None:
            detalhe = "o modelo nao aparece no PBE em ano nenhum"
        else:
            detalhe = f"o modelo aparece no PBE desde {primeiro_ano}, mas nao nos anos desta vigencia"
        if linha.get("pbe_nota"):
            detalhe += f" ({linha['pbe_nota']})"
        r.pendencias.append(f"ausente no PBE com a vigencia depois de {corte}, quando a ausencia "
                            f"passa a informar: {detalhe}")
        return r
    r.resolucoes.append({"regra": "P2", "forca": "fraca", "antes": proposta, "depois": proposta,
                         "base": f"mantem tudo: {base}", "ressalva": ""})
    r.decisao = _decisao_propulsao(proposta)
    return r


def _decisao_propulsao(valor: str) -> str:
    return f"propulsao_oferecida={valor}; eletrificacao={classificacao.eletrificacao(valor)}"


# ------------------------------------------------- P5: hibrido leve ou pleno

TIPOS_DECLARADOS = ("mhev", "hev", "ambiguo")
TOLERANCIA_HIBRIDO = 12  # meses antes do inicio da vigencia em que a fonte ainda trata dela


def carregar_hibridos() -> pd.DataFrame:
    if not config.HIBRIDO_FONTES.exists():
        return pd.DataFrame(columns=CHAVE + ["tipo_declarado", "data_fonte", "tipo_fonte",
                                             "pagina_salva"])
    return pd.read_csv(config.HIBRIDO_FONTES, dtype=str, keep_default_na=False)


def hibridos_da_linha(linha: pd.Series, fontes_chave: pd.DataFrame | None) -> pd.DataFrame | None:
    """As fontes do tipo de hibrido que tratam desta vigencia.

    Fonte datada trata da vigencia que contem a data, aceitando ate'
    `TOLERANCIA_HIBRIDO` meses antes do inicio (o anuncio de lancamento vem antes
    das vendas); fonte sem data trata de todas as vigencias do modelo.
    """
    if fontes_chave is None or fontes_chave.empty:
        return None
    inicio, fim = _mes(linha["vigencia_inicio"]), _mes(linha["vigencia_fim"])

    def cobre(data: str) -> bool:
        if not data:
            return True
        primeiro = _mes(data if len(data) == 7 else f"{data}-01")
        ultimo = _mes(data if len(data) == 7 else f"{data}-12")
        return ultimo >= inicio - TOLERANCIA_HIBRIDO and primeiro <= fim
    cobertas = fontes_chave[fontes_chave["data_fonte"].apply(cobre)]
    return cobertas if len(cobertas) else None


def p5(valor: str, fontes: pd.DataFrame | None) -> tuple[str, dict | None, str]:
    """(valor, resolucao, aviso) da P5 num conjunto com `hibrido_indefinido`.

    Fonte forte (oficial ou especializada) que declara hibrido leve troca
    `hibrido_indefinido` por `mhev`; que declara pleno, por `hev`. Fica
    `hibrido_indefinido`, com aviso para o rascunho, quando so' ha' fonte fraca,
    quando as fontes se contradizem ou quando alguma descreve sistema ambiguo.
    """
    if "hibrido_indefinido" not in valor.split("+") or fontes is None:
        return valor, None, ""
    declarados = set(fontes["tipo_declarado"])
    paginas = ", ".join(dict.fromkeys(fontes["pagina_salva"]))
    if "ambiguo" in declarados:
        return valor, None, (f"P5 nao decide: fonte descreve sistema ambiguo ({paginas}); "
                             "fica hibrido_indefinido")
    if len(declarados) > 1:
        return valor, None, (f"P5 nao decide: fontes se contradizem ({paginas}); fica "
                             "hibrido_indefinido")
    fortes = fontes[fontes["tipo_fonte"].isin(tipo_fonte.FORTES)]
    if fortes.empty:
        return valor, None, (f"P5 nao decide: fonte unica e fraca ({paginas}); fica "
                             "hibrido_indefinido")
    tipo = declarados.pop()
    novo = "+".join(_ordenados((set(valor.split("+")) - {"hibrido_indefinido"}) | {tipo}))
    resolucao = {
        "regra": "P5", "forca": "forte", "antes": valor, "depois": novo,
        "base": (f"fonte declara {'hibrido leve' if tipo == 'mhev' else 'hibrido pleno'} "
                 f"({', '.join(dict.fromkeys(fortes['pagina_salva']))})"),
        "ressalva": "o ano de entrada do tipo nao muda; so' o rotulo"}
    return novo, resolucao, ""


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


def carregar_buscas() -> dict[tuple, dict]:
    """Buscas de segunda fonte sem sucesso, por chave (decisao 5)."""
    if not config.SEGUNDA_FONTE_BUSCAS.exists():
        return {}
    buscas = pd.read_csv(config.SEGUNDA_FONTE_BUSCAS, dtype=str, keep_default_na=False)
    return {tuple(b[CHAVE]): b.to_dict() for _, b in buscas.iterrows()}


def _nota_segunda_fonte(linha: pd.Series, leitura: str, busca: dict | None) -> str:
    if leitura not in ("complementa", "ajusta_data"):
        return ""
    if linha["vigencia_fim"] < INICIO_JANELA_SEGUNDA_FONTE:
        return (f" -- vigencia inteira antes de {INICIO_JANELA_SEGUNDA_FONTE[:4]}: segunda fonte "
                "nao buscada (decisao 5)")
    if busca is None:
        return " -- segunda fonte ainda nao buscada"
    if busca.get("resultado") == "forte_achada":
        return (f" -- segunda fonte forte achada em {busca['data_busca']}, mas ela nao trata "
                "desta vigencia")
    return f" -- segunda fonte buscada em {busca['data_busca']} e nao achada"


def origem(linha: pd.Series, indice: int, fontes_chave: pd.DataFrame | None, caso: bool,
           linhas_modelo: pd.DataFrame, busca: dict | None = None) -> Resultado | None:
    """O1 a O4 numa linha. None quando a linha esta' fora do universo de origem."""
    valor = linha["origem_producao"]
    if fontes_chave is None or fontes_chave.empty:
        if not caso:
            return None
        return Resultado(pendencias=["origem sem fonte"], valor_apos_regras=valor)
    pior = min(fontes_chave["confronto_com_proposta"], key=ORDEM_CONFRONTO.index)
    if not caso and pior not in ("contradiz", "ajusta_data"):
        return None
    r = Resultado(valor_apos_regras=valor)
    # contradiz e inconclusivo de qualquer fonte mandam (O3); fora isso, a fonte forte
    # vem antes da fraca: a segunda fonte forte decide no lugar da primeira, fraca.
    if pior in ("contradiz", "inconclusivo"):
        consideradas = fontes_chave
    else:
        fortes_todas = fontes_chave[fontes_chave["tipo_fonte"].isin(tipo_fonte.FORTES)]
        consideradas = fortes_todas if not fortes_todas.empty else fontes_chave
    leitura = min(consideradas["confronto_com_proposta"], key=ORDEM_CONFRONTO.index)
    de_leitura = consideradas[consideradas["confronto_com_proposta"] == leitura]
    fortes = de_leitura[de_leitura["tipo_fonte"].isin(tipo_fonte.FORTES)]

    if leitura in ("contradiz", "inconclusivo"):
        nota = "" if len(fortes) else " -- fonte unica e fraca" if len(de_leitura) == 1 else \
            " -- so' fonte fraca"
        r.pendencias.append(f"O3: fonte de origem {leitura.replace('_', ' ')} "
                            f"({_descrever(de_leitura)}){nota}")
        return r
    if fortes.empty:
        if leitura == "confirma" and valor:
            r.resolucoes.append({"regra": "O4", "forca": "fraca", "antes": f"origem_producao={valor}",
                                 "depois": f"origem_producao={valor}",
                                 "base": f"confirma, so' fonte fraca: {_descrever(de_leitura)}",
                                 "ressalva": "fonte_fraca: proposta e pagina da web nao sao "
                                             "evidencia independente"})
            r.decisao = f"origem_producao={valor}"
            return r
        r.pendencias.append(f"O3: leitura '{leitura.replace('_', ' ')}' apoiada so' em fonte "
                            f"fraca ({_descrever(de_leitura)})"
                            + _nota_segunda_fonte(linha, leitura, busca))
        return r

    if leitura == "ajusta_data":
        # resposta 2 da fase 2: data de lancamento quando a fonte a da', senao de producao
        utilizaveis = sorted(
            (f for _, f in fortes.iterrows() if f["evento"] in EVENTOS_EFETIVOS
             and f.get("tipo_data_fonte", "producao") in ("lancamento", "producao")
             and all(MES.match(p) for p in f["origem_data_fonte"].split("/"))),
            key=lambda f: f.get("tipo_data_fonte", "producao") != "lancamento")
        if not utilizaveis:
            efetivas = fortes[fortes["evento"].isin(EVENTOS_EFETIVOS)
                              & (fortes.get("tipo_data_fonte", "producao") != "plano")]
            motivo = ("plano ou anuncio, nao evento efetivo" if efetivas.empty
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
        base = (f"{fonte['evento']} {fonte['origem_data_fonte']}, data de "
                f"{fonte.get('tipo_data_fonte', 'producao')} "
                f"({fonte['tipo_fonte']}, {tipo_fonte.dominio(fonte['origem_fonte_url'])})")
        if indice in mudancas:
            atributo, antes, depois = mudancas[indice]
            r.resolucoes.append({"regra": "O2", "forca": "forte", "antes": f"{atributo}={antes}",
                                 "depois": f"{atributo}={depois}", "base": base, "ressalva": ""})
            r.decisao = f"{atributo}={depois}"
        else:
            r.resolucoes.append({"regra": "O2", "forca": "forte", "antes": f"origem_producao={valor}",
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
        r.resolucoes.append({"regra": "O1", "forca": "forte", "antes": f"origem_producao={valor}",
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
        r.resolucoes.append({"regra": "O1", "forca": "forte", "antes": f"origem_producao={valor or '(vazia)'}",
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


# ------------------------------------------------------------- procedencia

# Decisao 6: a dimensao final carrega, por atributo, de onde veio o valor; `pendente`
# entrou como quinto valor na fase 2.
PROCEDENCIAS = ("humana", "regra_fonte_forte", "regra_fonte_fraca", "proposta", "pendente")


def _humana_toca(decisao: str, atributo: str) -> bool:
    """A decisao humana fala deste atributo? `ok` e texto livre falam de todos."""
    decisao = decisao.strip()
    if not decisao:
        return False
    if "=" not in decisao:
        return True
    return any(parte.strip().startswith(f"{atributo}=") for parte in decisao.split(";"))


def _procedencia(linha: pd.Series, atributo: str, resultado: Resultado | None,
                 confirmacao: str) -> str:
    """Procedencia de um atributo pela precedencia da fase 2 (humana, regra, proposta).

    `pendente` e' o quinto valor (resposta da fase 2): o atributo esta' em
    `a_adjudicar` sem decisao humana, e o dado mostra a proposta original. Fora do
    universo das regras, o valor que uma checagem confirmou conta como decidido
    pela regra da checagem (`confirmacao`: forte ou fraca); sem checagem que
    confirme, e' `proposta`.
    """
    if _humana_toca(linha.get("decisao_humana", ""), atributo):
        return "humana"
    if resultado is not None and resultado.pendencias:
        return "pendente"
    if resultado is not None and resultado.decisao:
        forcas = {res["forca"] for res in resultado.resolucoes}
        return "regra_fonte_fraca" if "fraca" in forcas else "regra_fonte_forte"
    if confirmacao:
        return f"regra_fonte_{confirmacao}"
    return "proposta"


def procedencia_carroceria(linha: pd.Series) -> str:
    """Carroceria: do sub-segmento da Fenabrave (regras S01-S10) ou do conhecimento."""
    if _humana_toca(linha.get("decisao_humana", ""), "carroceria"):
        return "humana"
    parte = next((p for p in linha["fonte_da_proposta"].split(" | ")
                  if p.startswith("carroceria:")), "")
    if "sub-segmento da fonte" in parte and "refinada por conhecimento" not in parte:
        return "regra_fonte_forte"
    return "proposta"


def _confirmacao_origem(fontes_chave: pd.DataFrame | None) -> str:
    if fontes_chave is None or fontes_chave.empty:
        return ""
    confirmam = fontes_chave[fontes_chave["confronto_com_proposta"] == "confirma"]
    if confirmam.empty or len(confirmam) < len(fontes_chave):
        return ""  # alguma fonte nao confirma: sem confirmacao limpa
    return "forte" if confirmam["tipo_fonte"].isin(tipo_fonte.FORTES).any() else "fraca"


# ---------------------------------------------------------------- aplicacao


def aplicar(rascunho: pd.DataFrame, casado: pd.DataFrame, fontes: pd.DataFrame, top: int,
            corte: int, buscas: dict | None = None, hibridos: pd.DataFrame | None = None
            ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(rascunho com colunas de regra, resolvido_por_regra).

    Colunas novas no rascunho: `regras_aplicadas`, `pendencias`, `avisos`,
    `propulsao_apos_regras`, `origem_apos_regras`, `origem_tipos_fonte`,
    `procedencia_propulsao`, `procedencia_carroceria`, `procedencia_origem` e
    `decisao_por_regra`. `corte` e' o ano de corte da P2 (decisao 3).
    """
    buscas = buscas or {}
    hibridos_por_chave = ({} if hibridos is None or hibridos.empty
                          else {k: g for k, g in hibridos.groupby(CHAVE)})
    saida = rascunho.copy()
    no_pbe = casado[casado["marca"] != ""]
    por_chave = {k: g for k, g in no_pbe.groupby(CHAVE)}
    primeiro = {k: int(g["ano_pbe"].astype(int).min()) for k, g in por_chave.items()}
    # cada fonte vale so' para as vigencias de que trata (resposta 3 da fase 2)
    fontes_da_linha = fontes_por_linha(saida, fontes)
    modelos = {k: g for k, g in saida.groupby(CHAVE, sort=False)}
    casos = casos_de_origem(saida, top)

    resolvidos, colunas = [], {c: {} for c in ("regras_aplicadas", "pendencias", "avisos",
                                                "propulsao_apos_regras", "origem_apos_regras",
                                                "origem_tipos_fonte", "procedencia_propulsao",
                                                "procedencia_carroceria", "procedencia_origem",
                                                "decisao_por_regra")}
    for indice, linha in saida.iterrows():
        chave = tuple(linha[CHAVE])
        resultados: list[tuple[str, Resultado]] = []
        if linha["pbe_situacao"] == "diverge" or (linha["pbe_situacao"] == "ausente"
                                                  and linha["posicao"] <= top):
            resultados.append(("propulsao_oferecida", propulsao(
                linha, por_chave.get(chave), primeiro.get(chave), modelos[chave], corte)))
        r_propulsao = dict(resultados).get("propulsao_oferecida")
        if r_propulsao is not None:
            novo, resolucao, aviso = p5(r_propulsao.valor_apos_regras, hibridos_da_linha(
                linha, hibridos_por_chave.get(chave)))
            if resolucao:
                r_propulsao.resolucoes.append(resolucao)
                r_propulsao.valor_apos_regras = novo
                if not r_propulsao.pendencias:
                    r_propulsao.decisao = _decisao_propulsao(novo)
            if aviso:
                r_propulsao.avisos.append(aviso)
        fontes_chave = fontes_da_linha.get(indice)
        r_origem = origem(linha, indice, fontes_chave, bool(casos[indice]), modelos[chave],
                          buscas.get(chave))
        if r_origem is not None:
            resultados.append(("origem_producao", r_origem))

        pendencias = [p for _, r in resultados for p in r.pendencias]
        for atributo, r in resultados:
            for res in r.resolucoes:
                resolvidos.append({
                    "regra": res["regra"], "forca": res["forca"], "atributo": atributo,
                    "situacao_da_linha": "resolvida" if not pendencias else "parcial",
                    **{c: linha[c] for c in ("posicao", "marca", "modelo", "segmento",
                                             "vigencia_inicio", "vigencia_fim",
                                             "unidades_na_vigencia")},
                    "antes": res["antes"], "depois": res["depois"], "base": res["base"],
                    "ressalva": res["ressalva"]})
        colunas["regras_aplicadas"][indice] = "+".join(dict.fromkeys(
            res["regra"] for _, r in resultados for res in r.resolucoes))
        colunas["pendencias"][indice] = " | ".join(pendencias)
        colunas["avisos"][indice] = " | ".join(a for _, r in resultados for a in r.avisos)
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
        por_atributo = dict(resultados)
        colunas["procedencia_propulsao"][indice] = _procedencia(
            linha, "propulsao_oferecida", por_atributo.get("propulsao_oferecida"),
            "forte" if linha["pbe_situacao"] == "concorda" else "")
        colunas["procedencia_origem"][indice] = _procedencia(
            linha, "origem_producao", por_atributo.get("origem_producao"),
            _confirmacao_origem(fontes_chave) if linha["origem_producao"] else "")
        colunas["procedencia_carroceria"][indice] = procedencia_carroceria(linha)
    for nome, valores in colunas.items():
        saida[nome] = pd.Series(valores)
    resolvido = pd.DataFrame(resolvidos, columns=[
        "regra", "forca", "atributo", "situacao_da_linha", "posicao", "marca", "modelo", "segmento",
        "vigencia_inicio", "vigencia_fim", "unidades_na_vigencia", "antes", "depois", "base",
        "ressalva"])
    return saida, resolvido


def a_adjudicar(com_regras: pd.DataFrame, fila_antes: pd.DataFrame) -> pd.DataFrame:
    """So' o que as regras nao decidem, maior volume primeiro."""
    antes = set(map(tuple, fila_antes[CHAVE + ["vigencia_inicio"]].to_numpy()))
    fila = com_regras[_na_fila(com_regras)].copy()
    fila["na_fila_antes"] = ["sim" if tuple(k) in antes else "nao, entrou nesta rodada"
                             for k in fila[CHAVE + ["vigencia_inicio"]].to_numpy()]
    fila["motivo"] = [" | ".join(m for m in (p, a) if m)
                      for p, a in zip(fila["pendencias"], _avisos(fila))]
    colunas = ["motivo", "na_fila_antes", "regras_aplicadas", "posicao", "marca", "modelo",
               "segmento", "vigencia_inicio", "vigencia_fim", "unidades_na_vigencia",
               "propulsao_oferecida", "propulsao_apos_regras", "pbe_propulsao", "pbe_anos",
               "pbe_diferenca", "pbe_nota", "origem_producao", "origem_apos_regras",
               "confianca_origem", "origem_confronto", "origem_tipos_fonte", "origem_data_fonte",
               "origem_fonte_url", "montagem_por_periodo", "observacao", "decisao_por_regra",
               "decisao_humana"]
    return fila.sort_values("unidades_na_vigencia", ascending=False, kind="stable")[colunas]


def _avisos(quadro: pd.DataFrame) -> pd.Series:
    return quadro["avisos"] if "avisos" in quadro else pd.Series("", index=quadro.index)


def _na_fila(com_regras: pd.DataFrame) -> pd.Series:
    """Linha vai a `a_adjudicar` com pendencia (atributo `pendente`) ou com aviso da P5."""
    return (com_regras["pendencias"] != "") | (_avisos(com_regras) != "")


def contas(fila_antes: pd.DataFrame, com_regras: pd.DataFrame, resolvido: pd.DataFrame
           ) -> pd.DataFrame:
    """A conta da rodada: quantas linhas sairam da fila, por regra, e quantas ficaram."""
    chave = CHAVE + ["vigencia_inicio"]
    antes = set(map(tuple, fila_antes[chave].to_numpy()))
    depois = set(map(tuple, com_regras.loc[_na_fila(com_regras), chave].to_numpy()))
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
    for regra in ("P1", "P2", "P3", "P4", "P5", "O1", "O2", "O4"):
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


def _unidades_por_mes(unidades: pd.DataFrame) -> dict[tuple, pd.Series]:
    """chave -> unidades por mes (indice inteiro de mes), do painel."""
    quadro = unidades.assign(_m=unidades["mes_ref"].map(_mes))
    return {k: g.groupby("_m")["unidades"].sum() for k, g in quadro.groupby(CHAVE)}


def periodos_montagem(com_regras: pd.DataFrame, montagem: pd.DataFrame,
                      unidades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(rascunho com `montagem_por_periodo`, tabela de periodos de montagem).

    Decisao 4: a montagem tem periodo proprio (`montagem_inicio`, `montagem_fim`),
    no padrao de vigencia do mapa de grupos. Dentro do periodo que uma fonte
    cobre, o modo da fonte; fora dele, `desconhecido`; em vigencia `importado`,
    `nao_se_aplica` -- para o carro importado o modo de montagem local nao existe.
    Os periodos de cada modelo cobrem todos os meses das suas vigencias, sem
    sobreposicao.
    """
    saida = com_regras.copy()
    por_mes = _unidades_por_mes(unidades)
    brasil = montagem[montagem["onde"] == "brasil"] if not montagem.empty else montagem
    fontes_por_chave = {k: g for k, g in brasil.groupby(CHAVE)} if not brasil.empty else {}
    periodos, resumos = [], {}
    for indice, linha in saida.iterrows():
        chave = tuple(linha[CHAVE])
        v_inicio, v_fim = _mes(linha["vigencia_inicio"]), _mes(linha["vigencia_fim"])
        origem_linha = linha.get("origem_apos_regras", linha["origem_producao"])
        serie = por_mes.get(chave, pd.Series(dtype=int))
        trechos = []  # (inicio, fim, fonte) recortados na vigencia
        fontes = fontes_por_chave.get(chave)
        for _, fonte in (fontes.iterrows() if fontes is not None else []):
            p_inicio, p_fim = _periodo_montagem(fonte["periodo_inicio"], fonte["periodo_fim"])
            if p_fim >= v_inicio and p_inicio <= v_fim:
                trechos.append((max(p_inicio, v_inicio), min(p_fim, v_fim), fonte))
        base = {c: linha[c] for c in CHAVE + ["vigencia_inicio", "vigencia_fim"]}
        base["origem_producao"] = origem_linha

        def periodo(inicio, fim, modo, fonte=None, procedencia="proposta", observacao=""):
            periodos.append({
                **base, "montagem_inicio": _texto_mes(inicio), "montagem_fim": _texto_mes(fim),
                "montagem_local": modo,
                "unidades": int(serie[(serie.index >= inicio) & (serie.index <= fim)].sum()),
                "fonte_url": "" if fonte is None else fonte["fonte_url"],
                "tipo_fonte": "" if fonte is None else fonte.get("tipo_fonte", ""),
                "procedencia": procedencia, "observacao": observacao})

        if origem_linha == "importado":
            nota = "; ".join(
                f"a fonte declara {f['montagem_local']} de {_texto_mes(a)} a {_texto_mes(b)}, "
                "mas a linha e' importado" + (" (origem desta vigencia em a_adjudicar)"
                                               if "O3" in linha.get("pendencias", "") else "")
                for a, b, f in trechos)
            periodo(v_inicio, v_fim, "nao_se_aplica",
                    procedencia=linha.get("procedencia_origem", "proposta"), observacao=nota)
            resumos[indice] = "nao_se_aplica"
            continue
        pontos = sorted({v_inicio, v_fim + 1} | {a for a, _, _ in trechos}
                        | {b + 1 for _, b, _ in trechos})
        partes = []
        for inicio, proximo in zip(pontos[:-1], pontos[1:]):
            fim = proximo - 1
            cobrem = [f for a, b, f in trechos if a <= inicio and b >= fim]
            modos = {f["montagem_local"] for f in cobrem}
            if not cobrem:
                periodo(inicio, fim, "desconhecido")
                modo = "desconhecido"
            elif len(modos) > 1:
                periodo(inicio, fim, "desconhecido",
                        observacao=f"fontes divergem: {', '.join(sorted(modos))}")
                modo = "desconhecido"
            else:
                fonte = cobrem[0]
                forte = fonte.get("tipo_fonte", "") in tipo_fonte.FORTES
                modo = fonte["montagem_local"]
                periodo(inicio, fim, modo, fonte,
                        "regra_fonte_forte" if forte else "regra_fonte_fraca",
                        fonte.get("observacao", ""))
            partes.append(f"{modo} {_texto_mes(inicio)} a {_texto_mes(fim)}")
        resumos[indice] = partes[0].split(" ")[0] if len(partes) == 1 else "; ".join(partes)
    saida["montagem_por_periodo"] = pd.Series(resumos)
    colunas = CHAVE + ["vigencia_inicio", "vigencia_fim", "origem_producao", "montagem_inicio",
                       "montagem_fim", "montagem_local", "unidades", "fonte_url", "tipo_fonte",
                       "procedencia", "observacao"]
    return saida, pd.DataFrame(periodos, columns=colunas)


def exterior_montagem(montagem: pd.DataFrame) -> pd.DataFrame:
    """Fontes de montagem no exterior: registradas, nao aplicadas."""
    if montagem.empty:
        return montagem
    return montagem[montagem["onde"] != "brasil"]


def resumo_montagem(periodos: pd.DataFrame) -> pd.DataFrame:
    total = periodos["unidades"].sum()
    linhas = []
    for rotulo, filtro in [
        ("todos os periodos", periodos.index == periodos.index),
        ("origem nacional ou ambos", periodos["origem_producao"].isin(LOCAL)),
        ("origem importado", periodos["origem_producao"] == "importado"),
        ("origem sem proposta", periodos["origem_producao"] == ""),
    ]:
        parte = periodos[filtro]
        for modo in MODOS_MONTAGEM:
            sub = parte[parte["montagem_local"] == modo]
            linhas.append({"recorte": rotulo, "montagem_local": modo, "periodos": len(sub),
                           "unidades": int(sub["unidades"].sum()),
                           "pct_do_classificado": round(100 * sub["unidades"].sum() / total, 2)})
    return pd.DataFrame(linhas)
