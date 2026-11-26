#!/usr/bin/env python3
"""MCTI: fator medio mensal de emissao de CO2 da eletricidade do SIN (inventarios).

Pagina: https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/sirene/dados-e-ferramentas/
fatores-de-emissao, secao "Fator medio - Inventarios corporativos". O link da
secao (resolveuid) leva a uma planilha unica com todos os anos, de 2006 ao ultimo
mes publicado, mensal e anual. O nome do arquivo muda a cada atualizacao
(`Inventario_2026_janout.xlsx` em 26/11/2026): o script guarda pelo nome final
da URL, e o manifesto registra a URL de entrada e a final.

Arquivo pequeno (~12 kB): vai para o git como veio, em `dados/bruto/mcti_fator/`.

Uso:
    python src/coleta/mcti_fator.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coleta import comum_coleta as cc  # noqa: E402
from comum import config  # noqa: E402

FONTE = "mcti_fator"
PAGINA = ("https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/sirene/dados-e-ferramentas/"
          "fatores-de-emissao")
URL_SECAO = PAGINA + "/resolveuid/53cfffc73aad4649940c1812315f7b7f"


def main() -> int:
    resposta = requests.get(URL_SECAO, headers={"User-Agent": config.USER_AGENT}, timeout=120)
    resposta.raise_for_status()
    if not resposta.content.startswith(b"PK"):
        raise RuntimeError("a resposta nao e' uma planilha xlsx (bloqueio ou mudanca de pagina)")
    nome = resposta.url.rsplit("/", 1)[-1]
    manifesto = cc.ler_manifesto(FONTE)
    cc.registrar(FONTE, manifesto, nome, resposta.url, resposta.content,
                 observacao=f"link da secao 'Fator medio - Inventarios corporativos' "
                            f"({URL_SECAO}) na pagina {PAGINA}")
    print(f"{nome}: {len(resposta.content)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
