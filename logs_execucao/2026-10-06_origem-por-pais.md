# Registro de execução — origem por país e por fábrica

06 e 07/10/2026. Branch `claude/new-session-rs2chd`. Instruções:
`PARA-O-CODE-origem-por-pais.md` (ESPEC, Parte 0, §9.6 e §10 continuam valendo).
Este registro vai no mesmo push do trabalho que ele descreve.

## Em uma frase

- **Seção 1, fechada:**
  - o 2008 fica `flex+hibrido_indefinido` (a P5 o rotula `mhev` em 2026);
  - os apelidos AMG antigos passam pelo teste de inclusão;
  - o calendário de políticas cobre 2003 a 2007, com o IPI completo mês a mês e
    a alíquota efetiva da habilitada;
  - 65 atos, 422 alíquotas, 74 páginas oficiais.
- **Seção 2, construída:**
  - `dados/processado/classificacao_origem.parquet` (etapa 14) dá o país de
    produção de cada vigência classificada, mês a mês. No Brasil, também a
    fábrica, o município e o código IBGE; em ckd/skd, o país do kit.
  - Fontes: 55 fábricas e 861 linhas de fábrica x modelo, cada uma com trecho
    literal de página guardada.
  - Testes: 19 novos, todos passando.
- **Meta de 80% com fonte forte:**
  - atingida em todos os anos de **2003 a 2022** (81,8% a 89,7%);
  - **não atingida** em 2023 (78,1%), 2024 (67,5%), 2025 (64,2%) e 2026 (27,4%).
- **Não sobrescrevi nada em silêncio.** As 49 divergências estão em
  `saidas/origem_divergencias.csv` e na aba `origem_pais` do rascunho:
  - 34 vigências com origem derivada diferente da atual;
  - 15 períodos em que a fonte contradiz a minha proposta.
  `classificacao.parquet` não mudou.
- **Uso-testes, só registro:**
  - **Comex:** acima do painel na Argentina em todos os anos até 2015. Os
    modelos que o explicariam são Palio, Siena e Classic, que a ADEFA põe lá.
  - **Anfavea:** o painel fica de 1 a 4,5 pontos abaixo na participação do
    importado em todos os anos de 2003 a 2025.
  - **Os dois apontam o Haval H6:** em 2024 e 2025 o painel põe na Tailândia 3
    a 4 vezes o que Comex e Anfavea registram de lá.

---

## Parte 1 — seção 1 (fechada em 06/10)

- **1.1 e 1.4** (commit `dece79f`):
  - **O 2008.** Decisão humana `propulsao_oferecida=flex+hibrido_indefinido`.
    Na decisão humana, `hibrido_indefinido` é tipo não decidido, e a P5 o
    resolve. A fonte é a mesma matéria da AutoData do 208 (12 V), e a P5 o
    rotula `mhev` em 2026.
  - **Os AMG.** AMG C, AMG GLA, AMG E e AMG GLC viram `sem_evidencia`: não têm
    chave própria viva, e a planilha não separa o AMG. O AMG C 63S casa com a
    chave AMG C63S.
  - **Efeito:** CLASSE C de 2021 a 2026 e GLC ficam pendentes, porque o `phev`
    só tinha apoio nas versões AMG. Banda e ABVE regerados; a ABVE fica dentro
    em todos os anos.
- **1.2 e 1.3** (commits `ec33c31`, `07271b0`):
  - **15 atos novos:**
    - IPI de 2002 a 2007: flex igual a álcool em 2002, TIPI de 2003, Decretos
      4.800, 4.902 e 5.058, TIPI de 2007;
    - TIPI de 2017 e de 2022;
    - ACE-55 com o México;
    - protocolos 31, 32, 33 e 35 do ACE-14;
    - regulamentos do IOF de 2002 e 2007.
  - **IPI completo.** As 11 categorias principais têm alíquota em todos os
    meses de 2003-01 a 2026-08; a etapa 13 falha se faltar mês.
  - **Alíquota efetiva da habilitada**, com o trecho da redução:
    - Decreto 7.567 em 2011–2012;
    - teto do crédito presumido do Decreto 7.819 em 2013–2017.
  - **Derivadas.** `derivada=sim` só nas cinco do 18,5% do Decreto 10.979.
  - **A TIPI de 2022** só produz efeito em 1/5/2022. Até 24/2/2022 valem a TIPI
    de 2017 e o Decreto 9.442.
  - **Uso-teste das datas:** 27 de 78 sem movimento além do sazonal.
  - O que ficou fora ou inferido está em `QUESTOES_ABERTAS.md`.

---

## Parte 2 — origem por país e por fábrica

### 2.1 O produto

`classificacao_origem.parquet`: uma linha por vigência, período e país de
produção (1.938 linhas). Dicionário em `saidas/origem_dicionario.md`.

