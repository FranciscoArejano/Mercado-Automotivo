# Registro de execução — classificação de modelo (fase 1) e catálogo

30/09/2026. Branch `claude/new-session-rs2chd`. Este registro vai no mesmo commit
do trabalho que ele descreve.

## Em uma frase

O rascunho de classificação está em `saidas/classificacao_rascunho.xlsx`, com
438 linhas (modelo-vigência) para os 409 modelos acima de 1.000 unidades. Nada
foi gravado em `dados/processado/`: **parei antes da fase 2**, como pedido. O
`CATALOGO.md` agora é gerado pela etapa 10 do pipeline. No caminho encontrei e
corrigi quatro defeitos meus de rodadas anteriores (seção 3). O que você precisa
decidir está na seção 4.

---

## 1. Tarefa 1 — classificação de modelo, fase 1

### 1.1 O que investiguei antes de propor

- **Escopo.** Refiz a conta no painel: 409 modelos têm volume total acima de
  1.000 unidades, e respondem por 99,88% do volume. Os outros 524 vão para a
  aba `nao_classificados`. Desses, 8 são chaves que só têm linhas com zero
  unidades (GM/BONANZA, LEXUS/IS 350 e outras). A primeira versão do script
  perdia essas 8, porque montava a lista a partir dos meses com unidades.
  Corrigi, e agora 409 + 524 = 933.
- **O que a fonte já dá: carroceria.** A Fenabrave põe cada linha num
  sub-segmento. Em 12 dos 13 do segmento de automóveis e nos 6 de comerciais
  leves, o sub-segmento é carroceria (Hatch, Sedan, SUV, Pick-up, Furgão,
  Monocab/Grandcab, SW, Sports). O 13º, **"Veículos de Entrada", não é
  carroceria. É faixa de preço.** Onze modelos do escopo só aparecem ali:
  Gol, Uno, Palio, Celta, Mobi, Kwid, Up, Clio, 206, 207 e Etios HB. Por isso
  a regra S09 o ignora, e esses modelos recebem carroceria por conhecimento,
  marcada como tal.
- **O que a fonte não dá: propulsão e origem.** Procurei marcadores de
  propulsão no próprio nome do modelo. Achei **só quatro regras inequívocas**,
  e elas cobrem 4 modelos (0,02% do volume): prefixo `E-` (JAC/E-JS1), `EM-I`/`DM-I`
  (GEELY/EX5 EM-I), BMW com três dígitos + `E` (330E) e Volvo `EX`/`EC` + dígito
  (EX30). A fonte não escreve "HYBRID", "HEV" ou "PHEV" em nenhum dos 409 nomes.
  **Consequência que você precisa ter em mente ao adjudicar: 99,9% do volume
  tem a propulsão proposta por conhecimento meu, e 98,7% tem a origem proposta
  por conhecimento meu.** Nessas duas colunas, `alta` quer dizer "não tenho
  dúvida razoável", não "verificado".

### 1.2 Decisões e por quê

1. **Três fontes de proposta, em ordem de precedência e sempre declaradas em
   `fonte_da_proposta`**:
   - carroceria: sub-segmento da fonte → conhecimento → vazio;
   - propulsão: regra por nome → conhecimento → vazio;
   - origem: conhecimento → vazio.

   Quando conhecimento e fonte discordam na carroceria, o valor que fica é o
   da fonte, com confiança rebaixada a `media` e a discordância anotada. É a
   fonte que um artigo cita.
2. **Carroceria da vigência = o sub-segmento com mais unidades nela** (regra
   S10). Se uma segunda carroceria tem 10% ou mais, a linha cai para `media`,
   com a divisão na observação. Também cai para `media` quando menos de 10% das
   unidades aparecem em sub-segmento de carroceria: F-150, Chana SC, Daily
   35S14 e Hafei Zhongyi Van só foram classificados pela fonte em poucos
   meses. Nos demais, entraram só pelo ranking, que não tem sub-segmento.
