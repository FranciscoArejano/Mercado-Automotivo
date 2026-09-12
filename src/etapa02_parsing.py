#!/usr/bin/env python3
"""Etapa 2 -- parsing dos informes (ESPEC.md sec.4).

Para cada informe baixado, extrai as tabelas por modelo e roda as conferencias
que o proprio documento permite:

1. *Mes declarado*  -- o titulo do PDF ("Resumo Mensal Agosto de 2026") tem de
   bater com o mes que o catalogo da fonte atribuiu ao arquivo. Divergencia e'
   erro de atribuicao de mes e para a execucao (sec.6, sec.7 item 1).
2. *Subtotais*      -- no layout antigo a fonte publica um 'Total' ao pe' de
   cada sub-segmento. A soma dos modelos listados tem de bater com ele dentro
   de 0,5% (sec.4).
3. *Ranking*        -- todo modelo do top-50 mensal que tambem aparece nas
   tabelas de sub-segmento tem de trazer o mesmo numero. Esta e' a conferencia
   que pega leitura de coluna errada.

O confronto entre a soma do painel e o total publicado no informe **nao** e'
tratado aqui como erro de parsing: as tabelas por modelo da fonte sao listas
truncadas (numero fixo de linhas por sub-segmento), entao a diferenca e'
estrutural, nao de leitura. Ela e' medida e entregue como cobertura (D5).
Ver QUESTOES_ABERTAS.md, Q2. Quem quiser a leitura literal da sec.4 usa
--tolerancia-total.

Uso:
    python src/etapa02_parsing.py [--inicio AAAA-MM] [--fim AAAA-MM] [--forcar]
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, informe, log, periodo  # noqa: E402

ETAPA = "etapa02_parsing"

CAMPOS_EXTRACAO = [
    "mes", "segmento", "origem_tabela", "sub_segmento_fonte", "posicao_fonte",
    "nome_completo_fonte", "unidades_mes", "unidades_mes_anterior",
    "unidades_acumulado", "participacao_pct", "pagina", "arquivo_origem",
]
CAMPOS_TOTAIS = ["mes", "segmento", "total_publicado", "arquivo_origem", "edicao"]
CAMPOS_VERIFICACAO = [
    "mes", "verificacao", "escopo", "esperado", "obtido", "diferenca",
    "diferenca_pct", "situacao", "detalhe",
]
CAMPOS_DIVERGENCIA = [
    "mes", "segmento", "nome_completo_fonte", "valor_ranking",
    "valor_sub_segmento", "diferenca", "arquivo_origem",
]


def _escrever(caminho: Path, campos: list[str], linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=campos)
        escritor.writeheader()
        for linha in linhas:
            escritor.writerow({campo: linha.get(campo, "") for campo in campos})


def _ler_manifesto() -> dict[str, dict]:
    if not config.MANIFESTO.exists():
        raise log.ErroDeParsing(
            f"{log.caminho_relativo(config.MANIFESTO)} nao existe -- rode a etapa 01 antes."
        )
    with config.MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
        return {linha["mes"]: linha for linha in csv.DictReader(fluxo)}


def processar_arquivo(mes: str, caminho: Path, tolerancia_total: float | None):
    """Le um informe e devolve (linhas, totais, verificacoes, divergencias)."""
    extracao = informe.ler(caminho)
    verificacoes: list[dict] = []
    divergencias: list[dict] = []

    def registrar(nome, escopo, esperado, obtido, situacao, detalhe=""):
        diferenca = None if esperado is None or obtido is None else obtido - esperado
        pct = (
            "" if not diferenca or not esperado else f"{100.0 * diferenca / esperado:.4f}"
        )
        verificacoes.append({
            "mes": mes, "verificacao": nome, "escopo": escopo,
            "esperado": "" if esperado is None else f"{esperado:.0f}",
            "obtido": "" if obtido is None else f"{obtido:.0f}",
            "diferenca": "" if diferenca is None else f"{diferenca:.0f}",
            "diferenca_pct": pct, "situacao": situacao, "detalhe": detalhe,
        })

    # 1. mes declarado no PDF x mes atribuido pelo catalogo da fonte
    if extracao.mes_declarado is None:
        registrar("mes_declarado", mes, None, None, "indeterminado",
                  "titulo 'Resumo Mensal' nao encontrado")
    elif extracao.mes_declarado != mes:
        raise log.ErroDeParsing(
            f"{caminho.name}: catalogo atribui {mes} mas o informe se declara "
            f"{extracao.mes_declarado}. Atribuicao de mes errada -- parar (sec.6)."
        )
    else:
        registrar("mes_declarado", mes, None, None, "ok", extracao.mes_declarado)

    if not extracao.modelos and not extracao.ranking:
        # Extracao de texto falhou: candidato a OCR (sec.8). Nao inventar nada.
        registrar("extracao_de_texto", mes, None, None, "falhou",
                  f"paginas={extracao.paginas} sem_texto={len(extracao.paginas_sem_texto)}")
        return [], [], verificacoes, divergencias, extracao

    # 2. subtotais publicados por sub-segmento
    soma_sub: dict[tuple[str, str], float] = defaultdict(float)
    for modelo in extracao.modelos:
        soma_sub[(modelo.segmento, modelo.sub_segmento_fonte)] += modelo.unidades_mes
    for chave, publicado in sorted(extracao.subtotal_publicado.items()):
        obtido = soma_sub.get(chave, 0.0)
        escopo = f"{chave[0]}/{chave[1]}"
        if publicado and abs(obtido - publicado) / publicado > config.TOLERANCIA_PARSING:
            raise log.ErroDeParsing(
                f"{caminho.name}: subtotal de '{escopo}' publicado={publicado:.0f} "
                f"mas a soma dos modelos lidos={obtido:.0f} "
                f"({100 * (obtido - publicado) / publicado:+.2f}%). Erro de parsing (sec.4)."
            )
        registrar("subtotal_sub_segmento", escopo, publicado, obtido, "ok")

    # 3. ranking x tabelas de sub-segmento
    por_nome: dict[tuple[str, str], float] = defaultdict(float)
    for modelo in extracao.modelos:
        por_nome[(modelo.segmento, modelo.nome_completo_fonte)] += modelo.unidades_mes

    linhas: list[dict] = []
    for modelo in extracao.modelos:
        linhas.append({
            "mes": mes, "segmento": modelo.segmento, "origem_tabela": "sub_segmento",
            "sub_segmento_fonte": modelo.sub_segmento_fonte,
            "posicao_fonte": modelo.posicao_fonte,
            "nome_completo_fonte": modelo.nome_completo_fonte,
            "unidades_mes": f"{modelo.unidades_mes:.0f}",
            "unidades_mes_anterior": f"{modelo.unidades_mes_anterior:.0f}",
            "unidades_acumulado": f"{modelo.unidades_acumulado:.0f}",
            "participacao_pct": f"{modelo.participacao_pct:.2f}",
            "pagina": modelo.pagina, "arquivo_origem": caminho.name,
        })

    conferidos = divergentes = 0
    for item in extracao.ranking:
        chave = (item.segmento, item.nome_completo_fonte)
        if chave in por_nome:
            conferidos += 1
            if abs(por_nome[chave] - item.unidades_mes) > 0.5:
                divergentes += 1
                divergencias.append({
                    "mes": mes, "segmento": item.segmento,
                    "nome_completo_fonte": item.nome_completo_fonte,
                    "valor_ranking": f"{item.unidades_mes:.0f}",
                    "valor_sub_segmento": f"{por_nome[chave]:.0f}",
                    "diferenca": f"{item.unidades_mes - por_nome[chave]:.0f}",
                    "arquivo_origem": caminho.name,
                })
            continue
        # Modelo que o ranking publica e a tabela de sub-segmento truncou.
        linhas.append({
            "mes": mes, "segmento": item.segmento, "origem_tabela": "ranking",
            "sub_segmento_fonte": "", "posicao_fonte": item.posicao_fonte,
            "nome_completo_fonte": item.nome_completo_fonte,
            "unidades_mes": f"{item.unidades_mes:.0f}",
            "unidades_mes_anterior": "", "unidades_acumulado": "",
            "participacao_pct": "", "pagina": item.pagina,
            "arquivo_origem": caminho.name,
        })
        por_nome[chave] = item.unidades_mes

    if conferidos:
        fracao = divergentes / conferidos
        situacao = "ok" if fracao <= config.TOLERANCIA_PARSING else "acima_da_tolerancia"
        registrar("ranking_x_sub_segmento", mes, conferidos, conferidos - divergentes,
                  situacao, f"{divergentes} modelos divergentes de {conferidos} conferidos")
        if situacao != "ok":
            raise log.ErroDeParsing(
                f"{caminho.name}: {divergentes} de {conferidos} modelos do ranking "
                f"divergem da tabela de sub-segmento. Erro de parsing (sec.4)."
            )

    # 4. cobertura: soma do painel x total publicado (D5, nao e' erro de parsing)
    totais: list[dict] = []
    for segmento in config.SEGMENTOS:
        publicado = extracao.total_publicado.get(segmento)
        totais.append({
            "mes": mes, "segmento": segmento,
            "total_publicado": "" if publicado is None else f"{publicado:.0f}",
            "arquivo_origem": caminho.name, "edicao": extracao.edicao or "",
        })
        obtido = sum(
            float(linha["unidades_mes"]) for linha in linhas if linha["segmento"] == segmento
        )
        if publicado:
            desvio = abs(obtido - publicado) / publicado
            registrar("cobertura", segmento, publicado, obtido,
                      "medido", f"cobertura={100 * obtido / publicado:.2f}%")
            if tolerancia_total is not None and desvio > tolerancia_total:
                raise log.ErroDeParsing(
                    f"{caminho.name}: {segmento} soma={obtido:.0f} x publicado={publicado:.0f} "
                    f"({100 * desvio:.2f}% > {100 * tolerancia_total:.2f}%). "
                    "Leitura literal da sec.4 exigida por --tolerancia-total."
                )
        else:
            registrar("cobertura", segmento, None, obtido, "sem_total_publicado")

    return linhas, totais, verificacoes, divergencias, extracao


def executar(inicio: str, fim: str, tolerancia_total: float | None, forcar: bool) -> int:
    logger = log.preparar(ETAPA)
    manifesto = _ler_manifesto()
    meses = [m for m in periodo.intervalo(inicio, fim) if m in manifesto]
    ausentes = [m for m in periodo.intervalo(inicio, fim) if m not in manifesto]
    if ausentes:
        logger.warning("%d meses sem informe baixado (ver lacunas.csv): %s",
                       len(ausentes), ", ".join(ausentes[:12]))

    config.DIR_EXTRACAO.mkdir(parents=True, exist_ok=True)
    todos_totais: list[dict] = []
    todas_verificacoes: list[dict] = []
    todas_divergencias: list[dict] = []
    sem_texto: list[dict] = []
    lidas = escritas = 0

    for mes in meses:
        caminho = config.RAIZ / manifesto[mes]["arquivo_local"]
        destino = config.DIR_EXTRACAO / f"{mes}.csv"
        if destino.exists() and not forcar:
            with destino.open(encoding="utf-8", newline="") as fluxo:
                existentes = list(csv.DictReader(fluxo))
            escritas += len(existentes)
            logger.info("%s: extracao ja' existe (%d linhas), reaproveitada", mes, len(existentes))
            continue
        try:
            linhas, totais, verificacoes, divergencias, extracao = processar_arquivo(
                mes, caminho, tolerancia_total
            )
        except log.ErroDeParsing as erro:
            logger.error("%s", erro)
            raise
        lidas += extracao.paginas
        for aviso in extracao.avisos:
            logger.warning("%s: %s", mes, aviso)
        if not linhas:
            sem_texto.append({
                "mes": mes, "arquivo": caminho.name, "paginas": extracao.paginas,
                "paginas_sem_texto": len(extracao.paginas_sem_texto),
                "motivo": "pdfplumber nao extraiu tabela de modelos; candidato a OCR (sec.8)",
            })
            logger.error("%s: nenhuma linha de modelo extraida", mes)
        _escrever(destino, CAMPOS_EXTRACAO, linhas)
        escritas += len(linhas)
        todos_totais.extend(totais)
        todas_verificacoes.extend(verificacoes)
        todas_divergencias.extend(divergencias)
        logger.info("%s: %d linhas, %d paginas", mes, len(linhas), extracao.paginas)

    _escrever(config.DIR_PROCESSADO / "extracao_totais.csv", CAMPOS_TOTAIS, todos_totais)
    _escrever(config.DIR_PROCESSADO / "extracao_verificacao.csv", CAMPOS_VERIFICACAO,
              todas_verificacoes)
    _escrever(config.DIR_SAIDAS / "divergencias_fonte.csv", CAMPOS_DIVERGENCIA,
              todas_divergencias)
    _escrever(config.DIR_SAIDAS / "arquivos_sem_texto.csv",
              ["mes", "arquivo", "paginas", "paginas_sem_texto", "motivo"], sem_texto)

    log.contagem(logger, meses=len(meses), paginas_lidas=lidas, linhas_escritas=escritas,
                 divergencias_fonte=len(todas_divergencias), sem_texto=len(sem_texto))
    if sem_texto:
        logger.warning("%d informes precisam de OCR -- ver saidas/arquivos_sem_texto.csv",
                       len(sem_texto))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--inicio", default=config.PERIODO_INICIO)
    analisador.add_argument("--fim", default=config.PERIODO_FIM)
    analisador.add_argument("--forcar", action="store_true",
                            help="reprocessa meses cuja extracao ja' existe")
    analisador.add_argument("--tolerancia-total", type=float, default=None,
                            help="aplica a leitura literal da sec.4 ao total do informe "
                                 "(ex.: 0.005); por padrao o desvio e' medido como cobertura")
    args = analisador.parse_args()
    return executar(args.inicio, args.fim, args.tolerancia_total, args.forcar)


if __name__ == "__main__":
    raise SystemExit(main())
