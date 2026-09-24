"""
Projeto Arandu — Treinador (o cérebro do M3).

Agente ReAct: raciocina, age (ferramentas), observa e decide. Decisões são do
Treinador; execução é das ferramentas (M1); a verdade vem da execução.

Suporta dois modos de estímulo:
  - stdin  (bugs estilo juiz online): a entrada é texto de stdin;
  - chamada (bugs estilo função/Refactory do M2): a entrada é uma chamada de
    função pronta, ex.: "search(5, (1, 5, 10))".
"""

from __future__ import annotations

import tools
import catalogo
import config
from verificador import verificar
from llm import LLM
from log import get_logger

_log = get_logger("treinador")


# Baralho de ações que o AGENTE pode escolher a cada momento.
# Ele decide sozinho qual usar (ou nenhuma = OBSERVAR) com base no contexto.
ACOES = {
    "OBSERVAR":       "não fazer nada agora; seguir só observando (quase sempre a escolha certa)",
    "ENCORAJAR":      "uma frase curta de incentivo, sem conteúdo técnico",
    "PERGUNTAR":      "uma pergunta socrática curta que faça o aluno pensar (não entrega resposta)",
    "SUGERIR_TESTE":  "sugerir um caso/entrada específico para o aluno testar sozinho",
    "MOSTRAR_VALORES":"sugerir que o aluno abra o visualizador de variáveis (o trace)",
    "DAR_DICA":       "acionar a investigação completa e dar uma dica ancorada em execução (só quando parecer travado de verdade)",
    "AVANCAR":        "sinalizar que pode seguir / parabenizar pelo progresso",
}


