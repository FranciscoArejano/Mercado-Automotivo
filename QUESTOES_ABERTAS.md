# Questões abertas — registro de decisões

ESPEC.md §9.6: "Ao encontrar ambiguidade não coberta por este documento: parar,
descrever o caso, propor as opções e esperar decisão."

Este arquivo é o cumprimento dessa regra e o registro do que já foi decidido.
As dez questões levantadas na primeira rodada foram respondidas pelo
pesquisador; abaixo, o que ficou decidido, o que o código faz agora, e o que
**continua aberto**.

## Estado, num relance

| # | Assunto | Situação |
|---|---|---|
| Parte 0 | `regras.csv` vazio nesta rodada | decidido e aplicado |
| B1 | HHI de grupo menor que HHI de marca em 2014 | **causa encontrada e corrigida** |
| B2 | Buraco de 2023-09 | **recuperado da fonte** |
| B3 | `volume_em_jogo` ordenando errado | corrigido |
| I1 | Cauda mais rasa que a planilha de controle | **fechado: truncamento nas unidades, colapso de variante na contagem** |
| I2 | Taxa de entrada não responde ao limiar | confirmado: é desenho, documentado |
| I3 | O corte de publicação fabrica a alta recente? | **resolvido pelo piso de volume: a alta é real até 2025; 2026 é artefato** |
| Q1 | Leitura de "pico móvel de 12 meses" | **encerrada com a regra de banda** |
| Q2 | Tolerância de 0,5% e piso de cobertura | decidido; piso medido, não aplicado |
| Q3 | Mapa de grupos econômicos | decidido; variante de robustez disponível |
| Q4 | Chave do painel e sub-segmento | decidido e aplicado |
| Q5 | O que significa "zero" | decidido; sinalização entregue |
| Q6 | Retroagir a 2003 | **feita**: a série começa em 2003-01 |
| Q7 | Ranking completando sub-segmento | decidido, mantido |
| Q8 | "Julho de 2023, maior mês desde 2019" | premissa corrigida na ESPEC |
| Q9 | Detector de queda abrupta | decidido e aplicado |
| Q10 | Censura à esquerda | formulação transportada para a ESPEC §5 |
| Rodada 2 | Modelos fantasma dominam a rotatividade | **achado novo, decomposto por piso de volume** |
| D1 | Duplicata por caixa (`Outlander`/`OUTLANDER`) | corrigido |
| D2 | Linhas que não são modelos | sinalizadas, nada apagado |
| D3 | Dois números para zeros frágeis | reconciliado |
| Rodada 3 | Série estendida a 2003-01 | **rodada: 284 meses, 57,8 milhões de unidades, 940 modelos** |
| D4 | 2013-11 é edição defeituosa na origem (marca trocada) | **detectado, reportado, não corrigido** |
| D5 | Duas edições curtas do informe (2003-10, 2005-03) | **medidas; completar é decisão do pesquisador** |

---

## Rodada 2 — o achado que muda a leitura das taxas

**207 dos 647 modelos somam 3.504 unidades em treze anos** — 0,012% do volume — e
cada um conta como uma entrada e uma saída. São registros avulsos, conversões de
encarroçador e erros de cadastro: `FIAT/FIAT`, `FORD/ENGERAUTO SPARTAKUS`,
`VW/ZILK`, `TOYOTA/RIBEIRAUTO`. Eles respondem por **30% a 55% de todas as
entradas e saídas**, ano a ano.

**Na série estendida a 2003 o problema é maior, e é pior nos anos antigos.**
São **363 dos 940 modelos — 39% da contagem — com 5.988 unidades em 24 anos**,
0,010% do volume. E a proporção que eles tomam da rotatividade cai ao longo da
série: em 2003 são 69% das entradas e **83% das saídas**; de 2012 a 2016 ficam
entre 19% e 36%; nos anos recentes voltam para a faixa de 40%. Ou seja, a
contaminação **não é constante no tempo** — ler a coluna "todos" não só infla as
taxas, como infla mais o começo da série que o meio. Era o item 4 de "o que
continua aberto" da rodada 2, e está respondido.

