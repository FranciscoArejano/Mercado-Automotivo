# Dicionario -- frota_municipal

Gravado pela etapa 17 a partir das planilhas da Senatran guardadas em `dados/bruto/senatran_frota/` (SHA-256 no manifesto). 11,306,332 linhas. Recorte tipo: 99 meses, 2003-12 a 2026-10; recorte combustivel: 84 meses, 2013-12 a 2026-10. Dezembro de cada ano ate' 2019 e todos os meses desde 2020-01 (decisao do pesquisador para volume grande).

**Fonte:** Senatran (Ministerio dos Transportes), Estatisticas da frota de veiculos, https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/estatisticas-frota-de-veiculos-senatran; URL e data de cada arquivo no manifesto.

| coluna | unidade | descricao |
|---|---|---|
| `mes` | texto AAAA-MM | Mes de referencia da estatistica (posicao no fim do mes). |
| `uf` | sigla | UF do municipio. |
| `cod_ibge_municipio` | 7 digitos | Codigo IBGE do municipio, da tabela de `dados/bruto/ibge/municipios.json` (a mesma das fabricas). |
| `recorte` | texto | `tipo` (linha da tabela municipio x tipo) ou `combustivel` (linha da tabela municipio x combustivel). **Nao somar entre recortes.** |
| `tipo_veiculo` | texto | Tipo harmonizado (`config/frota_rotulos.csv`); `todos` no recorte combustivel. |
| `combustivel` | texto | Combustivel harmonizado; `todos` no recorte tipo. |
| `veiculos` | veiculos | Frota registrada (com placa) no municipio no fim do mes. |
| `municipio_fonte` | texto | Nome do municipio como a Senatran escreve. |
| `rotulos_fonte` | texto | Rotulo(s) originais somados na linha (dois rotulos originais podem ter o mesmo harmonizado). |
| `arquivo_fonte` | texto | Arquivo em `dados/bruto/senatran_frota/` (e, depois de `#`, a planilha dentro do zip ou rar). |

## Ressalvas

- **A fonte nao cruza tipo com combustivel.** A frota eletrica (recorte combustivel) inclui todos os tipos: motocicleta, motoneta, ciclomotor, onibus, caminhao, automovel. Nao ha' frota eletrica de automoveis e camionetas nesta base.
- **Combustivel so' a partir de 2013** (dezembro de 2013 vem num banco Access, lido com `mdb-export`). Antes, so' o recorte tipo.
- **Frota e' registro, nao circulacao:** veiculo baixado tarde, roubado ou fora de uso continua contado ate' a baixa no Renavam. A frota antiga e' superestimada.
- **Rotulos harmonizados** em `config/frota_rotulos.csv`; os casos ambiguos (por exemplo `ELETRICO/FONTE INTERNA`) ficam com rotulo proprio e estao em `QUESTOES_ABERTAS.md`.
- **Conferencias** em `saidas/frota_validacao.csv` e por UF e mes em `saidas/frota_conferencia_uf.csv`.
