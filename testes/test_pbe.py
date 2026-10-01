"""Leitor das tabelas do PBE Veicular.

Os casos de `test_linhas_reais` sao linhas copiadas literalmente do texto
extraido das tabelas (2009 a 2024), cada uma escolhida por um defeito que ja'
apareceu ou que a diagramacao convida. Os outros testes usam linhas construidas,
e dizem isso.
"""

import pytest

from comum import pbe

MARCAS = sorted({("CHEVROLET",), ("VOLKSWAGEN",), ("KIA",), ("BYD",), ("NISSAN",),
                 ("LEAPMOTOR",), ("FIAT",), ("MERCEDES-BENZ",), ("TOYOTA",), ("LAND", "ROVER")},
                key=lambda t: -len(t))


def test_normalizar_tira_acento_e_unifica_hifen():
    assert pbe.normalizar("Elétrico  Híbrido­1.0") == "ELETRICO HIBRIDO-1.0"


@pytest.mark.parametrize("linha,esperado", [
    # 2009: sem categoria, sem coluna de propulsao
    ("CHEVROLET CELTA 2P SPIRIT 1.0 L M-5 N M F C",
     {"marca_pbe": "CHEVROLET", "modelo_versao": "CELTA 2P SPIRIT", "motor": "1.0",
      "tipo_propulsao": "", "combustivel": "F"}),
    # 2013: categoria antes da marca
    ("COMPACTO VOLKSWAGEN NOVO GOL 1.6-8V MTA-5 S H F 0,020 0,355 0,061 *** 0 112 7,3 9,5 "
     "10,7 13,6 1,84 B B -",
     {"categoria": "COMPACTO", "modelo_versao": "NOVO GOL", "combustivel": "F"}),
    # 2021: a palavra de propulsao cai entre a direcao e o combustivel
    ("SUB COMPACTO FIAT MOBI EASY 1.0-8V M-5 N M COMBUSTAO F 0,021 0,416 0,019 B 0 91 9,7 "
     "10,7 13,7 15,3 1,47 B B",
     {"modelo_versao": "MOBI EASY", "tipo_propulsao": "COMBUSTAO", "combustivel": "F"}),
    # 2021: "AT" no nome da versao nao e' a transmissao
    ("EXTRA GRANDE KIA STINGER GT 3.3 AT 3.3 - 24V A-8 S E COMBUSTAO G 0,010 0,129 0,006 A "
     "\\ 184 \\ \\ 6,6 9,2 2,98 E E",
     {"modelo_versao": "STINGER GT", "tipo_propulsao": "COMBUSTAO", "combustivel": "G"}),
    # 2021: MHEV no nome, Hibrido na coluna
    ("MEDIO KIA STONIC MHEV SX 1.0 - 12V DCT-7 S E HIBRIDO G 0,011 0,139 0,008 A \\ 100 "
     "\\ \\ 13,3 13,2 1,62 B B",
     {"modelo_versao": "STONIC MHEV SX", "tipo_propulsao": "HIBRIDO",
      "marcador_nome": "MHEV", "combustivel": "G"}),
    # 2024: eletrico, motor e propulsao escritos ELETRICO, transmissao N.A.
    ("SUB COMPACTO BYD DOLPHIN MINI GS EV ELETRICO ELETRICO N.A. S E E 0 0 0 A \\ 0 \\ "
     "\\ \\ \\ \\ 58.6 41.9 0.41 280 A A -",
     {"modelo_versao": "DOLPHIN MINI GS EV", "motor": "ELETRICO",
      "tipo_propulsao": "ELETRICO", "combustivel": "E"}),
    # 2021: motor escrito pelo nome comercial da Fiat
    ("FIAT PULSE DRIVE TF200 CVT-7 S E COMBUSTAO F 0,011 0,084 0,010 A 0 102 8,5 10,2 12,0 "
     "14,6 1,64 B B",
     {"modelo_versao": "PULSE DRIVE", "motor": "TF200", "combustivel": "F"}),
    # celula do modelo quebrada: a linha comeca no motor (2019)
    ("GRANDE MERCEDES-BENZ 2.0 - 16V DCT 7 S E G 0,014 0,113 0,010 A \\ 127 \\ \\ 9,2 "
     "13,5 2,05 C C -",
     {"marca_pbe": "MERCEDES-BENZ", "modelo_versao": "", "motor": "2.0", "combustivel": "G"}),
    # marca de duas palavras
    ("FORA DE ESTRADA LAND ROVER DEFENDER 90 - 2.0-16V A-8 S E COMBUSTAO G 0,005 0,126 "
     "0,019 A \\ 215 \\ \\ 6,1 6,8 3,49 D E",
     {"categoria": "FORA DE ESTRADA", "marca_pbe": "LAND ROVER", "modelo_versao": "DEFENDER 90 -"}),
])
def test_linhas_reais(linha, esperado):
    registro = pbe.ler_linha(linha, MARCAS)
    assert registro is not None
    for campo, valor in esperado.items():
        assert registro[campo] == valor, campo


@pytest.mark.parametrize("linha", [
    "www.inmetro.gov.br PROGRAMA BRASILEIRO DE ETIQUETAGEM",  # cabecalho
    "HAIMA 2 1.3-16V MT M-5 S H G 0,035",                    # marca fora da lista
    "CHEVROLET CELTA SPIRIT",                                 # sem motor nem trinca
])
def test_linha_que_nao_e_de_veiculo_lido(linha):
    assert pbe.ler_linha(linha, MARCAS) is None


def test_modelo_com_numero_nao_vira_motor():
    """'208' e' modelo, nao cilindrada: o motor exige ponto ou virgula. (Linha construida.)"""
    registro = pbe.ler_linha("COMPACTO PEUGEOT 208 ACTIVE 1.6-16V M-5 S E F 1", [("PEUGEOT",)])
    assert registro["modelo_versao"] == "208 ACTIVE"


def test_motor_em_outra_linha_nao_perde_o_modelo():
    """Celula do motor quebrada (2026): modelo ate' a propulsao, motor vazio."""
    linha = ("EXTRA GRANDE LEAPMOTOR C10 REEV PLUG-IN A-1 S E G 5 19 1 A \\ 135 111 7 \\ \\ \\ "
             "12,0 12,0 12,0 33,5 29,1 \\ \\ 0,65 111 A A SIM")
    registro = pbe.ler_linha(linha, MARCAS)
    assert registro["modelo_versao"] == "C10 REEV"
    assert registro["motor"] == ""
    assert registro["tipo_propulsao"] == "PLUG-IN"
    assert registro["marcador_nome"] == "REEV"
