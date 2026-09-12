"""Parametros e caminhos do pipeline.

ESPEC.md sec.2. Nada aqui e' decisao metodologica: sao os parametros que o
pesquisador escolheu, reunidos num lugar so' para que nenhuma etapa os
reinvente. Tudo pode ser sobrescrito por variavel de ambiente, para que uma
execucao de teste nao precise editar o arquivo.
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------- diretorios
DIR_CONFIG = RAIZ / "config"
DIR_DADOS = RAIZ / "dados"
DIR_BRUTO = DIR_DADOS / "bruto"
DIR_PDF = DIR_BRUTO / "pdf"
DIR_PROCESSADO = DIR_DADOS / "processado"
DIR_EXTRACAO = DIR_PROCESSADO / "extracao"
DIR_SAIDAS = RAIZ / "saidas"
DIR_LOGS = RAIZ / "logs"

# ------------------------------------------------------------------ arquivos
MANIFESTO = DIR_BRUTO / "manifesto.csv"
LACUNAS = DIR_BRUTO / "lacunas.csv"
CATALOGO = DIR_BRUTO / "catalogo_fonte.csv"

PAINEL_BRUTO = DIR_PROCESSADO / "painel_bruto.parquet"
TOTAIS_FONTE = DIR_PROCESSADO / "totais_fonte.parquet"
PAINEL = DIR_PROCESSADO / "painel.parquet"

REGRAS = RAIZ / "regras.csv"
MAPA_GRUPOS = DIR_CONFIG / "mapa_grupos.csv"
MARCAS = DIR_CONFIG / "marcas.csv"
SUB_SEGMENTOS = DIR_CONFIG / "sub_segmentos.csv"

CANDIDATOS = DIR_SAIDAS / "candidatos.xlsx"
VALIDACAO = DIR_SAIDAS / "validacao.md"
DICIONARIO = DIR_SAIDAS / "painel_dicionario.md"
COBERTURA = DIR_SAIDAS / "cobertura.csv"
REFERENCIA_CRUZADA = DIR_SAIDAS / "referencia_cruzada.md"

# Controle independente (sec.7). Nao e' fonte. Ausente => etapa 07 reporta e sai.
VENDAS_GERAL = DIR_DADOS / "referencia" / "Vendas_Geral.xlsx"

# ----------------------------------------------------------------- periodo
# Recomendacao da sec.2: validar 2014-01..2026-08 antes de retroagir a 2003-01.
PERIODO_INICIO = os.environ.get("PERIODO_INICIO", "2014-01")
PERIODO_FIM = os.environ.get("PERIODO_FIM", "2026-08")

# Piso absoluto do que a fonte publica (informes mensais desde 2003-01).
FONTE_PRIMEIRO_MES = "2003-01"

# ------------------------------------------------------------------- escopo
# Automoveis + comerciais leves, veiculos novos (0 km).
SEGMENTOS = ("automoveis", "comerciais_leves")

# --------------------------------------------------------------- aquisicao
BASE_API = "https://www.fenabrave.org.br/portalv2/api/Emplacamentos"
BASE_ARQUIVOS = "https://www.fenabrave.org.br/portal/files/"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)
# Respeitar o servidor: um pedido por vez, com pausa (sec.4).
PAUSA_SEGUNDOS = float(os.environ.get("PAUSA_SEGUNDOS", "2.0"))
TENTATIVAS = int(os.environ.get("TENTATIVAS", "4"))
TIMEOUT_SEGUNDOS = float(os.environ.get("TIMEOUT_SEGUNDOS", "120"))

# ------------------------------------------------------------------ parsing
# Divergencia entre a soma dos modelos e o total publicado no proprio informe
# acima disto e' erro de parsing, nao arredondamento (sec.4).
TOLERANCIA_PARSING = 0.005

# ------------------------------------------------------------------ regra D3
# Limiar principal e variantes de robustez.
LIMIAR_SAIDA = 0.05
LIMIARES_SAIDA = (0.03, 0.05, 0.10)
JANELA_PICO_MESES = 12
# Como se le' "pico movel de 12 meses" (ver QUESTOES_ABERTAS.md, Q1).
# 'media_movel'  -> pico = max_t( media das unidades em [t-11, t] )
# 'max_movel'    -> pico = max_t( max das unidades em [t-11, t] ) == pico global
PICO_MOVEL_MODO = os.environ.get("PICO_MOVEL_MODO", "media_movel")

# ------------------------------------------------------------------ sec.5
JANELA_BASTAO_MESES = 6
RAZAO_PICO_MIN = 0.4
RAZAO_PICO_MAX = 3.0
PRE_EXISTENCIA_MESES = 12
JANELA_CORRELACAO_MESES = 12
QUEDA_ABRUPTA = 0.80

# ------------------------------------------------------------------- geral
SEMENTE = 20240101
