# Dicionario -- origem por pais e por fabrica

Gerado por `src/etapa14_origem.py` (rodada 12, sec. 2). Tres tabelas de referencia e um
produto; a regra de derivacao esta' em `src/comum/origem_pais.py`.

**Fonte com trecho literal.** Cada linha de `fabricas.csv` e `fabrica_modelos.csv` cita uma
pagina guardada (`dados/bruto/fabricas_paginas/`, `origem_paginas/`), com URL e SHA-256 do
texto no manifesto; `tipo_fonte` vem do dominio (`config/tipo_fonte_dominio.csv`). Fonte
forte = `oficial` ou `imprensa_especializada`.

## `dados/referencia/fabricas.csv` (55 fabricas)

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

## `dados/referencia/fabrica_modelos.csv` (861 linhas)

Que modelo (chave do painel) cada fabrica produziu, em que periodo, segundo que fonte.
Vinculos: `abastece_o_brasil` 107, `producao_local` 335, `producao_no_exterior` 419. Regras de periodo:
`ano_da_tabela` 419, `declarado` 65, `duracao_ate_a_pagina` 12, `inicio_ate_a_pagina` 81, `meses_da_tabela` 87, `na_data_da_pagina` 197. Tipos: `imprensa_especializada` 341, `imprensa_geral` 1, `oficial` 519.

