# Dicionario -- precos_combustiveis_mensal (e a tabela municipal)

Tabela por UF: 23,681 linhas, 2004-05 a 2026-10. Tabela municipal (`precos_combustiveis_municipal_mensal.parquet`): 378,808 linhas, 702 municipios. Gravadas pela etapa 18 a partir da serie historica por posto do Levantamento de Precos de Combustiveis (LPC) da ANP.

**Fonte:** ANP, Serie historica de precos de combustiveis (dados abertos, por posto), https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis; sintese mensal por estado em https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos. URL, data e SHA-256 de cada arquivo no manifesto.

| coluna | unidade | descricao |
|---|---|---|
| `mes` | texto AAAA-MM | Mes da coleta (`Data da Coleta` do bruto). |
| `uf` | sigla | UF do posto. |
| `cod_ibge_municipio` | 7 digitos | So' na tabela municipal: codigo IBGE do municipio do posto. |
| `municipio_fonte` | texto | So' na tabela municipal: municipio como a ANP escreve. |
| `produto` | texto | `gasolina_comum` (`GASOLINA` no bruto), `etanol_hidratado` (`ETANOL`), `diesel_s10` (`DIESEL S10`), `gnv` (`GNV`). |
| `preco_medio_revenda` | R$/litro; GNV em R$/m3 | Media simples dos precos de venda coletados no mes, nominal. |
| `preco_real` | R$ do mes-base | `preco_medio_revenda` x IPCA(base) / IPCA(mes), com o IPCA cheio (sgs_433) encadeado de `macro_mensal`. Vazio depois do ultimo mes do IPCA em `macro_mensal`. |
| `base_real` | texto AAAA-MM | Mes-base do preco real. |
| `paridade_etanol_gasolina` | razao | Preco medio do etanol / preco medio da gasolina comum, na UF (ou municipio) e mes; repetida nas linhas dos quatro produtos. |
| `n_postos` | postos | Postos pesquisados (CNPJ distintos) com coleta do produto no mes. |
| `n_coletas` | coletas | Coletas (posto x data) do produto no mes. |
| `unidade` | texto | `Unidade de Medida` do bruto. |
| `arquivo_fonte` | texto | Arquivo por posto em `dados/bruto/anp_precos/` de que o mes saiu. |

## Ressalvas

- **Comeca em 2004-01**: a serie por posto nao existe antes. A sintese da ANP tem 2001-07 a 2003-12, mas nao entra no produto (ver QUESTOES_ABERTAS, rodada 13).
- **Amostra, nao censo:** o LPC pesquisa uma amostra de postos em uma amostra de municipios, que mudou ao longo do tempo (de 2017-07 a 2017-12 a cobertura caiu de 501 para 459 municipios; em 2018-05 a greve dos caminhoneiros reduziu as coletas; nao houve pesquisa de 18/8/2020 a 17/10/2020). Municipio fora da amostra nao tem linha.
- **Diesel S10 so' existe a partir de 2012-2013** no bruto; o diesel comum (S500) nao entra no recorte.
- **Media de coletas, nao de postos:** posto com mais coletas no mes pesa mais. O numero de coletas bate com o 'numero de postos pesquisados' da sintese da ANP (que conta posto x semana), mas o preco medio da sintese nao e' reproduzivel: difere em mais de 1% em 8012 de 23688 casos (UF x mes x produto), com mediana da diferenca de 0.60% e o nosso quase sempre acima. Testadas num semestre (2019-01), a media das semanas, a dos municipios e a mediana ficam iguais ou mais longe. Diferencas em `saidas/precos_combustiveis_conferencia_sintese.csv`.
- **Preco real em R$ de 2026-08** (ultimo mes do IPCA em `macro_mensal`); os meses posteriores ficam com `preco_real` vazio.