As taxas da §8 do relatório não mediam rotatividade de portfólio: mediam
rotatividade **mais** ruído de cadastro, em proporção parecida. É maior que
qualquer problema discutido antes, porque essa é a variável dependente do artigo
de escopo de produto.

**O que foi feito.** Nada foi filtrado do painel — a Parte 0 continua valendo.
A §8 passou a trazer as taxas sob **três pisos de volume total do modelo**:
todos, acima de 100 unidades, acima de 1.000. O piso entra no numerador e no
denominador. O relatório abre com a advertência de que **nenhuma leitura
substantiva deve sair da coluna "todos"**, e `saidas/taxas_por_piso_de_volume.csv`
traz contagens e denominadores.

---

## Parte 0 — A base primeiro, a harmonização depois

**Decidido.** `regras.csv` fica **vazio** nesta rodada. `saidas/candidatos.xlsx`
é evidência arquivada, não adjudicada. Nada é fundido.

A consequência foi explorada: as taxas de entrada e saída em
`saidas/validacao.md` §8 são o **limite superior** dessas taxas — o cenário em
que todo rebatismo conta como morte e nascimento. Quando a adjudicação vier,
teremos os dois extremos e saberemos quanto a harmonização move o resultado.
O relatório e o dicionário de dados dizem isso em texto, para que ninguém leia
essas taxas como se fossem o número final.

Quando a adjudicação vier, será em duas camadas — canônica (o que é fato em
qualquer artigo) e sobreposição por artigo (o que é leitura). O pipeline já
suporta as duas: a camada canônica é `regras.csv`, e uma sobreposição por
artigo é outro arquivo de regras passado à etapa 5.

---

## Os três defeitos da rodada 1

### B1. HHI de grupo menor que HHI de marca em 2014 — causa encontrada

O diagnóstico do pesquisador estava certo no princípio e a causa era outra:
não era denominador nem balde `NAO_MAPEADO`. **A identidade
`hhi_grupo ≥ hhi_marca` exige partição fixa**, e num agregado *anual* com mapa
datado ela não é fixa. Em 2014 a Fiat está no grupo `FIAT` até setembro e em
`FCA` de outubro em diante: o volume anual da marca **se parte em dois grupos**,
e o HHI de grupo cai. Os únicos três casos são FIAT, JEEP e DODGE, cuja
propriedade muda em outubro de 2014 — exatamente o único ano que invertia.

Três consequências no código:

1. A identidade é exigida **por mês**, onde a partição é fixa. Vale nos 152
   meses, e agora é verificação com falha de execução.
2. O agregado anual ganhou a coluna `hhi_grupo_particao_fixa`, que usa o grupo
   vigente num **mês de referência declarado** (o último mês do ano no painel).
   Com ela 2014 passa de 1.169,5 para **1.349,0**, acima dos 1.317,4 de marca,
   como a identidade manda. A coluna `hhi_grupo_datado` fica ao lado, e os anos
   de transição são listados.
3. Marca sem grupo vigente entra como **grupo unitário com o próprio nome** —
   nunca excluída, nunca num balde comum. São 19 marcas e 1.906 unidades
   (0,006% do painel), contadas em `saidas/validacao.md` §6.

### B2. O buraco de 2023-09 — recuperado

O informe de setembro de 2023 é um PDF inteiramente digitalizado. O OCR foi
tentado e **rejeitado pela própria verificação**: 21,6% do volume divergia
entre o ranking e as tabelas de sub-segmento do mesmo arquivo.

A recuperação veio pelo caminho que o pesquisador apontou: **o informe de
2023-10 republica setembro inteiro**, na coluna de mês anterior, modelo a
modelo, e também no Resumo Mensal. Isso não é interpolação nem estimativa — é
uma segunda publicação do mesmo número pela mesma fonte.

- 167 linhas recuperadas, 184.624 unidades (143.965 automóveis, 40.659 leves).
- Total publicado de setembro também recuperado: 145.676 e 41.754.
- **Confirmação independente pelo acumulado** — `acum(out) − mês(out) −
  acum(ago)` — bate em 122 de 151 modelos, com 39 unidades de diferença
  absoluta e 37 líquidas. As duas rotas concordam.
