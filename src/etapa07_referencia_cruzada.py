#!/usr/bin/env python3
"""Etapa 7 -- referencia cruzada com a planilha existente (ESPEC.md sec.7).

`Vendas_Geral.xlsx` **nao e' fonte**: e' controle independente, montado a' mao,
cobrindo 2013-2023. Depois de reconstruir o periodo do zero, comparamos modelo
a modelo e mes a mes e reportamos as divergencias -- elas revelam erro de
parsing de um lado ou do outro.

Dois fatos conhecidos sobre a planilha, usados como teste do proprio leitor:

1. Os rotulos de mes dizem `jan/23` em todas as abas, residuo de copia. A ordem
   das colunas esta' correta; o rotulo, nao. Por isso este leitor usa **posicao
   de coluna** e ignora o rotulo -- e reporta quando o rotulo confirma o erro.
2. A aba 2013 traz so' o top-50 anual, sem mensal. Fica **de fora**: misturada,
   criaria entrada fantasma em 2014.

A planilha e' opcional. Ausente, a etapa reporta a ausencia e sai sem falhar --
ela e' controle, nao insumo.

Uso:
    python src/etapa07_referencia_cruzada.py [--planilha CAMINHO]
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, familias, log, marcas, nomes  # noqa: E402

ETAPA = "etapa07_referencia_cruzada"
ANOS_COMPARAVEIS = range(2014, 2024)
RE_ROTULO_MES = re.compile(r"^([a-zA-Z]{3})[/\-]?(\d{2,4})$")


def _inteiros(quadro: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    """Contagem de unidades sai inteira, nao em notacao cientifica.

    `to_markdown` renderiza 3284610.0 como 3.28461e+06, que num relatorio de
    conferencia de totais e' exatamente o que nao se quer ler.
    """
    saida = quadro.copy()
    for coluna in colunas:
        if coluna in saida:
            saida[coluna] = saida[coluna].round(0).astype("Int64")
    return saida


def _tabela(quadro: pd.DataFrame, maximo: int = 40) -> str:
    if quadro.empty:
        return "_(vazio)_\n"
    texto = quadro.head(maximo).to_markdown(index=False)
    if len(quadro) > maximo:
        texto += f"\n\n_({len(quadro) - maximo} linhas restantes omitidas.)_"
    return texto + "\n"


RE_POSICAO = re.compile(r"^\d+\s*[ºo°]?$")


def _coluna_de_nome(rotulos: list[str], corpo: pd.DataFrame,
                    colunas_mes: list[int]) -> int | None:
    """Qual coluna traz `Marca Modelo`.

    O rotulo manda -- a planilha chama a coluna de `Marca/Veiculo`. So' quando
    ele nao existe e' que se procura pelo conteudo, e ai' a coluna de **posicao**
    ("1o", "2o", ...) tem de ser excluida explicitamente: sem isso o leitor a
    escolhe, e todo modelo vira um numero ordinal que nao casa com nada. Foi o
    que aconteceu na primeira execucao desta etapa.
    """
    for indice, rotulo in enumerate(rotulos):
        if indice in colunas_mes:
            continue
        chave = rotulo.strip().lower()
        if "veic" in chave or "veíc" in chave or "modelo" in chave:
            return indice

    melhor, melhor_texto = None, 0
    for indice in range(len(rotulos)):
        if indice in colunas_mes:
            continue
        valores = corpo.iloc[:, indice].dropna().astype(str).str.strip()
        valores = valores[valores.str.lower() != "nan"]
        if valores.empty:
            continue
        texto = int((~valores.str.match(RE_POSICAO)
                     & ~valores.str.match(r"^[\d.,]+$")).sum())
        if texto > melhor_texto:
            melhor, melhor_texto = indice, texto
    return melhor


def ler_planilha(caminho: Path, logger) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Le a planilha por posicao de coluna.

    Devolve (longo, observacoes, meses_sem_cobertura).
    """
    livro = pd.read_excel(caminho, sheet_name=None, header=None)
    observacoes: list[str] = []
    registros: list[dict] = []
    meses_vazios: set[str] = set()

    for aba, bruto in livro.items():
        achado = re.search(r"(20\d{2})", str(aba))
        if not achado:
            observacoes.append(f"aba `{aba}` ignorada: nome nao contem um ano")
            continue
        ano = int(achado.group(1))
        if ano == 2013:
            observacoes.append(
                "aba `2013` deixada de fora: a planilha traz so' o top-50 anual, sem mensal "
                "(sec.7, item 2). Misturada, criaria entrada fantasma em 2014."
            )
            continue
        if ano not in ANOS_COMPARAVEIS:
            observacoes.append(f"aba `{aba}` fora de 2014-2023, ignorada")
            continue

        # Cabecalho: primeira linha que traz pelo menos tres rotulos de mes.
        linha_cabecalho = None
        for indice in range(min(10, len(bruto))):
            rotulos = [str(v) for v in bruto.iloc[indice].tolist()]
            if sum(bool(RE_ROTULO_MES.match(r.strip())) for r in rotulos) >= 3:
                linha_cabecalho = indice
                break
        if linha_cabecalho is None:
            observacoes.append(f"aba `{aba}`: cabecalho de meses nao encontrado -- aba ignorada")
            continue

        rotulos = [str(v).strip() for v in bruto.iloc[linha_cabecalho].tolist()]
        colunas_mes = [i for i, r in enumerate(rotulos) if RE_ROTULO_MES.match(r)]
        distintos = {rotulos[i].lower() for i in colunas_mes}
        if len(distintos) == 1:
            observacoes.append(
                f"aba `{aba}`: os {len(colunas_mes)} rotulos de mes sao todos "
                f"`{rotulos[colunas_mes[0]]}` -- residuo de copia confirmado (sec.7, item 1). "
                "Colunas lidas por posicao."
            )
        colunas_mes = colunas_mes[:12]

        # Coluna de mes inteiramente vazia e' fim da cobertura do controle, nao
        # mercado parado: a aba 2023 so' vai ate' agosto. Compara-la contra o
        # painel acusaria +60% de divergencia que e' so' ausencia de dado.
        corpo_bruto = bruto.iloc[linha_cabecalho + 1:]
        vazias = [
            posicao for posicao, coluna in enumerate(colunas_mes, start=1)
            if pd.to_numeric(corpo_bruto.iloc[:, coluna], errors="coerce").fillna(0).sum() == 0
        ]
        if vazias:
            observacoes.append(
                f"aba `{aba}`: meses {', '.join(f'{m:02d}' for m in vazias)} sem nenhum "
                "valor -- a cobertura do controle termina antes do fim do ano. Esses "
                "meses ficam **fora** da comparacao."
            )
            meses_vazios.update(f"{ano}-{m:02d}" for m in vazias)

        corpo = bruto.iloc[linha_cabecalho + 1:]
        coluna_nome = _coluna_de_nome(rotulos, corpo, colunas_mes)
        if coluna_nome is None:
            observacoes.append(f"aba `{aba}`: coluna de nome nao identificada -- aba ignorada")
            continue
        for _, linha in corpo.iterrows():
            nome = str(linha.iloc[coluna_nome]).strip()
            if not nome or nome.lower() in {"nan", "total", "modelo"}:
                continue
            for posicao, coluna in enumerate(colunas_mes, start=1):
                valor = pd.to_numeric(linha.iloc[coluna], errors="coerce")
                if pd.isna(valor):
                    continue
                separacao = marcas.separar_da_planilha(nome)
                registros.append({
                    "mes_ref": f"{ano}-{posicao:02d}",
                    "marca": separacao.marca,
                    "modelo": separacao.modelo,
                    "nome_planilha": nome,
                    "unidades_planilha": float(valor),
                })
        logger.info("aba %s: %d colunas de mes, %d linhas de modelo", aba, len(colunas_mes), len(corpo))

    return pd.DataFrame(registros), observacoes, sorted(meses_vazios)


