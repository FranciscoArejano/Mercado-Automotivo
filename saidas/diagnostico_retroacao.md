# Diagnostico de retroacao -- 2003-01 a 2013-12

So' diagnostico: nada foi escrito no painel (ESPEC.md sec.2, QUESTOES_ABERTAS.md Q6). A decisao de estender a serie continua sendo do pesquisador, e este e' o insumo dela.

## Qualidade da extracao, ano a ano

|   ano |   informes |   sem_linha |   com_glifos |   modelos_medio |   cobertura_autos_media |   cobertura_leves_media |   linhas_com_nome_composto |
|------:|-----------:|------------:|-------------:|----------------:|------------------------:|------------------------:|---------------------------:|
|  2003 |         12 |           0 |            0 |          150.17 |                   95.44 |                   90.14 |                          2 |
|  2004 |         12 |           0 |            0 |          165    |                   99.8  |                   98.72 |                         12 |
|  2005 |         12 |           0 |            0 |          153.58 |                   95.03 |                   90.58 |                         11 |
|  2006 |         12 |           0 |            0 |          171.08 |                   99.66 |                   98.89 |                         12 |
|  2007 |         12 |           0 |            0 |          174.42 |                   99.25 |                   98.92 |                         12 |
|  2008 |         12 |           0 |            0 |          177.92 |                   97.97 |                   98.23 |                         11 |
|  2009 |         12 |           0 |            0 |          179.67 |                   98.15 |                   97.71 |                         12 |
|  2010 |         12 |           0 |            0 |          181.25 |                   97.99 |                   96.9  |                         11 |
|  2011 |         12 |           0 |            0 |          179.08 |                   97.46 |                   96.2  |                         12 |
|  2012 |         12 |           0 |            0 |          178.75 |                   97.41 |                   96.68 |                         12 |
|  2013 |         12 |           0 |            0 |          176.5  |                   98.08 |                   97.38 |                         12 |

## Deriva de agregacao: nomes compostos (`MARCA/A/B`)

Um registro unico para o que poderiam ser dois modelos. Se o padrao muda ao longo da serie, a unidade de observacao deriva sem aviso.

|   ano |   nomes_compostos | entram_no_padrao   | saem_do_padrao   |
|------:|------------------:|:-------------------|:-----------------|
|  2003 |                 1 | VW/FOX/CROSS FOX   |                  |
|  2004 |                 1 |                    |                  |
|  2005 |                 1 |                    |                  |
|  2006 |                 1 |                    |                  |
|  2007 |                 1 |                    |                  |
|  2008 |                 1 |                    |                  |
|  2009 |                 1 |                    |                  |
|  2010 |                 1 |                    |                  |
|  2011 |                 1 |                    |                  |
|  2012 |                 1 |                    |                  |
|  2013 |                 1 |                    |                  |

## Meses problematicos

Nenhum: todo informe do periodo rendeu tabela por modelo, com o mes declarado batendo com o do catalogo.

## Leitura

- **Extracao:** 132 informes lidos, 0 sem tabela por modelo, 0 precisando de traducao de glifos. O parser nao degrada com a idade do informe.
- **Cobertura:** o pior ano em automoveis e' 2005, com 95.0%. Anos abaixo de 97%: 2003, 2005.
- **Deriva de agregacao:** 1 nome composto distinto no periodo inteiro, sem entrada nem saida do padrao depois do primeiro ano. A unidade de observacao **nao deriva** nestes anos: o que a fonte agrega hoje ela ja' agregava em 2003.
- **Meses a resolver antes de estender:** 0.

A decisao de estender continua sendo do pesquisador (ESPEC.md sec.2). Para executar, basta rodar o pipeline com `--inicio 2003-01`.
