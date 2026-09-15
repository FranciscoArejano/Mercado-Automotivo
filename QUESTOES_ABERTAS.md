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
| I1 | Cauda mais rasa que a planilha de controle | **parcial — falta a planilha** |
| I2 | Taxa de entrada não responde ao limiar | confirmado: é desenho, documentado |
| I3 | O corte de publicação fabrica a alta recente? | **inconclusivo; a métrica do enunciado estava errada** |
| Q1 | Leitura de "pico móvel de 12 meses" | **continua aberta — a escolha importa** |
| Q2 | Tolerância de 0,5% e piso de cobertura | decidido; piso medido, não aplicado |
| Q3 | Mapa de grupos econômicos | decidido; variante de robustez disponível |
| Q4 | Chave do painel e sub-segmento | decidido e aplicado |
| Q5 | O que significa "zero" | decidido; sinalização entregue |
| Q6 | Retroagir a 2003 | diagnóstico rodado; extensão **não** feita |
| Q7 | Ranking completando sub-segmento | decidido, mantido |
| Q8 | "Julho de 2023, maior mês desde 2019" | premissa corrigida na ESPEC |
| Q9 | Detector de queda abrupta | decidido e aplicado |
| Q10 | Censura à esquerda | formulação transportada para a ESPEC §5 |

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

## Os três defeitos

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

A série não tem mais buracos: 152 meses, nenhuma lacuna.

### B3. `volume_em_jogo` — corrigido

Passou a ser `min(unidades_origem, unidades_destino)`: é o menor que limita
quanta substituição o par pode explicar. A soma continua disponível em
`volume_somado`. Com a correção, `VW/GOL → VW/BRASILIA` some do topo e a lista
começa por Prisma → Onix Plus (440.598) e Palio → Argo (390.713).

---

## As três investigações

### I1. Cauda mais rasa que a planilha de controle — **parcial**

**O que falta:** `Vendas_Geral.xlsx` não está no repositório. Sem ela não dá
para listar os modelos presentes na planilha e ausentes do painel em 2014, que
é metade da investigação. A etapa 7 está pronta e roda no instante em que o
arquivo aparecer em `dados/referencia/Vendas_Geral.xlsx`.

**O que já foi medido**, pelo outro lado da mesma pergunta: a contagem de
linhas com nome composto (`MARCA/A/B`) por ano, em `saidas/validacao.md` §5 e
em `saidas/nomes_compostos.csv`. É a medida da hipótese de **agregação da
fonte** — `VW/FOX/CROSS FOX` como registro único para o que a planilha tratava
como dois. Quanto maior esse número, menos a diferença de contagem é perda de
cobertura e mais é a unidade de observação sendo definida pela fonte.

### I2. A taxa de entrada não responde ao limiar — confirmado, é desenho

Confirmado: **a entrada é o primeiro mês com unidades positivas e não usa o
limiar**; só a saída aplica D3, que foi o que a ESPEC especificou. Por isso as
três colunas de entrada são idênticas nos treze anos.

A assimetria está agora declarada em três lugares: no dicionário de dados, na
seção 8 do relatório de validação, e aqui. Ela entra direto em qualquer
decomposição de margens, e quem for usar essas margens precisa decidir se quer
um critério simétrico — a decisão continua sendo do pesquisador.

### I3. O corte de publicação fabrica a alta recente? — **inconclusivo, e a métrica do enunciado estava errada**

Antes do teste foi preciso corrigir a medida. **A truncagem da Fenabrave não é
um piso de unidades: é número fixo de linhas por sub-segmento.** "Suv's" traz
exatamente 40 modelos nos 152 meses; "Furgões", 7; "Sedans Grandes", 12.
Sub-segmento com menos modelos que o teto não trunca nada. A série "corte
mediano 99 → 396" que motivou a hipótese media outra coisa — o tamanho do
modelo mediano da fonte, que sobe porque o mercado se concentrou, não porque a
fonte passou a cortar mais.

Medido corretamente (`saidas/validacao.md` §4, `saidas/truncamento_por_bloco.csv`),
o corte **não sobe em automóveis** — mediana entre 3 e 21 unidades, sem
tendência — e **sobe muito em comerciais leves**: de 25 unidades em 2014 para
172 em 2026. É o oposto do que a cobertura sugeria, já que é em comerciais
leves que ela é quase perfeita.

Com a medida certa, o subconjunto imune ao corte cai de 310 para **98 modelos**,
e o teste dá: entre 2022 e 2025 (último ano completo) a taxa de saída vai de
0,136 a 0,195 na série cheia (+0,059) e de 0,149 a 0,133 no subconjunto imune
(−0,016). **A subida desaparece nos imunes — aponta para artefato do corte.**

**Mas o teste não tem poder para concluir.** São 98 modelos e mediana de 6
saídas por ano na janela recente: duas ou três saídas a mais movem a taxa em
vários pontos. O resultado aponta na direção do artefato sem demonstrá-lo.
Fica como alerta forte, não como conclusão — e junto com o risco de cobertura
registrado em §3 (automóveis andam −2,63 pontos percentuais entre 2014 e 2026),
recomenda cautela com qualquer leitura substantiva da alta recente da taxa de
saída.

---

## As dez questões

**Q1 — pico móvel. Mantido `media_movel`, mas a questão CONTINUA ABERTA.**
A comparação foi rodada, como pedido, e o resultado não permite encerrar:
**5 dos 13 anos mudam de posição** no ranking de taxa de saída entre
`media_movel` e `max_movel` (2019, 2020, 2023, 2024, 2025). A escolha não é
inócua. Qualquer resultado sobre em que anos houve mais saída depende dela e
precisa declarar qual leitura usou. A tabela lado a lado está em
`saidas/validacao.md` §8.

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

**Q5 — o que é "zero". Adotado, com a sinalização.** Mês com informe em que o
modelo não aparece é zero; lacuna é ausente. O painel ganhou a coluna
`corte_publicacao` (menor valor listado naquele mês e segmento), e
`saidas/zeros_frageis.csv` lista os pares modelo × mês em que o corte está
**acima** do limiar de D3 do próprio modelo — onde o zero pode estar
escondendo valor relevante. São 5.609 pares em 189 modelos.

**Q6 — retroagir a 2003. Diagnóstico rodado; extensão não feita.**
Ver `saidas/diagnostico_retroacao.md`. O painel continua em 2014-01..2026-08.

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

1. **Q1** — a leitura de "pico móvel" muda a ordenação de 5 dos 13 anos. Não dá
   para encerrar sem uma decisão explícita, e ela precisa constar de qualquer
   artigo que use taxas de saída.
2. **I1** — falta `Vendas_Geral.xlsx` para separar truncamento de agregação.
3. **Q3** — o mapa de grupos é rascunho revisado, não fato. As quatro convenções
   discutíveis continuam sendo convenções.
4. **Adjudicação de `regras.csv`** — por decisão da Parte 0, para quando o
   desenho do artigo de escopo de produto estiver fechado.
