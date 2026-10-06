# Registro de execução — casamento com o PBE, unidades do Comex e calendário de políticas

05/10/2026. Branch `claude/new-session-rs2chd`. Este registro vai no mesmo push
do trabalho que ele descreve.

## Em uma frase

- **PBE:** o e-208 casa com o 208, pela soma da planilha; o e-2008 tem chave
  própria e não casa com o 2008. A auditoria das 578 versões eletrificadas sem
  casamento resolveu as que tinham evidência; as sem evidência estão em
  `saidas/pbe_variantes_sem_evidencia.csv` e seguram a saída do seu tipo (a
  guarda). A leitura curta da combustão segue a longa até 2020: 37 tipos
  mudaram, nenhum nível de eletrificação.
- **Comex:** `unidades_ajustadas` estima pelo peso as 2.035 linhas com menos de
  500 kg por unidade (4,23 milhões de unidades publicadas viram 168.672). O
  agregado de carros perde o 8703.10. Os três uso-testes foram refeitos com as
  ajustadas, e o salto de 2019 do BEV some.
- **Calendário de políticas:** 50 atos de 2008 a 2026 e 216 alíquotas, cada um
  com trecho literal de uma das 55 páginas oficiais guardadas;
  `politicas_mensal.parquet` junta ao painel pelo mês. Três pistas não se
  confirmaram em página oficial e ficaram fora (fim da quota de carros de 2023,
  protocolo argentino de 2013–2014, nada procurado antes de 2008).
- **Uso-teste das datas:** 25 das 61 datas não mostram movimento além do
  sazonal. A que mais pede conferência é a do desconto de junho de 2023, cuja
  janela de comparação (junho de 2022) vem logo depois do corte de IPI de maio
  de 2022.
- **Motorização:** registrada em `QUESTOES_ABERTAS.md` como próxima dimensão.
  Não construída.

---

## Parte 1 — o casamento com o PBE

### O que eu conferi primeiro

Os seus números bateram antes de eu mexer em qualquer coisa:

- **578 versões eletrificadas sem casamento**, de 2021 em diante. Contei 578 no
  casamento completo, que inclui as linhas sem chave; `saidas/pbe_casamento.csv`
  só guarda as casadas.
- **E2008 no informe:** 269, 62 e 8 unidades em 2024-01, 2024-02 e 2024-03, 339
  no total.
- **Planilha em 2023-02:**
  - o 208 do painel (1.163) é o Peugeot 208 (1.160) mais o e-208 (3);
  - o 2008 do painel (91) é o Peugeot 2008 (91), com o e-2008 (9) à parte.
- **Efeito no teto:**
  - 208, leitura longa: +1,33, +0,72 e +0,39 ponto em 2023–2025;
  - 208, leitura curta: +1,54 em 2022;
  - 2008: −0,27, −0,08, −0,32 e −0,45 ponto em 2022–2025.

### 1.1 Os dois casos resolvidos pela evidência

- **208.**
  - `E-208` casa com a chave 208 em `config/pbe_modelos.csv`, pela regra 2: a
    planilha soma.
  - Achei também o `208 E-GT` de 2021, que já casava, porque o nome começa com
    `208`.
- **2008.**
  - As três linhas do E-2008 em `propulsao_fontes.csv` passaram para a chave
    E2008. O conserto `5fa79c9` perdeu o objeto, como você disse.
  - A decisão "o 2008 fica `flex`" está em `config/decisoes_humanas.csv` (ver
    abaixo).
  - Registrei também a linha `PEUGEOT,2008,E2008,nao_casa` em
    `config/pbe_modelos.csv`, com as duas evidências. É só registro: o
    `E2008 GT` do PBE já casava com a chave própria.

**Como a decisão do 2008 entrou.** É a primeira decisão humana do projeto, e o
rascunho não tinha onde guardá-la de uma geração para a outra.

- **Arquivo novo:** `config/decisoes_humanas.csv`, versionado, uma linha por
  decisão (chave, `vigencia_inicio`, a decisão na sintaxe de `decisao_humana`,
  data, origem e observação).
- **Cópia a cada execução:** o gerador do rascunho copia cada decisão para a
  coluna `decisao_humana`. Decisão sem linha no rascunho, repetida ou fora da
  sintaxe é erro.
- **Guarda do gerador:** ele só recusa sobrescrever quando o rascunho tem
  decisão que não está no arquivo.

**Um conflito com uma regra sua, e como resolvi.** Na fase 2, você pediu que
falhe a linha com decisão humana que deixa atributo `pendente`.

- O 2008 tem a origem contestada pela O3 (garagem360 contra autodata). A sua
  decisão é só de propulsão.
- Não inventei origem. A decisão ficou
  `propulsao_oferecida=flex; origem_producao=pendente`.
- A sintaxe ganhou `atributo=pendente`: deixar pendente de propósito, escrito.
  A regra continua recusando o pendente não escrito.
- Também recusa `atributo=pendente` em atributo que não está pendente.
- Se preferir outra saída, o arquivo tem uma linha só.

**O que a decisão literal tira.** O PBE de 2026 lista o `2008 GT HYBRID`
(HIBRIDO), que a P4 transformava em `hibrido_indefinido`.

- **Antes**, a linha era `pendente` e mostrava a proposta (`flex+bev`); o
  híbrido não entrava na banda.
- **Agora** o 2008 é `flex` em todos os anos, como você escreveu.
- **Se a intenção era só tirar o `bev`**, a decisão vira
  `propulsao_oferecida=flex+hibrido_indefinido`. O 2008 entra no teto de 2026
  com 5.187 unidades, +0,28 ponto. Está em `QUESTOES_ABERTAS.md`.

### 1.2 A auditoria

**A busca** (`src/comum/pbe_variantes.py`) é por palavra inteira, não por
substring.

- **Normalização:** o nome vira palavras sem hífen, sem o `AMG` do início e com o
  `E` solto colado à palavra seguinte (`320 E SPRINTER` → `320 ESPRINTER`).
- **Relação entre o nome do PBE e o da chave:**
  - `mesmo_nome`: o nome começa com o da chave, a menos de espaço, hífen, `AMG`
    ou ordem das palavras;
  - `contem`: a chave aparece inteira mais adiante;
  - `prefixo`: `E` ou `I` colado na frente;
  - `sufixo`: letra depois de número (`RAV4H`) ou número depois de letra
    (`GLC43`).
