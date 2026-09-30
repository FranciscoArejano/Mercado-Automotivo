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
        if len(solucoes) != 1:
            linhas_part.append({**base, "resolucao": "ambigua" if solucoes else "sem solucao"})
            continue
        solucao = solucoes[0]
        linhas_part.append({
            **base, "resolucao": "unica",
            "direta_automoveis_pct": solucao.automoveis,
            "direta_comerciais_leves_pct": solucao.comerciais_leves,
            "direta_combinado_pct": solucao.combinado,
            "ordem_das_pizzas": solucao.ordem_das_pizzas,
            "direta_em_primeiro": solucao.direta_em_primeiro,
        })
        for segmento, publicada in (("automoveis", solucao.automoveis),
                                    ("comerciais_leves", solucao.comerciais_leves)):
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
    iguais = mesmo_valor_nos_dois_canais(painel)
    iguais.to_csv(config.DIR_SAIDAS / "canal_mesmo_valor_nos_dois_canais.csv", index=False)
    furos = posicoes_com_furo(painel)
    furos.to_csv(config.DIR_SAIDAS / "canal_posicoes_com_furo.csv", index=False)

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
                 meses_com_participacao=int((participacao.get("resolucao") == "unica").sum())
                 if not participacao.empty else 0,
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
