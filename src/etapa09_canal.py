#!/usr/bin/env python3
"""Etapa 9 -- painel de canal de venda: venda direta e varejo.

Tabela de fatos **paralela** ao painel de vendas, nunca coluna dele: um
modelo-mes tem ate' duas linhas de canal, e os totais nao reconciliam com as
tabelas de sub-segmento -- sao recortes diferentes da mesma realidade.

Produto: `dados/processado/painel_canal.parquet`, chave
`(mes_ref, segmento, canal, marca, modelo)`, com a procedencia de cada linha
(`origem_tabela`, `posicao_fonte`, `arquivo_origem`, `pagina_origem`).

**O que ele e' e o que nao e'.** A fonte publica o canal em ranking de 50
posicoes por segmento. Entao o painel de canal e' o **topo** de cada canal, e a
parte que ele cobre do mes anda 14 pontos ao longo da serie, em U. O **nivel**
das quantidades nao e' comparavel entre anos; comparacao segura e' dentro do
ano. Ver o dicionario e a sec.12 do validacao.md.

Tambem produz, em `saidas/`:
- `canal_cobertura.csv` -- quanto do total publicado as tabelas explicam, mes a mes;
- `canal_participacao.csv` -- a participacao publicada, nos 29 meses em texto;
- `canal_calibracao.csv` -- publicada contra calculada: o vies do top-50;
- `canal_mesmo_valor_nos_dois_canais.csv` -- conferencia de duplicata de leitura.

Grava cada mes ao terminar e retoma de onde parou (ESPEC sec.10.4).

Uso:
    python src/etapa09_canal.py [--inicio AAAA-MM] [--fim AAAA-MM] [--forcar]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import canal, config, log, marcas, nomes, periodo  # noqa: E402

ETAPA = "etapa09_canal"

CAMPOS_ENTRADA = ["mes_ref", "segmento", "canal", "posicao_fonte", "nome_completo_fonte",
                  "unidades", "origem_tabela", "pagina_origem", "arquivo_origem",
                  "metodo_extracao"]
CAMPOS_PIZZA = ["mes_ref", "pizza", "primeiro", "segundo", "pagina_origem"]
DICAS = ("modelo_direta_mes", "modelo_varejo_mes", "participacao_mes")


def _escrever(caminho: Path, campos: list[str], linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=campos)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({campo: linha.get(campo, "") for campo in campos})


def _dicas() -> dict[str, dict[str, int]]:
    """Paginas ja' localizadas pelo diagnostico da fase 1. So' economizam tempo:
    cada uma e' conferida pelo titulo antes de ser lida."""
    caminho = config.DIR_SAIDAS / "diagnostico_canal.csv"
    if not caminho.exists():
        return {}
    quadro = pd.read_csv(caminho, dtype=str, keep_default_na=False)
    saida = {}
    for linha in quadro.to_dict("records"):
        saida[linha["mes"]] = {
            tipo: int(float(linha[f"pg_{tipo}"]))
            for tipo in DICAS if linha.get(f"pg_{tipo}", "") not in ("", "nan")
        }
    return saida


def extrair_mes(mes: str, caminho: Path, dicas: dict[str, int]) -> tuple[list, list, list]:
    leitura = canal.ler(caminho, dicas)
    entradas = [{
        "mes_ref": mes, "segmento": e.segmento, "canal": e.canal,
        "posicao_fonte": e.posicao, "nome_completo_fonte": e.nome,
        "unidades": e.unidades, "origem_tabela": e.origem_tabela,
        "pagina_origem": e.pagina, "arquivo_origem": caminho.name,
        "metodo_extracao": e.metodo,
    } for e in leitura.entradas]
    pizzas = [{
        "mes_ref": mes, "pizza": indice + 1, "primeiro": primeiro, "segundo": segundo,
        "pagina_origem": leitura.paginas.get("participacao_mes", ""),
    } for indice, (primeiro, segundo) in enumerate(leitura.pizzas)]
    return entradas, pizzas, leitura.avisos


