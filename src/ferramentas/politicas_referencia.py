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


# ------------------------------------------------------------------ IPI 2002-2007
ato("ipi_2002_dec4317", "ipi", "decreto", "4.317", "2002-07-31", "2002-08-01", "2002-08-01",
    "2002-12-31", "", "reduz", "automoveis flex: a mesma aliquota dos carros a alcool (NC 87-2)",
    "dec_4317_2002",
    "Ficam fixadas nos percentuais indicados as alíquotas referentes aos automóveis de "
    "passageiros e veículos de uso misto, com motor a álcool ou com motor que utilize alternativa "
    "ou simultaneamente gasolina e álcool (flexible fuel engine)",
    "Equiparacao do flex ao alcool (pista da rodada 12). Antes da janela do painel: revogado a "
    "partir de 1/1/2003 pelo Decreto 4.542, cuja TIPI mantem o flex na NC (87-2).")
ato("ipi_2003_dec4542", "ipi", "decreto", "4.542", "2002-12-26", "2002-12-27", "2003-01-01",
    "2006-12-31", "ipi_2002_dec4317", "regulamenta", "TIPI de 2003 (aliquotas de base)",
    "dec_4542_2002",
    "Este Decreto entra em vigor na data de sua publicação, produzindo efeitos a partir de 1o de "
    "janeiro de 2003",
    "TIPI de 2003; o capitulo 87 esta' em dec_4542_2002_anexo17, que a Presidencia publica com "
    "as notas das alteracoes posteriores. 1.000 cm3 a 9%; gasolina de 1.000 a 2.000 cm3 a 15%; "
    "flex a 13% (20% acima de 2.000 cm3). Substituida pela TIPI de 2007 (Decreto 6.006).")
ato("ipi_2003_dec4800", "ipi", "decreto", "4.800", "2003-08-05", "2003-08-06", "2003-08-06",
    "2003-11-30", "ipi_2003_dec4542", "reduz", "automoveis ate 2.000 cm3 e comerciais leves",
    "dec_4800_2003",
    "Da data de vigência deste Decreto até 31 de outubro de 2003 [...] Art. 5º Este Decreto entra "
    "em vigor na data de sua publicação",
    "1.000 cm3 de 9 para 5% (6% em novembro); gasolina de 1.000 a 2.000 cm3 de 15 para 11% (12%); "
    "flex de 13 para 9% (10%). O art. 4o restabelecia a TIPI em 1/12/2003; o Decreto 4.902 "
    "prorrogou.")
ato("ipi_2003_dec4902", "ipi", "decreto", "4.902", "2003-11-28", "2003-12-01", "2003-12-01",
    "2004-02-29", "ipi_2003_dec4800", "prorroga", "automoveis ate 2.000 cm3 e comerciais leves",
    "dec_4902_2003", "no período de 1º de dezembro de 2003 a 29 de fevereiro de 2004",
    "1.000 cm3 a 6%; gasolina de 1.000 a 2.000 cm3 a 12%; flex a 10%. Nenhum ato prorroga: em "
    "marco e abril de 2004 vale a TIPI de 2003 (9, 15 e 13%) ate' o Decreto 5.058.")
ato("ipi_2004_dec5058", "ipi", "decreto", "5.058", "2004-04-30", "2004-04-30", "2004-05-01",
    "2006-12-31", "ipi_2003_dec4542", "reduz", "automoveis (aliquota permanente)",
    "dec_5058_2004",
    "Este Decreto entra em vigor na data de sua publicação, produzindo efeitos a partir de 1o de "
    "maio de 2004",
    "1.000 cm3 a 7%; gasolina de 1.000 a 2.000 cm3 a 13%; flex a 11% (18% acima de 2.000 cm3). "
    "As mesmas aliquotas ficam na TIPI de 2007.")
ato("ipi_2007_dec6006", "ipi", "decreto", "6.006", "2006-12-28", "2006-12-29", "2007-01-01",
    "", "ipi_2003_dec4542", "regulamenta", "TIPI de 2007 (aliquotas de base)", "dec_6006_2006",
    "Este Decreto entra em vigor na data de sua publicação, produzindo efeitos a partir de 1o de "
    "janeiro de 2007",
    "TIPI de 2007; capitulo 87 em dec_6006_2006_secaoxvii. Foi substituida pela TIPI de 2012 "
    "(Decreto 7.660), que nao foi guardada: fim nao confirmado em pagina aberta.")

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
ato("ipi_2018_dec9442", "ipi", "decreto", "9.442", "2018-07-05", "2018-07-06", "2018-11-01",
    "2022-04-30", "ipi_2017_dec8950", "reduz",
    "automoveis hibridos e eletricos (8703.40, 8703.60, 8703.80)", "dec_9442_2018",
    "Este Decreto entra em vigor a partir do primeiro dia do quarto mês subsequente ao de sua "
    "publicação",
    "Aliquota pela eficiencia energetica e pela massa: 9% a 20% (hibridos), 7% a 18% "
    "(eletricos). Vigencia em 1/11/2018: quarto mes depois de julho de 2018. As aliquotas do "
    "proprio ato valem ate' 24/2/2022 (o Decreto 10.979 as reduz em 18,5%); revogado a partir de "
    "1/5/2022 pelo Decreto 10.923 (art. 5o, pagina dec_10923_2021).")
ato("ipi_2017_dec8950", "ipi", "decreto", "8.950", "2016-12-29", "2016-12-30", "2017-01-01",
    "2022-04-30", "", "regulamenta", "TIPI de 2017 (aliquotas de base)", "dec_8950_2016",
    "Este Decreto entra em vigor na data de sua publicação, produzindo efeitos a partir de 1º de "
    "janeiro de 2017",
    "Capitulo 87 em dec_8950_2016_anexo_cap87 (paginas 385 a 389 do PDF da TIPI). Em 2017 a "
    "gasolina tem os 30 pontos do Inovar-Auto (NC 87-6); de 2018 em diante valem as aliquotas de "
    "base (1.000 cm3 a 7%, gasolina a 13%, flex a 11%). As reducoes de um ou dois pontos por "
    "eficiencia (NC 87-7 a 87-11) nao entram na tabela. Fim: revogado a partir de 1/5/2022 pelo "
    "Decreto 10.923 (art. 5o, redacao do Decreto 11.021).")