- Toda linha sai com `origem_tabela='mes_anterior'` e
  `metodo_extracao='reconstruido'`; o mês fica como `ok_reconstruido`.

A série não tem mais buracos: 284 meses, nenhuma lacuna.

O registro dessa
recuperação agora sobrevive a uma rodada que reaproveita a extração já gravada —
antes ele era reescrito do zero e sumia, deixando o painel marcando
`origem_tabela='mes_anterior'` sem procedência no relatório.

### B3. `volume_em_jogo` — corrigido

Passou a ser `min(unidades_origem, unidades_destino)`: é o menor que limita
quanta substituição o par pode explicar. A soma continua disponível em
`volume_somado`. Com a correção, `VW/GOL → VW/BRASILIA` some do topo e a lista
começa por Prisma → Onix Plus (440.598) e Palio → Argo (390.713).

---

## As três investigações da rodada 1

### I1. Cauda mais rasa que a planilha de controle — **fechado, com dois mecanismos**

O cruzamento com `Vendas_Geral.xlsx`, ano de 2014: 147 modelos casam
exatamente, 48 casam por família, e **115 não têm contraparte alguma, somando
44.737 unidades** — praticamente as 43.740 que a cobertura apontava como
faltantes em automóveis. **Truncamento confirmado nas unidades.** Os 115 têm
mediana de 65 unidades no ano; 99 vendem menos de 500. É cauda premium e de
nicho: Audi A1, Mini Countryman, BMW X5, Mercedes GLC, CAOA Chery Face.

**Mas a contagem de modelos tem um segundo mecanismo, e o teste de barra no nome
não o via.** A planilha traz `Pajero TR4` (7.519), `Pajero HPE` (4.800) e
`Pajero Full` (2.429) — três veículos; o painel traz uma única ficha
`MITSUBISHI/PAJERO`, **sem barra nenhuma**. A agregação é invisível para o teste
de `MARCA/A/B`, que encontra só três casos no painel inteiro e concluía que a
fonte quase não agrega.

**O que foi feito.** A etapa 7 ganhou busca de colapso por **cardinalidade de
família**: agrupa os dois lados pela primeira palavra do nome do modelo e
reporta as famílias em que a planilha tem mais entradas que o painel
(`saidas/colapsos_de_variante.csv`). A família é heurística de busca, não
classificação — aponta onde olhar, e o resultado vai para revisão humana.
Casos como Cruze e Etios ficam de fora por construção: são dois produtos dos
dois lados, só com nomenclatura diferente.

A etapa 7 também passou a produzir `saidas/so_na_planilha.csv`, a medida direta
do truncamento.

**Falta só rodar.** `Vendas_Geral.xlsx` ainda não está em `dados/referencia/`.
Com o arquivo no lugar, `python src/etapa07_referencia_cruzada.py` refaz isso
contra o painel completo, e não só contra as fichas.

### I2. A taxa de entrada não responde ao limiar — confirmado, é desenho

Confirmado: **a entrada é o primeiro mês com unidades positivas e não usa o
limiar**; só a saída aplica D3, que foi o que a ESPEC especificou. Por isso as
três colunas de entrada são idênticas nos 24 anos.

A assimetria está agora declarada em três lugares: no dicionário de dados, na
seção 8 do relatório de validação, e aqui. Ela entra direto em qualquer
decomposição de margens, e quem for usar essas margens precisa decidir se quer
um critério simétrico — a decisão continua sendo do pesquisador.

### I3. O corte de publicação fabrica a alta recente? — **resolvido: a alta é real até 2025**

Duas correções no caminho até a resposta, ambas minhas.

**Primeira: a métrica do enunciado estava errada.** A truncagem da Fenabrave não
é um piso de unidades: é **número fixo de linhas por sub-segmento**. "Suv's" traz
40 modelos no teto e nunca menos de 35 nos 284 meses; "Furgões", 7 sempre. A série "corte mediano
99 → 396" media o tamanho do modelo mediano da fonte, que sobe porque o mercado
se concentrou. Medido corretamente, o corte **não sobe em automóveis** — mediana
entre 3 e 21 unidades — e **sobe muito em comerciais leves**, de 25 unidades em
2014 para 172 em 2026.

