# Dicionario de dados -- `comex_veiculos.parquet`

Gerado em 2026-10-05T15:27:09+00:00 (UTC) por `src/etapa12_comex.py`, a partir das respostas do Comex
Stat (API `https://api-comexstat.mdic.gov.br/general`) guardadas em
`dados/bruto/comex/` com SHA-256 no manifesto.

Importacao e exportacao **mensais, oficiais, por NCM e pais**, das posicoes 8703
(automoveis) e 8704 (veiculos de carga), de 1997-01 a 2026-08: 73,316
linhas, 48 NCMs. Tabela de fatos **separada** do painel: a
juncao e' do codigo de analise.

| coluna | tipo | descricao |
|---|---|---|
| `mes_ref`, `ano`, `mes` | texto AAAA-MM, inteiros | mes do registro |
| `fluxo` | texto | `importacao` ou `exportacao` |
| `ncm` | texto | NCM de 8 digitos; descricao e classificacao em `config/ncm_veiculos.csv` (juncao por `ncm`) |
| `pais` | texto | pais de origem (importacao) ou de destino (exportacao), nome do Comex Stat |
| `fob_usd` | inteiro | valor FOB em dolares |
| `kg` | inteiro | peso liquido em kg |
| `unidades` | inteiro | quantidade estatistica **publicada**, so' onde a unidade estatistica da NCM e' "NUMERO (UNIDADE)"; vazio nas demais |
| `unidades_ajustadas` | inteiro | a publicada; nas linhas com menos de 500 kg por unidade publicada, o peso dividido pelo kg por unidade de referencia (mesma NCM, fluxo e ano, nas linhas plausiveis; sem ela, a da NCM em todos os anos), arredondado. **Padrao para contar carros** |
| `ajuste_unidades` | texto | `publicada` ou `estimada_pelo_peso` |

## `config/ncm_veiculos.csv`

Uma linha por NCM encontrada: descricao oficial (`tables/ncm` do Comex Stat),
unidade estatistica, primeiro e ultimo mes com dado, e duas colunas decididas por
regra (`src/comum/comex.py`):

- `grupo_propulsao_ncm`: `centelha` (gasolina, etanol, flex), `diesel`, `hev`,
  `phev`, `bev`, `outros`, `sem_separacao`. O grupo e' o do texto da subposicao
  depois da separacao. **As subposicoes de eletrificados so' existem desde
  2017-01 em 8703 e 2022-04 em
  8704** (`separa_eletrificados_desde`, conferido pela vigencia dos codigos):
  antes disso nenhuma NCM separa o eletrificado, e o mes deve ser lido como
  `sem_separacao` (`comum.comex.grupo_no_mes`). NCM que so' existiu antes da
  separacao tem `sem_separacao` na propria tabela. Em 8704, as subposicoes do SH
  2022 (8704.4x e 8704.5x) nao distinguem hibrido com e sem recarga externa (o
  texto oficial nao fala de recarga): ficam `hev`.
- `leve`: so' 8704; segue a descricao da NCM: `sim` quando o peso em carga maxima nao passa de 5 t. Nao casa exatamente com os comerciais leves da Fenabrave, que classifica por modelo. Ficam `indeterminado` o residual 8704.90 e o eletrico 8704.60, cuja descricao nao da faixa de peso.
- `agregado_carros`: `sim` para 8703 menos 8703.10 (neve, golfe e semelhantes; em
  2025, 12.908 unidades importadas, quase todas da China, a 36 kg cada) e para o
  8704 leve. Ficam fora 8703.10, o 8704 nao leve e os dois `indeterminado`
  (8704.60 e 8704.90). E' o agregado dos uso-testes.

**Duas coisas que a NCM nao diz.** O hibrido leve (MHEV) nao tem NCM propria: pode estar em 8703.40 ou nas NCMs de combustao. Nao se supoe nenhum dos dois. Kit SKD ou CKD de um veiculo entra na NCM do veiculo completo (regra geral 2a do SH): a importacao pode incluir kits para montagem local. Isso se registra, nao se separa.

