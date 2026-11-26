# Dicionario -- emissoes_uf_anual

Uma linha por tipo x UF x ano x setor x categoria x subcategoria x produto x gas, 2003 a 2025, 552,713 linhas. Gravado pela etapa 16 a partir do bruto reduzido da tabela geral do SEEG, **colecao 14.0** (`dados/bruto/seeg/`, SHA-256 do original e do reduzido no manifesto). O SEEG publica desde 1970; o bruto reduzido guarda de 2003 em diante, a janela do projeto.

**Fonte:** SEEG -- Sistema de Estimativas de Emissoes e Remocoes de Gases de Efeito Estufa, Observatorio do Clima, tabela geral `Dados-nacionais-14.0.xlsx` (https://seeg.eco.br/dados/), colecao 14.0, atualizada em 9/11/2026; URL e data do download no manifesto.

| coluna | unidade | descricao |
|---|---|---|
| `uf` | sigla | UF; vazia na parcela nao alocada a estado. |
| `estado_fonte` | texto | Estado como o SEEG escreve (`Não Alocado` para a parcela sem estado). |
| `ano` | inteiro | Ano civil da emissao. |
| `tipo` | texto | `Emissão`, `Remoção`, `Emissão NCI`, `Remoção NCI` (nao contabilizadas no inventario: remocao em area protegida e emissoes associadas) e `Bunker` (combustivel de navegacao e aviacao internacional), como a fonte. |
| `setor` | texto | Setor de emissao do SEEG (Agropecuária, Energia, Mudança de Uso da Terra e Floresta, Processos Industriais, Resíduos). |
| `categoria` | texto | Categoria emissora (o 'subsetor'): em Energia, por exemplo, `Transportes`, `Industrial`, `Geração de eletricidade (serviço público)`. |
| `subcategoria` | texto | Sub-categoria emissora: em Transportes, `Rodoviário`, `Aéreo`, `Ferroviário`, `Hidroviário`. |
| `produto` | texto | Produto ou sistema: em Energia, o combustivel (diesel, gasolina, etanol...). |
| `gas` | texto | Gas fisico (`CO2`, `CH4`, `N2O`, `NOX`, `CO`, `COVNM`, HFCs, PFCs, `SF6`) ou `CO2e_GWP_AR5` (todos os gases da linha convertidos pelo GWP do AR5). |
| `unidade` | texto | `t` (tonelada do gas) ou `t CO2e (GWP-AR5)`. |
| `valor` | ver `unidade` | Soma sobre detalhamento, recorte, atividade geral e bioma (colunas mais finas da fonte, guardadas no bruto reduzido). Remocao vem com sinal negativo, como na fonte. |
| `gas_fonte` | texto | Rotulo do gas como a fonte escreve. |
| `colecao_seeg` | texto | Colecao (versao) do SEEG de que a linha saiu. |

## Ressalvas

- **Colecao 14.0.** Cada colecao do SEEG recalcula a serie inteira: um numero de 2010 da colecao 14.0 nao e' o mesmo da 13.0. Citar a colecao junto do numero.
- **Metrica de CO2e:** GWP-AR5, a de referencia do SEEG. As outras (GWP-AR2, AR4, AR6, GTP) estao no original e nao no reduzido.
- **Nao somar gases fisicos com CO2e**, nem gases fisicos entre si (toneladas de gases diferentes). Para participacao de setor, usar `gas == 'CO2e_GWP_AR5'` e `tipo == 'Emissão'`.
- **Parcela nao alocada:** parte das emissoes (sobretudo de Energia: transporte aereo e hidroviario internacional, producao de combustiveis) nao tem estado; vai em `uf` vazia. Nas emissoes totais ela fica entre 2.0% e 3.4% do total Brasil, ano a ano. O total Brasil e' a soma das UFs mais o nao alocado (conferido em `saidas/emissoes_uf_anual_validacao.csv`).
- **Emissoes brutas e liquidas:** a remocao vem como linha propria, com sinal negativo; emissao liquida = Emissão + Remoção. Bunker fica fora do total nacional, como no inventario.
