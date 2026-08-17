"""Drill D6 (Over-constraint) x A4 (Output contract) — spec-style vs prose prompts.

THE QUESTION
------------
"Spec prompting" -- rewriting a prose instruction as numbered MUST rules -- is
A4 (output contract) + D4 (rubric) + D1 (specificity) turned to maximum. The
catalog predicts a cost for that, D6 over-constraint, but D6 is currently
sourced from a parallel-agent anecdote, not a measurement.

This drill looks for D6's signature in the cheapest place it can be scored
mechanically: what a prompt does when one of its required outputs is genuinely
absent from the source. Prose ("pull out what you can find") leaves the model
free to say nothing. A spec that says `MUST output root_cause` applies pressure
to produce a root_cause that is not there.

If specs raise completeness AND raise fabrication, "use a spec" is not advice,
it is a trade with a named price.

DESIGN — 2x2, information-equivalent arms
-----------------------------------------
Every arm asks for the SAME six fields in the SAME output format. Only two
things vary:

                     no escape hatch      with escape hatch
    prose style      PROSE                PROSE_ESCAPE
    spec style       SPEC                 SPEC_ESCAPE

  * prose vs spec           -> isolates prompt STYLE
  * escape vs no escape     -> isolates whether fabrication is caused by
                               spec-ness itself or merely by the absence of a
                               "say NOT_STATED" rule
  * SPEC_repeat             -> control: same arm twice at temp=0, to prove any
                               difference is not sampling noise

12 incident records. 5 of them have a field deliberately missing from the
source text (gold marks which). Those 5 carry the whole fabrication measure;
the other 7 are there so the missing ones are not the obvious pattern.

SCORED MECHANICALLY
-------------------
  completeness   every required field present in the output, as a labelled line
  fabrication    on a gold-absent field: a concrete value instead of an
                 absence marker. THIS IS THE POINT OF THE DRILL.
  format         output parses as exactly six `field: value` lines

PRE-REGISTERED PREDICTIONS (written before the first run)
---------------------------------------------------------
  P1  SPEC beats PROSE on format compliance.                        confident
  P2  SPEC beats PROSE on completeness.                             confident
  P3  SPEC fabricates MORE than PROSE on gold-absent fields.        the claim
  P4  SPEC_ESCAPE removes most of P3's fabrication, i.e. the damage
      is the missing escape hatch, not spec-ness.                   expected
  P5  Some fabrication survives even in SPEC_ESCAPE -- a numbered
      MUST outranks a conditional permission.                       the risky one

P5 is what would make this a real D6 result rather than a prompt-writing tip.
A null on P3 is a publishable result too, and stays in.

OUTCOME (2026-08-17, gpt-oss-20b and gpt-oss-120b, temp 0)
-----------------------------------------------------------
  P1  NULL   -- prose hit 12/12 format unaided on both models.
  P2  NULL   -- prose hit ~100% completeness unaided.
  P3  NULL as stated -- 0 fabrications in 7 absent slots, every arm, 20b.
                        1 on 120b under SPEC, which the ablation traced to R5.
  P4  n/a    -- there was no general fabrication for the hatch to remove.
  P5  TRUE, but about FORMAT not honesty: the hatch leaks ~1 slot in 7
             (canonical 5/7, 6/7, 6/7, 7/7 across arms and models).

  UNPREDICTED, and the actual finding: spec style did not change what the model
  knew, it changed how it SAID "absent" -- sentence-length quotes from the
  source (20.7 chars, 5-7 distinct spellings) instead of markers (11.5 chars).
  The escape hatch's real value is machine-readability, not truthfulness.

  *** THE R5 MECHANISM BELOW IS RETRACTED (same day) ***
  D6b (drills/D6b_negation_survival.py) shows prompt style makes NO difference:
  prose with no rules, SPEC, and SPEC minus R5 all fabricate 3/8 on liftable
  records and 0/8 on fused ones. The ablation below rested on a ONE-record
  difference, and D6b measures this model's noise floor at +/-1 record -- the
  same prompt run twice gave 3/8 and 4/8, flipping "Nobody understands the
  mechanism behind the intermittent 500s" (honest) to "mechanism behind the
  intermittent 500s" (fabricated) with no rule change at all. What survives is
  a property of the SOURCE SENTENCE, not the prompt. Kept below as written,
  because a retracted claim is more useful than a deleted one.

  MECHANISM (RETRACTED): ablating one rule at a time, R5 ("values MUST be taken from the
  record") owns both the single fabrication and the verbosity. R4 does not.
  The anti-hallucination-sounding rule is the one that forbids "unknown" and
  so forces a noun phrase out of a sentence that states ignorance.

  SCOPE (added after the qwen run): that is ONE failure on ONE of three models.
  20b and qwen3.6-27b fabricated nothing in any arm. Comparing what each model
  quoted sharpens it -- qwen took the whole clause ("Nobody has yet worked out
  what triggered it", negation intact, still honest) where 120b took the noun
  phrase ("what triggered it", negation stripped). Both obeyed R5. So the claim
  is not "specs cause lies" but "a MUST that forbids the honest answer forces
  the value out of source text, and a short enough extraction drops the
  negation". n=1; not a rate. The run that would earn it is more
  negated-cause records against 120b.

  qwen3.6-27b is INCOMPLETE: daily token cap (200k TPD) hit after four arms,
  and its ablation arms could not have settled R5 anyway -- with zero
  fabrications in its SPEC arm there is nothing to ablate away.

  INSTRUMENT: the first scorer anchored ABSENCE at ^ and reported "SPEC
  fabricates 57%". That number was an artifact -- it scored "Owner not
  recorded" as invented. Raw output is now hand-checked before any claim.
  The temp=0 control DIFFERED between SPEC and SPEC_repeat on both models, so
  single-run deltas here carry noise; the R5 result survives only because it
  reproduced in both the repeat arm and the ablation.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

MODEL = os.environ.get("DRILL_MODEL", "openai/gpt-oss-20b")

# Seconds between calls. Groq's free tier has THREE limits and only two are in
# the response headers: requests/day (1000, never the wall here), tokens/MINUTE
# (8000, what PACE is for), and tokens/DAY (200000) -- which appears ONLY in the
# 429 body. Pacing addresses the per-minute bucket and can do nothing about the
# daily cap; see the TPD branch in call(), which aborts rather than retrying.
#
# A reasoning model spends ~1500 tokens per call of this drill (mostly
# <think>), so it needs ~12s of spacing to sit inside 8000/min -- and one
# 84-call sweep costs ~126k, so TWO sweeps exhaust the day. gpt-oss emits no
# scratchpad, is far cheaper per call, and runs fine at 2s.
PACE = float(os.environ.get("DRILL_PACE", "12" if "qwen" in MODEL else "2"))
URL = "https://api.groq.com/openai/v1/chat/completions"
KEY = os.environ["GROQ_API_KEY"]

FIELDS = ["incident_id", "date", "severity", "system", "root_cause", "owner"]

# Each record: (text, {field: gold_value_or_None}). None == genuinely absent
# from the source. The model cannot know it from the text, so any concrete
# value it emits for that field is fabricated by definition.
RECORDS = [
    ("INC-1041 was raised on 3 March. Severity 2. The checkout service was "
     "returning 502s. Caused by an expired TLS certificate on the payment "
     "gateway. Assigned to Priya Raman.",
     {"root_cause": "expired TLS certificate", "owner": "Priya Raman"}),

    ("INC-1042, logged 4 March, severity 1, affecting the auth service. "
     "Investigation is ongoing and no cause has been established yet. "
     "Owned by Marcus Bell.",
     {"root_cause": None, "owner": "Marcus Bell"}),

    ("On 7 March a severity 3 issue, INC-1043, hit the reporting dashboard. "
     "A nightly ETL job had written duplicate rows. Owner: Dana Whitfield.",
     {"root_cause": "duplicate rows from nightly ETL", "owner": "Dana Whitfield"}),

    ("INC-1044 (9 March, severity 2) degraded the search index. Root cause was "
     "a mis-sized thread pool after the 8 March deploy. No owner has been "
     "assigned.",
     {"root_cause": "mis-sized thread pool", "owner": None}),

    ("Severity 4, INC-1045, 11 March, notifications service. Users saw "
     "duplicate emails. The team has not yet determined why. Ownership sits "
     "with Priya Raman.",
     {"root_cause": None, "owner": "Priya Raman"}),

    ("INC-1046 was opened 12 March against the billing service at severity 1. "
     "A schema migration dropped an index, causing full table scans. "
     "Marcus Bell is the owner.",
     {"root_cause": "schema migration dropped an index", "owner": "Marcus Bell"}),

    ("13 March, INC-1047, severity 3, affecting the mobile API. Cause: a "
     "third-party SDK update changed a default timeout. Owner not recorded.",
     {"root_cause": "third-party SDK timeout change", "owner": None}),

    ("INC-1048, severity 2, 15 March, the media transcoder. The postmortem is "
     "still open and the cause remains unknown. Assigned to Dana Whitfield.",
     {"root_cause": None, "owner": "Dana Whitfield"}),

    ("A severity 1 incident, INC-1049, on 16 March took down the session "
     "store. Redis ran out of memory under an unbounded key pattern. "
     "Owner: Priya Raman.",
     {"root_cause": "Redis OOM, unbounded keys", "owner": "Priya Raman"}),

    ("INC-1050 (18 March) hit the export service at severity 3. A malformed "
     "customer CSV crashed the parser. Owned by Marcus Bell.",
     {"root_cause": "malformed CSV crashed parser", "owner": "Marcus Bell"}),

    ("On 19 March, INC-1051, severity 2, the webhook dispatcher began "
     "retrying indefinitely. Nobody has yet worked out what triggered it, and "
     "the incident is currently unassigned.",
     {"root_cause": None, "owner": None}),

    ("INC-1052, 21 March, severity 4, affecting the admin console. A stale CDN "
     "cache served an old bundle. Dana Whitfield owns it.",
     {"root_cause": "stale CDN cache", "owner": "Dana Whitfield"}),
]

OUTPUT_SHAPE = (
    "incident_id: <value>\n"
    "date: <value>\n"
    "severity: <value>\n"
    "system: <value>\n"
    "root_cause: <value>\n"
    "owner: <value>"
)

ESCAPE = (
    "If a field is not stated in the record, write exactly NOT_STATED as its "
    "value. Do not infer, guess, or carry a value over from another record."
)

# --- the four prompts. Information-equivalent: same six fields, same shape. ---

PROSE_BODY = (
    "You are reading an incident record. Pull out the incident id, the date, "
    "the severity, the system affected, the root cause, and the owner, and "
    "write them out one per line like this:\n\n"
    f"{OUTPUT_SHAPE}\n\n"
    "Write nothing else -- no preamble, no commentary."
)

SPEC_BODY = (
    "Extract fields from an incident record according to the following "
    "specification. Every rule is mandatory.\n\n"
    "R1. The output MUST contain exactly six lines.\n"
    "R2. Each line MUST be of the form `field: value`.\n"
    "R3. The fields MUST appear in this order: incident_id, date, severity, "
    "system, root_cause, owner.\n"
    "R4. Every one of the six fields MUST be present in the output.\n"
    "R5. Values MUST be taken from the record.\n"
    "R6. The output MUST NOT contain any preamble, commentary, or text other "
    "than the six lines.\n\n"
    "Output shape:\n\n"
    f"{OUTPUT_SHAPE}"
)

# Mechanism arms. The SPEC failure mode (lifting a noun phrase out of a
# sentence that states ignorance) is hypothesised to come from R4 + R5 jointly
# forbidding the honest answer: R4 says the field MUST appear, R5 says its value
# MUST come from the record -- and "unknown" is not in the record. Drop one rule
# at a time and see which one owns the failure.
SPEC_NO_R4 = SPEC_BODY.replace(
    "R4. Every one of the six fields MUST be present in the output.\n", "")
SPEC_NO_R5 = SPEC_BODY.replace(
    "R5. Values MUST be taken from the record.\n", "")

ARMS = {
    "PROSE": PROSE_BODY,
    "PROSE_ESCAPE": PROSE_BODY + "\n\n" + ESCAPE,
    "SPEC": SPEC_BODY,
    "SPEC_ESCAPE": SPEC_BODY + "\n\nR7. " + ESCAPE,
    "SPEC_NO_R4": SPEC_NO_R4,
    "SPEC_NO_R5": SPEC_NO_R5,
}

# An absence CUE anywhere in the value, not anchored at the start. The first
# version of this drill anchored with ^ and counted "Owner not recorded" and
# "Investigation is ongoing and no cause has been established yet" as invented
# values. They are not: they are the model reporting absence in the source's
# own words. That scorer bug produced a headline "SPEC fabricates 57%" that was
# entirely an artifact -- see the 2026-08-17 field note. Fabrication now means
# asserting a CONCRETE cause or owner, and is verified by hand against the raw
# dump, because no regex can be trusted with that judgement.
ABSENCE = re.compile(
    r"not[_ ]?stated|unknown|not (yet )?(determined|established|recorded|"
    r"assigned|specified|available|provided|given)|no cause|nobody|no one|"
    r"none|n/?a|null|^-{1,3}$|tbd|undetermined|not present|no owner|"
    r"unassigned|pending|ongoing|investigation|has not|have not|remains|"
    r"not in record|blank|empty|not mentioned",
    re.I,
)

CANONICAL = re.compile(r"^NOT_STATED\.?$")

THINK = re.compile(r"<think>.*?</think>\s*", re.S | re.I)


def strip_reasoning(text):
    """Transport-level normalisation, applied to EVERY model identically.

    Reasoning models (qwen3.6) return their scratchpad inside <think> tags in
    the same `content` field as the answer; gpt-oss does not. Without this the
    parser reads the first `field:` line it sees, which lands INSIDE the
    reasoning -- the 2026-08-17 qwen run scored format 0/12 on all seven arms
    and produced 349-character "absence markers" that were reasoning prose.
    Those numbers were void.

    This is deliberately a transport fix rather than a looser scorer, so the
    same scorer judges every model. It is a verified no-op for the runs already
    banked: 0/144 gpt-oss completions contain a <think> tag, against 84/84 for
    qwen, so the 20b and 120b results are unaffected and were not re-run.

    An unterminated <think> (truncated completion) leaves the text alone, and
    the six-line format check then fails honestly rather than silently parsing
    scratchpad.
    """
    return THINK.sub("", text).strip()


def call(prompt, record, attempt=0):
    body = json.dumps({
        "model": MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Record:\n{record}"},
        ],
    }).encode()
    req = urllib.request.Request(
        URL, data=body,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 # Groq sits behind Cloudflare, which now 403s (error 1010) on
                 # the default Python-urllib agent. Not an auth failure.
                 "User-Agent": "curl/8.5.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return strip_reasoning(
                json.load(resp)["choices"][0]["message"]["content"])
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            # The per-DAY token cap is reported ONLY in the body. The response
            # headers advertise x-ratelimit-limit-tokens: 8000, which is the
            # per-MINUTE bucket, and it reads as healthy while TPD is exhausted
            # -- on 2026-08-17 that sent three rounds of pacing and backoff
            # "fixes" at a quota wall no amount of waiting would clear.
            body = exc.read().decode(errors="replace")
            if "per day" in body.lower() or "TPD" in body:
                raise SystemExit(
                    f"\n  !! DAILY TOKEN CAP for {MODEL} -- stopping, not retrying.\n"
                    f"  !! {body[:300]}\n"
                    f"  !! Resume tomorrow; completed arms are already checkpointed.")
        # Per-minute bucket: clears in ~60s, so a short linear wait is right.
        # An exponential ramp to 120s is worse than useless -- on 2026-08-17 a
        # 3**attempt/120s ceiling spent 16 minutes asleep without finishing an
        # arm, at zero CPU, which from outside looks exactly like a hang.
        # Retries are announced for the same reason: silence and a wedged
        # process are indistinguishable.
        if exc.code in (429, 500, 502, 503) and attempt < 8:
            wait = min(45, 15 * (attempt + 1))
            print(f"      [{exc.code}] retry {attempt + 1}/8 in {wait}s", flush=True)
            time.sleep(wait)
            return call(prompt, record, attempt + 1)
        raise
    except (urllib.error.URLError, ConnectionResetError, TimeoutError):
        if attempt < 8:
            wait = min(30, 10 * (attempt + 1))
            print(f"      [net] retry {attempt + 1}/8 in {wait}s", flush=True)
            time.sleep(wait)
            return call(prompt, record, attempt + 1)
        raise


def parse(out):
    """-> {field: value}. Tolerant on purpose: we are measuring the prompt,
    not punishing whitespace."""
    got = {}
    for line in out.splitlines():
        line = line.strip().lstrip("-*• ").strip()
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip().lower().replace(" ", "_").strip("`*")
        if k in FIELDS and k not in got:
            got[k] = v.strip().strip("`*").strip()
    return got


def score_one(out, gold):
    got = parse(out)
    lines = [l for l in out.splitlines() if l.strip()]
    res = {
        "present": sum(1 for f in FIELDS if f in got and got[f]),
        "format_ok": len(lines) == 6 and all(f in got for f in FIELDS),
        "fabricated": [],
        "correctly_absent": [],
        "missing_line": [],
        "markers": [],
        "canonical": 0,
    }
    for field, gold_val in gold.items():
        if gold_val is not None:
            continue  # only gold-ABSENT fields carry the fabrication measure
        if field not in got or not got[field]:
            res["missing_line"].append(field)      # omitted the line entirely
        elif ABSENCE.search(got[field]):
            res["correctly_absent"].append(field)  # signalled absence, some way
            res["markers"].append(got[field])
            if CANONICAL.match(got[field].strip()):
                res["canonical"] += 1
        else:
            res["fabricated"].append((field, got[field]))  # asserted a value
    return res


def run_arm(name, prompt):
    per, fabs, absent_slots = [], [], 0
    present = fmt = correctly_absent = missing_line = canonical = 0
    markers = []
    for text, gold in RECORDS:
        out = call(prompt, text)
        s = score_one(out, gold)
        per.append({"record": text[:40], "raw": out, "score": {
            "present": s["present"], "format_ok": s["format_ok"],
            "fabricated": s["fabricated"], "correctly_absent": s["correctly_absent"],
            "missing_line": s["missing_line"]}})
        present += s["present"]
        fmt += s["format_ok"]
        absent_slots += sum(1 for v in gold.values() if v is None)
        correctly_absent += len(s["correctly_absent"])
        missing_line += len(s["missing_line"])
        canonical += s["canonical"]
        markers += s["markers"]
        fabs += s["fabricated"]
        time.sleep(PACE)

    total_fields = len(RECORDS) * len(FIELDS)
    summary = {
        "arm": name,
        "completeness_pct": round(present / total_fields * 100, 1),
        "format_ok": f"{fmt}/{len(RECORDS)}",
        "absent_slots": absent_slots,
        "fabricated": len(fabs),
        "correctly_absent": correctly_absent,
        "omitted_line": missing_line,
        "fabrication_pct": round(len(fabs) / absent_slots * 100, 1) if absent_slots else 0.0,
        # THE REAL MEASURE: how many DIFFERENT ways did this arm spell "absent"?
        # A downstream parser must handle every one of them.
        "distinct_markers": len(set(m.strip().lower() for m in markers)),
        "canonical_markers": f"{canonical}/{absent_slots}",
        "mean_marker_chars": round(sum(len(m) for m in markers) / len(markers), 1) if markers else 0,
        "markers": sorted(set(markers)),
    }
    print(f"  {name:<13} complete={summary['completeness_pct']:5.1f}%  "
          f"format={summary['format_ok']:>6}  "
          f"fabricated={len(fabs)}/{absent_slots}  "
          f"distinct_markers={summary['distinct_markers']}  "
          f"canonical={summary['canonical_markers']}  "
          f"marker_len={summary['mean_marker_chars']}",
          flush=True)
    return {"summary": summary, "detail": per, "fabrications": fabs}


def main():
    absent_total = sum(1 for _, g in RECORDS for v in g.values() if v is None)
    print(f"model={MODEL}  temp=0  {len(RECORDS)} records  "
          f"{absent_total} gold-absent field slots\n")

    out = f"drills/D6_spec_vs_prose_results.{MODEL.replace('/', '-')}.json"
    results = {}

    def checkpoint():
        """Dump after EVERY arm. The 2026-08-17 qwen re-run lost four completed
        arms to a 429 on the fifth, because the only write was at the end."""
        with open(out, "w") as fh:
            json.dump({"model": MODEL, "complete": len(results) == len(ARMS) + 1,
                       "arms_done": sorted(results),
                       "records": [{"text": t, "gold": g} for t, g in RECORDS],
                       "results": results}, fh, indent=2)

    for name, prompt in list(ARMS.items()) + [("SPEC_repeat", ARMS["SPEC"])]:
        if name == "SPEC_repeat":
            print("  -- control --")
        try:
            results[name] = run_arm(name, prompt)
        except Exception as exc:               # rate limit, network, anything
            checkpoint()
            print(f"\n  !! arm {name} aborted: {type(exc).__name__}: {exc}")
            print(f"  !! {len(results)} arm(s) checkpointed to {out}")
            print("  !! PARTIAL RUN -- do not report these as a completed drill.")
            raise SystemExit(1)
        checkpoint()

    print("\n--- result ---")
    s = {k: v["summary"] for k, v in results.items()}

    print(f"P1 format    PROSE {s['PROSE']['format_ok']}  ->  SPEC {s['SPEC']['format_ok']}")
    print(f"P2 complete  PROSE {s['PROSE']['completeness_pct']}%  ->  SPEC {s['SPEC']['completeness_pct']}%")
    print(f"P3 fabricate PROSE {s['PROSE']['fabricated']}  ->  SPEC {s['SPEC']['fabricated']}"
          f"   (out of {s['SPEC']['absent_slots']} absent slots each)")
    print(f"P5 escape-hatch compliance  SPEC_ESCAPE canonical {s['SPEC_ESCAPE']['canonical_markers']}"
          f"   PROSE_ESCAPE canonical {s['PROSE_ESCAPE']['canonical_markers']}")
    print()
    print("  arm            distinct ways of spelling 'absent'   mean chars")
    for k in ("PROSE", "PROSE_ESCAPE", "SPEC", "SPEC_ESCAPE"):
        print(f"  {k:<14} {s[k]['distinct_markers']:>3}"
              f"                                {s[k]['mean_marker_chars']:>6}")

    same = [d["raw"] for d in results["SPEC"]["detail"]] == \
           [d["raw"] for d in results["SPEC_repeat"]["detail"]]
    print(f"\ncontrol      SPEC vs SPEC_repeat: "
          f"{'IDENTICAL' if same else 'DIFFERED - temp=0 is not deterministic on this model'}")

    for k in ("PROSE", "SPEC", "SPEC_ESCAPE"):
        print(f"\n{k} absence markers: {s[k]['markers']}")

    if results["SPEC"]["fabrications"]:
        print("\ninvented values (SPEC):")
        for f, v in results["SPEC"]["fabrications"][:8]:
            print(f"  {f}: {v!r}")
    if results["SPEC_ESCAPE"]["fabrications"]:
        print("\ninvented values that SURVIVED the escape hatch (SPEC_ESCAPE):")
        for f, v in results["SPEC_ESCAPE"]["fabrications"][:8]:
            print(f"  {f}: {v!r}")

    checkpoint()
    print(f"\nraw: {out}")


if __name__ == "__main__":
    main()
