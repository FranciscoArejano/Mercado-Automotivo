# Registro de execução — casamento com o PBE, unidades do Comex e calendário de políticas

05/10/2026. Branch `claude/new-session-rs2chd`. Este registro vai no mesmo push
do trabalho que ele descreve.

## Em uma frase

__RESUMO__

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

__PARTE2__
