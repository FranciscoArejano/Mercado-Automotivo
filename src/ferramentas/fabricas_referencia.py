#!/usr/bin/env python3
"""Monta as duas tabelas de fabricas da origem por pais (rodada 12, sec. 2.2).

- `dados/referencia/fabricas.csv`: empresa, fabrica, pais (nome e codigo do Comex
  Stat), municipio, UF e codigo IBGE (Brasil), inicio e fim de operacao quando a fonte
  os da', e a fonte;
- `dados/referencia/fabrica_modelos.csv`: que modelo (chave do painel) cada fabrica
  produziu, em que periodo, segundo que fonte, com o `vinculo` e a `regra_periodo` de
  `comum/origem_pais.py`.

Tres origens de linha:

1. **A' mao**, a partir das paginas guardadas em `dados/bruto/fabricas_paginas/` (e
   das de `origem_paginas/` ja' usadas pela origem): cada linha leva o trecho literal.
2. **ADEFA** (producao por modelo e versao na Argentina, anuarios 2006, 2013, 2017 e
   2025): as linhas de versao de cada modelo sao somadas por ano; uma linha por chave e
   ano com producao, `producao_no_exterior`, trecho = as linhas de versao. Falta 2007
   (os anuarios de 2007 a 2011 sao Flash).
3. **INEGI** (exportacao de veiculos leves por modelo e pais destino, filtrada para o
   Brasil, 2005 em diante): uma linha por chave e bloco de meses seguidos com exportacao
   ao Brasil (do primeiro mes ao ultimo mais dois, de transporte e estoque; bloco de menos
   de 100 unidades nao conta), `abastece_o_brasil`, trecho = a linha do mes de maior
   exportacao do bloco.

Antes de gravar, o script confere que cada parte de cada trecho (separadas por
" [...] ") esta' literalmente na pagina guardada, com os espacos normalizados; o teste
`test_origem_pais.py` repete a conferencia.

Uso:
    python src/ferramentas/fabricas_referencia.py
"""

from __future__ import annotations

import csv
import io
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from comum import config, origem_pais, tipo_fonte  # noqa: E402

PASTAS = {"fabricas_paginas": config.FABRICAS_PAGINAS,
          "origem_paginas": config.DIR_BRUTO / "origem_paginas"}
MAPA = tipo_fonte.carregar_mapa()
PAISES = origem_pais.paises_comex()
IBGE = origem_pais.municipios_ibge()
normal = origem_pais.normalizar
_TEXTO: dict[str, str] = {}
_MAN: dict[str, dict] = {}


def _manifesto(pasta: str) -> dict:
    if pasta not in _MAN:
        caminho = PASTAS[pasta] / "manifesto.csv"
        _MAN[pasta] = {r["nome"]: r for r in csv.DictReader(caminho.open(encoding="utf-8"))}
    return _MAN[pasta]


def texto(pagina: str) -> str:
    """Texto normalizado de 'pasta/nome'."""
    if pagina not in _TEXTO:
        pasta, nome = pagina.split("/")
        _TEXTO[pagina] = normal((PASTAS[pasta] / f"{nome}.txt").read_text(encoding="utf-8"))
    return _TEXTO[pagina]


def url_de(pagina: str) -> str:
    pasta, nome = pagina.split("/")
    return _manifesto(pasta)[nome]["url"]


def _p(nome: str) -> str:
    """Nome curto -> 'pasta/nome' (procura primeiro em fabricas_paginas)."""
    for pasta in PASTAS:
        if (PASTAS[pasta] / f"{nome}.txt").exists():
            return f"{pasta}/{nome}"
    raise FileNotFoundError(nome)


# ======================================================================= fabricas

F: list[dict] = []
A26 = "anfavea_anuario2026_unidades_industriais"
A23 = "anfavea_anuario2023_unidades_industriais"


def fabrica(id, empresa, nome, pais, municipio="", uf="", pagina="", trecho="", inicio="",
            fim="", pagina_op="", trecho_op="", obs=""):
    pag = _p(pagina) if pagina else ""
    F.append({
        "fabrica_id": id, "empresa": empresa, "fabrica": nome, "pais": pais,
        "pais_codigo": PAISES[pais], "municipio": municipio, "uf": uf,
        "cod_ibge_municipio": IBGE[(municipio, uf)] if municipio else "",
        "operacao_inicio": inicio, "operacao_fim": fim,
        "fonte_url": url_de(pag) if pag else "",
        "tipo_fonte": tipo_fonte.tipo_de(url_de(pag), MAPA) if pag else "",
        "fonte_trecho": trecho, "pagina_salva": pag,
        "operacao_trecho": trecho_op, "operacao_pagina": _p(pagina_op) if pagina_op else "",
        "observacao": obs})


BR = "Brasil"
fabrica("vw_anchieta", "Volkswagen", "Anchieta", BR, "São Bernardo do Campo", "SP", A26,
        "São Bernardo do Campo - SP Automóveis, comerciais leves Cars, light commercial "
        "vehicles [...] Volkswagen Vinhedo - SP Centro de distribuição", "1959", "",
        "vw_14_mais_fabricados_motorshow",
        "Esse volume contempla a produção das fábricas de Anchieta, em São Bernardo do "
        "Campo, inaugurada em 1959")
fabrica("vw_taubate", "Volkswagen", "Taubaté", BR, "Taubaté", "SP", A26,
        "Taubaté - SP Automóveis Cars [...] Volkswagen Vinhedo - SP Centro de distribuição",
        "1976-01", "", "vw_taubate_50anos_omecanico",
        "Inaugurada em 14 de janeiro de 1976")
fabrica("vw_sjp", "Volkswagen", "São José dos Pinhais", BR, "São José dos Pinhais", "PR", A26,
        "Volkswagen Vinhedo - SP Centro de distribuição Distribution center [...] São José dos "
        "Pinhais - PR Automóveis Cars", "1998", "", "vw_14_mais_fabricados_motorshow",
        "e São José dos Pinhais, no Paraná (1998)")
fabrica("audi_sjp", "Audi", "São José dos Pinhais", BR, "São José dos Pinhais", "PR", A26,
        "Audi São José dos Pinhais - PR Automóveis Cars")
fabrica("vwco_resende", "Volkswagen Caminhões e Ônibus", "Resende", BR, "Resende", "RJ", A26,
        "Resende - RJ Comerciais leves, caminhões e chassis para ônibus")
fabrica("fiat_betim", "Stellantis (Fiat)", "Polo Automotivo de Betim", BR, "Betim", "MG", A26,
        "Betim - MG Automóveis, comerciais leves, motores, transmissões")
fabrica("stellantis_goiana", "Stellantis (Jeep, Fiat, Ram)", "Polo Automotivo de Goiana", BR,
        "Goiana", "PE", A26, "Goiana - PE Automóveis, comerciais leves Cars, light commercial "
        "vehicles", "2015-04", "", "jeep_goiana_10anos_autodata_87978",
        "a operação nasceu, em abril de 2015, com o nome de Polo Automotivo Jeep")
fabrica("stellantis_porto_real", "Stellantis (Peugeot, Citroën)", "Polo Automotivo de Porto "
        "Real", BR, "Porto Real", "RJ", A26, "Stellantis Porto Real - RJ Automóveis Cars",
        "2001-02", "", "stellantis_porto_real_25anos_revistacarro",
        "Inaugurada em fevereiro de 2001, a unidade foi a primeira fábrica de automóveis "
        "instalada no estado do Rio de Janeiro")
fabrica("gm_scs", "General Motors", "São Caetano do Sul", BR, "São Caetano do Sul", "SP", A26,
        "São Caetano do Sul - SP Automóveis Cars")
fabrica("gm_sjc", "General Motors", "São José dos Campos", BR, "São José dos Campos", "SP", A26,
        "Automóveis, transmissoes manuais, motores Cars, manual transmissions, engines, and "
        "other [...] São José dos Campos - SP", "1959-03", "", "gm_sjc_65anos_media_gm",
        "Inaugurada no dia 10 de março de 1959")
fabrica("gm_gravatai", "General Motors", "Gravataí", BR, "Gravataí", "RS", A26,
        "Gravataí - RS Automóveis Cars", "2000-07", "", "gm_gravatai_45milhoes_media_gm",
        "A fábrica da GM em Gravataí iniciou suas atividades em 20 de julho de 2000")
fabrica("honda_itirapina", "Honda", "Itirapina", BR, "Itirapina", "SP", A26,
        "Itirapina - SP Automóveis Cars", "2019-02", "", "honda_itirapina_inaugura_autoindustria",
        "No dia 27 de fevereiro foi produzido o primeiro Fit em Itirapina.")
fabrica("honda_sumare", "Honda", "Sumaré", BR, "Sumaré", "SP", "honda_itirapina_inaugura_autoindustria",
        "localizada a cerca de 100 quilômetros de Sumaré, onde desde 1997 produz seus carros aqui",
        "1997", "", "", "", "Desde 2021 so' motores (Anfavea 2026: 'Sumaré - SP Motores e "
        "cabeçotes'); o fim da montagem de carros em Sumaré nao esta' datado em pagina guardada.")
fabrica("hpe_catalao", "HPE (Mitsubishi, Suzuki)", "Catalão", BR, "Catalão", "GO", A26,
        "Catalão - GO Automóveis, comerciais leves Cars, light commercial vehicles [...] HPE")
fabrica("hyundai_piracicaba", "Hyundai", "Piracicaba", BR, "Piracicaba", "SP", A26,
        "Hyundai Piracicaba - SP Automóveis Cars")
fabrica("caoa_anapolis", "Caoa (Hyundai, Chery)", "Anápolis", BR, "Anápolis", "GO", A26,
        "Anápolis - GO Automóveis, comerciais leves Cars, light commercial vehicles")
fabrica("chery_jacarei", "Chery / Caoa Chery", "Jacareí", BR, "Jacareí", "SP", A26,
        "Jacareí - SP Automóveis Cars [...] Caoa")
fabrica("iveco_sete_lagoas", "Iveco", "Sete Lagoas", BR, "Sete Lagoas", "MG", A26,
        "Iveco Sete Lagoas - MG Veículos comerciais e veículos para transporte de passageiros")
fabrica("jlr_itatiaia", "Jaguar Land Rover", "Itatiaia", BR, "Itatiaia", "RJ", A23,
        "Jaguar Land Rover Itatiaia - RJ Automóveis Cars")
fabrica("nissan_resende", "Nissan", "Resende", BR, "Resende", "RJ", A26,
        "Nissan Resende - RJ Automóveis Cars", "2014-04", "",
        "nissan_resende_10anos_autodata_70722",
        "Inaugurada em 15 de abril de 2014 a fábrica da Nissan instalada em Resende, RJ")
fabrica("renault_sjp", "Renault", "Complexo Ayrton Senna", BR, "São José dos Pinhais", "PR", A26,
        "São José dos Pinhais - PR [...] (Fábrica Curitiba veículos de passeio) [...] Renault "
        "Geely [...] (Fábrica Curitiba veículos utilitários)", "1998", "",
        "renault_3milhoes_autoindustria", "A fábrica paranaense da marca nasceu em 1998",
        "As duas fabricas do complexo (passeio e utilitarios) numa linha so'.")
fabrica("toyota_indaiatuba", "Toyota", "Indaiatuba", BR, "Indaiatuba", "SP", A26,
        "Indaiatuba - SP Automóveis Cars", "1998", "2026-06",
        "toyota_indaiatuba_adeus_autoindustria",
        "o processo de transferência da produção do Corolla para Sorocaba, SP, está sendo "
        "concluído oficialmente nesta terça-feira, 30 de junho, com o encerramento das "
        "operações da fábrica de Indaiatuba")
fabrica("toyota_sorocaba", "Toyota", "Sorocaba", BR, "Sorocaba", "SP", A26,
        "Toyota Sorocaba - SP", "2012", "", "toyota_3milhoes_motorshow",
        "A planta de Sorocaba, interior de São Paulo, foi criada em meados de 2012.")
fabrica("bmw_araquari", "BMW", "Araquari", BR, "Araquari", "SC", A26,
        "BMW Araquari - SC Automóveis Cars")
fabrica("agrale_caxias", "Agrale", "Caxias do Sul (Unidade 2)", BR, "Caxias do Sul", "RS", A26,
        "Comerciais leves, caminhões leves, médios e semipesados e Light commercial vehicles, "
        "light, medium, and [...] Caxias do Sul - RS (Unidade 2)")
