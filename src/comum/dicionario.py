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
    ("marca", "texto", "Marca como a fonte publica, em caixa canonica (ver abaixo)."),
    ("modelo", "texto", "Nome comercial apos a harmonizacao, em caixa canonica. Igual a "
                        "`modelo_fonte` quando nenhuma regra de rebatismo se aplica."),
    ("sub_segmento_fonte", "texto", "Sub-segmento em que a fonte listou a linha ('Suv's', "
                                    "'Sedans Compactos'). **Atributo da linha, fora da "
                                    "chave.** Vazio nas linhas vindas so' do ranking."),
    ("grupo_economico", "texto", "Grupo vigente para a marca **naquele mes** (D4). Marca sem "
                                 "linha no mapa entra como grupo unitario com o proprio nome."),
    ("grupo_mapeado", "booleano", "Falso quando o grupo saiu do nome da marca por ausencia "
                                  "de linha vigente em `config/mapa_grupos.csv`."),
    ("unidades", "inteiro", "Emplacamentos da linha no mes."),
    ("corte_publicacao", "inteiro", "Menor valor que a fonte listou naquele mes e segmento. "
                                    "Modelo ausente do painel esta' abaixo disto."),
    ("modelo_fonte", "texto", "Nome do modelo antes da harmonizacao, em caixa canonica."),
    ("grafias_fonte", "texto", "Todas as grafias cruas que a fonte usou para este modelo, "
                               "letra por letra. E' aqui que `Outlander` e `OUTLANDER` "
                               "continuam distinguiveis."),
    ("nome_suspeito", "booleano", "O nome provavelmente nao designa um veiculo -- registro "
                                  "avulso, encarrocador, erro de cadastro."),
    ("motivo_nome_suspeito", "texto", "Por que foi marcado. Vazio quando nao foi."),
    ("duplicata_publicada", "texto", "So' no painel bruto. Quando preenchida, esta linha "
     "repete outra do **mesmo informe**, com o mesmo valor, sob marca trocada, e o texto "
     "aponta qual. Essas linhas ficam fora do painel de analise, e o invariante central e' "
     "conferido depois de exclui-las. Hoje sao exatamente quatro, todas de 2013-11, travadas "
     "por teste. ASSIMETRIA DELIBERADA: o mesmo defeito teve dois tratamentos. Cinco "
     "duplicatas irmas foram removidas **a montante**, na canonizacao da chave de "
     "reconciliacao da etapa 02, porque a divergencia era tipografica (`VW /GOL` contra "
     "`VW/GOL`) e consertar a chave nao mexe no que foi transcrito. Estas quatro divergiam "
     "na **marca** (`PONTIAC/MONTANA` contra `GM /MONTANA`), e canoniza-las na etapa 02 "
     "significaria reescrever a marca dentro do painel bruto, que e' transcricao fiel da "
     "fonte (sec.4). Entao foram removidas **a jusante**, por supressao registrada. A regra: "
     "a montante quando da' para consertar sem tocar no transcrito; a jusante quando nao da'."),
    ("marca_publicada_fonte", "texto", "A marca como a fonte publicou, antes de qualquer "
     "recuperacao. Igual a `marca` em tudo menos nas linhas de D4."),
    ("marca_recuperada", "booleano", "A marca desta linha foi recuperada da coluna de mes "
     "anterior do informe seguinte, porque a edicao do mes saiu com a coluna trocada (D4). "
     "O **valor nao muda** -- muda a quem ele e' atribuido, e a nova atribuicao vem da mesma "
     "fonte republicando o mesmo mes, com o valor conferindo unidade a unidade. Hoje: 8 "
     "modelos de 2013-11. `marca_publicada_fonte` guarda a marca errada ao lado."),
    ("nome_completo_fonte", "texto", "Nome cru, `MARCA/MODELO`, sem alteracao alem da "
                                     "normalizacao tipografica."),
    ("houve_rebatismo", "booleano", "A serie foi fundida por uma regra `rebatismo` (D2)."),
    ("data_rebatismo", "texto AAAA-MM", "Data do rebatismo, do campo `data_evento` da regra."),
    ("cadeia_rebatismo", "texto", "Datas encadeadas quando houve mais de um rebatismo."),
    ("reclassificacao", "booleano", "O modelo participa de um desdobramento de familia (D1)."),
    ("conta_entrada_saida", "booleano", "Falso onde uma reclassificacao suprime a contagem "
                                        "de entrada/saida naquele ponto."),
    ("origem_tabela", "texto", "`sub_segmento`, `ranking`, `mes_anterior`, ou combinacao: "
                               "qual tabela do informe forneceu o numero."),
    ("arquivos_origem", "texto", "Arquivo(s) PDF de origem. Com o hash em "
                                 "`dados/bruto/manifesto.csv`, fecha a rastreabilidade."),
]


