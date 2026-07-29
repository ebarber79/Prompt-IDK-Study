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
