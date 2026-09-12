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

from comum import config, informe, log, meses as mod_meses, periodo  # noqa: E402

ETAPA = "etapa02_parsing"

CAMPOS_EXTRACAO = [
    "mes", "segmento", "origem_tabela", "sub_segmento_fonte", "posicao_fonte",
    "nome_completo_fonte", "unidades_mes", "unidades_mes_anterior",
    "unidades_acumulado", "participacao_pct", "pagina", "metodo_extracao",
    "arquivo_origem",
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
CAMPOS_SUBTOTAIS = [
    "mes", "segmento", "sub_segmento_fonte", "total_publicado", "soma_modelos_listados",
    "modelos_listados", "cauda_nao_publicada", "arquivo_origem",
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


def processar_arquivo(mes: str, caminho: Path, tolerancia_total: float | None,
                      usar_ocr: bool = False):
    """Le um informe e devolve (linhas, totais, verificacoes, divergencias)."""
    extracao = informe.ler(caminho, usar_ocr=usar_ocr)
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

    if extracao.sem_segmento:
        raise log.ErroMetodologico(
            f"{caminho.name}: {len(extracao.sem_segmento)} linhas de modelo em bloco cujo "
            "segmento nao pode ser determinado -- nem o nome do sub-segmento consta de "
            "config/sub_segmentos.csv, nem o marcador de secao foi reconhecido. "
            f"Primeiros casos: {extracao.sem_segmento[:5]}"
        )
    if extracao.sub_segmentos_novos:
        registrar("sub_segmento_novo", mes, None, None, "revisar",
                  "; ".join(extracao.sub_segmentos_novos[:5]))
    if extracao.divergencias_de_secao:
        # O nome do sub-segmento venceu o marcador da secao. Em Abr-Jun/2020 e'
        # o que impede o mes inteiro de automoveis virar comerciais leves.
        registrar("marcador_de_secao", mes, None, None, "corrigido_pelo_sub_segmento",
                  f"{len(extracao.divergencias_de_secao)} blocos; "
                  + extracao.divergencias_de_secao[0])

    if not extracao.modelos and not extracao.ranking:
        # Extracao de texto falhou: candidato a OCR (sec.8). Nao inventar nada.
        registrar("extracao_de_texto", mes, None, None, "falhou",
                  f"paginas={extracao.paginas} sem_texto={len(extracao.paginas_sem_texto)}")
        return [], [], [], verificacoes, divergencias, extracao

    # 2. subtotais publicados por sub-segmento
    soma_sub: dict[tuple[str, str], float] = defaultdict(float)
    for modelo in extracao.modelos:
        soma_sub[(modelo.segmento, modelo.sub_segmento_fonte)] += modelo.unidades_mes
    for chave, publicado in sorted(extracao.subtotal_publicado.items()):
        obtido = soma_sub.get(chave, 0.0)
        escopo = f"{chave[0]}/{chave[1]}"
        if not publicado:
            registrar("subtotal_sub_segmento", escopo, publicado, obtido, "sem_total")
            continue
        # O 'Total' que a fonte publica e' o total verdadeiro do sub-segmento; a
        # lista de modelos acima dele tem numero fixo de linhas e trunca a cauda.
        # Logo a soma lida so' pode ser MENOR ou igual. Maior significa que a
        # leitura pegou linha que nao pertence ali -- isso sim e' erro de parsing.
        if obtido > publicado * (1 + config.TOLERANCIA_PARSING):
            raise log.ErroDeParsing(
                f"{caminho.name}: a soma dos modelos lidos em '{escopo}' "
                f"({obtido:.0f}) excede o total que a fonte publica ({publicado:.0f}). "
                "A leitura pegou linha que nao pertence ao sub-segmento (sec.4)."
            )
        cauda = publicado - obtido
        registrar("subtotal_sub_segmento", escopo, publicado, obtido,
                  "ok" if cauda <= publicado * config.TOLERANCIA_PARSING else "cauda_truncada",
                  f"cauda nao publicada: {cauda:.0f} unidades")

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
            "pagina": modelo.pagina, "metodo_extracao": modelo.metodo_extracao,
            "arquivo_origem": caminho.name,
        })

    conferidos = divergentes = 0
    volume_conferido = desvio_absoluto = 0.0
    for item in extracao.ranking:
        chave = (item.segmento, item.nome_completo_fonte)
        if chave in por_nome:
            conferidos += 1
            volume_conferido += item.unidades_mes
            desvio_absoluto += abs(por_nome[chave] - item.unidades_mes)
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
            "metodo_extracao": item.metodo_extracao, "arquivo_origem": caminho.name,
        })
        por_nome[chave] = item.unidades_mes

    if conferidos and volume_conferido:
        # A tolerancia da sec.4 e' de *magnitude*: 0,5% do volume conferido.
        # Um punhado de unidades de diferenca num modelo e' inconsistencia da
        # fonte (reportada, mantida -- sec.9.4); leitura de coluna errada
        # deslocaria o volume inteiro e cai aqui.
        desvio = desvio_absoluto / volume_conferido
        situacao = "ok" if desvio <= config.TOLERANCIA_PARSING else "acima_da_tolerancia"
        registrar("ranking_x_sub_segmento", mes, volume_conferido,
                  volume_conferido - desvio_absoluto, situacao,
                  f"{divergentes} modelos divergentes de {conferidos} conferidos; "
                  f"desvio de volume {100 * desvio:.4f}%")
        if situacao != "ok":
            raise log.ErroDeParsing(
                f"{caminho.name}: o ranking e a tabela de sub-segmento divergem em "
                f"{desvio_absoluto:.0f} de {volume_conferido:.0f} unidades conferidas "
                f"({100 * desvio:.2f}% > {100 * config.TOLERANCIA_PARSING:.2f}%), "
                f"em {divergentes} de {conferidos} modelos. Erro de parsing (sec.4)."
            )

    subtotais: list[dict] = []
    for chave, publicado in sorted(extracao.subtotal_publicado.items()):
        segmento, sub = chave
        obtido = soma_sub.get(chave, 0.0)
        subtotais.append({
            "mes": mes, "segmento": segmento, "sub_segmento_fonte": sub,
            "total_publicado": f"{publicado:.0f}", "soma_modelos_listados": f"{obtido:.0f}",
            "modelos_listados": sum(
                1 for m in extracao.modelos
                if m.segmento == segmento and m.sub_segmento_fonte == sub
            ),
            "cauda_nao_publicada": f"{publicado - obtido:.0f}",
            "arquivo_origem": caminho.name,
        })

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

    return linhas, totais, subtotais, verificacoes, divergencias, extracao