3. **As regras ficam em `config/regras_classificacao.csv`, cada uma com um
   exemplo.** As de nome estão implementadas em `src/comum/classificacao.py`,
   uma função por id. Um teste confere que o CSV e o código têm os mesmos ids
   e que o exemplo de cada linha dispara a regra.
4. **A proposta por conhecimento é um arquivo versionado de entrada**:
   `dados/referencia/classificacao_proposta_assistente.csv`, uma linha por
   modelo ou vigência, com confiança **por atributo** e observação. Fica
   separada do código para que dê para ver e corrigir o que eu disse sem ler
   Python.
5. **Vigência só onde eu sei de uma mudança.** Foram 25 modelos com mais de uma
   vigência (54 linhas): Corolla ganha híbrido em 2019-10; Civic vira importado
   em 2022; Compass passa a nacional em 2016-09; os BMW de Araquari a partir de
   2014-10; Classe C e GLA em Iracemápolis de 2016 a 2020; GM/SONIC, que são
   dois produtos com onze anos de buraco; e outros. O script confere que as
   vigências de um modelo não se sobrepõem e cobrem todo mês com unidades. As
   datas que dei como aproximadas estão ditas na observação.
6. **A transição para o flex (2003–2006) não foi dividida em vigências.** Os
   103 modelos em que isso importa saem com o conjunto `gasolina+flex` na
   vigência inteira. Datar o lançamento flex modelo a modelo seria chute
   disfarçado de precisão. Fica como questão (seção 4).
7. **`confianca` = o pior dos três atributos.** As três colunas `confianca_*`
   dão o nível de cada um. Pus as três porque uma linha com carroceria `alta`
   e origem `baixa` precisa de atenção em lugar diferente de uma com tudo
   `media`.
8. **Vazio só quando declarei "não sei".** Um teste exige que todo valor vazio
   no rascunho corresponda a confiança `baixa` explícita na proposta. Isso
   separa ignorância de esquecimento (ver erro 3.5).
9. **Colunas além das pedidas**, todas para a adjudicação:
   - `posicao`: ordem por volume;
   - `unidades_na_vigencia`: as vigências particionam `unidades_totais`;
   - `sub_segmentos_fonte`: como a fonte distribuiu as unidades;
   - `observacao`;
   - `confianca_*`.
10. **Não é etapa do pipeline.** O pipeline roda sozinho e sobrescreve, e este
    arquivo vai receber a sua letra. A ferramenta é
    `src/ferramentas/classificacao_rascunho.py`, e ela **recusa sobrescrever**
    um rascunho que já tenha qualquer `decisao_humana` preenchida, salvo com
    `--sobrescrever`.
11. **Limitação registrada no dicionário** (`saidas/painel_dicionario.md`,
    "Dimensões paralelas"). A fonte não separa unidades por versão: a propulsão
    é conjunto, e somar os modelos `parcial` como eletrificados superestima a
    eletrificação. A mesma nota está na aba `leia_me`.

### 1.3 Resumo por nível de confiança

Calculado do rascunho (`saidas/classificacao_resumo.csv`). As vigências de um
modelo particionam o volume dele, então as unidades somam o volume classificado
(57.631.734, ou 99,88% do painel).

**Por modelo-vigência, confiança geral (o pior dos três atributos):**

| nível | modelo-vigências | unidades | % do painel |
|---|---:|---:|---:|
| alta | 173 | 39.551.724 | 68,55 |
| media | 233 | 17.281.123 | 29,95 |
| baixa | 32 | 798.887 | 1,38 |

**Por modelo, tomando a pior vigência de cada um** (409 modelos):

| nível | modelos | unidades | % do painel |
|---|---:|---:|---:|
| alta | 166 | 37.154.510 | 64,39 |
| media | 211 | 19.524.330 | 33,84 |
| baixa | 32 | 952.894 | 1,65 |

