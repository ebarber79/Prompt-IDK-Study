"""Drill L5 (Order) from the Prompt IDKs catalog, run for real.

Design, exactly as the card specifies:
  A      -- the 'current' example order
  B..E   -- four random permutations, everything else identical
  same 20 test inputs through all five; spread = the prompt's real error bar

Controls:
  * temperature=0, so ordering is the ONLY thing that varies between arms.
  * arm A is run twice (A and A_repeat) to prove the spread is not sampling noise.
"""

import json
import os
import random
import time
import urllib.error
import urllib.request

MODEL = "llama-3.1-8b-instant"
URL = "https://api.groq.com/openai/v1/chat/completions"
KEY = os.environ["GROQ_API_KEY"]

# 8 labelled examples, balanced 4/4.
EXAMPLES = [
    ("The battery lasts all day and the screen is gorgeous.", "POSITIVE"),
    ("Arrived cracked, and support never replied.", "NEGATIVE"),
    ("Does exactly what it says. No complaints.", "POSITIVE"),
    ("It works, but I've had to restart it every morning.", "NEGATIVE"),
    ("Cheaper than the competition and just as sturdy.", "POSITIVE"),
    ("The app is a mess of menus I can never find twice.", "NEGATIVE"),
    ("Setup took five minutes and my parents managed it alone.", "POSITIVE"),
    ("Looks premium. Fell apart in three weeks.", "NEGATIVE"),
]

# 20 held-out test items. Deliberately subtle (negation, concession, faint
# praise, sarcasm) -- the regime where order sensitivity is reported to bite.
TEST = [
    ("I was ready to hate this and I don't.", "POSITIVE"),
    ("Not the disaster the reviews promised.", "POSITIVE"),
    ("Sure, if you enjoy waiting on hold for an hour.", "NEGATIVE"),
    ("It's fine. I guess. For the price.", "POSITIVE"),
    ("Nothing wrong with it, nothing right either.", "NEGATIVE"),
    ("Took a while to click, but now I'd not go back.", "POSITIVE"),
    ("Would recommend, with reservations about the hinge.", "POSITIVE"),
    ("Beautiful object. Completely useless.", "NEGATIVE"),
    ("Worked perfectly until it didn't, which was Tuesday.", "NEGATIVE"),
    ("Better than my last one, and that's not saying much.", "POSITIVE"),
    ("I've stopped noticing it, which is the highest praise.", "POSITIVE"),
    ("Every update makes it slightly worse.", "NEGATIVE"),
    ("Not bad for a first attempt from this company.", "POSITIVE"),
    ("Can't fault the build. Can't forgive the software.", "NEGATIVE"),
    ("Does one thing, does it without fuss.", "POSITIVE"),
    ("The manual is longer than the warranty is useful.", "NEGATIVE"),
    ("Honestly surprised by how little I use it.", "NEGATIVE"),
    ("My only complaint is that I didn't buy two.", "POSITIVE"),
    ("Fast shipping. That's the compliment.", "NEGATIVE"),
    ("It has never once let me down.", "POSITIVE"),
]

SYSTEM = (
    "You classify product reviews. Reply with exactly one word: "
    "POSITIVE or NEGATIVE. No punctuation, no explanation."
)


def build_prompt(order, text):
    shots = "\n\n".join(
        f"Review: {EXAMPLES[i][0]}\nLabel: {EXAMPLES[i][1]}" for i in order
    )
    return f"{shots}\n\nReview: {text}\nLabel:"


def call(prompt, attempt=0):
    body = json.dumps(
        {
            "model": MODEL,
            "temperature": 0,
            "max_tokens": 4,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        URL,
        data=body,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json",
            # default Python-urllib UA is 403'd at Groq's edge
            "User-Agent": "prompt-idk-drill/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
        return payload["choices"][0]["message"]["content"].strip().upper()
    except urllib.error.HTTPError as exc:
        if exc.code in (429, 500, 502, 503) and attempt < 8:
            wait = exc.headers.get("retry-after")
            time.sleep(float(wait) if wait else min(30, 2 ** attempt))
            return call(prompt, attempt + 1)
        raise
    except (urllib.error.URLError, ConnectionResetError, TimeoutError):
        if attempt < 8:
            time.sleep(min(30, 2 ** attempt))
            return call(prompt, attempt + 1)
        raise


def run_arm(name, order):
    preds, correct = [], 0
    for text, gold in TEST:
        raw = call(build_prompt(order, text))
        pred = "POSITIVE" if raw.startswith("POS") else "NEGATIVE" if raw.startswith("NEG") else "?"
        preds.append(pred)
        correct += pred == gold
        time.sleep(1.1)
    acc = correct / len(TEST) * 100
    print(f"  {name:<9} order={list(order)}  acc={acc:5.1f}%  ({correct}/{len(TEST)})", flush=True)
    return {"arm": name, "order": list(order), "acc": acc, "preds": preds}


def main():
    rng = random.Random(20260729)
    base = list(range(len(EXAMPLES)))
    arms = [("A", tuple(base))]
    for label in ("B", "C", "D", "E"):
        perm = base[:]
        rng.shuffle(perm)
        arms.append((label, tuple(perm)))
    arms.append(("A_repeat", tuple(base)))  # control: temp=0 determinism

    print(f"model={MODEL}  temp=0  {len(TEST)} test items  {len(arms)} arms\n")
    results = [run_arm(name, order) for name, order in arms]

    perms = [r for r in results if r["arm"] in ("A", "B", "C", "D", "E")]
    accs = [r["acc"] for r in perms]
    a = next(r for r in results if r["arm"] == "A")
    a_rep = next(r for r in results if r["arm"] == "A_repeat")

    print("\n--- result ---")
    print(f"spread across 5 orderings: {min(accs):.1f}% .. {max(accs):.1f}%  "
          f"(range {max(accs) - min(accs):.1f} pts, mean {sum(accs)/len(accs):.1f}%)")
    identical = a["preds"] == a_rep["preds"]
    print(f"control (A vs A_repeat, same order, temp=0): "
          f"{'IDENTICAL - spread is not sampling noise' if identical else 'DIFFERED - temp=0 is not deterministic here'}")

    flips = sum(
        1 for i in range(len(TEST))
        if len({p["preds"][i] for p in perms}) > 1
    )
    print(f"test items whose label changed with ordering alone: {flips}/{len(TEST)}")

    out = "drills/L5_order_results.json"
    with open(out, "w") as fh:
        json.dump({"model": MODEL, "results": results, "test": TEST}, fh, indent=2)
    print(f"raw: {out}")


if __name__ == "__main__":
    main()
