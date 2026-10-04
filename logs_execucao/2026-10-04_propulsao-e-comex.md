# Registro de execução — fechar a propulsão e trazer o comércio exterior

04/10/2026. Branch `claude/new-session-rs2chd`. Este registro vai no mesmo push
do trabalho que ele descreve.

## Em uma frase

- **P5:** 16 vigências passaram de `hibrido_indefinido` para `mhev` e uma para
  `hev`, todas com fonte forte.
- **Saída de tipos:** é modelada nas duas leituras. A tabela anual passou a ter
  uma linha por vigência-ano.
- **ABVE:** fica dentro da banda da definição de cada ano, em todos os anos, e
  nunca acima do `teto_estrito`.
- **Comex Stat:** virou dimensão: `comex_veiculos.parquet`, de 1997 a 2026-08,
  com as três conferências pedidas.

- **Comex, uso-testes:**
  - a importação de elétricos puros (8703.80) passa as unidades só-`bev` do
    painel em todos os anos; a razão vai de 1,51 (2024) a 1,03 (2025) e volta a
    1,34 em 2026;
  - a importação total (8703 + 8704 leve) fica acima do `importado` do painel na
    maioria dos anos; sem as linhas de peso baixo, a distância chega a 1,3 ou
    mais em 2007, 2008 e 2026;
  - a China passa a Argentina como primeira origem em 2025.
- **Um achado no dado do Comex:** há linhas com menos de 500 kg por unidade.
  Passam de 10% das unidades importadas em 2001, 2003, 2006 e 2019–2021. Medi e
  marquei; não filtrei.

---

## Parte 1 — a propulsão

### O que eu conferi primeiro

Sua medida do §1 bate com o que vi antes da P5. Os dois maiores casos do
`parcial` de 2025–2026 eram Fastback, Pulse, Toro, Renegade e Commander, com
`hibrido_indefinido` vindo do PBE (P3/P4) e nenhuma fonte de tipo.

### 2.1 A regra P5

Entrou em `config/regras_adjudicacao.csv` com o seu texto. No motor
(`comum/adjudicacao.py`) ela roda depois de P1–P4, sobre o valor de propulsão já
ajustado.

- **Fontes.** Ficam em `dados/referencia/hibrido_fontes.csv`, uma linha por
  fonte e modelo, com `tipo_declarado` ∈ {`mhev`, `hev`, `ambiguo`} e o trecho
  literal da página guardada. O teste de citação cobre o arquivo (trecho literal
  e SHA-256).
- **Cobertura.** Fonte datada trata da vigência que contém a data, aceitando até
  12 meses antes do início (o anúncio vem antes das vendas). Fonte sem data trata
  de todas as vigências do modelo.
- **Decide** quando há fonte forte e todas as fontes da vigência declaram o mesmo
  tipo.
- **Não decide** com só fonte fraca, fontes que se contradizem ou sistema
  ambíguo. A linha vai a `a_adjudicar` como **aviso**.
  - Decisão minha: o aviso não torna o atributo `pendente`. Pendente mostraria a
    proposta original (o `flex` do Toro, por exemplo), e a regra diz que o valor
    fica `hibrido_indefinido`.
  - Para isso o motor ganhou uma coluna `avisos`, separada de `pendencias`. A
    fila é a união das duas.
- **Sem fonte, nada muda**, e a linha não vai à fila: a regra não lista esse
  caso.

**Universo, da maior para a menor vigência em unidades.** Busquei todas as 21.
Nenhuma ficou sem busca por limite da sessão.

| vigência | unidades | resultado | fonte forte (data) |
|---|---:|---|---|
| Renegade 2015-04 | 599.307 | `mhev` | Autodata, 26/03/2026: "sistema MHEV [...] 48V [...] Ainda não traciona o veículo" |
| Toro 2015-12 | 585.250 | `mhev` | Autodata, 29/05/2026: "sistema MHEV de 48V [...] motor elétrico que atua como auxiliar" |
| Pulse 2021-11 | 221.398 | `mhev` | Revista Carro (sem data no texto): "um sistema híbrido leve"; Autodata de 26/03/2026: 12 V |
| Fastback 2022-09 | 190.729 | `mhev` | as mesmas do Pulse |
| 208 2020-01 | 110.424 | `mhev` | Autodata, 26/03/2026: 12 V "já presente nos [...] Peugeot 208" |
| Tiggo 7 2020-03 | 108.649 | `mhev` | Auto+ TV, 15/06/2022: 48 V, "o motor elétrico não move as rodas" |
| Tiggo 5X 2020-03 | 100.302 | `mhev` | a mesma |
| Commander 2021-10 | 90.965 | `mhev` | Autodata, 30/03/2026: "híbrido flex leve de 48v [...] não propulsionam o veículo" |
| Discovery 2003-01 | 39.776 | `mhev` | Revista Carro, 12/01/2022: MHEV 48 V (Discovery Sport D200) |
| A3 Sedan 2014-01 | 25.185 | `mhev` | Auto+ TV, 07/07/2022: "híbrido leve de 48V" |
| XC40 2018-06 | 15.044 | fica | nenhuma fonte brasileira do B4 |
| Range Rover 2003-03 | 10.458 | `mhev` | Auto+ TV, 31/08/2022: "D350 MHEV" |
| Arrizo 6 2020-07 | 8.666 | `mhev` | Auto+ TV, 15/06/2022 |
| 911 2003-08 | 8.059 | fica, aviso | só Vrum (imprensa geral): 400 V, "não traciona o carro sozinho": nem leve nem pleno |
| Classe C 2021-01 | 6.013 | `mhev` | Revista Carro, 19/01/2022: 48 V EQ Boost com motor elétrico |
| Classe E 2003-01 | 4.859 | `mhev` | Autodata, 08/01/2024: "híbrido leve de 48 volts" |
| CLA 200 2014-01 | 4.670 | `mhev` | Auto+ TV, 01/10/2023: "híbrido-leve de 48 volts" |
| GLC 2016-04 | 4.500 | `mhev` | Motor Show, 27/11/2023: ISG e 48 V |
| Defender 2003-01 | 2.903 | fica | nenhuma fonte brasileira |
| GS4 2026-01 | 1.980 | **`hev`** | AutoPapo, 24/05/2025: "SUV híbrido HEV" |
| X6 2008-12 | 1.491 | fica | a matéria da AutoIndústria aberta não fala do sistema |

