# Construção do painel de vendas de veículos 0 km no Brasil

> Cole este documento inteiro no Claude Code como primeira mensagem do projeto,
> ou salve-o na raiz do repositório como `ESPEC.md` e peça ao Code que o siga.

---

## 0. Decisões já fechadas — confira antes de rodar

Estas cinco regras são **decisões metodológicas do pesquisador**, não escolhas de
implementação. O código as aplica; o código nunca as altera, nem "melhora", nem
substitui por heurística automática.

| # | Decisão | Regra fechada |
|---|---------|---------------|
| D1 | Unidade de observação | **Variante comercial.** Onix e Onix Plus são dois produtos. Desdobramentos de família são marcados como `reclassificacao` e **não contam como entrada nem como saída**. |
| D2 | Rebatismo | **Fundir em série contínua**, com a data do rebatismo registrada em campo próprio. Substituição de produto (plataforma nova) **não** funde. |
| D3 | Data de saída | Último mês em que o modelo atinge **≥ 5% do seu pico móvel de 12 meses**. Unidades posteriores continuam somando no volume, mas não deslocam a data. Gerar também as variantes a 3% e 10% para robustez. |
| D4 | Vendedor | **Duas chaves**: `marca` e `grupo_economico`. O mapa de propriedade é **datado** — Stellantis só existe a partir de 2021-01; antes disso FCA e PSA são grupos separados. Nunca aplicar propriedade retroativamente. |
| D5 | Piso de cobertura | **Medir primeiro.** Confrontar o total do painel contra o total publicado pela fonte, mês a mês, e só então fixar o piso. Entregar a comparação como produto. |

**Limitação declarada, não é regra:** troca de geração é invisível na fonte.
"Sobrevivência do modelo" significa sobrevivência do **nome comercial**, não do
produto físico. Registrar isso no dicionário de dados.

---

## 1. Contexto e consequências

Projeto de pesquisa em economia aplicada. O painel vai sustentar artigos com
desenho de identificação — decomposição de margens de entrada e saída, estudos de
evento, diferenças em diferenças. Três consequências que mandam em todas as
escolhas de implementação:

1. **Rastreabilidade vale mais que elegância.** Toda transformação tem de ser
   reconstituível a partir do arquivo original e do arquivo de regras.
2. **Nenhuma decisão metodológica no código.** Onde houver ambiguidade, o código
   *reporta* e para; não resolve por conta própria.
3. **O pipeline é idempotente.** Rodar duas vezes produz exatamente o mesmo
   resultado. Nada de estado acumulado entre execuções.

---

## 2. Parâmetros

```
PERIODO_INICIO  = 2003-01      # ver nota abaixo
PERIODO_FIM     = 2026-08
FONTE_PRIMARIA  = informes mensais de emplacamentos da Fenabrave
ESCOPO          = automóveis + comerciais leves, veículos novos (0 km)
```

**Nota sobre o início.** A Fenabrave publica informes mensais desde 2003. Uma vez
que o parser funcione, o custo marginal de retroagir é quase nulo. Comece por
**2014-01 a 2026-08** para validar o parser contra a base que já existe (ver §7),
e só então estenda para trás. Se a qualidade dos informes antigos não sustentar
extração confiável, pare e reporte o ano a partir do qual ela se degrada — não
force.

---

## 3. Produtos esperados

O pipeline entrega seis coisas. Nenhuma etapa sobrescreve a anterior.

| Produto | Descrição |
|---|---|
| `bruto/` | Arquivos originais baixados, **intocados**, com hash SHA-256 e data de download em `bruto/manifesto.csv`. Nunca reescrever. |
| `painel_bruto.parquet` | Transcrição fiel da fonte. Uma linha por (ano, mês, marca, modelo, unidades). **Nenhuma fusão, nenhuma limpeza semântica.** |
| `candidatos.xlsx` | Relatório para adjudicação humana (§5). |
| `regras.csv` | Arquivo de decisões caso a caso. **O código lê; o humano escreve.** Se não existir, criar com cabeçalho e zero linhas, e seguir sem fundir nada. |
| `painel.parquet` | Produto final harmonizado, com dicionário de dados em `painel_dicionario.md`. |
| `validacao.md` | Relatório de validação (§6), gerado a cada execução. |