**Segunda: o teste que montei não tinha poder, e apontou para o lado errado.**
O subconjunto imune ao corte tem 98 modelos e mediana de 5 saídas por ano; ali a
alta "desaparecia", e eu li isso como indício de artefato. Com o piso de volume —
190 a 197 modelos em vez de 98 — o teste ganha poder e responde o contrário:

| piso | 2022 | 2025 | variação |
|---|---:|---:|---:|
| todos | 0,120 | 0,195 | **+0,075** |
| acima de 100 unidades | 0,079 | 0,174 | **+0,095** |
| acima de 1.000 unidades | 0,068 | 0,149 | **+0,081** |

(Números da série estendida, 2003-01 a 2026-08. Na janela de 2014 em diante eram
+0,063, +0,085 e +0,063 — mesma conclusão, magnitude um pouco maior.)

**A alta não some com o piso — ela se mantém ou aumenta.** É movimento real de
portfólio entre 2022 e 2025, e não artefato nem do corte nem dos fantasmas.

E o salto de 2026 **inverte de sinal** assim que o piso entra: +0,030 com todos,
−0,031 acima de 100, −0,065 acima de 1.000. É fantasma somado a ano incompleto.
**2026 não é citável para rotatividade**, e o relatório diz isso antes da
primeira tabela.

O subconjunto imune fica no relatório como conferência secundária, com a ressalva
de que não decide nada sozinho.

---

## Os três defeitos da rodada 2

### D1. Duplicata por caixa — corrigido

A fonte escreveu `MITSUBISHI/Outlander` de 2014-01 a 2022-07 (35.231 unidades) e
`MITSUBISHI/OUTLANDER` em 2022-12 (8 unidades). Sem normalização, o mesmo carro
virava duas fichas, com uma saída e uma entrada fabricadas.

**A chave do painel passou a ser canonizada em caixa.** Isso não contraria a
ESPEC §4, que proíbe uniformizar maiúsculas *na transcrição*: `grafias_fonte` e
`nome_completo_fonte` guardam a grafia crua, letra por letra. E não é fusão de
modelos: não há decisão metodológica em dizer que `Outlander` e `OUTLANDER` são
a mesma cadeia de caracteres. Fusão de produtos distintos continua exigindo
linha em `regras.csv`. `saidas/colisoes_de_caixa.csv` registra o que foi
unificado — hoje só esse par, mas a retroação a 2003 multiplicava a chance de
reincidência, e é por isso que a regra entrou agora.

### D2. Linhas que não são modelos — sinalizadas, nada apagado

`FIAT/FIAT`, `FIAT/FAG`, `FORD/ENGERAUTO SPARTAKUS`, `VW/ZILK`,
`TOYOTA/RIBEIRAUTO`. O painel ganhou `nome_suspeito` e `motivo_nome_suspeito`;
`saidas/nomes_suspeitos.csv` traz os candidatos a revisão humana.

A marcação automática cobre só o caso **objetivo** — nome do modelo igual ao da
marca. O resto vem de `config/nomes_nao_veiculo.csv`, lista curada com motivo
por linha, porque volume baixo não serve como critério nos dois sentidos:
`TOYOTA/RIBEIRAUTO` soma 67 unidades em 25 meses e escaparia de qualquer corte,
enquanto `CITROEN/C4` e `DODGE/CHARGER` têm uma unidade só e são carros de
verdade. São 29 nomes marcados hoje na série 2003-2026 — eram 21 na janela de 2014 em diante.

### D3. Dois números para zeros frágeis — reconciliado

Ver Q5. Os 5.609 vinham da métrica de corte errada; o número corrente sai do
relatório, e a definição está fixada lá.

---

## Rodada 3 — a série estendida a 2003

A retroação foi feita: **284 meses, de 2003-01 a 2026-08**, 54.188 linhas de
fonte, **57.765.831 unidades**, 940 modelos. O invariante central — soma do
painel igual ao total que a fonte publica, dentro da tolerância — vale nos 284
meses. Nenhum informe precisou de OCR e nenhum ficou sem linha.