- **Dois países no mesmo período** são duas linhas.
- **No Brasil:** `fabrica_id`, `fabrica`, `municipio`, `uf` e
  `cod_ibge_municipio`, este da tabela de municípios do IBGE guardada em
  `dados/bruto/ibge/`.
- **Em ckd/skd:** `pais_do_kit`.
- **Fonte:** `fonte_url`, `fonte_trecho` e `pagina_salva`, com `procedencia`
  (`regra_fonte_forte`, `regra_fonte_fraca`, `proposta`, `pendente`).
- **Nomes de país:** os da tabela de países do Comex Stat
  (`dados/bruto/comex/paises.json`), com o código.
- **`origem_producao`:**
  - passa a ser derivada: Brasil → nacional, outro país → importado, os dois
    no mesmo período → ambos;
  - fica em `origem_vigencia_derivada`, ao lado da atual
    (`origem_vigencia_atual`);
  - `diverge_da_atual` marca a diferença.
- **Vigência não classificada** (abaixo do piso) tem uma linha, sem país.

Procedência das linhas classificadas:

| procedência | linhas |
|---|---:|
| `regra_fonte_forte` | 768 |
| `proposta` | 626 |
| `pendente` | 20 |

### 2.2 O método

**As tabelas**:
- `dados/referencia/fabricas.csv`:
  - 55 fábricas;
  - 35 no Brasil, com município, UF, código IBGE e, quando a fonte dá, início
    e fim de operação;
  - 20 no exterior. Quando a ADEFA ou o INEGI dão a empresa e não a planta, a
    fábrica é "a empresa no país", com essa observação.
- `dados/referencia/fabrica_modelos.csv`: 861 linhas, uma por fábrica, modelo
  (chave do painel) e período, com o `vinculo`:
  - `producao_local` (335): fábrica brasileira produz;
  - `abastece_o_brasil` (107): exportação ao Brasil do INEGI, ou matéria que
    diz de onde vem o importado;
  - `producao_no_exterior` (419): produção por modelo da ADEFA.

  A `regra_periodo` diz como o período saiu do texto.
- As duas tabelas saem de `src/ferramentas/fabricas_referencia.py`, que confere
  cada trecho antes de gravar.

**A ordem das fontes**:

1. **ADEFA:** produção por modelo e versão na Argentina, anuários de 2006,
   2013, 2017 e 2025.
2. **INEGI:** exportação mensal de veículos leves por modelo e país destino,
   filtrada para o Brasil, de 2005 em diante.
3. **Anfavea:** unidades industriais dos anuários de 2023 e 2026.
4. **Montadoras**, e depois imprensa especializada (O1–O4):
   - AutoData, AutoIndústria, AutoPapo, Motor Show, Revista Carro, O Mecânico,
     Mecânica Online;
   - quatro domínios entraram em `config/tipo_fonte_dominio.csv`, com
     justificativa: adefa.org.ar, anfavea.com.br, inegi.org.mx e
     media.gm.com, como `oficial`; omecanico.com.br, como
     `imprensa_especializada`.
- **Tipo da fonte:**
  - 519 linhas oficiais;
  - 341 de imprensa especializada;
  - 1 de imprensa geral.

**A regra, mês a mês** (`src/comum/origem_pais.py`):

1. P = os países que eu propus para o mês
   (`dados/referencia/origem_pais_proposta.csv`, 502 linhas).
2. Fonte `producao_local` confirma o Brasil. Fonte `abastece_o_brasil` confirma
   o seu país. Fonte `producao_no_exterior` só confirma país que já está em P:
   produção na Argentina não prova que o carro vendido aqui venha de lá.
3. Fonte com vínculo ao Brasil que nomeia país fora de P é contradição. O mês
   fica `pendente` com o país proposto e vai ao rascunho.
4. Senão, país confirmado fica `regra_fonte_forte` ou `regra_fonte_fraca`; o
   resto, `proposta`.

A fonte vale só para o período que trata (regra da fase 2).

**Decisões que tomei e que você pode querer rever:**

- **A proposta foi escrita antes de ler as fontes e não foi revista depois.**
  - Durante a busca, cheguei a mudar o Kangoo de 2024 para Argentina e o
    Pajero Sport para Tailândia. Reverti as duas mudanças.
  - Onde a fonte discorda, o mês fica `pendente` e a fonte que contradiz vai
    junto. Assim a contradição chega a você, em vez de sumir na minha
    proposta.
- **Ano sem mês:** janeiro no início, dezembro no fim (a convenção da fase 2).
  Gera falsos pendentes de borda, como o Tracker de 2020-01 e 2020-02.
