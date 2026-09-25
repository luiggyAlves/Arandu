"""
Projeto Arandu — Parâmetros e tetos do M3.
Tudo aqui é fácil de ajustar sem mexer na lógica.
"""

# --- Tetos do laço investigativo (protegem custo e travam loops) ---
MAX_PASSOS_REACT = 6            # passos raciocina->age->observa por intervenção
MAX_REGENERACOES_HIPOTESE = 2   # regenerações antes de cair pro modo direto
MAX_REJEICOES_VERIFICADOR = 3   # reprovações seguidas antes de rebaixar
MAX_CHAMADAS_LLM_SESSAO = 150   # teto global por sessão (protege a conta)

# --- Sessão ---
TIMEOUT_INATIVIDADE_S = 600     # 10 min sem interação -> encerra gentil

# --- Monitor agêntico (intervenção PROATIVA) ---
# O agente decide SOZINHO se/quando/como intervir a cada ação do aluno.
# Estes valores NÃO decidem quando ajudar (isso é do agente) — são só
# guarda-corpos de segurança para ele não atrapalhar (evitar spam).
COOLDOWN_INTERVENCAO_S = 15     # tempo mínimo entre duas intervenções proativas
MAX_INTERVENCOES_PROATIVAS = 8  # teto de intervenções proativas por sessão
MAX_EVENTOS_PAINEL = 200        # trunca o histórico do painel (protege memória)

# --- Escada de dica (níveis) ---
NIVEL_MIN = 1   # pergunta metacognitiva
NIVEL_MAX = 5   # nomear o equívoco (nunca a correção = nível "proibido")

# --- LLM ---
MODELO_LLM = "gpt-4o-mini"

# --- Ferramentas ---
MAX_PASSOS_TRACE = 200          # trunca traces longos (protege contexto/custo)

# --- Validação do banco ---
MAX_LINHAS_CONSERTO = 5