fabrica("ford_camacari", "Ford", "Camaçari", BR, "Camaçari", "BA", "ford_5fabricas_autopapo",
        "A inauguração da unidade baiana ocorreu em 2001.", "2001", "2021-01",
        "ford_fecha_fabricas_autoindustria",
        "A produção será encerrada imediatamente em Camaçari, BA, e Taubaté, SP")
fabrica("ford_sbc", "Ford", "São Bernardo do Campo (Taboão)", BR, "São Bernardo do Campo", "SP",
        "ford_5fabricas_autopapo",
        "A unidade do Taboão, em São Bernardo do Campo (SP), iniciou as atividades em 1954, "
        "montando o utilitário Jeep. [...] Em 1967, a Ford adquiriu todas as operações da Willys "
        "Overland no Brasil, inclusive a fábrica no ABC paulista. [...] Com o fechamento da "
        "planta, em 2019, esses veículos saíram de linha.", "1967", "2019")
fabrica("troller_horizonte", "Ford (Troller)", "Horizonte", BR, "Horizonte", "CE",
        "ford_fecha_fabricas_autoindustria",
        "A fábrica da Troller em Horizonte, CE, continuará operando até o quarto trimestre de "
        "2021.", "", "2021-12")
# fabricas so' da proposta: sem fonte de localizacao guardada nesta rodada
fabrica("mb_juiz_de_fora", "Mercedes-Benz", "Juiz de Fora", BR, "Juiz de Fora", "MG",
        "mb_classea_motorshow_fracasso",
        "em fevereiro de 1999, a Mercedes-Benz passou a produzir integralmente o novo Classe A em "
        "uma fábrica especialmente concebida para isso, na cidade de Juiz de Fora (MG).", "1999-02",
        obs="A Anfavea 2026 lista Juiz de Fora so' com cabinas de caminhoes; a montagem de "
            "automoveis acabou (fim do Classe A em 2005, do CLC sem data guardada).")
fabrica("mb_iracemapolis", "Mercedes-Benz", "Iracemápolis", BR, "Iracemápolis", "SP",
        "mb_gla_automotiveworld",
        "The Mercedes-Benz Iracemápolis plant is located in the São Paulo region and was opened in "
        "March 2016.", "2016-03", obs="Fim da montagem de automoveis (2020) sem pagina guardada "
        "nesta tabela; ver origem_fontes.")
fabrica("byd_camacari", "BYD", "Camaçari", BR, "Camaçari", "BA", "byd_camacari_autodata_96403",
        "A BYD montou 363 Dolphin Mini no primeiro mês de operação da fábrica de Camaçari, BA, "
        "inaugurada em outubro.", "2025-10")
fabrica("gwm_iracemapolis", "GWM", "Iracemápolis", BR, "Iracemápolis", "SP",
        "gwm_iracemapolis_um_ano",
        "Doze meses depois, a planta de Iracemápolis consolida uma operação industrial completa",
        "2025-08", obs="Inaugurada em agosto de 2025 (um ano antes da pagina de agosto de 2026).")
fabrica("gm_horizonte", "General Motors (PACE)", "Planta Automotiva do Ceará", BR, "Horizonte",
        "CE", "gm_spark_autopapo_pace",
        "Foi inaugurada nesta quarta (3) a PACE, Planta Automotiva do Ceará. Ela fica localizada em "
        "Horizonte (CE), onde era a unidade fabril da Troller.", "2025-12")
fabrica("nissan_sjp", "Nissan", "São José dos Pinhais", BR, "São José dos Pinhais", "PR",
        obs="Frontier e Xterra no complexo de Sao Jose dos Pinhais; sem pagina guardada.")
fabrica("mahindra_manaus", "Bramont (Mahindra)", "Manaus", BR, "Manaus", "AM",
        obs="Montagem da Bramont; sem pagina guardada.")


AR, MX = "Argentina", "México"
EMPRESAS_AR = {"ar_toyota": "Toyota Argentina S.A.", "ar_ford": "Ford Argentina S.C.A.",
               "ar_vw": "Volkswagen Argentina S.A.", "ar_fiat": "Fiat Auto / FCA Argentina S.A.",
               "ar_gm": "General Motors de Argentina S.R.L.",
               "ar_psa": "Peugeot-Citroën Argentina S.A.", "ar_renault": "Renault Argentina S.A.",
               "ar_nissan": "Nissan Argentina S.A.", "ar_mb": "Mercedes-Benz Argentina S.A.",
               "ar_honda": "Honda Motor de Argentina S.A."}
EMPRESAS_MX = {"mx_audi": "Audi México", "mx_bmw": "BMW Group (México)",
               "mx_chrysler": "FCA / Stellantis México", "mx_ford": "Ford Motor (México)",
               "mx_gm": "General Motors de México", "mx_honda": "Honda de México",
               "mx_kia": "Kia Motors México", "mx_mb": "Mercedes-Benz (México)",
               "mx_nissan": "Nissan Mexicana", "mx_vw": "Volkswagen de México"}
def fabricas_exterior() -> None:
    for fab, empresa in EMPRESAS_AR.items():
        fabrica(fab, empresa, f"{empresa} (planta não identificada na fonte)", AR,
                obs="A ADEFA da' a producao por empresa e modelo, nao a planta.")
    for fab, empresa in EMPRESAS_MX.items():
        fabrica(fab, empresa, f"{empresa} (planta não identificada na fonte)", MX,
                obs="O INEGI da' a exportacao por marca e modelo, nao a planta.")


fabricas_exterior()

# ============================================================ fabrica x modelo, a mao

L: list[dict] = []
FAB = {f["fabrica_id"]: f for f in F}


def chave(texto_chave: str) -> tuple[str, str, str]:
    """'FIAT|STRADA|c' -> (marca, modelo, segmento)."""
    marca, modelo, seg = texto_chave.split("|")
    return marca, modelo, {"a": "automoveis", "c": "comerciais_leves"}[seg]


def linha(fab, chaves, inicio, fim, vinculo, regra, data, pagina, trecho, obs="", pais=None):
    pag = _p(pagina)
    if isinstance(chaves, str):
        chaves = [chaves]
    pais = pais or (FAB[fab]["pais"] if fab else BR)
    for k in chaves:
        marca, modelo, segmento = chave(k)
        L.append({"fabrica_id": fab, "pais": pais, "marca": marca, "modelo": modelo,
                  "segmento": segmento, "periodo_inicio": inicio, "periodo_fim": fim,
                  "vinculo": vinculo, "regra_periodo": regra, "data_fonte": data,
                  "fonte_url": url_de(pag), "tipo_fonte": tipo_fonte.tipo_de(url_de(pag), MAPA),
                  "fonte_trecho": trecho, "pagina_salva": pag, "observacao": obs})


PL, AB = "producao_local", "abastece_o_brasil"
DEC, INI, DUR, PTO = ("declarado", "inicio_ate_a_pagina", "duracao_ate_a_pagina",
                      "na_data_da_pagina")

# ---- Volkswagen
T50 = "vw_taubate_50anos_omecanico"
linha("vw_taubate", "VW|GOL|a", "1980-01", "2022-12", PL, DEC, "2026-01", T50,
      "Em 1980, teve início a produção do Volkswagen Gol, o maior ícone da planta. [...] A "
      "produção do Gol e do Voyage foi encerrada em 2022.")
linha("vw_taubate", "VW|VOYAGE|a", "1982-01", "2022-12", PL, DEC, "2026-01", T50,
      "A família Gol — composta também por Voyage, Parati e Saveiro — passou a ser produzida "
      "na unidade a partir de 1982. [...] A produção do Gol e do Voyage foi encerrada em 2022.")
linha("vw_taubate", ["VW|PARATI|a", "VW|SAVEIRO|c"], "1982-01", "2026-01", PL, INI, "2026-01",
      T50, "A família Gol — composta também por Voyage, Parati e Saveiro — passou a ser "
      "produzida na unidade a partir de 1982.",
      "A pagina da' o inicio em Taubate e lista o modelo entre os ja' produzidos ali, sem o fim.")
linha("vw_taubate", "VW|UP|a", "2014-01", "2021-12", PL, DEC, "2026-01", T50,
      "Entre 2014 e 2021, Taubaté produziu o Volkswagen up!")
linha("vw_taubate", "VW|POLO|a", "2023-01", "2026-01", PL, INI, "2026-01", T50,
      "possibilitando a produção do Polo Track, iniciada em 2023. [...] Atualmente, a fábrica "
      "produz Tera, Polo e Polo Track")
linha("vw_taubate", "VW|TERA|a", "2025-06", "2026-01", PL, INI, "2026-01", T50,
      "O SUV Tera, lançado em junho de 2025 [...] Atualmente, a fábrica produz Tera, Polo e "
      "Polo Track")
linha("vw_taubate", ["VW|TERA|a", "VW|POLO|a"], "2025-12", "2025-12", PL, PTO, "2025-12",
      "vw_taubate_8milhoes_autodata_98288",
      "Atualmente dois modelos são produzidos em Taubaté, o Polo e o Tera.")
linha("vw_taubate", ["VW|TERA|a", "VW|POLO|a"], "2026-01", "2026-01", PL, PTO, "2026-01",
      "vw_taubate_50anos_autodata_98597",
      "Atualmente produz o Tera, SUV compacto, e os hatches Polo e Polo Track.")
linha("vw_taubate", ["VW|GOL|a", "VW|VOYAGE|a"], "2022-11", "2022-11", PL, PTO, "2022-11",
      "vw_gol_polo_track_autodata_48428",
      "Na virada do ano o Gol deixará as linhas de montagem de Taubaté, SP, para dar lugar ao "
      "Polo Track [...] ainda há volume de Gol e Voyage em produção na fábrica")
linha("vw_sjp", "VW|FOX/CROSS FOX|a", "2003-01", "2021-10", PL, DEC, "2021-10",
      "vw_fox_fim_autopapo",
      "“Desde o seu lançamento, em 2003, o Fox foi produzido exclusivamente na fábrica do "
      "Paraná e ao longo destes 18 anos")
M14 = "vw_14_mais_fabricados_motorshow"
linha("vw_sjp", "VW|GOLF|a", "1998-01", "2013-12", PL, DEC, "2026-01", M14,
      "A produção nacional do hatch médio da VW ocorreu em dois períodos distintos: entre 1998 "
      "e 2013, e depois entre 2016 e 2019, sempre na fábrica paranaense de Pinhais.")
linha("vw_sjp", "VW|GOLF|a", "2016-01", "2019-12", PL, DEC, "2026-01", M14,
      "A produção nacional do hatch médio da VW ocorreu em dois períodos distintos: entre 1998 "
      "e 2013, e depois entre 2016 e 2019, sempre na fábrica paranaense de Pinhais.")
linha("vw_sjp", "VW|T CROSS|a", "2019-01", "2026-01", PL, INI, "2026-01", M14,
      "Lançado em 2019, o T-Cross é o primeiro SUV compacto da Volks produzido no Brasil. "
      "Rapidamente se consolidou como um dos SUVs mais vendidos do País e segue em produção em "
      "São José dos Pinhais.")
linha("vw_anchieta", "VW|NIVUS|a", "2020-01", "2026-01", PL, INI, "2026-01", M14,
      "Apresentado em 2020, o Nivus inaugurou o segmento de SUVs coupés compactos da VW no "
      "Brasil. Desenvolvido localmente, é produzido em São Bernardo do Campo")
linha("vw_taubate", "VW|TERA|a", "2026-01", "2026-01", PL, PTO, "2026-01", M14,
      "O Tera é o SUV mais recente da VW no Brasil, com produção em Taubaté.")
linha("", "VW|KOMBI|c", "1957-01", "2013-12", PL, DEC, "2026-01", M14,
      "Produzida no Brasil desde 1957, a Kombi foi um dos veículos mais longevos da indústria "
      "nacional. [...] Saiu de linha em 2013, encerrando sua trajetória",
      "Pais sem fabrica: a pagina nao diz a planta.")
linha("", "VW|PARATI|a", "1982-01", "2012-12", PL, DEC, "2026-01", M14,
      "Versão perua do VW Gol, a Parati estreou em 1982 [...] Saiu de linha em 2012, com o fim "
      "da família Gol derivada.", "Pais sem fabrica: a lista e' de carros produzidos no Brasil.")
linha("", "VW|VOYAGE|a", "1981-01", "2023-12", PL, DEC, "2026-01", M14,
      "Sedan derivado do Gol, o Voyage estreou em 1981 [...] Saiu de linha em 2023.",
      "Pais sem fabrica: a lista e' de carros produzidos no Brasil.")
