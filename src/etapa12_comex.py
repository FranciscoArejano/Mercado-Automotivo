#!/usr/bin/env python3
"""Etapa 12 -- comercio exterior de veiculos (Comex Stat, MDIC).

Le o bruto de `dados/bruto/comex/` (baixado por `ferramentas/comex_baixar.py`,
com SHA-256 no manifesto) e a tabela de NCMs (`config/ncm_veiculos.csv`, gerada
por `ferramentas/comex_ncm.py` e com as colunas `leve` e `grupo_propulsao_ncm`
decididas por regra declarada).

Produtos:
- `dados/processado/comex_veiculos.parquet` -- importacao e exportacao mensal por
  NCM e pais: `mes_ref`, `ano`, `mes`, `fluxo`, `ncm`, `pais`, `fob_usd`, `kg`,
  `unidades` (vazio onde a unidade estatistica da NCM nao e' unidade). As colunas
  da tabela de NCMs vem por juncao;
- `saidas/comex_validacao.csv` -- as conferencias (soma sobre paises contra a
  consulta sem pais, meses faltando, NCMs fora das somas de unidades);
- `saidas/comex_uso_teste_bev.csv`, `comex_uso_teste_origem.csv`,
  `comex_origem_candidatos.csv`, `comex_paises_top10.csv`,
  `comex_diagnostico_peso.csv` -- o uso-teste e o diagnostico de peso por unidade;
- `saidas/comex_dicionario.md`.

Falha (codigo 1, nada gravado) se a soma sobre paises diferir da consulta sem
pais, se faltar mes na janela, ou se a tabela de NCMs nao bater com o bruto (NCM
faltando, unidade ou periodo diferentes).

Uso:
    python src/etapa12_comex.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import comex, config, log  # noqa: E402
from comum.fase2 import CHAVE  # noqa: E402

ETAPA = "etapa12_comex"
PRIMEIRO_MES = "1997-01"
NOTA_KITS = ("Kit SKD ou CKD de um veiculo entra na NCM do veiculo completo (regra geral 2a "
             "do SH): a importacao pode incluir kits para montagem local. Isso se registra, "
             "nao se separa.")
NOTA_LEVE = ("so' 8704; segue a descricao da NCM: `sim` quando o peso em carga maxima "
             "nao passa de 5 t. Nao casa exatamente com os comerciais leves da Fenabrave, "
             "que classifica por modelo. Ficam `indeterminado` o residual 8704.90 e o "
             "eletrico 8704.60, cuja descricao nao da faixa de peso.")
NOTA_MHEV = ("O hibrido leve (MHEV) nao tem NCM propria: pode estar em 8703.40 ou nas NCMs de "
             "combustao. Nao se supoe nenhum dos dois.")


def _ultimo_mes() -> str:
    import json
    dado = json.loads((comex.DIR / "ultima_atualizacao.json").read_bytes())["data"]
    return f"{dado['year']}-{dado['monthNumber']}"


def problemas_da_tabela(ncms: pd.DataFrame, calculada: pd.DataFrame) -> list[str]:
    """A tabela versionada cobre o bruto: toda NCM, com a unidade e o periodo dele."""
    saida = []
    versionada = ncms.set_index("ncm")
    for _, r in calculada.iterrows():
        if r["ncm"] not in versionada.index:
            saida.append(f"NCM {r['ncm']} do bruto fora de config/ncm_veiculos.csv")
            continue
        v = versionada.loc[r["ncm"]]
        for campo in ("unidade_estatistica", "primeiro_mes", "ultimo_mes",
                      "separa_eletrificados_desde"):
            if str(v[campo]) != str(r[campo]):
                saida.append(f"NCM {r['ncm']}: {campo} {v[campo]!r} na tabela, {r[campo]!r} "
                             "no bruto")
    if set(ncms["grupo_propulsao_ncm"]) - set(comex.GRUPOS):
        saida.append("grupo_propulsao_ncm fora da lista")
    return saida


# ------------------------------------------------------------- uso-teste


def _importacao_leve(dados: pd.DataFrame, ncms: pd.DataFrame) -> pd.DataFrame:
    """Importacao de 8703 e de 8704 leve, com as colunas da tabela de NCMs e a marca
    de peso baixo por unidade."""
    juntos = dados[dados["fluxo"] == "importacao"].merge(ncms, on="ncm")
    juntos = juntos[(juntos["posicao"] == "8703") | (juntos["leve"] == "sim")]
    return juntos.assign(peso_baixo=comex.peso_baixo(juntos))


def diagnostico_peso(dados: pd.DataFrame, ncms: pd.DataFrame) -> pd.DataFrame:
    """Por ano: unidades importadas (8703 + 8704 leve) em linhas com menos de
    `comex.KG_MINIMO` kg por unidade."""
    imp = _importacao_leve(dados, ncms)
    linhas = []
    for ano, g in imp.groupby("ano"):
        baixo = g[g["peso_baixo"]]
        principal = (baixo.groupby(["ncm", "pais"])["unidades"].sum().sort_values()
                     .tail(1))
        linhas.append({"ano": ano, "unidades": int(g["unidades"].sum()),
                       "unidades_peso_baixo": int(baixo["unidades"].sum()),
                       "pct_peso_baixo": round(100 * baixo["unidades"].sum()
                                               / max(int(g["unidades"].sum()), 1), 1),
                       "maior_caso": (f"{principal.index[0][0]} {principal.index[0][1]} "
                                      f"({int(principal.iloc[0])})") if len(principal) else ""})
    return pd.DataFrame(linhas)


def uso_teste_bev(dados: pd.DataFrame, ncms: pd.DataFrame, anual: pd.DataFrame
                  ) -> pd.DataFrame:
    """Importacao de eletricos puros contra as unidades do painel de vigencia-ano so'
    `bev` na leitura longa, 2017 em diante."""
    importacao = _importacao_leve(dados, ncms)
    bev = importacao[importacao["grupo_propulsao_ncm"] == "bev"]
    imp = bev.groupby("ano")["unidades"].sum()
    imp_pesado = bev[~bev["peso_baixo"]].groupby("ano")["unidades"].sum()
    painel = anual[anual["propulsao_no_ano"] == "bev"].groupby("ano")["unidades"].sum()
    linhas = []
    acumulada = 0
    for ano in range(2017, int(dados["ano"].max()) + 1):
        i, p = int(imp.get(ano, 0)), int(painel.get(ano, 0))
        acumulada += i - p
        sem_baixo = int(imp_pesado.get(ano, 0))
        linhas.append({"ano": ano, "importacao_bev": i,
                       "importacao_bev_sem_peso_baixo": sem_baixo, "painel_so_bev": p,
                       "razao": round(i / p, 2) if p else None,
                       "razao_sem_peso_baixo": round(sem_baixo / p, 2) if p else None,
                       "diferenca_acumulada": acumulada})
    return pd.DataFrame(linhas)


def uso_teste_origem(dados: pd.DataFrame, ncms: pd.DataFrame, dim: pd.DataFrame,
                     painel: pd.DataFrame) -> pd.DataFrame:
    """Importacao anual (8703 + 8704 leve) contra as unidades do painel de vigencias
    `importado`, com `ambos` contado como 0% e como 100%."""
    importacao = _importacao_leve(dados, ncms)
    imp = importacao.groupby("ano")["unidades"].sum()
    imp_pesado = importacao[~importacao["peso_baixo"]].groupby("ano")["unidades"].sum()
    meses = painel.groupby(CHAVE + ["mes_ref"], as_index=False)["unidades"].sum()
    juntos = meses.merge(dim[CHAVE + ["vigencia_inicio", "vigencia_fim", "origem_producao"]],
                         on=CHAVE)
    juntos = juntos[(juntos["mes_ref"] >= juntos["vigencia_inicio"])
                    & (juntos["mes_ref"] <= juntos["vigencia_fim"])]
    juntos = juntos.assign(ano=juntos["mes_ref"].str[:4].astype(int))
    por = juntos.pivot_table(index="ano", columns="origem_producao", values="unidades",
                             aggfunc="sum", fill_value=0)
    linhas = []
    for ano in range(2003, int(dados["ano"].max()) + 1):
        if ano not in por.index:
            continue
        p = por.loc[ano]
        importado, ambos = int(p.get("importado", 0)), int(p.get("ambos", 0))
        i = int(imp.get(ano, 0))
        linhas.append({"ano": ano, "importacao": i,
                       "importacao_sem_peso_baixo": int(imp_pesado.get(ano, 0)),
                       "painel_importado_min": importado,
                       "painel_importado_max": importado + ambos,
                       "painel_nao_classificado": int(p.get("", 0)),
                       "painel_total": int(p.sum()),
                       "razao_min": round(i / (importado + ambos), 2) if importado + ambos
                       else None,
                       "razao_max": round(i / importado, 2) if importado else None})
    return pd.DataFrame(linhas)


RAZAO_GRANDE = 1.3  # importacao 30% acima do maximo do painel importado, sem peso baixo


def anos_de_distancia(origem: pd.DataFrame) -> list[int]:
    """Anos em que a importacao, mesmo sem as linhas de peso baixo, passa o maximo do
    painel importado (`ambos` a 100%) em `RAZAO_GRANDE` ou mais."""
    razao = origem["importacao_sem_peso_baixo"] / origem["painel_importado_max"]
    return origem.loc[razao >= RAZAO_GRANDE, "ano"].astype(int).tolist()


def candidatos_da_origem(dim: pd.DataFrame, painel: pd.DataFrame, anos: list[int],
                         maximo: int = 10) -> pd.DataFrame:
    """Modelos de muito volume com origem `nacional` so' por `proposta` nos anos de
    distancia grande: os que poderiam ter versao importada nao classificada."""
    meses = painel.groupby(CHAVE + ["mes_ref"], as_index=False)["unidades"].sum()
    juntos = meses.merge(dim[CHAVE + ["vigencia_inicio", "vigencia_fim", "origem_producao",
                                      "procedencia_origem"]], on=CHAVE)
    juntos = juntos[(juntos["mes_ref"] >= juntos["vigencia_inicio"])
                    & (juntos["mes_ref"] <= juntos["vigencia_fim"])
                    & (juntos["procedencia_origem"] == "proposta")
                    & (juntos["origem_producao"] == "nacional")]
    juntos = juntos.assign(ano=juntos["mes_ref"].str[:4].astype(int))
    juntos = juntos[juntos["ano"].isin(anos)]
    tabela = (juntos.groupby(["ano"] + CHAVE + ["origem_producao"], as_index=False)["unidades"]
              .sum().sort_values(["ano", "unidades"], ascending=[True, False]))
    return tabela.groupby("ano").head(maximo).reset_index(drop=True)


def paises_top10(dados: pd.DataFrame, ncms: pd.DataFrame) -> pd.DataFrame:
    imp = _importacao_leve(dados, ncms)
    por = imp.groupby(["ano", "pais"], as_index=False)["unidades"].sum()
    so_8703 = (imp[imp["posicao"] == "8703"].groupby(["ano", "pais"])["unidades"].sum()
               .rename("unidades_8703"))
    por = por.merge(so_8703, on=["ano", "pais"], how="left").fillna({"unidades_8703": 0})
    por["unidades_8703"] = por["unidades_8703"].astype(int)
    por["posicao_no_ano"] = por.groupby("ano")["unidades"].rank(ascending=False,
                                                                method="first").astype(int)
    por["pct_do_ano"] = (100 * por["unidades"]
                         / por.groupby("ano")["unidades"].transform("sum")).round(1)
    return por[por["posicao_no_ano"] <= 10].sort_values(["ano", "posicao_no_ano"])


# ----------------------------------------------------------------- execucao


def executar() -> int:
    logger = log.preparar(ETAPA)
    if not config.NCM_VEICULOS.exists():
        logger.error("sem %s: rode src/ferramentas/comex_ncm.py",
                     log.caminho_relativo(config.NCM_VEICULOS))
        return 1
    com_pais, sem_pais = comex.ler_bruto()
    ncms = pd.read_csv(config.NCM_VEICULOS, dtype=str, keep_default_na=False)
    calculada = comex.tabela_de_ncms(com_pais, comex.unidades_das_ncms())
    ultimo = _ultimo_mes()

    conferencia = comex.conferencia_paises(com_pais, sem_pais)
    diferentes = conferencia[(conferencia[["fob_usd_diferenca", "kg_diferenca",
                                           "quantidade_diferenca"]] != 0).any(axis=1)]
    faltando = comex.meses_faltando(com_pais, PRIMEIRO_MES, ultimo)
    fora_da_soma = ncms[ncms["unidade_estatistica"] != comex.UNIDADE]
    problemas = problemas_da_tabela(ncms, calculada)
    problemas += [f"{r['fluxo']} NCM {r['ncm']} {r['ano']}: soma sobre paises difere da "
                  "consulta sem pais" for _, r in diferentes.head(20).iterrows()]
    problemas += [f"{r['fluxo']} {r['posicao']}: mes {r['mes_ref']} sem dado"
                  for _, r in faltando.head(20).iterrows()]
    if problemas:
        for p in problemas[:40]:
            logger.error(p)
        logger.error("%d problemas: nada gravado", len(problemas))
        return 1

    dados = comex.produto(com_pais, ncms)
    validacao = pd.DataFrame([
        {"conferencia": "soma sobre paises = consulta sem pais (fluxo x NCM x ano)",
         "casos": len(conferencia), "falhas": len(diferentes)},
        {"conferencia": f"meses faltando na janela {PRIMEIRO_MES} a {ultimo} "
                        "(fluxo x posicao)", "casos": com_pais.groupby(
            ["fluxo", "posicao"]).ngroups, "falhas": len(faltando)},
        {"conferencia": "NCMs fora das somas de unidades (unidade estatistica nao e' "
                        f"unidade): {', '.join(fora_da_soma['ncm']) or 'nenhuma'}",
         "casos": len(ncms), "falhas": 0},
    ])

    painel = pd.read_parquet(config.PAINEL, columns=CHAVE + ["mes_ref", "unidades"])
    dim = pd.read_parquet(config.CLASSIFICACAO)
    anual = pd.read_parquet(config.CLASSIFICACAO_PROPULSAO_ANUAL)
    bev = uso_teste_bev(dados, ncms, anual)
    origem = uso_teste_origem(dados, ncms, dim, painel)
    paises = paises_top10(dados, ncms)
    distantes = anos_de_distancia(origem)
    candidatos = candidatos_da_origem(dim, painel, distantes)
    peso = diagnostico_peso(dados, ncms)
    altos = peso[peso["pct_peso_baixo"] > 10]["ano"].tolist()
    validacao = pd.concat([validacao, pd.DataFrame([{
        "conferencia": (f"diagnostico, nao falha: unidades importadas leves em linhas com menos "
                        f"de {comex.KG_MINIMO} kg por unidade (saidas/comex_diagnostico_peso.csv); "
                        f"anos acima de 10%: {', '.join(map(str, altos)) or 'nenhum'}"),
        "casos": len(peso), "falhas": 0}])], ignore_index=True)

    config.DIR_PROCESSADO.mkdir(parents=True, exist_ok=True)
    dados.to_parquet(config.COMEX_VEICULOS, index=False)
    validacao.to_csv(config.COMEX_VALIDACAO, index=False)
    bev.to_csv(config.DIR_SAIDAS / "comex_uso_teste_bev.csv", index=False)
    origem.to_csv(config.DIR_SAIDAS / "comex_uso_teste_origem.csv", index=False)
    paises.to_csv(config.DIR_SAIDAS / "comex_paises_top10.csv", index=False)
    peso.to_csv(config.DIR_SAIDAS / "comex_diagnostico_peso.csv", index=False)
    candidatos.to_csv(config.DIR_SAIDAS / "comex_origem_candidatos.csv", index=False)
    config.COMEX_DICIONARIO.write_text(dicionario(dados, ncms, validacao, ultimo),
                                       encoding="utf-8")
    logger.info("comex: %d linhas, %d NCMs, %s a %s; %d NCMs fora das somas de unidades",
                len(dados), dados["ncm"].nunique(), dados["mes_ref"].min(),
                dados["mes_ref"].max(), len(fora_da_soma))
    logger.info("gravado %s", log.caminho_relativo(config.COMEX_VEICULOS))
    return 0


def _tabela_ncms(ncms: pd.DataFrame) -> str:
    linhas = ["| NCM | grupo | leve | periodo | descricao |", "|---|---|---|---|---|"]
    for _, r in ncms.iterrows():
        linhas.append(f"| {r['ncm']} | `{r['grupo_propulsao_ncm']}` | {r['leve'] or '--'} | "
                      f"{r['primeiro_mes']} a {r['ultimo_mes']} | {r['descricao'][:90]} |")
    return "\n".join(linhas)


def dicionario(dados: pd.DataFrame, ncms: pd.DataFrame, validacao: pd.DataFrame,
               ultimo: str) -> str:
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    separa = ncms.groupby("posicao")["separa_eletrificados_desde"].first().to_dict()
    return f"""# Dicionario de dados -- `comex_veiculos.parquet`

