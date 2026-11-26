"""Leitura das planilhas de frota da Senatran (rodada 13).

Tres formatos de tabela, estaveis desde 2003 apesar dos nomes de arquivo:

- **municipio x tipo** (largo): linha de cabecalho `UF | MUNICIPIO | TOTAL | <tipos>`,
  as vezes repetida; acima dela, o total Brasil publicado. Antes de 2014 e em
  alguns anos, a primeira aba e' um glossario;
- **UF x tipo** (largo): primeira coluna `Grandes Regiões e Unidades da Federação`
  com Brasil, as cinco regioes e as UFs por extenso;
- **municipio x combustivel** (longo): `UF (por extenso) | Município | Combustível
  Veículo | Qtd. Veículos`. Em 2013-12 vem num banco Access (.mdb), lido com
  `mdb-export` (pacote de sistema `mdbtools`).

Embalagem: planilha solta, zip (com zip dentro, de 2003 a 2012) ou rar (2015 e
2016, lido com `bsdtar`). Celula com traco (`-`, formato contabil do Excel) e'
zero; a contagem de tracos lidos como zero vai para a conferencia.
"""

from __future__ import annotations

import csv
import io
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import xlrd

from .energia import MESES_ABREV, chave_nome, sem_acento, sigla_da_uf

EXT_PLANILHA = (".xls", ".xlsx", ".mdb", ".csv")


# ------------------------------------------------------------------ embalagem


def desembalar(nome: str, conteudo: bytes) -> list[tuple[str, bytes]]:
    """(nome interno, bytes) de cada planilha, abrindo zip dentro de zip e rar."""
    baixo = nome.lower()
    if baixo.endswith(".zip"):
        saida = []
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            for interno in z.namelist():
                if interno.endswith("/"):
                    continue
                saida += desembalar(interno, z.read(interno))
        return saida
    if baixo.endswith(".rar"):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "a.rar"
            arquivo.write_bytes(conteudo)
            subprocess.run(["bsdtar", "-xf", str(arquivo), "-C", pasta], check=True,
                           capture_output=True)
            saida = []
            for p in sorted(Path(pasta).rglob("*")):
                if p.is_file() and p.name != "a.rar":
                    saida += desembalar(p.name, p.read_bytes())
            return saida
    if baixo.endswith(EXT_PLANILHA):
        return [(nome, conteudo)]
    return []


def e_dezembro(nome: str, ano: int) -> bool:
    n = sem_acento(nome).lower()
    curto = str(ano)[2:]
    return bool(re.search(r"dez", n) or re.search(rf"(?<!\d)12[ _.-]?(?:{ano}|{curto})(?!\d)", n)
                or re.match(r"^12\D", n))


def tipo_interno(nome: str) -> str | None:
    n = sem_acento(nome).lower()
    if "fabr" in n or "anofab" in n:
        return None
    if "combust" in n:
        return "municipio_combustivel"
    if "mun" in n:
        return "municipio_tipo"
    if "uf" in n or "regi" in n:
        return "uf_tipo"
    return None


# ------------------------------------------------------------------ planilhas


def _folhas(nome: str, conteudo: bytes) -> list[pd.DataFrame]:
    """Todas as abas como texto, sem cabecalho."""
    baixo = nome.lower()
    if baixo.endswith(".mdb"):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "a.mdb"
            arquivo.write_bytes(conteudo)
            tabelas = subprocess.run(["mdb-tables", "-1", str(arquivo)], check=True,
                                     capture_output=True, text=True).stdout.split("\n")
            saida = []
            for t in [t for t in tabelas if t.strip()]:
                texto = subprocess.run(["mdb-export", str(arquivo), t], check=True,
                                       capture_output=True, text=True).stdout
                linhas = list(csv.reader(io.StringIO(texto)))
                saida.append(pd.DataFrame(linhas).astype(str))
            return saida
    if baixo.endswith(".csv"):
        texto = conteudo.decode("utf-8-sig") if conteudo.startswith(b"\xef\xbb\xbf") else (
            conteudo.decode("latin-1"))
        separador = ";" if texto[:2000].count(";") > texto[:2000].count(",") else ","
        return [pd.read_csv(io.StringIO(texto), sep=separador, header=None, dtype=str,
                            keep_default_na=False)]
    if baixo.endswith(".xls"):
        try:
            livro = xlrd.open_workbook(file_contents=conteudo)
        except Exception:  # noqa: BLE001 -- xls antigo que o xlrd nao decodifica (2003-2009)
            livros = pd.read_excel(io.BytesIO(conteudo), header=None, sheet_name=None,
                                   dtype=object, engine="calamine")
            return [f.map(_celula_texto) for f in livros.values()]
        saida = []
        for folha in livro.sheets():
            linhas = [[_celula_xls(folha.cell(i, j)) for j in range(folha.ncols)]
                      for i in range(folha.nrows)]
            saida.append(pd.DataFrame(linhas, dtype=str))
        return saida
    livros = pd.read_excel(io.BytesIO(conteudo), header=None, sheet_name=None, dtype=object)
    return [f.map(_celula_texto) for f in livros.values()]


