# Registro de execução — a propulsão no tempo

02/10/2026. Branch `claude/new-session-rs2chd`. Este registro vai no mesmo push
do trabalho que ele descreve.

## Em uma frase

A tabela nova, `classificacao_propulsao_anual.parquet`, dá a cada tipo
eletrificado um ano de entrada. Com ela, o `parcial` de 2018 cai de **8,7% para
0,6%**, e o de 2021 de **19,3% para 5,4%**. A série da ABVE cai entre o piso e
o teto corrigidos em todos os anos de 2016 a 2026.

---

## O uso-teste: antes e depois

Participação de cada nível de eletrificação nas unidades do painel, por ano.

- **Antes** é pelo conjunto da vigência (a coluna que agora se chama
  `eletrificacao_na_vigencia`).
- **Depois** é pela tabela anual (`eletrificacao_no_ano`).
- `nao_classificado` (0,1% a 1,2%) completa os 100%.
- A tabela é gravada a cada execução da etapa 11 em
  `saidas/classificacao_uso_teste.csv`.

| ano | nenhuma antes | parcial antes | total antes | nenhuma depois | parcial depois | total depois |
|---|---:|---:|---:|---:|---:|---:|
| 2015 | 95,9% | 4,0% | 0,0% | 99,1% | 0,8% | 0,0% |
| 2016 | 92,5% | 7,3% | 0,0% | 99,3% | 0,5% | 0,0% |
| 2017 | 91,4% | 8,4% | 0,1% | 99,2% | 0,5% | 0,1% |
| 2018 | 91,1% | **8,7%** | 0,1% | 99,2% | **0,6%** | 0,1% |
| 2019 | 90,3% | 9,4% | 0,2% | 97,1% | 2,7% | 0,0% |
| 2020 | 86,6% | 12,9% | 0,2% | 96,9% | 2,6% | 0,2% |
| 2021 | 80,4% | **19,3%** | 0,1% | 94,3% | **5,4%** | 0,1% |
| 2022 | 78,1% | 21,6% | 0,1% | 88,0% | 11,7% | 0,1% |
| 2023 | 78,1% | 20,3% | 1,4% | 87,9% | 10,5% | 1,4% |
| 2024 | 76,5% | 18,7% | 4,6% | 85,4% | 9,9% | 4,6% |
| 2025 | 73,6% | 19,5% | 6,6% | 78,2% | 14,9% | 6,6% |
| 2026 (jan a ago) | 68,3% | 17,4% | 13,1% | 68,3% | 17,4% | 13,1% |

Reproduzi primeiro a sua série "antes" e ela bateu: 8,71% em 2018 e 19,28% em
2021.

### A série corrigida é plausível?

Cada mudança de patamar tem um evento datado que a explica.

