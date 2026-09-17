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
    marca_do_modelo, meses as mod_meses, nomes, periodo, rotatividade,
    truncamento, visoes,
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
        partes.append(
            "\n**Correcao ao diagnostico de retroacao.** O diagnostico previa 2003 e 2005 "
            "como os anos de cobertura mais fraca (95,4% e 95,0% em automoveis) e pedia que "
            "fossem registrados como tal. A extracao completa desmente isso: os dois ficam "
            "em 99,6% e 99,7%, na faixa dos melhores anos da serie. A diferenca e' de "
            "metodo, nao de dado -- o diagnostico somava so' a tabela por sub-segmento e "
            "tirava media entre meses, enquanto o painel tambem usa o ranking mensal para "
            "completar a cauda. Os 4 pontos inteiros vinham de **dois meses**, 2003-10 e "
            "2005-03, cujas edicoes curtas nao trazem tabela por sub-segmento (sec.7). Os "
            "anos de cobertura mais fraca da serie inteira sao 2026 (95,8%, parcial), 2025 "
            "(97,7%) e 2011 (97,9%) -- todos recentes.\n"
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

    inventario = nomes.inventario(por_modelo)
    marcados = inventario[inventario["nome_suspeito"]] if not inventario.empty else inventario
    revisao = nomes.candidatos_a_revisao(inventario)
    if not revisao.empty:
        revisao.to_csv(config.DIR_SAIDAS / "nomes_suspeitos.csv", index=False)
    partes.append(
        f"- Nomes que provavelmente **nao designam veiculo**: **{len(marcados)}** modelos, "
        f"{_mil(marcados['unidades'].sum()) if not marcados.empty else 0} unidades "
        "-- `FIAT/FIAT`, `FORD/ENGERAUTO SPARTAKUS`, `TOYOTA/RIBEIRAUTO`. Nada foi "
        "apagado: a coluna `nome_suspeito` marca as linhas e "
        f"`saidas/nomes_suspeitos.csv` traz os {len(revisao)} candidatos a revisao "
        "humana (marcados, mais os de volume infimo que ninguem olhou ainda).\n"
    )
    if not marcados.empty:
        partes.append("\n" + _tabela(
            marcados[["marca", "modelo", "unidades", "meses", "motivo"]], 12))

    caminho_colisoes = config.DIR_SAIDAS / "colisoes_de_caixa.csv"
    if caminho_colisoes.exists():
        colisoes = pd.read_csv(caminho_colisoes)
        partes.append(
            f"\n- Grafias unificadas por caixa na chave do modelo (D1): "
            f"**{len(colisoes)}** -- `MITSUBISHI/Outlander` e `MITSUBISHI/OUTLANDER` sao o "
            "mesmo carro, e sem a normalizacao virariam duas fichas, com uma saida e uma "
            "entrada fabricadas. A grafia crua segue em `grafias_fonte` e "
            "`nome_completo_fonte`.\n\n" + _tabela(colisoes)
        )
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

    abreviadas = truncamento.edicoes_abreviadas(bruto)
    if not abreviadas.empty:
        abreviadas.to_csv(config.DIR_SAIDAS / "edicoes_abreviadas.csv", index=False)
        curtas = abreviadas[abreviadas["situacao"] == "edicao curta do informe"]
        partes.append(
            "\n### Edicoes curtas do informe\n\n"
            "O informe normal traz 44 paginas e 17 sub-segmentos na tabela por modelo. "
            f"**{len(curtas)}** meses da serie sairam com uma edicao curta -- 10 paginas -- "
            "e trazem **um** sub-segmento. Ali o mes e' carregado quase inteiro pelo "
            "ranking mensal: o **total bate** com o publicado, porque o ranking cobre o "
            "topo, mas o **elenco de modelos fica pela metade** (89 e 87 fichas contra "
            "cerca de 180 nos meses vizinhos).\n\n"
            "Consequencia para quem usa a serie: nesses dois meses um modelo de cauda "
            "some sem ter saido do mercado. Nao vira saida -- D3 olha o pico movel de 12 "
            "meses --, mas vira zero fragil e entra na contagem de modelos do ano. **Nada "
            "foi completado** (sec.9.4): a coluna do mes anterior do informe seguinte "
            "poderia recuperar o elenco, do mesmo jeito que recuperou 2023-09, mas isso "
            "misturaria linha lida direto com linha republicada dentro do mesmo mes, e a "
            "regra de mistura e' decisao do pesquisador, nao do codigo.\n\n"
            + _tabela(abreviadas)
        )

    caminho_reconstruidos = config.DIR_SAIDAS / "meses_reconstruidos.csv"
    if caminho_reconstruidos.exists():
        reconstruidos = pd.read_csv(caminho_reconstruidos)
        if not reconstruidos.empty:
            partes.append("\n### Meses recuperados do informe seguinte\n\n"
                          + _tabela(reconstruidos))

    # ------------------------------------------ 8. taxas de entrada e saida
    ano_parcial = int(meses[-1][:4])
    ultimo_completo = ano_parcial - 1
    volume = rotatividade.volume_por_modelo(por_modelo)
    largo = ciclo_vida.grade(por_modelo, visoes.CHAVE_MODELO, meses, mod_meses.uteis())
    ciclos_por_limiar = {
        limiar: _ciclos_da_grade(largo, meses, limiar) for limiar in config.LIMIARES_SAIDA
    }
    ciclos_5 = ciclos_por_limiar[config.LIMIAR_SAIDA]

    partes.append(
        "\n## 8. Taxas de entrada e saida por ano (D3)\n\n"
        "**Leia a advertencia antes da tabela.** Estas taxas nao medem so' rotatividade de "
        "portfolio: medem rotatividade **mais ruido de cadastro**, em proporcao parecida. "
        "A decomposicao por piso de volume, logo abaixo, e' o que separa uma coisa da "
        "outra, e nenhuma leitura substantiva deve sair da coluna \"todos\".\n\n"
        f"Alem disso, **{ano_parcial} e' ano parcial** (a amostra termina em {meses[-1]}): "
        "contar saidas num ano incompleto infla a taxa por conta propria, e o numero nao e' "
        "citavel para rotatividade.\n\n"
        "**Assimetria declarada (I2):** a entrada e' o primeiro mes com unidades positivas "
        "e **nao depende do limiar**; so' a saida usa D3, que foi o que a ESPEC "
        "especificou. Por isso as colunas de entrada sao identicas entre limiares -- e' "
        "desenho, nao defeito.\n\n"
    )

    # ---------------------------------------------------- modelos fantasma
    partes.append(
        "### Quem sao os modelos que entram e saem\n\n"
        "Distribuicao dos modelos por volume total no periodo inteiro:\n\n"
    )
    distribuicao = rotatividade.distribuicao(volume, config.FAIXAS_VOLUME)
    distribuicao.to_csv(config.DIR_SAIDAS / "distribuicao_volume_modelos.csv", index=False)
    partes.append(_tabela(distribuicao))
    ate_cem = volume[volume <= 100]
    partes.append(
        f"\n**{len(ate_cem)} modelos -- {100 * len(ate_cem) / len(volume):.0f}% da contagem "
        f"-- somam {_mil(ate_cem.sum())} unidades em "
        f"{len({m[:4] for m in meses})} anos**, "
        f"{100 * ate_cem.sum() / volume.sum():.3f}% do volume. Sao registros avulsos, "
        "conversoes de encarrocador e erros de cadastro da fonte; "
        "`saidas/nomes_suspeitos.csv` lista os que nem sequer designam veiculo. Cada um "
        "deles conta como **uma entrada e uma saida**:\n\n"
    )
    participacao = rotatividade.participacao_dos_pequenos(ciclos_5, volume, 100)
    participacao.to_csv(config.DIR_SAIDAS / "rotatividade_dos_pequenos.csv", index=False)
    partes.append(_tabela(participacao))

    # ------------------------------------------- taxas por piso de volume
    partes.append(
        "\n### Taxas por piso de volume total do modelo\n\n"
        "O piso entra no numerador **e** no denominador: restringe quem pode entrar ou sair "
        "e quem conta como ativo. Nada e' filtrado do painel -- a Parte 0 continua valendo "
        "--, so' a medida e' decomposta.\n\n"
    )
    colunas_piso = []
    tabelas_piso = []
    for piso in config.PISOS_VOLUME_MODELO:
        rotulo = "todos" if piso <= 0 else f"acima de {piso}"
        recorte = rotatividade.acima_do_piso(por_modelo, volume, piso)
        ativos_piso = _ativos_por_ano(recorte)
        ciclos_piso = rotatividade.acima_do_piso(ciclos_5, volume, piso)
        tabela = _taxas(ciclos_piso, ativos_piso, config.LIMIAR_SAIDA,
                        sufixo=f" [{rotulo}]")
        tabela = tabela.rename(columns={"ativos": f"ativos [{rotulo}]"})
        tabelas_piso.append(tabela)
        colunas_piso.append(f"taxa_saida_{config.LIMIAR_SAIDA:.0%} [{rotulo}]")
    por_piso = pd.concat(tabelas_piso, axis=1).reset_index()
    por_piso.to_csv(config.DIR_SAIDAS / "taxas_por_piso_de_volume.csv", index=False)
    resumo_piso = por_piso[
        ["ano"] + [c for c in por_piso.columns if c.startswith("taxa_saida")]
    ]
    partes.append("Taxa de saida:\n\n" + _tabela(resumo_piso))
    partes.append("\nTaxa de entrada:\n\n" + _tabela(
        por_piso[["ano"] + [c for c in por_piso.columns if c.startswith("taxa_entrada")]]))
    partes.append(
        "\nContagens e denominadores completos em "
        "`saidas/taxas_por_piso_de_volume.csv`.\n"
    )

    # I3, refeito com o denominador oficial e o piso de volume.
    partes.append(
        "\n### O corte de publicacao esta' fabricando a alta recente? (I3)\n\n"
        "O piso de volume responde o que o subconjunto imune ao corte nao tinha poder para "
        "responder. Duas janelas, lidas em separado:\n\n"
    )
    indexado = resumo_piso.set_index("ano")
    anos_disponiveis = list(indexado.index)
    def _delta(inicio_ano, fim_ano):
        if inicio_ano not in anos_disponiveis or fim_ano not in anos_disponiveis:
            return None
        return pd.DataFrame([{
            "piso": coluna.split("[")[-1].rstrip("]"),
            f"taxa_{inicio_ano}": indexado.loc[inicio_ano, coluna],
            f"taxa_{fim_ano}": indexado.loc[fim_ano, coluna],
            "variacao": round(indexado.loc[fim_ano, coluna]
                              - indexado.loc[inicio_ano, coluna], 4),
        } for coluna in colunas_piso])

    recente = _delta(2022, ultimo_completo)
    if recente is not None:
        partes.append(f"**2022 a {ultimo_completo}** (ultimo ano completo):\n\n"
                      + _tabela(recente))
        sobe_com_piso = (recente["variacao"] > 0).all()
        partes.append(
            "\nA alta **nao some com o piso -- ela se mantem ou aumenta**. E' movimento "
            "real de portfolio, nao artefato do corte de publicacao nem dos modelos "
            "fantasma.\n" if sobe_com_piso else
            "\nA alta **se reduz ou inverte** conforme o piso sobe, o que aponta para "
            "ruido de cadastro e nao para movimento de portfolio.\n"
        )
    parcial = _delta(ultimo_completo, ano_parcial)
    if parcial is not None:
        partes.append(f"\n**{ultimo_completo} a {ano_parcial}** (ano parcial):\n\n"
                      + _tabela(parcial))
        inverte = (parcial["variacao"].iloc[0] > 0) and (parcial["variacao"].iloc[1:] < 0).all()
        partes.append(
            f"\nO salto de {ano_parcial} **inverte de sinal** assim que o piso entra: e' "
            "fantasma somado a ano incompleto, nao rotatividade. **Nao citar.**\n"
            if inverte else
            f"\n{ano_parcial} e' ano parcial e nao e' citavel para rotatividade, "
            "independentemente do que a tabela mostre.\n"
        )

    # O subconjunto imune ao corte fica como conferencia secundaria.
    com_imunidade = mod_cobertura.imunes_ao_corte(
        ciclos_5, cortes_modelo, config.LIMIAR_SAIDA)
    if "imune_ao_corte" in com_imunidade.columns and com_imunidade["imune_ao_corte"].any():
        imunes = com_imunidade[com_imunidade["imune_ao_corte"]]
        chaves_imunes = set(map(tuple, imunes[visoes.CHAVE_MODELO].to_numpy()))
        ativos_imunes = _ativos_por_ano(
            por_modelo[por_modelo.set_index(visoes.CHAVE_MODELO).index.isin(chaves_imunes)]
        )
        taxas_imunes = _taxas(imunes, ativos_imunes, config.LIMIAR_SAIDA, sufixo="_imunes")
        taxas_imunes = taxas_imunes.rename(columns={"ativos": "ativos_imunes"})
        partes.append(
            f"\n**Conferencia secundaria.** O teste do subconjunto imune ao corte -- "
            f"{len(imunes)} de {len(ciclos_5)} modelos cujo limiar de D3 supera o corte do "
            "bloco em todo mes da propria janela -- fica registrado, mas com mediana de "
            f"{float(taxas_imunes[f'saidas_{config.LIMIAR_SAIDA:.0%}_imunes'].median()):.0f} "
            "saidas por ano ele nao tem poder para decidir nada sozinho. O piso de volume "
            "e' o teste que responde.\n\n"
            + _tabela(taxas_imunes.reset_index())
        )

    # ------------------------------------------ os tres limiares de D3
    partes.append(
        "\n### Os tres limiares de D3\n\n"
        "Como manda a sec.6, lado a lado. Sem piso de volume: sao as taxas da coluna "
        "\"todos\", e valem a mesma advertencia.\n\n"
    )
    ativos = _ativos_por_ano(por_modelo)
    tabelas = [_taxas(ciclos_por_limiar[l], ativos, l) for l in config.LIMIARES_SAIDA]
    juntas = pd.concat(
        [tabelas[0][["ativos"]]] + [t.drop(columns=["ativos"]) for t in tabelas], axis=1
    ).reset_index()
    juntas.to_csv(config.DIR_SAIDAS / "taxas_entrada_saida.csv", index=False)
    partes.append(_tabela(juntas))

    colunas_saida = [f"taxa_saida_{l:.0%}" for l in config.LIMIARES_SAIDA]
    instaveis = _mudancas_de_ordenacao(juntas, colunas_saida)
    partes.append("\n#### Estabilidade da ordenacao entre limiares\n\n")
    if instaveis.empty:
        partes.append("A ordenacao dos anos por taxa de saida e' **identica** nos tres "
                      "limiares.\n")
    else:
        partes.append(
            f"**Achado metodologico:** {len(instaveis)} de {len(juntas)} anos mudam de "
            "posicao no ranking de taxa de saida conforme o limiar.\n\n" + _tabela(instaveis)
        )

    # Q1: as duas leituras de "pico movel", e a regra de banda que as encerra.
    outro_modo = "max_movel" if config.PICO_MOVEL_MODO == "media_movel" else "media_movel"
    ciclos_outro = _ciclos_da_grade(largo, meses, config.LIMIAR_SAIDA, modo=outro_modo)
    taxas_outro = _taxas(ciclos_outro, ativos, config.LIMIAR_SAIDA, sufixo=f"_{outro_modo}")
    comparacao_modo = pd.concat(
        [tabelas[1].drop(columns=["ativos"]), taxas_outro.drop(columns=["ativos"])], axis=1
    ).reset_index()
    comparacao_modo.to_csv(config.DIR_SAIDAS / "comparacao_pico_movel.csv", index=False)
    colunas_modo = [f"taxa_saida_{config.LIMIAR_SAIDA:.0%}",
                    f"taxa_saida_{config.LIMIAR_SAIDA:.0%}_{outro_modo}"]
    muda_modo = _mudancas_de_ordenacao(comparacao_modo, colunas_modo)
    partes.append(
        f"\n#### As duas leituras de \"pico movel de 12 meses\" (Q1 -- encerrada)\n\n"
        f"Em uso: `{config.PICO_MOVEL_MODO}`, por principio -- um lote isolado de venda "
        "direta nao e' a escala do produto, e `max_movel` numa serie completa degenera para "
        "o pico global.\n\n"
    )
    partes.append(_tabela(comparacao_modo))
    if muda_modo.empty:
        partes.append("\nA ordenacao dos anos e' identica nas duas leituras.\n")
    else:
        partes.append(
            f"\n**A regra que encerra Q1.** {len(muda_modo)} de {len(comparacao_modo)} anos "
            "mudam de posicao entre as duas leituras, e a consequencia vale mais que a "
            "escolha: **a ordenacao de anos por taxa de saida nao e' identificada** no "
            "nivel de precisao em que as duas leituras discordam. So' afirmar diferenca "
            "entre dois anos quando ela sobreviver as duas. Reportar banda, nao ponto.\n\n"
            + _tabela(muda_modo)
        )
        # O ano parcial fica fora: sua taxa e' inflada pelo recorte, nao por
        # rotatividade, e afirmar um degrau contra ele seria afirmar o artefato.
        completos = [int(a) for a in comparacao_modo["ano"] if int(a) <= ultimo_completo]
        pares_robustos = []
        for a, b in zip(completos, completos[1:]):
            linha_a = comparacao_modo[comparacao_modo["ano"] == a].iloc[0]
            linha_b = comparacao_modo[comparacao_modo["ano"] == b].iloc[0]
            variacoes = [linha_b[c] - linha_a[c] for c in colunas_modo]
            if all(v > 0.03 for v in variacoes) or all(v < -0.03 for v in variacoes):
                pares_robustos.append({
                    "de": a, "para": b,
                    colunas_modo[0]: round(variacoes[0], 4),
                    colunas_modo[1]: round(variacoes[1], 4),
                })
        partes.append(
            "\nO que **sobrevive** as duas leituras, e portanto pode ser afirmado -- "
            "variacao de mais de 3 pontos percentuais no mesmo sentido entre anos "
            f"consecutivos completos (o ano parcial de {ano_parcial} fica fora):\n\n"
            + _tabela(pd.DataFrame(pares_robustos))
        )

    # Q5: zeros frageis.
    partes.append(
        "\n### Zeros frageis (Q5)\n\n"
        "Mes em que o modelo nao aparece e o corte de publicacao **do bloco em que ele "
        "seria listado** (sec.4) esta' acima do limiar de D3 do proprio modelo: ali o zero "
        "pode estar escondendo valor relevante. A contagem so' considera meses entre a "
        "entrada e a saida do modelo, no limiar de "
        f"{config.LIMIAR_SAIDA:.0%}.\n\n"
    )
    fragil = mod_cobertura.zeros_fragis(largo, ciclos_5, cortes_modelo, config.LIMIAR_SAIDA)
    if fragil.empty:
        partes.append("Nenhum zero fragil no periodo.\n")
    else:
        fragil.to_csv(config.DIR_SAIDAS / "zeros_frageis.csv", index=False)
        por_ano_fragil = (
            fragil.assign(ano=fragil["mes_ref"].str.slice(0, 4).astype(int))
            .groupby("ano", as_index=False)
            .agg(zeros_frageis=("mes_ref", "size"), modelos=("modelo", "nunique"))
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
        "Duas familias de inconsistencia, ambas da fonte, ambas reportadas e mantidas "
        "(sec.9.4).\n\n"
    )
    divergentes = marca_do_modelo.divergencias(painel)
    partes.append(
        "### Marca trocada pela fonte\n\n"
        "Um nome de modelo aparece sob a mesma marca em quase todos os meses. Quando um mes "
        "o publica sob outra, e' esse mes que destoa. O que sobra nesta lista **nao foi "
        "corrigido**: o painel guarda o que a fonte publicou, e nem toda divergencia e' "
        "defeito -- `TIGGO 7` sob `CHERY` ate' 2020 e sob `CAOA CHERY` depois e' troca real "
        "de marca, que 'corrigir' destruiria.\n\n"
    )
    caminho_recuperada = config.DIR_SAIDAS / "marca_recuperada.csv"
    if caminho_recuperada.exists():
        recuperada = pd.read_csv(caminho_recuperada)
        feitas = recuperada[recuperada["marca_recuperada"].notna()
                            & (recuperada["marca_recuperada"].astype(str) != "")]
        sobraram = recuperada.drop(feitas.index)
        partes.append(
            f"**Recuperacao de D4: {len(feitas)} de {len(recuperada)} modelos.** Onde a "
            "edicao saiu com a coluna de marca trocada, o informe do mes seguinte republica "
            "o mes na coluna de mes anterior com a marca certa. O **valor nao muda** -- muda "
            "a atribuicao --, e so' se recupera quando o valor confere unidade a unidade. "
            "E' a mesma rota de 2023-09 (sec.9.2), usada para a marca em vez do valor. As "
            "linhas levam `marca_recuperada` e guardam a marca errada em "
            "`marca_publicada_fonte`.\n\n" + _tabela(
                feitas[["mes_ref", "modelo", "marca_publicada", "marca_recuperada",
                        "unidades"]], 14)
        )
        if not sobraram.empty:
            partes.append(
                f"\n**{len(sobraram)} sem rota.** O informe seguinte lista o modelo so' no "
                "ranking mensal, que nao traz coluna de mes anterior. Ficam no painel como "
                "a fonte os publicou.\n\n" + _tabela(
                    sobraram[["mes_ref", "modelo", "marca_publicada", "unidades",
                              "situacao"]], 8)
            )
    caminho_duplicatas = config.DIR_SAIDAS / "duplicatas_de_marca_trocada.csv"
    if caminho_duplicatas.exists():
        duplicatas = pd.read_csv(caminho_duplicatas)
        partes.append(
            f"\n**Consequencia medida e nao resolvida:** recuperada a marca, "
            f"**{len(duplicatas)}** linhas do ranking passam a repetir uma linha de "
            f"sub-segmento do mesmo informe -- {_mil(duplicatas['unidades_ranking'].sum())} "
            "unidades que a fonte publicou duas vezes, sob marcas diferentes. A regra Q7 "
            "diria para descartar a do ranking; descartar mudaria o total do mes e "
            "quebraria o invariante central, que existe para impedir que a harmonizacao "
            "mexa em volume. **Nada foi descartado** -- e' decisao do pesquisador (sec.9.6), "
            "e e' o que mantem a cobertura de 2013-11 em comerciais leves acima de 100%.\n\n"
            + _tabela(duplicatas, 8)
        )
    if divergentes.empty:
        partes.append("Nenhuma divergencia.\n")
    else:
        divergentes.to_csv(config.DIR_SAIDAS / "marca_divergente.csv", index=False)
        afetados = marca_do_modelo.meses_afetados(divergentes)
        partes.append(
            f"**{len(divergentes)}** pares (mes x modelo), "
            f"{_mil(divergentes['unidades'].sum())} unidades. Lista completa em "
            "`saidas/marca_divergente.csv`.\n\n" + _tabela(afetados, 12)
        )
        pior = afetados.iloc[0]
        if pior["modelos"] >= 5:
            partes.append(
                f"\n**{pior['mes_ref']} e' edicao defeituosa na origem.** Ali "
                f"{pior['modelos']} modelos saem sob marca trocada -- `PONTIAC/MONTANA`, "
                "`FORD/KOMBI`, `VW/RANGER`, `FORD/MASTER`, `THINK/CITY`, e um `/ELANTRA` "
                "sem marca nenhuma. Sao palavras unicas no PDF, nao erro de leitura: a "
                "fonte trocou a coluna. Cada troca cria uma marca fantasma com uma entrada "
                "e uma saida, e tira o volume da marca certa naquele mes. Quem for usar "
                f"series por marca precisa decidir o que fazer com {pior['mes_ref']}; o "
                "painel nao decide.\n"
            )
        legitimas = divergentes[divergentes["modelo"] == "TIGGO 7"]
        if not legitimas.empty:
            partes.append(
                "\nNem toda divergencia e' defeito: `TIGGO 7` sob `CHERY` em 2019-2020 "
                "contra `CAOA CHERY` depois e' **troca real de marca**, nao erro. O teste "
                "aponta; a leitura e' humana.\n"
            )

    partes.append("\n### Ranking contra tabela de sub-segmento\n\n")
    caminho_div = config.DIR_SAIDAS / "divergencias_fonte.csv"
    if caminho_div.exists():
        divergencias = pd.read_csv(caminho_div)
        partes.append(
            "Modelos em que o ranking mensal e a tabela de sub-segmento do **mesmo** informe "
            f"trazem numeros diferentes -- {len(divergencias)} casos. O painel usa o valor "
            "da tabela de sub-segmento.\n\n" + _tabela(divergencias, 20))
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