linha("", "VW|SAVEIRO|c", "1982-01", "2026-01", PL, INI, "2026-01", M14,
      "Lançada em 1982, a Saveiro é a versão picape do Gol. [...] A picape segue em linha no "
      "mercado brasileiro", "Pais sem fabrica: a lista e' de carros produzidos no Brasil.")
linha("", "VW|GOL|a", "1980-01", "2022-12", PL, DEC, "2026-01", M14,
      "Lançado em 1980, o Gol nasceu como hatch compacto [...] Saiu de linha em 2022 como o "
      "modelo mais produzido, vendido e exportado da história do Brasil.",
      "Pais sem fabrica: a lista e' de carros produzidos no Brasil.")
R65 = "vw_anchieta_65anos_revistacarro"
linha("vw_anchieta", "VW|POLO|a", "2002-01", "2024-11", PL, INI, "2024-11", R65,
      "2002: Inauguração da Nova Anchieta para produção do Polo. [...] Atualmente, a Anchieta "
      "fabrica o Polo GTS, o Virtus e o Saveiro.")
linha("vw_anchieta", "VW|SAVEIRO|c", "2016-01", "2024-11", PL, INI, "2024-11", R65,
      "2016: Anchieta inicia a produção de Novo Gol e a Nova Saveiro [...] Atualmente, a "
      "Anchieta fabrica o Polo GTS, o Virtus e o Saveiro.")
linha("vw_anchieta", "VW|GOL|a", "1994-01", "2022-12", PL, INI, "2024-11", R65,
      "1994: Início da produção do Gol na fábrica Anchieta [...] 2016: Anchieta inicia a "
      "produção de Novo Gol e a Nova Saveiro",
      "Fim no fim da producao do Gol (2022), dado pela pagina de Taubate.")
linha("vw_anchieta", "VW|VIRTUS|a", "2018-01", "2024-11", PL, INI, "2024-11", R65,
      "2018: Início da produção do Virtus [...] Atualmente, a Anchieta fabrica o Polo GTS, o "
      "Virtus e o Saveiro.")
linha("vw_anchieta", ["VW|POLO|a", "VW|NIVUS|a", "VW|VIRTUS|a", "VW|SAVEIRO|c"], "2026-02",
      "2026-02", PL, PTO, "2026-02", "vw_anchieta_15milhoes_autodata_99647",
      "Hoje saem das linhas de produção da Anchieta Polo Track, Nivus, Virtus e Saveiro")
linha("vw_anchieta", "VW|VIRTUS|a", "2018-01", "2025-11", PL, INI, "2025-11",
      "vw_virtus_300mil_autoindustria",
      "Com produção iniciada em 2018 na fábrica de São Bernardo do Campo, SP, e complementada "
      "em São José dos Pinhais, PR")
linha("vw_sjp", "VW|VIRTUS|a", "2025-01", "2025-11", PL, INI, "2025-11",
      "vw_virtus_300mil_autoindustria",
      "“A chegada do Virtus à produção de São José dos Pinhais, neste ano, consolida nossa "
      "fábrica")

# ---- Fiat, Jeep, Ram (Stellantis)
linha("fiat_betim", "FIAT|STRADA|c", "1998-01", "2025-09", PL, INI, "2025-09",
      "fiat_strada_25milhoes_autodata_94026",
      "A Fiat Strada chegou à marca de 2,5 milhões de unidades produzidas na fábrica de Betim, "
      "MG, desde 1998")
linha("fiat_betim", ["FIAT|ARGO|a", "FIAT|MOBI|a", "FIAT|PULSE|a", "FIAT|FASTBACK|a",
                     "FIAT|FIORINO|c", "PEUGEOT|PARTNER|c", "FIAT|STRADA|c"],
      "2025-09", "2025-09", PL, PTO, "2025-09", "fiat_strada_25milhoes_autodata_94026",
      "A fábrica de Betim tem capacidade para produzir 650 mil veículos/ano e, além da Strada, "
      "produz Argo, Mobi, Pulse, Fastback, Fiorino e Peugeot Partner Rapid.",
      "O Partner do painel, desde 2023, e' o Partner Rapid.")
linha("fiat_betim", ["FIAT|UNO|a", "FIAT|UNO|c"], "1984-08", "2021-12", PL, INI, "2021-12",
      "fiat_uno_ciao_motorshow",
      "Fabricado de forma ininterrupta desde agosto de 1984 no Polo Automotivo de Betim (MG), o "
      "Fiat Uno acumula 4.379.356 milhões de unidades produzidas.",
      "A chave comerciais leves e' o Uno furgao, da mesma linha.")
linha("fiat_betim", "FIAT|PALIO|a", "2017-11", "2017-11", PL, PTO, "2017-11",
      "fiat_palio_fim_autopapo",
      "De acordo com a assessoria de imprensa da Fiat, o Palio “continua em produção em Betim "
      "e, portanto, segue no mercado normalmente”.")
linha("fiat_betim", ["FIAT|WEEKEND|a", "FIAT|PALIO WEEKEND|a"], "1997-01", "2020-01", PL, DUR,
      "2020-01", "fiat_weekend_ultima_autodata_30411",
      "As linhas da fábrica da Fiat em Betim, MG, montaram na segunda-feira, 27, a última "
      "Weekend. Foram 23 anos de produção",
      "23 anos contados para tras da ultima unidade (janeiro de 2020).")
linha("fiat_betim", "FIAT|SIENA|a", "1999-01", "2025-03", PL, INI, "2025-03",
      "fiat_siena_2010_autopapo", "O carro passou a ser feito em Betim (MG) em 1999.")
linha("fiat_betim", "FIAT|MOBI|a", "2016-04", "2026-04", PL, INI, "2026-04",
      "fiat_mobi_10anos_autopapo",
      "Fabricado no Polo Automotivo de Betim (MG), o hatch subcompacto atingiu a marca de 700 "
      "mil unidades produzidas desde o seu lançamento, em abril de 2016.")
linha("fiat_betim", "FIAT|ARGO|a", "2017-01", "2023-11", PL, INI, "2023-11",
      "fiat_argo_500mil_revistacarro",
      "Lançado no Brasil em 2017, o Fiat Argo chega à marca de 500 mil unidades produzidas na "
      "fábrica da Stellantis em Betim, em Minas Gerais.")
J10 = "jeep_goiana_10anos_autodata_87978"
linha("stellantis_goiana", "JEEP|RENEGADE|a", "2015-04", "2025-05", PL, INI, "2025-05", J10,
      "a operação nasceu, em abril de 2015, com o nome de Polo Automotivo Jeep, e o primeiro "
      "modelo produzido foi o Renegade.")
linha("stellantis_goiana", "JEEP|COMMANDER|a", "2021-01", "2025-05", PL, INI, "2025-05", J10,
      "completaram, no fim de abril, dez anos de operação com a produção de quase 1,3 milhão "
      "de unidades dos SUVs Renegade [660 mil], Compass [545 mil] e Commander [75 mil] [...] "
      "até o sofisticado Commander de grande porte em 2021")
G15 = "stellantis_goiana_15milhao_autoindustria"
linha("stellantis_goiana", ["JEEP|RENEGADE|a", "JEEP|COMPASS|a", "JEEP|COMMANDER|a",
                            "FIAT|TORO|c"], "2023-04", "2023-04", PL, PTO, "2023-04", G15,
      "São três SUVs da Jeep — o pioneiro Renegade, o médio Compass e o topo de linha "
      "Commander — e a picape Fiat Toro em diversas versões.")
linha("stellantis_goiana", "FIAT|TORO|c", "2016-01", "2023-04", PL, INI, "2023-04", G15,
      "Já no ano seguinte, 2016, Toro e o Compass chegaram às lojas. [...] Única representante "
      "da linha Fiat fabricada em Goiana, a Toro também lidera seu segmento")
linha("stellantis_goiana", "JEEP|RENEGADE|a", "2015-03", "2026-01", PL, INI, "2026-01",
      "jeep_renegade_700mil_autodata_98722",
      "O Jeep Renegade chegou à marca de 700 mil unidades produzidas na fábrica de Goiana, PE. "
      "O SUV foi o primeiro modelo a ser fabricado ali, com a sua primeira geração saindo da "
      "linha de produção em março de 2015")
linha("stellantis_porto_real", "CITROEN|XSARA PICASSO|a", "2001-02", "2026-02", PL, INI,
      "2026-02", "stellantis_porto_real_25anos_autodata_99406",
      "Inaugurada em fevereiro de 2001 com a produção do Citroën Xsara Picasso")
linha("stellantis_porto_real", ["PEUGEOT|206|a", "CITROEN|XSARA PICASSO|a"], "2001-02",
      "2026-02", PL, INI, "2026-02", "stellantis_porto_real_25anos_revistacarro",
      "Inaugurada em fevereiro de 2001, a unidade foi a primeira fábrica de automóveis "
      "instalada no estado do Rio de Janeiro [...] Ao longo do período, 16 modelos passaram "
      "pelas linhas de montagem, com início nos projetos Peugeot 206 e Citroën Xsara Picasso.")
linha("stellantis_porto_real", ["CITROEN|C3|a", "CITROEN|AIRCROSS|a", "CITROEN|BASALT|a"],
      "2026-02", "2026-02", PL, PTO, "2026-02", "stellantis_porto_real_25anos_revistacarro",
      "Atualmente, a unidade produz os modelos Citroën C3, Aircross e Basalt")

# ---- GM
G5 = "gm_gravatai_5milhoes_autoindustria"
TL = ("2000 — Inauguração com o Celta (R$ 1,1 bilhão) 2006 — Ampliação para o Prisma (R$ 240 "
      "milhões) 2010-2012 — Expansão para o Onix (R$ 1,4 bilhão) 2019 — Modernização para novos "
      "Onix e Onix Plus (R$ 1,9 bilhão)")
PRODUZIU = ("Ao longo de sua trajetória, a unidade produziu modelos de grande volume da "
            "Chevrolet, caso de Celta, Prisma e da família Onix")
linha("gm_gravatai", "GM|CELTA|a", "2000-07", "2026-07", PL, INI, "2026-07", G5,
      f"unidade inaugurada em julho de 2000 para fabricar o Chevrolet Celta [...] {PRODUZIU}")
linha("gm_gravatai", "GM|PRISMA|a", "2006-01", "2026-07", PL, INI, "2026-07", G5,
      f"{PRODUZIU} [...] {TL}")
linha("gm_gravatai", "GM|ONIX|a", "2012-01", "2026-07", PL, INI, "2026-07", G5,
      f"{PRODUZIU} [...] {TL}")
linha("gm_gravatai", "GM|ONIX PLUS|a", "2019-01", "2026-07", PL, INI, "2026-07", G5,
      f"{PRODUZIU} [...] {TL}")
linha("gm_gravatai", "GM|SONIC|a", "2026-07", "2026-07", PL, PTO, "2026-07", G5,
      "Recentemente, a fábrica iniciou a produção do novo Chevrolet Sonic")
linha("gm_gravatai", ["GM|ONIX|a", "GM|ONIX PLUS|a"], "2020-07", "2020-07", PL, PTO, "2020-07",
      "gm_gravatai_20anos_autodata_31644",
      "produz o modelo campeão de vendas do mercado brasileiro, o Onix, além de sua versão "
      "sedã Onix Plus")
linha("gm_sjc", "GM|S10|c", "1995-01", "2020-07", PL, INI, "2020-07",
      "gm_s10_25anos_autodata_31542",
      "a picape Chevrolet S10, produzida desde 1995 em São José dos Campos, SP")
linha("gm_sjc", ["GM|S10|c", "GM|TRAILBLAZER|a"], "2024-03", "2024-03", PL, PTO, "2024-03",
      "gm_sjc_65anos_media_gm",
      "São seis fábricas que concentram a produção da picape S10 e do SUV Trailblazer")
linha("gm_scs", ["GM|TRACKER|a", "GM|SPIN|a", "GM|MONTANA|c", "GM|ONIX|a", "GM|PRISMA|a"],
      "2020-08", "2020-08", PL, PTO, "2020-08", "gm_scs_90anos_autodata_31820",
      "As linhas que produziram modelos icônicos, como Chevrolet Opala e Monza, eram bem "
      "diferentes das que, atualmente, entregam Tracker, Joy, Joy Plus, Spin e Montana.",
      "Joy e' o Onix da primeira geracao e Joy Plus o Prisma, vendidos com esses nomes.")