def montar_painel(meses: list[str]) -> pd.DataFrame:
    partes = []
    for mes in meses:
        caminho = config.DIR_CANAL / f"{mes}.csv"
        if caminho.exists():
            bloco = pd.read_csv(caminho, dtype=str, keep_default_na=False)
            if not bloco.empty:
                partes.append(bloco)
    if not partes:
        return pd.DataFrame(columns=CAMPOS_ENTRADA)
    painel = pd.concat(partes, ignore_index=True)
    separacoes = [marcas.separar(nome) for nome in painel["nome_completo_fonte"]]
    # Mesma canonizacao da chave do painel de vendas (D1), para a juncao ser direta.
    painel["marca"] = [nomes.chave(s.marca) for s in separacoes]
    painel["modelo"] = [nomes.chave(s.modelo) for s in separacoes]
    painel["unidades"] = pd.to_numeric(painel["unidades"]).astype("int64")
    painel["posicao_fonte"] = pd.to_numeric(painel["posicao_fonte"]).astype("int32")
    painel["pagina_origem"] = pd.to_numeric(painel["pagina_origem"]).astype("int32")
    painel["ano"] = painel["mes_ref"].str.slice(0, 4).astype("int32")
    painel["mes"] = painel["mes_ref"].str.slice(5, 7).astype("int32")
    colunas = ["mes_ref", "ano", "mes", "segmento", "canal", "marca", "modelo", "unidades",
               "posicao_fonte", "nome_completo_fonte", "origem_tabela", "arquivo_origem",
               "pagina_origem", "metodo_extracao"]
    return painel[colunas].sort_values(
        ["mes_ref", "segmento", "canal", "posicao_fonte"]).reset_index(drop=True)


def _totais_publicados() -> pd.DataFrame:
    caminho = config.DIR_PROCESSADO / "extracao_totais.csv"
    if not caminho.exists():
        return pd.DataFrame()
    totais = pd.read_csv(caminho)
    return totais.pivot_table(index="mes", columns="segmento", values="total_publicado",
                              aggfunc="first")


def cobertura(painel: pd.DataFrame, publicado: pd.DataFrame) -> pd.DataFrame:
    """direta + varejo do top-50 contra o total que o proprio informe publica."""
    if painel.empty or publicado.empty:
        return pd.DataFrame()
    somas = painel.pivot_table(index=["mes_ref", "segmento"], columns="canal",
                               values="unidades", aggfunc="sum", fill_value=0).reset_index()
    somas["total_publicado"] = [
        publicado.at[mes, segmento] if mes in publicado.index and segmento in publicado
        else float("nan") for mes, segmento in zip(somas["mes_ref"], somas["segmento"])
    ]
    somas["cobertura_pct"] = (
        100 * (somas["direta"] + somas["varejo"]) / somas["total_publicado"]).round(2)
    return somas.rename(columns={"direta": "direta_top50", "varejo": "varejo_top50"})