- **Falsos positivos que ela não produz**, com teste para cada um: `TT` dentro
  de `QUATTRO`, `GL` dentro de `GLB`, `M6` dentro de `M60`, `ON` dentro de
  `ONIX`.
- **A chave tem de estar viva no ano:** unidades no painel entre o ano anterior e
  o seguinte ao da tabela do PBE. Isso tira os casos em que a única chave com o
  nome morreu antes da versão existir:
  - `COUPE` (2007), `GL` (2007), `SL` (2007–2009), `M6` (2014–2016),
    `CHEROKEE` (até 2017) e `A 200` (até 2019);
  - `X2` (2019), `S90` (até 2022) e `VITARA` (até 2019);
  - `FPACE` (2017), `AMG GT` (2018) e `CLS` (até 2014).

Antes dos casamentos novos eram 188 pares versão-chave (119 com a chave viva);
depois, 118 continuam sem casamento, 54 com a chave viva.

**O teste de inclusão**, na sua ordem. A planilha ajuda pouco: só traz à parte
o e-208, o e-2008, o iX3 (2023-02 a 2023-08), o Arrizo 5e (2019-09 e 2019-10)
e, num mês só, GLC Coupé e GLE Coupé.

| chave | nome no PBE | regra | decisão | evidência |
|---|---|---|---|---|
| PEUGEOT 208 | `E-208 GT` | 2, planilha soma | casa | 2023-02: 1.163 = 1.160 + 3 |
| AUDI E TRON GT | `E-TRON GT` | 1, chave própria | casa | mesmo nome, com hífen |
| FORD ETRANSIT | `E-TRANSIT …` | 1 | casa | mesmo nome |
| FORD TRANSIT | `E-TRANSIT …` | 1 | não casa | a variante tem chave própria (ETRANSIT) |
| JAC IEV 330P | `IEV330P …` | 1 | casa | mesmo nome, sem espaço |
| M.BENZ CLA200 | `CLA 200 AMG LINE`, `CLA 200 PROGRESSIVE` | 1 | casa | mesmo nome, com espaço |
| M.BENZ CLA35 | `AMG CLA35 4M` | 1 | casa | mesmo nome, com o AMG da linha |
| M.BENZ S63 | `AMG S63 EP` | 1 | casa | idem |
| M.BENZ SL63S | `AMG SL63S EP` | 1 | casa | idem |
| M.BENZ ESPRINTER 320 | `320 ESPRINTER …`, `320 E SPRINTER …` | 1 | casa | mesmo nome, em outra ordem |
| M.BENZ SPRINTER | os mesmos | 1 | não casa | a variante tem chave própria (ESPRINTER 320) |
| BMW X3 | `IX3` | 3, planilha não soma | não casa | 2023-02: X3 do painel 53 = X3 da planilha 53, iX3 (10) à parte |
| BMW X1 | `IX1 …` | 4 | sem evidência | nem chave nem linha na planilha |
| BYD T3 | `ET3` | 4 | sem evidência | idem |
| CAOA CHERY e CHERY ARRIZO 5 | `ARRIZO5 E E` | 4, evidência contraditória | sem evidência | 2019-09 soma (301 = 191 + 110), 2019-10 não soma (210 = 210) |
| CITROEN JUMPY | `E-JUMPY CARGO` | 4 | sem evidência | nem chave nem linha na planilha |
| FIAT SCUDO | `E-SCUDO CARGO` | 4 | sem evidência | idem |
| PEUGEOT EXPERT | `E-EXPERT CARGO` | 4 | sem evidência | idem |
| LEXUS ES300 | `ES300H` | 4 | sem evidência | a planilha só traz "ES" |
| M.BENZ CLA45 | `AMG CLA45S 4M` | 4 | sem evidência | a planilha só traz "CLA" |
| M.BENZ GLC | `AMG GLC43 …`, `AMG GLC63S EP` | 4 | sem evidência | a planilha não separa o AMG |
| M.BENZ GLE | `AMG GLE53 4M`, `AMG GLE63 S CO COUPE` | 4 | sem evidência | idem |
| TOYOTA RAV4 | `RAV4H …` | 4 | sem evidência | a planilha só traz "RAV4" |

**Diferenças em relação à sua lista:**

- **`320 E SPRINTER` não vai para SPRINTER.** O painel tem a chave própria
  `ESPRINTER 320` (comerciais leves, desde 2025-02), e a regra 1 vem antes.
- **`E-TRANSIT` não vai para TRANSIT**, pelo mesmo motivo (chave ETRANSIT).
- **CLA200 casou pela regra 1.** O nome é o da chave com um espaço; não é
  variante.
- **`AMG GLC43` e `AMG GLC63S` ficaram sem evidência.** Achei uma incoerência
  aqui:
  - o apelido `AMG GLC` → GLC, de rodada anterior, já casa `AMG GLC 43` (com
    espaço) sem nunca ter passado por este teste;
  - o mesmo vale para `AMG C`, `AMG GLA` e `AMG E`;
  - não mexi nos antigos e registrei em `QUESTOES_ABERTAS.md`.
- **iX1 e iX3.** A planilha decide o iX3 (não soma) e não diz nada do iX1.
- **Fora da busca por nome:**
  - `A200 AMG LINE` (hev, 2023–2025) não contém nenhuma chave viva. Pode ser
    da `CLASSE A`, mas o nome não diz. Não casei.
  - `G CHEROKEE 4XE` é Grand Cherokee. A chave que o nome contém (CHEROKEE)
    morreu em 2017.

**Onde fica cada coisa:**

- **Decisões:** em `config/pbe_modelos.csv`, coluna nova `decisao`, com a
  evidência na observação. As linhas antigas ficaram `casa`.
- **Candidatos:** `saidas/pbe_variantes_candidatos.csv`, escrito pelo gerador do
  rascunho com a decisão de cada par.
- **Lista do item 4:** `saidas/pbe_variantes_sem_evidencia.csv`, escrita pela
  etapa 11, com 13 famílias.