def _agregar(subdir: str, campos: list[str]) -> list[dict]:
    """Junta os arquivos por mes de um subdiretorio, na ordem cronologica."""
    pasta = config.DIR_PROCESSADO / subdir
    linhas: list[dict] = []
    for caminho in sorted(pasta.glob("*.csv")):
        with caminho.open(encoding="utf-8", newline="") as fluxo:
            linhas.extend(csv.DictReader(fluxo))
    return [{campo: linha.get(campo, "") for campo in campos} for linha in linhas]


def executar(inicio: str, fim: str, tolerancia_total: float | None = None,
             forcar: bool = False, usar_ocr: bool = False) -> int:
    logger = log.preparar(ETAPA)
    manifesto = _ler_manifesto()
    pedidos = periodo.intervalo(inicio, fim)
    meses = [m for m in pedidos if m in manifesto]
    ausentes = [m for m in pedidos if m not in manifesto]
    if ausentes:
        logger.warning("%d meses sem informe baixado (ver lacunas.csv): %s",
                       len(ausentes), ", ".join(ausentes[:12]))

    # Cada mes grava os proprios arquivos. Assim um mes reaproveitado continua
    # entrando nos agregados, e a etapa segue idempotente (sec.1.3).
    pastas = {
        "extracao": CAMPOS_EXTRACAO,
        "totais": CAMPOS_TOTAIS,
        "subtotais": CAMPOS_SUBTOTAIS,
        "verificacao": CAMPOS_VERIFICACAO,
        "divergencias": CAMPOS_DIVERGENCIA,
    }
    for nome in pastas:
        (config.DIR_PROCESSADO / nome).mkdir(parents=True, exist_ok=True)

    paginas_lidas = processados = reaproveitados = 0

    for mes in meses:
        caminho = config.RAIZ / manifesto[mes]["arquivo_local"]
        destino = config.DIR_EXTRACAO / f"{mes}.csv"
        if destino.exists() and not forcar:
            reaproveitados += 1
            continue
        try:
            linhas, totais, subtotais, verificacoes, divergencias, extracao = processar_arquivo(
                mes, caminho, tolerancia_total, usar_ocr
            )
        except log.ErroDeParsing as erro:
            logger.error("%s", erro)
            raise
        paginas_lidas += extracao.paginas
        if extracao.paginas_com_cid:
            logger.info("%s: %d paginas com fonte sem ToUnicode, texto recuperado",
                        mes, len(extracao.paginas_com_cid))
        for aviso in extracao.avisos:
            logger.warning("%s: %s", mes, aviso)
        if not linhas:
            logger.error("%s: nenhuma linha de modelo extraida", mes)
        _escrever(destino, CAMPOS_EXTRACAO, linhas)
        _escrever(config.DIR_PROCESSADO / "totais" / f"{mes}.csv", CAMPOS_TOTAIS, totais)
        _escrever(config.DIR_PROCESSADO / "subtotais" / f"{mes}.csv", CAMPOS_SUBTOTAIS, subtotais)
        _escrever(config.DIR_PROCESSADO / "verificacao" / f"{mes}.csv", CAMPOS_VERIFICACAO,
                  verificacoes)
        _escrever(config.DIR_PROCESSADO / "divergencias" / f"{mes}.csv", CAMPOS_DIVERGENCIA,
                  divergencias)
        processados += 1
        logger.info("%s: %d linhas, %d paginas", mes, len(linhas), extracao.paginas)

    # Registro de quais meses tem dado utilizavel: e' o que separa zero de
    # lacuna nas etapas seguintes.
    registro = []
    sem_texto: list[dict] = []
    com_cid: list[dict] = []
    com_ocr: list[dict] = []
    for mes in meses:
        caminho_extracao = config.DIR_EXTRACAO / f"{mes}.csv"
        with caminho_extracao.open(encoding="utf-8", newline="") as fluxo:
            linhas_mes = list(csv.DictReader(fluxo))
        metodos = [l.get("metodo_extracao", "") for l in linhas_mes]
        arquivo = Path(manifesto[mes]["arquivo_local"]).name
        registro.append({
            "mes": mes, "linhas": len(linhas_mes),
            "situacao": "ok" if linhas_mes else "sem_linha_extraida",
            "metodo_predominante": max(set(metodos), key=metodos.count) if metodos else "",
            "arquivo_origem": manifesto[mes]["arquivo_local"],
        })
        if not linhas_mes:
            sem_texto.append({
                "mes": mes, "arquivo": arquivo,
                "motivo": "pdfplumber nao extraiu tabela de modelos; candidato a OCR (sec.8)",
            })
        if "texto_glifos" in metodos:
            com_cid.append({
                "mes": mes, "arquivo": arquivo,
                "linhas_recuperadas": metodos.count("texto_glifos"),
                "tratamento": "fonte sem ToUnicode; traducao pela ordem padrao de "
                              "glifos TrueType (sem OCR)",
            })
        if "ocr" in metodos:
            com_ocr.append({
                "mes": mes, "arquivo": arquivo, "linhas_por_ocr": metodos.count("ocr"),
                "aviso": "linhas reconhecidas por OCR; conferir antes de usar",
            })
    mod_meses.registrar(registro)

    agregados = {nome: _agregar(nome, campos) for nome, campos in pastas.items()
                 if nome != "extracao"}
    _escrever(config.DIR_PROCESSADO / "extracao_totais.csv", CAMPOS_TOTAIS, agregados["totais"])
    _escrever(config.DIR_PROCESSADO / "extracao_subtotais.csv", CAMPOS_SUBTOTAIS,
              agregados["subtotais"])
    _escrever(config.DIR_PROCESSADO / "extracao_verificacao.csv", CAMPOS_VERIFICACAO,
              agregados["verificacao"])
    _escrever(config.DIR_SAIDAS / "divergencias_fonte.csv", CAMPOS_DIVERGENCIA,
              agregados["divergencias"])
    _escrever(config.DIR_SAIDAS / "arquivos_sem_texto.csv",
              ["mes", "arquivo", "motivo"], sem_texto)
    _escrever(config.DIR_SAIDAS / "arquivos_com_fonte_sem_tounicode.csv",
              ["mes", "arquivo", "linhas_recuperadas", "tratamento"], com_cid)
    _escrever(config.DIR_SAIDAS / "arquivos_com_ocr.csv",
              ["mes", "arquivo", "linhas_por_ocr", "aviso"], com_ocr)

    linhas_extraidas = sum(
        1 for _ in _agregar("extracao", CAMPOS_EXTRACAO)
    )
    log.contagem(logger, meses=len(meses), processados=processados,
                 reaproveitados=reaproveitados, paginas_lidas=paginas_lidas,
                 linhas_extraidas=linhas_extraidas,
                 divergencias_fonte=len(agregados["divergencias"]),
                 sem_texto=len(sem_texto), fonte_sem_tounicode=len(com_cid),
                 com_ocr=len(com_ocr))
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
    analisador.add_argument("--ocr", action="store_true",
                            help="ultimo recurso (sec.8): reconhece por OCR as paginas sem "
                                 "texto extraivel. As linhas ficam marcadas com "
                                 "metodo_extracao=ocr ate o painel bruto.")
    analisador.add_argument("--tolerancia-total", type=float, default=None,
                            help="aplica a leitura literal da sec.4 ao total do informe "
                                 "(ex.: 0.005); por padrao o desvio e' medido como cobertura")
    args = analisador.parse_args()
    return executar(args.inicio, args.fim, args.tolerancia_total, args.forcar, args.ocr)


if __name__ == "__main__":
    raise SystemExit(main())
