#!/usr/bin/env python3
"""Monta as duas tabelas de referencia do calendario de politicas.

- `dados/referencia/politicas_atos.csv`: uma linha por ato oficial (Planalto, Diario
  Oficial, gov.br, Banco Central, Contran, Conama), com as datas e o trecho literal da
  pagina guardada em `dados/bruto/politicas_paginas/`;
- `dados/referencia/politicas_aliquotas.csv`: as aliquotas que o proprio ato fixa, em
  formato longo. IPI: as de automovel, uma por periodo efetivamente vigente (cronograma
  que ato posterior substituiu antes de valer fica fora). II: os Ex-tarifarios de
  eletrificados, lidos das tabelas dos atos. IOF: a aliquota diaria do credito a pessoa
  fisica.

Cada linha e' escrita aqui, a' mao, a partir das paginas guardadas; antes de gravar, o
script confere que cada parte do trecho (separadas por " [...] ") esta' literalmente na
pagina, com os espacos normalizados. O teste `test_politicas.py` repete a conferencia.

Uso:
    python src/ferramentas/politicas_referencia.py
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import config, politicas, tipo_fonte  # noqa: E402

D = config.POLITICAS_PAGINAS
MAN = {r["nome"]: r for r in csv.DictReader((D / "manifesto.csv").open(encoding="utf-8"))}
normal = politicas.normalizar
MAPA = tipo_fonte.carregar_mapa()
TEXTO: dict[str, str] = {}


def texto(pagina: str) -> str:
    if pagina not in TEXTO:
        TEXTO[pagina] = normal((D / f"{pagina}.txt").read_text(encoding="utf-8"))
    return TEXTO[pagina]


# ======================================================================= atos

A = []


def ato(id, tema, instrumento, numero, data_ato, data_pub, ini, fim, altera, sentido, alcance,
        pagina, trecho, obs=""):
    A.append(dict(id=id, tema=tema, instrumento=instrumento, numero=numero, data_ato=data_ato,
                  data_publicacao=data_pub, vigencia_inicio=ini, vigencia_fim=fim,
                  altera_id=altera, sentido=sentido, alcance=alcance,
                  fonte_url=MAN[pagina]["url"],
                  tipo_fonte=tipo_fonte.tipo_de(MAN[pagina]["url"], MAPA),
                  pagina_salva=pagina, fonte_trecho=trecho,
                  observacao=obs))


# ------------------------------------------------------------------ IPI 2008-2010
ato("ipi_2008_dec6687", "ipi", "decreto", "6.687", "2008-12-11", "2008-12-12", "2008-12-12",
    "2009-03-31", "", "reduz",
    "automoveis ate 2.000 cm3 (gasolina e flex) e comerciais leves (8704.21, 8704.31)",
    "dec_6687_2008",
    "produzindo efeitos a partir de 12 de dezembro de 2008 até 31 de março de 2009",
    "1.000 cm3 a 0%; flex de 1.000 a 2.000 cm3 a 5,5%; gasolina de 1.000 a 2.000 cm3 a 6,5%.")
ato("ipi_2009_dec6809", "ipi", "decreto", "6.809", "2009-03-30", "2009-03-31", "2009-04-01",
    "2009-06-30", "ipi_2008_dec6687", "prorroga", "os mesmos veiculos do Decreto 6.687",
    "dec_6809_2009",
    "I - entre 1o de abril e 30 de junho de 2009, em relação aos arts. 1o, 2o, 3o e 4o",
    "Mantem as aliquotas reduzidas ate 30/6/2009.")
ato("ipi_2009_dec6890", "ipi", "decreto", "6.890", "2009-06-29", "2009-06-30", "2009-07-01",
    "2009-12-31", "ipi_2009_dec6809", "prorroga", "automoveis ate 2.000 cm3 e comerciais leves",
    "dec_6890_2009",
    "Ficam fixadas nos percentuais e datas indicados nos Anexos III, V, VI e VIII as alíquotas",
    "Mantem as aliquotas ate 30/9/2009 e as eleva mes a mes de outubro a dezembro de 2009 "
    "(Anexos VI e VII); gasolina volta a' aliquota cheia em 1/1/2010. Vigencia a partir de "
    "1/7/2009, mes seguinte ao fim do Decreto 6.809 (o decreto vigora na publicacao, 30/6/2009).")
ato("ipi_2009_dec7017", "ipi", "decreto", "7.017", "2009-11-26", "2009-11-27", "2009-12-01",
    "2010-03-31", "ipi_2009_dec6890", "prorroga", "automoveis flex ou a alcool ate 2.000 cm3",
    "dec_7017_2009",
    "produzindo efeitos a partir de 1o de dezembro de 2009",
    "Flex ate 1.000 cm3 a 3% e de 1.000 a 2.000 cm3 a 7,5% ate 31/3/2010; aliquota cheia a "
    "partir de 1/4/2010.")

# ------------------------------------------------------------------ IPI 2011-2014
ato("ipi_2011_mp540", "ipi", "medida provisoria", "540", "2011-08-02", "2011-08-03",
    "2011-08-03", "2016-07-31", "", "cria",
    "IPI do setor automotivo condicionado a conteudo regional e investimento",
    "mpv_540_2011",
    "dispõe sobre a redução do Imposto sobre Produtos Industrializados - IPI à indústria automot"
    " [...] II - poderá ser usufruída até 31 de julho de 2016",
    "Base legal do Decreto 7.567/2011. Fim: o prazo da reducao no texto original (art. 5o, "
    "par. 1o, II). Convertida na Lei 12.546/2011, que nao foi guardada.")
ato("ipi_2011_dec7567", "ipi", "decreto", "7.567", "2011-09-15", "2011-09-16", "2011-12-16",
    "2012-12-31", "ipi_2011_mp540", "aumenta",
    "automoveis e comerciais leves de empresa nao habilitada (sem 65% de conteudo regional)",
    "dec_7567_2011",
    "De 16 de dezembro de 2011 a 31 de dezembro de 2012",
    "Mais 30 pontos na TIPI para 8703 e 8704 leve; a empresa habilitada tem a reducao de 30 "
    "pontos. Efeito a partir de 16/12/2011 pela redacao do Decreto 7.604/2011.")
ato("ipi_2012_dec7725", "ipi", "decreto", "7.725", "2012-05-21", "2012-05-22", "2012-05-22",
    "2012-08-31", "", "reduz", "automoveis ate 2.000 cm3 e comerciais leves", "dec_7725_2012",
    "De 22 de maio até 31 de agosto de 2012",
    "Na TIPI com os 30 pontos do Decreto 7.567: 1.000 cm3 de 37 para 30; flex de 1.000 a "
    "2.000 cm3 de 41 para 35,5.")
ato("ipi_2012_dec7796", "ipi", "decreto", "7.796", "2012-08-30", "2012-08-31", "2012-09-01",
    "2012-10-31", "ipi_2012_dec7725", "prorroga", "os mesmos veiculos do Decreto 7.725",
    "dec_7796_2012", "Até 31/10/2012 De 1º /11/2012 até 31/12/2012")
ato("ipi_2012_dec7834", "ipi", "decreto", "7.834", "2012-10-31", "2012-11-01", "2012-11-01",
    "2012-12-31", "ipi_2012_dec7796", "prorroga", "os mesmos veiculos do Decreto 7.725",
    "dec_7834_2012", "NOTA COMPLEMENTAR NC (87-4) DA TIPI Até 31 de dezembro de 2012")
ato("ipi_2013_dec7879", "ipi", "decreto", "7.879", "2012-12-27", "2012-12-28", "2013-01-01",
    "2013-06-30", "ipi_2012_dec7834", "prorroga", "automoveis e comerciais leves",
    "dec_7879_2012",
    "De 1º /01/2013 até 31/03/2013 De 1º /04/2013 até 30/06/2013 De 1º /07/2013 até 31/12/2017",
    "Retorno gradual: 1.000 cm3 a 32 (jan-mar) e 33,5 (abr-jun); flex a 37 e 39; cheia (37 e "
    "41) a partir de 1/7/2013. Aliquotas da TIPI com os 30 pontos do Inovar-Auto.")
ato("ipi_2013_dec7971", "ipi", "decreto", "7.971", "2013-03-28", "2013-04-01", "2013-04-01",
    "2013-12-31", "ipi_2013_dec7879", "prorroga", "automoveis e comerciais leves",
    "dec_7971_2013", "De 1º /04/2013 até 31/12/2013 De 1º /01/2014 até 31/12/2017",
    "Mantem 1.000 cm3 a 32 e flex a 37 ate 31/12/2013.")
ato("ipi_2014_dec8168", "ipi", "decreto", "8.168", "2013-12-23", "2013-12-24", "2014-01-01",
    "2014-06-30", "ipi_2013_dec7971", "prorroga", "automoveis e comerciais leves",
    "dec_8168_2013", "De 1º /1/2014 até 30/6/2014 De 1º /7/2014 até 31/12/2017",
    "1.000 cm3 a 33 e flex a 39 ate 30/6/2014.")
ato("ipi_2014_dec8279", "ipi", "decreto", "8.279", "2014-06-30", "2014-07-01", "2014-07-01",
    "2014-12-31", "ipi_2014_dec8168", "prorroga", "automoveis e comerciais leves",
    "dec_8279_2014", "De 1º /7/2014 até 31/12/2014 De 1º /1/2015 até 31/12/2017",
    "1.000 cm3 a 33 e flex a 39 ate 31/12/2014; aliquota cheia (37 e 41) a partir de 1/1/2015.")

# ------------------------------------------------------------------ IPI 2018-2025
ato("ipi_2018_dec9442", "ipi", "decreto", "9.442", "2018-07-05", "2018-07-06", "2018-11-01", "",
    "", "reduz", "automoveis hibridos e eletricos (8703.40, 8703.60, 8703.80)", "dec_9442_2018",
    "Este Decreto entra em vigor a partir do primeiro dia do quarto mês subsequente ao de sua "
    "publicação",
    "Aliquota pela eficiencia energetica e pela massa: 9% a 20% (hibridos), 7% a 18% "
    "(eletricos). Vigencia em 1/11/2018: quarto mes depois de julho de 2018. As aliquotas do "
    "proprio ato valem ate' 24/2/2022; dai' em diante a estrutura segue com as reducoes gerais "
    "da TIPI (10.979, 11.055, 11.158), cujas aliquotas para 8703.40/60/80 nao foram registradas. "
    "Fim do ato nao confirmado em pagina aberta.")
ato("ipi_2022_dec10979", "ipi", "decreto", "10.979", "2022-02-25", "2022-02-25", "2022-02-25",
    "2022-04-30", "", "reduz", "toda a TIPI; 18,5% na posicao 87.03", "dec_10979_2022",
    "I - 18,5% (dezoitos inteiros e cinco décimos por cento) para os produtos classificados nos "
    "códigos da posição 87.03",
    "Revogado a partir de 1/5/2022 pelo Decreto 11.055, que mantem a reducao de 18,5% nos "
    "automoveis.")
ato("ipi_2022_dec11055", "ipi", "decreto", "11.055", "2022-04-28", "2022-04-29", "2022-05-01",
    "2022-07-31", "ipi_2022_dec10979", "reduz", "toda a TIPI; automoveis com a reducao de 18,5%",
    "dec_11055_2022",
    "produz efeitos a partir de 1º de maio de 2022",
    "As aliquotas de 87.03 estao no anexo (dec_11055_2022_anexo): flex de 1.000 a 1.500 cm3 a "
    "8,97, como no Decreto 10.979.")
ato("ipi_2022_dec11158", "ipi", "decreto", "11.158", "2022-07-29", "2022-07-29", "2022-08-01", "",
    "ipi_2022_dec11055", "reduz", "toda a TIPI; automoveis com aliquotas novas",
    "dec_11158_2022",
    "produz efeitos a partir de 1º de agosto de 2022",
    "Nova TIPI: 1.000 cm3 a 5,27; gasolina de 1.000 a 2.000 cm3 a 9,78; flex a 8,28 "
    "(anexo dec_11158_2022_anexo4).")
ato("ipi_2025_dec12549", "ipi", "decreto", "12.549", "2025-07-10", "2025-07-11", "2025-11-01", "",
    "ipi_2022_dec11158", "regulamenta", "automoveis e comerciais leves (IPI Verde do Mover)",
    "dec_12549_2025",
    "II - no primeiro dia do quarto mês subsequente ao de sua publicação, quanto aos demais "
    "dispositivos",
    "Aliquota base de 6,30% em 8703 e 3,90% no 8704 leve, com acrescimos e decrescimos por "
    "fonte de energia, eficiencia e reciclabilidade; o Carro Sustentavel (NC 87-15) vale da "
    "publicacao (11/7/2025). Vigencia geral em 1/11/2025: quarto mes depois de julho.")

# ------------------------------------------------------------- regimes automotivos
ato("regime_2012_lei12715", "regime_automotivo", "lei", "12.715", "2012-09-17", "2012-09-18",
    "2013-01-01", "2017-12-31", "", "cria", "Inovar-Auto: automoveis, caminhoes, onibus, autopecas",
    "lei_12715_2012", "O Inovar-Auto aplicar-se-á até 31 de dezembro de 2017",
    "Vigencia de 2013 a 2017 pelo Decreto 7.819/2012, que regulamenta.")
ato("regime_2012_dec7819", "regime_automotivo", "decreto", "7.819", "2012-10-03", "2012-10-03",
    "2013-01-01", "2017-12-31", "regime_2012_lei12715", "regulamenta", "Inovar-Auto",
    "dec_7819_2012", "O INOVAR-AUTO será aplicado até 31 de dezembro de 2017")
ato("regime_2018_mp843", "regime_automotivo", "medida provisoria", "843", "2018-07-05",
    "2018-07-06", "2018-07-06", "2018-12-10", "", "cria",
    "Rota 2030: automoveis, caminhoes, onibus, chassis com motor, autopecas", "mpv_843_2018",
    "Fica instituído o Programa Rota 2030 - Mobilidade e Logística [...] Convertida na Lei nº "
    "13.755, de 2018",
    "Fim na data da lei de conversao (13.755, de 10/12/2018).")
ato("regime_2018_lei13755", "regime_automotivo", "lei", "13.755", "2018-12-10", "2018-12-11",
    "2018-12-11", "2023-12-30", "regime_2018_mp843", "cria", "Rota 2030", "lei_13755_2018",
    "Art. 7º Fica instituído o Programa Rota 2030 - Mobilidade e Logística",
    "Fim: revogacao dos artigos do programa pela MP 1.205, de 30/12/2023 (vigencia encerrada).")
ato("regime_2023_mp1205", "regime_automotivo", "medida provisoria", "1.205", "2023-12-30",
    "2023-12-30", "2023-12-30", "2024-06-27", "regime_2018_lei13755", "cria", "Mover",
    "mpv_1205_2023",
    "Institui o Programa Mobilidade Verde e Inovação - Programa MOVER",
    "Fim na data da lei de conversao (14.902, de 27/6/2024).")
ato("regime_2024_lei14902", "regime_automotivo", "lei", "14.902", "2024-06-27", "2024-06-28",
    "2024-06-28", "", "regime_2023_mp1205", "cria", "Mover", "lei_14902_2024",
    "Institui o Programa Mobilidade Verde e Inovação (Programa Mover)",
    "Os creditos dos arts. 15 a 20 tem prazo de 5 anos.")

# -------------------------------------------------------- imposto de importacao
ato("ii_2014_camex86", "imposto_importacao", "resolucao", "Camex 86", "2014-09-18", "2014-09-19",
    "2014-09-19", "2015-10-26", "", "reduz",
    "hibridos sem recarga externa (8703.22.10 e 8703.23.10, Ex)",
    "camex_86_2014_dou", "RESOLUÇÃO No- 86, DE 18 DE SETEMBRO DE 2014",
    "Ex-tarifarios de hibridos a 0% (desmontado), 2%, 4%, 5% e 7%, conforme o consumo "
    "energetico; vigor na publicacao (pagina camex_86_2014_dou_p21). Fim: a Camex 97 da' nova "
    "redacao aos mesmos Ex a partir de 27/10/2015.")
ato("ii_2015_camex97", "imposto_importacao", "resolucao", "Camex 97", "2015-10-26", "2015-10-27",
    "2015-10-27", "2023-12-31", "ii_2014_camex86", "reduz",
    "eletricos e a celula de combustivel (8703.90.00, Ex) e hibridos com recarga externa",
    "camex_97_2015_dou_p1", "RESOLUÇÃO No- 97, DE 26 DE OUTUBRO DE 2015",
    "Eletricos a 0% (Ex 001 a 006 de 8703.90.00, autonomia de 80 km ou mais); os Ex de "
    "hibridos passam a incluir recarga externa. Vigor na publicacao (camex_97_2015_dou_p3). "
    "Fim INFERIDO: a Gecex 532 tira os eletrificados do Anexo V da Gecex 272/2021 a partir de "
    "1/1/2024; a passagem dos Ex da Camex 97 para a Gecex 272 (e a mudanca de NCM de 2017) nao "
    "foi aberta.")
ato("ii_2023_gecex532", "imposto_importacao", "resolucao", "Gecex 532", "2023-11-20", "2023-11-23",
    "2024-01-01", "", "ii_2015_camex97", "aumenta",
    "hibridos, hibridos plug-in e eletricos (8703.40, 8703.60, 8703.80, 8704.60)",
    "gecex_532_2023",
    "Ficam excluídos do Anexo V da Resolução Gecex nº 272, de 19 de novembro de 2021, a partir "
    "de 1º de janeiro de 2024",
    "Degraus para o montado: hibrido 15/25/30%, plug-in 12/20/28%, eletrico 10/18/25% em "
    "jan/2024, jul/2024 e jul/2025, e TEC de 35% a partir de jul/2026; desmontado com "
    "degraus proprios; quotas a 0% por empresa ate jun/2026.")
ato("ii_2025_gecex774", "imposto_importacao", "resolucao", "Gecex 774", "2025-07-30", "2025-07-31",
    "2025-07-31", "2026-12-31", "ii_2023_gecex532", "aumenta",
    "eletrificados desmontados (CKD) e semidesmontados (SKD)", "gecex_774_2025",
    "8703.80.00 007 14 Automóvel desmontado",
    "Antecipa para 31/12/2026 o fim da aliquota de 14% do desmontado (era 30/6/2028); cria "
    "quotas a 0% para CKD e SKD de 1/8/2025 a 31/1/2026. A tabela repete os Ex de desmontado "
    "com inicio em 1/7/2025; na tabela de aliquotas eles comecam em 31/7/2025, quando o ato "
    "entra em vigor, e a linha da Gecex 532 para na vespera.")
ato("ii_2026_gecex927", "imposto_importacao", "resolucao", "Gecex 927", "2026-06-29", "2026-06-30",
    "2026-07-01", "2026-12-31", "ii_2025_gecex774", "reduz",
    "eletrificados desmontados ou semidesmontados, no ACE-14", "gecex_927_2026",
    "84.500.000 US$ (FOB) 01/07/2026 31/12/2026",
    "Novas quotas a 0% (US$ 84,5 mi hibrido, 281 mi plug-in, 97,5 mi eletrico) de jul a dez/2026.")

# --------------------------------------------------------- acordos automotivos
ato("acordo_2012_mex_dec7706", "acordo_automotivo", "decreto", "7.706", "2012-03-29", "2012-03-30",
    "2012-03-19", "2015-03-18", "", "cria", "importacao de veiculos leves do Mexico (ACE-55)",
    "dec_7706_2012",
    "De 19 de março de 2012 a 18 de março de 2013 US$ 1,450 bilhão",
    "Quotas anuais a tarifa zero: US$ 1,450, 1,560 e 1,640 bilhao; livre comercio previsto "
    "para 19/3/2015.")
ato("acordo_2015_mex_dec8419", "acordo_automotivo", "decreto", "8.419", "2015-03-18", "2015-03-19",
    "2015-03-19", "2019-03-18", "acordo_2012_mex_dec7706", "prorroga", "ACE-55 com o Mexico",
    "dec_8419_2015", "A partir de 19 de março de 2019 Livre Comércio",
    "Quotas de 2015 a 2019; livre comercio a partir de 19/3/2019.")
ato("acordo_2008_arg_dec6500", "acordo_automotivo", "decreto", "6.500", "2008-07-02", "2008-07-03",
    "2008-07-03", "2013-06-30", "", "regulamenta", "comercio automotivo com a Argentina (ACE-14)",
    "dec_6500_2008",
    "coeficiente de desvio sobre as exportações anual – flex – não superior a 1,95",
    "Flex de 1,95 (Brasil superavitario); livre comercio previsto para 1/7/2013.")
ato("acordo_2014_arg_dec8278", "acordo_automotivo", "decreto", "8.278", "2014-06-27", "2014-06-30",
    "2014-07-01", "2015-06-30", "acordo_2008_arg_dec6500", "prorroga", "ACE-14 com a Argentina",
    "dec_8278_2014",
    "de 1º de julho de 2014 a 30 de junho de 2015",
    "Flex de 1,5.")
ato("acordo_2015_arg_dec8477", "acordo_automotivo", "decreto", "8.477", "2015-06-30", "2015-07-01",
    "2015-07-01", "2016-06-30", "acordo_2014_arg_dec8278", "prorroga", "ACE-14 com a Argentina",
    "dec_8477_2015",
    "flex - não superior a 1,5", "Flex de 1,5 ate 30/6/2016.")
ato("acordo_2016_arg_dec8797", "acordo_automotivo", "decreto", "8.797", "2016-06-30", "2016-07-01",
    "2016-07-01", "2020-06-30", "acordo_2015_arg_dec8477", "prorroga", "ACE-14 com a Argentina",
    "dec_8797_2016",
    "para o período de 1º de julho de 2016 a 30 de junho de 2020",
    "Flex de 1,50.")
ato("acordo_2020_arg_dec10343", "acordo_automotivo", "decreto", "10.343", "2020-05-08", "2020-05-11",
    "2020-07-01", "2029-06-30", "acordo_2016_arg_dec8797", "prorroga", "ACE-14 com a Argentina",
    "dec_10343_2020",
    "A partir de 1º de julho de 2029, o intercâmbio de produtos automotivos entre as Partes se "
    "regerá pelo livre comércio",
    "Flex de 1,8 (jul/2020-jun/2023), 1,9, 2, 2,5 e 3; livre comercio a partir de 1/7/2029.")

# ------------------------------------------------------------------- credito
ato("credito_2008_iof_dec6339", "credito", "decreto", "6.339", "2008-01-03", "2008-01-03",
    "2008-01-03", "2008-12-11", "", "aumenta", "IOF do credito a pessoa fisica", "dec_6339_2008",
    "pessoa física: 0,0082% ao dia", "IOF diario de 0,0041% para 0,0082%.")
ato("credito_2008_iof_dec6691", "credito", "decreto", "6.691", "2008-12-11", "2008-12-12",
    "2008-12-12", "2011-04-08", "credito_2008_iof_dec6339", "reduz", "IOF do credito a pessoa fisica",
    "dec_6691_2008", "pessoa física: 0,0041% ao dia", "IOF diario volta a 0,0041%.")
ato("credito_2011_iof_dec7458", "credito", "decreto", "7.458", "2011-04-07", "2011-04-08",
    "2011-04-09", "2011-12-01", "credito_2008_iof_dec6691", "aumenta", "IOF do credito a pessoa fisica",
    "dec_7458_2011",
    "pessoa física: 0,0082% ao dia [...] produzindo efeitos a partir do dia seguinte à data de "
    "sua publicação",
    "Efeito no dia seguinte a' publicacao (8/4/2011).")
ato("credito_2011_iof_dec7632", "credito", "decreto", "7.632", "2011-12-01", "2011-12-01",
    "2011-12-02", "2012-05-22", "credito_2011_iof_dec7458", "reduz", "IOF do credito a pessoa fisica",
    "dec_7632_2011",
    "pessoa física: 0,0068% ao dia [...] a partir do dia seguinte à data de sua publicação",
    "Efeito no dia seguinte a' publicacao (1/12/2011, edicao extra).")
ato("credito_2012_iof_dec7726", "credito", "decreto", "7.726", "2012-05-21", "2012-05-22",
    "2012-05-23", "2015-01-21", "credito_2011_iof_dec7632", "reduz",
    "IOF do credito a pessoa fisica", "dec_7726_2012", "entra em vigor no dia 23 de maio de 2012",
    "IOF diario volta a 0,0041%.")
ato("credito_2015_iof_dec8392", "credito", "decreto", "8.392", "2015-01-20", "2015-01-21",
    "2015-01-22", "", "credito_2012_iof_dec7726", "aumenta", "IOF do credito a pessoa fisica",
    "dec_8392_2015",
    "mutuário pessoa física: 0,0082% ao dia [...] Este Decreto entra em vigor um dia após a data "
    "de sua publicação [...] publicado no DOU de 21.1.2015",
    "IOF diario de 0,0041% para 0,0082%. Mudancas posteriores do IOF nao foram procuradas.")
ato("credito_2010_bcb_circ3515", "credito", "circular", "BCB 3.515", "2010-12-03", "2010-12-03",
    "2010-12-06", "2011-11-11", "", "aumenta",
    "financiamento de veiculo a pessoa fisica com prazo acima de 24 meses", "bcb_circular_3515",
    "Deve ser aplicado FPR de 150% (cento e cinquenta por cento) às exposições relativas a "
    "operações de crédito",
    "Fator de ponderacao de 150% no capital para credito a pessoa fisica contratado a partir de "
    "6/12/2010 com prazo acima de 24 meses; veiculo isento conforme prazo e entrada.")
ato("credito_2011_bcb_circ3563", "credito", "circular", "BCB 3.563", "2011-11-11", "2011-11-11",
    "2011-11-11", "", "credito_2010_bcb_circ3515", "reduz",
    "financiamento de veiculo a pessoa fisica", "bcb_circular_3563",
    "III - financiamento com prazo contratual de até sessenta meses para aquisição de veículo "
    "automotor",
    "Isenta do fator de 150% o financiamento de veiculo de ate 60 meses.")

# -------------------------------------------------------------- programa direto
ato("programa_2023_mp1175", "programa_desconto", "medida provisoria", "1.175", "2023-06-05",
    "2023-06-06", "2023-06-06", "2023-10-03", "", "cria",
    "automoveis e comerciais leves sustentaveis de ate R$ 120 mil, caminhoes e onibus",
    "mpv_1175_2023",
    "R$ 800.000.000,00 (oitocen [...] será aplicável pelo prazo de cento e vinte dias, contado da "
    "data de entrada em vigor desta Medida Provisória",
    "Desconto patrocinado ate o limite dos recursos (R$ 800 milhoes para carros, depois da "
    "ampliacao). Fim: 120 dias a partir da vigencia (6/6 a 3/10/2023). O fim da quota de carros (7/7/2023, segundo noticia do MDIC) nao foi "
    "confirmado em pagina oficial aberta: as noticias do gov.br pedem autenticacao.")
ato("programa_2023_portaria151", "programa_desconto", "portaria", "GM/MDIC 151", "2023-06-06",
    "2023-06-07", "2023-06-07", "2023-10-03", "programa_2023_mp1175", "regulamenta",
    "habilitacao das montadoras ao desconto patrocinado", "portaria_mdic_151_2023_dou",
    "PORTARIA GM/MDIC Nº 151, DE 6 DE JUNHO DE 2023",
    "Fim junto com o prazo da MP 1.175.")

# ------------------------------------------------------------------ regulacao
ato("regulacao_2014_contran311", "regulacao", "resolucao", "Contran 311", "2009-04-03", "",
    "2014-01-01", "", "", "cria", "air bag frontal em automoveis e comerciais leves (M1 e N1)",
    "contran_311_2009", "01 de janeiro de 2014 100%",
    "Cronograma por percentual da producao desde 2010; 100% em 1/1/2014 (a data do calendario).")
ato("regulacao_2014_contran312", "regulacao", "resolucao", "Contran 312", "2009-04-03", "",
    "2014-01-01", "", "", "cria", "freio ABS em veiculos novos", "contran_312_2009",
    "A partir de 01 de janeiro de 2014, todos os veículos novos, saídos de fábrica, nacionais e "
    "importados, somente serão registrados e licenciados se dispuserem de sistema de "
    "antitravamento de rodas – ABS",
    "Cronograma por percentual da producao desde 2010; 100% em 1/1/2014.")
ato("regulacao_2022_conama492_l7", "regulacao", "resolucao", "Conama 492 (L7)", "2018-12-20",
    "2018-12-24", "2022-01-01", "2024-12-31", "", "cria",
    "limites de emissao de veiculos leves (Proconve L7)", "conama_492_2018",
    "Art. 1º Estabelecer, a partir de 1º de janeiro de 2022, novos limites máximos de emissão",
    "Uma linha por fase: a mesma resolucao fixa a L8 em 2025.")
ato("regulacao_2025_conama492_l8", "regulacao", "resolucao", "Conama 492 (L8)", "2018-12-20",
    "2018-12-24", "2025-01-01", "", "regulacao_2022_conama492_l7", "cria",
    "limites de emissao de veiculos leves (Proconve L8)", "conama_492_2018",
    "a partir de 1º de janeiro de 2025",
    "Uma linha por fase da mesma resolucao.")



POR_ID = {a["id"]: a for a in A}

# ================================================================== aliquotas

R = []


def linha(tributo, ncm, categoria, ini, fim, aliq, ato, trecho, pagina=None):
    R.append(dict(tributo=tributo, ncm=ncm, categoria=categoria, vigencia_inicio=ini,
                  vigencia_fim=fim, aliquota_pct=aliq, ato_id=ato,
                  pagina_salva=pagina or POR_ID[ato]["pagina_salva"], fonte_trecho=trecho))


C1 = "ate 1.000 cm3"
C1F = "ate 1.000 cm3, flex ou alcool"
C2G = "gasolina, 1.000 a 1.500 cm3, ate 6 passageiros"
C3G = "gasolina, 1.500 a 2.000 cm3, ate 6 passageiros (Ex 01)"
C4G = "gasolina, 1.500 a 3.000 cm3, ate 6 passageiros"
C2F = "flex ou alcool, 1.000 a 1.500 cm3"
C3F = "flex ou alcool, 1.500 a 2.000 cm3, ate 6 passageiros (Ex 01)"
C4F = "flex ou alcool, 1.500 a 3.000 cm3, ate 6 passageiros, acima de 2.000 cm3"
NC_FLEX_2008 = ("NC (87-2) Ficam fixadas nos percentuais indicados as alíquotas referentes aos "
                "automóveis de passageiros e veículos de uso misto, com motor a álcool")

# ---------------------------------------------------------------- 2008-2010
a, i, f = "ipi_2008_dec6687", "2008-12-12", "2009-03-31"
linha("ipi", "8703.21.00", C1, i, f, "0", a, "ANEXO I Código TIPI Alíquota (%) 8703.21.00 0")
linha("ipi", "8703.22.10", C2G, i, f, "6,5", a, "8703.21.00 0 8703.22.10 6,5")
linha("ipi", "8703.23.10 Ex 01", C3G, i, f, "6,5", a, "8703.23.10 Ex 01 6,5")
linha("ipi", "8703.22", C2F, i, f, "5,5", a, f"{NC_FLEX_2008} [...] 8703.22 5,5")
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "5,5", a, f"{NC_FLEX_2008} [...] 8703.23.10 Ex 01 5,5")
linha("ipi", "8703.23.10", C4F, i, f, "18", a, f"{NC_FLEX_2008} [...] 8703.23.10 18")

a, i, f = "ipi_2009_dec6809", "2009-04-01", "2009-06-30"
linha("ipi", "8703.21.00", C1, i, f, "0", a, "ANEXO II Código TIPI [...] 8703.21.00 0")
linha("ipi", "8703.22.10", C2G, i, f, "6,5", a, "8703.21.00 0 8703.22.10 6,5")
linha("ipi", "8703.23.10 Ex 01", C3G, i, f, "6,5", a, "8703.23.10 Ex 01 6,5")
linha("ipi", "8703.22", C2F, i, f, "5,5", a, "ANEXO IV “NC (87-2) Ficam fixadas [...] 8703.22 5,5")
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "5,5", a, "8703.23.10 Ex 01 5,5")
linha("ipi", "8703.23.10", C4F, i, f, "18", a, "8703.23.10 18")

a = "ipi_2009_dec6890"
for cab, ini, fim, v1, v2 in [
        ("Até 30 de setembro de 2009", "2009-07-01", "2009-09-30", "0", "6,5"),
        ("De 1o a 31 de outubro de 2009", "2009-10-01", "2009-10-31", "1,5", "8,0"),
        ("De 1o a 30 de novembro de 2009", "2009-11-01", "2009-11-30", "3,0", "9,5"),
        ("De 1o a 31 de dezembro de 2009", "2009-12-01", "2009-12-31", "5,0", "11,0"),
        ("A partir de 1o de janeiro de 2010", "2010-01-01", "2011-12-15", "7", "13")]:
    bloco = f"{cab} NCM ALÍQUOTA (%) 8703.21.00 {v1} 8703.22.10 {v2}"
    linha("ipi", "8703.21.00", C1 + ", gasolina", ini, fim, v1, a, bloco)
    linha("ipi", "8703.22.10", C2G, ini, fim, v2, a, bloco)
    linha("ipi", "8703.23.10 Ex 01", C3G, ini, fim, v2, a,
          f"{bloco} 8703.22.90 {v2} 8703.23.10 Ex 01 {v2}")
for cab, ini, fim, v in [("Até 30 de setembro de 2009 “NC (87-2)", "2009-07-01", "2009-09-30", "5,5"),
                         ("De 1oa 31 de outubro de 2009 NC (87-2)", "2009-10-01", "2009-10-31", "6,5"),
                         ("De 1o a 30 de novembro de 2009 NC (87-2)", "2009-11-01", "2009-11-30", "7,5")]:
    linha("ipi", "8703.22", C2F, ini, fim, v, a, f"{cab} [...] 8703.22 {v} 8703.23.10 18")
    linha("ipi", "8703.23.10 Ex 01", C3F, ini, fim, v, a, f"{cab} [...] 8703.23.10 Ex 01 {v}")

a = "ipi_2009_dec7017"
for cab, ini, fim, v1, v2 in [("De 1o a 31 de dezembro de 2009:", "2009-12-01", "2009-12-31", "3", "7,5"),
                              ("De 1o de janeiro a 31 de março de 2010:", "2010-01-01", "2010-03-31", "3", "7,5"),
                              ("A partir de 1o de abril de 2010:", "2010-04-01", "2011-12-15", "7", "11")]:
    linha("ipi", "8703.21", C1F, ini, fim, v1, a, f"{cab} [...] 8703.21 {v1} 8703.22 {v2}")
    linha("ipi", "8703.22", C2F, ini, fim, v2, a, f"{cab} [...] 8703.21 {v1} 8703.22 {v2}")
    linha("ipi", "8703.23.10 Ex 01", C3F, ini, fim, v2, a, f"{cab} [...] 8703.23.10 Ex 01 {v2}")

# ---------------------------------------------------------------- 2011-2014
# as faixas que o Decreto 7.725 reduz a partir de 22/5/2012 param na vespera
a, i, f = "ipi_2011_dec7567", "2011-12-16", "2012-12-31"
v = "2012-05-21"
cab = "De 16 de dezembro de 2011 a 31 de dezembro de 2012"
linha("ipi", "8703.21.00", C1, i, v, "37", a, f"{cab} [...] 8703.21.00 37")
linha("ipi", "8703.22.10", C2G, i, v, "43", a, f"{cab} [...] 8703.22.10 43")
linha("ipi", "8703.23.10", C4G, i, f, "55", a, f"{cab} [...] 8703.23.10 55")
linha("ipi", "8703.22", C2F, i, v, "41", a, f"{cab}: NC (87-2) [...] 8703.22 41")
linha("ipi", "8703.23.10 Ex 01", C3F, i, v, "41", a, f"{cab}: NC (87-2) [...] 8703.23.10 Ex 01 41")

# gasolina ate 1.000 cm3 na NC (87-7) dos tres decretos de 2012 (tabela em duas colunas:
# 8703.21.00 fica ao lado de 8704.21.90 Ex 02)
for a, i, f in (("ipi_2012_dec7725", "2012-05-22", "2012-08-31"),
                ("ipi_2012_dec7796", "2012-09-01", "2012-10-31"),
                ("ipi_2012_dec7834", "2012-11-01", "2012-12-31")):
    linha("ipi", "8703.21.00", C1 + ", gasolina", i, f, "30", a,
          "NOTA COMPLEMENTAR NC (87-7) DA TIPI Até [...] 8703.21.00 30 8704.21.90 Ex 02 5")

a, i, f = "ipi_2012_dec7725", "2012-05-22", "2012-08-31"
cab = "De 22/05/2012 até 31/08/2012"
linha("ipi", "8703.21.00", C1F, i, f, "30", a, f"{cab} [...] 8703.21.00 37 30 37 7")
linha("ipi", "8703.22", C2F, i, f, "35,5", a, f"{cab} [...] 8703.22 41 35,5 41 11")
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "35,5", a, f"{cab} [...] 8703.23.10 Ex 01 41 35,5 41 11")
linha("ipi", "8703.22.10", C2G, i, f, "36,5", a,
      "De 22 de maio até 31 de agosto de 2012 [...] 8703.22.10 36,5")

a, i, f = "ipi_2012_dec7796", "2012-09-01", "2012-10-31"
cab = "Até 31/10/2012 De 1º /11/2012 até 31/12/2012"
linha("ipi", "8703.21.00", C1F, i, f, "30", a, f"{cab} [...] 8703.21.00 30 37 7")
linha("ipi", "8703.22", C2F, i, f, "35,5", a, f"{cab} [...] 8703.22 35,5 41 11")
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "35,5", a, f"{cab} [...] 8703.23.10 Ex 01 35,5 41 11")
linha("ipi", "8703.22.10", C2G, i, f, "36,5", a, "NOTA COMPLEMENTAR NC (87-7) DA TIPI Até [...] 8703.22.10 36,5")

a, i, f = "ipi_2012_dec7834", "2012-11-01", "2012-12-31"
cab = "Código TIPI Alíquota (%) 8703.21.00 30 8703.22 35,5"
linha("ipi", "8703.21.00", C1F, i, f, "30", a, cab)
linha("ipi", "8703.22", C2F, i, f, "35,5", a, cab)
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "35,5", a, "8703.23.10 Ex 01 35,5")
linha("ipi", "8703.22.10", C2G, i, f, "36,5", a, "8703.22.10 36,5")

a, i, f = "ipi_2013_dec7879", "2013-01-01", "2013-03-31"
cab = "De 1º /01/2013 até 31/03/2013 De 1º /04/2013 até 30/06/2013"
linha("ipi", "8703.21", C1F, i, f, "32", a, f"{cab} [...] 8703.21 32 33,5 37 7")
linha("ipi", "8703.22", C2F, i, f, "37", a, f"{cab} [...] 8703.22 37 39 41 11")
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "37", a, f"{cab} [...] 8703.23.10 Ex 01 37 39 41 11")

a, i, f = "ipi_2013_dec7971", "2013-04-01", "2013-12-31"
cab = "De 1º /04/2013 até 31/12/2013 De 1º /01/2014 até 31/12/2017"
linha("ipi", "8703.21", C1F, i, f, "32", a, f"{cab} [...] 8703.21 32 37 7")
linha("ipi", "8703.22", C2F, i, f, "37", a, f"{cab} [...] 8703.22 37 41 11")
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "37", a, f"{cab} [...] 8703.23.10 Ex 01 37 41 11")

a, i, f = "ipi_2014_dec8168", "2014-01-01", "2014-06-30"
cab = "De 1º /1/2014 até 30/6/2014 De 1º /7/2014 até 31/12/2017"
linha("ipi", "8703.21", C1F, i, f, "33", a, f"{cab} [...] 8703.21 33 37 7")
linha("ipi", "8703.22", C2F, i, f, "39", a, f"{cab} [...] 8703.22 39 41 11")
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "39", a, f"{cab} [...] 8703.23.10 Ex 01 39 41 11")

a = "ipi_2014_dec8279"
cab = "De 1º /7/2014 até 31/12/2014 De 1º /1/2015 até 31/12/2017 A partir de 1º /1/2018"
for ini, fim, v1, v2 in [("2014-07-01", "2014-12-31", "33", "39"), ("2015-01-01", "2017-12-31", "37", "41"),
                         ("2018-01-01", "2022-02-24", "7", "11")]:
    linha("ipi", "8703.21", C1F, ini, fim, v1, a, f"{cab} [...] 8703.21 33 37 7")
    linha("ipi", "8703.22", C2F, ini, fim, v2, a, f"{cab} [...] 8703.22 39 41 11")
    linha("ipi", "8703.23.10 Ex 01", C3F, ini, fim, v2, a, f"{cab} [...] 8703.23.10 Ex 01 39 41 11")

# ---------------------------------------------------------------- 2018-2025
a = "ipi_2018_dec9442"
t = texto(POR_ID[a]["pagina_salva"])
inicio_nc = t.index("NC (87-6) Ficam fixadas")
for codigos, rotulo, bloco_ini, bloco_fim in [
        (("8703.40.00", "8703.60.00"), "hibrido (sem e com recarga externa)",
         "8703.40.00 e 8703.60.00 EE", "8703.80.00 EE"),
        (("8703.80.00",), "eletrico", "8703.80.00 EE", "Ficam reduzidas em dois pontos")]:
    i0 = t.index(bloco_ini, inicio_nc)
    bloco = t[i0:t.index(bloco_fim, i0 + 5)]
    for faixa in re.finditer(r"(EE [^M]+?) (MOM menor ou igual a 1400 (\d+) MOM maior que 1400 e "
                             r"menor ou igual a 1700 (\d+) MOM maior que 1700 (\d+))", bloco):
        ee = faixa.group(1)
        for mom, valor in zip(("massa ate 1400 kg", "massa de 1400 a 1700 kg", "massa acima de 1700 kg"),
                              faixa.group(3, 4, 5)):
            for codigo in codigos:
                linha("ipi", codigo, f"{rotulo}, {ee} MJ/km, {mom}", "2018-11-01", "2022-02-24",
                      valor, a, f"{ee} {faixa.group(2)}")

a, i, f = "ipi_2022_dec10979", "2022-02-25", "2022-04-30"
cab = "(flexible fuel engine), classificados nos códigos a seguir especificados: CÓDIGO DA TIPI ALÍQUOTA % 8703.22 8,965"
linha("ipi", "8703.22", C2F, i, f, "8,965", a, cab)
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "8,965", a, "8703.23.10 Ex 01 8,965")
linha("ipi", "8703.23.10", C4F, i, f, "14,67", a, "8703.22 8,965 8703.23.10 14,67")

a, i, f = "ipi_2022_dec11055", "2022-05-01", "2022-07-31"
p = "dec_11055_2022_anexo"
linha("ipi", "8703.21.00", C1, i, f, "5,71", a, "8703.21.00 -- De cilindrada não superior a 1.000 cm3 5,71", p)
linha("ipi", "8703.22.10", C2G, i, f, "10,6", a,
      "8703.22.10 Com capacidade de transporte de pessoas sentadas inferior ou igual a seis, "
      "incluindo o motorista 10,6", p)
linha("ipi", "8703.22", C2F, i, f, "8,97", a, "CÓDIGO DA TIPI 8703.22 8,97", p)
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "8,97", a, "8703.23.10 Ex 01 8,97", p)

a, i, f = "ipi_2022_dec11158", "2022-08-01", "2025-10-31"
p = "dec_11158_2022_anexo4"
linha("ipi", "8703.21.00", C1, i, f, "5,27", a, "8703.21. ‐‐ De cilindrada não superior a 1.000 cm3 00 5,27", p)
linha("ipi", "8703.22.10", C2G, i, f, "9,78", a,
      "8703.22. Com capacidade de transporte de pessoas sentadas inferior ou 10 igual a seis, "
      "incluindo o motorista 9,78", p)
linha("ipi", "8703.22", C2F, i, f, "8,28", a, "8703.22 8,28 8703.23.10 13,55", p)
linha("ipi", "8703.23.10 Ex 01", C3F, i, f, "8,28", a, "8703.23.10 Ex 01 8,28", p)
linha("ipi", "8703.23.10", C4F, i, f, "13,55", a, "8703.22 8,28 8703.23.10 13,55", p)

a, i = "ipi_2025_dec12549", "2025-11-01"
base = "aliquota base do IPI Verde (antes de acrescimos e decrescimos)"
for codigo in ("8703.21.00", "8703.22.10", "8703.23.10", "8703.40.00", "8703.80.00"):
    linha("ipi", codigo, base, i, "", "6,30", a, f"{codigo} 6,30")

# ------------------------------------------------------------- imposto de importacao
def ex_camex(a, paginas, ini, fim, codigos):
    """Os Ex de hibrido de cada codigo; a tabela continua na pagina seguinte do DOU."""
    t1, t2 = texto(paginas[0]), texto(paginas[1])
    for codigo in codigos:
        i0 = t1.index(f"{codigo} De cilindrada")
        fim_trecho = t1.find("8703.23.10 De cilindrada", i0 + 10)
        trechos = [(paginas[0], t1[i0:fim_trecho if fim_trecho > 0 and codigo != "8703.23.10" else None])]
        if codigo == "8703.23.10":
            trechos.append((paginas[1], t2[:t2.find("Art. 2º No Anexo I da Resolução CAMEX")]))
        vistos = set()
        for pagina, pedaco in trechos:
            for m in re.finditer(r"Ex (00\d) - ?(Automóvel [^0-9]+?) (\d) ", pedaco):
                n, desc, v = m.groups()
                if n in vistos:
                    continue
                vistos.add(n)
                prefixo = f"{codigo} De cilindrada [...] " if pagina == paginas[0] else ""
                linha("ii", f"{codigo} Ex {n}", f"hibrido: {desc}", ini, fim, v, a,
                      prefixo + m.group(0).strip(), pagina)


ex_camex("ii_2014_camex86", ("camex_86_2014_dou", "camex_86_2014_dou_p21"), "2014-09-19",
         "2015-10-26", ("8703.22.10", "8703.23.10"))
ex_camex("ii_2015_camex97", ("camex_97_2015_dou", "camex_97_2015_dou_p3"), "2015-10-27", "",
         ("8703.22.10", "8703.23.10"))
t = texto("camex_97_2015_dou")
i0 = t.index("8703.90.00 Outros 35")
for m in re.finditer(r"Ex (00[1-6]) - (Automóvel[^0-9]+?) (\d) ", t[i0:t.index("III - Os Ex-tarifários")]):
    n, desc, v = m.groups()
    linha("ii", f"8703.90.00 Ex {n}", f"eletrico ou a celula de combustivel: {desc}", "2015-10-27", "",
          v, "ii_2015_camex97", f"8703.90.00 Outros 35 [...] Ex {n} - {desc} {v}", "camex_97_2015_dou")


def ex_gecex(a, pagina):
    t = texto(pagina).replace(" . .", " ").replace(" .", " ")
    pad = re.compile(r"(870[34]\.[468]0\.00) (0\d\d) (\d+) ((?:(?!870[34]\.[468]0\.00 0\d\d ).)+?) "
                     r"((?:- )+|[0-9.]+ US\$ \(FOB\) |US\$ [0-9.]+ \(FOB\) )"
                     r"(\d\d/\d\d/\d{4}) (\d\d/\d\d/\d{4})")
    for m in pad.finditer(t):
        codigo, n, v, desc, quota, d1, d2 = m.groups()
        quota = quota.strip(" -")
        iso = lambda d: f"{d[6:]}-{d[3:5]}-{d[:2]}"
        cat = desc[:160] + (f"; quota {quota}" if quota else "")
        linha("ii", f"{codigo} Ex {n}", cat, iso(d1), iso(d2), v, a, m.group(0)[:400], pagina)


ex_gecex("ii_2023_gecex532", "gecex_532_2023")
ex_gecex("ii_2025_gecex774", "gecex_774_2025")
ex_gecex("ii_2026_gecex927", "gecex_927_2026")

# ------------------------------------------------------------------------ IOF
for a, v in [("credito_2008_iof_dec6339", "0,0082"), ("credito_2008_iof_dec6691", "0,0041"),
             ("credito_2011_iof_dec7458", "0,0082"), ("credito_2011_iof_dec7632", "0,0068"),
             ("credito_2012_iof_dec7726", "0,0041 "), ("credito_2015_iof_dec8392", "0,0082")]:
    linha("iof", "", "credito a pessoa fisica, aliquota diaria", POR_ID[a]["vigencia_inicio"],
          POR_ID[a]["vigencia_fim"], v.strip(), a, f"pessoa física: {v}% ao dia")



def uma_por_periodo(linhas: list[dict]) -> list[dict]:
    """Uma aliquota por periodo. A linha nao comeca antes do seu ato; quando um ato
    posterior fixa de novo a mesma NCM e categoria, a linha do anterior vale ate' a
    vespera do posterior, e sai se nem chegou a valer (cronograma substituido antes de
    valer)."""
    inicio = {a["id"]: a["vigencia_inicio"] for a in A}
    for r in linhas:
        r["vigencia_inicio"] = max(r["vigencia_inicio"], inicio[r["ato_id"]])
    saida = []
    for r in linhas:
        for s in linhas:
            if ((s["tributo"], s["ncm"], s["categoria"]) != (r["tributo"], r["ncm"], r["categoria"])
                    or inicio[s["ato_id"]] <= inicio[r["ato_id"]]):
                continue
            if not r["vigencia_fim"] or r["vigencia_fim"] >= s["vigencia_inicio"]:
                vespera = (date.fromisoformat(inicio[s["ato_id"]]) - timedelta(days=1)).isoformat()
                r["vigencia_fim"] = min(r["vigencia_fim"] or vespera, vespera)
        if r["vigencia_fim"] and r["vigencia_fim"] < r["vigencia_inicio"]:
            print(f"fora (substituida antes de valer): {r['ato_id']} {r['ncm']} "
                  f"{r['vigencia_inicio']}")
            continue
        saida.append(r)
    return saida


def conferir(linhas: list[dict]) -> list[str]:
    erros = []
    for r in linhas:
        t = texto(r["pagina_salva"])
        for parte in r["fonte_trecho"].split(" [...] "):
            if normal(parte) not in t:
                erros.append(f"{r.get('id') or r['ato_id']}: {parte[:100]}")
    return erros


def main() -> int:
    global R
    R = uma_por_periodo(R)
    erros = conferir(A) + conferir(R)
    if erros:
        print("\n".join(erros), file=sys.stderr)
        return 1
    for caminho, colunas, linhas in ((config.POLITICAS_ATOS, politicas.COLUNAS_ATOS, A),
                                     (config.POLITICAS_ALIQUOTAS, politicas.COLUNAS_ALIQUOTAS, R)):
        with caminho.open("w", encoding="utf-8", newline="") as fluxo:
            escritor = csv.DictWriter(fluxo, fieldnames=colunas)
            escritor.writeheader()
            escritor.writerows(linhas)
    print(f"{len(A)} atos; {len(R)} aliquotas", dict(Counter(r["tributo"] for r in R)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
