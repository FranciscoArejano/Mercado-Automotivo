# Dicionario de dados -- `classificacao.parquet`, `classificacao_propulsao_anual.parquet` e `classificacao_montagem.parquet`

Gerado em 2026-10-04T03:55:42+00:00 (UTC) por `src/etapa11_classificacao.py`, a partir de
`saidas/classificacao_rascunho.xlsx`. **O rascunho e' a fonte de verdade da
adjudicacao:** uma decisao se escreve nele, e a etapa roda de novo. Ninguem
edita o parquet a' mao.

**Advertencia.** Um artigo que use propulsao ou origem como variavel de tratamento deve restringir-se as procedencias `humana` e `regra_fonte_forte`, e declarar a fracao do volume que ficou de fora.

**Serie temporal de propulsao: use `classificacao_propulsao_anual.parquet`.**
`propulsao_na_vigencia` e `eletrificacao_na_vigencia` sao o conjunto de tudo que foi oferecido em algum momento da vigência — não usar em série temporal; para isso, `classificacao_propulsao_anual`.

## `classificacao.parquet`

Uma linha por `(marca, modelo, segmento, vigencia_inicio, vigencia_fim)`:
962 linhas -- 438 vigencias de 409 modelos classificados e
524 modelos abaixo do piso de 1,000
unidades, com atributos vazios. Toda chave do painel tem linha em todo mes com
unidades, e as vigencias de um modelo nao se sobrepoem (validado a cada execucao).
Juncao com o painel: pela chave, com `vigencia_inicio <= mes_ref <= vigencia_fim`.

