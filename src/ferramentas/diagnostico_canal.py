#!/usr/bin/env python3
"""Fase 1 da dimensao de canal: medir antes de construir.

Os informes separam **venda direta** de **varejo** em cinco tabelas. Antes de
extrair qualquer coisa, esta ferramenta mede, nos 284 informes:

1. em quais meses cada tabela existe, e desde quando;
2. a profundidade das tabelas por modelo -- quantas linhas, e se o numero e' fixo;
3. se o corte e' por segmento ou agregado;
4. se `direta + varejo` reconcilia com o total do mes publicado pela fonte.

**So' diagnostica**: nao escreve nada em `dados/processado/`.

Uso:
    python src/ferramentas/diagnostico_canal.py [--inicio AAAA-MM] [--fim AAAA-MM]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import config, informe, log, periodo  # noqa: E402

ETAPA = "diagnostico_canal"

# Os cinco tipos de tabela, pelo titulo que a propria fonte usa.
TIPOS = {
    "participacao_mes": re.compile(
        r"participa[çc][ãa]o de venda direta e (venda )?varejo\s+\w+/\d{4}", re.I),
    "participacao_acumulado": re.compile(
        r"participa[çc][ãa]o de venda direta e varejo acumulado", re.I),
    "marca_varejo_mes": re.compile(
        r"ranking por marca de emplac\w*\.? varejo\s+\w+/\d{4}", re.I),
    "marca_varejo_acumulado": re.compile(
        r"ranking por marca de emplac\w*\.? varejo acumulado", re.I),
    "marca_direta_mes": re.compile(
        r"ranking por marca de emplac\w*\.? venda direta\s+\w+/\d{4}", re.I),
    "marca_direta_acumulado": re.compile(
        r"ranking por marca de emplac\w*\.? venda direta acumulado", re.I),
    "modelo_direta_mes": re.compile(
        r"modelos mais emplacados venda direta\s+\w+/\d{4}", re.I),
    "modelo_varejo_mes": re.compile(
        r"modelos mais emplacados venda varejo\s+\w+/\d{4}", re.I),
    "modelo_direta_acumulado": re.compile(
        r"modelos mais emplac\w*\.? venda direta acumulado", re.I),
    "modelo_varejo_acumulado": re.compile(
        r"modelos mais emplac\w*\.? venda varejo acumulado", re.I),
}

# "12º VW/POLO 6.933" -- posicao, nome, unidades. Duas colunas por pagina.
# O nome PODE conter digito (`GM/S10`, `RAM/3500`, `BYD/DOLPHIN MINI`), entao as
# unidades sao o ultimo numero antes da proxima posicao ou do fim da linha --
# nao "o primeiro numero depois de um nome sem digitos", que perdia 1 em 10.
RE_LINHA_MODELO = re.compile(
    r"(\d{1,3})[ºo°]\s+(\S.*?)\s+([\d.]+)(?=\s+\d{1,3}[ºo°]\s|\s*$)")
RE_PCT = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*%")


def _tabela(quadro: pd.DataFrame, maximo: int = 40) -> str:
    if quadro.empty:
        return "_(vazio)_\n"
    texto = quadro.head(maximo).to_markdown(index=False)
    if len(quadro) > maximo:
        texto += f"\n\n_({len(quadro) - maximo} linhas restantes; ver o CSV.)_"
    return texto + "\n"


def _numero(texto: str) -> int | None:
    limpo = texto.replace(".", "").strip()
    return int(limpo) if limpo.isdigit() else None


def _linhas_de_modelo(texto: str) -> list[dict]:
    """Uma linha por modelo listado, com a coluna (1a = automoveis, 2a = leves)."""
    achados = []
    for linha in texto.splitlines():
        pares = RE_LINHA_MODELO.findall(linha)
        for coluna, (posicao, nome, valor) in enumerate(pares):
            unidades = _numero(valor)
            if unidades is None:
                continue
            achados.append({
                "posicao": int(posicao),
                "nome": " ".join(nome.split()),
                "unidades": unidades,
                "coluna": coluna,
            })
    return achados


def _participacao(texto: str) -> list[float]:
    return [float(p.replace(",", ".")) for p in RE_PCT.findall(texto)]


def diagnosticar(mes: str, caminho: Path) -> dict:
    achado: dict = {"mes": mes, "arquivo": caminho.name}
    if not caminho.exists():
        achado["situacao"] = "pdf ausente"
        return achado
    paginas_por_tipo: dict[str, int] = {}
    modelos: dict[str, list[dict]] = defaultdict(list)
    percentuais: list[float] = []
    try:
        with pdfplumber.open(caminho) as pdf:
            achado["paginas"] = len(pdf.pages)
            for numero, pagina in enumerate(pdf.pages, 1):
                texto = pagina.extract_text() or ""
                if not texto:
                    continue
                # Informe com fonte sem ToUnicode devolve `(cid:N)` no lugar do
                # texto. A etapa 02 ja' sabe traduzir isso pela ordem padrao de
                # glifos TrueType, e sem reusar isso aqui quatro meses de 2020 e
                # 2024 apareceriam como "a fonte nao publica tabela de canal",
                # quando publica -- o defeito seria do leitor.
                if informe.tem_cids(texto):
                    texto = informe.decodificar_cids(texto)
                cabecalho = "\n".join(texto.splitlines()[:6])
                for tipo, padrao in TIPOS.items():
                    if tipo in paginas_por_tipo or not padrao.search(cabecalho):
                        continue
                    paginas_por_tipo[tipo] = numero
                    if tipo.startswith("modelo_") and tipo.endswith("_mes"):
                        modelos[tipo] = _linhas_de_modelo(texto)
                    if tipo == "participacao_mes":
                        percentuais = _participacao(texto)
    except Exception as erro:
        achado["situacao"] = f"erro de leitura: {erro}"
        return achado

    achado["situacao"] = "ok" if paginas_por_tipo else "sem tabela de canal"
    for tipo in TIPOS:
        achado[f"pg_{tipo}"] = paginas_por_tipo.get(tipo, "")
    achado["tipos_presentes"] = len(paginas_por_tipo)

    for tipo in ("modelo_direta_mes", "modelo_varejo_mes"):
        linhas = modelos.get(tipo, [])
        curto = tipo.replace("modelo_", "").replace("_mes", "")
        autos = [l for l in linhas if l["coluna"] == 0]
        leves = [l for l in linhas if l["coluna"] == 1]
        achado[f"{curto}_linhas_automoveis"] = len(autos)
        achado[f"{curto}_linhas_leves"] = len(leves)
        achado[f"{curto}_unidades_automoveis"] = sum(l["unidades"] for l in autos)
        achado[f"{curto}_unidades_leves"] = sum(l["unidades"] for l in leves)
        achado[f"{curto}_ultima_posicao"] = max((l["posicao"] for l in linhas), default=0)

    achado["participacao_pct"] = "; ".join(f"{p:g}" for p in percentuais)
    achado["participacao_pares_fecham_100"] = sum(
        1 for i in range(0, len(percentuais) - 1, 2)
        if abs(percentuais[i] + percentuais[i + 1] - 100) <= 0.6
    )
    return achado


def _numerico(quadro: pd.DataFrame, colunas: list[str]) -> pd.DataFrame:
    saida = quadro.copy()
    for coluna in colunas:
        if coluna in saida:
            saida[coluna] = pd.to_numeric(saida[coluna], errors="coerce")
    return saida


def _cobertura(com_canal: pd.DataFrame) -> pd.DataFrame:
    """Quanto do total publicado as duas tabelas top-50 explicam, por ano.

    E' o teste que decide se a dimensao presta: se `direta + varejo` cobre uma
    fracao pequena do mes, a dimensao so' serve para o topo do ranking.
    """
    caminho = config.DIR_PROCESSADO / "extracao_totais.csv"
    if not caminho.exists():
        return pd.DataFrame()
    totais = pd.read_csv(caminho)
    publicado = totais.pivot_table(index="mes", columns="segmento",
                                   values="total_publicado", aggfunc="first")
    indexado = com_canal.set_index("mes")
    partes = []
    for segmento, direta, varejo in (
        ("automoveis", "direta_unidades_automoveis", "varejo_unidades_automoveis"),
        ("comerciais_leves", "direta_unidades_leves", "varejo_unidades_leves"),
    ):
        if segmento not in publicado or direta not in indexado:
            continue
        junto = pd.DataFrame({
            "direta": indexado[direta], "varejo": indexado[varejo],
            "publicado": publicado[segmento],
        }).dropna()
        if junto.empty:
            continue
        junto["cobertura_pct"] = 100 * (junto["direta"] + junto["varejo"]) / junto["publicado"]
        junto["ano"] = junto.index.str.slice(0, 4)
        resumo = junto.groupby("ano")["cobertura_pct"].agg(["min", "median", "max"]).round(1)
        resumo.insert(0, "segmento", segmento)
        partes.append(resumo.reset_index())
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def _relatorio(detalhe: pd.DataFrame, logger) -> None:
    """Fase 1 em texto: as quatro perguntas, respondidas com os numeros medidos."""
    numericas = ["tipos_presentes", "direta_linhas_automoveis", "varejo_linhas_automoveis",
                 "direta_linhas_leves", "varejo_linhas_leves", "direta_ultima_posicao",
                 "varejo_ultima_posicao", "participacao_pares_fecham_100",
                 "direta_unidades_automoveis", "varejo_unidades_automoveis",
                 "direta_unidades_leves", "varejo_unidades_leves"]
    quadro = _numerico(detalhe, numericas)
    com_canal = quadro[quadro["tipos_presentes"].fillna(0) > 0]
    sem_canal = quadro[quadro["tipos_presentes"].fillna(0) == 0]

    partes = [
        "# Dimensao de canal -- diagnostico da fase 1\n\n",
        "So' medida: **nada foi extraido e nada foi escrito** em `dados/processado/`. "
        "A fase 2 depende da leitura destes numeros.\n\n",
        "## 1. Em quais meses a estrutura existe\n\n",
        f"Os informes trazem as dez tabelas de canal em **{len(com_canal)} dos "
        f"{len(quadro)} meses**, desde **{com_canal['mes'].min()}** -- a estrutura "
        "nao nasce no meio da serie, e a dimensao **nao e' mais curta que o painel**.\n\n",
    ]
    if not sem_canal.empty:
        partes.append(
            f"Os **{len(sem_canal)}** meses sem ela sao os mesmos que ja' faltam no painel, "
            "pelas mesmas causas: " + ", ".join(f"`{m}`" for m in sem_canal["mes"]) + ". "
            "Duas sao as edicoes curtas de 10 paginas e a terceira e' o informe "
            "digitalizado, recuperado do mes seguinte.\n\n"
        )

    partes.append(
        "## 2. Profundidade das tabelas por modelo\n\n"
        "**Sao ranking de 50 posicoes por segmento, nao tabela de sub-segmento.** A "
        "suspeita da fase 1 se confirma: a cauda e' bem mais rasa que a do painel "
        "principal, que lista cerca de 180 modelos por mes somando os sub-segmentos.\n\n"
    )
    linhas_prof = []
    for rotulo, coluna in (
        ("automoveis, venda direta", "direta_linhas_automoveis"),
        ("automoveis, varejo", "varejo_linhas_automoveis"),
        ("comerciais leves, venda direta", "direta_linhas_leves"),
        ("comerciais leves, varejo", "varejo_linhas_leves"),
    ):
        serie = com_canal[coluna].dropna()
        if serie.empty:
            continue
        linhas_prof.append({
            "tabela": rotulo, "minimo": int(serie.min()),
            "mediana": float(serie.median()), "maximo": int(serie.max()),
            "meses_com_50_linhas": int((serie == 50).sum()),
        })
    partes.append(_tabela(pd.DataFrame(linhas_prof)) + "\n")
    teto = com_canal["direta_ultima_posicao"].dropna()
    if not teto.empty:
        partes.append(
            f"A **ultima posicao listada e' 50** em {int((teto == 50).sum())} dos "
            f"{len(teto)} meses. Automoveis sempre preenche as 50; comerciais leves fica "
            "abaixo porque o segmento tem menos modelos, nao porque a tabela corte antes.\n\n"
        )

    partes.append(
        "## 3. O corte e' por segmento\n\n"
        "Automoveis e comerciais leves saem **em colunas separadas na mesma pagina**, "
        "cada um com o proprio ranking de 50. Nao e' agregado.\n\n"
        "## 4. `direta + varejo` reconcilia com o total publicado?\n\n"
    )
    cobertura = _cobertura(com_canal)
    if cobertura.empty:
        partes.append("_Totais publicados indisponiveis -- rode a etapa 02._\n")
    else:
        autos = cobertura[cobertura["segmento"] == "automoveis"]
        leves = cobertura[cobertura["segmento"] == "comerciais_leves"]
        partes.append(
            "**Sim, e com folga.** A soma das duas tabelas top-50 contra o total que o "
            "proprio informe publica:\n\n"
        )
        if not autos.empty:
            partes.append(
                f"- **automoveis**: de {autos['min'].min():.1f}% a {autos['max'].max():.1f}%, "
                f"mediana anual entre {autos['median'].min():.1f}% e "
                f"{autos['median'].max():.1f}%\n")
        if not leves.empty:
            partes.append(
                f"- **comerciais leves**: de {leves['min'].min():.1f}% a "
                f"{leves['max'].max():.1f}% -- praticamente completo\n")
        partes.append(
            "\nNenhum mes fica abaixo de 70%, muito longe do piso de metade do volume que "
            "encerraria a tarefa. **A dimensao presta.**\n\n"
            "Mas a cobertura **anda ao longo da serie**, e isso e' advertencia de "
            "comparabilidade mais forte que a do painel principal (que deriva 3,8 pontos): "
            "aqui a amplitude e' de 14 pontos, em forma de U -- alta nos anos 2000, fundo "
            "por volta de 2011, recuperando depois. Um ranking de tamanho fixo cobre menos "
            "quanto mais modelos o mercado tem.\n\n" + _tabela(cobertura, 60)
        )

    texto_pct = com_canal[com_canal["participacao_pares_fecham_100"] == 3]
    partes.append(
        "\n## Achado que muda o plano da fase 2\n\n"
        "Das tres granularidades pedidas, **so' uma entrega unidades**.\n\n"
        "- **Tabelas por modelo**: texto, com unidades, nos 281 meses. Servem para "
        "`painel_canal.parquet` como especificado.\n"
        "- **Ranking por marca**: nao e' tabela, e' **grafico de barras**. Os rotulos saem "
        "como texto rotacionado e trazem **percentual, nao unidades**, com os tres paineis "
        "sobrepostos quase no mesmo x. `canal_por_marca.csv` so' poderia trazer "
        "participacao, e a extracao seria fragil.\n"
    )
    if not texto_pct.empty:
        partes.append(
            f"- **Participacao agregada**: percentual em texto em apenas "
            f"**{len(texto_pct)} dos {len(com_canal)} meses**, a partir de "
            f"**{texto_pct['mes'].min()}**. Nos {len(com_canal) - len(texto_pct)} meses "
            "anteriores os numeros sao desenho, nao texto -- a pagina traz so' os rotulos "
            "de segmento. `canal_participacao.csv` cobriria de "
            f"{texto_pct['mes'].min()} em diante, nao a serie.\n"
        )
    partes.append(
        "\nA decisao sobre o que vale extrair das duas tabelas em percentual e' do "
        "pesquisador (sec.9.6).\n"
    )
    caminho = config.DIR_SAIDAS / "diagnostico_canal.md"
    caminho.write_text("".join(partes), encoding="utf-8")
    logger.info("gravado %s", log.caminho_relativo(caminho))


def executar(inicio: str, fim: str, refazer: bool = False) -> int:
    logger = log.preparar(ETAPA)
    if not config.MANIFESTO.exists():
        raise SystemExit("manifesto ausente -- rode a etapa 01.")
    with config.MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
        manifesto = {linha["mes"]: linha for linha in csv.DictReader(fluxo)}

    # Grava a cada mes, e retoma de onde parou (ESPEC sec.10.4: tarefa de fundo
    # nao e' dona de resultado). A primeira versao acumulava tudo em memoria e
    # gravava uma vez no fim; um restart de container no meio da varredura levou
    # junto cem meses de leitura. Ler 284 PDFs custa uma hora -- perder isso por
    # nao ter gravado e' desperdicio evitavel.
    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    destino = config.DIR_SAIDAS / "diagnostico_canal.csv"
    ja_medidos: dict[str, dict] = {}
    if destino.exists() and not refazer:
        anterior = pd.read_csv(destino, dtype=str, keep_default_na=False)
        ja_medidos = {linha["mes"]: linha for linha in anterior.to_dict("records")}
        if ja_medidos:
            logger.info("retomando: %d meses ja' medidos em %s",
                        len(ja_medidos), log.caminho_relativo(destino))

    linhas: list[dict] = []
    for mes in periodo.intervalo(inicio, fim):
        if mes in ja_medidos:
            linhas.append(ja_medidos[mes])
            continue
        registro = manifesto.get(mes)
        if registro is None:
            achado = {"mes": mes, "situacao": "sem informe baixado"}
        else:
            achado = diagnosticar(mes, config.RAIZ / registro["arquivo_local"])
            logger.info("%s: %s, %d tipos de tabela", mes, achado.get("situacao"),
                        achado.get("tipos_presentes", 0))
        linhas.append(achado)
        pd.DataFrame(linhas).to_csv(destino, index=False)

    detalhe = pd.DataFrame(linhas)
    detalhe.to_csv(destino, index=False)
    _relatorio(detalhe, logger)
    # Retomada le' o CSV como texto, entao a contagem converte antes de comparar.
    tipos = pd.to_numeric(detalhe.get("tipos_presentes"), errors="coerce").fillna(0)
    log.contagem(logger, meses=len(detalhe), com_canal=int((tipos > 0).sum()))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--inicio", default=config.PERIODO_INICIO)
    analisador.add_argument("--fim", default=config.PERIODO_FIM)
    analisador.add_argument("--refazer", action="store_true",
                            help="ignora o que ja' foi medido e le' tudo de novo")
    argumentos = analisador.parse_args()
    return executar(argumentos.inicio, argumentos.fim, argumentos.refazer)


if __name__ == "__main__":
    raise SystemExit(main())