linha("gm_scs", ["GM|MONTANA|c", "GM|TRACKER|a", "GM|SPIN|a"], "2023-01", "2023-01", PL, PTO,
      "2023-01", "gm_scs_montana_autodata_50290",
      "GM São Caetano, atualizada, começa a produzir Montana [...] a Nova Montana demandou mais "
      "de um ano de obras na unidade São Caetano, em paralelo com a produção de Tracker e de "
      "Spin.")
linha("gm_scs", "GM|MONTANA|c", "2021-04", "2021-04", PL, PTO, "2021-05",
      "gm_montana_fim_revistacarro",
      "o Sindicato dos Metalúrgicos de São Caetano do Sul confirmou que a Montana não é mais "
      "produzida pela General Motors desde o fim de abril.",
      "A pagina de maio de 2021 da' o fim da producao em Sao Caetano: cobre o ultimo mes.")
linha("", "GM|CLASSIC|a", "2016-08", "2016-08", AB, PTO, "2016-09",
      "gm_classic_fim_revistacarro",
      "a GM confirmou o fim da importação do Classic, mas sua fabricação, atualmente em "
      "Rosário, na Argentina, ainda não terminou.",
      "Importado da Argentina ate' o mes anterior ao da pagina.", pais="Argentina")

# ---- Toyota
TM = "toyota_3milhoes_motorshow"
linha("toyota_indaiatuba", "TOYOTA|COROLLA|a", "1998-01", "2026-06", PL, DEC, "2026-06",
      "toyota_indaiatuba_adeus_autoindustria",
      "Inaugurada em 1998, a fábrica do interior paulista produziu mais de 1 milhão de Corolla "
      "Anunciado em 2024, o processo de transferência da produção do Corolla para Sorocaba, SP, "
      "está sendo concluído oficialmente nesta terça-feira, 30 de junho, com o encerramento das "
      "operações da fábrica de Indaiatuba")
linha("toyota_indaiatuba", "TOYOTA|COROLLA|a", "1998-01", "2025-06", PL, INI, "2025-06", TM,
      "A fábrica de Indaiatuba, erguida no final dos anos 1990, dá luz ao Corolla Sedan desde "
      "então [...] Início de produção do Corolla em Indaiatuba, em 1998")
linha("toyota_indaiatuba", "TOYOTA|FIELDER|a", "2000-01", "2009-12", PL, DEC, "2025-06", TM,
      "além de ter produzido sua perua Fielder por alguns anos na década de 2000.",
      "A pagina so' da' a decada.")
linha("toyota_sorocaba", ["TOYOTA|ETIOS HB|a", "TOYOTA|ETIOS SEDAN|a"], "2012-01", "2025-06",
      PL, INI, "2025-06", TM,
      "Lá, foram feitos Etios Hatch, Etios Sedan, Yaris Sedan, Yaris Hatch e Corolla Cross. "
      "[...] O Etios nasceu em 2012 com carroceria hatch ou sedan [...] Sempre foi feito em "
      "Sorocaba (SP), assim como Etios e Yaris")
linha("toyota_sorocaba", ["TOYOTA|YARIS HB|a", "TOYOTA|YARIS SEDAN|a"], "2018-06", "2025-06",
      PL, INI, "2025-06", TM,
      "Lá, foram feitos Etios Hatch, Etios Sedan, Yaris Sedan, Yaris Hatch e Corolla Cross. "
      "[...] O Yaris chegou na metade de 2018 [...] Sempre foi feito em Sorocaba (SP), assim "
      "como Etios e Yaris")
linha("toyota_sorocaba", "TOYOTA|COROLLA CROSS|a", "2021-01", "2025-06", PL, INI, "2025-06", TM,
      "o Cross nasceu oficialmente no começo de 2021 [...] Sempre foi feito em Sorocaba (SP)")

# ---- Hyundai
linha("hyundai_piracicaba", "HYUNDAI|HB20|a", "2012-09", "2017-09", PL, DEC, "2017-09",
      "hyundai_hb20_5anos_autodata_25293",
      "completaram-se os cinco primeiros anos de produção do HB20 na fábrica da Hyundai "
      "instalada em Piracicaba, SP. [...] foram produzidos 26 mil 3 HB20 de setembro a dezembro "
      "de 2012")
linha("hyundai_piracicaba", "HYUNDAI|HB20S|a", "2013-01", "2017-09", PL, DEC, "2017-09",
      "hyundai_hb20_5anos_autodata_25293",
      "completaram-se os cinco primeiros anos de produção do HB20 na fábrica da Hyundai "
      "instalada em Piracicaba, SP. [...] No primeiro ano completo de produção, esse volume "
      "saltou para 166 mil 269 unidades, já com as três versões disponíveis: o hatch HB20, o "
      "sedã HB20S")
linha("hyundai_piracicaba", ["HYUNDAI|HB20|a", "HYUNDAI|HB20S|a", "HYUNDAI|CRETA|a"], "2018-08",
      "2018-08", PL, PTO, "2018-08", "hyundai_1milhao_autoindustria",
      "dos HB20 hatch e sedã e do utilitário esportivo Creta, os três modelos fabricados no "
      "interior paulista.")
linha("hyundai_piracicaba", "HYUNDAI|CRETA|a", "2017-01", "2020-12", PL, INI, "2020-12",
      "hyundai_creta_200mil_autoindustria",
      "Lançado em janeiro de 2017, o Hyundai Creta acaba de acumular 200 mil unidades "
      "produzidas na fábrica da montadora em Piracicaba")

# ---- Ford
F5 = "ford_5fabricas_autopapo"
linha("ford_camacari", "FORD|ECOSPORT|a", "2003-01", "2021-01", PL, DEC, "2021-03", F5,
      "Em 2003, a unidade começou a fornecer o EcoSport [...] bruscamente encerrada no dia 11 de "
      "janeiro de 2021.")
linha("ford_camacari", ["FORD|KA|a", "FORD|KA SEDAN|a"], "2014-01", "2021-01", PL, DEC,
      "2021-03", F5,
      "Por fim, em 2014, a planta começou a fabricar a última geração do Ka, também nas "
      "configurações hatch e sedã. [...] bruscamente encerrada no dia 11 de janeiro de 2021.")
linha("ford_camacari", ["FORD|KA|a", "FORD|ECOSPORT|a"], "2019-02", "2019-02", PL, PTO,
      "2019-02", "ford_sbc_fechamento_autodata_28347",
      "Na Bahia são produzidos os modelos Ford Ka e EcoSport e motores.")
linha("ford_sbc", "FORD|FIESTA|a", "2019-02", "2019-02", PL, PTO, "2019-02",
      "ford_sbc_fechamento_autodata_28347",
      "anunciou o encerramento da produção de caminhões e do modelo hatch do Fiesta, que "
      "mantinha ativa a linha instalada no bairro do Taboão.")
linha("", "FORD|FIESTA|a", "1996-01", "2019-12", PL, DEC, "2019-11", "ford_sbc_icones_autopapo",
      "Em seus 24 anos de mercado, o Ford Fiesta marcou época. Ele começou a ser fabricado no "
      "Brasil em 1996, já na planta do ABC paulista. Depois de um tempo, passou a ser feito em "
      "Camaçari (BA), mas, depois, voltou para São Bernardo.",
      "Pais sem fabrica: a pagina alterna Sao Bernardo e Camacari sem datas; o fim (2019) e' o "
      "da fabrica, na mesma pagina.")
linha("", "FORD|KA|a", "1997-01", "2017-04", PL, INI, "2017-04", "ford_ka_1milhao_motorshow",
      "O Ka começou a ser produzido no Brasil em 1997, um ano após o lançamento do modelo no "
      "mercado europeu.", "Pais sem fabrica para a segunda geracao.")
linha("ford_sbc", "FORD|KA|a", "1997-01", "1997-12", PL, PTO, "2017-04",
      "ford_ka_1milhao_motorshow",
      "O Ka começou a ser produzido no Brasil em 1997 [...] Montado na fábrica da Ford em São "
      "Bernardo do Campo (SP).", "So' o inicio da primeira geracao tem fabrica na pagina.")

# ---- Renault
R3 = "renault_3milhoes_autoindustria"
linha("renault_sjp", "RENAULT|SCENIC|a", "1998-01", "2018-11", PL, INI, "2018-11", R3,
      "A fábrica paranaense da marca nasceu em 1998 a partir de investimento inicial de US$ 1,3 "
      "bilhão para iniciar a produção do Scénic")
linha("renault_sjp", ["RENAULT|CLIO|a", "RENAULT|CLIO SEDAN|a"], "2000-01", "2007-12", PL, DEC,
      "2018-11", R3, "Logo em seguida, a unidade recebeu o Clio, produzido de 2000 a 2007",
      "O texto nao separa hatch e sedan.")
linha("renault_sjp", ["RENAULT|KWID|a", "RENAULT|SANDERO|a", "RENAULT|LOGAN|a",
                      "RENAULT|DUSTER|a", "RENAULT|OROCH|c", "RENAULT|CAPTUR|a",
                      "RENAULT|MASTER|c"], "2018-11", "2018-11", PL, PTO, "2018-11", R3,
      "Atualmente, saem das linhas do complexo o Kwid, Sandero, Logan, Duster, Duster Oroch, "
      "Captur e o comercial leve Master.")
linha("renault_sjp", "RENAULT|KWID|a", "2017-01", "2026-07", PL, INI, "2026-07",
      "renault_kwid_800mil_autoindustria",
      "A Renault anuncia o marco de 800 mil Kwid produzidos no Complexo Ayrton Senna, em São "
      "José dos Pinhais (PR). [...] Lançado no mercado brasileiro em 2017")

# ---- Honda
HI = "honda_itirapina_inaugura_autoindustria"
linha("honda_sumare", ["HONDA|CIVIC|a", "HONDA|FIT|a", "HONDA|CITY|a", "HONDA|HR-V|a",
                       "HONDA|WR-V|a"], "1997-01", "2019-03", PL, INI, "2019-03", HI,
      "localizada a cerca de 100 quilômetros de Sumaré, onde desde 1997 produz seus carros aqui",
      "A frase cobre os carros da Honda feitos no Brasil ate' a data da pagina.")
linha("honda_itirapina", "HONDA|FIT|a", "2019-02", "2019-03", PL, INI, "2019-03", HI,
      "No dia 27 de fevereiro foi produzido o primeiro Fit em Itirapina.")

# ---- Nissan
linha("nissan_resende", "NISSAN|MARCH|a", "2020-08", "2020-08", PL, PTO, "2020-08",
      "nissan_march_fim_autoindustria",
      "A Nissan confirma o fim da produção do compacto March no complexo industrial da "
      "fabricante em Resende")


# ---- Fiat (lote 3)
linha("", "FIAT|PALIO|a", "1996-04", "2017-11", PL, DEC, "2026-09", "fiat_palio_divisor_autopapo",
      "O Fiat Palio permaneceu em produção de abril de 1996 até novembro de 2017.",
      "Pais sem fabrica nesta frase; a fabrica vem da pagina 'palio-2010'.")
linha("fiat_betim", "FIAT|PALIO|a", "1996-04", "2017-11", PL, DEC, "2024-09",
      "fiat_palio_2010_autopapo",
      "o hatch deu as caras no Brasil em 1996. Produzido em Betim (MG) sobre a plataforma do "
      "Uno europeu",
      "Periodo de producao (abril de 1996 a novembro de 2017) dado pela pagina 'divisor de "
      "aguas'; esta da' a fabrica.")
linha("", ["FIAT|PALIO WEEKEND|a", "FIAT|WEEKEND|a"], "1997-01", "2020-12", PL, DEC, "2026-09",
      "fiat_palio_divisor_autopapo",
      "já no ano seguinte, em 1997, chegou o restante da família: a perua Palio Weekend, o sedã "
      "Siena e a picape Strada. [...] Palio Weekend ficou em linha até 2020")
linha("fiat_betim", ["FIAT|STRADA|c", "FIAT|ARGO|a", "FIAT|MOBI|a", "FIAT|PULSE|a",
                     "FIAT|FASTBACK|a", "FIAT|FIORINO|c", "PEUGEOT|PARTNER|c"],
      "2023-07", "2023-07", PL, PTO, "2023-07", "fiat_betim_17milhoes_autoindustria",
      "Lá são produzidos os modelos Fiat Strada, Argo, Mobi, Pulse e Fastback, além dos "
      "comerciais leves Fiat Fiorino e Peugeot Partner Rapid.")