| coluna | tipo | descricao |
|---|---|---|
| `marca`, `modelo`, `segmento` | texto | chave do painel |
| `vigencia_inicio`, `vigencia_fim` | texto AAAA-MM | meses da vigencia, inclusive |
| `propulsao_na_vigencia` | texto | **conjunto de tudo que foi oferecido em algum momento da vigência — não usar em série temporal; para isso, `classificacao_propulsao_anual`.** Conjunto unido por '+': gasolina, flex, diesel, mhev, hibrido_indefinido, hev, phev, reev, bev. O que o modelo oferecia, nao o que vendeu |
| `eletrificacao_na_vigencia` | texto | **conjunto de tudo que foi oferecido em algum momento da vigência — não usar em série temporal; para isso, `classificacao_propulsao_anual`.** Derivada da propulsao: `total` (so' hev/phev/reev/bev), `parcial` (mistura, ou mhev/hibrido_indefinido), `nenhuma`; mesma procedencia da propulsao |
| `procedencia_propulsao` | texto | ver abaixo |
| `carroceria` | texto | hatch, sedan, suv, picape, minivan, furgao, caminhao_leve, perua, esportivo |
| `procedencia_carroceria` | texto | ver abaixo |
| `origem_producao` | texto | nacional, importado, ambos |
| `procedencia_origem` | texto | ver abaixo |
| `vigencia_ajustada_por` | texto | `regra` (O2: fronteira movida para a data da fonte) ou `humana`; vazio se a vigencia e' a proposta |
| `regras_aplicadas` | texto | ids das regras de adjudicacao que decidiram algo na linha (`config/regras_adjudicacao.csv`) |
| `vigencia_inicio_rascunho` | texto | inicio da vigencia no rascunho, para voltar a' linha de origem; vazio abaixo do piso |

### Procedencia

| valor | significado |
|---|---|
| `humana` | decidida pelo pesquisador |
| `regra_fonte_forte` | decidida ou confirmada por regra com fonte oficial ou especializada (inclusive o valor que o PBE ou fonte forte confirmou sem contestacao) |
| `regra_fonte_fraca` | decidida por regra apoiada em fonte fraca, ou sem evidencia positiva (P2) |
| `proposta` | proposta original, nunca tocada por checagem |
| `pendente` | contestada e ainda nao decidida; o valor exibido e' a proposta original |
| `nao_classificado` | modelo abaixo do piso de volume; atributos vazios |

Fracao do volume do painel, por atributo (juncao de teste, gravada em
`saidas/classificacao_procedencia.csv`):

| procedencia | propulsao | carroceria | origem |
|---|---:|---:|---:|
| `humana` | 0,0% | 0,0% | 0,0% |
| `regra_fonte_forte` | 92,0% | 79,4% | 4,9% |
| `regra_fonte_fraca` | 4,1% | 0,0% | 7,3% |
| `proposta` | 0,5% | 20,4% | 81,1% |
| `pendente` | 3,4% | 0,0% | 6,6% |
| `nao_classificado` | 0,1% | 0,1% | 0,1% |

### Limitacoes

- **Conjunto, nao parcela.** A fonte nao separa unidades por versao: um modelo
  `parcial` nao diz quantas unidades foram eletrificadas.
- **`hibrido_indefinido`** marca o modelo que o PBE poe em Hibrido sem que o nome
  da versao ou fonte digam se e' leve ou pleno; conta como `mhev`, e nunca leva a
  `total`.
- **Datas de troca de origem.** A fronteira entre vigencias usa a data de
  lancamento ou chegada ao mercado quando a fonte a da', senao a de producao. Os
  meses entre producao e lancamento sao imprecisos por construcao: num estudo de
  evento, ficam fora da janela.
- **Ausencia no PBE.** A ausencia no PBE so' foi tratada como informativa a partir de 2016, quando o programa passou a cobrir 95,5% do volume do painel.
- **Transicao para o flex** (2003-2006): `gasolina+flex` na vigencia inteira, sem
  data por modelo.

## `classificacao_propulsao_anual.parquet`

Uma linha por `(marca, modelo, segmento, vigencia_inicio, ano)` com unidades no
painel nos meses daquela vigencia naquele ano: 5,912 linhas. Juncao com o
painel: pela chave, pela vigencia (`vigencia_inicio <= mes_ref <= vigencia_fim`) e
pelo ano de `mes_ref`. Construida em `src/comum/propulsao_anual.py` a partir de
`classificacao.parquet`, do casamento PBE->painel (`saidas/pbe_casamento.csv`) e
das fontes datadas de `dados/referencia/propulsao_fontes.csv`. A entrada e a saida
de cada tipo, vigencia a vigencia, nas duas leituras, ficam em
`saidas/classificacao_propulsao_tipos.csv`, com os anos de presenca e de
ausencia que as sustentam.

| coluna | tipo | descricao |
|---|---|---|
| `marca`, `modelo`, `segmento` | texto | chave do painel |
| `vigencia_inicio`, `vigencia_fim` | texto AAAA-MM | a vigencia da classificacao |
| `ano` | inteiro | ano civil |
| `unidades` | inteiro | unidades do painel nos meses da vigencia no ano |
| `propulsao_no_ano` | texto | tipos oferecidos no ano, **leitura longa**: cada tipo dura o maximo que a evidencia permite |
| `eletrificacao_no_ano` | texto | derivada de `propulsao_no_ano` pelas regras de sempre: `hibrido_indefinido` e `mhev` nunca levam a `total` |
| `propulsao_no_ano_curta`, `eletrificacao_no_ano_curta` | texto | o mesmo na **leitura curta**: o minimo que a evidencia permite |
| `fonte_temporal` | texto | de onde vem a entrada dos tipos eletrificados do ano (leitura longa), o mais fraco deles: `vigencia_sem_datacao` < `pbe_ano` < `fonte_datada` < `vigencia` (so' combustao, ou modelo so' eletrificado) |
| `entrada_dos_tipos` | texto | `tipo=ano fonte` de cada tipo do ano (`longa/curta` quando diferem) |
| `saida_dos_tipos` | texto | tipos da vigencia com evidencia de saida: ultimo ano em cada leitura e de onde vem a ausencia (`pbe`, `fonte`) |
| `procedencia_propulsao` | texto | herdada da vigencia |

**Entrada de cada tipo.** Combustao: o inicio da vigencia. Eletrificado: (1) fonte
datada de lancamento, producao ou presenca a' venda -- `plano` nao conta -- que
manda sobre o PBE (`fonte_datada`); (2) senao, o ano da primeira tabela do PBE em
que uma versao daquele tipo aparece (`pbe_ano`), desde que um ano com coluna de
propulsao (2021 em diante), dentro da vigencia e antes dela, mostre o modelo sem o
tipo -- o marcador no nome prova presenca, nao ausencia; (3) senao, o inicio da
vigencia (`vigencia_sem_datacao`). Vigencia so' com tipos eletrificados: o
primeiro a entrar, no inicio dela (`vigencia`).

**Defasagem do PBE**, medida nos tipos com fonte datada e ano de PBE
(`saidas/classificacao_pbe_defasagem.csv`, 21 tipos, 6
comparaveis -- fonte de 2021 em diante): sem direcao dominante: as duas leituras ficam com `pbe_ano`.

**Saida de cada tipo**, com as mesmas fontes. Presenca: o tipo no PBE do ano, fonte
datada ou o ano de entrada. Ausencia, so' de 2021 em diante: o modelo no PBE do
ano com versao de outro tipo da vigencia e sem o tipo, ou fonte datada de fim de
venda ou de importacao. Modelo ausente do PBE nao informa; tipo que some e volta
e' lacuna. Leitura longa: o tipo fica ate' o ano da primeira ausencia depois da
ultima presenca; curta: ate' o ano da ultima presenca. Sem ausencia, as duas o
mantem ate' o fim da vigencia. Ano em que a leitura curta ficaria sem tipo (lacuna
do PBE entre a saida de um tipo e a entrada do seguinte) leva os tipos da longa.
97 tipos tem evidencia de saida. Cada ano de PBE vale para a vigencia
com mais meses nele.