O que a série antiga trouxe de novo, além do achado dos fantasmas acima:

### D4. 2013-11 é edição defeituosa na origem

O informe de Nov/2013 publica `PONTIAC/MONTANA` (3.901 unidades), `FORD/KOMBI`,
`VW/RANGER`, `FORD/MASTER`, `THINK/CITY` — e um `/ELANTRA` sem marca nenhuma.
São **12 modelos sob marca trocada, 12.355 unidades, 11 marcas fantasma** num
único mês.

**Não é erro de leitura.** Verificado no PDF: `PONTIAC/MONTANA` é um objeto de
texto único em x0=382,08, exatamente como os vizinhos corretos. Foi a fonte que
trocou a coluna naquela edição.

O efeito é pior que um número errado: cada troca fabrica uma marca fantasma com
uma entrada e uma saída, e tira o volume da marca certa naquele mês. Quem usar
séries **por marca** precisa decidir o que fazer com 2013-11.

`src/comum/marca_do_modelo.py` detecta isso pela redundância da própria série —
um modelo que aparece sob a mesma marca em ≥90% dos meses e destoa num — e
**não corrige nada** (ESPEC §9.4). São 55 pares (mês × modelo) na série inteira,
em `saidas/marca_divergente.csv`. Nem toda divergência é defeito: `TIGGO 7` sob
`CHERY` em 2019-2020 contra `CAOA CHERY` depois é **troca real de marca**. O
teste aponta; a leitura é humana.

Sobre grupos econômicos: `PONTIAC` entrou em `config/mapa_grupos.csv` com
vigência 2003-01 a 2010-10, que é quando a marca existiu. Em 2013-11 o mapa
devolve `('PONTIAC', False)` — sem grupo —, e isso está **certo** sob D4: o mapa
nunca é retroativo nem pós-datado. Atribuir grupo não conserta o defeito; só
registraria de quem a marca era.

### D5. Duas edições curtas do informe

O informe normal tem 44 páginas e 17 sub-segmentos na tabela por modelo.
**2003-10 (Ed. 10) e 2005-03 (Ed. 27) saíram com 10 páginas** e trazem **um**
sub-segmento. São as edições corretas dos meses certos — o cabeçalho confere —,
só que abreviadas na origem.

Ali o mês é carregado quase inteiro pelo ranking mensal: o **total bate** com o
publicado (99,0% de cobertura nos dois), porque o ranking cobre o topo, mas o
**elenco de modelos fica pela metade**: 89 e 87 fichas contra ~180 nos meses
vizinhos.

Consequência: nesses dois meses um modelo de cauda some sem ter saído do
mercado. Não vira saída — D3 olha o pico móvel de 12 meses —, mas vira zero
frágil e entra na contagem de modelos do ano.

**Nada foi completado.** A coluna de mês anterior do informe seguinte
recuperaria o elenco, do mesmo jeito que recuperou 2023-09; mas isso misturaria
linha lida direto com linha republicada **dentro do mesmo mês**, e a regra de
mistura é decisão do pesquisador, não do código (§9.6). A detecção está em
`truncamento.edicoes_abreviadas` e a lista em `saidas/edicoes_abreviadas.csv`.

*Opções, se o pesquisador quiser fechar isso:* (a) deixar como está e tratar os
dois meses como parcialmente observados na análise; (b) completar o elenco pela
coluna de mês anterior, marcando as linhas acrescentadas com
`origem_tabela='mes_anterior'`, de modo que a mistura fique visível linha a
linha; (c) excluir os dois meses das contagens de modelos, mantendo-os nos
volumes. A recomendação do código é (b), porque é a única que não perde
informação nem esconde a origem — mas nada foi escrito.

### Os 284 informes passaram a ser versionados