Os sistemas de 48 V dos Stellantis de Goiana chegaram a parecer o caso ambíguo
da sua regra: um resumo de busca falava num segundo motor elétrico no câmbio.
**As matérias abertas dizem o contrário:**
- Renegade: "Ainda não traciona o veículo";
- Commander: "Eles não propulsionam o veículo".

Por isso viraram `mhev`. Se você souber de fonte que descreve tração elétrica
própria nesses carros, a P5 os devolve a `hibrido_indefinido` sozinha (fontes
contraditórias).

A Discovery e o CLA 200 já tinham fonte de entrada (rodada anterior) com o tipo
`hibrido_indefinido`. Troquei o rótulo nas duas linhas de `propulsao_fontes.csv`,
sem mudar a data. Um teste novo exige que toda fonte de entrada aponte para um
tipo que a vigência tem.

**Efeito no rascunho.** A fila de `a_adjudicar` foi de 97 para 98: entrou o
911, como aviso. As procedências por volume não mudaram, porque as 17 linhas já
eram `regra_fonte_forte` pela P3/P4.

### 2.2 Saída de tipos e as duas leituras

Implementado em `comum/propulsao_anual.py` como você descreveu.

- **Presença:** o tipo no PBE do ano, fonte datada, ou o próprio ano de entrada.
- **Ausência:** só de 2021 em diante. O modelo está no PBE do ano sem o tipo, ou
  há fonte de fim de venda.
- **Lacuna não é saída:** conta só a ausência depois da última presença.
- **Leitura longa:** o tipo fica até o ano da primeira ausência e sai no
  seguinte.
- **Leitura curta:** o tipo fica até a última presença.

Três decisões de aplicação:

1. **Cada ano de PBE vale para a vigência com mais meses nele.** É a mesma
   repartição das regras de adjudicação: o ano dividido entre duas vigências não
   prova ausência na que tem menos meses.
2. **"Com outras versões" quer dizer versão de outro tipo da vigência.** O Tank
   300 tem `hev` na vigência (proposta `pendente`), e o PBE de 2025 e 2026 só o
   lista como PHEV. Sem essa leitura, o `hev` sairia e o ano ficaria sem tipo.
   Versão só de tipo que a vigência não tem contradiz a vigência; não prova
   ausência.
3. **Ano em que a leitura curta ficaria sem nenhum tipo leva os tipos da longa.**
   O modelo vende no ano, então algum tipo estava à venda. Aconteceu uma vez:
   Carnival 2025. A gasolina tem última presença em 2024 e o hev entra pelo PBE
   em 2026, e o modelo está fora do PBE de 2025.

As fontes de saída são as que eu já tinha aberto:

- **Outlander:** a página da AutoIndústria dá produção do PHEV "de 2014 a 2016".
  Registrei 2016 como presença datada (mesma página e trecho). O PBE de 2021
  traz o Outlander sem phev, então o phev sai depois de 2016 na curta e depois de
  2021 na longa.
- **XC40:** a coluna do O POVO (20/12/2021) anuncia que a Volvo deixa de
  importar o XC40 a combustão e híbrido "para comercializar exclusivamente sua
  versão elétrica a partir de 2022". Entra como `fim` para gasolina, phev e
  `hibrido_indefinido`. O PBE de 2022 também só lista o XC40 elétrico. **O XC40
  vira `total` em 2022 na curta e em 2023 nas duas.** É o caso que você citou.
- **E-2008:** sem fonte nova. A página da Motor Show já guardada (17/10/2024,
  citada para a entrada) diz que "A Peugeot confirmou o início das vendas do
  E-2008 no mercado brasileiro". Registrei como presença em 2024. Sem isso o
  `bev` sairia em 2022–2023, porque o PBE nunca casa o E-2008 com a chave 2008.
  Corrigi num commit próprio, depois do commit da seção 2.

