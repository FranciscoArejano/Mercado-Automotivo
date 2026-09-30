"""Rascunho da dimensao de classificacao (fase 1).

O que se trava aqui e' o que tornaria o rascunho enganoso sem ninguem notar:
regra do CSV sem codigo (ou codigo sem regra), sub-segmento novo da fonte sem
carroceria, vigencias que se sobrepoem ou deixam unidades de fora, e valor
fora da lista.
"""

import pandas as pd
import pytest

from comum import classificacao, config


def _painel(linhas):
    return pd.DataFrame(linhas, columns=["mes_ref", "marca", "modelo", "segmento",
                                         "sub_segmento_fonte", "unidades"])


def _propostas(linhas):
    colunas = ["marca", "modelo", "segmento", "vigencia_inicio", "vigencia_fim",
               "propulsao_oferecida", "carroceria", "origem_producao",
               "confianca_propulsao", "confianca_carroceria", "confianca_origem",
               "observacao"]
    return pd.DataFrame(linhas, columns=colunas, dtype=str)


@pytest.mark.parametrize("propulsao,esperado", [
    ("flex", "nenhuma"),
    ("gasolina+diesel", "nenhuma"),
    ("flex+hev", "parcial"),
    ("gasolina+phev+bev", "parcial"),
    ("bev", "total"),
    ("hev+phev", "total"),
    ("", ""),
])
def test_eletrificacao_derivada_do_conjunto(propulsao, esperado):
    assert classificacao.eletrificacao(propulsao) == esperado


def test_menor_confianca_e_o_pior_e_vazio_conta_como_baixa():
    assert classificacao.menor_confianca("alta", "media") == "media"
    assert classificacao.menor_confianca("alta", "") == "baixa"
    assert classificacao.menor_confianca("alta", "alta") == "alta"


def test_regras_por_nome_do_csv_e_do_codigo_sao_as_mesmas():
    regras = classificacao.carregar_regras()
    do_csv = set(regras.loc[regras["tipo"] == "nome", "id"])
    assert do_csv == set(classificacao.REGRAS_NOME)


def test_exemplo_de_cada_regra_por_nome_dispara_a_regra():
    regras = classificacao.carregar_regras()
    for _, regra in regras[regras["tipo"] == "nome"].iterrows():
        marca, modelo = regra["exemplo"].split("/", 1)
        disparada = classificacao.propulsao_por_nome(marca, modelo)
        assert disparada == (regra["id"], regra["valor"]), regra["id"]


@pytest.mark.parametrize("marca,modelo", [
    ("VW", "GOL"), ("BMW", "X1"), ("BMW", "320I"), ("VOLVO", "XC40"),
    ("RENAULT", "EXPRESS 1.6"), ("GM", "EQUINOX"),
])
def test_regra_por_nome_nao_dispara_em_nome_comum(marca, modelo):
    assert classificacao.propulsao_por_nome(marca, modelo) is None


def test_todo_sub_segmento_da_fonte_tem_regra_de_carroceria():
    mapa = classificacao.mapa_sub_segmento(classificacao.carregar_regras())
    da_fonte = set(pd.read_csv(config.SUB_SEGMENTOS)["sub_segmento_fonte"])
    assert da_fonte == set(mapa)
    assert set(mapa.values()) <= set(classificacao.CARROCERIAS) | {"(nenhum)"}
    assert mapa["Veículos de Entrada"] == "(nenhum)"


def test_carroceria_ignora_faixa_de_preco_e_marca_divisao():
    mapa = classificacao.mapa_sub_segmento(classificacao.carregar_regras())
    linhas = _painel([
        ("2020-01", "X", "Y", "automoveis", "Veículos de Entrada", 500),
        ("2020-01", "X", "Y", "automoveis", "Hatch Pequenos", 80),
        ("2020-02", "X", "Y", "automoveis", "Sedans Compactos", 20),
    ])
    resultado = classificacao.carroceria_da_fonte(linhas, mapa)
    assert resultado["carroceria"] == "hatch"
    assert resultado["confianca"] == "media"  # sedan tem 20% do classificado
    assert "Fonte divide" in resultado["nota"]


def _modelo(primeiro="2020-01", ultimo="2020-12"):
    return pd.Series({"marca": "X", "modelo": "Y", "segmento": "automoveis",
                      "primeiro_mes": primeiro, "ultimo_mes": ultimo})


def test_vigencias_sobrepostas_sao_recusadas():
    propostas = _propostas([
        ("X", "Y", "automoveis", "2020-01", "2020-06", "flex", "", "", "alta", "", "", ""),
        ("X", "Y", "automoveis", "2020-06", "2020-12", "flex", "", "", "alta", "", "", ""),
    ])
    with pytest.raises(ValueError, match="sobrepostas"):
        classificacao.vigencias_do_modelo(_modelo(), propostas)


def test_mes_com_unidades_fora_das_vigencias_e_recusado():
    propostas = _propostas([
        ("X", "Y", "automoveis", "2020-01", "2020-05", "flex", "", "", "alta", "", "", ""),
        ("X", "Y", "automoveis", "2020-08", "2020-12", "flex", "", "", "alta", "", "", ""),
    ])
    vigencias = classificacao.vigencias_do_modelo(_modelo(), propostas)
    with pytest.raises(ValueError, match="fora de qualquer vigencia"):
        classificacao.conferir_cobertura(_modelo(), vigencias, pd.Series(["2020-03", "2020-06"]))
    # buraco sem unidades e' permitido
    classificacao.conferir_cobertura(_modelo(), vigencias, pd.Series(["2020-03", "2020-09"]))


