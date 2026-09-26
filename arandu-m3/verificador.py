"""
Projeto Arandu — Verificador (agente crítico / guardrail).

Toda mensagem passa por aqui ANTES de chegar ao aluno. Ele reprova ("barra") em
dois casos:
  (a) a mensagem NÃO está ancorada em execução (afirmou sem provar rodando);
  (b) a mensagem REVELARIA a solução (deixaria copiar e passar).

Versão MVP: regras determinísticas + checagem por execução do caso (b). Pode
ganhar uma camada de LLM depois, mas as regras já cobrem o essencial e são baratas.
"""

from __future__ import annotations
import re
from tools import rodar_suite


def _contem_codigo_corretor(texto: str, cod_ref: str) -> bool:
    """Heurística: a dica traz trechos grandes do código de referência?"""
    linhas_ref = [l.strip() for l in cod_ref.splitlines() if len(l.strip()) > 8]
    achados = sum(1 for l in linhas_ref if l in texto)
    return achados >= 2   # duas linhas ou mais da referência = está entregando


def verificar(envelope: dict, cod_ref: str,
              testes: list[dict] | None = None,
              exigir_ancora: bool = True) -> dict:
    """
    envelope = {texto, nivel, revela_solucao, ancoras:[...]}
    Retorna {aprovado: bool, motivo: str}.

    exigir_ancora=True  -> dicas (afirmam algo sobre execução) PRECISAM de âncora;
    exigir_ancora=False -> cutucões socráticos (perguntas/encorajamento) não afirmam
                           nada sobre a execução, então a checagem de âncora é dispensada.
                           O bloqueio de vazar a solução continua valendo nos dois casos.
    """
    texto = envelope.get("texto", "").strip()

    # (0) mensagem vazia
    if not texto:
        return {"aprovado": False, "motivo": "mensagem vazia"}

    # (a) ancorada em execução? (só para dicas que afirmam algo)
    if exigir_ancora and not envelope.get("ancoras"):
        return {"aprovado": False,
                "motivo": "afirmação sem âncora de execução (nada foi rodado por trás)"}

    # (b1) o próprio agente admitiu revelar a solução
    if envelope.get("revela_solucao"):
        return {"aprovado": False, "motivo": "a mensagem revelaria a solução"}

    # (b2) a dica contém o código de referência (copiar-e-passar)
    if _contem_codigo_corretor(texto, cod_ref):
        return {"aprovado": False, "motivo": "a mensagem contém o código correto"}

    # (b3) checagem forte por execução: se o texto tem um bloco de código Python,
    #      ele passa em todos os testes? se passa, está entregando a solução.
    if testes:
        blocos = re.findall(r"```(?:python)?\n(.*?)```", texto, flags=re.DOTALL)
        for bloco in blocos:
            resultados = rodar_suite(bloco, testes)
            if resultados and all(r["passou"] for r in resultados):
                return {"aprovado": False,
                        "motivo": "o código embutido na dica passa em todos os testes (entrega a solução)"}

    return {"aprovado": True, "motivo": "ok"}
