"use strict";
(function () {
  function $(id) { return document.getElementById(id); }

  function clonar(id) {
    var tpl = $(id);
    if (!tpl || !tpl.content || !tpl.content.firstElementChild) return null;
    return tpl.content.firstElementChild.cloneNode(true);
  }

  function texto(v) {
    if (v == null) return "";
    return String(v);
  }

  function valorOuVazio(v) {
    if (v == null || v === "") return "(vazio)";
    return String(v);
  }

  function acrescentar(det, k, v, classe) {
    var row = clonar("tpl-det");
    if (!row) return false;
    var kk = row.querySelector(".det__k");
    var vv = row.querySelector(".det__v");
    if (!kk || !vv) return false;
    kk.textContent = k;
    vv.textContent = v;
    if (classe) vv.classList.add(classe);
    det.appendChild(row);
    return true;
  }

  function preencher(node, ev) {
    if (!node || !ev || typeof ev !== "object") return;
    if (!clonar("tpl-det") || !clonar("tpl-hip")) return;
    var det = node.querySelector(".evento__det");
    if (!det) return;
    var added = false;

    var ul = det.querySelector(".det-hips");
    if (ul && Array.isArray(ev.hipoteses) && ev.hipoteses.length) {
      var nHips = 0;
      ev.hipoteses.forEach(function (h) {
        if (!h || typeof h !== "object") return;
        var li = clonar("tpl-hip");
        if (!li) return;
        var idEl = li.querySelector(".det-hip__id");
        var descEl = li.querySelector(".det-hip__desc");
        var eqEl = li.querySelector(".det-hip__eq");
        if (!idEl || !descEl || !eqEl) return;
        idEl.textContent = texto(h.id);
        descEl.textContent = texto(h.descricao);
        eqEl.textContent = texto(h.rotulo || h.equivoco);
        ul.appendChild(li);
        nHips++;
      });
      if (nHips) {
        ul.hidden = false;
        added = true;
      }
    }

    if (ev.experimento && typeof ev.experimento === "object") {
      var ex = ev.experimento;
      if (acrescentar(det, "entrada", valorOuVazio(ex.entrada))) added = true;
      if (acrescentar(det, "seu código", valorOuVazio(ex.saida_aluno), ex.divergiu ? "det__v--diverge" : "")) added = true;
      if (acrescentar(det, "esperado", valorOuVazio(ex.saida_ref))) added = true;
      var resultado = ex.divergiu ? "divergiu: separa as hipóteses" : "mesma saída: não separa";
      if (acrescentar(det, "resultado", resultado, "det__v--texto")) added = true;
    }

    if (ev.sobreviventes != null) {
      var ids = Array.isArray(ev.sobreviventes) ? ev.sobreviventes : [ev.sobreviventes];
      var partes = [];
      ids.forEach(function (id) {
        if (id == null || id === "") return;
        partes.push(String(id));
      });
      if (acrescentar(det, "restaram", partes.length ? partes.join(", ") : "nenhuma")) added = true;
    }
    if (ev.raciocinio != null && texto(ev.raciocinio) !== "") {
      if (acrescentar(det, "por quê", texto(ev.raciocinio), "det__v--texto")) added = true;
    }

    if (ev.conclusivo !== undefined && ev.equivoco) {
      if (acrescentar(det, "equívoco", texto(ev.rotulo || ev.equivoco), "det__v--texto")) added = true;
      var certeza = ev.conclusivo
        ? "sobrou uma hipótese"
        : "inconclusivo; usei a entrada que falha";
      if (acrescentar(det, "certeza", certeza, "det__v--texto")) added = true;
    }

    if (ev.verificador && typeof ev.verificador === "object") {
      var vd = ev.verificador;
      var rej = vd.rejeicoes || 0;
      var frase;
      if (vd.rebaixado) frase = "barrou " + rej + " vezes; mandei uma pergunta segura";
      else if (rej) frase = "aprovou depois de " + rej + " reprovação(ões)";
      else frase = "aprovou";
      var clsV = (vd.aprovado && !vd.rebaixado) ? "det__v--ok" : "det__v--texto";
      if (acrescentar(det, "Verificador", frase, clsV)) added = true;
    }

    if (Array.isArray(ev.ancoras)) {
      ev.ancoras.forEach(function (a) {
        if (!a || typeof a !== "object") return;
        var v = valorOuVazio(a.entrada) + " → " + valorOuVazio(a.saida_aluno) + " (esperado " + valorOuVazio(a.saida_ref) + ")";
        if (acrescentar(det, "evidência", v, a.divergiu ? "det__v--diverge" : "")) added = true;
      });
    }

    if (added) det.hidden = false;
  }

  window.AranduEvidencia = { preencher: preencher };
})();
