"""Segmento derivado do nome do sub-segmento, e nao do marcador da secao."""

from comum import sub_segmentos
from comum.informe import _desdobrar


def test_mapa_cobre_os_dois_segmentos():
    assert sub_segmentos.segmento_de("Suv's") == "automoveis"
    assert sub_segmentos.segmento_de("Veículos de Entrada") == "automoveis"
    assert sub_segmentos.segmento_de("Furgões") == "comerciais_leves"
    assert sub_segmentos.segmento_de("Pick-up's Grandes") == "comerciais_leves"


def test_chave_ignora_acento_caixa_e_pontuacao():
    # variantes de grafia observadas na fonte tem de cair no mesmo lugar
    assert sub_segmentos.segmento_de("Pickup's Grandes") == "comerciais_leves"
    assert sub_segmentos.segmento_de("PICK-UPS GRANDES") == "comerciais_leves"
    assert sub_segmentos.segmento_de("sedans medios") == "automoveis"


def test_nome_desconhecido_nao_e_adivinhado():
    assert sub_segmentos.segmento_de("Categoria Inexistente") is None


def test_desdobra_linha_com_caractere_duplicado():
    # Jan/2022 desenha o cabecalho duas vezes; sem isto ele viraria sub-segmento
    assert _desdobrar("DDeezz JJaann AAccuummuullaaddoo") == "Dez Jan Acumulado"


def test_nao_desdobra_nome_legitimo():
    for nome in ["Sedans Compactos", "Suv's", "Veículos de Entrada", "Hatch Pequenos"]:
        assert _desdobrar(nome) == nome
