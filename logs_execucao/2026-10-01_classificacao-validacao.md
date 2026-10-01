# Registro de execução — classificação: taxonomia e validação contra fonte

01/10/2026. Branch `claude/new-session-rs2chd`. Este registro vai no mesmo push
do trabalho que ele descreve. Não é a fase 2: nada foi gravado em
`dados/processado/`.

## Em uma frase

A propulsão do rascunho foi confrontada com as 18 tabelas do PBE Veicular. A
origem foi confrontada com 77 fontes datadas, de 70 modelos, todas abertas nesta
rodada. A aba `a_adjudicar` traz só o que ainda precisa da sua decisão (164
linhas, maior volume primeiro), e a BYD está lá: a fonte confirma Camaçari desde
outubro de 2025. Duas coisas do seu pedido não se confirmaram como você
descreveu, e explico abaixo (seções 0 e 2.1).

---

## 0. Correções registradas

- **Branch `teste-permissao-tag`.** Registrado que você já a apagou. Pendentes
  ficam as tags `rodada-3` e `rodada-4`.
- **Os arquivos "máscara" do PBE de 2025 e 2026 são as tabelas.** Você conferiu
  que `mascara-pbev-2025...` e `mascara-pbev-2026...` não contêm veículos.
  Baixei os dois e eles contêm:
  - o de 2025 tem 13 páginas e o nome no servidor "MÁSCARA-PBEV-2025-24-NOV-2025";
  - o de 2026 tem 9 páginas e é servido como "Tabela PBEV 2026_25_AGO.pdf";
  - os dois listam modelo, versão e tipo de propulsão por linha (Dolphin Mini
    "Elétrico", Corolla Altis HV "Híbrido", Corolla GLi 2.0 "Combustão").

  A tabela de 2024 também se chama "Mascara PBEV 2024" no servidor. O que
  provavelmente enganou: a primeira página de cada um sai embaralhada na
  extração de texto (rótulos rotacionados). A de 2026 tem ainda texto
  sobreimpresso (cada letra desenhada várias vezes) em corpo 1,8 pt, que só se
  lê com deduplicação de caracteres e tolerâncias proporcionais ao corpo.
- **As tabelas de 2009 a 2021 estão na mesma página do Inmetro**, como
  "Veículos leves AAAA". O site antigo não foi preciso.
- **Parte das "24 trocas sem data" da rodada anterior era de propulsão, não de
  origem.** São Corolla híbrido, Pulse e Fastback MHEV, RAV4, Accord, Cayenne e
  Macan. A busca de fonte de origem se concentrou nas trocas de origem de fato:
  31 modelos, contando os de origem `ambos`.

---

## 1. Decisões de taxonomia aplicadas

- **`mhev` e `reev` entraram na propulsão; `caminhao_leve`, na carroceria.**
  Na derivação, modelo com `mhev` e combustão conta como `parcial`, nunca
  `total`. A regra está no código, testada, e no dicionário.
- **`caminhao_leve` entra pela regra S11** (`config/regras_classificacao.csv`):
  o conhecimento *refina* o furgão da fonte, que não tem a categoria, e não
  troca nenhuma outra carroceria. Aplicado a HR, Bongo K2500/K2700, Delivery
  Express (três chaves) e Foton Aumark (duas). Daily e Sprinter ficaram em
  furgão: o nome não separa furgão de chassi-cabine.
- **Propostas atualizadas:**
  - Pulse, Fastback, Tiggo 5X/7, Arrizo 6 e Stonic ganharam `mhev`;
  - o Leapmotor C10 ficou `bev+reev`.
- **Transição flex: fica como está.** Registrada como limitação no dicionário.
  Na comparação com o PBE, a gasolina de quem atravessou a transição antes de
  2009 não conta como divergência: o PBE não a pode ver.
- "Um nome, dois produtos" e "um produto, duas chaves" continuam adiadas. A aba
  `questoes` ganhou as colunas `estado` e `decisao_humana`, com as suas decisões.

---

## 2. Propulsão contra o PBE Veicular

### 2.1 Aquisição e leitura

- **18 tabelas, 2009 a 2026**, em `dados/bruto/pbe/` com manifesto SHA-256,
  comitadas e empurradas logo que baixadas (§10.1). Os arquivos de etiqueta
  (ENCE, VEHP) não são tabela e ficaram de fora.
- **O leitor** (`src/comum/pbe.py`, ferramenta `src/ferramentas/pbe_extracao.py`)
  não usa o cabeçalho. Os rótulos mudam de ordem (Motor vem antes de Versão de
  2014 a 2020), de alinhamento (em 2014 "Marca" fica 10 pt à direita do nome
  da marca) e são rotacionados nos anos recentes. Ele se apoia no que toda linha
  de veículo tem:
  - a marca, de uma lista em `config/pbe_marcas.csv`;
  - a trinca ar/direção/combustível (S|N, H|E|M|E-H, G|E|F|D);
  - o motor antes da trinca;
  - a palavra de propulsão.

  Modelo e versão saem juntos (`modelo_versao`): a fronteira entre os dois não
  é recuperável de forma confiável nas 18 diagramações, e o casamento é por
  prefixo, então não precisa dela.
