"""Validacao de regras.csv (sec.6). O codigo le'; o humano escreve."""

import csv

import pytest

from comum import config, regras as mod_regras
from comum.log import ErroMetodologico


def escrever(tmp_path, linhas, monkeypatch):
    caminho = tmp_path / "regras.csv"
    with caminho.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.writer(fluxo)
        escritor.writerow(mod_regras.CAMPOS)
        escritor.writerows(linhas)
    monkeypatch.setattr(config, "REGRAS", caminho)
    return caminho


def test_arquivo_ausente_e_criado_vazio(tmp_path, monkeypatch):
    caminho = tmp_path / "regras.csv"
    monkeypatch.setattr(config, "REGRAS", caminho)
    assert mod_regras.carregar() == []
    assert caminho.exists()
    assert caminho.read_text(encoding="utf-8").strip() == ",".join(mod_regras.CAMPOS)


def test_rebatismo_valido_resolve_a_cadeia(tmp_path, monkeypatch):
    escrever(tmp_path, [
        ["rebatismo", "GM", "PRISMA", "ONIX PLUS", "2019-09", "Prisma vira Onix Plus"],
        ["rebatismo", "GM", "ONIX PLUS", "ONIX SEDAN", "2024-01", ""],
    ], monkeypatch)
    regras = mod_regras.carregar()
    destino, datas = mod_regras.resolver_destino(("GM", "PRISMA"), regras)
    assert destino == ("GM", "ONIX SEDAN")
    assert datas == ["2019-09", "2024-01"]


def test_rebatismo_sem_data_para(tmp_path, monkeypatch):
    escrever(tmp_path, [["rebatismo", "GM", "PRISMA", "ONIX PLUS", "", ""]], monkeypatch)
    with pytest.raises(ErroMetodologico, match="data_evento"):
        mod_regras.carregar()


def test_tipo_desconhecido_para(tmp_path, monkeypatch):
    escrever(tmp_path, [["fundir", "GM", "PRISMA", "ONIX PLUS", "2019-09", ""]], monkeypatch)
    with pytest.raises(ErroMetodologico, match="tipo"):
        mod_regras.carregar()


def test_ciclo_de_rebatismo_para(tmp_path, monkeypatch):
    escrever(tmp_path, [
        ["rebatismo", "GM", "A", "B", "2019-01", ""],
        ["rebatismo", "GM", "B", "A", "2020-01", ""],
    ], monkeypatch)
    with pytest.raises(ErroMetodologico, match="ciclo"):
        mod_regras.carregar()


def test_duas_fusoes_para_a_mesma_origem_param(tmp_path, monkeypatch):
    escrever(tmp_path, [
        ["rebatismo", "GM", "A", "B", "2019-01", ""],
        ["rebatismo", "GM", "A", "C", "2020-01", ""],
    ], monkeypatch)
    with pytest.raises(ErroMetodologico, match="mesma"):
        mod_regras.carregar()


def test_data_de_evento_malformada_para(tmp_path, monkeypatch):
    escrever(tmp_path, [["rebatismo", "GM", "A", "B", "set/2019", ""]], monkeypatch)
    with pytest.raises(ErroMetodologico):
        mod_regras.carregar()


def test_tipos_que_nao_fundem_nao_mudam_o_destino(tmp_path, monkeypatch):
    escrever(tmp_path, [
        ["substituicao", "GM", "CELTA", "ONIX", "2016-01", "plataforma nova"],
        ["reclassificacao", "GM", "ONIX", "ONIX PLUS", "2019-09", "desdobramento"],
        ["ignorar", "GM", "X", "Y", "", "analisado e descartado"],
    ], monkeypatch)
    regras = mod_regras.carregar()
    assert len(regras) == 3
    assert mod_regras.resolver_destino(("GM", "CELTA"), regras) == (("GM", "CELTA"), [])
    assert mod_regras.resolver_destino(("GM", "ONIX"), regras) == (("GM", "ONIX"), [])
