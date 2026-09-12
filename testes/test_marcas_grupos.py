"""Separacao marca/modelo (sec.4) e mapa datado de grupo economico (D4)."""

from comum import grupos, marcas


def test_separa_pela_barra_que_a_fonte_usa():
    assert marcas.separar("VW/GOL") == marcas.Separacao("VW", "GOL", "barra", True)
    # marca de duas palavras nao pode quebrar no primeiro espaco
    assert marcas.separar("CAOA CHERY/TIGGO 5X").marca == "CAOA CHERY"
    assert marcas.separar("VW TRUCK E BUS/EXPRESS").marca == "VW TRUCK E BUS"
    # barra dentro do nome do modelo pertence ao modelo
    assert marcas.separar("VW/FOX/CROSS FOX").modelo == "FOX/CROSS FOX"


def test_sem_barra_usa_lista_explicita_e_nao_o_primeiro_espaco():
    separacao = marcas.separar("LAND ROVER DISCOVERY")
    assert (separacao.marca, separacao.modelo) == ("LAND ROVER", "DISCOVERY")
    assert separacao.metodo == "lista_de_marcas"


def test_nome_nao_resolvido_nao_e_adivinhado():
    separacao = marcas.separar("MARCA INEXISTENTE XYZ")
    assert separacao.metodo == "nao_resolvido"
    assert separacao.marca == ""
    assert not separacao.conhecida


def test_grupo_economico_e_datado_e_nunca_retroativo():
    # D4: Stellantis so' existe a partir de 2021-01
    assert grupos.grupo_de("FIAT", "2020-12") == "FCA"
    assert grupos.grupo_de("FIAT", "2021-01") == "STELLANTIS"
    assert grupos.grupo_de("PEUGEOT", "2020-12") == "PSA"
    assert grupos.grupo_de("PEUGEOT", "2021-01") == "STELLANTIS"
    # antes de 2021 FCA e PSA sao grupos separados
    assert grupos.grupo_de("FIAT", "2019-06") != grupos.grupo_de("PEUGEOT", "2019-06")


def test_outras_mudancas_de_propriedade_respeitam_a_data():
    assert grupos.grupo_de("VOLVO", "2010-07") == "FORD"
    assert grupos.grupo_de("VOLVO", "2010-08") == "GEELY"
    assert grupos.grupo_de("OPEL", "2017-07") == "GENERAL MOTORS"
    assert grupos.grupo_de("OPEL", "2017-08") == "PSA"


def test_marca_sem_linha_vigente_fica_marcada_e_nao_chutada():
    assert grupos.grupo_de("MARCA QUE NAO EXISTE", "2020-01") == grupos.NAO_MAPEADO
