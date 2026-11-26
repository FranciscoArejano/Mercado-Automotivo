"""Pecas comuns da coleta (rodada 13): download, manifesto, bruto reduzido.

Regra de guarda do pesquisador:

- arquivo bruto de ate' 50 MB vai para o git como veio, em `dados/bruto/<fonte>/`;
- acima disso, o original fica em `dados/bruto/<fonte>/fora_do_git/` (no
  `.gitignore`) e o git guarda um **bruto reduzido** em parquet comprimido
  (`dados/bruto/<fonte>/reduzido/`): so' as colunas e linhas que os produtos usam,
  sem conta, agregacao nem renomeacao -- as celulas ficam como texto, exatamente
  como o arquivo as escreveu;
- o manifesto guarda URL, data, tamanho e SHA-256 do original e do reduzido.

O reduzido e' deterministico (mesma entrada, mesmos bytes): por isso o teste
pode refaze-lo a partir do original, quando presente, e comparar o SHA-256.
"""

from __future__ import annotations

import csv
import hashlib
import io
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import requests

from comum import config

CAMPOS_MANIFESTO = ["arquivo", "url", "data_download", "bytes", "sha256", "no_git",
                    "reduzido", "bytes_reduzido", "sha256_reduzido", "observacao"]


def dir_fonte(fonte: str) -> Path:
    if fonte not in config.FONTES_ENERGIA:
        raise ValueError(f"fonte desconhecida: {fonte}")
    return config.DIR_BRUTO / fonte


def caminho_manifesto(fonte: str) -> Path:
    return dir_fonte(fonte) / "manifesto.csv"


def ler_manifesto(fonte: str) -> dict[str, dict]:
    caminho = caminho_manifesto(fonte)
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8", newline="") as fluxo:
        return {linha["arquivo"]: linha for linha in csv.DictReader(fluxo)}


def gravar_manifesto(fonte: str, linhas: dict[str, dict]) -> None:
    caminho = caminho_manifesto(fonte)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(fluxo, fieldnames=CAMPOS_MANIFESTO)
        escritor.writeheader()
        for chave in sorted(linhas):
            escritor.writerow({c: linhas[chave].get(c, "") for c in CAMPOS_MANIFESTO})


def sha256_bytes(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as fluxo:
        for bloco in iter(lambda: fluxo.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def baixar(url: str, tentativas: int = 8, timeout: float = 600) -> bytes:
    """Um pedido por vez, com pausa; download em blocos, retomado por `Range` quando a
    conexao cai no meio (arquivos de centenas de MB da ANP)."""
    erro, recebido, total = None, bytearray(), None
    tentativa = 0
    while tentativa < tentativas:  # so' conta a tentativa que nao trouxe nenhum byte
        antes = len(recebido)
        cabecalho = {"User-Agent": config.USER_AGENT}
        if recebido:
            cabecalho["Range"] = f"bytes={len(recebido)}-"
        try:
            with requests.get(url, headers=cabecalho, timeout=timeout, stream=True) as resposta:
                if resposta.status_code in (401, 403, 404):
                    erro = f"HTTP {resposta.status_code}"
                    break  # bloqueio ou ausencia: nao insistir nem contornar
                if recebido and resposta.status_code != 206:
                    recebido = bytearray()  # o servidor ignorou o Range: recomeca
                elif resposta.status_code not in (200, 206):
                    raise requests.RequestException(f"HTTP {resposta.status_code}")
                if total is None and "Content-Length" in resposta.headers:
                    total = int(resposta.headers["Content-Length"]) + len(recebido)
                for bloco in resposta.iter_content(1 << 20):
                    recebido.extend(bloco)
            if recebido and (total is None or len(recebido) == total):
                time.sleep(config.PAUSA_SEGUNDOS)
                return bytes(recebido)
            erro = f"incompleto: {len(recebido)} de {total} bytes"
        except requests.RequestException as excecao:
            erro = f"{type(excecao).__name__}: {excecao}"[:300]
        if len(recebido) > antes:
            time.sleep(2)
            continue
        tentativa += 1
        time.sleep(10 * tentativa)
    raise RuntimeError(f"{url}: {erro}")


def destino_original(fonte: str, nome: str, tamanho: int) -> tuple[Path, bool]:
    """(caminho, vai_para_o_git) do original, pela regra dos 50 MB."""
    no_git = tamanho <= config.LIMITE_GIT_BYTES
    base = dir_fonte(fonte) if no_git else dir_fonte(fonte) / "fora_do_git"
    return base / nome, no_git


def registrar(fonte: str, manifesto: dict[str, dict], nome: str, url: str, conteudo: bytes,
              observacao: str = "") -> Path:
    """Grava o original no lugar certo e o registra no manifesto."""
    caminho, no_git = destino_original(fonte, nome, len(conteudo))
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)
    linha = manifesto.get(nome, {})
    linha.update({"arquivo": nome, "url": url, "data_download": agora(),
                  "bytes": str(len(conteudo)), "sha256": sha256_bytes(conteudo),
                  "no_git": "sim" if no_git else "nao", "observacao": observacao})
    if no_git:
        linha.update({"reduzido": "", "bytes_reduzido": "", "sha256_reduzido": ""})
    manifesto[nome] = linha
    gravar_manifesto(fonte, manifesto)
    return caminho


def caminho_do_original(fonte: str, linha: dict) -> Path:
    """`arquivo#parte` (uma aba de um original) aponta para o proprio original."""
    base = dir_fonte(fonte)
    nome = linha["arquivo"].split("#", 1)[0]
    return base / nome if linha["no_git"] == "sim" else base / "fora_do_git" / nome


def bytes_parquet(tabela: pa.Table) -> bytes:
    """Parquet deterministico (zstd, sem metadado de pandas): mesma tabela, mesmos bytes."""
    tabela = tabela.replace_schema_metadata(None)
    buffer = io.BytesIO()
    pq.write_table(tabela, buffer, compression="zstd", compression_level=9,
                   use_dictionary=True, write_statistics=False)
    return buffer.getvalue()


def gravar_reduzido(tabela: pa.Table, caminho: Path) -> bytes:
    conteudo = bytes_parquet(tabela)
    if len(conteudo) > config.LIMITE_GIT_BYTES:
        raise RuntimeError(f"{caminho.name}: reduzido com {len(conteudo)} bytes, acima de "
                           "50 MB; divida por ano")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)
    return conteudo


def registrar_reduzido(fonte: str, manifesto: dict[str, dict], nome: str,
                       caminho_reduzido: Path, conteudo: bytes) -> None:
    linha = manifesto[nome]
    linha.update({"reduzido": str(caminho_reduzido.relative_to(dir_fonte(fonte))),
                  "bytes_reduzido": str(len(conteudo)),
                  "sha256_reduzido": sha256_bytes(conteudo)})
    gravar_manifesto(fonte, manifesto)