ato("ipi_2022_dec10923", "ipi", "decreto", "10.923", "2021-12-30", "", "2022-05-01",
    "2022-07-31", "ipi_2017_dec8950", "regulamenta", "TIPI de 2022 (aliquotas de base)",
    "dec_10923_2021", "Este Decreto entra em vigor na data de sua publicação e produz efeitos a "
    "partir de 1º de maio de 2022. (Redação dada pelo Decreto nº 11.021, de 2022) [...] "
    "(Revogado pelo Decreto nº 11.158, de 2022)",
    "Efeito em 1/5/2022 (era 1/4/2022 na redacao original), o mesmo dia em que o Decreto 11.055 "
    "da' novo anexo a esta TIPI: as aliquotas do anexo original (dec_10923_2021_anexo_cap87) "
    "nunca valeram sozinhas e nao entram na tabela de aliquotas. A pagina do Planalto da' a "
    "publicacao no 'DOU de 31.12.2022', erro evidente; a data fica vazia. Revogado pelo 11.158.")
ato("ipi_2022_dec10979", "ipi", "decreto", "10.979", "2022-02-25", "2022-02-25", "2022-02-25",
    "2022-04-30", "ipi_2017_dec8950", "reduz", "toda a TIPI; 18,5% na posicao 87.03", "dec_10979_2022",
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
ato("acordo_2002_mex_dec4458", "acordo_automotivo", "decreto", "4.458", "2002-11-05", "2002-11-06",
    "2002-11-06", "2012-03-18", "", "cria",
    "comercio automotivo com o Mexico (ACE-55, apendice Brasil-Mexico)", "dec_4458_2002",
    "Ano 1 1,1 % 112 000 7 000 119 000 Ano 2 0 % 131 900 8 400 140 300 Ano 3 0 % 153 600 Ano 4 0 % "
    "174 300 Ano 5 0 % Livre Comércio",
    "Automoveis: tarifa de 1,1% no ano 1 dentro da quota de 119 mil, 0% nos anos 2 a 4 com "
    "quotas, livre comercio no ano 5. Os anos contam da entrada em vigor do acordo entre Brasil e "
    "Mexico, que o decreto nao data (vigencia aqui: a publicacao do decreto). Fim INFERIDO: as "
    "quotas do Decreto 7.706 a partir de 19/3/2012.")
ato("acordo_2012_mex_dec7706", "acordo_automotivo", "decreto", "7.706", "2012-03-29", "2012-03-30",
    "2012-03-19", "2015-03-18", "acordo_2002_mex_dec4458", "cria", "importacao de veiculos leves do Mexico (ACE-55)",
    "dec_7706_2012",
    "De 19 de março de 2012 a 18 de março de 2013 US$ 1,450 bilhão",
    "Quotas anuais a tarifa zero: US$ 1,450, 1,560 e 1,640 bilhao; livre comercio previsto "
    "para 19/3/2015.")
ato("acordo_2015_mex_dec8419", "acordo_automotivo", "decreto", "8.419", "2015-03-18", "2015-03-19",
    "2015-03-19", "2019-03-18", "acordo_2012_mex_dec7706", "prorroga", "ACE-55 com o Mexico",
    "dec_8419_2015", "A partir de 19 de março de 2019 Livre Comércio",
    "Quotas de 2015 a 2019; livre comercio a partir de 19/3/2019.")
ato("acordo_2002_arg_dec4510", "acordo_automotivo", "decreto", "4.510", "2002-12-11", "2002-12-12",
    "2000-08-01", "2005-12-31", "", "regulamenta", "comercio automotivo com a Argentina (ACE-14)",
    "dec_4510_2002",
    "O presente Protocolo está em vigor desde 1º de agosto de 2000 [...] terá vigência até 31 de "
    "dezembro de 2005 [...] 2003 137,5 62,5 2,2 2004 141,2 58,8 2,4 2005 144,4 55,6 2,6",
    "Trigesimo primeiro protocolo (Politica Automotiva Comum): flex de 2,2 em 2003, 2,4 em 2004 "
    "e 2,6 em 2005; livre comercio previsto para 1/1/2006, que nao veio.")
ato("acordo_2006_arg_dec5663", "acordo_automotivo", "decreto", "5.663", "2006-01-09", "2006-01-10",
    "2006-01-01", "2006-03-01", "acordo_2002_arg_dec4510", "prorroga", "ACE-14 com a Argentina",
    "dec_5663_2006",
    "Prorrogar por um período de SESSENTA (60) dias, contados a partir de 1o de janeiro de 2006, a "
    "vigência do Trigésimo Primeiro Protocolo Adicional com as condições de aplicação estabelecidas "
    "para o ano 2005",
    "Trigesimo segundo protocolo: 60 dias com as condicoes de 2005 (fim em 1/3/2006).")
ato("acordo_2006_arg_dec5716", "acordo_automotivo", "decreto", "5.716", "2006-03-09", "2006-03-10",
    "2006-03-02", "2006-06-30", "acordo_2006_arg_dec5663", "prorroga", "ACE-14 com a Argentina",
    "dec_5716_2006",
    "Durante o período compreendido entre 2 de março de 2006 até 30 de junho de 2006 serão "
    "mantidas as condições estabelecidas no Trigésimo Primeiro Protocolo Adicional "
    "correspondentes ao ano de 2005",
    "Trigesimo terceiro protocolo.")
ato("acordo_2006_arg_dec5835", "acordo_automotivo", "decreto", "5.835", "2006-07-06", "2006-07-07",
    "2006-07-01", "2008-06-30", "acordo_2006_arg_dec5716", "regulamenta", "ACE-14 com a Argentina",
    "dec_5835_2006",
    "a partir de 1º de julho de 2006 até 30 junho de 2008 [...] deverá observar um coeficiente de "
    "desvio anual não superior a 1,95",
    "Trigesimo quinto protocolo: flex de 1,95 de julho de 2006 a junho de 2008.")
ato("acordo_2008_arg_dec6500", "acordo_automotivo", "decreto", "6.500", "2008-07-02", "2008-07-03",
    "2008-07-03", "2013-06-30", "acordo_2006_arg_dec5835", "regulamenta", "comercio automotivo com a Argentina (ACE-14)",
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
ato("credito_2002_iof_dec4494", "credito", "decreto", "4.494", "2002-12-03", "2002-12-04",
    "2002-12-04", "2007-12-16", "", "regulamenta", "IOF do credito a pessoa fisica",
    "dec_4494_2002", "2. mutuário pessoa física: 0,0041% ao dia",
    "Regulamento do IOF de 2002: 0,0041% ao dia para pessoa fisica. Substituido pelo "
    "regulamento de 2007 (Decreto 6.306).")
ato("credito_2007_iof_dec6306", "credito", "decreto", "6.306", "2007-12-14", "2007-12-17",
    "2007-12-17", "", "credito_2002_iof_dec4494", "regulamenta", "IOF do credito a pessoa fisica",
    "dec_6306_2007",
    "Este Decreto entra em vigor na data de sua publicação [...] 2. mutuário pessoa física: "
    "0,0082%; (Redação dada pelo Decreto nº 8.392, de 2015) (Vigência) b) quando ficar definido",
    "Regulamento do IOF em vigor (texto compilado, acessado nesta rodada): 0,0041% ao dia ate' o "
    "Decreto 6.339; depois as aliquotas mudam pelos decretos que o alteram. A ultima redacao da "
    "aliquota da pessoa fisica e' a do Decreto 8.392/2015: as mudancas de 2025 sao da pessoa "
    "juridica.")
ato("credito_2008_iof_dec6339", "credito", "decreto", "6.339", "2008-01-03", "2008-01-03",
    "2008-01-03", "2008-12-11", "credito_2007_iof_dec6306", "aumenta", "IOF do credito a pessoa fisica", "dec_6339_2008",
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
    "IOF diario de 0,0041% para 0,0082%. Ultima mudanca da aliquota da pessoa fisica, pelo "
    "texto compilado do Decreto 6.306 (rodada 12).")
ato("credito_2010_bcb_circ3515", "credito", "circular", "BCB 3.515", "2010-12-03", "2010-12-03",
    "2010-12-06", "", "", "aumenta",
    "financiamento de veiculo a pessoa fisica com prazo acima de 24 meses", "bcb_circular_3515",
    "Deve ser aplicado FPR de 150% (cento e cinquenta por cento) às exposições relativas a "
    "operações de crédito",
    "Fator de ponderacao de 150% no capital para credito a pessoa fisica contratado a partir de "
    "6/12/2010 com prazo acima de 24 meses; veiculo isento conforme prazo e entrada. A "
    "Circular 3.563 (11/11/2011) isenta o veiculo de ate' 60 meses, mas nao revoga esta: "
    "fim nao procurado.")
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


def linha(tributo, ncm, categoria, ini, fim, aliq, ato, trecho, pagina=None, categoria_ipi="",
          derivada="nao", obs=""):
    R.append(dict(tributo=tributo, ncm=ncm, categoria=categoria, categoria_ipi=categoria_ipi,
                  vigencia_inicio=ini, vigencia_fim=fim, aliquota_pct=aliq,
                  aliquota_efetiva_habilitada="", ato_id=ato,
                  pagina_salva=pagina or POR_ID[ato]["pagina_salva"], fonte_trecho=trecho,
                  reducao_ato_id="", reducao_pagina="", reducao_trecho="", derivada=derivada,
                  observacao=obs))


# ---------------------------------------------------------- IPI: categorias principais
# Uma linha por categoria e periodo (`categoria_ipi`, a lista de `politicas.CATEGORIAS_IPI`).
# O codigo da TIPI que a linha cita vai em `ncm`: 8703.21.00 (codigo, vale para qualquer
# combustivel que nenhuma Nota Complementar trate a' parte) ou 8703.21 (NC do flex).
G1, F1, G2, F2, G3, F3, G4, F4 = (politicas.CATEGORIAS_IPI[k] for k in
                                  ("g1", "f1", "g2", "f2", "g3", "f3", "g4", "f4"))
TODOS1 = (G1, F1)  # o codigo 8703.21.00 sem NC do flex: vale para os dois


def ipi(cats, ncm, ini, fim, aliq, ato, trecho, pagina=None, derivada="nao", obs=""):
    for cat in ([cats] if isinstance(cats, str) else cats):
        linha("ipi", ncm, cat, ini, fim, aliq, ato, trecho, pagina, categoria_ipi=cat,
              derivada=derivada, obs=obs)


def colunas(ato, cab, periodos, linhas_tabela, pagina=None):
    """Tabela com uma coluna por periodo: cada linha literal ('8703.21 32 33,5 37 7') da'
    os valores das ultimas colunas, na ordem dos periodos."""
    for cats, ncm, texto_linha in linhas_tabela:
        valores = texto_linha.split()[-len(periodos):]
        for (ini, fim), valor in zip(periodos, valores):
            ipi(cats, ncm, ini, fim, valor, ato, f"{cab} [...] {texto_linha}", pagina)


# ---- TIPI de 2003 (Decreto 4.542): de 1/1/2003 ate' o Decreto 4.800; de novo em marco e
# abril de 2004, depois do Decreto 4.902 e antes do 5.058
a, p = "ipi_2003_dec4542", "dec_4542_2002_anexo17"
for ini, fim, obs in (("2003-01-01", "2003-08-05", ""),
                      ("2004-03-01", "2004-04-30",
                       "TIPI restabelecida ao fim do Decreto 4.902 (29/2/2004), ate' o 5.058.")):
    ipi(TODOS1, "8703.21.00", ini, fim, "9", a,
        "8703.21.00 --De cilindrada não superior a 1.000cm³ 9", p, obs=obs)
    ipi(G2, "8703.22.10", ini, fim, "15", a,
        "8703.22.10 Com capacidade de transporte de pessoas sentadas inferior ou igual a 6, "
        "incluído o condutor 15", p, obs=obs)
    ipi(G3, "8703.23.10 Ex 01", ini, fim, "15", a,
        "Ex 01 – De cilindrada superior a 1.500 cm³, mas não superior a 2.000 cm³ 15", p, obs=obs)
    ipi(F2, "8703.22", ini, fim, "13", a, "CODIGO NCM ALÍQUOTA % 8703.22 13", p, obs=obs)
    ipi(F3, "8703.23.10 Ex 01", ini, fim, "13", a, "8703.23.10 Ex 01 13", p, obs=obs)
ipi(G4, "8703.23.10", "2003-01-01", "2006-12-31", "25", a,
    "8703.23.10 Com capacidade de transporte de pessoas sentadas inferior ou igual a 6, "
    "incluído o condutor 25", p)
ipi(F4, "8703.23.10", "2003-01-01", "2004-04-30", "20", a,
    "CODIGO NCM ALÍQUOTA % 8703.22 13 Vide Decreto nº 4.902/03 8703.23.10 20", p)

# ---- 2003: Decreto 4.800 (agosto a novembro) e 4.902 (dezembro a fevereiro de 2004)
a = "ipi_2003_dec4800"
per = (("2003-08-06", "2003-10-31"), ("2003-11-01", "2003-11-30"))
colunas(a, "Da data de vigência deste Decreto até 31 de outubro de 2003 De 1º a 30 de novembro "
           "2003", per, [(TODOS1, "8703.21.00", "8703.21.00 5 6"), (G2, "8703.22", "8703.22 11 12"),
                         (G3, "8703.23.10 Ex 01", "8703.23.10 Ex 01 11 12")])
colunas(a, "Da data de vigência deste Decreto até 31 de outubro de 2003 De 1º a 30 de novembro de "
           "2003", per, [(F2, "8703.22", "8703.22 9 10"),
                         (F3, "8703.23.10 Ex 01", "8703.23.10 Ex 01 9 10")])
a, i, f = "ipi_2003_dec4902", "2003-12-01", "2004-02-29"
flex = ("Ficam reduzidas para dez por cento, no período de 1º de dezembro de 2003 a 29 de "
        "fevereiro de 2004, as alíquotas do Imposto sobre Produtos Industrializados - IPI, "
        "incidentes sobre os produtos classificados sob os códigos 8703.22, 8703.23.10 Ex-01")
ipi(F2, "8703.22", i, f, "10", a, flex)
ipi(F3, "8703.23.10 Ex 01", i, f, "10", a, flex)
gas = "CODIGO ALÍQUOTA % 8703.21.00 6 8703.22 12 8703.23.10 Ex 01 12"
ipi(TODOS1, "8703.21.00", i, f, "6", a, gas)
ipi(G2, "8703.22", i, f, "12", a, gas)
ipi(G3, "8703.23.10 Ex 01", i, f, "12", a, gas)

# ---- 2004: Decreto 5.058 (aliquota permanente de maio de 2004 ate' a TIPI de 2007)
a, i, f = "ipi_2004_dec5058", "2004-05-01", "2006-12-31"
gas = "8703.21.00 7 3307.30.00 22 8703.22 13 3307.4 22 8703.23.10 Ex 01 13"
ipi(TODOS1, "8703.21.00", i, f, "7", a, gas)
ipi(G2, "8703.22", i, f, "13", a, gas)
ipi(G3, "8703.23.10 Ex 01", i, f, "13", a, gas)
flex = "Código NCM Alíquota (%) 8703.22 11 8703.23.10 18 8703.23.10 Ex 01 11"
ipi(F2, "8703.22", i, f, "11", a, flex)
ipi(F3, "8703.23.10 Ex 01", i, f, "11", a, flex)
ipi(F4, "8703.23.10", i, f, "18", a, flex)

# ---- TIPI de 2007 (Decreto 6.006): sem fim aqui; cada categoria vai ate' o ato seguinte
a, p, i = "ipi_2007_dec6006", "dec_6006_2006_secaoxvii", "2007-01-01"
ipi(TODOS1, "8703.21.00", i, "", "7", a, "8703.21.00 --De cilindrada não superior a 1.000cm³ 7", p)
ipi(G2, "8703.22.10", i, "", "13", a,
    "8703.22.10 Com capacidade de transporte de pessoas sentadas inferior ou igual a seis, "
    "incluído o motorista 13", p)
ipi(G3, "8703.23.10 Ex 01", i, "", "13", a,
    "Ex 01 – De cilindrada superior a 1.500 cm³, mas não superior a 2.000 cm³ 13", p)
ipi(G4, "8703.23.10", i, "", "25", a,
    "8703.23.10 Com capacidade de transporte de pessoas sentadas inferior ou igual a seis, "
    "incluído o motorista 25", p)
flex = "CODIGO NCM ALÍQUOTA % 8703.22 11 8703.23.10 18 8703.23.10 Ex 01 11"
ipi(F2, "8703.22", i, "", "11", a, flex, p)
ipi(F3, "8703.23.10 Ex 01", i, "", "11", a, flex, p)
ipi(F4, "8703.23.10", i, "", "18", a, flex, p)

# ---- 2008-2010
NC_FLEX_2008 = ("NC (87-2) Ficam fixadas nos percentuais indicados as alíquotas referentes aos "
                "automóveis de passageiros e veículos de uso misto, com motor a álcool")
a, i, f = "ipi_2008_dec6687", "2008-12-12", "2009-03-31"
ipi(TODOS1, "8703.21.00", i, f, "0", a, "ANEXO I Código TIPI Alíquota (%) 8703.21.00 0")
ipi(G2, "8703.22.10", i, f, "6,5", a, "8703.21.00 0 8703.22.10 6,5")
ipi(G3, "8703.23.10 Ex 01", i, f, "6,5", a, "8703.23.10 Ex 01 6,5")
ipi(F2, "8703.22", i, f, "5,5", a, f"{NC_FLEX_2008} [...] 8703.22 5,5")
ipi(F3, "8703.23.10 Ex 01", i, f, "5,5", a, f"{NC_FLEX_2008} [...] 8703.23.10 Ex 01 5,5")
ipi(F4, "8703.23.10", i, f, "18", a, f"{NC_FLEX_2008} [...] 8703.23.10 18")

a, i, f = "ipi_2009_dec6809", "2009-04-01", "2009-06-30"
ipi(TODOS1, "8703.21.00", i, f, "0", a, "ANEXO II Código TIPI Alíquota (%) 8703.21.00 0")
ipi(G2, "8703.22.10", i, f, "6,5", a, "8703.21.00 0 8703.22.10 6,5")
ipi(G3, "8703.23.10 Ex 01", i, f, "6,5", a, "8703.23.10 Ex 01 6,5")
ipi(F2, "8703.22", i, f, "5,5", a, "ANEXO IV “NC (87-2) Ficam fixadas [...] 8703.22 5,5")
ipi(F3, "8703.23.10 Ex 01", i, f, "5,5", a, "8703.23.10 Ex 01 5,5")
ipi(F4, "8703.23.10", i, f, "18", a, "8703.22 5,5 8703.23.10 18")

a = "ipi_2009_dec6890"
for cab, ini, fim, v1, v2 in [
        ("Até 30 de setembro de 2009", "2009-07-01", "2009-09-30", "0", "6,5"),
        ("De 1o a 31 de outubro de 2009", "2009-10-01", "2009-10-31", "1,5", "8,0"),
        ("De 1o a 30 de novembro de 2009", "2009-11-01", "2009-11-30", "3,0", "9,5"),
        ("De 1o a 31 de dezembro de 2009", "2009-12-01", "2009-12-31", "5,0", "11,0"),
        ("A partir de 1o de janeiro de 2010", "2010-01-01", "2011-12-15", "7", "13")]:
    bloco = f"{cab} NCM ALÍQUOTA (%) 8703.21.00 {v1} 8703.22.10 {v2}"
    ipi(TODOS1, "8703.21.00", ini, fim, v1, a, bloco)
    ipi(G2, "8703.22.10", ini, fim, v2, a, bloco)
    ipi(G3, "8703.23.10 Ex 01", ini, fim, v2, a, f"{bloco} 8703.22.90 {v2} 8703.23.10 Ex 01 {v2}")
for cab, ini, fim, v in [("Até 30 de setembro de 2009 “NC (87-2)", "2009-07-01", "2009-09-30", "5,5"),
                         ("De 1oa 31 de outubro de 2009 NC (87-2)", "2009-10-01", "2009-10-31", "6,5"),
                         ("De 1o a 30 de novembro de 2009 NC (87-2)", "2009-11-01", "2009-11-30", "7,5"),
                         ("De 1o a 31 de dezembro de 2009 NC (87-2)", "2009-12-01", "2009-12-31", "9,0"),
                         ("A partir de 1o de janeiro de 2010 NC (87-2)", "2010-01-01", "2011-12-15", "11")]:
    ipi(F2, "8703.22", ini, fim, v, a, f"{cab} [...] 8703.22 {v} 8703.23.10 18")
    ipi(F3, "8703.23.10 Ex 01", ini, fim, v, a, f"{cab} [...] 8703.23.10 Ex 01 {v}")
    ipi(F4, "8703.23.10", ini, fim, "18", a, f"{cab} [...] 8703.22 {v} 8703.23.10 18")

a = "ipi_2009_dec7017"
for cab, ini, fim, v1, v2 in [("De 1o a 31 de dezembro de 2009:", "2009-12-01", "2009-12-31", "3", "7,5"),
                              ("De 1o de janeiro a 31 de março de 2010:", "2010-01-01", "2010-03-31", "3", "7,5"),
                              ("A partir de 1o de abril de 2010:", "2010-04-01", "2011-12-15", "7", "11")]:
    ipi(F1, "8703.21", ini, fim, v1, a, f"{cab} [...] 8703.21 {v1} 8703.22 {v2}")
    ipi(F2, "8703.22", ini, fim, v2, a, f"{cab} [...] 8703.21 {v1} 8703.22 {v2}")
    ipi(F3, "8703.23.10 Ex 01", ini, fim, v2, a, f"{cab} [...] 8703.23.10 Ex 01 {v2}")
    ipi(F4, "8703.23.10", ini, fim, "18", a, f"{cab} [...] 8703.22 {v2} 8703.23.10 18")

# ---- 2011-2014
a, i, f = "ipi_2011_dec7567", "2011-12-16", "2012-12-31"
cab = "De 16 de dezembro de 2011 a 31 de dezembro de 2012"
gas = (f"{cab}: Código NCM Alíquota (%) Código NCM Alíquota (%) 8701.20.00 30 8704.21.30 Ex01 34 "
       "8703.21.00 37")
ipi(G1, "8703.21.00", i, f, "37", a, gas)
ipi(G2, "8703.22.10", i, f, "43", a, f"{gas} [...] 8703.22.10 43")
ipi(G3, "8703.23.10 Ex 01", i, f, "43", a, f"{gas} [...] 8703.23.10 Ex01 43")
ipi(G4, "8703.23.10", i, f, "55", a, f"{gas} [...] 8703.23.10 55")
flex = (f"{cab}: NC (87-2) [...] Código NCM ALÍQUOTA (%) 8703.21 37 8703.22 41 8703.23.10 48 "
        "8703.23.10 Ex 01 41")
for cat, ncm, v in ((F1, "8703.21", "37"), (F2, "8703.22", "41"), (F3, "8703.23.10 Ex 01", "41"),
                    (F4, "8703.23.10", "48")):
    ipi(cat, ncm, i, f, v, a, flex)

a = "ipi_2012_dec7725"
colunas(a, "Até 21/05/2012 De 22/05/2012 até 31/08/2012 De 1º /09/2012 até 31/12/2012 A partir de "
           "1º /01/2013",
        (("2012-05-22", "2012-08-31"), ("2012-09-01", "2012-12-31"), ("2013-01-01", "")),
        [(F1, "8703.21.00", "8703.21.00 37 30 37 7"), (F2, "8703.22", "8703.22 41 35,5 41 11"),
         (F4, "8703.23.10", "8703.23.10 48 48 48 18"),
         (F3, "8703.23.10 Ex 01", "8703.23.10 Ex 01 41 35,5 41 11")])
i, f = "2012-05-22", "2012-08-31"
ipi(G1, "8703.21.00", i, f, "30", a,
    "NOTA COMPLEMENTAR NC (87-7) DA TIPI Até [...] 8703.21.00 30 8704.21.90 Ex 02 5")
ipi(G2, "8703.22.10", i, f, "36,5", a, "De 22 de maio até 31 de agosto de 2012 [...] 8703.22.10 36,5")
ipi(G3, "8703.23.10 Ex 01", i, f, "36,5", a,
    "De 22 de maio até 31 de agosto de 2012 [...] 8703.23.10 Ex 01 36,5")

a = "ipi_2012_dec7796"
colunas(a, "Até 31/10/2012 De 1º /11/2012 até 31/12/2012 A partir de 1º /01/2013",
        (("2012-09-01", "2012-10-31"), ("2012-11-01", "2012-12-31"), ("2013-01-01", "")),
        [(F1, "8703.21.00", "8703.21.00 30 37 7"), (F2, "8703.22", "8703.22 35,5 41 11"),
         (F4, "8703.23.10", "8703.23.10 48 48 18"),
         (F3, "8703.23.10 Ex 01", "8703.23.10 Ex 01 35,5 41 11")])
i, f = "2012-09-01", "2012-10-31"
ipi(G1, "8703.21.00", i, f, "30", a,
    "NOTA COMPLEMENTAR NC (87-7) DA TIPI Até [...] 8703.21.00 30 8704.21.90 Ex 02 5")
ipi(G2, "8703.22.10", i, f, "36,5", a, "NOTA COMPLEMENTAR NC (87-7) DA TIPI Até [...] 8703.22.10 36,5")
ipi(G3, "8703.23.10 Ex 01", i, f, "36,5", a,
    "NOTA COMPLEMENTAR NC (87-7) DA TIPI Até [...] 8703.23.10 Ex 01 36,5")

a, i, f = "ipi_2012_dec7834", "2012-11-01", "2012-12-31"
flex = "Código TIPI Alíquota (%) 8703.21.00 30 8703.22 35,5 8703.23.10 48 8703.23.10 Ex 01 35,5"
for cat, ncm, v in ((F1, "8703.21.00", "30"), (F2, "8703.22", "35,5"), (F4, "8703.23.10", "48"),
                    (F3, "8703.23.10 Ex 01", "35,5")):
    ipi(cat, ncm, i, f, v, a, flex)
ipi(G1, "8703.21.00", i, f, "30", a,
    "NOTA COMPLEMENTAR NC (87-7) DA TIPI Até [...] 8703.21.00 30 8704.21.90 Ex 02 5")
ipi(G2, "8703.22.10", i, f, "36,5", a, "NOTA COMPLEMENTAR NC (87-7) DA TIPI Até [...] 8703.22.10 36,5")
ipi(G3, "8703.23.10 Ex 01", i, f, "36,5", a,
    "NOTA COMPLEMENTAR NC (87-7) DA TIPI Até [...] 8703.23.10 Ex 01 36,5")


def ciclo(a, cab_flex, cab_gas, per_flex, per_gas, flex, gas):
    """Decretos de 2013-2014: tabela do flex (NC 87-4) e da gasolina (NC 87-7)."""
    colunas(a, cab_flex, per_flex, [(F1, "8703.21", f"8703.21 {flex[0]}"),
                                    (F2, "8703.22", f"8703.22 {flex[1]}"),
                                    (F4, "8703.23.10", f"8703.23.10 {flex[2]}"),
                                    (F3, "8703.23.10 Ex 01", f"8703.23.10 Ex 01 {flex[1]}")])
    colunas(a, cab_gas, per_gas, [(G1, "8703.21.00", f"8703.21.00 {gas[0]}"),
                                  (G2, "8703.22.10", f"8703.22.10 {gas[1]}"),
                                  (G4, "8703.23.10", f"8703.23.10 {gas[2]}"),
                                  (G3, "8703.23.10 Ex 01", f"8703.23.10 Ex 01 {gas[1]}")])


ciclo("ipi_2013_dec7879",
      "De 1º /01/2013 até 31/03/2013 De 1º /04/2013 até 30/06/2013 De 1º /07/2013 até 31/12/2017 "
      "A partir de 1º /01/2018",
      "De 1º /01/2013 até 3103/2013 De 1º /04/2013 até 30/06/2013 De 1º /07/2013 até 31/12/2017",
      (("2013-01-01", "2013-03-31"), ("2013-04-01", "2013-06-30"), ("2013-07-01", "2017-12-31"),
       ("2018-01-01", "")),
      (("2013-01-01", "2013-03-31"), ("2013-04-01", "2013-06-30"), ("2013-07-01", "2017-12-31")),
      ("32 33,5 37 7", "37 39 41 11", "48 48 48 18"), ("32 33,5 37", "38 40 43", "55 55 55"))
ciclo("ipi_2013_dec7971",
      "De 1º /04/2013 até 31/12/2013 De 1º /01/2014 até 31/12/2017 A partir de 1º /01/2018",
      "De 1º /04/2013 até 31/12/2013 De 1º /01/2014 até 31/12/2017",
      (("2013-04-01", "2013-12-31"), ("2014-01-01", "2017-12-31"), ("2018-01-01", "")),
      (("2013-04-01", "2013-12-31"), ("2014-01-01", "2017-12-31")),
      ("32 37 7", "37 41 11", "48 48 18"), ("32 37", "38 43", "55 55"))
ciclo("ipi_2014_dec8168",
      "De 1º /1/2014 até 30/6/2014 De 1º /7/2014 até 31/12/2017 A partir de 1º /1/2018",
      "De 1º /1/2014 até 30/6/2014 De 1º /7/2014 até 31/12/2017",
      (("2014-01-01", "2014-06-30"), ("2014-07-01", "2017-12-31"), ("2018-01-01", "")),
      (("2014-01-01", "2014-06-30"), ("2014-07-01", "2017-12-31")),
      ("33 37 7", "39 41 11", "48 48 18"), ("33 37", "40 43", "55 55"))
ciclo("ipi_2014_dec8279",
      "De 1º /7/2014 até 31/12/2014 De 1º /1/2015 até 31/12/2017 A partir de 1º /1/2018",
      "De 1º /7/2014 até 31/12/2014 De 1º /1/2015 até 31/12/2017",
      (("2014-07-01", "2014-12-31"), ("2015-01-01", "2017-12-31"), ("2018-01-01", "")),
      (("2014-07-01", "2014-12-31"), ("2015-01-01", "2017-12-31")),
      ("33 37 7", "39 41 11", "48 48 18"), ("33 37", "40 43", "55 55"))

# ---- TIPI de 2017 (Decreto 8.950): 2017 com os 30 pontos (NC 87-6 e 87-4); de 2018 ate' a
# TIPI de 2022, as aliquotas de base
a, p = "ipi_2017_dec8950", "dec_8950_2016_anexo_cap87"
i, f = "2017-01-01", "2017-12-31"
gas = ("NC (87-6) Ficam fixadas nos percentuais indicados as alíquotas relativas aos produtos "
       "classificados nos códigos a seguir especificados [...] 8703.21.00 37 8703.22 43 "
       "8703.23.10 55 8703.23.10 Ex 01 43")
ipi(TODOS1, "8703.21.00", i, f, "37", a, gas, p)
ipi(G2, "8703.22", i, f, "43", a, gas, p)
ipi(G4, "8703.23.10", i, f, "55", a, gas, p)
ipi(G3, "8703.23.10 Ex 01", i, f, "43", a, gas, p)
colunas(a, "CÓDIGO DA TIPI De 1º/1/2017 até 31/12/2017 A partir de 1º/01/2018",
        (("2017-01-01", "2017-12-31"), ("2018-01-01", "2022-02-24")),
        [(F2, "8703.22", "8703.22 41 11"), (F4, "8703.23.10", "8703.23.10 48 18"),
         (F3, "8703.23.10 Ex 01", "8703.23.10 Ex 01 41 11")], p)


def base_tipi(a, p, i, f, fim_motorista):
    """Aliquotas de base do capitulo 87 (TIPI de 2017 e de 2022)."""
    ipi(TODOS1, "8703.21.00", i, f, "7", a,
        "8703.21.00 -- De cilindrada não superior a 1.000 cm3 7", p)
    ipi(G2, "8703.22.10", i, f, "13", a,
        "8703.22.10 Com capacidade de transporte de pessoas sentadas inferior ou igual a seis, "
        f"incluindo o motorista 13", p)
    ipi(G3, "8703.23.10 Ex 01", i, f, "13", a,
        "Ex 01 - De cilindrada superior a 1.500 cm³, mas não superior a 2.000 cm³ 13", p)
    ipi(G4, "8703.23.10", i, f, "25", a,
        "8703.23.10 Com capacidade de transporte de pessoas sentadas inferior ou igual a seis, "
        f"incluindo o motorista 25", p)


base_tipi(a, p, "2018-01-01", "2022-02-24", "")
# A TIPI de 2022 (Decreto 10.923) so' produz efeito em 1/5/2022, o mesmo dia em que o Decreto
# 11.055 da' a ela o anexo novo: as aliquotas do anexo original nunca valeram sozinhas.

# ---- 2022: Decretos 10.979, 11.055 e 11.158
a, i, f = "ipi_2022_dec10979", "2022-02-25", "2022-04-30"
cab = ("(flexible fuel engine), classificados nos códigos a seguir especificados: CÓDIGO DA TIPI "
       "ALÍQUOTA % 8703.22 8,965 8703.23.10 14,67 8703.23.10 Ex 01 8,965")
ipi(F2, "8703.22", i, f, "8,965", a, cab)
ipi(F3, "8703.23.10 Ex 01", i, f, "8,965", a, cab)
ipi(F4, "8703.23.10", i, f, "14,67", a, cab)
reducao = ("I - 18,5% (dezoitos inteiros e cinco décimos por cento) para os produtos "
           "classificados nos códigos da posição 87.03")
for cats, ncm, base, valor in ((TODOS1, "8703.21.00", "7", "5,705"), (G2, "8703.22.10", "13", "10,595"),
                               (G3, "8703.23.10 Ex 01", "13", "10,595"),
                               (G4, "8703.23.10", "25", "20,375")):
    ipi(cats, ncm, i, f, valor, a, reducao, derivada="sim",
        obs=f"Derivada: o ato reduz em 18,5% as aliquotas da posicao 87.03 e nao lista este "
            f"codigo; 18,5% sobre {base} (TIPI de 2017, Decreto 8.950) = {valor}.")

a, i, f, p = "ipi_2022_dec11055", "2022-05-01", "2022-07-31", "dec_11055_2022_anexo"
ipi(TODOS1, "8703.21.00", i, f, "5,71", a,
    "8703.21.00 -- De cilindrada não superior a 1.000 cm3 5,71", p)
ipi(G2, "8703.22.10", i, f, "10,6", a,
    "8703.22.10 Com capacidade de transporte de pessoas sentadas inferior ou igual a seis, "
    "incluindo o motorista 10,6", p)
ipi(G3, "8703.23.10 Ex 01", i, f, "10,6", a,
    "Ex 01 - De cilindrada superior a 1.500 cm³, mas não superior a 2.000 cm³ 10,6", p)
ipi(G4, "8703.23.10", i, f, "20,38", a,
    "8703.23.10 Com capacidade de transporte de pessoas sentadas inferior ou igual a seis, "
    "incluindo o motorista 20,38", p)
flex = "ALÍQUOTA (%) CÓDIGO DA TIPI 8703.22 8,97 8703.23.10 14,67 8703.23.10 Ex 01 8,97"
ipi(F2, "8703.22", i, f, "8,97", a, flex, p)
ipi(F4, "8703.23.10", i, f, "14,67", a, flex, p)
ipi(F3, "8703.23.10 Ex 01", i, f, "8,97", a, flex, p)

a, i, f, p = "ipi_2022_dec11158", "2022-08-01", "2025-10-31", "dec_11158_2022_anexo4"
ipi(TODOS1, "8703.21.00", i, f, "5,27", a,
    "8703.21. ‐‐ De cilindrada não superior a 1.000 cm3 00 5,27", p)
ipi(G2, "8703.22.10", i, f, "9,78", a,
    "8703.22. Com capacidade de transporte de pessoas sentadas inferior ou 10 igual a seis, "
    "incluindo o motorista 9,78", p)
ipi(G3, "8703.23.10 Ex 01", i, f, "9,78", a,
    "Ex 01 ‐ De cilindrada superior a 1.500 cm³, mas não superior a 2.000 cm³ 9,78", p)
ipi(G4, "8703.23.10", i, f, "18,81", a,
    "8703.23. Com capacidade de transporte de pessoas sentadas inferior ou 10 igual a seis, "
    "incluindo o motorista 18,81", p)
flex = "ALÍQUOTA (%) CÓDIGO DA TIPI 8703.22 8,28 8703.23.10 13,55 8703.23.10 Ex 01 8,28"
ipi(F2, "8703.22", i, f, "8,28", a, flex, p)
ipi(F4, "8703.23.10", i, f, "13,55", a, flex, p)
ipi(F3, "8703.23.10 Ex 01", i, f, "8,28", a, flex, p)

# ---- 2025: IPI Verde (Decreto 12.549), aliquota base antes de acrescimos e decrescimos
a, i = "ipi_2025_dec12549", "2025-11-01"
VERDE = ("Aliquota base do IPI Verde; o ato soma ou subtrai pontos por fonte de energia (flex 0; "
         "gasolina, hibrido e eletrico com valores proprios), eficiencia e reciclabilidade.")
for cats, codigo in ((TODOS1, "8703.21.00"), ((G2, F2), "8703.22.10"),
                     ((G3, F3, G4, F4), "8703.23.10")):
    ipi(cats, codigo, i, "", "6,30", a, f"{codigo} 6,30", obs=VERDE)

# ---------------------------------------------------- IPI: hibridos e eletricos (8703.40-80)
E40, E60, E80 = (politicas.CATEGORIAS_IPI[k] for k in ("e40", "e60", "e80"))
EE_HIBRIDO = ("EE ate 1,10 MJ/km", "EE de 1,10 a 1,68 MJ/km", "EE acima de 1,68 MJ/km")
EE_ELETRICO = ("EE ate 0,66 MJ/km", "EE de 0,66 a 1,35 MJ/km", "EE acima de 1,35 MJ/km")
MASSAS = ("massa ate 1400 kg", "massa de 1400 a 1700 kg", "massa acima de 1700 kg")
MOM = re.compile(r"MOM (?:menor ou igual a 1400|maior que 1400 e menor ou(?: igual a 1700)?|"
                 r"maior que 1700) (\d+(?:,\d+)?)")
EE_OBS = ("Tabela lida em ordem: o texto do PDF embaralha as colunas, mas os 18 valores vem "
          "na ordem eficiencia x massa, primeiro 8703.40/8703.60 e depois 8703.80. Flex ou "
          "alcool tem dois pontos a menos.")


def tabela_ee(a, pagina, marca_ini, marca_fim, ini, fim, obs=EE_OBS):
    t = texto(pagina)
    i0 = t.index(normal(marca_ini))
    segmento = t[i0:t.index(normal(marca_fim), i0)]
    achados = list(MOM.finditer(segmento))
    assert len(achados) == 18, (a, len(achados))
    for k, m in enumerate(achados):
        grupo, banda, massa = k // 9, (k % 9) // 3, k % 3
        alvos = ((E40, "8703.40.00"), (E60, "8703.60.00")) if grupo == 0 else ((E80, "8703.80.00"),)
        faixa = (EE_HIBRIDO if grupo == 0 else EE_ELETRICO)[banda]
        for cat, codigo in alvos:
            linha("ipi", codigo, f"{faixa}, {MASSAS[massa]}", ini, fim, m.group(1), a,
                  f"{marca_ini} [...] {m.group(0)}", pagina, categoria_ipi=cat, obs=obs)


tabela_ee("ipi_2018_dec9442", "dec_9442_2018", "NC (87-6) Ficam fixadas",
          "Ficam reduzidas em dois pontos", "2018-11-01", "2022-02-24")
tabela_ee("ipi_2022_dec10979", "dec_10979_2022", "8703.40.00 e 8703.60.00 EE",
          "Ficam reduzidas em dois pontos", "2022-02-25", "2022-04-30")
tabela_ee("ipi_2022_dec11055", "dec_11055_2022_anexo",
          "EFICIÊNCIA ENERGÉTICA (EE) CÓDIGO DA MASSA", "Ficam reduzidas em dois pontos",
          "2022-05-01", "2022-07-31")
tabela_ee("ipi_2022_dec11158", "dec_11158_2022_anexo4", "CÓDIGO EFICIÊNCIA DA TIPI ENERGÉTICA",
          "Ficam reduzidas em dois pontos", "2022-08-01", "2025-10-31")
for cat, codigo in ((E40, "8703.40.00"), (E60, "8703.60.00"), (E80, "8703.80.00")):
    linha("ipi", codigo, "aliquota base do IPI Verde", "2025-11-01", "", "6,30",
          "ipi_2025_dec12549", f"{codigo} 6,30", categoria_ipi=cat, obs=VERDE)

# ------------------------------------------- IPI: aliquota efetiva da empresa habilitada
# De 16/12/2011 a 31/12/2017 a TIPI inclui os 30 pontos; a empresa habilitada tem a reducao
# que o proprio ato da'. Fora desse periodo, a efetiva e' a nominal.
RED_7567_GAS = ("ANEXO III (Redação dada pelo Decreto nº 7.604, de 2011) De 16 de dezembro de "
                "2011 a 31 de dezembro de 2012: Código NCM Redução (em pontos percentuais)")
RED_7567_FLEX = ("Redução para os produtos de que trata a NC (87-2): Código NCM Redução (em pontos "
                 "percentuais) 8703.21 30 8703.22 30 8703.23.10 30 8703.23.10 Ex 01 30")
CODIGO_RED_GAS = {G1: "8703.21.00 30", G2: "8703.22.10 30", G3: "8703.23.10 Ex01 30",
                  G4: "8703.23.10 30"}
RED_7819 = ("§ 1º O valor do crédito presumido a ser utilizado para o pagamento de que trata o "
            "caput fica limitado ao valor correspondente ao que resultaria da aplicação de trinta "
            "por cento sobre a base de cálculo prevista na legislação do IPI")
OBS_7819 = ("Inovar-Auto: a reducao vem do credito presumido, limitado a 30% da base de calculo "
            "(art. 14, par. 1o); a efetiva e' a menor possivel, que a empresa so' alcanca com "
            "credito bastante.")


def efetiva_habilitada(r: dict) -> None:
    if r["tributo"] != "ipi":
        return
    ini, fim = r["vigencia_inicio"], r["vigencia_fim"] or "9999-12-31"
    if fim < "2011-12-16" or ini > "2017-12-31":
        r["aliquota_efetiva_habilitada"] = r["aliquota_pct"]
        return
    assert "2011-12-16" <= ini and fim <= "2017-12-31", (r["ato_id"], ini, fim)
    nominal = float(r["aliquota_pct"].replace(",", "."))
    efetiva = f"{max(nominal - 30, 0):g}".replace(".", ",")
    r["aliquota_efetiva_habilitada"] = efetiva
    if fim <= "2012-12-31":
        r["reducao_ato_id"], r["reducao_pagina"] = "ipi_2011_dec7567", "dec_7567_2011"
        r["reducao_trecho"] = (RED_7567_FLEX if r["categoria_ipi"] in (F1, F2, F3, F4)
                               else f"{RED_7567_GAS} [...] {CODIGO_RED_GAS[r['categoria_ipi']]}")
    else:
        assert ini >= "2013-01-01", (r["ato_id"], ini)
        r["reducao_ato_id"], r["reducao_pagina"] = "regime_2012_dec7819", "dec_7819_2012"
        r["reducao_trecho"] = RED_7819
        r["observacao"] = (r["observacao"] + " " + OBS_7819).strip()


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
for a, v in [("credito_2002_iof_dec4494", "0,0041"), ("credito_2007_iof_dec6306", "0,0041"),
             ("credito_2008_iof_dec6339", "0,0082"), ("credito_2008_iof_dec6691", "0,0041"),
             ("credito_2011_iof_dec7458", "0,0082"), ("credito_2011_iof_dec7632", "0,0068"),
             ("credito_2012_iof_dec7726", "0,0041 "), ("credito_2015_iof_dec8392", "0,0082")]:
    fim = "2008-01-02" if a == "credito_2007_iof_dec6306" else POR_ID[a]["vigencia_fim"]
    linha("iof", "", "credito a pessoa fisica, aliquota diaria", POR_ID[a]["vigencia_inicio"],
          fim, v.strip(), a, f"pessoa física: {v}% ao dia")



def uma_por_periodo(linhas: list[dict]) -> list[dict]:
    """Uma aliquota por periodo. A linha nao comeca antes do seu ato; quando um ato
    posterior fixa de novo a mesma linha (mesma categoria; fora do IPI, mesma NCM e
    categoria) num periodo que cruza o dela, a linha do anterior vale ate' a vespera da
    do posterior, e sai se nem chegou a valer (cronograma substituido antes de valer)."""
    inicio = {a["id"]: a["vigencia_inicio"] for a in A}
    for r in linhas:
        r["vigencia_inicio"] = max(r["vigencia_inicio"], inicio[r["ato_id"]])
    chave = politicas.chave_da_aliquota
    saida = []
    for r in linhas:
        for s in linhas:
            if chave(s) != chave(r) or inicio[s["ato_id"]] <= inicio[r["ato_id"]]:
                continue
            cruza = ((not s["vigencia_fim"] or r["vigencia_inicio"] <= s["vigencia_fim"])
                     and (not r["vigencia_fim"] or s["vigencia_inicio"] <= r["vigencia_fim"]))
            if not cruza:
                continue
            vespera = (date.fromisoformat(s["vigencia_inicio"]) - timedelta(days=1)).isoformat()
            r["vigencia_fim"] = min(r["vigencia_fim"] or vespera, vespera)
        if r["vigencia_fim"] and r["vigencia_fim"] < r["vigencia_inicio"]:
            print(f"fora (substituida antes de valer): {r['ato_id']} {r['ncm']} "
                  f"{r['categoria']} {r['vigencia_inicio']}")
            continue
        saida.append(r)
    return saida


def conferir(linhas: list[dict]) -> list[str]:
    erros = []
    for r in linhas:
        for pagina, trecho in ((r["pagina_salva"], r["fonte_trecho"]),
                               (r.get("reducao_pagina", ""), r.get("reducao_trecho", ""))):
            if not trecho:
                continue
            t = texto(pagina)
            for parte in trecho.split(" [...] "):
                if normal(parte) not in t:
                    erros.append(f"{r.get('id') or r['ato_id']} ({pagina}): {parte[:100]}")
    return erros


def main() -> int:
    global R
    R = uma_por_periodo(R)
    for r in R:
        efetiva_habilitada(r)
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