**97 tipos têm evidência de saída:** 49 gasolina, 21 flex, 14 diesel, 7 phev, 3
bev, 1 mhev, 1 hev e 1 `hibrido_indefinido`. Entre os eletrificados:

| vigência | tipo | último ano, longa / curta | de onde |
|---|---|---|---|
| Compass 2016-09 | phev | 2025 / 2024 | PBE de 2025 e 2026 sem o 4xe |
| Compass 2016-09 | diesel | 2025 / 2024 | PBE de 2025 e 2026 só flex e gasolina |
| Renegade 2015-04 | diesel | 2022 / 2021 | PBE de 2022 a 2026 só flex |
| XC40 2018-06 | phev, `hibrido_indefinido`, gasolina | 2022 / 2021 | PBE e fonte |
| Outlander 2007-06 | phev | 2021 / 2016 | PBE e presença datada |
| 208 2020-01 | bev | 2022 / 2021 | PBE de 2022 a 2026 sem o e-208 |
| E-2008 (2008) | bev | 2025 / 2024 | presença 2022 e 2024 |
| A3 Sedan | mhev | 2025 / 2024 | PBE de 2025 e 2026 sem Híbrido |
| Mustang | bev | 2026 / 2025 | PBE de 2026 sem o Mach-E |

Alguns desses podem ser artefato do PBE, que nem sempre lista todas as versões
nem rotula igual de um ano a outro. O caso mais provável é o A3 Sedan, cujo 48 V
continuou à venda. Ficou como a regra manda, e a banda entre as leituras mostra o
tamanho do efeito.

**Efeito da leitura curta na combustão.** Em 32 tipos de combustão, a curta
colapsa no ano de entrada. Quase todos são a gasolina dos modelos da transição
flex (Gol, Strada, Uno, Fox, Siena, Ka...): a gasolina não tem presença no PBE e
a ausência aparece em 2021. Isso não muda nenhum nível de eletrificação, mas a
leitura curta de `propulsao_no_ano_curta` não deve ser lida como datação da
transição flex.

### 2.3 Defasagem do PBE

São 21 tipos com fonte datada e ano de PBE (`saidas/classificacao_pbe_defasagem.csv`).
`pbe_ano − ano da fonte`:

- **Todos os 21:** 0 (4 casos), −1 (1), +1 (6), +2 (3), +3 (1), +4 (2), +5
  (1), +8 (2), +11 (1).
- **Só os comparáveis**, com fonte de 2021 em diante (6): 0, 0, 0, 0, −1
  (Discovery Sport, PBE antes do mercado) e +1 (CLA 200, PBE depois).

Decidi a direção só pelos comparáveis. Antes de 2021, o primeiro ano de PBE de
um tipo sem marcador é 2021 por construção, porque a tabela não o via. A
diferença ali mede a cegueira do PBE, não a defasagem (Kangoo +8, Outlander +11).
Esses casos foram justamente os que precisaram de fonte.

**Sem direção dominante:** as duas leituras ficam com `pbe_ano`. O código mede e
aplica sozinho (`defasagem_pbe`). Se os comparáveis passarem a ter direção, a
leitura longa e a curta se abrem em ±1.

### 2.4 Linha por vigência-ano

A chave passou a ser `(marca, modelo, segmento, vigencia_inicio, ano)`, com
5.912 linhas. A validação confere que as unidades de cada linha são as do painel
nos meses daquela vigência naquele ano. Corolla e RAV4 de 2019 voltaram a ter
uma linha por vigência:

- o `total` de 2019 voltou a 0,16%;
- o teto de 2019 caiu de 2,75% para 1,17%, porque o Corolla de janeiro a
  setembro deixou de contar como híbrido.

### 2.5 Itens 2, 5 e 6

Ficaram como limitação, em `QUESTOES_ABERTAS.md` (seção "Propulsão no tempo",
reescrita).

### 2.6 A banda e a ABVE

Gravada em `saidas/eletrificacao_banda.csv` pela etapa 11, uma linha por ano e
leitura. A comparação com a ABVE (`saidas/abve_comparacao.csv`) usa o teto da
definição de cada ano: `teto` em 2024 e `teto_sem_mhev` nos demais. A
participação da ABVE é recalculada sobre o total da Fenabrave.

