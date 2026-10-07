#!/usr/bin/env python3
"""Etapa 14 -- origem por pais e por fabrica (rodada 12, sec. 2).

Le as tres tabelas de referencia -- `dados/referencia/fabricas.csv` e
`fabrica_modelos.csv`, montadas por `ferramentas/fabricas_referencia.py` a partir das
paginas guardadas, e `origem_pais_proposta.csv` (a proposta do assistente) -- e as
confere (SHA-256 do manifesto, URL, tipo da fonte pelo dominio, trecho literal, pais da
tabela do Comex, municipio e codigo do IBGE, periodos). Deriva o pais de producao mes a
mes em cada vigencia classificada (regra em `comum/origem_pais.py`).

Produtos:
- `dados/processado/classificacao_origem.parquet` -- uma linha por vigencia, periodo e
  pais de producao, com fabrica, municipio, UF e codigo IBGE no Brasil, pais do kit em
  ckd/skd, fonte e procedencia. `origem_producao` derivada do pais fica ao lado da atual;
  `classificacao.parquet` nao muda;
- `saidas/origem_divergencias.csv` -- origem derivada diferente da atual e periodos em que
  a fonte contradiz a proposta (vao ao rascunho, aba `origem_pais`);
- `saidas/origem_cobertura.csv` -- cobertura por fonte forte, ano a ano (meta: 80%);
- `saidas/origem_uso_teste_comex.csv` e `origem_uso_teste_distancias.csv` -- importacao do
  Comex por pais e ano contra o painel, e as cinco maiores distancias de cada ano;
- `saidas/origem_uso_teste_anfavea.csv` -- emplacamento de importados da Anfavea (anuarios)
  contra o painel: so' registro e comparacao;
- `saidas/origem_mapa_uf.csv` -- unidades por UF de producao e ano, com alertas;
- `saidas/origem_validacao.csv`, `saidas/origem_dicionario.md`.

Nada e' reclassificado pelo Comex nem pela Anfavea. Falha (codigo 1, nada gravado) se
alguma conferencia falhar.

Uso:
    python src/etapa14_origem.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import anfavea, config, log  # noqa: E402
from comum import origem_pais as op  # noqa: E402

ETAPA = "etapa14_origem"
ENTRADAS = (config.FABRICAS, config.FABRICA_MODELOS, config.ORIGEM_PAIS_PROPOSTA,
            config.CLASSIFICACAO, config.CLASSIFICACAO_MONTAGEM, config.PAINEL,
            config.COMEX_VEICULOS)


def executar(inicio: str = config.PERIODO_INICIO, fim: str = config.PERIODO_FIM) -> int:
    logger = log.preparar(ETAPA)
    faltam = [c for c in ENTRADAS if not c.exists()]
    if faltam:
        for c in faltam:
            logger.error("sem %s", log.caminho_relativo(c))
        return 1
    fabricas = op.carregar_fabricas()
    fm = op.carregar_fabrica_modelos()
    proposta = op.carregar_proposta()
    classificacao = pd.read_parquet(config.CLASSIFICACAO)
    montagem = pd.read_parquet(config.CLASSIFICACAO_MONTAGEM)
    painel = pd.read_parquet(config.PAINEL, columns=[*op.CHAVE, "mes_ref", "unidades"])
    vigencias = classificacao[classificacao["procedencia_origem"] != "nao_classificado"]
    chaves = set(map(tuple, classificacao[op.CHAVE].values))

    manif = op.manifestos()
    urls = op.url_das_paginas(manif)
    citadas = op.paginas_citadas(fabricas, fm)
    texto = op.textos(citadas)
    serie, anf_paises = anfavea.series(), anfavea.por_pais()
    conferencias = [
        ("pagina guardada (fabricas_paginas e anfavea inteiras, origem_paginas citadas): "
         "arquivo presente, SHA-256 do manifesto, primeira linha com a URL",
         sum(len(m) for m in manif.values()), op.problemas_das_paginas(manif, citadas)),
        ("fabrica: id unico, pais e codigo do Comex, municipio/UF/codigo IBGE no Brasil, "
         "datas de operacao, fonte com URL do manifesto, tipo pelo dominio e trecho literal",
         len(fabricas), op.problemas_das_fabricas(fabricas, urls, texto)),
        ("fabrica x modelo: fabrica existente e do mesmo pais, chave do painel, vinculo e "
         "regra nas listas e coerentes, datas AAAA-MM, fonte e trecho literal",
         len(fm), op.problemas_de_fabrica_modelos(fm, fabricas, chaves, urls, texto)),
        ("proposta: pais e pais do kit do Comex, fabrica do mesmo pais, periodos, chave "
         "classificada, todo mes de vigencia classificada coberto",
         len(proposta), op.problemas_da_proposta(proposta, fabricas, vigencias)),
        ("Anfavea: segmentos somam o total, anos 2003-2025 completos, trecho na pagina, "
         "paises da 2.2.5 somam o TOTAL e batem com a 2.2.4",
         len(serie) + len(anf_paises), anfavea.problemas(serie, anf_paises)),
    ]
    if any(p for _, _, p in conferencias):
        for _, _, problemas in conferencias:
            for p in problemas[:40]:
                logger.error(p)
        logger.error("%d problemas nas tabelas de referencia: nada gravado",
                     sum(len(p) for _, _, p in conferencias))
        return 1

    por_mes = op.derivar_meses(vigencias, proposta, fm)
    prod = op.produto(classificacao, montagem, por_mes, fabricas, fm)
    p_prod = op.problemas_do_produto(prod, vigencias, fabricas)
    conferencias.append(
        ("produto: todo mes de vigencia classificada com pais, periodos sem sobreposicao, "
         "codigo do pais, procedencia, regra com fonte, fabrica e UF so' no Brasil, kit so' "
         "em ckd/skd, origem derivada coerente", len(prod), p_prod))
    if p_prod:
        for p in p_prod[:40]:
            logger.error(p)
        logger.error("%d problemas no produto: nada gravado", len(p_prod))
        return 1

    div = op.divergencias(prod, por_mes, fm)
    cob = op.cobertura_anual(por_mes, painel, fm)
    comex = pd.read_parquet(config.COMEX_VEICULOS,
                            columns=["mes_ref", "fluxo", "ncm", "pais", "unidades_ajustadas"])
    ncms = pd.read_csv(config.NCM_VEICULOS, dtype=str, keep_default_na=False)
    por_pais = op.unidades_por_pais(por_mes, painel, montagem)
    uso_comex = op.uso_teste_comex(por_pais, op.importacao_comex(comex, ncms, fim),
                                   int(inicio[:4]), int(fim[:4]))
    distancias = op.distancias_comex(uso_comex, por_mes, painel, fm)
    uso_anfavea = op.uso_teste_anfavea(op.participacao_importado_painel(por_mes, painel),
                                       anfavea.participacao_importados(serie), por_pais,
                                       anf_paises)
    uf = op.mapa_uf(por_mes, painel, fabricas)

    procedencias = prod.groupby("procedencia").size().to_dict()
    abaixo = cob[cob["atinge_meta_80"] == "nao"]
    validacao = pd.DataFrame(
        [{"conferencia": c, "casos": n, "falhas": len(p)} for c, n, p in conferencias] + [
            {"conferencia": "registro, nao falha: linhas do produto por procedencia: "
                            + ", ".join(f"{k} {v}" for k, v in sorted(procedencias.items())),
             "casos": len(prod), "falhas": 0},
            {"conferencia": "registro, nao falha: anos abaixo da meta de 80% de unidades com "
                            "fonte forte: " + (", ".join(f"{r.ano} ({r.pct_fonte_forte}%)"
                                                         for r in abaixo.itertuples())
                                               or "nenhum"),
             "casos": len(cob), "falhas": 0},
            {"conferencia": "registro, nao falha: divergencias ao rascunho (origem derivada "
                            "difere da atual; fonte contradiz a proposta): "
                            + ", ".join(f"{k} {v}" for k, v in
                                        div.groupby("tipo").size().items()),
             "casos": len(div), "falhas": 0},
            {"conferencia": "registro, nao falha: fabricas sem pagina guardada: "
                            + (", ".join(fabricas.loc[fabricas["pagina_salva"] == "",
                                                      "fabrica_id"]) or "nenhuma"),
             "casos": len(fabricas), "falhas": 0},
        ])

    config.DIR_PROCESSADO.mkdir(parents=True, exist_ok=True)
    prod.to_parquet(config.CLASSIFICACAO_ORIGEM, index=False)
    validacao.to_csv(config.ORIGEM_VALIDACAO, index=False)
    cob.to_csv(config.ORIGEM_COBERTURA, index=False)
    div.to_csv(config.ORIGEM_DIVERGENCIAS, index=False)
    uso_comex.to_csv(config.ORIGEM_USO_TESTE_COMEX, index=False)
    distancias.to_csv(config.ORIGEM_USO_TESTE_DISTANCIAS, index=False)
    uso_anfavea.to_csv(config.ORIGEM_USO_TESTE_ANFAVEA, index=False)
    uf.to_csv(config.ORIGEM_MAPA_UF, index=False)
    config.ORIGEM_DICIONARIO.write_text(
        dicionario(prod, fabricas, fm, proposta, cob, div, validacao, uso_comex, uso_anfavea,
                   uf), encoding="utf-8")
    logger.info("origem: %d linhas (%d vigencias classificadas), %d divergencias",
                len(prod), len(vigencias), len(div))
    logger.info("cobertura por fonte forte: %s", " ".join(
        f"{r.ano}:{r.pct_fonte_forte}" for r in cob.itertuples()))
    logger.info("gravado %s", log.caminho_relativo(config.CLASSIFICACAO_ORIGEM))
    return 0


def _md(quadro: pd.DataFrame) -> str:
    return quadro.to_markdown(index=False)


def dicionario(prod, fabricas, fm, proposta, cob, div, validacao, uso_comex, uso_anfavea,
               uf) -> str:
    vinculos = fm.groupby("vinculo").size().to_dict()
    regras = fm.groupby("regra_periodo").size().to_dict()
    tipos = fm.groupby("tipo_fonte").size().to_dict()
    part = uso_anfavea[uso_anfavea["tabela"] == "participacao"][
        ["ano", "anfavea_pct_importado", "painel_pct_importado", "painel_pct_importado_max",
         "diferenca_pp"]]
    alertas = uf[uf["alerta"] != ""]
    return f"""# Dicionario -- origem por pais e por fabrica

