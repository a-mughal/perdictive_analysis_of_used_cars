# Consumer Engine

A product-winning engine for Amazon sellers, in three files. You bring a product — it returns,
in a few minutes, a one-page plan for beating the competitors: the changes to make, what they
cost, the flags to close, and three ready-to-paste image prompts so you can *see* the improved
product before you build it.

The product is assumed already chosen (often from a sourcing briefing), so the engine never
declares anything a flop. Its two outcomes are **READY** or **FIX-FIRST**, and every flag is
routed to the agent that owns the fix.

| Agent | Role | What it produces |
|---|---|---|
| **scout** | market researcher | prices, the winning variant, complaint mining, live fees — every fact with a source |
| **competition** *(optional)* | the strategist | brand dominance (the 3,500-review rule), copycat risk, moats, the price war after clones arrive |
| **buyer** | the consumer | the seven buying laws applied in the first person: pain depth, future self, lazy path, benefits, the 3-second scan, durability instinct |
| **innovaty** | the competitor-beater | realistic changes by aspect, each put through a five-year durability test, packaging (inside the founder's chosen tier), colors, a bundle, moats baked in, and the 3 image prompts |
| **genius** | operator / CFO | BOM, tooling, timeline, forecast — all in honest ranges |
| **critic** | second pair of eyes | flags issues and routes each to its owner — it never vetoes |

`engine.py` does every calculation (contribution, break-even, 10,000-trial Monte-Carlo — run
twice when competition data exists, once at forecast volume and once after a clone-wave haircut
— sanity rails) so no model ever does arithmetic, validates every output, and writes REPORT.md.

```
engine.py    contracts, validation, economics, Monte-Carlo, report, prompt builder, self-test
CLAUDE.md    the protocol, the knowledge base (incl. the seven buying laws), the six agent briefs
README.md    this file
runs/        one folder per product — created as you go
```

## Run it in Claude Code (the intended way)

Open this folder with `claude`, then just say what you want:

```
analyze: Preset-Click Bicycle Torque Wrench, ASP $24.99 — "I don't know if I just
over-torqued my carbon stem and cracked it."
```

You can paste a whole product card from your sourcing briefings — name, buyer quote, ASP,
margin, tags — and the orchestrator mines it into the brief automatically. Or give a product
name, or 1–5 competitor URLs. Say which packaging tier you want (simple / moderate / premium),
or let the engine suggest one from the price band. It runs the phases and shows you REPORT.md.

## The seven buying laws (what the buyer agent runs on)

1. **Pain or pleasure.** Pain has three depths — *latent* (hidden, barely felt), *moderate*
   (searching and not searching), *extreme* (no way back) — and the depth decides the sale.
2. **The future self.** The buyer pictures who they become once they own it; the imagery must
   show that person.
3. **Comfort makes them lazy, and lazy buys.**
4. **Benefits sell, features don't** — every feature is translated into the buyer's life.
5. **The judgement takes seconds** — image, price, design, reviews, experience, one glance.
6. **Packaging is the first verdict** — a bad box convicts the product before it is used.
7. **They only value it when they need it** — plant a memory hook that keeps tempting them back.

Plus lifestyle targeting (the same product sells through different lifestyles to different
people), color psychology (red urgency, blue trust, green nature, gradients fun, black+gold
luxury), and durability instinct (`law.shape_memory`) — the buyer's own graveyard of broken
products teaches them to distrust a thin hinge or a snap-lid on sight, before a single review is
read. All of it is tagged (`law.*`) and scored, not decoration.

## The competition phase (optional, but cheap)

Reads `scout.json` only, plus at most 3 confirmation searches — not a second research pass.
Any page-one listing at **3,500+ reviews** makes the arena `dominated` by rule, no matter what
the agent judges; a dominated or partial arena always gets a deep study (what the leader does
right, where it's weak, how this product coexists or flanks it) — never a reason to give up.
It also sizes the copycat wave: months to the first clone, the price it undercuts at, and a
`share_haircut_pct` the engine uses to re-run the whole Monte-Carlo a second time at reduced
volume. "Profit survives a copycat wave" rides the report as a soft rail — it's always shown,
but only a **high** copycat risk with **no strong moat** turns into a blocking flag.

## The five-year test (built into innovaty)

Every idea — and the product as a whole — is reasoned from its working physics, not its looks:
the real five-year use cycle (how often opened, pressed, flexed; dust, heat, force, weather),
the specific failure modes that follow from it, and the design answer (wall thickness, hinge
type, fit range) chosen because it survives that cycle. Each idea gets a `durability_signal` —
`reassures`, `neutral`, or `warns` — read against the buyer's own durability instinct; a hero
idea can never warn, and the engine rejects one that does. The whole product then goes through
one more honest pass (`durability_review`): the single weakest point, the physics in plain
words, and a verdict — `survives` / `needs_change` / `fails`.

## What comes out

`runs/<slug>/REPORT.md`:

- **The picture in 6 lines** — market anchor, worst complaints, why they buy (pain depth), the
  future self, today's funnel, the memory hook
- **The competition** — arena, brand dominance, copycat risk and the price war after clones,
  the strongest moat (skipped gracefully if the phase didn't run)
- **The winning changes** — each idea with its aspect, cost tier, thumbnail visibility,
  durability signal and genius's ruling; the five-year verdict; plus packaging (in its tier),
  colors, the extra in the box, the title
- **The money** *(computed)* — price, landed, contribution, break-even, P(profit) — with and
  without a clone wave — first sale, and the engine's own feasibility verdict
- **Flags to close first** — each routed to its owner; nothing is a flop
- **Nano Banana prompts** — main image, packaging, lifestyle: paste them into the image model
  and look at your idea

## Built to be cheap

- Each agent gets only the knowledge slices it needs, not the whole base (see `KNOW_FOR` in
  `engine.py`).
- Hard search caps: 8 searches in category mode, 3 per product in focus mode. Competition gets
  at most 3, spent confirming scout's numbers, not re-researching. Gaps are recorded, not chased.
- Competition is the one optional phase — skip it entirely for a faster, cheaper pass; every
  later phase and the report fall back cleanly to the engine's own 3,500-review rule.
- Fast profile is the default; `--no-fast` on `run` buys the thorough pass.
- One subagent per phase, one pass each; the report is the only thing worth reading aloud.
- When a product has many shapes or dimensions, scout anchors everything on the single most
  successful variant instead of burning searches across all of them.

## Commands (all no-API except `run`)

```bash
python3 engine.py demo                      # self-test on synthetic data — try this first
python3 engine.py new runs/x --name "…"     # start a run (add --focus URL… --mine 1 for 1-5 URLs)
                                             # add --packaging simple|moderate|premium, or get asked
python3 engine.py next runs/x               # which phase is next
python3 engine.py prompt runs/x buyer       # the complete prompt for that phase
python3 engine.py check runs/x              # validate + cross-file coherence
python3 engine.py report runs/x             # compute the money and write REPORT.md
python3 engine.py run "product" --buyer "…" # drive all phases via the API (pip install anthropic)
```

`score` and `report` refuse to run on output that fails its contract (a missing field quietly
becomes a zero, and a zero quietly becomes a margin); `--force` overrides when you want to see a
half-finished run.

## Editing it

- **What an agent is asked for** → the contract in `engine.py` (the prompt is generated from the
  same object that validates the answer, so they cannot drift).
- **How an agent thinks** → its `## AGENT: <name>` section in `CLAUDE.md`.
- **The knowledge and the laws** → the `## KNOWLEDGE` section; `KNOW_FOR` in `engine.py` says
  which agent receives which slice.
- **The economics** → `economics()`, `sanity_rails()`, `monte_carlo()` in `engine.py`.

After any edit: `python3 engine.py demo` tells you if a contract now rejects valid output.