| ano | ABVE | menor piso | maior teto da definição | `teto_estrito` longa / curta | dentro? | acima do estrito? |
|---|---:|---:|---:|---:|---|---|
| 2016 | 0,05% | 0,02% | 0,55% | 0,55% / 0,55% | sim | não |
| 2017 | 0,15% | 0,11% | 0,60% | 0,60% / 0,38% | sim | não |
| 2018 | 0,16% | 0,10% | 0,66% | 0,57% / 0,48% | sim | não |
| 2019 | 0,45% | 0,16% | 1,17% | 1,07% / 0,99% | sim | não |
| 2020 | 1,01% | 0,18% | 2,82% | 2,82% / 2,69% | sim | não |
| 2021 | 1,77% | 0,09% | 5,45% | 5,45% / 5,30% | sim | não |
| 2022 | 2,52% | 0,16% | 10,65% | 10,64% / 9,09% | sim | não |
| 2023 | 4,31% | 1,77% | 9,33% | 9,30% / 9,30% | sim | não |
| 2024 (com MHEV) | 7,14% | 4,80% | 13,72% | 11,45% / 11,45% | sim | não |
| 2025 | 8,78% | 6,79% | 16,34% | 16,30% / 13,40% | sim | não |
| 2026 (jan a ago) | 17,40% | 13,24% | 18,76% | 18,72% / 18,65% | sim | não |

- **A ABVE nunca passa do `teto_estrito`.** Os dados não indicam híbrido pleno
  escondido entre os quatro indefinidos que sobraram.
- **Em 2026 a folga é pequena:** a ABVE recalculada dá 17,4%, contra estrito de
  18,7%. Os 20,2% que a ABVE publica ficariam acima do estrito, o que reforça que
  esse número não fecha.

**Conferência dos micro-híbridos.** Em 2025, as vigência-anos com `mhev` somam
159.750 unidades na leitura longa e 159.192 na curta. A ABVE contou 61.340
micro-híbridos. O painel fica acima, como deve: conta o modelo inteiro (todo
Fastback, todo Pulse, não só as versões híbridas). A P5 alcançou os modelos
certos.

### 2.7 Uso-teste: antes e depois

"Antes" é a tabela da rodada 9 (uma leitura só, `f7ba2e6`). "Depois" são as duas
leituras desta rodada. Todos os valores estão em % das unidades do painel.

**Piso e teto**

| ano | piso antes | piso longa | piso curta | teto antes | teto longa | teto curta |
|---|---:|---:|---:|---:|---:|---:|
| 2015 | 0,00 | 0,00 | 0,00 | 0,78 | 0,78 | 0,78 |
| 2016 | 0,02 | 0,02 | 0,02 | 0,55 | 0,55 | 0,55 |
| 2017 | 0,11 | 0,11 | 0,11 | 0,60 | 0,60 | 0,38 |
| 2018 | 0,10 | 0,10 | 0,10 | 0,66 | 0,66 | 0,56 |
| 2019 | 0,03 | 0,16 | 0,16 | 2,75 | 1,17 | 1,08 |
| 2020 | 0,18 | 0,18 | 0,18 | 2,82 | 2,82 | 2,69 |
| 2021 | 0,09 | 0,09 | 0,10 | 5,48 | 5,48 | 5,33 |
| 2022 | 0,15 | 0,16 | 0,41 | 11,85 | 11,78 | 10,24 |
| 2023 | 1,38 | 1,77 | 1,79 | 11,90 | 10,55 | 10,55 |
| 2024 | 4,56 | 4,80 | 4,80 | 14,46 | 13,72 | 13,72 |
| 2025 | 6,58 | 6,79 | 6,79 | 21,47 | 21,07 | 18,14 |
| 2026 (jan a ago) | 13,12 | 13,24 | 13,25 | 30,47 | 28,18 | 28,15 |

**Os dois tetos sem os híbridos leves**

| ano | sem MHEV antes | sem MHEV longa | sem MHEV curta | estrito antes | estrito longa | estrito curta |
|---|---:|---:|---:|---:|---:|---:|
| 2015 | 0,78 | 0,78 | 0,78 | 0,78 | 0,78 | 0,78 |
| 2016 | 0,55 | 0,55 | 0,55 | 0,55 | 0,55 | 0,55 |
| 2017 | 0,60 | 0,60 | 0,38 | 0,60 | 0,60 | 0,38 |
| 2018 | 0,66 | 0,66 | 0,56 | 0,57 | 0,57 | 0,48 |
| 2019 | 2,75 | 1,17 | 1,08 | 2,65 | 1,07 | 0,99 |
| 2020 | 2,82 | 2,82 | 2,69 | 2,82 | 2,82 | 2,69 |
| 2021 | 5,48 | 5,45 | 5,30 | 5,45 | 5,45 | 5,30 |
| 2022 | 11,82 | 10,65 | 9,09 | 10,70 | 10,64 | 9,09 |
| 2023 | 11,84 | 9,33 | 9,33 | 10,66 | 9,30 | 9,30 |
| 2024 | 14,45 | 11,45 | 11,45 | 12,19 | 11,45 | 11,45 |
| 2025 | 21,47 | 16,34 | 13,44 | 16,70 | 16,30 | 13,40 |
| 2026 (jan a ago) | 30,47 | 18,76 | 18,69 | 21,10 | 18,72 | 18,65 |

**Quanto a P5 derruba o teto.** O `teto` (`total` + `parcial`) não muda com a
P5: `mhev` e `hibrido_indefinido` são ambos `parcial`. O que cai é o teto da
definição da ABVE (`teto_sem_mhev`). Isolei o efeito recalculando a tabela desta
rodada com os rótulos da P5 desfeitos:

| ano | sem MHEV sem a P5, longa | com a P5, longa | queda | sem a P5, curta | com a P5, curta | queda |
|---|---:|---:|---:|---:|---:|---:|
| 2025 | 21,07 | 16,34 | **4,7 pontos** | 18,14 | 13,44 | **4,7 pontos** |
| 2026 (jan a ago) | 28,18 | 18,76 | **9,4 pontos** | 28,15 | 18,69 | **9,5 pontos** |

**Plausibilidade.** Nenhuma série muda de patamar sem evento. Medi, modelo a
modelo, quem move o `teto_sem_mhev` (leitura longa) de um ano para o outro:

- **2023 → 2024 (9,3% → 11,5%):**
  - sobem: BYD Dolphin Mini (+0,9 ponto), BYD Song (+0,7), Haval H6 (+0,5),
    Dolphin, E-2008, Ora 03;
  - descem: Compass (−0,7), Corolla (−0,5).
- **2024 → 2025 (11,5% → 16,3%):** o Tiggo 7 PHEV (+1,5; o phev entra pelo PBE
  em 2025), BYD Song (+1,0), Corolla Cross, Compass, Dolphin Mini e Haval.
- **2025 → 2026 (16,3% → 18,8%, oito meses):**
  - sobem: Dolphin Mini (+1,5), Yaris Cross (+1,4), Geely EX2 (+1,4), Dolphin
    (+1,1), Song, Haval;
  - descem: o Compass (−2,5; o 4xe sai na leitura longa depois de 2025) e o
    Corolla Cross (−1,0).
- A ABVE recalculada vai de 8,8% para 17,4% no mesmo período.

---

## Parte 2 — o comércio exterior (Comex Stat)

### Acesso e bruto

- **API.** `POST https://api-comexstat.mdic.gov.br/general`, como você descreveu.
  Segui as duas armadilhas que você testou: `ncm` vai sempre nos `details` (sem
  ele não vem quantidade), e cada consulta cobre um ano, de `-01` a `-12`.
- **Janela.** De 1997-01 a 2026-08. O mês final veio de `general/dates/updated`
  (`updated: 2026-09-04`, ano 2026, mês 08), guardado em
  `ultima_atualizacao.json`.
- **Consultas.** São 240: 2 fluxos × 2 posições × 30 anos × (com país, sem país).
  Mais 48 consultas a `tables/ncm`, com a descrição e a unidade estatística de
  cada NCM.
- **Onde ficou.** 22 MB em `dados/bruto/comex/`. O `manifesto.csv` guarda, por
  arquivo, a consulta, o SHA-256, os bytes, as linhas e a data de acesso.
- **Commit.** O bruto foi comitado logo depois do download (`02e9277`), antes de
  qualquer processamento. O teste `test_bruto_bate_com_o_manifesto` recalcula os
  SHA-256.
- **Ferramenta.** `src/ferramentas/comex_baixar.py`. Arquivo já no manifesto não
  é baixado de novo.

### A tabela de NCMs (`config/ncm_veiculos.csv`)

Gerada por `src/ferramentas/comex_ncm.py`. São 48 NCMs de 8 dígitos com movimento
na janela: 20 em 8703 e 28 em 8704. Todas têm unidade estatística
`NUMERO (UNIDADE)`, então nenhuma fica fora das somas de unidades.

**`grupo_propulsao_ncm`.** Vem do texto oficial da subposição: SH 2017 em 8703,
SH 2022 em 8704.

| posição | centelha | diesel | hev | phev | bev | outros | sem_separacao |
|---|---:|---:|---:|---:|---:|---:|---:|
| 8703 | 7 | 6 | 2 | 2 | 1 | 2 | 0 |
| 8704 | 6 | 13 | 2 | 0 | 1 | 3 | 3 |

Em 8704, o `hev` junta híbrido com e sem recarga externa. As subposições do SH
2022 (8704.41–43 e 8704.51–52) não falam de recarga no texto oficial, e por isso
o `phev` de 8704 fica vazio.

**Data da separação.** Confirmada pela vigência dos códigos: é o primeiro mês com
dado em qualquer subposição de eletrificado da posição.

- **8703: 2017-01.**
  - 87034000 (hev) e 87036000 (phev) aparecem em 2017-01; 87038000 (bev) em
    2017-02;
  - 87035000 (hev diesel) em 2019-12;
  - 87037000 (phev diesel) aparece num mês só, 2022-11.
- **8704: 2022-04.** 87046000 (bev) aparece em 2022-04, 87045100 em 2022-05 e
  87044100 em 2024-05.
- **Antes dessas datas** o dado não separa eletrificado. A coluna
  `separa_eletrificados_desde` guarda a data, e `comum.comex.grupo_no_mes`
  devolve `sem_separacao` para os meses anteriores.
- **Os três `sem_separacao` de 8704** são NCMs que só existiram antes de 2022-04:
  87041000 (dumpers), 87043220 e 87043290.