- **Testes** (`testes/test_pbe_variantes.py`):
  - a busca;
  - o teste da planilha: as decisões pela planilha batem com
    `saidas/referencia_cruzada.csv`;
  - toda variante viva tem decisão;
  - a lista cobre os sem evidência.

### 1.3 A guarda

Em `comum/propulsao_anual.py`: a ausência no PBE não prova saída no ano em que
há candidata sem decisão de casamento (`sem_evidencia`) do mesmo tipo.

**Uma decisão minha: a guarda olha o tipo.** A versão sem casamento só segura o
tipo da família dela.

- O `E-JUMPY` (`bev`) não segura o diesel do Jumpy.
- O `IX1` (`bev`) não segura a gasolina do X1.
- O motivo: uma versão sem casamento de outro tipo não explica a ausência
  daquele tipo.

**Efeito nesta rodada:** a guarda descartou um ano de ausência, o `bev` do
Arrizo 5 (CAOA CHERY) em 2021. Ele já não saía, porque havia presença depois.
Nenhuma saída mudou. Ela fica para as próximas tabelas do PBE.

### 1.4 A leitura curta na combustão

**A regra:** na combustão sem fonte datada de fim, a curta vai pelo menos até
`min(último ano longo, 2020)`. Com fonte de fim, a curta pode sair antes.

**Os seus 32 tipos.** São os de combustão em que a curta acabava no ano de
entrada e antes da longa.

- **28 deles acabavam antes de 2021**, e a regra os cobre.
- **4 entram em 2021 ou depois:** gasolina do Civic de 2022, do Stonic de 2022 e
  do Classe C de 2021, e flex do Classe GLA de 2021. Ali o PBE já tem coluna, e
  a regra não se aplica.

**37 tipos mudaram:** os 28, mais 9 cuja curta acabava antes de 2020 sem ser no
ano de entrada. Exemplos: o flex do Tucson ia até 2019 e o gasolina do CLA200
até 2015.

**Nenhum nível de eletrificação muda**, como você disse. A curta muda a
propulsão em 409 vigência-anos de 33 modelos, e a eletrificação em nenhum fora
do 208 e do 2008. Há teste.

### 1.5 Uso-teste

**Banda antes e depois, 2021–2026** (% das unidades do painel; 2026 de janeiro a
agosto). "Antes" é `f522c83`.

| ano | leitura | piso | teto antes | teto depois | sem MHEV antes | sem MHEV depois | estrito antes | estrito depois |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 | longa | 0,09 | 5,48 | 5,48 | 5,45 | 5,45 | 5,45 | 5,45 |
| 2022 | longa | 0,16 | 11,78 | 11,51 | 10,65 | 10,38 | 10,64 | 10,37 |
| 2023 | longa | 1,77 | 10,55 | 11,80 | 9,33 | 10,58 | 9,30 | 10,55 |
| 2024 | longa | 4,80 | 13,72 | 14,13 | 11,45 | 11,86 | 11,45 | 11,86 |
| 2025 | longa | 6,79 | 21,07 | 21,01 | 16,34 | 16,28 | 16,30 | 16,24 |
| 2026 | longa | 13,24 | 28,18 | 28,18 | 18,76 | 18,96 | 18,72 | 18,92 |
| 2021 | curta | 0,10 | 5,33 | 5,33 | 5,30 | 5,30 | 5,30 | 5,30 |
| 2022 | curta | 0,41 | 10,24 | 11,51 | 9,09 | 10,37 | 9,09 | 10,36 |
| 2023 | curta | 1,79 | 10,55 | 11,80 | 9,33 | 10,58 | 9,30 | 10,55 |
| 2024 | curta | 4,80 | 13,72 | 14,13 | 11,45 | 11,86 | 11,45 | 11,86 |
| 2025 | curta | 6,79 | 18,14 | 18,53 | 13,44 | 13,83 | 13,40 | 13,79 |
| 2026 | curta | 13,25 | 28,15 | 28,15 | 18,69 | 18,89 | 18,65 | 18,85 |

O piso não mudou em nenhum ano.

**Cada chave que ganhou ou perdeu tipo** (em pontos):

| chave | leitura | ano | antes | depois | teto | sem MHEV | estrito |
|---|---|---|---|---|---:|---:|---:|
| 208 | longa | 2023 | flex | flex+bev | +1,33 | +1,33 | +1,33 |
| 208 | longa | 2024 | flex | flex+bev | +0,72 | +0,72 | +0,72 |
| 208 | longa | 2025 | flex | flex+bev | +0,39 | +0,39 | +0,39 |
| 208 | longa | 2026 | flex+mhev | flex+mhev+bev | 0 | +0,20 | +0,20 |
| 208 | curta | 2022 | flex | flex+bev | +1,54 | +1,54 | +1,54 |
| 208 | curta | 2023–2025 | flex | flex+bev | +1,33 / +0,72 / +0,39 | idem | idem |
| 208 | curta | 2026 | flex+mhev | flex+mhev+bev | 0 | +0,20 | +0,20 |
| 2008 | longa | 2022 | flex+bev | flex | −0,27 | −0,27 | −0,27 |
| 2008 | longa | 2023 | flex+bev | flex | −0,08 | −0,08 | −0,08 |
| 2008 | longa | 2024 | flex+bev | flex | −0,32 | −0,32 | −0,32 |
| 2008 | longa | 2025 | flex+bev | flex | −0,45 | −0,45 | −0,45 |
| 2008 | curta | 2022–2024 | flex+bev | flex | −0,27 / −0,08 / −0,32 | idem | idem |

Nenhuma outra chave mudou de tipo eletrificado em nenhum ano.

- **Os casamentos novos de nome** (CLA200, CLA35, S63, SL63S, E-TRON GT,
  ETRANSIT, IEV 330P, ESPRINTER 320) não mexem na banda:
  - o CLA200 já tinha `mhev` pela P5;
  - os demais estão abaixo do piso de classificação.
- **Um único efeito novo:** o 208 ganha o `bev` também em 2026, porque o
  `E-208 GT` está no PBE de 2026. Isso dá +0,20 ponto nos dois tetos sem MHEV;
  o `teto` não muda, porque o `mhev` já o punha no `parcial`.

**ABVE, refeita** (`saidas/abve_comparacao.csv`):