linha("fiat_betim", "FIAT|PULSE|a", "2021-07", "2023-07", PL, INI, "2023-07",
      "fiat_pulse_betim_revistacarro",
      "A Fiat deu início à produção de unidades pré-série do SUV Pulse. O modelo começou a deixar "
      "a linha de montagem em Betim (MG)", "Fim na data da pagina de 2023 (Betim, 17 milhoes).")
linha("fiat_betim", ["FIAT|ARGO|a", "FIAT|MOBI|a", "FIAT|STRADA|c", "FIAT|UNO|a",
                     "FIAT|UNO|c", "FIAT|FIORINO|c", "FIAT|DOBLO|a", "FIAT|DOBLO|c",
                     "FIAT|SIENA|a"], "2021-07", "2021-07", PL, PTO, "2021-07",
      "fiat_pulse_betim_revistacarro",
      "Além do Pulse, o Polo Automotivo de Betim é responsável pela produção dos modelos Argo, "
      "Mobi, Strada, Uno, Fiorino, Doblò e Grand Siena.", "Grand Siena e' a chave SIENA.")

# ---- Renault (lote 3)
linha("renault_sjp", "RENAULT|LOGAN|a", "2007-01", "2024-10", PL, DUR, "2024-10",
      "renault_logan_fim_autopapo",
      "A produção do Renault Logan em São José dos Pinhais (PR) foi encerrada após 17 anos. "
      "[...] O Renault Logan foi lançado no Brasil em 2007")
linha("renault_sjp", "RENAULT|SANDERO|a", "2007-10", "2025-01", PL, DEC, "2025-01",
      "renault_sandero_fim_autoindustria",
      "nada mais natural do que o encerramento da produção em São José dos Pinhais, PR [...] "
      "Projeto original da romena Dacia, o Sandero começou a ser fabricado no Brasil no fim de "
      "2007.", "'fim de 2007' lido como o ultimo trimestre.")
linha("renault_sjp", ["RENAULT|KWID|a", "RENAULT|KARDIAN|a"], "2025-01", "2025-01", PL, PTO,
      "2025-01", "renault_sandero_fim_autoindustria",
      "a mesma do SUV Kardian lançado no ano passado e, ao lado do Kwid, já o produto de grande "
      "volume da fábrica de São José dos Pinhais.")
linha("renault_sjp", ["RENAULT|CAPTUR|a", "RENAULT|DUSTER|a", "RENAULT|KWID|a",
                      "RENAULT|LOGAN|a", "RENAULT|SANDERO|a"], "2022-04", "2022-04", PL, PTO,
      "2022-04", "renault_cmfb_autodata_37718",
      "a fábrica de carros de passeio em São José dos Pinhais, de onde saem Captur, Duster, "
      "Kwid, Logan e Sandero")
linha("renault_sjp", "RENAULT|OROCH|c", "2022-04", "2022-04", PL, PTO, "2022-04",
      "renault_cmfb_autodata_37718",
      "A Oroch, recente lançamento, seguiu em produção no período – suas linhas foram "
      "transferidas, ainda antes da pandemia, para a unidade de veículos comerciais.")

# ---- Hyundai (lote 3)
linha("hyundai_piracicaba", "HYUNDAI|HB20|a", "2012-09", "2018-09", PL, DUR, "2018-09",
      "hyundai_hb20_6anos_motorshow",
      "Nesta quinta-feira (20), a Hyundai celebra os seis anos da produção do primeiro HB20 na "
      "fábrica de Piracicaba (SP).")
linha("hyundai_piracicaba", ["HYUNDAI|HB20|a", "HYUNDAI|HB20S|a", "HYUNDAI|CRETA|a"],
      "2018-09", "2018-09", PL, PTO, "2018-09", "hyundai_hb20_6anos_motorshow",
      "Além dos carros da família HB20, a fábrica do interior paulista produz também o SUV "
      "compacto Creta.")
linha("hyundai_piracicaba", ["HYUNDAI|HB20|a", "HYUNDAI|CRETA|a", "HYUNDAI|I20|a"], "2026-06",
      "2026-06", PL, PTO, "2026-06", "hyundai_i20_piracicaba_autoindustria",
      "não vai alterar, nos próximos meses de 2026, o ritmo de produção na fábrica da Hyundai em "
      "Piracicaba, SP, de forma significativa. [...] “Perto de 75 mil para o Creta e o restante "
      "entre HB20 e agora o I20”.")
linha("hyundai_piracicaba", "HYUNDAI|HB20S|a", "2013-01", "2026-06", PL, INI, "2026-06",
      "hyundai_i20_piracicaba_autoindustria",
      "HB20, é bom frisar, com a carroceria hatch, já que a configuração sedã, apresentada no "
      "primeiro semestre de 2013, deixou de ser fabricada exatamente para abrir espaço na linha de "
      "montagem do interior paulista para o I20.",
      "Do lancamento do sedan (1o semestre de 2013) ao fim, dado na pagina de junho de 2026.")

# ---- Citroen, Nissan, GM (lote 3)
linha("stellantis_porto_real", "CITROEN|C3|a", "2003-05", "2025-12", PL, INI, "2025-12",
      "citroen_c3_100mil_autodata_97976",
      "Desde maio de 2003 saíram do Polo Automotivo Stellantis de Porto Real, RJ, 100 mil "
      "unidades do hatch compacto Citroën C3.")
linha("nissan_resende", "NISSAN|KICKS|a", "2017-07", "2024-08", PL, INI, "2024-08",
      "nissan_kicks_350mil_autodata_76926",
      "A Nissan celebrou a marca de 350 mil SUV Kicks produzidos no Complexo Industrial de "
      "Resende, RJ. [...] Desde que começou a ser fabricado, em julho de 2017")
linha("gm_scs", "GM|COBALT|a", "2011-01", "2020-02", PL, DEC, "2020-03",
      "gm_cobalt_fim_autodata_30633",
      "O Chevrolet Cobalt saiu das linhas de montagem de São Caetano do Sul, SP, onde era "
      "produzido desde 2011.", "Fim no mes anterior ao da pagina (marco de 2020).")
linha("gm_scs", ["GM|TRACKER|a", "GM|ONIX|a", "GM|PRISMA|a"], "2020-05", "2020-05", PL, PTO,
      "2020-05", "gm_tracker_scs_revistacarro",
      "na unidade de São Caetano do Sul (SP), com a fabricação do novo Tracker. [...] é possível "
      "ver os modelos Joy e Joy Plus (ex-Onix Joy e Prisma Joy) sendo produzidos na mesma linha "
      "do Tracker")
linha("gm_scs", ["GM|TRACKER|a", "GM|SPIN|a", "GM|ONIX|a", "GM|PRISMA|a", "GM|MONTANA|c"],
      "2021-01", "2021-01", PL, PTO, "2021-01", "gm_96anos_autoindustria",
      "a do ABC paulista, que hoje produz o novo Tracker, Spin, Joy, Joy Plus e Montana.")

# ---- GM, HPE e Fiat de 2003 a 2012 (lote 4)
CORSA = ("A General Motors do Brasil comemora a marca histórica de 2.074.619 unidades produzidas "
         "do Chevrolet Corsa nos Complexos Industriais de São José dos Campos e São Caetano do "
         "Sul. [...] O Corsa, que completou no último mês de fevereiro 12 anos de produção "
         "ininterrupta")
for fab in ("gm_sjc", "gm_scs"):
    linha(fab, ["GM|CORSA|a", "GM|CORSA SEDAN|a"], "1994-02", "2006-09", PL, DUR, "2006-09",
          "gm_corsa_2milhoes_mecanicaonline", CORSA,
          "A pagina da' as duas fabricas para a familia Corsa, sem separar versao por fabrica.")
    linha(fab, "GM|CLASSIC|a", "1995-01", "2006-09", PL, INI, "2006-09",
          "gm_corsa_2milhoes_mecanicaonline",
          CORSA + " [...] Lançado no mercado em 1995, o Chevrolet Corsa sedã, primeira geração, foi "
          "reposicionado como Chevrolet Classic em 2002",
          "O Classic e' o Corsa seda' de primeira geracao, parte da familia contada na pagina.")
linha("hpe_catalao", ["MITSUBISHI|L200|c", "MITSUBISHI|ASX|a", "MITSUBISHI|LANCER|a",
                      "MITSUBISHI|PAJERO|a"], "2018-08", "2018-08", PL, PTO, "2018-08",
      "hpe_catalao_20anos_motorshow",
      "Além da picape L200 Triton Sport, são produzidos atualmente na fábrica goiana os modelos "
      "ASX, Lancer e Pajero HPE.")
linha("hpe_catalao", "MITSUBISHI|L200|c", "1998-01", "2020-12", PL, DUR, "2020-12",
      "mitsubishi_l200_42anos_motorshow",
      "A partir de 1998, a HPE Automotores inaugurou sua fábrica em Catalão (GO) para a produção "
      "da L200 [...] Nos 22 anos de história, mais de 300 mil unidades da picape L200 foram "
      "produzidas em Catalão.", "22 anos contados de 1998.")
linha("gm_scs", "GM|MERIVA|a", "2002-01", "2012-12", PL, DEC, "2024-10", "gm_meriva_2012_autopapo",
      "Em questão de meses começou a ser produzida em São Caetano do Sul (SP) e vendida como "
      "Chevrolet Meriva por aqui. [...] Hoje, a Chevrolet Meriva, que foi vendida de 2002 a 2012")
linha("", "GM|ZAFIRA|a", "2001-04", "2012-12", PL, DEC, "2025-01", "gm_zafira_autopapo",
      "o carro foi apresentado no Brasil em abril de 2001 [...] o conjunto 8V foi recalibrado em "
      "2011, quando teve a potência elevada. Mas durou pouco tempo. No ano seguinte a Chevrolet "
      "Zafira deixou de ser produzida. Ao todo, 100 mil unidades foram feitas em 11 anos. [...] "
      "Além da minivan, a montadora produziu localmente")
FB = "fiat_bravo_linea_idea_revistacarro"
SUSP = "Quanto à suspensão dos três modelos em Betim"
linha("fiat_betim", "FIAT|IDEA|a", "2005-01", "2016-07", PL, INI, "2016-07", FB,
      f"Apresentado em 2005, defendeu a marca italiana contra o aguerrido Chevrolet Meriva [...] "
      f"{SUSP}", "Do lancamento a' suspensao da producao em Betim (julho de 2016).")
linha("fiat_betim", "FIAT|LINEA|a", "2008-01", "2016-07", PL, INI, "2016-07", FB,
      f"Essa estratégia havia começado em 2008, quando a marca apresentou o sedã médio (na "
      f"verdade, compacto-médio) Linea [...] {SUSP}",
      "Do lancamento a' suspensao da producao em Betim (julho de 2016).")
linha("fiat_betim", "FIAT|BRAVO|a", "2010-10", "2016-07", PL, INI, "2016-07", FB,
      f"O Bravo foi lançado no final de 2010 como competidor de Focus e Volkswagen Golf [...] "
      f"{SUSP}", "'final de 2010' lido como o ultimo trimestre.")
linha("fiat_betim", ["FIAT|DOBLO|a", "FIAT|DOBLO|c", "FIAT|PUNTO|a"], "2016-07", "2016-07", PL,
      PTO, "2016-07", FB,
      "É o caso do Doblò e do Punto, que mantêm produção normal nas outras linhas.")
linha("fiat_betim", ["FIAT|ARGO|a", "FIAT|SIENA|a", "FIAT|MOBI|a", "FIAT|FIORINO|c",
                     "FIAT|STRADA|c", "FIAT|UNO|a", "FIAT|UNO|c"], "2017-12", "2017-12", PL, PTO,
      "2017-12", "fiat_doblo_weekend_autopapo",
      "a fábrica da Fiat em Betim passa a produzir apenas seis modelos: Argo, Grand Siena, Mobi, "
      "Fiorino, Strada e Uno.")

# ---- anos recentes (lote 5)
linha("gm_scs", "GM|TRACKER|a", "2020-01", "2022-12", PL, INI, "2022-12",
      "gm_tracker_250mil_motorshow",
      "O Chevrolet Tracker alcançou a marca de 250 mil unidades produzidas na fábrica da GM em São "
      "Caetano do Sul (SP). [...] O Tracker está em sua terceira geração, na qual estreou em 2020")
linha("honda_itirapina", ["HONDA|CITY|a", "HONDA|CITY HATCH|a", "HONDA|WR-V|a", "HONDA|HR-V|a"],
      "2025-10", "2025-10", PL, PTO, "2025-10", "honda_itirapina_2turnos_autodata_95373",
      "Em Itirapina são produzidos os veículos City, nas carrocerias sedã e hatch, WR-V e HR-V.")
