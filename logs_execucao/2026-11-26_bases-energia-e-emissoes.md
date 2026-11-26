# Registro de execução — bases de energia, frota e emissões (rodada 13)

26/11/2026. Branch `claude/new-session-16k23l`, a partir de `12298a9` (fechamento
da rodada 12). Instruções: `PARA-O-CODE-bases-energia-e-emissoes.md` (ESPEC,
Parte 0, §9.6 e §10 continuam valendo). Este registro vai no mesmo push do
trabalho que ele descreve, e é atualizado a cada etapa.

---

## Parte 1 — testes de acesso

Registro reproduzível: `python src/coleta/testar_acesso.py` grava cada tentativa
em `dados/bruto/acesso_fontes_energia.csv` (as quatro primeiras linhas são os
testes manuais com `curl`, antes do script). O resumo vai para a tabela de
fontes do `CATALOGO.md` (`config/fontes_candidatas.csv`).

| fonte | resultado | o que fica |
|---|---|---|
| **ANEEL, geração distribuída** | **não abriu.** `dadosabertos.aneel.gov.br` aceita o túnel e reseta a conexão no TLS (seis tentativas, 01:20 a 01:45 UTC); `www.aneel.gov.br` e `portalrelatorios.aneel.gov.br` dão 403 do Cloudflare ("Sorry, you have been blocked") | registrado, não contornado; produto não construído |
| **ANEEL, tarifas** | **não abriu**: é o mesmo domínio, com o mesmo bloqueio | idem; a relação de municípios por distribuidora e o número de consumidores também vêm da ANEEL e ficam de fora |
| **Senatran, frota** | abre (gov.br/transportes) | a construir |
| **ANP, preços** | abre (gov.br/anp): série por posto e síntese mensal | a construir |
| **SEEG** | o primeiro teste deu 403 do CloudFront (com User-Agent `Mozilla/5.0`); com o User-Agent que o projeto usa desde a rodada 1 (`config.USER_AGENT`), a página de dados abre e a tabela geral da coleção 14.0 baixa; a API GraphQL da plataforma não respondeu em 300 s | a construir a partir da tabela geral; API não usada |
| **MCTI, fator do SIN** | abre (gov.br/mcti), com o User-Agent do projeto; um teste do script viu o desafio de robô (TSPD) no corpo, mas era o script da página: a página veio inteira (220 kB) e a planilha baixa | a construir |

**Sobre o User-Agent.** Não troquei User-Agent para passar por bloqueio: o
script de acesso usa o mesmo `config.USER_AGENT` que a etapa 1 usa para a
Fenabrave desde a primeira rodada. O 403 do SEEG apareceu só no primeiro teste
manual, com o `Mozilla/5.0` curto do `curl`. Na ANEEL, o mesmo User-Agent do
projeto continua bloqueado, e lá parei.

**Achados que mudam o desenho, registrados antes de construir:**

- **Senatran não cruza tipo de veículo com combustível em nenhum nível.** O
  arquivo de combustível é município × combustível, com todos os tipos juntos
  (moto, ônibus, caminhão, automóvel). O de tipo é município × tipo, sem
  combustível. A frota elétrica que sai daí é a de **todos os tipos**, não a de
  automóveis e camionetas. Isso vai para as ressalvas e para o uso-teste 1.
- **Senatran, cobertura por ano:** município × tipo desde 2003 (2003-2012 em
  zips anuais com as doze planilhas; desde 2013, planilhas mensais); município ×
  combustível a partir de 2013 (a página de 2013 traz combustível de junho em
  diante). Antes de 2013 não há combustível em nenhum nível.
- **ANP:** a série por posto começa em 2004-01; a síntese mensal por estado
  começa em 2001. O produto sai da série por posto (é o bruto que se reproduz),
  então começa em 2004-01. A síntese entra só como conferência.
- **MCTI:** o fator médio (inventário) começa em 2006-01.
- **SEEG:** coleção 14.0 (9/11/2026), séries anuais de 1970 a 2025.

---

## Parte 2 — regras de guarda, como ficaram