| ano | ABVE % | definição | piso mín. | teto máx. antes | teto máx. depois | estrito longa depois | estrito curta depois | dentro |
|---|---:|---|---:|---:|---:|---:|---:|---|
| 2021 | 1,77 | sem MHEV | 0,09 | 5,45 | 5,45 | 5,45 | 5,30 | sim |
| 2022 | 2,52 | sem MHEV | 0,16 | 10,65 | 10,38 | 10,37 | 10,36 | sim |
| 2023 | 4,31 | sem MHEV | 1,77 | 9,33 | 10,58 | 10,55 | 10,55 | sim |
| 2024 | 7,14 | teto (com MHEV) | 4,80 | 13,72 | 14,13 | 11,86 | 11,86 | sim |
| 2025 | 8,78 | sem MHEV | 6,79 | 16,34 | 16,28 | 16,24 | 13,79 | sim |
| 2026 | 17,40 | sem MHEV | 13,24 | 18,76 | 18,96 | 18,92 | 18,85 | sim |

- A ABVE continua dentro da banda em todos os anos e nunca acima do
  `teto_estrito`.
- O 20,2% publicado para 2026 segue acima do `teto_estrito` (agora 18,9%).

### Erros e correções desta parte

- **CRLF em `propulsao_fontes.csv`.** A primeira regravação trocou o fim de linha
  (o arquivo é CRLF) e o diff mostrava as 33 linhas mudando. Restaurei o CRLF;
  o diff ficou com as três linhas do E-2008.
- **Nome da coluna da guarda.** Ela se chamava `guarda_segurou_saida`, mas nesta
  rodada a guarda não segurou saída nenhuma, só descartou um ano de ausência.
  Renomeei para `ausencia_descartada`.
- **Teste que exigia chave do rascunho.** O teste das fontes de propulsão exigia
  que a chave estivesse na proposta do assistente, e o E2008 está abaixo do
  piso. Passou a exigir chave do painel. O teste de tipo da vigência ignora
  chave sem propulsão classificada.

---

## Parte 2 — Comex: as linhas de peso baixo

### O que eu conferi

**A referência.** A sua tabela sai do produto quando a referência é a média
ponderada (kg somados sobre unidades somadas) das linhas plausíveis da mesma
NCM, no mesmo fluxo e no mesmo ano.

| linha | publicadas | estimadas | US$ por unidade estimada |
|---|---:|---:|---:|
| Argentina, 2001, 87032210 | 222.440 | 779 | 9.143 |
| México, 2006, 87032310 | 306.783 | 2.745 | 13.714 |
| Alemanha, 2003, 87032310 | 29.144 | 9.440 | 13.926 |
| Japão, 2026, 87041010 (dumper) | 578.363 | 5 | 809.700 |
| Índia, 2019, 87038000 | 9.621 (= 9.621 kg) | 6 | 8.928 |

- As diferenças de preço vêm do arredondamento.
- No dumper japonês, divido o FOB pelas 5 unidades inteiras. O seu número
  (773.045) parece dividido pela estimativa sem arredondar.
- Com a referência dos dois fluxos juntos, os números não batem (Argentina 843,
  México 3.061). Por isso fiquei com o fluxo.

### O que mudou no dado

**`unidades` continua como publicada.** As duas colunas novas:

- **`unidades_ajustadas`** (Int64):
  - igual à publicada com 500 kg ou mais por unidade;
  - abaixo disso, o peso dividido pelo kg por unidade de referência,
    arredondado para inteiro (meio para cima).
- **`ajuste_unidades`:** `publicada` ou `estimada_pelo_peso`. Fica vazio onde
  `unidades` é vazio, o que hoje não acontece.

**A referência, em ordem:**

1. mesma NCM, fluxo e ano, nas linhas plausíveis;
2. sem ela, a mesma NCM e fluxo em todos os anos;
3. depois, a NCM nos dois fluxos.

O terceiro degrau é meu: você não disse o que fazer sem referência nenhuma, e
ele não é usado nesta rodada. Uma linha não tem referência em nenhum degrau:
exportação de 87037000 para o México em 2022-11, 3 unidades em 60 kg (a NCM
inteira é essa linha). Ela fica com a publicada e aparece na validação.

**Contas** (`saidas/comex_validacao.csv`):

- 2.036 linhas abaixo de 500 kg por unidade. 2.035 foram estimadas: 4.227.631
  unidades publicadas viraram 168.672.
- 71.281 linhas `publicada`, todas com a ajustada igual à publicada. A etapa 12
  falha se não for assim.
- Nove linhas de exportação têm 0 kg com quantidade positiva (FOB de US$ 1 a
  US$ 1.461). A estimativa delas é 0.

**O agregado de carros** é a coluna nova `agregado_carros` em
`config/ncm_veiculos.csv`: `sim` para 8703 menos 8703.10, e para o 8704 leve.
Ficam fora:

- 8703.10;
- os 16 do 8704 não leve;
- os dois `indeterminado` (87046000 e 87049000).

Conferi a sua conta do 8703.10 em 2025: 12.908 unidades, 12.894 da China, a 36
kg cada.

### Uso-testes refeitos, com unidades ajustadas (a publicada ao lado)

**1. BEV importado contra o painel só-`bev` (leitura longa)**

| ano | importação ajustada | publicada | painel só `bev` | razão | razão publicada | dif. acumulada | dif. acumulada publicada |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2017 | 43 | 50 | 0 | – | – | 43 | 50 |
| 2018 | 138 | 167 | 0 | – | – | 181 | 217 |
| 2019 | 805 | 27.024 | 0 | – | – | 986 | 27.241 |
| 2020 | 773 | 6.573 | 76 | 10,17 | 86,49 | 1.683 | 33.738 |
| 2021 | 3.162 | 11.963 | 818 | 3,87 | 14,62 | 4.027 | 44.883 |
| 2022 | 9.394 | 9.411 | 1.197 | 7,85 | 7,86 | 12.224 | 53.097 |
| 2023 | 28.441 | 28.823 | 12.721 | 2,24 | 2,27 | 27.944 | 69.199 |
| 2024 | 80.553 | 80.589 | 53.493 | 1,51 | 1,51 | 55.004 | 96.295 |
| 2025 | 68.207 | 68.236 | 66.140 | 1,03 | 1,03 | 57.071 | 98.391 |
| 2026 (jan a ago) | 168.711 | 168.720 | 125.641 | 1,34 | 1,34 | 100.141 | 141.470 |

