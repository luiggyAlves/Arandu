"""
Projeto Arandu — Taxa de bugs válidos, medida por execução.

O Validador (PDF) exige: o bug tem que falhar só onde deveria, não pode
travar, e um conserto pequeno tem que resolver. Os quatro critérios abaixo
são todos medidos com tools.rodar_suite — não por inspeção do código:

  referencia_passa       cod_ref passa em todos os testes
  falha_em_algum_teste   cod_bugado falha em pelo menos um teste
  nao_trava              nenhum resultado de cod_bugado traz erro
                         (exceção ou timeout); a falha é só saída errada
  conserto_pequeno       não medido: None (não entra em valido nem em detalhe)

linhas_alteradas
----------------
Diff linha a linha com difflib.ndiff, depois de descartar linhas em branco
(ou só com espaço). A contagem é a SOMA das linhas adicionadas (prefixo
'+ ') e removidas (prefixo '- '). Uma troca de uma linha conta 2, não 1.
Não usamos o máximo entre adicionadas e removidas. Vale para todos os itens.

conserto_pequeno não é medido (fica None em todos os itens). A referência do
banco é a solução de OUTRO aluno do Refactory, e as variações do Construtor a
herdam; o diff mede a distância entre dois programas, não o tamanho do
conserto (ex.: refactory_q1_567_v2 se conserta com uma linha e o diff dá 9).
linhas_alteradas continua no relatório como informação.
"""

from __future__ import annotations

import difflib
import json
import time

import banco_m2
import config
import tools


def _linhas_uteis(codigo: str) -> list[str]:
    return [ln for ln in (codigo or "").splitlines() if ln.strip()]


def _linhas_alteradas(cod_bugado: str, cod_ref: str) -> int:
    """Soma das linhas não vazias adicionadas e removidas (difflib.ndiff)."""
    adicionadas = 0
    removidas = 0
    for linha in difflib.ndiff(_linhas_uteis(cod_bugado), _linhas_uteis(cod_ref)):
        if linha.startswith("+ "):
            adicionadas += 1
        elif linha.startswith("- "):
            removidas += 1
    return adicionadas + removidas


def _teto_conserto() -> int:
    return int(getattr(config, "MAX_LINHAS_CONSERTO", 5))


def _rodar(codigo: str, testes: list[dict]):
    try:
        return tools.rodar_suite(codigo, testes), None
    except Exception as e:
        return None, e


def _avaliar(bug: dict) -> dict:
    """Avalia um item já no formato do M3 (id, cod_bugado, cod_ref, testes)."""
    testes = bug.get("testes") or []
    total = len(testes)
    n_linhas = _linhas_alteradas(bug.get("cod_bugado") or "", bug.get("cod_ref") or "")
    teto = _teto_conserto()

    ref, erro_ref = _rodar(bug.get("cod_ref") or "", testes)
    bugado, erro_bug = _rodar(bug.get("cod_bugado") or "", testes)

    if ref is None:
        referencia_passa = False
    else:
        referencia_passa = all(r.get("passou") for r in ref)

    if bugado is None:
        # suíte nem rodou: não dá para afirmar falha por saída, e conta como trava
        falhando = total
        falha_em_algum = False
        nao_trava = False
    else:
        falhando = sum(1 for r in bugado if not r.get("passou"))
        falha_em_algum = falhando >= 1
        nao_trava = all(not r.get("erro") for r in bugado)

    origem = bug.get("origem") or ""
    aplica_conserto_pequeno = False
    conserto_pequeno = (n_linhas <= teto) if aplica_conserto_pequeno else None
    criterios = {
        "referencia_passa": referencia_passa,
        "falha_em_algum_teste": falha_em_algum,
        "nao_trava": nao_trava,
        "conserto_pequeno": conserto_pequeno,
    }
    aplicaveis = [v for v in criterios.values() if v is not None]
    valido = all(aplicaveis)

    motivos = []
    if not referencia_passa:
        if erro_ref is not None:
            motivos.append(f"referência não executou ({type(erro_ref).__name__}: {erro_ref})")
        else:
            motivos.append("referência não passa em todos os testes")
    if not falha_em_algum:
        if erro_bug is not None:
            motivos.append(f"código bugado não executou ({type(erro_bug).__name__}: {erro_bug})")
        else:
            motivos.append("código bugado não falha em nenhum teste")
    if not nao_trava:
        if erro_bug is not None:
            motivos.append(f"código bugado trava (suíte não rodou: {type(erro_bug).__name__})")
        else:
            motivos.append("código bugado trava (exceção ou timeout)")
    if conserto_pequeno is False:
        motivos.append(f"conserto grande ({n_linhas} linhas, teto {teto})")

    return {
        "bug_id": bug.get("id") or bug.get("bug_id") or "",
        "origem": origem,
        "valido": valido,
        "criterios": criterios,
        "aplica_conserto_pequeno": aplica_conserto_pequeno,
        "linhas_alteradas": n_linhas,
        "testes_total": total,
        "testes_falhando": falhando,
        "detalhe": "" if valido else "; ".join(motivos),
    }


def _item_variacao(bruto: dict) -> dict:
    item = _avaliar(banco_m2._mapear(bruto))
    return {
        "bug_id": item["bug_id"],
        "origem": item["origem"],
        "aprovado_por_validador_m2": bruto.get("aprovado_por_validador"),
        "motivo_reprovacao": bruto.get("motivo_reprovacao"),
        "valido": item["valido"],
        "criterios": item["criterios"],
        "aplica_conserto_pequeno": item["aplica_conserto_pequeno"],
        "linhas_alteradas": item["linhas_alteradas"],
        "testes_total": item["testes_total"],
        "testes_falhando": item["testes_falhando"],
        "detalhe": item["detalhe"],
    }


def calcular(banco: list[dict], caminho_variacoes: str) -> dict:
    """Mede o banco servido e TODAS as variações geradas (inclusive reprovadas)."""
    itens_banco = [_avaliar(b) for b in banco]
    with open(caminho_variacoes, encoding="utf-8") as f:
        brutos = json.load(f)
    itens_geradas = [_item_variacao(b) for b in brutos]
    return {
        "estado": "pronto",
        "geradas": {
            "total": len(itens_geradas),
            "aprovadas_pelo_validador_m2": sum(
                1 for i in itens_geradas if i["aprovado_por_validador_m2"]
            ),
            "revalidadas_validas": sum(1 for i in itens_geradas if i["valido"]),
            "itens": itens_geradas,
        },
        "banco": {
            "total": len(itens_banco),
            "validos": sum(1 for i in itens_banco if i["valido"]),
            "itens": itens_banco,
        },
        "calculado_em": time.time(),
    }
