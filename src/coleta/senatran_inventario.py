"""Inventario dos arquivos de frota da Senatran: pagina de cada ano -> links por mes.

A Senatran publica uma pagina por ano (2013 a hoje) e, de 2000 a 2012, um zip anual.
Os nomes dos arquivos mudam de ano para ano (e as vezes de mes para mes); a
classificacao abaixo e' por padrao de nome, e todo link que nao casa com nenhum
padrao conhecido fica de fora com motivo -- nao se adivinha.
"""

from __future__ import annotations

import re
from urllib.parse import unquote

import requests

from comum import config
from comum.energia import MESES_ABREV, MESES_PT, sem_acento

BASE = "https://www.gov.br"
PAGINA_PRINCIPAL = (BASE + "/transportes/pt-br/assuntos/transito/conteudo-Senatran/"
                    "estatisticas-frota-de-veiculos-senatran")
PAGINA_ANO = BASE + "/transportes/pt-br/assuntos/transito/conteudo-Senatran/frota-de-veiculos-{ano}"
# 2007 a 2012: a pagina principal aponta por resolveuid para o zip do ano
ZIPS_ANUAIS = {
    2003: "/transportes/pt-br/assuntos/transito/arquivos-senatran/estatisticas/renavam/2003/frota2003.zip",
    2004: "/transportes/pt-br/assuntos/transito/arquivos-senatran/estatisticas/renavam/2004/frota2004.zip",
    2005: "/transportes/pt-br/assuntos/transito/arquivos-senatran/estatisticas/renavam/2005/frota2005.zip",
    2006: "/transportes/pt-br/assuntos/transito/arquivos-senatran/estatisticas/renavam/2006/frota2006.zip",
    2007: "/transportes/resolveuid/7daa0caf197a472790fd889f6b83e094",
    2008: "/transportes/resolveuid/67ef620d64db451fa3b5a444f0186903",
    2009: "/transportes/resolveuid/aaf9c20bff284498a7c8913e124e46f0",
    2010: "/transportes/resolveuid/669ddde7a6454d2ab00837c3d8be60ab",
    2011: "/transportes/resolveuid/f52a3d992271478bae4832d588ea4b20",
    2012: "/transportes/resolveuid/9643e62b2c8e45d298642929490dd335",
}
EXCLUIR = ("marca", "cep", "_cor_", "_cor", "ecor", "ocor", "potencia", "restric", "eixo",
           "anofab", "ano_fab", "ano_de_fab", "anodefab", "ano_modelo", "anomodelo",
           "anofabr", "demanda")


def copia(nome: str) -> bool:
    """`copy_of_`, `copy2_of_`...: copia que o portal cria ao republicar. As vezes e' o
    unico arquivo do mes; so' se usa quando nao ha' o original do mesmo mes e tipo."""
    return bool(re.match(r"copy\d*_of_", sem_acento(unquote(nome)).lower()))


def tipo_do_arquivo(nome: str) -> str | None:
    n = sem_acento(unquote(nome)).lower()
    n = re.sub(r"^copy\d*_of_", "", n)
    n = re.sub(r"[-. ]", "_", n)
    if "combust" in n:
        return "municipio_combustivel"
    if any(e in n for e in EXCLUIR):
        return None
    if "munic" in n or "municpio" in n:
        return "municipio_tipo"
    if re.search(r"uf.?e.?tipo|uf.?tipo|regioes.?tipo|reg.?uf.?tipo|uftipo|tipoveic|tipodeve",
                 n):
        return "uf_tipo"
    return None


def mes_do_link(caminho: str, ano: int) -> int | None:
    """Mes pelo nome do arquivo ou pela pasta (`.../2020/abril/...`)."""
    t = sem_acento(unquote(caminho)).lower().replace("maro", "marco")  # "Março" sem o c cedilha
    for parte in reversed(t.split("/")):
        for nome, numero in MESES_PT.items():
            if nome in parte:
                return numero
        m = re.search(r"(?<![a-z])(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)(?![a-z])"
                      r"|(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[-_.]?\d{2,4}"
                      r"|\d{2}(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)", parte)
        if m:
            return MESES_ABREV[next(g for g in m.groups() if g)]
    return None


def links_do_ano(ano: int) -> list[dict]:
    r = requests.get(PAGINA_ANO.format(ano=ano), headers={"User-Agent": config.USER_AGENT},
                     timeout=120)
    r.raise_for_status()
    saida = []
    for href in sorted(set(re.findall(r'href="([^"]+/@@download/file)"', r.text))):
        caminho = href.replace("/@@download/file", "")
        if caminho.startswith("http"):
            caminho = caminho.split("gov.br", 1)[1]
        nome = caminho.rsplit("/", 1)[-1]
        saida.append({"ano": ano, "arquivo": nome, "url": BASE + caminho + "/@@download/file",
                      "tipo": tipo_do_arquivo(nome), "mes": mes_do_link(caminho, ano),
                      "copia": copia(nome)})
    return saida