- O ajuste muda 2019–2021: o salto de 2019 some (805 em vez de 27.024).
- De 2022 em diante, quase nada muda.
- A diferença acumulada cai de 141.470 para 100.141.
- O painel não mudou nesta parte. O 208 ganhou `bev`, mas o 208 tem `flex`, e
  esta série é só das vigência-anos só-`bev`.

**2. Importação do agregado de carros contra o painel `importado`** (`ambos` a
0% e a 100%)

| ano | ajustada | publicada | razão mín–máx | razão publicada |
|---|---:|---:|---|---|
| 2003 | 72.985 | 92.792 | 1,20–1,81 | 1,52–2,30 |
| 2004 | 70.031 | 71.485 | 0,97–1,40 | 0,99–1,43 |
| 2005 | 96.162 | 98.086 | 1,10–1,43 | 1,12–1,46 |
| 2006 | 178.261 | 508.274 | **1,35**–1,63 | 3,85–4,66 |
| 2007 | 290.675 | 292.828 | **1,32**–1,62 | 1,33–1,64 |
| 2008 | 429.496 | 434.465 | **1,48**–1,83 | 1,50–1,85 |
| 2009 | 475.649 | 480.731 | 1,17–1,39 | 1,18–1,41 |
| 2010 | 699.276 | 702.264 | 1,22–1,39 | 1,22–1,40 |
| 2011 | 930.633 | 932.812 | 1,25–1,40 | 1,26–1,40 |
| 2012 | 726.784 | 730.690 | 1,05–1,18 | 1,06–1,19 |
| 2013 | 704.678 | 710.278 | 1,28–1,46 | 1,29–1,47 |
| 2014 | 577.458 | 583.127 | 1,16–1,40 | 1,18–1,42 |
| 2015 | 383.829 | 387.880 | 1,17–1,49 | 1,18–1,50 |
| 2016 | 231.966 | 235.717 | 0,92–1,17 | 0,93–1,19 |
| 2017 | 242.483 | 248.635 | 0,98–1,19 | 1,01–1,22 |
| 2018 | 342.405 | 347.124 | 1,08–1,23 | 1,09–1,24 |
| 2019 | 283.322 | 313.685 | 1,01–1,13 | 1,12–1,25 |
| 2020 | 165.842 | 198.094 | 0,88–0,97 | 1,05–1,16 |
| 2021 | 263.574 | 302.077 | 1,13–1,22 | 1,30–1,39 |
| 2022 | 289.079 | 294.249 | 1,18–1,24 | 1,20–1,26 |
| 2023 | 367.223 | 375.767 | 1,22–1,24 | 1,24–1,27 |
| 2024 | 516.680 | 529.850 | 1,26–1,30 | 1,29–1,34 |
| 2025 | 509.996 | 526.640 | 1,23–1,27 | 1,27–1,31 |
| 2026 (jan a ago) | 588.298 | 602.466 | **1,48**–1,50 | 1,52–1,54 |

**Anos de distância grande:** razão mínima, com as ajustadas, de 1,3 ou mais.

- Passam **2006, 2007, 2008 e 2026**.
- O 2006 entrou: antes eu tirava as linhas leves, e agora elas contam pelo peso
  (14.612 unidades).
- Os candidatos (`nacional` por `proposta`, maior volume) estão em
  `saidas/comex_origem_candidatos.csv`. Em 2006 são os mesmos carros de
  2007–2008 (Gol, Palio, Uno, Fox…).
- Não reclassifiquei nada.
- A importação sai um pouco abaixo da rodada passada também nos anos sem linhas
  leves (2025: 526.640 publicadas, contra 539.548), porque o 8703.10 saiu do
  agregado.

**3. Países de origem** (`saidas/comex_paises_top10.csv`). Colunas: `unidades`
ajustadas, `unidades_publicadas` e `unidades_8703`, que é 8703 sem 8703.10,
ajustado.

- **Argentina** é a primeira em todos os anos de 1997 a 2024, **inclusive
  2006**. Com a publicada, o México liderava 2006 pelas 306.783 unidades do
  dumper de peso. Ajustado, o México fica em segundo (22.073).
- **China** é a primeira em 2025 e 2026.
- **2025, ajustado:**
  - China 212.390 (publicada 228.450; só 8703: 207.351);
  - Argentina 191.649;
  - México 40.848.
  - O seu número da China (241.344) inclui as 12.894 unidades de 8703.10, que
    agora saem.
- **2026 (jan a ago):** China 391.838 (66,6% do ano), Argentina 116.676, México
  38.480.

### Erros e correções desta parte

- **CRLF de novo**, agora em `config/catalogo_usos.csv`, ao trocar o texto de
  uso do Comex. Restaurei antes do commit e passei a conferir o fim de linha de
  todos os arquivos tocados.

---

## Parte 3 — o calendário de políticas

### Fontes

**Só página oficial**, aberta nesta rodada e guardada em
`dados/bruto/politicas_paginas/` com URL e SHA-256 do texto no manifesto. São 55
páginas, comitadas em cinco lotes à medida que eram guardadas, e não uma por
commit (`e7f3062`, `ed1334d`, `7058e6c`, `516b224`, `ffb5133`):

- **Planalto** (41): decretos, medidas provisórias e leis;
- **Diário Oficial da União** (6): as resoluções Camex 86/2014 e 97/2015 e a
  Portaria GM/MDIC 151/2023, pelo visualizador de PDF da Imprensa Nacional;
- **gov.br** (5): as resoluções Gecex 532/2023, 774/2025 e 927/2026 (MDIC) e as
  resoluções Contran 311 e 312/2009 (Ministério dos Transportes);
- **Banco Central** (2): circulares 3.515/2010 e 3.563/2011;
- **Conama** (1): resolução 492/2018.

`tipo_fonte` é `oficial` em todos os 50 atos, pelo domínio, e há teste.

**O que não abriu:**