- **INEGI em blocos:**
  - meses seguidos de exportação ao Brasil (buracos de até dois meses
    juntam);
  - o período vai do primeiro mês ao último mais dois (trânsito e estoque);
  - bloco de menos de 100 unidades não conta.

  A leitura anual dava contradições espúrias (Kicks, March, Versa, Tiguan,
  Classe A, Cerato).
- **ADEFA:**
  - as linhas de versão são somadas por chave e ano;
  - ano presente em dois anuários usa o mais recente;
  - a linha FCA PALIO de 2025 foi descartada (artefato da extração).
- **Página que dá o início e lista o modelo como produzido hoje:** vira
  `inicio_ate_a_pagina`, com o fim na data da página. Quando o início vem de
  outra página, a observação diz qual. Exemplo: o Classic em São José dos
  Campos começa no lançamento do Corsa Sedan, de outra página da mesma linha do
  tempo da AutoData.
- **Fonte que nomeia só o país:** fica com `fabrica_id` vazio (19 linhas de
  produção local, 15 de abastecimento). A fábrica do período vem então da
  proposta (`fabrica_procedencia=proposta`).

### 2.3 Acesso às fontes (o que abriu e o que não)

| fonte | resultado |
|---|---|
| ADEFA, anuários em PDF | abriram os de 2006, 2013, 2017 e 2025; **os de 2007 a 2011 são Flash** e não se leem. Falta 2007 na Argentina |
| INEGI, exportação por modelo e destino | abriu (série mensal, 2005 em diante) |
| Anfavea, anuários | abriram os de 2023 e 2026; **os de antes de 2023 dão 404** |
| Anfavea, edições em Excel (séries mensais) | **não abriu**: a página monta os links por script |
| Stellantis, site de imprensa | **403** (bloqueio do servidor); usei a imprensa |
| web.archive.org | **429 e conexão encerrada**: não deu para buscar páginas antigas arquivadas |
| IBGE, municípios | abriu (5.571 municípios) |
| Comex Stat, tabela de países | abriu |
| AutoData (notícias e a revista em flipbook), AutoIndústria, AutoPapo, Motor Show, Revista Carro, O Mecânico, Mecânica Online | abriram |
| movimentoeconomico.com.br, autoo.com.br | página vazia (0 caracteres); não usadas |

As páginas guardadas:

- 128 em `dados/bruto/fabricas_paginas/` e 3 em `dados/bruto/anfavea/`, com
  SHA-256 no manifesto;
- mais 30 de `origem_paginas/`, de rodadas anteriores, relidas como fábrica x
  modelo;
- cada lote comitado no mesmo dia.

### 2.4 Cobertura por fonte forte, ano a ano

As unidades do painel com todos os países do mês confirmados por fonte forte
(`oficial` ou `imprensa_especializada`). O denominador é o painel inteiro,
inclusive as vigências não classificadas. "Só ADEFA" é a parte confirmada
apenas pela produção na Argentina (`saidas/origem_cobertura.csv`).

| ano | unidades do painel | com fonte forte | % | só ADEFA | proposta | pendente | meta |
|---|---:|---:|---:|---:|---:|---:|---|
| 2003 | 1.340.014 | 1.202.325 | 89,7 | 6.359 | 133.323 | 0 | sim |
| 2004 | 1.476.704 | 1.319.836 | 89,4 | 7.063 | 154.401 | 0 | sim |
| 2005 | 1.615.694 | 1.443.901 | 89,4 | 15.476 | 169.728 | 0 | sim |
| 2006 | 1.826.978 | 1.623.854 | 88,9 | 24.021 | 201.017 | 0 | sim |
| 2007 | 2.330.601 | 2.001.423 | 85,9 | 0 | 326.795 | 0 | sim |
| 2008 | 2.651.898 | 2.338.769 | 88,2 | 115.728 | 311.072 | 0 | sim |
| 2009 | 2.988.674 | 2.664.347 | 89,1 | 160.460 | 322.647 | 0 | sim |
| 2010 | 3.293.304 | 2.886.944 | 87,7 | 249.665 | 376.871 | 0 | sim |
| 2011 | 3.363.904 | 2.769.185 | 82,3 | 259.463 | 593.410 | 0 | sim |
| 2012 | 3.577.940 | 3.040.520 | 85,0 | 252.121 | 536.239 | 0 | sim |
| 2013 | 3.519.921 | 2.982.833 | 84,7 | 237.984 | 515.886 | 18.301 | sim |
| 2014 | 3.284.611 | 2.763.058 | 84,1 | 220.762 | 510.289 | 7.435 | sim |
| 2015 | 2.450.047 | 2.080.947 | 84,9 | 144.454 | 366.553 | 0 | sim |
| 2016 | 1.969.866 | 1.693.687 | 86,0 | 118.272 | 270.690 | 3.295 | sim |
| 2017 | 2.157.969 | 1.862.736 | 86,3 | 96.960 | 283.611 | 8.278 | sim |
| 2018 | 2.452.617 | 2.149.671 | 87,6 | 159.333 | 296.763 | 2.882 | sim |
| 2019 | 2.635.356 | 2.223.563 | 84,4 | 157.234 | 408.758 | 0 | sim |
| 2020 | 1.932.419 | 1.632.240 | 84,5 | 109.516 | 296.077 | 2.294 | sim |
| 2021 | 1.955.588 | 1.599.766 | 81,8 | 145.004 | 352.389 | 0 | sim |
| 2022 | 1.936.836 | 1.618.825 | 83,6 | 156.679 | 314.886 | 0 | sim |
| 2023 | 2.157.727 | 1.684.240 | 78,1 | 167.401 | 469.778 | 0 | **não** |
| 2024 | 2.454.954 | 1.656.921 | 67,5 | 178.275 | 793.686 | 253 | **não** |
| 2025 | 2.502.229 | 1.606.941 | 64,2 | 135.217 | 854.612 | 3.365 | **não** |
| 2026 | 1.824.350 | 500.442 | 27,4 | 0 | 1.271.330 | 0 | **não** |

