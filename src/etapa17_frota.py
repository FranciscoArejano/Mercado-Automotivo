#!/usr/bin/env python3
"""Etapa 17 -- frota de veiculos por municipio (Senatran).

Le o bruto de `dados/bruto/senatran_frota/` (baixado por
`src/coleta/senatran_frota.py`, SHA-256 no manifesto) e grava:

- `dados/processado/frota_municipal.parquet` -- uma linha por municipio x mes x
  tipo de veiculo x combustivel. A Senatran **nao cruza tipo com combustivel** em
  nenhum nivel: ha' duas tabelas, municipio x tipo e municipio x combustivel. As
  linhas vem com `recorte = tipo` (combustivel = `todos`) ou `recorte =
  combustivel` (tipo = `todos`). Somar entre recortes conta a frota duas vezes;
- `saidas/frota_validacao.csv` e `saidas/frota_conferencia_uf.csv` -- soma dos
  municipios contra o total da UF (planilha UF x tipo), soma das UFs contra o
  Brasil, total de linha contra a soma dos tipos, e o recorte por combustivel
  contra o por tipo;
- `saidas/frota_municipal_dicionario.md`.

Rotulos: tipo e combustivel mudam de grafia entre anos. Todo rotulo passa por
`config/frota_rotulos.csv` (rotulo original, harmonizado, anos em que vale);
rotulo sem linha, ou fora dos anos da linha, para a etapa (codigo 1). Municipio:
casado com o IBGE por UF e nome normalizado (caixa, acento, pontuacao); o que nao
casa so' entra com linha em `config/frota_municipios.csv`.

Recorte no tempo (decisao do pesquisador para volume grande): todos os meses
desde 2020-01 e dezembro de cada ano de 2003 a 2019. Combustivel so' existe a
partir de 2013.

Uso:
    python src/etapa17_frota.py
    python src/etapa17_frota.py --rotulos    # lista os rotulos e os anos em que aparecem
"""

from __future__ import annotations

import argparse
import warnings
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coleta import comum_coleta as cc  # noqa: E402
from comum import config, energia, frota, log  # noqa: E402

ETAPA = "etapa17_frota"
warnings.filterwarnings("ignore", message="Cannot parse header or footer")
FONTE = "senatran_frota"
TODOS = "todos"
DESCARTADOS: list[dict] = []
SEM_UF: list[pd.DataFrame] = []
TITULO_DIFERENTE: list[dict] = []
EXCLUIDOS: list[pd.Series] = []
# combustivel fora de escala: total nacional do recorte combustivel mais de 10% acima ou
# abaixo do recorte tipo no mesmo mes (2021-11 vem x10 na fonte). O valor nao muda; a linha
# ganha `alerta_fonte` e o caso vai para a conferencia e para QUESTOES_ABERTAS.
LIMITE_ESCALA = 0.10


def arquivos_do_mes() -> pd.DataFrame:
    """(mes, tipo, arquivo do manifesto, nome interno, bytes) de cada tabela a ler."""
    manifesto = cc.ler_manifesto(FONTE)
    linhas = []
    for chave, linha in sorted(manifesto.items()):
        tipo, mes = linha["observacao"].split(" ")
        ano = int(mes[:4])
        caminho = cc.caminho_do_original(FONTE, linha)
        if cc.sha256_arquivo(caminho) != linha["sha256"]:
            raise RuntimeError(f"{chave}: SHA-256 nao bate com o manifesto")
        conteudo = caminho.read_bytes()
        internos = frota.desembalar(caminho.name, conteudo)
        if tipo == "zip_anual":
            for nome, dados in internos:
                t = frota.tipo_interno(nome)
                if t and frota.e_dezembro(nome, ano):
                    linhas.append((f"{ano}-12", t, chave, nome, dados))
        else:
            for nome, dados in internos:
                linhas.append((mes, tipo, chave, nome, dados))
    tabela = pd.DataFrame(linhas, columns=["mes", "tipo", "arquivo", "interno", "conteudo"])
    # dentro do zip anual, a planilha republicada leva "new" no nome (2007-12, UF x tipo):
    # fica a republicada, e a outra sai com registro em saidas/frota_arquivos_lidos.csv
    repetidos = tabela.duplicated(["mes", "tipo"], keep=False)
    nova = tabela["interno"].str.lower().str.contains(r"\bnew\b")
    descartar = repetidos & ~nova & tabela.groupby(["mes", "tipo"])["interno"].transform(
        lambda s: s.str.lower().str.contains(r"\bnew\b").sum() == 1)
    DESCARTADOS.extend(tabela[descartar][["mes", "tipo", "arquivo", "interno"]].to_dict("records"))
    tabela = tabela[~descartar]
    duplicados = tabela[tabela.duplicated(["mes", "tipo"], keep=False)]
    if len(duplicados):
        raise RuntimeError("mais de uma tabela para o mesmo mes e tipo: "
                           f"{duplicados[['mes', 'tipo', 'arquivo', 'interno']].values.tolist()}")
    return tabela


