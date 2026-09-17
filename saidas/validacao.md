# Validacao do painel de vendas de veiculos 0 km

**Commit: `113ec86-sujo`.** Os numeros deste relatorio saem desse commit, e sao conferiveis nele sem reprocessar os informes (ESPEC sec.10.3).

Gerado em 2026-09-17T17:16:56+00:00 (UTC) por `src/etapa06_validacao.py`.

- Periodo: **2003-01 a 2026-08** (284 meses)
- Linhas: painel bruto 54,183 / painel 54,179 / visao por modelo 53,700
- Unidades: 57,700,201
- Modelos (marca x modelo x segmento): 933
- Leitura de "pico movel de 12 meses": `media_movel` (QUESTOES_ABERTAS.md, Q1)
- `regras.csv` vazio por decisao desta rodada: nada foi fundido, e as taxas de entrada e saida abaixo sao o **limite superior** dessas taxas -- o cenario em que todo rebatismo conta como morte e nascimento.

## 1. Invariante central

A soma de unidades por mes tem de ser identica nos dois paineis **depois de excluidas as linhas marcadas em `duplicata_publicada`**, e essas linhas sao exatamente **4**, enumeradas abaixo. Harmonizacao redistribui rotulos; nao cria nem destroi unidades.

A excecao e' enumerada e travada por teste (`testes/test_duplicatas_publicadas.py`), nao dispensada: ela nao pode crescer sem quebrar o teste, e por isso o invariante com ela e' mais forte que o invariante sem supressao nenhuma.