linha("honda_itirapina", ["HONDA|CITY|a", "HONDA|CITY HATCH|a", "HONDA|WR-V|a", "HONDA|HR-V|a"],
      "2026-01", "2026-01", PL, PTO, "2026-01", "honda_25milhoes_autoindustria",
      "Itirapina produz atualmente os modelos WR-V, HR-V, City Hatchback e City Sedan.")
linha("fiat_betim", "FIAT|STRADA|c", "1998-01", "2026-06", PL, INI, "2026-07",
      "fiat_strada_recorde_autodata_129940",
      "A Stellantis alcançou um novo recorde de produção da picape Fiat Strada no Polo Automotivo "
      "de Betim, MG. Em junho foram 19 mil 261 unidades, maior volume mensal registrado desde o "
      "seu lançamento, em 1998.",
      "O recorde mensal 'desde o lancamento, em 1998' compara a producao de Betim desde entao.")
linha("fiat_betim", ["FIAT|STRADA|c", "FIAT|ARGO|a", "FIAT|MOBI|a", "FIAT|PULSE|a",
                     "FIAT|FASTBACK|a", "FIAT|FIORINO|c", "PEUGEOT|PARTNER|c"],
      "2024-07", "2024-07", PL, PTO, "2024-08", "fiat_betim_recorde_revistacarro",
      "A Fiat Strada, que é fabricada por lá, teve mais de 15,7 mil unidades produzidas. A linha "
      "de montagem mineira também é responsável por fabricar Argo, Mobi, Fiat Pulse e Fastback, "
      "além dos comerciais leves Fiat Fiorino e Peugeot Partner Rapid.",
      "Producao de julho de 2024.")
linha("gm_sjc", ["GM|S10|c", "GM|TRAILBLAZER|a"], "2026-07", "2026-07", PL, PTO, "2026-07",
      "gm_s10_trailboss_autodata_130660",
      "a picape S10 e o SUV Trailblazer, ambos fabricados em São José dos Campos, SP.")
linha("gm_sjc", "GM|S10|c", "1995-01", "2025-12", PL, DEC, "2025-12", "gm_s10_30anos_revistacarro",
      "A Chevrolet S10 completa 30 anos de produção contínua no Brasil em 2025 [...] Produzida "
      "desde o início no complexo industrial da General Motors em São José dos Campos (SP)",
      "30 anos contados para tras de 2025.")
BYD_MS = "byd_dolphin_mini_brasileiro_motorshow"
linha("byd_camacari", ["BYD|DOLPHIN MINI|a", "BYD|KING|a", "BYD|SONG|a"], "2025-10", "2025-10",
      PL, PTO, "2025-10", BYD_MS,
      "O Dolphin Mini, hatch pequeno, é o primeiro carro elétrico produzido no Brasil, na fábrica "
      "da BYD em Camaçari (BA). Na realidade, montado: as unidades vêm desmontadas (SKD) da China, "
      "e são finalizadas por aqui. De início, com índice de nacionalização bem baixo, quase nulo, "
      "assim como acontece com King e Song Pro, outros dois BYD montados por lá",
      "A chave SONG agrega Song Plus e Song Pro; a pagina trata do Song Pro.")
linha("", "BYD|DOLPHIN MINI|a", "2025-10", "2025-10", AB, PTO, "2025-10", BYD_MS,
      "o Dolphin Mini brasileiro não é muito diferente do chinês, que segue sendo importado "
      "enquanto o volume de produção de Camaçari é tímido.", pais="China")
linha("", ["BYD|DOLPHIN MINI|a", "BYD|SONG|a", "BYD|KING|a"], "2025-07", "2025-07", AB, PTO,
      "2025-07", "byd_skd_importacao_autoindustria",
      "Com a montagem local, ideia é deixar de trazer da China os modelos Dolphin Mini, Song Pro e "
      "King", "Em julho de 2025 os tres vinham da China.", pais="China")
linha("byd_camacari", ["BYD|DOLPHIN MINI|a", "BYD|KING|a", "BYD|SONG|a"], "2026-05", "2026-05",
      PL, PTO, "2026-05", "byd_lider_varejo_2026",
      "Mais de 50 mil unidades dos modelos BYD Dolphin Mini, o BYD King e o BYD Song Pro já "
      "deixaram a linha de produção em Camaçari",
      "Pagina da BYD posterior a abril de 2026 (lideranca no varejo em abril).")

# ---- Ford, Hyundai, GM (lote 6)
NFH = "ford_new_fiesta_hatch_autopapo"
linha("ford_camacari", "FORD|FIESTA|a", "2002-01", "2010-12", PL, DEC, "2016-04", NFH,
      "2002 – Lançamento da nova geração do Fiesta com conceito de design New Edge, produzida no "
      "Complexo Industrial Ford Nordeste, na Bahia. [...] 2010 – 1 milhão de unidades da Linha "
      "Fiesta (Hatch e Sedan) produzidas na Bahia.",
      "Do lancamento da geracao feita na Bahia ao marco de 2010.")
linha("ford_camacari", "FORD|FIESTA SEDAN|a", "2004-01", "2010-12", PL, DEC, "2016-04", NFH,
      "2004 – Início de produção do Novo Fiesta Sedan com motor RoCam 1.6 Flex, o primeiro "
      "bicombustível da marca. [...] 2010 – 1 milhão de unidades da Linha Fiesta (Hatch e Sedan) "
      "produzidas na Bahia.")
linha("ford_sbc", "FORD|FIESTA|a", "2013-01", "2016-04", PL, INI, "2016-04", NFH,
      "2013 – Início da produção do New Fiesta Hatch em São Bernardo do Campo",
      "O New Fiesta hatch nacional e' lido na chave FIESTA (a NEW FIESTA e' o importado do "
      "Mexico); ver QUESTOES_ABERTAS.")
linha("ford_camacari", "FORD|KA|a", "2001-01", "2014-12", PL, DEC, "2025-09",
      "ford_ka_tres_decadas_autopapo",
      "2001 – Início da produção em Camaçari (BA); chegada do motor Zetec Rocam. [...] A segunda "
      "geração do Ford Ka tupiniquim seguiu no mercado até 2014.")
H2 = "hyundai_2milhoes_autoindustria"
linha("hyundai_piracicaba", ["HYUNDAI|HB20|a", "HYUNDAI|HB20S|a"], "2012-10", "2023-10", PL, DUR,
      "2023-10", H2,
      "Fábrica de Piracicaba ultrapassou 2 milhões de unidades montadas em 11 anos [...] Já a "
      "marca de 1 milhão de unidades foi registrada em 2018, apenas 5 anos e 10 meses depois da "
      "inauguração da planta paulista e do primeiro HB20 produzido. [...] Considerando as "
      "configurações de carroceria hatch e sedã, já são mais de 1,6 milhão de unidades fabricadas.",
      "11 anos contados para tras de outubro de 2023.")
linha("hyundai_piracicaba", "HYUNDAI|CRETA|a", "2017-01", "2023-10", PL, INI, "2023-10", H2,
      "Fábrica de Piracicaba ultrapassou 2 milhões de unidades montadas em 11 anos [...] Lançado "
      "em 2017, o Creta responde pelos 400 mil veículos restantes.")
linha("gm_sjc", "GM|CLASSIC|a", "2012-11", "2013-02", PL, DEC, "2012-11", "gm_classic_sjc_exame",
      "irá deixar de produzir o Classic na unidade em fevereiro de 2013 [...] o restante continua "
      "na produção do Classic até fevereiro.", "Fonte fraca (imprensa geral).")

# ---- paginas de origem_paginas (rodadas anteriores), relidas como fabrica x modelo
linha("byd_camacari", "BYD|DOLPHIN MINI|a", "2025-10", "2025-11", PL, INI, "2025-11",
      "byd_camacari_autodata_96403",
      "A BYD montou 363 Dolphin Mini no primeiro mês de operação da fábrica de Camaçari, BA, "
      "inaugurada em outubro.")
GWM1 = ("Depois do início da produção, em setembro de 2025, a unidade incorporou novos processos "
        "industriais [...] Desde a inauguração, a planta produz toda a linha híbrida Haval H6 Flex "
        "(nas versões HEV, PHEV19, PHEV35 e GT), a picape média Poer P30 e o SUV de 7 lugares Haval "
        "H9, ambos a diesel.")
linha("gwm_iracemapolis", ["GWM|HAVAL H6|a", "GWM|HAVAL H9|a", "GWM|POER|c"], "2025-09",
      "2026-08", PL, INI, "2026-08", "gwm_iracemapolis_um_ano", GWM1)
linha("bmw_araquari", "BMW|X1|a", "2023-04", "2023-08", PL, INI, "2023-08",
      "bmw_araquari_autodata_59749",
      "A fábrica foi inaugurada em 2014 e o modelo de número 90 mil produzido foi um X1 sDrive20i "
      "M Sport, que teve sua nova geração nacionalizada e é produzida aqui desde abril.")
linha("bmw_araquari", "BMW|X3|a", "2018-03", "2018-03", PL, INI, "2018-03",
      "bmw_x3_press_araquari_2018",
      "O novo BMW X3 começa [...] a ser produzido hoje (26) na fábrica do BMW Group em Araquari, "
      "Santa")
linha("jlr_itatiaia", ["LAND ROVER|EVOQUE|a", "LAND ROVER|DISCOVERY|a"], "2016-06", "2016-06", PL,
      PTO, "2016-06", "jlr_itatiaia_media_jlr",
      "The new facility will build both the Range Rover Evoque and Land Rover Discovery Sport "
      "for Brazilian customers. Vehicles will be on sale in dealers across Brazil this month.",
      "A chave DISCOVERY agrega o Discovery Sport (Itatiaia) e o Discovery importado.")
linha("audi_sjp", "AUDI|Q3|a", "2016-03", "2016-03", PL, INI, "2016-03", "audi_sjp_motorshow_q3",
      "A fábrica de São José dos Pinhais (PR) iniciou oficialmente nesta sexta-feira (11) a "
      "produção local do Q3")
linha("stellantis_goiana", "JEEP|COMPASS|a", "2016-09", "2025-07", PL, INI, "2025-07",
      "jeep_compass_goiana_autodata_91613",
      "Lançado em setembro de 2016 o Jeep Compass, fabricado em Goiana, PE, superou a marca de "
      "500 mil unidades vendidas no mercado brasileiro.")
linha("hpe_catalao", "MITSUBISHI|ASX|a", "2013-01", "2021-10", PL, DEC, "2021-11",
      "mitsubishi_asx_revistacarro_fim",
      "A produção nacional teve início em 2013 [...] O utilitário esportivo deixou de ser "
      "produzido em Catalão (GO)", "Fim no mes anterior ao da pagina (novembro de 2021).")
linha("hpe_catalao", "SUZUKI|JIMNY|a", "2013-01", "2022-08", PL, DEC, "2022-08",
      "suzuki_jimny_motorshow_fim",
      "Vale lembrar que o utilitário é fabricado no País desde 2013. [...] A HPE Automotores, "
      "representante oficial da Suzuki no Brasil, encerrou a produção do Jimny na fábrica de "
      "Catalão (GO).")
linha("gm_scs", ["GM|CRUZE SEDAN|a", "GM|CRUZE HB|a"], "2016-05", "2016-05", PL, PTO, "2016-05",
      "gm_cruze_motorshow_novo_2016",
      "O sedã deixa de ser produzido em São Caetano do Sul (SP) e passa a ser importado da "
      "Argentina.", "Em maio de 2016 o seda' ainda saia de Sao Caetano; o hatch nao e' citado.")
linha("nissan_resende", ["NISSAN|KICKS|a", "NISSAN|MARCH|a", "NISSAN|VERSA|a"], "2017-04",
      "2017-04", PL, PTO, "2017-04", "nissan_kicks_motorshow_inicio",
      "o Nissan Kicks começa a ser produzido na fábrica da marca japonesa em Resende (RJ), que "
      "também produz os compactos March e Versa.")
linha("nissan_resende", ["NISSAN|VERSA|a", "NISSAN|MARCH|a"], "2015-03", "2015-03", PL, PTO,
      "2015-03", "nissan_versa_motorshow_2015",
      "Produzido junto do hatch New March na planta industrial de Resende (RJ)")
linha("toyota_sorocaba", "TOYOTA|YARIS CROSS|a", "2026-01", "2026-01", PL, INI, "2026-01",
      "toyota_yaris_cross_autodata_99142",
      "a Toyota iniciou a produção do SUV compacto Yaris Cross em Sorocaba, SP.")