**Peso por unidade.** Em alguns anos, parte das unidades importadas esta' em linhas
(NCM x pais x mes) com menos de 500 kg por unidade publicada:
2001, 2003 e 2006 (mais de 30% das unidades do agregado) e 2019 a 2021 (10% a
17%). Nas maiores, o pesquisador conferiu que valor e peso sao de carro e a
quantidade nao (na India, em 2019, a quantidade e' o peso). `unidades` fica como
publicada; `unidades_ajustadas` estima essas linhas pelo peso
(`comum.comex.ajustar_unidades`), e e' o padrao dos uso-testes, com a publicada
ao lado. `saidas/comex_diagnostico_peso.csv` mede o peso de cada ano.

| NCM | grupo | leve | periodo | descricao |
|---|---|---|---|---|
| 87031000 | `outros` | -- | 1997-03 a 2026-08 | Veículos especialmente concebidos para se deslocar sobre a neve; veículos especiais para t |
| 87032100 | `centelha` | -- | 1997-01 a 2026-08 | Automóveis com motor explosão, de cilindrada não superior a 1.000 cm3 |
| 87032210 | `centelha` | -- | 1997-01 a 2026-08 | Automóveis com motor explosão, de cilindrada superior a 1.000 cm3, mas não superior a 1.50 |
| 87032290 | `centelha` | -- | 1997-01 a 2026-08 | Automóveis com motor explosão, de cilindrada superior a 1.000 cm3, mas não superior a 1.50 |
| 87032310 | `centelha` | -- | 1997-01 a 2026-08 | Automóveis com motor explosão, 1500 < cm3 <= 3000, até 6 passageiros |
| 87032390 | `centelha` | -- | 1997-01 a 2026-08 | Automóveis com motor explosão, 1500 < cm3 <=3000, superior a 6 passageiros |
| 87032410 | `centelha` | -- | 1997-01 a 2026-08 | Automóveis com motor explosão, cm3 > 3000, até 6 passageiros |
| 87032490 | `centelha` | -- | 1997-01 a 2026-08 | Automóveis com motor explosão, cm3 > 3000, superior a 6 passageiros |
| 87033110 | `diesel` | -- | 2001-05 a 2026-08 | Automóveis com motor diesel, cm3 <= 1500, até 6 passageiros |
| 87033190 | `diesel` | -- | 1998-09 a 2023-07 | Automóveis com motor diesel, cm3 <= 1500, superior a 6 passageiros |
| 87033210 | `diesel` | -- | 1997-01 a 2026-05 | Automóveis com motor diesel, 1500 < cm3 <= 2500, até 6 passageiros |
| 87033290 | `diesel` | -- | 1997-01 a 2026-08 | Automóveis com motor diesel, 1500 < cm3 <= 2500, superior a 6 passageiros |
| 87033310 | `diesel` | -- | 1997-01 a 2026-08 | Automóveis com motor diesel, cm3 > 2500, até 6 passageiros |
| 87033390 | `diesel` | -- | 1997-01 a 2026-08 | Automóveis com motor diesel, cm3 > 2500, superior a 6 passageiros |
| 87034000 | `hev` | -- | 2017-01 a 2026-08 | Outros veículos, equipados para propulsão, simultaneamente, com um motor de pistão alterna |
| 87035000 | `hev` | -- | 2019-12 a 2026-08 | Outros veículos, equipados para propulsão, simultaneamente, com um motor de pistão de igni |
| 87036000 | `phev` | -- | 2017-01 a 2026-08 | Outros veículos, equipados para propulsão, simultaneamente, com um motor de pistão alterna |
| 87037000 | `phev` | -- | 2022-11 a 2022-11 | Outros veículos, equipados para propulsão, simultaneamente, com um motor de pistão de igni |
| 87038000 | `bev` | -- | 2017-02 a 2026-08 | Outros veículos, equipados unicamente com motor elétrico para propulsão |
| 87039000 | `outros` | -- | 1997-03 a 2026-06 | Outros automóveis de passageiros, inclusive de uso misto, etc. |
| 87041000 | `sem_separacao` | nao | 1997-02 a 2004-02 | Dumpers para transporte de mercadoria, utilizado fora de rodovias |
| 87041010 | `outros` | nao | 2004-02 a 2026-08 | Dumpers para transporte de mercadoria >= 85 toneladas, utilizado fora de rodovias |
| 87041090 | `outros` | nao | 2004-01 a 2026-08 | Outros "dumpers" para transporte de mercadoria, utilizado fora de rodovias |
| 87042110 | `diesel` | sim | 1997-01 a 2026-08 | Chassis com motor diesel e cabina, para carga <= 5 toneladas |
| 87042120 | `diesel` | sim | 1997-01 a 2025-01 | Veículo automóvel com motor diesel, caixa basculante para carga <= 5 toneladas |
| 87042130 | `diesel` | sim | 2001-12 a 2023-03 | Veículos automóveis frigoríficos, etc, com motor diesel, carga <= 5 toneladas |
| 87042190 | `diesel` | sim | 1997-01 a 2026-08 | Outros veículos automóveis com motor diesel, para carga <= 5 toneladas |
| 87042210 | `diesel` | nao | 1997-01 a 2026-08 | Chassis com motor diesel e cabina, 5 toneladas < carga <= 20 toneladas |
| 87042220 | `diesel` | nao | 1997-01 a 2026-08 | Veículo automóvel com motor diesel, caixa basculante 5 toneladas < carga <= 20 toneladas |
| 87042230 | `diesel` | nao | 2000-06 a 2026-08 | Veículos automóveis frigoríficos, etc, com motor diesel, 5 toneladas < carga <= 20 tonelad |
| 87042290 | `diesel` | nao | 1997-01 a 2026-08 | Outros veículos automóveis com motor diesel, capacidade de carga entre 5 e 20 toneladas |
| 87042310 | `diesel` | nao | 1997-01 a 2026-08 | Chassis com motor diesel e cabina, capacidade de carga > 20 toneladas |
| 87042320 | `diesel` | nao | 1997-05 a 2026-08 | Veículos automóveis com motor diesel, caixa bascular, carga > 20 toneladas |
| 87042330 | `diesel` | nao | 2003-08 a 2026-07 | Veículos automóveis frigoríficos com motor diesel, capacidade de carga maior que 20 tonela |
| 87042340 | `diesel` | nao | 2018-05 a 2026-08 | Veículos de chassis articulado, p/ o transporte de troncos(forwarder), c/ grua incorporada |
| 87042390 | `diesel` | nao | 1997-01 a 2026-08 | Outros veículos automóveis motor diesel, carga > 20 toneladas |
| 87043110 | `centelha` | sim | 1997-01 a 2026-08 | Chassis com motor a explosão e cabina, de peso em carga máxima não superior a 5 toneladas |
| 87043120 | `centelha` | sim | 1997-01 a 2026-08 | Veículos automóveis com motor à explosão/caixa basculante, de peso em carga máxima não sup |
| 87043130 | `centelha` | sim | 1997-04 a 2025-11 | Veiculos automóveis frigoríficos ou isotérmicos, etc, com motor a explosão, de peso em car |
| 87043190 | `centelha` | sim | 1997-01 a 2026-08 | Outros veículos automóveis com motor a explosão, carga <= 5 toneladas |
| 87043210 | `centelha` | nao | 1997-08 a 2026-08 | Chassis com motor explosão e cabina, carga >5 toneladas |
| 87043220 | `sem_separacao` | nao | 2002-04 a 2020-12 | Veículos automóveis com motor à explosão/caixa basculante capacidade de carga > 5 tonelada |
| 87043230 | `centelha` | nao | 2011-08 a 2025-04 | Veículos automóveis frigoríficos, etc, com motor a explosão, carga > 5 toneladas |
| 87043290 | `sem_separacao` | nao | 1997-12 a 2021-04 | Outros veículos automóveis com motor a explosão, carga > 5 toneladas |
| 87044100 | `hev` | sim | 2024-05 a 2026-07 | Outros veículos automóveis para transporte de mercadorias, equipados para propulsão, simul |
| 87045100 | `hev` | sim | 2022-05 a 2026-08 | Outros veículos automóveis para transporte de mercadorias, equipados para propulsão, simul |
| 87046000 | `bev` | indeterminado | 2022-04 a 2026-08 | Outros veículos automóveis para transporte de mercadorias, unicamente com motor elétrico p |
| 87049000 | `outros` | indeterminado | 1997-05 a 2026-08 | Outros veículos automóveis para transporte de mercadorias |

## Conferencias (`saidas/comex_validacao.csv`)

| conferencia                                                                                                                                                                                                                                      |   casos |   falhas |
|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------:|---------:|
| soma sobre paises = consulta sem pais (fluxo x NCM x ano)                                                                                                                                                                                        |    1634 |        0 |
| meses faltando na janela 1997-01 a 2026-08 (fluxo x posicao)                                                                                                                                                                                     |       4 |        0 |
| NCMs fora das somas de unidades (unidade estatistica nao e' unidade): nenhuma                                                                                                                                                                    |      48 |        0 |
| unidades_ajustadas = unidades nas linhas com ajuste `publicada`                                                                                                                                                                                  |   71281 |        0 |
| linhas com menos de 500 kg por unidade publicada, estimadas pelo peso: 4,227,631 unidades publicadas viram 168,672; sem referencia de peso, mantidas publicadas: 1                                                                               |    2036 |        0 |
| fora do agregado de carros (agregado_carros = nao): 87031000, 87041000, 87041010, 87041090, 87042210, 87042220, 87042230, 87042290, 87042310, 87042320, 87042330, 87042340, 87042390, 87043210, 87043220, 87043230, 87043290, 87046000, 87049000 |      48 |        0 |
| diagnostico, nao falha: unidades publicadas do agregado de carros importado em linhas com menos de 500 kg por unidade (saidas/comex_diagnostico_peso.csv); anos acima de 10%: 2001, 2003, 2006, 2019, 2020, 2021                                 |      30 |        0 |

## Uso-teste

Todos sobre o agregado de carros e com `unidades_ajustadas`, a publicada ao lado:
`saidas/comex_uso_teste_bev.csv` (importacao de eletricos puros contra o painel so'
`bev`), `saidas/comex_uso_teste_origem.csv` (importacao contra o painel `importado`,
com `ambos` a 0% e a 100%) e `saidas/comex_paises_top10.csv`. Descritos no registro
da rodada; a explicacao das distancias fica para o calendario de politicas.
