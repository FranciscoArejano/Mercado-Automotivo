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
