# Questoes abertas

ESPEC.md sec.9.6: "Ao encontrar ambiguidade nao coberta por este documento:
parar, descrever o caso, propor as opcoes e esperar decisao. Nao escolher
sozinho."

Este arquivo e' o cumprimento dessa regra. Cada questao traz o caso, a
evidencia, o que o codigo faz **provisoriamente** para que o pipeline rode, e
as opcoes. Nenhuma delas esta' fechada. Onde ha' um padrao provisorio, ele e'
um parametro em `src/comum/config.py`, trocavel sem tocar em logica.

---

## Q1. Como se le' "pico movel de 12 meses" (D3)

**O caso.** D3 define a data de saida como o ultimo mes em que o modelo atinge
>= 5% do seu "pico movel de 12 meses". A expressao admite duas leituras que
nao dao a mesma data:

- `media_movel`: pico = `max_t( media das unidades em [t-11, t] )`. Trata
  "movel" como suavizacao: um unico mes excepcional nao define o patamar. Fica
  em escala mensal, comparavel com `unidades(t)`.
- `max_movel`: pico = `max_t( maior valor em [t-11, t] )`, que para uma serie
  completa e' o pico global do modelo.

A diferenca importa em modelos com um mes isolado de pico (lote de venda
direta, por exemplo): com `max_movel` o patamar sobe, o corte de 5% sobe junto
e a saida e' declarada **mais cedo**.

**Provisorio.** `config.PICO_MOVEL_MODO = "media_movel"`. As duas leituras
estao implementadas e testadas (`testes/test_ciclo_vida.py`).

**Opcoes.** (a) manter `media_movel`; (b) trocar para `max_movel`; (c) uma
terceira leitura -- por exemplo pico da soma movel de 12 meses dividida por 12,
que e' igual a (a) em janela cheia mas difere no inicio da serie.

**Como decidir.** `saidas/validacao.md` sec.7 ja' traz as taxas de entrada e
saida nos tres limiares (3%, 5%, 10%). Rodar a etapa 06 com
`PICO_MOVEL_MODO=max_movel` produz a tabela concorrente; se a ordenacao dos
anos nao mudar, a escolha e' inocua e a questao morre.

---

## Q2. A tolerancia de 0,5% da sec.4 nao se aplica ao total do informe

**O caso.** A sec.4 manda conferir que "a soma dos modelos bate com o total que
o proprio informe publica" e tratar divergencia acima de 0,5% como erro de
parsing. Medido: **a divergencia e' estrutural, nao de leitura**. As tabelas
por modelo do informe tem numero fixo de linhas por sub-segmento e truncam a
cauda. O proprio documento denuncia isso: em Jun/2016 o sub-segmento "Hatch
Medios" lista 6 modelos que somam 2.085 unidades e publica, na linha `Total`
logo abaixo, 2.510. A diferenca de 425 unidades e' cauda nao publicada, e nao
ha' leitura possivel que a recupere.

Aplicada ao pe' da letra, a regra pararia em todos os 152 arquivos.

**Provisorio.** A verificacao de parsing foi ancorada no que o documento
permite conferir de fato:

1. soma dos modelos listados x linha `Total` do proprio sub-segmento -- e' erro
   de parsing se a soma **exceder** o total (leitura pegou linha alheia);
2. top-50 do ranking mensal x tabela de sub-segmento, modelo a modelo, com
   tolerancia de 0,5% **do volume conferido** -- e' esta que pega leitura de
   coluna errada, que deslocaria o volume inteiro;
3. mes declarado no titulo do PDF x mes atribuido pelo catalogo da fonte.

O confronto entre o total do painel e o total publicado virou **medida de
cobertura (D5)**, entregue em `saidas/cobertura.csv` e resumida em
`saidas/validacao.md`. `dados/processado/extracao_subtotais.csv` quantifica a
cauda nao publicada sub-segmento a sub-segmento.

**Opcoes.** (a) manter; (b) exigir a leitura literal com
`--tolerancia-total 0.005` na etapa 02 -- ja' implementado, e o pipeline vai
parar no primeiro arquivo; (c) fixar um piso de cobertura como criterio de
aceitacao por mes, agora que ha' a medida (e' o que D5 pede: "medir primeiro").

---

## Q3. O mapa de grupo economico e' rascunho, nao dado

**O caso.** D4 fixa a regra (mapa datado, Stellantis so' a partir de 2021-01,
nada retroativo) mas nao fornece o mapa. `config/mapa_grupos.csv` foi montado
com os eventos societarios documentados e traz coluna `fonte`. Ele **precisa de
revisao**; ha' pelo menos quatro casos que sao decisao do pesquisador, nao
fato:

1. **Alianca Renault-Nissan-Mitsubishi.** Participacao cruzada nao e' controle.
   O mapa mantem Renault, Nissan e Mitsubishi como grupos separados e registra
   a alianca em `observacao`. Tratar como grupo unico muda concentracao e
   margens de entrada/saida.
2. **Hyundai e Kia.** Tratados como um grupo (`HYUNDAI`), pela participacao
   cruzada desde 1998. E' a convencao usual, mas e' convencao.
3. **CAOA Chery.** Joint venture desde 11/2017, controle compartilhado. Esta'
   como grupo proprio, separado de `CHERY`. Alternativa: acumular em `CHERY`.
4. **Sub-marcas chinesas recentes** -- `OMODA JAECOO`, `JETOUR` -- atribuidas ao
   grupo `CHERY`. Se o interesse for a marca comercial, elas deveriam ficar
   separadas.

**Provisorio.** O mapa como esta'. Marca sem linha vigente recebe
`NAO_MAPEADO`, nunca um chute; `saidas/grupos_nao_mapeados.csv` lista as
pendentes por volume.

---

## Q4. O mesmo nome comercial em dois segmentos e em dois sub-segmentos

**O caso.** Dois fatos medidos na fonte:

- **Dois segmentos.** Em Ago/2026 `RENAULT/KWID` aparece em automoveis (4.357)
  e em comerciais leves (80). Sao produtos diferentes com o mesmo nome.
- **Dois sub-segmentos.** No mesmo informe, `NISSAN/VERSA` aparece em "Sedans
  Pequenos" (geracao antiga, 0 unidades) e em "Sedans Compactos" (geracao nova,
  533). Aqui sao o mesmo nome comercial em geracoes diferentes -- e a ESPEC ja'
  declara que troca de geracao e' invisivel na fonte.

**Provisorio.** A chave do painel e' `(marca, modelo, segmento)`: o segmento
entra, os sub-segmentos somam. Migracao de segmento ao longo do tempo aparece
como saida em um segmento e entrada no outro, e vai para o relatorio de
candidatos como caso a decidir -- e' exatamente o que `reclassificacao` cobre.

**Opcoes.** (a) manter; (b) chave `(marca, modelo)`, somando os segmentos, o
que junta a picape e o hatch de mesmo nome; (c) chave incluindo sub-segmento,
o que separaria geracoes -- mas so' onde a fonte por acaso as separa, criando
serie descontinua sem criterio.

---

## Q5. O que significa "zero" num mes

**O caso.** Um modelo ausente das tabelas de um mes nao esta' necessariamente
com zero emplacamentos: pode estar abaixo do corte de publicacao daquele mes.
`saidas/validacao.md` sec.4 traz o corte medido por ano e segmento.

**Provisorio.** Para o calculo de D3, mes com informe em que o modelo nao
aparece entra como **zero**; mes sem informe (lacuna) entra como **ausente** e
sai da janela -- lacuna nunca vira zero (sec.9.2). O efeito pratico e' pequeno
porque o corte e' baixo perto do pico de qualquer modelo com serie relevante,
mas nao e' nulo para modelos de cauda.

**Opcoes.** (a) manter; (b) tratar como ausente tambem o mes em que o modelo
nao aparece, o que encurta as series e complica a leitura de "ultimo mes acima
do limiar"; (c) restringir o painel aos modelos que nunca somem entre entrada e
saida.

---

## Q6. Retroagir a 2003

**O caso.** A sec.2 manda validar 2014-01..2026-08 primeiro e so' entao
estender para tras, parando e reportando se a qualidade dos informes antigos
nao sustentar extracao confiavel. O catalogo da fonte lista os 284 meses de
2003-01 a 2026-08, e a etapa 01 ja' sabe baixa-los
(`--inicio 2003-01`).

**Provisorio.** O pipeline roda 2014-01..2026-08. A extensao nao foi executada.

**Como decidir.** Rodar `python src/pipeline.py --inicio 2003-01 --ate 2` e ler
`saidas/arquivos_sem_texto.csv` e `dados/processado/extracao_verificacao.csv`:
eles dizem, arquivo a arquivo, a partir de que ano a extracao degrada.

---

## Q7. O ranking completa a tabela de sub-segmento

**O caso.** O top-50 mensal publica modelos que as tabelas de sub-segmento
truncam. Em Ago/2026 isso e' 27 modelos e 3.022 unidades so' em comerciais
leves -- a cobertura do segmento passa de 93,84% para 99,87%.

**Provisorio.** O painel bruto usa a tabela de sub-segmento e completa com o
ranking apenas para modelos que ela nao lista (coluna `origem_tabela` diz
qual). Quando as duas trazem numeros diferentes para o mesmo modelo, vale a
tabela de sub-segmento e a divergencia vai para `saidas/divergencias_fonte.csv`
-- reportar e seguir (sec.9.4), nunca corrigir.