- matéria do DOU em `in.gov.br/materia/`: 403;
- notícias do gov.br: pedem autenticação ("Conteúdo Restrito");
- archive.org: 429.

O DOU veio pelo visualizador de PDF da Imprensa Nacional. As páginas antigas têm
duas ou três colunas, e o texto de colunas misturadas não serve para trecho. A
ferramenta de guardar páginas ganhou `--colunas`, que corta a página antes de
extrair. Notícia ajudou a achar ato em alguns casos e não é citada em lugar
nenhum.

### As duas tabelas

**`dados/referencia/politicas_atos.csv`: 50 atos.** São as suas colunas, mais
`tipo_fonte`, depois de `fonte_url`. `instrumento` fica numa lista fechada (lei,
medida provisória, decreto, resolução, circular, portaria).

| tema | atos | de | até |
|---|---:|---|---|
| IPI | 18 | 12/12/2008 | 01/11/2025 |
| regime automotivo | 6 | 01/01/2013 | 28/06/2024 |
| imposto de importação | 5 | 19/09/2014 | 01/07/2026 |
| acordo automotivo | 7 | 03/07/2008 | 01/07/2020 |
| crédito | 8 | 03/01/2008 | 22/01/2015 |
| desconto patrocinado | 2 | 06/06/2023 | 07/06/2023 |
| regulação | 4 | 01/01/2014 | 01/01/2025 |

**`dados/referencia/politicas_aliquotas.csv`: 216 linhas** (IPI 124, II 86, IOF
6). Só as alíquotas que o ato fixa. Acrescentei `pagina_salva`, porque várias
tabelas estão no anexo e não na página do decreto.

- **NCM:** com os pontos da TIPI e o Ex. Os dígitos sem pontos são prefixo da
  NCM do Comex Stat.
- **IPI de 2012 a 2017:** a alíquota da TIPI já inclui os 30 pontos do
  Inovar-Auto (37 = 7 + 30). A empresa habilitada tinha a redução.
- **IPI dos híbridos e elétricos em 2018:** uma linha por faixa de eficiência e
  de massa, para 8703.40, 8703.60 e 8703.80.
- **II:** os Ex-tarifários lidos das tabelas dos atos, com a quota quando há.
- **IOF:** a alíquota diária do crédito a pessoa física.

**A regra de uma alíquota por período.** Mesma NCM e categoria não têm dois
períodos que se cruzam. Quando um ato posterior fixa de novo a mesma linha, a do
anterior vale até a véspera do posterior. Se nem chegou a valer, sai. A etapa 13
falha se houver cruzamento. Três casos:

- a TIPI cheia de 16/12/2011 (Decreto 7.567) para em 21/05/2012, quando o 7.725
  reduz;
- a Gecex 774/2025 repete quatro Ex de desmontado da Gecex 532 com fim em
  31/12/2026 (era 30/06/2028). A linha da 532 para em 30/07/2025, e a da 774
  começa em 31/07/2025, quando ela entra em vigor, embora a tabela dela diga
  01/07/2025;
- o degrau de 14% do elétrico desmontado (8703.80.00 Ex 007), que a 532 marcava
  para 01/07/2026, sai: a 774 o antecipou antes de ele valer.

O Decreto 11.047/2022 está guardado e não é citado. Ele foi revogado pelo
11.055 antes de produzir efeito: os dois valiam a partir de 01/05/2022.

**`dados/processado/politicas_mensal.parquet`:** uma linha por mês e ato em
vigor, de 2008-01 a 2026-08 (1.924 linhas). Tem `comeca_no_mes`,
`termina_no_mes`, `dias_em_vigor` e `fracao_do_mes`. Junta ao painel pelo
`mes_ref`. Ato sem `vigencia_fim` vai até o último mês.

**A etapa 13** (`src/etapa13_politicas.py`, no pipeline antes da 6) confere:

- a página: arquivo, SHA-256 e URL;
- o ato: campos nas listas, datas, `altera_id`, URL igual à da página, fonte
  oficial e trecho literal;
- a alíquota: NCM no formato da TIPI, ato existente, trecho literal e uma por
  período.

Zero falhas. `testes/test_politicas.py` repete as guardas e testa as regras com
casos pequenos.

### As suas pistas, conferidas pelo ato

**Confirmadas:**

- **IPI 2008–2010:** decretos 6.687 (de 12/12/2008 a 31/03/2009), 6.809, 6.890
  (alta mês a mês de outubro a dezembro de 2009) e 7.017 (flex até 31/03/2010).
- **+30 pontos em 2011:** MP 540 e Decreto 7.567. O efeito começa em
  16/12/2011, pela redação do Decreto 7.604, e não na publicação (16/09/2011).
- **Ciclo de 2012:** decretos 7.725 (22/05/2012), 7.796, 7.834, 7.879, 7.971,
  8.168 e 8.279. A redução vai até 31/12/2014, e a alíquota cheia volta em
  01/01/2015.
- **IPI de 2022:** decretos 10.979 (25/02), 11.055 (01/05) e 11.158 (01/08).
- **Híbridos e elétricos em 2018:** Decreto 9.442, em vigor em 01/11/2018 (o
  quarto mês depois da publicação).
- **IPI Verde do Mover:** Decreto 12.549, em vigor em 01/11/2025.
- **Regimes:** Inovar-Auto (Lei 12.715 e Decreto 7.819, de 2013 a 2017), Rota
  2030 (MP 843 e Lei 13.755) e Mover (MP 1.205 e Lei 14.902).
- **II de eletrificados por volta de 2015:** são dois atos. A Camex 86, de
  setembro de 2014, cuida dos híbridos; a Camex 97, de outubro de 2015, põe o
  elétrico a 0%.
- **Gecex de novembro de 2023:** a 532 foi assinada em 20/11/2023 e vale a
  partir de 01/01/2024. Os degraus do montado são janeiro de 2024, julho de 2024
  e julho de 2025, com TEC de 35% a partir de julho de 2026. Vieram depois a 774
  (2025: desmontado e quotas) e a 927 (2026: quotas de julho a dezembro).
- **Quotas do México em 2012:** Decreto 7.706, com quotas desde 19/03/2012, e o
  8.419, que leva as quotas até 2019 e o livre comércio a 19/03/2019.