**`leve` (só em 8704).** O critério, declarado no arquivo e no dicionário:

- `sim` quando a descrição limita o peso em carga máxima a 5 t (10 NCMs);
- `nao` quando passa de 5 t ou é dumper (16 NCMs);
- `indeterminado` quando a descrição não dá limite (2 NCMs):
  - 87046000, de carga só elétrica, sem faixa de peso no SH 2022;
  - 87049000, o residual.

O `leve` não casa com o comercial leve da Fenabrave, que classifica por modelo.
Os dois indeterminados ficam fora da soma "8704 leve". Em 2026 (jan a ago), a
87046000 teve 2.936 unidades importadas e a 87049000 teve duas.

**Os dois registros que você pediu**, no dicionário e no docstring de
`comum/comex.py`:

- **MHEV.** Não suponho onde cai: pode estar em 8703.40 ou nas NCMs de combustão.
- **Kits.** SKD e CKD entram na NCM do veículo completo (regra geral 2a do SH).
  Está registrado, não separado.

### O produto

`dados/processado/comex_veiculos.parquet`:

- 73.316 linhas: 24.078 de importação e 49.238 de exportação;
- 48 NCMs, de 1997-01 a 2026-08;
- colunas `mes_ref, ano, mes, fluxo, ncm, pais, fob_usd, kg, unidades`.

`unidades` (Int64) só é preenchida onde a unidade estatística é unidade, o que
hoje vale para todas as NCMs. O grupo e o `leve` vêm da tabela de NCMs, pela
`ncm`.

Quem gera é a etapa 12 (`src/etapa12_comex.py`), que roda entre a 11 e a 6 no
pipeline. O dicionário está em `saidas/comex_dicionario.md`, com a tabela de
NCMs.

Entrou também:

- no CATÁLOGO (etapa 10, seção própria, com os usos em
  `config/catalogo_usos.csv`);
- no dicionário do painel;
- em `config/fontes_candidatas.csv`, como "construída".

### As conferências (seção 13 de `validacao.md`)

| conferência | casos | falhas |
|---|---:|---:|
| soma sobre países = consulta sem país (fluxo × NCM × ano; FOB, kg e quantidade) | 1.634 | 0 |
| mês faltando de 1997-01 a 2026-08 (fluxo × posição) | 4 | 0 |
| NCM fora das somas de unidades | 48 | 0 (nenhuma) |

A etapa 12 para com erro, sem gravar nada, em dois casos: se a soma sobre países
ou os meses falharem, ou se a tabela de NCMs versionada não cobrir o bruto
(NCM, unidade, período ou data da separação). A terceira conferência é de
construção: uma NCM fora de unidade sairia com `unidades` vazia, e um teste
confere isso.

### Um achado: linhas que não pesam como carro

Dividi o kg pelas unidades em cada linha (NCM × país × mês) e há linhas com menos
de 500 kg por unidade. Fui medir porque a importação de BEV de 2019 saltava sem
nada correspondente no painel.

- **Não filtrei nada.** O produto guarda as linhas como vêm, e
  `comum.comex.peso_baixo` só marca.
- **Onde ver.** `saidas/comex_diagnostico_peso.csv` dá o peso por ano. Nos
  uso-testes abaixo, as séries saem com e sem essas linhas.

Anos acima de 10% das unidades importadas (8703 + 8704 leve):

| ano | unidades | em linhas < 500 kg/un | % | maior caso (NCM, país, unidades) |
|---|---:|---:|---:|---|
| 2001 | 401.331 | 222.645 | 55,5 | 87032210, Argentina, 222.440 |
| 2003 | 92.944 | 29.432 | 31,7 | 87032310, Alemanha, 29.144 |
| 2006 | 508.319 | 344.665 | 67,8 | 87032310, México, 306.783 |
| 2019 | 313.821 | 32.391 | 10,3 | 87038000, China, 16.612 |
| 2020 | 198.196 | 33.424 | 16,9 | 87042110, China, 24.082 |
| 2021 | 302.179 | 40.150 | 13,3 | 87032100, China, 29.332 |

- **Peso médio no ano:** a 87032210 da Argentina em 2001 dá 25 kg por unidade, e
  a 87032310 do México em 2006 dá 92 kg.
- **A BEV de 2019** está em três meses:
  - China em setembro: 10.598 unidades, 1,3 kg cada;
  - Índia em agosto: 8.960 unidades, 1 kg cada;
  - China em novembro: 6.013 unidades, 3,9 kg cada.

### Uso-teste 1 — elétricos puros importados contra o painel

- **Importação:** a NCM 87038000. A 87046000 é `indeterminado` em `leve` e fica
  fora.
- **Painel:** unidades de vigência-ano com `propulsao_no_ano == bev` na leitura
  longa. Todas estão em automóveis.