def escrever(painel: pd.DataFrame) -> None:
    meses = sorted(painel["mes_ref"].unique())
    chave = ["marca", "modelo", "segmento"]
    linhas = [
        "# Dicionario de dados -- `painel.parquet`\n\n",
        f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC) por "
        "`src/etapa05_painel.py`.\n\n",
        f"- Periodo: **{meses[0]} a {meses[-1]}** ({len(meses)} meses)\n",
        f"- Linhas: {len(painel):,}\n",
        f"- Unidades: {int(painel['unidades'].sum()):,}\n",
        f"- Modelos (marca x modelo x segmento): "
        f"{painel[chave].drop_duplicates().shape[0]:,}\n\n",

        "## Unidade de observacao\n\n",
        "A **variante comercial**, identificada por `(marca, modelo, segmento)` (D1). "
        "Onix e Onix Plus sao dois produtos. O segmento entra na chave porque a fonte "
        "publica o mesmo nome comercial nos dois segmentos -- RENAULT/KWID aparece em "
        "automoveis e em comerciais leves no mesmo mes -- e juntar os dois somaria "
        "produtos diferentes.\n\n",

        "O **sub-segmento fica na linha, fora da chave**. Quando a fonte lista o mesmo "
        "`(marca, modelo, segmento)` em dois sub-segmentos no mesmo mes -- `NISSAN/VERSA` "
        "em 'Sedans Pequenos' com a geracao antiga e em 'Sedans Compactos' com a nova --, "
        "as duas linhas ficam separadas. Descartar o sub-segmento jogaria fora a unica "
        "pista de geracao que existe, e ela nao volta. Quem precisa da serie por modelo "
        "usa `comum.visoes.por_modelo`, que soma os sub-segmentos; quem precisa da geracao "
        "vai direto ao painel.\n\n",

        "## Campos\n\n",
        "| campo | tipo | descricao |\n|---|---|---|\n",
    ]
    linhas += [f"| `{nome}` | {tipo} | {texto} |\n" for nome, tipo, texto in CAMPOS]
    linhas += [
        "\n## As taxas de entrada e saida nao medem so' rotatividade\n\n",
        "**Leia isto antes de usar qualquer taxa.** Cerca de um terco dos modelos do painel "
        "soma algumas milhares de unidades no periodo inteiro -- 0,01% do volume -- e cada "
        "um conta como uma entrada e uma saida. Sao registros avulsos, conversoes de "
        "encarrocador e erros de cadastro da fonte. Eles respondem por 30% a 55% de toda a "
        "rotatividade medida.\n\n",
        "Por isso `saidas/validacao.md` sec.8 traz as taxas sob tres **pisos de volume total "
        "do modelo** -- todos, acima de 100 unidades, acima de 1.000 --, com o piso entrando "
        "no numerador e no denominador. **Nenhuma leitura substantiva deve sair da coluna "
        "\"todos\".** E o ano parcial, o ultimo da amostra, nao e' citavel para "
        "rotatividade: a taxa de saida dele e' inflada pelo recorte.\n\n",
        "A coluna `nome_suspeito` marca os casos em que o nome nem sequer designa veiculo, "
        "e `saidas/nomes_suspeitos.csv` traz os candidatos a revisao. Nada foi apagado do "
        "painel.\n\n",

        "\n## Caixa: chave contra transcricao\n\n",
        "A ESPEC sec.4 proibe uniformizar maiusculas **na transcricao**, e o painel obedece: "
        "`grafias_fonte` e `nome_completo_fonte` guardam o que a fonte escreveu. A **chave** "
        "(`marca`, `modelo`) e' outra coisa, e essa e' canonizada em caixa. Sem isso, "
        "`MITSUBISHI/Outlander` (35.231 unidades em oito anos) e `MITSUBISHI/OUTLANDER` "
        "(8 unidades num mes) seriam duas fichas do mesmo carro, com uma saida e uma entrada "
        "fabricadas. Normalizar caixa nao e' fundir modelos: fusao de produtos distintos "
        "continua exigindo linha em `regras.csv`.\n\n",

        "\n## Entrada e saida sao assimetricas\n\n",
        "**A entrada nao depende do limiar.** Ela e' o primeiro mes com unidades positivas; "
        "so' a saida usa a regra D3 (`>= limiar x pico movel de 12 meses`), que foi o que a "
        "ESPEC especificou. Por isso, em `saidas/validacao.md`, as contagens de entrada sao "
        "identicas nos tres limiares e so' as de saida variam -- e' desenho, nao defeito. "
        "A assimetria entra direto em qualquer decomposicao de margens de entrada e saida, "
        "e quem for usar essas margens precisa decidir se quer um criterio simetrico.\n\n",

        "## O que significa um zero\n\n",
        "Mes com informe em que o modelo nao aparece entra como **zero**: a fonte publicou "
        "aquele mes e nao listou o modelo. Mes sem informe legivel entra como **ausente** e "
        "sai das janelas moveis -- lacuna nunca vira zero (sec.9.2).\n\n",
        "A ressalva esta' em `corte_publicacao`: as tabelas da fonte sao truncadas, entao "
        "zero quer dizer 'abaixo do corte daquele mes'. Quando o corte esta' **acima** do "
        "limiar de D3 do proprio modelo, o zero e' fragil -- o modelo poderia estar em cima "
        "do limiar e mesmo assim nao ser listado. `saidas/zeros_frageis.csv` lista esses "
        "casos, e `saidas/validacao.md` sec.8 mede o efeito sobre a taxa de saida.\n\n",

        "## Limitacao declarada\n\n",
        "**Troca de geracao e' invisivel na fonte na maior parte dos casos -- nao em "
        "todos.** O informe publica o nome comercial, nao a geracao. Onde a fonte por acaso "
        "separa geracoes em sub-segmentos diferentes, o painel preserva a separacao (ver "
        "`sub_segmento_fonte`); fora desses casos, 'sobrevivencia do modelo' significa "
        "sobrevivencia do **nome comercial**, nao do produto fisico. Um Gol de 2005 e um "
        "Gol de 2015 sao a mesma serie aqui, ainda que sejam carros diferentes.\n\n",

        "## Cobertura\n\n",
        "As tabelas por modelo do informe tem numero fixo de linhas por sub-segmento e "
        "truncam a cauda. O painel cobre a maior parte do volume publicado, nao a "
        "totalidade; `saidas/cobertura.csv` traz o confronto mes a mes com o total que a "
        "propria fonte publica (D5). **Nenhum piso de cobertura foi aplicado ao painel**: "
        "`saidas/piso_recomendado.csv` traz a recomendacao e o volume que ela descartaria, "
        "para que a escolha continue sendo de analise.\n\n",

        "## Harmonizacao\n\n",
        "Nesta rodada `regras.csv` esta' **vazio**: nada foi fundido. As taxas de entrada e "
        "saida derivadas deste painel sao, portanto, o **limite superior** dessas taxas -- "
        "o cenario em que todo rebatismo conta como morte e nascimento. "
        "`saidas/candidatos.xlsx` e' a evidencia arquivada para a adjudicacao futura.\n\n",

        "## Reconstituicao\n\n",
        "Todo numero se reconstitui a partir de tres coisas versionadas: os PDFs originais "
        "(hash em `dados/bruto/manifesto.csv`), `regras.csv` e os scripts de `src/`. "
        "Nenhuma etapa sobrescreve a anterior; rodar duas vezes produz o mesmo resultado.\n",
    ]
    config.DICIONARIO.parent.mkdir(parents=True, exist_ok=True)
    config.DICIONARIO.write_text("".join(linhas), encoding="utf-8")
