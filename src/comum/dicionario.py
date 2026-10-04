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
     "fonte republicando o mesmo mes, com o valor conferindo unidade a unidade. Hoje: "
     "<<N_MARCA_RECUPERADA>> (contado do dado). `marca_publicada_fonte` guarda a "
     "marca errada ao lado."),
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


def _corte_pbe() -> str:
    """A frase citavel do corte da P2, da cobertura calculada (se ja' existe)."""
    if not config.PBE_COBERTURA.exists():
        return ""
    cobertura = pd.read_csv(config.PBE_COBERTURA)
    acima = cobertura[cobertura["cobertura_pct"] >= 80]
    if acima.empty:
        return ""
    corte = acima.iloc[0]
    anterior = cobertura[cobertura["ano"] == corte["ano"] - 1]
    antes = (f" (em {int(corte['ano']) - 1}, {anterior['cobertura_pct'].item():.1f}%)"
             .replace(".", ",") if len(anterior) else "")
    return (f"A ausencia no PBE so' foi tratada como informativa a partir de {int(corte['ano'])}, "
            f"quando o programa passou a cobrir {corte['cobertura_pct']:.1f}%".replace(".", ",")
            + f" do volume do painel{antes}; antes disso, a regra P2 mantem a proposta "
            "(`saidas/pbe_cobertura_por_ano.csv`).")


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
    # Contagem que muda com o dado sai do dado, nao do texto.
    recuperadas = (f"{int(painel['marca_recuperada'].sum())} linhas, em "
                   + ", ".join(sorted(painel.loc[painel["marca_recuperada"], "mes_ref"].unique()))
                   if "marca_recuperada" in painel and painel["marca_recuperada"].any()
                   else "nenhuma linha")
    linhas += [f"| `{nome}` | {tipo} | {texto.replace('<<N_MARCA_RECUPERADA>>', recuperadas)} |\n"
               for nome, tipo, texto in CAMPOS]
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

        "## Dimensoes paralelas\n\n",
        "Dois arquivos com a mesma unidade de tempo, **nunca colunas deste painel** -- a "
        "juncao e' do codigo de analise:\n\n",
        "- `painel_canal.parquet` -- venda direta e varejo por modelo, top-50 por segmento. "
        "Dicionario proprio em `saidas/painel_canal_dicionario.md`; leia a advertencia "
        "sobre o nivel antes de usar.\n",
        "- `macro_mensal.parquet` -- credito, juros, cambio, precos e atividade. Cada serie "
        "documentada em `config/series_macro.csv`, com a coluna `natureza_e_ressalvas`.\n",
        "- `classificacao.parquet` -- propulsao, eletrificacao, carroceria e origem da "
        "producao por modelo e vigencia, com a procedencia de cada atributo; e "
        "`classificacao_montagem.parquet`, o modo de montagem local por periodo; e "
        "`classificacao_propulsao_anual.parquet`, os tipos de propulsao oferecidos em cada "
        "vigencia e ano, nas leituras longa e curta -- **a tabela para serie temporal**: "
        "`propulsao_na_vigencia` e "
        "`eletrificacao_na_vigencia` sao o conjunto de tudo que foi oferecido em algum "
        "momento da vigencia, e numa serie anual inflam o `parcial` dos anos anteriores a' "
        "chegada da versao eletrificada. Gravadas "
        "pela etapa 11 a partir do rascunho adjudicado "
        "(`saidas/classificacao_rascunho.xlsx`), que e' a fonte de verdade. Dicionario proprio "
        "em `saidas/classificacao_dicionario.md`; leia a advertencia sobre procedencia antes "
        "de usar.\n\n",
        "**Limitacao da classificacao, registrada desde ja':** a fonte nao separa unidades "
        "por versao. Um modelo vendido em flex e em hibrido aparece como um numero so', e "
        "nao ha' como saber quantas unidades foram de cada. Por isso a propulsao sera' "
        "**conjunto** (`propulsao_na_vigencia`, e por ano `propulsao_no_ano`) e a "
        "eletrificacao tera' tres niveis "
        "(`nenhuma`, `parcial`, `total`). Somar as unidades dos modelos `parcial` como se "
        "fossem eletrificadas superestima a eletrificacao; soma-las como combustao a "
        "subestima. Contar unidades eletrificadas por propulsao exige fonte externa.\n\n",
        "**Regras e limitacoes decididas em 2026-10-01:** o hibrido leve (`mhev`) e o "
        "eletrico com extensor (`reev`) sao valores proprios da propulsao. Na derivacao de "
        "`eletrificacao`, modelo com `mhev` e combustao conta como `parcial` -- o hibrido "
        "leve nao roda em modo eletrico, e junta-lo a `hev` superestimaria a eletrificacao, "
        "omiti-lo a subestimaria; `total` exige so' tracao eletrica (`hev`, `phev`, `reev`, "
        "`bev`). `hibrido_indefinido` marca o modelo que o PBE poe em Hibrido sem que o nome da "
        "versao ou fonte digam se e' leve ou pleno; conta como `mhev` -- nunca leva a `total`, "
        "que exige evidencia positiva de tracao eletrica. A **transicao para o flex** (2003-2006) nao e' datada por modelo: os modelos "
        "que a atravessaram tem `gasolina+flex` na vigencia inteira -- precisao de mes seria "
        "falsa, e nenhum artigo planejado depende dela. A **montagem local** e' atributo "
        "proprio, `montagem_local` (`fabricacao`, `ckd`, `skd`, `desconhecido`, "
        "`nao_se_aplica`), separado da origem e com periodo proprio (`montagem_inicio`, "
        "`montagem_fim`): um carro pode ser `nacional` na origem e `ckd` no modo de montagem, e "
        "kit e carro inteiro tem tratamento tributario diferente. O modo so' vale dentro do "
        "periodo que a fonte declara; fora dele, `desconhecido`; carro importado e' "
        "`nao_se_aplica`.\n\n",
        "**Adjudicacao por regra:** o pesquisador aprova criterios "
        "(`config/regras_adjudicacao.csv`: o PBE Veicular acrescenta propulsao omitida; mantem-se "
        "o que o PBE nao podia ver; fonte de origem oficial ou de imprensa especializada que "
        "concorda ou ajusta a data e' aceita; contradicao, leitura inconclusiva ou fonte so' "
        "fraca vao a julgamento). So' o que os criterios nao decidem e' julgado linha a linha. "
        "A forca da fonte vem de `config/tipo_fonte_dominio.csv`. " + _corte_pbe() + "\n\n",
        "**Regra da fase 2 e procedencia:** nenhuma linha e' descartada; por linha e atributo "
        "vale a decisao humana, senao a decisao por regra, senao a proposta. A dimensao carrega, "
        "por atributo, a procedencia do valor: `humana`, `regra_fonte_forte`, "
        "`regra_fonte_fraca`, `proposta` (nunca tocada por checagem) ou `pendente` (contestada "
        "e ainda nao decidida; o valor e' a proposta original); `nao_classificado` abaixo do "
        "piso. **Um artigo que use propulsao ou origem como variavel de tratamento deve "
        "restringir-se as procedencias `humana` e `regra_fonte_forte`, e declarar a fracao do "
        "volume que ficou de fora.** As datas de troca de origem usam o lancamento quando a "
        "fonte o da', senao a producao: os meses entre producao e lancamento sao imprecisos "
        "por construcao, e num estudo de evento ficam fora da janela.\n\n",
        "**Propulsao no tempo (2026-10-02):** cada tipo eletrificado entra no ano da fonte "
        "datada de lancamento (`dados/referencia/propulsao_fontes.csv`), senao no da primeira "
        "tabela do PBE que o mostra -- se um ano com coluna de propulsao (2021 em diante) "
        "mostrava o modelo sem ele --, senao no inicio da vigencia, marcado "
        "`vigencia_sem_datacao`; combustao segue a vigencia. Toda dimensao nova passa por um "
        "uso-teste antes de ser declarada pronta (`saidas/classificacao_uso_teste.csv`).\n\n",
        "**Propulsao e comex (2026-10-04):** a regra P5 troca `hibrido_indefinido` por `mhev` "
        "ou `hev` quando fonte forte declara o tipo do hibrido. A saida de cada tipo (inclusive "
        "combustao) e' modelada como a entrada, em duas leituras: a longa mantem o tipo ate' a "
        "primeira ausencia no PBE (de 2021 em diante) ou fonte de fim de venda; a curta, ate' a "
        "ultima presenca. A banda da eletrificacao (piso, teto, teto sem MHEV, teto estrito) "
        "fica em `saidas/eletrificacao_banda.csv`.\n\n",
        "## Reconstituicao\n\n",
        "Todo numero se reconstitui a partir de tres coisas versionadas: os PDFs originais "
        "(hash em `dados/bruto/manifesto.csv`), `regras.csv` e os scripts de `src/`. "
        "Nenhuma etapa sobrescreve a anterior; rodar duas vezes produz o mesmo resultado.\n",
    ]
    config.DICIONARIO.parent.mkdir(parents=True, exist_ok=True)
    config.DICIONARIO.write_text("".join(linhas), encoding="utf-8")
