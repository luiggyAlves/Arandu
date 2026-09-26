---
name: Arandu
description: A code-practice bench on cool paper, with canopy green for the frame and one amber sun for whatever is live.
colors:
  papel: "#F1F4F2"
  superficie: "#FFFFFF"
  superficie-2: "#F6F8F7"
  linha: "#DCE2DF"
  linha-forte: "#C2CAC6"
  tinta: "#16211E"
  tinta-2: "#45524D"
  tinta-3: "#5B6661"
  neutro: "#E8ECEA"
  floresta: "#1B6B5A"
  floresta-hover: "#155646"
  floresta-escura: "#0E3B31"
  floresta-clara: "#E2EFEA"
  sol: "#E39B2D"
  sol-hover: "#D68D1F"
  sol-escuro: "#7A4F0C"
  sol-claro: "#FCF1DE"
  sol-tinta: "#2B1A02"
  erro: "#B3261E"
  erro-claro: "#FBEAE7"
  ok: "#17704A"
  ok-claro: "#E2F3EA"
  info: "#2D6A9F"
  info-claro: "#E8F0F8"
  codigo-bg: "#0F1C19"
  codigo-bg-2: "#13241F"
  codigo-tx: "#DCEFE8"
  codigo-gutter: "#6A8A80"
  codigo-hl: "rgba(227, 155, 45, .17)"
typography:
  display:
    fontFamily: '"Atkinson Hyperlegible Next", system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "28px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  headline:
    fontFamily: '"Atkinson Hyperlegible Next", system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "22px"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.02em"
  title:
    fontFamily: '"Atkinson Hyperlegible Next", system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "14px"
    fontWeight: 700
    letterSpacing: "normal"
  body:
    fontFamily: '"Atkinson Hyperlegible Next", system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  metric:
    fontFamily: '"Atkinson Hyperlegible Next", system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "40px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.03em"
  subhead:
    fontFamily: '"Atkinson Hyperlegible Next", system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "18px"
    fontWeight: 700
    letterSpacing: "-0.015em"
  label:
    fontFamily: '"Atkinson Hyperlegible Next", system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "13px"
    fontWeight: 600
    letterSpacing: "normal"
  caption:
    fontFamily: '"Atkinson Hyperlegible Next", system-ui, -apple-system, "Segoe UI", sans-serif'
    fontSize: "12px"
    fontWeight: 400
    letterSpacing: "normal"
  code:
    fontFamily: '"Atkinson Hyperlegible Mono", ui-monospace, "Cascadia Code", "SF Mono", Consolas, monospace'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "22px"
rounded:
  xs: "2px"
  sm: "4px"
  md: "6px"
  lg: "8px"
spacing:
  control: "6px"
  field: "8px"
  stack: "12px"
  panel: "16px"
  bar: "20px"
  dialog: "24px"
