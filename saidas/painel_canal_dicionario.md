# Dicionario de dados -- `painel_canal.parquet`

Gerado por `src/etapa09_canal.py`.

- Periodo: **2003-01 a 2026-08**
- Linhas: 48.996
- Chave: `(mes_ref, segmento, canal, marca, modelo)`
- Lacunas declaradas: `2003-10`, `2005-03`, `2023-09`

## Leia antes de usar

O nivel das quantidades de canal **nao e' comparavel entre anos**. Um ranking de tamanho fixo cobre menos quanto mais modelos o mercado tem, e e' isso que produz o U: em automoveis, a parte do mes que as tabelas explicam tem mediana de 99.2% em 2004, cai a 88.2% em 2011 e volta a 97.7% depois -- amplitude de 14.1 pontos entre o melhor e o pior mes, quase quatro vezes a deriva do painel principal. Comparacoes seguras sao **dentro do ano** -- entre modelos, entre marcas, entre canais. Qualquer serie temporal construida sobre esta dimensao tem de ser reportada **ao lado da serie de cobertura** (`saidas/canal_cobertura.csv`), nunca sozinha.

### Nivel da participacao de canal: por segmento

Venda direta e varejo tem rankings de 50 **separados**, que truncam caudas **diferentes**. Entao a participacao calculada destas tabelas nao e' neutra, e o quanto ela erra foi medido contra a participacao que a fonte publica em texto nos 29 meses de 2024-04 em diante (`saidas/canal_calibracao.csv`).

- **automoveis: a participacao construida NAO serve para o nivel -- so' para composicao dentro de cada canal.** O vies e' sempre do mesmo lado (28 de 28 meses superestimam a venda direta), medio de +1.32 ponto, mas **nao e' estavel**: anda de +1.03 nos seis primeiros meses a +1.91 nos seis ultimos. O mecanismo e' o da truncagem: a venda direta e' concentrada, e o top-50 dela capta quase tudo; o varejo e' disperso, e o top-50 dele capta menos -- e cada vez menos, conforme o mercado se fragmenta (correlacao do vies com a cobertura do varejo: -0.954). Uma correcao unica nao vale para a serie, e uma correcao condicionada a' cobertura extrapolaria: a amostra cobre so' 92.2% a 96.7% de cobertura, e o fundo do U fica abaixo disso.
- **comerciais leves: a participacao construida serve para o nivel.** Vies medio de +0.03 ponto, desvio de 0.03, estavel nos 29 meses da amostra. E a condicao em que ela foi medida vale na serie inteira: a cobertura do segmento fica entre 99.9% e 100.0% na amostra e perto de 100% em todos os anos.

Criterio de estabilidade: a media dos 6 ultimos meses nao pode se afastar da dos 6 primeiros por mais de 0.5 ponto, nem por mais de metade do proprio vies.

## O que esta dimensao e'

O **topo** de cada canal: ranking de 50 posicoes por segmento. Nao e' tabela de sub-segmento -- a cauda e' bem mais rasa que a do painel principal. Um modelo-mes tem ate' duas linhas, uma por canal, e o modelo que nao entra no top-50 de um canal simplesmente nao aparece nele: **ausencia aqui nao e' zero**.

Por isso e' tabela separada, nunca coluna do painel de vendas: os totais nao reconciliam com as tabelas de sub-segmento, porque sao recortes diferentes da mesma realidade.

## Conferencia com o painel principal

Onde o modelo aparece nos dois canais, direta + varejo foi comparado com o total que a tabela de sub-segmento publica: **18417 de 18799** (97.97%) batem exatamente. Sao duas tabelas independentes da fonte reconciliando unidade a unidade.

## Colunas

| coluna | tipo | descricao |
|---|---|---|
| `mes_ref` | texto AAAA-MM | Mes de referencia, no formato do painel principal. |
| `ano, mes` | inteiro | Partes de `mes_ref`. |
| `segmento` | texto | `automoveis` ou `comerciais_leves`. A fonte publica um ranking por segmento, em colunas separadas da mesma pagina. |
| `canal` | texto | `direta` ou `varejo`. Definicao da fonte: venda direta e' o que a montadora negocia com frotista e locadora, mais taxi, produtor rural e PCD; o resto e' varejo. |
| `marca, modelo` | texto | Com a mesma canonizacao de caixa da chave do painel principal (D1), para a juncao ser direta. |
| `unidades` | inteiro | Emplacamentos do modelo no canal, no mes. |
| `posicao_fonte` | inteiro | Posicao no ranking da fonte, de 1 a 50. |
| `nome_completo_fonte` | texto | O nome como a fonte escreveu, letra por letra. |
| `origem_tabela` | texto | `modelo_direta_mes` ou `modelo_varejo_mes`. |
| `arquivo_origem, pagina_origem` | texto, inteiro | O PDF e a pagina de onde a linha saiu. |
| `metodo_extracao` | texto | `texto`, ou `texto_glifos` quando a fonte embutida nao tinha ToUnicode e o texto foi recuperado pela ordem padrao de glifos. |

## O que ficou de fora, de proposito

- **Ranking por marca**: e' grafico de barras com rotulo rotacionado e paineis sobrepostos, em percentual, nao em unidades. E e' redundante: participacao de canal por marca sai de agregar este painel, que e' texto. Numero lido do rotulo de um grafico nao se defende em artigo; numero agregado de tabela de texto, com cobertura declarada, se defende.
- **Tabelas acumuladas no ano**: existem na fonte, mas a chave deste painel nao tem dimensao de periodo, e mistura-las criaria duas linhas para a mesma chave.
