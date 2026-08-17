# Prompt IDKs — study PWA

An installable, offline-capable field guide to the **atomic units of a prompt** ("IDKs"), sorted into three families: **Location**, **Action**, **Detail**. Text-first, with an image-prompting track alongside.

Companion to [Agent Operations](https://github.com/ebarber79/Agent-Ops-Study) — that project is about directing agents; this one is about the units the direction is made of.

## The idea

An IDK is the smallest part of a prompt you can change on its own and get a different result. Naming the unit turns a rewrite into an experiment: instead of rewording the whole prompt and changing six things at once, you move one unit and observe.

The three families are the questions the units sort into:

| Family | Asks | Example units |
|---|---|---|
| **Location** | where does this go? | slot, depth, adjacency, boundary, order, recurrence |
| **Action** | what should happen? | verb, role vs instruction, polarity, output contract, reasoning placement, termination |
| **Detail** | how precisely? | specificity gradient, demonstration, counterexample, rubric, grounding, over-constraint |

18 text units + 3 image units. Each carries what it is, the knob it turns, its failure signature, and an A/B drill.

## Evidence labelling

Every unit is labelled `measured` (published result, cited and linked), `vendor guidance` (documented by a model provider), or `folklore` / `craft` (widely practised, mechanism plausible, no citation worth defending). Six of the eighteen text units are unproven and say so — the drills are written so a unit can be moved from `folklore` to `measured` by running it.

Primary sources used: Liu et al. 2023 (lost in the middle), Lu et al. 2021 (prompt order sensitivity), Zhao et al. 2021 (calibrate before use), Zheng et al. 2023 (multiple-choice selection bias), Jang et al. 2022 (negated prompts), Min et al. 2022 (role of demonstrations), plus Anthropic's published prompting guidance. All were fetched and verified rather than recalled.

## Field notes

Three units (L5, A4, D2) carry a dated **field note** from a drill actually run against a live model, and `drills/` holds the runnable script plus raw results.

The first run (2026-07-29, `llama-3.1-8b-instant`, temp 0) is a **null**: five orderings of an 8-shot classifier over 20 subtle held-out reviews all scored 16/20 — accuracy spread 0.0 points. A sixth arm repeating ordering A returned byte-identical predictions, so the null is real rather than noise-masked. Only 1/20 items varied with ordering at all, and that variation was between two wrong answers.

Two things came out of it, both now in the app:

- **The drill's own metric was inadequate.** "Accuracy spread is your prompt's real error bar" is wrong as a sole measure — spread can be exactly zero while outputs still move. Per-item flip count is now part of the drill.
- **An unplanned A4 result.** The classifier prompt said "reply with exactly one word: POSITIVE or NEGATIVE"; on 3/20 items (15%) the model replied `NEUTRAL` — a label absent from both the instruction and all eight examples. Demonstrations *establish* a label space; they do not *enforce* one.

Nulls stay in. A drill that reproduces nothing is a result about scale and task, and deleting it would make the catalog look better than the evidence.

### D6 — Over-constraint, measured (2026-08-17)

D6 was the catalog's weakest card: sourced from a parallel-agent anecdote, no
citation, no drill. `drills/D6_spec_vs_prose.py` now measures it, on
`openai/gpt-oss-20b` and `openai/gpt-oss-120b`, temp 0.

The drill asks six fields out of short incident records, where seven field
slots are **genuinely absent from the source**. Four information-equivalent
arms: prose vs spec style, each with and without an explicit "write NOT_STATED
if absent" escape hatch.

**The pre-registered claim was a null.** Specs did not raise fabrication in
general, and did not raise completeness or format compliance either — prose hit
12/12 format and ~100% completeness unaided on both models. On a task this
size, "use a spec" bought nothing on the metrics it is usually sold on.

**What it did change is the shape of the absent value.** Under a spec the model
answered absence with a sentence lifted from the source (`"Investigation is
ongoing and no cause has been established yet."`) rather than a marker
(`unknown`) — mean marker length 20.7 chars vs 11.5 under prose, across 5–7
distinct spellings. Any parser downstream must handle every one of them. The
escape hatch collapses that to 1–2 spellings, 6/7 and 7/7 canonical. So the
hatch's value is not honesty, it is **machine-readability** — and it still
leaks about one slot in seven.

### RETRACTED: "R5 causes the fabrication" (claimed 2026-08-17, withdrawn same day)

The first version of this note reported a mechanism: on 120b, a spec turned
*"Nobody has yet worked out what triggered it"* into `root_cause: what
triggered it`, and ablating one rule at a time appeared to pin it on **R5**
(*"values MUST be taken from the record"*) — the rule that reads as an
anti-hallucination guardrail. It was a tidy story, it matched the
pre-registered prediction, and **it was wrong.**

It rested on a single record, where `SPEC` said `what triggered it` and
`SPEC minus R5` said `undetermined`. One flip, on a model whose temp=0 control
had *already failed* in that same run. I read a coin toss as an ablation.

`drills/D6b_negation_survival.py` was built to turn that n=1 into a rate: 24
records on 120b, 8 with ignorance phrased so a noun phrase names the missing
cause, 8 with the negation fused to the answer slot, 8 with real causes as
controls.

| arm | liftable-NP records | fused-negation records |
|---|---|---|
| PROSE (no spec at all) | 3/8 | 0/8 |
| SPEC | 3/8 | 0/8 |
| SPEC minus R5 | 3/8 | 0/8 |
| SPEC again (same prompt) | **4/8** | 0/8 |

**Prompt style makes no difference whatsoever.** Prose with no rules fabricates
at the same rate as a six-rule spec, and removing R5 changes nothing. The same
three records fail in every arm.

The last row is the point. `SPEC` and `SPEC_repeat` are the *same prompt* and
differ by one record, so **the noise floor on this model is ±1** — and the
entire R5 ablation was a one-record difference. Here is the flip, same record,
same prompt, same temperature:

    run 1   Nobody understands the mechanism behind the intermittent 500s   honest
    run 2   mechanism behind the intermittent 500s                          fabricated

That is the D6 result reproduced with no rule change at all.

### What actually survives

Fabrication is a property of **the source sentence**, not the prompt. It
happens when a statement of ignorance can be extracted from in a way that drops
the part carrying the ignorance:

| source phrasing | extracted as | |
|---|---|---|
| "Investigation **continues into** the source of the timeouts" | `source of the timeouts` | ✗ |
| "Engineers are **still tracing** the origin of the duplicate charges" | `duplicate charges` | ✗ |
| "The postmortem **has not settled** the trigger for the parser crash" | `parser crash` | ✗ |
| "**Nobody** has yet worked out what triggered it" | *quoted whole* | ✓ |
| "The cause **remains unknown**" | `unknown` | ✓ |

Two of the three failures contain **no negation word at all** — they express
ignorance through aspect (*an investigation in progress*). There is no negation
to preserve, so extraction cannot preserve one. The survivors either carry an
explicit negative marker (`nobody`, `no one`, `have not`) or fuse the ignorance
into the answer word itself (`unknown`, `never established`).

> **Ignorance stated as progress is not stated as ignorance.** "We are still
> investigating X" and "X is unknown" mean the same thing to a reader and
> different things to an extractor. The second cannot be quoted into a false
> claim; the first can, by quoting the X.

Honest limits on that: the design conflated two variables — *liftable noun
phrase* and *aspectual vs explicit negation* — so it cannot yet separate their
contributions, and a follow-up should cross them. The rate is 2–3 of 8 rather
than a firm 3, because hand-checking found the scorer counting
`trigger for the parser crash (unspecified)` as invented when `(unspecified)`
signals absence. One model, one task shape.

Both qwen and 20b results above stand — they concern the escape hatch and
marker variety, which replicate. The qwen arms remain incomplete (daily token
cap), and completing them would not bear on any of this.

**Two instrument notes, both worth more than the result.**

The first scorer anchored its absence regex at `^` and so counted `"Owner not
recorded"` as an invented value. It printed *"SPEC fabricates 57%"* — a clean,
plausible, entirely artefactual headline that matched the pre-registered
prediction. Reading the raw dump showed **zero** fabrications in any arm. That
is twice now (L5, D6) that this study's metric, not its models, was the weak
point; raw output is checked by hand before any number is believed.

Second, the control failed: `SPEC` vs `SPEC_repeat` at temp 0 were **not**
byte-identical on either model, so single-run differences here carry noise. The
R5 finding survives because it reproduced across the repeat arm and the
ablation, not because temp 0 was trusted.

**Reproducibility note:** L5's model, `llama-3.1-8b-instant`, no longer exists
on Groq — that drill cannot be re-run as written. Groq also now sits behind
Cloudflare, which 403s (error 1010) on Python's default urllib user agent; the
drills send `User-Agent: curl/8.5.0`. Neither is an auth failure, and both look
like one.

`D6 — Over-constraint` is not from the literature. It comes from a parallel-agent experiment in the companion project, where two agents given non-jointly-satisfiable formatting requirements each silently dropped the other's.

## Install on mobile

Open the live URL in Chrome (Android) or Safari (iOS), then:

- **Android/Chrome:** menu → "Add to Home screen" / "Install app"
- **iOS/Safari:** share icon → "Add to Home Screen"

It launches full-screen and works with zero connection — the service worker caches the whole app on first load.

## Local dev

No build step. Any static file server works:

```bash
python3 -m http.server 8000
```

Progress ("mark done" per unit) and the theme override are stored in `localStorage`, per-device.

Icons are generated, not hand-drawn — `python3 tools/mkicons.py` regenerates all three from stdlib only (`zlib` + `struct`, no Pillow).

## Tech stack

- Vanilla JavaScript Progressive Web App, no build step, no dependencies
- Offline-first service worker (`sw.js`); bump `CACHE` on content changes
- Web app manifest (`manifest.json`) for installability
- Light/dark via `prefers-color-scheme` with a manual override
