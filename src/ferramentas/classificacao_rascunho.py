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

from comum import classificacao, config  # noqa: E402

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
     "Conjunto de gasolina, flex, diesel, hev, phev, bev, unido por '+'. O que o "
     "modelo oferecia na vigencia, nao o que vendeu."),
    ("eletrificacao",
     "Derivada da propulsao: total = so' hev/phev/bev; parcial = mistura; nenhuma = "
     "so' combustao. Vazia quando a propulsao esta' vazia."),
    ("carroceria",
     "hatch, sedan, suv, picape, minivan, furgao, perua, esportivo. Sai do "
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
    ("regerar",
     "python src/ferramentas/classificacao_rascunho.py. O script recusa sobrescrever "
     "um rascunho que ja' tenha decisao preenchida."),
]


def _questoes(rascunho: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for tema, pergunta, opcoes, recomendacao, filtro in QUESTOES:
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
            "decisao_humana": "",
        })
    return pd.DataFrame(linhas)


def _decisoes_existentes() -> int:
    if not config.CLASSIFICACAO_RASCUNHO.exists():
        return 0
    anterior = pd.read_excel(config.CLASSIFICACAO_RASCUNHO, sheet_name="classificacao",
                             dtype=str, keep_default_na=False)
    return int((anterior["decisao_humana"].str.strip() != "").sum())


def gerar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    painel = pd.read_parquet(config.PAINEL)
    propostas = pd.read_csv(config.PROPOSTA_CLASSIFICACAO, dtype=str, keep_default_na=False)
    regras = classificacao.carregar_regras()
    rascunho, fora = classificacao.classificar(
        painel, propostas, regras, config.PISO_CLASSIFICACAO)
    volume = int(painel["unidades"].sum())
    resumo = classificacao.resumo_por_confianca(rascunho, volume)
    return rascunho, fora, resumo


def escrever(rascunho, fora, resumo, questoes, volume_painel: int) -> None:
    regras = classificacao.carregar_regras()
    n_modelos = rascunho[classificacao.CHAVE].drop_duplicates().shape[0]
    pct = 100 * rascunho["unidades_na_vigencia"].sum() / volume_painel
    leia_me = pd.DataFrame(
        [(t, x.format(piso=f"{config.PISO_CLASSIFICACAO:,}".replace(",", "."),
                      n_modelos=n_modelos, pct=f"{pct:.2f}".replace(".", ","),
                      n_fora=len(fora)))
         for t, x in LEIA_ME], columns=["topico", "texto"])

    config.DIR_SAIDAS.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(config.CLASSIFICACAO_RASCUNHO, engine="xlsxwriter") as escritor:
        abas = [("leia_me", leia_me), ("classificacao", rascunho), ("questoes", questoes),
                ("resumo", resumo), ("regras", regras), ("nao_classificados", fora)]
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

    rascunho, fora, resumo = gerar()
    questoes = _questoes(rascunho)
    volume = int(pd.read_parquet(config.PAINEL, columns=["unidades"])["unidades"].sum())
    escrever(rascunho, fora, resumo, questoes, volume)

    print(f"{len(rascunho)} linhas (modelo-vigencia) de "
          f"{rascunho[classificacao.CHAVE].drop_duplicates().shape[0]} modelos; "
          f"{len(fora)} nao classificados")
    print("\nconfianca geral:")
    print(resumo[resumo["atributo"].str.startswith("geral")].to_string(index=False))
    print("\nquestoes:")
    print(questoes[["tema", "modelos", "unidades"]].to_string(index=False))
    print(f"\ngravado {config.CLASSIFICACAO_RASCUNHO.relative_to(config.RAIZ)} e "
          f"{config.CLASSIFICACAO_RESUMO.relative_to(config.RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
