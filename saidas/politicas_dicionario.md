# Dicionario -- calendario de politicas

Gerado por `src/etapa13_politicas.py`. Tres arquivos: duas tabelas de referencia,
escritas a' mao a partir das paginas oficiais, e uma tabela mensal derivada delas.

**So' fonte oficial.** Planalto, Diario Oficial da Uniao (visualizador de PDF da
Imprensa Nacional), gov.br (Gecex/MDIC, Contran no Ministerio dos Transportes,
Conama), Banco Central. Cada pagina esta' em `dados/bruto/politicas_paginas/`, com
URL e SHA-256 do texto no manifesto. Noticia ajudou a achar ato, nunca e' citada.

## `dados/referencia/politicas_atos.csv` (65 atos)

| coluna | conteudo |
|---|---|
| `id` | tema, ano e ato (`ipi_2012_dec7725`) |
| `tema` | `ipi`, `regime_automotivo`, `imposto_importacao`, `acordo_automotivo`, `credito`, `programa_desconto`, `regulacao` |
| `instrumento`, `numero` | tipo e numero do ato |
| `data_ato`, `data_publicacao` | data de assinatura e da publicacao no DOU (vazia quando a pagina nao a da') |
| `vigencia_inicio`, `vigencia_fim` | periodo de efeito. `vigencia_fim` vazia: em vigor, ou fim nao confirmado em pagina aberta (a observacao diz qual) |
| `altera_id` | o ato que este altera, prorroga ou substitui |
| `sentido` | `cria`, `reduz`, `aumenta`, `prorroga`, `encerra`, `regulamenta` |
| `alcance` | o que o ato atinge |
| `fonte_url`, `tipo_fonte`, `pagina_salva` | pagina oficial; `tipo_fonte` = `oficial` pelo dominio (`config/tipo_fonte_dominio.csv`) |
| `fonte_trecho` | trecho literal da pagina; partes separadas por ` [...] ` |
| `observacao` | o que o trecho nao diz sozinho: aliquotas, fim inferido, data de efeito calculada |

| tema | atos | primeiro inicio | ultimo inicio |
|---|---|---|---|
| `ipi` | 26 | 2002-08-01 | 2025-11-01 |
| `regime_automotivo` | 6 | 2013-01-01 | 2024-06-28 |
| `imposto_importacao` | 5 | 2014-09-19 | 2026-07-01 |
| `acordo_automotivo` | 12 | 2000-08-01 | 2020-07-01 |
| `credito` | 10 | 2002-12-04 | 2015-01-22 |
| `programa_desconto` | 2 | 2023-06-06 | 2023-06-07 |
| `regulacao` | 4 | 2014-01-01 | 2025-01-01 |

## `dados/referencia/politicas_aliquotas.csv` (422 linhas: ii 86, iof 8, ipi 328)

So' as aliquotas que o proprio ato fixa -- nao e' a TIPI inteira. Uma aliquota por
periodo: a linha de um ato que um ato posterior fixa de novo (no IPI, a mesma categoria;
fora dele, a mesma NCM e categoria) vale ate' a vespera da do posterior; cronograma
substituido antes de valer fica fora.

**IPI completo.** Cada categoria principal (`categoria_ipi`) tem aliquota em todos os meses
em que existe: as de combustao de 2003-01 em diante, as de 8703.40, 8703.60 e
8703.80 desde 11/2018. A etapa falha se faltar um mes.

| coluna | conteudo |
|---|---|
| `tributo` | `ipi`, `ii` (imposto de importacao), `iof` |
| `ncm` | com os pontos da TIPI e, quando ha', o Ex (`8703.23.10 Ex 01`, `8703.80.00 Ex 007`). Os digitos sem os pontos sao prefixo da NCM do Comex Stat (`comex_veiculos.parquet`). Vazia no IOF |
| `categoria` | no IPI, a categoria principal (combustao) ou a faixa de eficiencia e massa (eletrificados); no II, a descricao do Ex e a quota |
| `categoria_ipi` | so' no IPI: `ate 1.000 cm3, gasolina`, `ate 1.000 cm3, flex ou alcool`, `1.000 a 1.500 cm3, gasolina`, `1.000 a 1.500 cm3, flex ou alcool`, `1.500 a 2.000 cm3, gasolina`, `1.500 a 2.000 cm3, flex ou alcool`, `acima de 2.000 cm3, gasolina`, `acima de 2.000 cm3, flex ou alcool`, `8703.40 (hibrido sem recarga externa)`, `8703.60 (hibrido com recarga externa)`, `8703.80 (eletrico)` |
| `vigencia_inicio`, `vigencia_fim` | periodo da aliquota |
| `aliquota_pct` | nominal, em %, com virgula decimal. IOF: % ao dia |
| `aliquota_efetiva_habilitada` | so' no IPI. De 16/12/2011 a 31/12/2017 a TIPI inclui 30 pontos; a efetiva da empresa habilitada e' a nominal menos a reducao que o proprio ato da' (30 pontos: Decreto 7.567 em 2011-2012; teto do credito presumido do Inovar-Auto, Decreto 7.819, em 2013-2017). Fora desse periodo, igual a' nominal |
| `reducao_ato_id`, `reducao_pagina`, `reducao_trecho` | o ato, a pagina e o trecho literal que fixam a reducao da habilitada |
| `derivada` | `sim` quando o ato fixa uma reducao percentual e nao a aliquota (a regra esta' na observacao): 18,5% do Decreto 10.979 sobre a TIPI de 2017 nos codigos que ele nao lista |
| `ato_id`, `pagina_salva`, `fonte_trecho` | ato, pagina (o anexo, quando a tabela esta' nele) e trecho literal |
| `observacao` | regra da derivada, leitura da tabela de eficiencia, base do IPI Verde |

## `dados/processado/politicas_mensal.parquet` (2,725 linhas, 2003-01 a 2026-08)

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

## Uso-teste (`saidas/politicas_uso_teste.csv`, 78 datas)

Uma linha por data de efeito: o inicio de cada ato e cada mudanca de aliquota que
o proprio ato fixa depois (degraus, retorno da aliquota cheia). Serie: vendas do
painel; no imposto de importacao, a importacao das NCMs do ato em unidades ajustadas;
no acordo automotivo, a importacao do agregado de carros vinda do pais parceiro.
Colunas: media dos 3 meses antes, o mes da data, media dos
3 depois, e as mesmas janelas um ano antes (o movimento sazonal).
`movimento` = `sim` quando a variacao do mes ou dos tres seguintes, contra os tres
anteriores, difere da do ano anterior em 10 pontos ou mais.
**Nao e' estimativa de efeito**: `nao` marca a data a conferir. Sem movimento:
27 de 78.

## Conferencias (`saidas/politicas_validacao.csv`)

| conferencia                                                                                                                    |   casos |   falhas |
|:-------------------------------------------------------------------------------------------------------------------------------|--------:|---------:|
| pagina guardada: arquivo presente, SHA-256 do manifesto, primeira linha com a URL                                              |      74 |        0 |
| ato: campos nas listas, datas validas, altera_id existente, pagina no manifesto com a mesma URL, fonte oficial, trecho literal |      65 |        0 |
| aliquota: tributo, NCM no formato da TIPI, ato existente, trecho literal, uma aliquota por periodo (NCM x categoria)           |     422 |        0 |
| ato sem nenhum mes na janela 2003-01 a 2026-08: nenhum                                                                         |      65 |        0 |
| IPI: categoria principal sem aliquota em algum mes (de 2003-01 ou do inicio da categoria a 2026-08): nenhuma                   |      11 |        0 |
| registro, nao falha: aliquotas derivadas (o ato fixa uma reducao percentual, nao a aliquota): 5                                |     422 |        0 |
| registro, nao falha: atos antecedentes (acabam antes da janela): ipi_2002_dec4317                                              |      65 |        0 |
| registro, nao falha: paginas guardadas que nenhum ato ou aliquota cita: dec_10923_2021_anexo_cap87, dec_11047_2022             |      74 |        0 |
| registro, nao falha: atos sem vigencia_fim (em vigor, ou fim nao confirmado): 12                                               |      65 |        0 |
