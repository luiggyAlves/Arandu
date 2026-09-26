"""
Projeto Arandu — Catálogo mínimo de equívocos (subconjunto inspirado no ProgMiscon
+ extensões locais para erros de lógica que o ProgMiscon não cobre).

Cada equívoco: id, nome legível, a crença errada, e o texto de correção
(usado para ancorar a explicação da dica). Na fase final isto vira o recorte
real do ProgMiscon + rótulos derivados dos dados.
"""

CATALOGO = {
    "CondicaoInvertida": {
        "nome": "Condição invertida",
        "crenca_errada": "acha que a condição seleciona o caso oposto ao que deveria",
        "correcao": "a condição de um if/while decide QUANDO o corpo executa; verifique com um exemplo qual ramo realmente entra.",
    },
    "SemFiltro": {
        "nome": "Esqueceu de filtrar",
        "crenca_errada": "processa todos os elementos, sem aplicar a condição pedida",
        "correcao": "só deve contar/somar os elementos que satisfazem a condição do enunciado.",
    },
    "AcumuladorReiniciado": {
        "nome": "Acumulador reiniciado no laço",
        "crenca_errada": "zera o acumulador dentro do laço, a cada iteração",
        "correcao": "o acumulador deve ser iniciado UMA vez, antes do laço.",
    },
    "LimiteLaco": {
        "nome": "Limite do laço (off-by-one)",
        "crenca_errada": "inclui ou exclui o último elemento por engano no range",
        "correcao": "confira os limites do range: o último índice entra ou não? teste com um caso pequeno.",
    },
    "IfIsLoop": {
        "nome": "if confundido com while",
        "crenca_errada": "acha que o corpo do if repete enquanto a condição for verdadeira",
        "correcao": "o if executa o corpo NO MÁXIMO uma vez; quem repete é o while.",
    },
    "ComparaAtribui": {
        "nome": "= no lugar de ==",
        "crenca_errada": "usa atribuição onde queria comparação (ou vice-versa)",
        "correcao": "'=' atribui um valor; '==' compara dois valores.",
    },
}


def texto_correcao(equivoco_id: str) -> str:
    e = CATALOGO.get(equivoco_id)
    return e["correcao"] if e else ""