O `.gitignore` excluía `dados/bruto/pdf/` desde a primeira rodada, com a
justificativa escrita no README de que "são pesados e a etapa 01 os rebaixa
idênticos". Isso nunca foi regra da ESPEC — foi escolha de implementação minha,
e a ESPEC só exige que `bruto/` seja intocado e tenha manifesto com hash (§1,
§9.3). **Decisão do pesquisador: reverter a escolha.** Os 284 informes, de
2003-01 a 2026-08 (~1,0 GB), estão agora em `dados/bruto/pdf/`.

Foi em dois passos, e vale registrar por quê. Primeiro entraram só os de
2003-2013, com o raciocínio de que a premissa "a etapa 01 os rebaixa idênticos"
pressupõe que a fonte continue servindo o arquivo — coisa que a Fenabrave tem
interesse em fazer com os informes recentes e nenhum com os de vinte anos atrás,
que somem numa reformulação de site sem aviso. Depois entraram os de 2014-2026
também: ali o risco é menor, mas não é zero, e uma regra sem exceção é mais
fácil de sustentar do que uma assimetria que alguém precisa lembrar de explicar.

O manifesto com os SHA-256 continua ao lado deles, então a conferência não
depende de confiar no repositório: qualquer cópia futura bate contra o hash.

Custo aceito: cerca de 1 GB para clonar.

### Duas variantes de grafia de sub-segmento

O informe de **2017-04** escreve `Pickup's Grandes` e `Pickup's Pequenas` onde os
outros 283 meses escrevem `Pick-up's Grandes` e `Pick-up's Pequenas`. Entraram em
`config/sub_segmentos.csv` como linhas próprias, com o segmento correto e o
motivo registrado — não foram renomeadas, porque o painel guarda o que a fonte
publicou. Sem efeito mensurável na truncagem: os tetos das duas grafias
coincidem (11 e 6 linhas).

### Correção: 2003 e 2005 não são os anos de cobertura mais fraca

O diagnóstico de retroação previa 2003 e 2005 como os piores anos de cobertura
(95,4% e 95,0% em automóveis) e a rodada 2 pediu que fossem registrados assim.
**A extração completa desmente isso**: ficam em 99,61% e 99,72%, na faixa dos
melhores anos da série.

A diferença é de método, não de dado. O diagnóstico somava só a tabela por
sub-segmento e tirava média entre meses; o painel também usa o ranking mensal
para completar a cauda. E os 4 pontos inteiros vinham dos **dois meses do D5**,
não do ano.

Os anos de cobertura mais fraca da série são **2026 (95,81%, parcial), 2025
(97,67%) e 2011 (97,89%)** — todos recentes. A deriva de cobertura em automóveis
é de −3,80 pontos entre 2003 e 2026, e ela anda **contra** a intuição de que os
informes antigos seriam piores.

---

## As dez questões

**Q1 — pico móvel. ENCERRADA, com uma regra que vale mais que a escolha.**
Mantido `media_movel`, por princípio: um lote isolado de venda direta não é a
escala do produto, e `max_movel` numa série completa degenera para o pico
global, o que esvazia a palavra "móvel".

A comparação mostrou que **14 dos 24 anos mudam de posição** entre as duas
leituras, e daí sai a regra: **a ordenação de anos por taxa de saída não é
identificada** no nível de precisão em que as duas leituras discordam. Só
afirmar diferença entre dois anos quando ela sobreviver às duas. **Reportar
banda, não ponto.**

O que sobrevive, medido entre anos consecutivos completos com variação acima de
3 pontos percentuais no mesmo sentido: o **degrau de 2015 para 2016** (a taxa
praticamente dobra nas duas leituras, +0,078 e +0,059) e o de **2017 para 2018**
(+0,040 e +0,032). O que não sobrevive é qualquer ordenação fina entre os anos
do meio. O relatório traz a regra e a lista em texto, na §8.

**Q2 — tolerância e piso. Adotado.** As três verificações internas ao documento
estão no lugar. Sobre D5: **o piso não é aplicado ao painel.** O que a rodada
entrega é a medida — cobertura por ano e segmento, corte de publicação por mês
— e uma recomendação: **piso de 300 unidades por modelo e mês**, que reduz a
amplitude da cobertura anual de 2,70 para 1,17 pontos percentuais e descartaria
1.073.128 unidades (3,6% do painel). A tabela inteira de pisos candidatos está
em `saidas/piso_recomendado.csv`. Parâmetro, não dado.

