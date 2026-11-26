# Dicionario -- fator_emissao_sin_mensal

Uma linha por mes, 2006-01 a 2026-10 (250 meses). Gravado pela etapa 15 a partir da planilha do MCTI guardada em `dados/bruto/mcti_fator/` com SHA-256. A serie comeca em 2006-01: antes disso o MCTI nao publica o fator medio, e a janela 2003-2005 fica vazia.

**Fonte:** MCTI, Fatores de emissao de CO2 da geracao de energia eletrica no SIN -- fator medio (inventarios corporativos), `Inventario_2026_janout.xlsx`, URL e data no manifesto.

| coluna | unidade | descricao |
|---|---|---|
| `mes` | texto AAAA-MM | Mes de referencia. |
| `ano` | inteiro | Ano de `mes`. |
| `fator_tco2_mwh` | tCO2/MWh | Fator medio mensal de emissao de CO2 da geracao do SIN, metodo para inventarios (media de todas as usinas em operacao, nao a margem). |
| `fator_anual_publicado_tco2_mwh` | tCO2/MWh | Fator medio anual que a mesma planilha publica para o ano, repetido nos meses do ano; vazio no ano corrente, que o MCTI so' fecha em dezembro. |
| `arquivo_fonte` | texto | Planilha de origem em `dados/bruto/mcti_fator/`. |

## Ressalvas

- E' o fator de **inventario** (media), nao o de margem de operacao nem o combinado do MDL, que estao na mesma pagina e medem outra coisa (a emissao deslocada na margem).
- A media simples dos doze meses bate com o fator anual publicado: diferenca maxima de 0.43% entre os anos completos, compativel com o arredondamento a quatro casas (ano a ano em `saidas/fator_emissao_sin_anual_conferencia.csv`). O ano corrente nao tem anual.
- Desde janeiro de 2025 o MCTI calcula com a base ampliada do ONS (novas usinas); a metodologia nao mudou, mas a base sim (nota tecnica NT_FE_jun25 na pagina).
- A planilha e' revisada pelo MCTI (houve correcao de nov/2012, jan/2013 e mar/2013, avisada na pagina). O SHA-256 no manifesto diz de qual versao o dado saiu.
