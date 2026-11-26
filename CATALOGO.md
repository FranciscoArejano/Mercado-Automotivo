# Catalogo do repositorio -- dado do commit `ad598df`

Gerado por `src/etapa10_catalogo.py` a cada execucao do pipeline. **Nao editar a mao**: janelas, linhas e contagens saem dos arquivos. O texto de usos esta' em `config/catalogo_usos.csv` e as fontes candidatas em `config/fontes_candidatas.csv`; edite la' e rode `python src/etapa10_catalogo.py`.

O commit da primeira linha e' o ultimo que alterou o dado descrito (`dados/processado`, `dados/referencia`, `dados/bruto/manifesto.csv`, `dados/bruto/pbe`, `dados/bruto/origem_paginas`, `dados/bruto/comex`, `dados/bruto/politicas_paginas`, `dados/bruto/fabricas_paginas`, `dados/bruto/anfavea`, `dados/bruto/ibge`, `dados/bruto/senatran_frota`, `dados/bruto/anp_precos`, `dados/bruto/seeg`, `dados/bruto/mcti_fator`, `dados/bruto/acesso_fontes_energia.csv`, `config`, `regras.csv`, `saidas/classificacao_rascunho.xlsx`); `-sujo` quer dizer que ha' alteracao nao comitada nesses caminhos, e o catalogo nao corresponde exatamente a nenhum commit.

## Indice

| produto | arquivo | linhas | janela efetiva |
|---|---|---|---|
| painel | `dados/processado/painel.parquet` | 54.179 | 2003-01..2026-08 |
| painel_bruto | `dados/processado/painel_bruto.parquet` | 54.183 | 2003-01..2026-08 |
| painel_canal | `dados/processado/painel_canal.parquet` | 48.996 | 2003-01..2026-08 |
| macro_mensal | `dados/processado/macro_mensal.parquet` | 284 | 2003-01..2026-08 |
| classificacao | `dados/processado/classificacao.parquet` | 962 | 2003-01 a 2026-08 |
| comex_veiculos | `dados/processado/comex_veiculos.parquet` | 73.316 | 1997-01 a 2026-08 |
| politicas_mensal | `dados/processado/politicas_mensal.parquet` | 2.725 | 2003-01 a 2026-08 |
| classificacao_origem | `dados/processado/classificacao_origem.parquet` | 1.938 | 2003-01 a 2026-08 |
| fator_emissao_sin_mensal | `dados/processado/fator_emissao_sin_mensal.parquet` | 250 | 2006-01 a 2026-10 |
| emissoes_uf_anual | `dados/processado/emissoes_uf_anual.parquet` | 552.713 | 2003 a 2025 |
| frota_municipal | `dados/processado/frota_municipal.parquet` | 11.306.332 | 2003-12 a 2026-10 |
| precos_combustiveis_mensal | `dados/processado/precos_combustiveis_mensal.parquet` | 23.681 | 2004-05 a 2026-10 |

## Parte A -- o que existe

### `painel`

- **Unidade de observacao:** o modelo (variante comercial) no mes e no sub-segmento em que a fonte o listou.
- **Chave:** `(mes_ref, marca, modelo, segmento)`; `sub_segmento_fonte` e' atributo da linha, e com ele a combinacao e' unica (conferida).
- **Janela efetiva:** 2003-01..2026-08 (284 meses com dado; meses sem informe legivel: nenhuma).
- **Linhas:** 54.179; modelos: 933; unidades: 57.700.201; linhas com zero unidades: 3.836.
- **Marcacoes:** 363 linhas com `nome_suspeito`; 4 com `marca_recuperada`; 0 com `houve_rebatismo`.
- **Cobertura do total publicado** (`saidas/cobertura.csv`): automoveis mediana 98,92%, minimo 94,54%; comerciais_leves mediana 99,97%, minimo 97,38%.
- **Dicionario:** `saidas/painel_dicionario.md`; validacao: `saidas/validacao.md`.
- **Ressalvas principais:** regras.csv vazio: nada foi fundido, e as taxas de entrada e saida sao o limite superior. A fonte trunca a cauda (cobertura abaixo de 100%, conferida mes a mes em saidas/cobertura.csv). O ultimo ano e' parcial e nao se cita para rotatividade. Nomes suspeitos sao marcados, nao apagados. O sub-segmento e' atributo da linha, fora da chave.

### `painel_bruto`

- **Unidade de observacao:** a linha publicada no informe, como a fonte a escreveu.
- **Chave:** `(mes_ref, segmento_fonte, origem_tabela, sub_segmento_fonte, posicao_fonte)` -- a posicao da linha na tabela da fonte.
- **Janela efetiva:** 2003-01..2026-08 (284 meses com dado; sem dado: nenhuma).
- **Linhas:** 54.183; unidades: 57.709.372.
- **Metodo de extracao:** `texto` 53.047; `texto_glifos` 969; `reconstruido` 167.
- **Tabela de origem:** `sub_segmento` 48.012; `ranking` 6.004; `mes_anterior` 167.
- **Duplicatas publicadas pela fonte, marcadas e fora do painel:** 4.
- **Ressalvas principais:** Transcricao fiel da fonte (ESPEC sec.4); nunca sobrescrito sem --recriar. As linhas com duplicata_publicada ficam fora do painel e do invariante central.

### `painel_canal`

- **Unidade de observacao:** o modelo no mes, no segmento e no canal (venda direta ou varejo), dentro do top-50 que a fonte publica por canal.
- **Chave:** `(mes_ref, segmento, canal, marca, modelo)`, unica (conferida).
- **Janela efetiva:** 2003-01..2026-08 (281 meses com dado; sem dado: `2003-10`, `2005-03`, `2023-09`).
- **Linhas:** 48.996 (`varejo` 26.516; `direta` 22.480); unidades: 54.848.238.
- **Dicionario e advertencia do U:** `saidas/painel_canal_dicionario.md`.
- **Ressalvas principais:** Top-50 por canal e segmento; a cauda e' mais rasa que a do painel. Toda serie temporal vai ao lado de saidas/canal_cobertura.csv. Dicionario proprio: saidas/painel_canal_dicionario.md.