**Por que 2023 a 2026 ficam abaixo.**

- Uma página só cobre até a sua data, e são poucas as páginas recentes que
  dizem onde o modelo é feito "desde" quando.
- Para 2026 seria preciso página de agosto a outubro de 2026 dizendo "produzido
  em X desde Y" para cada modelo, ou o anuário da ADEFA de 2026, que não existe.
- **O que procurei e não achei com a regra de período:**
  - HB20 e Creta depois de 2023-10: só pontos de 2026-03 e 2026-06;
  - Tracker de 2023 a 2025: pontos de 2023-01, 2025-07 e 2025-12;
  - HR-V de 2023 a 2025;
  - Montana, Spin, Kicks depois de 2024-08, Tiggo 7 de 2023 e 2024;
  - Renault (Duster, Oroch, Master, Kardian): ponto de 2026-04;
  - as importações da BYD de 2024 e 2025: pontos de 2024-02, 2025-02 e 2025-07.

**O que mais rendeu para 2007–2012:**

- a linha do tempo da GM na revista AutoData (São José dos Campos: Corsa
  1994–2012, Classic até 2013, Blazer 1995–2012);
- as fichas de carro usado do AutoPapo, que dão início e fim de produção:
  Punto, Astra, Vectra, Vectra GT, Corsa, Meriva, Tucson, Livina, i30 e Soul.

### 2.5 Divergências (vão ao rascunho, aba `origem_pais`)

**15 períodos em que a fonte contradiz a proposta:**

| chave | período | a fonte diz | eu propus |
|---|---|---|---|
| GM Tracker | 2020-01 a 2020-02 | Brasil (efeito do ano sem mês) | México |
| GWM Haval H6 | 2025-11 | China | Tailândia e Brasil |
| Honda CR-V | 2017-01 | México (INEGI) | Estados Unidos |
| Hyundai ix35 | 2013-01 a 2013-10 | Brasil | Coreia do Sul |
| Kia Cerato | 2016-08 a 2016-12 | México (INEGI) | Coreia do Sul |
| Mitsubishi ASX | 2013 | Brasil | Japão |
| Mitsubishi Lancer | 2014 | Brasil | Japão |
| Mitsubishi Pajero | 2025-01 | Tailândia | Brasil e Japão |
| Nissan Frontier | 2016-04 a 2016-12 | México (INEGI) | Brasil |
| Nissan Frontier | 2018-07 a 2018-12 | México (INEGI) | Argentina |
| Nissan Kicks | 2017-04 a 2017-07 | México (INEGI) | Brasil |
| Nissan March | 2014-04 a 2014-05 | México (INEGI) | Brasil |
| Peugeot 2008 | 2024-04 | Brasil | Argentina |
| Renault Kangoo | 2024-05 | Argentina | França |
| VW Tiguan | 2017-12 | México (INEGI) | Alemanha |

**34 vigências com origem derivada diferente da atual.**

- Em 26 delas a `origem_producao` atual está vazia.
- As outras incluem:
  - BYD Dolphin Mini, King e Song: de importado a ambos, com a montagem em
    Camaçari desde 2025-10;
  - Classic: de nacional a ambos, com Rosário;
  - Haval H6: de importado a ambos;
  - HR: de nacional a ambos;
  - Celer Sedan;
  - Frontier.

### 2.6 Uso-testes (só registro; nada foi reclassificado pelo Comex nem pela Anfavea)

**1. Comex.**

