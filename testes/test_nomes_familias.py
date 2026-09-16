"""Chave canonica, nomes que nao sao veiculo e colapso de variante (rodada 2)."""

import pandas as pd

from comum import familias, nomes


def test_chave_normaliza_caixa_e_espaco():
    assert nomes.chave(" Outlander ") == "OUTLANDER"
    assert nomes.chave("OUTLANDER") == nomes.chave("Outlander")


def test_colisao_de_caixa_e_detectada():
    """MITSUBISHI/Outlander e MITSUBISHI/OUTLANDER sao o mesmo carro (D1)."""
    quadro = pd.DataFrame([
        {"marca": "MITSUBISHI", "modelo": "Outlander", "segmento": "automoveis"},
        {"marca": "MITSUBISHI", "modelo": "OUTLANDER", "segmento": "automoveis"},
        {"marca": "GM", "modelo": "ONIX", "segmento": "automoveis"},
    ])
    colisoes = nomes.colisoes_de_caixa(quadro, ("marca", "modelo", "segmento"))
    assert len(colisoes) == 2
    assert set(colisoes["modelo"]) == {"Outlander", "OUTLANDER"}


def test_modelo_igual_a_marca_e_marcado_sem_lista():
    assert nomes.motivo_nao_veiculo("FIAT", "FIAT") == "nome do modelo igual ao da marca"


def test_lista_curada_pega_o_que_o_volume_nao_pegaria():
    """RIBEIRAUTO soma 67 unidades em 25 meses: nenhum corte de volume o acharia."""
    assert nomes.motivo_nao_veiculo("TOYOTA", "RIBEIRAUTO")
    assert nomes.motivo_nao_veiculo("M.BENZ", "RIBEIRAUTO")


def test_carro_de_verdade_com_uma_unidade_nao_e_marcado():
    """CITROEN/C4 e DODGE/CHARGER tem uma unidade e sao carros."""
    assert nomes.motivo_nao_veiculo("CITROEN", "C4") == ""
    assert nomes.motivo_nao_veiculo("DODGE", "CHARGER") == ""


def test_familia_agrupa_variantes_da_mesma_placa_de_nome():
    assert familias.familia("PAJERO TR4") == "PAJERO"
    assert familias.familia("Pajero Full") == "PAJERO"
    assert familias.familia("NEW FIESTA") == familias.familia("FIESTA")


def test_colapso_aparece_por_cardinalidade_e_nao_por_barra():
    """O painel traz uma ficha PAJERO; a planilha traz tres variantes."""
    do_painel = familias.cardinalidade(
        pd.DataFrame([{"marca": "MITSUBISHI", "modelo": "PAJERO", "unidades": 14_748}]),
        "marca", "modelo", "unidades")
    da_planilha = familias.cardinalidade(
        pd.DataFrame([
            {"marca": "Mitsubishi", "modelo": "Pajero TR4", "unidades": 7_519},
            {"marca": "Mitsubishi", "modelo": "Pajero HPE", "unidades": 4_800},
            {"marca": "Mitsubishi", "modelo": "Pajero Full", "unidades": 2_429},
        ]), "marca", "modelo", "unidades")
    colapsos = familias.colapsos(do_painel, da_planilha)
    assert len(colapsos) == 1
    linha = colapsos.iloc[0]
    assert linha["familia"] == "PAJERO"
    assert linha["variantes_painel"] == 1
    assert linha["variantes_planilha"] == 3
    assert linha["variantes_a_mais_na_planilha"] == 2
    # e nenhum dos nomes tem barra: o teste antigo nao veria nada disto
    assert "/" not in linha["nomes_planilha"]


def test_familia_igual_dos_dois_lados_nao_vira_colapso():
    """Cruze HB/Sedan contra Cruze/Cruze Sport6: dois produtos dos dois lados."""
    do_painel = familias.cardinalidade(
        pd.DataFrame([
            {"marca": "GM", "modelo": "CRUZE HB", "unidades": 10},
            {"marca": "GM", "modelo": "CRUZE SEDAN", "unidades": 10},
        ]), "marca", "modelo", "unidades")
    da_planilha = familias.cardinalidade(
        pd.DataFrame([
            {"marca": "GM", "modelo": "Cruze", "unidades": 10},
            {"marca": "GM", "modelo": "Cruze Sport6", "unidades": 10},
        ]), "marca", "modelo", "unidades")
    assert familias.colapsos(do_painel, da_planilha).empty
