"""
Projeto Arandu — logging central (observabilidade / LLMOps).

Padrão: escreve NO TERMINAL e num ARQUIVO (logs/arandu.log) ao mesmo tempo.
- terminal: acompanhar ao vivo durante o desenvolvimento/demo;
- arquivo: auditar depois (cada decisão do agente, cada chamada de LLM, custo).

Uso:
    from log import get_logger
    log = get_logger("treinador")
    log.info("investigando bug %s", bug_id)
"""

from __future__ import annotations
import logging
import os
import sys

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
_configurado = False


def _configurar():
    global _configurado
    if _configurado:
        return
    os.makedirs(_LOG_DIR, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
    raiz = logging.getLogger("arandu")
    raiz.setLevel(logging.INFO)
    raiz.propagate = False
    if not raiz.handlers:
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(fmt)
        raiz.addHandler(ch)
        fh = logging.FileHandler(os.path.join(_LOG_DIR, "arandu.log"), encoding="utf-8")
        fh.setFormatter(fmt)
        raiz.addHandler(fh)
    _configurado = True


def get_logger(nome: str = "") -> logging.Logger:
    _configurar()
    return logging.getLogger("arandu." + nome if nome else "arandu")