- **A comparação:** importação do agregado de carros (`unidades_ajustadas`) por
  país e ano, contra unidades do painel feitas no país mais as montadas aqui em
  ckd/skd com kit dele (`saidas/origem_uso_teste_comex.csv`).
- **O que não entra:** os meses com dois países ficam ao lado, fora da soma.
  Importação e emplacamento têm defasagem (trânsito, estoque).
- **A razão Comex/painel, nos seis países principais:**

| ano | Argentina | México | China | Coreia do Sul | Alemanha | Japão |
|---|---:|---:|---:|---:|---:|---:|
| 2003 | 1,27 | 41,32 | -- | 0,35 | 5,31 | 3,84 |
| 2004 | 1,16 | 4,19 | -- | 0,40 | 1,63 | 2,80 |
| 2005 | 1,36 | 1,30 | -- | 0,90 | 2,88 | 2,87 |
| 2006 | 1,37 | 1,55 | -- | 1,28 | 4,54 | 1,91 |
| 2007 | 1,53 | 1,31 | 4,20 | 1,41 | 1,30 | 1,51 |
| 2008 | 1,62 | 1,49 | 1,78 | 1,22 | 1,79 | 1,71 |
| 2009 | 1,38 | 1,01 | 1,38 | 1,17 | 1,37 | 1,13 |
| 2010 | 1,37 | 1,18 | 1,35 | 1,29 | 1,37 | 1,48 |
| 2011 | 1,38 | 1,33 | 1,57 | 1,04 | 1,28 | 1,21 |
| 2012 | 1,25 | 1,11 | 0,30 | 0,92 | 1,38 | 1,11 |
| 2013 | 1,45 | 1,12 | 2,08 | 0,86 | 1,60 | 0,91 |
| 2014 | 1,17 | 0,85 | 1,09 | 0,90 | 1,91 | 1,45 |
| 2015 | 1,16 | 0,94 | 0,61 | 0,84 | 0,98 | 2,25 |
| 2016 | 1,03 | 0,95 | 0,38 | 0,75 | 1,54 | 1,89 |
| 2017 | 1,10 | 1,15 | 0,64 | 0,78 | 1,72 | 3,44 |
| 2018 | 1,10 | 1,34 | 0,59 | 0,97 | 1,80 | 2,01 |
| 2019 | 1,04 | 1,04 | 1,01 | 0,66 | 2,16 | 2,03 |
| 2020 | 0,84 | 0,74 | 1,99 | 0,27 | 2,23 | 2,05 |
| 2021 | 1,08 | 1,38 | 1,09 | 0,28 | 1,95 | 4,24 |
| 2022 | 1,12 | 1,04 | 2,57 | 0,39 | 1,78 | 0,90 |
| 2023 | 1,08 | 1,47 | 2,34 | 0,69 | 1,24 | 3,11 |
| 2024 | 1,13 | 1,15 | 1,73 | 0,39 | 1,69 | 1,32 |
| 2025 | 1,22 | 1,25 | 1,85 | 0,78 | 1,86 | 1,54 |
| 2026 | 1,18 | 1,63 | 3,21 | 0,60 | 2,79 | 2,13 |

**As cinco maiores distâncias de cada ano** (`saidas/origem_uso_teste_distancias.csv`):

- **Distância** = Comex − painel.
- **Entre parênteses**, os modelos que a explicariam:
  - painel acima do Comex: os maiores modelos que o painel põe no país;
  - Comex acima do painel: os modelos que uma fonte põe no país no ano e o
    painel põe em outro.

