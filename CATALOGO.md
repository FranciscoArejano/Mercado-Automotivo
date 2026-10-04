# Catalogo do repositorio -- dado do commit `b20ec56`

Gerado por `src/etapa10_catalogo.py` a cada execucao do pipeline. **Nao editar a mao**: janelas, linhas e contagens saem dos arquivos. O texto de usos esta' em `config/catalogo_usos.csv` e as fontes candidatas em `config/fontes_candidatas.csv`; edite la' e rode `python src/etapa10_catalogo.py`.

O commit da primeira linha e' o ultimo que alterou o dado descrito (`dados/processado`, `dados/referencia`, `dados/bruto/manifesto.csv`, `dados/bruto/pbe`, `dados/bruto/origem_paginas`, `dados/bruto/comex`, `config`, `regras.csv`, `saidas/classificacao_rascunho.xlsx`); `-sujo` quer dizer que ha' alteracao nao comitada nesses caminhos, e o catalogo nao corresponde exatamente a nenhum commit.

## Indice

| produto | arquivo | linhas | janela efetiva |
|---|---|---|---|
| painel | `dados/processado/painel.parquet` | 54.179 | 2003-01..2026-08 |
| painel_bruto | `dados/processado/painel_bruto.parquet` | 54.183 | 2003-01..2026-08 |
| painel_canal | `dados/processado/painel_canal.parquet` | 48.996 | 2003-01..2026-08 |
| macro_mensal | `dados/processado/macro_mensal.parquet` | 284 | 2003-01..2026-08 |
| classificacao | `dados/processado/classificacao.parquet` | 962 | 2003-01 a 2026-08 |
| comex_veiculos | `dados/processado/comex_veiculos.parquet` | 73.316 | 1997-01 a 2026-08 |

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
| `nao_classificado` | 0,1% | 0,1% | 0,1% |
| `pendente` | 3,4% | 0,0% | 6,6% |
| `proposta` | 0,5% | 20,4% | 81,1% |
| `regra_fonte_forte` | 92,0% | 79,4% | 4,9% |
| `regra_fonte_fraca` | 4,1% | 0,0% | 7,3% |

- **Advertencia:** um artigo que use propulsao ou origem como variavel de tratamento deve restringir-se as procedencias `humana` e `regra_fonte_forte`, e declarar a fracao do volume que ficou de fora.
- **Pendentes:** 98 linhas em `a_adjudicar`; o dado as mostra com a proposta original e procedencia `pendente`.
- **Montagem local:** `dados/processado/classificacao_montagem.parquet`, 968 periodos, 6 deles com modo declarado por fonte (`fabricacao`, `ckd`, `skd`); o resto e' `desconhecido` ou `nao_se_aplica`.
- **Serie temporal de propulsao:** `dados/processado/classificacao_propulsao_anual.parquet`, 5.912 linhas `(marca, modelo, segmento, vigencia_inicio, ano)` com os tipos oferecidos no ano em duas leituras (`propulsao_no_ano` longa, `propulsao_no_ano_curta`). `propulsao_na_vigencia` e `eletrificacao_na_vigencia` sao o conjunto de tudo que foi oferecido em algum momento da vigencia -- nao usar em serie temporal. Dos 90 tipos eletrificados (vigencia x tipo), 3 entram sem datacao (`vigencia_sem_datacao`); 97 tipos tem evidencia de saida. Banda da eletrificacao (piso e tres tetos) em `saidas/eletrificacao_banda.csv`; uso-teste em `saidas/classificacao_uso_teste.csv`.
- **Arquivos:** dicionario em `saidas/classificacao_dicionario.md`; procedencia por atributo em `saidas/classificacao_procedencia.csv`; regras em `config/regras_classificacao.csv` e `config/regras_adjudicacao.csv`; mapeamento do PBE em `config/pbe_propulsao.csv` e `config/pbe_modelos.csv`; tipo de fonte em `config/tipo_fonte_dominio.csv`.
- **Ressalvas principais:** Dimensao gravada (etapa 11) a partir do rascunho adjudicado. Origem ainda e' quase toda `proposta`; um artigo que use propulsao ou origem como tratamento deve restringir-se as procedencias `humana` e `regra_fonte_forte` e declarar a fracao que ficou de fora.

