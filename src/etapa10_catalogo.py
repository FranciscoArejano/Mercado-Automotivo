#!/usr/bin/env python3
"""Etapa 10 -- `CATALOGO.md`, o indice do que o repositorio contem.

Gerado a partir do dado, nunca escrito a mao: numero escrito a mao mente em
silencio quando o dado muda. Toda janela, contagem de linhas e observacao sai
dos arquivos no momento da execucao. O texto que nao e' numero -- para que
serve cada produto, que fontes foram mapeadas -- fica em configuracao
(`config/catalogo_usos.csv`, `config/fontes_candidatas.csv`), para ser editado
sem tocar no codigo.

A primeira linha declara o commit do dado descrito: o ultimo commit que alterou
os caminhos de dado, com `-sujo` quando ha' alteracao nao comitada neles. Sem
data de geracao no corpo, de proposito: rodar de novo sobre o mesmo dado produz
o mesmo arquivo, e o catalogo so' muda no git quando o dado muda.

Roda por ultimo no pipeline, depois de tudo que ele descreve.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import classificacao, config, log, periodo  # noqa: E402

ETAPA = "etapa10_catalogo"

# Caminhos cujo ultimo commit e' o "commit do dado".
CAMINHOS_DE_DADO = ("dados/processado", "dados/referencia", "dados/bruto/manifesto.csv",
                    "dados/bruto/pbe", "dados/bruto/origem_paginas", "dados/bruto/comex",
                    "dados/bruto/politicas_paginas", "dados/bruto/fabricas_paginas",
                    "dados/bruto/anfavea", "dados/bruto/ibge",
                    "config", "regras.csv",
                    "saidas/classificacao_rascunho.xlsx")

SEM_TEXTO = "(sem texto em `config/catalogo_usos.csv`)"


def _git(*argumentos: str) -> str | None:
    try:
        feito = subprocess.run(["git", *argumentos], cwd=config.RAIZ,
                               capture_output=True, text=True, timeout=20)
    except Exception:
        return None
    return feito.stdout.strip() if feito.returncode == 0 else None


def commit_do_dado() -> str:
    ultimo = _git("log", "-1", "--format=%h", "--", *CAMINHOS_DE_DADO)
    if not ultimo:
        return "desconhecido (fora de um repositorio git)"
    sujo = _git("status", "--porcelain", "--", *CAMINHOS_DE_DADO)
    return ultimo + ("-sujo" if sujo else "")


def _mil(valor) -> str:
    return f"{int(valor):,}".replace(",", ".")


def _pct(valor: float, casas: int = 2) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def _celula(texto) -> str:
    return str(texto).replace("|", "/").replace("\n", " ").strip()


def _tabela(cabecalho: list[str], linhas: list[list]) -> str:
    saida = "| " + " | ".join(cabecalho) + " |\n"
    saida += "|" + "|".join("---" for _ in cabecalho) + "|\n"
    for linha in linhas:
        saida += "| " + " | ".join(_celula(c) for c in linha) + " |\n"
    return saida + "\n"


def _janela(meses: pd.Series) -> tuple[str, int, list[str]]:
    """'inicio..fim', numero de meses com dado, e os meses do intervalo sem dado."""
    presentes = sorted(set(meses.dropna()))
    if not presentes:
        return "vazia", 0, []
    intervalo = periodo.intervalo(presentes[0], presentes[-1])
    faltam = [m for m in intervalo if m not in set(presentes)]
    return f"{presentes[0]}..{presentes[-1]}", len(presentes), faltam


def _chave_unica(quadro: pd.DataFrame, chave: list[str]) -> str:
    repetidas = int(quadro.duplicated(chave).sum())
    return "unica (conferida)" if repetidas == 0 else f"**{repetidas} linhas repetidas**"


def _lacunas(faltam: list[str]) -> str:
    return ", ".join(f"`{m}`" for m in faltam) if faltam else "nenhuma"


# ------------------------------------------------------------------ produtos


def _painel() -> tuple[dict, str]:
    painel = pd.read_parquet(config.PAINEL)
    janela, n_meses, faltam = _janela(painel["mes_ref"])
    chave = ["mes_ref", "marca", "modelo", "segmento", "sub_segmento_fonte"]
    modelos = painel[classificacao.CHAVE].drop_duplicates().shape[0]
    corpo = [
        "- **Unidade de observacao:** o modelo (variante comercial) no mes e no "
        "sub-segmento em que a fonte o listou.\n",
        "- **Chave:** `(mes_ref, marca, modelo, segmento)`; `sub_segmento_fonte` e' "
        f"atributo da linha, e com ele a combinacao e' {_chave_unica(painel, chave)}.\n",
        f"- **Janela efetiva:** {janela} ({n_meses} meses com dado; meses sem informe "
        f"legivel: {_lacunas(faltam)}).\n",
        f"- **Linhas:** {_mil(len(painel))}; modelos: {_mil(modelos)}; unidades: "
        f"{_mil(painel['unidades'].sum())}; linhas com zero unidades: "
        f"{_mil((painel['unidades'] == 0).sum())}.\n",
        f"- **Marcacoes:** {_mil(painel['nome_suspeito'].sum())} linhas com "
        f"`nome_suspeito`; {_mil(painel['marca_recuperada'].sum())} com "
        f"`marca_recuperada`; {_mil(painel['houve_rebatismo'].sum())} com "
        "`houve_rebatismo`.\n",
    ]
    if config.COBERTURA.exists():
        cobertura = pd.read_csv(config.COBERTURA)
        partes = [f"{segmento} mediana {_pct(grupo['cobertura_pct'].median())}%, minimo "
                  f"{_pct(grupo['cobertura_pct'].min())}%"
                  for segmento, grupo in cobertura.groupby("segmento")]
        corpo.append("- **Cobertura do total publicado** (`saidas/cobertura.csv`): "
                     + "; ".join(partes) + ".\n")
    corpo.append("- **Dicionario:** `saidas/painel_dicionario.md`; validacao: "
                 "`saidas/validacao.md`.\n")
    resumo = {"produto": "painel", "arquivo": "dados/processado/painel.parquet",
              "linhas": len(painel), "janela": janela}
    return resumo, "".join(corpo)


def _painel_bruto() -> tuple[dict, str]:
    bruto = pd.read_parquet(config.PAINEL_BRUTO)
    janela, n_meses, faltam = _janela(bruto["mes_ref"])
    marcadas = int((bruto.get("duplicata_publicada", pd.Series(dtype=str)).fillna("") != "").sum())
    metodos = "; ".join(f"`{k}` {_mil(v)}" for k, v in
                        bruto["metodo_extracao"].value_counts().items())
    tabelas = "; ".join(f"`{k}` {_mil(v)}" for k, v in
                        bruto["origem_tabela"].value_counts().items())
    corpo = (
        "- **Unidade de observacao:** a linha publicada no informe, como a fonte a "
        "escreveu.\n"
        "- **Chave:** `(mes_ref, segmento_fonte, origem_tabela, sub_segmento_fonte, "
        "posicao_fonte)` -- a posicao da linha na tabela da fonte.\n"
        f"- **Janela efetiva:** {janela} ({n_meses} meses com dado; sem dado: "
        f"{_lacunas(faltam)}).\n"
        f"- **Linhas:** {_mil(len(bruto))}; unidades: {_mil(bruto['unidades'].sum())}.\n"
        f"- **Metodo de extracao:** {metodos}.\n"
        f"- **Tabela de origem:** {tabelas}.\n"
        f"- **Duplicatas publicadas pela fonte, marcadas e fora do painel:** {marcadas}.\n"
    )
    resumo = {"produto": "painel_bruto", "arquivo": "dados/processado/painel_bruto.parquet",
              "linhas": len(bruto), "janela": janela}
    return resumo, corpo


def _painel_canal() -> tuple[dict, str]:
    canal = pd.read_parquet(config.PAINEL_CANAL)
    janela, n_meses, faltam = _janela(canal["mes_ref"])
    chave = ["mes_ref", "segmento", "canal", "marca", "modelo"]
    por_canal = "; ".join(f"`{k}` {_mil(v)}" for k, v in canal["canal"].value_counts().items())
    corpo = (
        "- **Unidade de observacao:** o modelo no mes, no segmento e no canal (venda "
        "direta ou varejo), dentro do top-50 que a fonte publica por canal.\n"
        f"- **Chave:** `(mes_ref, segmento, canal, marca, modelo)`, {_chave_unica(canal, chave)}.\n"
        f"- **Janela efetiva:** {janela} ({n_meses} meses com dado; sem dado: "
        f"{_lacunas(faltam)}).\n"
        f"- **Linhas:** {_mil(len(canal))} ({por_canal}); unidades: "
        f"{_mil(canal['unidades'].sum())}.\n"
        "- **Dicionario e advertencia do U:** `saidas/painel_canal_dicionario.md`.\n"
    )
    resumo = {"produto": "painel_canal", "arquivo": "dados/processado/painel_canal.parquet",
              "linhas": len(canal), "janela": janela}
    return resumo, corpo


def _colunas_da_serie(codigo: str, colunas: list[str]) -> list[str]:
    if codigo.isdigit():
        return [c for c in (f"sgs_{codigo}",) if c in colunas]
    import etapa08_macro
    subitem = codigo.removeprefix("ipca_")
    apelido = etapa08_macro.SUBITENS_IPCA.get(subitem)
    return [c for c in colunas if apelido and c.startswith(f"ipca_{apelido}_")]


def _macro(usos: dict[str, dict]) -> tuple[dict, str, list[list]]:
    macro = pd.read_parquet(config.MACRO_MENSAL)
    janela, n_meses, faltam = _janela(macro["mes_ref"])
    series = pd.read_csv(config.SERIES_MACRO, dtype=str, keep_default_na=False)
    linhas, usos_series = [], []
    for _, serie in series.iterrows():
        colunas = _colunas_da_serie(serie["codigo"], list(macro.columns))
        if colunas:
            principal = colunas[0]
            com_dado = macro.loc[macro[principal].notna(), "mes_ref"]
            j, n, buracos = _janela(com_dado)
            efetiva = j + (f" ({len(buracos)} meses vazios dentro)" if buracos else "")
            nomes_colunas = ", ".join(f"`{c}`" for c in colunas)
        else:
            efetiva, n, nomes_colunas = "**sem coluna no arquivo**", 0, "--"
        linhas.append([f"`{serie['codigo']}`", serie["nome"], serie["fonte"], serie["unidade"],
                       efetiva, n, nomes_colunas, serie["natureza_e_ressalvas"]])
        uso = usos.get(serie["codigo"], {})
        usos_series.append([f"`{serie['codigo']}`", serie["nome"],
                            uso.get("sustenta") or SEM_TEXTO, uso.get("nao_sustenta", "")])
    corpo = (
        "- **Unidade de observacao:** o mes.\n"
        f"- **Chave:** `mes_ref`, {_chave_unica(macro, ['mes_ref'])}; uma coluna por "
        "serie (duas por subitem do IPCA: variacao e indice encadeado).\n"
        f"- **Janela efetiva do arquivo:** {janela} ({n_meses} meses; sem linha: "
        f"{_lacunas(faltam)}). A janela de cada serie esta' abaixo.\n"
        f"- **Linhas:** {_mil(len(macro))}; colunas de dado: {len(macro.columns) - 1}; "
        f"series documentadas: {len(series)}.\n\n"
        + _tabela(["codigo", "nome", "fonte", "unidade", "janela efetiva", "observacoes",
                   "colunas", "natureza_e_ressalvas"], linhas)
    )
    resumo = {"produto": "macro_mensal", "arquivo": "dados/processado/macro_mensal.parquet",
              "linhas": len(macro), "janela": janela}
    return resumo, corpo, usos_series


def _propulsao_anual() -> str:
    """A tabela de propulsao por ano, quando gravada."""
    if not config.CLASSIFICACAO_PROPULSAO_ANUAL.exists():
        return ""
    anual = pd.read_parquet(config.CLASSIFICACAO_PROPULSAO_ANUAL)
    tipos = pd.read_csv(config.CLASSIFICACAO_PROPULSAO_TIPOS)
    eletrificados = tipos[~tipos["tipo"].isin(["gasolina", "flex", "diesel"])]
    sem = int((eletrificados["fonte_temporal"] == "vigencia_sem_datacao").sum())
    saidas = int(tipos["fonte_saida"].fillna("").ne("").sum())
    return (
        "- **Serie temporal de propulsao:** `dados/processado/classificacao_propulsao_anual"
        f".parquet`, {_mil(len(anual))} linhas `(marca, modelo, segmento, vigencia_inicio, ano)` "
        "com os tipos oferecidos no ano em duas leituras (`propulsao_no_ano` longa, "
        "`propulsao_no_ano_curta`). `propulsao_na_vigencia` e `eletrificacao_na_vigencia` sao o "
        "conjunto de tudo que foi oferecido em algum momento da vigencia -- nao usar em serie "
        f"temporal. Dos {len(eletrificados)} tipos eletrificados (vigencia x tipo), {sem} entram "
        f"sem datacao (`vigencia_sem_datacao`); {saidas} tipos tem evidencia de saida. Banda da "
        "eletrificacao (piso e tres tetos) em `saidas/eletrificacao_banda.csv`; uso-teste em "
        "`saidas/classificacao_uso_teste.csv`.\n")


def _dimensao_classificacao() -> tuple[dict, str]:
    """A dimensao gravada pela etapa 11 (fase 2)."""
    dim = pd.read_parquet(config.CLASSIFICACAO)
    montagem = pd.read_parquet(config.CLASSIFICACAO_MONTAGEM)
    volume = pd.read_csv(config.CLASSIFICACAO_PROCEDENCIA)
    classificadas = dim[dim["vigencia_inicio_rascunho"] != ""]
    modelos = classificadas[classificacao.CHAVE].drop_duplicates().shape[0]
    fila = pd.read_excel(config.CLASSIFICACAO_RASCUNHO, sheet_name="a_adjudicar", dtype=str,
                         keep_default_na=False)
    pct = volume.pivot(index="procedencia", columns="atributo", values="pct_do_volume")
    linhas_tabela = ["| procedencia | propulsao | carroceria | origem |", "|---|---:|---:|---:|"]
    for procedencia in pct.index:
        p = pct.loc[procedencia]
        if p.sum() > 0:
            linhas_tabela.append(f"| `{procedencia}` | {_pct(p['propulsao'], 1)}% | "
                                 f"{_pct(p['carroceria'], 1)}% | {_pct(p['origem'], 1)}% |")
    com_modo = montagem[montagem["montagem_local"].isin(["fabricacao", "ckd", "skd"])]
    janela = f"{dim['vigencia_inicio'].min()} a {dim['vigencia_fim'].max()}"
    corpo = (
        "- **Estado: dimensao gravada (fase 2)** pela etapa 11, a partir do rascunho "
        "adjudicado `saidas/classificacao_rascunho.xlsx`, que e' a fonte de verdade da "
        "adjudicacao. Ninguem edita o parquet a' mao.\n"
        "- **Unidade de observacao:** o modelo `(marca, modelo, segmento)` numa vigencia "
        "(`vigencia_inicio`, `vigencia_fim`); juncao com o painel pela chave e o mes.\n"
        f"- **Linhas:** {_mil(len(dim))} -- {_mil(len(classificadas))} vigencias de "
        f"{_mil(modelos)} modelos classificados e {_mil(len(dim) - len(classificadas))} modelos "
        f"abaixo do piso de {_mil(config.PISO_CLASSIFICACAO)} unidades (`nao_classificado`). Toda "
        "chave do painel tem linha em todo mes com unidades (validado a cada execucao).\n"
        "- **Procedencia, do volume do painel:**\n\n" + "\n".join(linhas_tabela) + "\n\n"
        "- **Advertencia:** um artigo que use propulsao ou origem como variavel de tratamento "
        "deve restringir-se as procedencias `humana` e `regra_fonte_forte`, e declarar a fracao "
        "do volume que ficou de fora.\n"
        f"- **Pendentes:** {len(fila)} linhas em `a_adjudicar`; o dado as mostra com a proposta "
        "original e procedencia `pendente`.\n"
        f"- **Montagem local:** `dados/processado/classificacao_montagem.parquet`, "
        f"{_mil(len(montagem))} periodos, {len(com_modo)} deles com modo declarado por "
        "fonte (`fabricacao`, `ckd`, `skd`); o resto e' `desconhecido` ou `nao_se_aplica`.\n"
        + _propulsao_anual() +
        "- **Arquivos:** dicionario em `saidas/classificacao_dicionario.md`; procedencia por "
        "atributo em `saidas/classificacao_procedencia.csv`; regras em "
        "`config/regras_classificacao.csv` e `config/regras_adjudicacao.csv`; mapeamento do PBE "
        "em `config/pbe_propulsao.csv` e `config/pbe_modelos.csv`; tipo de fonte em "
        "`config/tipo_fonte_dominio.csv`.\n"
    )
    return ({"produto": "classificacao", "arquivo": "dados/processado/classificacao.parquet",
             "linhas": len(dim), "janela": janela}, corpo)


def _comex() -> tuple[dict, str]:
    """A dimensao de comercio exterior (etapa 12)."""
    if not config.COMEX_VEICULOS.exists():
        return ({"produto": "comex_veiculos", "arquivo": "--", "linhas": 0,
                 "janela": "nao construida"},
                "- **Estado:** nao construida; rode `python src/etapa12_comex.py`.\n")
    dados = pd.read_parquet(config.COMEX_VEICULOS)
    ncms = pd.read_csv(config.NCM_VEICULOS, dtype=str, keep_default_na=False)
    validacao = pd.read_csv(config.COMEX_VALIDACAO)
    janela = f"{dados['mes_ref'].min()} a {dados['mes_ref'].max()}"
    separa = ncms.groupby("posicao")["separa_eletrificados_desde"].first().to_dict()
    corpo = (
        "- **Estado: dimensao gravada** pela etapa 12, a partir das respostas do Comex Stat "
        "(MDIC) guardadas em `dados/bruto/comex/` com SHA-256 no manifesto.\n"
        "- **Unidade de observacao:** fluxo (importacao, exportacao) x NCM x pais x mes, "
        "posicoes 8703 (automoveis) e 8704 (veiculos de carga); tabela separada do painel.\n"
        f"- **Linhas:** {_mil(len(dados))}; {dados['ncm'].nunique()} NCMs, "
        f"{dados['pais'].nunique()} paises.\n"
        f"- **NCMs:** `config/ncm_veiculos.csv`, com `grupo_propulsao_ncm` (as subposicoes de "
        f"eletrificados existem desde {separa.get('8703', '')} em 8703 e "
        f"{separa.get('8704', '') or '--'} em 8704; antes, `sem_separacao`) e `leve` (8704 com "
        "peso em carga maxima ate' 5 t; nao casa exatamente com os comerciais leves da "
        "Fenabrave).\n"
        "- **Unidades:** `unidades` e' a publicada; `unidades_ajustadas` estima pelo peso as "
        "linhas com menos de 500 kg por unidade publicada "
        f"({_mil(int((dados['ajuste_unidades'] == 'estimada_pelo_peso').sum()))} linhas) e e' "
        "o padrao para contar carros. O agregado de carros (`agregado_carros`) tira 8703.10 "
        "(neve, golfe) e o 8704 nao leve ou sem peso na descricao.\n"
        "- **Ressalvas:** o hibrido leve nao tem NCM propria; kit SKD ou CKD entra na NCM do "
        "veiculo completo, entao a importacao pode incluir kits para montagem local.\n"
        f"- **Conferencias:** {int(validacao['falhas'].sum())} falhas em "
        f"`saidas/comex_validacao.csv`; dicionario em `saidas/comex_dicionario.md`.\n")
    return ({"produto": "comex_veiculos", "arquivo": "dados/processado/comex_veiculos.parquet",
             "linhas": len(dados), "janela": janela}, corpo)


def _politicas() -> tuple[dict, str]:
    """O calendario de politicas (etapa 13)."""
    if not config.POLITICAS_MENSAL.exists():
        return ({"produto": "politicas_mensal", "arquivo": "--", "linhas": 0,
                 "janela": "nao construida"},
                "- **Estado:** nao construida; rode `python src/etapa13_politicas.py`.\n")
    mensal = pd.read_parquet(config.POLITICAS_MENSAL)
    atos = pd.read_csv(config.POLITICAS_ATOS, dtype=str, keep_default_na=False)
    aliquotas = pd.read_csv(config.POLITICAS_ALIQUOTAS, dtype=str, keep_default_na=False)
    validacao = pd.read_csv(config.POLITICAS_VALIDACAO)
    paginas = len(list(config.POLITICAS_PAGINAS.glob("*.txt")))
    temas = atos.groupby("tema").size().to_dict()
    tributos = aliquotas.groupby("tributo").size().to_dict()
    janela = f"{mensal['mes_ref'].min()} a {mensal['mes_ref'].max()}"
    corpo = (
        "- **Estado: dimensao gravada** pela etapa 13, a partir de duas tabelas de "
        "referencia escritas a' mao (`dados/referencia/politicas_atos.csv`, "
        "`politicas_aliquotas.csv`), cada linha com trecho literal de uma das "
        f"{paginas} paginas oficiais guardadas em `dados/bruto/politicas_paginas/` "
        "(Planalto, Diario Oficial, gov.br, Banco Central), com SHA-256 no manifesto.\n"
        "- **Unidade de observacao:** mes x ato em vigor; junta ao painel pelo `mes_ref`.\n"
        f"- **Atos:** {len(atos)} -- "
        + ", ".join(f"{t} {n}" for t, n in temas.items()) + ".\n"
        f"- **Aliquotas:** {len(aliquotas)} linhas, so' as que o proprio ato fixa ("
        + ", ".join(f"{t} {n}" for t, n in tributos.items())
        + "); NCM com os pontos da TIPI, prefixo da NCM do Comex Stat.\n"
        "- **Ressalvas:** nao e' a TIPI inteira; `vigencia_fim` vazia quer dizer em vigor ou "
        "fim nao confirmado em pagina aberta; o uso-teste "
        "(`saidas/politicas_uso_teste.csv`) marca datas sem movimento, nao estima efeito.\n"
        f"- **Conferencias:** {int(validacao['falhas'].sum())} falhas em "
        "`saidas/politicas_validacao.csv`; dicionario em `saidas/politicas_dicionario.md`.\n")
    return ({"produto": "politicas_mensal", "arquivo": "dados/processado/politicas_mensal.parquet",
             "linhas": len(mensal), "janela": janela}, corpo)


def _origem() -> tuple[dict, str]:
    """A origem por pais e por fabrica (etapa 14)."""
    if not config.CLASSIFICACAO_ORIGEM.exists():
        return ({"produto": "classificacao_origem", "arquivo": "--", "linhas": 0,
                 "janela": "nao construida"},
                "- **Estado:** nao construida; rode `python src/etapa14_origem.py`.\n")
    prod = pd.read_parquet(config.CLASSIFICACAO_ORIGEM)
    fabricas = pd.read_csv(config.FABRICAS, dtype=str, keep_default_na=False)
    fm = pd.read_csv(config.FABRICA_MODELOS, dtype=str, keep_default_na=False)
    validacao = pd.read_csv(config.ORIGEM_VALIDACAO)
    cobertura = pd.read_csv(config.ORIGEM_COBERTURA)
    divergencias = pd.read_csv(config.ORIGEM_DIVERGENCIAS, dtype=str, keep_default_na=False)
    paginas = len(list(config.FABRICAS_PAGINAS.glob("*.txt")))
    classif = prod[prod["procedencia"] != "nao_classificado"]
    no_brasil = int((fabricas["pais"] == "Brasil").sum())
    abaixo = cobertura[cobertura["atinge_meta_80"] == "nao"]
    janela = f"{classif['periodo_inicio'].min()} a {classif['periodo_fim'].max()}"
    corpo = (
        "- **Estado: dimensao gravada** pela etapa 14, ao lado de `classificacao.parquet` (que "
        "nao muda): pais de producao por vigencia e periodo, a partir da proposta do "
        "assistente (`dados/referencia/origem_pais_proposta.csv`) confirmada por fonte "
        "(`fabricas.csv`, `fabrica_modelos.csv`), cada linha de fonte com trecho literal de "
        f"pagina guardada ({paginas} em `dados/bruto/fabricas_paginas/`, mais as de "
        "`origem_paginas/`).\n"
        "- **Unidade de observacao:** vigencia x periodo x pais de producao; dois paises no "
        "mesmo periodo sao duas linhas.\n"
        f"- **Fabricas:** {len(fabricas)} ({no_brasil} no Brasil, com municipio, UF e codigo "
        f"IBGE); {len(fm)} linhas de fabrica x modelo ("
        + ", ".join(f"{k} {v}" for k, v in fm.groupby("vinculo").size().items()) + ").\n"
        f"- **Procedencia** (linhas classificadas): "
        + ", ".join(f"`{k}` {v}" for k, v in classif.groupby("procedencia").size().items())
        + ".\n"
        "- **Cobertura por fonte forte** (unidades do painel): "
        + ", ".join(f"{r.ano} {_pct(r.pct_fonte_forte, 1)}%" for r in cobertura.itertuples())
        + f". Abaixo da meta de 80%: {', '.join(str(a) for a in abaixo['ano']) or 'nenhum'}.\n"
        f"- **Divergencias ao rascunho:** {len(divergencias)} "
        "(`saidas/origem_divergencias.csv`, aba `origem_pais`).\n"
        f"- **Conferencias:** {int(validacao['falhas'].sum())} falhas em "
        "`saidas/origem_validacao.csv`; dicionario em `saidas/origem_dicionario.md`; "
        "uso-testes em `saidas/origem_uso_teste_*.csv` e `saidas/origem_mapa_uf.csv`.\n")
    return ({"produto": "classificacao_origem",
             "arquivo": "dados/processado/classificacao_origem.parquet", "linhas": len(prod),
             "janela": janela}, corpo)


def _classificacao() -> tuple[dict, str]:
    if config.CLASSIFICACAO.exists():
        return _dimensao_classificacao()
    if not config.CLASSIFICACAO_RASCUNHO.exists():
        return ({"produto": "classificacao", "arquivo": "--", "linhas": 0,
                 "janela": "--"}, "- Nao existe nem rascunho.\n")
    rascunho = pd.read_excel(config.CLASSIFICACAO_RASCUNHO, sheet_name="classificacao",
                             dtype=str, keep_default_na=False)
    fora = pd.read_excel(config.CLASSIFICACAO_RASCUNHO, sheet_name="nao_classificados",
                         dtype=str, keep_default_na=False)
    unidades = rascunho["unidades_na_vigencia"].astype(int)
    total = unidades.sum()
    por_nivel = "; ".join(
        f"`{nivel}` {int((rascunho['confianca'] == nivel).sum())} linhas, "
        f"{_pct(100 * unidades[rascunho['confianca'] == nivel].sum() / total, 1)}% do volume"
        for nivel in classificacao.NIVEIS)
    decididas = int((rascunho["decisao_humana"].str.strip() != "").sum())
    validacao = ""
    if "pbe_situacao" in rascunho:
        pbe = "; ".join(
            f"`{s}` {_pct(100 * unidades[rascunho['pbe_situacao'] == s].sum() / total, 1)}%"
            for s in ("concorda", "diverge", "ausente"))
        com_fonte = rascunho.loc[rascunho["origem_situacao"] == "com_fonte_datada",
                                 classificacao.CHAVE].drop_duplicates().shape[0]
        validacao = (f"- **Validacao contra fonte** (do volume): propulsao contra o PBE -- {pbe}. "
                     f"Origem com fonte datada aberta: {com_fonte} modelos (aba `origem_fontes`).\n")
    if "pendencias" in rascunho:
        na_fila = int((rascunho["pendencias"] != "").sum())
        por_regra = int(((rascunho["regras_aplicadas"] != "")
                         & (rascunho["pendencias"] == "")).sum())
        com_modo = rascunho["montagem_por_periodo"].str.contains("fabricacao|ckd|skd", regex=True)
        forte = {c: _pct(100 * unidades[rascunho[f"procedencia_{c}"].isin(
                     ["humana", "regra_fonte_forte"])].sum() / total, 1)
                 for c in ("propulsao", "carroceria", "origem")}
        validacao += (f"- **Regras de adjudicacao** (`config/regras_adjudicacao.csv`): "
                      f"{por_regra} linhas decididas so' por regra (aba `resolvido_por_regra`); "
                      f"{na_fila} para decisao humana (aba `a_adjudicar`). Montagem local com "
                      f"modo de fonte em parte da vigencia de {int(com_modo.sum())} linhas "
                      "(aba `montagem_local`, por periodo).\n"
                      f"- **Procedencia forte ou humana** (previa, do volume): propulsao "
                      f"{forte['propulsao']}%, carroceria {forte['carroceria']}%, origem "
                      f"{forte['origem']}%.\n")
    modelos = rascunho[classificacao.CHAVE].drop_duplicates().shape[0]
    corpo = (
        "- **Estado: rascunho da fase 1, para adjudicacao. Nao e' dado** -- nada em "
        "`dados/processado/`.\n"
        "- **Unidade de observacao:** o modelo `(marca, modelo, segmento)` numa vigencia "
        "(`vigencia_inicio`, `vigencia_fim`).\n"
        f"- **Linhas:** {_mil(len(rascunho))} modelo-vigencias de {_mil(modelos)} modelos "
        f"(volume acima de {_mil(config.PISO_CLASSIFICACAO)} unidades); "
        f"{_mil(len(fora))} modelos `nao_classificado`.\n"
        f"- **Confianca da proposta:** {por_nivel}.\n"
        + validacao
        + f"- **Decisoes humanas preenchidas:** {decididas} de {len(rascunho)}.\n"
        "- **Arquivo:** `saidas/classificacao_rascunho.xlsx` (abas `leia_me`, `a_adjudicar`, "
        "`resolvido_por_regra`, `montagem_local`, `questoes`, `regras_adjudicacao`, "
        "`validacao`, `regras`); regras em `config/regras_classificacao.csv` e "
        "`config/regras_adjudicacao.csv`, mapeamento do PBE em `config/pbe_propulsao.csv` e "
        "`config/pbe_modelos.csv`, tipo de fonte em `config/tipo_fonte_dominio.csv`.\n"
    )
    return ({"produto": "classificacao (rascunho)",
             "arquivo": "saidas/classificacao_rascunho.xlsx", "linhas": len(rascunho),
             "janela": "--"}, corpo)


def _outros() -> str:
    pdfs = len(list(config.DIR_PDF.glob("*.pdf")))
    regras = pd.read_csv(config.REGRAS, dtype=str) if config.REGRAS.exists() else pd.DataFrame()
    mapa = pd.read_csv(config.MAPA_GRUPOS, dtype=str) if config.MAPA_GRUPOS.exists() else pd.DataFrame()
    linhas = [
        ["`dados/bruto/pdf/`", f"{pdfs} informes originais da Fenabrave, hash em "
                                "`dados/bruto/manifesto.csv`"],
        ["`dados/bruto/pbe/`", f"{len(list((config.DIR_BRUTO / 'pbe').glob('*.pdf')))} "
                               "tabelas do PBE Veicular (Inmetro), com manifesto SHA-256; "
                               "extracao em `saidas/pbe_versoes.csv`"],
        ["`dados/bruto/origem_paginas/`",
         f"{len(list((config.DIR_BRUTO / 'origem_paginas').glob('*.txt')))} paginas de fonte "
         "de origem, abertas e guardadas, com SHA-256"],
        ["`dados/bruto/politicas_paginas/`",
         f"{len(list(config.POLITICAS_PAGINAS.glob('*.txt')))} paginas oficiais do calendario "
         "de politicas, abertas e guardadas, com SHA-256"],
        ["`dados/bruto/fabricas_paginas/`",
         f"{len(list(config.FABRICAS_PAGINAS.glob('*.txt')))} paginas de fabrica e de fabrica "
         "x modelo (Anfavea, ADEFA, INEGI, montadoras, imprensa), com SHA-256"],
        ["`dados/bruto/anfavea/`",
         f"{len(list(config.ANFAVEA_LICENCIAMENTO.glob('*.txt')))} paginas dos anuarios da "
         "Anfavea (licenciamento de nacionais e importados), com SHA-256"],
        ["`dados/bruto/ibge/`", "tabela de municipios do IBGE (codigo do municipio das "
                                "fabricas), com SHA-256"],
        ["`regras.csv`", f"{len(regras)} regras de harmonizacao (rebatismo, desdobramento)"],
        ["`config/mapa_grupos.csv`", f"{len(mapa)} linhas marca-grupo com vigencia"],
        ["`dados/referencia/Vendas_Geral.xlsx`",
         "controle independente (ESPEC sec.7), nao fonte" if config.VENDAS_GERAL.exists()
         else "ausente"],
        ["`saidas/validacao.md`", "invariantes, taxas e testes da rodada, com o commit"],
        ["`saidas/candidatos.xlsx`", "pares candidatos a rebatismo, para adjudicacao"],
        ["`saidas/referencia_cruzada.md`", "confronto com o controle independente"],
    ]
    return _tabela(["arquivo", "conteudo"], linhas)


# ------------------------------------------------------------------ montagem


def gerar() -> str:
    usos_tabela = pd.read_csv(config.CATALOGO_USOS, dtype=str, keep_default_na=False)
    usos = {linha["alvo"]: linha for _, linha in usos_tabela.iterrows()}
    fontes = pd.read_csv(config.FONTES_CANDIDATAS, dtype=str, keep_default_na=False)

    secoes, resumos = [], []
    for nome, construir in (("painel", _painel), ("painel_bruto", _painel_bruto),
                            ("painel_canal", _painel_canal)):
        resumo, corpo = construir()
        resumos.append(resumo)
        secoes.append((nome, resumo["arquivo"], corpo))
    resumo_macro, corpo_macro, usos_series = _macro(usos)
    resumos.append(resumo_macro)
    secoes.append(("macro_mensal", resumo_macro["arquivo"], corpo_macro))
    resumo_class, corpo_class = _classificacao()
    resumos.append(resumo_class)
    secoes.append(("classificacao", resumo_class["arquivo"], corpo_class))
    resumo_comex, corpo_comex = _comex()
    resumos.append(resumo_comex)
    secoes.append(("comex_veiculos", resumo_comex["arquivo"], corpo_comex))
    resumo_politicas, corpo_politicas = _politicas()
    resumos.append(resumo_politicas)
    secoes.append(("politicas_mensal", resumo_politicas["arquivo"], corpo_politicas))
    resumo_origem, corpo_origem = _origem()
    resumos.append(resumo_origem)
    secoes.append(("classificacao_origem", resumo_origem["arquivo"], corpo_origem))

    texto = [
        f"# Catalogo do repositorio -- dado do commit `{commit_do_dado()}`\n\n",
        f"Gerado por `src/{ETAPA}.py` a cada execucao do pipeline. **Nao editar a mao**: "
        "janelas, linhas e contagens saem dos arquivos. O texto de usos esta' em "
        "`config/catalogo_usos.csv` e as fontes candidatas em "
        "`config/fontes_candidatas.csv`; edite la' e rode "
        f"`python src/{ETAPA}.py`.\n\n",
        "O commit da primeira linha e' o ultimo que alterou o dado descrito ("
        + ", ".join(f"`{c}`" for c in CAMINHOS_DE_DADO)
        + "); `-sujo` quer dizer que ha' alteracao nao comitada nesses caminhos, e o "
        "catalogo nao corresponde exatamente a nenhum commit.\n\n",
        "## Indice\n\n",
        _tabela(["produto", "arquivo", "linhas", "janela efetiva"],
                [[r["produto"], f"`{r['arquivo']}`", _mil(r["linhas"]), r["janela"]]
                 for r in resumos]),
        "## Parte A -- o que existe\n\n",
    ]
    for nome, arquivo, corpo in secoes:
        texto.append(f"### `{nome}`\n\n{corpo}")
        ressalvas = usos.get(nome, {}).get("ressalvas")
        if ressalvas:
            texto.append(f"- **Ressalvas principais:** {ressalvas}\n")
        texto.append("\n")
    texto += ["### Outros arquivos\n\n", _outros()]

    texto += [
        "## Parte B -- o que destrava\n\n",
        "### Produtos\n\n",
        _tabela(["produto", "sustenta", "nao sustenta"],
                [[f"`{nome}`", usos.get(nome, {}).get("sustenta") or SEM_TEXTO,
                  usos.get(nome, {}).get("nao_sustenta", "")] for nome, _, _ in secoes]),
        "### Series macro\n\n",
        _tabela(["codigo", "nome", "sustenta", "nao sustenta"], usos_series),
        "## Parte C -- o que foi mapeado e nao construido\n\n",
        _tabela(["fonte", "estado", "observacao"],
                fontes[["fonte", "estado", "observacao"]].values.tolist()),
    ]
    return "".join(texto)


def executar() -> int:
    logger = log.preparar(ETAPA)
    texto = gerar()
    config.CATALOGO_REPOSITORIO.write_text(texto, encoding="utf-8")
    faltando = texto.count(SEM_TEXTO)
    if faltando:
        logger.warning("%d produtos ou series sem texto em config/catalogo_usos.csv", faltando)
    logger.info("gravado %s", log.caminho_relativo(config.CATALOGO_REPOSITORIO))
    return 0


if __name__ == "__main__":
    raise SystemExit(executar())
