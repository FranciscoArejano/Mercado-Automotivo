"""Tipo da fonte de origem, pelo dominio da URL.

Verificado nao e' o mesmo que forte: a citacao de um agregador pode ser real e
ainda assim fraca para derrubar uma proposta. As regras de adjudicacao de origem
(O1, O2, O3) olham o tipo da fonte:

- `oficial`: site ou comunicado da montadora, orgao de governo, entidade setorial;
- `imprensa_especializada`: cobertura da industria automotiva;
- `imprensa_geral`: jornais e revistas de cobertura geral;
- `blog_agregador`: sites de entusiasta, agregadores, blogs de marca.

As duas primeiras sao fortes. O mapeamento dominio -> tipo esta' em
`config/tipo_fonte_dominio.csv`; e' julgamento, e o pesquisador edita. A coluna
`tipo_fonte` de `dados/referencia/origem_fontes.csv` e' derivada dele (do dominio
de `fonte_primaria`, quando a materia repassa outro veiculo) -- o teste
confere que esta' em dia, e `python src/ferramentas/origem_fonte.py --tipos`
regrava.
"""

from __future__ import annotations

from urllib.parse import urlparse

import pandas as pd

from . import config

TIPOS = ("oficial", "imprensa_especializada", "imprensa_geral", "blog_agregador")
FORTES = frozenset({"oficial", "imprensa_especializada"})


def dominio(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def carregar_mapa() -> dict[str, str]:
    """dominio -> tipo, de `config/tipo_fonte_dominio.csv`."""
    tabela = pd.read_csv(config.TIPO_FONTE_DOMINIO, dtype=str, keep_default_na=False)
    return dict(zip(tabela["dominio"], tabela["tipo_fonte"]))


def tipo_de(url: str, mapa: dict[str, str]) -> str:
    """Tipo do dominio mais especifico que cobre a URL; vazio se nenhum cobre."""
    host = dominio(url)
    candidatos = [d for d in mapa if host == d or host.endswith("." + d)]
    return mapa[max(candidatos, key=len)] if candidatos else ""


def tipo_da_citacao(url: str, primaria: str, mapa: dict[str, str]) -> str:
    """Tipo de uma citacao. Materia que repassa outro veiculo (`primaria`, o dominio
    dele) vale o tipo do veiculo original: revista forte repassando blog e' blog."""
    return tipo_de(f"https://{primaria}/", mapa) if primaria else tipo_de(url, mapa)


def com_tipo(fontes: pd.DataFrame, mapa: dict[str, str]) -> pd.DataFrame:
    """As fontes com a coluna `tipo_fonte` (re)calculada, logo depois da URL."""
    saida = fontes.drop(columns=["tipo_fonte"], errors="ignore")
    primarias = saida["fonte_primaria"] if "fonte_primaria" in saida else [""] * len(saida)
    posicao = list(saida.columns).index("origem_fonte_url") + 1
    saida.insert(posicao, "tipo_fonte", [tipo_da_citacao(u, p, mapa) for u, p in
                                         zip(saida["origem_fonte_url"], primarias)])
    return saida
