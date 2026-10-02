# Dicionario de dados -- `classificacao.parquet` e `classificacao_montagem.parquet`

Gerado em 2026-10-02T16:04:11+00:00 (UTC) por `src/etapa11_classificacao.py`, a partir de
`saidas/classificacao_rascunho.xlsx`. **O rascunho e' a fonte de verdade da
adjudicacao:** uma decisao se escreve nele, e a etapa roda de novo. Ninguem
edita o parquet a' mao.

**Advertencia.** Um artigo que use propulsao ou origem como variavel de tratamento deve restringir-se as procedencias `humana` e `regra_fonte_forte`, e declarar a fracao do volume que ficou de fora.

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
| `propulsao_oferecida` | texto | conjunto unido por '+': gasolina, flex, diesel, mhev, hibrido_indefinido, hev, phev, reev, bev. O que o modelo oferecia, nao o que vendeu |
| `eletrificacao` | texto | derivada da propulsao: `total` (so' hev/phev/reev/bev), `parcial` (mistura, ou mhev/hibrido_indefinido), `nenhuma`; mesma procedencia da propulsao |
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