def _sem_zero(serie: pd.Series) -> pd.Series:
    """Denominador com zero virando NaN, sem trocar o dtype.

    `serie.replace(0, pd.NA)` parece equivalente e nao e': devolve uma serie de
    objetos, e o `.round()` seguinte estoura com NAType. `.where` mantem float.
    """
    return serie.where(serie != 0)


def executar(caminho: Path = config.VENDAS_GERAL) -> int:
    logger = log.preparar(ETAPA)
    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    cabecalho = (
        "# Referencia cruzada com `Vendas_Geral.xlsx`\n\n"
        f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC).\n\n"
        "A planilha e' **controle independente**, nao fonte (ESPEC.md sec.7). "
        "Divergencia aqui nao decide nada sozinha: ela aponta onde olhar.\n\n"
    )

    if not caminho.exists():
        texto = (
            cabecalho
            + f"## Situacao: planilha ausente\n\n"
            f"Esperada em `{log.caminho_relativo(caminho)}` e nao encontrada. A comparacao "
            "nao foi feita. Isto **nao** invalida o painel: a planilha e' controle, nao "
            "insumo.\n\nPara rodar o confronto, coloque o arquivo nesse caminho (ou passe "
            "`--planilha CAMINHO`) e execute:\n\n```\npython src/etapa07_referencia_cruzada.py\n"
            "```\n\nO que este confronto entrega, e que nenhuma outra etapa entrega:\n\n"
            "- **`saidas/so_na_planilha.csv`** -- modelos que a planilha traz e o painel nao "
            "tem em mes nenhum. E' a medida direta do truncamento.\n"
            "- **`saidas/colapsos_de_variante.csv`** -- familias em que a planilha tem mais "
            "variantes que o painel, por cardinalidade e nao por barra no nome. E' o unico "
            "teste que enxerga a agregacao invisivel: `Pajero TR4`, `Pajero HPE` e "
            "`Pajero Full` contra um unico `MITSUBISHI/PAJERO`.\n"
            "- A comparacao mes a mes e modelo a modelo, que revela erro de leitura dos "
            "dois lados.\n"
        )
        config.REFERENCIA_CRUZADA.write_text(texto, encoding="utf-8")
        logger.warning("planilha de controle ausente em %s -- comparacao nao realizada",
                       log.caminho_relativo(caminho))
        return 0

    if not config.PAINEL.exists():
        raise log.ErroDeParsing(
            f"{log.caminho_relativo(config.PAINEL)} nao existe -- rode as etapas anteriores."
        )

    planilha, observacoes, meses_sem_cobertura = ler_planilha(caminho, logger)
    painel = pd.read_parquet(config.PAINEL)
    painel = painel[painel["ano"].isin(ANOS_COMPARAVEIS)]
    if meses_sem_cobertura:
        painel = painel[~painel["mes_ref"].isin(meses_sem_cobertura)]
        logger.info("%d meses fora da comparacao por falta de cobertura do controle: %s",
                    len(meses_sem_cobertura), ", ".join(meses_sem_cobertura))
    reconstruido = (
        painel.groupby(["mes_ref", "marca", "modelo"], as_index=False)["unidades"].sum()
        .rename(columns={"unidades": "unidades_painel"})
    )

    # A chave de comparacao e' canonizada em caixa dos dois lados: a fonte
    # publica "GOL", a planilha escreve "Gol", e sao o mesmo carro. Isto nao
    # toca o painel -- e' a chave do merge, e as grafias originais seguem nas
    # colunas ao lado.
    for quadro, lado in ((reconstruido, "painel"), (planilha, "planilha")):
        quadro[f"marca_{lado}_grafia"] = quadro["marca"]
        quadro[f"modelo_{lado}_grafia"] = quadro["modelo"]
        quadro["marca"] = quadro["marca"].map(nomes.chave_de_comparacao)
        quadro["modelo"] = quadro["modelo"].map(nomes.chave_de_comparacao)

    comparacao = reconstruido.merge(planilha, on=["mes_ref", "marca", "modelo"], how="outer")
    comparacao["unidades_painel"] = comparacao["unidades_painel"].fillna(0)
    comparacao["unidades_planilha"] = comparacao["unidades_planilha"].fillna(0)
    comparacao["diferenca"] = comparacao["unidades_painel"] - comparacao["unidades_planilha"]
    comparacao["situacao"] = "igual"
    comparacao.loc[comparacao["diferenca"] != 0, "situacao"] = "diverge"
    comparacao.loc[comparacao["unidades_planilha"] == 0, "situacao"] = "so_no_painel"
    comparacao.loc[comparacao["unidades_painel"] == 0, "situacao"] = "so_na_planilha"
    comparacao.sort_values(["mes_ref", "marca", "modelo"]).to_csv(
        config.DIR_SAIDAS / "referencia_cruzada.csv", index=False)

    mensal = comparacao.groupby("mes_ref", as_index=False).agg(
        painel=("unidades_painel", "sum"), planilha=("unidades_planilha", "sum"))
    mensal["diferenca"] = mensal["painel"] - mensal["planilha"]
    mensal["diferenca_pct"] = (
        100 * mensal["diferenca"] / _sem_zero(mensal["planilha"])).round(3)

    anual = comparacao.assign(ano=comparacao["mes_ref"].str.slice(0, 4).astype(int))
    anual = anual.groupby("ano", as_index=False).agg(
        painel=("unidades_painel", "sum"), planilha=("unidades_planilha", "sum"))
    anual["diferenca"] = anual["painel"] - anual["planilha"]
    anual["diferenca_pct"] = (
        100 * anual["diferenca"] / _sem_zero(anual["planilha"])).round(3)

    piores = (
        comparacao[comparacao["situacao"] != "igual"]
        .assign(magnitude=lambda q: q["diferenca"].abs())
        .sort_values("magnitude", ascending=False)
        .drop(columns=["magnitude"])
    )

    # --------------------------------------------- sem contraparte alguma
    # Modelo que a planilha traz e o painel nao tem em ano nenhum: e' a medida
    # direta do truncamento, e o que confirma (ou nao) a hipotese 1 de I1.
    do_painel = set(zip(reconstruido["marca"].map(familias.chave),
                        reconstruido["modelo"].map(familias.chave)))
    so_na_planilha = (
        planilha.assign(
            marca_chave=planilha["marca"].map(familias.chave),
            modelo_chave=planilha["modelo"].map(familias.chave),
        )
        .groupby(["marca_chave", "modelo_chave", "nome_planilha"], as_index=False)
        .agg(unidades=("unidades_planilha", "sum"),
             meses=("mes_ref", "nunique"), primeiro_mes=("mes_ref", "min"))
    )
    so_na_planilha = so_na_planilha[
        [(m, mo) not in do_painel
         for m, mo in zip(so_na_planilha["marca_chave"], so_na_planilha["modelo_chave"])]
    ].sort_values("unidades", ascending=False)
    so_na_planilha.to_csv(config.DIR_SAIDAS / "so_na_planilha.csv", index=False)

    # -------------------------------------- colapso por cardinalidade
    # O teste de barra no nome (`MARCA/A/B`) nao ve a agregacao invisivel: a
    # planilha traz Pajero TR4, HPE e Full, e o painel traz PAJERO, sem barra.
    # Cardinalidade de familia enxerga -- onde a planilha tem mais variantes que
    # o painel, houve colapso.
    familias_painel = familias.cardinalidade(
        reconstruido, "marca", "modelo", "unidades_painel")
    familias_planilha = familias.cardinalidade(
        planilha, "marca", "modelo", "unidades_planilha")
    colapsos = familias.colapsos(familias_painel, familias_planilha)
    colapsos.to_csv(config.DIR_SAIDAS / "colapsos_de_variante.csv", index=False)

    texto = cabecalho
    texto += "## Observacoes do leitor da planilha\n\n"
    texto += "".join(f"- {o}\n" for o in observacoes) or "_(nenhuma)_\n"
    colunas_de_unidades = ["painel", "planilha", "diferenca"]
    texto += "\n## Total por ano\n\n" + _tabela(_inteiros(anual, colunas_de_unidades))
    texto += "\n## Total por mes\n\n" + _tabela(_inteiros(mensal, colunas_de_unidades), 200)
    texto += (
        f"\n## Divergencias modelo a modelo\n\n{len(piores)} pares (mes x modelo) divergentes "
        f"de {len(comparacao)} comparados. Lista completa em "
        "`saidas/referencia_cruzada.csv`.\n\n" + _tabela(piores, 60)
    )
    texto += (
        "\n## Sem contraparte no painel (truncamento)\n\n"
        "Modelos que a planilha traz e o painel nao tem em nenhum mes. Se as unidades "
        "deles baterem com o que a cobertura aponta como faltante, o truncamento esta' "
        "confirmado e a taxa de saida do painel esta' subestimada -- os modelos pequenos, "
        "onde entrada e saida acontecem, nao entram.\n\n"
        f"**{len(so_na_planilha)} modelos, {int(so_na_planilha['unidades'].sum()):,} "
        "unidades.** Mediana de "
        f"{float(so_na_planilha['unidades'].median()) if len(so_na_planilha) else 0:.0f} "
        "unidades. Lista completa em `saidas/so_na_planilha.csv`.\n\n"
        + _tabela(so_na_planilha, 30)
    ).replace(",", ".")
    texto += (
        "\n## Colapso de variante (agregacao invisivel)\n\n"
        "Familias -- primeira palavra do nome do modelo -- em que a planilha tem mais "
        "entradas que o painel. E' o teste que enxerga o que a barra no nome nao ve: a "
        "planilha traz `Pajero TR4`, `Pajero HPE` e `Pajero Full`, tres veiculos; o painel "
        "traz `MITSUBISHI/PAJERO`, uma ficha, sem barra nenhuma.\n\n"
        "A familia e' **heuristica de busca, nao classificacao**: aponta onde olhar. Cada "
        "linha e' caso para revisao humana, nunca correcao automatica.\n\n"
        f"**{len(colapsos)} familias** com variantes a mais na planilha. Lista completa em "
        "`saidas/colapsos_de_variante.csv`.\n\n" + _tabela(colapsos, 40)
    )
    config.REFERENCIA_CRUZADA.write_text(texto, encoding="utf-8")

    log.contagem(logger, linhas_planilha=len(planilha), linhas_painel=len(reconstruido),
                 comparadas=len(comparacao), divergentes=len(piores),
                 so_na_planilha=len(so_na_planilha), colapsos=len(colapsos))
    logger.info("gravado %s", log.caminho_relativo(config.REFERENCIA_CRUZADA))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--planilha", type=Path, default=config.VENDAS_GERAL)
    args = analisador.parse_args()
    return executar(args.planilha)


if __name__ == "__main__":
    raise SystemExit(main())