def _celula_xls(celula) -> str:
    if celula.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return ""
    if celula.ctype == xlrd.XL_CELL_NUMBER:
        v = celula.value
        return str(int(v)) if float(v).is_integer() else repr(v)
    return str(celula.value)


def _celula_texto(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _numero(texto: str) -> tuple[int | None, bool]:
    """(valor, era_traco). Vazio vira None; traco contabil vira 0."""
    t = str(texto).strip()
    if t == "":
        return None, False
    if re.fullmatch(r"-+", t):
        return 0, True
    t = t.replace(".", "") if re.fullmatch(r"\d{1,3}(\.\d{3})+", t) else t
    try:
        v = float(t)
    except ValueError:
        return None, False
    if not v.is_integer():
        raise ValueError(f"quantidade nao inteira: {texto!r}")
    return int(v), False


def _cabecalho(folha: pd.DataFrame, primeira: str, segunda: str | None
               ) -> tuple[int, pd.DataFrame] | None:
    """Linha do cabecalho e a folha recortada a partir da coluna em que a tabela comeca
    (em algumas planilhas a coluna A vem vazia)."""
    for i in range(min(len(folha), 40)):
        for j0 in range(min(folha.shape[1] - 1, 4)):
            a = chave_nome(folha.iat[i, j0])
            b = chave_nome(folha.iat[i, j0 + 1])
            if a == "" or not a.startswith(primeira):
                continue
            if segunda is None or b.startswith(segunda):
                recortada = folha.iloc[:, j0:].copy()
                recortada.columns = range(recortada.shape[1])
                return i, recortada
    return None


def ler_municipio_tipo(nome: str, conteudo: bytes) -> tuple[pd.DataFrame, dict]:
    """Longo: uf, municipio_fonte, rotulo, veiculos; e o total publicado e as contagens."""
    for folha in _folhas(nome, conteudo):
        achado = _cabecalho(folha, "UF", "MUNIC")
        if achado is None:
            continue
        i, folha = achado
        cabecalho = [str(c).strip() for c in folha.iloc[i].tolist()]
        j_total = next(j for j, c in enumerate(cabecalho) if chave_nome(c) == "TOTAL")
        tipos = [(j, c) for j, c in enumerate(cabecalho) if j > j_total and c]
        publicado = None
        for k in range(i):
            v, _ = _numero(folha.iat[k, j_total]) if folha.shape[1] > j_total else (None, False)
            if v:
                publicado = v
        linhas, tracos, totais_linha = [], 0, []
        for k in range(i + 1, len(folha)):
            uf = str(folha.iat[k, 0]).strip()
            municipio = str(folha.iat[k, 1]).strip()
            if not re.fullmatch(r"[A-Z]{2}", uf) or not municipio or (
                    uf == "UF" and chave_nome(municipio).startswith("MUNIC")):
                continue  # linha vazia, de nota ou cabecalho repetido
            total, t = _numero(folha.iat[k, j_total])
            tracos += t
            soma = 0
            for j, rotulo in tipos:
                v, t = _numero(folha.iat[k, j])
                tracos += t
                v = v or 0
                soma += v
                linhas.append((uf, municipio, rotulo, v))
            totais_linha.append((uf, municipio, total, soma))
        quadro = pd.DataFrame(linhas, columns=["uf", "municipio_fonte", "rotulo", "veiculos"])
        return quadro, {"total_publicado": publicado, "tracos_zero": tracos,
                        "totais_linha": totais_linha}
    raise ValueError(f"{nome}: tabela municipio x tipo nao encontrada")


def ler_uf_tipo(nome: str, conteudo: bytes) -> pd.DataFrame:
    """Longo: uf (sigla, ou BR), rotulo, veiculos. Regioes ficam de fora."""
    for folha in _folhas(nome, conteudo):
        achado = _cabecalho(folha, "GRANDES REGIOES", "TOTAL")  # o glossario nao tem TOTAL
        if achado is None:
            continue
        i, folha = achado
        cabecalho = [str(c).strip() for c in folha.iloc[i].tolist()]
        linhas = []
        for k in range(i + 1, len(folha)):
            rotulo_linha = str(folha.iat[k, 0]).strip()
            if chave_nome(rotulo_linha) == "BRASIL":
                uf = "BR"
            else:
                uf = sigla_da_uf(rotulo_linha) if rotulo_linha else None
            if not uf:
                continue
            for j, c in enumerate(cabecalho[1:], start=1):
                if not c:
                    continue
                v, _ = _numero(folha.iat[k, j])
                linhas.append((uf, c, v or 0))
        return pd.DataFrame(linhas, columns=["uf", "rotulo", "veiculos"])
    raise ValueError(f"{nome}: tabela UF x tipo nao encontrada")


def ler_municipio_combustivel(nome: str, conteudo: bytes) -> pd.DataFrame:
    """Longo: uf (sigla), municipio_fonte, rotulo (combustivel), veiculos."""
    for folha in _folhas(nome, conteudo):
        achado = _cabecalho(folha, "UF", "MUNIC")
        if achado is None:
            continue
        i, folha = achado
        if folha.shape[1] < 4 or "COMBUST" not in chave_nome(folha.iat[i, 2]):
            continue
        corpo = folha.iloc[i + 1:, :4].copy()
        corpo.columns = ["uf_fonte", "municipio_fonte", "rotulo", "qtd"]
        corpo = corpo[corpo["uf_fonte"].str.strip() != ""]
        # linhas sem UF (`Não Identificado`, `Não se Aplica`, `Sem Informação`) ficam com
        # uf vazia: nao sao municipio, e a etapa as separa com registro
        siglas = {u: sigla_da_uf(u) or "" for u in corpo["uf_fonte"].unique()}
        valores = [_numero(q)[0] for q in corpo["qtd"]]
        return pd.DataFrame({"uf": corpo["uf_fonte"].map(siglas).values,
                             "uf_fonte": corpo["uf_fonte"].str.strip().values,
                             "municipio_fonte": corpo["municipio_fonte"].str.strip().values,
                             "rotulo": corpo["rotulo"].str.strip().values,
                             "veiculos": [v or 0 for v in valores]})
    raise ValueError(f"{nome}: tabela municipio x combustivel nao encontrada")


MESES_TITULO = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8,
                "set": 9, "out": 10, "nov": 11, "dez": 12}


def mes_do_titulo(nome: str, conteudo: bytes) -> str | None:
    """Mes que a propria planilha declara no titulo ('... - Dez/2006', '- novembro/2003')."""
    try:
        folhas = _folhas(nome, conteudo)
    except Exception:  # noqa: BLE001
        return None
    for folha in folhas:
        for i in range(min(len(folha), 6)):
            for j in range(min(folha.shape[1], 3)):
                t = sem_acento(str(folha.iat[i, j])).lower()
                m = re.search(r"-\s*([a-z]{3})[a-z]*\.?\s*/\s*(\d{4})", t)
                if m and m.group(1) in MESES_TITULO and "frota" in t:
                    return f"{m.group(2)}-{MESES_TITULO[m.group(1)]:02d}"
    return None


def mes_do_nome_interno(nome: str, ano: int) -> int | None:
    n = sem_acento(nome).lower()
    for abrev, numero in MESES_ABREV.items():
        if re.search(rf"{abrev}", n):
            return numero
    m = re.search(rf"(?<!\d)(\d{{1,2}})[ _.-]?(?:{ano})(?!\d)", n)
    return int(m.group(1)) if m and 1 <= int(m.group(1)) <= 12 else None