components:
  button-primary:
    backgroundColor: "{colors.floresta}"
    textColor: "{colors.superficie}"
    rounded: "{rounded.md}"
    padding: "0 13px"
    height: "34px"
  button-primary-hover:
    backgroundColor: "{colors.floresta-hover}"
    textColor: "{colors.superficie}"
  button-sun:
    backgroundColor: "{colors.sol}"
    textColor: "{colors.sol-tinta}"
    rounded: "{rounded.md}"
    padding: "0 13px"
    height: "34px"
  button-sun-hover:
    backgroundColor: "{colors.sol-hover}"
    textColor: "{colors.sol-tinta}"
  button-default:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.md}"
    padding: "0 13px"
    height: "34px"
  button-default-hover:
    backgroundColor: "{colors.superficie-2}"
    textColor: "{colors.tinta}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.tinta}"
    rounded: "{rounded.md}"
    padding: "0 13px"
    height: "34px"
  button-ghost-hover:
    backgroundColor: "rgba(0, 0, 0, .05)"
    textColor: "{colors.tinta}"
  button-sm:
    padding: "0 10px"
    height: "30px"
  button-lg:
    padding: "0 18px"
    height: "42px"
  card:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    typography: "{typography.title}"
    rounded: "{rounded.lg}"
    padding: "16px"
  input:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta}"
    typography: "{typography.code}"
    rounded: "{rounded.md}"
    padding: "7px 11px"
    height: "34px"
  chip:
    backgroundColor: "{colors.superficie}"
    textColor: "{colors.tinta-2}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "28px"
  chip-pressed:
    backgroundColor: "{colors.floresta-escura}"
    textColor: "{colors.superficie}"
    rounded: "{rounded.md}"
    height: "28px"
  pill:
    backgroundColor: "{colors.floresta-clara}"
    textColor: "{colors.floresta-escura}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "0 9px"
    height: "24px"
  tag:
    backgroundColor: "{colors.neutro}"
    textColor: "{colors.tinta-2}"
    rounded: "3px"
    padding: "0 7px"
    height: "20px"
  message-hint:
    backgroundColor: "{colors.sol-claro}"
    textColor: "{colors.tinta}"
    padding: "10px 12px"
  message-student:
    backgroundColor: "{colors.floresta}"
    textColor: "{colors.superficie}"
    padding: "10px 12px"
  topbar:
    backgroundColor: "{colors.floresta-escura}"
    textColor: "#EAF3EF"
    padding: "0 20px"
    height: "52px"
  editor:
    backgroundColor: "{colors.codigo-bg}"
    textColor: "{colors.codigo-tx}"
    typography: "{typography.code}"
---

# Design System: Arandu

## Overview

**Creative North Star: "The Clearing Bench"**

Arandu is a code-practice bench. The ground is cool paper with a green cast. A night-canopy bar holds the session. White panels sit on hairlines. The program itself is a dark ink well. One amber, Clearing Sun, marks whatever is live: the trainer's hint, the traced line, the current challenge, an unsaved file, the period after the wordmark.

The student works a fixed bench: mission and trainer on the left, editor over the test bench on the right. The trainer speaks rarely, in plain sentences, on a wash that matches the kind of help. Agent reasoning stays off that bench until someone opens Bastidores for a jury. The agent panel reuses the same panels as a dashboard capped at 1480px.

Density is tight and even. The interface face is chosen so 0 and O, and 1, l, and I, stay distinct. Titles are sentence case. Status is a word. Panels stay free of blur, glow, and gradient. Motion is short, transform and opacity on an exit curve, and it gets out of the way when the reader asks for less motion.

**Key Characteristics:**

- Cool paper ground, night-canopy bar, white hairline panels, dark code well
- Forest green for the frame and primary actions; amber only for what is live
- Atkinson Hyperlegible Next for the interface, Atkinson Hyperlegible Mono for code and data
- Corners at 4px, 6px, and 8px; panel titles at 14px / 700, sentence case
- Status as words; Bastidores closed until the jury opens it; timeline markers differ by color and shape
- Motion is transform and opacity on the exit curve, and reduced motion wins

## Colors

The palette is a canopy, a sun, a river, and cool paper. Forest green frames the work. Amber is scarce. The page never floods with green, and it never paints the forest as leaves.

### Primary