- **Coleta em `src/coleta/`**, uma por fonte, fora do pipeline (a etapa lê o
  bruto guardado; quem atualiza o bruto é a coleta). Peças comuns em
  `src/coleta/comum_coleta.py`: download (um pedido por vez, com pausa, em blocos
  e retomado por `Range` quando a conexão cai), manifesto por fonte e bruto
  reduzido.
- **Manifesto por fonte** (`dados/bruto/<fonte>/manifesto.csv`): arquivo, URL,
  data, tamanho e SHA-256 do original; se passou de 50 MB, `no_git = nao` e o
  caminho, o tamanho e o SHA-256 do reduzido.
- **Original acima de 50 MB** fica em `dados/bruto/<fonte>/fora_do_git/`, no
  `.gitignore`. **Reduzido** em `dados/bruto/<fonte>/reduzido/`, parquet zstd
  determinístico (mesma tabela, mesmos bytes: sem metadado de pandas, sem
  estatísticas). Só as colunas e linhas que o produto usa, células como a fonte
  as traz: texto nos CSV da ANP, número nas células numéricas do xlsx do SEEG.
  Nenhuma conta, agregação ou renomeação.
- **Teste dos dois SHA-256** (`testes/test_brutos_energia.py`): todo arquivo no
  git bate com o manifesto; todo reduzido existe, tem até 50 MB e bate; quando o
  original está presente, o SHA-256 dele bate e refazer o reduzido dá os mesmos
  bytes. Refazer os ~40 reduzidos da ANP leva ~20 minutos, então o padrão confere
  o SHA-256 de todos os originais e refaz uma amostra fixa (os dois primeiros de
  cada fonte); `TESTE_REDUZIDO_TODOS=1` refaz todos. Rodei com todos uma vez no
  fechamento (resultado na Parte 6).
- Sem Git LFS.

## Parte 3 — fator de emissão do SIN (MCTI), etapa 15

- Planilha única do método para inventários (`Inventario_2026_janout.xlsx`,
  12 kB): 2006-01 a 2026-10, 250 meses, mensal e anual.
- **Conferência:** a média simples dos doze meses bate com o anual publicado em
  todos os 20 anos completos (diferença máxima 0,43%, arredondamento a quatro
  casas). Eu tinha escrito no dicionário que o anual era ponderado pela geração;
  o dado mostrou que não há diferença a explicar, e o texto passou a dizer o que
  o dado diz.
- A série começa em 2006: 2003-2005 ficam vazios.

## Parte 4 — emissões (SEEG 14.0), etapa 16

- Tabela geral `Dados-nacionais-14.0.xlsx` (206 MB). Reduzido: a aba `Dados`
  com os gases físicos e o CO2e GWP-AR5, anos de 2003 em diante (111.588 linhas,
  13 MB), e a tabela dinâmica `Consulta Série Histórica` (o total Brasil por
  setor que o próprio SEEG calcula), para a conferência.
- Produto: 552.713 linhas, tipo × UF × ano × setor × categoria × subcategoria ×
  produto × gás, soma sobre as colunas mais finas (detalhamento, recorte,
  atividade, bioma). `uf` vazia = não alocado.
- **Conferência:** total Brasil = soma das UFs + não alocado em todos os 138
  casos (setor × ano, mais o total geral), diferença relativa máxima 3e-15.
- **Erro meu, corrigido:** na primeira passada a conferência falhou em 23 casos
  de Agropecuária, com diferença de 30 vezes. Não era o dado: "Agropecuária" é
  setor e também categoria de Energia, e eu lia as duas linhas da tabela
  dinâmica como setor. Passei a pegar só a primeira ocorrência (a do setor).
- A métrica de CO2e é a GWP-AR5. O SEEG não diz de que gás sai cada linha de
  CO2e, então gás físico e CO2e ficam em linhas separadas e não se somam.

## Parte 5 — frota (Senatran), etapa 17

**O que a fonte tem.** Uma página por ano desde 2013 e um zip por ano de 2000 a
2012. Três tabelas usadas: município × tipo (desde 2003), município ×
combustível (desde 2013; dez/2013 num banco Access `.mdb`) e UF × tipo (só para
a conferência). **Tipo e combustível nunca se cruzam**: a frota elétrica é de
todos os tipos (Q-E2).

