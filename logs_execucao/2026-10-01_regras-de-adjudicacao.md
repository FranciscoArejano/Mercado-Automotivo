# Registro de execução — regras de adjudicação, qualidade da fonte e montagem local

01/10/2026. Branch `claude/new-session-rs2chd`. Este registro vai no mesmo push
do trabalho que ele descreve. Não é a fase 2: nada foi gravado em
`dados/processado/`.

## A conta que importa

| | linhas | unidades |
|---|---:|---:|
| `a_adjudicar` que você recebeu | 164 | |
| … depois das correções desta rodada (seção 5, item 3) | 163 | 12.972.416 |
| **saíram por regra** | **33** | **4.556.505** |
| — só P1 | 15 | 2.003.893 |
| — só P2 | 11 | 1.347.645 |
| — só O2 | 2 | 451.074 |
| — P1 e O1 | 2 | 577.254 |
| — P2 e O1 | 2 | 85.345 |
| — P1 e P2 | 1 | 91.294 |
| **ficaram** | **130** | 8.415.911 |
| — com parte já decidida por regra | 33 | 991.751 |
| **entraram** (O3: leitura apoiada só em fonte fraca, e outras; seção 2.6) | **24** | 2.763.237 |
| **`a_adjudicar` agora** | **154** | 11.179.148 |

- Fora da fila, as regras decidiram mais seis linhas que não estavam nela
  (O1: Cruze Sedan e Cruze HB argentinos, Space Fox, Livina, Yaris Cross,
  Triton). No total, 39 linhas estão decididas só por regra.
- A fila caiu pouco em linhas, mas cada linha que ficou diz agora por que
  nenhuma regra a decidiu. E 24 linhas entraram porque a O3 manda para você o
  que antes eu aceitava com fonte fraca.

Decisões por regra (cada linha conta uma vez por regra, inclusive as parciais):
P1 em 33 linhas, P2 em 27, P3 em 0, O1 em 16, O2 em 2. Tudo está na aba
`resolvido_por_regra`, com o valor antes e depois, a evidência e a ressalva.
Nada some.

---

## 0. Correções registradas

- **Afirmação factual vinda de você é hipótese a verificar, não instrução.**
  - Fica registrado, como você pediu, a propósito das tabelas "máscara" do PBE
    de 2025 e 2026.
  - É o que continuo fazendo nesta rodada. Um dos seus exemplos de P1 estava
    errado, mas por culpa minha, não sua (item seguinte).
- **O "Sportage híbrido" da sua lista de P1 era erro meu.** O Kia Sportage
  tem "TMHEV" no nome da versão, turbo híbrido leve. Meu leitor do PBE só
  reconhecia "MHEV", então o Sportage saía como Híbrido pleno, e o meu
  registro anterior o chamou de híbrido.
  - Corrigi o leitor; o teste usa uma linha construída.
  - Agora a P1 acrescenta `mhev` ao Sportage, não `hev`.
- **A guarda contra citação inventada continua valendo para tudo que entrou
  depois da sua conferência de 77 de 77.**
  - São 80 linhas em `origem_fontes.csv` (três segundas fontes novas) e 13 em
    `montagem_fontes.csv`.
  - Todas passam pelo teste de trecho literal, hash e URL.

---

## 1. O que ficou na fila, por motivo

Uma linha pode ter mais de um motivo, então as linhas abaixo somam mais de 154:
58 só de propulsão, 75 só de origem e 21 com os dois.

| motivo | linhas | unidades |
|---|---:|---:|
| ausente no PBE: o modelo não aparece em ano nenhum | 39 | 2.480.725 |
| O3: leitura apoiada só em fonte fraca | 45 | 4.278.962 |
| origem sem fonte (caso que a rodada anterior mandou buscar) | 29 | 974.312 |
| P1 não decide: Híbrido do PBE sem HEV no nome (hev ou mhev?) | 18 | 1.603.165 |
| O3: fonte contradiz | 10 | 904.315 |
| P2 não decide: combustão com menos de 12 meses antes do PBE | 9 | 182.416 |
| O3: fonte inconclusiva | 7 | 555.928 |
| P3 não decide: Híbrido contra `mhev` | 6 | 630.779 |
| P2 não decide: tipo eletrificado ausente do PBE | 5 | 161.818 |
| P1 não decide: ano dividido entre duas vigências | 2 | 17.120 |
| P1 não decide: combustão só das tabelas sem coluna | 2 | 9.555 |
| O2 não decide: data sem mês (Jimny) | 2 | 18.008 |
| O2 não decide: plano, não evento (QQ) | 2 | 25.793 |
| O1 não decide: complementa sem cobrir a vigência (Pajero) | 1 | 194.310 |
| ausente no PBE: só em outros anos (Cruze Sedan 2011-2016) | 1 | 114.582 |
| propulsão sem proposta e ausente do PBE | 1 | 16.379 |

