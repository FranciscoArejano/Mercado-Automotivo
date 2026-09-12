"""Dicionario de dados do painel (ESPEC.md sec.3)."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from . import config

CAMPOS = [
    ("mes_ref", "texto AAAA-MM", "Mes de referencia do emplacamento, como o informe o declara."),
    ("ano", "inteiro", "Ano de `mes_ref`."),
    ("mes", "inteiro 1-12", "Mes de `mes_ref`."),
    ("data", "data", "Primeiro dia de `mes_ref`. Conveniencia para series temporais."),
    ("segmento", "texto", "`automoveis` ou `comerciais_leves`, como a fonte classifica."),
    ("marca", "texto", "Marca tal como a fonte publica, antes da primeira barra do nome."),
    ("modelo", "texto", "Nome comercial apos a harmonizacao. Igual a `modelo_fonte` quando "
                        "nenhuma regra de rebatismo se aplica."),
    ("grupo_economico", "texto", "Grupo vigente para a marca **naquele mes** (D4). "
                                 "`NAO_MAPEADO` quando config/mapa_grupos.csv nao cobre o caso."),
    ("unidades", "inteiro", "Emplacamentos do modelo no mes."),
    ("modelo_fonte", "texto", "Nome do modelo como saiu da fonte, antes da harmonizacao."),
    ("nome_completo_fonte", "texto", "Nome cru, `MARCA/MODELO`, sem nenhuma alteracao "
                                     "alem da normalizacao tipografica."),
    ("houve_rebatismo", "booleano", "A serie foi fundida por uma regra `rebatismo` (D2)."),
    ("data_rebatismo", "texto AAAA-MM", "Data do rebatismo, do campo `data_evento` da regra."),
    ("cadeia_rebatismo", "texto", "Datas encadeadas quando houve mais de um rebatismo."),
    ("reclassificacao", "booleano", "O modelo participa de um desdobramento de familia (D1)."),
    ("conta_entrada_saida", "booleano", "Falso onde uma reclassificacao suprime a contagem "
                                        "de entrada/saida naquele ponto."),
    ("origem_tabela", "texto", "`sub_segmento`, `ranking`, ou os dois: qual tabela do informe "
                               "forneceu o numero."),
    ("arquivos_origem", "texto", "Arquivo(s) PDF de origem. Com o hash em "
                                 "`dados/bruto/manifesto.csv`, fecha a rastreabilidade."),
]


def escrever(painel: pd.DataFrame) -> None:
    meses = sorted(painel["mes_ref"].unique())
    linhas = [
        "# Dicionario de dados -- `painel.parquet`\n\n",
        f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC) por "
        "`src/etapa05_painel.py`.\n\n",
        f"- Periodo: **{meses[0]} a {meses[-1]}** ({len(meses)} meses)\n",
        f"- Linhas: {len(painel):,}\n",
        f"- Unidades: {int(painel['unidades'].sum()):,}\n",
        f"- Modelos (marca x modelo x segmento): "
        f"{painel[['marca', 'modelo', 'segmento']].drop_duplicates().shape[0]:,}\n\n",
        "## Unidade de observacao\n\n",
        "A **variante comercial**, identificada por `(marca, modelo, segmento)` (D1). "
        "Onix e Onix Plus sao dois produtos. O segmento entra na chave porque a fonte "
        "publica o mesmo nome comercial nos dois segmentos -- RENAULT/KWID aparece em "
        "automoveis e em comerciais leves no mesmo mes -- e juntar os dois somaria "
        "produtos diferentes.\n\n",
        "## Campos\n\n",
        "| campo | tipo | descricao |\n|---|---|---|\n",
    ]
    linhas += [f"| `{nome}` | {tipo} | {texto} |\n" for nome, tipo, texto in CAMPOS]
    linhas += [
        "\n## Limitacao declarada\n\n",
        "**Troca de geracao e' invisivel na fonte.** O informe da Fenabrave publica o nome "
        "comercial, nao a geracao do produto. Portanto \"sobrevivencia do modelo\" neste "
        "painel significa sobrevivencia do **nome comercial**, nao do produto fisico. Um "
        "Gol de 2005 e um Gol de 2015 sao a mesma serie aqui, ainda que sejam carros "
        "diferentes. Isto nao e' regra metodologica: e' limite da fonte, e qualquer "
        "leitura de duracao de produto tem de leva-lo em conta.\n\n",
        "## Cobertura\n\n",
        "As tabelas por modelo do informe tem numero fixo de linhas por sub-segmento e "
        "truncam a cauda. O painel cobre a maior parte do volume publicado, nao a "
        "totalidade; `saidas/cobertura.csv` traz o confronto mes a mes com o total que a "
        "propria fonte publica (D5), e `saidas/validacao.md` sumariza. Ausencia de um "
        "modelo num mes significa **abaixo do corte de publicacao daquele mes**, nao "
        "necessariamente zero.\n\n",
        "## Reconstituicao\n\n",
        "Todo numero do painel se reconstitui a partir de tres coisas versionadas: os PDFs "
        "originais (hash em `dados/bruto/manifesto.csv`), `regras.csv` e os scripts de "
        "`src/`. Nenhuma etapa sobrescreve a anterior; rodar duas vezes produz o mesmo "
        "resultado.\n",
    ]
    config.DICIONARIO.parent.mkdir(parents=True, exist_ok=True)
    config.DICIONARIO.write_text("".join(linhas), encoding="utf-8")