Gerado por `src/etapa14_origem.py` (rodada 12, sec. 2). Tres tabelas de referencia e um
produto; a regra de derivacao esta' em `src/comum/origem_pais.py`.

**Fonte com trecho literal.** Cada linha de `fabricas.csv` e `fabrica_modelos.csv` cita uma
pagina guardada (`dados/bruto/fabricas_paginas/`, `origem_paginas/`), com URL e SHA-256 do
texto no manifesto; `tipo_fonte` vem do dominio (`config/tipo_fonte_dominio.csv`). Fonte
forte = `oficial` ou `imprensa_especializada`.

## `dados/referencia/fabricas.csv` ({len(fabricas)} fabricas)

| coluna | conteudo |
|---|---|
| `fabrica_id` | identificador (`vw_taubate`, `ar_toyota`) |
| `empresa`, `fabrica` | empresa e planta. No exterior, quando a fonte (ADEFA, INEGI) da' a empresa e nao a planta, a fabrica e' a empresa no pais |
| `pais`, `pais_codigo` | nome e codigo da tabela de paises do Comex Stat (`dados/bruto/comex/paises.json`) |
| `municipio`, `uf`, `cod_ibge_municipio` | so' no Brasil; o codigo e' o da tabela de municipios do IBGE (`dados/bruto/ibge/municipios.json`) |
| `operacao_inicio`, `operacao_fim` | AAAA ou AAAA-MM, quando a fonte os da' |
| `fonte_url`, `tipo_fonte`, `fonte_trecho`, `pagina_salva` | a fonte da existencia da fabrica |
| `operacao_trecho`, `operacao_pagina` | a fonte das datas de operacao, quando e' outra pagina |
| `observacao` | o que a fonte nao diz sozinha |