- **2003:** Argentina +8.700; Alemanha +8.572; México +4.234; Japão +3.265; Coreia do Sul -1.832 (Kia Besta, Hyundai H100).
- **2004:** Argentina +5.914; Japão +3.418; França -2.502 (Peugeot 307, Peugeot 307Sw); Alemanha +1.708; Coreia do Sul -1.605 (Kia Besta, Hyundai H100).
- **2005:** Argentina +15.832; Alemanha +6.919; França -6.621 (Peugeot 307, Citroen C5); Japão +4.619; Áustria +937.
- **2006:** Argentina +29.124; Alemanha +15.074; México +7.855; Japão +3.307; França +2.332.
- **2007:** Argentina +65.495; Coreia do Sul +8.956; México +8.751; Japão +3.623; Tailândia +1.903.
- **2008:** Argentina +94.196 (Fiat Palio, Fiat Siena); México +20.698; Coreia do Sul +11.446; França +8.057; Japão +7.068.
- **2009:** Argentina +76.562 (Fiat Palio, Fiat Siena); Coreia do Sul +13.779; França -5.832 (Citroen C4, Smart Fortwo); Espanha -4.708 (Citroen C4 Picasso, Nissan Pathfinder); Alemanha +3.503.
- **2010:** Argentina +100.708 (Fiat Palio, Gm Classic); Coreia do Sul +34.375; México +11.263; França -8.779 (Citroen C4, Smart Fortwo); Alemanha +7.161.
- **2011:** Argentina +107.924 (Gm Classic, Fiat Palio); China +37.671; México +33.078; Uruguai +10.660; Bélgica +7.845.
- **2012:** Argentina +70.117 (Fiat Palio, Fiat Siena); China -27.191 (Jac J3, Chery Qq); México +19.266; Coreia do Sul -7.456 (Hyundai I30, Hyundai Ix35); Alemanha +6.622.
- **2013:** Argentina +115.807 (Fiat Palio, Fiat Siena); Alemanha +16.085; México +14.664; China +13.441; Uruguai +10.143.
- **2014:** Argentina +43.895 (Fiat Palio, Fiat Siena); México -19.214 (Vw Golf, Nissan Versa); Alemanha +18.804; Uruguai +14.416; Japão +7.989.
- **2015:** Argentina +27.910 (Fiat Palio, Fiat Siena); Japão +11.508; Uruguai +8.591; África do Sul +7.839; Bélgica +4.670.
- **2016:** Argentina +3.696 (Fiat Palio, Honda Hr-V); Coreia do Sul -3.643 (Kia Sportage, Hyundai I30); Japão +3.542; China -3.527 (Lifan X60, Jac T5); Alemanha +3.509.
- **2017:** Argentina +13.179 (Renault Sandero, Honda Hr-V); Japão +7.024; México +6.468 (Nissan Kicks, Vw Tiguan); Alemanha +4.459; Uruguai +3.831.
- **2018:** México +20.247 (Nissan Frontier); Argentina +17.744 (Renault Sandero, Honda Hr-V); Japão +6.958; Uruguai +4.682; Alemanha +4.494.
- **2019:** Argentina +5.969 (Renault Sandero, Honda Hr-V); Reino Unido +5.758; Alemanha +5.584; Japão +5.559; Estados Unidos +3.575.
- **2020:** Argentina -18.636 (Toyota Hilux, Ford Ranger); México -7.801 (Vw Tiguan, Vw Jetta); Coreia do Sul -4.718 (Kia K2500, Hyundai Tucson); Japão +3.534; China +3.495.
- **2021:** Argentina +13.811 (Renault Sandero, Renault Logan); México +9.249; Estados Unidos +3.966; Coreia do Sul -3.788 (Kia K2500, Hyundai Tucson); Alemanha +3.637.
- **2022:** Argentina +21.973 (Gm Tracker, Renault Sandero); China +6.430; Uruguai +3.866; Coreia do Sul -3.537 (Kia K2500, Hyundai Tucson); Alemanha +3.446.
- **2023:** China +28.172; Argentina +15.680 (Gm Tracker, Renault Sandero); México +14.300; Tailândia -8.348 (Gwm Haval H6, Gwm Ora 03); Eslováquia +4.754.
- **2024:** China +67.892; Argentina +26.926 (Gm Tracker, Renault Logan); Tailândia -20.004 (Gwm Haval H6, Gwm Ora 03); Hong Kong +6.897; México +5.575.
- **2025:** China +97.587 (Gwm Haval H6); Argentina +34.201 (Gm Tracker, Renault Kangoo); Tailândia -14.823 (Gwm Haval H6, Gwm Ora 03); México +8.095; Alemanha +6.570.
- **2026:** China +269.586; Argentina +17.597; México +14.823; Índia -5.672 (Hyundai I20); Alemanha +5.371.

**Leitura:**

- **Argentina, até 2015.** O Comex fica de 16% a 62% acima do painel em todos
  os anos de 2003 a 2015. Os modelos que o explicariam são o Palio e o Siena
  (e o Classic em 2010–2011): a ADEFA os põe na Argentina, e eu os propus só no
  Brasil. É a maior pista para rever a proposta.
- **Haval H6.** De 2023 a 2025 a Tailândia tem no painel bem mais que no Comex,
  e a China bem menos. É o H6.
- **China, 2026** (+269.586 em oito meses). Parte deve ser o kit SKD da BYD,
  que entra na NCM do veículo completo. A tabela de montagem marca as BYD como
  `nao_se_aplica`, porque a origem atual delas é importado. Então o painel não
  conta kit nenhum.

**2. Anfavea.**

- **A série mensal não abriu** (ver 2.3).
- **Os anuários abriram**: tabelas de licenciamento total e de importados, de
  2003 a 2025, e de importados por país de origem, de 2016 a 2025. Estão
  guardados em `dados/bruto/anfavea/` e são lidos por `src/comum/anfavea.py`.
  A leitura confere que os segmentos somam o total, e que os países somam a
  linha TOTAL e batem com a tabela de importados.