- **Canopy Green** (#1B6B5A): primary buttons, links, the selected tab underline, the student's own messages, guide numbers, and the default score bar.
- **Pressed Canopy** (#155646): hover on primary buttons.
- **Night Canopy** (#0E3B31): the top bar, pressed filter chips, and the strong end of the canopy.
- **Canopy Wash** (#E2EFEA): the first-run guide, the default status label, and the "returned" tag.

### Secondary

- **Clearing Sun** (#E39B2D): the live accent. Hint tags, the traced line's gutter numeral, the current progress segment, the unsaved-file fill, the caret, the wordmark's period, and the keyboard focus outline.
- **Sun Press** (#D68D1F): hover on the sun button.
- **Burnt Amber** (#7A4F0C): text and ticks on a gold wash (hint level, drawer warning).
- **Gold Wash** (#FCF1DE): hint bubbles, the active trace row, and the drawer's warning strip.
- **Sun Ink** (#2B1A02): text on Clearing Sun (the sun button, a changed variable name, the active line number).

### Tertiary

- **River Blue** (#2D6A9F): question bubbles, the "printed" tag, reading and investigation markers, and the correction score bar.
- **River Wash** (#E8F0F8): the question bubble fill.

### Neutral

- **Cool Paper** (#F1F4F2): the page ground.
- **Card White** (#FFFFFF): panels, fields, dialogs.
- **Quiet Paper** (#F6F8F7): the recessed fill inside a panel (signature block, trainer bubbles at rest, definition labels).
- **Hairline** (#DCE2DF): the 1px edge of every panel, tab row, and table rule.
- **Strong Hairline** (#C2CAC6): control borders and the dashed "still working" bubble.
- **Canopy Ink** (#16211E): primary text.
- **Secondary Ink** (#45524D): supporting copy, the mission statement.
- **Meta Ink** (#5B6661): status lines, timestamps, empty states, floating field labels.
- **Cool Gray** (#E8ECEA): tags, idle tab counts, the neutral label.
- **Signal Red** (#B3261E): runtime errors, failing tests, verifier-blocked events, alert toasts.
- **Blush** (#FBEAE7): error blocks and the failing-test summary.
- **Verified Green** (#17704A): passing tests and the pass summary.
- **Verified Wash** (#E2F3EA): the pass summary fill and the encourage tag.
- **Code Night** (#0F1C19): the editor and the console.
- **Gutter Night** (#13241F): the line-number column.
- **Code Mist** (#DCEFE8): program text.
- **Gutter Sage** (#6A8A80): idle line numbers and empty console text.
- **Trace Wash** (rgba(227, 155, 45, .17)): the full-width wash behind the traced line.

**The One Sun Rule.** Clearing Sun appears only on what is live right now: the hint, the traced line, the current challenge segment, the unsaved file, the caret, the wordmark's period, and the 2px keyboard focus outline. A second sun used as decoration breaks the bench.

**The Canopy Frame Rule.** Night Canopy is the bar. Canopy Green is the primary action and the student's words. The page ground stays Cool Paper. Green does not flood the panels, and the mark is the word "Arandu" plus a sun period, with no leaf.

## Typography

**UI font:** Atkinson Hyperlegible Next (with system-ui, Segoe UI, sans-serif), loaded from Google Fonts at 400, 500, 600, and 700.
**Code font:** Atkinson Hyperlegible Mono (with ui-monospace, Cascadia Code, SF Mono, Consolas, monospace), loaded from Google Fonts at 400, 600, and 700.

**Character:** A legibility pair. The UI face is plain and slightly closed, so a beginner can read Portuguese instructions without a display costume. The mono is reserved for program text and values, where confusing 0/O or 1/l/I is the actual bug. Body copy sets tabular numerals.

### Hierarchy

- **Display** (700, 28px, line-height 1.25, tracking -0.025em): the agent panel's page title.
- **Headline** (700, 22px, line-height 1.25, tracking -0.02em): the mission title and dialog titles. The wordmark is the same weight at 19px, tracking -0.015em, with a Clearing Sun period.
- **Title** (700, 14px, sentence case, no extra tracking): panel titles ("Missão", "Treinador", "Linha do tempo do raciocínio") and dashboard subtitles. On the agent panel a 16px monochrome stroke icon may sit beside the title, in Meta Ink, with no tinted disc behind it.
- **Body** (400, 15px, line-height 1.5): interface copy. The mission statement caps at 68ch. Explanation text uses this size in a field.
- **Label** (600, 13px, sentence case, tracking normal): session status, progress text, pills, the trainer's status line. Tags and floating field labels step down to 12px / 600. Nothing in the ramp is uppercase.
- **Code** (400, 14px, line-height 22px): the editor. The console and signatures step to 13px. Variable chips are 12px. Line numbers in the gutter are 13px.

**The Sentence Case Rule.** Panel titles, tabs, buttons, and status are sentence case at the sizes above. There is no tracked uppercase eyebrow above a heading.

**The Two Faces Rule.** Atkinson Hyperlegible Next sets the interface. Atkinson Hyperlegible Mono sets code, signatures, console output, inputs on the bench, and variable values. Mono is not a costume for labels.

## Layout

The student session is a full-viewport bench under a 52px sticky bar. The grid is `minmax(340px, 390px)` beside a fluid column, gap 12px, inset 12px 16px 16px, height `calc(100dvh - 52px)`. The left column stacks the mission (at most half the column) over the trainer. The right column gives the editor about 58% and the test bench the rest, with 12px between them.

Opening Bastidores reserves a 380px drawer: the bench's right inset becomes `16px + 380px`. Below 1280px the drawer overlays and the bench keeps its 16px inset. Below 1080px the bench becomes one column: mission, then editor and test bench, then the trainer (at least 360px). Below 640px the page inset drops to 10px, the run controls wrap, the drawer is full width, and the trace table collapses to line number plus code.

The agent panel is the same panels in a dashboard: 20px inset, 16px gaps, max-width 1480px. A single stats strip divides into six cells (three from 1280px, two from 640px). Below that, the timeline takes 1.5 shares and the student model takes 1, stacking at 1080px.

The recurring space steps are 6px inside control groups, 8px between a field and its button, 12px between panels, 16px as the panel inset, 20px as the bar and dashboard inset, and 24px inside a dialog.

**The Bench Rule.** New student surfaces keep this split: task and trainer on the left, code and the test bench on the right, status and actions in the bar. The agent view is a dashboard of the same panels, not a second visual language.

**The Closed Drawer Rule.** Bastidores (`#bastidores`) is hidden on load, and so is its toggle until the session is in demo mode. It opens only when the jury asks. The warning strip on the drawer says the student does not see that column.

## Elevation & Depth

Panels are flat. A card is Card White, a 1px Hairline, and an 8px corner. Depth inside the bench comes from Quiet Paper recessed inside a panel, and from the code well, which is a dark surface set into the card with no shadow of its own.

Three overlays lift, all in canopy-tinted ink, never a neutral gray glow:

- **Dialog and toast** (`box-shadow: 0 16px 48px rgba(14, 59, 49, .22), 0 2px 6px rgba(14, 59, 49, .10)`): explanation, rubric, end of session, and toasts.
- **Drawer** (`box-shadow: -12px 0 32px rgba(14, 59, 49, .08)`): Bastidores, plus a 1px Hairline on its left edge.
- **Backdrop** (`rgba(14, 33, 28, .5)`): a flat dim behind dialogs. No blur.

Keyboard focus is a 2px Clearing Sun outline, 2px outside the control. Fields replace the outline with a Canopy Green border and a 3px ring (`0 0 0 3px rgba(27, 107, 90, .14)`); the question reply uses River Blue and `rgba(45, 106, 159, .15)`. That ring is focus, not a resting glow.

**The Hairline Rule.** Panels, the stats strip, and the code well do not wear a shadow, a blur, or a gradient. The only lifted surfaces are the dialog, the toast, and the reasoning drawer.

**The Exit Ease Rule.** Entrances (messages, timeline events), the drawer, dialogs, and toasts move with transform and opacity on `--saida` (`cubic-bezier(.16, 1, .3, 1)`), over 250–300ms. Score bars grow with `scaleX` on the same curve over 700ms. The busy spinner rotates linearly. `@media (prefers-reduced-motion: reduce)` collapses animation and transition.

## Shapes

Corners are tight and squared-off. The scale is 4px for status labels, 6px for buttons, fields, chips, and consoles, and 8px for panels. Tags, tab counts, variable chips, and keycaps sit at 3px. Dialogs step to 10px, once, and that step is not a license to round the bench further.

Trainer bubbles cut the top-left corner to 2px and keep 8px elsewhere. The student's bubble mirrors that cut on the top-right. Progress is a row of 16×4px ticks at 1px radius. Hint level is five 9×4px ticks. Filter chips are 6px, not capsules. The status label called a pill in the markup is 4px radius and 24px tall.

The unsaved-file mark is a 7px circle: a hairline ring while the file is clean, Clearing Sun when it is modified. Timeline markers are 9px, and each kind has its own silhouette (see Components). Empty states are a sentence. The decorative marks in the sprite (leaf, owl, trophy) are not drawn.

**The Tight Corner Rule.** Reuse 4px, 6px, and 8px. Do not introduce capsule pills, 14px cards, or a score ring.

## Components

Controls feel like a desktop tool: 600 weight, 6px corners, a 1px press (translate 1px down), and 45% opacity when disabled. A busy button hides its label and shows a 14px spinner.

### Buttons

- **Shape:** 6px radius, height 34px, padding 0 13px, label 14px / 600. Small is 30px and 13px type; large is 42px and 15px type.
- **Primary:** Canopy Green fill, white text, same-color border. Hover is Pressed Canopy. "Rodar" and "Enviar correção" are primary.
- **Sun:** Clearing Sun fill, Sun Ink text. Hover is Sun Press. This is the trainer's action ("Pedir dica"), not a general primary.
- **Default:** Card White, Strong Hairline, Canopy Ink. Hover warms the fill to Quiet Paper and darkens the border to Meta Ink. "Passo a passo" is default.
- **Ghost:** transparent, no border. Hover is black at 5% opacity. On the night bar the label is mist (`#D4E6DF`) and the hover is white at 8%; pressed is white at 14%.
- **Focus:** the 2px Clearing Sun outline. Pressed state drops 1px. Disabled is 45% opacity and does not drop.

### Chips

- **Style:** 28px tall, 6px radius, 1px Strong Hairline, Card White, Secondary Ink, 13px / 600, padding 0 10px. Counts sit at 70% opacity.
- **State:** pressed chips fill Night Canopy with white text. They filter the timeline; they are not capsules and they have no status dot.

### Cards / Containers

- **Corner style:** 8px.
- **Background:** Card White on Cool Paper.
- **Shadow strategy:** none. See Elevation.
- **Border:** 1px Hairline. The mission, trainer, editor, and dashboard cards rule the header off with the same line.
- **Internal padding:** header 10px 16px (min-height 44px; the trainer header is 52px); body 4px 16px 16px. The title is 14px / 700, sentence case.

### Inputs / Fields

- **Style:** bench fields are mono at 14px, min-height 34px, padding 7px 11px, 6px radius, Strong Hairline. The label floats on the top border at 12px / 600, Meta Ink, with a Card White notch.
- **Focus:** outline removed; border becomes Canopy Green and the 3px canopy ring appears. The question reply uses a river border (`#BCD0E6`) and the river ring.
- **Error:** a runtime error is a separate Blush block under the console, Signal Red mono text, a `#F0C4BE` border, and a 16px alert icon. Disabled buttons fade to 45%. Empty states center a 14px Meta Ink sentence. No icon.

### Navigation

The top bar is 52px, Night Canopy, inset 0 20px, sticky. The mark is the word "Arandu" at 19px / 700 plus a Clearing Sun period, then a 13px subtitle (`#A9C9BE`). Progress is 16×4px ticks (idle white at 18% opacity, done `#7FC8A9`, current Clearing Sun) and a 13px label (`#C3DBD2`). Session status is plain text on the bar (`#C3DBD2`, weight 500): "Investigando", "Explicando", "Encerrada". No dot, no pulse.

Tabs are a 38px row on a Hairline. Idle tabs are Meta Ink at 14px / 600. Hover becomes Canopy Ink. The selected tab is Night Canopy with a 2px Canopy Green underline, inset 6px from each side. Counts are 18px square chips; an error count fills Signal Red and a pass fills Verified Green.

### Trainer messages

Bubbles sit on the left, padding 10px 12px, Quiet Paper, Hairline, the cut corner, and rise 6px over 300ms. Hint bubbles switch to Gold Wash with a `#EFD6A6` border and a solid sun tag. Question bubbles use River Wash with a `#C9DBEE` border and a River Blue tag. The student's bubble sits on the right, at most 88% wide, Canopy Green, white text, the opposite cut; its meta line is `#B7DCCF`. System lines are centered, 12px, Meta Ink, between hairlines. Hint level is five ticks in Burnt Amber plus a word ("nível"). The working state is a dashed Strong Hairline bubble with a sentence and the elapsed seconds. The thread footer is a Hairline, 13px Meta Ink, and the sun button.

### Editor

The well fills the card: Code Night, Code Mist at 14px on a 22px line, 14px padding, a Gutter Night column. The active line number is Sun Ink on Clearing Sun. A Trace Wash marks the traced line. The caret is Clearing Sun. Selection is `rgba(127, 200, 169, .32)` in the editor and Clearing Sun at 30% opacity on the page. The console reuses the well at 13px / 1.55 inside a 6px block.

### Reasoning timeline

A 1px Hairline runs down the feed. Each event is a 9px marker on that line, told apart by color and shape, with any emoji in the node hidden (`font-size: 0`):

- Reading: River Blue square (2px corner).
- Decision: Canopy Green diamond (the square rotated 45deg); the sentence is 700.
- Investigation: River Blue circle.
- Speech or hint: Clearing Sun square.
- Student or trace: hollow circle, Meta Ink ring.
- Verifier block: Signal Red square; the sentence is Signal Red.

A decision's confidence is a 36×3px track filled with Canopy Green via `scaleX`. The same feed is used in the drawer and on the agent panel.

### Rubric

The score is a 40px / 700 numeral in Night Canopy, tracking -0.03em. It is not a ring. The three criteria are 6px tracks filled by `scaleX`: Canopy Green, Clearing Sun, River Blue.

**The Plain Status Rule.** Session status and the trainer's status are words. They do not lead with a dot, and nothing in the status pulses.

**The Marker Rule.** Timeline events are distinguished by the marker's color and shape together. A reading and an investigation can share River Blue because one is a square and the other is a circle. Emoji is not the marker.

## Do's and Don'ts

### Do:

- **Do** set the page on Cool Paper, panels on Card White with a 1px Hairline and an 8px corner, the bar on Night Canopy, and code on Code Night.
- **Do** keep Clearing Sun for the live state only: the hint, the traced line and its gutter numeral, the current progress segment, the unsaved-file mark, the caret, the wordmark's period, and the 2px keyboard focus outline.
- **Do** load Atkinson Hyperlegible Next and Atkinson Hyperlegible Mono from Google Fonts. Use Next for the interface and Mono for code, signatures, console output, bench fields, and variable values.
- **Do** title panels in sentence case at 14px / 700. Write session status and the trainer's status as plain text, with no dot and no pulse.
- **Do** leave Bastidores hidden. The drawer and its toggle are for the jury; the student bench does not show agent reasoning.
- **Do** distinguish timeline events by marker color and shape, and move with transform and opacity on `--saida`, including score bars via `scaleX`. Honor `prefers-reduced-motion`.

### Don't:

- **Don't** make the bench gamified or childish: no trophies, owls, confetti, score rings, pulsing dots, emoji reactions, or level-up chrome.
- **Don't** restyle the editor as a neon hacker IDE: no cyan glow, scanlines, gradient syntax coloring, or a mono face worn as a costume.
- **Don't** drift into corporate SaaS: no Inter, Plus Jakarta Sans, or JetBrains Mono; no pill-and-dot status; no uppercase tracked labels; no soft shadow on every card; no blur backdrop.
- **Don't** caricature the Amazon: no leaves, no leaf mark, no forest-green flood. The canopy is the bar and the primary action.
- **Don't** reach for the AI-template kit: uppercase eyebrows, icons in tinted circles, emoji timeline markers, side-stripe accents, hero-metric tiles, conic score rings, capsule pills, or gradient meshes.