### `comex_veiculos`

- **Estado: dimensao gravada** pela etapa 12, a partir das respostas do Comex Stat (MDIC) guardadas em `dados/bruto/comex/` com SHA-256 no manifesto.
- **Unidade de observacao:** fluxo (importacao, exportacao) x NCM x pais x mes, posicoes 8703 (automoveis) e 8704 (veiculos de carga); tabela separada do painel.
- **Linhas:** 73.316; 48 NCMs, 178 paises.
- **NCMs:** `config/ncm_veiculos.csv`, com `grupo_propulsao_ncm` (as subposicoes de eletrificados existem desde 2017-01 em 8703 e 2022-04 em 8704; antes, `sem_separacao`) e `leve` (8704 com peso em carga maxima ate' 5 t; nao casa exatamente com os comerciais leves da Fenabrave).
- **Ressalvas:** o hibrido leve nao tem NCM propria; kit SKD ou CKD entra na NCM do veiculo completo, entao a importacao pode incluir kits para montagem local.
- **Conferencias:** 0 falhas em `saidas/comex_validacao.csv`; dicionario em `saidas/comex_dicionario.md`.
- **Ressalvas principais:** Antes das subposicoes de eletrificados (2017-01 em 8703, 2022-04 em 8704) nenhuma NCM separa o eletrificado. Kit SKD ou CKD entra na NCM do veiculo completo. Em 2001, 2003, 2006 e 2019-2021 parte relevante das unidades esta' em linhas com menos de 500 kg por unidade, que nao descrevem veiculo completo (saidas/comex_diagnostico_peso.csv).

### Outros arquivos

| arquivo | conteudo |
|---|---|
| `dados/bruto/pdf/` | 284 informes originais da Fenabrave, hash em `dados/bruto/manifesto.csv` |
| `dados/bruto/pbe/` | 18 tabelas do PBE Veicular (Inmetro), com manifesto SHA-256; extracao em `saidas/pbe_versoes.csv` |
| `dados/bruto/origem_paginas/` | 137 paginas de fonte de origem, abertas e guardadas, com SHA-256 |
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
| Frota e idade do estoque (Senatran) | não testado |  |
| Produção, exportação, emprego (Anfavea) | não testado |  |
| PBE Veicular (consumo, CO₂) | adquirido (18 tabelas, 2009-2026, em dados/bruto/pbe/) e lido para o tipo de propulsão por versão; consumo e CO₂ não extraídos; crosswalk modelo–versão não feito | Usado na validação da propulsão do rascunho de classificação (2026-10-01). As tabelas de 2025 e 2026 estão no site com rótulo de máscara. |
| Preços por versão (FIPE) | não testado; exige o mesmo crosswalk |  |
| Emplacamento por UF (Fenabrave, Dados Regionais) | granularidade não verificada |  |
| Calendário de política (IPI, MP 1175, tarifa de eletrificados) | construção manual a partir de decretos |  |
| Emplacamento de eletrificados por tipo de propulsão (ABVE) | testado em 2026-10-02: abve.org.br acessível; a série completa (desde 2012, por tecnologia, mensal) está só no painel Power BI do ABVE Data, que não se lê sem navegador; os comunicados mensais e anuais trazem em texto as unidades do ano por tecnologia e a participação. Série anual 2016-2026 registrada em dados/referencia/abve_serie_anual.csv; comparação em saidas/abve_comparacao.csv | É a única saída para contar unidades por propulsão, que a Fenabrave não separa. Sugerida pelo assistente, aceita em 2026-10-01. A definição de eletrificado muda: 2024 inclui MHEV (e 3.828 micro-híbridos), 2025 exclui. Nenhuma dimensão construída a partir dela (rodada propulsão no tempo). |

