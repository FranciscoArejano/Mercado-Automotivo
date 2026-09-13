"""Recuperacao de um mes cujo informe nao e' legivel (ESPEC.md sec.9.2).

Isto **nao** e' interpolacao, media nem estimativa -- essas seguem proibidas.
E' leitura de uma segunda publicacao do mesmo numero pela mesma fonte: cada
informe traz, ao lado do mes de referencia, a coluna do **mes anterior**, tanto
na tabela por modelo quanto no Resumo Mensal. Quando o informe de M nao pode
ser lido, o informe de M+1 republica M inteiro.

Toda linha assim recuperada sai marcada com `origem_tabela='mes_anterior'` e
`metodo_extracao='reconstruido'`, e o mes fica registrado como
`ok_reconstruido` em `meses_extraidos.csv`. Nada disso se confunde com uma
leitura direta.

Confirmacao independente: onde M-1 tambem existe, o acumulado da' o mesmo
numero por outro caminho -- `acumulado(M+1) - unidades(M+1) - acumulado(M-1)`.
As duas rotas sao comparadas e a divergencia e' reportada.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from . import config, periodo


@dataclass
class Reconstrucao:
    mes: str
    mes_fonte: str
    linhas: list[dict] = field(default_factory=list)
    totais: list[dict] = field(default_factory=list)
    conferidos: int = 0
    divergentes: int = 0
    divergencia_absoluta: float = 0.0
    divergencia_liquida: float = 0.0
    observacoes: list[str] = field(default_factory=list)


def _ler(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as fluxo:
        return list(csv.DictReader(fluxo))


def _numero(texto: str) -> float | None:
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def reconstruir(mes: str) -> Reconstrucao | None:
    """Recupera o mes `mes` a partir do informe do mes seguinte."""
    seguinte = periodo.de_indice(periodo.para_indice(mes) + 1)
    anterior = periodo.de_indice(periodo.para_indice(mes) - 1)
    linhas_seguinte = [
        l for l in _ler(config.DIR_EXTRACAO / f"{seguinte}.csv")
        if l.get("origem_tabela") == "sub_segmento"
    ]
    if not linhas_seguinte:
        return None

    resultado = Reconstrucao(mes=mes, mes_fonte=seguinte)

    # Rota de confirmacao: acumulado de M-1, quando existe.
    acumulado_anterior: dict[tuple[str, str], float] = {}
    for linha in _ler(config.DIR_EXTRACAO / f"{anterior}.csv"):
        if linha.get("origem_tabela") != "sub_segmento":
            continue
        valor = _numero(linha.get("unidades_acumulado", ""))
        if valor is None:
            continue
        chave = (linha["segmento"], linha["nome_completo_fonte"])
        acumulado_anterior[chave] = acumulado_anterior.get(chave, 0.0) + valor

    # Rota A (a que vira dado): coluna de mes anterior, linha a linha.
    # Rota B (a que confere): acumulado, agregado por modelo -- tem de ser
    # agregado, porque um modelo pode ocupar dois sub-segmentos no mesmo mes e
    # o acumulado de M-1 vem somado.
    rota_mes_anterior: dict[tuple[str, str], float] = {}
    rota_acumulado: dict[tuple[str, str], float] = {}

    for linha in linhas_seguinte:
        unidades = _numero(linha.get("unidades_mes_anterior", ""))
        if unidades is None:
            continue
        acumulado_seguinte = _numero(linha.get("unidades_acumulado", ""))
        unidades_seguinte = _numero(linha.get("unidades_mes", ""))
        acumulado = (
            acumulado_seguinte - unidades_seguinte
            if acumulado_seguinte is not None and unidades_seguinte is not None
            else None
        )
        chave = (linha["segmento"], linha["nome_completo_fonte"])
        rota_mes_anterior[chave] = rota_mes_anterior.get(chave, 0.0) + unidades
        if acumulado is not None:
            rota_acumulado[chave] = rota_acumulado.get(chave, 0.0) + acumulado

        resultado.linhas.append({
            "mes": mes,
            "segmento": linha["segmento"],
            "origem_tabela": "mes_anterior",
            "sub_segmento_fonte": linha.get("sub_segmento_fonte", ""),
            "posicao_fonte": linha.get("posicao_fonte", ""),
            "nome_completo_fonte": linha["nome_completo_fonte"],
            "unidades_mes": f"{unidades:.0f}",
            "unidades_mes_anterior": "",
            "unidades_acumulado": "" if acumulado is None else f"{acumulado:.0f}",
            "participacao_pct": "",
            "pagina": linha.get("pagina", ""),
            "metodo_extracao": "reconstruido",
            "arquivo_origem": linha.get("arquivo_origem", ""),
        })

    for chave, acumulado in rota_acumulado.items():
        if chave not in acumulado_anterior:
            continue
        por_acumulado = acumulado - acumulado_anterior[chave]
        resultado.conferidos += 1
        diferenca = por_acumulado - rota_mes_anterior.get(chave, 0.0)
        if abs(diferenca) > 0.5:
            resultado.divergentes += 1
            resultado.divergencia_absoluta += abs(diferenca)
        resultado.divergencia_liquida += diferenca

    totais_seguinte = _ler(config.DIR_PROCESSADO / "totais" / f"{seguinte}.csv")
    for linha in totais_seguinte:
        publicado = _numero(linha.get("total_publicado_mes_anterior", ""))
        resultado.totais.append({
            "mes": mes,
            "segmento": linha["segmento"],
            "total_publicado": "" if publicado is None else f"{publicado:.0f}",
            "total_publicado_mes_anterior": "",
            "origem": f"coluna de mes anterior do informe de {seguinte}",
            "arquivo_origem": linha.get("arquivo_origem", ""),
            "edicao": linha.get("edicao", ""),
        })

    resultado.observacoes.append(
        f"{len(resultado.linhas)} linhas recuperadas do informe de {seguinte}"
    )
    if resultado.conferidos:
        resultado.observacoes.append(
            f"rota do acumulado confere {resultado.conferidos - resultado.divergentes} de "
            f"{resultado.conferidos} modelos; diferenca absoluta "
            f"{resultado.divergencia_absoluta:.0f} unidades, liquida "
            f"{resultado.divergencia_liquida:+.0f}"
        )
    return resultado