**Por atributo** (unidades na vigência, % do classificado):

| atributo | alta | media | baixa |
|---|---:|---:|---:|
| propulsão | 72,19 | 27,71 | 0,10 |
| carroceria | 99,42 | 0,57 | 0,01 |
| origem | 86,96 | 11,69 | 1,35 |

A carroceria é o atributo firme. Dela, 79,9% do volume vem da própria fonte e
20,1% do conhecimento, quase tudo nos onze "Veículos de Entrada", todos
hatch. A
origem é o atributo frágil: 27 modelos ficaram sem proposta (1,3% do volume).
Entre eles estão os Renault Clio, Mégane e Kangoo e os Peugeot Partner e
Boxer, em que não sei separar Argentina, Brasil e França por período.

### 1.4 O que conferir primeiro na adjudicação

Em ordem de volume em jogo:

1. **Origem dos modelos `ambos` e das vigências de produção local.** São 24
   modelos com a troca não datada ou datada só aproximadamente: BYD em
   Camaçari, GWM em Iracemápolis, BMW em Araquari, Mitsubishi em Catalão e CAOA
   em Anápolis.
2. **As propulsões `media` de picapes e SUVs grandes.** Exemplos: a Hilux
   saiu `diesel+gasolina+flex`, mas as versões a gasolina e flex existiram só
   em parte do período; a S10 também tem flex e gasolina em parte da vida.
3. **As 23 carrocerias por conhecimento.** Os de maior volume (Gol, Uno, Palio)
   não têm dúvida; os de comerciais leves sem sub-segmento (Sprinter por
   número, Daily 30-130 e 30S13) têm.

---

## 2. Tarefa 2 — `CATALOGO.md`

### 2.1 O que foi feito

- **`src/etapa10_catalogo.py`**, nova etapa, a última do pipeline. Janela
  efetiva, linhas, meses sem dado, unicidade da chave, contagens de marcação,
  cobertura e, para cada série macro, janela e observações: tudo é calculado
  dos arquivos na hora. A janela de cada série sai dos meses **com valor**, não
  das linhas.
- **Parte A** tem uma seção por produto:
  - `painel`, `painel_bruto`, `painel_canal` e `macro_mensal`;
  - a classificação, que hoje aparece como rascunho, com o número de decisões
    já preenchidas. Quando existir um `classificacao*.parquet` em
    `dados/processado/`, a seção passa a descrevê-lo.
- Na macro, uma linha por série com a coluna `natureza_e_ressalvas` do
  `config/series_macro.csv`. Há ainda uma seção curta de "outros arquivos":
  PDFs, `regras.csv`, mapa de grupos, planilha de controle e relatórios.
- **Parte B** vem de `config/catalogo_usos.csv`, com três colunas por produto
  ou série: `sustenta`, `nao_sustenta` e `ressalvas`. Uma célula vazia aparece
  no catálogo como "(sem texto em `config/catalogo_usos.csv`)", e há teste
  para isso.
- **Parte C** vem de `config/fontes_candidatas.csv`, com a sua tabela
  transcrita literalmente e uma coluna `observacao` vazia para quando uma
  fonte for testada.

### 2.2 Decisões

- **"Commit do dado" na primeira linha = o último commit que alterou os
  caminhos de dado.** Esses caminhos são `dados/processado`,
  `dados/referencia`, o manifesto, `config`, `regras.csv` e o rascunho de
  classificação. Se houver alteração não comitada neles, a linha leva `-sujo`.
  Escolhi isso em vez do `HEAD`, que é o que o `validacao.md` usa, porque o
  catálogo descreve o dado, não o código. Com o `HEAD`, todo commit mudaria o
  catálogo.
- **Sem data de geração no corpo.** Rodar de novo sobre o mesmo dado produz o
  mesmo arquivo, e o catálogo só muda no git quando o dado muda. Um teste
  confere que o `CATALOGO.md` versionado é o que o script produz hoje, sem
  contar a primeira linha. Quem editar `config/catalogo_usos.csv` sem rodar a
  etapa 10 descobre ali.
