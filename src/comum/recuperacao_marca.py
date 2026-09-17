"""Recuperacao da marca de um mes cuja edicao saiu com a coluna trocada (D4).

Novembro de 2013 publica `PONTIAC/MONTANA` (3.901 unidades), `FORD/KOMBI`,
`VW/RANGER`, `FORD/MASTER`, `THINK/CITY` e um `/ELANTRA` sem marca nenhuma. Nao
e' erro de leitura -- sao objetos de texto unicos no PDF --, e' a fonte que
trocou a coluna naquela edicao.

**Isto nao e' correcao de numero da fonte, e nao contraria a sec.9.4.** O numero
nao muda: o que muda e' a quem ele e' atribuido, e a nova atribuicao vem da
**mesma fonte republicando o mesmo mes**. E' a rota ja' validada em 2023-09
(sec.9.2): o informe de M+1 traz a coluna de mes anterior com M inteiro. Aqui
ela e' usada para a marca em vez de para o valor.

A validacao e' a coincidencia exata: so' se recupera a marca quando o valor
publicado em M+1 para aquele modelo bate **unidade a unidade** com o que M
publicou sob a marca trocada. Valor diferente nao recupera nada -- vira registro
de que a rota falhou ali.

Duas coisas que esta rota **nao** faz:

- Nao usa o acumulado do proprio informe de M. Em novembro de 2013 o defeito
  contamina as duas tabelas (a pg. 7 traz `PONTIAC/MONTANA` com o acumulado do
  ano), entao a conferencia interna carregaria o mesmo erro.
- Nao opina sobre divergencia que nao seja defeito de edicao. `TIGGO 7` sob
  `CHERY` ate' 2020 e sob `CAOA CHERY` depois e' **troca real de marca**, e
  recupera-la seria destruir o dado. Por isso o escopo vem de
  `config/meses_com_marca_trocada.csv`, lista curada com motivo e evidencia por
  linha: o codigo le', o humano escreve.
"""

from __future__ import annotations

import csv

import pandas as pd

from . import config, marca_do_modelo, periodo

CAMPOS_MESES = ["mes_ref", "motivo", "fonte"]


def meses_declarados() -> dict[str, dict]:
    """Meses que o pesquisador declarou como edicao com marca trocada."""
    if not config.MESES_COM_MARCA_TROCADA.exists():
        return {}
    with config.MESES_COM_MARCA_TROCADA.open(encoding="utf-8", newline="") as fluxo:
        return {linha["mes_ref"]: linha for linha in csv.DictReader(fluxo)
                if linha.get("mes_ref")}


def _chave(nome: str) -> str:
    return str(nome).split("/")[-1].upper().strip()


def _extracao(mes: str) -> pd.DataFrame:
    caminho = config.DIR_EXTRACAO / f"{mes}.csv"
    if not caminho.exists():
        return pd.DataFrame()
    return pd.read_csv(caminho)


def recuperar(mes: str, divergentes: pd.DataFrame) -> pd.DataFrame:
    """Confronta os modelos marcados em `mes` com a coluna de mes anterior de M+1.

    Devolve uma linha por modelo, recuperado ou nao, com a evidencia ao lado.
    """
    alvo = divergentes[divergentes["mes_ref"] == mes]
    if alvo.empty:
        return pd.DataFrame()

    seguinte = periodo.de_indice(periodo.para_indice(mes) + 1)
    proximo = _extracao(seguinte)
    if proximo.empty:
        return pd.DataFrame()
    proximo = proximo.assign(chave=proximo["nome_completo_fonte"].map(_chave))

    linhas = []
    for _, registro in alvo.iterrows():
        chave = _chave(registro["modelo"])
        achados = proximo[proximo["chave"] == chave]
        linha = {
            "mes_ref": mes,
            "modelo": registro["modelo"],
            "segmento": registro["segmento"],
            "marca_publicada": registro["marca"],
            "unidades": registro["unidades"],
            "mes_fonte": seguinte,
        }
        if achados.empty:
            linhas.append({**linha, "marca_recuperada": "", "situacao":
                           "sem contraparte no informe seguinte"})
            continue
        candidato = achados.iloc[0]
        valor = candidato.get("unidades_mes_anterior")
        marca_seguinte = str(candidato["nome_completo_fonte"]).rsplit("/", 1)[0].strip()
        linha.update({
            "nome_no_informe_seguinte": candidato["nome_completo_fonte"],
            "pagina_fonte": candidato.get("pagina"),
            "origem_tabela_fonte": candidato.get("origem_tabela"),
            "valor_no_informe_seguinte": valor,
        })
        if pd.isna(valor):
            linhas.append({**linha, "marca_recuperada": "", "situacao":
                           "informe seguinte lista o modelo so' no ranking mensal, "
                           "que nao traz coluna de mes anterior"})
        elif float(valor) != float(registro["unidades"]):
            linhas.append({**linha, "marca_recuperada": "", "situacao":
                           f"valor nao confere ({valor:.0f} contra "
                           f"{float(registro['unidades']):.0f})"})
        else:
            linhas.append({**linha, "marca_recuperada": marca_seguinte,
                           "situacao": "recuperado: valor identico, marca corrigida"})
    return pd.DataFrame(linhas)


