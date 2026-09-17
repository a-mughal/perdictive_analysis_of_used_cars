"""
Consumer Engine — deterministic skeleton.

Nothing here thinks. This module:
  init      creates runs/<slug>/brief.json
  validate  checks every agent JSON against schemas/ and the engine's extra rules
  score     computes evidence, buyer, innovation, feasibility scores + Monte-Carlo
  verdict   renders VERDICT.md

Usage:
  python -m engine.engine init runs/<slug> --name "Product" [--url URL]
  python -m engine.engine validate runs/<slug>
  python -m engine.engine score runs/<slug>
  python -m engine.engine verdict runs/<slug>
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"

AGENT_FILES = ["scout", "buyer", "innovaty", "genius", "critic"]
FRAMEWORK_PREFIXES = (
    "kahneman.", "ariely.", "cialdini.", "underhill.", "jtbd.", "ulwick.", "kano.",
    "nudge.", "schwartz.", "rogers.", "moore.", "sharp.", "sutherland.", "dunford.",
    "post.", "gate.", "triz.", "erric.", "forecast.",
)

# ----------------------------------------------------------------------------- io

def load(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:40] or "product"


# ---------------------------------------------------------------------------- init

def cmd_init(run_dir: Path, name: str, url: str | None):
    run_dir.mkdir(parents=True, exist_ok=True)
    brief = {
        "slug": run_dir.name if re.fullmatch(r"[a-z0-9-]{2,40}", run_dir.name) else slugify(name),
        "product_name": name,
        "source_url": url or "",
        "marketplace": "amazon.com",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current_state": "category" if (url and "/s?" in url) else ("competitor_listing" if url else "idea"),
        "target_buyer": {"description": "TO FILL: who is buying, in one sentence", "context": "", "price_band_usd": {"min": 0, "max": 0}},
        "seller_constraints": {"launch_budget_usd": 0, "time_to_market_months": 0, "origin_country": "CN", "existing_supplier": False, "must_keep": [], "must_avoid": []},
        "user_hypotheses": [],
        "assumptions": [],
        "iterations": 0,
    }
    out = run_dir / "brief.json"
    if out.exists():
        print(f"brief.json already exists at {out}; not overwriting")
        return
    dump(brief, out)
    print(f"created {out}\nfill target_buyer and seller_constraints before phase 1")


# ------------------------------------------------------------------------ validate

def _jsonschema_validate(instance, schema_name: str) -> list[str]:
    """Validate with jsonschema if installed; otherwise a minimal required-keys check."""
    schema = load(SCHEMAS / f"{schema_name}.json")
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource

        range_schema = load(SCHEMAS / "_range.json")
        registry = Registry().with_resource("_range.json", Resource.from_contents(range_schema))
        validator = Draft202012Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
        return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]
    except ImportError:
        missing = [k for k in schema.get("required", []) if k not in instance]
        return [f"<root>: missing required key '{k}'" for k in missing]


def _walk(obj, path=""):
    """Yield (path, value) for every leaf and dict in a JSON tree."""
    if isinstance(obj, dict):
        yield path, obj
        for k, v in obj.items():
            yield from _walk(v, f"{path}/{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def _range_rule_errors(obj) -> list[str]:
    """Extra rule: any dict with low/base/high must be ordered and not degenerate on uncertain items."""
    errs = []
    for p, v in _walk(obj):
        if isinstance(v, dict) and {"low", "base", "high"} <= set(v):
            lo, b, hi = v["low"], v["base"], v["high"]
            if not (lo <= b <= hi):
                errs.append(f"{p}: range not ordered low<=base<=high ({lo},{b},{hi})")
            if lo == hi and b != 0:
                errs.append(f"{p}: degenerate range (low==high) — point estimates are rejected; widen it")
    return errs


def _quote_rule_errors(obj) -> list[str]:
    """Copyright hygiene: paraphrased examples must be short."""
    errs = []
    for p, v in _walk(obj):
        if isinstance(v, str) and p.endswith("]") and "paraphrased_examples" in p and len(v.split()) > 25:
            errs.append(f"{p}: paraphrased example too long ({len(v.split())} words) — condense")
    return errs


def cmd_validate(run_dir: Path) -> int:
    failures = 0
    brief_path = run_dir / "brief.json"
    if brief_path.exists():
        errs = _jsonschema_validate(load(brief_path), "product_brief")
        _report("brief", errs)
        failures += bool(errs)
    else:
        print("brief.json missing"); failures += 1

    for name in AGENT_FILES:
        p = run_dir / f"{name}.json"
        if not p.exists():
            print(f"[{name}] not yet written")
            continue
        try:
            inst = load(p)
        except json.JSONDecodeError as e:
            print(f"[{name}] INVALID JSON: {e}"); failures += 1; continue
        errs = _jsonschema_validate(inst, name)
        errs += _range_rule_errors(inst)
        errs += _quote_rule_errors(inst)
        if name == "genius" and inst.get("planning_fallacy_multiplier", 1.3) < 1.3:
            errs.append("planning_fallacy_multiplier: must be >= 1.3 (see knowledge/04 §0)")
        if name == "innovaty":
            heroes = [i for i in inst.get("ideas", []) if i.get("role") == "hero"]
            if len(heroes) != 1:
                errs.append(f"ideas: exactly one hero required, found {len(heroes)}")
            elif heroes[0].get("thumbnail_visibility") != "high":
                errs.append("ideas[hero]: hero must have thumbnail_visibility=high")
            for i in inst.get("ideas", []):
                if i.get("thumbnail_visibility") == "low" and i.get("priority") == "now" and not i.get("fixes_complaint_clusters"):
                    errs.append(f"ideas[{i.get('idea_id')}]: low visibility + priority now requires a fixed complaint cluster")
        _report(name, errs)
        failures += bool(errs)
    return 1 if failures else 0


def _report(name, errs):
    if errs:
        print(f"[{name}] {len(errs)} problem(s):")
        for e in errs:
            print(f"   - {e}")
    else:
        print(f"[{name}] ok")


# --------------------------------------------------------------------------- score

def _tag_coverage(obj) -> tuple[int, int]:
    """Count items that have >=1 framework tag vs items that have a 'tags' key at all."""
    tagged = total = 0
    for p, v in _walk(obj):
        if isinstance(v, dict) and ("tags" in v or "triz_or_erric_tags" in v):
            total += 1
            tags = v.get("tags") or v.get("triz_or_erric_tags") or []
            if any(str(t).startswith(FRAMEWORK_PREFIXES) for t in tags):
                tagged += 1
    return tagged, total


def score_evidence(scout, critic) -> dict:
    facts = scout.get("facts", [])
    sourced = sum(1 for f in facts if str(f.get("source", "")).startswith("http"))
    fee = scout.get("fee_inputs", {})
    stale = sum(1 for k, v in fee.items() if isinstance(v, dict) and v.get("stale"))
    unsourced = len(critic.get("unsourced_claim_paths", [])) if critic else 0
    score = 100.0
    score *= (sourced / len(facts)) if facts else 0
    score -= 8 * stale
    score -= 4 * unsourced
    return {"facts": len(facts), "sourced": sourced, "stale_fee_inputs": stale, "unsourced_claims_flagged": unsourced, "score": round(max(0, min(100, score)), 1)}


def score_buyer(buyer) -> dict:
    p = buyer.get("purchase_probability_current", {})
    tagged, total = _tag_coverage(buyer)
    coverage = tagged / total if total else 0
    opps = sorted((o.get("opportunity", 0) for o in buyer.get("outcomes_ulwick", [])), reverse=True)
    top_opp = opps[0] if opps else 0
    # Headroom: how much room a better product has = (1 - p_buy) weighted by top opportunity
    headroom = (1 - p.get("buy", 0.5)) * min(1.0, top_opp / 10.0)
    return {
        "p_click": p.get("click"), "p_cart": p.get("add_to_cart"), "p_buy": p.get("buy"),
        "framework_tag_coverage": round(coverage, 2),
        "top_opportunity": top_opp,
        "underserved_outcomes": sum(1 for o in opps if o >= 6.0),
        "headroom_score": round(100 * headroom * (0.5 + 0.5 * coverage), 1),
    }


_GATE_W = {"gate.image_orientation": 1.0, "gate.image_fit": 1.0, "gate.social_proof": 0.6, "gate.price_vs_anchor": 0.8,
           "gate.title_scan": 0.6, "gate.image_2_to_6": 0.7, "gate.bullets": 0.4, "gate.reviews_negative_first": 0.9,
           "gate.reviews_with_photos": 0.9, "gate.qna": 0.3, "gate.variations": 0.4, "gate.brand_trust": 0.5}
_VIS_W = {"high": 1.0, "medium": 0.55, "low": 0.25}
_COST_W = {"free": 1.0, "cents": 1.2, "dimes": 1.8, "dollars": 3.0, "tooling": 2.5}
_RULING_W = {"realistic": 1.0, "stretch": 0.6, "unrealistic": 0.0}


def score_innovation(innovaty, scout, genius) -> dict:
    clusters = {c["cluster_id"]: c.get("share_of_negative", 0) for c in scout.get("complaint_clusters", [])}
    rulings = {r["idea_id"]: r["ruling"] for r in (genius or {}).get("idea_rulings", [])}
    rows = []
    for idea in innovaty.get("ideas", []):
        gate_w = max([_GATE_W.get(g, 0.3) for g in idea.get("improves_gates", [])] or [0.3])
        fixed = sum(clusters.get(c, 0) for c in idea.get("fixes_complaint_clusters", []))
        vis = _VIS_W.get(idea.get("thumbnail_visibility"), 0.25)
        cost = _COST_W.get(idea.get("cost_tier"), 2.0)
        impact = 100 * gate_w * vis * (0.3 + fixed) / cost
        ruling = rulings.get(idea["idea_id"], "unrated")
        rows.append({"idea_id": idea["idea_id"], "name": idea["name"], "role": idea["role"],
                     "impact_score": round(impact, 1), "ruling": ruling,
                     "weighted": round(impact * _RULING_W.get(ruling, 0.7), 1)})
    rows.sort(key=lambda r: r["weighted"], reverse=True)
    hero = next((r for r in rows if r["role"] == "hero"), None)
    return {"ideas_ranked": rows, "hero": hero,
            "v1_realistic_count": sum(1 for r in rows if r["ruling"] == "realistic"),
            "score": round(min(100, sum(r["weighted"] for r in rows[:4]) / 4), 1) if rows else 0}


def _tri(r: dict, rng: random.Random) -> float:
    lo, b, hi = float(r["low"]), float(r["base"]), float(r["high"])
    if hi <= lo:
        return b
    b = min(max(b, lo), hi)
    return rng.triangular(lo, hi, b)


def monte_carlo(mc: dict, trials: int = 10_000, seed: int = 7) -> dict:
    rng = random.Random(seed)
    profits, paybacks = [], []
    for _ in range(trials):
        price = _tri(mc["price"], rng)
        landed = _tri(mc["landed_cost"], rng)
        contrib = (price
                   - price * _tri(mc["referral_rate"], rng)
                   - _tri(mc["fba_fee"], rng)
                   - _tri(mc["storage_alloc"], rng)
                   - price * _tri(mc["ad_rate"], rng)
                   - _tri(mc["return_rate"], rng) * (0.4 * price + 0.6 * landed)
                   - landed)
        m6, m12 = _tri(mc["monthly_units_m6"], rng), _tri(mc["monthly_units_m12"], rng)
        # linear ramp 0→m6 over months 1–6, m6→m12 over 7–12
        units = [m6 * (i / 6) for i in range(1, 7)] + [m6 + (m12 - m6) * (i / 6) for i in range(1, 7)]
        fixed = _tri(mc["fixed_launch_cost"], rng)
        cum, payback = -fixed, None
        for month, u in enumerate(units, start=1):
            cum += u * contrib
            if payback is None and cum >= 0:
                payback = month
        profits.append(cum)
        paybacks.append(payback if payback else 99)
    profits.sort()
    q = lambda p: profits[int(p * (trials - 1))]
    return {"trials": trials,
            "p_profit_positive_12m": round(sum(1 for x in profits if x > 0) / trials, 3),
            "p_payback_within_12m": round(sum(1 for x in paybacks if x <= 12) / trials, 3),
            "profit_12m_p10": round(q(0.10)), "profit_12m_p50": round(q(0.50)), "profit_12m_p90": round(q(0.90)),
            "median_payback_month": int(statistics.median(paybacks)) if paybacks else None}


def score_feasibility(genius, mc_out) -> dict:
    rails = genius.get("sanity_rails", [])
    passed = sum(1 for r in rails if r.get("pass"))
    fatal = sum(1 for p in genius.get("premortem", []) if p.get("impact") == "fatal" and p.get("probability", 0) >= 0.25)
    s = 100 * (passed / len(rails) if rails else 0.5)
    s = 0.6 * s + 40 * mc_out["p_profit_positive_12m"]
    s -= 15 * fatal
    return {"rails_passed": f"{passed}/{len(rails)}", "high_prob_fatal_risks": fatal,
            "verdict": genius.get("feasibility_verdict"), "score": round(max(0, min(100, s)), 1)}


def decide(evidence, buyer, innovation, feasibility, critic) -> tuple[str, str]:
    fatal_open = sum(1 for f in (critic or {}).get("findings", []) if f.get("severity") == "fatal")
    overall = (critic or {}).get("overall", "fix_and_rerun")
    if overall == "block" or fatal_open:
        return "NO-GO", f"critic: {fatal_open} unresolved fatal finding(s)"
    if evidence["score"] < 50:
        return "NO-GO", "evidence too thin — most facts unsourced or fees stale"
    if feasibility["verdict"] == "unrealistic":
        return "NO-GO", "genius: unrealistic economics"
    if buyer["headroom_score"] < 25:
        return "PIVOT", "buyer sees little room for a better product in this term — change the search term or the product"
    if feasibility["verdict"] == "stretch" or innovation["v1_realistic_count"] < 2:
        return "GO-SMALL", "ship the realistic subset only; prove the jaw before the hero"
    return "GO", "all gates passed"


def cmd_score(run_dir: Path):
    scout = load(run_dir / "scout.json")
    buyer = load(run_dir / "buyer.json")
    innovaty = load(run_dir / "innovaty.json")
    genius = load(run_dir / "genius.json")
    critic = load(run_dir / "critic.json") if (run_dir / "critic.json").exists() else {}
    ev = score_evidence(scout, critic)
    bu = score_buyer(buyer)
    inn = score_innovation(innovaty, scout, genius)
    mc = monte_carlo(genius["mc_inputs"])
    fe = score_feasibility(genius, mc)
    decision, why = decide(ev, bu, inn, fe, critic)
    out = {"scored_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "evidence": ev, "buyer": bu, "innovation": inn, "monte_carlo": mc, "feasibility": fe,
           "decision": decision, "decision_reason": why,
           "critic_overall": critic.get("overall"), "critic_fatal": sum(1 for f in critic.get("findings", []) if f.get("severity") == "fatal")}
    dump(out, run_dir / "scores.json")
    print(json.dumps({"decision": decision, "why": why, "evidence": ev["score"], "headroom": bu["headroom_score"],
                      "innovation": inn["score"], "feasibility": fe["score"], "p_profit": mc["p_profit_positive_12m"]}, indent=2))


# ------------------------------------------------------------------------- verdict

def _r(rng: dict, unit="$", digits=2) -> str:
    if not isinstance(rng, dict):
        return "—"
    fmt = (lambda x: f"{unit}{x:,.{digits}f}") if unit == "$" else (lambda x: f"{x:,.{digits}f}{unit}")
    return f"{fmt(rng['base'])} ({fmt(rng['low'])}–{fmt(rng['high'])})" + (" ⚠stale" if rng.get("stale") else "")


def cmd_verdict(run_dir: Path):
    brief = load(run_dir / "brief.json")
    scout = load(run_dir / "scout.json")
    buyer = load(run_dir / "buyer.json")
    innovaty = load(run_dir / "innovaty.json")
    genius = load(run_dir / "genius.json")
    critic = load(run_dir / "critic.json") if (run_dir / "critic.json").exists() else {}
    if not (run_dir / "scores.json").exists():
        cmd_score(run_dir)
    s = load(run_dir / "scores.json")
    hero = next((i for i in innovaty["ideas"] if i["role"] == "hero"), {})
    rec = genius["recommended_first_version"]
    mc = s["monte_carlo"]
    top_fears = buyer["fears"][:3]
    top_clusters = sorted(scout["complaint_clusters"], key=lambda c: -c["share_of_negative"])[:3]

    lines = [
        f"# {brief['product_name']} — VERDICT: **{s['decision']}**",
        f"*{s['decision_reason']}*  ·  {date.today().isoformat()}  ·  run `{brief['slug']}`",
        "",
        "## Scores",
        f"| Evidence | Buyer headroom | Innovation | Feasibility | P(profit 12 m) |",
        f"|---|---|---|---|---|",
        f"| {s['evidence']['score']} | {s['buyer']['headroom_score']} | {s['innovation']['score']} | {s['feasibility']['score']} | {mc['p_profit_positive_12m']:.0%} |",
        "",
        "## The market (scout)",
        f"- Primary term **{scout['price_ladder']['primary_term']}**, first-page median **${scout['price_ladder']['median']:.2f}** — {scout['price_ladder']['anchor_note']}",
        "- Top complaint clusters: " + "; ".join(f"{c['pattern']} ({c['share_of_negative']:.0%})" for c in top_clusters),
        "",
        "## The buyer",
        f"- Would buy the current product: click {buyer['purchase_probability_current']['click']:.0%} → cart {buyer['purchase_probability_current']['add_to_cart']:.0%} → buy {buyer['purchase_probability_current']['buy']:.0%}",
        f"- Will pay up to **${buyer['price_psychology']['max_with_reason_usd']:.2f}** if the reason is visible: *{buyer['price_psychology']['reason_required']}*",
        "- Top fears: " + "; ".join(f"“{f['question']}”" for f in top_fears),
        "",
        "## The product (innovaty)",
        f"- **Hero:** {hero.get('name','—')} — {hero.get('buyer_sentence','')}",
        f"- v1 now: {', '.join(innovaty['version_plan']['v1_now'])}",
        f"- Title (first 60): `{innovaty['listing_implications']['title_first_60']}`",
        "",
        "## The money (genius)",
        f"- Recommended first version: **{rec['version_id']}** → landed {_r(rec['landed_cost_usd'])}, price {_r(rec['price_usd'])}, contribution {_r(rec['contribution_pct'], '%', 0)}",
        f"- Break-even {_r(rec['break_even_units'], '', 0)} units · ~{rec['months_to_break_even_base']} months at base forecast",
        f"- Year-1 profit P10 / P50 / P90: ${mc['profit_12m_p10']:,} / ${mc['profit_12m_p50']:,} / ${mc['profit_12m_p90']:,} · P(payback ≤ 12 m) {mc['p_payback_within_12m']:.0%}",
        f"- Time to first sale: {_r(genius['timeline']['weeks_to_first_sale'], ' wk', 0)} (planning-fallacy ×{genius.get('planning_fallacy_multiplier', '—')})",
        f"- Feasibility: **{genius['feasibility_verdict']}**",
        "",
        "## The red team (critic)",
        f"- Overall: **{critic.get('overall','not run')}** · fatal {s['critic_fatal']} · " + f"{len(critic.get('findings', []))} findings",
    ]
    for t in critic.get("three_things_the_founder_must_hear", []):
        lines.append(f"- {t}")
    lines += ["", "## Genius, to the founder"]
    lines += [f"> {t}" for t in genius["three_sentences_to_founder"]]
    lines += ["", "## Next action",
              {"GO": "Send RFQ for the recommended version to two suppliers; brief the photographer on the hero.",
               "GO-SMALL": "Tool the realistic subset only. Re-run genius on the hero after 100 reviews.",
               "PIVOT": "Re-run scout on the alternative search terms; the buyer is not in this grid.",
               "NO-GO": "Do not tool. Resolve the fatal findings or choose another product."}[s["decision"]]]
    (run_dir / "VERDICT.md").write_text("\n".join(lines), encoding="utf-8")
    print((run_dir / "VERDICT.md").read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------ cli

def main(argv=None):
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("run_dir"); p.add_argument("--name", required=True); p.add_argument("--url")
    for c in ("validate", "score", "verdict"):
        sub.add_parser(c).add_argument("run_dir")
    a = ap.parse_args(argv)
    rd = Path(a.run_dir)
    if a.cmd == "init":
        cmd_init(rd, a.name, a.url)
    elif a.cmd == "validate":
        sys.exit(cmd_validate(rd))
    elif a.cmd == "score":
        cmd_score(rd)
    elif a.cmd == "verdict":
        cmd_verdict(rd)


if __name__ == "__main__":
    main()
