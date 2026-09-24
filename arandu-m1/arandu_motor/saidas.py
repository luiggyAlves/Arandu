"""Comparação de saídas, com as mesmas regras em todo o motor."""

import ast


def normalizar_saida(texto: str) -> str:
    """Ignora espaços no fim das linhas e linhas vazias no final, como os juízes."""
    linhas = [linha.rstrip() for linha in texto.replace("\r\n", "\n").split("\n")]
    while linhas and not linhas[-1]:
        linhas.pop()
    return "\n".join(linhas)


def saidas_equivalentes(obtida: str, esperada: str) -> bool:
    if normalizar_saida(obtida) == normalizar_saida(esperada):
        return True
    # Regra do Refactory: dicionários e conjuntos podem sair em outra ordem.
    if "{" in obtida and "{" in esperada:
        try:
            return ast.literal_eval(obtida.strip()) == ast.literal_eval(esperada.strip())
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            return False
    return False
