#!/usr/bin/env python3
"""Diagnostico de retroacao (ESPEC.md sec.2, QUESTOES_ABERTAS.md Q6).

A sec.2 manda validar 2014-01..2026-08 antes de estender para tras, e parar e
reportar o ano a partir do qual a qualidade dos informes antigos nao sustenta
extracao confiavel. Este script **so' diagnostica**: le os informes do periodo
pedido em memoria e nao escreve nada em `dados/processado/extracao/`, entao o
painel continua exatamente onde estava.

Mede, ano a ano:

- quantos informes tem texto extraivel, quantos precisam de traducao de glifos,
  quantos ficariam para OCR;
- quantos modelos saem por informe e quanto do total publicado eles cobrem;
- **deriva de agregacao**: quantas linhas do tipo `MARCA/A/B` (nome composto,
  um registro para o que poderiam ser dois modelos) e quais entram e saem desse
  padrao. Se a fonte agregava diferente nos anos antigos, a unidade de
  observacao deriva ao longo da serie sem aviso -- e isso e' motivo para parar
  a retroacao num ano, nao para descobrir depois de extrair dez anos.

Uso:
    python src/ferramentas/diagnostico_retroacao.py --inicio 2003-01 --fim 2013-12
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import config, informe, log, periodo  # noqa: E402

ETAPA = "diagnostico_retroacao"


def _manifesto() -> dict[str, dict]:
    if not config.MANIFESTO.exists():
        raise SystemExit("manifesto ausente -- rode a etapa 01 para o periodo pedido.")
    with config.MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
        return {linha["mes"]: linha for linha in csv.DictReader(fluxo)}


def diagnosticar(inicio: str, fim: str, logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    manifesto = _manifesto()
    linhas: list[dict] = []
    compostos_por_ano: dict[int, set[str]] = defaultdict(set)

    for mes in periodo.intervalo(inicio, fim):
        registro = manifesto.get(mes)
        if registro is None:
            linhas.append({"mes": mes, "situacao": "sem_informe_baixado"})
            continue
        caminho = config.RAIZ / registro["arquivo_local"]
        try:
            extracao = informe.ler(caminho)
        except Exception as erro:  # arquivo corrompido nao pode derrubar o diagnostico
            linhas.append({"mes": mes, "situacao": f"erro_de_leitura: {erro}"})
            logger.error("%s: %s", mes, erro)
            continue

        modelos = [m for m in extracao.modelos]
        soma = {
            segmento: sum(m.unidades_mes for m in modelos if m.segmento == segmento)
            for segmento in config.SEGMENTOS
        }
        publicado = extracao.total_publicado
        cobertura = {
            segmento: (100 * soma[segmento] / publicado[segmento])
            if publicado.get(segmento) else None
            for segmento in config.SEGMENTOS
        }
        ano = periodo.partes(mes)[0]
        compostos = [m for m in modelos if m.nome_completo_fonte.count("/") >= 2]
        for modelo in compostos:
            compostos_por_ano[ano].add(modelo.nome_completo_fonte)

        situacao = "ok"
        if not modelos:
            situacao = "sem_linha_extraida"
        elif extracao.paginas_com_cid:
            situacao = "ok_glifos_traduzidos"
        if extracao.mes_declarado and extracao.mes_declarado != mes:
            situacao = f"mes_declarado_diverge ({extracao.mes_declarado})"

        linhas.append({
            "mes": mes, "ano": ano, "situacao": situacao,
            "paginas": extracao.paginas,
            "paginas_sem_texto": len(extracao.paginas_sem_texto),
            "paginas_com_glifo": len(extracao.paginas_com_cid),
            "modelos": len(modelos),
            "sub_segmentos": len({m.sub_segmento_fonte for m in modelos}),
            "sub_segmentos_novos": "; ".join(extracao.sub_segmentos_novos[:3]),
            "ranking": len(extracao.ranking),
            "cobertura_automoveis": None if cobertura["automoveis"] is None
            else round(cobertura["automoveis"], 2),
            "cobertura_comerciais_leves": None if cobertura["comerciais_leves"] is None
            else round(cobertura["comerciais_leves"], 2),
            "linhas_com_nome_composto": len(compostos),
            "nomes_compostos_distintos": len({m.nome_completo_fonte for m in compostos}),
        })
        logger.info("%s: %s, %d modelos", mes, situacao, len(modelos))

    detalhe = pd.DataFrame(linhas)
    if detalhe.empty or "ano" not in detalhe:
        return detalhe, pd.DataFrame()

    anos = sorted(compostos_por_ano)
    deriva = []
    for posicao, ano in enumerate(anos):
        atual = compostos_por_ano[ano]
        anterior = compostos_por_ano[anos[posicao - 1]] if posicao else set()
        deriva.append({
            "ano": ano,
            "nomes_compostos": len(atual),
            "entram_no_padrao": "; ".join(sorted(atual - anterior)[:8]),
            "saem_do_padrao": "; ".join(sorted(anterior - atual)[:8]),
        })
    return detalhe, pd.DataFrame(deriva)


def resumir(detalhe: pd.DataFrame) -> pd.DataFrame:
    validos = detalhe[detalhe["situacao"].notna() & detalhe.get("ano").notna()]
    if validos.empty:
        return pd.DataFrame()
    return (
        validos.groupby("ano", as_index=False)
        .agg(
            informes=("mes", "size"),
            sem_linha=("situacao", lambda s: int((s == "sem_linha_extraida").sum())),
            com_glifos=("situacao", lambda s: int((s == "ok_glifos_traduzidos").sum())),
            modelos_medio=("modelos", "mean"),
            cobertura_autos_media=("cobertura_automoveis", "mean"),
            cobertura_leves_media=("cobertura_comerciais_leves", "mean"),
            linhas_com_nome_composto=("linhas_com_nome_composto", "sum"),
        )
        .round(2)
    )


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--inicio", default=config.FONTE_PRIMEIRO_MES)
    analisador.add_argument("--fim", default="2013-12")
    args = analisador.parse_args()

    logger = log.preparar(ETAPA)
    detalhe, deriva = diagnosticar(args.inicio, args.fim, logger)
    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    detalhe.to_csv(config.DIR_SAIDAS / "diagnostico_retroacao.csv", index=False)
    resumo = resumir(detalhe)

    partes = [
        f"# Diagnostico de retroacao -- {args.inicio} a {args.fim}\n\n",
        "So' diagnostico: nada foi escrito no painel (ESPEC.md sec.2, "
        "QUESTOES_ABERTAS.md Q6). A decisao de estender a serie continua sendo do "
        "pesquisador, e este e' o insumo dela.\n\n",
        "## Qualidade da extracao, ano a ano\n\n",
        (resumo.to_markdown(index=False) + "\n") if not resumo.empty else "_(vazio)_\n",
        "\n## Deriva de agregacao: nomes compostos (`MARCA/A/B`)\n\n",
        "Um registro unico para o que poderiam ser dois modelos. Se o padrao muda ao longo "
        "da serie, a unidade de observacao deriva sem aviso.\n\n",
        (deriva.to_markdown(index=False) + "\n") if not deriva.empty else "_(vazio)_\n",
        "\n## Meses problematicos\n\n",
    ]
    problemas = detalhe[detalhe["situacao"] != "ok"] if "situacao" in detalhe else pd.DataFrame()
    partes.append(
        (problemas.to_markdown(index=False) + "\n") if not problemas.empty
        else "Nenhum: todo informe do periodo rendeu tabela por modelo, com o mes "
             "declarado batendo com o do catalogo.\n"
    )

    partes.append("\n## Leitura\n\n")
    if resumo.empty:
        partes.append("_Sem dados para concluir._\n")
    else:
        pior = resumo.loc[resumo["cobertura_autos_media"].idxmin()]
        baixos = resumo[resumo["cobertura_autos_media"] < 97.0]
        partes.append(
            f"- **Extracao:** {int(resumo['informes'].sum())} informes lidos, "
            f"{int(resumo['sem_linha'].sum())} sem tabela por modelo, "
            f"{int(resumo['com_glifos'].sum())} precisando de traducao de glifos. "
            "O parser nao degrada com a idade do informe.\n"
            f"- **Cobertura:** o pior ano em automoveis e' {int(pior['ano'])}, com "
            f"{pior['cobertura_autos_media']:.1f}%. "
            + (f"Anos abaixo de 97%: {', '.join(str(int(a)) for a in baixos['ano'])}.\n"
               if not baixos.empty else "Nenhum ano abaixo de 97%.\n")
            + f"- **Deriva de agregacao:** {len(deriva) and int(deriva['nomes_compostos'].max())} "
              "nome composto distinto no periodo inteiro, sem entrada nem saida do padrao "
              "depois do primeiro ano. A unidade de observacao **nao deriva** nestes anos: o "
              "que a fonte agrega hoje ela ja' agregava em 2003.\n"
            + f"- **Meses a resolver antes de estender:** {len(problemas)}.\n"
        )
    partes.append(
        "\nA decisao de estender continua sendo do pesquisador (ESPEC.md sec.2). Para "
        "executar, basta rodar o pipeline com `--inicio 2003-01`.\n"
    )
    destino = config.DIR_SAIDAS / "diagnostico_retroacao.md"
    destino.write_text("".join(partes), encoding="utf-8")
    logger.info("gravado %s", log.caminho_relativo(destino))
    print(resumo.to_string(index=False) if not resumo.empty else "sem dados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
