"""
Projeto Arandu — Interface de LLM (plugável).

O Treinador fala com o LLM por UMA porta: chamar(tarefa, dados) -> dict.
Assim dá pra:
  - rodar TUDO sem chave, com o MockLLM (respostas roteirizadas) -> testar a estrutura;
  - plugar a OpenAI (gpt-4o-mini) trocando só qual objeto é instanciado.

'tarefa' é uma etiqueta ("gerar_hipoteses", "projetar_entrada", "podar",
"redigir_dica"). Cada implementação sabe responder a cada etiqueta.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import json
import os

from log import get_logger

_log = get_logger("llm")


def _carregar_dotenv():
    """Lê o arquivo .env (ao lado deste módulo) e popula variáveis de ambiente
    que ainda não estejam setadas. Sem dependência externa. Assim a chave da
    OpenAI vem do .env automaticamente, em qualquer ponto de entrada."""
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(caminho):
        return
    try:
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, valor = linha.split("=", 1)
                chave, valor = chave.strip(), valor.strip().strip('"').strip("'")
                # ignora placeholder não preenchido (evita erro de autenticação)
                if valor in ("", "cole-sua-chave-aqui"):
                    continue
                if chave and not os.environ.get(chave):
                    os.environ[chave] = valor
    except Exception:
        pass


_carregar_dotenv()


class LLM(ABC):
    @abstractmethod
    def chamar(self, tarefa: str, dados: dict) -> dict:
        ...


# --------------------------------------------------------------------------- #
# MockLLM — respostas roteirizadas para o cenário "contar pares".
# Serve para rodar e testar o laço do Treinador SEM chave de API.
# --------------------------------------------------------------------------- #
class MockLLM(LLM):
    def __init__(self):
        self.chamadas = 0

    def chamar(self, tarefa: str, dados: dict) -> dict:
        self.chamadas += 1
        _log.info("LLM(mock) tarefa=%s (chamada #%d)", tarefa, self.chamadas)

        if tarefa == "gerar_hipoteses":
            return {"hipoteses": [
                {"id": "H1", "equivoco": "CondicaoInvertida",
                 "descricao": "inverteu a condição e está contando os ímpares"},
                {"id": "H2", "equivoco": "SemFiltro",
                 "descricao": "conta todos os números, esqueceu de filtrar"},
            ]}

        if tarefa == "projetar_entrada":
            # entrada só com pares separa as hipóteses:
            # conta-ímpares -> 0 ; conta-todos -> 3 ; correto -> 3
            return {"entradas": ["2 4 6"],
                    "justificativa": "só pares: conta-ímpares daria 0, conta-todos daria 3"}

        if tarefa == "podar":
            r = dados.get("resultado", {})
            sa = (r.get("saida_aluno") or "").strip()
            sr = (r.get("saida_ref") or "").strip()
            # se aluno=0 e ref=3 -> sobra H1 (conta ímpares)
            if sa == "0" and sr == "3":
                return {"sobreviventes": ["H1"],
                        "raciocinio": "aluno deu 0; conta-todos daria 3 (cai H2); conta-ímpares dá 0 (bate H1)"}
            return {"sobreviventes": [h["id"] for h in dados.get("hipoteses", [])],
                    "raciocinio": "resultado não separou as hipóteses"}

        if tarefa == "redigir_dica":
            anc = dados.get("ancoras", [])
            a = anc[-1] if anc else {}
            ent = a.get("entrada", "a entrada que falha")
            det = ""
            if a.get("saida_aluno") is not None and a.get("saida_ref") is not None:
                det = f" (seu programa devolveu {a.get('saida_aluno')!r}; o esperado era {a.get('saida_ref')!r})"
            return {
                "texto": (f"[dica de exemplo — rode com a chave da OpenAI para dicas reais] "
                          f"Rode com {ent}{det} e observe em que ponto o resultado do seu "
                          f"programa passa a divergir do esperado."),
                "nivel": dados.get("nivel", 3),
                "revela_solucao": False,
            }

        if tarefa == "avaliar_explicacao":
            expl = (dados.get("explicacao") or "").strip().lower()
            if not expl or expl in ("não sei", "nao sei"):
                return {"identificou": 0.1, "causa": 0.0, "correcao": 0.0, "nota": 0.05,
                        "comentario": "Tudo bem não saber ainda — tente descrever o que muda na saída quando o erro aparece."}
            return {"identificou": 0.7, "causa": 0.5, "correcao": 0.6, "nota": 0.6,
                    "comentario": "Boa! Você apontou o erro; tente detalhar por que ele mudava o resultado."}

        if tarefa == "avaliar_resposta":
            resp = (dados.get("resposta") or "").strip().lower()
            if not resp or resp in ("não sei", "nao sei", "sei lá", "sei la"):
                return {"feedback": "Sem problema! Tenta rodar uma entrada bem simples e "
                                    "observar as variáveis passo a passo — o que muda?",
                        "compreensao": 0.2}
            return {"feedback": "Boa — é por aí. Agora confirme sua ideia rodando um caso "
                                "que a teste.",
                    "compreensao": 0.6}

        if tarefa == "decidir_acao":
            # Heurística simples só para o MockLLM (sem chave). O agente de verdade
            # é o gpt-4o-mini com o prompt decidir_acao — aqui é só para a estrutura rodar.
            ev = dados.get("evento_atual", {}) or {}
            prog = dados.get("progresso", {}) or {}
            iface = (dados.get("modelo_aluno", {}) or {}).get("interface_neste_bug", {}) or {}
            ja_interviu = dados.get("ja_intervim_neste_bug")
            ult = (dados.get("ultima_intervencao_do_agente") or {}).get("acao")
            if ev.get("tipo") == "colou_codigo_externo":
                return {"acao": "PERGUNTAR", "confianca": 0.7,
                        "motivo": "ele colou um código de fora; quero garantir que entendeu o que colou",
                        "mensagem": "Vi que você colou um código de fora — consegue me explicar, com suas palavras, o que ele faz?"}
            if ev.get("entrada_expoe_o_erro"):
                return {"acao": "ENCORAJAR", "confianca": 0.7,
                        "motivo": "ele achou justamente a entrada que expõe o erro — está no caminho certo",
                        "mensagem": "Boa! Essa entrada expôs o problema — o que ela te diz sobre o erro?"}
            if prog.get("execucoes_neste_bug", 0) <= 2:
                return {"acao": "OBSERVAR", "confianca": 0.7,
                        "motivo": "início do desafio; dando espaço para ele explorar", "mensagem": ""}
            if prog.get("repeticoes_seguidas_da_mesma_entrada", 0) >= 2:
                # escalona: se já sugeri teste antes e não pegou, mostro as variáveis
                if ja_interviu and ult in ("SUGERIR_TESTE", "PERGUNTAR") and not iface.get("abriu_ver_variaveis"):
                    return {"acao": "MOSTRAR_VALORES", "confianca": 0.7,
                            "motivo": "meu cutucão anterior não pegou e ele nunca olhou as variáveis; vou mostrar o estado",
                            "mensagem": "Deixa eu te mostrar as variáveis passo a passo nessa entrada."}
                return {"acao": "SUGERIR_TESTE", "confianca": 0.7,
                        "motivo": "repetiu a mesma entrada várias vezes seguidas sem concluir nada",
                        "mensagem": "Você repetiu esse caso algumas vezes — que tal um caso extremo, tipo uma lista vazia?"}
            if ev.get("submeteu_e_falhou") and dados.get("ja_usou_dica"):
                return {"acao": "DAR_DICA", "confianca": 0.7,
                        "motivo": "já pediu ajuda antes e ainda erra na submissão", "mensagem": ""}
            return {"acao": "OBSERVAR", "confianca": 0.7,
                    "motivo": "está explorando entradas diferentes; melhor não interromper", "mensagem": ""}

        return {}


# --------------------------------------------------------------------------- #
# OpenAILLM — implementação real (gpt-4o-mini). Só é usada se houver chave.
# Não é exercitada no demo; fica pronta para plugar.
# --------------------------------------------------------------------------- #
_PROMPTS = {
    "gerar_hipoteses":
        "Você é um tutor de programação. Com base no código do aluno, no de "
        "referência e na saída errada (tudo em DADOS), liste 2 a 3 HIPÓTESES "
        "concorrentes sobre o EQUÍVOCO conceitual do aluno (não sobre a linha). "
        "Use os equívocos de DADOS.equivocos_possiveis quando encaixarem. "
        "Responda SOMENTE JSON: "
        '{"hipoteses":[{"id":"H1","equivoco":"...","descricao":"..."}]} . '
        "Mantenha os mesmos ids (H1, H2, ...) nas etapas seguintes.",
    "projetar_entrada":
        "Com as hipóteses e os dois códigos em DADOS, proponha de 2 a 4 ENTRADAS "
        "CANDIDATAS que façam as hipóteses preverem saídas DIFERENTES entre si. "
        "Se DADOS.modo == 'chamada', cada entrada é uma CHAMADA de função pronta no "
        "formato de DADOS.assinatura (ex.: 'search(5, (1, 5, 10))'); senão é texto de stdin. "
        "Raciocine: para cada hipótese, que saída ela daria? Escolha entradas em que "
        "essas saídas NÃO coincidem. NÃO repita nenhuma de DADOS.entradas_ja_tentadas. "
        'Responda SOMENTE JSON: {"entradas":["...","..."],"justificativa":"..."} .',
    "podar":
        "Dado o resultado real da execução em DADOS.resultado, diga quais "
        "hipóteses de DADOS.hipoteses SOBREVIVEM (pelos ids). Responda SOMENTE "
        'JSON: {"sobreviventes":["H1"],"raciocinio":"..."} .',
    "redigir_dica":
        "Escreva uma dica no nível indicado em DADOS.nivel (1=pergunta socrática "
        "... 5=nomear o equívoco). NUNCA entregue o código correto nem trechos "
        "dele. Ancore-se nos valores reais de DADOS.ancoras. Responda SOMENTE "
        'JSON: {"texto":"...","nivel":3,"revela_solucao":false} .',
    "avaliar_explicacao":
        "Avalie a explicação do aluno (DADOS.explicacao) sobre o erro que ele acabou "
        "de corrigir, comparando com o equívoco de referência DADOS.equivoco e a "
        "correção DADOS.correcao. Dê uma RUBRICA TRANSPARENTE com três dimensões, cada "
        "uma de 0 a 1: "
        "identificou = apontou O QUE estava errado; "
        "causa = explicou POR QUE aquilo gerava o comportamento errado; "
        "correcao = relacionou com a correção feita. "
        "Dê também 'nota' (0 a 1, visão geral) e um 'comentario' curto e construtivo "
        "(1 frase). Se a explicação for vazia ou 'não sei', notas baixas e comentário "
        "acolhedor sugerindo o próximo passo. NÃO seja severo com uma explicação "
        "essencialmente correta ainda que informal. Responda SOMENTE JSON: "
        '{"identificou":<0-1>,"causa":<0-1>,"correcao":<0-1>,"nota":<0-1>,"comentario":"..."} .',
    "avaliar_resposta":
        "Você é um tutor de depuração. O aluno respondeu a uma PERGUNTA sua "
        "(DADOS.pergunta) com DADOS.resposta. Dê um feedback CURTO (1-2 frases), "
        "caloroso e ANCORADO na tarefa de depuração — reaja ao que ele disse, aponte "
        "se o raciocínio faz sentido e o empurre ao próximo passo. É uma checagem de "
        "entendimento, NÃO um chat: não responda perguntas fora do exercício, não "
        "entregue a correção nem trechos do código certo (o equívoco de referência é "
        "DADOS.equivoco). Se a resposta for vaga ('não sei'), acolha e sugira uma ação "
        "concreta de investigação. Avalie a COMPREENSÃO demonstrada de 0 a 1. "
        'Responda SOMENTE JSON: {"feedback":"...","compreensao":<0 a 1>} .',
    "decidir_acao":
        "Você é um tutor de depuração observando um aluno EM TEMPO REAL. A cada ação "
        "dele você decide, por julgamento, se age e como. Não há regra fixa; use o "
        "PROGRESSO e o contexto em DADOS.\n"
        "REGRA DE OURO: OBSERVAR é a resposta padrão. Só intervenha quando tiver uma "
        "razão CLARA. Um tutor que fala demais atrapalha; a maioria das ações do aluno "
        "não pede resposta nenhuma.\n"
        "Quando OBSERVAR (deixe a mensagem vazia):\n"
        "- é a 1ª ou 2ª execução no bug (DADOS.progresso.execucoes_neste_bug <= 2) — dê espaço;\n"
        "- o aluno está EXPLORANDO: testando entradas DIFERENTES "
        "(entradas_distintas_testadas crescendo, e_repeticao_da_anterior=false);\n"
        "- o aluno ACABOU de achar / já achou uma entrada que expõe o erro "
        "(evento_atual.entrada_expoe_o_erro=true OU progresso.ja_achou_entrada_que_expoe_o_erro=true): "
        "ele está no caminho certo — no MÁXIMO um ENCORAJAR curto, jamais 'tente algo diferente';\n"
        "- você já interveio há pouco (DADOS.ultima_intervencao_do_agente recente) e nada mudou.\n"
        "IMPORTANTE: em modo 'chamada_de_funcao', trocar a ENTRADA sem mexer no código é "
        "TESTE NORMAL e saudável — NÃO é estagnação. 'editou_o_codigo=false' sozinho nunca "
        "é motivo para agir.\n"
        "Quando AGIR (com parcimônia, variando conforme a situação):\n"
        "- colou código de fora (modelo_aluno.interface_neste_bug.colou_codigo_de_fora > 0) -> "
        "PERGUNTAR pedindo que ele EXPLIQUE, com as próprias palavras, o que o código colado faz "
        "(cópia sem entender é o principal risco pedagógico);\n"
        "- repetiu a MESMA entrada várias vezes seguidas "
        "(progresso.repeticoes_seguidas_da_mesma_entrada >= 2) sem tirar conclusão -> PERGUNTAR "
        "ou SUGERIR_TESTE que o empurre a um caso-limite;\n"
        "- já rodou várias entradas mas NENHUMA expõe o erro e ele parece sem rumo -> SUGERIR_TESTE;\n"
        "- ele NUNCA abriu as variáveis (interface_neste_bug.abriu_ver_variaveis == 0) e a saída "
        "está confusa, OU já achou a entrada que expõe o erro mas não entende por quê -> MOSTRAR_VALORES;\n"
        "- acabou de achar a entrada que expõe o erro -> ENCORAJAR (uma frase);\n"
        "- resolveu / está quase lá -> AVANCAR.\n"
        "ESCALONAMENTO (importante): se você JÁ interveio neste bug "
        "(ja_intervim_neste_bug=true) e o aluno continua preso, NÃO repita o mesmo tipo de ação "
        "(veja ultima_intervencao_do_agente.acao). SUBA de nível: um SUGERIR_TESTE que não pegou "
        "vira MOSTRAR_VALORES; se ainda assim travar, vira DAR_DICA. Guarde DAR_DICA para quando "
        "ele já pediu ajuda, ou continua preso mesmo depois de MOSTRAR_VALORES.\n"
        "Escolha UMA ação de DADOS.acoes_possiveis. Para ações com fala "
        "(ENCORAJAR/PERGUNTAR/SUGERIR_TESTE/MOSTRAR_VALORES/AVANCAR) escreva em 'mensagem' UMA "
        "frase curta e calorosa que NUNCA entregue a correção nem trechos do código certo. "
        "Para OBSERVAR e DAR_DICA deixe 'mensagem' vazia. "
        "Em 'motivo', 1 frase dizendo COMO você leu a situação (aparece numa tela ao vivo). "
        "Responda SOMENTE JSON: "
        '{"acao":"OBSERVAR","motivo":"...","confianca":<0 a 1>,"mensagem":""} .',
}


class OpenAILLM(LLM):
    def __init__(self, modelo: str = "gpt-4o-mini", api_key: str | None = None):
        from openai import OpenAI          # import tardio (só quando usado)
        # timeout + poucos retries: se a rede engasgar, a chamada FALHA rápido em
        # vez de pendurar para sempre (o que travava o servidor).
        self.cliente = OpenAI(api_key=api_key, timeout=20.0, max_retries=1)   # lê OPENAI_API_KEY do ambiente se None
        self.modelo = modelo
        self.chamadas = 0
        self.tokens_entrada = 0
        self.tokens_saida = 0

    def chamar(self, tarefa: str, dados: dict) -> dict:
        self.chamadas += 1
        instrucao = _PROMPTS[tarefa]          # sem .format(): os prompts têm chaves JSON literais
        conteudo = instrucao + "\n\nDADOS:\n" + json.dumps(dados, ensure_ascii=False)
        resp = self.cliente.chat.completions.create(
            model=self.modelo,
            messages=[{"role": "user", "content": conteudo}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        u = getattr(resp, "usage", None)
        if u:
            self.tokens_entrada += getattr(u, "prompt_tokens", 0)
            self.tokens_saida += getattr(u, "completion_tokens", 0)
        _log.info("LLM(%s) tarefa=%s tokens=%s/%s (acum %s/%s)", self.modelo, tarefa,
                  getattr(u, "prompt_tokens", "?"), getattr(u, "completion_tokens", "?"),
                  self.tokens_entrada, self.tokens_saida)
        return json.loads(resp.choices[0].message.content)
