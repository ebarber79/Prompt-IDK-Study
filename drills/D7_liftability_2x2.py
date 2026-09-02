"""Drill D7 -- the clean 2x2: liftable NP x explicit-vs-aspectual negation.

WHY THIS EXISTS
---------------
D6b (2026-08-17, commit bc8b88c) retracted D6's R5 mechanism and replaced it
with a better claim: fabrication is a property of the SOURCE SENTENCE, not the
prompt. Plain prose, a six-rule SPEC, and SPEC-minus-R5 each fabricated 3/8 on
"LIFTABLE" records and 0/8 on "FUSED" ones -- the same three records every time.

But D6b's LIFTABLE class confounded two properties, and its own limits section
says so. Of the three records that failed, TWO carried no negation word at all
-- ignorance expressed aspectually ("Investigation continues into the source of
the timeouts", "Engineers are still tracing the origin of the duplicate
charges") -- while five of the six explicitly-negated LIFTABLE records survived.
And the FUSED class contained no aspectual items whatsoever, so the cell that
would discriminate the two factors was never run.

Two rival readings of D6b fit its data equally well:

    (a) LIFTABILITY drives it. A noun phrase that names the missing cause can
        be extracted while dropping the operator that carried the ignorance.
    (b) ASPECT drives it. "Ignorance stated as progress is not stated as
        ignorance" -- there is no negation to preserve, so nothing is lost.

THE HYPOTHESES, PRE-REGISTERED
------------------------------
    H1 (liftability main effect): LIFT_* fabricate at a higher rate than
       FUSED_*, collapsing over negation form.
    H2 (aspect main effect): *_ASPECTUAL fabricate at a higher rate than
       *_EXPLICIT, collapsing over liftability.
    H3 (interaction): LIFT_ASPECTUAL is the worst cell by a margin larger
       than either main effect predicts alone.

    Prior from D6b, for the record:
       LIFT_ASPECTUAL 2/2   LIFT_EXPLICIT 1/6
       FUSED_EXPLICIT 0/8   FUSED_ASPECTUAL  NEVER RUN

    Falsified by: four comparable cells (neither factor is the driver), or
    ~0 across all four (D6b's rate was itself noise).

    Decision rule, fixed BEFORE the run: an effect counts only if it exceeds
    this run's own measured noise floor -- the per-record disagreement between
    PROSE and PROSE_repeat, which are byte-identical prompts. D6b established
    that temp=0 is NOT deterministic here (noise floor +/-1 per 8), so the
    floor is measured, not assumed.

DESIGN -- WITHIN-ITEM
---------------------
12 incident stems. Each stem appears in all four cells, with the incident id,
date, severity, system, owner and SYMPTOM SENTENCE held byte-identical; only
the one ignorance sentence changes. So a cell difference cannot be blamed on
which incident it was. 12 x 4 = 48 absent records, + 8 PRESENT controls
(reused from D6b so the scorer is comparable) = 56 per arm.

Four phrasing families are rotated across the stems (3 stems each) so no cell
is one template's artifact; within a stem, all four variants come from the
same family.

Arms: PROSE, PROSE_repeat (the noise floor), SPEC. Prompt style was measured
null in D6b -- SPEC is here as a third replicate and a re-test of that null,
not as a live hypothesis. Pooled, that is n=36 per cell.

SCORING
-------
Mechanical first pass, then EVERY gold-absent value is dumped for hand-check.
Two instruments have now beaten the models on this study (L5, D6), and D6's
first scorer printed a confident prediction-confirming artifact. No number
from this file is reported without reading the values.

NOTE, scorer fix carried over: D6b's ABSENCE regex had unbounded alternatives
(`n/?a` matches the "na" inside "final"). Word boundaries added here.

Truncation is tracked per call (Codex rule: a truncated response is not a
completed one) and never silently scored.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

MODEL = os.environ.get("DRILL_MODEL", "openai/gpt-oss-120b")
PACE = float(os.environ.get("DRILL_PACE", "12" if "qwen" in MODEL else "2"))
URL = "https://api.groq.com/openai/v1/chat/completions"
KEY = os.environ["GROQ_API_KEY"]

FIELDS = ["incident_id", "date", "severity", "system", "root_cause", "owner"]
CELLS = ["LIFT_EXPLICIT", "LIFT_ASPECTUAL", "FUSED_EXPLICIT", "FUSED_ASPECTUAL"]

# (id, date, severity, system, owner, symptom sentence, liftable cause NP, family)
STEMS = [
    ("INC-3001", "2 April", "2", "the webhook dispatcher", "Priya Raman",
     "The dispatcher emitted a retry storm for forty minutes.",
     "what triggered the retry storm", "A"),
    ("INC-3002", "3 April", "1", "the auth service", "Marcus Bell",
     "Sign-ins failed for roughly one user in five.",
     "the underlying fault", "A"),
    ("INC-3003", "5 April", "3", "the search index", "Dana Whitfield",
     "Queries timed out intermittently through the afternoon.",
     "the source of the timeouts", "A"),
    ("INC-3004", "6 April", "2", "the billing service", "Priya Raman",
     "A batch of customers were charged twice.",
     "the origin of the duplicate charges", "B"),
    ("INC-3005", "8 April", "4", "the notifications service", "Marcus Bell",
     "Push sends lagged by up to nine minutes.",
     "the reason for the delayed sends", "B"),
    ("INC-3006", "9 April", "1", "the session store", "Dana Whitfield",
     "The connection pool exhausted twice in one hour.",
     "the condition that exhausts the pool", "B"),
    ("INC-3007", "11 April", "3", "the export service", "Priya Raman",
     "The CSV parser crashed on a subset of jobs.",
     "the trigger for the parser crash", "C"),
    ("INC-3008", "12 April", "2", "the mobile API", "Marcus Bell",
     "Clients saw intermittent 500s all morning.",
     "the mechanism behind the intermittent 500s", "C"),
    ("INC-3009", "14 April", "2", "the checkout service", "Dana Whitfield",
     "Around three percent of carts failed to submit.",
     "the reason for the failed submissions", "C"),
    ("INC-3010", "15 April", "1", "the payment gateway", "Priya Raman",
     "Settlement batches posted hours late.",
     "the cause of the settlement delay", "D"),
    ("INC-3011", "17 April", "3", "the reporting dashboard", "Marcus Bell",
     "Several charts rendered stale figures.",
     "the source of the stale figures", "D"),
    ("INC-3012", "18 April", "4", "the admin console", "Dana Whitfield",
     "The console served an outdated bundle to some staff.",
     "what caused the outdated bundle", "D"),
]

# Within a family the four cells are matched: LIFT_* share the same NP and
# differ only in negation form; FUSED_* keep the ignorance in the predicate,
# with no noun phrase that names the missing cause.
FAMILIES = {
    "A": {"LIFT_EXPLICIT":   "Nobody has worked out {cnp}.",
          "LIFT_ASPECTUAL":  "Investigation continues into {cnp}.",
          "FUSED_EXPLICIT":  "The cause was never established.",
          "FUSED_ASPECTUAL": "The cause is still under investigation."},
    "B": {"LIFT_EXPLICIT":   "The team has not identified {cnp}.",
          "LIFT_ASPECTUAL":  "The team is still tracing {cnp}.",
          "FUSED_EXPLICIT":  "The cause remains unknown.",
          "FUSED_ASPECTUAL": "Root cause analysis is ongoing."},
    "C": {"LIFT_EXPLICIT":   "No one has pinned down {cnp}.",
          "LIFT_ASPECTUAL":  "Engineers are working to determine {cnp}.",
          "FUSED_EXPLICIT":  "No explanation has been found.",
          "FUSED_ASPECTUAL": "An explanation is still being sought."},
    "D": {"LIFT_EXPLICIT":   "The postmortem has not settled {cnp}.",
          "LIFT_ASPECTUAL":  "The postmortem is still examining {cnp}.",
          "FUSED_EXPLICIT":  "The postmortem reached no conclusion.",
          "FUSED_ASPECTUAL": "The postmortem remains open."},
}

PRESENT = [
    ("INC-3017, 26 April, severity 2, the checkout service. Caused by an "
     "expired TLS certificate. Owner: Marcus Bell.", "expired TLS certificate"),
    ("INC-3018 (27 April, severity 1), the billing service. A schema migration "
     "dropped an index. Owned by Dana Whitfield.", "schema migration dropped an index"),
    ("On 29 April, INC-3019, severity 3, the reporting dashboard. A nightly "
     "ETL job wrote duplicate rows. Owner: Priya Raman.", "nightly ETL wrote duplicate rows"),
    ("INC-3020, 30 April, severity 2, the search index. Root cause was a "
     "mis-sized thread pool. Owned by Marcus Bell.", "mis-sized thread pool"),
    ("INC-3021 (1 May, severity 1), the session store. Redis ran out of memory "
     "under an unbounded key pattern. Owner: Dana Whitfield.", "Redis OOM, unbounded keys"),
    ("INC-3022, 3 May, severity 4, the notifications service. A third-party "
     "SDK update changed a default timeout. Owned by Priya Raman.", "third-party SDK timeout change"),
    ("INC-3023 on 4 May, severity 3, the export service. A malformed customer "
     "CSV crashed the parser. Owner: Marcus Bell.", "malformed CSV crashed parser"),
    ("INC-3024 (6 May, severity 2), the admin console. A stale CDN cache "
     "served an old bundle. Owned by Dana Whitfield.", "stale CDN cache"),
]


def build_records():
    """56 records/arm: 12 stems x 4 cells (matched), + 8 PRESENT controls."""
    rows = []
    for iid, date, sev, system, owner, symptom, cnp, fam in STEMS:
        for cell in CELLS:
            ign = FAMILIES[fam][cell].format(cnp=cnp)
            text = (f"{iid}, {date}, severity {sev}, {system}. {symptom} "
                    f"{ign} Owner: {owner}.")
            rows.append({"text": text, "gold": None, "cell": cell,
                         "stem": iid, "family": fam, "cnp": cnp})
    for text, gold in PRESENT:
        rows.append({"text": text, "gold": gold, "cell": "PRESENT",
                     "stem": text[:8], "family": "-", "cnp": ""})
    return rows


RECORDS = build_records()

OUTPUT_SHAPE = (
    "incident_id: <value>\ndate: <value>\nseverity: <value>\n"
    "system: <value>\nroot_cause: <value>\nowner: <value>"
)

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
    f"Output shape:\n\n{OUTPUT_SHAPE}"
)

ARMS = [("PROSE", PROSE_BODY), ("PROSE_repeat", PROSE_BODY), ("SPEC", SPEC_BODY)]

# Unanchored on purpose (D6's first scorer anchored at ^ and produced a
# confident artifact), but word-bounded -- D6b's `n/?a` matched inside "final".
ABSENCE = re.compile(
    r"\bnot[_ ]?stated\b|\bunknown\b|\bunexplained\b|\bundetermined\b|"
    r"\bunidentified\b|\bnot\b|\bnever\b|\bno\b|\bnone\b|\bnobody\b|"
    r"\bno one\b|\bn/?a\b|\bnull\b|\btbd\b|\bpending\b|\bongoing\b|"
    r"\binvestigation\b|\binvestigating\b|\bcontinues\b|\bremains\b|"
    r"\bstill\b|\bunresolved\b|\bopen\b|\bbeing sought\b|\bunder review\b|"
    r"\btracing\b|\bexamining\b|\bdetermine\b|\byet\b",
    re.I,
)
THINK = re.compile(r"<think>.*?</think>\s*", re.S | re.I)


def call(prompt, record, attempt=0, cap=400):
    body = json.dumps({
        "model": MODEL, "temperature": 0, "max_tokens": cap,
        "messages": [{"role": "system", "content": prompt},
                     {"role": "user", "content": f"Record:\n{record}"}],
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
        "User-Agent": "curl/8.5.0"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            ch = json.load(resp)["choices"][0]
            txt = THINK.sub("", ch["message"].get("content") or "").strip()
            fin = ch.get("finish_reason", "")
            # A truncated response is not a completed one. Retry once, bigger.
            if fin == "length" and cap < 1200:
                return call(prompt, record, attempt, cap * 3)
            return txt, fin
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            b = exc.read().decode(errors="replace")
            if "per day" in b.lower() or "TPD" in b:
                raise SystemExit(f"\n  !! DAILY TOKEN CAP for {MODEL}\n  !! {b[:250]}")
        if exc.code in (429, 500, 502, 503) and attempt < 8:
            wait = min(45, 15 * (attempt + 1))
            print(f"      [{exc.code}] retry {attempt + 1}/8 in {wait}s", flush=True)
            time.sleep(wait)
            return call(prompt, record, attempt + 1, cap)
        raise
    except (urllib.error.URLError, ConnectionResetError, TimeoutError):
        if attempt < 8:
            time.sleep(min(30, 10 * (attempt + 1)))
            return call(prompt, record, attempt + 1, cap)
        raise


def parse(out):
    got = {}
    for line in out.splitlines():
        line = line.strip().lstrip("-*| ").strip()
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip().lower().replace(" ", "_").strip("`*|")
        if k in FIELDS and k not in got:
            got[k] = v.strip().strip("`*|").strip()
    return got


def is_lift(val, cnp):
    """Did the value come from the liftable NP with the operator dropped?"""
    if not val or not cnp:
        return False
    a = re.sub(r"[^a-z0-9 ]", "", val.lower()).strip()
    b = re.sub(r"[^a-z0-9 ]", "", cnp.lower()).strip()
    return bool(a) and (a in b or b in a)


def run_arm(name, prompt, limit=None):
    rows = []
    todo = RECORDS[:limit] if limit else RECORDS
    for i, rec in enumerate(todo, 1):
        out, fin = call(prompt, rec["text"])
        val = parse(out).get("root_cause", "")
        if rec["gold"] is None:
            verdict = ("omitted" if not val else
                       "honest" if ABSENCE.search(val) else "FABRICATED")
        else:
            verdict = "n/a-control" if val else "control-EMPTY"
        rows.append({"cell": rec["cell"], "stem": rec["stem"],
                     "family": rec["family"], "root_cause": val,
                     "verdict": verdict, "lift": is_lift(val, rec["cnp"]),
                     "finish": fin, "raw": out if not val else ""})
        if i % 14 == 0:
            print(f"      {name}: {i}/{len(todo)}", flush=True)
        time.sleep(PACE)

    tally = {}
    for c in CELLS:
        sub = [r for r in rows if r["cell"] == c]
        tally[c] = [sum(1 for r in sub if r["verdict"] == "FABRICATED"), len(sub)]
    print(f"  {name:<13} " + "  ".join(
        f"{c.replace('_',' '):<15} {tally[c][0]:>2}/{tally[c][1]}" for c in CELLS),
        flush=True)
    return {"arm": name, "tally": tally, "rows": rows}


def main():
    smoke = "--smoke" in sys.argv
    limit = 8 if smoke else None
    print(f"model={MODEL}  temp=0  {len(RECORDS)} records/arm "
          f"(12 stems x 4 cells + 8 PRESENT){'  [SMOKE]' if smoke else ''}\n")
    out_path = ("drills/D7_liftability_2x2_results."
                f"{MODEL.replace('/', '-')}{'.smoke' if smoke else ''}.json")
    results = {}

    def checkpoint():
        with open(out_path, "w") as fh:
            json.dump({"model": MODEL, "design": "2x2 within-item, 12 stems",
                       "hypotheses": {"H1": "liftability main effect",
                                      "H2": "aspect main effect",
                                      "H3": "LIFT_ASPECTUAL interaction"},
                       "complete": len(results) == len(ARMS),
                       "arms_done": sorted(results), "results": results},
                      fh, indent=2)

    for nm, pr in ARMS:
        try:
            results[nm] = run_arm(nm, pr, limit)
        except SystemExit:
            checkpoint()
            raise
        checkpoint()
        if smoke:
            break

    if smoke:
        for r in results["PROSE"]["rows"]:
            print(f"  [{r['cell']:<15} {r['verdict']:<10} lift={str(r['lift']):<5}]"
                  f" {r['root_cause'][:56]}")
        print(f"\nraw: {out_path}")
        return

    # ---- noise floor, measured: PROSE vs PROSE_repeat, identical prompts ----
    a, b = results["PROSE"]["rows"], results["PROSE_repeat"]["rows"]
    flips = sum(1 for x, y in zip(a, b) if x["verdict"] != y["verdict"])
    print(f"\n--- measured noise floor ---\n  PROSE vs PROSE_repeat "
          f"(byte-identical prompts): {flips}/{len(a)} records disagree")

    # ---- pooled 2x2 ----
    pool = {c: [0, 0] for c in CELLS}
    for arm in results.values():
        for c in CELLS:
            pool[c][0] += arm["tally"][c][0]
            pool[c][1] += arm["tally"][c][1]
    print("\n--- pooled 2x2 (fabrications / n, all 3 arms) ---")
    print(f"  {'':<10} {'EXPLICIT':>12} {'ASPECTUAL':>12}")
    for lif in ("LIFT", "FUSED"):
        e, s = pool[f"{lif}_EXPLICIT"], pool[f"{lif}_ASPECTUAL"]
        print(f"  {lif:<10} {f'{e[0]}/{e[1]}':>12} {f'{s[0]}/{s[1]}':>12}")

    lift_n = pool["LIFT_EXPLICIT"][0] + pool["LIFT_ASPECTUAL"][0]
    fused_n = pool["FUSED_EXPLICIT"][0] + pool["FUSED_ASPECTUAL"][0]
    asp_n = pool["LIFT_ASPECTUAL"][0] + pool["FUSED_ASPECTUAL"][0]
    exp_n = pool["LIFT_EXPLICIT"][0] + pool["FUSED_EXPLICIT"][0]
    floor = flips  # this run's own disagreement count, in records
    print(f"\n  H1 liftability : LIFT {lift_n} vs FUSED {fused_n} "
          f"(delta {lift_n - fused_n}, floor ~{floor})")
    print(f"  H2 aspect      : ASPECTUAL {asp_n} vs EXPLICIT {exp_n} "
          f"(delta {asp_n - exp_n}, floor ~{floor})")
    print(f"  H3 interaction : LIFT_ASPECTUAL {pool['LIFT_ASPECTUAL'][0]}"
          f"/{pool['LIFT_ASPECTUAL'][1]} vs next-worst "
          f"{max(pool[c][0] for c in CELLS if c != 'LIFT_ASPECTUAL')}")

    lifted = sum(1 for arm in results.values() for r in arm["rows"]
                 if r["verdict"] == "FABRICATED" and r["lift"])
    total_fab = lift_n + fused_n
    print(f"\n  mechanism check: {lifted}/{total_fab} fabrications are literal "
          f"lifts of the record's cause NP")

    print("\nevery FABRICATED value (hand-check these):")
    for arm in results.values():
        for r in arm["rows"]:
            if r["verdict"] == "FABRICATED":
                print(f"  [{arm['arm']:<12} {r['cell']:<15} {r['stem']} "
                      f"lift={str(r['lift']):<5}] {r['root_cause'][:60]}")
    print("\ncontrols (PRESENT) that came back empty, if any:")
    for arm in results.values():
        for r in arm["rows"]:
            if r["verdict"] == "control-EMPTY":
                print(f"  [{arm['arm']}] {r['stem']}")
    trunc = [r for arm in results.values() for r in arm["rows"]
             if r["finish"] not in ("stop", "")]
    print(f"\ntruncated/incomplete responses: {len(trunc)}")
    print(f"raw: {out_path}")


if __name__ == "__main__":
    main()