### `macro_mensal`

- **Unidade de observacao:** o mes.
- **Chave:** `mes_ref`, unica (conferida); uma coluna por serie (duas por subitem do IPCA: variacao e indice encadeado).
- **Janela efetiva do arquivo:** 2003-01..2026-08 (284 meses; sem linha: nenhuma). A janela de cada serie esta' abaixo.
- **Linhas:** 284; colunas de dado: 22; series documentadas: 17.

| codigo | nome | fonte | unidade | janela efetiva | observacoes | colunas | natureza_e_ressalvas |
|---|---|---|---|---|---|---|---|
| `20749` | Taxa media de juros -- PF aquisicao de veiculos | BCB/SGS | % a.a. | 2003-01..2026-08 | 284 | `sgs_20749` | Taxa media de juros das operacoes de credito livre para aquisicao de veiculos por pessoa fisica. Nivel, em % a.a. Sem ressalva conhecida. |
| `20603` | Saldo da carteira -- PF aquisicao de veiculos | BCB/SGS | R$ milhoes | 2007-03..2026-08 | 234 | `sgs_20603` | Estoque (saldo) da carteira de credito para veiculos PF. Nivel nominal, nao deflacionado. Comeca em 2007-03: os 50 meses anteriores sao lacuna, nao zero. |
| `21131` | Prazo medio -- PF aquisicao de veiculos | BCB/SGS | meses | 2011-03..2026-08 | 186 | `sgs_21131` | Prazo medio das operacoes, em meses. Comeca em 2011-03. |
| `20758` | Inadimplencia -- PF aquisicao de veiculos | BCB/SGS | % da carteira | 2011-03..2026-08 | 186 | `sgs_20758` | Inadimplencia da carteira de veiculos PF, % da carteira. Comeca em 2011-03. |
| `20126` | Concessoes -- PF aquisicao de veiculos | BCB/SGS | R$ milhoes | 2004-02..2022-12 | 227 | `sgs_20126` | DESCONTINUADA em 2022-12. Fluxo nominal de concessoes. Os 44 meses finais do painel sao lacuna -- nao estender com o ultimo valor, nao substituir por serie parecida sem decisao. |
| `3698` | Cambio R$/US$ venda -- media do periodo | BCB/SGS | R$/US$ | 2003-01..2026-08 | 284 | `sgs_3698` | Cambio medio mensal de venda. Nivel. |
| `4390` | Selic acumulada no mes | BCB/SGS | % a.m. | 2003-01..2026-08 | 284 | `sgs_4390` | Selic acumulada no mes. Vai um mes alem do painel (2026-09); o mes extra fica fora da juncao. |
| `4189` | Selic acumulada em 12 meses | BCB/SGS | % a.a. | 2003-01..2026-08 | 284 | `sgs_4189` | Selic acumulada em 12 meses. Janela movel -- os meses sucessivos se sobrepoem em 11 de 12, entao nao somar nem tratar como independentes. |
| `433` | IPCA -- variacao mensal | BCB/SGS | % a.m. | 2003-01..2026-08 | 284 | `sgs_433` | IPCA cheio, variacao mensal. Encadear para ter nivel. |
| `4192` | IGP-DI -- numero indice | BCB/SGS | indice (base a confirmar) | 2003-01..2026-08 | 284 | `sgs_4192` | IGP-DI em NUMERO INDICE, mas a ordem de grandeza (501.192 a 2.642.850) nao e' de indice base 100: a base nao foi confirmada. Usar em VARIACAO, nao em nivel, ate' confirmar. |
| `24363` | IBC-Br | BCB/SGS | indice | 2003-01..2026-07 | 283 | `sgs_24363` | IBC-Br, proxy mensal do PIB, dessazonalizado pelo BCB. Termina em 2026-07: um mes a menos que o painel. |
| `7832` | Massa salarial real | BCB/SGS | % (variacao) | 2003-01..2019-08 | 200 | `sgs_7832` | DESCONTINUADA em 2019-08. A ordem de grandeza (-24,80 a 16,97, alternando de sinal) mostra que e' VARIACAO percentual, nao nivel de massa salarial. Os 84 meses finais sao lacuna. |
| `ipca_7641` | IPCA subitem 5102001 -- Automovel novo | IBGE/SIDRA | % a.m. e indice encadeado (base 2003-01=100) | 2003-01..2026-08 | 284 | `ipca_automovel_novo_var_pct`, `ipca_automovel_novo_indice` | Preco de automovel novo no IPCA. Indice encadeado com base declarada 2003-01 = 100, efetiva igual. |
| `ipca_107654` | IPCA subitem -- Automovel usado | IBGE/SIDRA | % a.m. e indice encadeado (base 2003-01=100) | 2006-07..2026-08 | 242 | `ipca_automovel_usado_var_pct`, `ipca_automovel_usado_indice` | NAO E' PRECO DE MERCADO DE USADO: e' INDICE DE DEPRECIACAO. O subitem acompanha um veiculo que envelhece. Medido no dado: 143 dos 242 meses com variacao negativa, media mensal de -0,160%, indice de 99,58 em 2006-07 a 67,31 em 2026-08 -- queda de 32,4% na janela em que o automovel novo subiu 42,0%. Usa-lo como preco do bem substituto num modelo de demanda e' erro conceitual. Comeca em 2006-07: na tabela 655 o SIDRA aceita o codigo mas devolve '...' nos 83 meses, e o tratamento como ausente esta' correto. A base declarada 2003-01 = 100 e' VAZIA para esta serie; a base efetiva e' 2006-06 = 100. |
| `ipca_7657` | IPCA subitem -- Gasolina | IBGE/SIDRA | % a.m. e indice encadeado (base 2003-01=100) | 2003-01..2026-08 | 284 | `ipca_gasolina_var_pct`, `ipca_gasolina_indice` | Preco da gasolina no IPCA. Indice encadeado, base 2003-01 = 100. |
| `ipca_7658` | IPCA subitem -- Etanol | IBGE/SIDRA | % a.m. e indice encadeado (base 2003-01=100) | 2003-01..2026-08 | 284 | `ipca_etanol_var_pct`, `ipca_etanol_indice` | Preco do etanol no IPCA. Indice encadeado, base 2003-01 = 100. |
| `ipca_7654` | IPCA subitem -- Motocicleta | IBGE/SIDRA | % a.m. e indice encadeado (base 2003-01=100) | 2003-01..2026-08 | 284 | `ipca_motocicleta_var_pct`, `ipca_motocicleta_indice` | Preco da motocicleta no IPCA. Indice encadeado, base 2003-01 = 100. |