- **Flex com a Argentina:** decretos 6.500 (2008, até 30/06/2013), 8.278
  (2014), 8.477 (2015), 8.797 (2016 a 2020) e 10.343 (2020 a 2029).
- **IOF:** decretos 6.339 (03/01/2008, alta), 6.691 (12/12/2008, baixa), 7.458
  (09/04/2011, alta), 7.632 (02/12/2011, baixa) e 7.726 (23/05/2012, baixa).
  Acrescentei o 8.392 (22/01/2015, alta para 0,0082% ao dia).
- **Banco Central:** Circular 3.515 (crédito contratado desde 06/12/2010) e
  Circular 3.563 (11/11/2011). A 3.563 não é reversão inteira: isenta o veículo
  de até 60 meses e não revoga a 3.515, que fica sem fim.
- **Desconto de junho de 2023:** MP 1.175 (de 06/06/2023, por 120 dias, até
  03/10/2023) e Portaria GM/MDIC 151.
- **Air bag e ABS a 100% em 01/01/2014:** resoluções Contran 311 e 312, de 2009.
- **Proconve:** Conama 492/2018, uma linha por fase. L7 em 01/01/2022, L8 em
  01/01/2025.

**Não confirmadas, e fora:**

1. **O fim da quota de carros do desconto de 2023** (7/7/2023 na notícia do
   MDIC). Nenhuma página oficial aberta o dá. O ato fica com o prazo da MP.
2. **O protocolo com a Argentina de 01/07/2013 a 30/06/2014.** Não foi aberto.
3. **2003 a 2007.** As pistas começam em 2008, e eu não procurei atos antes
   disso. A tabela não tem nada nesses cinco anos, e isso não quer dizer que não
   houve política.

**Inferido, com a inferência na observação:**

- **O fim da Camex 97 em 31/12/2023.** A Gecex 532 tira os eletrificados do
  Anexo V da Gecex 272/2021 a partir de 01/01/2024. A passagem dos Ex da Camex
  97 para a Gecex 272 não foi aberta.

**Fins que tirei do próprio texto:**

- MP 540: 31/07/2016, o prazo da redução no texto original;
- MP 843 e MP 1.205: a data da lei de conversão;
- Camex 86: 26/10/2015, porque a Camex 97 dá nova redação aos mesmos Ex.

**Sem fim:** onze atos. Estão em vigor ou o fim não foi confirmado, e a
observação diz qual. O Decreto 9.442 é um deles. As alíquotas dele valem até
24/02/2022; daí em diante a estrutura segue com as reduções gerais de 2022, que
não registrei para 8703.40/60/80.

**Registrado e não feito:**

- as alíquotas de gasolina e de 8704 em 2013–2014;
- o IOF depois de 2015;
- o Decreto 10.923/2021 (a TIPI de 2022).

### 3.5 Uso-teste das datas

`saidas/politicas_uso_teste.csv` tem uma linha por data de efeito. São 61 datas:
o início de cada ato e cada mudança de alíquota que o próprio ato fixa depois
(degraus, volta da alíquota cheia).

**A série:**

- vendas do painel (automóveis e comerciais leves);
- no imposto de importação, a importação das NCMs do ato, em unidades ajustadas;
- no acordo automotivo, a importação do agregado de carros vinda do país
  parceiro.

**As colunas:** média dos 3 meses antes, o mês da data, média dos 3 meses
depois, e as mesmas janelas um ano antes.

**A marca de movimento é minha.** Você pediu para eu dizer onde a data não casa
com movimento, e a venda mensal tem sazonalidade forte: janeiro sempre cai
contra outubro–dezembro. Por isso comparo com o ano anterior. `movimento = sim`
quando a variação do mês, ou a dos três meses seguintes, contra os três
anteriores, difere da do ano anterior em 10 pontos ou mais.

Isso não estima efeito. `sim` não quer dizer que foi o ato, e o limiar pega
ruído também.

**Onde a data não casa com movimento (25 de 61): o lugar de conferir a data.**

| data | ato | série | 3 meses antes | mês | 3 meses depois | mês / antes | depois / antes | idem, ano anterior |
|---|---|---|---:|---:|---:|---:|---:|---|
| 03/01/2008 | decreto 6.339 | vendas | 228.540 | 203.880 | 218.714 | −10,8 | −4,3 | −18,8 / −8,1 |
| 09/04/2011 | decreto 7.458 | vendas | 255.068 | 268.463 | 286.761 | +5,3 | +12,4 | +4,8 / +2,5 |
| 11/11/2011 | circular BCB 3.563 | vendas | 283.009 | 299.813 | 266.889 | +5,9 | −5,7 | +6,8 / −3,3 |
| 02/12/2011 | decreto 7.632 | vendas | 282.054 | 321.114 | 252.938 | +13,8 | −10,3 | +21,3 / −13,0 |
| 16/12/2011 | decreto 7.567 | vendas | 282.054 | 321.114 | 252.938 | +13,8 | −10,3 | +21,3 / −13,0 |
| 01/01/2013 | decreto 7.879, lei 12.715, decreto 7.819 | vendas | 317.430 | 292.099 | 264.720 | −8,0 | −16,6 | −15,5 / −14,6 |
| 01/01/2014 | decreto 8.168, Contran 311 e 312 | vendas | 307.575 | 294.915 | 247.722 | −4,1 | −19,5 | −8,0 / −16,6 |
| 01/07/2014 | decreto 8.278 | importação da Argentina | 28.355 | 24.506 | 23.654 | −13,6 | −16,6 | −9,8 / −17,2 |
| 01/07/2014 | decreto 8.279 | vendas | 265.885 | 276.416 | 274.204 | +4,0 | +3,1 | +5,8 / +0,0 |
| 01/07/2015 | decreto 8.477 | importação da Argentina | 20.091 | 16.390 | 16.430 | −18,4 | −18,2 | −13,6 / −16,6 |
| 01/01/2018 | decreto 8.279 (degrau) | vendas | 197.795 | 174.591 | 186.160 | −11,7 | −5,9 | −18,1 / −10,9 |
| 06/07/2018 | MP 843 | vendas | 198.425 | 206.949 | 227.815 | +4,3 | +14,8 | +0,9 / +12,6 |
| 01/11/2018 | decreto 9.442 | vendas | 227.815 | 219.624 | 200.098 | −3,6 | −12,2 | −1,4 / −11,2 |
| 11/12/2018 | lei 13.755 | vendas | 221.895 | 222.782 | 191.724 | +0,4 | −13,6 | +4,7 / −9,9 |
| 01/01/2022 | Conama 492 (L7) | vendas | 166.540 | 115.608 | 129.300 | −30,6 | −22,4 | −25,1 / −23,3 |
| 06/06/2023 | MP 1.175, portaria 151 | vendas | 166.590 | 178.300 | 197.826 | +7,0 | +18,7 | +11,4 / +21,9 |
| 30/12/2023 | MP 1.205 | vendas | 196.334 | 233.853 | 158.958 | +19,1 | −19,0 | +12,0 / −19,3 |
| 28/06/2024 | lei 14.902 | vendas | 186.528 | 200.098 | 221.895 | +7,3 | +19,0 | +7,0 / +18,7 |
| 01/01/2025 | Conama 492 (L8) | vendas | 241.985 | 157.349 | 182.368 | −35,0 | −24,6 | −29,5 / −16,6 |
| 01/11/2025 | decreto 12.549 | vendas | 226.211 | 222.717 | 196.918 | −1,5 | −12,9 | +4,0 / −17,2 |

