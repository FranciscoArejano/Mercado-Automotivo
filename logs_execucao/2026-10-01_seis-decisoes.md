# Registro de execução — as seis decisões e o registro das tags

01/10/2026. Branch `claude/new-session-rs2chd`. Este registro vai no mesmo push
do trabalho que ele descreve. Não é a fase 2: nada foi gravado em
`dados/processado/`. A regra que a fase 2 vai seguir ficou fixada (decisão 6),
sem executá-la.

## A conta

`a_adjudicar` foi de **154 linhas para 104**:

| | linhas | unidades |
|---|---:|---:|
| saíram pela decisão 1 (P4, `hibrido_indefinido`) | 12 | 1.329.486 |
| saíram pela decisão 1 e pela aceitação da decisão 5 | 1 | 6.013 |
| saíram pelo corte da P2 (decisão 3) | 10 | 774.840 |
| saíram pelo corte e pela aceitação da decisão 5 | 2 | 234.460 |
| saíram pela aceitação de fonte fraca (decisão 5, O4) | 20 | 2.031.419 |
| saíram por segunda fonte forte (decisão 5, O1) | 7 | 541.096 |
| **saíram, no total** | **52** | |
| ficaram | 102 | |
| voltaram pelo corte da P2 (Cruze HB 2012-2016, Captiva) | 2 | |

As contas que você pediu:

- **Decisão 1:** das 18 linhas do Híbrido sem HEV no nome, **13 saíram**.
  - As outras 5 receberam `hibrido_indefinido`, mas ficam por outro motivo:
    208 e Discovery pela origem inconclusiva; A3 Sedan pela origem que
    contradiz; 2008 pelo `bev` ausente do PBE e pela origem; A3 pela guarda da
    tabela sem coluna.
- **Decisão 3:** das cinco linhas da P2, Blazer, J3 e Edge ficam resolvidas;
  **Cruze HB 2012-2016 e Captiva voltam**, porque a vigência chega a 2016.
- **Decisão 5**, as 45 linhas de "só fonte fraca":
  - **23 saem por aceitação** (O4);
  - **7 saem porque ganharam segunda fonte forte**: Tracker (três vigências),
    GLA (três) e Spark;
  - **15 ficam**. Cinco delas também ganharam segunda fonte forte, mas ela não
    decide: Versa (três vigências), porque a fonte dá o ano e não o mês;
    Civic (duas), porque a fonte é plano.
- **Decisão 2:** as seis linhas da sensibilidade (Kicks, Cruze HB, Cruze Sedan
  2016-2026, Space Fox) seguem resolvidas.

---

## 0. Antes das decisões: um defeito meu de extração

Ao medir a cobertura do PBE para a decisão 3, a tabela de 2017 saiu com 71,0%
do volume, entre 95,5% (2016) e 85,1% (2018). O Onix, carro mais vendido do
país, estava em 2016 e 2018, mas não em 2017.

- **A causa era o leitor, não o PBE.** De 2017 a 2019 a célula do modelo
  quebra, e o nome sai numa linha própria, acima da linha de dados:

  ```
  NOVO ONIX
  COMPACTO CHEVROLET 1.0MT LS / 1.0MT LT 1.0L - 8V M-6 S E F ...
  (MY17)
  ```

  O leitor lia a versão ("1.0MT LS") como nome, e ela não casava com o
  painel.
- **A correção:**
  - cada linha de veículo leva agora `linha_acima`, a linha imediatamente
    anterior na mesma página, quando ela não é linha de veículo nem cabeçalho;
  - o casamento só a usa quando o nome da própria linha não casa (coluna
    `casou_por`).
  - Recuperou 75 linhas em 2017, 83 em 2018, 63 em 2019 e algumas outras
    (Megane 2010-2012, Porsche 2024).
  - Conferi a recuperação por amostra (Ranger, Prisma, Cobalt, Hilux, Tucson):
    todas corretas, e nenhuma das linhas de cima traz marcador de propulsão.
  - Testes: uma linha literal de 2017 na extração e um caso no casamento.
- **Efeito:**
  - a cobertura passa a 87,8% em 2017, 91,7% em 2018 e 90,0% em 2019;
  - duas comparações mudam: Ranger e Megane 2003-2011 passam a concordar com
    o PBE;
  - **o ano de corte não muda**: de 2009 a 2015 o defeito quase não aparecia.

---

## 1. Decisão 1 — `hibrido_indefinido`

- **Taxonomia:** valor novo na propulsão, entre `mhev` e `hev`. Na derivação
  da eletrificação conta como `mhev`: `parcial`, nunca `total`. Testado
  sozinho, com `hev` e com `flex`.