def recuperacoes(painel: pd.DataFrame) -> pd.DataFrame:
    """Todas as recuperacoes dos meses declarados, num quadro so'."""
    declarados = meses_declarados()
    if not declarados:
        return pd.DataFrame()
    divergentes = marca_do_modelo.divergencias(painel)
    if divergentes.empty:
        return pd.DataFrame()
    partes = [recuperar(mes, divergentes) for mes in sorted(declarados)]
    partes = [parte for parte in partes if not parte.empty]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def marcar_duplicatas_publicadas(bruto: pd.DataFrame) -> pd.DataFrame:
    """Marca, no painel bruto, a linha do ranking que duplica uma de sub-segmento.

    Recuperada a marca (`recuperacoes`), quatro linhas de 2013-11 passam a ser o
    **mesmo modelo, com o mesmo valor, no mesmo informe** que uma linha da tabela
    de sub-segmento. A regra Q7 e' que o sub-segmento manda e o ranking so'
    preenche o que ela nao lista, entao essas quatro nao deviam ter entrado.

    **Por que aqui e nao na chave da etapa 02.** As cinco irmas deste defeito --
    `VW /GOL` contra `VW/GOL` -- foram consertadas la', na canonizacao da chave
    de reconciliacao, porque a divergencia era **tipografica**: mesma marca,
    mesmo modelo, espaco a mais. Estas quatro resistiram ao mesmo conserto por um
    motivo incidental: a divergencia e' de **marca** (`PONTIAC/MONTANA` contra
    `GM /MONTANA`), e canonizar isso na etapa 02 significaria reescrever a marca
    dentro do painel bruto, que e' transcricao fiel da fonte (sec.4). Entao a
    linha entra como a fonte a publicou e sai **marcada**, nao apagada:
    `duplicata_publicada` aponta a linha que ela duplica, e a supressao acontece
    a jusante, no painel de analise.

    E' o mesmo defeito com dois tratamentos, e a assimetria esta' registrada no
    dicionario de dados e em `validacao.md` porque ela precisa de resposta
    escrita: a montante quando da' para consertar sem mexer no transcrito, a
    jusante quando nao da'.
    """
    marcado = bruto.copy()
    marcado["duplicata_publicada"] = ""
    recuperacoes_feitas = recuperacoes(
        marcado.rename(columns={"marca_fonte": "marca", "modelo_fonte": "modelo",
                                "segmento_fonte": "segmento"})
    )
    if recuperacoes_feitas.empty:
        return marcado
    aplicadas = recuperacoes_feitas[recuperacoes_feitas["marca_recuperada"] != ""]

    from .nomes import chave as _chave_do_nome

    for _, linha in aplicadas.iterrows():
        marca_certa = _chave_do_nome(linha["marca_recuperada"])
        modelo = _chave_do_nome(linha["modelo"])
        no_mes = (
            (marcado["mes_ref"] == linha["mes_ref"])
            & (marcado["segmento_fonte"] == linha["segmento"])
            & (marcado["modelo_fonte"].map(_chave_do_nome) == modelo)
        )
        do_sub = marcado[
            no_mes & (marcado["origem_tabela"] == "sub_segmento")
            & (marcado["marca_fonte"].map(_chave_do_nome) == marca_certa)
        ]
        do_ranking = marcado[
            no_mes & (marcado["origem_tabela"] == "ranking")
            & (marcado["marca_fonte"].map(_chave_do_nome)
               == _chave_do_nome(linha["marca_publicada"]))
        ]
        if do_sub.empty or do_ranking.empty:
            continue
        referencia = do_sub.iloc[0]
        if int(referencia["unidades"]) != int(do_ranking.iloc[0]["unidades"]):
            continue
        marcado.loc[do_ranking.index, "duplicata_publicada"] = (
            f"{referencia['nome_completo_fonte']} "
            f"({referencia['sub_segmento_fonte']}, pg. {referencia['pagina_origem']})"
        )
    return marcado


def duplicatas_apos_recuperacao(bruto: pd.DataFrame) -> pd.DataFrame:
    """Linhas do ranking que, recuperada a marca, repetem uma de sub-segmento.

    A regra Q7 e' que a tabela de sub-segmento manda e o ranking so' preenche o
    que ela nao lista. A deduplicacao compara o nome **com a marca**, entao a
    troca de coluna a derrotou: em 2013-11 o ranking publica `PONTIAC/MONTANA`
    e a tabela de sub-segmento `GM /MONTANA`, chaves diferentes, e a linha do
    ranking entrou como modelo novo. O mesmo numero foi contado duas vezes.

    E' o que explica a cobertura de 2013 acima de 100%.

    Esta funcao **so' mede**. Descartar as linhas mudaria o total do mes e
    quebraria o invariante central, que existe justamente para impedir que a
    harmonizacao mexa em volume -- e essa e' decisao do pesquisador (sec.9.6),
    nao do codigo.
    """
    if bruto.empty or "marca_recuperada" not in bruto:
        return pd.DataFrame()
    chave = ["mes_ref", "segmento_fonte", "marca_chave", "modelo_chave"]
    do_sub = bruto[bruto["origem_tabela"] == "sub_segmento"][chave + ["unidades"]]
    do_sub = do_sub.rename(columns={"unidades": "unidades_sub_segmento"})
    do_ranking = bruto[
        (bruto["origem_tabela"] == "ranking") & bruto["marca_recuperada"]
    ][chave + ["unidades", "marca_publicada_fonte"]]
    if do_ranking.empty or do_sub.empty:
        return pd.DataFrame()
    junto = do_ranking.merge(do_sub, on=chave, how="inner")
    junto["valor_identico"] = junto["unidades"] == junto["unidades_sub_segmento"]
    return junto.rename(columns={"unidades": "unidades_ranking"}).sort_values(
        "unidades_ranking", ascending=False)