- **Resultado:** 12.154 linhas de versão em `saidas/pbe_versoes.csv`, de 31
  (2009) a 1.114 (2021) por ano. Ficaram 17 linhas sem leitura
  (`saidas/pbe_linhas_nao_lidas.csv`), quase todas cabeçalho ou linha sem
  modelo.

### 2.2 O que o PBE distingue — enumerado

- **Até 2020 não há coluna de propulsão.** Só o combustível (G, F, D, E) e, às
  vezes, um marcador no nome da versão ("HYBRID", "PHEV").
- **De 2021 em diante, quatro valores, e só esses:** Combustão, Híbrido,
  Plug-In, Elétrico. Contagens por ano estão no próprio arquivo de versões.
- **Não distingue híbrido leve, e é inconsistente:**
  - em 2021, o Kia Stonic MHEV e o Subaru Forester MHEV estão em Híbrido, e o
    Subaru XV MHEV em Combustão;
  - os Stellantis "HYB" (Pulse e Fastback de 2025 e 2026, Renegade de 2026),
    o Toro de 2026 (sem marcador nenhum no nome) e o Land Rover Discovery Sport
    D200, que são híbridos leves, estão em Híbrido sem MHEV no nome.
- **Não distingue REEV:** o Leapmotor C10 REEV está em Plug-In.
- **O mapeamento está em `config/pbe_propulsao.csv`**, com regras ordenadas e
  observação em cada uma. Onde o nome da versão diz MHEV ou REEV, o nome manda.
  Híbrido sem marcador vira `hev`, e por isso "só no PBE: hev" contra uma
  proposta `mhev` tem de ser lido como possível rótulo do PBE, não como erro da
  proposta.

### 2.3 Casamento e comparação

- **Casamento** por marca (`config/pbe_marcas.csv`: CHEVROLET→GM,
  VOLKSWAGEN→VW, MERCEDES-BENZ→M.BENZ…) e pelo **prefixo mais longo** do nome do
  modelo, versão ignorada.
- **Apelidos** onde o PBE escreve diferente estão em `config/pbe_modelos.csv`,
  cada um com observação: ETIOS HATCHBACK, UP!, SPACEFOX, CR-V, GRAND VITARA,
  C4 LOUNGE, e as classes da Mercedes.
  - Dois apelidos são inferência e estão marcados como tal: HB20X→HB20 e GRAND
    SIENA→SIENA, porque o painel não tem essas chaves.
  - "CRUZE" e "CRUZE LT", sem dizer se é sedã ou hatch, e "GRAND CHEROKEE", sem
    chave no painel, ficaram de fora de propósito.
- **Cada ano do PBE vai para a vigência com mais meses naquele ano.**
- **Resultado:**

| | modelos | % do volume classificado |
|---|---:|---:|
| com alguma versão no PBE | 300 de 409 | 95,1 |
| propulsão **concorda** | 226 | 82,5 |
| propulsão **diverge** | 67 | 11,8 |
| propulsão **ausente** no PBE | 132 | 5,7 |

(Um modelo com duas vigências pode estar em dois níveis, então a coluna de
modelos não soma 409.)

### 2.4 O que as divergências mostram

Conferi as maiores linha a linha no PBE. São conteúdo da tabela, não erro de
casamento:

- **Propostas minhas incompletas:**
  - L200 sem a versão flex (2014-2018 no PBE);
  - Outlander sem a diesel (2016-2019);
  - Kangoo sem a elétrica;
  - Tiggo 7 sem a plug-in;
  - HR-V e Compass sem as versões só a gasolina (HR-V Touring 1.5 turbo,
    Compass Blackhawk 2.0);
  - Sportage sem a híbrida.
- **Elementos da proposta que o PBE não vê** porque são anteriores a ele ou
  versões que não participaram. Exemplos: o diesel do EcoSport (até ~2006) e o
  flex de Lancer e Eclipse Cross. Ficam na fila para você decidir.
- **Híbrido leve rotulado como Híbrido pelo PBE** (ver 2.2). Não é divergência
  de produto; é decisão sua se aceita o rótulo do PBE ou o `mhev` da proposta.

Duas chaves do painel parecem agregar dois produtos, porque o PBE casou
versões de ambos nelas e não há chave separada para o segundo: OUTLANDER
recebe o Outlander Sport, e DISCOVERY recebe o Discovery Sport.

---

## 3. Origem contra fontes datadas

