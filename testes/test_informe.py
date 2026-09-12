"""Leitura posicional das linhas do informe (sec.4, sec.7 item 1)."""

from comum.informe import _eh_ruido, _linha_modelo, _mes_do_titulo, _subtotal, _totais_do_resumo


def test_le_linha_de_modelo_da_direita_para_a_esquerda():
    lido = _linha_modelo("1º FIAT/MOBI 5.193 5.587 44.272 52,80%")
    assert lido == (1, "FIAT/MOBI", 5193.0, 5587.0, 44272.0, 52.80)


def test_numero_dentro_do_nome_do_modelo_nao_confunde():
    # 'IVECO/DAILY 3514' tem digitos no nome; os quatro campos da direita mandam
    lido = _linha_modelo("17º IVECO/DAILY 3514 270 302 302 4,92%")
    assert lido[1] == "IVECO/DAILY 3514"
    assert lido[3] == 302.0
    assert _linha_modelo("31º M.BENZ/SPRINTER 417 120 130 900 1,00%")[1] == "M.BENZ/SPRINTER 417"


def test_glifo_de_variacao_e_descartado():
    lido = _linha_modelo("3º RENAULT/E-KWID 0,00 1 = 235 0,28%")
    assert lido == (3, "RENAULT/E-KWID", 0.0, 1.0, 235.0, 0.28)


def test_linha_que_nao_e_modelo_e_recusada():
    assert _linha_modelo("Total 67.545 61.156 61.156 100%") is None
    assert _linha_modelo("Hatch Pequenos") is None
    assert _linha_modelo("Modelo Part.") is None


def test_subtotal_publicado_e_o_valor_do_mes():
    assert _subtotal("Total 67.545 61.156 61.156 100%") == 61156.0
    assert _subtotal("Hatch Pequenos") is None


def test_moldura_da_pagina_e_ruido():
    for linha in ["Ed. 133", "Informativo - Emplacamentos", "São Paulo, 01 de Fevereiro de 2014",
                  "www.fenabrave.org.br 11", "2013 2014 2014", "Modelo Part.",
                  "Dez Jan Acumulado"]:
        assert _eh_ruido(linha.strip()), linha
    for linha in ["Veículos de Entrada", "Suv's", "Pick-up's Pequenas", "Furgões"]:
        assert not _eh_ruido(linha), linha
    # marcadores de segmento nao passam por _eh_ruido: sao tratados antes, na
    # deteccao de secao, e por isso ficam de fora desta lista.


def test_mes_do_titulo():
    assert _mes_do_titulo("Resumo Mensal Agosto de 2026") == "2026-08"
    assert _mes_do_titulo("Resumo Mensal Janeiro de 2014") == "2014-01"
    assert _mes_do_titulo("Resumo Mensal") is None


def test_total_publicado_e_a_primeira_coluna():
    linhas = [
        "A) Autos 255.437 287.567 255.437 253.429 253.429 -11,17 0,79 0,79",
        "B) Com. Leves 44.300 48.359 44.300 43.423 43.423 -8,39 2,02 2,02",
    ]
    assert _totais_do_resumo(linhas) == {"automoveis": 255437.0, "comerciais_leves": 44300.0}
