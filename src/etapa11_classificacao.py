#!/usr/bin/env python3
"""Etapa 11 -- dimensao de classificacao de modelo (fase 2).

Le o rascunho adjudicado (`saidas/classificacao_rascunho.xlsx`) e grava a
dimensao. O rascunho e' a fonte de verdade da adjudicacao: esta etapa so' o le,
e ninguem edita o parquet a' mao -- a decisao se escreve no rascunho e a etapa
roda de novo. A precedencia e as procedencias estao em `comum/fase2.py`.

Produtos:
- `dados/processado/classificacao.parquet` -- uma linha por
  `(marca, modelo, segmento, vigencia_inicio, vigencia_fim)`, com o valor final e
  a procedencia de cada atributo;
- `dados/processado/classificacao_montagem.parquet` -- periodos de montagem
  local, com procedencia propria;
- `dados/processado/classificacao_propulsao_anual.parquet` -- os tipos de
  propulsao oferecidos em cada ano, uma linha por `(marca, modelo, segmento,
  vigencia_inicio, ano)` com unidades, nas leituras longa e curta; e' a tabela
  para serie temporal (`comum/propulsao_anual.py`), com a entrada e a saida de
  cada tipo em `saidas/classificacao_propulsao_tipos.csv` e a defasagem medida
  do PBE em `saidas/classificacao_pbe_defasagem.csv`;
- `saidas/classificacao_uso_teste.csv` -- o uso-teste da ESPEC: participacao de
  cada nivel de eletrificacao nas unidades, por ano, pelo conjunto da vigencia e
  pela tabela anual nas duas leituras;
- `saidas/eletrificacao_banda.csv` -- piso e tres tetos da eletrificacao, por ano
  e leitura;
- `saidas/classificacao_procedencia.csv` -- fracao do volume do painel em cada
  procedencia, por atributo (juncao de teste);
- `saidas/classificacao_dicionario.md` -- dicionario da dimensao.

Falha (codigo 1, nada gravado) se: uma chave do painel ficar sem linha em algum
mes com unidades, ou vigencias se sobrepuserem; um valor `humana` ou `regra_*`
diferir do rascunho; um modo de montagem com fonte diferir do rascunho; ou uma
decisao humana nao puder ser aplicada (texto livre, `dividir em`, ou atributo
deixado `pendente` numa linha com decisao humana); ou a tabela anual tiver
vigencia-ano sem linha, unidades diferentes do painel nos meses da vigencia,
tipo fora da vigencia, leitura curta com tipo que a longa nao tem, ano sem
propulsao, ou intervalo de tipo fora de ordem.

Uso:
    python src/etapa11_classificacao.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import adjudicacao, config, fase2, log, pbe_variantes, propulsao_anual  # noqa: E402

ETAPA = "etapa11_classificacao"
ADVERTENCIA = ("Um artigo que use propulsao ou origem como variavel de tratamento deve "
               "restringir-se as procedencias `humana` e `regra_fonte_forte`, e declarar a "
               "fracao do volume que ficou de fora.")


def ler_rascunho() -> tuple[pd.DataFrame, pd.DataFrame]:
    def aba(nome):
        return pd.read_excel(config.CLASSIFICACAO_RASCUNHO, sheet_name=nome, dtype=str,
                             keep_default_na=False)
    return aba("classificacao"), aba("nao_classificados")


def executar() -> int:
    logger = log.preparar(ETAPA)
    if not config.CLASSIFICACAO_RASCUNHO.exists():
        logger.error("sem rascunho em %s", log.caminho_relativo(config.CLASSIFICACAO_RASCUNHO))
        return 1
    rascunho, nao_classificados = ler_rascunho()
    painel = pd.read_parquet(config.PAINEL, columns=fase2.CHAVE + ["mes_ref", "unidades"])

    try:
        dim = fase2.dimensao(rascunho, nao_classificados, painel)
    except fase2.DecisaoInvalida as erro:
        logger.error("decisao humana que a fase 2 nao aplica: %s", erro)
        return 1

    problemas = fase2.problemas_de_cobertura(dim, painel)
    problemas += fase2.problemas_de_fidelidade(dim, rascunho)
    montagem = fase2.montagem_final(dim, rascunho, adjudicacao.carregar_montagem(), painel,
                                    adjudicacao.periodos_montagem)
    problemas += fase2.problemas_de_cobertura(montagem, painel, "montagem_inicio",
                                              "montagem_fim")
    if config.CLASSIFICACAO_MONTAGEM_RASCUNHO.exists():
        do_rascunho = pd.read_csv(config.CLASSIFICACAO_MONTAGEM_RASCUNHO, dtype=str,
                                  keep_default_na=False)
        problemas += fase2.problemas_de_montagem(montagem, do_rascunho)
    casado = pd.read_csv(config.PBE_CASAMENTO, dtype=str, keep_default_na=False)
    fontes = pd.read_csv(config.PROPULSAO_FONTES, dtype=str, keep_default_na=False)
    defasagem, direcao = propulsao_anual.defasagem_pbe(fontes, casado)
    variantes = pbe_variantes.ler_candidatos()
    tipos = propulsao_anual.tabela_de_tipos(dim, casado, fontes, direcao,
                                            pbe_variantes.guardas(variantes))
    anual = propulsao_anual.anual(dim, tipos, painel)
    problemas += propulsao_anual.problemas(anual, dim, tipos, painel)
    if problemas:
        for problema in problemas[:50]:
            logger.error(problema)
        logger.error("%d problemas: nada gravado", len(problemas))
        return 1

    volume = fase2.volume_por_procedencia(dim, painel)
    uso = propulsao_anual.uso_teste(dim, anual, painel)
    banda = propulsao_anual.banda(anual, painel)
    config.DIR_PROCESSADO.mkdir(parents=True, exist_ok=True)
    dim.to_parquet(config.CLASSIFICACAO, index=False)
    montagem.to_parquet(config.CLASSIFICACAO_MONTAGEM, index=False)
    anual.to_parquet(config.CLASSIFICACAO_PROPULSAO_ANUAL, index=False)
    tipos.to_csv(config.CLASSIFICACAO_PROPULSAO_TIPOS, index=False)
    defasagem.to_csv(config.CLASSIFICACAO_PBE_DEFASAGEM, index=False)
    uso.to_csv(config.CLASSIFICACAO_USO_TESTE, index=False)
    banda.to_csv(config.ELETRIFICACAO_BANDA, index=False)
    sem_evidencia = pbe_variantes.sem_evidencia(variantes, tipos, propulsao_anual.FAMILIA_PBE)
    sem_evidencia.to_csv(config.PBE_VARIANTES_SEM_EVIDENCIA, index=False)
    volume.to_csv(config.CLASSIFICACAO_PROCEDENCIA, index=False)
    config.CLASSIFICACAO_DICIONARIO.write_text(
        dicionario(dim, montagem, volume, anual, tipos, banda, defasagem, direcao),
        encoding="utf-8")
    logger.info("dimensao: %d linhas (%d classificadas, %d abaixo do piso); montagem: %d "
                "periodos", len(dim), int((dim["vigencia_inicio_rascunho"] != "").sum()),
                int((dim["vigencia_inicio_rascunho"] == "").sum()), len(montagem))
    for _, linha in volume[volume["unidades"] > 0].iterrows():
        logger.info("%-10s %-18s %5.2f%%", linha["atributo"], linha["procedencia"],
                    linha["pct_do_volume"])
    eletrificados = tipos[~tipos["tipo"].isin(propulsao_anual.COMBUSTAO)]
    logger.info("propulsao anual: %d linhas; entrada dos %d tipos eletrificados: %s; "
                "%d tipos com evidencia de saida; defasagem do PBE: direcao %d",
                len(anual), len(eletrificados),
                ", ".join(f"{f} {n}" for f, n in
                          eletrificados["fonte_temporal"].value_counts().items()),
                int((tipos["fonte_saida"] != "").sum()), direcao)
    sem_decisao = variantes[variantes["chave_viva"] & (variantes["decisao"] == "")]
    logger.info("variantes do PBE sem casamento: %d familias sem evidencia; a guarda "
                "descartou ausencia em %d tipos; %d pares versao-chave sem decisao em "
                "config/pbe_modelos.csv",
                len(sem_evidencia), int((tipos["anos_guardados"] != "").sum()), len(sem_decisao))
    if len(sem_decisao):
        logger.warning("versoes sem decisao (entram na guarda e na lista): %s",
                       "; ".join(sorted(set(sem_decisao["modelo_versao"]))))
    logger.info("gravado %s, %s e %s", log.caminho_relativo(config.CLASSIFICACAO),
                log.caminho_relativo(config.CLASSIFICACAO_MONTAGEM),
                log.caminho_relativo(config.CLASSIFICACAO_PROPULSAO_ANUAL))
    return 0


# --------------------------------------------------------------- dicionario


def _pct(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def _tabela_volume(volume: pd.DataFrame) -> str:
    largura = volume.pivot(index="procedencia", columns="atributo", values="pct_do_volume")
    linhas = ["| procedencia | propulsao | carroceria | origem |", "|---|---:|---:|---:|"]
    for procedencia in fase2.PROCEDENCIAS:
        if procedencia in largura.index:
            p = largura.loc[procedencia]
            linhas.append(f"| `{procedencia}` | {_pct(p['propulsao'])}% | "
                          f"{_pct(p['carroceria'])}% | {_pct(p['origem'])}% |")
    return "\n".join(linhas)


def _corte_pbe() -> str:
    if not config.PBE_COBERTURA.exists():
        return ""
    cobertura = pd.read_csv(config.PBE_COBERTURA)
    acima = cobertura[cobertura["cobertura_pct"] >= 80]
    if acima.empty:
        return ""
    corte = acima.iloc[0]
    return (f"A ausencia no PBE so' foi tratada como informativa a partir de "
            f"{int(corte['ano'])}, quando o programa passou a cobrir "
            f"{_pct(corte['cobertura_pct'])}% do volume do painel.")


MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
AVISO_VIGENCIA = ("conjunto de tudo que foi oferecido em algum momento da vigência — não usar "
                  "em série temporal; para isso, `classificacao_propulsao_anual`.")


def _rotulo(ano: int, meses: int) -> str:
    return str(ano) if meses == 12 else f"{ano} (jan a {MESES[meses - 1]})"


def _tabela_banda(banda: pd.DataFrame) -> str:
    linhas = ["| ano | leitura | piso | teto | teto_sem_mhev | teto_estrito |",
              "|---|---|---:|---:|---:|---:|"]
    for _, b in banda.sort_values(["ano", "leitura"], ascending=[True, False]).iterrows():
        linhas.append(f"| {_rotulo(b['ano'], b['meses'])} | {b['leitura']} | "
                      + " | ".join(f"{_pct(b[c])}%" for c in propulsao_anual.TETOS) + " |")
    return "\n".join(linhas)


def _tabela_fonte_temporal(tipos: pd.DataFrame) -> str:
    eletrificados = tipos[~tipos["tipo"].isin(propulsao_anual.COMBUSTAO)]
    contagem = eletrificados["fonte_temporal"].value_counts()
    linhas = ["| fonte_temporal | tipos eletrificados (vigencia x tipo) |", "|---|---:|"]
    for fonte in reversed(propulsao_anual.FONTES_TEMPORAIS):
        linhas.append(f"| `{fonte}` | {int(contagem.get(fonte, 0))} |")
    return "\n".join(linhas)


def dicionario(dim: pd.DataFrame, montagem: pd.DataFrame, volume: pd.DataFrame,
               anual: pd.DataFrame, tipos: pd.DataFrame, banda: pd.DataFrame,
               defasagem: pd.DataFrame, direcao: int) -> str:
    saidas = tipos[tipos["fonte_saida"] != ""]
    comparaveis = defasagem[defasagem["comparavel"]]
    texto_direcao = {0: "sem direcao dominante: as duas leituras ficam com `pbe_ano`",
                     1: "o PBE vem depois do mercado: a longa entra em `pbe_ano - 1`",
                     -1: "o PBE vem antes do mercado: a curta entra em `pbe_ano + 1`"}[direcao]
    classificadas = dim[dim["vigencia_inicio_rascunho"] != ""]
    modelos = classificadas[fase2.CHAVE].drop_duplicates().shape[0]
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""# Dicionario de dados -- `classificacao.parquet`, `classificacao_propulsao_anual.parquet` e `classificacao_montagem.parquet`

Gerado em {agora} (UTC) por `src/etapa11_classificacao.py`, a partir de
`saidas/classificacao_rascunho.xlsx`. **O rascunho e' a fonte de verdade da
adjudicacao:** uma decisao se escreve nele, e a etapa roda de novo. Ninguem
edita o parquet a' mao.

**Advertencia.** {ADVERTENCIA}

**Serie temporal de propulsao: use `classificacao_propulsao_anual.parquet`.**
`propulsao_na_vigencia` e `eletrificacao_na_vigencia` sao o {AVISO_VIGENCIA}

## `classificacao.parquet`

Uma linha por `(marca, modelo, segmento, vigencia_inicio, vigencia_fim)`:
{len(dim):,} linhas -- {len(classificadas):,} vigencias de {modelos} modelos classificados e
{len(dim) - len(classificadas):,} modelos abaixo do piso de {config.PISO_CLASSIFICACAO:,}
unidades, com atributos vazios. Toda chave do painel tem linha em todo mes com
unidades, e as vigencias de um modelo nao se sobrepoem (validado a cada execucao).
Juncao com o painel: pela chave, com `vigencia_inicio <= mes_ref <= vigencia_fim`.

| coluna | tipo | descricao |
|---|---|---|
| `marca`, `modelo`, `segmento` | texto | chave do painel |
| `vigencia_inicio`, `vigencia_fim` | texto AAAA-MM | meses da vigencia, inclusive |
| `propulsao_na_vigencia` | texto | **{AVISO_VIGENCIA}** Conjunto unido por '+': gasolina, flex, diesel, mhev, hibrido_indefinido, hev, phev, reev, bev. O que o modelo oferecia, nao o que vendeu |
| `eletrificacao_na_vigencia` | texto | **{AVISO_VIGENCIA}** Derivada da propulsao: `total` (so' hev/phev/reev/bev), `parcial` (mistura, ou mhev/hibrido_indefinido), `nenhuma`; mesma procedencia da propulsao |
| `procedencia_propulsao` | texto | ver abaixo |
| `carroceria` | texto | hatch, sedan, suv, picape, minivan, furgao, caminhao_leve, perua, esportivo |
| `procedencia_carroceria` | texto | ver abaixo |
| `origem_producao` | texto | nacional, importado, ambos |
| `procedencia_origem` | texto | ver abaixo |
| `vigencia_ajustada_por` | texto | `regra` (O2: fronteira movida para a data da fonte) ou `humana`; vazio se a vigencia e' a proposta |
| `regras_aplicadas` | texto | ids das regras de adjudicacao que decidiram algo na linha (`config/regras_adjudicacao.csv`) |
| `vigencia_inicio_rascunho` | texto | inicio da vigencia no rascunho, para voltar a' linha de origem; vazio abaixo do piso |

### Procedencia

| valor | significado |
|---|---|
| `humana` | decidida pelo pesquisador |
| `regra_fonte_forte` | decidida ou confirmada por regra com fonte oficial ou especializada (inclusive o valor que o PBE ou fonte forte confirmou sem contestacao) |
| `regra_fonte_fraca` | decidida por regra apoiada em fonte fraca, ou sem evidencia positiva (P2) |
| `proposta` | proposta original, nunca tocada por checagem |
| `pendente` | contestada e ainda nao decidida; o valor exibido e' a proposta original |
| `nao_classificado` | modelo abaixo do piso de volume; atributos vazios |

Fracao do volume do painel, por atributo (juncao de teste, gravada em
`saidas/classificacao_procedencia.csv`):

{_tabela_volume(volume)}

### Limitacoes

- **Conjunto, nao parcela.** A fonte nao separa unidades por versao: um modelo
  `parcial` nao diz quantas unidades foram eletrificadas.
- **`hibrido_indefinido`** marca o modelo que o PBE poe em Hibrido sem que o nome
  da versao ou fonte digam se e' leve ou pleno; conta como `mhev`, e nunca leva a
  `total`.
- **Datas de troca de origem.** A fronteira entre vigencias usa a data de
  lancamento ou chegada ao mercado quando a fonte a da', senao a de producao. Os
  meses entre producao e lancamento sao imprecisos por construcao: num estudo de
  evento, ficam fora da janela.
- **Ausencia no PBE.** {_corte_pbe()}
- **Transicao para o flex** (2003-2006): `gasolina+flex` na vigencia inteira, sem
  data por modelo.

## `classificacao_propulsao_anual.parquet`

Uma linha por `(marca, modelo, segmento, vigencia_inicio, ano)` com unidades no
painel nos meses daquela vigencia naquele ano: {len(anual):,} linhas. Juncao com o
painel: pela chave, pela vigencia (`vigencia_inicio <= mes_ref <= vigencia_fim`) e
pelo ano de `mes_ref`. Construida em `src/comum/propulsao_anual.py` a partir de
`classificacao.parquet`, do casamento PBE->painel (`saidas/pbe_casamento.csv`) e
das fontes datadas de `dados/referencia/propulsao_fontes.csv`. A entrada e a saida
de cada tipo, vigencia a vigencia, nas duas leituras, ficam em
`saidas/classificacao_propulsao_tipos.csv`, com os anos de presenca e de
ausencia que as sustentam.

| coluna | tipo | descricao |
|---|---|---|
| `marca`, `modelo`, `segmento` | texto | chave do painel |
| `vigencia_inicio`, `vigencia_fim` | texto AAAA-MM | a vigencia da classificacao |
| `ano` | inteiro | ano civil |
| `unidades` | inteiro | unidades do painel nos meses da vigencia no ano |
| `propulsao_no_ano` | texto | tipos oferecidos no ano, **leitura longa**: cada tipo dura o maximo que a evidencia permite |
| `eletrificacao_no_ano` | texto | derivada de `propulsao_no_ano` pelas regras de sempre: `hibrido_indefinido` e `mhev` nunca levam a `total` |
| `propulsao_no_ano_curta`, `eletrificacao_no_ano_curta` | texto | o mesmo na **leitura curta**: o minimo que a evidencia permite |
| `fonte_temporal` | texto | de onde vem a entrada dos tipos eletrificados do ano (leitura longa), o mais fraco deles: `vigencia_sem_datacao` < `pbe_ano` < `fonte_datada` < `vigencia` (so' combustao, ou modelo so' eletrificado) |
| `entrada_dos_tipos` | texto | `tipo=ano fonte` de cada tipo do ano (`longa/curta` quando diferem) |
| `saida_dos_tipos` | texto | tipos da vigencia com evidencia de saida: ultimo ano em cada leitura e de onde vem a ausencia (`pbe`, `fonte`) |
| `procedencia_propulsao` | texto | herdada da vigencia |

**Entrada de cada tipo.** Combustao: o inicio da vigencia. Eletrificado: (1) fonte
datada de lancamento, producao ou presenca a' venda -- `plano` nao conta -- que
manda sobre o PBE (`fonte_datada`); (2) senao, o ano da primeira tabela do PBE em
que uma versao daquele tipo aparece (`pbe_ano`), desde que um ano com coluna de
propulsao (2021 em diante), dentro da vigencia e antes dela, mostre o modelo sem o
tipo -- o marcador no nome prova presenca, nao ausencia; (3) senao, o inicio da
vigencia (`vigencia_sem_datacao`). Vigencia so' com tipos eletrificados: o
primeiro a entrar, no inicio dela (`vigencia`).

**Defasagem do PBE**, medida nos tipos com fonte datada e ano de PBE
(`saidas/classificacao_pbe_defasagem.csv`, {len(defasagem)} tipos, {len(comparaveis)}
comparaveis -- fonte de 2021 em diante): {texto_direcao}.

**Saida de cada tipo**, com as mesmas fontes. Presenca: o tipo no PBE do ano, fonte
datada ou o ano de entrada. Ausencia, so' de 2021 em diante: o modelo no PBE do
ano com versao de outro tipo da vigencia e sem o tipo, ou fonte datada de fim de
venda ou de importacao. Modelo ausente do PBE nao informa; tipo que some e volta
e' lacuna. Leitura longa: o tipo fica ate' o ano da primeira ausencia depois da
ultima presenca; curta: ate' o ano da ultima presenca. Sem ausencia, as duas o
mantem ate' o fim da vigencia. Ano em que a leitura curta ficaria sem tipo (lacuna
do PBE entre a saida de um tipo e a entrada do seguinte) leva os tipos da longa.
{len(saidas)} tipos tem evidencia de saida. Cada ano de PBE vale para a vigencia
com mais meses nele.

**Guarda da saida.** Ausencia no PBE nao prova saida no ano em que ha', sem
casamento, versao da mesma marca e do mesmo tipo cujo nome contem o da chave e
sem decisao de casamento em `config/pbe_modelos.csv`
(`saidas/pbe_variantes_sem_evidencia.csv`; {int((tipos["anos_guardados"] != "").sum())}
tipos tiveram ausencia descartada). **Combustao na leitura curta:** sem fonte
datada de fim, a curta segue a longa ate' 2020 -- antes da coluna de propulsao, a
falta de presenca no PBE nao data a saida da combustao.

{_tabela_fonte_temporal(tipos)}

### Uso-teste e banda da eletrificacao

A serie mais obvia que um artigo faria com a classificacao -- participacao de cada
nivel de eletrificacao nas unidades, por ano -- pelo conjunto da vigencia (o uso
errado) e pela tabela anual nas duas leituras, em `saidas/classificacao_uso_teste.csv`.
A banda, em `saidas/eletrificacao_banda.csv` (% das unidades do painel):

- `piso`: `total`;
- `teto`: `total` + `parcial`;
- `teto_sem_mhev`: tira do `parcial` a vigencia-ano cujo unico tipo eletrificado e'
  `mhev` (a definicao da ABVE desde 2025);
- `teto_estrito`: tira a vigencia-ano cujos tipos eletrificados sao so' `mhev` ou
  `hibrido_indefinido`.

{_tabela_banda(banda)}

## `classificacao_montagem.parquet`

Periodos de montagem local, no padrao de vigencia do mapa de grupos: {len(montagem):,}
periodos que cobrem os meses das vigencias de cada modelo, sem sobreposicao.

| coluna | descricao |
|---|---|
| `marca`, `modelo`, `segmento` | chave do painel |
| `vigencia_inicio`, `vigencia_fim` | a vigencia de classificacao a que o periodo pertence |
| `origem_producao` | origem final da vigencia |
| `montagem_inicio`, `montagem_fim` | meses do periodo, inclusive |
| `montagem_local` | `fabricacao`, `ckd`, `skd` (so' no periodo que a fonte declara), `desconhecido` (fora dele), `nao_se_aplica` (vigencia importada), vazio abaixo do piso |
| `procedencia` | `regra_fonte_forte`/`regra_fonte_fraca` pelo tipo da fonte do modo; em `nao_se_aplica`, a da origem; `proposta` em `desconhecido`; `nao_classificado` abaixo do piso |
| `fonte_url`, `tipo_fonte`, `observacao` | a fonte do modo e a leitura dela |

Kit e carro inteiro tem tratamento tributario diferente: para o artigo de tarifa,
o periodo e' a variavel. Fontes em `dados/referencia/montagem_fontes.csv`.
"""


if __name__ == "__main__":
    raise SystemExit(executar())