linha("hpe_catalao", "MITSUBISHI|TRITON|c", "2025-01", "2025-01", PL, PTO, "2025-01",
      "mitsubishi_triton_autodata_82909", "A Triton, produzida em Catalão, GO, foi o modelo mais "
      "vendido")
linha("", "MITSUBISHI|ECLIPSE CROSS|a", "2025-01", "2025-01", PL, PTO, "2025-01",
      "mitsubishi_triton_autodata_82909",
      "O Eclipse Cross, também nacional, somou 8,3 mil vendas")
linha("", "MITSUBISHI|PAJERO|a", "2025-01", "2025-01", AB, PTO, "2025-01",
      "mitsubishi_triton_autodata_82909",
      "o Pajero Sport, importado da Tailândia, registrou 2,9 mil unidades comercializadas.",
      "A chave agrega os Pajero; a fonte trata do Pajero Sport.", pais="Tailândia")
linha("ar_vw", "VW|SPACE FOX|a", "2006-01", "2018-12", AB, DEC, "2019-01",
      "vw_spacefox_autopapo_fim",
      "a VW SpaceFox já não está sendo mais produzida na Argentina, de onde era exportada para "
      "nosso mercado. [...] A SpaceFox foi lançada em 2006 e produzida na Argentina desde então.")
linha("caoa_anapolis", ["CAOA CHERY|TIGGO 5X|a", "CAOA CHERY|TIGGO 7|a", "CAOA CHERY|TIGGO 8|a"],
      "2025-01", "2025-07", PL, DEC, "2025-08", "caoa_anapolis_autodata_200mil",
      "Em 2025 os modelos Caoa Chery produzidos em Anápolis, os SUVs Tiggo 5, Tiggo 7 e Tiggo 8, "
      "somaram 35 mil emplacamentos até julho",
      "Tiggo 5 e' a chave TIGGO 5X.")
linha("iveco_sete_lagoas", ["IVECO|DAILY|c", "IVECO|DAILY 30-130|c", "IVECO|DAILY 30S13|c",
                            "IVECO|DAILY 35-150|c", "IVECO|DAILY 3514|c", "IVECO|DAILY 35S14|c"],
      "2026-08", "2026-08", PL, PTO, "2026-08", "iveco_daily_autodata_sete_lagoas",
      "o reflexo desta maior procura pelos veículos da família Daily resultou na contratação de "
      "duzentos trabalhadores na fábrica de Sete Lagoas, MG")
linha("renault_sjp", "NISSAN|LIVINA|a", "2009-01", "2009-01", PL, INI, "2009-01",
      "nissan_livina_release_2009",
      "The Nissan Livina is the first passenger vehicle to be produced through the Renault-Nissan "
      "Alliance Plant in São José dos Pinhais.")
linha("stellantis_porto_real", "PEUGEOT|2008|a", "2024-04", "2024-04", PL, PTO, "2024-04",
      "peugeot_2008_autodata_71222",
      "A geração anterior deixará de ser produzida em Porto Real, RJ",
      "Em abril de 2024 a geracao anterior ainda saia de Porto Real; conflita com a data de fim "
      "de outra fonte (novembro de 2023).")
linha("caoa_anapolis", "HYUNDAI|IX35|a", "2013-01", "2017-09", PL, INI, "2017-09",
      "hyundai_autodata_25343",
      "A CAOA anunciou na quinta-feira, 28, que já foram produzidos no País 51 mil unidades do "
      "modelo Hyundai iX35, veículo fabricado pela empresa em Anápolis, GO, desde 2013.")
linha("gm_scs", "GM|TRACKER|a", "2020-03", "2020-03", PL, PTO, "2020-03",
      "gm_tracker_autoindustria_2020",
      "Com a nova geração produzida em São Caetano, objetivo é estar entre os SUVs líderes")
linha("mb_iracemapolis", ["M.BENZ|CLASSE GLA|a", "M.BENZ|CLASSE C|a"], "2016-09", "2016-09", PL,
      PTO, "2016-09", "mb_gla_automotiveworld",
      "Mercedes-Benz has started the production of a second model at its new passenger-car plant "
      "in Iracemápolis. The compact SUV GLA will be flexibly assembled on the same line as the "
      "C-Class Sedan.")
linha("honda_sumare", "HONDA|CIVIC|a", "2021-10", "2021-10", PL, PTO, "2021-10",
      "honda_civic_marklines_260331",
      "Honda's Brazilian factory in Sumare will end production of the Civic in November")
linha("gm_horizonte", "GM|SPARK|a", "2025-12", "2025-12", PL, INI, "2025-12",
      "gm_spark_autopapo_pace",
      "Ela fica localizada em Horizonte (CE), onde era a unidade fabril da Troller. [...] O "
      "primeiro produto feito lá é o Chevrolet Spark EUV.")
linha("caoa_anapolis", "HYUNDAI|TUCSON|a", "2010-01", "2019-12", PL, DEC, "2024-03",
      "hyundai_tucson_caoa_ultimo",
      "entre modelos importados (2004 a 2010) e produzidos em Anápolis-GO (entre os anos de 2010 "
      "e 2019)", "Os importados nao tem pais na pagina.")
linha("hpe_catalao", "MITSUBISHI|LANCER|a", "2014-01", "2019-12", PL, DEC, "2020-01",
      "mitsubishi_lancer_autopapo_fim",
      "ele passou a ser produzido, em 2014, na fábrica da Mitsubishi em Catalão (GO). [...] o "
      "Brasil foi o último país a produzi-lo, até o final do ano passado.")
linha("", "MITSUBISHI|OUTLANDER|a", "2014-01", "2022-12", PL, DEC, "2025-06",
      "mitsubishi_outlander_autoindustria_2025",
      "O SUV foi fabricado aqui com motorização híbrida já entre os distantes anos de 2014 a 2016 "
      "[...] A geração anterior saiu de linha em 2022")
linha("ar_renault", ["RENAULT|KANGOO|a", "RENAULT|KANGOO|c"], "1998-01", "2018-05", AB, INI,
      "2018-05", "renault_kangoo_parabrisas_historia",
      "En 1998 dejó de importarse desde Francia para lanzarse el Kangoo producido en la planta "
      "Santa Isabel, ubicada en la provincia de Córdoba. [...] Además de comercializarse en el "
      "mercado interno, fue exportado a Brasil,")
linha("ar_renault", ["RENAULT|KANGOO|a", "RENAULT|KANGOO|c"], "2024-05", "2024-05", AB, INI,
      "2024-05", "renault_kangoo_autodata_71784",
      "A Renault iniciou a exportação do Kangoo, produzido na fábrica de Santa Isabel, em "
      "Córdoba, Argentina, para o Brasil.")
linha("mb_juiz_de_fora", "M.BENZ|CLASSE A|a", "1999-02", "2005-08", PL, DEC, "2025-06",
      "mb_classea_motorshow_fracasso",
      "em fevereiro de 1999, a Mercedes-Benz passou a produzir integralmente o novo Classe A em "
      "uma fábrica especialmente concebida para isso, na cidade de Juiz de Fora (MG). [...] Em "
      "agosto de 2005, a produção do Classe A geração W168 foi descontinuada no Brasil.")
linha("", "M.BENZ|CLASSE A|a", "2025-06", "2025-06", AB, PTO, "2025-06",
      "mb_classea_motorshow_fracasso", "Hoje o Classe A é hatch médio, importado da Alemanha,",
      pais="Alemanha")


# ===================================================================== ADEFA

ADEFA_COLUNAS = {
    "adefa_anuario2006_produccion_por_modelo": ["1959/2001", "2002", "2003", "2004", "2005",
                                                 "2006", "total"],
    "adefa_anuario2013_produccion_por_modelo": [str(a) for a in range(2008, 2014)] + ["total"],
    "adefa_anuario2017_produccion_por_modelo": [str(a) for a in range(2010, 2018)] + ["total"],
    "adefa_anuario2025_produccion_por_modelo": [str(a) for a in range(2018, 2026)] + ["total"],
}
# (regex sobre o nome da linha de versao, chaves do painel, fabrica)
ADEFA = [
    (r"^(Hilux (-|cabina)|HILUX (-|NUEVA|CABINA)|NEW HILUX|HILUX)\b(?!.*SW)", ["TOYOTA|HILUX|c"],
     "ar_toyota"),
    (r"^(Hilux SW4|HILUX SW4|SW ?4)\b", ["TOYOTA|HILUX SW4|a"], "ar_toyota"),
    (r"^(FORD RANGER|NEW RANGER|RANGER)\b", ["FORD|RANGER|c"], "ar_ford"),
    (r"^(FORD FOCUS|FOCUS 2|NUEVO FOCUS|FOCUS)\b", ["FORD|FOCUS|a", "FORD|FOCUS SEDAN|a"],
     "ar_ford"),
    (r"^AMAROK\b", ["VW|AMAROK|c"], "ar_vw"),
    (r"^(VW SURAN|SURAN)\b", ["VW|SPACE FOX|a", "VW|SPACECROSS|a"], "ar_vw"),
    (r"^TAOS\b", ["VW|TAOS|a"], "ar_vw"),
    (r"^CRONOS\b", ["FIAT|CRONOS|a"], "ar_fiat"),
    (r"^(SIENA NAFTA|Siena (Nafta|Diesel))\b", ["FIAT|SIENA|a"], "ar_fiat"),
    (r"^(PALIO ELX|PALIO 5P\.|Palio 5p\.)", ["FIAT|PALIO|a"], "ar_fiat"),
    (r"^TITANO\b", ["FIAT|TITANO|c"], "ar_fiat"),
    (r"^DAKOTA\b", ["RAM|DAKOTA|c"], "ar_fiat"),
    (r"^AGILE\b", ["GM|AGILE|a"], "ar_gm"),
    (r"^(CHEVROLET CLASSIC|CLASSIC (4DR|LS|LT|ADVANTAGE)|CORSA CLASSIC)\b", ["GM|CLASSIC|a"],
     "ar_gm"),
    (r"^CRUZE 4P\b", ["GM|CRUZE SEDAN|a"], "ar_gm"),
    (r"^CRUZE 5P\b", ["GM|CRUZE HB|a"], "ar_gm"),
    (r"^CRUZE$", ["GM|CRUZE SEDAN|a", "GM|CRUZE HB|a"], "ar_gm"),
    (r"^TRACKER\b", ["GM|TRACKER|a"], "ar_gm"),
    (r"^Chevrolet Grand Vitara\b(?!.*PICK)", ["GM|TRACKER|a"], "ar_gm"),
    (r"^207 COMPACT\b", ["PEUGEOT|207 SEDAN|a"], "ar_psa"),
    (r"^(307 -|PEUGEOT 307)\b", ["PEUGEOT|307|a", "PEUGEOT|307 SEDAN|a"], "ar_psa"),
    (r"^308\b", ["PEUGEOT|308|a"], "ar_psa"),
    (r"^408\b", ["PEUGEOT|408|a"], "ar_psa"),
    (r"^2008\b", ["PEUGEOT|2008|a"], "ar_psa"),
    (r"^208\b", ["PEUGEOT|208|a"], "ar_psa"),
    (r"^C4 BICUERPO\b", ["CITROEN|C4|a"], "ar_psa"),
    (r"^C4 - ", ["CITROEN|C4 PALLAS|a"], "ar_psa"),
    (r"^C4 LOUNGE\b", ["CITROEN|C4L|a"], "ar_psa"),
    (r"^(PARTNER (-|FURGON|PATAGONICA)|PEUGEOT PARTNER|PARTNER)\b", ["PEUGEOT|PARTNER|c"],
     "ar_psa"),
    (r"^(RENAULT CLIO|NUEVO CLIO)\b", ["RENAULT|CLIO|a"], "ar_renault"),
    (r"^SYMBOL\b", ["RENAULT|SYMBOL|a"], "ar_renault"),
    (r"^FLUENCE\b", ["RENAULT|FLUENCE|a"], "ar_renault"),
    (r"^(RENAULT KANGOO|KANGOO)\b", ["RENAULT|KANGOO|a", "RENAULT|KANGOO|c"], "ar_renault"),
    (r"^(RENAULT MEGANE)\b", ["RENAULT|MEGANE|a"], "ar_renault"),
    (r"^(NUEVO SANDERO|SANDERO)\b", ["RENAULT|SANDERO|a"], "ar_renault"),
    (r"^(NUEVO LOGAN|LOGAN)\b", ["RENAULT|LOGAN|a"], "ar_renault"),
    (r"^FRONTIER\b", ["NISSAN|FRONTIER|c"], "ar_nissan"),
    (r"^(Sprinter -|SPRINTER)\b", ["M.BENZ|SPRINTER|c", "M.BENZ|SPRINTER 311|c",
                                   "M.BENZ|SPRINTER 313|c", "M.BENZ|SPRINTER 314|c",
                                   "M.BENZ|SPRINTER 315|c", "M.BENZ|SPRINTER 317|c",
                                   "M.BENZ|SPRINTER 413|c", "M.BENZ|SPRINTER 416|c"], "ar_mb"),
    (r"^CITY\b", ["HONDA|CITY|a"], "ar_honda"),
    (r"^HRV\b", ["HONDA|HR-V|a"], "ar_honda"),
    (r"^HIACE\b", ["TOYOTA|HIACE|c"], "ar_toyota"),
]
# linhas descartadas por defeito de extracao (a do Palio de 2025 repete os numeros do Cronos)
ADEFA_DESCARTE = {("adefa_anuario2025_produccion_por_modelo", "PALIO")}
NUM = r"(?:\d{1,3}(?:\.\d{3})*|-)"