---

## 4. Etapas 1 a 3 — aquisição, parsing, painel bruto

**Aquisição.** Baixar os informes mensais. Respeitar o servidor: um pedido por
vez, com pausa entre eles. Registrar no manifesto o que foi baixado, quando, e o
hash. Se um mês não existir ou falhar, **registrar a lacuna explicitamente** em
`bruto/lacunas.csv` — nunca preencher, interpolar ou estimar.

**Parsing.** Os informes são PDF. Extrair a tabela de emplacamentos por modelo.
Para cada arquivo, conferir que a soma dos modelos bate com o total que o próprio
informe publica; divergência acima de 0,5% é erro de parsing, não arredondamento —
parar e reportar o arquivo.

**Painel bruto.** Formato longo, uma linha por observação:

```
ano, mes, data, marca_fonte, modelo_fonte, nome_completo_fonte, unidades, arquivo_origem
```

Separar marca de modelo por **lista explícita de marcas conhecidas**, não pelo
primeiro espaço. Marcas de duas ou mais palavras existentes na base atual:
`CAOA Chery`, `Land Rover`, `Aston Martin`, `Alfa Romeo`, `Great Wall`,
`Mercedes-Benz`, `Rolls-Royce`. Novas marcas chinesas a partir de 2023 provavelmente
ampliam essa lista — ao encontrar um nome não mapeado, **reportar, não adivinhar**.

Normalizar apenas o que é seguramente tipográfico: espaço não separável (`\xa0`),
espaços duplicados, espaços nas pontas. **Não** normalizar acentos, não uniformizar
maiúsculas, não corrigir grafia. O nome cru fica preservado em `nome_completo_fonte`.

---

## 5. Etapa 4 — relatório de candidatos

Esta é a etapa que existe para **produzir evidência de decisão**, não para decidir.

Para cada modelo cuja série termina antes do fim da amostra, montar uma ficha com:
série mensal completa, pico, data de entrada, data de saída pela regra D3, e os
candidatos a sucessor encontrados pelo **teste de passagem de bastão**:

- modelos **da mesma marca** cuja data de entrada caia em `[saída(A) − 6, saída(A) + 6]` meses;
- com pico entre `0,4 ×` e `3,0 ×` o pico de A;
- excluindo B cuja série já existia antes de `saída(A) − 12` (não é sucessor novo);
- reportando a correlação das duas séries mensais na janela de ±12 meses.

**Armadilha obrigatória de tratar — censura à esquerda.** Todo modelo vivo no
primeiro mês da amostra tem "entrada" nesse mês, e todo modelo que sai perto do
início casa falsamente com dezenas de candidatos. Excluir do teste qualquer
entrada que coincida com o primeiro mês da amostra, e qualquer saída no último.
Na base atual isso produzia 14 candidatos falsos só para o Chevrolet Agile.

**Segundo detector, para rebatismo puro:** modelo cuja queda é abrupta (perda
superior a 80% num único mês, sem declínio prévio) pareado com uma entrada na
mesma marca no mesmo mês ou no adjacente.

Ordenar por volume em jogo. Uma linha por par candidato, com coluna
`decisao` vazia para o humano preencher.

> **Proibido:** fundir modelos por similaridade de nome. Testado na base atual,
> o casamento aproximado produz 204 pares, quase todos falsos — "Série 2 Gran
> Coupé" com "Série 6 Gran Coupé", "RS 3 Sportback" com "RS 5 Sportback" — e
> **não encontra** o caso que mais importa, Prisma → Onix Plus, porque as duas
> cadeias não compartilham uma letra. Similaridade de string não é sinal aqui.

---

## 6. Etapas 5 e 6 — regras e validação

`regras.csv` tem uma linha por decisão, com estas colunas:

```
tipo, marca, modelo_origem, modelo_destino, data_evento, observacao
```

