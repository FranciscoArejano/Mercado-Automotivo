# Painel de vendas de veiculos 0 km no Brasil

Pipeline de construcao de um painel mensal de emplacamentos de automoveis e
comerciais leves novos, a partir dos informes mensais da Fenabrave.

A especificacao de pesquisa esta' em [`ESPEC.md`](ESPEC.md) e manda no codigo,
nao o contrario. As decisoes metodologicas (D1 a D5) sao do pesquisador: o
codigo as aplica, reporta o que nao esta' coberto por elas e **para** em vez de
resolver por conta propria. O que ficou em aberto esta' em
[`QUESTOES_ABERTAS.md`](QUESTOES_ABERTAS.md).

## Como rodar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python src/pipeline.py                 # 2014-01..2026-08, sete etapas
.venv/bin/python src/pipeline.py --pular 1       # sem rebaixar os PDFs
.venv/bin/python src/pipeline.py --de 3 --ate 6  # so' um trecho
.venv/bin/python -m pytest testes -q
```

Cada etapa tambem roda isolada e recebe `--inicio` / `--fim`:

```bash
.venv/bin/python src/etapa01_aquisicao.py --inicio 2003-01 --fim 2026-08
.venv/bin/python src/etapa02_parsing.py --forcar
```

Parametros ficam em `src/comum/config.py` e aceitam variavel de ambiente
(`PERIODO_INICIO`, `PERIODO_FIM`, `PICO_MOVEL_MODO`, `PAUSA_SEGUNDOS`).

## As sete etapas

| # | Script | O que faz | Produto |
|---|---|---|---|
| 1 | `etapa01_aquisicao.py` | Baixa os informes, um por vez, com pausa | `dados/bruto/pdf/`, `manifesto.csv`, `lacunas.csv`, `catalogo_fonte.csv` |
| 2 | `etapa02_parsing.py` | Extrai as tabelas por modelo e roda as conferencias internas ao documento | `dados/processado/extracao/*.csv`, totais, subtotais, verificacoes |
| 3 | `etapa03_painel_bruto.py` | Transcricao fiel, sem fusao nem limpeza semantica | `painel_bruto.parquet` |
| 4 | `etapa04_candidatos.py` | Evidencia para adjudicacao humana | `saidas/candidatos.xlsx` |
| 5 | `etapa05_painel.py` | Aplica `regras.csv`, confere o invariante central | `painel.parquet`, `saidas/painel_dicionario.md` |
| 6 | `etapa06_validacao.py` | Validacoes obrigatorias da sec.6 | `saidas/validacao.md`, `saidas/cobertura.csv` |
| 7 | `etapa07_referencia_cruzada.py` | Confronto com `Vendas_Geral.xlsx` (controle, nao fonte) | `saidas/referencia_cruzada.md` |

## Arquivos que o humano escreve

| Arquivo | Para que serve |
|---|---|
| `regras.csv` | Uma linha por decisao de fusao/classificacao. O codigo le'; o humano escreve. Ausente, e' criado vazio e nada e' fundido. |
| `config/mapa_grupos.csv` | Mapa **datado** de marca para grupo economico (D4). Rascunho -- ver Q3. |
| `config/marcas.csv` | Lista curada de marcas conhecidas. Marca observada e fora dela e' reportada, nunca adivinhada. |

`saidas/candidatos.xlsx` e' o insumo de `regras.csv`: a aba `pares` traz uma
coluna `decisao` vazia para preencher e transportar.

## A fonte

Informes mensais de emplacamentos da Fenabrave, em PDF, catalogados pela
propria fonte em `portalv2/api/Emplacamentos`. O catalogo cobre 2003-01 a
2026-08 e e' consultado em vez de se adivinhar nome de arquivo -- a fonte usa
tres padroes diferentes ao longo do periodo.

Duas tabelas de cada informe alimentam o painel:

- **Sub-segmentos** (`Modelos mais emplacados acumulado ate <Mes>`), secoes
  AUTOMOVEIS e COMERCIAIS LEVES. E' a tabela principal. Lida **por posicao de
  coluna**, da direita para a esquerda; o cabecalho serve so' de conferencia.
- **Ranking mensal** (top 50 de cada segmento). Serve de verificacao
  independente -- e' o teste que pega leitura de coluna errada -- e completa o
  painel com os modelos que a tabela de sub-segmento trunca.

A cobertura resultante nao e' 100% e nao poderia ser: as tabelas por modelo tem
numero fixo de linhas por sub-segmento. Quanto falta, medido mes a mes contra o
total que o proprio informe publica, esta' em `saidas/cobertura.csv`. E' o
produto que fecha D5.

## O que o pipeline nunca faz

Traducao direta da sec.9 da ESPEC:

1. Nao funde, renomeia nem agrupa modelos sem linha correspondente em `regras.csv`.
2. Nao preenche lacuna com interpolacao, media ou estimativa. Lacuna e' lacuna.
3. Nao sobrescreve `dados/bruto/` nem `painel_bruto.parquet`. Conteudo diferente
   faz a etapa parar e gravar ao lado, para o humano comparar.
4. Nao "corrige" numero da fonte que pareca errado -- reporta e segue.
5. Nao aplica o mapa de grupos economicos retroativamente.
6. Diante de ambiguidade nao coberta pela ESPEC: para, descreve e espera decisao.

Nao ha' casamento aproximado de nome em lugar nenhum, por decisao da sec.5:
na base anterior produziu 204 pares, quase todos falsos, e nao encontrou
Prisma -> Onix Plus.

## Rastreabilidade

Todo numero do painel se reconstitui a partir de tres coisas versionadas: os
PDFs originais (hash SHA-256 em `dados/bruto/manifesto.csv`), `regras.csv` e os
scripts de `src/`. Os PDFs em si nao vao para o repositorio -- sao pesados e a
etapa 01 os rebaixa identicos; o manifesto e as lacunas, sim.

Cada etapa escreve `logs/<etapa>.log` com contagem de linhas lidas e escritas.
O pipeline e' idempotente: rodar duas vezes produz o mesmo resultado.
