#!/usr/bin/env python3
"""
Consumer Engine — the whole deterministic side of the product-decision engine, in one file.

Nothing in here thinks. It defines the contracts each agent must satisfy, checks their output,
does every piece of arithmetic (so no model ever has to), runs the Monte-Carlo, scores the run
and writes the one page a human reads.

    python engine.py new     runs/cable-clips --name "magnetic cable clips" [--url URL]
    python engine.py new     runs/cable-clips --name "cable clips" --focus URL1 URL2 [--mine 1]
    python engine.py next    runs/cable-clips              # which phase to run now
    python engine.py prompt  runs/cable-clips buyer        # the exact prompt for that phase
    python engine.py check   runs/cable-clips              # validate + cross-file coherence
    python engine.py score   runs/cable-clips              # economics + Monte-Carlo + readiness
    python engine.py report  runs/cable-clips              # writes the one-page REPORT.md
    python engine.py demo                                  # self-test on synthetic data, no API
    python engine.py run "magnetic cable clips" [--focus URL...] [--fast]   # drive it via the API

Dependencies: none for everything except `run`, which needs `pip install anthropic`.
The agent briefs and the knowledge base live in CLAUDE.md next to this file.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE / "CLAUDE.md"
PHASES = ["scout", "competition", "buyer", "innovaty", "genius", "critic"]
REQUIRED = ("scout", "buyer", "innovaty", "genius")     # competition is scored when present
TIERS = ("simple", "moderate", "premium")
TIER_HELP = {"simple": "poly bag or sleeve + one printed card — cents",
             "moderate": "printed tuck box + paper tray or insert — dimes",
             "premium": "rigid box, magnetic lid, foam or moulded insert — dollars"}

DEFAULT_MODEL = "claude-opus-5"
FAST_MODELS = {"scout": "claude-sonnet-5", "competition": "claude-sonnet-5",
               "buyer": "claude-sonnet-5", "innovaty": "claude-sonnet-5"}
MC_TRIALS = 10_000
MC_SEED = 7

# Any judgement an agent makes should carry one of these prefixes. See CLAUDE.md § KNOWLEDGE.
TAGS = ("kahneman.", "ariely.", "cialdini.", "underhill.", "jtbd.", "ulwick.", "kano.", "nudge.",
        "schwartz.", "rogers.", "moore.", "sharp.", "sutherland.", "dunford.", "post.", "gate.",
        "triz.", "erric.", "forecast.", "law.")


# ============================================================================ contract language
# A contract is a tree of nodes. Each node knows how to (a) validate a value and (b) print itself
# as a readable skeleton for the agent prompt. That keeps the contract and its documentation from
# ever drifting apart, which is what a separate schemas/ folder could not guarantee.

def S(h, req=True, minlen=1, maxlen=None):
    return {"t": "str", "h": h, "req": req, "minlen": minlen, "maxlen": maxlen}

def U(h="source URL", req=True):
    return {"t": "url", "h": h, "req": req}

def N(h, req=True, lo=None, hi=None):
    return {"t": "num", "h": h, "req": req, "lo": lo, "hi": hi}

def P(h, req=True):  # probability / share, 0-1
    return {"t": "num", "h": h + " (0-1)", "req": req, "lo": 0, "hi": 1}

def B(h, req=True):
    return {"t": "bool", "h": h, "req": req}

def EN(h, *opts, req=True):
    return {"t": "enum", "h": h, "opts": opts, "req": req}

def RG(h, req=True, pos=False):
    """pos=True means the low end must be above zero — a price or a cost cannot be free."""
    return {"t": "range", "h": h, "req": req, "pos": pos}

def AR(item, h="", lo=0, hi=None, req=True):
    return {"t": "list", "item": item, "h": h, "lo": lo, "hi": hi, "req": req}

def OB(fields, h="", req=True):
    return {"t": "obj", "f": fields, "h": h, "req": req}


def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and not math.isnan(float(v))


def check(node, val, path, errs, relax=0):
    """Validate `val` against `node`, appending 'path: problem' strings to errs."""
    t = node["t"]
    if t == "obj":
        if not isinstance(val, dict):
            errs.append(f"{path}: expected an object"); return
        for k, sub in node["f"].items():
            p = f"{path}.{k}" if path else k
            empty = k not in val or val[k] is None or (val[k] in ("", []) and not sub.get("req"))
            if empty:
                if sub.get("req"):
                    errs.append(f"{p}: missing ({sub['h']})")
                continue
            check(sub, val[k], p, errs, relax)
    elif t == "list":
        if not isinstance(val, list):
            errs.append(f"{path}: expected a list"); return
        lo = node["lo"]
        if lo and relax and lo != node.get("hi"):
            lo = max(1, lo - relax)
        if len(val) < lo:
            errs.append(f"{path}: needs at least {lo} items, has {len(val)}")
        if node["hi"] and len(val) > node["hi"]:
            errs.append(f"{path}: at most {node['hi']} items, has {len(val)}")
        for i, v in enumerate(val):
            check(node["item"], v, f"{path}[{i}]", errs, relax)
    elif t == "range":
        if not isinstance(val, dict):
            errs.append(f"{path}: expected a range object {{low, base, high, assumption}}"); return
        for k in ("low", "base", "high"):
            if not _isnum(val.get(k)):
                errs.append(f"{path}.{k}: missing or not a number"); return
        lo, b, hi = float(val["low"]), float(val["base"]), float(val["high"])
        if not lo <= b <= hi:
            errs.append(f"{path}: range must be ordered low <= base <= high, got ({lo}, {b}, {hi})")
        elif lo == hi and b != 0:
            errs.append(f"{path}: point estimate disguised as a range (low == high) — widen it")
        if node.get("pos") and lo <= 0:
            errs.append(f"{path}: must be above zero at the low end, got {lo}")
        a = val.get("assumption", "")
        if not isinstance(a, str) or len(a.strip()) < 8:
            errs.append(f"{path}.assumption: say in a sentence what this range assumes")
    elif t == "enum":
        if val not in node["opts"]:
            errs.append(f"{path}: must be one of {'|'.join(map(str, node['opts']))}, got {val!r}")
    elif t == "num":
        if not _isnum(val):
            errs.append(f"{path}: expected a number, got {val!r}"); return
        if node.get("lo") is not None and val < node["lo"]:
            errs.append(f"{path}: must be >= {node['lo']}, got {val}")
        if node.get("hi") is not None and val > node["hi"]:
            errs.append(f"{path}: must be <= {node['hi']}, got {val}")
    elif t == "bool":
        if not isinstance(val, bool):
            errs.append(f"{path}: expected true or false")
    elif t == "url":
        if not (isinstance(val, str) and val.startswith(("http://", "https://"))):
            errs.append(f"{path}: needs a real source URL (a claim without one is deleted at scoring)")
    elif t == "str":
        if not isinstance(val, str):
            errs.append(f"{path}: expected a string"); return
        if len(val.strip()) < node.get("minlen", 0):
            errs.append(f"{path}: too short, needs >= {node['minlen']} characters")
        if node.get("maxlen") and len(val) > node["maxlen"]:
            errs.append(f"{path}: too long, max {node['maxlen']} characters")


def render(node, ind=0, relax=0) -> str:
    """Print a contract as a compact, readable skeleton for the prompt."""
    pad = "  " * ind
    t = node["t"]
    if t == "obj":
        rows = []
        for k, sub in node["f"].items():
            body = render(sub, ind + 1, relax).lstrip()
            if not sub.get("req"):
                body += " — OPTIONAL" if "#" in body.rsplit("\n", 1)[-1] else "   # OPTIONAL"
            rows.append(f'{pad}  "{k}": {body}')
        return "{\n" + "\n".join(rows) + f"\n{pad}}}"
    if t == "list":
        lo = node["lo"]
        if lo and relax and lo != node.get("hi"):
            lo = max(1, lo - relax)
        card = f">= {lo}" if lo else ""
        card += (" and " if card and node["hi"] else "") + (f"<= {node['hi']}" if node["hi"] else "")
        note = " ".join(x for x in [f"{card} items" if card else "", node["h"]] if x).strip(" ,")
        head = "[" + (f"   # {note}" if note else "")
        return head + "\n" + pad + "    " + render(node["item"], ind + 2, relax).lstrip() + f"\n{pad}  ]"
    if t == "range":
        return '{"low": n, "base": n, "high": n, "assumption": "why"}   # ' + node["h"]
    if t == "enum":
        return "|".join(map(str, node["opts"])) + (f"   # {node['h']}" if node["h"] else "")
    if t == "url":
        return f'"https://…"   # {node["h"]}'
    if t == "num":
        return f"number   # {node['h']}"
    if t == "bool":
        return f"true|false   # {node['h']}"
    return f'"…"   # {node["h"]}'


# ==================================================================================== contracts

TAGLIST = AR(S("a framework tag, e.g. kano.must_be"), "framework tags", lo=1)

BRIEF = OB({
    "slug": S("kebab-case run id"),
    "product_name": S("what we are analysing"),
    "source_url": U("listing or category URL", req=False),
    "marketplace": S("amazon.com unless stated"),
    "created_at": S("ISO timestamp"),
    "mode": EN("focus = only the named products; category = sweep the term", "focus", "category"),
    "target_buyer": OB({
        "description": S("who is buying, in one sentence", minlen=10),
        "context": S("where and when they buy", req=False),
        "price_band_usd": OB({"min": N("floor"), "max": N("ceiling")}, req=False),
    }),
    "seller_constraints": OB({
        "launch_budget_usd": N("cash available", req=False),
        "time_to_market_months": N("deadline", req=False),
        "origin_country": S("manufacturing origin", req=False),
        "must_keep": AR(S("constraint"), req=False),
        "must_avoid": AR(S("constraint"), req=False),
    }, req=False),
    "focus_products": AR(OB({
        "product_id": S("P1..P5"),
        "url": U("product URL"),
        "role": EN("which one is ours", "mine", "competitor", "reference"),
        "name": S("short name", req=False),
    }), "the only products the engine may think about, in focus mode", req=False),
    "search_budget_per_product": N("hard cap on web searches per product in focus mode", req=False),
    "search_budget": N("hard cap on web searches in category mode (default 8)", req=False),
    "packaging_tier": EN("chosen by the founder before the run", *TIERS, req=False),
    "packaging_note": S("anything the founder said about the packaging", req=False),
    "user_hypotheses": AR(S("something the seller believes and wants tested"), req=False),
    "assumptions": AR(S("what we assumed rather than knew"), req=False),
    "iterations": N("fix-loop count", req=False),
}, "runs/<slug>/brief.json")

SCOUT = OB({
    "retrieved_at": S("ISO date of research"),
    "facts": AR(OB({
        "fact_id": S("F1, F2, …"),
        "statement": S("one fact, paraphrased, never quoted", minlen=10),
        "source": U(),
        "confidence": EN("how sure", "high", "medium", "low"),
    }), "every number anyone downstream uses must appear here first", lo=5),
    "search_terms": AR(OB({
        "term": S("the literal words a buyer types"),
        "seasonal": B("does demand swing by season", req=False),
        "notes": S("why this term", req=False),
    }), lo=3),
    "price_ladder": OB({
        "primary_term": S("the term the ladder describes"),
        "min": N("cheapest on page 1", req=False),
        "median": N("the visual anchor — median of the first row"),
        "max": N("dearest on page 1", req=False),
        "typical_pack_count": N("units per pack", req=False),
        "anchor_note": S("what the anchor means for pricing", minlen=10),
    }),
    "variant_chosen": OB({
        "description": S("the shape/dimension/pack that wins the category"),
        "why": S("review count, rank or share that says this variant is the winner", minlen=10),
    }, "when the product exists in several shapes or dimensions, anchor ALL research on the most successful one", req=False),
    "competitors": AR(OB({
        "name": S("title, first 60 chars"),
        "asin": S("ASIN if known", req=False),
        "price_usd": N("shelf price"),
        "rating": N("stars", req=False, lo=0, hi=5),
        "review_count": N("count", req=False),
        "est_monthly_units": N("tracker estimate, +/-40%", req=False),
        "main_image_description": S("what the thumbnail shows, one line", req=False),
        "fact_ids": AR(S("F…"), lo=1),
    }), lo=3),
    "complaint_clusters": AR(OB({
        "cluster_id": S("C1, C2, …"),
        "pattern": S("the failure in the buyer's words, paraphrased", minlen=10),
        "share_of_negative": P("share of 1-2 star reviews in this cluster"),
        "stage": S("which journey stage it happens at (0-6)"),
        "root_cause_hypothesis": S("why it happens", req=False),
        "paraphrased_examples": AR(S("<= 12 words, no reviewer names", maxlen=120), hi=2, req=False),
        "fact_ids": AR(S("F…"), lo=1),
    }), "mined from 1-2 star reviews across >= 3 products", lo=2),
    "praise_clusters": AR(OB({
        "pattern": S("what 5-star reviews love — do not break this"),
        "share_of_positive": P("share of positive reviews"),
    }), lo=1),
    "fee_inputs": OB({
        "referral_rate": RG("Amazon referral fee as a fraction of price"),
        "fba_fee_usd": RG("FBA fulfilment fee for the likely size tier"),
        "storage_per_cuft_month_usd": RG("monthly storage rate"),
        "duty_rate": RG("import duty as a fraction of EXW cost"),
        "sea_freight_usd_per_cbm": RG("ocean freight per cubic metre"),
        "additional_tariff_rate": RG("Section 301 / reciprocal tariff", req=False),
        "hts_code": S("tariff code", req=False),
        "origin_assumed": S("country of manufacture assumed", req=False),
    }, "fetched, never remembered — set stale: true inside any range you could not source"),
    "unanswered_questions": AR(S("recurring Q&A theme = a missing image"), req=False),
    "trends": AR(S("what moved in the last 12 months"), req=False),
    "gaps": AR(S("what you could not find, and why"), req=False),
}, "runs/<slug>/scout.json")

BUYER = OB({
    "persona": OB({
        "who_i_am": S("first person, one line", minlen=20),
        "trigger": S("what just happened (jtbd.hiring_moment)", minlen=10),
        "fired_solution": S("what I used before and why it failed (jtbd.firing)", minlen=10),
        "urgency": EN("how fast I need it", "today", "this_week", "someday"),
        "search_term": S("what I will actually type"),
        "why_this_term": S("why that one and not another", minlen=10),
    }),
    "buy_driver": OB({
        "driver": EN("what is really making me buy", "pain", "pleasure", "both"),
        "pain_level": EN("latent = hidden, barely felt; moderate = searching and not searching; "
                         "extreme = no way back, cannot live without a fix",
                         "none", "latent", "moderate", "extreme"),
        "evidence": S("the complaint or praise clusters that prove this, by C… id", minlen=20),
        "tags": TAGLIST,
    }, "the engine of the purchase (law.pain_latent / law.pain_moderate / law.pain_extreme / law.pleasure)"),
    "future_self": S("first person: the picture in my head of my life once I own it — the imagery "
                     "must show this person (law.future_self)", minlen=60),
    "comfort_and_laziness": S("the effort it removes and the lazy path it unlocks — comfort makes "
                              "me lazy and lazy me buys (law.comfort_laziness)", minlen=40),
    "benefits_not_features": AR(OB({
        "feature": S("what the product has"),
        "benefit": S("what that does for MY life, in my words (law.benefit_not_feature)", minlen=15),
    }), "features tell, benefits sell — translate each one", lo=3, hi=6),
    "three_second_scan": AR(OB({
        "signal": EN("what I judge in the first seconds", "image", "price", "rating", "design",
                     "experience_promise"),
        "what_i_see": S("in scout's actual grid, not an imagined one", minlen=10),
        "verdict": EN("does it pull me in or push me away", "pull", "neutral", "push_away"),
        "tags": TAGLIST,
    }), "the seconds-long grid judgement that decides the click (law.three_second_scan)", lo=4, hi=5),
    "purchase_probability_current": OB({
        "click": P("I click the tile"),
        "add_to_cart": P("given a click, I add to cart"),
        "buy": P("given a cart, I buy"),
        "reasoning": S("one line per number", minlen=30),
    }, "for the product under evaluation as it stands today"),
    "fears": AR(OB({
        "rank": N("1 = asked first"),
        "question": S("the question in my head, verbatim"),
        "tags": TAGLIST,
        "from_cluster_id": S("C… if it comes from a complaint cluster", req=False),
        "answered_by": EN("what would settle it", "image", "bullet", "product_change", "unanswerable", req=False),
    }), lo=3, hi=6),
    "unmet_needs": AR(OB({
        "need_id": S("N1, N2, …"),
        "statement": S("the pain or job in my words", minlen=15),
        "pain_level": EN("how far this pain has come", "latent", "moderate", "extreme"),
        "severity": N("1-10: how badly the category fails me on this today", lo=1, hi=10),
        "evidence_cluster_ids": AR(S("C…"), req=False),
    }), "what innovaty must aim at — nothing else", lo=3, hi=6),
    "price_psychology": OB({
        "anchor_seen_usd": N("the median tile price I saw"),
        "max_without_reason_usd": N("most I would pay with no visible justification"),
        "max_with_reason_usd": N("most I would pay if the reason is visible in the image"),
        "reason_required": S("what that visible reason would have to be", minlen=20),
    }),
    "packaging_expectation": S("what the unboxing must feel like, and what would make me silently "
                               "assume third-rate quality (law.packaging_first_touch)", minlen=40),
    "lifestyle_target": OB({
        "primary": S("the lifestyle and identity the imagery must show (law.lifestyle_match)", minlen=15),
        "avoid": S("the framing that would push me away", req=False),
    }),
    "memory_hook": S("the one detail that keeps tempting me to think about it again later, even if "
                     "I do not buy today (law.delayed_desire)", minlen=30),
    "durability_instinct": OB({
        "what_warns_me": S("the shapes, hinges, angles, thin walls or mechanisms in this grid that my "
                           "past failures taught me to distrust — the ones that will betray me next "
                           "(law.shape_memory)", minlen=30),
        "what_reassures_me": S("what I would need to see to believe it survives five years of use", minlen=20),
    }, "lived experience judging durability from shape alone"),
    "color_read": S("the color direction that would anchor ME for this product, and why "
                    "(law.color_anchor)", req=False),
    "hypotheses_tested": AR(OB({
        "hypothesis": S("what the seller believes"),
        "verdict": EN("my ruling", "confirmed", "partly", "rejected"),
        "why": S("one line", req=False),
    }), req=False),
    "what_would_make_me_buy": S("one first-person paragraph: what makes me buy this one and tell a friend", minlen=150),
}, "runs/<slug>/buyer.json — you must NOT read innovaty.json or genius.json")

COST_TIERS = ("free", "cents", "dimes", "dollars", "tooling")
ASPECTS = ("reliability", "durability", "design", "color", "experience", "packaging",
           "convenience", "comfort", "pain_removal", "eye_catching", "addition", "other")

INNOVATY = OB({
    "target_spec": OB({
        "needs_targeted": AR(S("N… from buyer.unmet_needs — severity >= 5 only"),
                             "the needs you aim at", lo=1),
        "must_fix_clusters": AR(S("C… with share >= 15%"), "clusters you must fix"),
        "should_fix_clusters": AR(S("C… with share 5-15%"), req=False),
        "over_served_to_cut": AR(S("where the category overspends — cut cost here"), req=False),
    }),
    "ideas": AR(OB({
        "idea_id": S("I1, I2, …"),
        "name": S("short name"),
        "role": EN("exactly one hero", "hero", "supporting", "hygiene"),
        "aspect": EN("what kind of change this is", *ASPECTS),
        "mechanism": S("how it physically works, 2-3 sentences an engineer could sketch from", minlen=60),
        "fixes_complaint_clusters": AR(S("C…"), "ideas that fix nothing are cut"),
        "improves_needs": AR(S("N… from buyer.unmet_needs"), req=False),
        "improves_gates": AR(S("gate.…"), lo=1),
        "kano_class": EN("what kind of value", "must_be", "performance", "delighter"),
        "triz_or_erric_tags": TAGLIST,
        "thumbnail_visibility": EN("visible at 300 px next to 15 rivals?", "high", "medium", "low"),
        "cost_tier": EN("added unit cost", *COST_TIERS),
        "priority": EN("v1 or later", "now", "later"),
        "prior_art_risk": EN("chance someone already owns this", "low", "medium", "high"),
        "prior_art_reason": S("one line", minlen=10),
        "test_that_proves_it": S("the named test that would prove the claim", minlen=15),
        "how_it_looks_in_main_image": S("one sentence a photographer could shoot", minlen=15),
        "buyer_sentence": S("what the buyer says to a friend, in the buyer's voice", minlen=15),
        "durability_signal": EN("what the shape says to a buyer who has been betrayed before",
                                "reassures", "neutral", "warns"),
        "five_year_test": OB({
            "use_cycle": S("how it is really used over five years: how often opened, closed, removed, "
                           "pressed; dust, heat, force, weather", minlen=25),
            "failure_modes": AR(S("what breaks, jams or wears first"), lo=1),
            "design_answer": S("the dimensions, angles, wall thickness, hinge type or mechanism chosen "
                               "so it survives that cycle", minlen=25),
            "fit_range": S("the sizes, diameters or loads it accommodates — cover the medium case, "
                           "not just the thin one", req=False),
        }, "reason from the working physics, not from how cool it looks"),
    }), lo=4, hi=7),
    "durability_review": OB({
        "weakest_point": S("the part of the whole product that fails first", minlen=15),
        "physics": S("where the force, wear, dust, heat and fatigue actually go, in plain words", minlen=40),
        "five_year_verdict": EN("does the product as designed survive five years", "survives", "needs_change", "fails"),
        "changes_made": AR(S("what you changed because of this review"), lo=1),
    }, "the whole product through the five-year test"),
    "pillars": OB({
        "reliability": S("how it works every time", minlen=10),
        "durability": S("how it lasts", minlen=10),
        "uniqueness": S("what nobody else in the grid has", minlen=10),
        "exclusiveness": S("what makes it feel like the one to own", minlen=10),
        "attraction": S("what pulls the eye in the grid", minlen=10),
    }, "never underestimated — one honest line each"),
    "moat_built_in": AR(S("the competition moat this design bakes in, by name"),
                        "what a quantity-first cloner cannot copy cheaply", lo=1),
    "packaging": OB({
        "tier": EN("must match the founder's choice in brief.packaging_tier", *TIERS),
        "unboxing_moment": S("what the customer feels in the first ten seconds of opening — the "
                             "first physical impression convicts or acquits the whole brand", minlen=25),
        "upgrade_vs_category": S("what changes vs the category norm and why it reads as quality", minlen=20),
        "cost_tier": EN("added cost of the upgrade", *COST_TIERS),
    }, "law.packaging_first_touch — bad packaging means a bad review whatever the product is"),
    "color_strategy": OB({
        "product_color": S("the color of the product itself and the psychology behind it "
                           "(red urgency, blue trust, green nature, gradient fun, black+gold luxury)", minlen=15),
        "main_image_anchor": S("the background / accent of the main image that makes the tile pop "
                               "in a grid of look-alikes", minlen=15),
        "brand_direction": S("what kind of brand these colors say we are"),
    }, "law.color_anchor — distinguish or disappear"),
    "bundle_or_addition": OB({
        "what": S("the extra thing in the box or the companion piece"),
        "why_it_wins": S("the fear or need it answers", minlen=10),
        "cost_tier": EN("added cost", *COST_TIERS),
    }, "something complimentary that tips the comparison", req=False),
    "errc": OB({
        "eliminate": AR(S("what the category competes on that buyers do not value"), lo=1),
        "reduce": AR(S("do less than the norm"), lo=1),
        "raise": AR(S("do far more than the norm"), lo=1),
        "create": AR(S("what the category never offered"), lo=1),
    }),
    "version_plan": OB({
        "v1_now": AR(S("I… shipping in version 1"), lo=1),
        "v2_later": AR(OB({"idea_id": S("I…"), "unlock_trigger": S("what has to be true first")}), req=False),
    }),
    "listing_implications": OB({
        "title_first_60": S("the only words a phone shows", maxlen=80),
        "main_image_brief": S("what the hero shot must show", minlen=20),
        "image_briefs_2_to_4": AR(S("one line each: scale, hard case, install"), lo=3, hi=3),
        "honest_limitations": AR(S("state it before a reviewer does (cialdini.reciprocity)"), lo=2),
    }),
    "image_prompts": AR(OB({
        "purpose": EN("which shot", "main_image", "packaging", "lifestyle"),
        "prompt": S("a complete, paste-ready prompt for an image model (Nano Banana): the improved "
                    "product with every visible change, colors and anchor background, mood, setting, "
                    "camera angle — one paragraph", minlen=80),
    }), "exactly one each: main_image, packaging, lifestyle (the buyer's future self)", lo=3, hi=3),
    "sustainability": OB({
        "claims": AR(OB({"claim": S("specific and verifiable"), "verification": S("how it is proven")}), req=False),
        "rejected_claims": AR(S("what you refused to claim and why"), req=False),
    }, req=False),
    "what_i_cut": AR(S("what the category does that you would remove to pay for the above"), lo=2),
}, "runs/<slug>/innovaty.json")

BRAND_RULE_REVIEWS = 3500   # a page-one listing at or above this = treat the arena as brand-dominated

COMPETITION = OB({
    "arena": OB({
        "sellers_on_page_one": N("distinct sellers or brands sharing page one"),
        "lookalike_share": P("share of page-one tiles that are near-identical products"),
        "price_floor_usd": N("the cheapest credible price a quantity-first clone could sell at"),
        "dominant_form": S("the shape or design most tiles share"),
        "summary": S("the competitive environment in two sentences", minlen=40),
    }),
    "brand_dominance": OB({
        "level": EN("none = open field; partial = one strong brand but room; dominated = a brand owns the term",
                    "none", "partial", "dominated"),
        "top_brand": S("who", req=False),
        "top_review_count": N("the largest review count on page one"),
        "rule_3500": B("true when any page-one product has 3500+ reviews — that alone means brand-dominated"),
        "evidence": S("what shows this", minlen=20),
        "deep_study": S("when partial or dominated: what the brand does right, where it is weak, how we "
                        "coexist or flank it — studied hard, never surrendered", req=False, minlen=60),
    }),
    "copycat_risk": OB({
        "level": EN("how fast and cheap a clone wave would follow our launch", "low", "medium", "high"),
        "months_to_first_clone": RG("months until a look-alike appears at a lower price"),
        "clone_price_usd": RG("what the clones will sell at"),
        "why": S("what makes it easy or hard to copy", minlen=20),
    }),
    "price_war": OB({
        "win_probability_before_clones": P("our chance of being the chosen tile at launch"),
        "win_probability_after_clones": P("our chance once cheap look-alikes fill the grid"),
        "choice_rank_after_clones": N("where we land in the buyer's shortlist once clones arrive (1 = first)", lo=1),
        "share_haircut_pct": N("the share of our forecast volume the clone wave takes — the engine "
                               "re-runs the profit simulation with it", lo=0, hi=100),
        "why": S("how the buyer's comparison shifts when the grid fills with cheaper twins", minlen=20),
    }),
    "moats": AR(OB({
        "moat": S("the defensible edge"),
        "type": EN("kind", "design_registration", "review_lead", "bundle", "spec_edge",
                   "packaging_experience", "supply_exclusivity", "brand_story", "other"),
        "strength": EN("how hard it is to copy cheaply", "weak", "medium", "strong"),
        "cost_tier": EN("what it costs us", *COST_TIERS),
        "why": S("why a quantity-first cloner will not bother", minlen=15),
    }), "what a cloner who believes in quantity, not quality, cannot copy", lo=2),
    "competitor_profiles": AR(OB({
        "name": S("from scout.competitors"),
        "price_usd": N("price"),
        "review_count": N("count", req=False),
        "strength": S("what they do right"),
        "weakness": S("where they lose"),
        "threat": EN("to us", "low", "medium", "high"),
    }), lo=3),
    "watch_signals": AR(S("what to monitor after launch: new sellers, price drops, review velocity"), lo=2),
    "tags": TAGLIST,
}, "runs/<slug>/competition.json")

GENIUS = OB({
    "planning_fallacy_multiplier": N("applied to the timeline; >= 1.3", lo=1.3),
    "versions": AR(OB({
        "version_id": S("v1_now, v1_plus_hero, …"),
        "idea_ids": AR(S("I…"), lo=1),
        "bom": AR(OB({
            "part": S("what it is"),
            "qty": N("per unit"),
            "unit_cost_usd": RG("quoted or estimated cost of this part"),
        }), lo=3),
        "unit_weight_g": N("shipping weight", req=False),
        "landed_cost_usd": RG("EXW + freight + duty + inbound to FBA, per unit", pos=True),
    }), lo=1),
    "tooling_and_nre": AR(OB({
        "item": S("mould, FTO search, photography, certification, …"),
        "cost_usd": RG("one-off cost"),
    }), lo=2),
    "fixed_launch_cost_usd": RG("everything you spend before unit one sells", pos=True),
    "price_usd": RG("shelf price — must sit inside what the buyer said they would pay", pos=True),
    "economics": OB({
        "referral_rate": RG("fraction of price"),
        "fba_fee_usd": RG("per unit"),
        "storage_alloc_usd": RG("per unit"),
        "return_rate": RG("fraction of units returned"),
        "ad_rate": RG("ACoS as a fraction of price"),
    }, "the engine computes contribution, break-even and the sanity rails from these — do not compute them yourself"),
    "forecast": OB({
        "term_monthly_units": RG("all units sold monthly on the primary term", pos=True),
        "share_m6": RG("our share of that by month 6"),
        "share_m12": RG("our share by month 12"),
        "monthly_units_m6": RG("our units in month 6"),
        "monthly_units_m12": RG("our units in month 12"),
        "annual_units_y1": RG("year-1 total"),
        "seasonality_note": S("when demand swings", req=False),
        "reasoning": S("how you got from term volume to our units", minlen=100),
    }),
    "timeline": OB({
        "phases": AR(OB({
            "phase": S("tooling, testing, freight, …"),
            "weeks": RG("calendar weeks, multiplier already applied"),
        }), lo=3),
        "weeks_to_first_sale": RG("total, multiplier already applied", pos=True),
    }),
    "premortem": AR(OB({
        "obituary": S("it is 12 months on and this killed us: …", minlen=25),
        "probability": P("chance it happens"),
        "impact": EN("how bad", "fatal", "major", "minor"),
        "mitigation": S("what prevents it", minlen=10),
        "mitigation_cost_usd": RG("what the prevention costs", req=False),
    }), lo=4),
    "idea_rulings": AR(OB({
        "idea_id": S("I… — one ruling for every idea innovaty proposed"),
        "ruling": EN("can we actually do this", "realistic", "stretch", "unrealistic"),
        "why": S("one line", minlen=10),
        "deciding_number": S("the number that decided it", minlen=3),
    }), lo=4),
    "recommended_version_id": S("which version to ship first"),
    "feasibility_verdict": EN("your own call, before the engine computes its rails", "realistic", "stretch", "unrealistic"),
    "regulatory": AR(S("what applies, or 'none for a passive accessory'"), req=False),
    "three_sentences_to_founder": AR(S("plain, numbers first, no hype"), lo=3, hi=3),
}, "runs/<slug>/genius.json")

CRITIC = OB({
    "findings": AR(OB({
        "id": S("K1, K2, …"),
        "file": EN("where", "scout", "buyer", "innovaty", "genius", "brief"),
        "field_path": S("the exact field, e.g. genius.price_usd"),
        "severity": EN("high = the owner must look before samples are ordered", "high", "medium", "low"),
        "finding": S("what is wrong", minlen=20),
        "fix": S("what would fix it", minlen=10),
        "owner_agent": EN("who should have a look", "scout", "buyer", "innovaty", "genius", "orchestrator"),
    })),
    "unsourced_claim_paths": AR(S("field paths asserting a market fact with no scout fact_id")),
    "untagged_judgement_paths": AR(S("judgements with no framework tag — they score at half weight")),
    "contamination_detected": B("did buyer praise something only innovaty invented", req=False),
    "overall": EN("you flag and route — you never veto", "clean", "flags_to_fix"),
    "three_things_the_founder_must_hear": AR(S("plain and unsoftened"), lo=3, hi=3),
}, "runs/<slug>/critic.json — flags routed to their owners; the product is never declared a flop")

CONTRACTS = {"brief": BRIEF, "scout": SCOUT, "competition": COMPETITION, "buyer": BUYER,
             "innovaty": INNOVATY, "genius": GENIUS, "critic": CRITIC}

# In focus mode the grid is smaller by definition, so list minimums drop by this much.
FOCUS_RELAX = {"scout": 2, "competition": 1, "buyer": 1, "innovaty": 1, "genius": 1, "critic": 0}


# ============================================================================================ io

def load(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump(obj, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "product"


def read_run(run: Path) -> dict:
    out = {}
    for name in ["brief"] + PHASES:
        p = run / f"{name}.json"
        if p.exists():
            try:
                out[name] = load(p)
            except json.JSONDecodeError as e:
                out[name] = {"__broken__": str(e)}
    return out


# ========================================================================================== new

def suggest_tier(price_max: float) -> tuple[str, str]:
    """A default packaging tier from the price band. The founder confirms or overrides."""
    if price_max and price_max <= 15:
        return "simple", "under $15 the box cannot earn its cost back — spend on the product"
    if not price_max or price_max <= 35:
        return "moderate", "a printed box with an insert reads as a brand without a premium bill"
    return "premium", "above $35 the unboxing is part of what they paid for"


def cmd_new(run: Path, name: str, url: str | None, focus: list[str] | None, mine: int | None, budget: int,
            packaging: str | None = None, packaging_note: str | None = None):
    if (run / "brief.json").exists():
        print(f"{run/'brief.json'} already exists; not overwriting"); return
    brief = {
        "slug": run.name if re.fullmatch(r"[a-z0-9-]{2,40}", run.name) else slugify(name),
        "product_name": name,
        "source_url": url or (focus[0] if focus else ""),
        "marketplace": "amazon.com",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "focus" if focus else "category",
        "target_buyer": {"description": "TO FILL: who is buying, in one sentence",
                         "context": "", "price_band_usd": {"min": 0, "max": 0}},
        "seller_constraints": {"launch_budget_usd": 0, "time_to_market_months": 0,
                               "origin_country": "CN", "must_keep": [], "must_avoid": []},
        "user_hypotheses": [], "assumptions": [], "iterations": 0,
    }
    if not focus:
        brief["search_budget"] = 8
    if packaging in TIERS:
        brief["packaging_tier"] = packaging
    if packaging_note:
        brief["packaging_note"] = packaging_note
    if focus:
        brief["focus_products"] = [
            {"product_id": f"P{i}", "url": u, "role": "mine" if mine == i else "competitor", "name": ""}
            for i, u in enumerate(focus[:5], start=1)]
        brief["search_budget_per_product"] = budget
        brief["assumptions"].append(
            f"FOCUS MODE: only {len(brief['focus_products'])} named product(s); no category sweep")
    dump(brief, run / "brief.json")
    print(f"created {run/'brief.json'} ({brief['mode']} mode)")
    print("fill target_buyer.description before running scout, then:  python engine.py next", run)
    if packaging not in TIERS:
        tier, why = suggest_tier(0)
        print("\nPACKAGING — ask the founder to choose one tier (set brief.packaging_tier):")
        for t in TIERS:
            print(f"   {t:9} {TIER_HELP[t]}")
        print(f"   suggested: {tier} — {why}; refine once the price band is known")


# ===================================================================================== validate

def phase_errors(name: str, data: dict, focus: bool) -> list[str]:
    if not isinstance(data, dict):
        return [f"{name}: the file must contain a single JSON object"]
    if "__broken__" in data:
        return [f"{name}: file is not valid JSON — {data['__broken__']}"]
    errs: list[str] = []
    check(CONTRACTS[name], data, name, errs, relax=FOCUS_RELAX.get(name, 0) if focus else 0)
    if name == "scout":
        for i, c in enumerate(_dicts(data, "complaint_clusters")):
            for j, ex in enumerate(c.get("paraphrased_examples") or []):
                if len(str(ex).split()) > 12:
                    errs.append(f"scout.complaint_clusters[{i}].paraphrased_examples[{j}]: "
                                f"{len(str(ex).split())} words — never reproduce more than 12 from a review")
    if name == "innovaty":
        ideas = [i for i in data.get("ideas") or [] if isinstance(i, dict)]
        heroes = [i for i in ideas if i.get("role") == "hero"]
        if len(heroes) != 1:
            errs.append(f"innovaty.ideas: exactly one idea must have role 'hero', found {len(heroes)}")
        for h in heroes:
            if h.get("thumbnail_visibility") != "high":
                errs.append(f"innovaty.ideas[{h.get('idea_id')}]: the hero must be visible in the "
                            f"thumbnail (high)")
            if h.get("durability_signal") == "warns":
                errs.append(f"innovaty.ideas[{h.get('idea_id')}]: the hero's shape warns the buyer it will "
                            f"betray them — redesign it before it is the hero")
        for i in ideas:
            if not (i.get("fixes_complaint_clusters") or i.get("improves_needs")):
                errs.append(f"innovaty.ideas[{i.get('idea_id')}]: fixes no complaint cluster and improves "
                            f"no unmet need — cut it")
            if i.get("thumbnail_visibility") == "low" and i.get("priority") == "now" \
                    and not i.get("fixes_complaint_clusters"):
                errs.append(f"innovaty.ideas[{i.get('idea_id')}]: invisible and priority 'now' "
                            f"without fixing a complaint cluster — make it 'later'")
        v1 = set(_strs(data["version_plan"].get("v1_now"))) if isinstance(
            data.get("version_plan"), dict) else set()
        known = {i.get("idea_id") for i in ideas}
        for stray in sorted(v1 - known):
            errs.append(f"innovaty.version_plan.v1_now: {stray} is not one of your ideas")
        purposes = {pr.get("purpose") for pr in _dicts(data, "image_prompts")}
        for need in ("main_image", "packaging", "lifestyle"):
            if need not in purposes:
                errs.append(f"innovaty.image_prompts: no prompt with purpose '{need}' — all three are needed")
    return errs


def top_reviews(scout) -> float:
    """The largest review count scout saw on page one."""
    return max((c["review_count"] for c in _dicts(scout, "competitors") if _isnum(c.get("review_count"))),
               default=0)


def _strs(v) -> list[str]:
    """The string entries of a value that should be a list. Never raises, never iterates a string."""
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []


def _dicts(obj, key) -> list[dict]:
    """The list at obj[key], keeping only the dict entries. Never raises."""
    v = (obj or {}).get(key) if isinstance(obj, dict) else None
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _ids(obj, key, field) -> set:
    return {x[field] for x in _dicts(obj, key) if isinstance(x.get(field), str) and x[field].strip()}


def cross_errors(run: dict) -> list[str]:
    """Coherence between files. These are the contradictions a human spots and a schema cannot."""
    errs = []
    scout, buyer = run.get("scout"), run.get("buyer")
    inn, gen = run.get("innovaty"), run.get("genius")
    usable = lambda d: isinstance(d, dict) and "__broken__" not in d
    scout, buyer, inn, gen = (d if usable(d) else None for d in (scout, buyer, inn, gen))

    if scout and inn:
        known = _ids(scout, "complaint_clusters", "cluster_id")
        for i in _dicts(inn, "ideas"):
            for c in _strs(i.get("fixes_complaint_clusters")):
                if c not in known:
                    errs.append(f"innovaty.ideas[{i.get('idea_id')}]: cites cluster {c}, "
                                f"which is not in scout.complaint_clusters")
    if buyer and inn:
        needs = _dicts(buyer, "unmet_needs")
        known_n = {n.get("need_id") for n in needs if isinstance(n.get("need_id"), str)}
        weak = {n.get("need_id") for n in needs if _isnum(n.get("severity")) and n["severity"] < 5}
        spec = inn.get("target_spec") if isinstance(inn.get("target_spec"), dict) else {}
        for nid in _strs(spec.get("needs_targeted")):
            if nid in weak:
                errs.append(f"innovaty.target_spec: {nid} is already well served (severity < 5) — "
                            f"spend nothing there, cut cost instead")
            elif nid not in known_n:
                errs.append(f"innovaty.target_spec: {nid} is not in buyer.unmet_needs")
        for i in _dicts(inn, "ideas"):
            for nid in _strs(i.get("improves_needs")):
                if nid not in known_n:
                    errs.append(f"innovaty.ideas[{i.get('idea_id')}]: cites need {nid}, "
                                f"which is not in buyer.unmet_needs")
    if inn and gen:
        ids, ruled = _ids(inn, "ideas", "idea_id"), _ids(gen, "idea_rulings", "idea_id")
        for missing in sorted(ids - ruled):
            errs.append(f"genius.idea_rulings: no ruling for {missing}")
        for extra in sorted(ruled - ids):
            errs.append(f"genius.idea_rulings: {extra} is not an idea innovaty proposed")
        vids = _ids(gen, "versions", "version_id")
        rec = gen.get("recommended_version_id")
        if not (isinstance(rec, str) and rec in vids):
            errs.append(f"genius.recommended_version_id: {rec!r} is not one of the versions you costed "
                        f"({', '.join(sorted(vids)) or 'none'})")
    if buyer and gen:
        cap = (buyer.get("price_psychology") or {}).get("max_with_reason_usd") \
            if isinstance(buyer.get("price_psychology"), dict) else None
        price = (gen.get("price_usd") or {}).get("base") if isinstance(gen.get("price_usd"), dict) else None
        if _isnum(cap) and _isnum(price) and price > cap * 1.05:
            errs.append(f"genius.price_usd: base ${price:.2f} is above the ${cap:.2f} the buyer said they "
                        f"would pay even with a visible reason — reprice or change the product")
    comp, brief = run.get("competition"), run.get("brief")
    comp = comp if usable(comp) else None
    brief = brief if usable(brief) else None
    if scout and comp:
        top = top_reviews(scout)
        bd = comp.get("brand_dominance") if isinstance(comp.get("brand_dominance"), dict) else {}
        if top >= BRAND_RULE_REVIEWS and bd.get("level") in ("none", "partial"):
            errs.append(f"competition.brand_dominance.level: a page-one listing has {top:,.0f} reviews (>= "
                        f"{BRAND_RULE_REVIEWS:,}) — that is 'dominated' by rule, not '{bd.get('level')}'; "
                        f"say so and study it")
        if top >= BRAND_RULE_REVIEWS and bd.get("rule_3500") is False:
            errs.append(f"competition.brand_dominance.rule_3500: scout shows {top:,} reviews — set it true")
        if bd.get("level") in ("partial", "dominated") and len(str(bd.get("deep_study") or "")) < 60:
            errs.append("competition.brand_dominance.deep_study: the arena has a strong brand — study it "
                        "hard (what they do right, where they are weak, how we flank them)")
    if brief and inn:
        want = brief.get("packaging_tier")
        pk = inn.get("packaging") if isinstance(inn.get("packaging"), dict) else {}
        if want in TIERS and pk.get("tier") and pk["tier"] != want:
            errs.append(f"innovaty.packaging.tier: founder chose '{want}', you designed '{pk['tier']}' — "
                        f"design inside the chosen tier")
    if gen:
        f = gen.get("forecast") if isinstance(gen.get("forecast"), dict) else {}
        term, share, units = _b(f.get("term_monthly_units")), _b(f.get("share_m6")), _b(f.get("monthly_units_m6"))
        if term and share and units and not (0.5 <= units / (term * share) <= 2.0):
            errs.append(f"genius.forecast: month-6 units ({units:,.0f}) do not follow from "
                        f"{share:.1%} of {term:,.0f} term units ({term*share:,.0f}) — reconcile them")
        for v in _dicts(gen, "versions"):
            bom = sum(_b(p.get("unit_cost_usd")) * (p.get("qty") if _isnum(p.get("qty")) else 1)
                      for p in _dicts(v, "bom"))
            landed = _b(v.get("landed_cost_usd"))
            if bom and landed and bom > landed:
                errs.append(f"genius.versions[{v.get('version_id')}]: the BOM adds to ${bom:.2f} but the "
                            f"landed cost is ${landed:.2f} — landed must also carry freight, duty and inbound")
    return errs


def cmd_check(run: Path) -> int:
    data = read_run(run)
    focus = isinstance(data.get("brief"), dict) and data["brief"].get("mode") == "focus"
    bad = 0
    if "brief" not in data:
        print(f"[brief] missing — run `python engine.py new {run} --name \"…\"` first")
        bad += 1
    for name in ["brief"] + PHASES:
        if name not in data:
            if name != "brief":
                print(f"[{name}] not written yet")
            continue
        if "__broken__" in data[name]:
            print(f"[{name}] INVALID JSON: {data[name]['__broken__']}"); bad += 1; continue
        if name == "brief":
            if not isinstance(data[name], dict):
                print("[brief] the file must contain a single JSON object"); bad += 1; continue
            errs = []
            check(BRIEF, data[name], "brief", errs)
            tb = data[name].get("target_buyer")
            if str((tb or {}).get("description", "") if isinstance(tb, dict) else "").startswith("TO FILL"):
                errs.append("brief.target_buyer.description: still the placeholder — say who is buying, "
                            "in one sentence, before scout runs")
        else:
            errs = phase_errors(name, data[name], focus)
        _report(name, errs); bad += bool(errs)
    x = cross_errors(data)
    _report("coherence", x); bad += bool(x)
    return 1 if bad else 0


def _report(name, errs):
    if errs:
        print(f"[{name}] {len(errs)} problem(s):")
        for e in errs:
            print(f"   - {e}")
    else:
        print(f"[{name}] ok")


# ======================================================================================== score

def _tag_coverage(obj) -> tuple[int, int]:
    tagged = total = 0
    stack = [obj]
    while stack:
        v = stack.pop()
        if isinstance(v, dict):
            if "tags" in v or "triz_or_erric_tags" in v:
                total += 1
                if any(str(t).startswith(TAGS) for t in (v.get("tags") or v.get("triz_or_erric_tags") or [])):
                    tagged += 1
            stack.extend(v.values())
        elif isinstance(v, list):
            stack.extend(v)
    return tagged, total


def score_evidence(scout, critic) -> dict:
    facts = _dicts(scout, "facts")
    sourced = sum(1 for f in facts if str(f.get("source", "")).startswith("http"))
    fees = scout.get("fee_inputs") if isinstance(scout.get("fee_inputs"), dict) else {}
    stale = sum(1 for v in fees.values() if isinstance(v, dict) and v.get("stale"))
    unsourced = len(critic.get("unsourced_claim_paths") or [])
    s = 100.0 * (sourced / len(facts) if facts else 0) - 6 * stale - 4 * unsourced
    return {"facts": len(facts), "sourced": sourced, "stale_fee_inputs": stale,
            "unsourced_claims": unsourced, "score": round(max(0, min(100, s)), 1)}


_PAIN_W = {"latent": 0.55, "moderate": 0.8, "extreme": 1.0}


def score_buyer(buyer) -> dict:
    """Headroom = how much room a better product has: the share of shoppers the incumbents lose
    across all three funnel steps, weighted by the worst unmet need — an extreme pain the category
    fails at is the biggest opening there is."""
    p = buyer.get("purchase_probability_current") or {}
    g = lambda k, d: p[k] if _isnum(p.get(k)) else d
    click, cart, buy = g("click", 0.5), g("add_to_cart", 0.5), g("buy", 0.5)
    tagged, total = _tag_coverage(buyer)
    cov = tagged / total if total else 0
    needs = [n for n in _dicts(buyer, "unmet_needs") if _isnum(n.get("severity"))]
    top = max((n["severity"] * _PAIN_W.get(n.get("pain_level"), 0.7) for n in needs), default=0)
    top_need = max(needs, key=lambda n: n["severity"] * _PAIN_W.get(n.get("pain_level"), 0.7), default={})
    driver = buyer.get("buy_driver") if isinstance(buyer.get("buy_driver"), dict) else {}
    headroom = (1 - click * cart * buy) * min(1.0, top / 10.0)
    return {"p_click": click, "p_cart": cart, "p_buy": buy,
            "p_purchase_overall": round(click * cart * buy, 4),
            "framework_tag_coverage": round(cov, 2),
            "driver": driver.get("driver"), "pain_level": driver.get("pain_level"),
            "top_need": top_need.get("statement"), "top_need_id": top_need.get("need_id"),
            "burning_needs": sum(1 for n in needs
                                 if n["severity"] >= 7 or n.get("pain_level") == "extreme"),
            "headroom_score": round(100 * headroom * (0.5 + 0.5 * cov), 1)}


_GATE_W = {"gate.image_orientation": 1.0, "gate.image_fit": 1.0, "gate.price_vs_anchor": 0.8,
           "gate.reviews_negative_first": 0.9, "gate.reviews_with_photos": 0.9, "gate.image_2_to_6": 0.7,
           "gate.social_proof": 0.6, "gate.title_scan": 0.6, "gate.brand_trust": 0.5,
           "gate.bullets": 0.4, "gate.variations": 0.4, "gate.qna": 0.3}
_VIS_W = {"high": 1.0, "medium": 0.55, "low": 0.25}
_COST_W = {"free": 1.0, "cents": 1.2, "dimes": 1.8, "dollars": 3.0, "tooling": 3.5}
# An idea nobody ruled on is worth less than one an engineer called a stretch.
_RULING_W = {"realistic": 1.0, "stretch": 0.6, "unrealistic": 0.0, "unrated": 0.5}


def score_innovation(inn, scout, genius) -> dict:
    share = {c["cluster_id"]: (c["share_of_negative"] if _isnum(c.get("share_of_negative")) else 0)
             for c in _dicts(scout, "complaint_clusters") if isinstance(c.get("cluster_id"), str)}
    rulings = {r["idea_id"]: r.get("ruling", "unrated") for r in _dicts(genius, "idea_rulings")
               if isinstance(r.get("idea_id"), str)}
    v1 = set(_strs(inn["version_plan"].get("v1_now"))) \
        if isinstance(inn.get("version_plan"), dict) else set()
    rows = []
    for i in _dicts(inn, "ideas"):
        gate = max([_GATE_W.get(g, 0.3) for g in (i.get("improves_gates") or [])] or [0.3])
        fixed = min(1.0, sum(share.get(c, 0) for c in set(_strs(i.get("fixes_complaint_clusters")))))
        impact = 100 * gate * _VIS_W.get(i.get("thumbnail_visibility"), 0.25) * (0.3 + fixed) \
            / _COST_W.get(i.get("cost_tier"), 2.0)
        ruling = rulings.get(i.get("idea_id"), "unrated")
        rows.append({"idea_id": i.get("idea_id"), "name": i.get("name"), "role": i.get("role"),
                     "durability": i.get("durability_signal"),
                     "in_v1": i.get("idea_id") in v1, "impact": round(impact, 1), "ruling": ruling,
                     "weighted": round(impact * _RULING_W.get(ruling, 0.5), 1)})
    rows.sort(key=lambda r: -r["weighted"])
    top = rows[:4]
    dr = inn.get("durability_review") if isinstance(inn.get("durability_review"), dict) else {}
    return {"ideas_ranked": rows, "hero": next((r for r in rows if r["role"] == "hero"), None),
            "five_year_verdict": dr.get("five_year_verdict"), "weakest_point": dr.get("weakest_point"),
            "warning_shapes": [r["idea_id"] for r in rows if r.get("durability") == "warns"],
            "v1_realistic_count": sum(1 for r in rows if r["in_v1"] and r["ruling"] == "realistic"),
            "v1_unrealistic": [r["idea_id"] for r in rows if r["in_v1"] and r["ruling"] == "unrealistic"],
            "score": round(min(100, sum(r["weighted"] for r in top) / len(top)), 1) if top else 0}


_MOAT_W = {"weak": 1, "medium": 2, "strong": 3}
_HAIRCUT_DEFAULT = {"low": 15, "medium": 30, "high": 50}


def score_competition(comp, scout) -> dict:
    """The arena as the engine sees it: the 3500-review rule is applied here regardless of what the
    agent said, and the clone-wave haircut is what the second profit simulation runs on."""
    top = top_reviews(scout)
    bd = comp.get("brand_dominance") if isinstance(comp.get("brand_dominance"), dict) else {}
    cr = comp.get("copycat_risk") if isinstance(comp.get("copycat_risk"), dict) else {}
    pw = comp.get("price_war") if isinstance(comp.get("price_war"), dict) else {}
    ar = comp.get("arena") if isinstance(comp.get("arena"), dict) else {}
    level = bd.get("level") if bd.get("level") in ("none", "partial", "dominated") else None
    raised = top >= BRAND_RULE_REVIEWS and level != "dominated"
    if raised:
        level = "dominated"
    moats = [m for m in _dicts(comp, "moats") if m.get("strength") in _MOAT_W]
    best = max(moats, key=lambda m: _MOAT_W[m["strength"]], default={})
    risk = cr.get("level") if cr.get("level") in _HAIRCUT_DEFAULT else None
    haircut = pw["share_haircut_pct"] if _isnum(pw.get("share_haircut_pct")) else _HAIRCUT_DEFAULT.get(risk, 30)
    return {"present": bool(comp), "brand_dominance": level or "unknown", "top_review_count": top,
            "rule_3500_triggered": top >= BRAND_RULE_REVIEWS, "raised_by_rule": raised,
            "top_brand": bd.get("top_brand"),
            "sellers_on_page_one": ar.get("sellers_on_page_one"),
            "lookalike_share": ar.get("lookalike_share"),
            "copycat_risk": risk or "unknown", "months_to_clone": _b(cr.get("months_to_first_clone")),
            "clone_price_usd": _b(cr.get("clone_price_usd")), "share_haircut_pct": haircut,
            "win_before": pw.get("win_probability_before_clones"),
            "win_after": pw.get("win_probability_after_clones"),
            "choice_rank_after": pw.get("choice_rank_after_clones"),
            "strongest_moat": best.get("moat"), "moat_strength": best.get("strength", "none"),
            "deep_study": bd.get("deep_study")}


# ------------------------------------------------------------------ economics the engine computes

def _b(r, d=0.0):
    """The base of a range, tolerating a missing key, a null, or a bare number."""
    if isinstance(r, dict):
        v = r.get("base")
        return float(v) if _isnum(v) else d
    return float(r) if _isnum(r) else d


def pick_version(genius) -> tuple[dict, bool]:
    """The version genius recommended, and whether we had to substitute a different one."""
    versions = [v for v in (genius.get("versions") or []) if isinstance(v, dict)]
    rec = genius.get("recommended_version_id")
    for v in versions:
        if v.get("version_id") == rec:
            return v, False
    return (versions[0] if versions else {}), bool(versions)


def economics(genius) -> dict:
    """Contribution, break-even and the sanity rails — computed here so no model has to."""
    ver, substituted = pick_version(genius)
    e = genius.get("economics") if isinstance(genius.get("economics"), dict) else {}
    price, landed = _b(genius.get("price_usd")), _b(ver.get("landed_cost_usd"))
    referral = price * _b(e.get("referral_rate"))
    fba, storage = _b(e.get("fba_fee_usd")), _b(e.get("storage_alloc_usd"))
    ads = price * _b(e.get("ad_rate"))
    returns = _b(e.get("return_rate")) * (0.4 * price + 0.6 * landed)
    contribution = price - referral - fba - storage - ads - returns - landed
    fixed = _b(genius.get("fixed_launch_cost_usd"))
    be_units = fixed / contribution if contribution > 0 else None
    fc = genius.get("forecast") if isinstance(genius.get("forecast"), dict) else {}
    m6, m12 = _b(fc.get("monthly_units_m6")), _b(fc.get("monthly_units_m12"))
    units, cum, months = ramp(m6, m12), -fixed, None
    for mth, u in enumerate(units, start=1):
        cum += u * contribution
        if months is None and cum >= 0:
            months = mth
    return {"version_id": ver.get("version_id"), "version_substituted": substituted,
            "price_usd": round(price, 2), "landed_cost_usd": round(landed, 2),
            "fee_stack_usd": {"referral": round(referral, 2), "fba": round(fba, 2), "storage": round(storage, 2),
                              "ads": round(ads, 2), "returns": round(returns, 2)},
            "contribution_usd": round(contribution, 2),
            "contribution_pct": round(100 * contribution / price, 1) if price else 0,
            "landed_pct_of_price": round(100 * landed / price, 1) if price else 0,
            "break_even_units": None if be_units is None else round(be_units),
            "months_to_break_even": months}


def ramp(m6: float, m12: float) -> list[float]:
    """Monthly units: a straight line from zero to month 6, then on to month 12."""
    return [m6 * (i / 6) for i in range(1, 7)] + [m6 + (m12 - m6) * (i / 6) for i in range(1, 7)]


def unmitigated_fatal(genius) -> list[dict]:
    """A fatal obituary at 25% or more with nothing in place to prevent it."""
    return [p for p in _dicts(genius, "premortem")
            if p.get("impact") == "fatal" and _isnum(p.get("probability")) and p["probability"] >= 0.25
            and len(str(p.get("mitigation") or "").strip()) < 10]


def _hi(r):
    """The high end of a range, or None. A rail with no number behind it does not pass."""
    if isinstance(r, dict) and _isnum(r.get("high")):
        return float(r["high"])
    return float(r) if _isnum(r) else None


def sanity_rails(econ, genius, mc, buyer, mc_cloned=None) -> list[dict]:
    tl = genius.get("timeline") if isinstance(genius.get("timeline"), dict) else {}
    hi_weeks = _hi(tl.get("weeks_to_first_sale"))
    fatal = unmitigated_fatal(genius)
    pp = (buyer or {}).get("price_psychology")
    cap = pp.get("max_with_reason_usd") if isinstance(pp, dict) else None
    mult = genius.get("planning_fallacy_multiplier")
    price, contrib, landed = econ["price_usd"], econ["contribution_pct"], econ["landed_pct_of_price"]
    rails = [
        ("contribution >= 25% of price", price > 0 and contrib >= 25, f"{contrib}%"),
        ("contribution >= 15% of price (hard floor)", price > 0 and contrib >= 15, f"{contrib}%"),
        ("landed cost <= 30% of price", price > 0 and 0 < landed <= 30, f"{landed}%"),
        ("P(profit > 0 in 12 months) >= 60%", mc["p_profit_positive_12m"] >= 0.60,
         f"{mc['p_profit_positive_12m']:.0%}"),
        ("first sale within 9 months at high", hi_weeks is not None and hi_weeks <= 39,
         f"{hi_weeks:.0f} wk high" if hi_weeks is not None else "not stated"),
        ("no fatal risk above 25% without a mitigation", not fatal, f"{len(fatal)} unmitigated"),
        ("price within what the buyer will pay", _isnum(cap) and price <= cap * 1.05,
         f"${price:.2f} vs ${cap:.2f}" if _isnum(cap) else "buyer stated no ceiling"),
        ("planning-fallacy multiplier applied", _isnum(mult) and mult >= 1.3,
         str(mult) if _isnum(mult) else "not stated"),
    ]
    out = [{"rail": r, "pass": bool(ok), "value": v, "soft": False} for r, ok, v in rails]
    if mc_cloned:
        out.append({"rail": "profit survives a copycat wave (P >= 40%)",
                    "pass": mc_cloned["p_profit_positive_12m"] >= 0.40,
                    "value": f"{mc_cloned['p_profit_positive_12m']:.0%} after the clone haircut",
                    "soft": True, "owner": "innovaty"})
    return out


def _tri(r, rng):
    """Sample a triangular distribution from a range, tolerating a bare number or a missing end."""
    if not isinstance(r, dict):
        return float(r) if _isnum(r) else 0.0
    b = _b(r)
    lo = float(r["low"]) if _isnum(r.get("low")) else b
    hi = float(r["high"]) if _isnum(r.get("high")) else b
    if hi <= lo:
        return b
    return rng.triangular(lo, hi, min(max(b, lo), hi))


def monte_carlo(genius, trials=MC_TRIALS, seed=MC_SEED, units_scale=1.0) -> dict:
    """units_scale < 1 simulates the clone wave: cheaper twins take that share of our volume."""
    ver, _sub = pick_version(genius)
    e = genius.get("economics") if isinstance(genius.get("economics"), dict) else {}
    f = genius.get("forecast") if isinstance(genius.get("forecast"), dict) else {}
    rng = random.Random(seed)
    profits, paybacks = [], []
    for _ in range(trials):
        price, landed = _tri(genius.get("price_usd"), rng), _tri(ver.get("landed_cost_usd"), rng)
        contrib = (price
                   - price * _tri(e.get("referral_rate"), rng)
                   - _tri(e.get("fba_fee_usd"), rng)
                   - _tri(e.get("storage_alloc_usd"), rng)
                   - price * _tri(e.get("ad_rate"), rng)
                   - _tri(e.get("return_rate"), rng) * (0.4 * price + 0.6 * landed)
                   - landed)
        m6, m12 = _tri(f.get("monthly_units_m6"), rng), _tri(f.get("monthly_units_m12"), rng)
        units = ramp(m6 * units_scale, m12 * units_scale)
        cum, payback = -_tri(genius.get("fixed_launch_cost_usd"), rng), None
        for month, u in enumerate(units, start=1):
            cum += u * contrib
            if payback is None and cum >= 0:
                payback = month
        profits.append(cum)
        paybacks.append(payback or 99)
    profits.sort()
    q = lambda p: profits[int(p * (trials - 1))]
    return {"trials": trials,
            "p_profit_positive_12m": round(sum(1 for x in profits if x > 0) / trials, 3),
            "p_payback_within_12m": round(sum(1 for x in paybacks if x <= 12) / trials, 3),
            "profit_12m_p10": round(q(0.10)), "profit_12m_p50": round(q(0.50)), "profit_12m_p90": round(q(0.90)),
            "median_payback_month": int(statistics.median(paybacks))}


def feasibility(rails, mc, genius) -> dict:
    """Soft rails (the clone wave) are reported and watched, but never decide the verdict."""
    hard = [r for r in rails if not r.get("soft")]
    passed = sum(1 for r in hard if r["pass"])
    broken = [r["rail"] for r in hard if not r["pass"]]
    fatal = unmitigated_fatal(genius)
    computed = ("unrealistic" if (len(broken) > 1 or fatal)
                else "stretch" if broken else "realistic")
    s = 0.6 * (100 * passed / len(hard)) + 40 * mc["p_profit_positive_12m"]
    s -= 15 * len(fatal)
    soft_broken = [r["rail"] for r in rails if r.get("soft") and not r["pass"]]
    return {"rails_passed": f"{passed}/{len(hard)}", "rails_broken": broken, "soft_broken": soft_broken,
            "verdict_computed": computed, "verdict_claimed": genius.get("feasibility_verdict"),
            "disagreement": computed != genius.get("feasibility_verdict"),
            "score": round(max(0, min(100, s)), 1)}


# The rails that must hold before samples are ordered; the rest go on the watch list.
_HARD_RAILS = {"contribution >= 15% of price (hard floor)",
               "price within what the buyer will pay",
               "P(profit > 0 in 12 months) >= 60%",
               "no fatal risk above 25% without a mitigation"}


def readiness(ev, bu, inn, fe, critic, comp=None) -> tuple[str, str, list[str], list[str]]:
    """READY or FIX-FIRST — never a flop. Every flag names the agent that owns the fix."""
    fixes, watch = [], []
    comp = comp or {}
    if comp.get("brand_dominance") in ("partial", "dominated"):
        watch.append(f"[orchestrator] brand-{comp['brand_dominance']} arena — the top listing has "
                     f"{comp.get('top_review_count', 0):,.0f} reviews. Not a reason to give up: flagged for "
                     f"serious consideration; read the deep study in the report")
    if comp.get("copycat_risk") == "high" and comp.get("moat_strength") != "strong":
        fixes.append("[innovaty] copycat risk is high and no strong moat is built in — a quantity-first "
                     "cloner will undercut us within months; add a defensible edge (design registration, "
                     "bundle, spec edge, review lead plan) before launch")
    elif comp.get("copycat_risk") == "medium" and comp.get("moat_strength") in ("none", "weak"):
        watch.append("[innovaty] medium copycat risk with only a weak moat — plan the review lead and a "
                     "visible difference clones will not bother with")
    if inn.get("five_year_verdict") == "fails":
        fixes.append(f"[innovaty] the design fails its own five-year test (weakest point: "
                     f"{inn.get('weakest_point') or '?'}) — redesign the mechanism, not the styling")
    elif inn.get("five_year_verdict") == "needs_change":
        watch.append(f"[innovaty] five-year test says 'needs change' at: {inn.get('weakest_point') or '?'}")
    if inn.get("warning_shapes"):
        watch.append(f"[innovaty] shapes that warn a betrayed buyer: {', '.join(inn['warning_shapes'])} — "
                     f"the buyer will assume they break")
    if not comp.get("present"):
        watch.append("[orchestrator] the competition phase has not run — the clone-wave numbers are defaults")
    for f in _dicts(critic, "findings"):
        line = f"[{f.get('owner_agent') or f.get('file') or '?'}] {f.get('finding')} — fix: {f.get('fix')}"
        (fixes if f.get("severity") == "high" else watch).append(line)
    if ev["score"] < 50:
        fixes.append("[scout] evidence is thin — source the facts and fetch the live fees before "
                     "trusting any number below")
    for r in fe["rails_broken"]:
        (fixes if r in _HARD_RAILS else watch).append(f"[genius] broken rail: {r}")
    if fe["verdict_computed"] == "unrealistic" and not any(r in _HARD_RAILS for r in fe["rails_broken"]):
        fixes.append("[genius] two or more sanity rails are broken (" + "; ".join(fe["rails_broken"][:3])
                     + ") — the plan is unrealistic as costed; reprice, re-cost or re-time it")
    for r in fe.get("soft_broken") or []:
        watch.append(f"[innovaty] {r} — the moat must be stronger or the price war will eat the margin")
    if inn["v1_unrealistic"]:
        fixes.append(f"[innovaty] v1 contains ideas genius ruled unrealistic "
                     f"({', '.join(inn['v1_unrealistic'])}) — move them to v2")
    if bu["headroom_score"] < 25:
        watch.append(f"[innovaty] the buyer sees little room on this term (headroom "
                     f"{bu['headroom_score']}) — the changes must be sharper and more visible, "
                     f"or the search term wants rethinking")
    if not critic:
        watch.append("[orchestrator] the critic has not run yet — run it before ordering samples")
    status = "READY" if not fixes else "FIX-FIRST"
    summary = ("no open flags — order samples of v1 and shoot the images" if not fixes else
               f"{len(fixes)} flag(s) to close, each routed to its owner — nothing here kills the product")
    return status, summary, fixes, watch


def cmd_score(run: Path, quiet=False, force=False) -> dict:
    d = read_run(run)
    if not isinstance(d.get("brief"), dict) or "__broken__" in d["brief"]:
        sys.exit(f"cannot score: {run}/brief.json is missing or is not valid JSON")
    for need in REQUIRED:
        if need not in d:
            sys.exit(f"cannot score: {need}.json is missing")
    focus = d["brief"].get("mode") == "focus"
    scored = [n for n in REQUIRED + ("competition",) if n in d]
    blocking = [e for n in scored for e in phase_errors(n, d[n], focus)]
    if blocking and not force:
        print(f"cannot score — {len(blocking)} contract problem(s). Fix these, or pass --force to "
              f"score anyway (numbers will be wrong):", file=sys.stderr)
        for e in blocking[:25]:
            print(f"   - {e}", file=sys.stderr)
        sys.exit(1)
    # With --force the files may be malformed; treat anything that is not an object as absent.
    scout, buyer, inn, gen = (d[n] if isinstance(d[n], dict) else {} for n in REQUIRED)
    comp = d.get("competition") if isinstance(d.get("competition"), dict) else {}
    if "__broken__" in comp:
        comp = {}
    critic = d.get("critic") or {}
    if not isinstance(critic, dict):
        critic = {}
    if "__broken__" in critic:
        print("warning: critic.json is not valid JSON — scoring without the red team", file=sys.stderr)
        critic = {}
    econ = economics(gen)
    mc = monte_carlo(gen)
    sc = score_competition(comp, scout)
    mc_cloned = monte_carlo(gen, units_scale=1 - sc["share_haircut_pct"] / 100.0) if sc["present"] else None
    rails = sanity_rails(econ, gen, mc, buyer, mc_cloned)
    ev, bu = score_evidence(scout, critic), score_buyer(buyer)
    ino, fe = score_innovation(inn, scout, gen), feasibility(rails, mc, gen)
    status, summary, fixes, watch = readiness(ev, bu, ino, fe, critic, sc)
    out = {"scored_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "evidence": ev, "buyer": bu, "innovation": ino, "competition": sc, "economics": econ,
           "sanity_rails": rails, "monte_carlo": mc, "monte_carlo_cloned": mc_cloned, "feasibility": fe,
           "critic_overall": critic.get("overall", "not run"),
           "critic_high": sum(1 for f in _dicts(critic, "findings") if f.get("severity") == "high"),
           "status": status, "summary": summary, "fixes": fixes, "watch": watch}
    dump(out, run / "scores.json")
    if not quiet:
        print(json.dumps({"status": status, "summary": summary, "fixes": fixes,
                          "evidence": ev["score"], "headroom": bu["headroom_score"],
                          "innovation": ino["score"], "feasibility": fe["score"],
                          "contribution_pct": econ["contribution_pct"],
                          "p_profit_12m": mc["p_profit_positive_12m"],
                          "p_profit_12m_under_clones": mc_cloned["p_profit_positive_12m"] if mc_cloned else None,
                          "feasibility_computed": fe["verdict_computed"]}, indent=2))
    return out


# ======================================================================================= report

def _r(rng, unit="$", d=2):
    if not (isinstance(rng, dict) and all(_isnum(rng.get(k)) for k in ("low", "base", "high"))):
        return "—"
    fmt = (lambda x: f"{unit}{x:,.{d}f}") if unit == "$" else (lambda x: f"{x:,.{d}f}{unit}")
    return f"{fmt(rng['base'])} ({fmt(rng['low'])}–{fmt(rng['high'])})" + (" ⚠stale" if rng.get("stale") else "")


def _one_line(text, cap=170):
    t = " ".join(str(text or "").split())
    return t if len(t) <= cap else t[:cap - 1].rstrip() + "…"


def cmd_report(run: Path, force=False):
    d = read_run(run)
    s = cmd_score(run, quiet=True, force=force)
    ok = lambda x: x if isinstance(x, dict) and "__broken__" not in x else {}
    brief, scout, buyer, inn, gen = (ok(d.get(n)) for n in ("brief",) + REQUIRED)
    econ, mc, bu, sc, mcc = s["economics"], s["monte_carlo"], s["buyer"], s["competition"], s["monte_carlo_cloned"]
    clusters = sorted([c for c in _dicts(scout, "complaint_clusters") if _isnum(c.get("share_of_negative"))],
                      key=lambda c: -c["share_of_negative"])[:3]
    be = econ["break_even_units"]
    pl = scout.get("price_ladder") if isinstance(scout.get("price_ladder"), dict) else {}
    pp = buyer.get("price_psychology") if isinstance(buyer.get("price_psychology"), dict) else {}
    vp = inn.get("version_plan") if isinstance(inn.get("version_plan"), dict) else {}
    li = inn.get("listing_implications") if isinstance(inn.get("listing_implications"), dict) else {}
    pack = inn.get("packaging") if isinstance(inn.get("packaging"), dict) else {}
    col = inn.get("color_strategy") if isinstance(inn.get("color_strategy"), dict) else {}
    bun = inn.get("bundle_or_addition") if isinstance(inn.get("bundle_or_addition"), dict) else {}
    variant = scout.get("variant_chosen") if isinstance(scout.get("variant_chosen"), dict) else {}
    rulings = {r.get("idea_id"): r.get("ruling") for r in _dicts(gen, "idea_rulings")}
    v1 = set(_strs(vp.get("v1_now")))
    broken = [r for r in s["sanity_rails"] if not r["pass"] and not r.get("soft")]
    weeks = _r((gen.get("timeline") or {}).get("weeks_to_first_sale") if isinstance(gen.get("timeline"), dict) else None, " wk", 0)

    L = [f"# {brief.get('product_name', '(unnamed product)')} — **{s['status']}**",
         f"*{s['summary']}*  ·  critic: {s['critic_overall']}  ·  {date.today().isoformat()}"
         f"  ·  `{brief.get('slug', '?')}`",
         "",
         "## The picture in 6 lines",
         f"- **Market:** term **{pl.get('primary_term', '—')}**, page-1 anchor "
         + (f"**${pl['median']:.2f}**" if _isnum(pl.get("median")) else "**not found**")
         + (f" · winning variant: {_one_line(variant.get('description'), 60)}" if variant.get("description") else ""),
         "- **Worst complaints:** " + ("; ".join(f"{_one_line(c.get('pattern'), 60)} ({c['share_of_negative']:.0%})"
                                                 for c in clusters) or "—"),
         f"- **Why they buy:** {bu.get('driver') or '—'}"
         + (f" (**{bu.get('pain_level')}** pain)" if bu.get("pain_level") not in (None, "none") else "")
         + (f" · top unmet need: {_one_line(bu.get('top_need'), 90)}" if bu.get("top_need") else ""),
         f"- **Future self:** {_one_line(buyer.get('future_self'))}",
         f"- **Buyer today:** click {bu['p_click']:.0%} → cart {bu['p_cart']:.0%} → buy {bu['p_buy']:.0%}"
         + (f" · pays up to **${pp['max_with_reason_usd']:.2f}** with a visible reason"
            if _isnum(pp.get("max_with_reason_usd")) else ""),
         f"- **Memory hook:** {_one_line(buyer.get('memory_hook'))}",
         "",
         "## The competition",
         ("- **Competition phase has not run** — the numbers below are the engine's rule alone" if not sc["present"] else
          f"- **Arena:** {sc.get('sellers_on_page_one') or '?'} sellers on page one")
         + (f", {sc['lookalike_share']:.0%} look-alikes" if _isnum(sc.get("lookalike_share")) else "")
         + f" · brand dominance **{sc['brand_dominance']}**"
         + (f" ({sc.get('top_brand')}, " if sc.get("top_brand") else " (")
         + f"top listing {sc['top_review_count']:,.0f} reviews"
         + (" — 3500 rule" + (", raised by the engine" if sc.get("raised_by_rule") else "") + ")"
            if sc["rule_3500_triggered"] else ")"),
         f"- **If cloned:** copycat risk **{sc['copycat_risk']}**"
         + (f", first clone in ~{sc['months_to_clone']:.0f} months at ~${sc['clone_price_usd']:.2f}"
            if sc["months_to_clone"] and sc["clone_price_usd"] else "")
         + (f" · our win chance {sc['win_before']:.0%} → {sc['win_after']:.0%}"
            if _isnum(sc.get("win_before")) and _isnum(sc.get("win_after")) else "")
         + (f", shortlist rank {sc['choice_rank_after']:.0f}" if _isnum(sc.get("choice_rank_after")) else "")
         + f" · volume haircut {sc['share_haircut_pct']:.0f}%",
         f"- **Moat:** {_one_line(sc.get('strongest_moat'), 90) or 'none named'} ({sc['moat_strength']})",
         "",
         "## The winning changes"]
    for idea in _dicts(inn, "ideas"):
        iid = idea.get("idea_id")
        mark = "★ " if idea.get("role") == "hero" else ""
        tag = " · v1" if iid in v1 else " · v2"
        L.append(f"- {mark}**{idea.get('name', iid)}** [{idea.get('aspect', '?')}] — "
                 f"{_one_line(idea.get('buyer_sentence'), 100)} · {idea.get('cost_tier', '?')}"
                 f" · thumbnail {idea.get('thumbnail_visibility', '?')}"
                 f" · durability {idea.get('durability_signal', '?')}"
                 f" · {rulings.get(iid, 'unrated')}{tag}")
    dr = inn.get("durability_review") if isinstance(inn.get("durability_review"), dict) else {}
    if dr:
        L.append(f"- **Five-year test:** **{dr.get('five_year_verdict', '?')}** — weakest point: "
                 f"{_one_line(dr.get('weakest_point'), 80)}; changed: "
                 f"{_one_line('; '.join(_strs(dr.get('changes_made'))), 110)}")
    if pack:
        L.append(f"- **Packaging ({pack.get('tier', '?')})** — {_one_line(pack.get('unboxing_moment'), 110)}"
                 f" · {pack.get('cost_tier', '?')}")
    if col:
        L.append(f"- **Colors** — product: {_one_line(col.get('product_color'), 80)} · "
                 f"main-image anchor: {_one_line(col.get('main_image_anchor'), 80)}")
    if bun:
        L.append(f"- **Extra in the box** — {_one_line(bun.get('what'), 60)}: "
                 f"{_one_line(bun.get('why_it_wins'), 80)} · {bun.get('cost_tier', '?')}")
    if li.get("title_first_60"):
        L.append(f"- **Title (first 60):** `{li['title_first_60']}`")
    L += ["",
          "## The money  *(computed, not estimated)*",
          f"- Price **${econ['price_usd']:.2f}** · landed ${econ['landed_cost_usd']:.2f} "
          f"({econ['landed_pct_of_price']}%) · contribution **${econ['contribution_usd']:.2f}/unit "
          f"({econ['contribution_pct']}%)**",
          (f"- Break-even **{be:,} units** (~{econ['months_to_break_even'] or '>12'} months) · "
           if be is not None else "- Break-even **never at these numbers** · ")
          + f"P(profit 12 m) **{mc['p_profit_positive_12m']:.0%}**"
          + (f", under a clone wave **{mcc['p_profit_positive_12m']:.0%}**" if mcc else "")
          + f" · year-1 P50 ${mc['profit_12m_p50']:,} (P10 ${mc['profit_12m_p10']:,})",
          f"- First sale in {weeks} · rails {s['feasibility']['rails_passed']}"
          + (" — broken: " + "; ".join(b["rail"] for b in broken) if broken else " — all pass")
          + f" · feasibility **{s['feasibility']['verdict_computed']}**"
          + (f" (genius said *{s['feasibility']['verdict_claimed']}*)" if s["feasibility"]["disagreement"] else "")]
    if econ.get("version_substituted"):
        L.append(f"- ⚠ numbers are for **{econ['version_id']}** — genius recommended "
                 f"`{gen.get('recommended_version_id') or 'nothing'}`, which it never costed")
    if sc.get("brand_dominance") in ("partial", "dominated") and sc.get("deep_study"):
        L += ["", "## A brand owns this shelf — the deep study",
              _one_line(sc["deep_study"], 600)]
    if s["fixes"]:
        L += ["", "## Flags to close first  *(routed to their owners — nothing here is a flop)*"]
        L += [f"- {f}" for f in s["fixes"]]
    if s["watch"]:
        L += ["", "## Watch list"] + [f"- {w}" for w in s["watch"][:4]]
    L += ["", "## Next step",
          ("Close the flags above, then order samples of v1 (" + ", ".join(sorted(v1)) + ")."
           if s["fixes"] else
           "Order samples of v1 (" + (", ".join(sorted(v1)) or "—") + ") from two suppliers and "
           "shoot the three images below.")]
    prompts = {pr.get("purpose"): pr.get("prompt") for pr in _dicts(inn, "image_prompts")}
    if prompts:
        L += ["", "## Nano Banana prompts"]
        for purpose, label in (("main_image", "Main listing image"), ("packaging", "Packaging"),
                               ("lifestyle", "Lifestyle — the buyer's future self")):
            if prompts.get(purpose):
                L += [f"**{label}**", "```", str(prompts[purpose]).strip(), "```"]
    (run / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


cmd_verdict = cmd_report  # old name still works


# ======================================================================================= prompts

def brain() -> dict:
    """Split CLAUDE.md into {'protocol', 'standards', 'knowledge', 'scout', 'buyer', …}."""
    if not BRAIN.exists():
        sys.exit(f"CLAUDE.md not found next to engine.py ({BRAIN})")
    out, key, buf, fenced = {}, "protocol", [], False
    for line in BRAIN.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            fenced = not fenced
        m = None if fenced else re.match(r"^## (KNOWLEDGE|STANDARDS|AGENT: (\w+))\s*$", line)
        if m:
            out[key] = "\n".join(buf).strip()
            key, buf = (m.group(2) or m.group(1)).lower(), []
            continue
        buf.append(line)
    out[key] = "\n".join(buf).strip()
    return out


def next_phase(run: Path) -> str | None:
    for p in PHASES:
        if not (run / f"{p}.json").exists():
            return p
    return None


# Which knowledge subsections each agent receives (matched against the ### headings in
# CLAUDE.md's KNOWLEDGE section). Sending everyone everything is the single biggest credit leak.
KNOW_FOR = {"scout": ("buyer journey",),
            "competition": ("competition playbook",),
            "buyer": ("buying laws", "tag vocabulary", "buyer journey"),
            "innovaty": ("buying laws", "tag vocabulary", "buyer journey", "innovation playbook",
                         "five-year test", "competition playbook"),
            "genius": ("unit economics", "competition playbook"),
            "critic": ("buying laws", "tag vocabulary", "buyer journey", "innovation playbook",
                       "five-year test", "competition playbook", "unit economics")}


def knowledge_for(phase: str, knowledge: str) -> str:
    """The slices of the knowledge base this phase actually uses; the whole thing as a fallback."""
    parts = re.split(r"(?m)^### ", knowledge)
    keep = [q for q in parts[1:]
            if any(k in q.splitlines()[0].lower() for k in KNOW_FOR.get(phase, ()))]
    if not keep:
        return knowledge
    return (parts[0].strip() + "\n\n" + "\n\n".join("### " + q.strip() for q in keep)).strip()


def build_prompt(run: Path, phase: str, fast=False) -> str:
    if phase not in PHASES:
        sys.exit(f"phase must be one of {', '.join(PHASES)}")
    b, d = brain(), read_run(run)
    for key in (phase, "knowledge", "standards"):
        if not b.get(key):
            sys.exit(f"CLAUDE.md has no '{key}' section — it must keep its '## KNOWLEDGE' and "
                     f"'## AGENT: <name>' headings")
    if "brief" not in d:
        sys.exit(f"{run}/brief.json is missing — start with `engine.py new`")
    order = PHASES[:PHASES.index(phase)]
    needs = [n for n in order if n != "competition" or (run / "competition.json").exists()]
    if phase == "competition":
        needs = ["scout"]
    missing = [n for n in needs if n not in d]
    broken = [n for n in needs if n in d and "__broken__" in d[n]]
    if missing or broken:
        sys.exit(f"{phase} needs " + ", ".join(
            [f"{n} (missing)" for n in missing] + [f"{n} (invalid JSON)" for n in broken]) + " first")
    focus = d["brief"].get("mode") == "focus"
    parts = [b[phase],
             "\n# STANDARDS THAT APPLY TO EVERY PHASE\n" + b["standards"],
             "\n# KNOWLEDGE BASE\n" + knowledge_for(phase, b["knowledge"]),
             "\n# brief.json\n```json\n" + json.dumps(d["brief"], indent=1) + "\n```"]
    if focus:
        parts.append("\nFOCUS MODE. Think only about the products in `brief.focus_products`. Do not survey the "
                     "category, do not open products you were not given. The one with role `mine` (else P1) is "
                     "the product under evaluation; the others are the grid the buyer sees. Scout: hard cap of "
                     f"{d['brief'].get('search_budget_per_product', 3)} web searches per product, plus 2 for fees. "
                     "When the cap is reached, stop and record a gap.")
    elif phase == "scout":
        parts.append(f"\nSEARCH BUDGET: hard cap of {d['brief'].get('search_budget', 8)} web searches in "
                     "total, plus 2 for fees. Stop at the cap and record gaps instead of chasing them. "
                     "If the product exists in several shapes or dimensions, name the most successful "
                     "variant (reviews, rank, share) in `variant_chosen` and anchor ALL research on it — "
                     "do not mix numbers across shapes.")
    if phase == "competition":
        parts.append("\nSEARCH BUDGET: reason from scout.json first; at most 3 web searches, only to "
                     "confirm seller count, a brand's presence, or a clone price. Record gaps.")
    if phase == "innovaty":
        tier = d["brief"].get("packaging_tier")
        parts.append(f"\nPACKAGING TIER chosen by the founder: **{tier}** — {TIER_HELP[tier]}. Design the "
                     f"unboxing inside this tier: unique, exclusive, eye-catching and affordable, never a "
                     f"$500 unboxing." if tier in TIERS else
                     "\nNo packaging tier was chosen. Assume 'moderate' (printed box + insert) and say so.")
        if d["brief"].get("packaging_note"):
            parts.append(f"Founder's packaging note: {d['brief']['packaging_note']}")
    if fast:
        note = {"scout": "cover the essentials and record gaps rather than chasing them",
                "competition": "the 3500 rule, the clone wave, two moats — nothing more",
                "buyer": "keep every section to its minimum length; the 3-second scan and the "
                         "strongest needs carry the weight",
                "innovaty": "four ideas, not seven",
                "genius": "cost the recommended version only",
                "critic": "high-severity flags only; skip the low findings"}[phase]
        parts.append(f"\nFAST MODE: {note}. Be concise everywhere the contract allows it.")
    for n in needs:
        parts.append(f"\n# {n}.json\n```json\n" + json.dumps(d[n], indent=1) + "\n```")
    relax = FOCUS_RELAX.get(phase, 0) if focus else 0
    parts.append(f"\n# YOUR OUTPUT CONTRACT — write this to `{run}/{phase}.json`\n"
                 f"Every field below is required unless marked OPTIONAL. Ranges are "
                 f'`{{"low", "base", "high", "assumption"}}` and may carry `"stale": true`. '
                 f"The list minimums shown are the ones that will be enforced.\n\n```\n"
                 + render(CONTRACTS[phase], relax=relax) + "\n```")
    parts.append("\nReturn only the JSON object. No prose, no code fences.")
    return "\n".join(parts)


# ========================================================================================== run

def cmd_run(product, url, buyer_desc, focus, mine, budget, model, fast, only, packaging=None):
    try:
        import anthropic
    except ImportError:
        sys.exit("this command needs the SDK:  pip install anthropic")
    client = anthropic.Anthropic()
    run = HERE / "runs" / slugify(product)
    if not (run / "brief.json").exists():
        cmd_new(run, product, url, focus, mine, budget, packaging)
    brief = load(run / "brief.json")
    if buyer_desc:
        brief["target_buyer"]["description"] = buyer_desc
    if packaging in TIERS:
        brief["packaging_tier"] = packaging
    if brief.get("packaging_tier") not in TIERS:
        band = (brief.get("target_buyer") or {}).get("price_band_usd")
        tier, why = suggest_tier(float(band.get("max") or 0) if isinstance(band, dict) else 0)
        brief["packaging_tier"] = tier
        brief.setdefault("assumptions", []).append(f"packaging tier assumed '{tier}' ({why}); pass --packaging to choose")
        print(f"packaging tier not chosen — assuming '{tier}': {why}")
    dump(brief, run / "brief.json")
    if str(brief["target_buyer"]["description"]).startswith("TO FILL"):
        sys.exit(f"fill target_buyer.description in {run/'brief.json'} first (or pass --buyer)")
    fast = fast or brief.get("mode") == "focus"

    for phase in [p for p in PHASES if p in (only or PHASES)]:
        if (run / f"{phase}.json").exists():
            print(f"→ {phase}: already written, skipping"); continue
        m = (FAST_MODELS.get(phase, model) if fast else model)
        print(f"→ {phase} ({m}) …", flush=True)
        prompt = build_prompt(run, phase, fast)
        tools = [{"type": "web_search_20250305", "name": "web_search",
                  "max_uses": {"scout": 12, "competition": 3}.get(phase, 4)}] if phase != "buyer" else None
        data = _ask(client, m, prompt, tools)
        errs = phase_errors(phase, data, load(run / "brief.json").get("mode") == "focus")
        if errs:
            print(f"   {len(errs)} contract problem(s) — asking for a repair of those fields only")
            data = _ask(client, m, prompt + "\n\n# YOUR PREVIOUS OUTPUT\n```json\n" + json.dumps(data)
                        + "\n```\n\nFix ONLY these problems and return the whole corrected object:\n- "
                        + "\n- ".join(errs[:40]), None)
        dump(data, run / f"{phase}.json")
        print(f"   {phase}.json written")
    print()
    if next_phase(run):
        print(f"{next_phase(run)} has not run yet — no report. "
              f"Run without --only, or `python engine.py next {run}`.")
        return
    cmd_report(run)


def _ask(client, model, prompt, tools, tries=2):
    for attempt in range(tries):
        kwargs = {"model": model, "max_tokens": 16000,
                  "messages": [{"role": "user", "content": prompt}]}
        if tools:
            kwargs["tools"] = tools
        msg = client.messages.create(**kwargs)
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
        try:
            return json.loads(text[text.find("{"):text.rfind("}") + 1])
        except Exception as e:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            prompt += f"\n\nYour last reply was not valid JSON ({e}). Return only the JSON object."
    return {}


# ========================================================================================= demo

DEMO = {
    "brief": {"slug": "_demo", "product_name": "Magnetic cable clips (demo)", "source_url": "",
              "marketplace": "amazon.com", "created_at": "2026-01-01T00:00:00+00:00", "mode": "category",
              "target_buyer": {"description": "Renter with a desk against drywall who keeps losing charging cables behind it",
                               "context": "Phone, evening, after a cable falls again",
                               "price_band_usd": {"min": 8, "max": 20}},
              "seller_constraints": {"launch_budget_usd": 25000, "time_to_market_months": 9,
                                     "origin_country": "CN", "must_keep": [], "must_avoid": ["electronics"]},
              "user_hypotheses": ["Buyers will pay more for clips that do not pull paint"],
              "packaging_tier": "moderate", "packaging_note": "unique but affordable — not a $500 unboxing",
              "assumptions": ["synthetic demo data"], "iterations": 0},
    "scout": {"retrieved_at": "2026-01-01",
              "facts": [{"fact_id": f"F{i}", "statement": s, "source": "https://example.com/demo", "confidence": c}
                        for i, (s, c) in enumerate([
                            ("Page-one prices for the primary term run $6.99 to $18.99", "high"),
                            ("The best seller holds 4.4 stars across 12,400 reviews", "high"),
                            ("Adhesive failure appears in roughly a third of one-star reviews", "medium"),
                            ("A quarter of negative reviews mention paint damage on removal", "medium"),
                            ("Six-packs are the dominant configuration on the first page", "high"),
                            ("Magnetic variants appeared in the top twenty during the last year", "low")], start=1)],
              "search_terms": [{"term": "cable clips", "seasonal": False},
                               {"term": "cord organizer desk", "seasonal": False},
                               {"term": "cable management clips adhesive", "seasonal": False}],
              "price_ladder": {"primary_term": "cable clips", "min": 6.99, "median": 10.99, "max": 18.99,
                               "typical_pack_count": 6,
                               "anchor_note": "Row one sits near $11, so anything past $16 needs a visible reason"},
              "competitors": [{"name": f"Demo competitor {i}", "price_usd": p, "rating": r, "review_count": n,
                               "main_image_description": "White clip on a thin white cable",
                               "fact_ids": ["F1", "F2"]}
                              for i, (p, r, n) in enumerate([(8.99, 4.4, 12400), (10.99, 4.2, 3100),
                                                             (14.99, 4.5, 860), (6.99, 3.9, 540)], start=1)],
              "complaint_clusters": [
                  {"cluster_id": "C1", "pattern": "The adhesive lets go after a few weeks", "share_of_negative": 0.34,
                   "stage": "5", "root_cause_hypothesis": "Generic acrylic tape with no surface prep",
                   "paraphrased_examples": ["fell off within a month"], "fact_ids": ["F3"]},
                  {"cluster_id": "C2", "pattern": "Removal pulls paint off the wall", "share_of_negative": 0.24,
                   "stage": "6", "root_cause_hypothesis": "High-tack tape with no pull tab", "fact_ids": ["F4"]},
                  {"cluster_id": "C3", "pattern": "Thick cables will not seat in the jaw", "share_of_negative": 0.18,
                   "stage": "4", "root_cause_hypothesis": "Single fixed jaw width", "fact_ids": ["F3"]}],
              "praise_clusters": [{"pattern": "Small and almost invisible once fitted", "share_of_positive": 0.41}],
              "fee_inputs": {k: {"low": lo, "base": b, "high": hi, "assumption": a, "stale": st}
                             for k, (lo, b, hi, a, st) in {
                                 "referral_rate": (0.13, 0.15, 0.17, "home category referral band", False),
                                 "fba_fee_usd": (3.1, 3.4, 3.8, "small standard, under 6 oz", False),
                                 "storage_per_cuft_month_usd": (0.78, 0.87, 2.4, "peak months included", False),
                                 "duty_rate": (0.03, 0.05, 0.08, "plastic articles, origin CN", True),
                                 "sea_freight_usd_per_cbm": (60, 95, 160, "China to US west coast LCL", True),
                             }.items()},
              "gaps": ["synthetic demo — no live sources"]},
    "competition": {
        "arena": {"sellers_on_page_one": 14, "lookalike_share": 0.8, "price_floor_usd": 5.99,
                  "dominant_form": "white adhesive clip, six-pack, thin-cable photo",
                  "summary": "A crowded open field of near-identical white clips priced $7–11, where nobody "
                             "shows a thick cable or a painted wall. One large-review seller anchors the top row."},
        "brand_dominance": {"level": "dominated", "top_brand": "Demo competitor 1", "top_review_count": 12400,
                            "rule_3500": True,
                            "evidence": "One listing carries 12,400 reviews; the next carries 3,100; the rest are under 900",
                            "deep_study": "The leader wins on review count and a $8.99 six-pack, not on the product: its "
                                          "one-stars repeat the adhesive and paint failures. It never shows removal or a "
                                          "thick cable, so we flank it on the two fears it leaves open rather than on price."},
        "copycat_risk": {"level": "high",
                         "months_to_first_clone": {"low": 2, "base": 4, "high": 8, "assumption": "a pull tab is visible and cheap to imitate"},
                         "clone_price_usd": {"low": 6.99, "base": 8.99, "high": 10.99, "assumption": "clones sell at the category floor"},
                         "why": "The tab is visible in the thumbnail, needs no special tooling, and the category already has dozens of quantity-first sellers"},
        "price_war": {"win_probability_before_clones": 0.55, "win_probability_after_clones": 0.3,
                      "choice_rank_after_clones": 3, "share_haircut_pct": 40,
                      "why": "Once three tiles show a tab at $8.99, the buyer compares tabs on price and we drop to the third choice unless the reviews say ours is the one that lasted"},
        "moats": [
            {"moat": "Named 3M pad plus a printed 30-day shear test in the listing", "type": "spec_edge", "strength": "medium",
             "cost_tier": "cents", "why": "A quantity seller will not pay for the branded tape or run the test"},
            {"moat": "Two spare plates and the prep wipe in every pack", "type": "bundle", "strength": "medium",
             "cost_tier": "cents", "why": "Adds cents per pack that a price-floor seller cannot afford"},
            {"moat": "Registered design on the shear-plate tab geometry", "type": "design_registration", "strength": "strong",
             "cost_tier": "dollars", "why": "Lets us report the exact copies and slows the wave by a season"}],
        "competitor_profiles": [
            {"name": "Demo competitor 1", "price_usd": 8.99, "review_count": 12400, "strength": "review count and price",
             "weakness": "adhesive and paint complaints, never shows removal", "threat": "high"},
            {"name": "Demo competitor 2", "price_usd": 10.99, "review_count": 3100, "strength": "clean white design",
             "weakness": "thin-cable only", "threat": "medium"},
            {"name": "Demo competitor 3", "price_usd": 14.99, "review_count": 860, "strength": "premium look",
             "weakness": "same tape as everyone", "threat": "low"}],
        "watch_signals": ["New sellers showing a tab in the thumbnail", "Price drops below $8 on page one",
                          "Our review velocity vs the leader's"],
        "tags": ["sharp.physical_availability", "cialdini.social_proof", "moore.chasm"]},
    "buyer": {"persona": {"who_i_am": "I rent a flat and my desk sits against a painted drywall wall",
                          "trigger": "My charging cable slid behind the desk for the third time tonight",
                          "fired_solution": "Cheap sticky hooks that fell off in a fortnight",
                          "urgency": "this_week", "search_term": "cable clips",
                          "why_this_term": "It is what the last pack was called and what I half-remember"},
              "buy_driver": {"driver": "pain", "pain_level": "moderate",
                             "evidence": "C1 and C2 are the whole one-star story and I have lived both — "
                                         "the hooks fell and the paint came with them",
                             "tags": ["law.pain_moderate", "kahneman.loss_aversion"]},
              "future_self": "I see my desk with every cable exactly where I left it, a friend asking why the "
                             "flat suddenly looks so tidy, and me never crawling under the desk again.",
              "comfort_and_laziness": "It deletes the nightly crawl behind the desk; once the clips are up I "
                                      "never think about cables again — that lazy path is what I am paying for.",
              "benefits_not_features": [
                  {"feature": "Pull tab on the base plate", "benefit": "I keep my deposit — no repainting when I move out"},
                  {"feature": "Branded high-tack pad", "benefit": "I stick it once and forget it exists"},
                  {"feature": "Prep wipe in the box", "benefit": "It actually stays up — no guessing if the wall was clean"}],
              "three_second_scan": [
                  {"signal": "image", "what_i_see": "Sixteen near-identical white clips on thin white cables",
                   "verdict": "neutral", "tags": ["gate.image_orientation", "kahneman.system1"]},
                  {"signal": "price", "what_i_see": "Most tiles sit around eleven dollars",
                   "verdict": "neutral", "tags": ["gate.price_vs_anchor", "kahneman.anchoring"]},
                  {"signal": "rating", "what_i_see": "Four-plus stars but the top one-stars all say it fell off",
                   "verdict": "push_away", "tags": ["gate.reviews_negative_first", "kahneman.availability"]},
                  {"signal": "design", "what_i_see": "No tile shows a thick black cable or a painted wall — my case",
                   "verdict": "push_away", "tags": ["kahneman.wysiati", "law.three_second_scan"]}],
              "purchase_probability_current": {"click": 0.35, "add_to_cart": 0.3, "buy": 0.22,
                                               "reasoning": "The tile is indistinguishable, the reviews confirm my last failure, and nothing shows my case"},
              "fears": [{"rank": 1, "question": "Will it stay up longer than the last one?", "tags": ["kahneman.loss_aversion"], "from_cluster_id": "C1", "answered_by": "product_change"},
                        {"rank": 2, "question": "Will it take the paint with it?", "tags": ["post.return_reason"], "from_cluster_id": "C2", "answered_by": "image"},
                        {"rank": 3, "question": "Will my thick cable fit?", "tags": ["kahneman.wysiati"], "from_cluster_id": "C3", "answered_by": "image"}],
              "unmet_needs": [
                  {"need_id": "N1", "statement": "A clip that stays up for a year, not a fortnight",
                   "pain_level": "extreme", "severity": 9, "evidence_cluster_ids": ["C1"]},
                  {"need_id": "N2", "statement": "Getting it off the wall without losing my deposit",
                   "pain_level": "moderate", "severity": 8, "evidence_cluster_ids": ["C2"]},
                  {"need_id": "N3", "statement": "One clip that takes my fat charger and my thin earphone wire",
                   "pain_level": "moderate", "severity": 6, "evidence_cluster_ids": ["C3"]},
                  {"need_id": "N4", "statement": "Clips that disappear into the room once fitted",
                   "pain_level": "latent", "severity": 3, "evidence_cluster_ids": []}],
              "price_psychology": {"anchor_seen_usd": 10.99, "max_without_reason_usd": 12.0,
                                   "max_with_reason_usd": 17.0,
                                   "reason_required": "I have to see, in the thumbnail, that it grips a thick cable and lifts off without taking paint"},
              "packaging_expectation": "A small crisp box that opens flat with the clips held in place and the "
                                       "wipe on top — a poly bag of loose clips would tell me this is the same "
                                       "third-rate pack I threw away.",
              "lifestyle_target": {"primary": "Tidy-home renter: a clean desk in a small bright flat, someone who "
                                              "fixes things in ten minutes on a weeknight",
                                   "avoid": "Corporate server-room cable management — that is not me"},
              "memory_hook": "The little pull tab — next time a hook rips my paint I will remember the clip "
                             "that promised to come off clean.",
              "durability_instinct": {
                  "what_warns_me": "Thin living hinges and clever snap-lids — every one I have owned went stiff with "
                                   "dust and cracked within a year; a tiny cable hole means the fat charger never fits",
                  "what_reassures_me": "A solid one-piece body, a jaw wide enough for my charger, and a photo of it "
                                       "still up after months"},
              "color_read": "Blue accents on white — this purchase is about trust that it stays up and comes off clean",
              "hypotheses_tested": [{"hypothesis": "Buyers will pay more for clips that do not pull paint",
                                     "verdict": "confirmed", "why": "It is my second fear and my deposit"}],
              "what_would_make_me_buy": (
                  "I would buy the one whose first picture shows a fat black cable held in a clip on a painted wall, "
                  "with a little tab you pull to take it off. I want to see that it survives longer than a month, and "
                  "I want the pack to include a wipe so I do not have to guess whether the wall was clean enough. If "
                  "the picture answers those three things before I open the listing, I will pay a few dollars more "
                  "than the cheap six-pack I threw away, and I will tell my flatmate about it when hers falls down.")},
    "innovaty": {"target_spec": {"needs_targeted": ["N1", "N2", "N3"],
                                 "must_fix_clusters": ["C1", "C2", "C3"], "should_fix_clusters": [],
                                 "over_served_to_cut": ["colour variants", "pack size variety"]},
                 "ideas": [
                     {"idea_id": "I1", "name": "Pull-tab base plate", "role": "hero", "aspect": "pain_removal",
                      "mechanism": "The adhesive sits on a separate thin plate with a folded tab below the clip body. Pulling the tab shears the bond along the wall plane instead of peeling the paint away, so the plate releases before the paint fails.",
                      "fixes_complaint_clusters": ["C2"], "improves_needs": ["N2"],
                      "improves_gates": ["gate.image_orientation", "gate.image_fit"],
                      "kano_class": "must_be", "triz_or_erric_tags": ["triz.segmentation", "triz.taking_out"],
                      "thumbnail_visibility": "high", "cost_tier": "cents", "priority": "now",
                      "prior_art_risk": "medium", "prior_art_reason": "Stretch-release tabs are widely patented; a shear plate is a different mechanism but needs a search",
                      "test_that_proves_it": "Removal on painted drywall after 30 days at 23 C and 40 C, 20 samples",
                      "how_it_looks_in_main_image": "A thumb pulling a small tab as the clip lifts off a painted wall, paint intact",
                      "buyer_sentence": "You just pull the tab and it comes off without taking the paint",
                      "durability_signal": "reassures",
                      "five_year_test": {"use_cycle": "Stuck once, left for years, removed once or twice at a move; the tab is pulled maybe three times in its life",
                                         "failure_modes": ["tab tears off if the fold is too thin", "plate creeps under a heavy cable"],
                                         "design_answer": "1.2 mm tab with a radiused fold, plate area sized for three times the cable weight",
                                         "fit_range": "any wall clip; independent of cable size"}},
                     {"idea_id": "I2", "name": "Branded high-tack acrylic pad", "role": "supporting", "aspect": "reliability",
                      "mechanism": "Replace generic tape with a die-cut branded acrylic foam pad rated for the cable load. The foam conforms to wall texture and the higher shear rating covers the creep that makes generic tape let go.",
                      "fixes_complaint_clusters": ["C1"], "improves_needs": ["N1"],
                      "improves_gates": ["gate.bullets", "gate.reviews_negative_first"],
                      "kano_class": "must_be", "triz_or_erric_tags": ["erric.raise", "cialdini.authority"],
                      "thumbnail_visibility": "low", "cost_tier": "cents", "priority": "now",
                      "prior_art_risk": "low", "prior_art_reason": "Buying a named tape is not an invention",
                      "test_that_proves_it": "Static shear at three times cable weight for 30 days",
                      "how_it_looks_in_main_image": "A named tape logo on the pad, called out in image three",
                      "buyer_sentence": "It uses the proper tape, not the cheap stuff",
                      "durability_signal": "neutral",
                      "five_year_test": {"use_cycle": "Holds a static load for years through summer heat and winter dry air",
                                         "failure_modes": ["creep at 40 C", "adhesion loss on dusty paint"],
                                         "design_answer": "Acrylic foam rated for the load with margin, applied after the prep wipe"}},
                     {"idea_id": "I3", "name": "Dual-durometer flexing jaw", "role": "supporting", "aspect": "comfort",
                      "mechanism": "The jaw is overmoulded in a softer elastomer over a rigid body so it spreads for a thick cable and closes on a thin one. The soft lip provides the retention instead of an interference fit.",
                      "fixes_complaint_clusters": ["C3"], "improves_needs": ["N3"],
                      "improves_gates": ["gate.image_fit"], "kano_class": "performance",
                      "triz_or_erric_tags": ["triz.local_quality", "triz.dynamics"],
                      "thumbnail_visibility": "high", "cost_tier": "dimes", "priority": "now",
                      "prior_art_risk": "medium", "prior_art_reason": "Overmoulded jaws exist in cable management; the geometry may be free",
                      "test_that_proves_it": "Retention at 2 mm and 10 mm diameters over 1000 cycles",
                      "how_it_looks_in_main_image": "One clip holding a fat black cable beside one holding a thin white cable",
                      "buyer_sentence": "It grips my thick charger as well as the thin one",
                      "durability_signal": "reassures",
                      "five_year_test": {"use_cycle": "Cable pushed in and pulled out a few times a week for years; dust settles in the jaw",
                                         "failure_modes": ["elastomer lip tears", "jaw takes a set and loses grip"],
                                         "design_answer": "Rigid body with a 2 mm elastomer lip, no hinge to jam, opening sized 2–10 mm",
                                         "fit_range": "2 mm earphone wire to 10 mm braided charger"}},
                     {"idea_id": "I4", "name": "Prep wipe in the pack", "role": "hygiene", "aspect": "addition",
                      "mechanism": "An alcohol prep pad ships in the box and the instruction is printed on the liner itself, so the wall gets cleaned before the pad is applied. Most early failures are a dirty wall, not weak tape.",
                      "fixes_complaint_clusters": ["C1"], "improves_needs": ["N1"],
                      "improves_gates": ["gate.image_2_to_6"], "kano_class": "delighter",
                      "triz_or_erric_tags": ["triz.preliminary_action", "triz.merging"],
                      "thumbnail_visibility": "medium", "cost_tier": "cents", "priority": "now",
                      "prior_art_risk": "low", "prior_art_reason": "Including a wipe is common practice",
                      "test_that_proves_it": "Peel strength with and without prep on three wall finishes",
                      "how_it_looks_in_main_image": "The wipe sachet laid beside the clips in the what-is-in-the-box shot",
                      "buyer_sentence": "They even give you the wipe so it actually sticks",
                      "durability_signal": "neutral",
                      "five_year_test": {"use_cycle": "Used once at installation",
                                         "failure_modes": ["sachet dries out in storage"],
                                         "design_answer": "Foil sachet instead of paper so the alcohol does not dry out on the shelf"}}],
                 "durability_review": {"weakest_point": "the fold of the pull tab on the base plate",
                                       "physics": "Static shear on the pad for years, one pull-force event at removal through the tab, and repeated cable push-in against the jaw lip; no hinge means no dust-jam and no fatigue crack",
                                       "five_year_verdict": "survives",
                                       "changes_made": ["dropped a snap-lid variant that fails the hinge test", "widened the jaw opening to 10 mm"]},
                 "pillars": {"reliability": "one-piece body, no moving hinge, named tape",
                             "durability": "no fatigue part; the only consumable is the pad, and spares are in the box",
                             "uniqueness": "the only clip in the grid that shows clean removal",
                             "exclusiveness": "blue tab and printed lid read as a considered brand, not a bag of clips",
                             "attraction": "the tab-pull photo on a painted wall stops the scroll"},
                 "moat_built_in": ["Named 3M pad plus a printed 30-day shear test in the listing",
                                   "Two spare plates and the prep wipe in every pack"],
                 "packaging": {"tier": "moderate", "unboxing_moment": "A crisp matte box opens flat like a book: six clips seated in a "
                                                  "paper tray, the wipe on top, the pull-tab promise printed inside the lid",
                               "upgrade_vs_category": "The category ships loose clips in a poly bag; a tray plus a "
                                                      "printed lid reads as a brand, not a commodity",
                               "cost_tier": "dimes"},
                 "color_strategy": {"product_color": "Clean white body with a blue pull tab — blue is the trust this "
                                                     "purchase runs on, and the tab must be findable",
                                    "main_image_anchor": "Soft warm-grey wall background so the white clip and blue tab "
                                                         "pop in a grid of white-on-white tiles",
                                    "brand_direction": "Calm, reliable, renter-friendly — trust over flash"},
                 "bundle_or_addition": {"what": "Two spare adhesive plates in every pack",
                                        "why_it_wins": "Answers the fear of a failed stick and makes moving flat painless",
                                        "cost_tier": "cents"},
                 "errc": {"eliminate": ["colour variants"], "reduce": ["pack count from twelve to six"],
                          "raise": ["adhesive specification"], "create": ["clean removal as a stated feature"]},
                 "version_plan": {"v1_now": ["I1", "I2", "I4"],
                                  "v2_later": [{"idea_id": "I3", "unlock_trigger": "after 100 reviews confirm the jaw complaint persists"}]},
                 "listing_implications": {"title_first_60": "Cable Clips That Come Off Clean - Pull Tab, 6 Pack",
                                          "main_image_brief": "Thumb pulling the tab off a painted wall, paint intact, thick black cable still in the jaw",
                                          "image_briefs_2_to_4": ["Scale against a hand and a ruler",
                                                                  "A 10 mm cable seated in the jaw",
                                                                  "Three-step install with the wipe"],
                                          "honest_limitations": ["Not for textured or freshly painted walls",
                                                                 "One pad per clip; spares included, more sold separately"]},
                 "image_prompts": [
                     {"purpose": "main_image",
                      "prompt": "Product photo for an Amazon main image: a small white cable clip holding a thick black "
                                "braided charging cable against a softly lit warm-grey painted wall, a thumb pulling a "
                                "small blue tab at the base as the clip lifts cleanly off, paint perfectly intact, "
                                "crisp studio lighting, sharp focus, minimal shadows, square 1:1 crop, no text"},
                     {"purpose": "packaging",
                      "prompt": "Packshot of a small matte white tuck box opened flat like a book on a light wooden desk: "
                                "six white cable clips seated in a paper tray, a folded alcohol wipe sachet on top, the "
                                "inside of the lid printed with a simple blue pull-tab diagram, soft daylight, clean "
                                "e-commerce styling, square 1:1, no logos"},
                     {"purpose": "lifestyle",
                      "prompt": "Bright small apartment desk scene at golden hour: a tidy white desk against a warm-grey "
                                "wall, three charging cables held in neat white clips with tiny blue tabs, a young renter "
                                "working relaxed on a laptop, plants and a coffee mug, cozy organised feeling, shallow "
                                "depth of field, 4:5 vertical"}],
                 "what_i_cut": ["colour variants", "the twelve-pack SKU"]},
    "genius": {"planning_fallacy_multiplier": 1.4,
               "versions": [{"version_id": "v1_now", "idea_ids": ["I1", "I2", "I4"],
                             "bom": [{"part": "Moulded PP clip body", "qty": 6,
                                      "unit_cost_usd": {"low": 0.04, "base": 0.06, "high": 0.09, "assumption": "10k units, 8 cavities"}},
                                     {"part": "Die-cut branded acrylic pad", "qty": 6,
                                      "unit_cost_usd": {"low": 0.05, "base": 0.08, "high": 0.12, "assumption": "named tape, die-cut"}},
                                     {"part": "Alcohol prep wipe", "qty": 2,
                                      "unit_cost_usd": {"low": 0.01, "base": 0.015, "high": 0.02, "assumption": "bulk sachets"}},
                                     {"part": "Printed tuck box", "qty": 1,
                                      "unit_cost_usd": {"low": 0.1, "base": 0.16, "high": 0.25, "assumption": "FSC paperboard"}}],
                             "unit_weight_g": 70,
                             "landed_cost_usd": {"low": 1.5, "base": 1.95, "high": 2.6, "assumption": "EXW plus LCL freight, duty and inbound"}}],
               "tooling_and_nre": [{"item": "Steel production tool, 8 cavities",
                                    "cost_usd": {"low": 9000, "base": 13000, "high": 19000, "assumption": "two-plate tool with a shear-plate insert"}},
                                   {"item": "FTO search on the pull tab",
                                    "cost_usd": {"low": 1500, "base": 3000, "high": 6000, "assumption": "prior art on stretch-release is dense"}},
                                   {"item": "Photography and first ad budget",
                                    "cost_usd": {"low": 2500, "base": 4000, "high": 7000, "assumption": "one shoot plus eight weeks of ads"}}],
               "fixed_launch_cost_usd": {"low": 14000, "base": 21000, "high": 33000, "assumption": "tooling, FTO, testing, photography, launch ads"},
               "price_usd": {"low": 14.99, "base": 16.99, "high": 18.99, "assumption": "above the $11 anchor, at the ceiling the buyer named for a visible reason"},
               "economics": {"referral_rate": {"low": 0.13, "base": 0.15, "high": 0.17, "assumption": "home category band"},
                             "fba_fee_usd": {"low": 3.1, "base": 3.4, "high": 3.8, "assumption": "small standard under 6 oz"},
                             "storage_alloc_usd": {"low": 0.04, "base": 0.07, "high": 0.14, "assumption": "two months of cover including Q4"},
                             "return_rate": {"low": 0.03, "base": 0.05, "high": 0.09, "assumption": "adhesive products run high on fit complaints"},
                             "ad_rate": {"low": 0.15, "base": 0.25, "high": 0.45, "assumption": "launch ACoS falling to steady state"}},
               "forecast": {"term_monthly_units": {"low": 18000, "base": 26000, "high": 38000, "assumption": "tracker sum across the top twenty, plus or minus forty percent"},
                            "share_m6": {"low": 0.01, "base": 0.025, "high": 0.05, "assumption": "page two to one once reviews pass thirty"},
                            "share_m12": {"low": 0.02, "base": 0.045, "high": 0.08, "assumption": "page one on the primary term"},
                            "monthly_units_m6": {"low": 180, "base": 650, "high": 1900, "assumption": "share applied to term volume"},
                            "monthly_units_m12": {"low": 360, "base": 1170, "high": 3040, "assumption": "share applied to term volume"},
                            "annual_units_y1": {"low": 2400, "base": 8000, "high": 21000, "assumption": "ramp integrated over twelve months"},
                            "reasoning": "Scout's tracker estimates put the term near 26k units a month within plus or minus forty percent. A new entrant with a visibly different thumbnail reaches one to five percent of a term by month six once it clears the review chasm, and three to eight percent by month twelve if the click-through holds, so the base case takes 2.5 percent then 4.5 percent."},
               "timeline": {"phases": [{"phase": "CAD, DFM and prototypes", "weeks": {"low": 5, "base": 7, "high": 10, "assumption": "two suppliers quoting in parallel"}},
                                       {"phase": "Adhesive and jaw testing", "weeks": {"low": 3, "base": 5, "high": 8, "assumption": "30-day creep test is the long pole"}},
                                       {"phase": "Tooling and first article", "weeks": {"low": 7, "base": 11, "high": 17, "assumption": "one iteration expected"}},
                                       {"phase": "Production, freight and check-in", "weeks": {"low": 8, "base": 11, "high": 15, "assumption": "ocean freight plus FBA receiving"}}],
                            "weeks_to_first_sale": {"low": 23, "base": 34, "high": 50, "assumption": "phases in series with the 1.4 multiplier applied"}},
               "premortem": [{"obituary": "The pull tab shears the plate but the pad still lifts paint on cheap emulsion, and the one-star reviews say so",
                              "probability": 0.3, "impact": "fatal", "mitigation": "Test on three paint grades before tooling and state the limitation in the bullets",
                              "mitigation_cost_usd": {"low": 800, "base": 1500, "high": 3000, "assumption": "third-party test house"}},
                             {"obituary": "A factory copies the visible tab within ninety days at sixty percent of the price",
                              "probability": 0.45, "impact": "major", "mitigation": "Own the term with review velocity and keep the tape specification as the moat",
                              "mitigation_cost_usd": {"low": 2000, "base": 5000, "high": 12000, "assumption": "extra launch ad spend"}},
                             {"obituary": "Packaging comes in two millimetres over the small-standard line and the FBA fee jumps",
                              "probability": 0.2, "impact": "major", "mitigation": "Freeze the box spec against the current size table before tooling",
                              "mitigation_cost_usd": {"low": 0, "base": 400, "high": 1200, "assumption": "one packaging revision"}},
                             {"obituary": "The duty rate on the origin moves and the landed cost breaks the margin rail",
                              "probability": 0.25, "impact": "major", "mitigation": "Quote a second-source country before committing the tool",
                              "mitigation_cost_usd": {"low": 500, "base": 1200, "high": 3000, "assumption": "sampling from a second factory"}}],
               "idea_rulings": [{"idea_id": "I1", "ruling": "realistic", "why": "Adds a cheap second part and a tab feature to the tool", "deciding_number": "+$0.03 per unit, no new tool"},
                                {"idea_id": "I2", "ruling": "realistic", "why": "Named tape costs cents more and answers the worst cluster", "deciding_number": "+$0.05 per unit"},
                                {"idea_id": "I3", "ruling": "stretch", "why": "Overmould needs a second shot and a second tool", "deciding_number": "+$9k tooling, +$0.14 per unit"},
                                {"idea_id": "I4", "ruling": "realistic", "why": "A sachet and a printed liner", "deciding_number": "+$0.03 per pack"}],
               "recommended_version_id": "v1_now",
               "feasibility_verdict": "realistic",
               "regulatory": ["None for a passive accessory; check Prop 65 wording on packaging"],
               "three_sentences_to_founder": [
                   "The category loses on removal and adhesive creep, and both are cents to fix, so the product problem is real and cheap.",
                   "Price at about fifteen dollars against an eleven dollar anchor only works if the thumbnail shows the tab and the thick cable.",
                   "Hold the overmoulded jaw for version two; it doubles your tooling before you know the jaw complaint survives your own fix."]},
    "critic": {"findings": [
        {"id": "K1", "file": "genius", "field_path": "genius.forecast.share_m12", "severity": "low",
         "finding": "A 4.5 percent share of the term by month twelve assumes the click-through beats the median from launch, which nothing yet proves",
         "fix": "Widen the low end or name the CTR assumption explicitly", "owner_agent": "genius"},
        {"id": "K2", "file": "scout", "field_path": "scout.fee_inputs.duty_rate", "severity": "high",
         "finding": "The duty rate and the freight rate are both marked stale, so the landed cost carries unquantified error",
         "fix": "Fetch the current HTS line and one live LCL quote before tooling", "owner_agent": "scout"}],
        "unsourced_claim_paths": [], "untagged_judgement_paths": [], "contamination_detected": False,
        "overall": "flags_to_fix",
        "three_things_the_founder_must_hear": [
            "Your whole margin rests on a duty rate nobody fetched this run.",
            "The pull tab is the only thing a stranger can see at 300 pixels; if it does not photograph, you have a commodity.",
            "A factory can copy the tab in a quarter, so the review count you build in the first six months is the actual asset."]}
}


def cmd_demo():
    run = HERE / "runs" / "_demo"
    for name, obj in DEMO.items():
        dump(obj, run / f"{name}.json")
    print(f"wrote synthetic run to {run}\n")
    bad = cmd_check(run)
    print()
    cmd_score(run)
    print()
    cmd_verdict(run)
    print("\n" + ("demo FAILED — the contracts reject the fixture" if bad else "demo passed"))
    return bad


# ========================================================================================== cli

def main(argv=None):
    ap = argparse.ArgumentParser(prog="engine.py", description="Consumer Engine — deterministic side")
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="create runs/<slug>/brief.json")
    n.add_argument("run_dir"); n.add_argument("--name", required=True); n.add_argument("--url")
    n.add_argument("--focus", nargs="+", metavar="URL", help="1-5 product URLs; think only about these")
    n.add_argument("--mine", type=int, help="1-based index of the URL that is your product")
    n.add_argument("--budget", type=int, default=3, help="web searches per product in focus mode")
    n.add_argument("--packaging", choices=TIERS, help="simple | moderate | premium (asked if omitted)")
    n.add_argument("--packaging-note", help="anything the founder said about the box")

    for c, h in [("check", "validate every file and their coherence"), ("next", "print the phase to run now")]:
        sub.add_parser(c, help=h).add_argument("run_dir")
    for c, al, h in [("score", [], "economics, Monte-Carlo, readiness"),
                     ("report", ["verdict"], "write the one-page REPORT.md")]:
        q = sub.add_parser(c, aliases=al, help=h)
        q.add_argument("run_dir")
        q.add_argument("--force", action="store_true", help="run even if a contract check fails")

    p = sub.add_parser("prompt", help="print the exact prompt for one phase")
    p.add_argument("run_dir"); p.add_argument("phase", choices=PHASES); p.add_argument("--fast", action="store_true")

    sub.add_parser("demo", help="self-test on synthetic data, no API calls")

    r = sub.add_parser("run", help="drive every phase through the Anthropic API")
    r.add_argument("product"); r.add_argument("--url"); r.add_argument("--buyer")
    r.add_argument("--focus", nargs="+", metavar="URL"); r.add_argument("--mine", type=int)
    r.add_argument("--budget", type=int, default=3); r.add_argument("--model", default=DEFAULT_MODEL)
    r.add_argument("--packaging", choices=TIERS, help="simple | moderate | premium (suggested from price if omitted)")
    r.add_argument("--fast", action=argparse.BooleanOptionalAction, default=True,
                   help="fast is the default; --no-fast for the thorough pass")
    r.add_argument("--only", nargs="*", choices=PHASES)

    a = ap.parse_args(argv)
    if a.cmd == "demo":
        sys.exit(cmd_demo())
    if a.cmd == "run":
        return cmd_run(a.product, a.url, a.buyer, a.focus, a.mine, a.budget, a.model, a.fast, a.only, a.packaging)
    if a.cmd == "new":
        return cmd_new(Path(a.run_dir), a.name, a.url, a.focus, a.mine, a.budget, a.packaging, a.packaging_note)
    run = Path(a.run_dir)
    if a.cmd == "check":
        sys.exit(cmd_check(run))
    if a.cmd == "score":
        cmd_score(run, force=a.force)
    elif a.cmd in ("report", "verdict"):
        cmd_report(run, force=a.force)
    elif a.cmd == "next":
        nxt = next_phase(run)
        print(f"next phase: {nxt}\n  python engine.py prompt {run} {nxt}" if nxt
              else "all six phases are written — run `check`, then `report`")
    elif a.cmd == "prompt":
        print(build_prompt(run, a.phase, a.fast))


if __name__ == "__main__":
    main()