def participacao_e_calibracao(meses: list[str], cobertura_mensal: pd.DataFrame,
                              publicado: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A participacao publicada nos meses em texto, e o vies do top-50 contra ela."""
    linhas_part, linhas_cal = [], []
    indice = cobertura_mensal.set_index(["mes_ref", "segmento"])
    for mes in meses:
        caminho = config.DIR_CANAL / f"{mes}.pizzas.csv"
        if not caminho.exists():
            continue
        pizzas = pd.read_csv(caminho)
        if len(pizzas) != 3 or mes not in publicado.index:
            continue
        pares = [(float(p.primeiro), float(p.segundo)) for p in pizzas.itertuples()]
        totais = {s: float(publicado.at[mes, s]) for s in ("automoveis", "comerciais_leves")}

        def limites(segmento):
            linha = indice.loc[(mes, segmento)]
            total = totais[segmento]
            return (100 * linha["direta_top50"] / total,
                    100 * (1 - linha["varejo_top50"] / total))

        argumentos = (pares, totais["automoveis"], totais["comerciais_leves"],
                      limites("automoveis"), limites("comerciais_leves"))
        # A ordem das pizzas vem do layout; a aritmetica decide so' qual numero
        # e' venda direta. A busca livre fica registrada ao lado, para a escolha
        # da ordem ser visivel e conferivel mes a mes.
        solucoes = canal.atribuir_participacao(*argumentos, ordens=[canal.ORDEM_DO_LAYOUT])
        livres = canal.atribuir_participacao(*argumentos)
        base = {"mes_ref": mes, "solucoes": len(solucoes),
                "solucoes_com_ordem_livre": len(livres),
                "ordem_livre_confirma_layout": bool(livres) and all(
                    s.ordem_das_pizzas == "automoveis / comerciais_leves / combinado"
                    for s in livres),
                "pares_publicados": "; ".join(f"{a:g}/{b:g}" for a, b in pares)}
        # Resolucao POR SEGMENTO. Duas solucoes nao tornam o mes inteiro
        # ambiguo: em 2024-08 elas concordam em automoveis e em leves e so'
        # divergem no par do conjunto, que nem entra na calibracao. Um valor e'
        # determinado quando todas as solucoes concordam nele.
        determinado = {}
        for segmento, atributo in (("automoveis", "automoveis"),
                                   ("comerciais_leves", "comerciais_leves"),
                                   ("combinado", "combinado")):
            candidatos = sorted({getattr(s, atributo) for s in solucoes})
            base[f"direta_{segmento}_pct"] = candidatos[0] if len(candidatos) == 1 else ""
            base[f"resolucao_{segmento}"] = (
                "unica" if len(candidatos) == 1
                else ("sem solucao" if not candidatos
                      else "ambigua entre " + " e ".join(f"{c:g}" for c in candidatos)))
            if len(candidatos) == 1:
                determinado[segmento] = candidatos[0]
        linhas_part.append(base)

        for segmento in ("automoveis", "comerciais_leves"):
            if segmento not in determinado:
                continue
            publicada = determinado[segmento]
            linha = indice.loc[(mes, segmento)]
            direta, varejo = float(linha["direta_top50"]), float(linha["varejo_top50"])
            total = totais[segmento]
            calculada = 100 * direta / (direta + varejo)
            linhas_cal.append({
                "mes_ref": mes, "segmento": segmento,
                "direta_publicada_pct": publicada,
                "direta_calculada_pct": round(calculada, 2),
                "vies_pp": round(calculada - publicada, 2),
                "cobertura_direta_pct": round(100 * direta / (publicada / 100 * total), 2),
                "cobertura_varejo_pct": round(
                    100 * varejo / ((100 - publicada) / 100 * total), 2),
                "cobertura_total_pct": round(100 * (direta + varejo) / total, 2),
            })
    return pd.DataFrame(linhas_part), pd.DataFrame(linhas_cal)


def mesmo_valor_nos_dois_canais(painel: pd.DataFrame) -> pd.DataFrame:
    """Modelo com valor identico em venda direta e varejo no mesmo mes.

    Um modelo pode legitimamente vender nos dois canais; valor **identico** nos
    dois e' o sinal de duplicata de leitura, do mesmo tipo do 2013-11 -- ou
    coincidencia, em modelo pequeno. A funcao lista; a leitura e' humana.
    """
    if painel.empty:
        return pd.DataFrame()
    chave = ["mes_ref", "segmento", "marca", "modelo"]
    largo = painel.pivot_table(index=chave, columns="canal", values="unidades",
                               aggfunc="sum").dropna()
    if largo.empty or "direta" not in largo or "varejo" not in largo:
        return pd.DataFrame()
    iguais = largo[largo["direta"] == largo["varejo"]].reset_index()
    return iguais.rename(columns={"direta": "unidades_direta", "varejo": "unidades_varejo"})


def contra_painel_principal(painel: pd.DataFrame) -> pd.DataFrame:
    """direta + varejo contra o total do modelo na tabela de sub-segmento.

    Sao duas tabelas **independentes** do mesmo informe: o ranking por canal e a
    tabela por sub-segmento. Para todo modelo-mes que aparece nos dois canais,
    a soma tem de dar o total que o painel principal traz. E' a conferencia mais
    forte que a dimensao admite -- e e' ela que explica os modelos com valor
    identico nos dois canais: o T-Cross de 2023-12 vendeu 3.896 + 3.896 = 7.792,
    e 7.792 e' o que a tabela de sub-segmento publica.

    Modelo que so' aparece num canal nao entra: o outro canal truncou-o, e a
    soma ficaria incompleta por construcao.
    """
    if painel.empty or not config.PAINEL.exists():
        return pd.DataFrame()
    principal = pd.read_parquet(config.PAINEL, columns=[
        "mes_ref", "segmento", "marca", "modelo", "unidades"])
    total = (principal.groupby(["mes_ref", "segmento", "marca", "modelo"])["unidades"]
             .sum().rename("unidades_painel_principal"))
    largo = painel.pivot_table(index=["mes_ref", "segmento", "marca", "modelo"],
                               columns="canal", values="unidades", aggfunc="sum").dropna()
    if largo.empty or "direta" not in largo or "varejo" not in largo:
        return pd.DataFrame()
    junto = largo.join(total, how="left").reset_index()
    junto = junto.rename(columns={"direta": "unidades_direta", "varejo": "unidades_varejo"})
    junto["soma_canais"] = junto["unidades_direta"] + junto["unidades_varejo"]
    junto["diferenca"] = junto["soma_canais"] - junto["unidades_painel_principal"]
    junto["situacao"] = "sem contraparte no painel principal"
    com = junto["unidades_painel_principal"].notna()
    junto.loc[com & (junto["diferenca"] == 0), "situacao"] = "identico"
    junto.loc[com & (junto["diferenca"] != 0), "situacao"] = "diverge"
    return junto


def posicoes_com_furo(painel: pd.DataFrame) -> pd.DataFrame:
    """Posicoes que faltam na sequencia 1..n de cada ranking.

    O ranking e' contiguo por construcao da fonte. Um buraco na sequencia e'
    linha que o leitor nao conseguiu casar -- o teste mais direto de que nada
    ficou para tras.
    """
    furos = []
    for (mes, segmento, canal_), grupo in painel.groupby(["mes_ref", "segmento", "canal"]):
        vistas = set(grupo["posicao_fonte"])
        faltam = sorted(set(range(1, max(vistas) + 1)) - vistas)
        if faltam or len(grupo) != len(vistas):
            furos.append({"mes_ref": mes, "segmento": segmento, "canal": canal_,
                          "posicoes_faltando": " ".join(map(str, faltam)),
                          "posicoes_repetidas": len(grupo) - len(vistas)})
    return pd.DataFrame(furos)


def advertencia_de_nivel(cobertura_mensal: pd.DataFrame) -> str:
    """A advertencia do U, com os numeros tirados do dado -- nao escritos a' mao,
    que e' como um texto passa a mentir em silencio quando o dado muda."""
    autos = cobertura_mensal[cobertura_mensal["segmento"] == "automoveis"].dropna(
        subset=["cobertura_pct"]).copy()
    if autos.empty:
        return ""
    autos["ano"] = autos["mes_ref"].str.slice(0, 4)
    anual = autos.groupby("ano")["cobertura_pct"].median()
    fundo, topo = anual.idxmin(), anual.idxmax()
    amplitude = float(autos["cobertura_pct"].max() - autos["cobertura_pct"].min())
    return (
        "O nivel das quantidades de canal **nao e' comparavel entre anos**. Um ranking de "
        "tamanho fixo cobre menos quanto mais modelos o mercado tem, e e' isso que produz o "
        f"U: em automoveis, a parte do mes que as tabelas explicam tem mediana de "
        f"{anual[topo]:.1f}% em {topo}, cai a {anual[fundo]:.1f}% em {fundo} e volta a "
        f"{anual[anual.index > fundo].max():.1f}% depois -- amplitude de {amplitude:.1f} "
        "pontos entre o melhor e o pior mes, quase quatro vezes a deriva do painel "
        "principal. Comparacoes seguras sao **dentro do ano** -- entre modelos, entre marcas, "
        "entre canais. Qualquer serie temporal construida sobre esta dimensao tem de ser "
        "reportada **ao lado da serie de cobertura** (`saidas/canal_cobertura.csv`), nunca "
        "sozinha."
    )


def _veredito(linha) -> str:
    segmento = "automoveis" if linha["segmento"] == "automoveis" else "comerciais leves"
    if linha["estavel"]:
        return (
            f"**{segmento}: a participacao construida serve para o nivel.** Vies medio de "
            f"{linha['vies_medio_pp']:+.2f} ponto, desvio de {linha['desvio_pp']:.2f}, "
            f"estavel nos {linha['meses']} meses da amostra. E a condicao em que ela foi "
            f"medida vale na serie inteira: a cobertura do segmento fica entre "
            f"{linha['cobertura_total_min_pct']:.1f}% e {linha['cobertura_total_max_pct']:.1f}% "
            "na amostra e perto de 100% em todos os anos."
        )
    return (
        f"**{segmento}: a participacao construida NAO serve para o nivel -- so' para "
        "composicao dentro de cada canal.** O vies e' sempre do mesmo lado "
        f"({linha['meses_positivos']} de {linha['meses']} meses superestimam a venda direta), "
        f"medio de {linha['vies_medio_pp']:+.2f} ponto, mas **nao e' estavel**: anda de "
        f"{linha[f'media_{canal.MESES_DA_PONTA}_primeiros']:+.2f} nos seis primeiros meses a "
        f"{linha[f'media_{canal.MESES_DA_PONTA}_ultimos']:+.2f} nos seis ultimos. O mecanismo "
        "e' o da truncagem: a venda direta e' concentrada, e o top-50 dela capta quase tudo; "
        "o varejo e' disperso, e o top-50 dele capta menos -- e cada vez menos, conforme o "
        "mercado se fragmenta (correlacao do vies com a cobertura do varejo: "
        f"{linha['correlacao_com_cobertura_do_varejo']:+.3f}). Uma correcao unica nao vale "
        "para a serie, e uma correcao condicionada a' cobertura extrapolaria: a amostra cobre "
        f"so' {linha['cobertura_total_min_pct']:.1f}% a {linha['cobertura_total_max_pct']:.1f}% "
        "de cobertura, e o fundo do U fica abaixo disso."
    )


def escrever_dicionario(painel: pd.DataFrame, registro: list[dict], resumo: pd.DataFrame,
                        cruzamento: pd.DataFrame, cobertura_mensal: pd.DataFrame) -> None:
    lacunas = [r["mes"] for r in registro if r["situacao"] != "ok"]
    meses = sorted(painel["mes_ref"].unique()) if not painel.empty else []
    identicos = int((cruzamento.get("situacao") == "identico").sum()) if not cruzamento.empty else 0
    comparaveis = int(cruzamento["unidades_painel_principal"].notna().sum()) \
        if not cruzamento.empty else 0
    campos = [
        ("mes_ref", "texto AAAA-MM", "Mes de referencia, no formato do painel principal."),
        ("ano, mes", "inteiro", "Partes de `mes_ref`."),
        ("segmento", "texto", "`automoveis` ou `comerciais_leves`. A fonte publica um ranking "
         "por segmento, em colunas separadas da mesma pagina."),
        ("canal", "texto", "`direta` ou `varejo`. Definicao da fonte: venda direta e' o que a "
         "montadora negocia com frotista e locadora, mais taxi, produtor rural e PCD; o "
         "resto e' varejo."),
        ("marca, modelo", "texto", "Com a mesma canonizacao de caixa da chave do painel "
         "principal (D1), para a juncao ser direta."),
        ("unidades", "inteiro", "Emplacamentos do modelo no canal, no mes."),
        ("posicao_fonte", "inteiro", "Posicao no ranking da fonte, de 1 a 50."),
        ("nome_completo_fonte", "texto", "O nome como a fonte escreveu, letra por letra."),
        ("origem_tabela", "texto", "`modelo_direta_mes` ou `modelo_varejo_mes`."),
        ("arquivo_origem, pagina_origem", "texto, inteiro", "O PDF e a pagina de onde a "
         "linha saiu."),
        ("metodo_extracao", "texto", "`texto`, ou `texto_glifos` quando a fonte embutida nao "
         "tinha ToUnicode e o texto foi recuperado pela ordem padrao de glifos."),
    ]
    partes = [
        "# Dicionario de dados -- `painel_canal.parquet`\n\n",
        "Gerado por `src/etapa09_canal.py`.\n\n",
        f"- Periodo: **{meses[0]} a {meses[-1]}**\n" if meses else "",
        f"- Linhas: {len(painel):,}\n".replace(",", "."),
        "- Chave: `(mes_ref, segmento, canal, marca, modelo)`\n",
        f"- Lacunas declaradas: {', '.join(f'`{m}`' for m in lacunas) or 'nenhuma'}\n\n",
        "## Leia antes de usar\n\n",
        advertencia_de_nivel(cobertura_mensal) + "\n\n",
        "### Nivel da participacao de canal: por segmento\n\n",
        "Venda direta e varejo tem rankings de 50 **separados**, que truncam caudas "
        "**diferentes**. Entao a participacao calculada destas tabelas nao e' neutra, e o "
        "quanto ela erra foi medido contra a participacao que a fonte publica em texto nos "
        "29 meses de 2024-04 em diante (`saidas/canal_calibracao.csv`).\n\n",
    ]
    if not resumo.empty:
        for linha in resumo.to_dict("records"):
            partes.append("- " + _veredito(linha) + "\n")
        partes.append(
            f"\nCriterio de estabilidade: a media dos {canal.MESES_DA_PONTA} ultimos meses "
            f"nao pode se afastar da dos {canal.MESES_DA_PONTA} primeiros por mais de "
            f"{canal.DERIVA_MAXIMA_PP} ponto, nem por mais de metade do proprio vies.\n\n")
    partes += [
        "## O que esta dimensao e'\n\n",
        "O **topo** de cada canal: ranking de 50 posicoes por segmento. Nao e' tabela de "
        "sub-segmento -- a cauda e' bem mais rasa que a do painel principal. Um modelo-mes "
        "tem ate' duas linhas, uma por canal, e o modelo que nao entra no top-50 de um canal "
        "simplesmente nao aparece nele: **ausencia aqui nao e' zero**.\n\n",
        "Por isso e' tabela separada, nunca coluna do painel de vendas: os totais nao "
        "reconciliam com as tabelas de sub-segmento, porque sao recortes diferentes da mesma "
        "realidade.\n\n",
        "## Conferencia com o painel principal\n\n",
        f"Onde o modelo aparece nos dois canais, direta + varejo foi comparado com o total "
        f"que a tabela de sub-segmento publica: **{identicos} de {comparaveis}** "
        f"({100 * identicos / comparaveis:.2f}%) batem exatamente. Sao duas tabelas "
        "independentes da fonte reconciliando unidade a unidade.\n\n" if comparaveis else "",
        "## Colunas\n\n| coluna | tipo | descricao |\n|---|---|---|\n",
    ]
    partes += [f"| `{nome}` | {tipo} | {descricao} |\n" for nome, tipo, descricao in campos]
    partes += [
        "\n## O que ficou de fora, de proposito\n\n",
        "- **Ranking por marca**: e' grafico de barras com rotulo rotacionado e paineis "
        "sobrepostos, em percentual, nao em unidades. E e' redundante: participacao de canal "
        "por marca sai de agregar este painel, que e' texto. Numero lido do rotulo de um "
        "grafico nao se defende em artigo; numero agregado de tabela de texto, com cobertura "
        "declarada, se defende.\n",
        "- **Tabelas acumuladas no ano**: existem na fonte, mas a chave deste painel nao tem "
        "dimensao de periodo, e mistura-las criaria duas linhas para a mesma chave.\n",
    ]
    config.DICIONARIO_CANAL.parent.mkdir(parents=True, exist_ok=True)
    config.DICIONARIO_CANAL.write_text("".join(partes), encoding="utf-8")


def executar(inicio: str | None = None, fim: str | None = None, forcar: bool = False) -> int:
    logger = log.preparar(ETAPA)
    inicio = inicio or config.PERIODO_INICIO
    fim = fim or config.PERIODO_FIM
    if not config.MANIFESTO.exists():
        raise log.ErroDeParsing("manifesto ausente -- rode a etapa 01.")
    with config.MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
        manifesto = {linha["mes"]: linha for linha in csv.DictReader(fluxo)}
    dicas = _dicas()
    meses = periodo.intervalo(inicio, fim)
    config.DIR_CANAL.mkdir(parents=True, exist_ok=True)

    lidos = reaproveitados = 0
    registro = []
    for mes in meses:
        destino = config.DIR_CANAL / f"{mes}.csv"
        if mes not in manifesto:
            registro.append({"mes": mes, "situacao": "lacuna: sem informe baixado", "linhas": 0})
            continue
        if destino.exists() and not forcar:
            reaproveitados += 1
        else:
            entradas, pizzas, avisos = extrair_mes(
                mes, config.RAIZ / manifesto[mes]["arquivo_local"], dicas.get(mes, {}))
            _escrever(destino, CAMPOS_ENTRADA, entradas)
            _escrever(config.DIR_CANAL / f"{mes}.pizzas.csv", CAMPOS_PIZZA, pizzas)
            for aviso in avisos:
                logger.warning("%s: %s", mes, aviso)
            lidos += 1
            logger.info("%s: %d linhas de modelo, %d pizzas em texto",
                        mes, len(entradas), len(pizzas))
        n = sum(1 for _ in open(destino, encoding="utf-8")) - 1
        pizzas_em_texto = (config.DIR_CANAL / f"{mes}.pizzas.csv").exists() and sum(
            1 for _ in open(config.DIR_CANAL / f"{mes}.pizzas.csv", encoding="utf-8")) - 1 == 3
        registro.append({
            "mes": mes,
            # Lacuna e' lacuna (sec.9.2): o mes fica sem linha no painel e
            # registrado aqui, nunca preenchido com zero.
            "situacao": "ok" if n else "lacuna: informe sem tabela de canal",
            "linhas": n,
            "participacao_em_texto": pizzas_em_texto,
        })

    _escrever(config.CANAL_MESES, ["mes", "situacao", "linhas", "participacao_em_texto"],
              registro)
    painel = montar_painel(meses)
    painel.to_parquet(config.PAINEL_CANAL, index=False)

    publicado = _totais_publicados()
    cobertura_mensal = cobertura(painel, publicado)
    cobertura_mensal.to_csv(config.DIR_SAIDAS / "canal_cobertura.csv", index=False)
    participacao, calibracao = participacao_e_calibracao(meses, cobertura_mensal, publicado)
    participacao.to_csv(config.DIR_SAIDAS / "canal_participacao.csv", index=False)
    calibracao.to_csv(config.DIR_SAIDAS / "canal_calibracao.csv", index=False)
    cruzamento = contra_painel_principal(painel)
    cruzamento.to_csv(config.DIR_SAIDAS / "canal_contra_painel_principal.csv", index=False)
    iguais = mesmo_valor_nos_dois_canais(painel)
    if not iguais.empty and not cruzamento.empty:
        # Cada caso de valor identico ganha o veredito do cruzamento: se a soma
        # dos canais bate com o painel principal, os dois canais sao mesmo
        # iguais; se cada canal bate sozinho, uma tabela repetiu a outra.
        chave = ["mes_ref", "segmento", "marca", "modelo"]
        iguais = iguais.merge(
            cruzamento[chave + ["unidades_painel_principal", "situacao"]], on=chave, how="left")
        iguais["veredito"] = "sem contraparte no painel principal"
        com = iguais["unidades_painel_principal"].notna()
        soma_bate = com & (iguais["situacao"] == "identico")
        repete = com & ~soma_bate & (
            iguais["unidades_direta"] == iguais["unidades_painel_principal"])
        iguais.loc[soma_bate, "veredito"] = "coincidencia: direta + varejo = total do modelo"
        iguais.loc[repete, "veredito"] = "DUPLICATA: cada canal repete o total do modelo"
        iguais.loc[com & ~soma_bate & ~repete, "veredito"] = "nenhum dos dois bate"
        iguais = iguais.drop(columns=["situacao"])
    iguais.to_csv(config.DIR_SAIDAS / "canal_mesmo_valor_nos_dois_canais.csv", index=False)
    furos = posicoes_com_furo(painel)
    furos.to_csv(config.DIR_SAIDAS / "canal_posicoes_com_furo.csv", index=False)
    resumo = canal.resumo_calibracao(calibracao)
    resumo.to_csv(config.DIR_SAIDAS / "canal_calibracao_resumo.csv", index=False)
    escrever_dicionario(painel, registro, resumo, cruzamento, cobertura_mensal)

    if not painel.empty and painel.duplicated(
            ["mes_ref", "segmento", "canal", "marca", "modelo"]).any():
        repetidas = painel[painel.duplicated(
            ["mes_ref", "segmento", "canal", "marca", "modelo"], keep=False)]
        repetidas.to_csv(config.DIR_SAIDAS / "canal_chave_repetida.csv", index=False)
        logger.warning("%d linhas com chave repetida -- ver saidas/canal_chave_repetida.csv",
                       len(repetidas))

    lacunas = [r["mes"] for r in registro if r["situacao"] != "ok"]
    log.contagem(logger, meses=len(meses), lidos=lidos, reaproveitados=reaproveitados,
                 linhas=len(painel), lacunas=len(lacunas),
                 meses_com_participacao=len(participacao),
                 calibracao_automoveis=int((calibracao.get("segmento") == "automoveis").sum())
                 if not calibracao.empty else 0,
                 calibracao_leves=int((calibracao.get("segmento") == "comerciais_leves").sum())
                 if not calibracao.empty else 0,
                 posicoes_com_furo=len(furos), mesmo_valor_nos_dois_canais=len(iguais))
    if lacunas:
        logger.info("lacunas declaradas: %s", ", ".join(lacunas))
    logger.info("gravado %s", log.caminho_relativo(config.PAINEL_CANAL))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--inicio", default=config.PERIODO_INICIO)
    analisador.add_argument("--fim", default=config.PERIODO_FIM)
    analisador.add_argument("--forcar", action="store_true")
    argumentos = analisador.parse_args()
    return executar(argumentos.inicio, argumentos.fim, argumentos.forcar)


if __name__ == "__main__":
    raise SystemExit(main())
