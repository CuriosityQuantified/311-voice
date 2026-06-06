#!/usr/bin/env python3
"""SLM-vs-Gemini bake-off for the 311 service-selection step.

Both backends pick from the SAME Pinecone candidates per complaint (retrieval is shared, so
the comparison is purely about pick quality). We report:

  * AGREEMENT (primary): how often the SLM picks the same KA as Gemini, over ALL samples.
    Needs no subjective gold — direct evidence the SLM can stand in for Gemini.
  * ABSOLUTE ACCURACY (correctness floor): on the SCORABLE categories (those with an
    unambiguous keyword in the correct candidate's title/description). Agency-coded /
    "general" complaints are excluded from accuracy (gold unreliable) but kept for agreement.
  * RETRIEVAL CEILING: % where any top-5 candidate matches the category (pick can't beat this).
  * LATENCY: per-backend mean / p50 / p95.

Ground truth = each transcript is verbatim from a category template in
data/voice-files/generate_transcripts.py (reverse-mapped here).

Usage:  PYTHONPATH=. python3 scripts/eval_llm.py [N]      # N = sample cap (default all 200)
Env:    needs GEMINI/GOOGLE key (Gemini) + a llama-server on :8080 (SLM).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time

from app.llm.base import Candidate
from app.llm.gemini import GeminiBackend
from app.llm.slm import SLMBackend
from app.match import parse_hits
from app.retrieval import make_retriever

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VOICE = os.path.join(ROOT, "data", "voice-files")

# Categories whose CORRECT 311 service contains an unambiguous keyword -> we can score
# absolute accuracy. Keyword(s) are matched (lowercased) against the picked candidate's
# title+description. Agency-coded/vague categories are intentionally omitted (agreement-only).
SCORABLE = {
    "heat": ["heat", "hot water", "boiler"],
    "noise": ["noise"],
    "pothole": ["pothole", "cave-in", "street condition"],
    "trash": ["sanitation", "garbage", "trash", "litter", "dirty condition",
              "missed collection", "recycling", "dumping"],
    "rats": ["rodent", "rat ", "pest"],
    "mold": ["mold"],
    "plumbing": ["plumb", "leak", "sewer", "drain", "water quality"],
    "electrical": ["electric", "wiring", "elevator"],
    "graffiti": ["graffiti"],
    "tree": ["tree"],
    "sidewalk": ["sidewalk"],
    "street_light": ["street light", "lamp", "traffic signal", "street light condition"],
    "water": ["water main", "hydrant", "catch basin", "flooding", "sewer", "water leak"],
    "bed_bugs": ["bed bug"],
    "sewer": ["sewer", "catch basin"],
    "parking": ["parking", "blocked", "abandoned vehicle", "illegal park", "derelict"],
    "building": ["building", "facade", "structural", "elevator", "construction"],
    "homeless": ["homeless", "encampment"],
    "air_quality": ["air", "smoke", "odor", "fume", "smoking"],
    "animal": ["animal", "dog", "wildlife", "rodent"],
    "asbestos": ["asbestos"],
    "lead": ["lead"],
    "scaffolding": ["scaffold", "shed"],
    "taxi": ["taxi", "for-hire", "tlc", "driver"],
    "food": ["food", "restaurant"],
    "school": ["school"],
}


def load_gold():
    """transcript text -> category, via the generator's TEMPLATES (verbatim reverse map)."""
    spec = importlib.util.spec_from_file_location(
        "gt", os.path.join(VOICE, "generate_transcripts.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rev = {t.strip(): cat for cat, texts in mod.TEMPLATES.items() for t in texts}
    transcripts = json.load(open(os.path.join(VOICE, "transcripts.json")))

    def cat_of(t):
        t = t.strip()
        if t in rev:
            return rev[t]
        for tmpl, cat in rev.items():           # variants are "<template> <loc>. <time>"
            if t.startswith(tmpl):
                return cat
        return None

    return [(t, cat_of(t)) for t in transcripts]


def cand_matches_category(c: Candidate, category: str) -> bool:
    kws = SCORABLE.get(category)
    if not kws:
        return False
    hay = f"{c.title} {c.description}".lower()
    return any(k in hay for k in kws)


def pct(n, d):
    return 0.0 if d == 0 else 100.0 * n / d


def summarize(latencies):
    s = sorted(latencies)
    n = len(s)
    if n == 0:
        return {"mean": 0, "p50": 0, "p95": 0}
    return {"mean": sum(s) / n, "p50": s[n // 2], "p95": s[min(n - 1, int(n * 0.95))]}


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    gold = load_gold()[:limit]
    retr = make_retriever()
    gemini, slm = GeminiBackend(), SLMBackend()

    rows = []
    agree = 0
    retr_hit = 0           # any candidate matches gold (scorable only)
    scorable_n = 0
    g_correct = s_correct = 0
    g_lat, s_lat = [], []

    for i, (text, cat) in enumerate(gold, 1):
        cands = parse_hits(retr(text))
        by_ka = {c.ka: c for c in cands}

        t = time.time(); gs = gemini.select_service(text, cands); g_lat.append(time.time() - t)
        t = time.time(); ss = slm.select_service(text, cands); s_lat.append(time.time() - t)

        same = gs.picked_ka == ss.picked_ka
        agree += same

        scorable = cat in SCORABLE
        gc = sc = None
        if scorable:
            scorable_n += 1
            if any(cand_matches_category(c, cat) for c in cands):
                retr_hit += 1
            gc = cand_matches_category(by_ka.get(gs.picked_ka), cat) if gs.picked_ka in by_ka else False
            sc = cand_matches_category(by_ka.get(ss.picked_ka), cat) if ss.picked_ka in by_ka else False
            g_correct += gc
            s_correct += sc

        rows.append({"i": i, "category": cat, "text": text,
                     "gemini": gs.picked_ka, "slm": ss.picked_ka, "agree": same,
                     "scorable": scorable, "gemini_correct": gc, "slm_correct": sc,
                     "gemini_s": round(g_lat[-1], 3), "slm_s": round(s_lat[-1], 3)})
        if i % 10 == 0:
            print(f"  [{i}/{len(gold)}] agree={pct(agree,i):.0f}%  "
                  f"G={pct(g_correct,scorable_n):.0f}%/S={pct(s_correct,scorable_n):.0f}% "
                  f"(scorable n={scorable_n})", flush=True)

    n = len(gold)
    report = {
        "n": n,
        "agreement_pct": round(pct(agree, n), 1),
        "scorable_n": scorable_n,
        "retrieval_ceiling_pct": round(pct(retr_hit, scorable_n), 1),
        "gemini_accuracy_pct": round(pct(g_correct, scorable_n), 1),
        "slm_accuracy_pct": round(pct(s_correct, scorable_n), 1),
        "gemini_latency_s": {k: round(v, 3) for k, v in summarize(g_lat).items()},
        "slm_latency_s": {k: round(v, 3) for k, v in summarize(s_lat).items()},
    }
    # decision rule (PLAN §5): SLM if absolute >=80% AND within 10 pts of Gemini
    slm_ok = (report["slm_accuracy_pct"] >= 80.0
              and (report["gemini_accuracy_pct"] - report["slm_accuracy_pct"]) <= 10.0)
    report["decision"] = "SLM" if slm_ok else "GEMINI"

    out = os.path.join(ROOT, "data", "eval-results.json")
    json.dump({"report": report, "rows": rows}, open(out, "w"), indent=2)

    print("\n" + "=" * 60)
    print(f"SLM vs GEMINI bake-off  (n={n})")
    print("=" * 60)
    print(f"Agreement (SLM==Gemini):     {report['agreement_pct']}%  over all {n}")
    print(f"Scorable samples:            {scorable_n}")
    print(f"Retrieval ceiling:           {report['retrieval_ceiling_pct']}%")
    print(f"Gemini accuracy:             {report['gemini_accuracy_pct']}%")
    print(f"SLM accuracy:                {report['slm_accuracy_pct']}%")
    print(f"Gemini latency (mean/p50/p95): {report['gemini_latency_s']}")
    print(f"SLM latency    (mean/p50/p95): {report['slm_latency_s']}")
    print(f"\nDECISION (>=80% abs & within 10pt of Gemini): {report['decision']}")
    print(f"\nFull rows -> {out}")


if __name__ == "__main__":
    main()