**Q3 — mapa de grupos. Adotado, com as quatro escolhas confirmadas.**
Renault-Nissan-Mitsubishi separados, Hyundai e Kia juntos, CAOA Chery como
grupo próprio, Omoda/Jaecoo e Jetour no grupo Chery. Verificado: as 14 linhas
da Stellantis vigoram a partir de 2021-01, e **todas as 141 linhas do mapa têm
`fonte` preenchida**. A variante de robustez pedida está em
`src/ferramentas/robustez_grupos.py`, que roda Kia separada por padrão e aceita
qualquer outro remapeamento na linha de comando. **Resultado: separar Kia de
Hyundai move o HHI de grupo em no máximo 10,3 pontos (0,87%), em 2014-2016, e
menos de 3 pontos de 2023 em diante.** A convenção não é consequente para
concentração; `saidas/robustez_grupos.csv` traz a tabela ano a ano.

**Q4 — chave do painel. Adotado, com a emenda.** A chave é
`(marca, modelo, segmento)`, e **o sub-segmento passou a ser atributo da
linha, fora da chave**. Onde a fonte publica o mesmo modelo em dois
sub-segmentos no mesmo mês, as duas linhas ficam separadas no painel; a soma
por modelo virou uma *visão* (`comum/visoes.py`), não o esquema. A ESPEC foi
corrigida: geração é invisível na maior parte dos casos, não em todos.

**Q5 — o que significa "zero". Adotado, com a sinalização.** Mês com informe em
que o modelo não aparece é zero; lacuna é ausente. O painel ganhou a coluna
`corte_publicacao` e `saidas/zeros_frageis.csv` lista os pares modelo × mês em
que o corte está **acima** do limiar de D3 do próprio modelo.

**D3 — os dois números reconciliados.** Os 5.609 que este arquivo trazia vinham
da métrica de corte errada (o menor valor publicado no mês inteiro), que
superestimava a truncagem. Com o corte medido por bloco, o número é o do
relatório. A definição, para não haver terceira versão: **par (modelo, mês) em
que o modelo não aparece, o mês está entre a entrada e a saída do modelo no
limiar de 5%, e o corte do bloco em que ele seria listado supera o limiar de D3
dele.** O número corrente sai sempre de `saidas/validacao.md` §8 e de
`saidas/zeros_frageis.csv`; este arquivo não o repete mais.

**Q6 — retroagir a 2003. FEITA.** O diagnóstico não deixou argumento contra:
132 informes de 2003-01 a 2013-12, **todos com tabela por modelo**, nenhum
precisando de OCR ou de tradução de glifos, cobertura média de automóveis entre
95,0% (2005) e 99,8% (2004) — a mesma ordem dos anos recentes — e **nenhuma
deriva de agregação**: um único nome composto no período inteiro, o mesmo
`VW/FOX/CROSS FOX`, presente desde 2003.

O ganho é o que faltava na janela de 2014: o boom até 2012, as reduções de IPI
de 2008-2009 e de 2012, e o Inovar-Auto. Para o artigo de escopo de produto, é a
diferença entre uma recessão e um ciclo completo.

**Um defeito encontrado no caminho, e não era de parsing.** O catálogo da
Fenabrave aponta o mês 2005-04 para `3_2005_05_2.pdf`, que é a edição 29 e se
declara "Resumo Mensal Maio de 2005" — o mesmo conteúdo servido em 2005-05. O
informe de abril existe, é a edição 28, e está em `3_2005_04_2.pdf`, só não
listado. Foi o teste de mês declarado que pegou. A correção entrou em
`config/correcoes_catalogo.csv`, com motivo e evidência por linha.

`PERIODO_INICIO` passou a ser `2003-01`. A série tem hoje **284 meses, 54.188
linhas de fonte, 57.765.831 unidades e 940 modelos**, com o invariante central
válido nos 284 meses.