---

## 2. Como cada regra foi aplicada

O texto de cada regra, como foi aplicada e um exemplo estão em
`config/regras_adjudicacao.csv` e na aba `regras_adjudicacao`. Abaixo, onde eu
precisei interpretar.

### 2.1 P1 — o PBE acrescenta

Aplicada a cada tipo em "só no PBE". Em cinco situações a evidência do PBE é
um artefato conhecido, e a linha vai para você em vez de a regra acrescentar:

1. **`Híbrido` sem HEV no nome da versão.** O PBE rotula híbrido leve como
   Híbrido; o Stonic MHEV, o Forester MHEV e o Sportage TMHEV estão lá assim,
   com o nome dizendo. Então o rótulo sozinho não escolhe entre `hev` e
   `mhev`, que é a premissa da sua P3.
   - Os casos: Renegade, Toro e Commander "HYB" de 2026; os 208 e 2008
     "HYBRID"; A3 e A3 Sedan, Classe C, Classe E, CLA, GLC, X6, XC40 B4,
     Defender, Discovery, Range Rover, 911 e GS4 (18 linhas).
   - Só o Carnival (CARNIVAL HEV EX/LX/SX) passa, e ganha `hev`.
   - **Leitura literal da P1**, `hev` de qualquer Híbrido: 12 linhas sairiam da
     fila (1.329.486 unidades). Contei, mas não apliquei. Pelo meu
     conhecimento, quase todas são híbridos leves de 48 V. Isso é hipótese, não
     fonte.
2. **Ano dividido entre duas vigências.** Cada ano do PBE vai para a vigência
   com mais meses nele. O PBE de 2016 do Compass lista a segunda geração, flex
   e diesel, e caiu na vigência da primeira (8 meses contra 4). A P1 literal
   acrescentaria flex e diesel ao Compass americano a gasolina.
3. **Combustão que só aparece nas tabelas sem coluna de propulsão (até 2020),
   quando a proposta tem eletrificado.** Ali, híbrido sem HYBRID no nome sai
   como gasolina. A P1 literal acrescentaria gasolina ao Prius.
4. **Combustão de versão cujo nome diz híbrido.** O PBE de 2026 põe RAV4 S
   HYBRID e SX HYBRID em Combustão.
5. **`Híbrido` contra `mhev` da proposta.** É da P3, não da P1.

Seus exemplos:

- **L200 flex, HR-V a gasolina e Compass (2ª geração) a gasolina:** saíram da
  fila.
- **Kangoo elétrico:** a P1 acrescenta `bev` nas duas chaves. A de automóveis
  saiu; a de comerciais leves fica pela origem (O3).
- **Outlander diesel:** a P1 acrescenta flex e diesel. A linha fica pelo
  `phev` da proposta, que o PBE não mostra, e pela origem.
- **Tiggo 7 plug-in:** a P1 acrescenta `phev`. A linha fica pela P3.
- **Sportage:** sai com `mhev`, não `hev` (seção 0).

Decisões da P1 para você olhar, porque o tipo veio de outro produto sob o
mesmo nome:

- **Mustang `+bev`:** veio do MUSTANG MACH-E GT. O painel não tem chave
  Mach-E, então ou a Fenabrave publica o Mach-E dentro de MUSTANG, ou o
  casamento está juntando dois carros.
- **Outlander flex e Discovery flex:** vieram do Outlander Sport e do
  Discovery Sport. São as duas chaves que já apontei como agregando dois
  produtos; a questão é de `regras.csv`, adiada pela Parte 0.
- **Proposta vazia:** em três linhas a P1 preencheu a propulsão inteira só
  pelo PBE, todas com ressalva. São o i20 (2026) e o Tiggo 2 (2021), que ficam
  flex, e o Jetour T2, que fica `phev`.

### 2.2 P2 — o que o PBE não pode ver