(A tabela agrupa as datas iguais com a mesma série; as 25 linhas estão no CSV.)

**O que eu leio nela, sem explicar efeito:**

- **A data de junho de 2023 é a que mais pede conferência.** O desconto não
  aparece contra 2022. Mas junho de 2022 é o mês seguinte ao corte de IPI de
  01/05/2022 (o 11.055 dá +34% no mês): a janela de comparação está contaminada
  por outra política.
- **A série não é o grupo afetado** em vários casos:
  - o +30 do Decreto 7.567 recai sobre a empresa não habilitada (sem 65% de
    conteúdo regional), e a série é a venda total;
  - os regimes (Inovar-Auto, Rota 2030, Mover) e o IPI Verde não mudam preço na
    data de início.
- **Prorrogação sem mudança de alíquota** não deveria mexer: 8.279 em julho de
  2014, 8.477 com a Argentina.
- **As datas de regulação** (air bag e ABS em 2014, L7, L8) caem em janeiro, e
  janeiro cai igual no ano anterior.

**Onde há movimento** (35 datas, no CSV). Alguns casos ajudam a ler a marca:

- **Batem com a data:**
  - 7.725 (22/05/2012): +44,2% nos três meses seguintes, contra +7,5% no ano
    anterior;
  - 11.055 (01/05/2022): +34,1% no mês, contra +5,2%;
  - a volta do IPI cheio em 01/01/2015: −33,3% contra −19,5% (no mesmo mês da
    alta do IOF do 8.392);
  - os degraus de julho de 2024 e julho de 2025 da Gecex 532: a importação das
    NCMs de eletrificados cai mais de 80% no mês do degrau, depois de três meses
    acima de 37 mil unidades;
  - as quotas do México de 2012: −26,4% contra +29,7%.
- **Mexe, mas não pelo ato:**
  - dezembro de 2008 (6.687 e 6.691): a janela anterior é a crise de
    outubro–novembro;
  - julho de 2020 com a Argentina (10.343): +231,7%, saída do fundo da
    pandemia;
  - a MP 540 (agosto de 2011): não muda alíquota na data, e a marca dá `sim` —
    é o ruído do limiar.
- **A data é a prorrogação, e o movimento fica em volta da data que ela
  adiou:** o 7.796 (01/09/2012) dá −24,3% no mês. A média de junho a agosto de
  2012 (361 mil) é a maior da tabela, e 31/08 era o fim que o 7.725 previa.
- **A série não vê o Ex:** Camex 86 e 97. Antes de 2017 a NCM não separa o
  híbrido nem o elétrico, e a série é a importação inteira de 8703.22.10 e
  8703.23.10 (e 8703.90.00), quase toda a combustão.

**Fora da série:** a Gecex 927 (01/07/2026). O Comex vai até 2026-08, e a janela
pede até 2026-10.

### 3.6 A próxima dimensão

A motorização (cilindrada pela coluna `motor` do PBE) está em
`QUESTOES_ABERTAS.md`, com o que já se sabe da coluna. Não construí nada.

### Erros e correções desta parte

- **Dois decretos fora do assunto guardados** (6.996/2009 e 8.035/2013). Saíram
  do manifesto e da pasta antes do commit.
- **PDF do DOU com colunas misturadas.** Resolvido com `--colunas`. O corte
  dava `ValueError` fora da caixa da página, e passou a usar a caixa da página
  com `strict=False`.
- **Leitura das tabelas da Camex:**
  - a tabela continua na página seguinte do DOU;
  - "Ex 002 -Automóvel" vem sem espaço;
  - o recorte do 8703.90 tem de parar em "III - Os Ex-tarifários".
- **Gecex:** o padrão com um hífen só juntava linhas. Corrigido.
- **Data do Decreto 7.632:** produz efeito no dia seguinte à publicação
  (02/12/2011), e não na data do ato.
- **Fim da MP 540.** Eu tinha anotado 31/12/2012, que é o prazo do Reintegra no
  art. 3º, não do IPI. O certo, pelo texto, é 31/07/2016 (art. 5º).
- **Fim do Decreto 6.691** (08/04/2011): o ato e a linha de IOF divergiam em um
  dia. Igualei.
- **Cruzamentos de alíquota.** A etapa 13 os apontou:
  - as linhas "a partir de 2010" e "a partir de 2018" não tinham fim;
  - a TIPI cheia de 2011 cruzava o ciclo de 2012.
  Fechei cada uma na véspera do ato seguinte e acrescentei a gasolina até 1.000
  cm³ dos decretos de 2012 (NC 87-7), que faltava.
- **Circular 3.515:** eu a tinha encerrado em 11/11/2011. A 3.563 não a revoga,
  e ela fica sem fim.

---

## Fechamento

`saidas/validacao.md` e `CATALOGO.md` foram regerados em árvore limpa, com os
testes passando, e comitados. A linha `rodada-11` está em `tags_pendentes.csv`.