Gerado em {agora} (UTC) por `src/etapa12_comex.py`, a partir das respostas do Comex
Stat (API `https://api-comexstat.mdic.gov.br/general`) guardadas em
`dados/bruto/comex/` com SHA-256 no manifesto.

Importacao e exportacao **mensais, oficiais, por NCM e pais**, das posicoes 8703
(automoveis) e 8704 (veiculos de carga), de {PRIMEIRO_MES} a {ultimo}: {len(dados):,}
linhas, {dados['ncm'].nunique()} NCMs. Tabela de fatos **separada** do painel: a
juncao e' do codigo de analise.

| coluna | tipo | descricao |
|---|---|---|
| `mes_ref`, `ano`, `mes` | texto AAAA-MM, inteiros | mes do registro |
| `fluxo` | texto | `importacao` ou `exportacao` |
| `ncm` | texto | NCM de 8 digitos; descricao e classificacao em `config/ncm_veiculos.csv` (juncao por `ncm`) |
| `pais` | texto | pais de origem (importacao) ou de destino (exportacao), nome do Comex Stat |
| `fob_usd` | inteiro | valor FOB em dolares |
| `kg` | inteiro | peso liquido em kg |
| `unidades` | inteiro | quantidade estatistica, so' onde a unidade estatistica da NCM e' "{comex.UNIDADE}"; vazio nas demais |

