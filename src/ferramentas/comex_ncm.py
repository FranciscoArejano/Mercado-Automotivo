#!/usr/bin/env python3
"""Gera `config/ncm_veiculos.csv` a partir do bruto do Comex Stat.

Uma linha por NCM de 8 digitos encontrada nas respostas guardadas: descricao
oficial e unidade estatistica (`tables/ncm`), primeiro e ultimo mes com dado, e
as duas colunas decididas por regra (`comum/comex.py`):

- `grupo_propulsao_ncm`, pelo texto da subposicao (`GRUPO_POR_PREFIXO`), com
  `sem_separacao` para NCM que so' existiu antes das subposicoes de
  eletrificados da sua posicao (`separa_eletrificados_desde`);
- `leve` (so' 8704): `sim` quando a descricao limita o peso em carga maxima a 5 t;
- `agregado_carros`: `sim` para 8703 menos 8703.10 (neve, golfe e semelhantes) e
  para o 8704 leve -- o agregado dos uso-testes.

A coluna `criterio` diz a regra de cada linha. A etapa 12 confere que a tabela
versionada continua batendo com o bruto (NCM, unidade, periodo).

Uso:
    python src/ferramentas/comex_ncm.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import comex, config  # noqa: E402


def criterio(linha) -> str:
    partes = []
    if linha["grupo_propulsao_ncm"] == "sem_separacao":
        partes.append(f"so' existiu antes de {linha['separa_eletrificados_desde']}, quando a "
                      "posicao ainda nao separava eletrificado")
    else:
        partes.append(f"grupo pelo texto da subposicao {linha['ncm'][:4]}."
                      f"{linha['ncm'][4:6]}")
    if linha["ncm"].startswith("8704") and linha["grupo_propulsao_ncm"] == "hev":
        partes.append("o texto nao separa recarga externa: `hev` inclui o plug-in")
    if linha["leve"]:
        partes.append({"sim": "leve: peso em carga maxima ate' 5 t na descricao",
                       "nao": "nao leve: acima de 5 t ou dumper",
                       "indeterminado": "leve indeterminado: descricao sem limite de peso"}[
                           linha["leve"]])
    if linha["agregado_carros"] != "sim":
        partes.append("fora do agregado de carros"
                      + (": neve, golfe e semelhantes" if linha["ncm"].startswith("870310")
                         else ""))
    return "; ".join(partes)


def main() -> int:
    com_pais, _ = comex.ler_bruto()
    tabela = comex.tabela_de_ncms(com_pais, comex.unidades_das_ncms())
    tabela["criterio"] = tabela.apply(criterio, axis=1)
    tabela.to_csv(config.NCM_VEICULOS, index=False)
    print(tabela[["ncm", "unidade_estatistica", "primeiro_mes", "ultimo_mes", "leve",
                  "grupo_propulsao_ncm"]].to_string(index=False))
    print(f"gravado {config.NCM_VEICULOS.relative_to(config.RAIZ)}: {len(tabela)} NCMs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
