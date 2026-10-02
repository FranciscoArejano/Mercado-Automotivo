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
- `saidas/classificacao_procedencia.csv` -- fracao do volume do painel em cada
  procedencia, por atributo (juncao de teste);
- `saidas/classificacao_dicionario.md` -- dicionario da dimensao.

Falha (codigo 1, nada gravado) se: uma chave do painel ficar sem linha em algum
mes com unidades, ou vigencias se sobrepuserem; um valor `humana` ou `regra_*`
diferir do rascunho; um modo de montagem com fonte diferir do rascunho; ou uma
decisao humana nao puder ser aplicada (texto livre, `dividir em`, ou atributo
deixado `pendente` numa linha com decisao humana).

Uso:
    python src/etapa11_classificacao.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comum import adjudicacao, config, fase2, log  # noqa: E402

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
    if problemas:
        for problema in problemas[:50]:
            logger.error(problema)
        logger.error("%d problemas: nada gravado", len(problemas))
        return 1

    volume = fase2.volume_por_procedencia(dim, painel)
    config.DIR_PROCESSADO.mkdir(parents=True, exist_ok=True)
    dim.to_parquet(config.CLASSIFICACAO, index=False)
    montagem.to_parquet(config.CLASSIFICACAO_MONTAGEM, index=False)
    volume.to_csv(config.CLASSIFICACAO_PROCEDENCIA, index=False)
    config.CLASSIFICACAO_DICIONARIO.write_text(dicionario(dim, montagem, volume),
                                               encoding="utf-8")
    logger.info("dimensao: %d linhas (%d classificadas, %d abaixo do piso); montagem: %d "
                "periodos", len(dim), int((dim["vigencia_inicio_rascunho"] != "").sum()),
                int((dim["vigencia_inicio_rascunho"] == "").sum()), len(montagem))
    for _, linha in volume[volume["unidades"] > 0].iterrows():
        logger.info("%-10s %-18s %5.2f%%", linha["atributo"], linha["procedencia"],
                    linha["pct_do_volume"])
    logger.info("gravado %s e %s", log.caminho_relativo(config.CLASSIFICACAO),
                log.caminho_relativo(config.CLASSIFICACAO_MONTAGEM))
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


def dicionario(dim: pd.DataFrame, montagem: pd.DataFrame, volume: pd.DataFrame) -> str:
    classificadas = dim[dim["vigencia_inicio_rascunho"] != ""]
    modelos = classificadas[fase2.CHAVE].drop_duplicates().shape[0]
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""# Dicionario de dados -- `classificacao.parquet` e `classificacao_montagem.parquet`

Gerado em {agora} (UTC) por `src/etapa11_classificacao.py`, a partir de
`saidas/classificacao_rascunho.xlsx`. **O rascunho e' a fonte de verdade da
adjudicacao:** uma decisao se escreve nele, e a etapa roda de novo. Ninguem
edita o parquet a' mao.

**Advertencia.** {ADVERTENCIA}

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
| `propulsao_oferecida` | texto | conjunto unido por '+': gasolina, flex, diesel, mhev, hibrido_indefinido, hev, phev, reev, bev. O que o modelo oferecia, nao o que vendeu |
| `eletrificacao` | texto | derivada da propulsao: `total` (so' hev/phev/reev/bev), `parcial` (mistura, ou mhev/hibrido_indefinido), `nenhuma`; mesma procedencia da propulsao |
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