onde `tipo` ∈ `{rebatismo, reclassificacao, substituicao, ignorar}`. `rebatismo`
funde as séries; `reclassificacao` marca o desdobramento de família (D1) e
**suprime a contagem de entrada/saída** naquele ponto; `substituicao` e `ignorar`
não fundem nada, existindo só para registrar que o caso foi analisado.

### Validações obrigatórias, todas em `validacao.md`

**O invariante central.** A soma de unidades por mês em `painel.parquet` tem de
ser **idêntica** à de `painel_bruto.parquet`. Harmonização redistribui rótulos;
não cria nem destrói unidades. Qualquer diferença é bug — falhar a execução.

Além dele:

- **Teste de sanidade temporal.** Abril de 2020 tem de ser o menor mês do período
  2014-2023. Julho de 2023 tem de ser o maior mês desde 2019. Se não for, a
  atribuição de mês está errada — provavelmente pelo cabeçalho (§7).
- **Cobertura (D5).** Tabela mês a mês: total do painel, total publicado pela
  fonte, diferença absoluta e percentual. É este produto que fecha D5.
- **Contagem de modelos** por ano, comparada com a contagem no informe.
- **Ausências:** nenhum modelo com unidades negativas; nenhum com série
  integralmente nula; lacunas de mês listadas.
- **Taxas de entrada e saída** por ano, calculadas nas três variantes de limiar
  de D3 (3%, 5%, 10%), lado a lado. Se a ordenação dos anos mudar entre limiares,
  destacar — é achado metodológico relevante, não detalhe.

---

## 7. Referência cruzada com a base existente

Existe uma planilha `Vendas_Geral.xlsx` com 2013–2023 montada à mão. **Ela não é
fonte** — é *controle independente*. Depois de reconstruir 2014–2023 do zero,
comparar modelo a modelo e mês a mês contra ela e reportar as divergências. Elas
revelam erros de parsing de um lado ou do outro.

Duas coisas conhecidas sobre essa planilha, úteis como teste:

1. **Os rótulos de mês dizem `jan/23` em todas as abas** — resíduo de cópia. A
   ordem das colunas está correta; o rótulo, não. Se o seu parser reproduzir esse
   erro, ele está lendo cabeçalho em vez de posição.
2. **A aba 2013 traz só o top-50 anual**, sem mensal. Não misturar com o resto: no
   painel ela criaria entrada fantasma em 2014. Ou 2013 vem completo da fonte
   primária, ou fica de fora.

Números da planilha para conferência rápida, em unidades:

| Ano | Total | Modelos | HHI por marca |
|---|---|---|---|
| 2014 | 3.325.627 | 310 | 1.297 |
| 2016 | 1.986.502 | 301 | 1.055 |
| 2020 | 1.949.892 | 299 | 1.146 |
| 2022 | 1.952.794 | 270 | 1.208 |
| 2023 (jan–ago) | 1.345.006 | 257 | 1.231 |

---

## 8. Restrições técnicas

- Python. `pandas` + `pyarrow`. Para PDF, tentar `pdfplumber` antes de OCR; só cair
  para OCR se a extração de texto falhar, e registrar quais arquivos precisaram.
- Estrutura de repositório com `src/`, `dados/bruto/`, `dados/processado/`,
  `saidas/`. Um script por etapa, encadeáveis e executáveis isoladamente.
- Semente fixa onde houver qualquer aleatoriedade. Versões travadas em
  `requirements.txt`.
- Logs em arquivo, com contagem de linhas lidas e escritas por etapa.
- Sem notebooks como produto final — notebook para exploração, script para pipeline.

## 9. Proibições explícitas

1. Não fundir, renomear ou agrupar modelos sem linha correspondente em `regras.csv`.
2. Não preencher lacuna de dado com interpolação, média ou estimativa. Lacuna é lacuna.
3. Não sobrescrever `bruto/` nem `painel_bruto.parquet` em nenhuma hipótese.
4. Não "corrigir" um número da fonte que pareça errado. Reportar e seguir.
5. Não aplicar o mapa de grupos econômicos retroativamente (D4).
6. Ao encontrar ambiguidade não coberta por este documento: parar, descrever o caso,
   propor as opções e esperar decisão. Não escolher sozinho.