- **Registro e comparação apenas;** nenhuma dimensão construída com eles.
- **Participação do importado** em automóveis + comerciais leves, em %
  (`saidas/origem_uso_teste_anfavea.csv`):
  - **mínima:** só os meses de país estrangeiro;
  - **máxima:** somando os meses com os dois países e as vigências não
    classificadas.

| ano | Anfavea | painel (mínima) | painel (máxima) | diferença (pontos) |
|---|---:|---:|---:|---:|
| 2003 | 5,4 | 3,3 | 4,0 | -2,1 |
| 2004 | 4,0 | 3,6 | 4,3 | -0,4 |
| 2005 | 5,3 | 4,3 | 5,1 | -1,0 |
| 2006 | 7,6 | 6,4 | 7,1 | -1,2 |
| 2007 | 11,7 | 8,4 | 9,2 | -3,3 |
| 2008 | 13,9 | 10,4 | 11,2 | -3,5 |
| 2009 | 16,1 | 12,9 | 13,4 | -3,2 |
| 2010 | 19,8 | 16,4 | 17,9 | -3,4 |
| 2011 | 24,9 | 21,3 | 21,9 | -3,6 |
| 2012 | 21,6 | 18,3 | 18,8 | -3,3 |
| 2013 | 19,7 | 15,2 | 15,8 | -4,5 |
| 2014 | 18,4 | 15,4 | 15,9 | -3,0 |
| 2015 | 16,6 | 13,4 | 13,7 | -3,2 |
| 2016 | 13,7 | 11,3 | 11,7 | -2,4 |
| 2017 | 11,1 | 9,5 | 9,9 | -1,6 |
| 2018 | 12,5 | 11,5 | 11,8 | -1,0 |
| 2019 | 11,0 | 9,6 | 9,9 | -1,4 |
| 2020 | 10,6 | 9,1 | 9,4 | -1,5 |
| 2021 | 12,5 | 11,5 | 11,9 | -1,0 |
| 2022 | 13,6 | 12,4 | 12,8 | -1,2 |
| 2023 | 15,8 | 13,8 | 14,1 | -2,0 |
| 2024 | 18,5 | 16,6 | 17,0 | -1,9 |
| 2025 | 19,3 | 15,0 | 17,1 | -4,3 |

- **O painel fica abaixo da Anfavea em todos os anos**, mesmo na leitura
  máxima. A parte que falta é importado que eu propus no Brasil; a Argentina
  acima é o sinal maior.
- **Por país (2016–2025):**
  - Alemanha: o painel tem de 16% a 42% da Anfavea. Muitos importados alemães
    estão abaixo do piso ou em mais de um país.
  - Reino Unido: zero no painel em 2024; Jaguar e Land Rover estão propostos
    em Itatiaia.
  - Itália: os comerciais leves de 2023 a 2025 (888, 2.181, 3.089) não
    aparecem no painel.
  - Tailândia: em 2024–2025 o painel tem de 3 a 4 vezes a Anfavea.

**3. Mapa por UF** (`saidas/origem_mapa_uf.csv`; meses com o Brasil como único
país):

- **Onde o padrão é implausível:**
  - **2013, SP de 37,8% para 45,2%:**
    - entram o HB20 (Piracicaba) e o Etios (Sorocaba), plausíveis;
    - a chave FIESTA passa inteira da BA para SP, implausível: ela junta o
      Fiesta Rocam (Camaçari, até 2014) e o New Fiesta (São Bernardo, desde
      2013).
  - **Ford São Bernardo e Camaçari depois de fechar:** unidades em 2020 a 2026
    (de 1 a 7.424 por ano). Em 2021 é a cauda de Camaçari; depois, cauda de
    emplacamento.
  - **Toyota Indaiatuba em 2026,** depois de 2026-06 (2.520 unidades): a
    proposta mantém a fábrica até o fim da vigência.
  - **2016, MG de 20,8% para 15,2%:** caem os Fiat de Betim (Palio de 122 mil
    para 64 mil, Uno, Strada, Siena) e sobe Goiana (PE de 39 mil para 99 mil).
    Plausível.
  - **2021, RS de 11,8% para 6,8%:** a queda vem do Onix (de 121 mil para 63
    mil) e do Onix Plus, os dois de Gravataí. Plausível.

### 2.7 Erros e o que corrigi

- **INEGI anual.** Dava contradições espúrias. Passei a blocos mensais com
  dois meses de defasagem e piso de 100 unidades.
- **Derivação lenta.** Levava 337 s; reescrevi em Python puro e passou a 1,3 s.
- **Compass.** Tirei a linha da página do J10: "lançado em 2016" virava 2016-01
  e contradizia a proposta (Estados Unidos até 2016-08). Ficou a da AutoData,
  com início em 2016-10.
