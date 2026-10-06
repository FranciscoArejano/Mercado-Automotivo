#!/usr/bin/env python3
"""Etapa 13 -- calendario de politicas (2003-2026).

Le as duas tabelas de referencia -- `dados/referencia/politicas_atos.csv` e
`politicas_aliquotas.csv`, montadas por `ferramentas/politicas_referencia.py` a
partir das paginas oficiais guardadas em `dados/bruto/politicas_paginas/` -- e
confere cada linha contra a pagina (SHA-256 do manifesto, URL, trecho literal,
fonte oficial).

Produtos:
- `dados/processado/politicas_mensal.parquet` -- uma linha por mes e ato em vigor,
  para juntar ao painel pelo `mes_ref`;
- `saidas/politicas_validacao.csv` -- as conferencias;
- `saidas/politicas_uso_teste.csv` -- a serie em volta de cada data de efeito
  (vendas do painel, ou a importacao afetada em unidades ajustadas). Nao estima
  efeito: marca onde a data nao casa com movimento;
- `saidas/politicas_dicionario.md`.

Falha (codigo 1, nada gravado) se alguma conferencia falhar.

Uso:
    python src/etapa13_politicas.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, log, politicas  # noqa: E402

ETAPA = "etapa13_politicas"


def vendas_mensais() -> pd.Series:
    """Unidades do painel por mes, automoveis e comerciais leves."""
    painel = pd.read_parquet(config.PAINEL, columns=["mes_ref", "segmento", "unidades"])
    painel = painel[painel["segmento"].isin(config.SEGMENTOS)]
    return painel.groupby("mes_ref")["unidades"].sum()


def executar(inicio: str = config.PERIODO_INICIO, fim: str = config.PERIODO_FIM) -> int:
    logger = log.preparar(ETAPA)
    for caminho in (config.POLITICAS_ATOS, config.POLITICAS_ALIQUOTAS):
        if not caminho.exists():
            logger.error("sem %s: rode src/ferramentas/politicas_referencia.py",
                         log.caminho_relativo(caminho))
            return 1
    atos = politicas.carregar_atos()
    aliquotas = politicas.carregar_aliquotas()
    manifesto = politicas.carregar_manifesto()
    texto = politicas.textos(politicas.paginas_citadas(atos, aliquotas))

    p_paginas = politicas.problemas_das_paginas(manifesto)
    p_atos = politicas.problemas_dos_atos(atos, manifesto, texto)
    p_aliquotas = politicas.problemas_das_aliquotas(aliquotas, atos, manifesto, texto)
    problemas = p_paginas + p_atos + p_aliquotas
    if problemas:
        for p in problemas[:40]:
            logger.error(p)
        logger.error("%d problemas: nada gravado", len(problemas))
        return 1

    mensal = politicas.mensal(atos, inicio, fim)
    antecedentes = sorted(atos.loc[(atos["vigencia_fim"] != "")
                                   & (atos["vigencia_fim"] < f"{inicio}-01"), "id"])
    sem_mes = sorted(set(atos["id"]) - set(mensal["ato_id"]) - set(antecedentes))
    lacunas = politicas.lacunas_do_ipi(aliquotas, inicio, fim)
    derivadas = aliquotas[aliquotas["derivada"] == "sim"]
    citadas = politicas.paginas_citadas(atos, aliquotas)
    nao_citadas = sorted(set(manifesto["nome"]) - citadas)
    abertos = atos[atos["vigencia_fim"] == ""]
    validacao = pd.DataFrame([
        {"conferencia": "pagina guardada: arquivo presente, SHA-256 do manifesto, primeira "
                        "linha com a URL", "casos": len(manifesto), "falhas": len(p_paginas)},
        {"conferencia": "ato: campos nas listas, datas validas, altera_id existente, pagina "
                        "no manifesto com a mesma URL, fonte oficial, trecho literal",
         "casos": len(atos), "falhas": len(p_atos)},
        {"conferencia": "aliquota: tributo, NCM no formato da TIPI, ato existente, trecho "
                        "literal, uma aliquota por periodo (NCM x categoria)",
         "casos": len(aliquotas), "falhas": len(p_aliquotas)},
        {"conferencia": f"ato sem nenhum mes na janela {inicio} a {fim}: "
                        f"{', '.join(sem_mes) or 'nenhum'}", "casos": len(atos),
         "falhas": len(sem_mes)},
        {"conferencia": "IPI: categoria principal sem aliquota em algum mes (de "
                        f"{inicio} ou do inicio da categoria a {fim}): "
                        + ("; ".join(f"{l['categoria']} {l['de']} a {l['ate']}" for l in lacunas)
                           or "nenhuma"),
         "casos": len(politicas.CATEGORIAS_IPI), "falhas": len(lacunas)},
        {"conferencia": "registro, nao falha: aliquotas derivadas (o ato fixa uma reducao "
                        f"percentual, nao a aliquota): {len(derivadas)}",
         "casos": len(aliquotas), "falhas": 0},
        {"conferencia": "registro, nao falha: atos antecedentes (acabam antes da janela): "
                        f"{', '.join(antecedentes) or 'nenhum'}", "casos": len(atos), "falhas": 0},
        {"conferencia": "registro, nao falha: paginas guardadas que nenhum ato ou aliquota "
                        f"cita: {', '.join(nao_citadas) or 'nenhuma'}",
         "casos": len(manifesto), "falhas": 0},
        {"conferencia": "registro, nao falha: atos sem vigencia_fim (em vigor, ou fim nao "
                        f"confirmado): {len(abertos)}", "casos": len(atos), "falhas": 0},
    ])
    if sem_mes or lacunas:
        for l in lacunas:
            logger.error("IPI sem aliquota: %s de %s a %s", l["categoria"], l["de"], l["ate"])
        if sem_mes:
            logger.error("atos fora da janela: %s", sem_mes)
        logger.error("nada gravado")
        return 1

    comex = pd.read_parquet(config.COMEX_VEICULOS,
                            columns=["mes_ref", "fluxo", "ncm", "pais", "unidades_ajustadas"])
    ncms = pd.read_csv(config.NCM_VEICULOS, dtype=str, keep_default_na=False)
    uso = politicas.uso_teste(atos, aliquotas, vendas_mensais(), comex, ncms)

    config.DIR_PROCESSADO.mkdir(parents=True, exist_ok=True)
    mensal.to_parquet(config.POLITICAS_MENSAL, index=False)
    validacao.to_csv(config.POLITICAS_VALIDACAO, index=False)
    uso.to_csv(config.POLITICAS_USO_TESTE, index=False)
    config.POLITICAS_DICIONARIO.write_text(dicionario(atos, aliquotas, mensal, validacao, uso),
                                           encoding="utf-8")
    logger.info("politicas: %d atos, %d aliquotas, %d linhas mensais (%s a %s)",
                len(atos), len(aliquotas), len(mensal), mensal["mes_ref"].min(),
                mensal["mes_ref"].max())
    logger.info("uso-teste: %d datas; sem movimento: %d", len(uso),
                int((uso["movimento"] == "nao").sum()))
    logger.info("gravado %s", log.caminho_relativo(config.POLITICAS_MENSAL))
    return 0


def _atos_por_tema(atos: pd.DataFrame) -> str:
    linhas = ["| tema | atos | primeiro inicio | ultimo inicio |", "|---|---|---|---|"]
    for tema in politicas.TEMAS:
        g = atos[atos["tema"] == tema]
        if len(g):
            linhas.append(f"| `{tema}` | {len(g)} | {g['vigencia_inicio'].min()} | "
                          f"{g['vigencia_inicio'].max()} |")
    return "\n".join(linhas)


def dicionario(atos: pd.DataFrame, aliquotas: pd.DataFrame, mensal: pd.DataFrame,
               validacao: pd.DataFrame, uso: pd.DataFrame) -> str:
    por_tributo = aliquotas.groupby("tributo").size().to_dict()
    inicio_janela = mensal["mes_ref"].min()
    categorias = ", ".join(f"`{c}`" for c in politicas.CATEGORIAS_IPI.values())
    sem_mov = uso[uso["movimento"] == "nao"]
    return f"""# Dicionario -- calendario de politicas