### 3.1 Como

- **Regra contra citação inventada, tornada verificável.** Cada página aberta
  foi baixada nesta rodada pela ferramenta `src/ferramentas/origem_fonte.py`,
  que guarda o texto em `dados/bruto/origem_paginas/` com SHA-256 no manifesto.
  Foram 48 páginas salvas e 44 citadas.
- **Cada trecho copiado em `dados/referencia/origem_fontes.csv` aparece
  literalmente no texto guardado.** O teste `test_origem_fontes.py` confere,
  junto com o hash e a URL. Um trecho parafraseado quebra o teste.
- **Colunas no rascunho:** `origem_fonte_url`, `origem_fonte_trecho`,
  `origem_data_fonte`, `origem_situacao` e `origem_confronto`.
  - `origem_confronto` (confirma, complementa, ajusta_data, contradiz,
    inconclusivo) é a **minha leitura** da fonte contra a proposta, marcada como
    tal. Confira o trecho antes de aceitar.
  - A proposta original ficou intacta.

### 3.2 Resultado

- **Trocas de origem: 25 dos 31 modelos ganharam fonte datada.** Ficaram sem
  fonte:
  - 330E, BYD Song, BYD Yuan e Frontier;
  - o Versa, cuja fonte não traz o mês;
  - o RAV4, que entrou no grupo por engano: a troca dele é de propulsão.
- **Origem `media`/`baixa` entre os 241 maiores:** dos 90 modelos da busca
  inteira, 58 têm fonte datada e 32 não (lista na seção 5).
- **Confronto, por modelo, nas 77 fontes:**

| leitura | modelos |
|---|---:|
| confirma | 38 |
| complementa (preenche origem vazia ou acrescenta período) | 10 |
| ajusta a data da vigência | 9 |
| contradiz a proposta | 10 |
| inconclusivo | 7 |

- **O que contradiz, por volume:**
  - **BYD Dolphin Mini**: montagem em Camaçari desde 2025-10, segundo a
    Autodata de 5/11/2025, que dá 363 unidades no primeiro mês. A proposta dizia
    importado até 2026-08.
  - **BYD King**: anunciado como nacional em 2025-10 (notícia da própria BYD),
    mas a Autodata de novembro diz que ainda não era montado. Sem data de
    início. O **Song Pro**, idem.
  - **GWM Haval H6**: Iracemápolis, produção desde 2025-09, segundo a fonte
    oficial da GWM. O H9 e a Poer saem da mesma fábrica, com a origem que eu não
    tinha proposto agora coberta.
  - **VW Jetta**: a linha do tempo da fábrica Anchieta lista o Jetta produzido
    lá de 2014 a 2018. Eu tinha proposto importado com confiança `alta`. É o
    caso que mostra que `alta` por conhecimento não é verificação.
  - **Golf, Audi Q3, Audi A3 Sedan, ix35, ASX e Peugeot 2008**: eu tinha `ambos`
    na vigência inteira; as fontes mostram troca datada, que pede divisão.
    Golf nacional desde 2015-01; Q3 desde 2016-03; A3 Sedan desde 2015-10; ix35
    desde 2013-11; ASX desde 2013; 2008 em Porto Real até 2023-11, argentino
    depois.
- **O que ajusta datas:**
  - Tracker nacional desde 2020-01 (eu tinha 2020-03);
  - Kicks desde 2017-04 (eu tinha 2017-05);
  - Civic com fim previsto para 2021-11 (fonte de segunda mão);
  - GLA desde 2016-08;
  - Jimny desde 2013 (eu tinha 2012);
  - Classe A em Juiz de Fora até 2005-07;
  - 208 em Porto Real até 2020-03;
  - QQ importado da China desde 2015-04 e nacional só a partir de 2016-03 (eu
    tinha nacional desde 2015-01).

### 3.3 Questão nova (§9.6): montagem de conjuntos importados

Várias das trocas com fonte são montagem de kits:

- a BYD (fonte não detalha);
- o Spark EUV em Horizonte (SKD declarado);
- o Land Rover de Itatiaia no início (CKD);
- os furgões do Uruguai (SKD).

A GWM declara processo "peça a peça". A lista de origem não distingue montagem
de fabricação. Para o artigo de tarifa isso importa, porque o kit tem alíquota
diferente do carro inteiro. A pergunta está na aba `questoes` com três opções.
Recomendo um valor ou coluna própria (`montagem_local`), em vez de juntar a
`nacional`.

---

## 4. Erros cometidos e como foram corrigidos

1. **Nomear colunas pelo rótulo mais próximo.** Minha primeira tentativa achava
   as colunas pelo início recorrente das palavras e as nomeava pelo rótulo do
   cabeçalho. Falhou em metade dos anos, porque cada página tem legendas com as
   mesmas palavras. Troquei pelas âncoras da seção 2.1.