- **Uma fonte que não pus na Parte C, e sugiro:** uma fonte de emplacamento
  **por propulsão** (a ABVE publica eletrificados por tipo). É a única saída
  para a limitação da seção 1.2, item 11. Não acrescentei porque a tabela é
  sua; se quiser, é uma linha em `config/fontes_candidatas.csv`.

---

## 3. Erros encontrados e corrigidos

Os quatro primeiros são de rodadas anteriores e estavam no repositório.

1. **O pipeline não rodava as etapas 8 e 9 sem argumentos.** O `--ate` tinha
   padrão 7, fixo desde a primeira versão. Quando acrescentei as etapas 8
   (macro) e 9 (canal), não mudei o padrão, e `python src/pipeline.py` pulava
   as duas. Não houve dano no dado, porque rodei as duas à mão, mas uma
   reconstituição "rode o pipeline" teria saído sem macro e sem canal.
   Corrigido: o padrão agora é a maior etapa da lista. Um teste confere que a
   corrida sem argumentos chama todas.
2. **A etapa 8 mandava os subitens do IPCA ao SGS do Banco Central.** Na
   rodada anterior acrescentei os cinco subitens (`ipca_7641` e os outros) ao
   `config/series_macro.csv` por causa da coluna `natureza_e_ressalvas`. O laço
   do SGS lia todas as linhas do catálogo e tentava os cinco, que davam 404. O
   efeito ficou visível no `validacao.md` §11 comitado: "22 séries" em vez de
   17, e cinco linhas `nan`. Em `saidas/macro_series.csv` eram cinco linhas
   "falhou". O `macro_mensal.parquet` **não** foi afetado: rodei a etapa de
   novo e o arquivo saiu byte a byte igual. Corrigido: o laço do SGS pula as
   linhas de outra fonte. Há teste, e ele falha no código antigo.
3. **O resumo da etapa 8 contava como coberto o mês vazio do SIDRA.** O IPCA
   de automóvel usado começa em 2006-07. Antes disso o SIDRA devolve "...", e o
   parquet guardava vazio corretamente, mas o resumo contava a linha e dizia
   "284 meses, 2003-01..2026-08" onde há 242 e 2006-07. Com isso, o
   `validacao.md` §11 dizia "6 séries não cobrem os 284 meses" quando são 7.
   Corrigido e testado no mesmo teste. O `natureza_e_ressalvas` sempre disse
   2006-07; só o resumo mentia. O catálogo novo não depende desse resumo:
   calcula a janela direto do parquet.
4. **Número escrito à mão no dicionário, desatualizado.** O campo
   `marca_recuperada` dizia "Hoje: 8 modelos de 2013-11". É o número da rodada
   da planilha, e o commit daquela rodada diz "8 dos 12". Na rodada seguinte,
   quatro daquelas linhas viraram `duplicata_publicada`, e o dado hoje tem
   **4 linhas**. É o mesmo "4 de 8" que o `validacao.md` já calculava. É
   exatamente o defeito que a tarefa 2 combate. Agora o dicionário conta do
   dado.
5. **Esquecimento na minha proposta: TOYOTA/ETIOS HB saiu sem carroceria.** Ele
   só aparece em "Veículos de Entrada" (249.864 unidades) e eu não pus
   carroceria na linha dele, sem declarar dúvida. Achei ao listar as
   carrocerias `baixa`; corrigi para `hatch`. Acrescentei o teste do item 8 da
   seção 1.2, que pega a classe inteira de erro e falha na versão antiga.
6. **Filtros da aba `questoes`, na primeira versão:**
   - "caminhão leve" diferenciava maiúscula e perdia o Kia K2500;
   - "carroceria discordante" pegava os caminhões leves, porque as duas notas
     dizem "a fonte o põe em";
   - "produção local não datada" pegava a transição flex, pelo "não datada".

   Corrigi os três; as contagens da aba são as finais.

