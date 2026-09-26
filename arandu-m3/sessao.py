"""
Projeto Arandu — Motor da Sessão (M3).

É o "orquestrador" da Fase B: uma máquina de estados que recebe EVENTOS do aluno
(vindos da interface do M4) e coordena Treinador, Verificador, ferramentas e
modelo do aluno. O motor NÃO pensa (isso é do Treinador) e NÃO desenha tela
(isso é do M4) — ele liga as peças na ordem certa e garante as regras
(ex.: toda dica passou pelo Verificador; toda correção passa por avaliação).

Fronteira com o M4:
  interface  --evento-->  sessao.processar_evento(evento)  --resposta-->  interface

Eventos: rodou_entrada | pediu_dica | submeteu_correcao | explicou | inativo | sair
"""

from __future__ import annotations

import time

import tools
import catalogo
import config
import registro
from treinador import Treinador
from modelo_aluno import ModeloAluno
from verificador import verificar
from llm import ContadorLLM
from log import get_logger

_log = get_logger("sessao")


# estados
ESCOLHENDO_BUG = "escolhendo_bug"
ALUNO_TRABALHANDO = "aluno_trabalhando"
AGUARDANDO_EXPLICACAO = "aguardando_explicacao"
ENCERRADA = "encerrada"

# Mesmo texto socrático usado quando o Verificador esgota as rejeições.
_TEXTO_DICA_SEGURA = ("Qual a sua hipótese sobre o erro? Que entrada você "
                      "poderia rodar para testá-la?")


def _hips_evento(extra: dict) -> list[dict]:
    """Hipóteses do log da investigação, no formato do painel."""
    saida = []
    for h in extra.get("hipoteses") or []:
        if not isinstance(h, dict):
            continue
        eq = h.get("equivoco")
        saida.append({
            "id": h.get("id"),
            "equivoco": eq,
            "rotulo": (catalogo.CATALOGO.get(eq) or {}).get("nome"),
            "descricao": h.get("descricao"),
        })
    return saida


def _experimento_evento(passo, extra: dict) -> dict:
    anc = extra.get("ancora") if isinstance(extra.get("ancora"), dict) else {}
    return {
        "entrada": anc.get("entrada", passo[1] if len(passo) > 1 else None),
        "saida_aluno": anc.get("saida_aluno"),
        "saida_ref": anc.get("saida_ref"),
        "divergiu": anc.get("divergiu"),
    }


