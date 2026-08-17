# VOID_*.json — kept deliberately, not a result

`VOID_D6_spec_vs_prose_results.qwen-qwen3.6-27b.think-polluted.json`
(run 2026-08-17 10:40) contains **no usable numbers**.

qwen3.6 returns its scratchpad inside `<think>` tags in the same `content`
field as the answer. The parser reads the first `field:` line it finds, which
landed inside the reasoning. Every arm scored `format 0/12`, PROSE scored
`fabricated 7/7`, and the "absence markers" were 349-character reasoning
prose. All of it is an artifact of the harness, not behaviour of the model.

It is kept for two reasons:

1. It is the record of the instrument failure, and this study keeps those.
2. Its reasoning text is the best qualitative evidence in the drill: qwen
   verbalises the R5 mechanism unprompted — *"Actually, 'unknown' isn't in the
   record. I'll use 'Nobody has yet worked out what triggered it'"* — naming
   the same rule the gpt-oss-120b ablation implicated. Corroboration, not
   proof: a verbalised reason is the model's account of itself, not the cause.

The fix is `strip_reasoning()` in the drill, applied to every model identically
and verified a no-op on the banked gpt-oss runs (0/144 completions contain a
`<think>` tag, vs 84/84 for qwen).
