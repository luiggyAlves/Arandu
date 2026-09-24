"""
Projeto Arandu — Modelo do Aluno (Contrato D).

Guarda o retrato de cada aluno em quatro dimensões + histórico:
  1. Domínio conceitual por equívoco  (estilo BKT)
  2. Habilidade de depuração          (como ele depura)
  3. Sinais da interface              (métricas ricas que a interface captura)
  4. Qualidade da explicação          (sinal fraco, via rubrica de LLM)

Regra de ouro: só EVIDÊNCIA LIMPA atualiza o modelo. Estratégias adotadas por
falha de ferramenta (degradação do sistema) NÃO entram aqui.
Persistência: um JSON por id_aluno (pseudônimo, sem dado pessoal — LGPD).
"""

from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass, field, asdict

PASTA_DADOS = os.path.join(os.path.dirname(__file__), "dados_alunos")


def _bkt_update(p: float, acertou: bool,
                p_aprender=0.30, p_slip=0.10, p_guess=0.20) -> float:
    """Atualização Bayesian Knowledge Tracing (simplificada)."""
    if acertou:
        num = p * (1 - p_slip)
        den = num + (1 - p) * p_guess
    else:
        num = p * p_slip
        den = num + (1 - p) * (1 - p_guess)
    p_post = num / den if den > 0 else p
    return round(p_post + (1 - p_post) * p_aprender, 4)   # + transição de aprendizado


def _nudge(v: float, positivo: bool, taxa=0.2) -> float:
    """Empurra um sinal 0..1 para cima (positivo) ou para baixo (negativo)."""
    return round(v + taxa * (1 - v), 4) if positivo else round(v * (1 - taxa), 4)


@dataclass
class ModeloAluno:
    id_aluno: str

    # 1. domínio conceitual: equivoco_id -> probabilidade de domínio (0..1)
    dominio_por_equivoco: dict = field(default_factory=dict)

    # 2. habilidade de depuração (0..1)
    depuracao: dict = field(default_factory=lambda: {
        "forma_hipotese": 0.5,
        "testa_entrada_discriminante": 0.5,
        "le_variaveis": 0.5,
        "localiza_antes_de_editar": 0.5,
    })

    # 3. sinais captados pela interface (agregados)
    sinais_interface: dict = field(default_factory=lambda: {
        "num_execucoes": 0,
        "num_execucoes_proprias_discriminantes": 0,  # rodou sozinho uma entrada que separa -> OURO
        "usou_trace": 0,
        "tempo_ate_primeira_execucao_s": None,
        "churn_edicao": 0,             # quanto apagou/reescreveu
        "colagens_externas": 0,        # possível cópia de fora
        "pausas_longas": 0,            # possível travamento/frustração
        "acertou_local_antes_de_rodar": 0,
    })

    # 4. qualidade da explicação (0..1, sinal fraco)
    explicacao_qualidade: float = 0.0

    # histórico e controle de repetição
    historico: list = field(default_factory=list)   # [{bug_id, equivoco, resultado, quando}]
    bugs_resolvidos: list = field(default_factory=list)  # ids de bug já resolvidos

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def dominio(self, equivoco_id: str) -> float:
        return self.dominio_por_equivoco.get(equivoco_id, 0.3)  # prior baixo

    def ja_resolveu(self, bug_id: str) -> bool:
        return bug_id in self.bugs_resolvidos

    def equivocos_fracos(self, limite=0.6) -> list[str]:
        """Equívocos com domínio abaixo do limite (candidatos a treinar)."""
        return [e for e, p in self.dominio_por_equivoco.items() if p < limite]

    # ------------------------------------------------------------------ #
    # Atualizações (só com evidência limpa!)
    # ------------------------------------------------------------------ #
    def registrar_conceitual(self, equivoco_id: str, acertou: bool,
                             evidencia_limpa: bool = True):
        if not evidencia_limpa:
            return
        p = self.dominio_por_equivoco.get(equivoco_id, 0.3)
        self.dominio_por_equivoco[equivoco_id] = _bkt_update(p, acertou)

    def registrar_depuracao(self, sinais: dict, evidencia_limpa: bool = True):
        """sinais: {chave_da_depuracao: bool}. Ex.: {'testa_entrada_discriminante': True}"""
        if not evidencia_limpa:
            return
        for chave, positivo in sinais.items():
            if chave in self.depuracao:
                self.depuracao[chave] = _nudge(self.depuracao[chave], positivo)

    def registrar_sinais_interface(self, eventos: dict):
        """Acumula métricas cruas vindas da interface (M4)."""
        for chave, valor in eventos.items():
            # tempo até a 1ª execução: grava só a primeira vez
            if chave == "tempo_ate_primeira_execucao_s":
                if self.sinais_interface.get(chave) is None:
                    self.sinais_interface[chave] = valor
                continue
            # demais: contadores que somam
            if self.sinais_interface.get(chave) is None:
                self.sinais_interface[chave] = 0
            self.sinais_interface[chave] += int(valor) if isinstance(valor, bool) else valor

    def registrar_explicacao(self, qualidade_0a1):
        try:
            self.explicacao_qualidade = round(float(qualidade_0a1), 4)
        except (TypeError, ValueError):
            self.explicacao_qualidade = 0.0

    def registrar_resultado_bug(self, bug_id: str, equivoco_id: str, resolvido: bool):
        self.historico.append({
            "bug_id": bug_id, "equivoco": equivoco_id,
            "resultado": "resolvido" if resolvido else "abandonado",
            "quando": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        if resolvido and bug_id not in self.bugs_resolvidos:
            self.bugs_resolvidos.append(bug_id)

    # ------------------------------------------------------------------ #
    # Persistência (um JSON por aluno)
    # ------------------------------------------------------------------ #
    def salvar(self, pasta: str = PASTA_DADOS):
        os.makedirs(pasta, exist_ok=True)
        caminho = os.path.join(pasta, f"{self.id_aluno}.json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def carregar(cls, id_aluno: str, pasta: str = PASTA_DADOS) -> "ModeloAluno":
        caminho = os.path.join(pasta, f"{id_aluno}.json")
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                return cls(**json.load(f))
        return cls(id_aluno=id_aluno)   # aluno novo
