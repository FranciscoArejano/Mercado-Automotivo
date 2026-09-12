"""OCR como ultimo recurso (ESPEC.md sec.8).

"tentar `pdfplumber` antes de OCR; so' cair para OCR se a extracao de texto
falhar, e registrar quais arquivos precisaram."

Aqui o OCR e' **opcional e explicito**: a etapa 02 so' o aciona com `--ocr`, e
toda linha que sai daqui carrega `metodo_extracao='ocr'` ate' o painel bruto,
para que o pesquisador possa isolar ou descartar o mes inteiro.

O reconhecimento e' posicional: as palavras sao reagrupadas em linhas pela
coordenada vertical e ordenadas pela horizontal, para que a tabela sobreviva.
Texto corrido de OCR perde a linha e mistura colunas.
"""

from __future__ import annotations

from pathlib import Path

DPI = 400
TOLERANCIA_LINHA = 18  # pontos de imagem: palavras dentro disto sao a mesma linha
CONFIANCA_MINIMA = 20


def disponivel() -> tuple[bool, str]:
    try:
        import pypdfium2  # noqa: F401
        import pytesseract
    except ImportError as erro:
        return False, f"dependencia ausente: {erro.name}"
    try:
        versao = pytesseract.get_tesseract_version()
    except Exception as erro:  # binario ausente ou quebrado
        return False, f"binario tesseract indisponivel: {erro}"
    return True, f"tesseract {versao}"


def texto_das_paginas(caminho: Path, paginas: list[int], idioma: str = "por") -> dict[int, str]:
    """Devolve {numero_da_pagina: texto} para as paginas pedidas (1-indexadas)."""
    import pypdfium2 as pdfium
    import pytesseract
    from pytesseract import Output

    documento = pdfium.PdfDocument(str(caminho))
    resultado: dict[int, str] = {}
    for numero in paginas:
        imagem = documento[numero - 1].render(scale=DPI / 72).to_pil()
        dados = pytesseract.image_to_data(
            imagem, lang=idioma, config="--psm 6", output_type=Output.DICT
        )
        linhas: dict[float, list[tuple[int, str]]] = {}
        for indice, bruto in enumerate(dados["text"]):
            palavra = bruto.strip()
            if not palavra:
                continue
            try:
                confianca = float(dados["conf"][indice])
            except (TypeError, ValueError):
                confianca = -1.0
            if confianca < CONFIANCA_MINIMA:
                continue
            centro = dados["top"][indice] + dados["height"][indice] / 2
            chave = next((k for k in linhas if abs(k - centro) < TOLERANCIA_LINHA), centro)
            linhas.setdefault(chave, []).append((dados["left"][indice], palavra))
        resultado[numero] = "\n".join(
            " ".join(p for _, p in sorted(linhas[y])) for y in sorted(linhas)
        )
    documento.close()
    return resultado


def limpar(texto: str) -> str:
    """Correcoes tipograficas que o OCR introduz -- e so' elas."""
    return (
        texto.replace(" /", "/").replace("/ ", "/")
        .replace("Iº", "1º").replace("l º", "1º")
    )