| coluna | conteudo |
|---|---|
| `fabrica_id`, `pais` | a fabrica (vazia quando a pagina nomeia so' o pais) e o seu pais |
| `marca`, `modelo`, `segmento` | a chave do painel |
| `periodo_inicio`, `periodo_fim` | AAAA-MM. A fonte vale so' para o periodo que trata; ano sem mes vira janeiro no inicio e dezembro no fim |
| `vinculo` | `producao_local` (fabrica brasileira produz), `abastece_o_brasil` (a fonte diz que o modelo vem de la' para o Brasil: exportacao ao Brasil do INEGI, materia sobre o importado), `producao_no_exterior` (a fonte so' diz que e' feito la', como a producao por modelo da ADEFA) |
| `regra_periodo` | `declarado` (inicio e fim no texto), `inicio_ate_a_pagina` (inicio no texto, fim na data da pagina), `duracao_ate_a_pagina`, `na_data_da_pagina` (um mes), `ano_da_tabela` (ADEFA), `meses_da_tabela` (INEGI: meses seguidos de exportacao ao Brasil, do primeiro ao ultimo mais dois; bloco de menos de 100 unidades nao conta) |
| `data_fonte` | data da pagina (AAAA-MM) |
| `fonte_url`, `tipo_fonte`, `fonte_trecho`, `pagina_salva`, `observacao` | a fonte; partes do trecho separadas por ` [...] ` |

## `dados/referencia/origem_pais_proposta.csv` (501 linhas)

O pais (e a fabrica, no Brasil; e o pais do kit, em ckd/skd) que o assistente propoe para
cada chave classificada, por periodo. E' conhecimento, nao fonte: foi escrita antes da
leitura das fontes e nao foi revista depois; onde a fonte discorda, o mes fica `pendente`
e vai ao rascunho.

## `dados/processado/classificacao_origem.parquet` (1,938 linhas)

Uma linha por vigencia, periodo e pais de producao. Dois paises no mesmo periodo sao duas
linhas. Vigencia nao classificada (abaixo do piso) tem uma linha, sem pais.

| coluna | conteudo |
|---|---|
| `marca`, `modelo`, `segmento`, `vigencia_inicio`, `vigencia_fim` | a vigencia de `classificacao.parquet` |
| `periodo_inicio`, `periodo_fim` | meses seguidos com o mesmo conteudo |
| `pais_producao`, `pais_codigo` | pais (nome e codigo do Comex) |
| `origem_no_periodo` | `nacional`, `importado` ou `ambos` (dois paises, um deles o Brasil) |
| `fabrica_id`, `fabrica`, `municipio`, `uf`, `cod_ibge_municipio` | so' no Brasil; varias fabricas separadas por `+` (ou ` \| `) |
| `fabrica_procedencia` | `fonte` (a fabrica vem das fontes que confirmam o Brasil) ou `proposta` |
| `montagem_local`, `pais_do_kit` | da tabela de montagem; o pais do kit so' em ckd/skd no Brasil |
| `procedencia` | `regra_fonte_forte`, `regra_fonte_fraca`, `proposta`, `pendente` (fonte com vinculo ao Brasil nomeia pais fora da proposta; o valor e' a proposta), `nao_classificado` |
| `vinculo`, `fonte_url`, `tipo_fonte`, `fonte_trecho`, `pagina_salva` | as fontes que confirmam o pais (separadas por ` \| `) |
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

|   ano |   unidades_painel |   unidades_fonte_forte |   pct_fonte_forte |   unidades_forte_so_producao_no_exterior |   unidades_pendente | atinge_meta_80   |
|------:|------------------:|-----------------------:|------------------:|-----------------------------------------:|--------------------:|:-----------------|
|  2003 |           1340014 |                1202325 |              89.7 |                                     6359 |                   0 | sim              |
|  2004 |           1476704 |                1319836 |              89.4 |                                     7063 |                   0 | sim              |
|  2005 |           1615694 |                1443901 |              89.4 |                                    15476 |                   0 | sim              |
|  2006 |           1826978 |                1623854 |              88.9 |                                    24021 |                   0 | sim              |
|  2007 |           2330601 |                2001423 |              85.9 |                                        0 |                   0 | sim              |
|  2008 |           2651898 |                2338769 |              88.2 |                                   115728 |                   0 | sim              |
|  2009 |           2988674 |                2664347 |              89.1 |                                   160460 |                   0 | sim              |
|  2010 |           3293304 |                2886944 |              87.7 |                                   249665 |                   0 | sim              |
|  2011 |           3363904 |                2769185 |              82.3 |                                   259463 |                   0 | sim              |
|  2012 |           3577940 |                3040520 |              85   |                                   252121 |                   0 | sim              |
|  2013 |           3519921 |                2982833 |              84.7 |                                   237984 |               18301 | sim              |
|  2014 |           3284611 |                2763058 |              84.1 |                                   220762 |                7435 | sim              |
|  2015 |           2450047 |                2080947 |              84.9 |                                   144454 |                   0 | sim              |
|  2016 |           1969866 |                1693687 |              86   |                                   118272 |                3295 | sim              |
|  2017 |           2157969 |                1862736 |              86.3 |                                    96960 |                8278 | sim              |
|  2018 |           2452617 |                2149671 |              87.6 |                                   159333 |                2882 | sim              |
|  2019 |           2635356 |                2223563 |              84.4 |                                   157234 |                   0 | sim              |
|  2020 |           1932419 |                1632240 |              84.5 |                                   109516 |                2294 | sim              |
|  2021 |           1955588 |                1599766 |              81.8 |                                   145004 |                   0 | sim              |
|  2022 |           1936836 |                1618825 |              83.6 |                                   156679 |                   0 | sim              |
|  2023 |           2157727 |                1684240 |              78.1 |                                   167401 |                   0 | nao              |
|  2024 |           2454954 |                1656921 |              67.5 |                                   178275 |                 253 | nao              |
|  2025 |           2502229 |                1606941 |              64.2 |                                   135217 |                3365 | nao              |
|  2026 |           1824350 |                 500442 |              27.4 |                                        0 |                   0 | nao              |

## Divergencias (`saidas/origem_divergencias.csv`, 49 linhas)

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

|   ano |   anfavea_pct_importado |   painel_pct_importado |   painel_pct_importado_max |   diferenca_pp |
|------:|------------------------:|-----------------------:|---------------------------:|---------------:|
|  2003 |                     5.4 |                    3.3 |                        4   |           -2.1 |
|  2004 |                     4   |                    3.6 |                        4.3 |           -0.4 |
|  2005 |                     5.3 |                    4.3 |                        5.1 |           -1   |
|  2006 |                     7.6 |                    6.4 |                        7.1 |           -1.2 |
|  2007 |                    11.7 |                    8.4 |                        9.2 |           -3.3 |
|  2008 |                    13.9 |                   10.4 |                       11.2 |           -3.5 |
|  2009 |                    16.1 |                   12.9 |                       13.4 |           -3.2 |
|  2010 |                    19.8 |                   16.4 |                       17.9 |           -3.4 |
|  2011 |                    24.9 |                   21.3 |                       21.9 |           -3.6 |
|  2012 |                    21.6 |                   18.3 |                       18.8 |           -3.3 |
|  2013 |                    19.7 |                   15.2 |                       15.8 |           -4.5 |
|  2014 |                    18.4 |                   15.4 |                       15.9 |           -3   |
|  2015 |                    16.6 |                   13.4 |                       13.7 |           -3.2 |
|  2016 |                    13.7 |                   11.3 |                       11.7 |           -2.4 |
|  2017 |                    11.1 |                    9.5 |                        9.9 |           -1.6 |
|  2018 |                    12.5 |                   11.5 |                       11.8 |           -1   |
|  2019 |                    11   |                    9.6 |                        9.9 |           -1.4 |
|  2020 |                    10.6 |                    9.1 |                        9.4 |           -1.5 |
|  2021 |                    12.5 |                   11.5 |                       11.9 |           -1   |
|  2022 |                    13.6 |                   12.4 |                       12.8 |           -1.2 |
|  2023 |                    15.8 |                   13.8 |                       14.1 |           -2   |
|  2024 |                    18.5 |                   16.6 |                       17   |           -1.9 |
|  2025 |                    19.3 |                   15   |                       17.1 |           -4.3 |

## Uso-teste 3 -- mapa por UF (`origem_mapa_uf.csv`)

Unidades por UF de producao e ano (meses com o Brasil como unico pais). `alerta`: fabrica
fora do seu periodo de operacao, variacao de participacao de 5 pontos ou mais, mes sem
fabrica. Linhas com alerta: 16.

## Conferencias (`saidas/origem_validacao.csv`)

| conferencia                                                                                                                                                                                                                                                        |   casos |   falhas |
|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------:|---------:|
| pagina guardada (fabricas_paginas e anfavea inteiras, origem_paginas citadas): arquivo presente, SHA-256 do manifesto, primeira linha com a URL                                                                                                                    |     268 |        0 |
| fabrica: id unico, pais e codigo do Comex, municipio/UF/codigo IBGE no Brasil, datas de operacao, fonte com URL do manifesto, tipo pelo dominio e trecho literal                                                                                                   |      55 |        0 |
| fabrica x modelo: fabrica existente e do mesmo pais, chave do painel, vinculo e regra nas listas e coerentes, datas AAAA-MM, fonte e trecho literal                                                                                                                |     861 |        0 |
| proposta: pais e pais do kit do Comex, fabrica do mesmo pais, periodos, chave classificada, todo mes de vigencia classificada coberto                                                                                                                              |     501 |        0 |
| Anfavea: segmentos somam o total, anos 2003-2025 completos, trecho na pagina, paises da 2.2.5 somam o TOTAL e batem com a 2.2.4                                                                                                                                    |     506 |        0 |
| produto: todo mes de vigencia classificada com pais, periodos sem sobreposicao, codigo do pais, procedencia, regra com fonte, fabrica e UF so' no Brasil, kit so' em ckd/skd, origem derivada coerente                                                             |    1938 |        0 |
| registro, nao falha: linhas do produto por procedencia: nao_classificado 524, pendente 20, proposta 626, regra_fonte_forte 768                                                                                                                                     |    1938 |        0 |
| registro, nao falha: anos abaixo da meta de 80% de unidades com fonte forte: 2023 (78.1%), 2024 (67.5%), 2025 (64.2%), 2026 (27.4%)                                                                                                                                |      24 |        0 |
| registro, nao falha: divergencias ao rascunho (origem derivada difere da atual; fonte contradiz a proposta): fonte_contradiz_proposta 15, origem_derivada_difere_da_atual 34                                                                                       |      49 |        0 |
| registro, nao falha: fabricas sem pagina guardada: nissan_sjp, mahindra_manaus, ar_toyota, ar_ford, ar_vw, ar_fiat, ar_gm, ar_psa, ar_renault, ar_nissan, ar_mb, ar_honda, mx_audi, mx_bmw, mx_chrysler, mx_ford, mx_gm, mx_honda, mx_kia, mx_mb, mx_nissan, mx_vw |      55 |        0 |