def ler_tudo(tabela: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    municipal, uf, notas = [], [], []
    for r in tabela.itertuples():
        if r.tipo != "municipio_combustivel":
            titulo = frota.mes_do_titulo(r.interno, r.conteudo)
            if titulo and titulo != r.mes:
                TITULO_DIFERENTE.append({"mes": r.mes, "tipo": r.tipo, "arquivo": r.arquivo,
                                         "interno": r.interno, "mes_no_titulo": titulo})
        try:
            if r.tipo == "municipio_tipo":
                quadro, info = frota.ler_municipio_tipo(r.interno, r.conteudo)
                quadro["recorte"] = "tipo"
                linhas = pd.DataFrame(info["totais_linha"],
                                      columns=["uf", "municipio_fonte", "total", "soma"])
                notas.append({"mes": r.mes, "tipo": r.tipo, "arquivo": r.arquivo,
                              "total_publicado": info["total_publicado"],
                              "tracos_zero": info["tracos_zero"],
                              "linhas_total_diferente": int(
                                  (linhas["total"].notna() & (linhas["total"] != linhas["soma"])
                                   ).sum())})
            elif r.tipo == "municipio_combustivel":
                quadro = frota.ler_municipio_combustivel(r.interno, r.conteudo)
                quadro["recorte"] = "combustivel"
            else:
                q = frota.ler_uf_tipo(r.interno, r.conteudo)
                q["mes"] = r.mes
                uf.append(q)
                continue
        except Exception as erro:  # noqa: BLE001
            if r.tipo == "uf_tipo":
                notas.append({"mes": r.mes, "tipo": r.tipo, "arquivo": r.arquivo,
                              "erro_leitura": f"{type(erro).__name__}: {str(erro)[:120]}"})
                continue
            raise RuntimeError(f"{r.arquivo} ({r.interno}): {erro}") from erro
        quadro["mes"] = r.mes
        quadro["arquivo_fonte"] = r.arquivo + ("" if r.interno == Path(r.arquivo).name
                                               else f"#{r.interno}")
        municipal.append(quadro)
    municipal = pd.concat(municipal, ignore_index=True)
    sem_uf = municipal["uf"] == ""
    SEM_UF.append(municipal[sem_uf].groupby(["mes", "uf_fonte"])["veiculos"].sum()
                  .reset_index())
    return municipal[~sem_uf].drop(columns="uf_fonte"), pd.concat(uf, ignore_index=True), notas


def harmonizar(quadro: pd.DataFrame, rotulos: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Rotulo harmonizado por (dimensao, rotulo original, ano); e as faltas."""
    quadro = quadro.assign(ano=quadro["mes"].str[:4].astype(int),
                           dimensao=quadro["recorte"].map({"tipo": "tipo",
                                                           "combustivel": "combustivel"}))
    chaves = quadro[["dimensao", "rotulo", "ano"]].drop_duplicates()
    unidas = chaves.merge(rotulos, left_on=["dimensao", "rotulo"],
                          right_on=["dimensao", "rotulo_original"], how="left")
    valido = unidas["rotulo_harmonizado"].notna() & (
        unidas["ano"] >= unidas["ano_inicial"]) & (unidas["ano"] <= unidas["ano_final"])
    ok = unidas[valido].drop_duplicates(["dimensao", "rotulo", "ano"])
    faltas = chaves.merge(ok[["dimensao", "rotulo", "ano"]], how="left", indicator=True)
    faltas = faltas[faltas["_merge"] == "left_only"].drop(columns="_merge")
    mapa = {(d, r, a): h for d, r, a, h in ok[["dimensao", "rotulo", "ano",
                                               "rotulo_harmonizado"]].itertuples(index=False)}
    harmonizado = pd.Series([mapa.get(k) for k in zip(quadro["dimensao"], quadro["rotulo"],
                                                      quadro["ano"])], index=quadro.index)
    return harmonizado, faltas


def listar_rotulos(municipal: pd.DataFrame, uf: pd.DataFrame) -> pd.DataFrame:
    m = municipal.assign(ano=municipal["mes"].str[:4].astype(int))
    u = uf.assign(ano=uf["mes"].str[:4].astype(int), recorte="tipo_uf")
    juntos = pd.concat([m[["recorte", "rotulo", "ano", "veiculos"]],
                        u[["recorte", "rotulo", "ano", "veiculos"]]])
    return juntos.groupby(["recorte", "rotulo"]).agg(
        ano_inicial=("ano", "min"), ano_final=("ano", "max"),
        anos=("ano", "nunique"), veiculos_ultimo=("veiculos", "sum")).reset_index()


def executar(so_rotulos: bool = False) -> int:
    logger = log.preparar(ETAPA)
    tabela = arquivos_do_mes()
    municipal, uf, notas = ler_tudo(tabela)
    if so_rotulos:
        pd.set_option("display.width", 200)
        print(listar_rotulos(municipal, uf).to_string())
        return 0
    rotulos = pd.read_csv(config.FROTA_ROTULOS, dtype={"ano_inicial": int, "ano_final": int},
                          keep_default_na=False)
    municipal["harmonizado"], faltas = harmonizar(municipal, rotulos)
    uf_rec = uf.assign(recorte="tipo")
    uf["harmonizado"], faltas_uf = harmonizar(uf_rec, rotulos)
    faltas = pd.concat([faltas, faltas_uf]).drop_duplicates()
    if len(faltas):
        logger.error("rotulos sem linha em config/frota_rotulos.csv (ou fora dos anos):\n%s",
                     faltas.to_string())
        return 1
    excecoes = pd.read_csv(config.FROTA_MUNICIPIOS, dtype=str, keep_default_na=False)
    fora = excecoes[excecoes["cod_ibge_municipio"] == ""]
    excecoes = excecoes[excecoes["cod_ibge_municipio"] != ""]
    chave_fora = {(u, energia.chave_nome(n)) for u, n in zip(fora["uf"], fora["nome_fonte"])}
    nomes_fora = {energia.chave_nome(n) for u, n in zip(fora["uf"], fora["nome_fonte"])
                  if u == "*"}
    sai = pd.Series([(u, energia.chave_nome(n)) in chave_fora or energia.chave_nome(n)
                     in nomes_fora for u, n in zip(municipal["uf"], municipal["municipio_fonte"])],
                    index=municipal.index)
    municipal[sai].groupby(["mes", "uf", "municipio_fonte", "recorte"])["veiculos"].sum(
    ).reset_index().merge(pd.concat(SEM_UF).rename(columns={"uf_fonte": "municipio_fonte"})
                          .assign(uf="", recorte="combustivel"), how="outer").to_csv(
        config.DIR_SAIDAS / "frota_sem_municipio.csv", index=False)
    EXCLUIDOS.append(municipal[sai & (municipal["recorte"] == "tipo")].groupby(
        ["mes", "uf"])["veiculos"].sum())
    municipal = municipal[~sai]
    pares = municipal[["uf", "municipio_fonte"]].drop_duplicates()
    pares["cod_ibge_municipio"] = energia.casar_municipios(pares, "uf", "municipio_fonte",
                                                           excecoes)
    sem_codigo = pares[pares["cod_ibge_municipio"].isna()]
    if len(sem_codigo):
        logger.error("municipios sem codigo IBGE (%d); acrescente a config/frota_municipios.csv:"
                     "\n%s", len(sem_codigo), sem_codigo.to_string())
        return 1
    municipal = municipal.merge(pares, on=["uf", "municipio_fonte"], how="left")
    produto = construir(municipal)
    conferencias, por_uf = conferir(produto, municipal, uf, notas)
    validacao = energia.gravar_validacao(config.FROTA_VALIDACAO, conferencias)
    por_uf.to_csv(config.DIR_SAIDAS / "frota_conferencia_uf.csv", index=False)
    pd.DataFrame(notas + [dict(d, erro_leitura="descartada: ha' versao 'new' no mesmo zip")
                          for d in DESCARTADOS]).to_csv(
        config.DIR_SAIDAS / "frota_arquivos_lidos.csv", index=False)
    if int(validacao["falhas"].sum()):
        logger.error("conferencias da frota com falha:\n%s", validacao.to_string())
        return 1
    produto.to_parquet(config.FROTA_MUNICIPAL, index=False)
    escrever_dicionario(produto)
    log.contagem(logger, linhas=len(produto), meses=produto["mes"].nunique(),
                 municipios=produto["cod_ibge_municipio"].nunique())
    logger.info("gravado %s", log.caminho_relativo(config.FROTA_MUNICIPAL))
    return 0


def construir(municipal: pd.DataFrame) -> pd.DataFrame:
    """Soma por rotulo harmonizado (dois rotulos originais podem virar o mesmo).

    Zeros publicados nao viram linha: no formato longo, a ausencia da combinacao
    municipio x mes x tipo (ou combustivel) quer dizer zero publicado -- a planilha
    traz todos os municipios e todos os tipos em todo mes.
    """
    tipo = municipal["recorte"] == "tipo"
    municipal = municipal.assign(
        tipo_veiculo=municipal["harmonizado"].where(tipo, TODOS),
        combustivel=municipal["harmonizado"].where(~tipo, TODOS))
    chave = ["mes", "uf", "cod_ibge_municipio", "recorte", "tipo_veiculo", "combustivel"]
    produto = municipal.groupby(chave, as_index=False, sort=False)["veiculos"].sum()
    produto = produto[produto["veiculos"] != 0]
    nomes = municipal.drop_duplicates(["mes", "cod_ibge_municipio", "municipio_fonte"]).groupby(
        ["mes", "cod_ibge_municipio"])["municipio_fonte"].agg(
        lambda s: " | ".join(sorted(s))).reset_index()
    rotulos = municipal.drop_duplicates(["mes", "recorte", "tipo_veiculo", "combustivel",
                                         "rotulo"]).groupby(
        ["mes", "recorte", "tipo_veiculo", "combustivel"]).agg(
        rotulos_fonte=("rotulo", lambda s: " | ".join(sorted(s))),
        arquivo_fonte=("arquivo_fonte", "first")).reset_index()
    produto = produto.merge(nomes, on=["mes", "cod_ibge_municipio"], how="left").merge(
        rotulos, on=["mes", "recorte", "tipo_veiculo", "combustivel"], how="left")
    produto["veiculos"] = produto["veiculos"].astype("int64")
    produto["alerta_fonte"] = ""
    por_mes = produto.groupby(["mes", "recorte"])["veiculos"].sum().unstack()
    razao = (por_mes["combustivel"] / por_mes["tipo"]).dropna()
    fora = razao[(razao - 1).abs() > LIMITE_ESCALA].index
    produto.loc[(produto["recorte"] == "combustivel") & produto["mes"].isin(fora),
                "alerta_fonte"] = "combustivel_fora_de_escala"
    return produto.sort_values(chave).reset_index(drop=True)


def conferir(produto, municipal, uf, notas) -> tuple[list[dict], pd.DataFrame]:
    tipo = produto[produto["recorte"] == "tipo"]
    comb = produto[produto["recorte"] == "combustivel"]
    excluidos = pd.concat(EXCLUIDOS) if EXCLUIDOS else pd.Series(dtype="int64")
    soma_uf = tipo.groupby(["mes", "uf"])["veiculos"].sum().rename("soma_municipios")
    soma_uf = soma_uf.add(excluidos.reindex(soma_uf.index).fillna(0)).rename(
        "soma_municipios")
    uf_total = uf[uf["harmonizado"] != "total"].groupby(["mes", "uf"])["veiculos"].sum().rename(
        "planilha_uf")
    por_uf = pd.concat([soma_uf, uf_total], axis=1).reset_index()
    soma_br = por_uf[por_uf["uf"] != "BR"].groupby("mes")[["soma_municipios"]].sum()
    br = por_uf[por_uf["uf"] == "BR"].set_index("mes")["planilha_uf"]
    por_uf = por_uf[por_uf["uf"] != "BR"]
    por_uf["diferenca"] = por_uf["soma_municipios"] - por_uf["planilha_uf"]
    com_uf = por_uf.dropna(subset=["planilha_uf"])
    difere = com_uf[com_uf["diferenca"] != 0]
    soma_ufs_planilha = com_uf.groupby("mes")["planilha_uf"].sum()
    br_difere = (soma_ufs_planilha - br.reindex(soma_ufs_planilha.index)).dropna()
    publicados = pd.DataFrame([n for n in notas if n.get("tipo") == "municipio_tipo"])
    publicados = publicados.set_index("mes")
    total_mun = soma_br["soma_municipios"]  # ja' com os nao informados
    pub = publicados["total_publicado"].dropna()
    pub_difere = (total_mun.reindex(pub.index) - pub)
    pub_difere = pub_difere[pub_difere != 0]
    sem_uf = sorted(set(tipo["mes"]) - set(com_uf["mes"]))
    erros_uf = [n for n in notas if n.get("erro_leitura")]
    escala = sorted(produto.loc[produto["alerta_fonte"] != "", "mes"].unique())
    comb_uf = comb.groupby(["mes", "uf"])["veiculos"].sum()
    tipo_uf = soma_uf.reindex(comb_uf.index)
    comb_dif = ((comb_uf - tipo_uf) / tipo_uf).abs()
    linhas = [
        {"conferencia": "soma dos municipios (mais os 'MUNICIPIO NAO INFORMADO' da UF) = total "
                        "da UF na planilha UF x tipo (mes x UF; diferenca registrada, nao e' "
                        "falha)",
         "casos": len(com_uf), "falhas": 0,
         "observacao": f"{len(difere)} casos com diferenca; maior |diferenca| "
                       f"{int(com_uf['diferenca'].abs().max()) if len(com_uf) else 0}; "
                       f"meses sem planilha de UF legivel: {', '.join(sem_uf) or 'nenhum'}"},
        {"conferencia": "soma das UFs = Brasil, na planilha UF x tipo",
         "casos": len(br_difere), "falhas": 0,
         "observacao": f"{int((br_difere != 0).sum())} meses com diferenca; maior |diferenca| "
                       f"{int(br_difere.abs().max()) if len(br_difere) else 0}"},
        {"conferencia": "soma dos municipios (mais os nao informados) = total Brasil impresso "
                        "na planilha municipio x tipo",
         "casos": len(pub), "falhas": 0,
         "observacao": f"{len(pub_difere)} meses com diferenca"
                       + (f": {', '.join(f'{m} ({int(v):+d})' for m, v in pub_difere.items())}"
                          if len(pub_difere) else "")},
        {"conferencia": "linha do municipio: coluna TOTAL = soma dos tipos",
         "casos": int(publicados.shape[0]), "falhas": 0,
         "observacao": f"{int(publicados['linhas_total_diferente'].sum())} linhas com "
                       "diferenca no conjunto"},
        {"conferencia": "recorte por combustivel contra recorte por tipo, por UF e mes "
                        "(diferenca relativa acima de 0,5%; registrada)",
         "casos": len(comb_dif), "falhas": 0,
         "observacao": f"{int((comb_dif > 0.005).sum())} casos acima de 0,5%; maior "
                       f"{100 * comb_dif.max():.2f}%"},
        {"conferencia": "recorte combustivel fora de escala (total nacional mais de 10% longe do "
                        "recorte tipo): linhas com alerta_fonte, valor da fonte mantido",
         "casos": len(escala), "falhas": 0, "observacao": ", ".join(escala) or "nenhum"},
        {"conferencia": "mes declarado no titulo da planilha diferente do mes do arquivo "
                        "(registrado, nao corrigido)",
         "casos": len(TITULO_DIFERENTE), "falhas": 0,
         "observacao": "; ".join(f"{t['mes']} {t['tipo']}: titulo diz {t['mes_no_titulo']}"
                                 for t in TITULO_DIFERENTE) or "nenhum"},
        {"conferencia": "planilha UF x tipo ilegivel (so' a conferencia fica sem ela)",
         "casos": len(erros_uf), "falhas": 0,
         "observacao": "; ".join(f"{n['mes']} {n['arquivo']}" for n in erros_uf) or "nenhuma"},
        {"conferencia": "tracos (formato contabil) lidos como zero na planilha municipio x tipo",
         "casos": int(publicados["tracos_zero"].sum()), "falhas": 0, "observacao": ""},
        {"conferencia": "chave unica (mes, municipio, recorte, tipo, combustivel)",
         "casos": len(produto),
         "falhas": int(produto.duplicated(["mes", "cod_ibge_municipio", "recorte",
                                           "tipo_veiculo", "combustivel"]).sum()),
         "observacao": ""},
    ]
    por_uf = por_uf.merge(comb_uf.rename("soma_combustivel").reset_index(), on=["mes", "uf"],
                          how="left")
    return linhas, por_uf


def escrever_dicionario(produto: pd.DataFrame) -> None:
    tipo = produto[produto["recorte"] == "tipo"]
    comb = produto[produto["recorte"] == "combustivel"]
    campos = [
        ("mes", "texto AAAA-MM", "Mes de referencia da estatistica (posicao no fim do mes)."),
        ("uf", "sigla", "UF do municipio."),
        ("cod_ibge_municipio", "7 digitos", "Codigo IBGE do municipio, da tabela de "
         "`dados/bruto/ibge/municipios.json` (a mesma das fabricas)."),
        ("recorte", "texto", "`tipo` (linha da tabela municipio x tipo) ou `combustivel` "
         "(linha da tabela municipio x combustivel). **Nao somar entre recortes.**"),
        ("tipo_veiculo", "texto", "Tipo harmonizado (`config/frota_rotulos.csv`); `todos` no "
         "recorte combustivel."),
        ("combustivel", "texto", "Combustivel harmonizado; `todos` no recorte tipo."),
        ("veiculos", "veiculos", "Frota registrada (com placa) no municipio no fim do mes."),
        ("municipio_fonte", "texto", "Nome do municipio como a Senatran escreve."),
        ("rotulos_fonte", "texto", "Rotulo(s) originais somados na linha (dois rotulos "
         "originais podem ter o mesmo harmonizado)."),
        ("arquivo_fonte", "texto", "Arquivo em `dados/bruto/senatran_frota/` (e, depois de `#`, "
         "a planilha dentro do zip ou rar)."),
    ]
    energia.gravar_dicionario(
        config.FROTA_DICIONARIO, "Dicionario -- frota_municipal",
        f"Gravado pela etapa 17 a partir das planilhas da Senatran guardadas em "
        f"`dados/bruto/senatran_frota/` (SHA-256 no manifesto). {len(produto):,} linhas. "
        f"Recorte tipo: {tipo['mes'].nunique()} meses, {tipo['mes'].min()} a "
        f"{tipo['mes'].max()}; recorte combustivel: {comb['mes'].nunique()} meses, "
        f"{comb['mes'].min()} a {comb['mes'].max()}. Dezembro de cada ano ate' 2019 e todos "
        "os meses desde 2020-01 (decisao do pesquisador para volume grande).",
        campos,
        ["**A fonte nao cruza tipo com combustivel.** A frota eletrica (recorte combustivel) "
         "inclui todos os tipos: motocicleta, motoneta, ciclomotor, onibus, caminhao, "
         "automovel. Nao ha' frota eletrica de automoveis e camionetas nesta base.",
         "**Combustivel so' a partir de 2013** (dezembro de 2013 vem num banco Access, lido com "
         "`mdb-export`). Antes, so' o recorte tipo.",
         "**Frota e' registro, nao circulacao:** veiculo baixado tarde, roubado ou fora de uso "
         "continua contado ate' a baixa no Renavam. A frota antiga e' superestimada.",
         "**Rotulos harmonizados** em `config/frota_rotulos.csv`; os casos ambiguos (por "
         "exemplo `ELETRICO/FONTE INTERNA`) ficam com rotulo proprio e estao em "
         "`QUESTOES_ABERTAS.md`.",
         "**Conferencias** em `saidas/frota_validacao.csv` e por UF e mes em "
         "`saidas/frota_conferencia_uf.csv`."],
        "Senatran (Ministerio dos Transportes), Estatisticas da frota de veiculos, "
        "https://www.gov.br/transportes/pt-br/assuntos/transito/conteudo-Senatran/"
        "estatisticas-frota-de-veiculos-senatran; URL e data de cada arquivo no manifesto.")


if __name__ == "__main__":
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--rotulos", action="store_true")
    raise SystemExit(executar(analisador.parse_args().rotulos))