- **Regra nova, P4:** o tipo `hev` que o PBE acrescenta a partir de versão sem
  HEV no nome entra como `hibrido_indefinido`.
  - Passa pela mesma guarda de ano dividido da P1.
  - Versão com HEV no nome continua entrando como `hev` pela P1 (Carnival).
  - A P3 (Híbrido contra `mhev` da proposta) continua mandando para você seis
    linhas: Pulse, Fastback, Tiggo 5X, Tiggo 7, Arrizo 6 e Stonic.
  - A decisão 1 não falou delas. Se quiser, seguem a mesma lógica (ficam
    `mhev`, ou viram `hibrido_indefinido`); a eletrificação é `parcial` nos
    dois casos.
- **Na `resolvido_por_regra`:** 18 decisões P4, 13 de linhas que saíram da
  fila.

## 2. Decisão 2 — revista automotiva de consumo

- **Nada mudou no mapeamento.** As decisões ficaram como estavam.
- **Removi a conta de sensibilidade** do rascunho e o parâmetro que a
  calculava; a decisão a encerrou.
- **Achado relacionado** (seção 5, item 2): a força de uma citação de segunda
  mão agora é a do veículo original.

## 3. Decisão 3 — corte da P2 pela cobertura do PBE

- **Cobertura por ano:** `saidas/pbe_cobertura_por_ano.csv` (aba
  `pbe_cobertura`). É a fração do volume do painel cujo modelo aparece na
  tabela daquele ano.
  - É cobertura por modelo, não por versão: o modelo conta inteiro se uma
    versão dele está na tabela.
  - Depende do casamento: modelo que o PBE escreve de um jeito que o
    casamento não reconhece conta como ausente.

| ano | versões | cobertura |
|---|---:|---:|
| 2009 | 31 | 44,5% |
| 2010 | 67 | 40,3% |
| 2011 | 73 | 50,6% |
| 2012 | 205 | 58,2% |
| 2013 | 448 | 67,2% |
| 2014 | 599 | 70,8% |
| 2015 | 692 | 75,2% |
| **2016** | 1.102 | **95,5%** |
| 2017 | 720 | 87,8% |
| 2018 a 2026 | 675 a 1.114 | 90,0% a 98,8% |

- **Corte: 2016.** No dicionário está a frase citável: "a ausência no PBE só
  foi tratada como informativa a partir de 2016, quando o programa passou a
  cobrir 95,5% do volume do painel (em 2015, 75,2%)". O número sai do CSV,
  não está escrito à mão.
- **Uma premissa sua conferida.** A tabela de 2009 tinha mesmo 31 versões,
  mas elas cobriam 44,5% do volume, porque eram dos carros mais vendidos.
  Pouco em versões não é pouco em volume. Abaixo de 80% ela está, então a
  conclusão não muda.
- **Como a P2 ficou:**
  - **Linha ausente do PBE:** vigência inteira antes de 2016 mantém tudo;
    senão, decisão humana.
  - **Linha que diverge:** mantém o tipo de combustão quando há pelo menos 12
    meses de vigência antes do primeiro ano do modelo no PBE **e** antes do
    corte, o que vier primeiro. Nenhuma decisão antiga mudou com isso: os
    primeiros anos dos modelos em questão são anteriores a 2016.
- **As cinco linhas:**
  - ficam resolvidas Blazer (2003-2012), J3 (2011-2012) e Edge (2009-2015);
  - voltam Cruze HB 2012-2016 e Captiva 2008-2016.