- **Erros das próprias fontes, que evitei:**
  - a AutoIndústria escreve "Iracemápolis" para a Honda de Itirapina;
  - o subtítulo do Argo diz "Lançado em 2027"; usei a frase do corpo, "Lançado
    em 2017".
- **Ford Ka.** A linha estava como `na_data_da_pagina` cobrindo o ano de 1997.
  A conferência nova pegou o erro; passou a `declarado`.
- **`config/fontes_candidatas.csv`.** O módulo csv recitava as aspas de todas as
  linhas. Refiz a edição como texto, para o diff ficar só no que mudou.
- **`saidas/classificacao_regras_contas.csv`.** Ao regerar o rascunho, a ordem
  das linhas empatadas mudou, com os números iguais. Restaurei o arquivo.

### 2.8 O que continua aberto

Está em `QUESTOES_ABERTAS.md` ("Origem por país: o que a rodada 12 deixou
aberto"):

- as 49 divergências para decidir;
- a cobertura de 2023 a 2026;
- o ano sem mês;
- a ADEFA de 2007;
- modelo em mais de uma fábrica, sem divisão de volume;
- a chave FIESTA;
- as fontes que não abriram;
- as leituras dos uso-testes.

## Commits

- `dece79f` Rodada 12, sec. 1.1 e 1.4: o 2008 fica flex+hibrido_indefinido (a P5 o rotula mhev em 2026); apelidos AMG antigos passam pelo teste de inclusao
- `ec33c31` Calendario de politicas: paginas oficiais de 2002-2007 (TIPI 2003 e 2007, IPI de 2003-2004, flex de 2002, ACE-55, protocolos do ACE-14 de 2002-2006, IOF) e capitulo 87 das TIPI de 2017 e 2022
- `07271b0` Rodada 12, sec. 1.2 e 1.3: calendario de 2003 a 2007 e IPI completo mes a mes, com a aliquota efetiva da habilitada
- `3cedfc5` Origem por pais: paginas de producao por modelo (ADEFA 2002-2025, INEGI exportacao ao Brasil 2005-2026), unidades industriais da Anfavea (2023, 2026) e tabela de paises do Comex Stat
- `8746494` Origem por pais: primeiro lote de paginas de fabrica-modelo (VW Taubate, Anchieta e Sao Jose dos Pinhais; Fiat Betim; GM Gravatai e Sao Jose dos Campos; Ford; Renault; Toyota; Hyundai)
- `fcc8690` Origem por pais: segundo lote de paginas de fabrica-modelo (Fiat Betim, Jeep e Fiat Goiana, Honda Sumare e Itirapina, Hyundai Piracicaba, GM Sao Caetano, Porto Real, Nissan Resende, Siena) e tabela de municipios do IBGE
- `803e084` Origem por pais: terceiro lote de paginas de fabrica-modelo (Palio, Logan, Sandero, C3, Kicks, Cobalt, Pulse, Tracker, HB20, i20, Fiorino)
- `64cf75e` Origem por pais: quarto lote de paginas de fabrica-modelo (familia Corsa, Meriva, Zafira, HPE Catalao, Fiat Betim 2016-2026, Honda Itirapina, S10, Tracker, BYD Camacari)
- `14d1d55` Origem por pais: tabelas de fabricas e fabrica x modelo (primeira versao), proposta de pais por chave e derivacao mes a mes
- `6185fb1` Origem por pais: quinto lote de paginas de fabrica-modelo (Argo, Fastback, Pulse, Toro, Rampage, GM Sao Caetano 2025, Kicks nova geracao, Haval H6) e linhas correspondentes
- `9315dc7` Origem por pais: sexto lote de paginas de fabrica-modelo (Compass, Goiana, Caoa Anapolis, Hyundai 2026, BYD importado da China, GM Sao Jose dos Campos 2009, fichas de Punto, Astra, i30, Tucson, Livina e Soul)
- `6034e55` Origem por pais: setimo lote de paginas de fabrica-modelo (linha do tempo da GM na revista AutoData, fichas de Vectra, Meriva e Corsa)
- `24a2ad5` Origem por pais: oitavo lote de paginas de fabrica-modelo (Renault Sao Jose dos Pinhais 2026, GM Sao Caetano 2012 e 2023)
- `a5976c0` Fabricas: as duas tabelas de fabricas (fabricas.csv, fabrica_modelos.csv), versao da rodada
- `9c2b96a` Origem por pais: produto classificacao_origem (etapa 14), validacoes e uso-testes
- (este registro e o ajuste das distâncias do uso-teste, depois o fechamento: `validacao.md` e `CATALOGO.md` regerados em árvore limpa)

## Tag

`rodada-12`, criada localmente; o push da tag é recusado. A linha vai em
`tags_pendentes.csv`.
