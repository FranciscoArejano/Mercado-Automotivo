"""Pisos de volume nas taxas de entrada e saida (rodada 2, sec.1)."""

import pandas as pd

from comum import rotatividade


def _por_modelo(linhas):
    quadro = pd.DataFrame(linhas)
    quadro["ano"] = quadro["mes_ref"].str.slice(0, 4).astype(int)
    return quadro


def _linha(marca, modelo, mes, unidades, segmento="automoveis"):
    return {"marca": marca, "modelo": modelo, "segmento": segmento,
            "mes_ref": mes, "unidades": unidades}


def test_volume_por_modelo_soma_o_periodo_inteiro():
    pm = _por_modelo([
        _linha("GM", "ONIX", "2020-01", 1000),
        _linha("GM", "ONIX", "2020-02", 1500),
        _linha("X", "FANTASMA", "2020-03", 1),
    ])
    volume = rotatividade.volume_por_modelo(pm)
    assert volume[("GM", "ONIX", "automoveis")] == 2500
    assert volume[("X", "FANTASMA", "automoveis")] == 1


def test_distribuicao_separa_fantasma_de_modelo():
    pm = _por_modelo(
        [_linha("X", f"F{i}", "2020-01", 1) for i in range(5)]
        + [_linha("GM", "ONIX", "2020-01", 50_000)]
    )
    volume = rotatividade.volume_por_modelo(pm)
    tabela = rotatividade.distribuicao(volume, ((0, 10), (11, None)))
    assert tabela.iloc[0]["modelos"] == 5
    assert tabela.iloc[0]["unidades"] == 5
    # cinco de seis modelos, e quase nada do volume
    assert tabela.iloc[0]["pct_dos_modelos"] > 80
    assert tabela.iloc[0]["pct_das_unidades"] < 0.1


def test_acima_do_piso_corta_numerador_e_denominador():
    pm = _por_modelo([
        _linha("GM", "ONIX", "2020-01", 5_000),
        _linha("X", "FANTASMA", "2020-01", 1),
    ])
    volume = rotatividade.volume_por_modelo(pm)
    assert len(rotatividade.acima_do_piso(pm, volume, 0)) == 2
    restrito = rotatividade.acima_do_piso(pm, volume, 100)
    assert len(restrito) == 1
    assert restrito.iloc[0]["modelo"] == "ONIX"


def test_participacao_dos_pequenos_mede_o_ruido():
    pm = _por_modelo([
        _linha("GM", "ONIX", "2020-01", 5_000),
        _linha("X", "FANTASMA", "2020-06", 1),
    ])
    volume = rotatividade.volume_por_modelo(pm)
    ciclos = pd.DataFrame([
        {"marca": "GM", "modelo": "ONIX", "segmento": "automoveis",
         "entrada": "2020-01", "saida": "2020-12",
         "censura_esquerda": False, "censura_direita": False},
        {"marca": "X", "modelo": "FANTASMA", "segmento": "automoveis",
         "entrada": "2020-06", "saida": "2020-06",
         "censura_esquerda": False, "censura_direita": False},
    ])
    tabela = rotatividade.participacao_dos_pequenos(ciclos, volume, 100)
    linha = tabela.iloc[0]
    assert linha["entradas"] == 2 and linha["entradas_ate_100"] == 1
    assert linha["pct_entradas_ate_100"] == 50


def test_piso_zero_nao_muda_nada():
    pm = _por_modelo([_linha("GM", "ONIX", "2020-01", 1)])
    volume = rotatividade.volume_por_modelo(pm)
    assert rotatividade.acima_do_piso(pm, volume, 0).equals(pm)