class Treinador:
    def __init__(self, llm: LLM):
        self.llm = llm
        self.log_sistema = []   # degradações (falha de ferramenta) — NÃO vai pro modelo do aluno

    # ------------------------------------------------------------------ #
    # Decisão AUTÔNOMA de intervir (o coração do "ser agêntico").
    # Recebe um retrato da situação (modelo do aluno + contexto da sessão) e
    # devolve a ação que o AGENTE escolheu, com o motivo (para a tela ao vivo).
    # Não há regra fixa aqui: quem decide é o LLM, olhando o retrato.
    # ------------------------------------------------------------------ #
    def decidir_intervencao(self, retrato: dict) -> dict:
        dados = dict(retrato)
        dados["acoes_possiveis"] = ACOES
        try:
            d = self.llm.chamar("decidir_acao", dados) or {}
        except Exception as e:
            # rede/LLM falhou: não travar nem derrubar o evento — segue observando
            _log.warning("decidir_acao falhou (%s) — assumindo OBSERVAR", e)
            return {"acao": "OBSERVAR", "motivo": "", "confianca": None, "mensagem": ""}
        acao = str(d.get("acao", "OBSERVAR")).upper().strip()
        if acao not in ACOES:
            acao = "OBSERVAR"
        dec = {"acao": acao,
               "motivo": (d.get("motivo") or "").strip(),
               "confianca": d.get("confianca"),
               "mensagem": (d.get("mensagem") or "").strip()}
        _log.info("decisão do agente: %s (conf=%s) — %s", acao, dec["confianca"], dec["motivo"])
        return dec

    # ------------------------------------------------------------------ #
    def escolher_bug(self, modelo, banco: list[dict]) -> dict | None:
        candidatos = [b for b in banco if not modelo.ja_resolveu(b["id"])]
        if not candidatos:
            return None
        # dificuldade PRIMEIRO (mais simples antes), domínio como desempate:
        # garante que os desafios comecem simples e fiquem mais complexos aos poucos.
        candidatos.sort(key=lambda b: (b.get("dificuldade", 3), modelo.dominio(b["equivoco"])))
        return candidatos[0]

    def _equivocos(self):
        return list(catalogo.CATALOGO.keys())

    def _analisar(self, cod_a: str, cod_ref: str, estimulo: str, chamada: bool) -> dict:
        """Chama a ferramenta certa conforme o modo (chamada de função ou stdin)."""
        if chamada:
            return tools.analisar(cod_a, cod_ref, chamada=estimulo)
        return tools.analisar(cod_a, cod_ref, entrada=estimulo)

    def _ancora(self, r, modo=None):
        a = {"entrada": r["entrada"], "divergiu": r["divergiu"],
             "saida_aluno": r["saida_aluno"].strip(), "saida_ref": r["saida_ref"].strip()}
        if modo:
            a["modo"] = modo
        return a

    # ------------------------------------------------------------------ #
    # Laço investigativo (ReAct) — multi-candidato + realimentação
    # ------------------------------------------------------------------ #
    def investigar(self, cod_aluno: str, cod_ref: str, entrada_falha: str,
                   chamada: bool = False, assinatura: str = "") -> dict:
        modo = "chamada" if chamada else "stdin"
        log = []
        hipoteses = self.llm.chamar("gerar_hipoteses", {
            "cod_aluno": cod_aluno, "cod_ref": cod_ref,
            "equivocos_possiveis": self._equivocos(),
        }).get("hipoteses", [])
        log.append(("gerar_hipoteses", [h.get("id") for h in hipoteses]))
        _log.info("hipóteses iniciais: %s", [h.get("id") for h in hipoteses])

        ancoras: list[dict] = []
        tentadas: list[str] = []
        passos = 0
        regeneracoes = 0

        while len(hipoteses) > 1 and passos < config.MAX_PASSOS_REACT:
            passos += 1
            proj = self.llm.chamar("projetar_entrada", {
                "hipoteses": hipoteses, "cod_aluno": cod_aluno, "cod_ref": cod_ref,
                "entradas_ja_tentadas": tentadas, "modo": modo, "assinatura": assinatura})
            candidatos = proj.get("entradas") or ([proj["entrada"]] if proj.get("entrada") else [])
            candidatos = [c for c in candidatos if c not in tentadas][:4]

            if not candidatos:
                if regeneracoes < config.MAX_REGENERACOES_HIPOTESE:
                    regeneracoes += 1
                    hipoteses = self.llm.chamar("gerar_hipoteses", {
                        "cod_aluno": cod_aluno, "cod_ref": cod_ref,
                        "equivocos_possiveis": self._equivocos()}).get("hipoteses", hipoteses)
                    log.append(("regenerar_hipoteses", regeneracoes))
                    continue
                break

            resultado_div = None
            for estimulo in candidatos:
                tentadas.append(estimulo)
                r = self._analisar(cod_aluno, cod_ref, estimulo, chamada)
                ancoras.append(self._ancora(r))
                log.append(("analisar", estimulo, f"divergiu={r['divergiu']}"))
                _log.info("analisar estimulo=%r divergiu=%s (aluno=%r ref=%r)",
                          estimulo, r["divergiu"], r["saida_aluno"].strip(), r["saida_ref"].strip())
                if r["divergiu"]:
                    resultado_div = r
                    break

            if resultado_div is None:
                log.append(("nenhum_candidato_separou", candidatos))
                continue

            poda = self.llm.chamar("podar", {
                "hipoteses": hipoteses, "resultado": tools.resumo_analise(resultado_div)})
            sobrev = set(poda.get("sobreviventes", []))
            novas = [h for h in hipoteses if h.get("id") in sobrev]
            log.append(("podar", list(sobrev)))
            _log.info("podar -> sobreviventes=%s", list(sobrev))

            if not novas:
                if regeneracoes < config.MAX_REGENERACOES_HIPOTESE:
                    regeneracoes += 1
                    hipoteses = self.llm.chamar("gerar_hipoteses", {
                        "cod_aluno": cod_aluno, "cod_ref": cod_ref,
                        "equivocos_possiveis": self._equivocos()}).get("hipoteses", [])
                    log.append(("regenerar_hipoteses", regeneracoes))
                    continue
                break
            hipoteses = novas

        conclusivo = len(hipoteses) == 1
        if not conclusivo:
            r = self._analisar(cod_aluno, cod_ref, entrada_falha, chamada)
            ancoras.append(self._ancora(r, modo="direto"))
            log.append(("fallback_direto", entrada_falha))
            _log.info("fallback direto com estimulo=%r", entrada_falha)

        eq = hipoteses[0] if hipoteses else None
        _log.info("conclusivo=%s equivoco=%s", conclusivo, eq.get("equivoco") if eq else None)
        return {"equivoco": eq, "ancoras": ancoras, "conclusivo": conclusivo, "log": log}

    # ------------------------------------------------------------------ #
    def produzir_dica(self, equivoco: dict | None, ancoras: list[dict], nivel: int) -> dict:
        correcao = catalogo.texto_correcao(equivoco["equivoco"]) if equivoco else ""
        resp = self.llm.chamar("redigir_dica", {
            "equivoco": equivoco, "ancoras": ancoras, "nivel": nivel, "correcao": correcao})
        return {
            "texto": resp.get("texto", ""),
            "nivel": resp.get("nivel", nivel),
            "revela_solucao": resp.get("revela_solucao", False),
            "ancoras": ancoras,
        }

    # ------------------------------------------------------------------ #
    def intervir(self, cod_aluno: str, cod_ref: str, entrada_falha: str,
                 testes: list[dict] | None = None, nivel_inicial: int = 3,
                 chamada: bool = False, assinatura: str = "") -> dict:
        inv = self.investigar(cod_aluno, cod_ref, entrada_falha, chamada, assinatura)
        nivel = nivel_inicial
        rejeicoes = 0
        while True:
            envelope = self.produzir_dica(inv["equivoco"], inv["ancoras"], nivel)
            veredito = verificar(envelope, cod_ref, testes)
            _log.info("dica nivel=%s veredito=%s", nivel, veredito)
            if veredito["aprovado"]:
                return {"envelope": envelope, "veredito": veredito,
                        "investigacao": inv, "rejeicoes": rejeicoes}
            rejeicoes += 1
            if rejeicoes >= config.MAX_REJEICOES_VERIFICADOR:
                seguro = {"texto": ("Qual a sua hipótese sobre o erro? Que entrada você "
                                    "poderia rodar para testá-la?"),
                          "nivel": config.NIVEL_MIN, "revela_solucao": False,
                          "ancoras": inv["ancoras"]}
                _log.info("rebaixado ao nível seguro após %d rejeições", rejeicoes)
                return {"envelope": seguro, "veredito": verificar(seguro, cod_ref, testes),
                        "investigacao": inv, "rejeicoes": rejeicoes, "rebaixado": True}
            nivel = max(config.NIVEL_MIN, nivel - 1)
