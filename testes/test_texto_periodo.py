"""Normalizacao tipografica e aritmetica de meses."""

import pytest

from comum import periodo
from comum.texto import eh_numero_br, normalizar_tipografia, numero_br


def test_normaliza_so_o_que_e_tipografico():
    assert normalizar_tipografia("  VW\xa0/  GOL   ") == "VW / GOL"
    # acento, caixa e grafia ficam intactos (sec.4)
    assert normalizar_tipografia("Veículos de Entrada") == "Veículos de Entrada"
    assert normalizar_tipografia("CAMINÕES") == "CAMINÕES"


def test_numero_no_formato_da_fonte():
    assert numero_br("44.272") == 44272.0
    assert numero_br("0,00") == 0.0
    assert numero_br("1") == 1.0
    assert numero_br("58,43") == 58.43
    assert eh_numero_br("3514") and not eh_numero_br("=") and not eh_numero_br("1º")
    with pytest.raises(ValueError):
        numero_br("100%")


def test_intervalo_e_distancia():
    assert len(periodo.intervalo("2014-01", "2026-08")) == 152
    assert periodo.intervalo("2014-11", "2015-02") == ["2014-11", "2014-12", "2015-01", "2015-02"]
    assert periodo.distancia("2014-01", "2013-11") == -2
    assert periodo.de_indice(periodo.para_indice("2020-04")) == "2020-04"
    with pytest.raises(ValueError):
        periodo.intervalo("2015-01", "2014-01")