- **Ressalvas principais:** Lacuna e' lacuna: serie que comeca depois de 2003-01 ou termina antes do fim fica vazia, sem interpolacao. Ler natureza_e_ressalvas de cada serie antes de usar (tabela acima).

### `classificacao`

- **Estado: dimensao gravada (fase 2)** pela etapa 11, a partir do rascunho adjudicado `saidas/classificacao_rascunho.xlsx`, que e' a fonte de verdade da adjudicacao. Ninguem edita o parquet a' mao.
- **Unidade de observacao:** o modelo `(marca, modelo, segmento)` numa vigencia (`vigencia_inicio`, `vigencia_fim`); juncao com o painel pela chave e o mes.
- **Linhas:** 962 -- 438 vigencias de 409 modelos classificados e 524 modelos abaixo do piso de 1.000 unidades (`nao_classificado`). Toda chave do painel tem linha em todo mes com unidades (validado a cada execucao).
- **Procedencia, do volume do painel:**

| procedencia | propulsao | carroceria | origem |
|---|---:|---:|---:|
| `humana` | 0,1% | 0,0% | 0,0% |
| `nao_classificado` | 0,1% | 0,1% | 0,1% |
| `pendente` | 3,2% | 0,0% | 6,6% |
| `proposta` | 0,5% | 20,4% | 81,1% |
| `regra_fonte_forte` | 91,9% | 79,4% | 4,9% |
| `regra_fonte_fraca` | 4,1% | 0,0% | 7,3% |

- **Advertencia:** um artigo que use propulsao ou origem como variavel de tratamento deve restringir-se as procedencias `humana` e `regra_fonte_forte`, e declarar a fracao do volume que ficou de fora.
- **Pendentes:** 100 linhas em `a_adjudicar`; o dado as mostra com a proposta original e procedencia `pendente`.
- **Montagem local:** `dados/processado/classificacao_montagem.parquet`, 968 periodos, 6 deles com modo declarado por fonte (`fabricacao`, `ckd`, `skd`); o resto e' `desconhecido` ou `nao_se_aplica`.
- **Serie temporal de propulsao:** `dados/processado/classificacao_propulsao_anual.parquet`, 5.912 linhas `(marca, modelo, segmento, vigencia_inicio, ano)` com os tipos oferecidos no ano em duas leituras (`propulsao_no_ano` longa, `propulsao_no_ano_curta`). `propulsao_na_vigencia` e `eletrificacao_na_vigencia` sao o conjunto de tudo que foi oferecido em algum momento da vigencia -- nao usar em serie temporal. Dos 88 tipos eletrificados (vigencia x tipo), 5 entram sem datacao (`vigencia_sem_datacao`); 92 tipos tem evidencia de saida. Banda da eletrificacao (piso e tres tetos) em `saidas/eletrificacao_banda.csv`; uso-teste em `saidas/classificacao_uso_teste.csv`.
- **Arquivos:** dicionario em `saidas/classificacao_dicionario.md`; procedencia por atributo em `saidas/classificacao_procedencia.csv`; regras em `config/regras_classificacao.csv` e `config/regras_adjudicacao.csv`; mapeamento do PBE em `config/pbe_propulsao.csv` e `config/pbe_modelos.csv`; tipo de fonte em `config/tipo_fonte_dominio.csv`.
- **Ressalvas principais:** Dimensao gravada (etapa 11) a partir do rascunho adjudicado. Origem ainda e' quase toda `proposta`; um artigo que use propulsao ou origem como tratamento deve restringir-se as procedencias `humana` e `regra_fonte_forte` e declarar a fracao que ficou de fora.

### `comex_veiculos`

