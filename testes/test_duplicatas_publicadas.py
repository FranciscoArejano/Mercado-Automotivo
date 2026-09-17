"""As quatro linhas que a fonte publicou duas vezes (D4, Parte A).

Este teste e' a guarda do invariante central reescrito. A regra nova diz que os
totais mensais de `painel.parquet` e `painel_bruto.parquet` coincidem **depois
de excluidas as linhas marcadas em `duplicata_publicada`, e que essas linhas sao
exatamente estas quatro**. Um invariante com excecao enumerada e' mais forte que
um com dispensa: a excecao nao pode crescer em silencio, porque crescer quebra
este teste.

Se uma quinta duplicata aparecer -- outra edicao defeituosa, por exemplo --, e'
aqui que se descobre, e nao no total de um mes que mudou sozinho.
"""

import pandas as pd
import pytest

from comum import config, recuperacao_marca

# Mes, segmento, marca como publicada, modelo, valor. Travados de proposito.
AS_QUATRO = [
    ("2013-11", "automoveis", "THINK", "CITY", 2464),
    ("2013-11", "comerciais_leves", "PONTIAC", "MONTANA", 3901),
    ("2013-11", "comerciais_leves", "VW", "RANGER", 1967),
    ("2013-11", "comerciais_leves", "FORD", "MASTER", 839),
]
UNIDADES_SUPRIMIDAS = 9171


def _painel_bruto():
    if not config.PAINEL_BRUTO.exists():
        pytest.skip("painel_bruto.parquet ausente -- rode a etapa 03")
    return pd.read_parquet(config.PAINEL_BRUTO)


def test_as_marcadas_sao_exatamente_estas_quatro():
    bruto = _painel_bruto()
    marcadas = bruto[bruto["duplicata_publicada"] != ""]
    observadas = sorted(
        (linha.mes_ref, linha.segmento_fonte, linha.marca_fonte,
         linha.modelo_fonte, int(linha.unidades))
        for linha in marcadas.itertuples()
    )
    assert observadas == sorted(AS_QUATRO)
    assert int(marcadas["unidades"].sum()) == UNIDADES_SUPRIMIDAS


def test_cada_marcada_aponta_a_linha_que_duplica():
    bruto = _painel_bruto()
    marcadas = bruto[bruto["duplicata_publicada"] != ""]
    for linha in marcadas.itertuples():
        # Veio do ranking, e aponta uma linha de sub-segmento com pagina.
        assert linha.origem_tabela == "ranking"
        assert "pg." in linha.duplicata_publicada
        assert linha.modelo_fonte.upper() in linha.duplicata_publicada.upper()


def test_a_linha_apontada_existe_com_o_mesmo_valor():
    bruto = _painel_bruto()
    marcadas = bruto[bruto["duplicata_publicada"] != ""]
    for linha in marcadas.itertuples():
        gemeas = bruto[
            (bruto["mes_ref"] == linha.mes_ref)
            & (bruto["segmento_fonte"] == linha.segmento_fonte)
            & (bruto["origem_tabela"] == "sub_segmento")
            & (bruto["modelo_fonte"].str.upper() == linha.modelo_fonte.upper())
        ]
        assert not gemeas.empty, f"{linha.modelo_fonte} sem a linha que duplica"
        assert int(gemeas.iloc[0]["unidades"]) == int(linha.unidades)


def test_o_painel_nao_carrega_nenhuma_delas():
    if not config.PAINEL.exists():
        pytest.skip("painel.parquet ausente -- rode a etapa 05")
    painel = pd.read_parquet(config.PAINEL)
    bruto = _painel_bruto()
    assert (int(bruto["unidades"].sum()) - int(painel["unidades"].sum())
            == UNIDADES_SUPRIMIDAS)


def test_invariante_vale_nos_284_meses_excluidas_as_marcadas():
    if not config.PAINEL.exists():
        pytest.skip("painel.parquet ausente -- rode a etapa 05")
    painel = pd.read_parquet(config.PAINEL)
    bruto = _painel_bruto()
    sem_marcadas = bruto[bruto["duplicata_publicada"] == ""]
    antes = sem_marcadas.groupby("mes_ref")["unidades"].sum()
    depois = painel.groupby("mes_ref")["unidades"].sum()
    comparacao = pd.DataFrame({"bruto": antes, "painel": depois}).fillna(0)
    quebras = comparacao[comparacao["bruto"] != comparacao["painel"]]
    assert quebras.empty, f"invariante quebrado em {len(quebras)} meses"
    assert len(comparacao) == 284


def test_marcacao_exige_valor_identico():
    # A marcacao so' vale quando as duas linhas trazem o MESMO numero. Valor
    # diferente sao dois fatos da fonte, nao uma duplicata.
    bruto = pd.DataFrame([
        {"mes_ref": "2013-11", "segmento_fonte": "comerciais_leves",
         "marca_fonte": "GM", "modelo_fonte": "MONTANA", "origem_tabela": "sub_segmento",
         "unidades": 3901, "sub_segmento_fonte": "Pick-up's Pequenas",
         "nome_completo_fonte": "GM/MONTANA", "pagina_origem": 18},
        {"mes_ref": "2013-11", "segmento_fonte": "comerciais_leves",
         "marca_fonte": "PONTIAC", "modelo_fonte": "MONTANA", "origem_tabela": "ranking",
         "unidades": 3900, "sub_segmento_fonte": "",
         "nome_completo_fonte": "PONTIAC/MONTANA", "pagina_origem": 6},
    ])
    saida = recuperacao_marca.marcar_duplicatas_publicadas(bruto)
    assert (saida["duplicata_publicada"] == "").all()
