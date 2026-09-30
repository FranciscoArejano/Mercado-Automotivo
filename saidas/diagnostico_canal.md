# Dimensao de canal -- diagnostico da fase 1

So' medida: **nada foi extraido e nada foi escrito** em `dados/processado/`. A fase 2 depende da leitura destes numeros.

## 1. Em quais meses a estrutura existe

Os informes trazem as dez tabelas de canal em **281 dos 284 meses**, desde **2003-01** -- a estrutura nao nasce no meio da serie, e a dimensao **nao e' mais curta que o painel**.

Os **3** meses sem ela sao os mesmos que ja' faltam no painel, pelas mesmas causas: `2003-10`, `2005-03`, `2023-09`. Duas sao as edicoes curtas de 10 paginas e a terceira e' o informe digitalizado, recuperado do mes seguinte.

## 2. Profundidade das tabelas por modelo

**Sao ranking de 50 posicoes por segmento, nao tabela de sub-segmento.** A suspeita da fase 1 se confirma: a cauda e' bem mais rasa que a do painel principal, que lista cerca de 180 modelos por mes somando os sub-segmentos.

| tabela                         |   minimo |   mediana |   maximo |   meses_com_50_linhas |
|:-------------------------------|---------:|----------:|---------:|----------------------:|
| automoveis, venda direta       |       50 |        50 |       50 |                   281 |
| automoveis, varejo             |       50 |        50 |       50 |                   281 |
| comerciais leves, venda direta |       21 |        29 |       44 |                     0 |
| comerciais leves, varejo       |       27 |        48 |       50 |                   118 |

A **ultima posicao listada e' 50** em 281 dos 281 meses. Automoveis sempre preenche as 50; comerciais leves fica abaixo porque o segmento tem menos modelos, nao porque a tabela corte antes.

## 3. O corte e' por segmento

Automoveis e comerciais leves saem **em colunas separadas na mesma pagina**, cada um com o proprio ranking de 50. Nao e' agregado.

## 4. `direta + varejo` reconcilia com o total publicado?

**Sim, e com folga.** A soma das duas tabelas top-50 contra o total que o proprio informe publica:

- **automoveis**: de 85.2% a 99.3%, mediana anual entre 88.2% e 99.2%
- **comerciais leves**: de 99.8% a 100.0% -- praticamente completo

Nenhum mes fica abaixo de 70%, muito longe do piso de metade do volume que encerraria a tarefa. **A dimensao presta.**

Mas a cobertura **anda ao longo da serie**, e isso e' advertencia de comparabilidade mais forte que a do painel principal (que deriva 3,8 pontos): aqui a amplitude e' de 14 pontos, em forma de U -- alta nos anos 2000, fundo por volta de 2011, recuperando depois. Um ranking de tamanho fixo cobre menos quanto mais modelos o mercado tem.

|   ano | segmento         |   min |   median |   max |
|------:|:-----------------|------:|---------:|------:|
|  2003 | automoveis       |  99   |     99.2 |  99.3 |
|  2004 | automoveis       |  99.1 |     99.2 |  99.3 |
|  2005 | automoveis       |  98.7 |     99   |  99.3 |
|  2006 | automoveis       |  97.9 |     98.5 |  98.7 |
|  2007 | automoveis       |  96.1 |     97.3 |  98.1 |
|  2008 | automoveis       |  93.7 |     95.4 |  96.3 |
|  2009 | automoveis       |  92.7 |     94.5 |  95   |
|  2010 | automoveis       |  91   |     92.4 |  93.7 |
|  2011 | automoveis       |  85.2 |     88.2 |  90.3 |
|  2012 | automoveis       |  87.7 |     89.5 |  90.5 |
|  2013 | automoveis       |  89.8 |     90.4 |  91.4 |
|  2014 | automoveis       |  89.4 |     91   |  91.9 |
|  2015 | automoveis       |  90.4 |     91   |  91.9 |
|  2016 | automoveis       |  92.1 |     92.9 |  94.7 |
|  2017 | automoveis       |  92.7 |     93.8 |  94.4 |
|  2018 | automoveis       |  92.2 |     92.8 |  93.4 |
|  2019 | automoveis       |  93.1 |     94   |  94.5 |
|  2020 | automoveis       |  93.3 |     94.6 |  95.8 |
|  2021 | automoveis       |  95.2 |     95.6 |  97.2 |
|  2022 | automoveis       |  96.6 |     97.7 |  98.1 |
|  2023 | automoveis       |  96.8 |     97.4 |  97.8 |
|  2024 | automoveis       |  95.6 |     96.3 |  96.7 |
|  2025 | automoveis       |  95.1 |     95.9 |  96.4 |
|  2026 | automoveis       |  92.2 |     93.9 |  94.4 |
|  2003 | comerciais_leves | 100   |    100   | 100   |
|  2004 | comerciais_leves | 100   |    100   | 100   |
|  2005 | comerciais_leves | 100   |    100   | 100   |
|  2006 | comerciais_leves | 100   |    100   | 100   |
|  2007 | comerciais_leves | 100   |    100   | 100   |
|  2008 | comerciais_leves |  99.8 |     99.9 | 100   |
|  2009 | comerciais_leves |  99.9 |    100   | 100   |
|  2010 | comerciais_leves |  99.9 |    100   | 100   |
|  2011 | comerciais_leves |  99.9 |    100   | 100   |
|  2012 | comerciais_leves | 100   |    100   | 100   |
|  2013 | comerciais_leves | 100   |    100   | 100   |
|  2014 | comerciais_leves |  99.9 |     99.9 | 100   |
|  2015 | comerciais_leves | 100   |    100   | 100   |
|  2016 | comerciais_leves | 100   |    100   | 100   |
|  2017 | comerciais_leves | 100   |    100   | 100   |
|  2018 | comerciais_leves |  99.9 |    100   | 100   |
|  2019 | comerciais_leves | 100   |    100   | 100   |
|  2020 | comerciais_leves | 100   |    100   | 100   |
|  2021 | comerciais_leves | 100   |    100   | 100   |
|  2022 | comerciais_leves | 100   |    100   | 100   |
|  2023 | comerciais_leves | 100   |    100   | 100   |
|  2024 | comerciais_leves | 100   |    100   | 100   |
|  2025 | comerciais_leves |  99.9 |    100   | 100   |
|  2026 | comerciais_leves |  99.9 |     99.9 | 100   |

## Achado que muda o plano da fase 2

Das tres granularidades pedidas, **so' uma entrega unidades**.

- **Tabelas por modelo**: texto, com unidades, nos 281 meses. Servem para `painel_canal.parquet` como especificado.
- **Ranking por marca**: nao e' tabela, e' **grafico de barras**. Os rotulos saem como texto rotacionado e trazem **percentual, nao unidades**, com os tres paineis sobrepostos quase no mesmo x. `canal_por_marca.csv` so' poderia trazer participacao, e a extracao seria fragil.
- **Participacao agregada**: percentual em texto em apenas **29 dos 281 meses**, a partir de **2024-04**. Nos 252 meses anteriores os numeros sao desenho, nao texto -- a pagina traz so' os rotulos de segmento. `canal_participacao.csv` cobriria de 2024-04 em diante, nao a serie.

A decisao sobre o que vale extrair das duas tabelas em percentual e' do pesquisador (sec.9.6).