- **Estado: dimensao gravada** pela etapa 12, a partir das respostas do Comex Stat (MDIC) guardadas em `dados/bruto/comex/` com SHA-256 no manifesto.
- **Unidade de observacao:** fluxo (importacao, exportacao) x NCM x pais x mes, posicoes 8703 (automoveis) e 8704 (veiculos de carga); tabela separada do painel.
- **Linhas:** 73.316; 48 NCMs, 178 paises.
- **NCMs:** `config/ncm_veiculos.csv`, com `grupo_propulsao_ncm` (as subposicoes de eletrificados existem desde 2017-01 em 8703 e 2022-04 em 8704; antes, `sem_separacao`) e `leve` (8704 com peso em carga maxima ate' 5 t; nao casa exatamente com os comerciais leves da Fenabrave).
- **Unidades:** `unidades` e' a publicada; `unidades_ajustadas` estima pelo peso as linhas com menos de 500 kg por unidade publicada (2.035 linhas) e e' o padrao para contar carros. O agregado de carros (`agregado_carros`) tira 8703.10 (neve, golfe) e o 8704 nao leve ou sem peso na descricao.
- **Ressalvas:** o hibrido leve nao tem NCM propria; kit SKD ou CKD entra na NCM do veiculo completo, entao a importacao pode incluir kits para montagem local.
- **Conferencias:** 0 falhas em `saidas/comex_validacao.csv`; dicionario em `saidas/comex_dicionario.md`.
- **Ressalvas principais:** Antes das subposicoes de eletrificados (2017-01 em 8703, 2022-04 em 8704) nenhuma NCM separa o eletrificado. Kit SKD ou CKD entra na NCM do veiculo completo. Em 2001, 2003, 2006 e 2019-2021 parte relevante das unidades publicadas esta' em linhas com menos de 500 kg por unidade, em que a quantidade nao e' de carros; use `unidades_ajustadas`, que as estima pelo peso (saidas/comex_diagnostico_peso.csv).

### `politicas_mensal`

- **Estado: dimensao gravada** pela etapa 13, a partir de duas tabelas de referencia escritas a' mao (`dados/referencia/politicas_atos.csv`, `politicas_aliquotas.csv`), cada linha com trecho literal de uma das 74 paginas oficiais guardadas em `dados/bruto/politicas_paginas/` (Planalto, Diario Oficial, gov.br, Banco Central), com SHA-256 no manifesto.
- **Unidade de observacao:** mes x ato em vigor; junta ao painel pelo `mes_ref`.
- **Atos:** 65 -- acordo_automotivo 12, credito 10, imposto_importacao 5, ipi 26, programa_desconto 2, regime_automotivo 6, regulacao 4.
- **Aliquotas:** 422 linhas, so' as que o proprio ato fixa (ii 86, iof 8, ipi 328); NCM com os pontos da TIPI, prefixo da NCM do Comex Stat.
- **Ressalvas:** nao e' a TIPI inteira; `vigencia_fim` vazia quer dizer em vigor ou fim nao confirmado em pagina aberta; o uso-teste (`saidas/politicas_uso_teste.csv`) marca datas sem movimento, nao estima efeito.
- **Conferencias:** 0 falhas em `saidas/politicas_validacao.csv`; dicionario em `saidas/politicas_dicionario.md`.
- **Ressalvas principais:** vigencia_fim vazia quer dizer em vigor ou fim nao confirmado em pagina aberta. O fim da Camex 97 (31/12/2023) e o inicio do ACE-55 sao inferidos. Cinco aliquotas de 2022 sao derivadas (18,5% do Decreto 10.979). Faltam o 8704, o protocolo argentino de 2013-2014 e o fim da quota de carros do desconto de 2023 (noticia do MDIC, sem pagina oficial aberta).

### `classificacao_origem`

- **Estado: dimensao gravada** pela etapa 14, ao lado de `classificacao.parquet` (que nao muda): pais de producao por vigencia e periodo, a partir da proposta do assistente (`dados/referencia/origem_pais_proposta.csv`) confirmada por fonte (`fabricas.csv`, `fabrica_modelos.csv`), cada linha de fonte com trecho literal de pagina guardada (128 em `dados/bruto/fabricas_paginas/`, mais as de `origem_paginas/`).
- **Unidade de observacao:** vigencia x periodo x pais de producao; dois paises no mesmo periodo sao duas linhas.
- **Fabricas:** 55 (35 no Brasil, com municipio, UF e codigo IBGE); 861 linhas de fabrica x modelo (abastece_o_brasil 107, producao_local 335, producao_no_exterior 419).
- **Procedencia** (linhas classificadas): `pendente` 20, `proposta` 626, `regra_fonte_forte` 768.
- **Cobertura por fonte forte** (unidades do painel): 2003 89,7%, 2004 89,4%, 2005 89,4%, 2006 88,9%, 2007 85,9%, 2008 88,2%, 2009 89,1%, 2010 87,7%, 2011 82,3%, 2012 85,0%, 2013 84,7%, 2014 84,1%, 2015 84,9%, 2016 86,0%, 2017 86,3%, 2018 87,6%, 2019 84,4%, 2020 84,5%, 2021 81,8%, 2022 83,6%, 2023 78,1%, 2024 67,5%, 2025 64,2%, 2026 27,4%. Abaixo da meta de 80%: 2023, 2024, 2025, 2026.
- **Divergencias ao rascunho:** 49 (`saidas/origem_divergencias.csv`, aba `origem_pais`).
- **Conferencias:** 0 falhas em `saidas/origem_validacao.csv`; dicionario em `saidas/origem_dicionario.md`; uso-testes em `saidas/origem_uso_teste_*.csv` e `saidas/origem_mapa_uf.csv`.
- **Ressalvas principais:** Cobertura por fonte forte acima de 80% das unidades em cada ano de 2003 a 2022; abaixo em 2023 a 2026 (pagina so' cobre ate' a sua data, e ha' poucas paginas recentes). A ADEFA confirma pais ja' proposto, nao diz que o carro abastece o Brasil. Ano sem mes na fonte vira janeiro no inicio e dezembro no fim. `classificacao.parquet` nao foi sobrescrita: as divergencias estao em saidas/origem_divergencias.csv e na aba `origem_pais` do rascunho.

### `fator_emissao_sin_mensal`

- **Estado: gravada** pela etapa 15, da planilha do MCTI (fator medio, metodo para inventarios) guardada em `dados/bruto/mcti_fator/` com SHA-256.
- **Unidade de observacao:** o mes (tCO2/MWh da geracao do SIN).
- **Linhas:** 250; janela efetiva 2006-01 a 2026-10 (o MCTI comeca em 2006-01: 2003-2005 ficam vazios).
- **No repositorio:** 0,0 MB de bruto em `dados/bruto/mcti_fator/` (sem `fora_do_git/`) e 0,0 MB de produto.
- **Conferencias:** 0 falhas em `saidas/fator_emissao_sin_validacao.csv`; dicionario em `saidas/fator_emissao_sin_mensal_dicionario.md`.
- **Ressalvas principais:** Fator medio (inventarios), nao o de margem de operacao. A base do ONS foi ampliada em 2025-01.

### `emissoes_uf_anual`

- **Estado: gravada** pela etapa 16, do bruto reduzido da tabela geral do SEEG (colecao 14.0), original de 206 MB fora do git, SHA-256 do original e do reduzido no manifesto.
- **Unidade de observacao:** tipo (emissao, remocao, bunker, NCI) x UF x ano x setor x categoria x subcategoria x produto x gas; `uf` vazia e' a parcela nao alocada.
- **Linhas:** 552.713; janela efetiva 2003 a 2025 (anual; o SEEG publica desde 1970, o reduzido guarda de 2003 em diante); 19 gases, incluindo `CO2e_GWP_AR5`.
- **No repositorio:** 13,4 MB de bruto em `dados/bruto/seeg/` (sem `fora_do_git/`) e 3,7 MB de produto.
- **Conferencias:** 0 falhas em `saidas/emissoes_uf_anual_validacao.csv`; dicionario em `saidas/emissoes_uf_anual_dicionario.md`.
- **Ressalvas principais:** Colecao 14.0 do SEEG (recalcula a serie inteira). CO2e pelo GWP-AR5. A parcela nao alocada fica com uf vazia.

### `frota_municipal`

- **Estado: gravada** pela etapa 17, das planilhas da Senatran guardadas em `dados/bruto/senatran_frota/` (todas abaixo de 50 MB, como vieram) com SHA-256.
- **Unidade de observacao:** municipio x mes x tipo de veiculo **ou** combustivel (a fonte nao cruza os dois: `recorte` diz qual; nao somar entre recortes).
- **Linhas:** 11.306.332; 5571 municipios. Janela efetiva: tipo 99 meses (2003-12 a 2026-10; dezembro ate' 2019, todos os meses desde 2020-01); combustivel 84 meses (2013-12 a 2026-10).
- **Alertas da fonte:** 39.321 linhas marcadas (`combustivel_fora_de_escala`: 2021-11 vem x10 na fonte; valor mantido).
- **No repositorio:** 224,2 MB de bruto em `dados/bruto/senatran_frota/` (sem `fora_do_git/`) e 35,7 MB de produto.
- **Conferencias:** 0 falhas em `saidas/frota_validacao.csv`; por UF e mes em `saidas/frota_conferencia_uf.csv`; rotulos em `config/frota_rotulos.csv`; municipios fora da tipografia em `config/frota_municipios.csv`; dicionario em `saidas/frota_municipal_dicionario.md`.
- **Ressalvas principais:** Nao somar entre recortes. Combustivel de 2021-11 vem x10 na fonte (alerta_fonte). ELETRICO/FONTE INTERNA e' rotulo ambiguo, mantido a' parte.

### `precos_combustiveis_mensal`

- **Estado: gravada** pela etapa 18, da serie historica por posto do LPC da ANP (`dados/bruto/anp_precos/`: originais de ate' 50 MB como vieram; os maiores fora do git, com bruto reduzido em parquet e os dois SHA-256 no manifesto).
- **Unidade de observacao:** UF x mes x produto (gasolina comum, etanol hidratado, diesel S10, GNV); e, em `precos_combustiveis_municipal_mensal.parquet`, municipio x mes x produto.
- **Linhas:** 23.681 (UF) e 378.808 (municipio, 702 municipios); janela efetiva 2004-05 a 2026-10 (a serie por posto comeca em 2004-05).
- **No repositorio:** 299,3 MB de bruto em `dados/bruto/anp_precos/` (sem `fora_do_git/`) e 10,0 MB de produto.
- **Conferencias:** 0 falhas em `saidas/precos_combustiveis_validacao.csv`; contra a sintese mensal da ANP em `saidas/precos_combustiveis_conferencia_sintese.csv`; dicionario em `saidas/precos_combustiveis_mensal_dicionario.md`.
- **Ressalvas principais:** Amostra do LPC muda no tempo; sem pesquisa de 18/8/2020 a 17/10/2020. Preco real em R$ de 2026-08.

### Outros arquivos

| arquivo | conteudo |
|---|---|
| `dados/bruto/pdf/` | 284 informes originais da Fenabrave, hash em `dados/bruto/manifesto.csv` |
| `dados/bruto/pbe/` | 18 tabelas do PBE Veicular (Inmetro), com manifesto SHA-256; extracao em `saidas/pbe_versoes.csv` |
| `dados/bruto/origem_paginas/` | 137 paginas de fonte de origem, abertas e guardadas, com SHA-256 |
| `dados/bruto/politicas_paginas/` | 74 paginas oficiais do calendario de politicas, abertas e guardadas, com SHA-256 |
| `dados/bruto/fabricas_paginas/` | 128 paginas de fabrica e de fabrica x modelo (Anfavea, ADEFA, INEGI, montadoras, imprensa), com SHA-256 |
| `dados/bruto/anfavea/` | 3 paginas dos anuarios da Anfavea (licenciamento de nacionais e importados), com SHA-256 |
| `dados/bruto/ibge/` | tabela de municipios do IBGE (codigo do municipio das fabricas), com SHA-256 |
| `dados/bruto/acesso_fontes_energia.csv` | testes de acesso das fontes da rodada 13 (cada tentativa, com o resultado) |
| `dados/bruto/senatran_frota/` | planilhas de frota da Senatran (municipio x tipo, municipio x combustivel, UF x tipo), com SHA-256 |
| `dados/bruto/anp_precos/` | serie por posto do LPC da ANP (originais ate' 50 MB; os maiores como bruto reduzido em parquet) e a sintese mensal por estado, com SHA-256 |
| `dados/bruto/seeg/` | tabela geral do SEEG 14.0 como bruto reduzido (original fora do git), com os dois SHA-256 |
| `dados/bruto/mcti_fator/` | planilha do fator medio de emissao do SIN (MCTI), com SHA-256 |
| `regras.csv` | 0 regras de harmonizacao (rebatismo, desdobramento) |
| `config/mapa_grupos.csv` | 148 linhas marca-grupo com vigencia |
| `dados/referencia/Vendas_Geral.xlsx` | controle independente (ESPEC sec.7), nao fonte |
| `saidas/validacao.md` | invariantes, taxas e testes da rodada, com o commit |
| `saidas/candidatos.xlsx` | pares candidatos a rebatismo, para adjudicacao |
| `saidas/referencia_cruzada.md` | confronto com o controle independente |

## Parte B -- o que destrava

### Produtos

| produto | sustenta | nao sustenta |
|---|---|---|
| `painel` | Participacao de mercado e concentracao (HHI) por marca, grupo economico e modelo, mes a mes desde 2003. Ciclo de vida do nome comercial: entrada, saida e sobrevivencia, com os pisos de volume e de pico. Sazonalidade e choques (IPI, crises, pandemia) no mercado e no modelo. Com a classificacao adjudicada (fase 2): eletrificacao, SUVizacao, nacional contra importado. | Preco, versao e propulsao (ainda). Venda por UF. Geracao do produto, salvo onde a fonte a separa em sub-segmentos. A cauda abaixo do corte de publicacao: zero quer dizer 'abaixo do corte daquele mes'. |
| `painel_bruto` | Auditoria e reconstituicao: cada numero volta ao PDF e a' pagina de origem. Reprocessar com outras regras de harmonizacao sem reler os informes. | Analise direta: marca como publicada, grafias cruas, sem harmonizacao, com as duplicatas publicadas pela fonte ainda dentro (marcadas). |
| `painel_canal` | Composicao dentro do canal e dentro do ano: que modelos dependem de venda direta (locadora, frotista, PCD) e quais do varejo. Participacao da venda direta no nivel, so' em comerciais leves. | Nivel entre anos em automoveis (o U da cobertura). Participacao de venda direta em automoveis como nivel. Ranking de marca (descartado de proposito). Ausencia no top-50 nao e' zero. |
| `macro_mensal` | Controles e choques mensais para o painel: credito (juros, prazo, inadimplencia, saldo, concessoes), cambio, Selic, inflacao e atividade; preco relativo do automovel novo, do usado e dos combustiveis. | Preco por modelo ou por versao. Qualquer mes fora da janela efetiva de cada serie. |
| `classificacao` | Eletrificacao da oferta por ano (classificacao_propulsao_anual, leituras longa e curta, e a banda piso-teto em saidas/eletrificacao_banda.csv), SUVizacao por carroceria, nacional contra importado, e as regras de elegibilidade de politica que dependem desses atributos. | Unidades por versao ou por propulsao: a fonte nao separa. Eletrificacao 'parcial' nao diz quantas unidades foram eletrificadas. Serie temporal pela propulsao da vigencia (propulsao_na_vigencia): e' o conjunto do que foi oferecido em algum momento dela. |
| `comex_veiculos` | Importacao e exportacao mensal de automoveis (8703) e veiculos de carga (8704) por NCM e pais desde 1997: origem do que se importa, peso de cada pais, exportacoes como proxy de producao exportada, e, desde 2017 (8703) e 2022 (8704), a separacao entre combustao, hibrido, plug-in e eletrico puro na fronteira. | Vendas: importado entra no estoque antes de ser emplacado. Modelo ou marca: a NCM nao identifica o veiculo. Hibrido leve: nao tem NCM propria. Comerciais leves no sentido da Fenabrave: `leve` segue o peso em carga maxima da NCM. |
| `politicas_mensal` | Calendario dos atos que mexem no mercado de carros novos desde 2003: IPI (TIPI de 2003, 2007, 2017 e 2022; cortes de 2003-2004, 2008-2010, 2012-2014 e 2022; hibridos e eletricos em 2018; IPI Verde em 2025), regimes automotivos (Inovar-Auto, Rota 2030, Mover), imposto de importacao de eletrificados (Camex 2014-2015, Gecex 2023-2026), acordos com Mexico (ACE-55, quotas de 2012) e Argentina (protocolos do ACE-14 desde 2002), credito (IOF, Banco Central 2010-2011), o desconto patrocinado de 2023 e a regulacao (air bag e ABS em 2014, Proconve L7 e L8). O IPI das categorias principais esta' completo mes a mes, com a aliquota efetiva da empresa habilitada em 2011-2017. Junta ao painel pelo mes; as aliquotas juntam ao Comex Stat pela NCM. | Efeito de politica: o uso-teste so' marca onde a data nao casa com movimento. A TIPI inteira: so' as categorias principais de automovel e as aliquotas que o proprio ato fixa. A aliquota paga por cada empresa (habilitacao, credito presumido, quotas por empresa): a efetiva da habilitada e' o piso que o ato permite. |
| `classificacao_origem` | Pais de producao (e fabrica, municipio, UF e codigo IBGE no Brasil) de cada modelo classificado, por periodo dentro da vigencia, de 2003 a 2026: separar nacional de importado mes a mes, juntar a' importacao do Comex Stat pelo pais, mapear a producao por UF, acompanhar trocas de origem (Argentina, Mexico, China, montagem em ckd/skd com o pais do kit). Cada pais confirmado leva a fonte (pagina guardada, trecho literal) e a forca dela. | Volume por fabrica quando o modelo sai de mais de uma (a divisao nao e' conhecida). Modelos abaixo do piso de classificacao (sem pais). Origem confirmada onde a procedencia e' `proposta` ou `pendente`: e' a proposta do assistente, nao fonte. |
| `fator_emissao_sin_mensal` | Emissao indireta do carro eletrico pela rede: kWh x fator do mes (ou do ano) do SIN; comparacao de emissao por km entre eletrico e combustao ao longo do tempo; choques hidrologicos (2014-2015, 2021) que encarecem a energia em CO2. | Emissao de ciclo de vida, de margem ou de projeto (MDL): e' o fator medio de inventario. Fator por submercado ou por hora. Qualquer mes antes de 2006-01. |
| `emissoes_uf_anual` | Participacao do transporte rodoviario (e de cada combustivel) nas emissoes de cada UF e do Brasil, ano a ano; emissoes brutas e liquidas por setor; comparacao entre UFs e controle anual em painel por UF. | Mes ou municipio (a tabela municipal do SEEG nao foi guardada nesta rodada). Comparar numeros de colecoes diferentes do SEEG. Somar gases fisicos com CO2e. |
| `frota_municipal` | Frota registrada por municipio e tipo (desde 2003, dezembro ate' 2019 e mensal desde 2020) e por combustivel (desde 2013): estoque de eletricos, hibridos e flex por municipio e UF; motorizacao por habitante; denominador para vendas e para emissao por veiculo. | Frota eletrica de automoveis: a fonte nao cruza tipo com combustivel, e o combustivel inclui motos, onibus e caminhoes. Circulacao efetiva (e' registro). Meses de 2004 a 2019 fora de dezembro. |
| `precos_combustiveis_mensal` | Preco nominal e real de gasolina, etanol, diesel S10 e GNV por UF (e por municipio da amostra) desde 2004-05; paridade etanol/gasolina e a escolha do combustivel no flex; custo de uso do carro a combustao contra o eletrico (com a tarifa, quando houver). | Preco de 2003 (a serie por posto nao existe; a sintese da ANP sim, fora do produto). Municipio fora da amostra do LPC. Diesel S500. Preco ponderado por volume vendido (e' media de coletas). |

### Series macro

| codigo | nome | sustenta | nao sustenta |
|---|---|---|---|
| `20749` | Taxa media de juros -- PF aquisicao de veiculos | Custo do credito como determinante da demanda; transmissao da politica monetaria ao mercado de veiculos. |  |
| `20603` | Saldo da carteira -- PF aquisicao de veiculos | Ciclo e alavancagem do financiamento de veiculos (deflacionar antes de comparar anos). | Nada antes de 2007-03. |
| `21131` | Prazo medio -- PF aquisicao de veiculos | Condicao de credito alem da taxa: alongamento do prazo e parcela. | Nada antes de 2011-03. |
| `20758` | Inadimplencia -- PF aquisicao de veiculos | Risco de credito e aperto de oferta de financiamento. | Nada antes de 2011-03. |
| `20126` | Concessoes -- PF aquisicao de veiculos | Fluxo de credito novo contra vendas no periodo coberto. | Nada depois de 2022-12 (descontinuada). |
| `3698` | Cambio R$/US$ venda -- media do periodo | Custo do importado e do componente importado; com a classificacao: nacional contra importado. |  |
| `4390` | Selic acumulada no mes | Politica monetaria mes a mes. |  |
| `4189` | Selic acumulada em 12 meses | Nivel da politica monetaria suavizado. | Soma ou media entre meses: a janela e' movel e os meses se sobrepoem. |
| `433` | IPCA -- variacao mensal | Deflator geral; inflacao como controle. |  |
| `4192` | IGP-DI -- numero indice | Deflator alternativo depois de confirmada a base. | Uso como indice antes de confirmar a base. |
| `24363` | IBC-Br | Atividade e renda agregada mensal. | O ultimo mes do painel. |
| `7832` | Massa salarial real | Renda do trabalho ate' 2019-08. | Nivel (e' variacao). Nada depois de 2019-08. |
| `ipca_7641` | IPCA subitem 5102001 -- Automovel novo | Preco relativo do carro novo contra o IPCA; repasse de IPI e de cambio. |  |
| `ipca_107654` | IPCA subitem -- Automovel usado | Ritmo de depreciacao do usado no IPCA. | Preco de mercado do usado; substituicao novo-usado so' com cautela. |
| `ipca_7657` | IPCA subitem -- Gasolina | Custo de uso; com o etanol: preco relativo e escolha do combustivel no flex. |  |
| `ipca_7658` | IPCA subitem -- Etanol | Preco relativo etanol-gasolina e escolha do combustivel no flex. |  |
| `ipca_7654` | IPCA subitem -- Motocicleta | Preco do substituto de entrada (motocicleta). |  |

## Parte C -- o que foi mapeado e nao construido

| fonte | estado | observacao |
|---|---|---|
| Comex Stat (importação por NCM e origem) | construída | Dimensão comex_veiculos.parquet (etapa 12, rodada propulsão e comex): importação e exportação mensal de 8703 e 8704 por NCM e país, 1997 a 2026-08, bruto em dados/bruto/comex com SHA-256. A quantidade só vem com ncm nos details, e o período filtra ano e mês separadamente (uma consulta por ano). A API limita o ritmo (HTTP 429). |
| Produção, exportação, emprego (Anfavea) | testado em 2026-10-07: anuários de 2023 e 2026 abrem (PDF); de antes de 2023, 404; a página de edições em Excel monta os links por script e a série mensal não abriu | Do anuário guardadas, com SHA-256: unidades industriais (fábricas, em dados/bruto/fabricas_paginas) e licenciamento de nacionais e importados, total e por país de origem (dados/bruto/anfavea). Uso-teste da origem por país (rodada 12): só registro e comparação, nenhuma dimensão construída a partir dele. |
| PBE Veicular (consumo, CO₂) | adquirido (18 tabelas, 2009-2026, em dados/bruto/pbe/) e lido para o tipo de propulsão por versão; consumo e CO₂ não extraídos; crosswalk modelo–versão não feito | Usado na validação da propulsão do rascunho de classificação (2026-10-01). As tabelas de 2025 e 2026 estão no site com rótulo de máscara. |
| Preços por versão (FIPE) | não testado; exige o mesmo crosswalk |  |
| Emplacamento por UF (Fenabrave, Dados Regionais) | granularidade não verificada |  |
| Calendário de política (IPI, MP 1175, tarifa de eletrificados) | construída | Dimensão politicas_mensal.parquet (etapa 13, rodadas 11 e 12): 65 atos de 2003 a 2026 e as alíquotas que eles fixam (IPI completo mês a mês), escritos à mão a partir de 74 páginas oficiais (Planalto, DOU, gov.br, Banco Central) guardadas em dados/bruto/politicas_paginas com SHA-256. As matérias de in.gov.br e as notícias do gov.br não abrem (403, conteúdo restrito); o DOU vem pelo visualizador de PDF da Imprensa Nacional. |
| Emplacamento de eletrificados por tipo de propulsão (ABVE) | testado em 2026-10-02: abve.org.br acessível; a série completa (desde 2012, por tecnologia, mensal) está só no painel Power BI do ABVE Data, que não se lê sem navegador; os comunicados mensais e anuais trazem em texto as unidades do ano por tecnologia e a participação. Série anual 2016-2026 registrada em dados/referencia/abve_serie_anual.csv; comparação em saidas/abve_comparacao.csv | É a única saída para contar unidades por propulsão, que a Fenabrave não separa. Sugerida pelo assistente, aceita em 2026-10-01. A definição de eletrificado muda: 2024 inclui MHEV (e 3.828 micro-híbridos), 2025 exclui. Nenhuma dimensão construída a partir dela (rodada propulsão no tempo). |
| Produção por modelo na Argentina (ADEFA, anuários) | usada (rodada 12) | Anuários de 2006, 2013, 2017 e 2025 lidos como fonte de fábrica x modelo (producao_no_exterior); os de 2007 a 2011 são Flash e não abrem: falta 2007. |
| Exportação de veículos leves por modelo e país destino (INEGI, México) | usada (rodada 12) | Série mensal filtrada para o Brasil, de 2005 em diante, lida como fonte de fábrica x modelo (abastece_o_brasil). |
| Frota e idade do estoque (Senatran) | construída (rodada 13): acesso testado em 2026-11-26, gov.br/transportes abre | Dimensão frota_municipal.parquet (etapa 17): município x mês x tipo ou combustível, dezembro de 2003 a 2019 e todos os meses desde 2020-01; combustível desde 2013-12. A fonte não cruza tipo com combustível em nenhum nível. Bruto em dados/bruto/senatran_frota (270 arquivos, todos abaixo de 50 MB). Idade do estoque (ano de fabricação) e marca/modelo existem na fonte e não foram usados. |
| Geração distribuída (ANEEL, dados abertos: empreendimentos de micro e minigeração) | testado em 2026-11-26: NÃO abriu. dadosabertos.aneel.gov.br reseta a conexão TLS (seis tentativas, entre 01:20 e 01:45 UTC); www.aneel.gov.br e portalrelatorios.aneel.gov.br respondem 403 do Cloudflare ('Sorry, you have been blocked') | Registrado e não contornado (rodada 13, §1). gd_municipal_mensal.parquet não construído. Registro das tentativas em dados/bruto/acesso_fontes_energia.csv. Ver QUESTOES_ABERTAS (rodada 13, Q-E1). |
| Tarifas de aplicação das distribuidoras (ANEEL, dados abertos) | testado em 2026-11-26: NÃO abriu; mesmo bloqueio do domínio da ANEEL (reset de conexão em dadosabertos.aneel.gov.br, 403 do Cloudflare no portal) | Registrado e não contornado. tarifa_energia.parquet e tarifa_energia_mensal não construídos; a relação de municípios por distribuidora e o número de consumidores (para a ponderação por UF) também ficam de fora, porque vêm do mesmo domínio. Ver QUESTOES_ABERTAS (rodada 13, Q-E1). |
| Preços de combustíveis (ANP, Levantamento de Preços: série histórica por posto e síntese mensal) | construída (rodada 13): acesso testado em 2026-11-26, gov.br/anp abre | Dimensão precos_combustiveis_mensal.parquet e a tabela municipal (etapa 18), da série por posto (2004-05 em diante; 33 originais acima de 50 MB como bruto reduzido). A síntese mensal por estado (2001-07 em diante) só na conferência: a contagem bate, o preço médio não se reproduz (QUESTOES, Q-E6). O servidor corta a conexão a cada poucos MB: download com retomada. |
| Emissões por estado, setor e gás (SEEG, Observatório do Clima) | construída (rodada 13): seeg.eco.br/dados deu 403 do CloudFront ao primeiro teste e abriu com o User-Agent do projeto; a API GraphQL da plataforma não respondeu | Dimensão emissoes_uf_anual.parquet (etapa 16), coleção 14.0 (9/11/2026), da tabela geral Dados-nacionais-14.0.xlsx (206 MB, fora do git; bruto reduzido em parquet). A tabela municipal (Google Drive) não foi baixada. |
| Fator médio mensal de emissão de CO₂ do SIN (MCTI, método para inventários) | construída (rodada 13): acesso testado em 2026-11-26, gov.br/mcti abre | Dimensão fator_emissao_sin_mensal.parquet (etapa 15), 2006-01 a 2026-10, da planilha do método para inventários. O fator de margem de operação (MDL), na mesma página, não foi usado. |
| População residente estimada por UF (IBGE, SIDRA tabela 6579) | usada (rodada 13): acesso testado em 2026-11-26 | Estimativa de 2025 por UF em dados/bruto/ibge/populacao_uf_2025.json, só para o uso-teste por mil habitantes. |

