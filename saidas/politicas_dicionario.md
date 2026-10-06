# Dicionario -- calendario de politicas

Gerado por `src/etapa13_politicas.py`. Tres arquivos: duas tabelas de referencia,
escritas a' mao a partir das paginas oficiais, e uma tabela mensal derivada delas.

**So' fonte oficial.** Planalto, Diario Oficial da Uniao (visualizador de PDF da
Imprensa Nacional), gov.br (Gecex/MDIC, Contran no Ministerio dos Transportes,
Conama), Banco Central. Cada pagina esta' em `dados/bruto/politicas_paginas/`, com
URL e SHA-256 do texto no manifesto. Noticia ajudou a achar ato, nunca e' citada.

## `dados/referencia/politicas_atos.csv` (50 atos)

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
| `ipi` | 18 | 2008-12-12 | 2025-11-01 |
| `regime_automotivo` | 6 | 2013-01-01 | 2024-06-28 |
| `imposto_importacao` | 5 | 2014-09-19 | 2026-07-01 |
| `acordo_automotivo` | 7 | 2008-07-03 | 2020-07-01 |
| `credito` | 8 | 2008-01-03 | 2015-01-22 |
| `programa_desconto` | 2 | 2023-06-06 | 2023-06-07 |
| `regulacao` | 4 | 2014-01-01 | 2025-01-01 |

## `dados/referencia/politicas_aliquotas.csv` (216 linhas: ii 86, iof 6, ipi 124)

So' as aliquotas que o proprio ato fixa -- nao e' a TIPI inteira. Uma aliquota por
periodo: a linha de um ato que um ato posterior fixa de novo (mesma NCM e categoria)
vale ate' a vespera do posterior; cronograma substituido antes de valer fica fora.

| coluna | conteudo |
|---|---|
| `tributo` | `ipi`, `ii` (imposto de importacao), `iof` |
| `ncm` | com os pontos da TIPI e, quando ha', o Ex (`8703.23.10 Ex 01`, `8703.80.00 Ex 007`). Os digitos sem os pontos sao prefixo da NCM do Comex Stat (`comex_veiculos.parquet`). Vazia no IOF |
| `categoria` | faixa de cilindrada e combustivel (IPI), descricao do Ex e quota (II) |
| `vigencia_inicio`, `vigencia_fim` | periodo da aliquota |
| `aliquota_pct` | em %, com virgula decimal. IPI de 2012 a 2017: a TIPI ja' inclui os 30 pontos do Inovar-Auto (37 = 7 + 30); a empresa habilitada tinha a reducao. IOF: % ao dia |
| `ato_id`, `pagina_salva`, `fonte_trecho` | ato, pagina (o anexo, quando a tabela esta' nele) e trecho literal |

## `dados/processado/politicas_mensal.parquet` (1,924 linhas, 2008-01 a 2026-08)

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

## Uso-teste (`saidas/politicas_uso_teste.csv`, 61 datas)

Uma linha por data de efeito: o inicio de cada ato e cada mudanca de aliquota que
o proprio ato fixa depois (degraus, retorno da aliquota cheia). Serie: vendas do
painel; no imposto de importacao, a importacao das NCMs do ato em unidades ajustadas;
no acordo automotivo, a importacao do agregado de carros vinda do pais parceiro.
Colunas: media dos 3 meses antes, o mes da data, media dos
3 depois, e as mesmas janelas um ano antes (o movimento sazonal).
`movimento` = `sim` quando a variacao do mes ou dos tres seguintes, contra os tres
anteriores, difere da do ano anterior em 10 pontos ou mais.
**Nao e' estimativa de efeito**: `nao` marca a data a conferir. Sem movimento:
25 de 61.

## Conferencias (`saidas/politicas_validacao.csv`)

| conferencia                                                                                                                    |   casos |   falhas |
|:-------------------------------------------------------------------------------------------------------------------------------|--------:|---------:|
| pagina guardada: arquivo presente, SHA-256 do manifesto, primeira linha com a URL                                              |      55 |        0 |
| ato: campos nas listas, datas validas, altera_id existente, pagina no manifesto com a mesma URL, fonte oficial, trecho literal |      50 |        0 |
| aliquota: tributo, NCM no formato da TIPI, ato existente, trecho literal, uma aliquota por periodo (NCM x categoria)           |     216 |        0 |
| ato sem nenhum mes na janela 2003-01 a 2026-08: nenhum                                                                         |      50 |        0 |
| registro, nao falha: paginas guardadas que nenhum ato ou aliquota cita: dec_11047_2022                                         |      55 |        0 |
| registro, nao falha: atos sem vigencia_fim (em vigor, ou fim nao confirmado): 11                                               |      50 |        0 |