O pedido de "registrar 2003 e 2005 como os anos de cobertura mais fraca" **não
se sustentou na extração completa** — ver a seção da rodada 3: a média do
diagnóstico vinha de duas edições curtas, e os anos fracos são os recentes. A
decomposição por piso de volume da §8 vale para a série estendida e mostrou que
a proporção de fantasmas é **maior** nos anos antigos, não igual.

**Q7 — ranking completando sub-segmento. Mantido.** Tabela de sub-segmento como
base, ranking preenchendo o que ela não lista, `origem_tabela` registrando a
procedência, divergências reportadas sem correção.

**Q8 — julho de 2023. Premissa corrigida.** A ESPEC §6 passou a dizer "maior
mês desde janeiro de 2021", que se confirma, e ganhou o segundo teste: julho de
2023 supera junho em pelo menos 15% — medido, **+20,0%** tanto no painel quanto
no total publicado. Registrados: máximo da série inteira em dezembro de 2014
(353.567 unidades, quando o mercado era muito maior) e máximo desde 2019 em
dezembro de 2025 (267.117). A rotina que roda cada teste duas vezes, no painel
e na fonte, e separa "bug nosso" de "premissa não confirmada", ficou e vale
para todo teste de sanidade.

**Q9 — queda abrupta. Adotado (b) mais (c).** A queda passou a ser medida
**depois de descontada a variação do próprio segmento no mês**, e a série
precisa ter ao menos 100 unidades antes da queda. A coluna
`variacao_mercado_no_mes` ficou, documentando o filtro. Efeito: os pares caem
de 819 para **212** (175 por passagem de bastão, 37 por queda abrupta), e os
que sobram são casos de verdade — Punto → Argo, BYD Song Plus → King,
Iveco Daily 3514 → Daily 35S14 (correlação −0,95).

**Q10 — censura. Nada a decidir; formulação transportada.** A ESPEC §5 agora
distingue as duas exclusões: censura à esquerda invalida a **entrada** e
descarta o modelo como *sucessor*; censura à direita invalida a **saída** e o
descarta como *quem sai*. Um modelo vivo no primeiro mês continua podendo sair
— é o caso do Prisma. `testes/test_candidatos.py` trava o comportamento.

---

## O que continua aberto

1. **Adjudicação de `regras.csv`** — por decisão da Parte 0, para quando o
   desenho do artigo de escopo de produto estiver fechado. Enquanto isso, as
   taxas são o limite superior.
2. **Cruzamento com `Vendas_Geral.xlsx`** — a etapa 7 está pronta, com busca de
   colapso por cardinalidade de família e a lista de modelos sem contraparte.
   Falta o arquivo em `dados/referencia/`.
3. **O mapa de grupos** é rascunho revisado, não fato. As quatro convenções
   discutíveis continuam sendo convenções; separar Kia de Hyundai move o HHI em
   no máximo 0,87%.
4. **Revisão de `config/nomes_nao_veiculo.csv`** — 29 nomes marcados,
   `saidas/nomes_suspeitos.csv` traz os 180 candidatos a revisão humana. A
   retroação a 2003 multiplicou a lista de nomes de volume ínfimo.
5. **O que fazer com 2013-11** (D4) em qualquer série por marca. O painel
   registra o defeito e não decide.
6. **As duas edições curtas** (D5): manter como está, completar pela coluna de
   mês anterior, ou excluir das contagens de modelos. Três opções descritas
   acima; nenhuma aplicada.

---

## Regras que passaram a valer para qualquer artigo

1. **Nenhuma leitura de rotatividade sai da coluna "todos"** das taxas de
   entrada e saída. Use os pisos de volume.
2. **O ano parcial não é citável** para rotatividade. Hoje é 2026.
3. **Diferença entre dois anos só se afirma quando sobrevive às duas leituras de
   "pico móvel"** (Q1). Banda, não ponto.
4. **Todo teste de sanidade roda duas vezes**, no painel e no total publicado
   pela fonte, e separa "bug nosso" de "premissa não confirmada".
5. **A contaminação por fantasmas não é constante no tempo** — é mais forte em
   2003-2011 que no meio da série. Comparar anos distantes exige piso de volume,
   não só advertência.