Gerado por `src/etapa13_politicas.py`. Tres arquivos: duas tabelas de referencia,
escritas a' mao a partir das paginas oficiais, e uma tabela mensal derivada delas.

**So' fonte oficial.** Planalto, Diario Oficial da Uniao (visualizador de PDF da
Imprensa Nacional), gov.br (Gecex/MDIC, Contran no Ministerio dos Transportes,
Conama), Banco Central. Cada pagina esta' em `dados/bruto/politicas_paginas/`, com
URL e SHA-256 do texto no manifesto. Noticia ajudou a achar ato, nunca e' citada.

## `dados/referencia/politicas_atos.csv` ({len(atos)} atos)

| coluna | conteudo |
|---|---|
| `id` | tema, ano e ato (`ipi_2012_dec7725`) |
| `tema` | {", ".join(f"`{t}`" for t in politicas.TEMAS)} |
| `instrumento`, `numero` | tipo e numero do ato |
| `data_ato`, `data_publicacao` | data de assinatura e da publicacao no DOU (vazia quando a pagina nao a da') |
| `vigencia_inicio`, `vigencia_fim` | periodo de efeito. `vigencia_fim` vazia: em vigor, ou fim nao confirmado em pagina aberta (a observacao diz qual) |
| `altera_id` | o ato que este altera, prorroga ou substitui |
| `sentido` | {", ".join(f"`{s}`" for s in politicas.SENTIDOS)} |
| `alcance` | o que o ato atinge |
| `fonte_url`, `tipo_fonte`, `pagina_salva` | pagina oficial; `tipo_fonte` = `oficial` pelo dominio (`config/tipo_fonte_dominio.csv`) |
| `fonte_trecho` | trecho literal da pagina; partes separadas por ` [...] ` |
| `observacao` | o que o trecho nao diz sozinho: aliquotas, fim inferido, data de efeito calculada |

{_atos_por_tema(atos)}

## `dados/referencia/politicas_aliquotas.csv` ({len(aliquotas)} linhas: {", ".join(f"{k} {v}" for k, v in por_tributo.items())})

So' as aliquotas que o proprio ato fixa -- nao e' a TIPI inteira. Uma aliquota por
periodo: a linha de um ato que um ato posterior fixa de novo (no IPI, a mesma categoria;
fora dele, a mesma NCM e categoria) vale ate' a vespera da do posterior; cronograma
substituido antes de valer fica fora.

**IPI completo.** Cada categoria principal (`categoria_ipi`) tem aliquota em todos os meses
em que existe: as de combustao de {inicio_janela} em diante, as de 8703.40, 8703.60 e
8703.80 desde 11/2018. A etapa falha se faltar um mes.

| coluna | conteudo |
|---|---|
| `tributo` | `ipi`, `ii` (imposto de importacao), `iof` |
| `ncm` | com os pontos da TIPI e, quando ha', o Ex (`8703.23.10 Ex 01`, `8703.80.00 Ex 007`). Os digitos sem os pontos sao prefixo da NCM do Comex Stat (`comex_veiculos.parquet`). Vazia no IOF |
| `categoria` | no IPI, a categoria principal (combustao) ou a faixa de eficiencia e massa (eletrificados); no II, a descricao do Ex e a quota |
| `categoria_ipi` | so' no IPI: {categorias} |
| `vigencia_inicio`, `vigencia_fim` | periodo da aliquota |
| `aliquota_pct` | nominal, em %, com virgula decimal. IOF: % ao dia |
| `aliquota_efetiva_habilitada` | so' no IPI. De 16/12/2011 a 31/12/2017 a TIPI inclui 30 pontos; a efetiva da empresa habilitada e' a nominal menos a reducao que o proprio ato da' (30 pontos: Decreto 7.567 em 2011-2012; teto do credito presumido do Inovar-Auto, Decreto 7.819, em 2013-2017). Fora desse periodo, igual a' nominal |
| `reducao_ato_id`, `reducao_pagina`, `reducao_trecho` | o ato, a pagina e o trecho literal que fixam a reducao da habilitada |
| `derivada` | `sim` quando o ato fixa uma reducao percentual e nao a aliquota (a regra esta' na observacao): 18,5% do Decreto 10.979 sobre a TIPI de 2017 nos codigos que ele nao lista |
| `ato_id`, `pagina_salva`, `fonte_trecho` | ato, pagina (o anexo, quando a tabela esta' nele) e trecho literal |
| `observacao` | regra da derivada, leitura da tabela de eficiencia, base do IPI Verde |

## `dados/processado/politicas_mensal.parquet` ({len(mensal):,} linhas, {mensal['mes_ref'].min()} a {mensal['mes_ref'].max()})

Uma linha por mes e ato em vigor. Junta ao painel pelo `mes_ref`; um mes tem varios
atos.

| coluna | conteudo |
|---|---|
| `mes_ref`, `ano`, `mes` | o mes |
| `ato_id`, `tema`, `sentido`, `instrumento`, `numero` | do ato |
| `vigencia_inicio`, `vigencia_fim` | do ato |
| `comeca_no_mes`, `termina_no_mes` | o ato comeca ou termina neste mes |
| `dias_em_vigor`, `fracao_do_mes` | dias do mes com o ato em vigor |

Ato sem `vigencia_fim` vai ate' o ultimo mes da janela.

## Uso-teste (`saidas/politicas_uso_teste.csv`, {len(uso)} datas)

Uma linha por data de efeito: o inicio de cada ato e cada mudanca de aliquota que
o proprio ato fixa depois (degraus, retorno da aliquota cheia). Serie: vendas do
painel; no imposto de importacao, a importacao das NCMs do ato em unidades ajustadas;
no acordo automotivo, a importacao do agregado de carros vinda do pais parceiro.
Colunas: media dos {politicas.JANELA} meses antes, o mes da data, media dos
{politicas.JANELA} depois, e as mesmas janelas um ano antes (o movimento sazonal).
`movimento` = `sim` quando a variacao do mes ou dos tres seguintes, contra os tres
anteriores, difere da do ano anterior em {politicas.LIMIAR_PONTOS:.0f} pontos ou mais.
**Nao e' estimativa de efeito**: `nao` marca a data a conferir. Sem movimento:
{len(sem_mov)} de {len(uso)}.

## Conferencias (`saidas/politicas_validacao.csv`)

{validacao.to_markdown(index=False)}
"""


if __name__ == "__main__":
    raise SystemExit(executar())
