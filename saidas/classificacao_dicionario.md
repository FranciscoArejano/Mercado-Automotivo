# Dicionario de dados -- `classificacao.parquet`, `classificacao_propulsao_anual.parquet` e `classificacao_montagem.parquet`

Gerado em 2026-10-02T20:42:25+00:00 (UTC) por `src/etapa11_classificacao.py`, a partir de
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

Uma linha por `(marca, modelo, segmento, ano)` com unidades no painel:
5,896 linhas. Juncao com o painel: pela chave e pelo ano de `mes_ref`.
Construida em `src/comum/propulsao_anual.py` a partir de `classificacao.parquet`,
do casamento PBE->painel (`saidas/pbe_casamento.csv`) e das fontes datadas de
`dados/referencia/propulsao_fontes.csv`; o ano de entrada de cada tipo, vigencia
a vigencia, fica em `saidas/classificacao_propulsao_entradas.csv`.

| coluna | tipo | descricao |
|---|---|---|
| `marca`, `modelo`, `segmento` | texto | chave do painel |
| `ano` | inteiro | ano civil |
| `unidades` | inteiro | unidades do modelo no ano (soma do painel) |
| `propulsao_no_ano` | texto | tipos oferecidos **naquele ano** (em algum momento dele), unidos por '+' |
| `eletrificacao_no_ano` | texto | derivada de `propulsao_no_ano` pelas regras de sempre: `hibrido_indefinido` e `mhev` nunca levam a `total` |
| `fonte_temporal` | texto | de onde vem o ano de entrada dos tipos eletrificados do ano, o mais fraco deles: `vigencia_sem_datacao` < `pbe_ano` < `fonte_datada` < `vigencia` (so' combustao, ou modelo so' eletrificado) |
| `entrada_dos_tipos` | texto | `tipo=ano fonte` de cada tipo do ano |
| `procedencia_propulsao` | texto | herdada da vigencia; com duas vigencias no ano, a mais fraca |
| `vigencias` | texto | `vigencia_inicio` das vigencias com unidades no ano, separados por ';' |

Ano de entrada de cada tipo:

- **combustao** (gasolina, flex, diesel): o inicio da vigencia (a P2 decidiu o
  que valia antes do PBE; a transicao flex segue sem data);
- **eletrificado** (hev, phev, bev, reev, mhev, hibrido_indefinido): (1) fonte
  datada de lancamento, producao ou presenca a' venda, com o trecho copiado da
  pagina guardada -- `plano` nao conta -- e, onde existe, manda sobre o PBE
  (`fonte_datada`); (2) senao, o ano da primeira tabela do PBE em que uma versao
  daquele tipo aparece para o modelo (`pbe_ano`), desde que haja, dentro da
  vigencia e antes dela, um ano com coluna de propulsao (2021 em diante) em que
  o modelo esta' na tabela sem o tipo -- o marcador no nome prova presenca, nao
  ausencia; (3) senao, o inicio da vigencia (`vigencia_sem_datacao`);
- vigencia so' com tipos eletrificados: o primeiro a entrar, no inicio dela
  (`vigencia`).

O tipo fica ate' o fim da vigencia: a saida de um tipo nao e' modelada. O ano de
PBE se aproxima do ano-modelo e pode estar um ano a' frente da chegada ao
mercado. Num ano com duas vigencias, os tipos sao a uniao das duas.

| fonte_temporal | tipos eletrificados (vigencia x tipo) | % das unidades eletrificadas (parcial + total) |
|---|---:|---:|
| `vigencia` | 30 | 24,7% |
| `fonte_datada` | 22 | 27,4% |
| `pbe_ano` | 35 | 46,9% |
| `vigencia_sem_datacao` | 3 | 1,1% |

### Uso-teste

A serie mais obvia que um artigo faria com a classificacao -- participacao de
cada nivel de eletrificacao nas unidades, por ano -- pelo conjunto da vigencia
(o uso errado) e pela tabela anual. Gravada em `saidas/classificacao_uso_teste.csv`.
`nao_classificado` completa os 100%.

| ano | nenhuma (vigencia) | parcial (vigencia) | total (vigencia) | nenhuma (anual) | parcial (anual) | total (anual) |
|---|---:|---:|---:|---:|---:|---:|
| 2015 | 95,9% | 4,0% | 0,0% | 99,1% | 0,8% | 0,0% |
| 2016 | 92,5% | 7,3% | 0,0% | 99,3% | 0,5% | 0,0% |
| 2017 | 91,4% | 8,4% | 0,1% | 99,2% | 0,5% | 0,1% |
| 2018 | 91,1% | 8,7% | 0,1% | 99,2% | 0,6% | 0,1% |
| 2019 | 90,3% | 9,4% | 0,2% | 97,1% | 2,7% | 0,0% |
| 2020 | 86,6% | 12,9% | 0,2% | 96,9% | 2,6% | 0,2% |
| 2021 | 80,4% | 19,3% | 0,1% | 94,3% | 5,4% | 0,1% |
| 2022 | 78,1% | 21,6% | 0,1% | 88,0% | 11,7% | 0,1% |
| 2023 | 78,1% | 20,3% | 1,4% | 87,9% | 10,5% | 1,4% |
| 2024 | 76,5% | 18,7% | 4,6% | 85,4% | 9,9% | 4,6% |
| 2025 | 73,6% | 19,5% | 6,6% | 78,2% | 14,9% | 6,6% |
| 2026 (jan a ago) | 68,3% | 17,4% | 13,1% | 68,3% | 17,4% | 13,1% |

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
