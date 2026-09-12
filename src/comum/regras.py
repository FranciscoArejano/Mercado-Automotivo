"""Leitura e validacao de regras.csv (ESPEC.md sec.6).

    tipo, marca, modelo_origem, modelo_destino, data_evento, observacao

`tipo` em {rebatismo, reclassificacao, substituicao, ignorar}:

- `rebatismo`       funde as series de origem e destino numa serie continua e
                    registra a data do evento em campo proprio (D2);
- `reclassificacao` marca desdobramento de familia (D1) e suprime a contagem de
                    entrada/saida naquele ponto -- nao funde nada;
- `substituicao`    produto novo em plataforma nova: nao funde (D2);
- `ignorar`         par analisado e descartado.

O codigo le'; o humano escreve. Arquivo ausente e' criado com cabecalho e zero
linhas, e o pipeline segue sem fundir nada (sec.3). Regra malformada para a
execucao: preferimos parar a fundir errado (sec.1.2).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

from . import config, periodo
from .log import ErroMetodologico
from .texto import normalizar_tipografia

CAMPOS = ["tipo", "marca", "modelo_origem", "modelo_destino", "data_evento", "observacao"]
TIPOS = {"rebatismo", "reclassificacao", "substituicao", "ignorar"}
TIPOS_QUE_FUNDEM = {"rebatismo"}


@dataclass(frozen=True)
class Regra:
    tipo: str
    marca: str
    modelo_origem: str
    modelo_destino: str
    data_evento: str
    observacao: str
    linha: int

    @property
    def chave_origem(self) -> tuple[str, str]:
        return (self.marca, self.modelo_origem)

    @property
    def chave_destino(self) -> tuple[str, str]:
        return (self.marca, self.modelo_destino)


def garantir_arquivo() -> None:
    if config.REGRAS.exists():
        return
    with config.REGRAS.open("w", encoding="utf-8", newline="") as fluxo:
        csv.writer(fluxo).writerow(CAMPOS)


def carregar() -> list[Regra]:
    garantir_arquivo()
    regras: list[Regra] = []
    with config.REGRAS.open(encoding="utf-8", newline="") as fluxo:
        leitor = csv.DictReader(fluxo)
        faltando = [c for c in CAMPOS if c not in (leitor.fieldnames or [])]
        if faltando:
            raise ErroMetodologico(
                f"regras.csv sem as colunas {faltando}. Cabecalho esperado: {CAMPOS}"
            )
        for numero, bruta in enumerate(leitor, start=2):
            if not any(normalizar_tipografia(v or "") for v in bruta.values()):
                continue
            regra = Regra(
                tipo=normalizar_tipografia(bruta["tipo"]).lower(),
                marca=normalizar_tipografia(bruta["marca"]),
                modelo_origem=normalizar_tipografia(bruta["modelo_origem"]),
                modelo_destino=normalizar_tipografia(bruta["modelo_destino"]),
                data_evento=normalizar_tipografia(bruta["data_evento"]),
                observacao=normalizar_tipografia(bruta["observacao"]),
                linha=numero,
            )
            _validar(regra)
            regras.append(regra)
    _validar_conjunto(regras)
    return regras


def _validar(regra: Regra) -> None:
    onde = f"regras.csv linha {regra.linha}"
    if regra.tipo not in TIPOS:
        raise ErroMetodologico(f"{onde}: tipo {regra.tipo!r} fora de {sorted(TIPOS)}")
    if not regra.marca or not regra.modelo_origem:
        raise ErroMetodologico(f"{onde}: marca e modelo_origem sao obrigatorios")
    if regra.tipo in {"rebatismo", "reclassificacao", "substituicao"} and not regra.modelo_destino:
        raise ErroMetodologico(f"{onde}: tipo {regra.tipo!r} exige modelo_destino")
    if regra.data_evento:
        try:
            periodo.partes(regra.data_evento)
        except ValueError as erro:
            raise ErroMetodologico(f"{onde}: {erro}") from erro
    elif regra.tipo in TIPOS_QUE_FUNDEM:
        raise ErroMetodologico(
            f"{onde}: rebatismo exige data_evento (AAAA-MM) -- e' o campo que D2 manda registrar"
        )


def _validar_conjunto(regras: list[Regra]) -> None:
    fusoes = {r.chave_origem: r for r in regras if r.tipo in TIPOS_QUE_FUNDEM}
    duplicadas = [r for r in regras if r.tipo in TIPOS_QUE_FUNDEM]
    vistos: dict[tuple[str, str], int] = {}
    for regra in duplicadas:
        anterior = vistos.get(regra.chave_origem)
        if anterior:
            raise ErroMetodologico(
                f"regras.csv linhas {anterior} e {regra.linha}: duas fusoes para a mesma "
                f"origem {regra.chave_origem}. Uma origem so' pode ter um destino."
            )
        vistos[regra.chave_origem] = regra.linha
    for origem in fusoes:
        visitados = [origem]
        atual = origem
        while atual in fusoes:
            atual = fusoes[atual].chave_destino
            if atual in visitados:
                caminho = " -> ".join(f"{m}/{n}" for m, n in visitados + [atual])
                raise ErroMetodologico(f"regras.csv: ciclo de rebatismo {caminho}")
            visitados.append(atual)


def resolver_destino(chave: tuple[str, str], regras: list[Regra]) -> tuple[tuple[str, str], list[str]]:
    """Segue a cadeia de rebatismos ate' o nome final. Devolve (chave, datas)."""
    fusoes = {r.chave_origem: r for r in regras if r.tipo in TIPOS_QUE_FUNDEM}
    atual, datas = chave, []
    while atual in fusoes:
        datas.append(fusoes[atual].data_evento)
        atual = fusoes[atual].chave_destino
    return atual, datas