def adefa() -> list[dict]:
    soma = defaultdict(Counter)
    trechos = defaultdict(list)
    for nome, colunas in ADEFA_COLUNAS.items():
        pagina = f"fabricas_paginas/{nome}"
        bruto = (config.FABRICAS_PAGINAS / f"{nome}.txt").read_text(encoding="utf-8")
        for l in bruto.split("\n"):
            m = re.match(r"^(.*?[A-Za-z].*?)\s+((?:" + NUM + r"\s+)+" + NUM + r")\s*$", l.strip())
            if not m:
                continue
            versao, valores = m.group(1).strip(), m.group(2).split()
            if len(valores) != len(colunas) or (nome, versao) in ADEFA_DESCARTE:
                continue
            for regex, chaves, fab in ADEFA:
                if re.search(regex, versao):
                    for ano, v in zip(colunas, valores):
                        if not re.fullmatch(r"\d{4}", ano) or v == "-" or v == "0":
                            continue
                        for k in chaves:
                            soma[(k, fab, ano)][pagina] += int(v.replace(".", ""))
                            trechos[(k, fab, ano, pagina)].append(" ".join(l.split()))
                    break
    linhas = []
    for (k, fab, ano), por_pagina in sorted(soma.items()):
        # o ano que aparece em dois anuarios fica com o mais recente (numero revisado)
        pagina = max(por_pagina)
        marca, modelo, segmento = chave(k)
        partes = list(dict.fromkeys(trechos[(k, fab, ano, pagina)]))
        linhas.append({"fabrica_id": fab, "pais": AR, "marca": marca, "modelo": modelo,
                       "segmento": segmento, "periodo_inicio": f"{ano}-01",
                       "periodo_fim": f"{ano}-12", "vinculo": "producao_no_exterior",
                       "regra_periodo": "ano_da_tabela", "data_fonte": f"{ano}-12",
                       "fonte_url": url_de(pagina),
                       "tipo_fonte": tipo_fonte.tipo_de(url_de(pagina), MAPA),
                       "fonte_trecho": origem_pais.SEPARADOR.join(partes), "pagina_salva": pagina,
                       "observacao": f"ADEFA, producao na Argentina em {ano}: "
                                     f"{por_pagina[pagina]} unidades (soma das versoes)."})
    return linhas


# ===================================================================== INEGI

INEGI_PAGINA = "fabricas_paginas/inegi_raiavl10_exportacao_brasil"
# (regex sobre "Empresa - Modelo", chaves do painel, fabrica)
INEGI = [
    (r"^Audi - Q5$", ["AUDI|Q5|a"], "mx_audi"),
    (r"^BMW Group - M2$", ["BMW|M2|a"], "mx_bmw"),
    (r"^Chrysler - Journey$", ["DODGE|JOURNEY|a"], "mx_chrysler"),
    (r"^Chrysler - RAM 2500-$", ["RAM|2500|c", "DODGE|RAM|c"], "mx_chrysler"),
    (r"^Fiat - Fiat 500-$", ["FIAT|500|a"], "mx_chrysler"),
    (r"^Ford Motor - Bronco Sport$", ["FORD|BRONCO|a"], "mx_ford"),
    (r"^Ford Motor - Fiesta NA Sedan$", ["FORD|NEW FIESTA|a"], "mx_ford"),
    (r"^Ford Motor - Fusion( Hibrido)?$", ["FORD|FUSION|a"], "mx_ford"),
    (r"^Ford Motor - Maverick$", ["FORD|MAVERICK|c"], "mx_ford"),
    (r"^General Motors - Captiva Sport$", ["GM|CAPTIVA|a"], "mx_gm"),
    (r"^General Motors - Equinox (SUV-|EV)$", ["GM|EQUINOX|a"], "mx_gm"),
    (r"^General Motors - Silverado 2500 Doble Cabina-$", ["GM|SILVERADO|c"], "mx_gm"),
    (r"^General Motors - Sonic-$", ["GM|SONIC|a", "GM|SONIC SEDAN|a"], "mx_gm"),
    (r"^General Motors - Trax$", ["GM|TRACKER|a"], "mx_gm"),
    (r"^Honda - Accord-$", ["HONDA|ACCORD|a"], "mx_honda"),
    (r"^Honda - CR-V-$", ["HONDA|CRV|a"], "mx_honda"),
    (r"^KIA - Forte-$", ["KIA|CERATO|a"], "mx_kia"),
    (r"^Mercedes Benz_Prod_Expo - Clase A Sedán_$", ["M.BENZ|CLASSE A|a"], "mx_mb"),
    (r"^Mercedes Benz_Prod_Expo - GLB_$", ["M.BENZ|CLASSE GLB|a"], "mx_mb"),
    (r"^Nissan - Kicks$", ["NISSAN|KICKS|a"], "mx_nissan"),
    (r"^Nissan - March$", ["NISSAN|MARCH|a"], "mx_nissan"),
    (r"^Nissan - (NP300|Pickup Largo)$", ["NISSAN|FRONTIER|c"], "mx_nissan"),
    (r"^Nissan - Sentra( 4 PTS)?$", ["NISSAN|SENTRA|a"], "mx_nissan"),
    (r"^Nissan - Tiida 5 PTS$", ["NISSAN|TIIDA|a"], "mx_nissan"),
    (r"^Nissan - Tiida Sedan$", ["NISSAN|TIIDA SEDAN|a"], "mx_nissan"),
    (r"^Nissan - Versa$", ["NISSAN|VERSA|a"], "mx_nissan"),
    (r"^Volkswagen - Beetle$", ["VW|BEETLE|a"], "mx_vw"),
    (r"^Volkswagen - Bora$", ["VW|BORA|a"], "mx_vw"),
    (r"^Volkswagen - Golf-$", ["VW|GOLF|a"], "mx_vw"),
    (r"^Volkswagen - Golf Variant-/Crossgolf$", ["VW|GOLF VARIANT|a"], "mx_vw"),
    (r"^Volkswagen - (Jetta|Jetta 4 PTAS|Nuevo Jetta)$", ["VW|JETTA|a"], "mx_vw"),
    (r"^Volkswagen - Sportwagen$", ["VW|JETTA VARIANT|a"], "mx_vw"),
    (r"^Volkswagen - Taos$", ["VW|TAOS|a"], "mx_vw"),
    (r"^Volkswagen - Tiguan-$", ["VW|TIGUAN|a"], "mx_vw"),
]
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
            "Septiembre", "Octubre", "Noviembre", "Diciembre"]


# um bloco de meses seguidos com exportacao vale do primeiro mes ao ultimo mais dois
# (transporte e estoque); intervalo de ate' dois meses sem exportacao nao separa blocos;
# bloco com menos de 100 unidades (amostra, frota de teste) nao conta
INEGI_DEFASAGEM = 2
INEGI_MINIMO = 100


def _mais(mes: str, n: int) -> str:
    return (pd.Period(mes, "M") + n).strftime("%Y-%m")


def inegi() -> list[dict]:
    bruto = (config.FABRICAS_PAGINAS / "inegi_raiavl10_exportacao_brasil.txt").read_text(
        encoding="utf-8")
    csv_texto = bruto[bruto.index('"Año"'):]
    linhas_csv = csv_texto.split("\n")
    dados = pd.read_csv(io.StringIO(csv_texto), dtype=str, keep_default_na=False)
    dados.columns = ["ano", "mes", "item", "valor"]
    dados["linha"] = linhas_csv[1:len(dados) + 1]
    dados["v"] = pd.to_numeric(dados["valor"].replace({"-": "0"}), errors="coerce").fillna(0)
    dados = dados[dados["v"] > 0].copy()
    dados["mes_ref"] = [f"{a}-{MESES_ES.index(m) + 1:02d}" for a, m in zip(dados["ano"],
                                                                           dados["mes"])]
    dados["modelo_inegi"] = dados["item"].str.split(" - ").str[:2].str.join(" - ")
    saida = []
    for regex, chaves, fab in INEGI:
        sel = dados[[bool(re.search(regex, x)) for x in dados["modelo_inegi"]]]
        if sel.empty:
            continue
        por_mes = sel.groupby("mes_ref")["v"].sum().sort_index()
        blocos, atual = [], []
        for mes in por_mes.index:
            if atual and (pd.Period(mes, "M") - pd.Period(atual[-1], "M")).n > INEGI_DEFASAGEM + 1:
                blocos.append(atual)
                atual = []
            atual.append(mes)
        blocos.append(atual)
        for bloco in blocos:
            total = int(por_mes[bloco].sum())
            if total < INEGI_MINIMO:
                continue
            g = sel[sel["mes_ref"].isin(bloco)]
            maior = g.loc[g["v"].idxmax()]
            for k in chaves:
                marca, modelo, segmento = chave(k)
                saida.append({
                    "fabrica_id": fab, "pais": MX, "marca": marca, "modelo": modelo,
                    "segmento": segmento, "periodo_inicio": bloco[0],
                    "periodo_fim": _mais(bloco[-1], INEGI_DEFASAGEM),
                    "vinculo": "abastece_o_brasil", "regra_periodo": "meses_da_tabela",
                    "data_fonte": bloco[-1], "fonte_url": url_de(INEGI_PAGINA),
                    "tipo_fonte": tipo_fonte.tipo_de(url_de(INEGI_PAGINA), MAPA),
                    "fonte_trecho": maior["linha"], "pagina_salva": INEGI_PAGINA,
                    "observacao": (f"INEGI, exportacao ao Brasil de {bloco[0]} a {bloco[-1]}: "
                                   f"{total} unidades em {len(bloco)} meses "
                                   f"({', '.join(sorted(set(g['modelo_inegi'])))}); periodo = "
                                   f"esses meses e os {INEGI_DEFASAGEM} seguintes; trecho = o "
                                   f"mes de maior exportacao.")})
    return saida


# ===================================================================== saida


def conferir(linhas: list[dict], campos=(("pagina_salva", "fonte_trecho"),)) -> list[str]:
    erros = []
    for r in linhas:
        for c_pag, c_tre in campos:
            pagina, trecho = r.get(c_pag, ""), r.get(c_tre, "")
            if not trecho:
                continue
            t = texto(pagina)
            for parte in trecho.split(origem_pais.SEPARADOR):
                if normal(parte) not in t:
                    erros.append(f"{r.get('fabrica_id')} {r.get('modelo', '')} ({pagina}): "
                                 f"{parte[:90]}")
    return erros


def main() -> int:
    modelos = L + adefa() + inegi()
    erros = (conferir(F, (("pagina_salva", "fonte_trecho"),
                          ("operacao_pagina", "operacao_trecho"))) + conferir(modelos))
    if erros:
        print("\n".join(erros), file=sys.stderr)
        return 1
    for caminho, colunas, linhas in ((config.FABRICAS, origem_pais.COLUNAS_FABRICAS, F),
                                     (config.FABRICA_MODELOS, origem_pais.COLUNAS_FABRICA_MODELOS,
                                      modelos)):
        with caminho.open("w", encoding="utf-8", newline="") as fluxo:
            escritor = csv.DictWriter(fluxo, fieldnames=colunas)
            escritor.writeheader()
            escritor.writerows(linhas)
    print(f"{len(F)} fabricas; {len(modelos)} linhas fabrica x modelo",
          dict(Counter(r["vinculo"] for r in modelos)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
