# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: beginner Python students** in their first programming course (persona "Marina"; context includes the interior of Amazonas, Brazil). They practice debugging alone, outside any online judge, on short programs that run without crashing but give a wrong answer. Their job: find the logic error by running inputs and reading variable values, fix it, and explain it in one sentence.
- **Secondary: hackathon jury / demo audience.** They need to see that the agent decides and verifies (hypotheses, discriminating experiments, Verifier blocks). The agent's reasoning must be showable on demand and hideable so it never clutters or spoils the student's view.
- **Secondary: teachers / coordination.** A light class-level misconception view is in scope for the MVP; the full teacher dashboard is a later phase.

## Product Purpose

Arandu (Tupi for "knowledge") is an autonomous debugging trainer. It hands the student a realistic silent-failure bug, lets them investigate (run inputs, step through variables), and intervenes only when useful, climbing a feedback ladder (question, failing test, where behavior diverges with real values, next step, misconception name). It never gives the corrected code. Success: the student fixes the bug, explains it, and gets better at debugging across sessions.

## Positioning

Online judges only say right or wrong. Arandu teaches the act of debugging itself, and every claim the agent makes about the code was proven by actually executing it (hypotheses, then an input that separates them, then an instrumented run). A Verifier blocks any message without execution evidence or that would reveal the solution.

## Operating Context

- Used on desktop/notebook browsers with a normal internet connection; served locally by `python3 arandu-m3/servidor_web.py` at `http://localhost:8002`.
- Live demo in front of a jury: the student session is shown, and the agent reasoning is toggled on to prove autonomy.
- A session runs challenge after challenge: investigate, submit, explain, see the rubric, next challenge. Agent calls take ~2–4 s; a hint with investigation can take much longer (no streaming).

## Capabilities and Constraints

- Student surface (`arandu-m3/web/index.html`): problem statement, editable buggy code, input (function call or stdin), run output and runtime errors, step-by-step variable trace, hidden-test submission with failing cases (input, expected, obtained, error), trainer messages (hint with level 1–5, question with reply, show values, suggest test, encourage), one-sentence explanation, rubric (identified, cause, correction, score, comment), end of session.
- Agent panel (`arandu-m3/web/painel.html`) and an in-session toggleable "Bastidores" drawer: timeline of reading, decision (+ confidence), investigation, speech/hint, Verifier blocks, student actions; student model (mastery per misconception, debugging skills, interface signals).
- Integration contract: plain HTML/CSS with `<template>` elements cloned by vanilla JS (`arandu-m3/web/js/aluno.js`, `arandu-m3/web/js/painel.js`); element IDs are part of the contract. No framework, no build step.
- Not yet available in the backend: class/teacher aggregation, ablation metric, cost per session, valid-bug rate, total number of challenges, multi-user sessions. The UI may reserve places for them but must not fabricate values.
- Terminology (Portuguese UI): desafio, treinador, dica, passo a passo, equívoco, Verificador, bastidores.

## Brand Commitments

Name "Arandu" and its meaning (Tupi, "knowledge"), plus a connection to the Amazon (never as caricature: no leaves or forest-green overload).

The user approved the current palette (deep forest green, amber, warm neutrals, dark code surface) and the current layout (mission + trainer left, editor + test bench right, toggleable agent drawer). Standing preference: the category standard, executed with craft. Refinements must preserve palette and layout and remove generic AI-generated tells rather than reinvent the identity. Rejected looks: childish/gamified, dark neon "hacker IDE", generic corporate SaaS, caricatured Amazon.

## Evidence on Hand

- Project brief: `Projeto-Arandu.pdf` (repo root), `docs/contexto-projeto-arandu.md`.
- Real bug bank: 8 items from Refactory (misconceptions `ComparisonWithBoolLiteral`, `MapToBooleanWithIf`, `ParenthesesOnlyIfArgument`); synthetic variants for LGPD.
- Cited stats (from the brief): INEP ~23% failure/dropout in programming logic; UFPR study: 79% of those who failed Algorithms dropped out.
- No logo, testimonials, pilot results, or ablation numbers exist yet; do not invent them.

## Product Principles

1. Never hand over the answer; guide toward it.
2. Every agent statement is backed by a real execution the student could reproduce.
3. The student's workspace stays calm and focused; agent internals are for the jury and teacher, shown only on demand.
4. Silence is a valid intervention; the trainer speaks only when it helps.
5. Show real values, not abstractions: debugging is learned by looking at what the program actually did.

## Accessibility & Inclusion

Beginners with little programming vocabulary: plain Portuguese, no internal jargon (no model names, build strings, or misconception IDs on the student surface). Keyboard-operable editor and controls.