**Opcoes.** (a) manter; (b) usar so' as tabelas de sub-segmento, perdendo
cobertura; (c) dar precedencia ao ranking onde houver conflito.

---

## Q8. "Julho de 2023 e' o maior mes desde 2019" nao se confirma na fonte

**O caso.** A sec.6 pede dois testes de sanidade temporal. O primeiro passa:
abril de 2020 e' de fato o menor mes de 2014-2023. O segundo nao passa -- e o
problema nao esta' no painel.

Medido no **total que a propria Fenabrave publica** em cada informe, nao no
painel, para automoveis + comerciais leves:

| janela | maior mes na fonte | unidades | posicao de 2023-07 |
|---|---|---:|---:|
| 2019-01..2023-08 | 2019-12 | 251.973 | 10 de 56 |
| 2020-01..2023-08 | 2020-12 | 232.814 | 2 de 44 |
| 2021-01..2023-08 | **2023-07** | 215.711 | 1 de 32 |
| 2022-01..2023-08 | **2023-07** | 215.711 | 1 de 20 |

Julho de 2023 (215.711) foi de fato um pico -- o maior mes **desde janeiro de
2021**, e um salto de 20% sobre junho, coerente com o programa de incentivo
daquele mes. Mas dezembro de 2019 (251.973) e dezembro de 2020 (232.814) sao
maiores. Estendida a amostra ate' 2026-08, o maior mes da serie e' dezembro de
2025 (267.117).

Como painel e fonte concordam entre si e a atribuicao de mes passa no teste de
abril de 2020, isto **nao** e' erro de leitura de cabecalho. E' a premissa que
nao se confirma neste escopo.

**Provisorio.** A etapa 06 roda o teste duas vezes -- no painel e no total
publicado -- e classifica: `FALHOU` (e a execucao falha) so' quando o painel
discorda da fonte; `PREMISSA NAO CONFIRMADA` quando os dois concordam e a
premissa e' que nao se sustenta. A tabela de janelas acima e' reproduzida em
`saidas/validacao.md`.

**Opcoes.** (a) trocar a premissa por "maior mes desde 2021", que se confirma;
(b) manter "desde 2019" e verificar se ela vale para outro escopo -- total com
motos, ou a serie da planilha de controle, que termina em ago/2023; (c)
abandonar o segundo teste e ficar so' com abril de 2020, que e' robusto.

---

## Q9. O detector de queda abrupta dispara em choque de mercado

**O caso.** O segundo detector da sec.5 marca perda superior a 80% num unico
mes sem declinio previo. Em abril de 2020 o mercado inteiro caiu 73% num mes:
praticamente todo modelo satisfaz o criterio, e o relatorio se enche de pares
em que nada aconteceu com o produto. O mesmo vale, em menor grau, para janeiro
de todo ano (sazonalidade) e para os meses de escassez de semicondutores.

**Provisorio.** O detector segue exatamente como a ESPEC o define -- nao ha'
filtro escondido. Cada par ganhou a coluna `variacao_mercado_no_mes`, com a
variacao do total do segmento naquele mes: quando ela esta' em -0,73, a queda
do modelo e' a queda do mercado. A ordenacao por volume em jogo, que a sec.5
manda, ja' empurra os casos reais para o topo.

**Opcoes.** (a) manter e filtrar na planilha; (b) exigir que a queda do modelo
supere a do mercado por uma margem -- por exemplo, queda relativa acima de 80%
depois de descontada a variacao do segmento; (c) exigir volume minimo do modelo
antes da queda, para nao marcar serie de tres unidades.

---

## Q10. A janela de +-6 meses e a censura a' esquerda de quem sai

**O caso.** Vale registrar como o teste de passagem de bastao foi lido, porque
a leitura decide se o caso mais importante aparece ou nao. A sec.5 manda
"excluir do teste qualquer entrada que coincida com o primeiro mes da amostra,
e qualquer saida no ultimo". Sao duas exclusoes com alvos diferentes: a censura
a' esquerda invalida a **entrada**, entao descarta o modelo no papel de
*sucessor*; a censura a' direita invalida a **saida**, entao descarta o modelo
no papel de *quem sai*.

Descartar quem sai por censura a' esquerda esconderia exatamente Prisma ->
Onix Plus: o Prisma esta' vivo em 2014-01, o primeiro mes da amostra, mas sua
saida em 2020-01 e' evento real. Com a leitura acima, o par aparece em segundo
lugar por volume em jogo (889.618 unidades, razao de picos 0,93, defasagem de
-4 meses). O teste `testes/test_candidatos.py` fixa esse comportamento.

**Provisorio.** A leitura descrita acima, com teste que a trava.
