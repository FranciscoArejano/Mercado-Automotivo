#!/usr/bin/env python3
"""Etapa 6 -- relatorio de validacao (ESPEC.md sec.6).

Gera `saidas/validacao.md` a cada execucao. Tres classes de resultado:

- **falha**: quebra de identidade ou de invariante. Falha a execucao.
- **premissa nao confirmada**: painel e fonte concordam entre si e discordam de
  algo que a ESPEC dava como conhecido. Reportado, nunca corrigido (sec.9.4).
- **medida**: cobertura, corte de publicacao, taxas. Entregue como produto.

Uso:
    python src/etapa06_validacao.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import (  # noqa: E402
    ciclo_vida, cobertura as mod_cobertura, concentracao, config, log,
    meses as mod_meses, periodo, truncamento, visoes,
)

ETAPA = "etapa06_validacao"

# Numeros da planilha de controle (ESPEC.md sec.7), em unidades. Nao e' fonte.
REFERENCIA_SEC7 = {
    2014: {"total": 3_325_627, "modelos": 310, "hhi_marca": 1_297},
    2016: {"total": 1_986_502, "modelos": 301, "hhi_marca": 1_055},
    2020: {"total": 1_949_892, "modelos": 299, "hhi_marca": 1_146},
    2022: {"total": 1_952_794, "modelos": 270, "hhi_marca": 1_208},
}

# Premissas de sanidade temporal, revisadas contra a propria fonte (Q8).
PREMISSA_MENOR_MES = ("2014-01", "2023-12", "2020-04")
# A premissa vale na janela em que foi estabelecida -- ate' ago/2023, fim da
# planilha de controle. Depois disso a serie tem meses maiores, o que nao a
# contradiz. O maximo da serie inteira e o maximo desde 2019 vao a parte.
PREMISSA_MAIOR_MES = ("2021-01", "2023-08", "2023-07")
SALTO_JULHO_2023 = ("2023-06", "2023-07", 0.15)


def _mil(valor) -> str:
    """Milhar com ponto, como se escreve em portugues."""
    return f"{int(valor):,}".replace(",", ".")


def _tabela(quadro: pd.DataFrame, maximo: int | None = None) -> str:
    if quadro is None or quadro.empty:
        return "_(vazio)_\n"
    recorte = quadro if maximo is None else quadro.head(maximo)
    texto = recorte.to_markdown(index=False)
    if maximo is not None and len(quadro) > maximo:
        texto += (f"\n\n_({len(quadro) - maximo} linhas restantes omitidas; "
                  "ver CSV correspondente.)_")
    return texto + "\n"


def _totais_publicados() -> pd.DataFrame:
    caminho = config.DIR_PROCESSADO / "extracao_totais.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=["mes", "segmento", "total_publicado"])
    totais = pd.read_csv(caminho)
    return totais[totais["total_publicado"].notna()][["mes", "segmento", "total_publicado"]]


def _extracao_completa() -> pd.DataFrame:
    arquivos = sorted(config.DIR_EXTRACAO.glob("*.csv"))
    if not arquivos:
        return pd.DataFrame()
    return pd.concat(
        [pd.read_csv(a, dtype=str, keep_default_na=False) for a in arquivos], ignore_index=True
    )


def _coerencia_entre_meses(bruto_extracao: pd.DataFrame, meses_uteis: set[str]):
    """Usa a redundancia da propria fonte para conferir a leitura.

    Cada linha traz o mes anterior, o mes de referencia e o acumulado do ano.
    Duas identidades tem de valer sem depender de interpretacao nossa:
    `unidades_mes_anterior(M)` = `unidades_mes(M-1)`, e
    `acumulado(M) - acumulado(M-1)` = `unidades_mes(M)` dentro do mesmo ano.
    """
    if bruto_extracao.empty:
        return pd.DataFrame(), pd.DataFrame(), {}
    dados = bruto_extracao[bruto_extracao["origem_tabela"] == "sub_segmento"].copy()
    if dados.empty:
        return pd.DataFrame(), pd.DataFrame(), {}
    for coluna in ("unidades_mes", "unidades_mes_anterior", "unidades_acumulado"):
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")
    chave = ["mes", "segmento", "nome_completo_fonte"]
    dados = dados.groupby(chave, as_index=False)[
        ["unidades_mes", "unidades_mes_anterior", "unidades_acumulado"]
    ].sum()

    dados["mes_anterior"] = dados["mes"].map(
        lambda m: periodo.de_indice(periodo.para_indice(m) - 1))
    anterior = dados[["mes", "segmento", "nome_completo_fonte", "unidades_mes",
                      "unidades_acumulado"]].rename(columns={
        "mes": "mes_anterior", "unidades_mes": "mes_anterior_observado",
        "unidades_acumulado": "acumulado_anterior",
    })
    junto = dados.merge(anterior, on=["mes_anterior", "segmento", "nome_completo_fonte"],
                        how="left")
    junto = junto[junto["mes_anterior"].isin(meses_uteis) & junto["mes"].isin(meses_uteis)]

    comparados = {
        "mes_anterior": int(junto["mes_anterior_observado"].notna().sum()),
        "acumulado": int(junto["acumulado_anterior"].notna().sum()),
    }
    coluna = junto[junto["mes_anterior_observado"].notna()].copy()
    coluna["diferenca"] = coluna["unidades_mes_anterior"] - coluna["mes_anterior_observado"]
    coluna = coluna[coluna["diferenca"] != 0][
        ["mes", "segmento", "nome_completo_fonte", "unidades_mes_anterior",
         "mes_anterior_observado", "diferenca"]
    ].sort_values("diferenca", key=abs, ascending=False)

    janeiro = junto["mes"].str.endswith("-01")
    acumulado = junto.copy()
    acumulado["acumulado_esperado"] = acumulado["unidades_mes"] + acumulado[
        "acumulado_anterior"].where(~janeiro, 0.0)
    acumulado = acumulado[acumulado["acumulado_esperado"].notna()]
    acumulado["diferenca"] = acumulado["unidades_acumulado"] - acumulado["acumulado_esperado"]
    acumulado = acumulado[acumulado["diferenca"] != 0][
        ["mes", "segmento", "nome_completo_fonte", "unidades_acumulado",
         "acumulado_esperado", "diferenca"]
    ].sort_values("diferenca", key=abs, ascending=False)
    return coluna, acumulado, comparados


def _ciclos_da_grade(largo: pd.DataFrame, meses: list[str], limiar: float,
                     modo: str | None = None) -> pd.DataFrame:
    primeiro, ultimo = meses[0], meses[-1]
    registros = []
    for chave, serie in largo.iterrows():
        ciclo = ciclo_vida.calcular(
            serie, limiar, primeiro, ultimo, janela=config.JANELA_PICO_MESES,
            modo=modo or config.PICO_MOVEL_MODO,
        )
        if ciclo.entrada is None:
            continue
        registros.append({
            "marca": chave[0], "modelo": chave[1], "segmento": chave[2],
            "entrada": ciclo.entrada, "saida": ciclo.saida, "pico": ciclo.pico,
            "unidades_totais": ciclo.unidades_totais,
            "censura_esquerda": ciclo.censura_esquerda,
            "censura_direita": ciclo.censura_direita,
        })
    return pd.DataFrame(registros)


def _taxas(ciclos: pd.DataFrame, ativos: pd.Series, limiar: float,
           sufixo: str = "") -> pd.DataFrame:
    rotulo = f"{limiar:.0%}{sufixo}"
    entradas = (
        ciclos[~ciclos["censura_esquerda"]]
        .assign(ano=lambda q: q["entrada"].str.slice(0, 4).astype(int))
        .groupby("ano").size().rename(f"entradas_{rotulo}")
    )
    saidas = (
        ciclos[~ciclos["censura_direita"]]
        .assign(ano=lambda q: q["saida"].str.slice(0, 4).astype(int))
        .groupby("ano").size().rename(f"saidas_{rotulo}")
    )
    tabela = pd.concat([ativos.rename("ativos"), entradas, saidas], axis=1).fillna(0).astype(int)
    tabela[f"taxa_entrada_{rotulo}"] = (
        tabela[f"entradas_{rotulo}"] / tabela["ativos"]).round(4)
    tabela[f"taxa_saida_{rotulo}"] = (tabela[f"saidas_{rotulo}"] / tabela["ativos"]).round(4)
    return tabela


def _ativos_por_ano(por_modelo: pd.DataFrame) -> pd.Series:
    return (
        por_modelo[por_modelo["unidades"] > 0]
        .groupby("ano")[visoes.CHAVE_MODELO]
        .apply(lambda b: b.drop_duplicates().shape[0])
        .rename("ativos")
    )


def _mudancas_de_ordenacao(tabela: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    presentes = [c for c in colunas if c in tabela.columns]
    if len(presentes) < 2:
        return pd.DataFrame()
    ordens = pd.DataFrame(
        {c: tabela.set_index("ano")[c].rank(ascending=False, method="min") for c in presentes}
    )
    return ordens[ordens.nunique(axis=1) > 1].reset_index()


def executar() -> int:  # noqa: C901 -- relatorio longo por natureza
    logger = log.preparar(ETAPA)
    for exigido in (config.PAINEL_BRUTO, config.PAINEL):
        if not exigido.exists():
            raise log.ErroDeParsing(
                f"{log.caminho_relativo(exigido)} nao existe -- rode as etapas anteriores.")
    bruto = pd.read_parquet(config.PAINEL_BRUTO)
    painel = pd.read_parquet(config.PAINEL)
    por_modelo = visoes.por_modelo(painel)
    meses = sorted(painel["mes_ref"].unique())
    totais = _totais_publicados()
    partes: list[str] = []
    falhas: list[str] = []
    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)

    partes.append(
        "# Validacao do painel de vendas de veiculos 0 km\n\n"
        f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC) por "
        f"`src/{ETAPA}.py`.\n\n"
        f"- Periodo: **{meses[0]} a {meses[-1]}** ({len(meses)} meses)\n"
        f"- Linhas: painel bruto {len(bruto):,} / painel {len(painel):,} / "
        f"visao por modelo {len(por_modelo):,}\n"
        f"- Unidades: {int(painel['unidades'].sum()):,}\n"
        f"- Modelos (marca x modelo x segmento): "
        f"{por_modelo[visoes.CHAVE_MODELO].drop_duplicates().shape[0]:,}\n"
        f"- Leitura de \"pico movel de 12 meses\": `{config.PICO_MOVEL_MODO}` "
        "(QUESTOES_ABERTAS.md, Q1)\n"
        "- `regras.csv` vazio por decisao desta rodada: nada foi fundido, e as taxas de "
        "entrada e saida abaixo sao o **limite superior** dessas taxas -- o cenario em que "
        "todo rebatismo conta como morte e nascimento.\n"
    )

    # ---------------------------------------------------- 1. invariante central
    antes = bruto.groupby("mes_ref")["unidades"].sum()
    depois = painel.groupby("mes_ref")["unidades"].sum()
    invariante = pd.DataFrame({"painel_bruto": antes, "painel": depois}).fillna(0)
    invariante["diferenca"] = invariante["painel"] - invariante["painel_bruto"]
    quebras = invariante[invariante["diferenca"] != 0]
    partes.append("\n## 1. Invariante central\n\n"
                  "A soma de unidades por mes tem de ser identica nos dois paineis. "
                  "Harmonizacao redistribui rotulos; nao cria nem destroi unidades.\n\n")
    if quebras.empty:
        partes.append(f"**OK** -- identica nos {len(invariante)} meses.\n")
    else:
        falhas.append(f"invariante central quebrado em {len(quebras)} meses")
        partes.append("**FALHOU**\n\n" + _tabela(quebras.reset_index(), 20))

    # -------------------------------------------------- 2. sanidade temporal
    mensal = painel.groupby("mes_ref")["unidades"].sum()
    publicado_mensal = totais.groupby("mes")["total_publicado"].sum() if not totais.empty else None
    partes.append(
        "\n## 2. Sanidade temporal\n\n"
        "Cada teste roda duas vezes: no painel e no **total que a propria fonte publica**. "
        "E' a segunda rodada que diz de quem e' o erro. Painel discordando da fonte e' bug "
        "nosso -- provavelmente atribuicao de mes, por leitura de cabecalho (sec.7) -- e "
        "falha a execucao. Painel e fonte concordando entre si e discordando da premissa e' "
        "premissa nao confirmada: reportada, nao corrigida.\n\n"
    )

    def conferir(rotulo, meses_alvo, esperado, extremo):
        disponiveis = [m for m in meses_alvo if m in mensal.index]
        if not disponiveis:
            return
        obtido = getattr(mensal.loc[disponiveis], extremo)()
        na_fonte = None
        if publicado_mensal is not None:
            comuns = [m for m in disponiveis if m in publicado_mensal.index]
            if comuns:
                na_fonte = getattr(publicado_mensal.loc[comuns], extremo)()
        if obtido == esperado:
            situacao, detalhe = "OK", ""
        elif na_fonte is not None and na_fonte != obtido:
            situacao = "FALHOU"
            detalhe = (f" -- o total publicado pela fonte aponta `{na_fonte}`, "
                       "entao a divergencia e' do painel")
            falhas.append(f"{rotulo}: painel diz {obtido}, fonte diz {na_fonte}")
        else:
            situacao = "PREMISSA NAO CONFIRMADA"
            detalhe = (f" -- o total publicado pela fonte tambem aponta `{na_fonte}`; "
                       "painel e fonte concordam e quem nao se confirma e' a premissa")
        partes.append(f"- {rotulo}: **{obtido}** ({int(mensal.loc[obtido]):,} unidades) "
                      f"-- esperado `{esperado}`: {situacao}{detalhe}\n")

    inicio, fim, esperado = PREMISSA_MENOR_MES
    conferir(f"Menor mes de {inicio[:4]}-{fim[:4]}",
             [m for m in meses if inicio <= m <= fim], esperado, "idxmin")
    inicio, fim, esperado = PREMISSA_MAIOR_MES
    conferir(f"Maior mes desde {inicio}",
             [m for m in meses if m >= inicio and (fim is None or m <= fim)],
             esperado, "idxmax")

    base, alvo, minimo = SALTO_JULHO_2023
    if base in mensal.index and alvo in mensal.index:
        salto = mensal.loc[alvo] / mensal.loc[base] - 1
        salto_fonte = None
        if publicado_mensal is not None and {base, alvo} <= set(publicado_mensal.index):
            salto_fonte = publicado_mensal.loc[alvo] / publicado_mensal.loc[base] - 1
        situacao = "OK" if salto >= minimo else "PREMISSA NAO CONFIRMADA"
        partes.append(
            f"- Salto de {base} para {alvo}: **{100 * salto:+.1f}%** no painel"
            + (f", {100 * salto_fonte:+.1f}% no total publicado" if salto_fonte is not None else "")
            + f" -- esperado ao menos +{100 * minimo:.0f}%: {situacao}\n"
        )
        if situacao != "OK":
            partes.append("  (o salto e' o fato que interessa ao estudo de choque "
                          "tributario; se ele nao aparece, a leitura do mes esta' errada)\n")

    if publicado_mensal is not None and len(publicado_mensal):
        maximo = publicado_mensal.idxmax()
        partes.append(f"- Maximo da serie inteira, no total publicado: **{maximo}** "
                      f"({int(publicado_mensal.loc[maximo]):,} unidades) -- o mercado de "
                      "2014 era muito maior que o de hoje, entao o pico absoluto fica la'\n")
        desde_2019 = publicado_mensal[publicado_mensal.index >= "2019-01"]
        if len(desde_2019):
            pico = desde_2019.idxmax()
            partes.append(f"- Maximo desde 2019, no total publicado: **{pico}** "
                          f"({int(desde_2019.loc[pico]):,} unidades)\n")

    # -------------------------------------------------- 3. cobertura (D5)
    partes.append(
        "\n## 3. Cobertura da fonte (D5)\n\n"
        "Total do painel contra o total que o proprio informe publica. A diferenca e' "
        "estrutural, nao erro de leitura: as tabelas por modelo da fonte tem numero fixo de "
        "linhas por sub-segmento e truncam a cauda. **O piso nao e' aplicado ao painel** -- "
        "filtrar destroi informacao de forma irreversivel, e a escolha e' de analise. O que "
        "esta rodada entrega e' a medida e uma recomendacao.\n\n"
    )
    if totais.empty:
        partes.append("_Totais publicados nao disponiveis: rode a etapa 02._\n")
        cobertura_por_ano = pd.DataFrame()
    else:
        cobertura = mod_cobertura.por_mes(painel, totais)
        sem_total = cobertura[cobertura["total_publicado"].isna()]
        cobertura = cobertura[cobertura["total_publicado"].notna()]
        cobertura.sort_values(["mes", "segmento"]).to_csv(config.COBERTURA, index=False)
        cobertura_por_ano = mod_cobertura.tendencia(cobertura)
        partes.append("Por ano:\n\n" + _tabela(cobertura_por_ano))
        partes.append(
            f"\nMeses-segmento sem total publicado legivel (fora dos agregados): "
            f"**{len(sem_total)}**"
            + (f" -- {', '.join(sorted(sem_total['mes'].unique()))}" if len(sem_total) else "")
            + f"\n\nTabela mes a mes em `{log.caminho_relativo(config.COBERTURA)}`.\n"
        )

        partes.append("\n### Tendencia da cobertura\n\n"
                      "Cobertura que anda ao longo da serie contamina qualquer comparacao "
                      "de taxas entre anos: o painel de 2026 nao ve a mesma parte do mercado "
                      "que o de 2014.\n\n")
        deriva = mod_cobertura.deriva(cobertura_por_ano)
        partes.append(_tabela(deriva))
        arriscados = deriva[deriva["variacao_pp"].abs() > 1.0]
        if not arriscados.empty:
            partes.append(
                "\n**Risco identificado:** "
                + "; ".join(
                    f"{linha.segmento} anda {linha.variacao_pp:+.2f} pontos percentuais entre "
                    f"{linha.primeiro_ano} e {linha.ultimo_ano}"
                    for linha in arriscados.itertuples()
                )
                + ". As taxas de entrada e saida da sec.8 tem de ser lidas com isso em "
                  "mente; a coluna do subconjunto imune ao corte existe para separar os "
                  "efeitos.\n"
            )
        else:
            partes.append("\nNenhum segmento anda mais de 1 ponto percentual. OK.\n")

        partes.append("\n### Piso recomendado (nao aplicado)\n\n"
                      "Para cada piso candidato sobre as unidades mensais do modelo: a "
                      "cobertura anual que resulta, sua amplitude entre anos, e o volume "
                      "que ficaria de fora. O recomendado e' o que deixa a fracao coberta "
                      "mais parecida entre os anos.\n\n")
        recomendacao = mod_cobertura.recomendar_piso(painel, totais)
        recomendacao.to_csv(config.DIR_SAIDAS / "piso_recomendado.csv", index=False)
        partes.append(_tabela(recomendacao))
        if not recomendacao.empty:
            escolhido = recomendacao[recomendacao["recomendado"]].iloc[0]
            partes.append(
                f"\n**Recomendacao:** piso de **{int(escolhido['piso_unidades_mes'])} unidades "
                f"por modelo e mes**, que deixa a cobertura anual entre "
                f"{escolhido['cobertura_min_pct']}% e {escolhido['cobertura_max_pct']}% "
                f"(amplitude de {escolhido['amplitude_pp']} pontos) e descartaria "
                f"{_mil(escolhido['volume_descartado'])} unidades "
                f"({escolhido['volume_descartado_pct']}% do painel). "
                "Registrado como parametro; nao gravado no dado.\n"
            )

    # -------------------------------------------- 4. corte de publicacao
    partes.append(
        "\n## 4. Onde a fonte corta a cauda\n\n"
        "A truncagem da Fenabrave **nao e' um piso de unidades**: e' numero fixo de linhas "
        "por sub-segmento. \"Suv's\" traz exatamente 40 modelos nos 152 meses; \"Furgoes\", 7; "
        "\"Sedans Grandes\", 12. Sub-segmento com menos modelos que o teto nao trunca nada. "
        "Logo o corte que vale para um modelo e' o do **bloco** em que ele seria listado, "
        "quando aquele bloco esta' no teto -- e nao o menor valor publicado no mes inteiro, "
        "que mede o tamanho do menor modelo da fonte, nao a truncagem.\n\n"
    )
    blocos = truncamento.por_bloco(bruto)
    blocos.to_csv(config.DIR_SAIDAS / "truncamento_por_bloco.csv", index=False)
    corte_anual = truncamento.resumo_anual(blocos)
    partes.append(_tabela(corte_anual))
    cortes_modelo = truncamento.por_modelo_e_mes(bruto, meses)

    # ------------------------------------------------- 5. contagem de modelos
    partes.append(
        "\n## 5. Contagem de modelos por ano\n\n"
        "A fonte nao publica contagem de modelos: a contagem abaixo e' a do painel, que por "
        "construcao e' a dos modelos listados nos informes. A coluna de referencia vem da "
        "planilha de controle da sec.7, que **nao e' fonte**.\n\n"
    )
    contagem = (
        por_modelo[por_modelo["unidades"] > 0]
        .groupby("ano")
        .apply(lambda b: pd.Series({
            "modelos": b[visoes.CHAVE_MODELO].drop_duplicates().shape[0],
            "marcas": b["marca"].nunique(),
            "unidades": int(b["unidades"].sum()),
        }), include_groups=False)
        .reset_index()
    )
    for campo, coluna in (("modelos", "ref_modelos_sec7"), ("total", "ref_total_sec7")):
        contagem[coluna] = contagem["ano"].map(
            lambda a, c=campo: REFERENCIA_SEC7.get(a, {}).get(c))
    contagem["diferenca_modelos"] = contagem["modelos"] - contagem["ref_modelos_sec7"]
    partes.append(_tabela(contagem))

    partes.append(
        "\n### Agregacao da fonte: nomes compostos\n\n"
        "`VW/FOX/CROSS FOX` e' um registro unico para o que a planilha de controle tratava "
        "como dois modelos. Contar quantos nomes trazem barra depois da marca mede quanto da "
        "diferenca de contagem e' **agregacao da fonte** em vez de truncamento -- as duas "
        "hipoteses de I1, com implicacoes opostas. Se for agregacao, nao ha' perda de "
        "cobertura: e' a unidade de observacao sendo definida pela fonte.\n\n"
    )
    compostos = bruto[bruto["nome_completo_fonte"].str.count("/") >= 2]
    tabela_compostos = (
        compostos.groupby("ano", as_index=False)
        .agg(linhas=("unidades", "size"), unidades=("unidades", "sum"),
             nomes=("nome_completo_fonte", "nunique"))
        if not compostos.empty else pd.DataFrame()
    )
    partes.append(_tabela(tabela_compostos))
    if not compostos.empty:
        lista = (
            compostos.groupby(["marca_fonte", "modelo_fonte"], as_index=False)
            .agg(unidades=("unidades", "sum"), primeiro_mes=("mes_ref", "min"),
                 ultimo_mes=("mes_ref", "max"))
            .sort_values("unidades", ascending=False)
        )
        lista.to_csv(config.DIR_SAIDAS / "nomes_compostos.csv", index=False)
        partes.append("\nOs de maior volume:\n\n" + _tabela(lista, 15))

    # ---------------------------------------------------- 6. concentracao
    partes.append(
        "\n## 6. Concentracao: marca e grupo\n\n"
        "Agrupar marcas so' pode **aumentar** o HHI -- desde que a particao seja a mesma "
        "para tudo o que se soma. Num agregado anual com mapa datado ela nao e': em 2014 a "
        "FIAT esta' no grupo `FIAT` ate' setembro e em `FCA` de outubro em diante, e o "
        "volume anual da marca se parte em dois grupos. Por isso a identidade e' exigida "
        "**por mes**, onde a particao e' fixa, e o agregado anual usa o grupo vigente num "
        "mes de referencia declarado.\n\n"
    )
    mensal_hhi = concentracao.por_mes(por_modelo)
    violacoes = mensal_hhi[mensal_hhi["diferenca"] < -0.05]
    mensal_hhi.to_csv(config.DIR_SAIDAS / "hhi_mensal.csv", index=False)
    if violacoes.empty:
        partes.append(f"**OK** -- `hhi_grupo >= hhi_marca` nos {len(mensal_hhi)} meses.\n\n")
    else:
        falhas.append(f"hhi_grupo < hhi_marca em {len(violacoes)} meses")
        partes.append("**FALHOU**\n\n" + _tabela(violacoes, 20))

    anual_hhi = concentracao.por_ano(por_modelo)
    anual_hhi["ref_hhi_marca_sec7"] = anual_hhi["ano"].map(
        lambda a: REFERENCIA_SEC7.get(a, {}).get("hhi_marca"))
    anual_hhi.to_csv(config.DIR_SAIDAS / "hhi_anual.csv", index=False)
    partes.append(_tabela(anual_hhi))
    invertidos = anual_hhi[anual_hhi["hhi_grupo_particao_fixa"] < anual_hhi["hhi_marca"]]
    if not invertidos.empty:
        falhas.append(
            f"hhi_grupo (particao fixa) < hhi_marca em {len(invertidos)} anos")
    transicao = anual_hhi[anual_hhi["marcas_que_mudam_de_grupo_no_ano"] > 0]
    if not transicao.empty:
        partes.append(
            "\nAnos com mudanca de propriedade no meio: "
            + "; ".join(
                f"{int(linha.ano)} ({linha.marcas_que_mudam_de_grupo_no_ano} marcas, "
                f"{_mil(linha.volume_dessas_marcas)} unidades)"
                for linha in transicao.itertuples()
            )
            + ". Neles `hhi_grupo_datado` fica abaixo de `hhi_marca` por construcao, e a "
              "coluna de particao fixa e' a comparavel.\n"
        )

    sem_mapa = painel[~painel["grupo_mapeado"]] if "grupo_mapeado" in painel else painel.iloc[0:0]
    partes.append(
        f"\nMarcas sem grupo vigente no mapa, tratadas como **grupo unitario com o proprio "
        f"nome**: **{sem_mapa['marca'].nunique()}** marcas, "
        f"{_mil(sem_mapa['unidades'].sum())} unidades "
        f"({100 * sem_mapa['unidades'].sum() / painel['unidades'].sum():.3f}% do painel). "
        "Nenhuma e' excluida do calculo nem somada num balde comum: as duas coisas "
        "distorceriam o indice em direcoes opostas.\n"
    )
    if not sem_mapa.empty:
        pendentes = (
            sem_mapa.groupby("marca", as_index=False)["unidades"].sum()
            .sort_values("unidades", ascending=False)
        )
        pendentes.to_csv(config.DIR_SAIDAS / "grupos_nao_mapeados.csv", index=False)
        partes.append("\n" + _tabela(pendentes, 25))

    # ---------------------------------------------------------- 7. ausencias
    partes.append("\n## 7. Ausencias\n\n")
    negativos = painel[painel["unidades"] < 0]
    partes.append(f"- Linhas com unidades negativas: **{len(negativos)}** "
                  f"({'OK' if negativos.empty else 'FALHOU'})\n")
    if not negativos.empty:
        falhas.append(f"{len(negativos)} linhas com unidades negativas")
    soma_modelo = por_modelo.groupby(visoes.CHAVE_MODELO)["unidades"].sum()
    nulos = soma_modelo[soma_modelo == 0]
    partes.append(
        f"- Modelos com serie integralmente nula: **{len(nulos)}**"
        + (": " + ", ".join(f"`{a}/{b}` ({c})" for a, b, c in nulos.index) if not nulos.empty
           else " (OK)") + "\n")
    partes.append(f"- Nomes sem marca resolvida: "
                  f"**{int((bruto['metodo_separacao'] == 'nao_resolvido').sum())}** linhas\n")
    partes.append(f"- Marcas fora de `config/marcas.csv`: "
                  f"**{bruto.loc[~bruto['marca_conhecida'], 'marca_fonte'].nunique()}**\n")

    partes.append("\n### Lacunas de mes\n\n"
                  "Mes sem informe baixado, e mes cujo informe nao rendeu nenhuma linha. "
                  "Lacuna e' lacuna: nao se preenche, nao se interpola, nao se estima "
                  "(sec.9.2). Nas series de D3 estes meses entram como ausentes, nunca "
                  "como zero. Mes recuperado pela coluna de mes anterior do informe "
                  "seguinte **nao** e' lacuna: e' segunda publicacao do mesmo numero pela "
                  "mesma fonte.\n\n")
    lacunas = pd.DataFrame(mod_meses.lacunas())
    partes.append(f"{len(lacunas)} lacunas.\n\n" + _tabela(lacunas, 40))
    esperados = periodo.intervalo(meses[0], meses[-1])
    faltantes = [m for m in esperados if m not in set(meses)]
    partes.append(f"\nMeses do intervalo sem nenhuma linha no painel: **{len(faltantes)}**"
                  + (f" ({', '.join(faltantes)})" if faltantes else "") + "\n")
    if faltantes:
        falhas.append(f"{len(faltantes)} meses do intervalo sem nenhuma linha: "
                      + ", ".join(faltantes))

    caminho_reconstruidos = config.DIR_SAIDAS / "meses_reconstruidos.csv"
    if caminho_reconstruidos.exists():
        reconstruidos = pd.read_csv(caminho_reconstruidos)
        if not reconstruidos.empty:
            partes.append("\n### Meses recuperados do informe seguinte\n\n"
                          + _tabela(reconstruidos))

    # ------------------------------------------ 8. taxas de entrada e saida
    partes.append(
        "\n## 8. Taxas de entrada e saida por ano (D3)\n\n"
        "Tres limiares lado a lado, como manda a sec.6. Modelos censurados -- vivos no "
        "primeiro mes da amostra, ou ainda vivos no ultimo -- ficam fora da contagem de "
        "entrada e de saida respectivamente.\n\n"
        "**Assimetria declarada (I2):** a entrada e' o primeiro mes com unidades positivas "
        "e **nao depende do limiar**; so' a saida usa D3, que foi o que a ESPEC "
        "especificou. Por isso as tres colunas de entrada sao identicas -- e' desenho, nao "
        "defeito. A assimetria entra direto em qualquer decomposicao de margens e esta' "
        "registrada no dicionario de dados.\n\n"
    )
    ativos = _ativos_por_ano(por_modelo)
    largo = ciclo_vida.grade(por_modelo, visoes.CHAVE_MODELO, meses, mod_meses.uteis())
    tabelas, ciclos_por_limiar = [], {}
    for limiar in config.LIMIARES_SAIDA:
        ciclos = _ciclos_da_grade(largo, meses, limiar)
        ciclos_por_limiar[limiar] = ciclos
        tabelas.append(_taxas(ciclos, ativos, limiar))
    juntas = pd.concat(
        [tabelas[0][["ativos"]]] + [t.drop(columns=["ativos"]) for t in tabelas], axis=1
    ).reset_index()
    juntas.to_csv(config.DIR_SAIDAS / "taxas_entrada_saida.csv", index=False)
    partes.append(_tabela(juntas))

    colunas_saida = [f"taxa_saida_{l:.0%}" for l in config.LIMIARES_SAIDA]
    instaveis = _mudancas_de_ordenacao(juntas, colunas_saida)
    partes.append("\n### Estabilidade da ordenacao entre limiares\n\n")
    if instaveis.empty:
        partes.append("A ordenacao dos anos por taxa de saida e' **identica** nos tres "
                      "limiares.\n")
    else:
        partes.append(
            f"**Achado metodologico:** {len(instaveis)} de {len(juntas)} anos mudam de "
            "posicao no ranking de taxa de saida conforme o limiar. A escolha do limiar nao "
            "e' inocua para esses anos.\n\n" + _tabela(instaveis)
        )

    # Q1: a outra leitura de "pico movel", lado a lado.
    outro_modo = "max_movel" if config.PICO_MOVEL_MODO == "media_movel" else "media_movel"
    ciclos_outro = _ciclos_da_grade(largo, meses, config.LIMIAR_SAIDA, modo=outro_modo)
    taxas_outro = _taxas(ciclos_outro, ativos, config.LIMIAR_SAIDA, sufixo=f"_{outro_modo}")
    comparacao_modo = pd.concat(
        [tabelas[1].drop(columns=["ativos"]), taxas_outro.drop(columns=["ativos"])], axis=1
    ).reset_index()
    partes.append(
        f"\n### As duas leituras de \"pico movel de 12 meses\" (Q1)\n\n"
        f"Em uso: `{config.PICO_MOVEL_MODO}`. Ao lado, `{outro_modo}`, no limiar de "
        f"{config.LIMIAR_SAIDA:.0%}. Se a ordenacao dos anos nao mudar, a escolha e' inocua "
        "e a questao pode ser encerrada.\n\n"
    )
    partes.append(_tabela(comparacao_modo))
    colunas_modo = [f"taxa_saida_{config.LIMIAR_SAIDA:.0%}",
                    f"taxa_saida_{config.LIMIAR_SAIDA:.0%}_{outro_modo}"]
    muda_modo = _mudancas_de_ordenacao(comparacao_modo, colunas_modo)
    partes.append(
        "\nA ordenacao dos anos e' **identica** nas duas leituras: a escolha entre elas nao "
        "muda nenhuma conclusao sobre quais anos tiveram mais saida, e Q1 pode ser "
        "encerrada.\n" if muda_modo.empty else
        f"\n**{len(muda_modo)} de {len(comparacao_modo)} anos mudam de posicao** entre as "
        "duas leituras. A escolha entre `media_movel` e `max_movel` **nao e' inocua**, e Q1 "
        "continua aberta: qualquer resultado sobre em que anos houve mais saida depende "
        "dela e precisa declarar qual leitura usou.\n\n" + _tabela(muda_modo)
    )

    # I3: o corte de publicacao pode estar fabricando a alta recente.
    partes.append(
        "\n### O corte de publicacao esta' fabricando a alta recente? (I3)\n\n"
        "A taxa de saida sobe nos ultimos anos, e o corte de publicacao poderia explica-la: "
        "se o limiar de D3 de um modelo ficar **abaixo** do corte do bloco em que ele e' "
        "listado, ele some da fonte antes de cruzar o proprio limiar, e a data de saida "
        "passa a ser pratica editorial. Medido o corte corretamente (sec.4), ele nao sobe "
        "em automoveis mas **sobe muito em comerciais leves** -- a mediana vai de 25 "
        "unidades em 2014 para 172 em 2026. O teste isola os modelos em que o corte nao "
        "morde: aqueles cujo limiar de D3 supera, em **todo mes** da propria janela, o corte "
        "do bloco em que estariam.\n\n"
    )
    ciclos_5 = ciclos_por_limiar[config.LIMIAR_SAIDA]
    com_imunidade = mod_cobertura.imunes_ao_corte(
        ciclos_5, cortes_modelo, config.LIMIAR_SAIDA)
    if "imune_ao_corte" in com_imunidade.columns and com_imunidade["imune_ao_corte"].any():
        imunes = com_imunidade[com_imunidade["imune_ao_corte"]]
        # Denominador proprio: quantos modelos imunes estavam ativos em cada ano.
        # Com o denominador cheio o nivel da taxa nao significaria nada.
        chaves_imunes = set(map(tuple, imunes[visoes.CHAVE_MODELO].to_numpy()))
        ativos_imunes = _ativos_por_ano(
            por_modelo[
                por_modelo.set_index(visoes.CHAVE_MODELO).index.isin(chaves_imunes)
            ]
        )
        taxas_imunes = _taxas(imunes, ativos_imunes, config.LIMIAR_SAIDA, sufixo="_imunes")
        taxas_imunes = taxas_imunes.rename(columns={"ativos": "ativos_imunes"})
        lado_a_lado = pd.concat([tabelas[1], taxas_imunes], axis=1).reset_index()
        partes.append(
            f"{len(imunes)} de {len(ciclos_5)} modelos sao imunes ao corte. Cada taxa usa o "
            "seu proprio denominador -- modelos ativos no ano, no conjunto respectivo -- "
            "para que o nivel, e nao so' a forma, seja comparavel.\n\n"
            + _tabela(lado_a_lado)
        )
        # A comparacao so' vale entre anos completos: o ultimo ano da amostra
        # termina no meio e infla a taxa de saida por conta propria.
        ultimo_completo = int(meses[-1][:4]) - 1
        recentes = [a for a in lado_a_lado["ano"] if 2022 <= a <= ultimo_completo]
        if len(recentes) >= 2:
            indexado = lado_a_lado.set_index("ano")
            cheia = indexado[f"taxa_saida_{config.LIMIAR_SAIDA:.0%}"]
            imune = indexado[f"taxa_saida_{config.LIMIAR_SAIDA:.0%}_imunes"]
            saidas_imunes = indexado[f"saidas_{config.LIMIAR_SAIDA:.0%}_imunes"]
            inicio_, fim_ = recentes[0], recentes[-1]
            variacao_cheia = cheia.loc[fim_] - cheia.loc[inicio_]
            variacao_imune = imune.loc[fim_] - imune.loc[inicio_]
            proporcao = (variacao_imune / variacao_cheia) if variacao_cheia else float("nan")
            if variacao_cheia <= 0:
                veredito = ("a serie cheia nao sobe nesta janela, entao nao ha' o que "
                            "atribuir ao corte")
                ressalva = "fica sem objeto enquanto a serie cheia nao subir"
            elif variacao_imune <= 0:
                veredito = ("a subida **desaparece** no subconjunto imune, o que aponta "
                            "para artefato do corte de publicacao")
                ressalva = ("aponta na direcao do artefato sem demonstra-lo, porque com "
                            "tao poucas saidas o desaparecimento tambem cabe no acaso")
            elif proporcao >= 0.5:
                veredito = ("a subida **persiste** no subconjunto imune, entao nao e' "
                            "artefato do corte")
                ressalva = ("descarta a hipotese forte -- a de que a alta seja "
                            "**inteiramente** artefato do corte --, nao a fraca")
            else:
                veredito = ("a subida **atenua** no subconjunto imune -- parte do movimento "
                            "pode ser do corte, parte nao")
                ressalva = ("a atenuacao e' compativel tanto com artefato parcial quanto "
                            "com ruido de amostra pequena")
            mediana_saidas = float(saidas_imunes.loc[recentes].median())
            partes.append(
                f"\nEntre {inicio_} e {fim_} (o ultimo ano completo), a taxa de saida vai de "
                f"{cheia.loc[inicio_]:.3f} a {cheia.loc[fim_]:.3f} na serie cheia "
                f"({variacao_cheia:+.3f}) e de {imune.loc[inicio_]:.3f} a "
                f"{imune.loc[fim_]:.3f} no subconjunto imune ({variacao_imune:+.3f}): "
                f"{veredito}.\n\n"
                f"**Ressalva de tamanho:** o subconjunto imune tem so' {len(imunes)} modelos "
                f"e mediana de {mediana_saidas:.0f} saidas por ano na janela recente. Com "
                "contagens assim, uma diferenca de duas ou tres saidas move a taxa em varios "
                f"pontos, e o teste **nao tem poder** para concluir com seguranca: {ressalva}.\n"
            )
    else:
        partes.append("_Nenhum modelo imune ao corte no periodo._\n")

    sem_ano_parcial = juntas[juntas["ano"] < int(meses[-1][:4])] if meses else juntas
    partes.append(
        f"\n### Sem o ano parcial\n\n"
        f"{meses[-1][:4]} termina em {meses[-1]}: contar saidas num ano incompleto infla a "
        "taxa por conta propria. A mesma tabela sem ele:\n\n" + _tabela(sem_ano_parcial)
    )

    # Q5: zeros frageis.
    partes.append(
        "\n### Zeros frageis (Q5)\n\n"
        "Mes em que o modelo nao aparece e o corte de publicacao esta' **acima** do limiar "
        "de D3 do proprio modelo: ali o zero pode estar escondendo valor relevante, e a data "
        "de saida fica a merce da pratica editorial.\n\n"
    )
    fragil = mod_cobertura.zeros_fragis(largo, ciclos_5, cortes_modelo, config.LIMIAR_SAIDA)
    if fragil.empty:
        partes.append("Nenhum zero fragil no periodo.\n")
    else:
        fragil.to_csv(config.DIR_SAIDAS / "zeros_frageis.csv", index=False)
        por_ano_fragil = (
            fragil.assign(ano=fragil["mes_ref"].str.slice(0, 4).astype(int))
            .groupby("ano", as_index=False)
            .agg(zeros_frageis=("mes_ref", "size"),
                 modelos=("modelo", "nunique"))
        )
        partes.append(
            f"**{len(fragil)}** pares (modelo x mes) frageis, em "
            f"{fragil.groupby(visoes.CHAVE_MODELO).ngroups} modelos. Lista completa em "
            "`saidas/zeros_frageis.csv`.\n\n" + _tabela(por_ano_fragil)
        )

    # -------------------------------------------- 9. coerencia entre meses
    partes.append(
        "\n## 9. Coerencia entre meses\n\n"
        "Cada linha da fonte traz o mes anterior, o mes de referencia e o acumulado do ano. "
        "Duas identidades tem de valer sem depender de interpretacao nossa: a coluna de mes "
        "anterior de M repete o mes de M-1, e a diferenca de acumulados da' o mes.\n\n"
    )
    extracao = _extracao_completa()
    coluna_anterior, acumulados, comparados = _coerencia_entre_meses(extracao, mod_meses.uteis())
    if coluna_anterior.empty and acumulados.empty:
        partes.append("_Sem dados de extracao para conferir._\n")
    else:
        coluna_anterior.to_csv(config.DIR_SAIDAS / "coerencia_mes_anterior.csv", index=False)
        acumulados.to_csv(config.DIR_SAIDAS / "coerencia_acumulado.csv", index=False)
        base_a = comparados.get("mes_anterior", 0) or 1
        base_b = comparados.get("acumulado", 0) or 1
        partes.append(
            f"- Coluna de mes anterior divergente do mes observado: **{len(coluna_anterior)}** "
            f"de {_mil(comparados.get('mes_anterior', 0))} pares comparados "
            f"({100 * len(coluna_anterior) / base_a:.2f}%)\n"
            f"- Acumulado divergente da soma do mes com o acumulado anterior: "
            f"**{len(acumulados)}** de {_mil(comparados.get('acumulado', 0))} "
            f"({100 * len(acumulados) / base_b:.2f}%)\n\n"
            "A fonte revisa meses ja publicados, e e' isso que a maior parte destas linhas "
            "mostra. Casos em que duas linhas do mesmo mes se compensam -- VW/GOL -676 e "
            "VW/VOYAGE +676 em Ago/2016 -- sao remanejamento de unidades entre modelos, "
            "candidatos naturais a `reclassificacao`. Listas completas em "
            "`saidas/coerencia_mes_anterior.csv` e `saidas/coerencia_acumulado.csv`.\n\n"
        )
        partes.append("Maiores divergencias na coluna de mes anterior:\n\n")
        partes.append(_tabela(coluna_anterior, 15))

    # ------------------------------------------ 10. divergencias da fonte
    partes.append(
        "\n## 10. Divergencias internas da fonte\n\n"
        "Modelos em que o ranking mensal e a tabela de sub-segmento do **mesmo** informe "
        "trazem numeros diferentes. Sao inconsistencias da fonte, reportadas e mantidas "
        "(sec.9.4); o painel usa o valor da tabela de sub-segmento.\n\n"
    )
    caminho_div = config.DIR_SAIDAS / "divergencias_fonte.csv"
    if caminho_div.exists():
        divergencias = pd.read_csv(caminho_div)
        partes.append(f"{len(divergencias)} divergencias.\n\n" + _tabela(divergencias, 20))
    else:
        partes.append("_Nao disponivel._\n")

    # ------------------------------------------------------------ 11. fecho
    partes.append("\n## 11. Situacao\n\n")
    if falhas:
        partes.append("**Validacao FALHOU:**\n\n" + "".join(f"- {f}\n" for f in falhas))
    else:
        partes.append("Todas as verificacoes obrigatorias passaram.\n")

    config.VALIDACAO.write_text("".join(partes), encoding="utf-8")
    logger.info("gravado %s", log.caminho_relativo(config.VALIDACAO))
    log.contagem(logger, linhas_painel=len(painel), linhas_por_modelo=len(por_modelo),
                 meses=len(meses), falhas=len(falhas))
    for falha in falhas:
        logger.error("validacao: %s", falha)
    return 1 if falhas else 0


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    return executar()


if __name__ == "__main__":
    raise SystemExit(main())
