#!/usr/bin/env python3
"""Compara a participacao dos eletrificados publicada pela ABVE com o piso e o teto
da classificacao, ano a ano. So' registra e compara: nao constroi dimensao.

Entrada: `dados/referencia/abve_serie_anual.csv` (unidades de eletrificados leves
por ano, com o trecho copiado de cada comunicado guardado),
`saidas/eletrificacao_banda.csv` (piso e tetos, gravados pela etapa 11) e
`saidas/cobertura.csv` (total publicado pela fonte, mes a mes, para o
denominador).

A participacao da ABVE e' recalculada sobre o total publicado pela Fenabrave para
automoveis e comerciais leves nos meses do ano (`saidas/cobertura.csv`), o mesmo
mercado que a ABVE cita; a participacao que o comunicado publica fica ao lado,
e a diferenca entre as duas e' sinalizada.
A banda vem de `saidas/eletrificacao_banda.csv`, nas leituras longa e curta. A
ABVE muda de definicao, entao cada ano usa o teto da sua (rodada propulsao e
comex): 2024, que inclui MHEV, o `teto`; os demais, sem MHEV, o `teto_sem_mhev`.
A ABVE deve cair entre o menor piso e o maior teto da definicao dela, entre as
duas leituras. A posicao em relacao ao `teto_estrito` (sem os modelos so' leves
ou indefinidos) vai ao lado: acima dele, ha' hibrido pleno entre os indefinidos.

Saida: `saidas/abve_comparacao.csv`.

Uso:
    python src/ferramentas/abve_comparacao.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import config  # noqa: E402

ABVE = config.DIR_DADOS / "referencia" / "abve_serie_anual.csv"
SAIDA = config.DIR_SAIDAS / "abve_comparacao.csv"


def _numero(texto: str) -> float | None:
    return float(texto.replace(",", ".")) if texto else None


ANOS_COM_MHEV = {2024}  # definicao da ABVE que inclui MHEV


def comparar() -> pd.DataFrame:
    abve = pd.read_csv(ABVE, dtype=str, keep_default_na=False)
    banda = pd.read_csv(config.ELETRIFICACAO_BANDA)
    cobertura = pd.read_csv(config.DIR_SAIDAS / "cobertura.csv")
    cobertura = cobertura[cobertura["segmento"].isin(["automoveis", "comerciais_leves"])]
    linhas = []
    for _, r in abve.iterrows():
        ano, unidades, meses = int(r["ano"]), int(r["eletrificados_leves"]), int(r["meses"])
        do_ano = cobertura[cobertura["mes"].between(f"{ano}-01", f"{ano}-{meses:02d}")]
        mercado = int(do_ano["total_publicado"].sum())
        publicada = _numero(r["participacao_publicada_pct"])
        if publicada is None and r["mercado_leves"]:
            publicada = round(100 * unidades / int(r["mercado_leves"]), 2)
        pct = 100 * unidades / mercado
        linha = {"ano": ano, "meses": meses, "abve_unidades": unidades,
                 "mercado_fenabrave": mercado, "abve_pct": round(pct, 2),
                 "abve_pct_publicada": publicada if publicada is not None else "",
                 "publicada_nao_fecha": publicada is not None and abs(publicada - pct) > 0.5}
        do_ano_banda = banda[banda["ano"] == ano].set_index("leitura")
        if len(do_ano_banda):
            teto = "teto" if ano in ANOS_COM_MHEV else "teto_sem_mhev"
            linha.update({
                "teto_da_definicao": teto,
                "piso_min": do_ano_banda["piso"].min(),
                "teto_max": do_ano_banda[teto].max(),
                "teto_estrito_longa": do_ano_banda.loc["longa", "teto_estrito"],
                "teto_estrito_curta": do_ano_banda.loc["curta", "teto_estrito"]})
            linha["dentro"] = linha["piso_min"] <= linha["abve_pct"] <= linha["teto_max"]
            linha["acima_do_teto_estrito"] = linha["abve_pct"] > do_ano_banda[
                "teto_estrito"].max()
        linhas.append(linha)
    return pd.DataFrame(linhas)


def main() -> int:
    tabela = comparar()
    tabela.to_csv(SAIDA, index=False)
    print(tabela.to_string(index=False))
    fora = tabela[tabela.get("dentro", pd.Series(dtype=bool)) == False]  # noqa: E712
    if len(fora):
        print(f"\n{len(fora)} anos com a ABVE fora do intervalo piso-teto", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