- **Além das cinco, para você confirmar.** A regra também resolve 12 linhas de
  modelos que **nunca** aparecem no PBE, com vigência inteira antes de 2016.
  - São Agile, Astra, Zafira, Xsara Picasso, Scenic, Vectra Hatch, Sonic
    Sedan, Veracruz, Hoggar, Tiida, 206 e 320 (2003-2014).
  - Elas estavam na fila por "ausente no PBE". O seu texto ("antes dele,
    ausência no PBE é não informativa e a P2 mantém") as cobre.
  - Se a intenção era só o caso "PBE já existente", elas voltam.
  - A procedência delas é `regra_fonte_fraca`: a P2 decide sem evidência
    positiva.

## 4. Decisão 4 — montagem com `nao_se_aplica` e período próprio

- **Tabela de períodos.** A montagem virou uma tabela própria, aba
  `montagem_local` e `saidas/classificacao_montagem_periodos.csv`, no padrão
  de vigência do mapa de grupos.
  - Cada vigência é cortada nos meses que a fonte cobre: dentro, o modo da
    fonte; fora, `desconhecido`.
  - Vigência `importado` é `nao_se_aplica`. Os períodos de cada modelo cobrem
    todos os meses, sem sobreposição.
  - Na aba `classificacao`, `montagem_por_periodo` resume a linha, por
    exemplo "ckd 2016-06 a 2016-12; desconhecido 2017-01 a 2026-08".
- **Resultado:**

| modo | períodos | unidades | % do volume |
|---|---:|---:|---:|
| `fabricacao` | 4 | 46.266 | 0,08 |
| `ckd` | 1 | 1.071 | 0,00 |
| `skd` | 1 | 628 | 0,00 |
| `desconhecido` | 194 | 50.601.524 | 87,80 |
| `nao_se_aplica` | 244 | 6.982.245 | 12,12 |

- **Os períodos com modo:**
  - **`fabricacao`:** March e Versa em Resende (2014-04 a 2015-04), Haval H9
    e Poer em Iracemápolis (2026-08);
  - **`ckd`:** Evoque em Itatiaia (2016-06 a 2016-12);
  - **`skd`:** Spark EUV em Horizonte (2026-03).
  - O Evoque de 2016-2026 era `ckd` inteiro na rodada anterior. Agora é
    `ckd` só em 2016 e `desconhecido` de 2017 em diante, porque a fonte diz
    "na fase inicial".
- **Pendentes:** BYD (Dolphin Mini, King, Song) e Haval H6 são `nao_se_aplica`
  enquanto a vigência for `importado`. A observação do período diz qual modo a
  fonte declara. Quando você dividir a vigência (está em `a_adjudicar`), a
  parte nacional recebe `skd` ou `fabricacao`.
- **O volume com modo é quase nada.** Para o artigo de tarifa, a montagem
  ainda é quase toda `desconhecido`. Só fontes novas mudam isso.

## 5. Decisão 5 — aceitação, segunda fonte e o que apareceu nela

### 5.1 O4 e a nota da O3

- **O4, regra nova:** `confirma` apoiada só em fonte fraca é aceita, com
  procedência `regra_fonte_fraca`. A ressalva viaja em `resolvido_por_regra`:
  "proposta e página da web não são evidência independente".
- **A O3 diz agora, no motivo,** se a segunda fonte:
  - não foi buscada (vigência anterior a 2014);
  - foi buscada e não achada;
  - ou ainda não foi buscada.
- **Registro das buscas:** `dados/referencia/segunda_fonte_buscas.csv`.
- **Interpretação minha de "vigências de 2014 em diante":** vigência que
  **começa** em 2014 ou depois. Tracker, GLA, Civic e 208 têm vigências dos
  dois lados da fronteira, e a busca por modelo cobre as duas.
  - Ficaram sem busca, por começarem antes de 2014, Tucson, Outlander, Kangoo,
    Lancer, X3 e Classe A, embora atravessem a janela.
  - Se a intenção era "vigência que toca 2014", são esses seis.

### 5.2 As segundas fontes

Mesma regra contra citação inventada: página guardada com SHA-256, trecho
literal e teste.

- **Spark EUV — achada.** AutoPapo, 03/12/2025, na inauguração da PACE: "O
  primeiro produto feito lá é o Chevrolet Spark EUV", montado em SKD.
  - Pela O1, a origem que eu não tinha proposto passa a `nacional`: a fonte
    cobre a vigência inteira, que começa em 2026-03.
- **GLA — achada.** O comunicado da Mercedes (Automotive World) e a Motor
  Show, ambos de 02/09/2016: produção iniciada "cinco meses depois da
  inauguração".
  - Confirma a proposta (nacional desde 2016-09). O 2016-08 da Comprecar era
    data que eu tinha derivado.
  - Ressalva: pelo "cinco meses", o início pode ter sido no fim de agosto.
- **Tracker — achada.** AutoIndústria, 18/03/2020: a nova geração produzida
  em São Caetano e já à venda.
  - Não data o início da produção (janeiro, segundo a GM Authority), mas
    confirma a fronteira da proposta, que é o lançamento.
  - Abri também uma AutoData com o título "GM começa a produzir o novo
    Tracker". É de **julho de 2025**, sobre a reestilização, e não a citei.
- **Versa — achada, não decide.**
  - Motor Show, 18/03/2015: o Novo Versa feito em Resende chega às lojas.
  - Motor Show, 22 anos da Nissan: produção em série em 2015.
  - **A proposta (nacional desde 2014-04) está errada pelas duas.** Mas
    nenhuma dá o mês de início da produção, então a O2 não decide. A
    fronteira fica com você: 2015-01, 02 ou 03.
- **Civic — achada, não decide.**
  - MarkLines (22/10/2021) e Motor Show (19/10/2021) falam em encerrar em
    novembro, no futuro: é plano. A da Motor Show repassa o Autos Segredos.
  - AutoPapo (11/11/2021): a Honda confirma o fim "até o final do ano",
    sem mês.
  - Fica com você.
- **208 — só fraca.**
  - O mês do fim em Porto Real (meados de março de 2020) só aparece na
    Autoweb argentina, que repassa o Autos Segredos.
  - As MarkLines tratam do 208 novo na Argentina, não do fim em Porto Real.

### 5.3 Duas coisas que a busca mostrou

1. **Citação de segunda mão.** Motor Show e Autoweb repassam o Autos Segredos,
   um blog.
   - Um veículo forte que repassa um blog não é evidência forte. Nova coluna
     `fonte_primaria` em `origem_fontes.csv`: quando a matéria repassa outro
     veículo, o tipo é o do original.
   - Procurei marcas de repasse ("segundo o site", "Autos Segredos",
     "according to"…) em todas as páginas já citadas. Só a da dol.com.br (o
     Civic) repassava o fato citado. Ela passa de `imprensa_geral` a
     `blog_agregador`, ainda fraca, e o resultado não muda.
   - `autossegredos.com.br` entrou no mapeamento como `blog_agregador`. Nunca
     abri o site diretamente.
2. **Data de produção não é data de emplacamento.** As vigências são de
   emplacamento; as fontes datam produção.
   - O Tracker começou a ser produzido em janeiro de 2020, mas os
     emplacamentos de janeiro e fevereiro ainda eram do importado: o novo foi
     lançado em março. O Civic parou de ser produzido em novembro de 2021, e
     o estoque nacional seguiu emplacando.
   - **A O2 que você aprovou move a fronteira para a data de produção.** Foi
     o que aconteceu com o Kicks (2017-04, por início de produção), e o
     primeiro Kicks nacional emplacado pode ser de maio, como a proposta
     dizia.
   - É questão para você: a O2 deve exigir data de chegada ao mercado, ou
     aceitar a defasagem? Não mudei a regra.

### 5.4 Leitura da linha: a fonte forte vem antes da fraca

Antes, a leitura de uma linha era a pior entre as fontes do modelo. Uma
segunda fonte forte que **confirma** não desfazia um `ajusta_data` fraco, e
a busca seria inútil.

- **Agora:** se alguma fonte contradiz ou é inconclusiva, essa leitura manda
  (O3, de qualquer fonte, como você escreveu). Senão, vale a pior leitura
  **entre as fontes fortes**, quando há alguma.
- **Testado** com o caso do GLA e com um contradiz fraco que continua
  mandando.
- **Consequência que você deve conhecer.** As fontes são do modelo, não da
  vigência, então a confirmação vale para todas as vigências do modelo.
  - O Tracker de 2003-2009 (importado) e o de 2013-2020 saíram da fila pela
    O1 com uma fonte de 2020.
  - O GLA importado de 2021-2023 saiu com fontes do início da produção.
  - A procedência delas é `regra_fonte_forte`, o que é generoso para
    vigências que a fonte não trata.

## 6. Decisão 6 — precedência e procedência

- **O `leia_me` mudou.** A regra antiga ("linha com decisão vazia não entra na
  fase 2") saiu. Em seu lugar entrou o tópico "regra da fase 2", com a
  precedência por linha e atributo e as quatro procedências.
- **Prévia na aba `classificacao`:** colunas `procedencia_propulsao`,
  `procedencia_carroceria` e `procedencia_origem` (a montagem tem a sua, por
  período). As interpretações são minhas, para você conferir:
  - **Valor confirmado sem contestação conta como regra com fonte.** Um valor
    que a checagem confirmou sem contestá-lo é `regra_fonte_forte`; a
    `proposta` fica para o que nenhuma checagem tocou. São o PBE que concorda
    com a propulsão, a origem confirmada por fonte forte fora da fila e a
    carroceria tirada do sub-segmento da Fenabrave.
    - Com a leitura literal ("decidida por regra"), 83% do volume da
      propulsão, que o PBE confirma, passaria por `proposta`.
  - **P2 e O4 dão `regra_fonte_fraca`.** A P2 mantém sem evidência positiva.
  - **`pendente` não é um dos quatro valores.** Marca o atributo que está em
    `a_adjudicar` sem decisão humana. Pela precedência, a fase 2 pegaria a
    proposta, e chamá-la de `proposta` ("nunca contestada") seria falso.
    Proponho que a fase 2 se recuse a rodar com `pendente`.
- **Hoje, em volume:**

| | forte | fraca | pendente | proposta |
|---|---:|---:|---:|---:|
| propulsão | 91,0% | 4,1% | 4,5% | 0,5% |
| carroceria | 79,5% | — | — | 20,5% |
| origem | 4,4% | 7,3% | 7,2% | **81,2%** |

  **A origem continua quase toda sem checagem.** Os modelos de confiança
  `alta` nunca foram para a busca (Gol, Onix, HB20…). Um artigo que use origem
  como tratamento e se restrinja à procedência forte fica hoje com 4,4% do
  volume.

## 7. Tags

- **`tags_pendentes.csv`** na raiz, com as quatro linhas que você mandou, e uma
  linha no README.
- **Conferi cada uma contra as tags locais: as quatro batem.**
- **Um erro meu na rodada anterior:** minha tag local `rodada-6` apontava
  para `fba281a`, o commit do trabalho, e não para o de fechamento como as
  outras. Movi para `611b74e`, como na sua tabela. Ela nunca chegou ao remoto.
- **Ao fechar, acrescento a `rodada-7`** com o commit de fechamento desta
  rodada.

---

## 8. Erros cometidos e como foram corrigidos

1. **Extração de 2017-2019** (seção 0).
2. **Sobrescrevi uma página guardada.** Abri de novo a matéria da Revista
   Carro sobre o 208 com o mesmo nome de arquivo usado na rodada B, e a
   ferramenta sobrescreveu o snapshot. Só a barra final da URL mudou, mas o
   hash mudou e o teste quebrou.
   - Restaurei o original pelo git.
   - Agora a ferramenta recusa nome que já está no manifesto.
3. **Leitura minha corrigida.** Ao reler essa mesma matéria, vi que a rodada B
   a tinha lido como `confirma`. "Já não é mais fabricado em Porto Real há
   alguns meses" não decide entre 2019-12 e 2020-03. Corrigi para
   `inconclusivo`, com nota datada na observação. Com a leitura nova, que põe
   a fonte forte primeiro, o `confirma` teria aceitado a fronteira de 2019-12
   sem base.
4. **Página que não serve.** A AutoData do "novo Tracker" é de 2025, e quase
   a citei para 2020. Conferi a data de publicação no metadado, não citei e
   registrei na planilha de buscas.
5. **Tag local `rodada-6`** (seção 7).

## 9. O que ficou em aberto

- **As 104 linhas de `a_adjudicar`.**
- **Questões:**
  1. As 12 linhas de modelos nunca listados no PBE que o corte resolve
     (seção 3): ficam?
  2. Data de produção ou de emplacamento na O2 (seção 5.3)? O Kicks está
     resolvido por data de produção.
  3. Fonte do modelo vale para todas as vigências dele (seção 5.4)?
  4. P3 (6 linhas): mesma lógica da decisão 1?
  5. Procedência: "confirmado sem contestação" como `regra_fonte_forte`, e
     `pendente` impedindo a fase 2 (seção 6)?
  6. "Vigências de 2014 em diante": começar ou tocar (seção 5.1)?
- **Duas chaves do mesmo carro.** O PBE escreve "320I", que só casa com a
  chave BMW/320I. A chave BMW/320 nunca casa, e a vigência 2014-2019 dela
  fica "ausente". É o caso "um produto, duas chaves", adiado pela Parte 0.
- **Fase 2:** não começada. A regra dela está no `leia_me` e no dicionário.

## 10. Conferência

- **Testes:** 255. O novo cobre a extração com linha de cima, o casamento,
  `hibrido_indefinido`, P4, P2 com corte, O4, a leitura com fonte forte
  primeiro, a nota de segunda fonte, a montagem por período, a procedência, a
  cobertura e o tipo da citação de segunda mão. Pyflakes limpo.
- **Fontes:** 90 citações em `origem_fontes.csv`. São 10 novas, de 15
  páginas abertas nesta rodada; as cinco não citadas estão explicadas na
  planilha de buscas.
- **Rascunho:** abas novas `pbe_cobertura` e `montagem_local` (refeita). Na
  aba `classificacao`, colunas novas `procedencia_*` e `montagem_por_periodo`.
- **`validacao.md` e `CATALOGO.md`** regerados sobre a árvore limpa depois do
  commit do trabalho.