**Recorte:** dezembro de 2003 a 2019 e todos os meses desde 2020-01 (99 meses de
tipo; 83 de combustível, de 2013-12 a 2026-10). Bruto: 270 arquivos, 215 MB, todos
abaixo de 50 MB, no git como vieram. Produto: 11.306.332 linhas, 5.571 municípios,
35,7 MB.

**Escolhas e erros, na ordem em que apareceram:**

1. **Nomes de arquivo.** Mudam de mês para mês (`Maro` sem o ç, `copy_of_`,
   `-xlsx` sem ponto, hífen no lugar de sublinhado). O inventário
   (`dados/bruto/senatran_frota/inventario_links.csv`) classifica por padrão e
   escolhe um por mês e tipo: original antes da cópia, depois xlsx, xls, csv, zip,
   rar. A primeira versão do padrão deixava o arquivo de **cor** passar como
   município × tipo (separador com hífen); corrigido antes de baixar.
2. **Erro meu: os zips de 2007 a 2012 eram HTML.** O `resolveuid` da página leva à
   página de visualização do arquivo, e eu baixei e comitei seis páginas HTML com
   nome de zip. Achei ao abrir os zips; removi, resolvo o endereço e peço o
   `@@download/file`, e a coleta passou a recusar HTML no lugar de planilha. Os
   seis HTML ficam no histórico do git (276 kB cada), não na árvore.
3. **Formatos.** Aba de glossário antes da tabela; tabela começando na coluna B
   (2006); cabeçalho repetido; `.xls` de 2003-2009 que o `xlrd` não decodifica
   (lido com `calamine`); combustível de 2013-12 em Access (`mdb-export`); rar em
   2015 e 2016 (`bsdtar`). Em 2007 o zip traz duas planilhas de UF de dezembro;
   fiquei com a marcada `new` (é só conferência), com registro.
4. **Rótulos** (`config/frota_rotulos.csv`, 63 linhas): 32 de tipo (os acentos
   somem em 2009; `CHASSI PLATAFAFORMA` até 2008) e 31 de combustível, com os
   ambíguos à parte (Q-E3). Rótulo novo, ou fora dos anos da linha, para a etapa.
5. **Municípios:** casamento com o IBGE por UF e nome normalizado; 72 grafias e
   nomes antigos em `config/frota_municipios.csv`, cada um com motivo. Para as
   renomeações usei uma prova no próprio dado: o nome antigo e o novo nunca
   aparecem no mesmo mês. Ela derrubou dois palpites meus (Santarém-PB não é
   Santa Cecília, é Joca Claudino; Espírito Santo do Oeste não é Patu, é Paraú).
   `MUNICIPIO NAO INFORMADO` e `IBITIUVA` ficam fora, com registro.
6. **Linhas sem UF** no combustível (`Não Identificado`, `Não se Aplica`,
   `Sem Informação` na coluna de UF) não são município: fora do produto, somadas
   em `saidas/frota_sem_municipio.csv`.
7. **Desempenho:** a primeira versão agregava com `lambda` sobre 11 milhões de
   linhas e passou de dez minutos. Reescrevi: rótulos e nomes de origem no nível
   (mês, rótulo) e (mês, município), e zeros publicados fora do formato longo
   (linha ausente = zero publicado; a planilha traz todos os municípios e tipos).

**Conferências** (`saidas/frota_validacao.csv`, 0 falhas):

- soma dos municípios mais os "não informados" = total Brasil impresso na
  planilha, nos **96 meses** em que ele vem impresso;
- = total da UF na planilha UF × tipo em todos os 2.646 casos, **exceto os 27 de
  2024-02**, em que a planilha UF é defeituosa na fonte (Q-E4); dez/2017 não tem
  planilha UF;
- soma das UFs = Brasil na planilha UF, nos 98 meses;
- coluna TOTAL de cada município = soma dos tipos, em todas as linhas;
- recorte combustível contra recorte tipo: 27 casos acima de 0,5%, **todos de
  2021-11**, o mês em que a fonte vem ×10 (Q-E4). As linhas levam
  `alerta_fonte`; o valor não mudou.