| fonte_temporal | tipos eletrificados (vigencia x tipo) |
|---|---:|
| `vigencia` | 30 |
| `fonte_datada` | 22 |
| `pbe_ano` | 35 |
| `vigencia_sem_datacao` | 3 |

### Uso-teste e banda da eletrificacao

A serie mais obvia que um artigo faria com a classificacao -- participacao de cada
nivel de eletrificacao nas unidades, por ano -- pelo conjunto da vigencia (o uso
errado) e pela tabela anual nas duas leituras, em `saidas/classificacao_uso_teste.csv`.
A banda, em `saidas/eletrificacao_banda.csv` (% das unidades do painel):

- `piso`: `total`;
- `teto`: `total` + `parcial`;
- `teto_sem_mhev`: tira do `parcial` a vigencia-ano cujo unico tipo eletrificado e'
  `mhev` (a definicao da ABVE desde 2025);
- `teto_estrito`: tira a vigencia-ano cujos tipos eletrificados sao so' `mhev` ou
  `hibrido_indefinido`.

| ano | leitura | piso | teto | teto_sem_mhev | teto_estrito |
|---|---|---:|---:|---:|---:|
| 2015 | longa | 0,0% | 0,8% | 0,8% | 0,8% |
| 2015 | curta | 0,0% | 0,8% | 0,8% | 0,8% |
| 2016 | longa | 0,0% | 0,6% | 0,6% | 0,6% |
| 2016 | curta | 0,0% | 0,6% | 0,6% | 0,6% |
| 2017 | longa | 0,1% | 0,6% | 0,6% | 0,6% |
| 2017 | curta | 0,1% | 0,4% | 0,4% | 0,4% |
| 2018 | longa | 0,1% | 0,7% | 0,7% | 0,6% |
| 2018 | curta | 0,1% | 0,6% | 0,6% | 0,5% |
| 2019 | longa | 0,2% | 1,2% | 1,2% | 1,1% |
| 2019 | curta | 0,2% | 1,1% | 1,1% | 1,0% |
| 2020 | longa | 0,2% | 2,8% | 2,8% | 2,8% |
| 2020 | curta | 0,2% | 2,7% | 2,7% | 2,7% |
| 2021 | longa | 0,1% | 5,5% | 5,5% | 5,5% |
| 2021 | curta | 0,1% | 5,3% | 5,3% | 5,3% |
| 2022 | longa | 0,2% | 11,8% | 10,7% | 10,6% |
| 2022 | curta | 0,4% | 10,2% | 9,1% | 9,1% |
| 2023 | longa | 1,8% | 10,6% | 9,3% | 9,3% |
| 2023 | curta | 1,8% | 10,6% | 9,3% | 9,3% |
| 2024 | longa | 4,8% | 13,7% | 11,4% | 11,4% |
| 2024 | curta | 4,8% | 13,7% | 11,4% | 11,4% |
| 2025 | longa | 6,8% | 21,1% | 16,3% | 16,3% |
| 2025 | curta | 6,8% | 18,1% | 13,4% | 13,4% |
| 2026 (jan a ago) | longa | 13,2% | 28,2% | 18,8% | 18,7% |
| 2026 (jan a ago) | curta | 13,2% | 28,1% | 18,7% | 18,6% |

## `classificacao_montagem.parquet`

Periodos de montagem local, no padrao de vigencia do mapa de grupos: 968
periodos que cobrem os meses das vigencias de cada modelo, sem sobreposicao.

| coluna | descricao |
|---|---|
| `marca`, `modelo`, `segmento` | chave do painel |
| `vigencia_inicio`, `vigencia_fim` | a vigencia de classificacao a que o periodo pertence |
| `origem_producao` | origem final da vigencia |
| `montagem_inicio`, `montagem_fim` | meses do periodo, inclusive |
| `montagem_local` | `fabricacao`, `ckd`, `skd` (so' no periodo que a fonte declara), `desconhecido` (fora dele), `nao_se_aplica` (vigencia importada), vazio abaixo do piso |
| `procedencia` | `regra_fonte_forte`/`regra_fonte_fraca` pelo tipo da fonte do modo; em `nao_se_aplica`, a da origem; `proposta` em `desconhecido`; `nao_classificado` abaixo do piso |
| `fonte_url`, `tipo_fonte`, `observacao` | a fonte do modo e a leitura dela |

Kit e carro inteiro tem tratamento tributario diferente: para o artigo de tarifa,
o periodo e' a variavel. Fontes em `dados/referencia/montagem_fontes.csv`.