| ano | importação BEV | sem peso baixo | painel só `bev` | razão | razão sem peso baixo | diferença acumulada |
|---|---:|---:|---:|---:|---:|---:|
| 2017 | 50 | 41 | 0 | – | – | 50 |
| 2018 | 167 | 132 | 0 | – | – | 217 |
| 2019 | 27.024 | 768 | 0 | – | – | 27.241 |
| 2020 | 6.573 | 760 | 76 | 86,49 | 10,00 | 33.738 |
| 2021 | 11.963 | 3.112 | 818 | 14,62 | 3,80 | 44.883 |
| 2022 | 9.411 | 9.392 | 1.197 | 7,86 | 7,85 | 53.097 |
| 2023 | 28.823 | 28.402 | 12.721 | 2,27 | 2,23 | 69.199 |
| 2024 | 80.589 | 80.537 | 53.493 | 1,51 | 1,51 | 96.295 |
| 2025 | 68.236 | 68.194 | 66.140 | 1,03 | 1,03 | 98.391 |
| 2026 (jan a ago) | 168.720 | 168.707 | 125.641 | 1,34 | 1,34 | 141.470 |

Descrição, sem explicação:

- **Sempre acima.** A importação passa o painel em todos os anos.
- **Diferença acumulada 2017–2026:** 141.470 unidades; sem as linhas de peso
  baixo, 99.959.
- **Até 2022** o painel tem poucos `bev` (zero até 2019) e a razão é alta.
- **De 2023 em diante** a razão vai de 2,23 a 1,51, depois 1,03 e 1,34.
- **2026 (jan a ago):** 168.720 BEV e 163.826 PHEV importados, como na sua conta.

### Uso-teste 2 — importação total contra a origem do painel

- **Importação:** 8703 + 8704 leve.
- **Painel:** unidades das vigências com origem `importado`. O `ambos` entra a 0%
  (mínimo) e a 100% (máximo), e o `nao_classificado` vai em coluna à parte.
- **Razões:** a mínima é importação ÷ painel máximo; a máxima é importação ÷
  painel mínimo.

| ano | importação | sem peso baixo | painel mín | painel máx | razão mín–máx | sem peso baixo |
|---|---:|---:|---:|---:|---|---|
| 2003 | 92.944 | 63.512 | 40.288 | 60.967 | 1,52–2,31 | 1,04–1,58 |
| 2004 | 71.655 | 69.141 | 50.054 | 72.088 | 0,99–1,43 | 0,96–1,38 |
| 2005 | 98.193 | 95.043 | 67.333 | 87.276 | 1,13–1,46 | 1,09–1,41 |
| 2006 | 508.319 | 163.654 | 109.089 | 131.955 | 3,85–4,66 | 1,24–1,50 |
| 2007 | 292.939 | 290.109 | 178.887 | 220.732 | 1,33–1,64 | **1,31**–1,62 |
| 2008 | 434.661 | 428.097 | 234.486 | 289.670 | 1,50–1,85 | **1,48**–1,83 |
| 2009 | 480.973 | 474.996 | 341.402 | 406.132 | 1,18–1,41 | 1,17–1,39 |
| 2010 | 702.506 | 698.290 | 501.863 | 575.100 | 1,22–1,40 | 1,21–1,39 |
| 2011 | 933.015 | 929.480 | 666.777 | 741.964 | 1,26–1,40 | 1,25–1,39 |
| 2012 | 730.991 | 726.304 | 614.733 | 690.464 | 1,06–1,19 | 1,05–1,18 |
| 2013 | 710.406 | 702.161 | 482.180 | 551.681 | 1,29–1,47 | 1,27–1,46 |
| 2014 | 583.198 | 576.005 | 411.270 | 495.848 | 1,18–1,42 | 1,16–1,40 |
| 2015 | 390.087 | 382.310 | 257.882 | 327.711 | 1,19–1,51 | 1,17–1,48 |
| 2016 | 235.749 | 231.122 | 198.655 | 252.157 | 0,93–1,19 | 0,92–1,16 |
| 2017 | 248.724 | 241.485 | 203.145 | 246.692 | 1,01–1,22 | 0,98–1,19 |
| 2018 | 347.210 | 340.393 | 278.836 | 317.463 | 1,09–1,25 | 1,07–1,22 |
| 2019 | 313.821 | 281.430 | 251.363 | 280.982 | 1,12–1,25 | 1,00–1,12 |
| 2020 | 198.196 | 164.772 | 171.402 | 188.267 | 1,05–1,16 | 0,88–0,96 |
| 2021 | 302.179 | 262.029 | 216.751 | 233.227 | 1,30–1,39 | 1,12–1,21 |
| 2022 | 294.455 | 288.303 | 233.952 | 246.012 | 1,20–1,26 | 1,17–1,23 |
| 2023 | 376.276 | 365.850 | 295.848 | 302.217 | 1,25–1,27 | 1,21–1,24 |
| 2024 | 530.649 | 514.679 | 396.885 | 411.447 | 1,29–1,34 | 1,25–1,30 |
| 2025 | 539.548 | 507.748 | 400.974 | 416.280 | 1,30–1,35 | 1,22–1,27 |
| 2026 (jan a ago) | 604.294 | 584.992 | 391.189 | 396.836 | 1,52–1,54 | **1,47**–1,50 |