def test_classificar_combina_as_tres_fontes_e_respeita_o_piso():
    painel = _painel([
        ("2020-01", "JAC", "E-JS1", "automoveis", "Hatch Pequenos", 1500),
        ("2020-01", "VW", "GOL", "automoveis", "Veículos de Entrada", 3000),
        ("2020-01", "ZZ", "RARO", "automoveis", "", 10),
    ])
    propostas = _propostas([
        ("VW", "GOL", "automoveis", "", "", "flex", "hatch", "nacional",
         "alta", "alta", "alta", ""),
        ("JAC", "E-JS1", "automoveis", "", "", "", "", "importado", "", "", "alta", ""),
    ])
    rascunho, fora = classificacao.classificar(
        painel, propostas, classificacao.carregar_regras(), piso=1000)

    assert list(rascunho["modelo"]) == ["GOL", "E-JS1"]  # volume decrescente
    gol, ejs1 = rascunho.iloc[0], rascunho.iloc[1]
    assert gol["carroceria"] == "hatch" and "conhecimento" in gol["fonte_da_proposta"]
    assert ejs1["propulsao_oferecida"] == "bev" and "N01" in ejs1["fonte_da_proposta"]
    assert ejs1["carroceria"] == "hatch" and "sub-segmento" in ejs1["fonte_da_proposta"]
    assert ejs1["eletrificacao"] == "total"
    assert (rascunho["decisao_humana"] == "").all()
    assert list(fora["modelo"]) == ["RARO"]
    assert (fora["classificacao"] == classificacao.NAO_CLASSIFICADO).all()


def test_modelo_sem_proposta_fica_vazio_com_confianca_baixa():
    painel = _painel([("2020-01", "X", "Y", "automoveis", "", 5000)])
    rascunho, _ = classificacao.classificar(
        painel, _propostas([]), classificacao.carregar_regras(), piso=1000)
    linha = rascunho.iloc[0]
    assert linha["propulsao_oferecida"] == linha["carroceria"] == linha["origem_producao"] == ""
    assert linha["confianca"] == "baixa"


def test_proposta_com_valor_fora_da_lista_e_recusada():
    painel = _painel([("2020-01", "X", "Y", "automoveis", "", 5000)])
    propostas = _propostas([
        ("X", "Y", "automoveis", "", "", "flex+mhev", "", "", "media", "", "", ""),
    ])
    with pytest.raises(ValueError, match="mhev"):
        classificacao.classificar(painel, propostas, classificacao.carregar_regras(), piso=1000)


def test_proposta_real_cobre_o_escopo_real():
    """A proposta versionada cobre os modelos acima do piso, e so' eles."""
    if not config.PAINEL.exists():
        pytest.skip("painel.parquet ausente")
    painel = pd.read_parquet(config.PAINEL)
    propostas = pd.read_csv(config.PROPOSTA_CLASSIFICACAO, dtype=str, keep_default_na=False)
    rascunho, fora = classificacao.classificar(
        painel, propostas, classificacao.carregar_regras(), config.PISO_CLASSIFICACAO)
    totais = classificacao.totais_por_modelo(painel)
    acima = set(map(tuple, totais.loc[totais["unidades_totais"] > config.PISO_CLASSIFICACAO,
                                      classificacao.CHAVE].to_numpy()))
    assert set(map(tuple, propostas[classificacao.CHAVE].to_numpy())) == acima
    # as vigencias particionam o volume de cada modelo
    por_modelo = rascunho.groupby(classificacao.CHAVE)["unidades_na_vigencia"].sum()
    assert (por_modelo == rascunho.groupby(classificacao.CHAVE)["unidades_totais"].first()).all()
    assert len(fora) + len(por_modelo) == len(totais)


def test_valor_vazio_no_rascunho_e_sempre_intencional():
    """Vazio so' quando a proposta declarou `baixa` para o atributo.

    Pega esquecimento: o TOYOTA/ETIOS HB, so' em 'Veiculos de Entrada', saiu da
    primeira versao da proposta sem carroceria e sem que ninguem tivesse dito
    'nao sei'. Vazio por omissao e vazio por ignorancia tem de ser distinguiveis.
    """
    if not config.PAINEL.exists():
        pytest.skip("painel.parquet ausente")
    painel = pd.read_parquet(config.PAINEL)
    propostas = pd.read_csv(config.PROPOSTA_CLASSIFICACAO, dtype=str, keep_default_na=False)
    rascunho, _ = classificacao.classificar(
        painel, propostas, classificacao.carregar_regras(), config.PISO_CLASSIFICACAO)
    atributos = {"propulsao_oferecida": "confianca_propulsao",
                 "carroceria": "confianca_carroceria",
                 "origem_producao": "confianca_origem"}
    indice = {tuple(r[c] for c in classificacao.CHAVE): [] for _, r in propostas.iterrows()}
    for _, r in propostas.iterrows():
        indice[tuple(r[c] for c in classificacao.CHAVE)].append(r)
    omissoes = []
    for _, linha in rascunho.iterrows():
        chave = tuple(linha[c] for c in classificacao.CHAVE)
        candidatas = [p for p in indice.get(chave, [])
                      if p["vigencia_inicio"] in ("", linha["vigencia_inicio"])]
        for atributo, confianca in atributos.items():
            if linha[atributo] == "" and not any(p[confianca] == "baixa" for p in candidatas):
                omissoes.append(f"{'/'.join(chave)} {linha['vigencia_inicio']}: {atributo}")
    assert not omissoes, omissoes