## `dados/referencia/fabrica_modelos.csv` ({len(fm)} linhas)

Que modelo (chave do painel) cada fabrica produziu, em que periodo, segundo que fonte.
Vinculos: {", ".join(f"`{k}` {v}" for k, v in vinculos.items())}. Regras de periodo:
{", ".join(f"`{k}` {v}" for k, v in regras.items())}. Tipos: {", ".join(f"`{k}` {v}" for k, v in tipos.items())}.

| coluna | conteudo |
|---|---|
| `fabrica_id`, `pais` | a fabrica (vazia quando a pagina nomeia so' o pais) e o seu pais |
| `marca`, `modelo`, `segmento` | a chave do painel |
| `periodo_inicio`, `periodo_fim` | AAAA-MM. A fonte vale so' para o periodo que trata; ano sem mes vira janeiro no inicio e dezembro no fim |
| `vinculo` | `producao_local` (fabrica brasileira produz), `abastece_o_brasil` (a fonte diz que o modelo vem de la' para o Brasil: exportacao ao Brasil do INEGI, materia sobre o importado), `producao_no_exterior` (a fonte so' diz que e' feito la', como a producao por modelo da ADEFA) |
| `regra_periodo` | `declarado` (inicio e fim no texto), `inicio_ate_a_pagina` (inicio no texto, fim na data da pagina), `duracao_ate_a_pagina`, `na_data_da_pagina` (um mes), `ano_da_tabela` (ADEFA), `meses_da_tabela` (INEGI: meses seguidos de exportacao ao Brasil, do primeiro ao ultimo mais dois; bloco de menos de 100 unidades nao conta) |
| `data_fonte` | data da pagina (AAAA-MM) |
| `fonte_url`, `tipo_fonte`, `fonte_trecho`, `pagina_salva`, `observacao` | a fonte; partes do trecho separadas por ` [...] ` |

## `dados/referencia/origem_pais_proposta.csv` ({len(proposta)} linhas)

O pais (e a fabrica, no Brasil; e o pais do kit, em ckd/skd) que o assistente propoe para
cada chave classificada, por periodo. E' conhecimento, nao fonte: foi escrita antes da
leitura das fontes e nao foi revista depois; onde a fonte discorda, o mes fica `pendente`
e vai ao rascunho.

## `dados/processado/classificacao_origem.parquet` ({len(prod):,} linhas)

Uma linha por vigencia, periodo e pais de producao. Dois paises no mesmo periodo sao duas
linhas. Vigencia nao classificada (abaixo do piso) tem uma linha, sem pais.

| coluna | conteudo |
|---|---|
| `marca`, `modelo`, `segmento`, `vigencia_inicio`, `vigencia_fim` | a vigencia de `classificacao.parquet` |
| `periodo_inicio`, `periodo_fim` | meses seguidos com o mesmo conteudo |
| `pais_producao`, `pais_codigo` | pais (nome e codigo do Comex) |
| `origem_no_periodo` | `nacional`, `importado` ou `ambos` (dois paises, um deles o Brasil) |
| `fabrica_id`, `fabrica`, `municipio`, `uf`, `cod_ibge_municipio` | so' no Brasil; varias fabricas separadas por `+` (ou ` \\| `) |
| `fabrica_procedencia` | `fonte` (a fabrica vem das fontes que confirmam o Brasil) ou `proposta` |
| `montagem_local`, `pais_do_kit` | da tabela de montagem; o pais do kit so' em ckd/skd no Brasil |
| `procedencia` | `regra_fonte_forte`, `regra_fonte_fraca`, `proposta`, `pendente` (fonte com vinculo ao Brasil nomeia pais fora da proposta; o valor e' a proposta), `nao_classificado` |
| `vinculo`, `fonte_url`, `tipo_fonte`, `fonte_trecho`, `pagina_salva` | as fontes que confirmam o pais (separadas por ` \\| `) |
| `origem_vigencia_derivada` | origem da vigencia derivada dos paises de todos os meses |
| `origem_vigencia_atual`, `diverge_da_atual` | a `origem_producao` de `classificacao.parquet` e se difere da derivada |
| `observacao` | a contradicao, quando ha', e a observacao da proposta |

Regra, mes a mes: P = paises propostos. Fonte `producao_local` confirma o Brasil; fonte
`abastece_o_brasil` confirma o seu pais; fonte `producao_no_exterior` so' confirma pais que
ja' esta' em P. Fonte com vinculo ao Brasil que nomeia pais fora de P: contradicao,
`pendente`. Senao, pais confirmado fica `regra_fonte_forte` ou `regra_fonte_fraca`; o resto,
`proposta`.

## Cobertura por fonte forte (`saidas/origem_cobertura.csv`)

Unidades do painel (todas as vigencias, classificadas ou nao) cobertas por fonte forte:
todos os paises do mes confirmados por fonte forte. `forte_so_producao_no_exterior` e' a
parte confirmada so' pela ADEFA (producao no pais, sem dizer que abastece o Brasil). Meta da
rodada: 80% em cada ano de 2003 a 2026.

{_md(cob[["ano", "unidades_painel", "unidades_fonte_forte", "pct_fonte_forte", "unidades_forte_so_producao_no_exterior", "unidades_pendente", "atinge_meta_80"]])}

## Divergencias (`saidas/origem_divergencias.csv`, {len(div)} linhas)

`origem_derivada_difere_da_atual`: a origem derivada dos paises difere da `origem_producao`
atual. `fonte_contradiz_proposta`: periodo `pendente`, com a fonte que contradiz. As duas
vao a' aba `origem_pais` do rascunho (`ferramentas/classificacao_rascunho.py`);
`classificacao.parquet` nao foi sobrescrita.

## Uso-teste 1 -- Comex (`origem_uso_teste_comex.csv`, `origem_uso_teste_distancias.csv`)

Por ano e pais: importacao do agregado de carros (`unidades_ajustadas`) contra unidades do
painel feitas no pais (meses de um pais so') mais as montadas aqui em ckd/skd com kit dele.
`unidades_compartilhadas` (meses com dois paises) ficam ao lado, fora da soma. Importacao e
emplacamento tem defasagem (estoque, transito). As distancias: as cinco maiores de cada ano,
com os modelos que as explicariam. Nada e' reclassificado pelo Comex.

## Uso-teste 2 -- Anfavea (`origem_uso_teste_anfavea.csv`)

A serie mensal de licenciamento de nacionais e importados nao abriu; os anuarios abriram
(`dados/bruto/anfavea/`): total e importados por ano (2003-2025) e importados por pais de
origem (2016-2025). So' registro e comparacao: nenhuma dimensao foi construida com eles.
Participacao do importado (automoveis + comerciais leves), Anfavea x painel (minima: meses
de pais estrangeiro; maxima: somando meses com os dois paises e vigencias nao
classificadas):

{_md(part)}

## Uso-teste 3 -- mapa por UF (`origem_mapa_uf.csv`)

Unidades por UF de producao e ano (meses com o Brasil como unico pais). `alerta`: fabrica
fora do seu periodo de operacao, variacao de participacao de 5 pontos ou mais, mes sem
fabrica. Linhas com alerta: {len(alertas)}.

## Conferencias (`saidas/origem_validacao.csv`)

{_md(validacao)}
"""


if __name__ == "__main__":
    raise SystemExit(executar())
