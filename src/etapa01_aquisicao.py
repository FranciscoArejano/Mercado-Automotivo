#!/usr/bin/env python3
"""Etapa 1 -- aquisicao dos informes mensais da Fenabrave (ESPEC.md sec.4).

- Um pedido por vez, com pausa entre eles.
- `dados/bruto/` nunca e' reescrito: arquivo ja' presente e integro e' mantido
  (idempotencia, sec.1.3 e sec.9.3).
- Mes que nao existe na fonte ou cuja baixa falha vai para `bruto/lacunas.csv`.
  Lacuna e' lacuna: nao se preenche, nao se interpola, nao se estima (sec.9.2).

Uso:
    python src/etapa01_aquisicao.py [--inicio AAAA-MM] [--fim AAAA-MM] [--so-catalogo]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import config, log, periodo  # noqa: E402

ETAPA = "etapa01_aquisicao"

CAMPOS_MANIFESTO = [
    "mes", "arquivo_local", "arquivo_fonte", "url", "sha256", "bytes", "data_download",
]
CAMPOS_LACUNAS = ["mes", "motivo", "detalhe", "data_verificacao"]
CAMPOS_CATALOGO = ["mes", "arquivo_fonte", "url", "descricao_fonte", "data_consulta"]


def _sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update({"User-Agent": config.USER_AGENT})
    return sessao


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def baixar_catalogo(sessao: requests.Session, anos: list[int], logger) -> dict[str, dict]:
    """Consulta a API de emplacamentos ano a ano.

    A fonte nao usa um padrao unico de nome de arquivo ('3_2014_01_2.pdf',
    '2020_12_2.pdf', '2025_01_02.pdf'), entao o nome nunca e' adivinhado: e'
    sempre lido do catalogo que a propria fonte publica.
    """
    catalogo: dict[str, dict] = {}
    for ano in anos:
        resposta = _com_tentativas(
            lambda: sessao.post(
                config.BASE_API, data={"ano": str(ano)}, timeout=config.TIMEOUT_SEGUNDOS
            ),
            logger,
            f"catalogo {ano}",
        )
        if resposta is None:
            logger.warning("catalogo do ano %s indisponivel", ano)
            continue
        corpo = resposta.json()
        blocos = (corpo.get("data") or {}).get("blocos") or []
        for bloco in blocos:
            data_bruta = (bloco.get("data") or "")[:7]
            arquivo = (bloco.get("link") or "").strip()
            if not data_bruta or not arquivo:
                continue
            catalogo[data_bruta] = {
                "mes": data_bruta,
                "arquivo_fonte": arquivo,
                "url": config.BASE_ARQUIVOS + arquivo,
                "descricao_fonte": (bloco.get("descricao") or "").strip(),
                "data_consulta": _agora(),
            }
        logger.info("catalogo %s: %d informes listados", ano, len(blocos))
        time.sleep(config.PAUSA_SEGUNDOS)
    return catalogo


def _com_tentativas(chamada, logger, rotulo: str):
    """Repete apenas falhas de rede, com espera exponencial (2s, 4s, 8s, 16s)."""
    espera = 2.0
    for tentativa in range(1, config.TENTATIVAS + 1):
        try:
            resposta = chamada()
            if resposta.status_code == 200:
                return resposta
            logger.warning("%s: HTTP %s (tentativa %d)", rotulo, resposta.status_code, tentativa)
            if 400 <= resposta.status_code < 500:
                return None  # 404 nao melhora com repeticao
        except requests.RequestException as erro:
            logger.warning("%s: %s (tentativa %d)", rotulo, erro, tentativa)
        if tentativa < config.TENTATIVAS:
            time.sleep(espera)
            espera *= 2
    return None


def sha256(caminho: Path) -> str:
    digestor = hashlib.sha256()
    with caminho.open("rb") as fluxo:
        for pedaco in iter(lambda: fluxo.read(1 << 20), b""):
            digestor.update(pedaco)
    return digestor.hexdigest()


def _ler_manifesto() -> dict[str, dict]:
    if not config.MANIFESTO.exists():
        return {}
    with config.MANIFESTO.open(encoding="utf-8", newline="") as fluxo:
        return {linha["mes"]: linha for linha in csv.DictReader(fluxo)}


def _escrever(caminho: Path, campos: list[str], linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=campos)
        escritor.writeheader()
        for linha in sorted(linhas, key=lambda item: item["mes"]):
            escritor.writerow({campo: linha.get(campo, "") for campo in campos})


def executar(inicio: str, fim: str, so_catalogo: bool = False) -> int:
    logger = log.preparar(ETAPA)
    meses = periodo.intervalo(inicio, fim)
    anos = sorted({periodo.partes(mes)[0] for mes in meses})
    logger.info("periodo %s..%s (%d meses, anos %s)", inicio, fim, len(meses), anos)

    config.DIR_PDF.mkdir(parents=True, exist_ok=True)
    sessao = _sessao()

    catalogo = baixar_catalogo(sessao, anos, logger)
    _escrever(config.CATALOGO, CAMPOS_CATALOGO, list(catalogo.values()))
    logger.info("catalogo gravado em %s (%d meses)", log.caminho_relativo(config.CATALOGO), len(catalogo))
    if so_catalogo:
        return 0

    manifesto = _ler_manifesto()
    lacunas: list[dict] = []
    baixados = reaproveitados = 0

    for mes in meses:
        entrada = catalogo.get(mes)
        if entrada is None:
            lacunas.append({
                "mes": mes, "motivo": "ausente_na_fonte",
                "detalhe": "mes nao listado no catalogo da Fenabrave",
                "data_verificacao": _agora(),
            })
            logger.warning("%s: ausente no catalogo da fonte", mes)
            continue

        destino = config.DIR_PDF / f"{mes}.pdf"
        if destino.exists():
            # Nunca reescrever bruto/ (sec.9.3): confere o hash e segue.
            digest = sha256(destino)
            registro = manifesto.get(mes)
            if registro and registro.get("sha256") and registro["sha256"] != digest:
                logger.error("%s: hash local diverge do manifesto -- arquivo intocado", mes)
                lacunas.append({
                    "mes": mes, "motivo": "hash_divergente",
                    "detalhe": f"local={digest} manifesto={registro['sha256']}",
                    "data_verificacao": _agora(),
                })
                continue
            manifesto[mes] = {
                "mes": mes,
                "arquivo_local": log.caminho_relativo(destino),
                "arquivo_fonte": entrada["arquivo_fonte"],
                "url": entrada["url"],
                "sha256": digest,
                "bytes": destino.stat().st_size,
                "data_download": (registro or {}).get("data_download") or _agora(),
            }
            reaproveitados += 1
            continue

        resposta = _com_tentativas(
            lambda url=entrada["url"]: sessao.get(url, timeout=config.TIMEOUT_SEGUNDOS),
            logger, f"{mes} {entrada['arquivo_fonte']}",
        )
        time.sleep(config.PAUSA_SEGUNDOS)
        if resposta is None:
            lacunas.append({
                "mes": mes, "motivo": "falha_download", "detalhe": entrada["url"],
                "data_verificacao": _agora(),
            })
            continue
        tipo = resposta.headers.get("content-type", "")
        if "pdf" not in tipo.lower() and not resposta.content.startswith(b"%PDF"):
            lacunas.append({
                "mes": mes, "motivo": "conteudo_nao_pdf",
                "detalhe": f"content-type={tipo} bytes={len(resposta.content)}",
                "data_verificacao": _agora(),
            })
            logger.error("%s: resposta nao e' PDF (%s)", mes, tipo)
            continue

        provisorio = destino.with_suffix(".pdf.parcial")
        provisorio.write_bytes(resposta.content)
        provisorio.rename(destino)
        manifesto[mes] = {
            "mes": mes,
            "arquivo_local": log.caminho_relativo(destino),
            "arquivo_fonte": entrada["arquivo_fonte"],
            "url": entrada["url"],
            "sha256": sha256(destino),
            "bytes": destino.stat().st_size,
            "data_download": _agora(),
        }
        baixados += 1
        logger.info("%s: baixado (%d bytes)", mes, destino.stat().st_size)
        if baixados % 10 == 0:
            # Descarga parcial: uma baixa longa fica observavel e retomavel.
            _escrever(config.MANIFESTO, CAMPOS_MANIFESTO, list(manifesto.values()))

    _escrever(config.MANIFESTO, CAMPOS_MANIFESTO, list(manifesto.values()))
    _escrever(config.LACUNAS, CAMPOS_LACUNAS, lacunas)
    log.contagem(
        logger, meses_pedidos=len(meses), baixados=baixados,
        ja_presentes=reaproveitados, lacunas=len(lacunas),
        manifesto_linhas=len(manifesto),
    )
    if lacunas:
        logger.warning("%d lacunas registradas em %s", len(lacunas), log.caminho_relativo(config.LACUNAS))
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--inicio", default=config.PERIODO_INICIO)
    analisador.add_argument("--fim", default=config.PERIODO_FIM)
    analisador.add_argument("--so-catalogo", action="store_true",
                            help="apenas consulta o catalogo da fonte, sem baixar PDFs")
    args = analisador.parse_args()
    return executar(args.inicio, args.fim, args.so_catalogo)


if __name__ == "__main__":
    raise SystemExit(main())