| mes_ref   | segmento_fonte   | marca_fonte   | modelo_fonte   |   unidades | duplicata_publicada                      |
|:----------|:-----------------|:--------------|:---------------|-----------:|:-----------------------------------------|
| 2013-11   | automoveis       | THINK         | CITY           |       2464 | HONDA/CITY (Sedans Compactos, pg. 12)    |
| 2013-11   | comerciais_leves | PONTIAC       | MONTANA        |       3901 | GM /MONTANA (Pick-up's Pequenas, pg. 18) |
| 2013-11   | comerciais_leves | VW            | RANGER         |       1967 | FORD/RANGER (Pick-up's Grandes, pg. 18)  |
| 2013-11   | comerciais_leves | FORD          | MASTER         |        839 | RENAULT/MASTER (Furgões, pg. 18)         |

**OK** -- identica nos 284 meses.

## 2. Sanidade temporal

Cada teste roda duas vezes: no painel e no **total que a propria fonte publica**. E' a segunda rodada que diz de quem e' o erro. Painel discordando da fonte e' bug nosso -- provavelmente atribuicao de mes, por leitura de cabecalho (sec.7) -- e falha a execucao. Painel e fonte concordando entre si e discordando da premissa e' premissa nao confirmada: reportada, nao corrigida.

- Menor mes de 2014-2023: **2020-04** (50,955 unidades) -- esperado `2020-04`: OK
- Maior mes desde 2021-01: **2023-07** (213,909 unidades) -- esperado `2023-07`: OK
- Salto de 2023-06 para 2023-07: **+20.0%** no painel, +20.0% no total publicado -- esperado ao menos +15%: OK
- Maximo da serie inteira, no total publicado: **2012-08** (405,469 unidades) -- o mercado de 2014 era muito maior que o de hoje, entao o pico absoluto fica la'
- Maximo desde 2019, no total publicado: **2025-12** (267,117 unidades)

## 3. Cobertura da fonte (D5)

Total do painel contra o total que o proprio informe publica. A diferenca e' estrutural, nao erro de leitura: as tabelas por modelo da fonte tem numero fixo de linhas por sub-segmento e truncam a cauda. **O piso nao e' aplicado ao painel** -- filtrar destroi informacao de forma irreversivel, e a escolha e' de analise. O que esta rodada entrega e' a medida e uma recomendacao.

Por ano:

|   ano | segmento         |   total_painel |   total_publicado |   cobertura_pct |
|------:|:-----------------|---------------:|------------------:|----------------:|
|  2003 | automoveis       |        1209697 |           1214393 |           99.61 |
|  2003 | comerciais_leves |         130317 |            130329 |           99.99 |
|  2004 | automoveis       |        1312790 |           1314994 |           99.83 |
|  2004 | comerciais_leves |         163914 |            163926 |           99.99 |
|  2005 | automoveis       |        1435063 |           1439138 |           99.72 |
|  2005 | comerciais_leves |         180631 |            180680 |           99.97 |
|  2006 | automoveis       |        1627124 |           1632199 |           99.69 |
|  2006 | comerciais_leves |         199854 |            200272 |           99.79 |
|  2007 | automoveis       |        2074274 |           2085385 |           99.47 |
|  2007 | comerciais_leves |         256327 |            256479 |           99.94 |
|  2008 | automoveis       |        2322693 |           2341981 |           99.18 |
|  2008 | comerciais_leves |         329205 |            329455 |           99.92 |
|  2009 | automoveis       |        2624388 |           2644610 |           99.24 |
|  2009 | comerciais_leves |         364286 |            364484 |           99.95 |
|  2010 | automoveis       |        2822537 |           2857839 |           98.76 |
|  2010 | comerciais_leves |         470767 |            471025 |           99.95 |
|  2011 | automoveis       |        2840988 |           2902153 |           97.89 |
|  2011 | comerciais_leves |         522916 |            523198 |           99.95 |
|  2012 | automoveis       |        3059146 |           3115506 |           98.19 |
|  2012 | comerciais_leves |         518794 |            519000 |           99.96 |
|  2013 | automoveis       |        2986084 |           3041863 |           98.17 |
|  2013 | comerciais_leves |         533837 |            534031 |           99.96 |
|  2014 | automoveis       |        2751394 |           2795134 |           98.44 |
|  2014 | comerciais_leves |         533217 |            533583 |           99.93 |
|  2015 | automoveis       |        2095964 |           2122820 |           98.73 |
|  2015 | comerciais_leves |         354083 |            354258 |           99.95 |
|  2016 | automoveis       |        1671323 |           1687907 |           99.02 |
|  2016 | comerciais_leves |         298543 |            298614 |           99.98 |
|  2017 | automoveis       |        1841616 |           1856179 |           99.22 |
|  2017 | comerciais_leves |         316353 |            316431 |           99.98 |
|  2018 | automoveis       |        2083468 |           2101566 |           99.14 |
|  2018 | comerciais_leves |         369149 |            369338 |           99.95 |
|  2019 | automoveis       |        2238307 |           2262220 |           98.94 |
|  2019 | comerciais_leves |         397049 |            397136 |           99.98 |
|  2020 | automoveis       |        1597158 |           1615782 |           98.85 |
|  2020 | comerciais_leves |         335261 |            335300 |           99.99 |
|  2021 | automoveis       |        1539065 |           1558185 |           98.77 |
|  2021 | comerciais_leves |         416523 |            416557 |           99.99 |
|  2022 | automoveis       |        1556883 |           1574554 |           98.88 |
|  2022 | comerciais_leves |         379953 |            380021 |           99.98 |
|  2023 | automoveis       |        1700464 |           1720955 |           98.81 |
|  2023 | comerciais_leves |         457263 |            458550 |           99.72 |
|  2024 | automoveis       |        1918507 |           1948404 |           98.47 |
|  2024 | comerciais_leves |         536447 |            536649 |           99.96 |
|  2025 | automoveis       |        1950172 |           1996751 |           97.67 |
|  2025 | comerciais_leves |         552057 |            552500 |           99.92 |
|  2026 | automoveis       |        1448814 |           1512141 |           95.81 |
|  2026 | comerciais_leves |         375536 |            375878 |           99.91 |

Meses-segmento sem total publicado legivel (fora dos agregados): **0**

Tabela mes a mes em `saidas/cobertura.csv`.

**Correcao ao diagnostico de retroacao.** O diagnostico previa 2003 e 2005 como os anos de cobertura mais fraca (95,4% e 95,0% em automoveis) e pedia que fossem registrados como tal. A extracao completa desmente isso: os dois ficam em 99,6% e 99,7%, na faixa dos melhores anos da serie. A diferenca e' de metodo, nao de dado -- o diagnostico somava so' a tabela por sub-segmento e tirava media entre meses, enquanto o painel tambem usa o ranking mensal para completar a cauda. Os 4 pontos inteiros vinham de **dois meses**, 2003-10 e 2005-03, cujas edicoes curtas nao trazem tabela por sub-segmento (sec.7). Os anos de cobertura mais fraca da serie inteira sao 2026 (95,8%, parcial), 2025 (97,7%) e 2011 (97,9%) -- todos recentes.

### Tendencia da cobertura

Cobertura que anda ao longo da serie contamina qualquer comparacao de taxas entre anos: o painel de 2026 nao ve a mesma parte do mercado que o de 2014.

| segmento         |   primeiro_ano |   cobertura_primeiro |   ultimo_ano |   cobertura_ultimo |   variacao_pp |   amplitude_pp |
|:-----------------|---------------:|---------------------:|-------------:|-------------------:|--------------:|---------------:|
| automoveis       |           2003 |                99.61 |         2026 |              95.81 |         -3.8  |           4.02 |
| comerciais_leves |           2003 |                99.99 |         2026 |              99.91 |         -0.08 |           0.27 |

**Risco identificado:** automoveis anda -3.80 pontos percentuais entre 2003 e 2026. As taxas de entrada e saida da sec.8 tem de ser lidas com isso em mente; a coluna do subconjunto imune ao corte existe para separar os efeitos.

### Piso recomendado (nao aplicado)

Para cada piso candidato sobre as unidades mensais do modelo: a cobertura anual que resulta, sua amplitude entre anos, e o volume que ficaria de fora. O recomendado e' o que deixa a fracao coberta mais parecida entre os anos.

|   piso_unidades_mes |   cobertura_min_pct |   cobertura_max_pct |   amplitude_pp |   desvio_padrao_pp |   linhas_descartadas |   volume_descartado |   volume_descartado_pct | recomendado   |
|--------------------:|--------------------:|--------------------:|---------------:|-------------------:|---------------------:|--------------------:|------------------------:|:--------------|
|                   0 |               96.63 |               99.85 |           3.22 |              0.664 |                    0 |                   0 |                   0     | False         |
|                   1 |               96.63 |               99.85 |           3.22 |              0.664 |                 3836 |                   0 |                   0     | False         |
|                   5 |               96.61 |               99.8  |           3.18 |              0.655 |                10586 |               13171 |                   0.023 | False         |
|                  10 |               96.58 |               99.74 |           3.16 |              0.648 |                13575 |               33351 |                   0.058 | False         |
|                  25 |               96.47 |               99.52 |           3.06 |              0.623 |                18184 |              106941 |                   0.185 | False         |
|                  50 |               96.33 |               99.12 |           2.79 |              0.576 |                21837 |              237800 |                   0.412 | False         |
|                 100 |               96.02 |               98.52 |           2.5  |              0.517 |                26076 |              544623 |                   0.944 | False         |
|                 150 |               95.68 |               98.13 |           2.45 |              0.529 |                28635 |              859463 |                   1.49  | True          |
|                 200 |               95.36 |               97.82 |           2.46 |              0.58  |                30528 |             1188260 |                   2.059 | False         |
|                 300 |               94.47 |               97.27 |           2.8  |              0.789 |                33168 |             1835573 |                   3.181 | False         |
|                 400 |               92.33 |               96.73 |           4.4  |              1.11  |                34946 |             2454735 |                   4.254 | False         |
|                 500 |               90.9  |               95.65 |           4.75 |              1.246 |                36289 |             3056078 |                   5.296 | False         |
|                 750 |               87.98 |               93.26 |           5.28 |              1.344 |                38773 |             4593583 |                   7.961 | False         |
|                1000 |               84.51 |               89.93 |           5.42 |              1.637 |                40891 |             6433638 |                  11.15  | False         |

**Recomendacao:** piso de **150 unidades por modelo e mes**, que deixa a cobertura anual entre 95.68% e 98.13% (amplitude de 2.45 pontos) e descartaria 859.463 unidades (1.49% do painel). Registrado como parametro; nao gravado no dado.

## 4. Onde a fonte corta a cauda

A truncagem da Fenabrave **nao e' um piso de unidades**: e' numero fixo de linhas por sub-segmento. "Suv's" traz exatamente 40 modelos nos 152 meses; "Furgoes", 7; "Sedans Grandes", 12. Sub-segmento com menos modelos que o teto nao trunca nada. Logo o corte que vale para um modelo e' o do **bloco** em que ele seria listado, quando aquele bloco esta' no teto -- e nao o menor valor publicado no mes inteiro, que mede o tamanho do menor modelo da fonte, nao a truncagem.

|   ano | segmento         |   blocos |   blocos_no_teto |   corte_mediano |   corte_maximo |
|------:|:-----------------|---------:|-----------------:|----------------:|---------------:|
|  2003 | automoveis       |      144 |               76 |             4.5 |            298 |
|  2003 | comerciais_leves |       44 |               38 |            48   |             78 |
|  2004 | automoveis       |      156 |               97 |            10   |            516 |
|  2004 | comerciais_leves |       48 |               47 |            24   |             83 |
|  2005 | automoveis       |      144 |               86 |            13   |            421 |
|  2005 | comerciais_leves |       44 |               40 |            30   |            100 |
|  2006 | automoveis       |      156 |              103 |            21   |           1446 |
|  2006 | comerciais_leves |       48 |               43 |            58   |            120 |
|  2007 | automoveis       |      156 |              102 |            19   |           1788 |
|  2007 | comerciais_leves |       48 |               47 |            86.5 |            141 |
|  2008 | automoveis       |      156 |              115 |            17   |           1393 |
|  2008 | comerciais_leves |       48 |               47 |            98   |            214 |
|  2009 | automoveis       |      156 |              125 |            13.5 |           1030 |
|  2009 | comerciais_leves |       48 |               47 |            60   |            184 |
|  2010 | automoveis       |      156 |              130 |            12   |           1761 |
|  2010 | comerciais_leves |       48 |               48 |           112   |            311 |
|  2011 | automoveis       |      156 |              127 |            40   |           1193 |
|  2011 | comerciais_leves |       48 |               48 |           207   |            422 |
|  2012 | automoveis       |      156 |              131 |            15   |           1400 |
|  2012 | comerciais_leves |       48 |               48 |           129   |            445 |
|  2013 | automoveis       |      156 |              132 |            14.5 |           1070 |
|  2013 | comerciais_leves |       48 |               48 |            47   |            307 |
|  2014 | automoveis       |      156 |              132 |            21   |            528 |
|  2014 | comerciais_leves |       48 |               48 |            25.5 |            270 |
|  2015 | automoveis       |      156 |              132 |            12.5 |            339 |
|  2015 | comerciais_leves |       48 |               48 |            28.5 |            177 |
|  2016 | automoveis       |      156 |              128 |             7.5 |            287 |
|  2016 | comerciais_leves |       48 |               40 |            24   |             93 |
|  2017 | automoveis       |      156 |              122 |             4   |             56 |
|  2017 | comerciais_leves |       48 |               46 |            11   |             65 |
|  2018 | automoveis       |      156 |              128 |             8   |            314 |
|  2018 | comerciais_leves |       48 |               36 |            21   |            156 |
|  2019 | automoveis       |      156 |              128 |             6   |            346 |
|  2019 | comerciais_leves |       48 |               46 |            13.5 |            189 |
|  2020 | automoveis       |      156 |              129 |            11   |            173 |
|  2020 | comerciais_leves |       48 |               40 |            50   |            195 |
|  2021 | automoveis       |      156 |              127 |             3   |            116 |
|  2021 | comerciais_leves |       48 |               42 |            25   |            248 |
|  2022 | automoveis       |      156 |              118 |             3   |             71 |
|  2022 | comerciais_leves |       48 |               47 |            39.5 |            189 |
|  2023 | automoveis       |      142 |              101 |             4   |            105 |
|  2023 | comerciais_leves |       44 |               35 |           116   |            251 |
|  2024 | automoveis       |      155 |              107 |             6   |            498 |
|  2024 | comerciais_leves |       48 |               42 |           120   |            554 |
|  2025 | automoveis       |      146 |               99 |             3   |            132 |
|  2025 | comerciais_leves |       48 |               36 |           152   |            684 |
|  2026 | automoveis       |      104 |               75 |             6   |            432 |
|  2026 | comerciais_leves |       32 |               24 |           172   |            438 |

## 5. Contagem de modelos por ano

A fonte nao publica contagem de modelos: a contagem abaixo e' a do painel, que por construcao e' a dos modelos listados nos informes. A coluna de referencia vem da planilha de controle da sec.7, que **nao e' fonte**.

|   ano |   modelos |   marcas |    unidades |   ref_modelos_sec7 |   ref_total_sec7 |   diferenca_modelos |
|------:|----------:|---------:|------------:|-------------------:|-----------------:|--------------------:|
|  2003 |       231 |       44 | 1.34001e+06 |                nan |    nan           |                 nan |
|  2004 |       227 |       37 | 1.4767e+06  |                nan |    nan           |                 nan |
|  2005 |       220 |       40 | 1.61569e+06 |                nan |    nan           |                 nan |
|  2006 |       226 |       38 | 1.82698e+06 |                nan |    nan           |                 nan |
|  2007 |       236 |       40 | 2.3306e+06  |                nan |    nan           |                 nan |
|  2008 |       252 |       41 | 2.6519e+06  |                nan |    nan           |                 nan |
|  2009 |       259 |       41 | 2.98867e+06 |                nan |    nan           |                 nan |
|  2010 |       259 |       40 | 3.2933e+06  |                nan |    nan           |                 nan |
|  2011 |       259 |       42 | 3.3639e+06  |                nan |    nan           |                 nan |
|  2012 |       250 |       43 | 3.57794e+06 |                nan |    nan           |                 nan |
|  2013 |       237 |       44 | 3.51992e+06 |                nan |    nan           |                 nan |
|  2014 |       234 |       43 | 3.28461e+06 |                310 |      3.32563e+06 |                 -76 |
|  2015 |       251 |       45 | 2.45005e+06 |                nan |    nan           |                 nan |
|  2016 |       260 |       49 | 1.96987e+06 |                301 |      1.9865e+06  |                 -41 |
|  2017 |       269 |       45 | 2.15797e+06 |                nan |    nan           |                 nan |
|  2018 |       259 |       46 | 2.45262e+06 |                nan |    nan           |                 nan |
|  2019 |       260 |       43 | 2.63536e+06 |                nan |    nan           |                 nan |
|  2020 |       253 |       46 | 1.93242e+06 |                299 |      1.94989e+06 |                 -46 |
|  2021 |       251 |       43 | 1.95559e+06 |                nan |    nan           |                 nan |
|  2022 |       250 |       41 | 1.93684e+06 |                270 |      1.95279e+06 |                 -20 |
|  2023 |       254 |       43 | 2.15773e+06 |                nan |    nan           |                 nan |
|  2024 |       242 |       42 | 2.45495e+06 |                nan |    nan           |                 nan |
|  2025 |       226 |       45 | 2.50223e+06 |                nan |    nan           |                 nan |
|  2026 |       231 |       46 | 1.82435e+06 |                nan |    nan           |                 nan |

### Agregacao da fonte: nomes compostos

`VW/FOX/CROSS FOX` e' um registro unico para o que a planilha de controle tratava como dois modelos. Contar quantos nomes trazem barra depois da marca mede quanto da diferenca de contagem e' **agregacao da fonte** em vez de truncamento -- as duas hipoteses de I1, com implicacoes opostas. Se for agregacao, nao ha' perda de cobertura: e' a unidade de observacao sendo definida pela fonte.

|   ano |   linhas |   unidades |   nomes |
|------:|---------:|-----------:|--------:|
|  2003 |        4 |       6001 |       2 |
|  2004 |       12 |      54383 |       1 |
|  2005 |       12 |      94962 |       1 |
|  2006 |       12 |     107600 |       1 |
|  2007 |       12 |     126291 |       1 |
|  2008 |       12 |     115059 |       1 |
|  2009 |       12 |     129179 |       1 |
|  2010 |       12 |     143427 |       1 |
|  2011 |       12 |     121584 |       1 |
|  2012 |       12 |     167683 |       1 |
|  2013 |       12 |     129925 |       1 |
|  2014 |       12 |     101336 |       1 |
|  2015 |       12 |      79595 |       1 |
|  2016 |       12 |      43730 |       1 |
|  2017 |       12 |      42719 |       1 |
|  2018 |       12 |      39213 |       1 |
|  2019 |       12 |      38486 |       1 |
|  2020 |       16 |      21677 |       2 |
|  2021 |       24 |      21478 |       2 |
|  2022 |       13 |       2148 |       2 |
|  2023 |        7 |        931 |       2 |

Os de maior volume:

| marca_fonte   | modelo_fonte            |   unidades | primeiro_mes   | ultimo_mes   |
|:--------------|:------------------------|-----------:|:---------------|:-------------|
| VW            | FOX/CROSS FOX           |    1579510 | 2003-10        | 2022-01      |
| VW            | MAN/EXPRESS             |       7892 | 2020-09        | 2023-06      |
| RENAULT       | MARCOPOLO/VOLARE V9L EO |          4 | 2023-06        | 2023-06      |
| MPLM          | MPLM/JAVALI             |          1 | 2003-12        | 2003-12      |

## 6. Concentracao: marca e grupo

Agrupar marcas so' pode **aumentar** o HHI -- desde que a particao seja a mesma para tudo o que se soma. Num agregado anual com mapa datado ela nao e': em 2014 a FIAT esta' no grupo `FIAT` ate' setembro e em `FCA` de outubro em diante, e o volume anual da marca se parte em dois grupos. Por isso a identidade e' exigida **por mes**, onde a particao e' fixa, e o agregado anual usa o grupo vigente num mes de referencia declarado.

**OK** -- `hhi_grupo >= hhi_marca` nos 284 meses.

|   ano | mes_referencia_do_grupo   |   hhi_marca |   hhi_grupo_particao_fixa |   hhi_grupo_datado |   marcas_que_mudam_de_grupo_no_ano |   volume_dessas_marcas |   ref_hhi_marca_sec7 |
|------:|:--------------------------|------------:|--------------------------:|-------------------:|-----------------------------------:|-----------------------:|---------------------:|
|  2003 | 2003-12                   |      1878.3 |                    1913.9 |             1913.9 |                                  0 |                      0 |                  nan |
|  2004 | 2004-12                   |      1831.2 |                    1861.7 |             1861.7 |                                  0 |                      0 |                  nan |
|  2005 | 2005-12                   |      1806.4 |                    1834.3 |             1834.3 |                                  0 |                      0 |                  nan |
|  2006 | 2006-12                   |      1832.1 |                    1854.8 |             1854.8 |                                  0 |                      0 |                  nan |
|  2007 | 2007-12                   |      1831.3 |                    1851.9 |             1851.9 |                                  0 |                      0 |                  nan |
|  2008 | 2008-12                   |      1688.1 |                    1707.8 |             1709   |                                  1 |                   4295 |                  nan |
|  2009 | 2009-12                   |      1691.1 |                    1710.4 |             1710.4 |                                  0 |                      0 |                  nan |
|  2010 | 2010-12                   |      1544   |                    1570.8 |             1571.5 |                                  1 |                   1700 |                  nan |
|  2011 | 2011-12                   |      1438.5 |                    1468.9 |             1468.9 |                                  0 |                      0 |                  nan |
|  2012 | 2012-12                   |      1498.2 |                    1513.6 |             1513.6 |                                  1 |                     22 |                  nan |
|  2013 | 2013-12                   |      1386.6 |                    1406.1 |             1406.1 |                                  0 |                      0 |                  nan |
|  2014 | 2014-12                   |      1317.4 |                    1349   |             1169.5 |                                  3 |                 700384 |                 1297 |
|  2015 | 2015-12                   |      1122.8 |                    1219   |             1219   |                                  0 |                      0 |                  nan |
|  2016 | 2016-12                   |      1069   |                    1189.6 |             1189.6 |                                  0 |                      0 |                 1055 |
|  2017 | 2017-12                   |      1059.4 |                    1191.8 |             1191.8 |                                  0 |                      0 |                  nan |
|  2018 | 2018-12                   |      1080.6 |                    1217.8 |             1217.8 |                                  0 |                      0 |                  nan |
|  2019 | 2019-12                   |      1110.2 |                    1265.2 |             1265.2 |                                  0 |                      0 |                  nan |
|  2020 | 2020-12                   |      1165.1 |                    1378   |             1378   |                                  0 |                      0 |                 1146 |
|  2021 | 2021-12                   |      1191   |                    1712.3 |             1712.3 |                                  0 |                      0 |                  nan |
|  2022 | 2022-12                   |      1226.6 |                    1798.5 |             1798.5 |                                  0 |                      0 |                 1208 |
|  2023 | 2023-12                   |      1228   |                    1731.5 |             1731.5 |                                  0 |                      0 |                  nan |
|  2024 | 2024-12                   |      1129.3 |                    1557.6 |             1557.6 |                                  0 |                      0 |                  nan |
|  2025 | 2025-12                   |      1108.4 |                    1533.9 |             1533.9 |                                  0 |                      0 |                  nan |
|  2026 | 2026-08                   |      1036.9 |                    1359.2 |             1359.2 |                                  0 |                      0 |                  nan |

Anos com mudanca de propriedade no meio: 2008 (1 marcas, 4.295 unidades); 2010 (1 marcas, 1.700 unidades); 2012 (1 marcas, 22 unidades); 2014 (3 marcas, 700.384 unidades). Neles `hhi_grupo_datado` fica abaixo de `hhi_marca` por construcao, e a coluna de particao fixa e' a comparavel.

Marcas sem grupo vigente no mapa, tratadas como **grupo unitario com o proprio nome**: **30** marcas, 3.209 unidades (0.006% do painel). Nenhuma e' excluida do calculo nem somada num balde comum: as duas coisas distorceriam o indice em direcoes opostas.

| marca        |   unidades |
|:-------------|-----------:|
| RELY         |       2181 |
| ASA          |        415 |
| FEVER        |        125 |
| CROSS LANDER |        118 |
| ASIA         |        118 |
| ARROW        |         52 |
| WILLYS       |         37 |
| VICR         |         32 |
| HITECH E     |         29 |
| HITECH       |         21 |
| MATRA        |         14 |
| ENGESA       |         13 |
| MON          |         12 |
| AMGC HUMER   |         11 |
| EDRA         |          5 |
| VICTORY      |          4 |
| FARGO        |          3 |
| JPX          |          3 |
| KARRY        |          2 |
| LVTONG       |          2 |
| MG           |          2 |
| DKW          |          2 |
| FREIGHTLINER |          1 |
| DATSUM       |          1 |
| CBP          |          1 |

_(5 linhas restantes omitidas; ver CSV correspondente.)_

## 7. Ausencias

- Linhas com unidades negativas: **0** (OK)
- Modelos com serie integralmente nula: **8**: `AMGC HUMER/HMC4 6.5T` (automoveis), `CHEVROLET/SPORT VAN` (automoveis), `ENGESA/ENVEMO CAMPER` (automoveis), `GM/BONANZA` (automoveis), `GM/DLX` (automoveis), `LAND ROVER/LAND ROVER` (automoveis), `LEXUS/IS 350` (automoveis), `MITSUBISHI/SMART` (automoveis)
- Nomes sem marca resolvida: **0** linhas
- Nomes que provavelmente **nao designam veiculo**: **28** modelos, 1.448 unidades -- `FIAT/FIAT`, `FORD/ENGERAUTO SPARTAKUS`, `TOYOTA/RIBEIRAUTO`. Nada foi apagado: a coluna `nome_suspeito` marca as linhas e `saidas/nomes_suspeitos.csv` traz os 180 candidatos a revisao humana (marcados, mais os de volume infimo que ninguem olhou ainda).

| marca            | modelo              |   unidades |   meses | motivo                                                                                                       |
|:-----------------|:--------------------|-----------:|--------:|:-------------------------------------------------------------------------------------------------------------|
| CADILLAC         | CADILLAC            |          1 |       1 | nome do modelo igual ao da marca                                                                             |
| DATSUM           | DATSUM              |          1 |       1 | nome do modelo igual ao da marca                                                                             |
| FIAT             | FAG                 |          1 |       1 | FAG nao corresponde a nenhum modelo Fiat; registro avulso de uma unidade.                                    |
| FIAT             | FIAT                |          1 |       1 | nome do modelo igual ao da marca                                                                             |
| FIAT             | PICK UP             |          1 |       1 | Descricao generica de carroceria, nao nome de modelo.                                                        |
| FORD             | ENGERAUTO SPARTAKUS |          1 |       1 | Engerauto e' encarrocador; 'Spartakus' e' a linha de transformacao, nao um modelo de fabrica.                |
| GMC              | GMC                 |          1 |       1 | nome do modelo igual ao da marca                                                                             |
| HAFEI            | PICK UP             |          1 |       1 | Descricao generica de carroceria, nao nome de modelo.                                                        |
| INTERNATIONAL    | INTERNATIONAL       |          1 |       1 | nome do modelo igual ao da marca                                                                             |
| NISSAN           | NISSAN              |          1 |       1 | nome do modelo igual ao da marca                                                                             |
| NÃO IDENTIFICADO | EE34                |          1 |       1 | Marcador da propria fonte para registro sem marca identificada; vale para qualquer modelo publicado sob ele. |
| OPEL             | OPEL                |          1 |       1 | nome do modelo igual ao da marca                                                                             |

_(16 linhas restantes omitidas; ver CSV correspondente.)_

- Grafias unificadas por caixa na chave do modelo (D1): **2** -- `MITSUBISHI/Outlander` e `MITSUBISHI/OUTLANDER` sao o mesmo carro, e sem a normalizacao virariam duas fichas, com uma saida e uma entrada fabricadas. A grafia crua segue em `grafias_fonte` e `nome_completo_fonte`.

| marca      | modelo    | segmento   | marca_chave   | modelo_chave   | segmento_chave   |
|:-----------|:----------|:-----------|:--------------|:---------------|:-----------------|
| MITSUBISHI | Outlander | automoveis | MITSUBISHI    | OUTLANDER      | AUTOMOVEIS       |
| MITSUBISHI | OUTLANDER | automoveis | MITSUBISHI    | OUTLANDER      | AUTOMOVEIS       |
- Marcas fora de `config/marcas.csv`: **1**

### Lacunas de mes

Mes sem informe baixado, e mes cujo informe nao rendeu nenhuma linha. Lacuna e' lacuna: nao se preenche, nao se interpola, nao se estima (sec.9.2). Nas series de D3 estes meses entram como ausentes, nunca como zero. Mes recuperado pela coluna de mes anterior do informe seguinte **nao** e' lacuna: e' segunda publicacao do mesmo numero pela mesma fonte.

0 lacunas.

_(vazio)_

Meses do intervalo sem nenhuma linha no painel: **0**

### Edicoes curtas do informe

O informe normal traz 44 paginas e 17 sub-segmentos na tabela por modelo. **2** meses da serie sairam com uma edicao curta -- 10 paginas -- e trazem **um** sub-segmento. Ali o mes e' carregado quase inteiro pelo ranking mensal: o **total bate** com o publicado, porque o ranking cobre o topo, mas o **elenco de modelos fica pela metade** (89 e 87 fichas contra cerca de 180 nos meses vizinhos).

Consequencia para quem usa a serie: nesses dois meses um modelo de cauda some sem ter saido do mercado. Nao vira saida -- D3 olha o pico movel de 12 meses --, mas vira zero fragil e entra na contagem de modelos do ano. **Nada foi completado** (sec.9.4): a coluna do mes anterior do informe seguinte poderia recuperar o elenco, do mesmo jeito que recuperou 2023-09, mas isso misturaria linha lida direto com linha republicada dentro do mesmo mes, e a regra de mistura e' decisao do pesquisador, nao do codigo.

| mes_ref   |   linhas_total |   linhas_sub_segmento |   sub_segmentos |   sub_segmentos_tipicos |   fracao_do_tipico | situacao                           |
|:----------|---------------:|----------------------:|----------------:|------------------------:|-------------------:|:-----------------------------------|
| 2003-10   |             89 |                     9 |               1 |                      17 |              0.059 | edicao curta do informe            |
| 2005-03   |             87 |                     9 |               1 |                      17 |              0.059 | edicao curta do informe            |
| 2023-09   |            167 |                     0 |               0 |                      17 |              0     | mes recuperado do informe seguinte |

### Meses recuperados do informe seguinte

| mes     | mes_fonte   |   linhas |   modelos_conferidos_pelo_acumulado |   modelos_divergentes |   divergencia_absoluta |   divergencia_liquida | observacao                                                                                                                              |
|:--------|:------------|---------:|------------------------------------:|----------------------:|-----------------------:|----------------------:|:----------------------------------------------------------------------------------------------------------------------------------------|
| 2023-09 | 2023-10     |      167 |                                 151 |                    29 |                     39 |                   -37 | 167 linhas recuperadas do informe de 2023-10; rota do acumulado confere 122 de 151 modelos; diferenca absoluta 39 unidades, liquida -37 |

## 8. Taxas de entrada e saida por ano (D3)

**Leia a advertencia antes da tabela.** Estas taxas nao medem so' rotatividade de portfolio: medem rotatividade **mais ruido de cadastro**, em proporcao parecida. A decomposicao por piso de volume, logo abaixo, e' o que separa uma coisa da outra, e nenhuma leitura substantiva deve sair da coluna "todos".

Alem disso, **2026 e' ano parcial** (a amostra termina em 2026-08): contar saidas num ano incompleto infla a taxa por conta propria, e o numero nao e' citavel para rotatividade.

**Assimetria declarada (I2):** a entrada e' o primeiro mes com unidades positivas e **nao depende do limiar**; so' a saida usa D3, que foi o que a ESPEC especificou. Por isso as colunas de entrada sao identicas entre limiares -- e' desenho, nao defeito.

### Quem sao os modelos que entram e saem

Distribuicao dos modelos por volume total no periodo inteiro:

| faixa_de_volume   |   modelos |   pct_dos_modelos |   unidades |   pct_das_unidades |
|:------------------|----------:|------------------:|-----------:|-------------------:|
| ate 10            |       234 |              25.1 |        638 |              0.001 |
| 11 a 100          |       129 |              13.8 |       5292 |              0.009 |
| 101 a 1.000       |       161 |              17.3 |      62537 |              0.108 |
| 1.001 a 10.000    |       168 |              18   |     639704 |              1.109 |
| acima de 10.000   |       241 |              25.8 |   56992030 |             98.773 |

**363 modelos -- 39% da contagem -- somam 5.930 unidades em 24 anos**, 0.010% do volume. Sao registros avulsos, conversoes de encarrocador e erros de cadastro da fonte; `saidas/nomes_suspeitos.csv` lista os que nem sequer designam veiculo. Cada um deles conta como **uma entrada e uma saida**:

|   ano |   entradas |   entradas_ate_100 |   saidas |   saidas_ate_100 |   pct_entradas_ate_100 |   pct_saidas_ate_100 |
|------:|-----------:|-------------------:|---------:|-----------------:|-----------------------:|---------------------:|
|  2003 |         85 |                 59 |       29 |               24 |                     69 |                   83 |
|  2004 |         44 |                 26 |       31 |               26 |                     59 |                   84 |
|  2005 |         29 |                 13 |       23 |               18 |                     45 |                   78 |
|  2006 |         39 |                 15 |       22 |               18 |                     38 |                   82 |
|  2007 |         34 |                 16 |       30 |               25 |                     47 |                   83 |
|  2008 |         47 |                 20 |       28 |               17 |                     43 |                   61 |
|  2009 |         41 |                 18 |       31 |               20 |                     44 |                   65 |
|  2010 |         36 |                 15 |       32 |               16 |                     42 |                   50 |
|  2011 |         43 |                 11 |       30 |               13 |                     26 |                   43 |
|  2012 |         20 |                  2 |       20 |                5 |                     10 |                   25 |
|  2013 |         20 |                  4 |       25 |                7 |                     20 |                   28 |
|  2014 |         16 |                  3 |       24 |                5 |                     19 |                   21 |
|  2015 |         23 |                  7 |       22 |                8 |                     30 |                   36 |
|  2016 |         27 |                  9 |       40 |               10 |                     33 |                   25 |
|  2017 |         28 |                  8 |       28 |               10 |                     29 |                   36 |
|  2018 |         33 |                 19 |       39 |               15 |                     58 |                   38 |
|  2019 |         23 |                 11 |       38 |               10 |                     48 |                   26 |
|  2020 |         37 |                 11 |       37 |               17 |                     30 |                   46 |
|  2021 |         25 |                 13 |       40 |               10 |                     52 |                   25 |
|  2022 |         26 |                  9 |       30 |               13 |                     35 |                   43 |
|  2023 |         29 |                 11 |       42 |               16 |                     38 |                   38 |
|  2024 |         24 |                  9 |       41 |               16 |                     38 |                   39 |
|  2025 |         28 |                  9 |       44 |                8 |                     32 |                   18 |
|  2026 |         22 |                  8 |       52 |               23 |                     36 |                   44 |

### Taxas por piso de volume total do modelo

O piso entra no numerador **e** no denominador: restringe quem pode entrar ou sair e quem conta como ativo. Nada e' filtrado do painel -- a Parte 0 continua valendo --, so' a medida e' decomposta.

Taxa de saida:

|   ano |   taxa_saida_5% [todos] |   taxa_saida_5% [acima de 100] |   taxa_saida_5% [acima de 1000] |
|------:|------------------------:|-------------------------------:|--------------------------------:|
|  2003 |                  0.1255 |                         0.035  |                          0      |
|  2004 |                  0.1366 |                         0.0323 |                          0      |
|  2005 |                  0.1045 |                         0.0312 |                          0.0075 |
|  2006 |                  0.0973 |                         0.0229 |                          0.0068 |
|  2007 |                  0.1271 |                         0.0267 |                          0.0191 |
|  2008 |                  0.1111 |                         0.0531 |                          0.0281 |
|  2009 |                  0.1197 |                         0.0509 |                          0.0376 |
|  2010 |                  0.1236 |                         0.0734 |                          0.0513 |
|  2011 |                  0.1158 |                         0.0746 |                          0.0664 |
|  2012 |                  0.08   |                         0.0649 |                          0.0714 |
|  2013 |                  0.1055 |                         0.0807 |                          0.08   |
|  2014 |                  0.1026 |                         0.0841 |                          0.0761 |
|  2015 |                  0.0876 |                         0.0609 |                          0.0597 |
|  2016 |                  0.1538 |                         0.1277 |                          0.1089 |
|  2017 |                  0.1041 |                         0.0744 |                          0.0537 |
|  2018 |                  0.1506 |                         0.1071 |                          0.0765 |
|  2019 |                  0.1462 |                         0.1233 |                          0.1015 |
|  2020 |                  0.1462 |                         0.0913 |                          0.0939 |
|  2021 |                  0.1594 |                         0.1364 |                          0.1311 |
|  2022 |                  0.12   |                         0.0787 |                          0.0678 |
|  2023 |                  0.1654 |                         0.1182 |                          0.0739 |
|  2024 |                  0.1694 |                         0.1174 |                          0.0955 |
|  2025 |                  0.1947 |                         0.1739 |                          0.1488 |
|  2026 |                  0.2251 |                         0.1429 |                          0.0843 |

Taxa de entrada:

|   ano |   taxa_entrada_5% [todos] |   taxa_entrada_5% [acima de 100] |   taxa_entrada_5% [acima de 1000] |
|------:|--------------------------:|---------------------------------:|----------------------------------:|
|  2003 |                    0.368  |                           0.1818 |                            0.1849 |
|  2004 |                    0.1938 |                           0.1161 |                            0.0787 |
|  2005 |                    0.1318 |                           0.1    |                            0.0752 |
|  2006 |                    0.1726 |                           0.1371 |                            0.1164 |
|  2007 |                    0.1441 |                           0.0963 |                            0.0828 |
|  2008 |                    0.1865 |                           0.1304 |                            0.1348 |
|  2009 |                    0.1583 |                           0.1065 |                            0.086  |
|  2010 |                    0.139  |                           0.0963 |                            0.0923 |
|  2011 |                    0.166  |                           0.1404 |                            0.1374 |
|  2012 |                    0.08   |                           0.0779 |                            0.0667 |
|  2013 |                    0.0844 |                           0.0717 |                            0.05   |
|  2014 |                    0.0684 |                           0.0575 |                            0.0305 |
|  2015 |                    0.0916 |                           0.0696 |                            0.0647 |
|  2016 |                    0.1038 |                           0.0766 |                            0.0396 |
|  2017 |                    0.1041 |                           0.0826 |                            0.0585 |
|  2018 |                    0.1274 |                           0.0625 |                            0.0408 |
|  2019 |                    0.0885 |                           0.0529 |                            0.0355 |
|  2020 |                    0.1462 |                           0.1187 |                            0.0773 |
|  2021 |                    0.0996 |                           0.0545 |                            0.0546 |
|  2022 |                    0.104  |                           0.0787 |                            0.0565 |
|  2023 |                    0.1142 |                           0.0818 |                            0.0511 |
|  2024 |                    0.0992 |                           0.0704 |                            0.0506 |
|  2025 |                    0.1239 |                           0.0918 |                            0.0655 |
|  2026 |                    0.0952 |                           0.069  |                            0.0723 |

Contagens e denominadores completos em `saidas/taxas_por_piso_de_volume.csv`.

### A segunda familia de piso: pico mensal

O piso de volume total **nao e' neutro quanto a' longevidade**. Volume total e' venda mensal media vezes meses de vida, entao um piso sobre ele descarta preferencialmente modelo de vida curta -- que sao exatamente os que contribuem com uma entrada e uma saida. Um piso que morde a variavel dependente nao serve sozinho de prova.

O piso sobre o **pico mensal** nao tem esse vies: um modelo que vendeu 500 num mes so' passa, e um que vendeu 3 por mes durante dez anos nao. Conclusao que sobrevive as duas familias nao e' artefato da escolha do piso.

|   ano |   taxa_saida_5% [todos] |   taxa_saida_5% [pico >= 10/mes] |   taxa_saida_5% [pico >= 50/mes] |
|------:|------------------------:|---------------------------------:|---------------------------------:|
|  2003 |                  0.1255 |                           0.0408 |                           0.0312 |
|  2004 |                  0.1366 |                           0.044  |                           0.0219 |
|  2005 |                  0.1045 |                           0.0373 |                           0.0144 |
|  2006 |                  0.0973 |                           0.0339 |                           0.0133 |
|  2007 |                  0.1271 |                           0.0374 |                           0.0314 |
|  2008 |                  0.1111 |                           0.058  |                           0.0278 |
|  2009 |                  0.1197 |                           0.0607 |                           0.0423 |
|  2010 |                  0.1236 |                           0.078  |                           0.0657 |
|  2011 |                  0.1158 |                           0.0833 |                           0.0714 |
|  2012 |                  0.08   |                           0.0652 |                           0.0725 |
|  2013 |                  0.1055 |                           0.1004 |                           0.0846 |
|  2014 |                  0.1026 |                           0.0969 |                           0.0896 |
|  2015 |                  0.0876 |                           0.0655 |                           0.0683 |
|  2016 |                  0.1538 |                           0.1288 |                           0.1058 |
|  2017 |                  0.1041 |                           0.0868 |                           0.0711 |
|  2018 |                  0.1506 |                           0.1091 |                           0.09   |
|  2019 |                  0.1462 |                           0.1256 |                           0.1139 |
|  2020 |                  0.1462 |                           0.0922 |                           0.086  |
|  2021 |                  0.1594 |                           0.1448 |                           0.1421 |
|  2022 |                  0.12   |                           0.0963 |                           0.0789 |
|  2023 |                  0.1654 |                           0.1182 |                           0.0947 |
|  2024 |                  0.1694 |                           0.1168 |                           0.1211 |
|  2025 |                  0.1947 |                           0.184  |                           0.1778 |
|  2026 |                  0.2251 |                           0.1442 |                           0.1136 |

Contagens completas em `saidas/taxas_por_piso_de_pico.csv`.

#### As duas familias lado a lado

Se a conclusao depende de qual piso se escolhe, ela nao e' conclusao. Aqui nao depende:

| familia      | piso           |   2022 -> 2025 |   2025 -> 2026 |
|:-------------|:---------------|---------------:|---------------:|
| volume total | todos          |         0.0747 |         0.0304 |
| volume total | acima de 100   |         0.0952 |        -0.031  |
| volume total | acima de 1000  |         0.081  |        -0.0645 |
| pico mensal  | todos          |         0.0747 |         0.0304 |
| pico mensal  | pico >= 10/mes |         0.0877 |        -0.0398 |
| pico mensal  | pico >= 50/mes |         0.0989 |        -0.0642 |

**A alta de 2022 a 2025 sobrevive as duas familias e fica mais forte com piso em ambas** -- nao e' artefato do corte de publicacao, dos modelos fantasma nem da escolha do piso. **O salto de 2026 inverte de sinal nas duas** assim que qualquer piso entra: e' fantasma somado a ano incompleto, e nao e' citavel.

### O corte de publicacao esta' fabricando a alta recente? (I3)

O piso de volume responde o que o subconjunto imune ao corte nao tinha poder para responder. Duas janelas, lidas em separado:

**2022 a 2025** (ultimo ano completo):

| piso          |   taxa_2022 |   taxa_2025 |   variacao |
|:--------------|------------:|------------:|-----------:|
| todos         |      0.12   |      0.1947 |     0.0747 |
| acima de 100  |      0.0787 |      0.1739 |     0.0952 |
| acima de 1000 |      0.0678 |      0.1488 |     0.081  |

A alta **nao some com o piso -- ela se mantem ou aumenta**. E' movimento real de portfolio, nao artefato do corte de publicacao nem dos modelos fantasma.

**2025 a 2026** (ano parcial):

| piso          |   taxa_2025 |   taxa_2026 |   variacao |
|:--------------|------------:|------------:|-----------:|
| todos         |      0.1947 |      0.2251 |     0.0304 |
| acima de 100  |      0.1739 |      0.1429 |    -0.031  |
| acima de 1000 |      0.1488 |      0.0843 |    -0.0645 |

O salto de 2026 **inverte de sinal** assim que o piso entra: e' fantasma somado a ano incompleto, nao rotatividade. **Nao citar.**

**Conferencia secundaria.** O teste do subconjunto imune ao corte -- 168 de 925 modelos cujo limiar de D3 supera o corte do bloco em todo mes da propria janela -- fica registrado, mas com mediana de 5 saidas por ano ele nao tem poder para decidir nada sozinho. O piso de volume e' o teste que responde.

|   ano |   ativos_imunes |   entradas_5%_imunes |   saidas_5%_imunes |   taxa_entrada_5%_imunes |   taxa_saida_5%_imunes |
|------:|----------------:|---------------------:|-------------------:|-------------------------:|-----------------------:|
|  2003 |              66 |                   25 |                 17 |                   0.3788 |                 0.2576 |
|  2004 |              58 |                   12 |                 13 |                   0.2069 |                 0.2241 |
|  2005 |              51 |                    7 |                  5 |                   0.1373 |                 0.098  |
|  2006 |              58 |                   11 |                  6 |                   0.1897 |                 0.1034 |
|  2007 |              58 |                    5 |                  8 |                   0.0862 |                 0.1379 |
|  2008 |              58 |                    7 |                  7 |                   0.1207 |                 0.1207 |
|  2009 |              59 |                    8 |                  7 |                   0.1356 |                 0.1186 |
|  2010 |              59 |                    4 |                  4 |                   0.0678 |                 0.0678 |
|  2011 |              58 |                    5 |                  8 |                   0.0862 |                 0.1379 |
|  2012 |              56 |                    2 |                  3 |                   0.0357 |                 0.0536 |
|  2013 |              48 |                    2 |                  5 |                   0.0417 |                 0.1042 |
|  2014 |              48 |                    1 |                  3 |                   0.0208 |                 0.0625 |
|  2015 |              46 |                    2 |                  3 |                   0.0435 |                 0.0652 |
|  2016 |              48 |                    3 |                  5 |                   0.0625 |                 0.1042 |
|  2017 |              49 |                    4 |                  4 |                   0.0816 |                 0.0816 |
|  2018 |              43 |                    1 |                  3 |                   0.0233 |                 0.0698 |
|  2019 |              47 |                    2 |                  5 |                   0.0426 |                 0.1064 |
|  2020 |              45 |                    5 |                  5 |                   0.1111 |                 0.1111 |
|  2021 |              47 |                    3 |                 11 |                   0.0638 |                 0.234  |
|  2022 |              46 |                    4 |                  6 |                   0.087  |                 0.1304 |
|  2023 |              41 |                    2 |                  4 |                   0.0488 |                 0.0976 |
|  2024 |              43 |                    3 |                  3 |                   0.0698 |                 0.0698 |
|  2025 |              44 |                    6 |                  6 |                   0.1364 |                 0.1364 |
|  2026 |              42 |                    3 |                  9 |                   0.0714 |                 0.2143 |

### Os tres limiares de D3

Como manda a sec.6, lado a lado. Sem piso de volume: sao as taxas da coluna "todos", e valem a mesma advertencia.

|   ano |   ativos |   entradas_3% |   saidas_3% |   taxa_entrada_3% |   taxa_saida_3% |   entradas_5% |   saidas_5% |   taxa_entrada_5% |   taxa_saida_5% |   entradas_10% |   saidas_10% |   taxa_entrada_10% |   taxa_saida_10% |
|------:|---------:|--------------:|------------:|------------------:|----------------:|--------------:|------------:|------------------:|----------------:|---------------:|-------------:|-------------------:|-----------------:|
|  2003 |      231 |            85 |          27 |            0.368  |          0.1169 |            85 |          29 |            0.368  |          0.1255 |             85 |           30 |             0.368  |           0.1299 |
|  2004 |      227 |            44 |          33 |            0.1938 |          0.1454 |            44 |          31 |            0.1938 |          0.1366 |             44 |           30 |             0.1938 |           0.1322 |
|  2005 |      220 |            29 |          22 |            0.1318 |          0.1    |            29 |          23 |            0.1318 |          0.1045 |             29 |           23 |             0.1318 |           0.1045 |
|  2006 |      226 |            39 |          23 |            0.1726 |          0.1018 |            39 |          22 |            0.1726 |          0.0973 |             39 |           24 |             0.1726 |           0.1062 |
|  2007 |      236 |            34 |          29 |            0.1441 |          0.1229 |            34 |          30 |            0.1441 |          0.1271 |             34 |           29 |             0.1441 |           0.1229 |
|  2008 |      252 |            47 |          28 |            0.1865 |          0.1111 |            47 |          28 |            0.1865 |          0.1111 |             47 |           28 |             0.1865 |           0.1111 |
|  2009 |      259 |            41 |          30 |            0.1583 |          0.1158 |            41 |          31 |            0.1583 |          0.1197 |             41 |           31 |             0.1583 |           0.1197 |
|  2010 |      259 |            36 |          33 |            0.139  |          0.1274 |            36 |          32 |            0.139  |          0.1236 |             36 |           32 |             0.139  |           0.1236 |
|  2011 |      259 |            43 |          29 |            0.166  |          0.112  |            43 |          30 |            0.166  |          0.1158 |             43 |           30 |             0.166  |           0.1158 |
|  2012 |      250 |            20 |          21 |            0.08   |          0.084  |            20 |          20 |            0.08   |          0.08   |             20 |           20 |             0.08   |           0.08   |
|  2013 |      237 |            20 |          25 |            0.0844 |          0.1055 |            20 |          25 |            0.0844 |          0.1055 |             20 |           27 |             0.0844 |           0.1139 |
|  2014 |      234 |            16 |          21 |            0.0684 |          0.0897 |            16 |          24 |            0.0684 |          0.1026 |             16 |           26 |             0.0684 |           0.1111 |
|  2015 |      251 |            23 |          23 |            0.0916 |          0.0916 |            23 |          22 |            0.0916 |          0.0876 |             23 |           27 |             0.0916 |           0.1076 |
|  2016 |      260 |            27 |          37 |            0.1038 |          0.1423 |            27 |          40 |            0.1038 |          0.1538 |             27 |           38 |             0.1038 |           0.1462 |
|  2017 |      269 |            28 |          30 |            0.1041 |          0.1115 |            28 |          28 |            0.1041 |          0.1041 |             28 |           26 |             0.1041 |           0.0967 |
|  2018 |      259 |            33 |          40 |            0.1274 |          0.1544 |            33 |          39 |            0.1274 |          0.1506 |             33 |           41 |             0.1274 |           0.1583 |
|  2019 |      260 |            23 |          37 |            0.0885 |          0.1423 |            23 |          38 |            0.0885 |          0.1462 |             23 |           36 |             0.0885 |           0.1385 |
|  2020 |      253 |            37 |          37 |            0.1462 |          0.1462 |            37 |          37 |            0.1462 |          0.1462 |             37 |           39 |             0.1462 |           0.1542 |
|  2021 |      251 |            25 |          41 |            0.0996 |          0.1633 |            25 |          40 |            0.0996 |          0.1594 |             25 |           38 |             0.0996 |           0.1514 |
|  2022 |      250 |            26 |          30 |            0.104  |          0.12   |            26 |          30 |            0.104  |          0.12   |             26 |           32 |             0.104  |           0.128  |
|  2023 |      254 |            29 |          44 |            0.1142 |          0.1732 |            29 |          42 |            0.1142 |          0.1654 |             29 |           41 |             0.1142 |           0.1614 |
|  2024 |      242 |            24 |          42 |            0.0992 |          0.1736 |            24 |          41 |            0.0992 |          0.1694 |             24 |           37 |             0.0992 |           0.1529 |
|  2025 |      226 |            28 |          40 |            0.1239 |          0.177  |            28 |          44 |            0.1239 |          0.1947 |             28 |           43 |             0.1239 |           0.1903 |
|  2026 |      231 |            22 |          56 |            0.0952 |          0.2424 |            22 |          52 |            0.0952 |          0.2251 |             22 |           53 |             0.0952 |           0.2294 |

#### Estabilidade da ordenacao entre limiares

**Achado metodologico:** 19 de 24 anos mudam de posicao no ranking de taxa de saida conforme o limiar.

|   ano |   taxa_saida_3% |   taxa_saida_5% |   taxa_saida_10% |
|------:|----------------:|----------------:|-----------------:|
|  2003 |              14 |              12 |               11 |
|  2004 |               8 |              10 |               10 |
|  2005 |              21 |              19 |               22 |
|  2006 |              20 |              22 |               21 |
|  2007 |              12 |              11 |               14 |
|  2008 |              18 |              17 |               18 |
|  2010 |              11 |              13 |               13 |
|  2013 |              19 |              18 |               17 |
|  2014 |              23 |              21 |               18 |
|  2015 |              22 |              23 |               20 |
|  2016 |               9 |               6 |                8 |
|  2017 |              17 |              20 |               23 |
|  2018 |               6 |               7 |                4 |
|  2019 |               9 |               8 |                9 |
|  2020 |               7 |               8 |                5 |
|  2021 |               5 |               5 |                7 |
|  2022 |              13 |              14 |               12 |
|  2023 |               4 |               4 |                3 |
|  2024 |               3 |               3 |                6 |

#### As duas leituras de "pico movel de 12 meses" (Q1 -- encerrada)

Em uso: `media_movel`, por principio -- um lote isolado de venda direta nao e' a escala do produto, e `max_movel` numa serie completa degenera para o pico global.

|   ano |   entradas_5% |   saidas_5% |   taxa_entrada_5% |   taxa_saida_5% |   entradas_5%_max_movel |   saidas_5%_max_movel |   taxa_entrada_5%_max_movel |   taxa_saida_5%_max_movel |
|------:|--------------:|------------:|------------------:|----------------:|------------------------:|----------------------:|----------------------------:|--------------------------:|
|  2003 |            85 |          29 |            0.368  |          0.1255 |                      85 |                    29 |                      0.368  |                    0.1255 |
|  2004 |            44 |          31 |            0.1938 |          0.1366 |                      44 |                    31 |                      0.1938 |                    0.1366 |
|  2005 |            29 |          23 |            0.1318 |          0.1045 |                      29 |                    23 |                      0.1318 |                    0.1045 |
|  2006 |            39 |          22 |            0.1726 |          0.0973 |                      39 |                    22 |                      0.1726 |                    0.0973 |
|  2007 |            34 |          30 |            0.1441 |          0.1271 |                      34 |                    30 |                      0.1441 |                    0.1271 |
|  2008 |            47 |          28 |            0.1865 |          0.1111 |                      47 |                    28 |                      0.1865 |                    0.1111 |
|  2009 |            41 |          31 |            0.1583 |          0.1197 |                      41 |                    31 |                      0.1583 |                    0.1197 |
|  2010 |            36 |          32 |            0.139  |          0.1236 |                      36 |                    33 |                      0.139  |                    0.1274 |
|  2011 |            43 |          30 |            0.166  |          0.1158 |                      43 |                    30 |                      0.166  |                    0.1158 |
|  2012 |            20 |          20 |            0.08   |          0.08   |                      20 |                    20 |                      0.08   |                    0.08   |
|  2013 |            20 |          25 |            0.0844 |          0.1055 |                      20 |                    27 |                      0.0844 |                    0.1139 |
|  2014 |            16 |          24 |            0.0684 |          0.1026 |                      16 |                    26 |                      0.0684 |                    0.1111 |
|  2015 |            23 |          22 |            0.0916 |          0.0876 |                      23 |                    25 |                      0.0916 |                    0.0996 |
|  2016 |            27 |          40 |            0.1038 |          0.1538 |                      27 |                    38 |                      0.1038 |                    0.1462 |
|  2017 |            28 |          28 |            0.1041 |          0.1041 |                      28 |                    28 |                      0.1041 |                    0.1041 |
|  2018 |            33 |          39 |            0.1274 |          0.1506 |                      33 |                    41 |                      0.1274 |                    0.1583 |
|  2019 |            23 |          38 |            0.0885 |          0.1462 |                      23 |                    37 |                      0.0885 |                    0.1423 |
|  2020 |            37 |          37 |            0.1462 |          0.1462 |                      37 |                    34 |                      0.1462 |                    0.1344 |
|  2021 |            25 |          40 |            0.0996 |          0.1594 |                      25 |                    41 |                      0.0996 |                    0.1633 |
|  2022 |            26 |          30 |            0.104  |          0.12   |                      26 |                    31 |                      0.104  |                    0.124  |
|  2023 |            29 |          42 |            0.1142 |          0.1654 |                      29 |                    42 |                      0.1142 |                    0.1654 |
|  2024 |            24 |          41 |            0.0992 |          0.1694 |                      24 |                    41 |                      0.0992 |                    0.1694 |
|  2025 |            28 |          44 |            0.1239 |          0.1947 |                      28 |                    39 |                      0.1239 |                    0.1726 |
|  2026 |            22 |          52 |            0.0952 |          0.2251 |                      22 |                    56 |                      0.0952 |                    0.2424 |

**A regra que encerra Q1.** 14 de 24 anos mudam de posicao entre as duas leituras, e a consequencia vale mais que a escolha: **a ordenacao de anos por taxa de saida nao e' identificada** no nivel de precisao em que as duas leituras discordam. So' afirmar diferenca entre dois anos quando ela sobreviver as duas. Reportar banda, nao ponto.

|   ano |   taxa_saida_5% |   taxa_saida_5%_max_movel |
|------:|----------------:|--------------------------:|
|  2003 |              12 |                        13 |
|  2004 |              10 |                         9 |
|  2005 |              19 |                        20 |
|  2006 |              22 |                        23 |
|  2007 |              11 |                        12 |
|  2008 |              17 |                        18 |
|  2010 |              13 |                        11 |
|  2013 |              18 |                        17 |
|  2014 |              21 |                        18 |
|  2015 |              23 |                        22 |
|  2016 |               6 |                         7 |
|  2017 |              20 |                        21 |
|  2018 |               7 |                         6 |
|  2020 |               8 |                        10 |

O que **sobrevive** as duas leituras, e portanto pode ser afirmado -- variacao de mais de 3 pontos percentuais no mesmo sentido entre anos consecutivos completos (o ano parcial de 2026 fica fora):

|   de |   para |   taxa_saida_5% |   taxa_saida_5%_max_movel |
|-----:|-------:|----------------:|--------------------------:|
| 2004 |   2005 |         -0.0321 |                   -0.0321 |
| 2011 |   2012 |         -0.0358 |                   -0.0358 |
| 2015 |   2016 |          0.0662 |                    0.0466 |
| 2016 |   2017 |         -0.0497 |                   -0.0421 |
| 2017 |   2018 |          0.0465 |                    0.0542 |
| 2021 |   2022 |         -0.0394 |                   -0.0393 |
| 2022 |   2023 |          0.0454 |                    0.0414 |

### Zeros frageis (Q5)

Mes em que o modelo nao aparece e o corte de publicacao **do bloco em que ele seria listado** (sec.4) esta' acima do limiar de D3 do proprio modelo: ali o zero pode estar escondendo valor relevante. A contagem so' considera meses entre a entrada e a saida do modelo, no limiar de 5%.

**8240** pares (modelo x mes) frageis, em 267 modelos. Lista completa em `saidas/zeros_frageis.csv`.

|   ano |   zeros_frageis |   modelos |
|------:|----------------:|----------:|
|  2003 |              35 |         9 |
|  2004 |              93 |        20 |
|  2005 |              86 |        20 |
|  2006 |             173 |        35 |
|  2007 |             201 |        34 |
|  2008 |             335 |        54 |
|  2009 |             350 |        56 |
|  2010 |             460 |        62 |
|  2011 |             629 |        70 |
|  2012 |             507 |        76 |
|  2013 |             687 |        79 |
|  2014 |             663 |        79 |
|  2015 |             591 |        79 |
|  2016 |             538 |        73 |
|  2017 |             480 |        70 |
|  2018 |             538 |        68 |
|  2019 |             408 |        67 |
|  2020 |             351 |        58 |
|  2021 |             345 |        57 |
|  2022 |             233 |        48 |
|  2023 |             224 |        46 |
|  2024 |             180 |        35 |
|  2025 |             110 |        27 |
|  2026 |              23 |        11 |

## 9. Coerencia entre meses

Cada linha da fonte traz o mes anterior, o mes de referencia e o acumulado do ano. Duas identidades tem de valer sem depender de interpretacao nossa: a coluna de mes anterior de M repete o mes de M-1, e a diferenca de acumulados da' o mes.

- Coluna de mes anterior divergente do mes observado: **1590** de 45.065 pares comparados (3.53%)
- Acumulado divergente da soma do mes com o acumulado anterior: **2376** de 45.065 (5.27%)

A fonte revisa meses ja publicados, e e' isso que a maior parte destas linhas mostra. Casos em que duas linhas do mesmo mes se compensam -- VW/GOL -676 e VW/VOYAGE +676 em Ago/2016 -- sao remanejamento de unidades entre modelos, candidatos naturais a `reclassificacao`. Listas completas em `saidas/coerencia_mes_anterior.csv` e `saidas/coerencia_acumulado.csv`.

Maiores divergencias na coluna de mes anterior:

| mes     | segmento   | nome_completo_fonte   |   unidades_mes_anterior |   mes_anterior_observado |   diferenca |
|:--------|:-----------|:----------------------|------------------------:|-------------------------:|------------:|
| 2019-09 | automoveis | GM/ONIX               |                   21377 |                    22396 |       -1019 |
| 2016-08 | automoveis | VW/VOYAGE             |                    2663 |                     1987 |         676 |
| 2016-08 | automoveis | VW/GOL                |                    5790 |                     6466 |        -676 |
| 2016-01 | automoveis | M.BENZ/CLASSE C       |                     895 |                      321 |         574 |
| 2021-04 | automoveis | BMW/320I              |                     622 |                       51 |         571 |
| 2015-10 | automoveis | FORD/FOCUS            |                     932 |                     1310 |        -378 |
| 2015-10 | automoveis | FORD/FOCUS SEDAN      |                     785 |                      407 |         378 |
| 2022-03 | automoveis | RENAULT/KWID          |                    4637 |                     4262 |         375 |
| 2017-07 | automoveis | CITROEN/C3            |                    1040 |                      802 |         238 |
| 2018-01 | automoveis | FORD/KA               |                    7880 |                     7649 |         231 |
| 2021-01 | automoveis | TOYOTA/YARIS HB       |                    2956 |                     2754 |         202 |
| 2022-03 | automoveis | GM/ONIX               |                    6724 |                     6541 |         183 |
| 2022-03 | automoveis | VW/T CROSS            |                    5278 |                     5118 |         160 |
| 2020-01 | automoveis | FIAT/UNO              |                    1128 |                     1283 |        -155 |
| 2016-09 | automoveis | HONDA/CIVIC           |                     596 |                      451 |         145 |

_(1575 linhas restantes omitidas; ver CSV correspondente.)_

## 10. Divergencias internas da fonte

Duas familias de inconsistencia, ambas da fonte, ambas reportadas e mantidas (sec.9.4).

### Marca trocada pela fonte

Um nome de modelo aparece sob a mesma marca em quase todos os meses. Quando um mes o publica sob outra, e' esse mes que destoa. O que sobra nesta lista **nao foi corrigido**: o painel guarda o que a fonte publicou, e nem toda divergencia e' defeito -- `TIGGO 7` sob `CHERY` ate' 2020 e sob `CAOA CHERY` depois e' troca real de marca, que 'corrigir' destruiria.

**O caminho completo de D4, em tres passos.** A fonte publicou **12** modelos sob marca trocada em 2013-11. **Quatro** deles eram a linha do ranking duplicando a tabela de sub-segmento e foram suprimidos (sec.1) -- nao ha' o que recuperar numa linha que nao entra. Dos **8 que restam**, os numeros abaixo.

**Recuperados: 4 de 8.** Onde a edicao saiu com a coluna de marca trocada, o informe do mes seguinte republica o mes na coluna de mes anterior com a marca certa. O **valor nao muda** -- muda a atribuicao --, e so' se recupera quando o valor confere unidade a unidade. E' a mesma rota de 2023-09 (sec.9.2), usada para a marca em vez do valor. As linhas levam `marca_recuperada` e guardam a marca errada em `marca_publicada_fonte`.

| mes_ref   | modelo   | marca_publicada   | marca_recuperada   |   unidades |
|:----------|:---------|:------------------|:-------------------|-----------:|
| 2013-11   | KOMBI    | FORD              | VW                 |       2383 |
| 2013-11   | ELANTRA  | nan               | HYUNDAI            |        460 |
| 2013-11   | T4       | TROLER            | TROLLER            |        120 |
| 2013-11   | CAMARO   | CAMARO            | GM                 |         59 |

**4 sem rota.** O informe seguinte lista o modelo so' no ranking mensal, que nao traz coluna de mes anterior. Ficam no painel como a fonte os publicou.

| mes_ref   | modelo   | marca_publicada   |   unidades | situacao                                                                                   |
|:----------|:---------|:------------------|-----------:|:-------------------------------------------------------------------------------------------|
| 2013-11   | SPRINTER | DODGE             |         66 | informe seguinte lista o modelo so' no ranking mensal, que nao traz coluna de mes anterior |
| 2013-11   | SC       | LEXUS             |         42 | informe seguinte lista o modelo so' no ranking mensal, que nao traz coluna de mes anterior |
| 2013-11   | TOPIC    | ASIA              |         34 | informe seguinte lista o modelo so' no ranking mensal, que nao traz coluna de mes anterior |
| 2013-11   | MINIVAN  | DFM               |         20 | informe seguinte lista o modelo so' no ranking mensal, que nao traz coluna de mes anterior |

**A assimetria, e por que ela existe.** O mesmo defeito de 2013-11 teve dois tratamentos, e a diferenca nao e' de criterio, e' de onde cabe o conserto.

- **Cinco linhas foram removidas a montante**, na canonizacao da chave de reconciliacao da etapa 02 -- `VW/GOL` 20.360, `FIAT/UNO` 15.851, `FIAT/PALIO` 12.816, `GM/CELTA` 5.007, `TOYOTA/ETIOS HB` 2.425, somando 56.459 unidades. Ali a divergencia era **tipografica**: o ranking escreve `VW /GOL` com um espaco a mais e a tabela de sub-segmento `VW/GOL`. Consertar a chave nao mexe em nada do que foi transcrito, e o invariante nunca correu risco.
- **Quatro foram removidas a jusante**, por supressao marcada em `duplicata_publicada`. Estas divergiam na **marca** (`PONTIAC/MONTANA` contra `GM /MONTANA`), e canoniza-las na etapa 02 seria reescrever a marca dentro do painel bruto, que e' transcricao fiel da fonte (sec.4). Nao cabe la'.

A regra que sai disso: **a montante quando da' para consertar sem tocar no transcrito; a jusante, marcado e enumerado, quando nao da'.**

**Consequencia medida e nao resolvida:** recuperada a marca, **4** linhas do ranking passam a repetir uma linha de sub-segmento do mesmo informe -- 9.171 unidades que a fonte publicou duas vezes, sob marcas diferentes. A regra Q7 diria para descartar a do ranking; descartar mudaria o total do mes e quebraria o invariante central, que existe para impedir que a harmonizacao mexa em volume. **Nada foi descartado** -- e' decisao do pesquisador (sec.9.6), e e' o que mantem a cobertura de 2013-11 em comerciais leves acima de 100%.

| mes_ref   | segmento_fonte   | marca_chave   | modelo_chave   |   unidades_ranking | marca_publicada_fonte   |   unidades_sub_segmento | valor_identico   |
|:----------|:-----------------|:--------------|:---------------|-------------------:|:------------------------|------------------------:|:-----------------|
| 2013-11   | comerciais_leves | GM            | MONTANA        |               3901 | PONTIAC                 |                    3901 | True             |
| 2013-11   | automoveis       | HONDA         | CITY           |               2464 | THINK                   |                    2464 | True             |
| 2013-11   | comerciais_leves | FORD          | RANGER         |               1967 | VW                      |                    1967 | True             |
| 2013-11   | comerciais_leves | RENAULT       | MASTER         |                839 | FORD                    |                     839 | True             |
**47** pares (mes x modelo), 2.347 unidades. Lista completa em `saidas/marca_divergente.csv`.

| mes_ref   |   modelos |   unidades |   marcas_fantasma | exemplos                     |
|:----------|----------:|-----------:|------------------:|:-----------------------------|
| 2019-12   |         1 |        320 |                 1 | TIGGO 7                      |
| 2019-07   |         1 |        317 |                 1 | TIGGO 7                      |
| 2019-10   |         1 |        314 |                 1 | TIGGO 7                      |
| 2020-02   |         1 |        290 |                 1 | TIGGO 7                      |
| 2019-09   |         1 |        255 |                 1 | TIGGO 7                      |
| 2019-08   |         1 |        237 |                 1 | TIGGO 7                      |
| 2019-11   |         1 |        228 |                 1 | TIGGO 7                      |
| 2020-01   |         1 |        181 |                 1 | TIGGO 7                      |
| 2013-11   |         4 |        162 |                 4 | MINIVAN, SC, SPRINTER, TOPIC |
| 2017-07   |         2 |          6 |                 1 | AMAROK, SAVEIRO              |
| 2017-10   |         1 |          5 |                 1 | SAVEIRO                      |
| 2016-07   |         2 |          4 |                 2 | 2500, SAVEIRO                |

_(28 linhas restantes omitidas; ver CSV correspondente.)_

Nem toda divergencia e' defeito: `TIGGO 7` sob `CHERY` em 2019-2020 contra `CAOA CHERY` depois e' **troca real de marca**, nao erro. O teste aponta; a leitura e' humana.

### Ranking contra tabela de sub-segmento

Modelos em que o ranking mensal e a tabela de sub-segmento do **mesmo** informe trazem numeros diferentes -- 440 casos. O painel usa o valor da tabela de sub-segmento.

| mes     | segmento         | nome_completo_fonte   |   valor_ranking |   valor_sub_segmento |   diferenca | arquivo_origem   |
|:--------|:-----------------|:----------------------|----------------:|---------------------:|------------:|:-----------------|
| 2003-01 | automoveis       | CITROEN/XSARA         |             277 |                   62 |         215 | 2003-01.pdf      |
| 2003-02 | automoveis       | CITROEN/XSARA         |             246 |                   81 |         165 | 2003-02.pdf      |
| 2003-03 | automoveis       | CITROEN/XSARA         |             178 |                   63 |         115 | 2003-03.pdf      |
| 2003-04 | automoveis       | CITROEN/XSARA         |             160 |                   49 |         111 | 2003-04.pdf      |
| 2003-04 | automoveis       | AUDI/A4               |              40 |                   39 |           1 | 2003-04.pdf      |
| 2003-05 | automoveis       | CITROEN/XSARA         |              87 |                   19 |          68 | 2003-05.pdf      |
| 2003-07 | automoveis       | CITROEN/XSARA         |              67 |                    4 |          63 | 2003-07.pdf      |
| 2003-08 | automoveis       | CITROEN/XSARA         |              51 |                    2 |          49 | 2003-08.pdf      |
| 2003-11 | automoveis       | CITROEN/XSARA         |              64 |                    2 |          62 | 2003-11.pdf      |
| 2005-12 | comerciais_leves | VW/KOMBI              |            1265 |                 1231 |          34 | 2005-12.pdf      |
| 2006-01 | comerciais_leves | VW/KOMBI              |            1406 |                 1350 |          56 | 2006-01.pdf      |
| 2006-02 | comerciais_leves | VW/KOMBI              |            1367 |                 1343 |          24 | 2006-02.pdf      |
| 2006-02 | comerciais_leves | VW/SAVEIRO            |            1133 |                 1132 |           1 | 2006-02.pdf      |
| 2006-03 | comerciais_leves | VW/KOMBI              |            1873 |                 1851 |          22 | 2006-03.pdf      |
| 2006-03 | comerciais_leves | VW/SAVEIRO            |            1827 |                 1819 |           8 | 2006-03.pdf      |
| 2006-04 | comerciais_leves | VW/SAVEIRO            |            1580 |                 1569 |          11 | 2006-04.pdf      |
| 2006-04 | comerciais_leves | VW/KOMBI              |            1522 |                 1509 |          13 | 2006-04.pdf      |
| 2006-05 | comerciais_leves | VW/SAVEIRO            |            1765 |                 1743 |          22 | 2006-05.pdf      |
| 2006-05 | comerciais_leves | VW/KOMBI              |            1570 |                 1558 |          12 | 2006-05.pdf      |
| 2006-06 | comerciais_leves | VW/SAVEIRO            |            1592 |                 1567 |          25 | 2006-06.pdf      |

_(420 linhas restantes omitidas; ver CSV correspondente.)_

## 11. Situacao

Todas as verificacoes obrigatorias passaram.