---

## 4. O que ficou em aberto

### 4.1 Para você decidir antes de adjudicar linha a linha (§9.6)

Estão na aba `questoes` do rascunho, com modelos e volume calculados:

| questão | modelos | unidades |
|---|---:|---:|
| **Híbrido leve (MHEV)**: não existe na lista. Pulse, Fastback, Tiggo 5X/7, Arrizo 6 e Stonic saíram só com a propulsão a combustão. Recomendo acrescentar `mhev`. | 6 | 630.779 |
| **REEV** (elétrico com extensor a combustão): Leapmotor C10. Saiu `bev`, com nota. Recomendo `reev`, ou juntar a `phev`. | 1 | 4.793 |
| **Caminhão leve** (HR, Bongo, Delivery Express, Aumark, chassis da Daily e da Sprinter): a fonte põe em Furgões, e a lista não tem o valor. Recomendo `caminhao_leve`. | 17 | 261.262 |
| **Carroceria só por conhecimento**: modelos sem sub-segmento de carroceria. | 23 | 11.583.043 |
| **Carroceria discordante da fonte** (Picanto e SX4 em Monocab, CLC em Sedans Pequenos, DS5 em Sedans Grandes): fica o valor da fonte. | 4 | 52.838 |
| **Carroceria da fonte dividida ou rala**. | 7 | 21.434 |
| **Transição flex não datada**. | 103 | 32.477.613 |
| **Troca sem data ou com data aproximada** (produção local, versão eletrificada). | 24 | 906.737 |
| **Origem sem proposta**. | 27 | 740.615 |
| **Propulsão sem proposta** (modelos de 2025–26 que não conheço e produtos não identificados). | 9 | 38.695 |
| **Um nome, dois produtos** (GM/SONIC, VOLVO/V40, FIAT/UNO...): questão de `regras.csv`, só sinalizada. | 6 | 3.946.478 |
| **Um produto, duas chaves** (CHERY/TIGGO 7 antes de CAOA CHERY/TIGGO 7): idem. | 2 | 12.038 |

Como preencher `decisao_humana` está na aba `leia_me`:

- `ok` aceita a linha;
- `atributo=valor; atributo=valor` corrige só o que for dito;
- `dividir em AAAA-MM` pede nova vigência;
- vazio = não entra na fase 2.

### 4.2 Pendências de repositório

- **Tags.** Na rodada anterior o push da tag `rodada-3` deu HTTP 403, e ficou
  no remoto a branch `teste-permissao-tag`, que também não consegui apagar
  (403). Vou tentar a `rodada-4` ao fechar esta rodada; se der 403 de novo,
  as duas tags e a branch ficam com você.
- **ESPEC §3.** A tabela de produtos ainda lista seis, sem `painel_canal`,
  `macro_mensal`, `CATALOGO.md` e o rascunho de classificação. Todos estão
  versionados (os de `saidas/` e `dados/processado/` pela §10.2; o
  `CATALOGO.md`, na raiz, também), então não há risco de durabilidade, mas a
  tabela está incompleta. Não editei: a ESPEC é sua.
- **Fase 2 da classificação**: gravar a dimensão em `dados/processado/` a
  partir do rascunho adjudicado. Não começada, de propósito.

---

## 5. Conferência

- 177 testes passando (`pytest testes`), contra 142 no commit anterior:
  25 da classificação, 6 do catálogo, 1 da macro e 3 do pipeline (um deles é
  o teste de contrato que passou a cobrir a etapa 10). Pyflakes limpo.
- `validacao.md` e `CATALOGO.md` foram regerados sobre a árvore limpa, depois
  do commit do trabalho, e comitados em seguida.
- O `macro_mensal.parquet` não mudou. `saidas/macro_series.csv` e o §11 do
  `validacao.md` mudaram pelas correções 3.2 e 3.3.
