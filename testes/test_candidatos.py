"""Detectores da sec.5 e o tratamento de censura."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import etapa04_candidatos as etapa  # noqa: E402


def _grade(series: dict[tuple[str, str, str], list[float]], meses: list[str]) -> pd.DataFrame:
    quadro = pd.DataFrame(series).T.astype("float64")
    quadro.columns = meses
    quadro.index = pd.MultiIndex.from_tuples(quadro.index, names=["marca", "modelo", "segmento"])
    return quadro


def _meses(n: int, inicio_ano: int = 2014) -> list[str]:
    saida, ano, mes = [], inicio_ano, 1
    for _ in range(n):
        saida.append(f"{ano:04d}-{mes:02d}")
        mes += 1
        if mes == 13:
            ano, mes = ano + 1, 1
    return saida


def test_passagem_de_bastao_acha_o_sucessor_de_um_modelo_censurado_a_esquerda():
    """Prisma -> Onix Plus: A esta' vivo no primeiro mes da amostra.

    Censura a' esquerda invalida a *entrada* de A, nao a sua *saida*. Excluir A
    do teste por isso esconderia justamente o caso que a ESPEC diz importar mais.
    """
    meses = _meses(36)
    antigo = [1000.0] * 24 + [10.0] * 12          # vivo desde o inicio, sai no mes 24
    novo = [0.0] * 22 + [900.0] * 14              # entra no mes 23
    largo = _grade({("GM", "ANTIGO", "automoveis"): antigo,
                    ("GM", "NOVO", "automoveis"): novo}, meses)
    fichas = etapa._fichas(largo, meses, 0.05)
    assert bool(fichas.set_index("modelo").loc["ANTIGO", "censura_esquerda"])

    pares = etapa._passagem_de_bastao(fichas, largo, meses, {})
    achado = [p for p in pares if p["modelo_origem"] == "ANTIGO" and p["modelo_destino"] == "NOVO"]
    assert achado, "sucessor de modelo censurado a' esquerda tem de aparecer"


def test_entrada_no_primeiro_mes_nao_vira_candidato_a_sucessor():
    """A armadilha do Agile: quem 'entra' no primeiro mes nao entrou coisa alguma."""
    meses = _meses(36)
    saindo = [0.0] * 6 + [1000.0] * 12 + [10.0] * 18   # entra no mes 7, sai por volta do 18
    sempre_vivo = [800.0] * 36                          # 'entra' no primeiro mes: artefato
    largo = _grade({("GM", "SAINDO", "automoveis"): saindo,
                    ("GM", "SEMPRE", "automoveis"): sempre_vivo}, meses)
    fichas = etapa._fichas(largo, meses, 0.05)
    pares = etapa._passagem_de_bastao(fichas, largo, meses, {})
    assert not [p for p in pares if p["modelo_destino"] == "SEMPRE"]


def test_saida_no_ultimo_mes_nao_conta_como_saida():
    meses = _meses(36)
    vivo = [500.0] * 36
    outro = [0.0] * 30 + [400.0] * 6
    largo = _grade({("GM", "VIVO", "automoveis"): vivo,
                    ("GM", "OUTRO", "automoveis"): outro}, meses)
    fichas = etapa._fichas(largo, meses, 0.05)
    assert bool(fichas.set_index("modelo").loc["VIVO", "censura_direita"])
    pares = etapa._passagem_de_bastao(fichas, largo, meses, {})
    assert not [p for p in pares if p["modelo_origem"] == "VIVO"]


def test_mesmo_nome_em_dois_segmentos_nao_e_par_de_sucessao():
    meses = _meses(36)
    largo = _grade({
        ("RENAULT", "KWID", "automoveis"): [1000.0] * 24 + [5.0] * 12,
        ("RENAULT", "KWID", "comerciais_leves"): [0.0] * 22 + [700.0] * 14,
    }, meses)
    fichas = etapa._fichas(largo, meses, 0.05)
    assert not etapa._passagem_de_bastao(fichas, largo, meses, {})


def test_queda_abrupta_exige_queda_sem_declinio_previo():
    meses = _meses(24)
    # cai de 1000 para 50 num mes, sem vir caindo antes
    abrupta = [1000.0] * 12 + [50.0] * 12
    # desce devagar: nao e' queda abrupta
    suave = [1000.0, 900.0, 800.0, 700.0, 600.0, 500.0, 400.0, 300.0, 200.0,
             150.0, 100.0, 80.0, 60.0, 40.0, 30.0, 20.0, 15.0, 10.0, 8.0, 6.0,
             4.0, 3.0, 2.0, 1.0]
    largo = _grade({("X", "ABRUPTA", "automoveis"): abrupta,
                    ("X", "SUAVE", "automoveis"): suave}, meses)
    quedas = etapa._quedas_abruptas(largo, meses)
    assert quedas.get(("X", "ABRUPTA", "automoveis")) == ["2015-01"]
    assert ("X", "SUAVE", "automoveis") not in quedas


def test_similaridade_de_nome_nao_e_usada():
    """A sec.5 proibe casamento por nome; o modulo nao pode nem importar isso."""
    fonte = Path(etapa.__file__).read_text(encoding="utf-8")
    for proibido in ("difflib", "SequenceMatcher", "fuzz", "levenshtein", "rapidfuzz"):
        assert proibido not in fonte
