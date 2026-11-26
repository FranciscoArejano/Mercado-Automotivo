#!/usr/bin/env python3
"""Etapa 16 -- emissoes por UF, ano, setor, subsetor e gas (SEEG).

Le o bruto reduzido da tabela geral do SEEG (`dados/bruto/seeg/reduzido/`, feito
por `src/coleta/seeg.py`, SHA-256 no manifesto) e grava:

- `dados/processado/emissoes_uf_anual.parquet` -- uma linha por tipo (emissao,
  remocao, bunker, NCI) x UF x ano x setor x categoria x subcategoria x produto x
  gas. A soma e' sobre as colunas mais finas da fonte (detalhamento, recorte,
  atividade geral, bioma), que ficam no bruto reduzido. `uf` vazia e
  `estado_fonte = Não Alocado` e' a parcela que o SEEG nao aloca a estado;
- `saidas/emissoes_uf_anual_validacao.csv` -- conferencia do total Brasil (tabela
  dinamica do proprio SEEG) contra a soma das UFs mais o nao alocado, por setor e
  ano, em CO2e GWP-AR5;
- `saidas/emissoes_uf_anual_dicionario.md`.

O gas: os gases fisicos (CO2, CH4, N2O, ..., em toneladas do gas) e a metrica
`CO2e_GWP_AR5` (toneladas de CO2e pelo GWP do AR5, que e' a metrica de referencia
do SEEG). As outras metricas de CO2e (GWP-AR2, AR4, AR6, GTP) nao entram. A linha
de CO2e nao diz de que gas saiu: o SEEG converte gas a gas e publica so' o total
da linha. Somar `CO2e_GWP_AR5` com um gas fisico e' erro de unidade.

Uso:
    python src/etapa16_emissoes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coleta import comum_coleta as cc  # noqa: E402
from coleta import seeg  # noqa: E402
from comum import config, energia, log  # noqa: E402

ETAPA = "etapa16_emissoes"
NAO_ALOCADO = "Não Alocado"
SETORES = ["Agropecuária", "Energia", "Mudança de Uso da Terra e Floresta",
           "Processos Industriais", "Resíduos"]
RENOMEAR = {"Emissão/Remoção/Bunker": "tipo", "Gás": "gas_fonte", "Setor de emissão": "setor",
            "Categoria emissora": "categoria", "Sub-categoria emissora": "subcategoria",
            "Produto ou sistema": "produto", "Estado": "estado_fonte"}
TOLERANCIA_RELATIVA = 1e-6


def ler_reduzido(parte: str) -> pd.DataFrame:
    manifesto = cc.ler_manifesto(seeg.FONTE)
    chave = seeg.NOME if parte == "dados" else f"{seeg.NOME}#{seeg.ABA_SERIE}"
    caminho = cc.dir_fonte(seeg.FONTE) / manifesto[chave]["reduzido"]
    if cc.sha256_arquivo(caminho) != manifesto[chave]["sha256_reduzido"]:
        raise RuntimeError(f"{caminho}: SHA-256 do reduzido nao bate com o manifesto")
    return pd.read_parquet(caminho)


def gas_e_unidade(gas_fonte: str) -> tuple[str, str]:
    if gas_fonte == seeg.METRICA_CO2E:
        return "CO2e_GWP_AR5", "t CO2e (GWP-AR5)"
    nome = gas_fonte.replace(" (t)", "").strip()
    return nome, "t"


def construir(dados: pd.DataFrame) -> pd.DataFrame:
    anos = [c for c in dados.columns if c.isdigit()]
    chaves = list(RENOMEAR)
    agregado = dados.groupby(chaves, dropna=False)[anos].sum(min_count=1).reset_index()
    longo = agregado.melt(id_vars=chaves, value_vars=anos, var_name="ano", value_name="valor")
    longo = longo.dropna(subset=["valor"]).rename(columns=RENOMEAR)
    longo["ano"] = longo["ano"].astype(int)
    pares = {g: gas_e_unidade(g) for g in longo["gas_fonte"].unique()}
    longo["gas"] = longo["gas_fonte"].map(lambda g: pares[g][0])
    longo["unidade"] = longo["gas_fonte"].map(lambda g: pares[g][1])
    siglas = {e: (None if e == NAO_ALOCADO else energia.sigla_da_uf(e))
              for e in longo["estado_fonte"].unique()}
    sem_sigla = [e for e, s in siglas.items() if s is None and e != NAO_ALOCADO]
    if sem_sigla:
        raise RuntimeError(f"estados do SEEG sem sigla: {sem_sigla}")
    longo["uf"] = longo["estado_fonte"].map(siglas)
    longo["colecao_seeg"] = seeg.COLECAO
    colunas = ["uf", "estado_fonte", "ano", "tipo", "setor", "categoria", "subcategoria",
               "produto", "gas", "unidade", "valor", "gas_fonte", "colecao_seeg"]
    return longo[colunas].sort_values(colunas[:9]).reset_index(drop=True)


def total_da_tabela_dinamica(serie: pd.DataFrame) -> pd.DataFrame:
    """Linhas de setor (e 'Total Geral') da 'Consulta Série Histórica' do SEEG."""
    filtros = {serie.iat[i, 0]: serie.iat[i, 1] for i in range(4)}
    if filtros != {"Emissão/Remoção/Bunker": "Emissão", "Gás": seeg.METRICA_CO2E,
                   "Estado": "(Tudo)", "Bioma": "(Tudo)"}:
        raise RuntimeError(f"filtros inesperados na tabela dinamica: {filtros}")
    cabecalho = serie.iloc[5].tolist()
    anos = {j: int(str(c).replace("Soma de ", "")) for j, c in enumerate(cabecalho)
            if str(c).startswith("Soma de ")}
    linhas, vistos = [], set()
    for i in range(6, len(serie)):
        rotulo = serie.iat[i, 0]
        # o rotulo do setor tambem aparece como categoria (Energia > Agropecuária): a linha
        # do setor e' a primeira ocorrencia, que vem antes das suas categorias
        if (rotulo in SETORES or rotulo == "Total Geral") and rotulo not in vistos:
            vistos.add(rotulo)
            for j, ano in anos.items():
                v = serie.iat[i, j]
                linhas.append({"setor": rotulo, "ano": ano,
                               "total_seeg": None if v is None or pd.isna(v) else float(v)})
    return pd.DataFrame(linhas)


def conferir(produto: pd.DataFrame, serie: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
    co2e = produto[(produto["tipo"] == "Emissão") & (produto["gas"] == "CO2e_GWP_AR5")]
    soma = co2e.groupby(["setor", "ano"])["valor"].sum().reset_index(name="soma_ufs_nao_alocado")
    total = co2e.groupby("ano")["valor"].sum().reset_index(name="soma_ufs_nao_alocado")
    total["setor"] = "Total Geral"
    soma = pd.concat([soma, total], ignore_index=True)
    nao_alocado = co2e[co2e["estado_fonte"] == NAO_ALOCADO].groupby(
        "ano")["valor"].sum().rename("nao_alocado_total")
    referencia = total_da_tabela_dinamica(serie)
    referencia = referencia[referencia["ano"] >= int(produto["ano"].min())]
    comparacao = referencia.merge(soma, on=["setor", "ano"], how="left")
    comparacao["diferenca"] = comparacao["soma_ufs_nao_alocado"] - comparacao["total_seeg"]
    base = comparacao["total_seeg"].abs().where(comparacao["total_seeg"] != 0, 1)
    comparacao["diferenca_relativa"] = comparacao["diferenca"].abs() / base
    falhas = comparacao[comparacao["diferenca_relativa"] > TOLERANCIA_RELATIVA]
    comparacao = comparacao.merge(nao_alocado.reset_index(), on="ano", how="left")
    ufs = set(produto["uf"].dropna())
    linhas = [
        {"conferencia": "total Brasil do SEEG (tabela dinamica 'Consulta Série Histórica', "
                        "Emissão, CO2e GWP-AR5) = soma das UFs + nao alocado, por setor e ano",
         "casos": len(comparacao), "falhas": len(falhas),
         "observacao": f"tolerancia relativa {TOLERANCIA_RELATIVA:g}; maior diferenca "
                       f"relativa {comparacao['diferenca_relativa'].max():.2e}"},
        {"conferencia": "27 UFs presentes", "casos": 27, "falhas": 27 - len(ufs & set(
            energia.ufs()["uf"])), "observacao": ""},
        {"conferencia": "chave unica (tipo, estado, ano, setor, categoria, subcategoria, "
                        "produto, gas)", "casos": len(produto),
         "falhas": int(produto.duplicated(["tipo", "estado_fonte", "ano", "setor", "categoria",
                                           "subcategoria", "produto", "gas"]).sum()),
         "observacao": ""},
    ]
    return linhas, comparacao


CAMPOS = [
    ("uf", "sigla", "UF; vazia na parcela nao alocada a estado."),
    ("estado_fonte", "texto", "Estado como o SEEG escreve (`Não Alocado` para a parcela sem "
     "estado)."),
    ("ano", "inteiro", "Ano civil da emissao."),
    ("tipo", "texto", "`Emissão`, `Remoção`, `Emissão NCI`, `Remoção NCI` (nao contabilizadas "
     "no inventario: remocao em area protegida e emissoes associadas) e `Bunker` (combustivel "
     "de navegacao e aviacao internacional), como a fonte."),
    ("setor", "texto", "Setor de emissao do SEEG (Agropecuária, Energia, Mudança de Uso da Terra "
     "e Floresta, Processos Industriais, Resíduos)."),
    ("categoria", "texto", "Categoria emissora (o 'subsetor'): em Energia, por exemplo, "
     "`Transportes`, `Industrial`, `Geração de eletricidade (serviço público)`."),
    ("subcategoria", "texto", "Sub-categoria emissora: em Transportes, `Rodoviário`, `Aéreo`, "
     "`Ferroviário`, `Hidroviário`."),
    ("produto", "texto", "Produto ou sistema: em Energia, o combustivel (diesel, gasolina, "
     "etanol...)."),
    ("gas", "texto", "Gas fisico (`CO2`, `CH4`, `N2O`, `NOX`, `CO`, `COVNM`, HFCs, PFCs, `SF6`) "
     "ou `CO2e_GWP_AR5` (todos os gases da linha convertidos pelo GWP do AR5)."),
    ("unidade", "texto", "`t` (tonelada do gas) ou `t CO2e (GWP-AR5)`."),
    ("valor", "ver `unidade`", "Soma sobre detalhamento, recorte, atividade geral e bioma "
     "(colunas mais finas da fonte, guardadas no bruto reduzido). Remocao vem com sinal "
     "negativo, como na fonte."),
    ("gas_fonte", "texto", "Rotulo do gas como a fonte escreve."),
    ("colecao_seeg", "texto", "Colecao (versao) do SEEG de que a linha saiu."),
]


def executar() -> int:
    logger = log.preparar(ETAPA)
    dados = ler_reduzido("dados")
    serie = ler_reduzido("serie_historica")
    produto = construir(dados)
    linhas, comparacao = conferir(produto, serie)
    tabela = energia.gravar_validacao(config.EMISSOES_VALIDACAO, linhas)
    comparacao.to_csv(config.DIR_SAIDAS / "emissoes_uf_anual_conferencia_total.csv", index=False)
    if int(tabela["falhas"].sum()):
        logger.error("conferencias do SEEG com falha:\n%s", tabela.to_string())
        return 1
    produto.to_parquet(config.EMISSOES_UF_ANUAL, index=False)
    nao_alocado = comparacao[comparacao["setor"] == "Total Geral"]
    pct = (100 * nao_alocado["nao_alocado_total"] / nao_alocado["total_seeg"]).describe()
    energia.gravar_dicionario(
        config.EMISSOES_DICIONARIO, "Dicionario -- emissoes_uf_anual",
        f"Uma linha por tipo x UF x ano x setor x categoria x subcategoria x produto x gas, "
        f"{produto['ano'].min()} a {produto['ano'].max()}, {len(produto):,} linhas. Gravado "
        f"pela etapa 16 a partir do bruto reduzido da tabela geral do SEEG, **colecao "
        f"{seeg.COLECAO}** (`dados/bruto/seeg/`, SHA-256 do original e do reduzido no "
        "manifesto). O SEEG publica desde 1970; o bruto reduzido guarda de 2003 em diante, a "
        "janela do projeto.",
        CAMPOS,
        [f"**Colecao {seeg.COLECAO}.** Cada colecao do SEEG recalcula a serie inteira: um "
         "numero de 2010 da colecao 14.0 nao e' o mesmo da 13.0. Citar a colecao junto do "
         "numero.",
         "**Metrica de CO2e:** GWP-AR5, a de referencia do SEEG. As outras (GWP-AR2, AR4, AR6, "
         "GTP) estao no original e nao no reduzido.",
         "**Nao somar gases fisicos com CO2e**, nem gases fisicos entre si (toneladas de gases "
         "diferentes). Para participacao de setor, usar `gas == 'CO2e_GWP_AR5'` e `tipo == "
         "'Emissão'`.",
         "**Parcela nao alocada:** parte das emissoes (sobretudo de Energia: transporte aereo e "
         "hidroviario internacional, producao de combustiveis) nao tem estado; vai em `uf` "
         f"vazia. Nas emissoes totais ela fica entre {pct['min']:.1f}% e {pct['max']:.1f}% do "
         "total Brasil, ano a ano. O total Brasil e' a soma das UFs mais o nao alocado "
         "(conferido em `saidas/emissoes_uf_anual_validacao.csv`).",
         "**Emissoes brutas e liquidas:** a remocao vem como linha propria, com sinal negativo; "
         "emissao liquida = Emissão + Remoção. Bunker fica fora do total nacional, como no "
         "inventario."],
        f"SEEG -- Sistema de Estimativas de Emissoes e Remocoes de Gases de Efeito Estufa, "
        f"Observatorio do Clima, tabela geral `{seeg.NOME}` (https://seeg.eco.br/dados/), "
        "colecao 14.0, atualizada em 9/11/2026; URL e data do download no manifesto.")
    log.contagem(logger, linhas=len(produto))
    logger.info("gravado %s", log.caminho_relativo(config.EMISSOES_UF_ANUAL))
    return 0


if __name__ == "__main__":
    raise SystemExit(executar())
