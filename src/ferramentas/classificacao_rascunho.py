#!/usr/bin/env python3
"""Rascunho da dimensao de classificacao de modelo, para adjudicacao humana.

Fase 1. Produz `saidas/classificacao_rascunho.xlsx` -- uma linha por
modelo-vigencia dos modelos acima de `config.PISO_CLASSIFICACAO` unidades,
maior volume primeiro -- e `saidas/classificacao_resumo.csv`, com modelos e
volume por nivel de confianca. **Nao grava nada em `dados/processado/`**: a
fase 2, que transforma o rascunho adjudicado em dimensao, so' existe depois
da decisao humana.

Nao e' etapa do pipeline de proposito: o pipeline roda sozinho e sobrescreve,
e este arquivo vai receber a letra do pesquisador. Por isso tambem ha' guarda:
se o rascunho existente tiver qualquer `decisao_humana` preenchida, o script
recusa sobrescrever sem `--sobrescrever`.

Uso:
    python src/ferramentas/classificacao_rascunho.py
    python src/ferramentas/classificacao_rascunho.py --sobrescrever
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comum import classificacao, config, validacao_classificacao as validacao  # noqa: E402

# A busca de fonte de origem cobre a origem `media`/`baixa` dos maiores modelos.
TOP_ORIGEM = 241

# Questoes que a lista de valores ou a fonte nao resolvem (sec.9.6). Os
# modelos afetados e o volume sao calculados do rascunho, nao escritos aqui.
# (tema, pergunta, opcoes, recomendacao, filtro sobre o rascunho)
QUESTOES = [
    ("hibrido leve (MHEV)",
     "A lista de propulsao nao tem hibrido leve (48V, sem tracao eletrica). "
     "Os modelos MHEV foram propostos so' com a propulsao a combustao.",
     "(a) manter como combustao; (b) acrescentar `mhev` a' lista; (c) contar como `hev`",
     "(b): juntar a combustao esconde a tecnologia, e juntar a `hev` infla a "
     "eletrificacao.",
     lambda r: r["observacao"].str.contains("MHEV", regex=False)),
    ("eletrico com extensor (REEV)",
     "Eletrico de tracao so' eletrica com motor a combustao como gerador. Nao ha' "
     "valor para isso; foi proposto so' `bev` e a versao REEV vai na observacao.",
     "(a) `phev`; (b) acrescentar `reev`; (c) `bev`",
     "(b), ou (a) se a analise seguir a contagem que junta REEV a plug-in.",
     lambda r: r["observacao"].str.contains("REEV", regex=False)),
    ("caminhao leve",
     "A fonte poe caminhoes leves cabine-sobre-motor (Hyundai HR, Kia Bongo, VW "
     "Delivery Express, Foton Aumark, chassis da Daily e da Sprinter) em Furgoes, "
     "e a lista de carroceria nao tem `caminhao_leve`.",
     "(a) seguir a fonte (`furgao`); (b) acrescentar `caminhao_leve`",
     "(b): furgao e caminhao leve respondem a politicas e demandas diferentes.",
     lambda r: r["observacao"].str.contains("caminhao leve|chassi", case=False, regex=True)),
    ("carroceria so' por conhecimento",
     "Modelo sem sub-segmento de carroceria na fonte: so' em 'Veiculos de Entrada' "
     "(faixa de preco, regra S09) ou so' no ranking. A carroceria veio do "
     "conhecimento do assistente.",
     "confirmar ou corrigir linha a linha",
     "conferir primeiro os de maior volume (Gol, Uno, Palio).",
     lambda r: r["fonte_da_proposta"].str.contains(
         "carroceria: " + re.escape(classificacao.FONTE_CONHECIMENTO), regex=True)),
    ("carroceria discordante da fonte",
     "O assistente discorda do sub-segmento da fonte (Kia Picanto e Suzuki SX4 em "
     "Monocab, Mercedes CLC em Sedans Pequenos, Citroen DS5 em Sedans Grandes). "
     "O rascunho fica com o valor da fonte, rebaixado a `media`.",
     "(a) fonte; (b) conhecimento",
     "(a) para artigo que cita a Fenabrave; (b) para artigo sobre produto.",
     lambda r: r["fonte_da_proposta"].str.contains("sinalizada pelo assistente")
     & ~r["observacao"].str.contains("caminhao leve|fonte divide", case=False, regex=True)),
    ("carroceria da fonte dividida ou rala",
     "Uma segunda carroceria tem 10% ou mais do volume da vigencia na propria fonte "
     "(geracao nova com outra carroceria, ou reclassificacao), ou a fonte so' "
     "classificou menos de 10% das unidades do modelo.",
     "(a) manter a dominante; (b) dividir a vigencia no mes da troca",
     "olhar `sub_segmentos_fonte`; dividir so' quando a troca for de produto.",
     lambda r: r["observacao"].str.contains("Fonte divide|So' [0-9.]+% das", regex=True)),
    ("transicao para o flex nao datada",
     "Modelos lancados a gasolina que ganharam versao flex entre 2003 e 2006 aparecem "
     "com o conjunto `gasolina+flex` na vigencia inteira. A data da troca por modelo "
     "nao foi proposta.",
     "(a) aceitar o conjunto; (b) dividir a vigencia na data do lancamento flex",
     "(a), salvo se algum artigo depender da difusao do flex.",
     lambda r: r["propulsao_oferecida"].str.contains("gasolina")
     & r["propulsao_oferecida"].str.contains("flex")),
    ("troca sem data ou com data aproximada",
     "O atributo mudou dentro do nome -- producao local iniciada (BYD em Camacari, GWM "
     "em Iracemapolis, BMW em Araquari, Mitsubishi em Catalao, CAOA em Anapolis) ou "
     "versao eletrificada lancada -- e a troca nao foi datada, ou foi datada so' "
     "aproximadamente. A transicao para o flex tem questao propria.",
     "datar a troca e dividir a vigencia",
     "datar primeiro os de maior volume; a origem e' o atributo mais fragil.",
     lambda r: r["observacao"].str.contains("nao datad|aproximad|Datas", regex=True)
     & ~r["observacao"].str.contains("ransicao", regex=False)),
    ("origem sem proposta",
     "O assistente nao soube propor a origem da producao.",
     "preencher", "",
     lambda r: r["origem_producao"] == ""),
    ("propulsao sem proposta",
     "O assistente nao soube propor a propulsao.",
     "preencher", "",
     lambda r: r["propulsao_oferecida"] == ""),
    ("montagem de conjuntos importados (SKD/CKD)",
     "Varias trocas de origem com fonte sao montagem de conjuntos importados: a BYD em "
     "Camacari (conjuntos da China), o Spark EUV em Horizonte (SKD), o Land Rover de "
     "Itatiaia no inicio (CKD), os furgoes do Uruguai (SKD). A GWM declara processo 'peca a "
     "peca'. A lista de origem nao distingue montagem de fabricacao.",
     "(a) SKD/CKD conta como `nacional`; (b) conta como `importado`; (c) acrescentar um valor "
     "(`montagem_local`)",
     "(c), ou (a) com coluna propria: para o artigo de tarifa, o kit tem aliquota diferente do "
     "carro inteiro, e juntar os dois apaga exatamente a variacao que interessa.",
     lambda r: r["origem_fonte_trecho"].str.contains("SKD|CKD|conjuntos|kits", regex=True)
     | r["observacao"].str.contains("SKD|CKD", regex=True)),
    ("um nome, dois produtos",
     "O nome comercial cobre produtos diferentes em momentos diferentes (GM/SONIC "
     "hatch de 2012 e crossover de 2025; VOLVO/V40 perua e hatch). E' questao de "
     "`regras.csv` (D1), fora desta fase; aqui so' se sinaliza.",
     "decidir em `regras.csv`", "",
     lambda r: r["observacao"].str.contains("Outro produto|O nome cobre|Nome agregado|"
                                            "Nome composto|Nome generico", regex=True)),
    ("um produto, duas chaves",
     "O mesmo carro aparece sob duas marcas na fonte (CHERY/TIGGO 7 antes de CAOA "
     "CHERY/TIGGO 7). A classificacao e' por chave e repete a proposta; a fusao, se "
     "houver, e' linha de `regras.csv`.",
     "decidir em `regras.csv`", "",
     lambda r: r["observacao"].str.contains("Mesmo produto de", regex=False)),
]

LEIA_ME = [
    ("o que e'",
     "Rascunho da dimensao de classificacao de modelo (fase 1). Cada linha e' uma "
     "PROPOSTA para adjudicacao, nao um fato. Nada daqui esta' em `dados/processado/`."),
    ("unidade",
     "Uma linha por (marca, modelo, segmento) e vigencia. A chave e' a do painel. A "
     "vigencia existe porque o atributo muda dentro do nome: o Corolla ganhou versao "
     "hibrida, o Civic passou de nacional a importado."),
    ("escopo",
     "Os modelos com volume total acima de {piso} unidades: {n_modelos} modelos, "
     "{pct}% do volume do painel. Os outros {n_fora} estao na aba "
     "`nao_classificados` com `nao_classificado`."),
    ("limitacao da fonte",
     "A fonte nao separa unidades por versao. Um modelo vendido em flex e em hibrido "
     "aparece como um numero so', e nao ha' como saber quantas unidades foram de cada. "
     "Por isso `propulsao_oferecida` e' conjunto e `eletrificacao` tem tres niveis. "
     "Contar unidades eletrificadas por propulsao exige fonte externa."),
    ("propulsao_oferecida",
     "Conjunto de gasolina, flex, diesel, mhev, hev, phev, reev, bev, unido por '+'. O que "
     "o modelo oferecia na vigencia, nao o que vendeu. `mhev` (hibrido leve) e `reev` "
     "(eletrico com extensor) entraram por decisao de 2026-10-01."),
    ("eletrificacao",
     "Derivada da propulsao: total = so' hev/phev/reev/bev; parcial = mistura, ou qualquer "
     "conjunto com mhev (o hibrido leve nao roda em modo eletrico; junta-lo a hev "
     "superestimaria, omiti-lo subestimaria); nenhuma = so' combustao. Vazia quando a "
     "propulsao esta' vazia."),
    ("carroceria",
     "hatch, sedan, suv, picape, minivan, furgao, caminhao_leve, perua, esportivo. Sai do "
     "sub-segmento em que a propria Fenabrave listou o modelo (regras S01-S10, aba "
     "`regras`); so' quando a fonte nao classifica e' que vem do conhecimento."),
    ("origem_producao",
     "nacional, importado, ambos. So' conhecimento: a fonte nao informa origem. E' o "
     "atributo mais fragil do rascunho."),
    ("confianca",
     "Da proposta, nao da verdade. `confianca` e' o pior dos tres atributos; as "
     "colunas `confianca_*` dao o de cada um. alta: regra sobre a fonte, regra por "
     "nome, ou conhecimento sem duvida razoavel. media: conhecimento com duvida, ou "
     "fonte dividida. baixa: sem proposta -- o valor fica vazio. Preferiu-se vazio a "
     "chute."),
    ("fonte_da_proposta",
     "De onde saiu cada valor, atributo por atributo: 'sub-segmento da fonte' (com a "
     "fracao das unidades que a fonte classificou), 'regra por nome Nxx', "
     "'conhecimento do assistente', ou 'sem proposta'."),
    ("sub_segmentos_fonte",
     "Como a fonte distribuiu as unidades da vigencia entre sub-segmentos. O que falta "
     "para 100% veio do ranking, que nao tem sub-segmento."),
    ("unidades",
     "`unidades_totais`, `primeiro_mes` e `ultimo_mes` sao do modelo inteiro; "
     "`unidades_na_vigencia` e' so' da linha. As vigencias de um modelo cobrem todo "
     "mes com unidades e nao se sobrepoem (conferido pelo script)."),
    ("como preencher decisao_humana",
     "`ok` aceita a linha como esta'. `atributo=valor; atributo=valor` corrige so' o "
     "que for dito (ex.: `propulsao_oferecida=flex+hev; origem_producao=nacional`); o "
     "resto fica como proposto. `dividir em AAAA-MM` pede nova vigencia a partir "
     "daquele mes -- descreva os atributos de cada lado. Qualquer outro texto e' lido "
     "a mao. Linha com decisao vazia nao entra na fase 2."),
    ("questoes",
     "A aba `questoes` lista o que a lista de valores ou a fonte nao resolvem (hibrido "
     "leve, REEV, caminhao leve e outras), com os modelos e o volume afetados. Sao "
     "decisoes de desenho, a tomar antes de adjudicar linha a linha."),
    ("decisoes de 2026-10-01",
     "mhev e reev entram na propulsao; caminhao_leve entra na carroceria (regra S11: "
     "refina o furgao da fonte); a transicao flex fica como esta' (gasolina+flex na "
     "vigencia inteira, limitacao conhecida); 'um nome, dois produtos' e 'um produto, duas "
     "chaves' seguem adiadas pela Parte 0. Ver a coluna `estado` da aba `questoes`."),
    ("a_adjudicar",
     "So' o que ainda precisa de decisao humana, maior volume primeiro: divergencia com o "
     "PBE; ausencia no PBE entre os {top} maiores; fonte de origem que contradiz a proposta "
     "ou ajusta a data dela; e origem sem fonte datada nos casos que a rodada mandou buscar. "
     "A coluna `motivo` diz qual. A decisao pode ser escrita ali ou na aba `classificacao`."),
    ("validacao contra o PBE",
     "Colunas `pbe_*`. O PBE Veicular (Inmetro, 2009-2026) lista por versao o tipo de "
     "propulsao (coluna propria desde 2021) e o combustivel. Casamento por marca e prefixo do "
     "modelo, versao ignorada; cada ano do PBE vai para a vigencia com mais meses naquele "
     "ano. `pbe_situacao`: concorda (mesmo conjunto), diverge (`pbe_diferenca` diz o que "
     "sobra de cada lado), ausente (o modelo nao aparece no PBE nos anos da vigencia -- "
     "ausencia NAO e' evidencia de combustao). A gasolina da transicao flex, anterior ao "
     "PBE, nao conta como divergencia. A proposta fica intacta ao lado."),
    ("o que o PBE distingue",
     "Combustao, Hibrido, Plug-In e Eletrico, mais o combustivel (G, F, D, E). NAO distingue "
     "hibrido leve: o Kia Stonic MHEV e o Subaru Forester MHEV estao em Hibrido, o Subaru XV "
     "MHEV em Combustao (2021); os Stellantis 'HYB' (Pulse, Fastback, Renegade), o Toro de "
     "2026 e o Discovery Sport D200 estao em Hibrido sem MHEV no nome -- 'so' no PBE: hev' "
     "contra uma proposta mhev e' provavelmente rotulo do PBE. NAO distingue REEV: o "
     "Leapmotor C10 REEV esta' em Plug-In. "
     "Onde o nome da versao diz MHEV ou REEV, o nome manda (aba `pbe_mapeamento`). Ate' "
     "2020 nao ha' coluna de propulsao: hibrido sem marcador no nome sai como combustao."),
    ("origem contra fonte datada",
     "Colunas `origem_*`. Cada fonte foi aberta na rodada de validacao; o texto da pagina "
     "esta' guardado em dados/bruto/origem_paginas/ e o trecho copiado aparece nele "
     "literalmente (testado). `origem_confronto` (confirma, complementa, ajusta_data, "
     "contradiz, inconclusivo) e' a LEITURA DO ASSISTENTE da fonte contra a proposta -- "
     "confira o trecho antes de aceitar. Aba `origem_fontes` com todas as linhas."),
    ("regerar",
     "python src/ferramentas/classificacao_rascunho.py. O script recusa sobrescrever "
     "um rascunho que ja' tenha decisao preenchida."),
]


# Decisoes do pesquisador sobre as questoes (PARA-O-CODE-classificacao-validacao, sec.1).
DECISOES = {
    "hibrido leve (MHEV)": ("decidida em 2026-10-01", "`mhev` entra na lista de propulsao; "
                            "na eletrificacao conta como `parcial`."),
    "eletrico com extensor (REEV)": ("decidida em 2026-10-01", "`reev` entra como valor proprio."),
    "caminhao leve": ("decidida em 2026-10-01", "`caminhao_leve` entra na carroceria (regra "
                      "S11). Daily e Sprinter ficam em furgao: o nome nao separa furgao de chassi."),
    "transicao para o flex nao datada": ("decidida em 2026-10-01", "Fica como esta': "
                                         "`gasolina+flex` na vigencia inteira. Limitacao "
                                         "conhecida, registrada no dicionario."),
    "um nome, dois produtos": ("adiada (Parte 0)", "Questao de `regras.csv`."),
    "um produto, duas chaves": ("adiada (Parte 0)", "Questao de `regras.csv`."),
}


def _questoes(rascunho: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for tema, pergunta, opcoes, recomendacao, filtro in QUESTOES:
        estado, decisao = DECISOES.get(tema, ("aberta", ""))
        afetados = rascunho[filtro(rascunho)]
        modelos = afetados.drop_duplicates(classificacao.CHAVE)
        linhas.append({
            "tema": tema,
            "pergunta": pergunta,
            "opcoes": opcoes,
            "recomendacao": recomendacao,
            "modelos": len(modelos),
            "unidades": int(afetados["unidades_na_vigencia"].sum()),
            "exemplos": ", ".join(f"{m}/{n}" for m, n in
                                  modelos[["marca", "modelo"]].head(12).to_numpy()),
            "estado": estado,
            "decisao_humana": decisao,
        })
    return pd.DataFrame(linhas)


def _decisoes_existentes() -> int:
    if not config.CLASSIFICACAO_RASCUNHO.exists():
        return 0
    anterior = pd.read_excel(config.CLASSIFICACAO_RASCUNHO, sheet_name="classificacao",
                             dtype=str, keep_default_na=False)
    return int((anterior["decisao_humana"].str.strip() != "").sum())


def gerar():
    painel = pd.read_parquet(config.PAINEL)
    propostas = pd.read_csv(config.PROPOSTA_CLASSIFICACAO, dtype=str, keep_default_na=False)
    regras = classificacao.carregar_regras()
    rascunho, fora = classificacao.classificar(
        painel, propostas, regras, config.PISO_CLASSIFICACAO)
    volume = int(painel["unidades"].sum())
    resumo = classificacao.resumo_por_confianca(rascunho, volume)

    # validacao contra fonte: propulsao no PBE, origem em fontes datadas
    versoes = pd.read_csv(config.PBE_VERSOES, dtype=str, keep_default_na=False)
    regras_pbe = validacao.regras_propulsao()
    mapeados = [validacao.mapear_propulsao(t, c, m, mo, regras_pbe) for t, c, m, mo in zip(
        versoes["tipo_propulsao"], versoes["combustivel"], versoes["marcador_nome"],
        versoes["motor"])]
    versoes["valor_taxonomia"] = [v for v, _ in mapeados]
    versoes["regra_mapeamento"] = [o for _, o in mapeados]
    chaves = painel[validacao.CHAVE].drop_duplicates()
    casado = validacao.casar(versoes, chaves)
    rascunho = validacao.comparar_pbe(rascunho, casado)
    rascunho = validacao.anexar_origem(rascunho, validacao.carregar_fontes_origem())
    # decisao_humana fica sempre por ultimo
    rascunho = rascunho[[c for c in rascunho.columns if c != "decisao_humana"]
                        + ["decisao_humana"]]
    top = TOP_ORIGEM
    fila = validacao.a_adjudicar(rascunho, top)
    resumo_val = pd.concat([_casamento(rascunho, casado),
                            validacao.resumo_validacao(rascunho, volume, top)],
                           ignore_index=True)
    return rascunho, fora, resumo, fila, resumo_val, casado


def _casamento(rascunho: pd.DataFrame, casado: pd.DataFrame) -> pd.DataFrame:
    """Taxa de casamento com o PBE, em modelos e em volume."""
    no_pbe = set(map(tuple, casado.loc[casado["marca"] != "", validacao.CHAVE].to_numpy()))
    modelos = rascunho.groupby(validacao.CHAVE, as_index=False).agg(
        unidades=("unidades_na_vigencia", "sum"), ultimo=("vigencia_fim", "max"))
    modelos["casado"] = [tuple(k) in no_pbe for k in modelos[validacao.CHAVE].to_numpy()]
    total = modelos["unidades"].sum()
    linhas = []
    for nivel, parte in [
        ("modelos classificados", modelos),
        ("... com alguma versao no PBE (qualquer ano)", modelos[modelos["casado"]]),
        ("modelos com vida depois de 2008 (o PBE comeca em 2009)",
         modelos[modelos["ultimo"] >= "2009-01"]),
        ("... com alguma versao no PBE", modelos[(modelos["ultimo"] >= "2009-01")
                                                 & modelos["casado"]]),
    ]:
        linhas.append({"quadro": "casamento com o PBE", "nivel": nivel,
                       "modelo_vigencias": "", "modelos": len(parte),
                       "unidades": int(parte["unidades"].sum()),
                       "pct_do_classificado": round(100 * parte["unidades"].sum() / total, 2)})
    return pd.DataFrame(linhas)


def _nao_casados(casado: pd.DataFrame, rascunho: pd.DataFrame) -> pd.DataFrame:
    """Versoes do PBE de marcas do escopo que nao casaram com modelo nenhum."""
    marcas_escopo = set(rascunho["marca"])
    tradutor = validacao.marcas_pbe()
    sem = casado[(casado["marca"] == "")
                 & casado["marca_pbe"].map(lambda m: bool(set(tradutor.get(m, []))
                                                          & marcas_escopo))].copy()
    sem["inicio_do_nome"] = sem["modelo_versao"].str.split(" ").str[:2].str.join(" ")
    return (sem.groupby(["marca_pbe", "inicio_do_nome"], as_index=False)
            .agg(versoes=("modelo_versao", "size"),
                 anos=("ano_pbe", lambda a: validacao._anos_compactos([int(x) for x in a])),
                 exemplo=("modelo_versao", "first"))
            .sort_values(["versoes"], ascending=False))


def escrever(rascunho, fora, resumo, questoes, volume_painel: int, fila, resumo_val,
             casado) -> None:
    regras = classificacao.carregar_regras()
    n_modelos = rascunho[classificacao.CHAVE].drop_duplicates().shape[0]
    pct = 100 * rascunho["unidades_na_vigencia"].sum() / volume_painel
    leia_me = pd.DataFrame(
        [(t, x.format(piso=f"{config.PISO_CLASSIFICACAO:,}".replace(",", "."),
                      n_modelos=n_modelos, pct=f"{pct:.2f}".replace(".", ","),
                      n_fora=len(fora), top=TOP_ORIGEM))
         for t, x in LEIA_ME], columns=["topico", "texto"])

    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(config.CLASSIFICACAO_RASCUNHO, engine="xlsxwriter") as escritor:
        abas = [("leia_me", leia_me), ("a_adjudicar", fila), ("classificacao", rascunho),
                ("questoes", questoes), ("validacao", resumo_val), ("resumo", resumo),
                ("origem_fontes", validacao.carregar_fontes_origem()),
                ("pbe_mapeamento", validacao.regras_propulsao()),
                ("pbe_nao_casados", _nao_casados(casado, rascunho)),
                ("regras", regras), ("nao_classificados", fora)]
        for nome, quadro in abas:
            quadro.to_excel(escritor, sheet_name=nome, index=False)
            folha = escritor.sheets[nome]
            folha.freeze_panes(1, 0)
            if len(quadro):
                folha.autofilter(0, 0, len(quadro), len(quadro.columns) - 1)
            for i, coluna in enumerate(quadro.columns):
                largura = max([len(str(coluna))] + [len(str(v)) for v in quadro[coluna].head(200)])
                folha.set_column(i, i, min(max(largura, 8) + 1, 70))
    resumo.to_csv(config.CLASSIFICACAO_RESUMO, index=False)
    resumo_val.to_csv(config.DIR_SAIDAS / "classificacao_validacao.csv", index=False)
    casado[casado["marca"] != ""][
        ["ano_pbe", "pagina", "marca_pbe", "modelo_versao", "tipo_propulsao", "marcador_nome",
         "combustivel", "valor_taxonomia", "regra_mapeamento", "marca", "modelo", "segmento"]
    ].to_csv(config.DIR_SAIDAS / "pbe_casamento.csv", index=False)


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--sobrescrever", action="store_true",
                            help="sobrescrever mesmo com decisao_humana preenchida")
    args = analisador.parse_args()

    ja_decididas = _decisoes_existentes()
    if ja_decididas and not args.sobrescrever:
        print(f"{config.CLASSIFICACAO_RASCUNHO} tem {ja_decididas} decisoes preenchidas; "
              "recuso sobrescrever sem --sobrescrever.", file=sys.stderr)
        return 2

    rascunho, fora, resumo, fila, resumo_val, casado = gerar()
    questoes = _questoes(rascunho)
    volume = int(pd.read_parquet(config.PAINEL, columns=["unidades"])["unidades"].sum())
    escrever(rascunho, fora, resumo, questoes, volume, fila, resumo_val, casado)

    print(f"{len(rascunho)} linhas (modelo-vigencia) de "
          f"{rascunho[classificacao.CHAVE].drop_duplicates().shape[0]} modelos; "
          f"{len(fora)} nao classificados")
    print("\nconfianca geral:")
    print(resumo[resumo["atributo"].str.startswith("geral")].to_string(index=False))
    print("\nquestoes:")
    print(questoes[["tema", "estado", "modelos", "unidades"]].to_string(index=False))
    print("\nvalidacao contra fonte:")
    print(resumo_val.to_string(index=False))
    print(f"\na adjudicar: {len(fila)} linhas")
    print(f"\ngravado {config.CLASSIFICACAO_RASCUNHO.relative_to(config.RAIZ)} e "
          f"{config.CLASSIFICACAO_RESUMO.relative_to(config.RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
