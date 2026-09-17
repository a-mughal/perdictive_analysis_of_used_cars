# Consumer Engine

A product-decision engine for Amazon sellers. Claude Code is the brain; this repository is the body.

Give it a product (a name, a listing, a category link, or a rough idea) and it runs a structured
investigation with five specialised agents, each reasoning from an explicit knowledge base
distilled from the consumer-behaviour, innovation and forecasting literature:

| Agent | Role | Question it answers |
|---|---|---|
| **scout** | Market researcher | What is actually selling, at what price, and what do the 1-star reviews say? |
| **buyer** | The consumer | If I were the person on Amazon right now, would I buy this — and why or why not? |
| **innovaty** | The seller / inventor | What should change so a buyer chooses ours, and stays happy after unboxing? |
| **genius** | Operator / CFO | What does it cost, how long does it take, is it realistic, and what will it sell? |
| **critic** | Red team | Where is the whole plan lying to itself? |

A deterministic Python layer (`engine/`) validates every agent's output against a JSON schema,
scores it, runs a Monte-Carlo profit simulation on genius's ranges, and writes a one-page verdict.
Nothing in Python "thinks"; it only keeps the thinking honest.

## Install into Claude Code

```bash
git clone <this repo> consumer-engine     # or copy the folder
cd consumer-engine
pip install -r requirements.txt
claude                                     # start Claude Code in this directory
```

Claude Code picks up `CLAUDE.md` (the orchestration protocol), `.claude/agents/*.md`
(the five subagents) and `.claude/commands/analyze.md` (the `/analyze` slash command) automatically.

## Run

Inside Claude Code:

```
/analyze Clip-on adjustable monitor privacy screen
/analyze https://www.amazon.com/s?k=cable+clips
/analyze examples/cable_clips_brief.json
```

Or, standalone through the API (no Claude Code needed):

```bash
export ANTHROPIC_API_KEY=...
python -m engine.run_api "magnetic cable clips" --model claude-fable-5-1
```

Every run writes to `runs/<slug>/`:

```
brief.json            what we're analysing (normalised)
scout.json            market facts with sources
buyer.json            the buyer's decision trace, objections, must-haves
innovaty.json         ranked innovations with mechanism, cost tier, thumbnail visibility
genius.json           BOM, tooling, timeline, sales forecast ranges, risks
critic.json           red-team findings and required fixes
scores.json           deterministic scores + Monte-Carlo output
VERDICT.md            the one page a human reads
```

## Smoke test (no API needed)

```bash
./smoke_test.sh          # validates, scores and renders a verdict on synthetic agent output
```

`examples/fixture_run/` contains deliberately shaped agent JSON so you can see the scoring and
Monte-Carlo behave before spending credits. Install `jsonschema` for full contract validation;
without it the validator falls back to required-key and range-rule checks only.

## Validate / score by hand

```bash
python -m engine.engine validate runs/cable-clips
python -m engine.engine score    runs/cable-clips
python -m engine.engine verdict  runs/cable-clips
```

## Design principles

1. **Evidence before opinion.** scout runs first; every other agent must cite scout facts or
   knowledge-base frameworks. Unsupported claims are flagged by critic and down-weighted in scoring.
2. **Innovation must be photographable.** Innovaty scores every idea on `thumbnail_visibility`.
   On a $8 commodity, an improvement a buyer can't see in a 300-px image does not exist.
3. **Ranges, not points.** Genius never outputs a single number for cost, time or sales — always
   low / base / high with the assumption behind each. The Monte-Carlo layer turns that into a
   probability of profit.
4. **The critic can veto.** A verdict of `GO` requires critic to find no unresolved fatal flaw.
5. **Nothing is hard-coded that changes.** FBA fees, referral rates, freight rates, tariffs and
   ad costs are inputs that scout fetches fresh. The engine ships with placeholders, not facts.

## Layout

```
CLAUDE.md                 orchestration protocol (the brain's standing orders)
.claude/agents/           scout, buyer, innovaty, genius, critic
.claude/commands/         /analyze
knowledge/                the "books": psychology, Amazon journey, innovation, economics
schemas/                  JSON contracts each agent must satisfy
engine/                   validation, scoring, Monte-Carlo, verdict rendering, API runner
examples/                 a worked brief (cable clips) + fixture_run for the smoke test
smoke_test.sh             end-to-end check of the skeleton without API calls
runs/                     outputs, one folder per product
```