- **Anos de distância grande.** O critério, declarado em `RAZAO_GRANDE`: razão
  mínima de 1,3 ou mais, já sem as linhas de peso baixo. Passam 2007, 2008 e
  2026. Com todas as linhas, 2003 e 2006 também passariam; 2021 e 2025 ficam em
  1,296.
- **Com todas as linhas** a importação passa o máximo do painel em 22 dos 24
  anos; só 2004 e 2016 ficam abaixo de 1.
- **Modelos de alto volume com origem só `proposta`.** Estão em
  `saidas/comex_origem_candidatos.csv`: os 10 maiores com origem `nacional` por
  procedência `proposta` em cada ano de distância grande. Escolhi os `nacional`
  porque são os que a distância põe em dúvida.
  - **2007:** Gol, Palio, Uno, Fox/CrossFox, Celta, Classic, Siena, Strada,
    Prisma, EcoSport.
  - **2008:** Gol, Palio, Uno, Celta, Fox/CrossFox, Classic, Siena, Strada, Ka,
    Prisma.
  - **2026:** Strada, Argo, Onix, T-Cross, Tera, Creta, HB20, Mobi, Kwid, Toro.

Não reclassifiquei nada.

### Uso-teste 3 — os países de origem

`saidas/comex_paises_top10.csv` traz os 10 primeiros por ano, de 1997 a 2026, em
8703 + 8704 leve, com a parte só de 8703 em coluna à parte.

- **Argentina** é a primeira em todos os anos de 1997 a 2024, menos 2006. Em 2006
  o primeiro é o México, onde estão as 306.783 unidades de peso baixo.
- **China** é a primeira em 2025 e 2026.
- **2025:**
  - China 241.344 (só 8703: 236.304);
  - Argentina 191.649 (só 8703: 82.005);
  - México 41.280 (só 8703: 34.356).

  Os seus números (236 mil, 82 mil e 34 mil) batem com a coluna só de 8703. A
  Argentina mais que dobra quando entra o 8704 leve.
- **2026 (jan a ago):** China 407.096 (67,4% do ano), Argentina 116.677, México
  39.129.
- **Uruguai** aparece só em 8704 leve: 17.785 em 2024 e 10.357 em 2026.
- **Brasil** aparece como país de origem de 2000 a 2005 (4.220 em 2003).

### Erros e correções

- **HTTP 429 no meio do download.** Pus backoff longo (8 tentativas, a partir de
  30 s e até 600 s) e 3 s entre as consultas, e retomei de onde parou. O
  manifesto confere que nada se perdeu.
- **Regex do `leve`.** A primeira versão só lia "superior a N" e "<= 5". Deixava
  como `indeterminado` as descrições com "> 20", "entre 5 e 20" e "maior que 20".
  Reescrevi a regra lendo os números e há um teste para cada forma.
- **Teste do catálogo.** Ele exige texto de uso para cada produto. Acrescentei o
  `comex_veiculos` em `config/catalogo_usos.csv` e atualizei o texto da
  `classificacao`, que ainda descrevia a rodada 8.

### O que fica aberto (também em `QUESTOES_ABERTAS.md`)

1. **Linhas de peso baixo.** Estão medidas e marcadas; filtrar ou não é decisão
   sua.
2. **Distância entre importação e origem.** Está registrada; 2007, 2008 e 2026
   têm razão de 1,3 ou mais, e os candidatos estão listados. Nada foi
   reclassificado.
3. **Excesso da importação de BEV sobre o painel.** Registrado, não explicado.
4. **O `leve` não é o comercial leve da Fenabrave.** A 87046000 e a 87049000
   ficam fora da soma.
5. **O MHEV e os kits** estão registrados e não separados.

### Arquivos desta parte

- código:
  - `src/comum/comex.py`;
  - `src/etapa12_comex.py`;
  - `src/ferramentas/comex_baixar.py`, `src/ferramentas/comex_ncm.py`;
  - mudanças em `src/etapa06_validacao.py` (seção 13), `src/etapa10_catalogo.py`,
    `src/pipeline.py`, `src/comum/config.py`;
- configuração: `config/ncm_veiculos.csv`, `config/catalogo_usos.csv`,
  `config/fontes_candidatas.csv`;
- dado: `dados/bruto/comex/` (comitado antes), `dados/processado/comex_veiculos.parquet`;
- saídas:
  - `saidas/comex_validacao.csv`, `saidas/comex_dicionario.md`,
    `saidas/comex_diagnostico_peso.csv`;
  - `saidas/comex_uso_teste_bev.csv`, `saidas/comex_uso_teste_origem.csv`;
  - `saidas/comex_paises_top10.csv`, `saidas/comex_origem_candidatos.csv`;
- testes: `testes/test_comex.py`.

### Fechamento

`validacao.md` e `CATALOGO.md` são regerados sobre a árvore limpa, com os testes
passando, num commit próprio. A tag `rodada-10` vai nesse commit, e a linha dela
em `tags_pendentes.csv`.
