#!/usr/bin/env python3
"""Compara a participacao dos eletrificados publicada pela ABVE com o piso e o teto
da classificacao, ano a ano. So' registra e compara: nao constroi dimensao.

Entrada: `dados/referencia/abve_serie_anual.csv` (unidades de eletrificados leves
por ano, com o trecho copiado de cada comunicado guardado),
`saidas/classificacao_uso_teste.csv` (participacao de cada nivel de
eletrificacao, gravada pela etapa 11) e `saidas/cobertura.csv` (total publicado
pela fonte, mes a mes, para o denominador).

A participacao da ABVE e' recalculada sobre o total publicado pela Fenabrave para
automoveis e comerciais leves nos meses do ano (`saidas/cobertura.csv`), o mesmo
mercado que a ABVE cita; a participacao que o comunicado publica fica ao lado,
e a diferenca entre as duas e' sinalizada.
O piso e' `total` (modelos so' com tracao eletrica) e o teto, `total + parcial`
(todas as unidades dos modelos que oferecem algum tipo eletrificado); a ABVE
conta unidades eletrificadas, entao deve cair entre os dois. Fora disso e'
sinal de problema de um lado ou do outro.

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


def comparar() -> pd.DataFrame:
    abve = pd.read_csv(ABVE, dtype=str, keep_default_na=False)
    uso = pd.read_csv(config.CLASSIFICACAO_USO_TESTE)
    largura = {c: uso.pivot(index="ano", columns="nivel", values=c)
               for c in ("pct_pela_vigencia", "pct_anual")}
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
        if ano in largura["pct_anual"].index:
            anual, vig = largura["pct_anual"].loc[ano], largura["pct_pela_vigencia"].loc[ano]
            linha.update({
                "piso_total": anual["total"],
                "teto_total_mais_parcial": round(anual["total"] + anual["parcial"], 2),
                "teto_antes_pela_vigencia": round(vig["total"] + vig["parcial"], 2)})
            linha["dentro"] = (linha["piso_total"] <= linha["abve_pct"]
                               <= linha["teto_total_mais_parcial"])
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