- **2019 (0,6% → 2,7%):** chega o Corolla híbrido flex (vendas desde
  12/09/2019, Revista Carro).
  - O salto está inflado pela resolução anual: o Corolla de 2019 inteiro sai
    `parcial`, inclusive os meses da geração anterior (ver "ano com duas
    vigências", abaixo).
- **2021 (2,6% → 5,4%):** Corolla Cross híbrido (1,8 ponto) e e-208 (0,8).
- **2022 (5,4% → 11,7%):** Compass 4xe (PBE 2022, 3,3 pontos sozinho), Tiggo 8,
  5X e 7 (1,5 juntos) e e-2008 (0,3).
- **2023:** o `parcial` recua (10,5%) e o `total` sobe de 0,15% para 1,4%, com
  BYD (Song Plus, Dolphin) e Haval H6, modelos só eletrificados.
- **2025 (9,9% → 14,9%):** Fastback (2,3 pontos) e Pulse (1,8) híbridos (PBE
  2025).
- **2026:** Toro (2,1 pontos), Renegade (1,5), Yaris Cross (1,4) e Commander
  (0,6).
  - **2026 não muda** entre antes e depois: as vigências terminam em 2026-08,
    e todos os tipos já entraram nesse ano.

O `parcial` corrigido ainda é teto. Uma Compass diesel de 2022 conta como
`parcial` porque a Compass oferecia o 4xe. A fonte não separa unidades por
versão.

### O `total` só mudou em 2019, e para baixo

Foi de 0,16% para 0,03%. O RAV4 tem duas vigências em 2019: só gasolina até
maio, só hev a partir de junho. Num ano com duas vigências, a tabela anual une
os tipos das duas, e o RAV4 de 2019 inteiro vira `parcial`. O piso continua
piso, só mais baixo.

---

## O que foi construído

### A tabela

`dados/processado/classificacao_propulsao_anual.parquet` tem 5.896 linhas, uma
por `(marca, modelo, segmento, ano)` com unidades no painel. É gravada pela
etapa 11, logo depois da dimensão; a lógica está em
`src/comum/propulsao_anual.py`.

| coluna | o que é |
|---|---|
| `propulsao_no_ano` | os tipos oferecidos em algum momento do ano |
| `eletrificacao_no_ano` | pelas regras de sempre; `hibrido_indefinido` e `mhev` nunca levam a `total` |
| `fonte_temporal` | a fonte da entrada mais fraca entre os tipos eletrificados do ano |
| `entrada_dos_tipos` | `tipo=ano fonte` de cada tipo |
| `procedencia_propulsao` | herdada da vigência; com duas vigências no ano, a mais fraca |
| `vigencias` | as vigências com unidades no ano |
| `unidades` | soma do painel no ano |

O ano de entrada de cada tipo, vigência a vigência, fica em
`saidas/classificacao_propulsao_entradas.csv`.

### As regras de entrada

**Combustão** entra no início da vigência, como você pediu.

**Eletrificado**, nesta ordem:

1. **Fonte datada** em `dados/referencia/propulsao_fontes.csv` → `fonte_datada`.
   - Vale lançamento, produção ou presença à venda; `plano` não conta.
   - Onde existe, manda sobre o PBE (sua regra 4).
2. **Primeira tabela do PBE** com uma versão daquele tipo para o modelo →
   `pbe_ano`. Só vale se houver, dentro da vigência e antes da primeira
   aparição, um ano com coluna de propulsão (2021 em diante) em que o modelo
   está na tabela sem o tipo.
3. **Senão**, o início da vigência → `vigencia_sem_datacao`.

**Vigência só com tipos eletrificados:** o primeiro a entrar entra no início da
vigência, marcado `vigencia`. O modelo não vende sem propulsão (Prius, Dolphin,
RAV4 híbrido).

Contagem dos 90 tipos eletrificados (vigência × tipo):

| `fonte_temporal` | tipos | % das unidades eletrificadas (parcial + total) |
|---|---:|---:|
| `pbe_ano` | 35 | 46,9% |
| `vigencia` | 30 | 24,7% |
| `fonte_datada` | 22 | 27,4% |
| `vigencia_sem_datacao` | 3 | 1,1% |

### Decisão: o marcador no nome prova presença, não ausência

Essa decisão estreita a sua regra 2.

Você escreveu que antes de 2021 só o marcador no nome revela eletrificação.
Concordo, mas isso não basta para datar a entrada: datar exige provar que o
tipo **não** estava lá no ano anterior. Uma tabela sem marcador não prova isso,
porque as tabelas antigas nem sempre listam versões. O caso que me fez mudar:

- **Cayenne.** O PBE só mostra o PHEV em 2021, com o marcador. A tabela de 2020
  lista só "CAYENNE (19MY)".
- A Mecânica Online de 10/11/2016 diz que o "Cayenne S E-Hybrid já [está]
  disponível para vendas no Brasil".
- Pela leitura literal da regra 2, o Cayenne entraria por `pbe_ano` em 2021,
  cinco anos tarde.

Por isso só a coluna de propulsão (2021 em diante) prova ausência. Isso trouxe
para a busca de fonte, além dos casos "sem marcador antes de 2021":

- **Ano de PBE pós-2021 sem ano anterior visível.** CLA 200 (o modelo some do
  PBE de 2020 a 2023) e Civic (a vigência começa em 2022, e o modelo só aparece
  em 2023).
- **Marcador antes de 2021 sem ano anterior visível.** Fusion (o PBE só tem o
  Fusion a partir de 2011, já HYBRID).
- **Marcador em 2021 sobre tabela de 2020 genérica.** Accord, Range Rover, Mini
  Cooper e Cayenne.

### As fontes: 23 tipos, 27 linhas

Todas abertas nesta rodada com `src/ferramentas/origem_fonte.py`, com o trecho
copiado. `testes/test_origem_fontes.py` confere o trecho literal e o SHA-256 de
cada página.

| modelo | tipo | entrada | data da fonte | fonte (tipo) |
|---|---|---:|---|---|
| Corolla | hev | 2019 | lançamento 2019-09 | Revista Carro (especializada) |
| Peugeot 2008 | bev | 2022 | lançamento 2022 | Motor Show (especializada) |
| Peugeot 208 | bev | 2021 | lançamento 2021-09 | AutoPapo (especializada) |
| Discovery (inclui o Sport) | hibrido_indefinido | 2022 | lançamento 2022-01 | Forbes (geral) |
| XC90 | phev | 2017 | lançamento 2017-03 | Forbes (geral) |
| XC60 | phev | 2018 | pré-venda 2018-09 | TNH1 (geral) |
| S60 | phev | 2019 | presença 2019-12 | Mecânica Online (especializada) |
| XC40 | phev | 2020 | lançamento 2020-06 | Canaltech (geral) |
| Golf | phev | 2019 | lançamento 2019-11 | Canaltech (geral) |
| Fusion | hev | 2010 | lançamento 2010-11 | Auto+ TV (especializada) |
| X3 | phev | 2020 | pré-venda 2020-08 | AutoPapo (especializada) |
| X5 | phev | 2020 | lançamento 2020-03 | Revista Carro (especializada) |
| Panamera | phev | 2017 | lançamento 2017-12 | Auto+ TV (especializada) |
| Cayenne | phev | 2016 | presença 2016-11 | Mecânica Online (especializada) |
| Kangoo (auto e comerciais) | bev | 2013 | presença 2013-10 | Mundo Logística (geral) |
| Accord | hev | 2021 | lançamento 2021-08 | Revista Carro (especializada) |
| Civic | hev | 2023 | lançamento 2023-01 | Canaltech (geral) |
| Range Rover (inclui o Sport) | phev | 2020 | lançamento 2020-02 | Revista Carro (especializada) |
| Mini Cooper | bev | 2021 | pré-venda 2021-03 | TecMundo (geral) |
| CLA 200 | hibrido_indefinido | 2023 | lançamento 2023-09 | car.blog.br (blog) |
| Outlander | phev | 2014 | produção 2014 | AutoIndústria (especializada; página da rodada de validação) |

Mais quatro linhas `plano`, registradas para mostrar a busca, que não datam
nada:

- Corolla, Eixos de 17/04/2019;
- e-2008, Canaltech de 27/10/2022, sem preço;
- A3 e-tron, Motor Show de 2014: "será vendido [...] no fim do ano que vem";
- Cayenne S Hybrid, Olhar Direto de 2010, que só confirma exibição no Salão.

**Critério de `lancamento` contra `plano`.** Anúncio com preço e mês, publicado
até um mês antes, conta como lançamento: Golf GTE ("vendas iniciando já na
próxima semana"), X5 ("a partir de março, com preço sugerido"). Pré-venda
aberta também conta. Anúncio sem preço ou com meses de antecedência conta como
plano (Corolla na Eixos, e-2008 na Canaltech).

**Domínios novos em `config/tipo_fonte_dominio.csv`, propostos por mim:**

- `imprensa_especializada` (mesma fronteira da Motor Show): mecanicaonline e
  automaistv;
- `imprensa_geral`: forbes.com.br, tnh1, tecmundo, olhardireto, mundologistica
  e eixos; os dois últimos são especializados, mas não em automóvel;
- `blog_agregador`: car.blog.br.

`origem_fonte.py --tipos` agora recalcula também `propulsao_fontes.csv`.

### Os três tipos que ficaram sem datação

| modelo | tipo | por quê |
|---|---|---|
| XC40 | hibrido_indefinido (o B4 do PBE 2021) | nenhuma fonte brasileira sobre o B4; só achei o T5 plug-in |
| A3 | phev (`pendente`) | só o anúncio de 2014; nenhuma notícia da venda |
| Cayenne | hev (`pendente`) | só a confirmação no Salão de 2010; nenhuma notícia da venda |

Os três entram no início da vigência, marcados `vigencia_sem_datacao`: 1,1% das
unidades eletrificadas.

### O que os casos da sua tabela viraram

| modelo | antes, 2018 | depois, 2018 | entrada do tipo eletrificado |
|---|---|---|---|
| Compass | parcial | nenhuma | phev 2022 (`pbe_ano`) |
| Toro | parcial | nenhuma | hibrido_indefinido 2026 (`pbe_ano`) |
| Renegade | parcial | nenhuma | hibrido_indefinido 2026 (`pbe_ano`) |
| Peugeot 2008 | parcial | nenhuma | bev 2022 (`fonte_datada`); o híbrido de 2026 do PBE não está no conjunto da vigência, que é `pendente` e mostra a proposta |
| Equinox | parcial | nenhuma | bev 2025 (`pbe_ano`) |
| Peugeot 208 | — | — | a vigência começa em 2020-01: bev 2021 (`fonte_datada`), hibrido_indefinido 2026 (`pbe_ano`) |

`testes/test_propulsao_anual.py` trava Toro, Compass e Renegade:

- `nenhuma` em 2018;
- `nenhuma` no ano anterior à chegada;
- `parcial` no ano da chegada.

---

## A coluna da vigência

Em `classificacao.parquet`:

- `propulsao_oferecida` passou a `propulsao_na_vigencia`;
- `eletrificacao` passou a `eletrificacao_na_vigencia`.

O dicionário (`saidas/classificacao_dicionario.md`) diz em destaque, no topo e
na linha de cada coluna: **"conjunto de tudo que foi oferecido em algum momento
da vigência — não usar em série temporal; para isso,
`classificacao_propulsao_anual`."** O dicionário do painel e o catálogo dizem o
mesmo.

**Decisão: o rascunho não mudou de nome.** O rascunho
(`classificacao_rascunho.xlsx`) continua com `propulsao_oferecida`, que é o
nome da proposta.

- A decisão humana aceita os dois nomes: `propulsao_na_vigencia=flex+hev` vale
  o mesmo que `propulsao_oferecida=flex+hev`.
- Mudar o rascunho obrigaria a regenerá-lo, e não havia razão para isso nesta
  rodada.

---

## A regra nova na ESPEC

Acrescentei o seu texto, literal, ao fim das "Validações obrigatórias" (§6),
com uma nota de quando e por que entrou. Para a classificação, o uso-teste
deixou de depender de alguém lembrar de fazê-lo: a etapa 11 grava a série pela
vigência e pela tabela anual, lado a lado, a cada execução. A plausibilidade
continua sendo leitura humana; o código não decide o que é "evento que
explica".

---

## A ABVE

**Acesso.** `abve.org.br` abre.

- **A série completa** (mensal, por tecnologia, desde 2012) está só num painel
  Power BI embutido, que não se lê sem navegador.
- **Os comunicados** mensais e anuais trazem em texto as unidades do ano, por
  tecnologia, e às vezes a participação.
- Guardei os de 2020, 2022, 2023, 2024, 2025 e agosto de 2026.
- O de 2021 voltou vazio nas quatro tentativas: o servidor às vezes devolve
  página vazia, e o de 2024 só abriu na quarta. As unidades de 2021 vêm do
  comunicado de 2022.
- Abri também `abve.org.br/vendas/`, que é vitrine de produtos, não
  estatística. Como toda página aberta e não citada nos CSVs nesta rodada (nove ao
  todo), ela fica guardada no manifesto.

**Registro, sem construir nada.**

- `dados/referencia/abve_serie_anual.csv` tem a série anual, com o trecho de
  cada comunicado; um teste confere o trecho literal.
- `src/ferramentas/abve_comparacao.py` grava `saidas/abve_comparacao.csv`.

**Denominador.** A participação da ABVE foi recalculada sobre o total que a
Fenabrave publica para automóveis e comerciais leves (`saidas/cobertura.csv`).
É o mesmo mercado que a ABVE cita: 2.658.692 em 2019 e 2.549.517 em 2025,
contra 2.659.356 e 2.549.251 na Fenabrave.

| ano | ABVE, unidades | ABVE, % dos leves | piso (`total`) | teto corrigido (`total + parcial`) | teto antes (pela vigência) | entre piso e teto? |
|---|---:|---:|---:|---:|---:|---|
| 2016 | 1.091 | 0,05% | 0,02% | 0,55% | 7,36% | sim |
| 2017 | 3.296 | 0,15% | 0,11% | 0,60% | 8,48% | sim |
| 2018 | 3.970 | 0,16% | 0,10% | 0,66% | 8,81% | sim |
| 2019 | 11.858 | 0,45% | 0,03% | 2,74% | 9,59% | sim |
| 2020 | 19.745 | 1,01% | 0,18% | 2,82% | 13,08% | sim |
| 2021 | 34.990 | 1,77% | 0,09% | 5,48% | 19,37% | sim |
| 2022 | 49.245 | 2,52% | 0,15% | 11,85% | 21,78% | sim |
| 2023 | 93.927 | 4,31% | 1,38% | 11,89% | 21,69% | sim |
| 2024 | 177.358 | 7,14% | 4,56% | 14,46% | 23,29% | sim |
| 2025 | 223.912 | 8,78% | 6,58% | 21,47% | 26,06% | sim |
| 2026 (jan a ago) | 328.477 | 17,40% | 13,12% | 30,48% | 30,48% | sim |

O que a comparação mostra:

- **A ABVE cai entre o piso e o teto em todos os anos.** O teto antigo também
  a continha: um teto inflado ainda é teto. O que a correção mudou foi a
  largura do intervalo: em 2018, de 0,1–8,8% para 0,1–0,7%.
- **O piso fica muito abaixo da ABVE até 2023.** Os híbridos flex (Corolla e
  Corolla Cross) são `parcial`, não `total`, porque o modelo vende também a
  combustão. É o limite da fonte, que não separa unidades por versão; a ABVE é
  a saída para isso, como diz `fontes_candidatas.csv`.
- **Duas coisas a ABVE não fecha por dentro.** Não as corrigi:
  - A **participação acumulada de 2026** publicada é 20,2%. As 328.477 unidades
    do comunicado sobre os 1.888.019 leves da Fenabrave de janeiro a agosto dão
    17,4%; agosto sozinho fecha (21,8% publicado, 21,82% recalculado). As duas
    caem entre 13,1% e 30,5%.
  - A **definição de eletrificado muda**: 2024 (177.358) inclui MHEV, inclusive
    3.828 micro-híbridos de 12 V; 2025 (223.912) exclui MHEV. O comunicado de
    2025 compara um com o outro.
- `config/fontes_candidatas.csv` registra o teste: estado da ABVE de "não
  testado" para o que está acima.

---

## Erros cometidos e como foram corrigidos

1. **A "pior" procedência saía a melhor.** Na tabela anual, a procedência de um
   ano com duas vigências devia ser a mais fraca, mas a função pegava o
   primeiro valor na ordem da tupla, que vai de `humana` para baixo. O teste
   novo (RAV4 sintético: `pendente` + `regra_fonte_forte`) pegou; corrigi antes
   de gravar.
2. **A validação acusava "tipo fora da vigência" no Compass de 2016.** Ela
   filtrava as linhas da vigência pelo intervalo de anos, e 2016 pertence às
   duas vigências do Compass por calendário, mas só à segunda por unidades. Era
   defeito da validação, não do dado. A tabela passou a gravar quais vigências
   têm unidades em cada ano (`vigencias`), e a validação usa isso.
3. **O teste de Toro/Compass/Renegade falhou** por eu supor que o Toro é
   `automoveis`; é `comerciais_leves`. Corrigi o teste.
4. **Ia citar sem abrir.** Na primeira versão da série da ABVE, escrevi na
   observação de 2024 que "na imprensa" os 177.358 incluíam micro-híbridos.
   Era o resumo de uma busca, de página não aberta. Tirei antes de gravar,
   insisti no comunicado de 2024 da ABVE até ele abrir, e a observação agora
   cita o trecho dele.
5. **A busca na web bateu no limite da sessão** no meio da rodada. As páginas
   já guardadas sobreviveram à pausa, e retomei de onde parei.
6. **O rótulo de 2026 no dicionário saiu "jan-08"**; agora sai "jan a ago".

---

## O que ficou em aberto

Está registrado também em `QUESTOES_ABERTAS.md`, seção "Propulsão no tempo".

1. **A saída de um tipo não é modelada.**
   - O Outlander phev (produção de 2014 a 2016, segundo a fonte) fica até 2022,
     embora o PBE de 2021 e 2022 mostre o Outlander sem phev.
   - A coluna de Boris Feldman no O POVO (20/12/2021, página `xc40_b4_opovo`)
     anuncia que a Volvo deixa de importar o XC40 híbrido a partir de 2022.
2. **Três tipos sem datação** (tabela acima).
3. **Ano com duas vigências une as duas.** Desde 2015, só Corolla e RAV4 de
   2019, ou 2,3% das unidades de 2019.
   - Separar exigiria uma linha por vigência-ano, e a chave que você pediu é
     por ano.
   - Se preferir a linha por vigência-ano, a troca é pequena: a função já sabe
     quais vigências cada ano tem.
4. **`hibrido_indefinido` que as fontes dizem leve.** "MHEV" no Discovery Sport
   D200 e "48 volts" no CLA 200. Passar a `mhev` é decisão sua no rascunho; a
   eletrificação fica igual.
5. **Entradas talvez anteriores à fonte.** X5 xDrive40e e Panamera S E-Hybrid
   da primeira geração, se vendidos aqui, não têm fonte brasileira datada. S60
   e Cayenne são datados por presença à venda.
6. **A chave do painel junta modelos que o PBE separa.** DISCOVERY inclui o
   Discovery Sport, e RANGE ROVER inclui o Range Rover Sport e o Velar. A
   entrada do tipo vale para a chave, não para cada carro dentro dela.
7. **O ano de PBE pode estar um ano à frente do mercado.** O Discovery Sport
   D200 MHEV aparece no PBE de 2021 e chegou em janeiro de 2022. Onde não houve
   fonte, `pbe_ano` carrega esse viés.

---

## Conferência

- **Etapa 11** grava a dimensão, os 968 períodos de montagem e a tabela anual
  (5.896 linhas).
  - Validações da tabela anual: uma linha por chave-ano com unidades;
    unidades iguais ao painel; tipo só da vigência; nada some dentro da
    vigência; o último ano da vigência com o conjunto inteiro.
  - Todas passam.
- **Procedências da dimensão:** idênticas às da rodada anterior (a correção é
  só no tempo, não no valor).
- **Testes:** 292 passam; o do catálogo passa depois que `validacao.md` e
  `CATALOGO.md` são regerados sobre a árvore limpa, no commit seguinte.
- **Tag:** `rodada-9` na linha nova de `tags_pendentes.csv`.