class Sessao:
    def __init__(self, id_aluno: str, banco: list[dict], treinador: Treinador,
                 carregar_modelo: bool = True, nome_llm: str = ""):
        # carregar_modelo=False começa um aluno do zero (útil para demo/testes)
        self.modelo = ModeloAluno.carregar(id_aluno) if carregar_modelo else ModeloAluno(id_aluno=id_aluno)
        self.banco = banco
        self.treinador = treinador
        # cada sessão conta o próprio custo, mesmo compartilhando o LLM interno
        if not isinstance(self.treinador.llm, ContadorLLM):
            self.treinador.llm = ContadorLLM(self.treinador.llm)
        self.registro = registro.RegistroSessao(id_aluno, nome_llm)
        self.estado = ESCOLHENDO_BUG
        self.bug = None
        self.cod_atual = ""          # código que o aluno tem agora (começa bugado)
        self.tentativas = 0
        self.usou_dica = False
        self.chamada = False         # bug estilo função (Refactory/M2)? senão, stdin
        self.assinatura = ""         # 'def f(...)' — contexto para o LLM em bugs de função

        # --- estado do MONITOR agêntico (decisão proativa de intervir) ---
        self.painel = []                  # stream do "raciocínio do agente" (para a tela ao vivo)
        self.historico = []               # últimas ações do aluno (contexto p/ a decisão)
        self.ts_inicio_bug = time.time()  # quando o aluno começou o bug atual
        self.ts_ultima_intervencao = 0.0  # cooldown entre intervenções proativas
        self.n_intervencoes = 0           # quantas vezes o agente já interveio sozinho
        self.ultima_entrada = None        # última entrada rodada (para notar repetição)
        self.cod_ultima_exec = None       # código na última execução (para notar 'mudou?')
        # --- sinais de PROGRESSO por bug (matéria-prima honesta da decisão) ---
        self.execucoes_bug = 0            # quantas vezes rodou neste bug
        self.entradas_testadas = []       # todas as entradas rodadas neste bug (p/ variedade)
        self.repeticoes_seguidas = 0      # quantas vezes seguidas repetiu a MESMA entrada
        self.achou_discriminante = False  # já rodou uma entrada que EXPÕE o erro?
        self.editou_codigo = False        # já mexeu no editor (não só na entrada)?
        self.usou_trace_bug = 0           # abriu o "ver variáveis" neste bug?
        self.colou_codigo_bug = 0         # colou código de fora neste bug?
        self.ja_intervim_bug = False      # o agente já cutucou neste bug?
        self.ultima_acao_agente = None    # {acao, ha_s} da última intervenção proativa

    # ------------------------------------------------------------------ #
    def iniciar(self) -> dict:
        return self._proximo_bug()

    def _proximo_bug(self) -> dict:
        bug = self.treinador.escolher_bug(self.modelo, self.banco)
        if bug is None:
            return self._encerrar("resolveu todos os bugs disponíveis")
        self.bug = bug
        self.cod_atual = bug["cod_bugado"]
        self.tentativas = 0
        self.usou_dica = False
        self.chamada = (bug.get("modo") == "chamada")
        self.assinatura = bug.get("assinatura", "")
        self.estado = ALUNO_TRABALHANDO
        # reinicia o contexto do monitor para o novo bug
        self.ts_inicio_bug = time.time()
        self.ultima_entrada = None
        self.cod_ultima_exec = None
        self.historico = []
        self.execucoes_bug = 0
        self.entradas_testadas = []
        self.repeticoes_seguidas = 0
        self.achou_discriminante = False
        self.editou_codigo = False
        self.usou_trace_bug = 0
        self.colou_codigo_bug = 0
        self.ja_intervim_bug = False
        self.ultima_acao_agente = None
        self._painel("📘", f"novo desafio ({bug.get('equivoco', '?')}) — observando o aluno")
        _log.info("novo bug: %s (equívoco=%s, modo=%s)", bug["id"], bug["equivoco"], bug.get("modo", "stdin"))
        self.registro.novo_desafio(bug)
        return {"resposta": "novo_bug",
                "bug": {"id": bug["id"], "codigo": bug["cod_bugado"], "enunciado": bug.get("enunciado", ""),
                        "modo": bug.get("modo", "stdin"), "assinatura": bug.get("assinatura", ""),
                        "exemplo_entrada": bug.get("exemplo_entrada", "")},
                "estado": self.estado, "encerrada": False}

    def _encerrar(self, motivo: str) -> dict:
        self.estado = ENCERRADA
        self.modelo.salvar()
        self.registro.encerrar(motivo)
        self._salvar_registro()
        return {"resposta": "encerrada", "motivo": motivo,
                "estado": self.estado, "encerrada": True}

    # ------------------------------------------------------------------ #
    # Porta única que a interface (M4) chama
    # ------------------------------------------------------------------ #
    def processar_evento(self, evento: dict) -> dict:
        tipo = evento.get("tipo")
        dados = evento.get("dados", {})

        if self.estado == ENCERRADA:
            return {"resposta": "sessao_ja_encerrada", "estado": self.estado, "encerrada": True}

        # mantém o código atual em sincronia com o editor: qualquer evento pode trazê-lo
        if isinstance(dados, dict) and dados.get("codigo") is not None and self.estado == ALUNO_TRABALHANDO:
            self.cod_atual = dados["codigo"]

        resp = self._dispatch(tipo, dados)
        # persiste o modelo do aluno A CADA evento (não só no fim da sessão),
        # para o que está na tela refletir no disco mesmo sem encerrar
        if self.estado != ENCERRADA:
            try:
                self.modelo.salvar()
            except Exception:
                pass
        try:
            self._salvar_registro()
        except Exception:
            pass
        return resp

    def _dispatch(self, tipo, dados):
        if tipo == "sair":
            return self._encerrar("aluno pediu para sair")
        if tipo == "inativo":
            return self._encerrar("inatividade")
        if tipo == "rodou_entrada":
            return self._on_rodou_entrada(dados)
        if tipo == "pediu_dica":
            return self._on_pediu_dica()
        if tipo == "submeteu_correcao":
            return self._on_submeteu(dados)
        if tipo == "explicou" and self.estado == AGUARDANDO_EXPLICACAO:
            return self._on_explicou(dados)
        if tipo == "respondeu_pergunta":
            return self._on_respondeu(dados)
        if tipo == "ver_trace":
            return self._on_ver_trace(dados)
        if tipo == "sinais":
            dados = dados or {}
            texto = (dados.get("texto") or "").strip()
            # 'texto' é metadado (string), não um contador — separa dos sinais numéricos
            metrics = {k: v for k, v in dados.items() if k != "texto"}
            # colar código de fora é sinal pedagógico forte (possível cópia). MAS
            # colar algo que já está DENTRO do exercício (o próprio código/enunciado)
            # não é cópia externa — não conta e não dispara a reação.
            if metrics.get("colagens_externas"):
                # comparação IGNORANDO espaços/indentação, contra tudo que a própria
                # ferramenta já mostrou (código, enunciado, assinatura). Assim, colar um
                # trecho do exercício não é confundido com cópia externa.
                def _norm(s):
                    return "".join((s or "").split())
                alvo = _norm(texto)
                refs = [self.cod_atual]
                if self.bug:
                    refs += [self.bug.get("cod_bugado"), self.bug.get("cod_ref"),
                             self.bug.get("enunciado"), self.bug.get("assinatura"),
                             self.bug.get("exemplo_entrada")]
                interno = bool(alvo) and any(alvo in _norm(r) for r in refs)
                if interno:
                    metrics.pop("colagens_externas", None)   # não conta como cópia
                    self.modelo.registrar_sinais_interface(metrics)
                    self._hist("colou um trecho do próprio exercício (interno)")
                    return {"resposta": "sinais_ok", "estado": self.estado, "encerrada": False}
                self.modelo.registrar_sinais_interface(metrics)
                self.colou_codigo_bug += 1
                self.registro.colou_codigo()
                self._hist("colou um código de fora no editor")
                resp = {"resposta": "sinais_ok", "estado": self.estado, "encerrada": False}
                interv = self._monitorar({"tipo": "colou_codigo_externo"})
                if interv:
                    resp["intervencao"] = interv
                return resp
            self.modelo.registrar_sinais_interface(metrics)
            return {"resposta": "sinais_ok", "estado": self.estado, "encerrada": False}
        return {"resposta": "evento_ignorado", "tipo": tipo, "estado": self.estado, "encerrada": False}

    def _on_ver_trace(self, dados: dict) -> dict:
        """Aluno abriu o visualizador de variáveis (trace) — sinal de boa depuração."""
        entrada = dados.get("entrada", "")
        r = tools.trace(self.cod_atual, chamada=entrada) if self.chamada else tools.trace(self.cod_atual, entrada)
        self.modelo.registrar_sinais_interface({"usou_trace": 1})
        self.modelo.registrar_depuracao({"le_variaveis": True})
        self.usou_trace_bug += 1
        self.registro.ver_trace()
        self._hist("abriu o visualizador de variáveis (trace)")
        self._painel("📗", "aluno abriu as variáveis — boa prática de depuração", {"tipo": "aluno"})
        # NÃO aciona o monitor aqui: abrir as variáveis é o aluno fazendo a coisa certa;
        # interromper com "sugira um teste" seria contraproducente. Só observamos.
        return {"resposta": "trace", "passos": r.get("passos", []),
                "saida": r.get("saida", ""), "erro": r.get("erro"),
                "estado": self.estado, "encerrada": False}

    def custo(self) -> dict:
        """Chamadas e tokens desta sessão (sem valor em dinheiro)."""
        return self.treinador.llm.resumo()

    def _salvar_registro(self) -> None:
        self.registro.salvar(
            self.custo(),
            self.modelo.dominio_por_equivoco,
            self.modelo.depuracao,
        )

    def resumo_modelo(self) -> dict:
        """Snapshot do modelo do aluno (para o painel de sinais da interface)."""
        m = self.modelo
        return {"id_aluno": m.id_aluno, "dominio_por_equivoco": m.dominio_por_equivoco,
                "depuracao": m.depuracao, "sinais_interface": m.sinais_interface,
                "bugs_resolvidos": m.bugs_resolvidos,
                "explicacao_qualidade": m.explicacao_qualidade}

    # ================================================================== #
    # MONITOR AGÊNTICO — o agente decide SOZINHO se/quando/como intervir.
    # A cada ação relevante do aluno chamamos _monitorar(...), que monta um
    # retrato da situação, pergunta ao Treinador o que fazer, aplica os
    # guarda-corpos (segurança) e registra tudo no painel (tela ao vivo).
    # ================================================================== #
    def _painel(self, icone: str, texto: str, extra: dict | None = None) -> None:
        ev = {"ts": time.time(), "icone": icone, "texto": texto}
        if extra:
            ev.update(extra)
        self.painel.append(ev)
        if len(self.painel) > config.MAX_EVENTOS_PAINEL:
            self.painel = self.painel[-config.MAX_EVENTOS_PAINEL:]

    def _hist(self, texto: str) -> None:
        self.historico.append(texto)
        self.historico = self.historico[-8:]

    def snapshot_painel(self) -> dict:
        # cópia rasa: o servidor é multi-thread; evita "list changed size" se um
        # evento estiver escrevendo no painel enquanto /painel serializa.
        return {"eventos": list(self.painel), "estado": self.estado}

    def _retrato(self, evento_atual: dict) -> dict:
        """Retrato compacto da situação — a matéria-prima da decisão do agente.
        Só FATOS observados (não decide nada): o que acabou de acontecer, o
        PROGRESSO do aluno neste bug, o histórico recente e o modelo do aluno."""
        m = self.modelo
        eq = self.bug["equivoco"] if self.bug else None
        return {
            "evento_atual": evento_atual,
            # progresso HONESTO neste bug — é o que distingue exploração de estagnação
            "progresso": {
                "execucoes_neste_bug": self.execucoes_bug,
                "entradas_distintas_testadas": len(set(self.entradas_testadas)),
                "repeticoes_seguidas_da_mesma_entrada": self.repeticoes_seguidas,
                "ja_achou_entrada_que_expoe_o_erro": self.achou_discriminante,
                "editou_o_codigo": self.editou_codigo,
                "modo": "chamada_de_funcao" if self.chamada else "stdin",
            },
            "historico_recente": list(self.historico),
            "modelo_aluno": {
                "dominio_do_equivoco_atual": round(m.dominio(eq), 2) if eq else None,
                "depuracao": {k: round(v, 2) for k, v in m.depuracao.items()},
                "bugs_resolvidos": len(m.bugs_resolvidos),
                "interface_neste_bug": {
                    "abriu_ver_variaveis": self.usou_trace_bug,   # 0 = nunca olhou as variáveis
                    "colou_codigo_de_fora": self.colou_codigo_bug,
                },
            },
            "bug": {
                "enunciado": self.bug.get("enunciado", "") if self.bug else "",
                "equivoco": eq,
                "tempo_no_bug_s": int(time.time() - self.ts_inicio_bug),
            },
            "ja_usou_dica": self.usou_dica,
            "ja_intervim_neste_bug": self.ja_intervim_bug,
            "ultima_intervencao_do_agente": (
                {"acao": self.ultima_acao_agente["acao"],
                 "ha_s": int(time.time() - self.ultima_acao_agente["ts"])}
                if self.ultima_acao_agente else None),
        }

    def _monitorar(self, evento_atual: dict) -> dict | None:
        """Roda a decisão do agente e devolve a intervenção (ou None p/ silêncio)."""
        if self.estado != ALUNO_TRABALHANDO or self.bug is None:
            return None
        dec = self.treinador.decidir_intervencao(self._retrato(evento_atual))
        # o raciocínio SEMPRE aparece no painel (é o que torna a agência visível)
        if dec["motivo"]:
            self._painel("🧠", "leitura: " + dec["motivo"], {"tipo": "leitura"})
        self._painel("🎯", "decisão: " + dec["acao"],
                     {"tipo": "decisao", "acao": dec["acao"], "confianca": dec.get("confianca")})

        if dec["acao"] == "OBSERVAR":
            return None

        # --- guarda-corpos (segurança; NÃO decidem quando ajudar) ---
        agora = time.time()
        if self.n_intervencoes >= config.MAX_INTERVENCOES_PROATIVAS:
            self._painel("🔒", "(teto de intervenções atingido nesta sessão — só observando)",
                         {"tipo": "guard"})
            return None
        if agora - self.ts_ultima_intervencao < config.COOLDOWN_INTERVENCAO_S:
            self._painel("🔒", "(intervim há pouco — aguardo um instante para não atrapalhar)",
                         {"tipo": "guard"})
            return None

        interv = self._executar_acao(dec)
        if interv:
            self.ts_ultima_intervencao = agora
            self.n_intervencoes += 1
            self.ja_intervim_bug = True
            self.ultima_acao_agente = {"acao": dec["acao"], "ts": agora}
            self.registro.intervencao(dec["acao"])
        return interv

    def _executar_acao(self, dec: dict) -> dict | None:
        """Executa a ação escolhida pelo agente, com o Verificador como guardrail."""
        acao = dec["acao"]

        if acao == "DAR_DICA":
            return self._intervir_completo(origem="proativo")

        # ações de mensagem curta (cutucão socrático): não afirmam nada sobre
        # execução, mas ainda passam pelo Verificador para não vazar solução.
        msg = dec.get("mensagem", "").strip()
        if not msg:
            return None
        envelope = {"texto": msg, "nivel": 2, "revela_solucao": False, "ancoras": []}
        vd = verificar(envelope, self.bug["cod_ref"], self.bug["testes"], exigir_ancora=False)
        if not vd["aprovado"]:
            self._painel("🔒", "(o Verificador barrou a mensagem: " + vd["motivo"] + ")",
                         {"tipo": "guard"})
            return None
        self._painel("💬", msg, {"tipo": "fala", "acao": acao})
        interv = {"acao": acao, "mensagem": msg, "proativa": True}
        # PERGUNTAR abre a palavra para o aluno responder (fecha o laço, não é papo livre)
        interv["espera_resposta"] = (acao == "PERGUNTAR")
        if acao == "MOSTRAR_VALORES":
            # não só sugere: RODA o trace de verdade e mostra as variáveis passo a passo,
            # para o aluno enxergar o estado (sem entregar a correção).
            entrada = self.ultima_entrada or self._entrada_que_falha()
            try:
                r = tools.trace(self.cod_atual, chamada=entrada) if self.chamada else tools.trace(self.cod_atual, entrada)
                passos = r.get("passos", [])
                interv["trace"] = {"entrada": entrada, "passos": passos}
                self._painel("🔎", f"abri as variáveis em {entrada} ({len(passos)} passos) — veja no painel de variáveis",
                             {"tipo": "trace"})
            except Exception:
                pass
            # NÃO credita le_variaveis do aluno: quem abriu as variáveis foi o AGENTE,
            # não é evidência da habilidade de depuração dele (evidência limpa).
        return interv

    def _intervir_completo(self, origem: str = "proativo") -> dict:
        """Investigação completa (ReAct) + dica verificada. Usada tanto quando o
        aluno pede quanto quando o AGENTE decide dar a dica sozinho."""
        self.usou_dica = True
        try:
            entrada_falha = self._entrada_que_falha()
            res = self.treinador.intervir(
                cod_aluno=self.cod_atual, cod_ref=self.bug["cod_ref"],
                entrada_falha=entrada_falha, testes=self.bug["testes"], nivel_inicial=3,
                chamada=self.chamada, assinatura=self.assinatura)
        except Exception as e:
            self._painel("🔒", "não consegui investigar agora (" + str(e)[:120] + ")",
                         {"tipo": "guard"})
            return {"acao": "DAR_DICA", "mensagem": _TEXTO_DICA_SEGURA,
                    "nivel": config.NIVEL_MIN, "proativa": (origem == "proativo")}
        self._painel_investigacao(res["investigacao"])
        env = res["envelope"]
        rotulo = "dica (o agente decidiu intervir)" if origem == "proativo" else "dica (a pedido do aluno)"
        inv = res.get("investigacao") or {}
        ancoras = []
        for a in (inv.get("ancoras") or [])[-3:]:
            if not isinstance(a, dict):
                continue
            ancoras.append({
                "entrada": a.get("entrada"),
                "saida_aluno": a.get("saida_aluno"),
                "saida_ref": a.get("saida_ref"),
                "divergiu": a.get("divergiu"),
            })
        vd = res.get("veredito") or {}
        self._painel("💬", env["texto"], {
            "tipo": "dica", "nivel": env["nivel"], "rotulo": rotulo,
            "verificador": {
                "aprovado": vd.get("aprovado"),
                "rejeicoes": res.get("rejeicoes", 0),
                "rebaixado": bool(res.get("rebaixado")),
            },
            "ancoras": ancoras,
        })
        return {"acao": "DAR_DICA", "mensagem": env["texto"], "nivel": env["nivel"],
                "proativa": (origem == "proativo")}

    def _painel_investigacao(self, inv: dict) -> None:
        """Traduz o log da investigação (ReAct) em linhas legíveis no painel —
        é AQUI que o público vê o agente formular hipóteses, projetar e rodar
        experimentos, e podar. Torna a investigação (antes escondida) visível."""
        self._painel("🔬", "aluno parece travado — vou investigar antes de falar", {"tipo": "invest"})
        for passo in inv.get("log", []):
            tag = passo[0]
            extra = passo[-1] if len(passo) > 1 and isinstance(passo[-1], dict) else {}
            if tag == "gerar_hipoteses":
                self._painel("🔬", f"levantei {len(passo[1])} hipóteses concorrentes sobre o erro",
                             {"tipo": "invest", "hipoteses": _hips_evento(extra)})
            elif tag == "regenerar_hipoteses":
                self._painel("🔬", "as hipóteses não bastaram — refiz o conjunto",
                             {"tipo": "invest", "hipoteses": _hips_evento(extra)})
            elif tag == "analisar":
                sep = "SEPAROU as hipóteses" if "divergiu=True" in str(passo[2]) else "não separou"
                self._painel("🔬", f"experimento: rodei {passo[1]} → {sep}",
                             {"tipo": "invest", "experimento": _experimento_evento(passo, extra)})
            elif tag == "nenhum_candidato_separou":
                self._painel("🔬", "nenhum candidato separou as hipóteses; tento outros",
                             {"tipo": "invest"})
            elif tag == "podar":
                self._painel("🔬", f"descartei hipóteses; sobreviveram {passo[1]}", {
                    "tipo": "invest",
                    "sobreviventes": extra.get("sobreviventes", passo[1]),
                    "raciocinio": extra.get("raciocinio", ""),
                })
            elif tag == "fallback_direto":
                self._painel("🔬", f"sem separar tudo, olhei direto a entrada que falha ({passo[1]})",
                             {"tipo": "invest", "experimento": _experimento_evento(passo, extra)})
        eq = inv.get("equivoco")
        if eq:
            eq_id = eq.get("equivoco")
            self._painel("🔬", f"conclusão: o equívoco parece ser '{eq_id}'", {
                "tipo": "invest",
                "equivoco": eq_id,
                "rotulo": (catalogo.CATALOGO.get(eq_id) or {}).get("nome"),
                "conclusivo": inv.get("conclusivo"),
            })

    # ------------------------------------------------------------------ #
    def _on_rodou_entrada(self, dados: dict) -> dict:
        entrada = dados.get("entrada", "")
        if self.chamada:
            r = tools.executar(self.cod_atual, chamada=entrada)
            a = tools.analisar(self.cod_atual, self.bug["cod_ref"], chamada=entrada)
        else:
            r = tools.executar(self.cod_atual, entrada)
            a = tools.analisar(self.cod_atual, self.bug["cod_ref"], entrada=entrada)
        self.modelo.registrar_sinais_interface({"num_execucoes": 1})
        _log.info("rodou_entrada estimulo=%r -> saida=%r (discriminante=%s)",
                  entrada, (r["saida"] or "").strip(), a["divergiu"])
        # sinal-ouro: a entrada que o aluno escolheu é DISCRIMINANTE?
        if a["divergiu"]:
            self.modelo.registrar_sinais_interface({"num_execucoes_proprias_discriminantes": 1})
            self.modelo.registrar_depuracao({"testa_entrada_discriminante": True})

        # --- atualiza os sinais de PROGRESSO (fatos; não decidem nada) ---
        self.execucoes_bug += 1
        igual = (entrada == self.ultima_entrada)
        self.repeticoes_seguidas = (self.repeticoes_seguidas + 1) if igual else 0
        self.entradas_testadas.append(entrada)
        if a["divergiu"]:
            self.achou_discriminante = True
        if self.cod_atual != self.bug["cod_bugado"]:
            self.editou_codigo = True
        self.registro.rodou_entrada(entrada, bool(a["divergiu"]))

        evento_atual = {
            "tipo": "rodou_entrada", "entrada": entrada,
            "saida": (r["saida"] or "").strip(),
            "entrada_expoe_o_erro": a["divergiu"],   # essa entrada é discriminante? (vitória do aluno)
            "e_repeticao_da_anterior": igual,
        }
        self._hist(f"rodou {entrada!r} → " +
                   ("ACHOU a entrada que expõe o erro!" if a["divergiu"]
                    else ("repetiu a mesma de antes" if igual else "não expôs o erro (testando)")))
        self.ultima_entrada = entrada
        self.cod_ultima_exec = self.cod_atual

        resp = {"resposta": "resultado_execucao", "saida": r["saida"], "erro": r["erro"],
                "estado": self.estado, "encerrada": False}
        interv = self._monitorar(evento_atual)
        if interv:
            resp["intervencao"] = interv
        return resp

    def _on_respondeu(self, dados: dict) -> dict:
        """O aluno respondeu a uma PERGUNTA do agente. O agente dá um feedback CURTO
        e ANCORADO na tarefa (nunca papo livre, nunca revela a solução) e ajusta o
        modelo do aluno conforme a resposta demonstrou (ou não) entendimento."""
        pergunta = dados.get("pergunta", "")
        resposta = dados.get("resposta", "")
        self._hist(f"respondeu ao agente: {resposta!r}")
        try:
            aval = self.treinador.llm.chamar("avaliar_resposta", {
                "pergunta": pergunta, "resposta": resposta,
                "equivoco": self.bug["equivoco"] if self.bug else "",
                "correcao": catalogo.texto_correcao(self.bug["equivoco"]) if self.bug else "",
                "cod_aluno": self.cod_atual})
        except Exception:
            feedback = "Anotei a sua resposta. Continue investigando o que a execução mostra."
            compreensao = None
        else:
            feedback = (aval.get("feedback") or "").strip()
            compreensao = aval.get("compreensao")
            # feedback também passa pelo Verificador (não pode vazar a solução)
            env = {"texto": feedback, "nivel": 2, "revela_solucao": False, "ancoras": []}
            vd = verificar(env, self.bug["cod_ref"], self.bug["testes"], exigir_ancora=False)
            if not vd["aprovado"]:
                feedback = "Boa tentativa — continue investigando o que a execução mostra."
            # sinal de entendimento (evidência limpa: veio do próprio aluno)
            try:
                c = float(compreensao)
                self.modelo.registrar_depuracao({"forma_hipotese": c >= 0.5})
            except (TypeError, ValueError):
                pass
            _log.info("respondeu %r -> compreensao=%s", resposta, compreensao)
        self._painel("🧑", f"aluno respondeu: {resposta}", {"tipo": "aluno"})
        self._painel("💬", feedback, {"tipo": "fala", "acao": "FEEDBACK"})
        return {"resposta": "feedback_resposta", "feedback": feedback,
                "compreensao": compreensao, "estado": self.estado, "encerrada": False}

    def _on_pediu_dica(self) -> dict:
        _log.info("pediu_dica (bug=%s)", self.bug["id"])
        self._hist("pediu dica")
        self.registro.pediu_dica()
        interv = self._intervir_completo(origem="aluno")
        self.ts_ultima_intervencao = time.time()   # respeita o cooldown depois disso
        return {"resposta": "dica", "mensagem": interv["mensagem"],
                "nivel": interv.get("nivel"), "estado": self.estado, "encerrada": False}

    def _on_submeteu(self, dados: dict) -> dict:
        self.cod_atual = dados.get("codigo", self.cod_atual)
        self.tentativas += 1
        resultados = tools.rodar_suite(self.cod_atual, self.bug["testes"])
        passou_tudo = all(r["passou"] for r in resultados)
        self.registro.submeteu(passou_tudo)
        _aprov = sum(r["passou"] for r in resultados)
        _log.info("submeteu_correcao (bug=%s): %d/%d testes passaram", self.bug["id"], _aprov, len(resultados))
        if not passou_tudo:
            falhou = [r for r in resultados if not r["passou"]]
            self._hist(f"submeteu correção: {_aprov}/{len(resultados)} testes passaram")
            resp = {"resposta": "correcao_incompleta",
                    "falhas": falhou, "estado": self.estado, "encerrada": False}
            interv = self._monitorar({
                "tipo": "submeteu_correcao", "submeteu_e_falhou": True,
                "testes_passaram": _aprov, "testes_total": len(resultados)})
            if interv:
                resp["intervencao"] = interv
            return resp
        # passou na suíte -> agora pede a explicação (resolvido = passou E explicou)
        self.estado = AGUARDANDO_EXPLICACAO
        return {"resposta": "peca_explicacao",
                "mensagem": "Passou nos testes! Em uma frase: qual era o erro?",
                "estado": self.estado, "encerrada": False}

    def _on_explicou(self, dados: dict) -> dict:
        explicacao = dados.get("texto", "")
        try:
            aval = self.treinador.llm.chamar("avaliar_explicacao", {
                "explicacao": explicacao,
                "equivoco": self.bug["equivoco"],
                "correcao": catalogo.texto_correcao(self.bug["equivoco"])})
        except Exception as e:
            _log.info("explicou: avaliação falhou (%s)", e)
            aval = None

        if aval is None:
            rubrica = {
                "identificou": None,
                "causa": None,
                "correcao": None,
                "nota": None,
                "comentario": "Não consegui avaliar a explicação agora.",
            }
        else:
            qualidade = aval.get("nota", aval.get("qualidade", 0.0))
            _log.info("explicou: %r -> nota=%s (rubrica id=%s causa=%s corr=%s)",
                      explicacao, qualidade, aval.get("identificou"), aval.get("causa"), aval.get("correcao"))
            # EVIDÊNCIA LIMPA: passar nos testes NÃO é domínio. Domínio só sobe se o aluno
            # DEMONSTROU entender (explicação boa). Passar colando código de fora e não saber
            # explicar é sinal de que NÃO domina -> o domínio deve CAIR, não subir.
            try:
                q = float(qualidade)
            except (TypeError, ValueError):
                q = 0.0
            demonstrou = (q >= 0.5) and (self.colou_codigo_bug == 0 or q >= 0.7)
            self.modelo.registrar_conceitual(self.bug["equivoco"], acertou=demonstrou)
            self.modelo.registrar_explicacao(q)
            _log.info("modelo: demonstrou_entendimento=%s (qualidade=%.2f, colagens=%d)",
                      demonstrou, q, self.colou_codigo_bug)
            rubrica = {
                "identificou": aval.get("identificou"),
                "causa": aval.get("causa"),
                "correcao": aval.get("correcao"),
                "nota": qualidade,
                "comentario": aval.get("comentario", ""),
            }
        # resolvido para fins de PROGRESSÃO (passou nos testes), mesmo que não tenha dominado
        self.modelo.registrar_resultado_bug(self.bug["id"], self.bug["equivoco"], resolvido=True)
        bug_resolvido_id = self.bug["id"]
        self.registro.explicou(rubrica)
        # próximo bug ou encerra
        prox = self._proximo_bug()
        prox["rubrica"] = rubrica
        prox["bug_resolvido"] = bug_resolvido_id
        return prox

    # ------------------------------------------------------------------ #
    def _entrada_que_falha(self) -> str:
        for r in tools.rodar_suite(self.cod_atual, self.bug["testes"]):
            if not r["passou"]:
                return r["entrada"]
        if self.bug["testes"]:
            t0 = self.bug["testes"][0]
            return t0.get("entrada") or t0.get("chamada", "")
        return ""
