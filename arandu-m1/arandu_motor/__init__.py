"""Arandu -- M1: motor de execução e ferramentas (Contrato A).

Uso direto em Python (M2, M3):

    from arandu_motor import executar, trace, rodar_suite, diff_comportamental

Servidor MCP (agentes) e API REST (front): python -m arandu_motor --help
Configuração (limites, servidor, fronteiras entre módulos): m1.config
"""

from .ferramentas import diff_comportamental, executar, rodar_suite, trace
from .sandbox import Limites

__version__ = "0.2.0"

__all__ = ["executar", "trace", "rodar_suite", "diff_comportamental", "Limites"]