## `config/ncm_veiculos.csv`

Uma linha por NCM encontrada: descricao oficial (`tables/ncm` do Comex Stat),
unidade estatistica, primeiro e ultimo mes com dado, e duas colunas decididas por
regra (`src/comum/comex.py`):

- `grupo_propulsao_ncm`: `centelha` (gasolina, etanol, flex), `diesel`, `hev`,
  `phev`, `bev`, `outros`, `sem_separacao`. O grupo e' o do texto da subposicao
  depois da separacao. **As subposicoes de eletrificados so' existem desde
  {separa.get('8703', '')} em 8703 e {separa.get('8704', '') or '(nenhuma)'} em
  8704** (`separa_eletrificados_desde`, conferido pela vigencia dos codigos):
  antes disso nenhuma NCM separa o eletrificado, e o mes deve ser lido como
  `sem_separacao` (`comum.comex.grupo_no_mes`). NCM que so' existiu antes da
  separacao tem `sem_separacao` na propria tabela. Em 8704, as subposicoes do SH
  2022 (8704.4x e 8704.5x) nao distinguem hibrido com e sem recarga externa (o
  texto oficial nao fala de recarga): ficam `hev`.
- `leve`: {NOTA_LEVE}

**Duas coisas que a NCM nao diz.** {NOTA_MHEV} {NOTA_KITS}

**Peso por unidade.** Em alguns anos, parte das unidades importadas esta' em linhas
(NCM x pais x mes) com menos de {comex.KG_MINIMO} kg por unidade, o que nao descreve
veiculo completo: 2001, 2003 e 2006 (mais de 30% das unidades leves) e 2019 a
2021 (10% a 17%). O produto nao filtra nada; `saidas/comex_diagnostico_peso.csv`
mede, e o uso-teste mostra as series com e sem essas linhas
(`comum.comex.peso_baixo`).

{_tabela_ncms(ncms)}

## Conferencias (`saidas/comex_validacao.csv`)

{validacao.to_markdown(index=False)}

## Uso-teste

`saidas/comex_uso_teste_bev.csv` (importacao de eletricos puros contra o painel so'
`bev`), `saidas/comex_uso_teste_origem.csv` (importacao contra o painel `importado`,
com `ambos` a 0% e a 100%) e `saidas/comex_paises_top10.csv`. Descritos no registro
da rodada; a explicacao das distancias fica para o calendario de politicas.
"""


if __name__ == "__main__":
    raise SystemExit(executar())
