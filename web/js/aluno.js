"use strict";
(function () {
  // config.py TIMEOUT_INATIVIDADE_S = 600
  var INATIVIDADE_MS = 600 * 1000;
  // arandu_motor LIMITES max_passos. tools.trace não repassa o flag `truncado`.
  var LIMITE_PASSOS_TRACE = 500;

  var TAG_ACAO = {
    DAR_DICA: "Dica",
    PERGUNTAR: "Pergunta",
    SUGERIR_TESTE: "Sugestão de teste",
    MOSTRAR_VALORES: "Valores reais",
    ENCORAJAR: "Incentivo",
    AVANCAR: "Avançar",
    FEEDBACK: "Retorno",
  };
  var ROTULO_NIVEL = {
    1: "pergunta",
    2: "teste que falha",
    3: "onde diverge",
    4: "próximo passo",
    5: "nome do equívoco",
  };
  var ABAS = ["abaSaida", "abaTrace", "abaTestes"];
  var PAINEIS = { abaSaida: "painelSaida", abaTrace: "painelTrace", abaTestes: "painelTestes" };
  var BOTOES_ACAO = ["btnRodar", "btnTrace", "btnDica", "btnSubmeter"];
  var TEXTO_PENSANDO = {
    rodar: "Rodando o seu código",
    trace: "Montando o passo a passo",
    dica: "Rodando experimentos no seu código antes de responder",
    submeter: "Rodando os testes escondidos",
    explicar: "Lendo a sua explicação",
    responder: "Lendo a sua resposta",
  };
  var TIMEOUT_LLM_MS = 90 * 1000;

  var infoServidor = null;
  var codigoOriginal = "";
  var tInicio = Date.now();
  var primeiraExec = false;
  var lastLen = 0;
  var lastEdit = 0;
  var churn = 0;
  var pausas = 0;
  var nResolvidos = 0;
  var nExecucoes = 0;
  var nDicas = 0;
  var bugsVistos = 0;
  var passosAtuais = [];
  var passoAtual = 0;
  var ocupado = false;
  var pronto = false;
  var sessaoAtiva = false;
  var sessaoEncerrada = false;
  var mostrandoRubrica = false;
  var pendente = null;
  var textoExplicado = "";
  var timerInat = null;
  var pollBast = null;
  var bastEmVoo = false;
  var bastVistos = 0;
  var bastUltimo = null;
  var btnTentar = null;
  var reiniciando = false;
  var timerPensando = null;

  function $(id) { return document.getElementById(id); }

  function clonar(id) {
    return $(id).content.firstElementChild.cloneNode(true);
  }

  function relogio(ts, comSegundos) {
    var d = typeof ts === "number" ? new Date(ts * 1000) : new Date();
    var p = function (n) { return String(n).padStart(2, "0"); };
    var base = p(d.getHours()) + ":" + p(d.getMinutes());
    return comSegundos ? base + ":" + p(d.getSeconds()) : base;
  }

  function txtVar(v) {
    if (typeof v === "string") return v;
    if (v == null) return String(v);
    try { return JSON.stringify(v); } catch (e) { return String(v); }
  }

  function pct(v) {
    var n = Number(v);
    if (!Number.isFinite(n)) return 0;
    return Math.round(n * 100);
  }

  function eLacoQueNaoTermina(erro) {
    var e = String(erro || "");
    return e.indexOf("LimiteDeLinhas") >= 0 || e.indexOf("LimiteDeTempo") >= 0
      || e.indexOf("laço infinito") >= 0 || e.indexOf("Tempo limite") >= 0
      || /Limite de .+ linhas/.test(e);
  }

  function traceFoiTruncado(meta, n) {
    if (meta && meta.truncado) return true;
    if (n >= LIMITE_PASSOS_TRACE) return true;
    if (meta && eLacoQueNaoTermina(meta.erro)) return true;
    return false;
  }

  function motivoLegivel(m) {
    if (m == null || m === "") return "";
    if (m === "resolveu todos os bugs disponíveis") return "Você resolveu todos os desafios disponíveis.";
    if (m === "aluno pediu para sair") return "Você encerrou a sessão.";
    if (m === "inatividade") return "A sessão foi encerrada por inatividade.";
    return String(m);
  }

  function erroReq(detalhe) {
    var e = new Error(detalhe || "falha");
    e.detalhe = detalhe || "";
    return e;
  }

  function api(method, rota, corpo) {
    var opts = { method: method, headers: {}, cache: "no-store" };
    var ctrl = null;
    var timer = null;
    if (method === "POST" && (rota === "/evento" || rota === "/iniciar")) {
      ctrl = new AbortController();
      opts.signal = ctrl.signal;
      timer = setTimeout(function () { ctrl.abort(); }, TIMEOUT_LLM_MS);
    }
    if (corpo !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(corpo);
    }
    function limparTimeout() {
      if (timer != null) {
        clearTimeout(timer);
        timer = null;
      }
    }
    return fetch(rota, opts).then(function (resp) {
      return resp.json().catch(function () { return null; }).then(function (data) {
        if (!resp.ok) throw erroReq(data && data.erro ? String(data.erro) : "");
        if (data == null) throw erroReq("");
        return data;
      });
    }, function (err) {
      if (err && err.name === "AbortError") {
        throw erroReq("O treinador demorou demais para responder. Tente de novo.");
      }
      throw erroReq("");
    }).then(function (data) {
      limparTimeout();
      return data;
    }, function (e) {
      limparTimeout();
      throw e;
    });
  }

  function toastErro(e) {
    var node = clonar("tpl-toast");
    node.classList.add("toast--erro");
    var det = e && e.detalhe ? " " + e.detalhe : "";
    node.querySelector(".toast__tx").textContent = "Não consegui falar com o servidor." + det;
    $("toasts").appendChild(node);
    setTimeout(function () { node.remove(); }, 6000);
  }

  function setEstado(estado) {
    var map = {
      aluno_trabalhando: "Investigando",
      aguardando_explicacao: "Explicando",
      encerrada: "Encerrada",
    };
    $("estadoSessao").textContent = map[estado] || estado || "Investigando";
  }

  function renderProgresso(comAtual) {
    var trilha = $("progressoTrilha");
    trilha.replaceChildren();
    var i;
    for (i = 0; i < nResolvidos; i++) {
      var feito = document.createElement("i");
      feito.className = "feito";
      trilha.appendChild(feito);
    }
    if (comAtual) {
      var atual = document.createElement("i");
      atual.className = "atual";
      trilha.appendChild(atual);
    }
    var n = comAtual ? nResolvidos + 1 : Math.max(nResolvidos, 1);
    $("progressoTexto").textContent = "Desafio " + n;
  }

  function textoPensando(seg) {
    if (seg < 60) return seg + " s";
    return Math.floor(seg / 60) + " min " + (seg % 60) + " s";
  }

  function pararPensando() {
    if (timerPensando != null) {
      clearInterval(timerPensando);
      timerPensando = null;
    }
    var tempo = $("pensandoTempo");
    if (tempo) tempo.textContent = "";
  }

  function mostrarPensando(texto) {
    pararPensando();
    var tempo = $("pensandoTempo");
    var rotulo = $("pensandoTexto");
    if (rotulo) {
      if (texto) rotulo.textContent = texto;
      else rotulo.textContent = rotulo.textContent.replace(/\s*[….]+$/, "");
    }
    if (tempo) tempo.textContent = "0 s";
    $("pensando").hidden = false;
    var t0 = Date.now();
    timerPensando = setInterval(function () {
      var seg = Math.floor((Date.now() - t0) / 1000);
      if (tempo) tempo.textContent = textoPensando(seg);
    }, 1000);
  }

  function esconderPensando() {
    $("pensando").hidden = true;
    pararPensando();
  }

  function limparConversa() {
    var conv = $("conversa");
    Array.prototype.slice.call(conv.children).forEach(function (el) {
      if (el.id !== "conversaVazia" && el.id !== "pensando") el.remove();
    });
    $("conversaVazia").hidden = false;
    esconderPensando();
    conv.appendChild($("pensando"));
  }

  function publicar(node) {
    var conv = $("conversa");
    conv.insertBefore(node, $("pensando"));
    $("conversaVazia").hidden = true;
    conv.scrollTop = conv.scrollHeight;
  }

  function addMsgSistema(texto) {
    var node = clonar("tpl-msg-sistema");
    node.querySelector(".msg__texto").textContent = texto;
    publicar(node);
  }

  function addMsgAluno(texto) {
    var node = clonar("tpl-msg-aluno");
    node.querySelector(".msg__texto").textContent = texto;
    node.querySelector(".msg__hora").textContent = relogio();
    publicar(node);
  }

  function addMsgTreinador(iv) {
    if (!iv) return;
    var mensagem = iv.mensagem == null ? "" : String(iv.mensagem);
    var temTrace = iv.acao === "MOSTRAR_VALORES" && iv.trace && Array.isArray(iv.trace.passos);
    if (!mensagem.trim() && !temTrace) return;
    var node = clonar("tpl-msg");
    node.dataset.acao = iv.acao || "";
    node.querySelector(".msg__tag").textContent = TAG_ACAO[iv.acao] || iv.acao || "Treinador";
    node.querySelector(".msg__hora").textContent = relogio();
    node.querySelector(".msg__texto").textContent = mensagem;
    if (iv.nivel) {
      var nivel = node.querySelector(".nivel");
      nivel.hidden = false;
      nivel.dataset.nivel = String(iv.nivel);
      nivel.title = "Nível " + iv.nivel + " de 5";
      nivel.querySelector(".nivel__rotulo").textContent = ROTULO_NIVEL[iv.nivel] || "";
    }
    if (iv.acao === "DAR_DICA") nDicas++;
    if (temTrace) {
      var passos = iv.trace.passos;
      var entrada = iv.trace.entrada || "";
      var meta = { truncado: passos.length >= LIMITE_PASSOS_TRACE };
      renderTrace(passos, entrada, meta);
      ativarAba("abaTrace");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn--sm";
      btn.textContent = "Ver no passo a passo";
      btn.addEventListener("click", function () {
        renderTrace(passos, entrada, meta);
        ativarAba("abaTrace");
      });
      node.querySelector(".msg__acoes").appendChild(btn);
    }
    if (iv.acao === "PERGUNTAR" && iv.espera_resposta) {
      var form = clonar("tpl-resposta");
      var ta = form.querySelector("textarea");
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var resposta = ta.value.trim();
        if (!resposta) return;
        responderPergunta(form, mensagem, resposta);
      });
      ta.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          form.requestSubmit();
        }
      });
      node.appendChild(form);
    }
    publicar(node);
  }

  function tipoEfetivo(ev) {
    if (ev.tipo) return ev.tipo;
    if (ev.icone === "🔒") return "guard";
    if (ev.icone === "🔬") return "invest";
    return "aluno";
  }

  function montarEvento(ev) {
    var node = clonar("tpl-evento");
    var tipo = tipoEfetivo(ev);
    node.dataset.tipo = tipo;
    node.querySelector(".evento__ic").textContent = ev.icone || "•";
    node.querySelector(".evento__tx").textContent = ev.texto || "";
    var time = node.querySelector("time");
    time.textContent = relogio(ev.ts, true);
    var tag = "";
    if (ev.acao) tag = String(ev.acao);
    else if (ev.rotulo) tag = String(ev.rotulo);
    else if (ev.nivel != null && ev.nivel !== "") tag = "nível " + ev.nivel;
    var tagEl = node.querySelector(".evento__tag");
    if (tag) {
      tagEl.hidden = false;
      tagEl.textContent = tag;
    }
    if (ev.confianca != null && ev.confianca !== "") {
      var c = Number(ev.confianca);
      if (Number.isFinite(c)) {
        var conf = node.querySelector(".conf");
        conf.hidden = false;
        conf.querySelector("i").style.setProperty("--v", String(Math.round(c * 100)));
        conf.querySelector(".conf__tx").textContent = Math.round(c * 100) + "%";
      }
    }
    window.AranduEvidencia && AranduEvidencia.preencher(node, ev);
    return node;
  }

  function mesmoEv(a, b) {
    return a && b && a.ts === b.ts && a.texto === b.texto && a.icone === b.icone;
  }

  function atualizarBastidores() {
    if ($("bastidores").hidden) return Promise.resolve();
    if (bastEmVoo) return Promise.resolve();
    bastEmVoo = true;
    return api("GET", "/painel").then(function (m) {
      var evs = (m && m.eventos) || [];
      var feed = $("feedBastidores");
      var ok = bastVistos === 0 || (evs.length >= bastVistos && mesmoEv(evs[bastVistos - 1], bastUltimo));
      if (!ok) {
        feed.replaceChildren();
        bastVistos = 0;
        bastUltimo = null;
      }
      var i;
      for (i = bastVistos; i < evs.length; i++) feed.appendChild(montarEvento(evs[i]));
      bastVistos = evs.length;
      bastUltimo = evs.length ? evs[evs.length - 1] : null;
      var sc = feed.parentElement;
      if (sc) sc.scrollTop = sc.scrollHeight;
    }).catch(function () {
      /* polling silencioso */
    }).then(function () {
      bastEmVoo = false;
    });
  }

  function setBastidores(aberto) {
    $("bastidores").hidden = !aberto;
    document.body.classList.toggle("bastidores-aberto", aberto);
    $("btnBastidores").setAttribute("aria-pressed", aberto ? "true" : "false");
    if (pollBast) {
      clearInterval(pollBast);
      pollBast = null;
    }
    if (aberto) {
      atualizarBastidores();
      pollBast = setInterval(atualizarBastidores, 2500);
    }
  }

  function ligarDemoEAlternar() {
    $("btnBastidores").hidden = false;
    setBastidores($("bastidores").hidden);
  }

  function ativarAba(idBtn) {
    ABAS.forEach(function (id) {
      var on = id === idBtn;
      $(id).setAttribute("aria-selected", on ? "true" : "false");
      $(PAINEIS[id]).hidden = !on;
    });
  }

  function setContador(id, texto, tipo) {
    var el = $(id);
    el.textContent = texto;
    el.classList.remove("aba__contador--erro", "aba__contador--ok");
    if (tipo) el.classList.add(tipo);
  }

  function esconderDestaque() {
    $("linhaDestaque").hidden = true;
    $("gutter").querySelectorAll(".ativa").forEach(function (s) { s.classList.remove("ativa"); });
  }

  function atualizarGutter() {
    var g = $("gutter");
    var n = Math.max(1, $("codigo").value.split("\n").length);
    while (g.children.length < n) g.appendChild(document.createElement("span"));
    while (g.children.length > n) g.removeChild(g.lastElementChild);
    var i;
    for (i = 0; i < n; i++) g.children[i].textContent = String(i + 1);
  }

  function atualizarModificado() {
    $("arquivo").classList.toggle("modificado", $("codigo").value !== codigoOriginal);
  }

  function contabilizarEdicao() {
    var ed = $("codigo");
    var n = ed.value.length;
    if (n < lastLen) churn += (lastLen - n);
    lastLen = n;
    var agora = Date.now();
    if (lastEdit && agora - lastEdit > 8000) pausas++;
    lastEdit = agora;
  }

  function aposEdicao() {
    contabilizarEdicao();
    esconderDestaque();
    atualizarGutter();
    atualizarModificado();
  }

  function destacarLinha(linha) {
    var hl = $("linhaDestaque");
    var gutter = $("gutter");
    gutter.querySelectorAll(".ativa").forEach(function (s) { s.classList.remove("ativa"); });
    var n = Number(linha);
    if (!n) {
      hl.hidden = true;
      return;
    }
    hl.hidden = false;
    hl.style.setProperty("--hl-linha", String(n));
    var span = gutter.children[n - 1];
    if (span) span.classList.add("ativa");
    var editor = $("editor");
    var y = (n - 1) * 22;
    if (y < editor.scrollTop || y + 22 > editor.scrollTop + editor.clientHeight) {
      editor.scrollTop = Math.max(0, y - 22);
    }
  }

  function resetBancada() {
    $("saidaVazia").hidden = false;
    $("saidaConteudo").hidden = true;
    $("saida").textContent = "";
    $("saida").classList.remove("console--vazio");
    $("saidaErro").hidden = true;
    $("saidaErroTexto").textContent = "";
    $("traceVazio").hidden = false;
    $("traceConteudo").hidden = true;
    $("traceCorpo").replaceChildren();
    $("traceTruncado").hidden = true;
    $("traceContador").textContent = "Passo 1 de 1";
    $("traceSlider").max = "0";
    $("traceSlider").value = "0";
    var code = $("traceEntrada").querySelector("code");
    if (code) code.textContent = "";
    $("testesVazio").hidden = false;
    $("testesConteudo").hidden = true;
    $("listaTestes").replaceChildren();
    setContador("contTrace", "", null);
    setContador("contTestes", "", null);
    ativarAba("abaSaida");
    esconderDestaque();
    passosAtuais = [];
    passoAtual = 0;
  }

  function renderBug(bug) {
    bugsVistos++;
    if (bugsVistos > 1) addMsgSistema("Novo desafio");
    var chamada = bug.modo === "chamada";
    $("enunciado").textContent = bug.enunciado || "";
    var ass = bug.assinatura || "";
    $("assinatura").hidden = !ass;
    $("assinaturaTexto").textContent = ass;
    $("modoBug").textContent = chamada ? "função" : "entrada padrão";
    $("entradaRotulo").textContent = chamada ? "Chamada" : "Entrada (stdin)";
    var ent = $("entrada");
    if (chamada) {
      ent.value = bug.exemplo_entrada || "";
      ent.placeholder = bug.exemplo_entrada || "";
    } else {
      ent.value = "";
      ent.placeholder = "2 4 6";
    }
    ent.scrollLeft = 0;
    codigoOriginal = bug.codigo || "";
    var ed = $("codigo");
    ed.value = codigoOriginal;
    lastLen = ed.value.length;
    tInicio = Date.now();
    primeiraExec = false;
    atualizarGutter();
    atualizarModificado();
    resetBancada();
    renderProgresso(true);
  }

  function mostrarSaida(entrada, saida, erro) {
    ativarAba("abaSaida");
    $("saidaVazia").hidden = true;
    $("saidaConteudo").hidden = false;
    var ent = entrada == null ? "" : String(entrada);
    $("saidaEntrada").textContent = ent.trim() ? ent : "(sem entrada)";
    var texto = saida == null ? "" : String(saida);
    var pre = $("saida");
    if (!texto.trim()) {
      pre.textContent = "(o programa não imprimiu nada)";
      pre.classList.add("console--vazio");
    } else {
      pre.textContent = texto;
      pre.classList.remove("console--vazio");
    }
    if (erro) {
      $("saidaErro").hidden = false;
      $("saidaErroTitulo").textContent = eLacoQueNaoTermina(erro)
        ? "Parece um laço que não termina"
        : "O programa parou com erro";
      $("saidaErroTexto").textContent = String(erro);
    } else {
      $("saidaErro").hidden = true;
      $("saidaErroTexto").textContent = "";
    }
  }

  function anexarEvt(col, classe, texto) {
    var wrap = document.createElement("span");
    wrap.className = "evt-passo";
    var tag = document.createElement("span");
    tag.className = "tag " + classe;
    tag.textContent = texto;
    wrap.appendChild(tag);
    col.appendChild(wrap);
  }

  function renderTrace(passos, entrada, meta) {
    passosAtuais = Array.isArray(passos) ? passos : [];
    var n = passosAtuais.length;
    $("traceVazio").hidden = true;
    $("traceConteudo").hidden = false;
    setContador("contTrace", String(n), null);
    var codeEnt = $("traceEntrada").querySelector("code");
    if (codeEnt) codeEnt.textContent = entrada || "";
    $("traceTruncado").hidden = !traceFoiTruncado(meta, n);
    var corpo = $("traceCorpo");
    corpo.replaceChildren();
    var anteriores = {};
    passosAtuais.forEach(function (p, i) {
      var tr = clonar("tpl-passo");
      tr.dataset.indice = String(i);
      tr.dataset.linha = p.linha == null ? "" : String(p.linha);
      tr.tabIndex = -1;
      tr.querySelector(".col-passo").textContent = String(i + 1);
      tr.querySelector(".col-linha").textContent = p.linha == null ? "" : String(p.linha);
      tr.querySelector(".col-codigo code").textContent = p.codigo || "";
      var colCodigo = tr.querySelector(".col-codigo");
      if (p.retornou != null) anexarEvt(colCodigo, "tag--retornou", "retornou " + txtVar(p.retornou));
      if (p.imprimiu != null) anexarEvt(colCodigo, "tag--imprimiu", "imprimiu " + txtVar(p.imprimiu));
      if (p.erro != null) anexarEvt(colCodigo, "tag--erro", txtVar(p.erro));
      var vars = tr.querySelector(".vars");
      var atuais = {};
      var mapa = p.variaveis && typeof p.variaveis === "object" ? p.variaveis : {};
      Object.keys(mapa).forEach(function (nome) {
        var valor = txtVar(mapa[nome]);
        atuais[nome] = valor;
        var chip = clonar("tpl-var");
        chip.querySelector("b").textContent = nome;
        var c = chip.querySelector("code");
        c.textContent = valor;
        c.title = valor;
        chip.title = valor;
        if (!Object.prototype.hasOwnProperty.call(anteriores, nome) || anteriores[nome] !== valor) {
          chip.classList.add("var--mudou");
        }
        vars.appendChild(chip);
      });
      anteriores = atuais;
      corpo.appendChild(tr);
    });
    var slider = $("traceSlider");
    slider.max = String(Math.max(0, n - 1));
    slider.value = "0";
    $("traceContador").textContent = n ? "Passo 1 de " + n : "Passo 0 de 0";
    if (n) selecionarPasso(0, false);
  }

  function selecionarPasso(i, focar) {
    var n = passosAtuais.length;
    if (!n) return;
    if (i < 0) i = 0;
    if (i >= n) i = n - 1;
    passoAtual = i;
    $("traceSlider").value = String(i);
    $("traceContador").textContent = "Passo " + (i + 1) + " de " + n;
    var linhas = $("traceCorpo").children;
    var atual = null;
    var k;
    for (k = 0; k < linhas.length; k++) {
      var on = k === i;
      linhas[k].classList.toggle("atual", on);
      if (on) atual = linhas[k];
    }
    if (!atual) return;
    atual.scrollIntoView({ block: "nearest" });
    if (focar) atual.focus();
    destacarLinha(passosAtuais[i].linha);
  }

  function moverPasso(delta) {
    if (!passosAtuais.length) return;
    selecionarPasso(passoAtual + delta, true);
  }

  function mostrarFalhas(falhas) {
    var n = falhas.length;
    ativarAba("abaTestes");
    $("testesVazio").hidden = true;
    $("testesConteudo").hidden = false;
    $("testesResumoTitulo").textContent = n === 1
      ? "Ainda falha em 1 teste"
      : "Ainda falha em " + n + " testes";
    setContador("contTestes", String(n), "aba__contador--erro");
    var lista = $("listaTestes");
    lista.replaceChildren();
    falhas.forEach(function (falha) {
      var li = clonar("tpl-teste");
      li.querySelector(".entrada").textContent = falha.entrada == null ? "" : String(falha.entrada);
      li.querySelector(".esperado").textContent = falha.esperado == null ? "" : String(falha.esperado);
      li.querySelector(".obtido").textContent = falha.obtido == null ? "" : String(falha.obtido);
      if (falha.erro != null) {
        li.querySelector(".erro-dt").hidden = false;
        var dd = li.querySelector(".erro");
        dd.hidden = false;
        dd.textContent = String(falha.erro);
      }
      li.querySelector(".btn-usar-entrada").addEventListener("click", function () {
        $("entrada").value = falha.entrada == null ? "" : String(falha.entrada);
        verTrace();
      });
      lista.appendChild(li);
    });
  }

  function faseDialogo(fase) {
    var dlg = $("dlgExplicar");
    dlg.dataset.fase = fase;
    dlg.querySelectorAll("[data-fase-conteudo]").forEach(function (el) {
      el.hidden = el.getAttribute("data-fase-conteudo") !== fase;
    });
  }

  function abrirExplicacao(r) {
    $("testesConteudo").hidden = true;
    $("testesVazio").hidden = false;
    $("listaTestes").replaceChildren();
    setContador("contTestes", "✓", "aba__contador--ok");
    faseDialogo("explicar");
    $("explicarMensagem").textContent = r.mensagem || "";
    $("explicacao").value = "";
    if (!$("dlgExplicar").open) $("dlgExplicar").showModal();
    $("explicacao").focus();
  }

  function mostrarRubrica(r) {
    mostrandoRubrica = true;
    pendente = r;
    faseDialogo("rubrica");
    var rub = r.rubrica || {};
    var pares = [
      [$("rubricaAnel"), pct(rub.nota)],
      [$("rubIdentificou"), pct(rub.identificou)],
      [$("rubCausa"), pct(rub.causa)],
      [$("rubCorrecao"), pct(rub.correcao)],
    ];
    pares.forEach(function (par) { par[0].style.setProperty("--v", "0"); });
    $("rubricaNota").textContent = pct(rub.nota) + "%";
    $("rubIdentificouTx").textContent = pct(rub.identificou) + "%";
    $("rubCausaTx").textContent = pct(rub.causa) + "%";
    $("rubCorrecaoTx").textContent = pct(rub.correcao) + "%";
    $("rubricaComentario").textContent = rub.comentario || "";
    $("rubricaExplicacao").textContent = textoExplicado;
    if (!$("dlgExplicar").open) $("dlgExplicar").showModal();
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        pares.forEach(function (par) { par[0].style.setProperty("--v", String(par[1])); });
      });
    });
    $("btnProximo").focus();
  }

  function abrirFim(r) {
    if (sessaoEncerrada && $("dlgFim").open) return;
    sessaoEncerrada = true;
    sessaoAtiva = false;
    pronto = false;
    clearTimeout(timerInat);
    if ($("dlgExplicar").open) $("dlgExplicar").close();
    setEstado("encerrada");
    $("fimMotivo").textContent = motivoLegivel(r && r.motivo);
    $("fimResolvidos").textContent = String(nResolvidos);
    $("fimExecucoes").textContent = String(nExecucoes);
    $("fimDicas").textContent = String(nDicas);
    var tudo = r && r.motivo === "resolveu todos os bugs disponíveis";
    renderProgresso(!tudo);
    if (!$("dlgFim").open) $("dlgFim").showModal();
  }

  function irProximo() {
    var r = pendente;
    pendente = null;
    mostrandoRubrica = false;
    if ($("dlgExplicar").open) $("dlgExplicar").close();
    if (r && r.bug_resolvido) nResolvidos++;
    if (r && r.bug && !r.encerrada) {
      setEstado(r.estado);
      renderBug(r.bug);
    } else {
      abrirFim(r || {});
    }
  }

  function tratar(r) {
    if (!r || typeof r !== "object") return;
    if (r.estado) setEstado(r.estado);
    if (r.resposta === "dica") {
      var msg = (r.mensagem || "").trim();
      if (msg) addMsgTreinador({ acao: "DAR_DICA", mensagem: r.mensagem, nivel: r.nivel, proativa: false });
      else addMsgSistema("Não consegui montar uma dica verificada agora. Tente rodar outras entradas e peça de novo.");
    }
    if (r.resposta === "correcao_incompleta") mostrarFalhas(r.falhas || []);
    if (r.resposta === "peca_explicacao") abrirExplicacao(r);
    if (r.resposta === "feedback_resposta" && r.feedback) {
      addMsgTreinador({ acao: "FEEDBACK", mensagem: r.feedback });
    }
    if (r.rubrica) mostrarRubrica(r);
    else if (r.intervencao) addMsgTreinador(r.intervencao);
    if (r.encerrada && !mostrandoRubrica) abrirFim(r);
  }

  function enviarSinais(dados) {
    return api("POST", "/evento", { tipo: "sinais", dados: dados }).then(function (r) {
      tratar(r);
      return r;
    }).catch(function (e) {
      toastErro(e);
      return null;
    });
  }

  function flushSinais() {
    if (!churn && !pausas) return Promise.resolve();
    var dados = { churn_edicao: churn, pausas_longas: pausas };
    churn = 0;
    pausas = 0;
    return enviarSinais(dados);
  }

  function comAcao(btn, fn, modo) {
    if (!pronto || ocupado || sessaoEncerrada) return Promise.resolve();
    ocupado = true;
    var botoes = BOTOES_ACAO.map($);
    if (btn) btn.setAttribute("aria-busy", "true");
    botoes.forEach(function (b) { b.disabled = true; });
    mostrarPensando(TEXTO_PENSANDO[modo] || TEXTO_PENSANDO.rodar);
    $("treinadorStatus").textContent = modo === "dica"
      ? "Investigando o seu código…"
      : "Pensando…";
    $("conversa").appendChild($("pensando"));
    $("conversa").scrollTop = $("conversa").scrollHeight;
    return Promise.resolve().then(fn).catch(function (e) {
      toastErro(e);
    }).then(function () {
      if (btn) btn.removeAttribute("aria-busy");
      botoes.forEach(function (b) { b.disabled = false; });
      esconderPensando();
      $("conversa").appendChild($("pensando"));
      $("treinadorStatus").textContent = "Observando você investigar";
      ocupado = false;
      if (!$("bastidores").hidden) atualizarBastidores();
    });
  }

  function rodar() {
    return comAcao($("btnRodar"), function () {
      var prep = Promise.resolve();
      if (!primeiraExec) {
        primeiraExec = true;
        prep = enviarSinais({ tempo_ate_primeira_execucao_s: Math.round((Date.now() - tInicio) / 1000) });
      }
      return prep.then(function () {
        if (sessaoEncerrada) return null;
        return flushSinais();
      }).then(function () {
        if (sessaoEncerrada) return null;
        var entrada = $("entrada").value;
        return api("POST", "/evento", {
          tipo: "rodou_entrada",
          dados: { entrada: entrada, codigo: $("codigo").value },
        }).then(function (r) {
          if (r.resposta === "resultado_execucao") {
            nExecucoes++;
            mostrarSaida(entrada, r.saida, r.erro);
          }
          tratar(r);
        });
      });
    }, "rodar");
  }

  function verTrace() {
    return comAcao($("btnTrace"), function () {
      var entrada = $("entrada").value;
      return api("POST", "/evento", {
        tipo: "ver_trace",
        dados: { entrada: entrada, codigo: $("codigo").value },
      }).then(function (r) {
        if (r.resposta === "trace") {
          nExecucoes++;
          renderTrace(r.passos || [], entrada, r);
          ativarAba("abaTrace");
        }
        tratar(r);
      });
    }, "trace");
  }

  function pedirDica() {
    return comAcao($("btnDica"), function () {
      return flushSinais().then(function () {
        if (sessaoEncerrada) return null;
        return api("POST", "/evento", {
          tipo: "pediu_dica",
          dados: { codigo: $("codigo").value },
        }).then(tratar);
      });
    }, "dica");
  }

  function submeter() {
    return comAcao($("btnSubmeter"), function () {
      return flushSinais().then(function () {
        if (sessaoEncerrada) return null;
        return api("POST", "/evento", {
          tipo: "submeteu_correcao",
          dados: { codigo: $("codigo").value },
        }).then(tratar);
      });
    }, "submeter");
  }

  function enviarExplicacao() {
    var texto = $("explicacao").value.trim();
    if (!texto) {
      $("explicacao").focus();
      return;
    }
    textoExplicado = texto;
    comAcao($("btnExplicar"), function () {
      return api("POST", "/evento", { tipo: "explicou", dados: { texto: texto } }).then(tratar);
    }, "explicar");
  }

  function responderPergunta(form, pergunta, resposta) {
    var btn = form.querySelector("button");
    comAcao(btn, function () {
      addMsgAluno(resposta);
      form.remove();
      return api("POST", "/evento", {
        tipo: "respondeu_pergunta",
        dados: { pergunta: pergunta, resposta: resposta },
      }).then(tratar);
    }, "responder");
  }

  function linhaNoCursor() {
    var ed = $("codigo");
    var v = ed.value;
    var i = ed.selectionStart;
    var ini = v.lastIndexOf("\n", i - 1) + 1;
    var fim = v.indexOf("\n", i);
    if (fim < 0) fim = v.length;
    return { ini: ini, fim: fim, texto: v.slice(ini, fim) };
  }

  function editarCodigo(inicio, fim, texto) {
    var ed = $("codigo");
    ed.setRangeText(texto, inicio, fim, "end");
    aposEdicao();
  }

  function pulsoAtividade() {
    if (!sessaoAtiva) return;
    clearTimeout(timerInat);
    timerInat = setTimeout(ficarInativo, INATIVIDADE_MS);
  }

  function ficarInativo() {
    if (!sessaoAtiva || sessaoEncerrada) return;
    api("POST", "/evento", { tipo: "inativo", dados: {} }).then(function (r) {
      if (mostrandoRubrica && pendente && pendente.bug_resolvido) nResolvidos++;
      mostrandoRubrica = false;
      pendente = null;
      abrirFim(r && r.motivo ? r : { motivo: "inatividade" });
    }).catch(function (e) {
      toastErro(e);
      pulsoAtividade();
    });
  }

  function prepararCarregando() {
    $("carregando").hidden = false;
    $("carregando").querySelector("p").textContent = "Preparando o seu desafio…";
    if (btnTentar) btnTentar.hidden = true;
  }

  function mostrarErroCarregando(e) {
    var box = $("carregando");
    box.hidden = false;
    var p = box.querySelector("p");
    var det = e && e.detalhe ? " " + e.detalhe : "";
    p.textContent = "Não consegui falar com o servidor." + det;
    if (!btnTentar) {
      btnTentar = document.createElement("button");
      btnTentar.className = "btn btn--primario";
      btnTentar.type = "button";
      btnTentar.style.marginTop = "12px";
      btnTentar.textContent = "Tentar de novo";
      btnTentar.addEventListener("click", function () { boot(); });
      p.insertAdjacentElement("afterend", btnTentar);
    }
    btnTentar.hidden = false;
  }

  function aplicarInicio(r) {
    sessaoEncerrada = false;
    sessaoAtiva = true;
    pronto = true;
    if (!r || r.encerrada || !r.bug) {
      abrirFim(r || {});
      return;
    }
    setEstado(r.estado);
    renderBug(r.bug);
    pulsoAtividade();
  }

  function resetLocal() {
    nResolvidos = 0;
    nExecucoes = 0;
    nDicas = 0;
    bugsVistos = 0;
    codigoOriginal = "";
    pendente = null;
    mostrandoRubrica = false;
    textoExplicado = "";
    primeiraExec = false;
    tInicio = Date.now();
    lastLen = 0;
    lastEdit = 0;
    churn = 0;
    pausas = 0;
    passosAtuais = [];
    bastVistos = 0;
    bastUltimo = null;
    $("feedBastidores").replaceChildren();
    limparConversa();
    renderProgresso(true);
  }

  function iniciarSessao() {
    prepararCarregando();
    return api("POST", "/iniciar").then(function (r) {
      $("carregando").hidden = true;
      aplicarInicio(r);
    }).catch(function (e) {
      sessaoAtiva = false;
      pronto = false;
      mostrarErroCarregando(e);
    });
  }

  function boot() {
    if (reiniciando) return Promise.resolve();
    reiniciando = true;
    prepararCarregando();
    return api("GET", "/info").then(function (info) {
      infoServidor = info;
      var el = $("infoModelo");
      if (el && info) {
        var txt = info.llm ? String(info.llm) : "";
        if (info.build) txt += (txt ? " · " : "") + String(info.build);
        el.textContent = txt;
      }
    }).catch(function () {
      infoServidor = null;
    }).then(iniciarSessao).then(function () {
      reiniciando = false;
    }, function () {
      reiniciando = false;
    });
  }

  function recomecar() {
    if (ocupado || reiniciando) return;
    reiniciando = true;
    pronto = false;
    sessaoAtiva = false;
    sessaoEncerrada = false;
    if ($("dlgFim").open) $("dlgFim").close();
    if ($("dlgExplicar").open) $("dlgExplicar").close();
    resetLocal();
    iniciarSessao().then(function () { reiniciando = false; });
  }

  function urlDemo() {
    return new URLSearchParams(location.search).has("demo");
  }

  $("codigo").addEventListener("input", aposEdicao);
  $("codigo").addEventListener("paste", function (e) {
    var txt = "";
    try { txt = (e.clipboardData || window.clipboardData).getData("text") || ""; } catch (err) { txt = ""; }
    enviarSinais({ colagens_externas: 1, texto: txt });
  });
  $("codigo").addEventListener("keydown", function (e) {
    var ed = $("codigo");
    if (e.key === "Tab" && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      if (e.shiftKey) {
        var lin = linhaNoCursor();
        var n = 0;
        while (n < 4 && lin.texto.charAt(n) === " ") n++;
        if (n) editarCodigo(lin.ini, lin.ini + n, "");
      } else {
        editarCodigo(ed.selectionStart, ed.selectionEnd, "    ");
      }
      return;
    }
    if (e.key === "Enter" && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      var atual = linhaNoCursor();
      var ind = 0;
      while (atual.texto.charAt(ind) === " ") ind++;
      var extra = atual.texto.trimEnd().endsWith(":") ? "    " : "";
      editarCodigo(ed.selectionStart, ed.selectionEnd, "\n" + " ".repeat(ind) + extra);
    }
  });

  $("entrada").addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      rodar();
    }
  });

  document.addEventListener("keydown", function (e) {
    var mod = e.ctrlKey || e.metaKey;
    if (mod && e.shiftKey && e.key.toLowerCase() === "d") {
      e.preventDefault();
      ligarDemoEAlternar();
      return;
    }
    if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && e.target && ABAS.indexOf(e.target.id) >= 0) {
      e.preventDefault();
      var i = ABAS.indexOf(e.target.id);
      var j = e.key === "ArrowRight" ? (i + 1) % ABAS.length : (i - 1 + ABAS.length) % ABAS.length;
      $(ABAS[j]).focus();
      ativarAba(ABAS[j]);
      return;
    }
    var noTrace = e.target && e.target.closest && e.target.closest("#painelTrace");
    if ((e.key === "ArrowLeft" || e.key === "ArrowRight") && noTrace && !$("painelTrace").hidden && e.target !== $("traceSlider")) {
      e.preventDefault();
      moverPasso(e.key === "ArrowRight" ? 1 : -1);
      return;
    }
    if (mod && e.key.toLowerCase() === "s" && !e.shiftKey) {
      e.preventDefault();
      var dlgS = $("dlgExplicar").open || $("dlgFim").open;
      if (!dlgS) submeter();
      return;
    }
    if (mod && e.key === "Enter") {
      if (e.target && e.target.id === "explicacao" && !e.shiftKey) {
        e.preventDefault();
        $("formExplicar").requestSubmit();
        return;
      }
      var dlg = $("dlgExplicar").open || $("dlgFim").open;
      if (dlg) return;
      e.preventDefault();
      if (e.shiftKey) verTrace();
      else rodar();
    }
  });

  ["input", "keydown", "click"].forEach(function (nome) {
    document.addEventListener(nome, pulsoAtividade, true);
  });

  ABAS.forEach(function (id) {
    $(id).addEventListener("click", function () { ativarAba(id); });
  });
  $("btnRodar").addEventListener("click", rodar);
  $("btnTrace").addEventListener("click", verTrace);
  $("btnDica").addEventListener("click", pedirDica);
  $("btnSubmeter").addEventListener("click", submeter);
  $("tracePrev").addEventListener("click", function () { moverPasso(-1); });
  $("traceNext").addEventListener("click", function () { moverPasso(1); });
  $("traceSlider").addEventListener("input", function () {
    selecionarPasso(Number($("traceSlider").value), false);
  });
  $("traceCorpo").addEventListener("click", function (e) {
    var tr = e.target.closest("tr");
    if (!tr || tr.dataset.indice == null || tr.dataset.indice === "") return;
    selecionarPasso(Number(tr.dataset.indice), true);
  });

  $("formExplicar").addEventListener("submit", function (e) {
    e.preventDefault();
    enviarExplicacao();
  });
  $("dlgExplicar").addEventListener("cancel", function (e) {
    e.preventDefault();
    if ($("dlgExplicar").dataset.fase === "rubrica") irProximo();
  });
  $("btnProximo").addEventListener("click", irProximo);
  $("dlgFim").addEventListener("cancel", function (e) { e.preventDefault(); });
  $("btnRecomecar").addEventListener("click", recomecar);

  $("btnSair").addEventListener("click", function () {
    if (sessaoEncerrada || !pronto) return;
    if (!confirm("Encerrar a sessão? Seu progresso neste desafio será perdido.")) return;
    api("POST", "/evento", { tipo: "sair", dados: {} }).then(function (r) {
      abrirFim(r && r.motivo ? r : { motivo: "aluno pediu para sair" });
    }).catch(function (e) { toastErro(e); });
  });

  $("btnRestaurar").addEventListener("click", function () {
    if (!confirm("Restaurar o código original deste desafio?")) return;
    var ed = $("codigo");
    ed.value = codigoOriginal;
    lastLen = ed.value.length;
    atualizarGutter();
    esconderDestaque();
    atualizarModificado();
  });

  $("btnFecharGuia").addEventListener("click", function () {
    $("guia").hidden = true;
    try { localStorage.setItem("arandu.guia.fechado", "1"); } catch (e) { /* storage bloqueado */ }
  });
  try {
    if (localStorage.getItem("arandu.guia.fechado") === "1") $("guia").hidden = true;
  } catch (e) { /* storage bloqueado */ }

  $("btnBastidores").addEventListener("click", function () {
    setBastidores($("bastidores").hidden);
  });
  $("btnFecharBastidores").addEventListener("click", function () { setBastidores(false); });
  if (urlDemo()) $("btnBastidores").hidden = false;

  renderProgresso(true);
  boot();
})();