2. **Marcador do nome confundido com propulsão.** "MHEV", "HEV" e "PHEV" do nome
   da versão entravam como valor da coluna de propulsão. Isso produzia "MHEV +
   Combustão" para o Stonic, que na coluna é Híbrido. Separei `tipo_propulsao`
   (a coluna) de `marcador_nome` (o nome).
3. **Motor casando com números de emissão.** O padrão de cilindrada ("0,013")
   casava com números depois da trinca, e linhas com o motor quebrado em outra
   linha eram descartadas. Passei a localizar a trinca primeiro e procurar o
   motor só antes dela. Sem motor, o modelo vai até a transmissão. Também
   aceitei "TF200" (motor da Fiat) e a transmissão quebrada "A- 9". As três
   correções recuperaram 131 linhas (de 12.023 para 12.154), entre elas a do
   Leapmotor C10 REEV.
4. **Extração sem cache da parte lenta.** Interrompi a primeira corrida
   completa e reorganizei a ferramenta: o texto de cada página fica em cache
   (`logs/cache_pbe/`) e a interpretação, que é instantânea, roda sobre ele.
   Sem isso, cada ajuste no leitor custaria 25 minutos de releitura.
5. **Página comprimida gravada como binário.** O primeiro download da Exame
   veio comprimido. Acrescentei `--compressed` e baixei de novo.
6. **Linhas "reais" inventadas nos testes.** Escrevi três linhas de teste à mão
   (Stonic, C10 REEV, Defender) e o docstring dizia que eram reais. Troquei
   todas por linhas copiadas do texto extraído, e o docstring diz quais são
   construídas.
7. **Prefixo casando produto errado.** "C4 LOUNGE" caía na chave C4. Corrigido
   com apelido. Os apelidos levaram o casamento de 288 para 300 modelos e
   tiraram falsas ausências (Etios, Up, SpaceFox, Yaris).
8. **Teste obsoleto.** Um teste usava `mhev` como exemplo de valor inválido;
   com a sua decisão ele passou a ser válido. Troquei o exemplo e acrescentei
   testes para `mhev`→`parcial` e para a regra S11.

---

## 5. O que ficou em aberto

- **A aba `a_adjudicar`**: 164 linhas.

| motivo | linhas |
|---|---:|
| PBE diverge | 71 |
| ausente no PBE (entre os 241 maiores) | 57 |
| origem sem fonte datada | 32 |
| fonte de origem ajusta data | 21 |
| fonte de origem contradiz | 10 |

  Uma linha pode ter mais de um motivo.
- **Origens sem fonte datada**, em ordem de volume. É trabalho seu, ou de outra
  rodada: Nissan Versa (a fonte não tem o mês), Frontier, BYD Song (inconclusivo),
  Peugeot 207 Sedan, Renault Clio Sedan, Kia K2500, Peugeot 307, Outlander (fonte
  sem data), Mégane, Mégane GT, Peugeot 308, Citroën C4L, C4, Boxer, Symbol,
  Chery Tiggo, Sprinter 313, Grand Vitara, Jumper, Partner, C4 Picasso, 307
  Sedan, 207 SW (fonte sem data), Titano, Lifan X60, Hafei Ruiyi, RAV4, Sprinter
  311, C180, BYD Yuan, Hafei Towner, BMW 330E.
- **Outras pendências que a busca deixou à vista:**
  - BMW X1, primeira geração: ainda não sei se foi montada em Araquari
    (2014-2016). A fonte data a segunda geração em 2016-03.
  - A interrupção e a retomada da Audi no Paraná depois de 2020.
  - Os anos do Clio em São José dos Pinhais.
  - O início efetivo do QQ nacional e do Lancer nacional.
  - A data da montagem do King e do Song Pro em Camaçari.
- **Chaves que agregam dois produtos** (OUTLANDER com o Outlander Sport,
  DISCOVERY com o Discovery Sport): questão de `regras.csv`, adiada pela
  Parte 0.
- **Tags:** `rodada-3` e `rodada-4` seguem pendentes com você. Tento a
  `rodada-5` ao fechar; se der 403 de novo, fica com você também.
- **Fase 2**: não começada, de propósito.

## 6. Conferência

- 219 testes passando, 42 a mais que no fim da rodada anterior: o leitor do PBE
  com linhas reais, o mapeamento, o casamento, a comparação e a regra contra
  citação inventada. Pyflakes limpo.
- `validacao.md` e `CATALOGO.md` foram regerados sobre a árvore limpa depois do
  commit do trabalho.
- Outros arquivos da rodada:
  - ESPEC §3 atualizada, com registro datado;
  - ABVE em `config/fontes_candidatas.csv`, e o PBE marcado como adquirido;
  - dicionário com a regra do `mhev` e a limitação da transição flex.