A proposta não data cada tipo, então a regra olha a vigência:

- **Vigência inteira antes de 2009** (o PBE não existia): mantém tudo. São 4
  linhas, sem ressalva.
- **Vigência inteira antes do primeiro ano do modelo no PBE:** mantém tudo.
  São 12 linhas, mas com ressalva. O PBE já existia em parte da vigência e não
  listou o modelo. A regra mantém pelo texto, mas a razão dela ("o PBE não
  tinha como registrar") não vale ali.
  - Em vários casos o "primeiro ano" é de outra vida do nome: Captiva 2008-2016
    contra o Captiva de 2026, Blazer, Sonic, Megane.
  - As linhas: Tracker 2003-2009, Cruze HB 2012-2016, Captiva, X1 2010-2014,
    Megane, 320i 2008-2014, Sonic 2012-2014, Blazer, J3, Jimny 2003-2011, Lifan
    X60 e Edge.
  - Cinco delas dependem disso para sair da fila: Cruze HB 2012-2016 (com a
    O1), Captiva, Blazer, J3 e Edge. As outras ficam por outro motivo.
  - Se você preferir a leitura estrita (só antes de 2009), essas cinco voltam.
- **Pelo menos 12 meses de vigência antes do primeiro ano do modelo no PBE:**
  mantém os tipos de combustão, com ressalva de condição necessária, não prova.
  São 11 linhas: EcoSport diesel (o seu exemplo), Ranger flex, Sportage
  diesel, Sorento diesel, Evoque 2011-2016 diesel, Freelander diesel, J3 Turin
  flex, Panamera diesel, e as parciais Lancer flex, C4 Picasso flex e Cayenne
  diesel.
  - O limite de 12 meses é escolha minha. Sem ele, o Fluence manteria
    "gasolina" por 3 meses de 2010, e o Fluence brasileiro sempre foi flex.
- **Tipo eletrificado ausente do PBE:** vai sempre para você (5 linhas).
  - São o `bev` do 2008, o `phev` do Outlander e do A3, e o `hev` do Tank 300
    e do Cayenne.
  - O `phev` do Range Rover saiu desta lista com a correção do marcador PHEV
    (seção 5, item 2).
  - O PBE existe desde 2009, e quase toda a eletrificação é posterior. Não há
    "anterior ao PBE" plausível para eles.
- **Modelo que nunca aparece no PBE:** não há primeiro ano, e a regra não se
  aplica. Ficam 39 linhas (Agile, Corsa Sedan, Meriva, Astra, Vectra, Parati…).

### 2.3 P3 — híbrido leve

- **Nenhuma linha resolvida, por construção.** Onde o nome da versão declara
  híbrido leve (MHEV, TMHEV), o mapeamento já dá `mhev`, e a linha nem
  diverge.
- **Seis linhas vão para você:** Pulse e Fastback "HYB", Tiggo 5X e Tiggo 7
  "PRO H", Arrizo 6 "PRO H" e Stonic 2022 (STONIC LX/SX/GT sem MHEV no nome).

### 2.4 O1 — fonte forte que concorda

- **16 decisões, todas `confirma`.** Compass, Evoque (as duas vigências,
  comunicado da JLR), Livina (comunicado da Nissan) e Cruze, pela Motor Show.
  Tiggo 5X, 7 e 8, Eclipse Cross, Triton, Yaris Cross e Daily, pela Autodata.
  Space Fox, pelo AutoPapo.
- **Nenhuma `complementa` passou.** Exigi que a fonte forte cobrisse a
  vigência inteira, porque "aceitar o complemento" muda o valor.
  - O Pajero (Autodata: Pajero Sport importado da Tailândia em 2024) não
    cobre 2003-2025 e entrou na fila.
  - Haval H9 e Poer, que a fonte da GWM cobriria, estão fora do universo de
    origem (seção 2.6).

### 2.5 O2 — fonte forte que ajusta a data

- **Só o Kicks passa.** A Motor Show dá o início em Resende em 2017-04. A
  vigência importada passa a terminar em 2017-03 e a nacional a começar em
  2017-04, em `decisao_por_regra`.
- **Os outros não passam:**
  - Civic, GLA, Versa, Tracker, Classe A e 208 têm só fonte fraca (O3);
  - Jimny tem só o ano;
  - QQ é plano.

### 2.6 O3 — sempre humano, e o universo de origem

- **Universo das regras de origem:**
  - as linhas que a rodada anterior mandou buscar fonte (troca sem data,
    `ambos`, origem `media`/`baixa` entre os 241 maiores);
  - mais as que têm fonte que contradiz ou ajusta a data, que iam para a fila
    de qualquer jeito.
  - Fora disso nada muda. Uma linha `alta` confirmada pela Garagem360 (Fiesta)
    não precisava de decisão antes e não precisa agora.
- **As 24 linhas que entraram:**
  - 21 são `confirma` ou `complementa` apoiadas só em fonte fraca, que a
    rodada anterior deixava fora da fila por terem data. Exemplos: Montana
    (GM Authority), Polo Sedan e Fiesta Sedan (Garagem360), March (Comprecar),
    Focus (Tribuna PR), os furgões do Uruguai (autoblog.com.uy).
  - O Clio, que nem tem origem proposta, estava fora da fila só porque tinha
    fonte datada. Era um buraco da rodada anterior, e a O3 o fecha.
  - O X1 2014-2026 tem leitura inconclusiva.
  - O Pajero é o caso da O1 acima.
- **Uma rodada de segunda fonte forte para as 45 linhas de "só fonte fraca"
  tiraria da fila as que a encontrassem.** Não fiz: você pediu segunda fonte
  só para `contradiz`.

---

## 3. Qualidade da fonte

### 3.1 A coluna `tipo_fonte`

Está em `origem_fontes.csv`, calculada de `config/tipo_fonte_dominio.csv`, que
é a proposta para você editar. Depois de editar, rode
`python src/ferramentas/origem_fonte.py --tipos`. Um teste falha se a coluna
estiver defasada ou se algum domínio citado não tiver tipo.

As 80 citações:

| tipo | citações |
|---|---:|
| oficial | 7 |
| imprensa_especializada | 30 |
| imprensa_geral | 16 |
| blog_agregador | 27 |

Julgamentos meus que você pode querer mudar:

- **Revista automotiva de consumo** (Motor Show, Revista Carro, AutoPapo,
  Parabrisas): 14 citações, classificadas como `imprensa_especializada`, com
  subtipo próprio.
  - Se o critério for só imprensa de indústria (Autodata, MarkLines,
    AutoIndústria), elas são `imprensa_geral`.
  - **Sensibilidade:** rebaixá-las devolve 6 linhas à fila (829.561 unidades):
    Kicks (as duas, O2), Cruze HB (duas), Cruze Sedan 2016-2026 e Space Fox.
  - Golf, Q3, A3 Sedan e ASX, que contradizem pela Motor Show ou pela Carro,
    passariam a "fonte única e fraca".
- **Comprecar** como `blog_agregador`, embora os textos citados reproduzam
  comunicados da Mercedes e da Nissan.
- **Vrum** (seção automotiva de jornal geral) como `imprensa_geral`.

### 3.2 Segunda fonte para as contradições fracas

Mesma regra contra citação inventada: página guardada, trecho literal, teste.

- **VW Jetta.** A primeira fonte era a legenda de foto da Garagem360 ("VW
  Jetta (2014 a 2018) | Foto: Divulgação").
  - A segunda, MarkLines (30/09/2014, `imprensa_especializada`): "Production
    will start in the first half of 2015. […] The domestic production model will
    complement the current import from the Puebla plant in Mexico".
  - É plano, não produção comprovada, e sustenta `ambos` a partir de 2015, não
    `nacional` de 2014 a 2018.
  - A Motor Show de 2014 diz o mesmo plano ("no segundo trimestre de 2015");
    guardei a página e não a citei, por ser redundante.
  - A linha segue `contradiz`, agora com fonte forte e não "fonte única e
    fraca". Não achei fonte que confirme a produção efetiva nem o período.
- **Peugeot 2008.** A primeira fonte, Garagem360 (14/11/2023), dava o fim em
  Porto Real em 15/11/2023.
  - A segunda, Autodata (25/04/2024): "A geração anterior deixará de ser
    produzida em Porto Real". Fala no futuro em abril de 2024.
  - As duas confirmam a troca para a Argentina, mas **conflitam no mês da
    fronteira**. Fica em aberto, com você.
- **Hyundai ix35.** A primeira fonte era a Exame (08/11/2013,
  `imprensa_geral`).
  - A segunda, Autodata (28/09/2017): "fabricado pela empresa em Anápolis,
    GO, desde 2013". Confirma o ano.
  - Segue `contradiz`, porque a proposta tem `ambos` na vigência inteira e a
    fonte pede divisão. Agora com fonte forte.
- **Nenhuma contradição depende mais só de fonte fraca.** O 206 SW
  (inconclusivo, só Garagem360) leva "fonte única e fraca". Não busquei
  segunda fonte para ele, porque é `inconclusivo`, não `contradiz`.

---

## 4. Montagem local

A decisão aplicada é a sua: coluna `montagem_local` (`fabricacao`, `ckd`,
`skd`, `desconhecido`), separada de `origem_producao`, com padrão
`desconhecido`.

- **Fontes:** `dados/referencia/montagem_fontes.csv`, 13 linhas de 6 páginas.
  - Cada linha traz o trecho copiado e o período que a fonte sustenta, que é
    leitura minha, explicada na observação.
  - BYD e Land Rover são páginas novas desta rodada.
  - As de Spark, furgões do Uruguai, GWM e Nissan já estavam guardadas. **Abri
    as seis de novo hoje, ao vivo, e o trecho de cada uma ainda está lá.**
- **Regras de aplicação** (minhas, para revisar):
  - **Só em linha não `importado`.** A montagem SKD dos furgões no Uruguai é do
    país de origem; para o Brasil eles chegam inteiros, então não é montagem
    local.
  - **BYD (Dolphin Mini, King, Song) e Haval H6:** a linha é `importado` na
    proposta, e a divisão da vigência na data da produção local está pedida em
    `a_adjudicar` (O3, contradiz). Quando você dividir, a parte nacional recebe
    `skd` (BYD) ou `fabricacao` (GWM).
  - **Cobertura parcial também muda o valor**, e `montagem_cobertura` diz
    quanto a fonte cobre. **Nenhuma fonte cobre uma vigência inteira**:
    - o CKD do Evoque é "na fase inicial", sem data de fim;
    - a GWM declara fabricação completa "hoje", em agosto de 2026;
    - a Nissan declara o ciclo completo no primeiro ano de Resende.
- **Resultado:** 6 linhas com modo, todas com cobertura parcial.
  - **`fabricacao`:** March e Versa (Resende), Haval H9 e Poer (Iracemápolis);
  - **`ckd`:** Evoque 2016-2026;
  - **`skd`:** Spark EUV.
- **Ficaram `desconhecido` 432 das 438 linhas.** Entre as de origem `nacional`
  ou `ambos`, ficaram 164 de 167, ou 86,19% do volume classificado.
- **Ressalva:** a regra de montagem não exige fonte forte, e a maioria destas é
  fraca. InvestNews, Vrum e Gazeta do Povo são `imprensa_geral`; Comprecar e
  autoblog.com.uy são `blog_agregador`; só a GWM é `oficial`.

---

## 5. Erros cometidos e como foram corrigidos

1. **TMHEV não reconhecido** (seção 0). Corrigido no leitor, com teste;
   `pbe_versoes.csv` regerado.
2. **PHEV rotulado Híbrido virava `hev`.** O PBE põe plug-in em Híbrido em
   alguns anos (Range Rover PHEV em 2021, Jaguar F-Pace PHEV em 2022).
   - Meu mapeamento só deixava o nome mandar para MHEV e REEV. Agora PHEV
     também manda (`config/pbe_propulsao.csv`, nova regra 3).
   - "PHEV404" (Range Rover Sport, potência colada) passa a contar como PHEV.
   - Teste com a linha literal da tabela de 2021. Mudaram 8 linhas de
     `pbe_versoes.csv`.
3. **O GR Corolla casava com o Corolla.** O PBE escreve "COROLLA HB GR", e o
   prefixo COROLLA o levava para a chave do sedã, acrescentando gasolina.
   - O painel tem chave própria, TOYOTA/COROLLA GR.
   - Apelido novo em `config/pbe_modelos.csv`. O Corolla 2019-2026 passou a
     concordar com o PBE: é a linha que fez a fila ir de 164 para 163 antes
     das regras.
4. **A primeira versão da P1 era literal.**
   - Ao ler a lista de decisões, achei Compass 1ª geração com flex e diesel,
     Prius com gasolina e RAV4 com gasolina, todas erradas.
   - As guardas 2 a 4 da seção 2.1 vieram daí. Cada uma tem teste com o caso
     que a motivou.
5. **A primeira versão da montagem marcava linhas `importado`.**
   - O período "2016" do CKD do Evoque (só o ano) tocava a vigência importada
     de 2011-2016, e BYD e Haval H6 recebiam o modo na vigência importada.
   - Corrigido: montagem só em linha não importada.
6. **Buraco na fila da rodada anterior.** O Clio, sem origem proposta, estava
   fora de `a_adjudicar` porque tinha fonte datada (inconclusiva). Entrou
   agora.
7. **BYD em "junho de 2025".** O resumo de uma busca dizia que Camaçari
   começou em junho de 2025. A página (Canaltech) mostra que era plano: "BYD
   confirma produção nacional do Dolphin Mini para junho de 2025". A
   inauguração foi em outubro de 2025 (Autodata, InvestNews). Guardei a página
   e não a citei como início.
8. **Página não aproveitada:** InfoMoney sobre os 15 milhões de Anchieta, que
   não menciona o Jetta. Guardada, não citada. MovimentoEconômico (BYD)
   bloqueou o acesso; nada gravado.

---

## 6. O que ficou em aberto

- **As 154 linhas de `a_adjudicar`.**
  - `motivo` diz por que cada regra não decidiu.
  - `decisao_por_regra` traz o que já foi decidido nas parciais.
  - `propulsao_apos_regras` e `origem_apos_regras` mostram o valor depois
    das regras.
- **Questões para você:**
  1. **P1 literal ou com a guarda do Híbrido sem HEV?** A guarda segura 12
     linhas que sairiam com `hev`.
  2. **Revista automotiva de consumo:** imprensa especializada ou geral? São
     6 linhas.
  3. **P2 em modelo que o PBE, já existindo, não listou:** fica pelo texto ou
     cai? Cinco linhas voltariam.
  4. **Montagem:** cobertura parcial basta para mudar o valor? E linha
     `importado` deve ter um quinto valor (`nao_se_aplica`) em vez de
     `desconhecido`?
     - Hoje 244 linhas importadas contam como `desconhecido`; isso infla a
       contagem.
  5. **Segunda fonte** para as 45 linhas de "só fonte fraca"?
  6. **Antes da fase 2:** como ela lê `decisao_por_regra` junto de
     `decisao_humana`, e o que acontece com as linhas que nunca estiveram na
     fila.
     - O `leia_me` diz desde a fase 1 que "linha com decisão vazia não entra
       na fase 2", e isso não combina com uma fila que é só parte do
       rascunho.
     - Não mudei essa regra: a decisão é sua.
- **Fronteira do 2008 em Porto Real** (novembro de 2023 ou depois de abril de
  2024) e **período do Jetta em Anchieta:** fontes em conflito ou só plano.
- **Tags:** `rodada-3`, `rodada-4` e `rodada-5` seguem com você. Tento a
  `rodada-6` ao fechar; se falhar como as outras, fica com você também.
- **Fase 2:** não começada, de propósito. Parei aqui.

---

## 7. Conferência

- **Testes:** 243 passam (eram 219 no fim da rodada anterior). Os novos cobrem:
  - as regras, com um teste por regra e por guarda;
  - o tipo de fonte;
  - as fontes de montagem;
  - o marcador PHEV.

  Pyflakes limpo.
- **Rascunho:** `saidas/classificacao_rascunho.xlsx`.
  - Abas novas: `resolvido_por_regra`, `montagem_local` (casos e, abaixo, a
    contagem de `desconhecido`), `regras_adjudicacao`, `contas_das_regras` (a
    tabela do início e as duas sensibilidades), `montagem_fontes` e
    `tipo_fonte_dominio`.
  - `a_adjudicar` refeita.
  - Na aba `classificacao`, colunas novas: `regras_aplicadas`, `pendencias`,
    `propulsao_apos_regras`, `origem_apos_regras`, `origem_tipos_fonte`,
    `montagem_local`, `montagem_cobertura`, `montagem_fonte_url` e
    `decisao_por_regra`. A proposta original está intacta.
- **Em CSV:** `saidas/classificacao_regras_contas.csv` e
  `saidas/classificacao_resolvido_por_regra.csv`.
- **Dicionário** com a coluna de montagem e a adjudicação por regra.
- **`validacao.md` e `CATALOGO.md`** regerados sobre a árvore limpa depois do
  commit do trabalho.
