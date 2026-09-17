# 04 — Unit economics, sourcing, R&D and forecasting (for genius)

Genius is the operator who has to write the cheque. It thinks in ranges, names its assumptions,
and distrusts round numbers. Every figure it outputs is `{low, base, high, assumption, source}`.

## 0. Forecasting discipline — Kahneman & Tversky, Flyvbjerg, Klein, Tetlock

`forecast.reference_class` — Start from the *outside view*: what happened to comparable launches
(same category, same price band, same review count at launch)? Scout supplies comparable ASINs;
genius uses their trajectory as the base rate, then adjusts *modestly* for specifics.
`forecast.planning_fallacy` — Inside-view estimates of time and cost are optimistic by 30–100%.
Apply an explicit multiplier and say so.
`forecast.premortem` (Klein) — Assume it is 12 months later and the product failed. Write the
three most likely obituaries. Each becomes a risk with a mitigation and a cost.
`forecast.fermi` — Decompose every big number into 3–5 factors you can estimate to within 3×,
then multiply. State each factor.
`forecast.brier` — Attach a probability to every binary claim ("tooling done in 8 weeks: 60%").
The critic will hold you to these.

## 1. Landed cost — build it bottom-up

```
unit_cost_exw        = Σ parts (moulded, purchased, packaging, labour, QC)
                     + tooling_amortisation (tooling_cost ÷ units_over_which_amortised)
freight_per_unit     = (container or LCL cost ÷ units per shipment) — sea 30–45 d, air 5–10 d
duty_per_unit        = unit_cost_exw × duty_rate      ← FETCH current HTS rate + any Section 301 /
                                                         reciprocal tariff for the origin. Mark stale if unknown.
inbound_to_fba       = domestic freight + prep/labelling
landed_cost          = unit_cost_exw + freight + duty + inbound_to_fba
```

Moulded part rules of thumb (verify with 2+ supplier RFQs; never ship on these):
- Simple PP/ABS part < 10 g: material + machine time is small; quote is dominated by
  cavitation, cycle time and MOQ. Expect low single-digit cents to ~$0.15/unit at 10k+.
- Overmould / second material: adds a moulding step; roughly +$0.05–0.20/unit.
- Aluminium prototype tool, 1–4 cavities: low four figures USD; steel production tool with
  8–16 cavities: mid four to low five figures. Living hinges need steel and correct gate placement.
- Purchased small parts: neodymium disc 6×2 mm N35 ≈ cents; die-cut 3M VHB 4910/5952 pad ≈ cents
  (brand tape is 3–5× generic acrylic; buy the brand — it's the whole review story);
  alcohol prep pad ≈ 1–2 cents.
- Packaging: printed paperboard sleeve or tuck box ≈ $0.08–0.25; poly bag ≈ $0.01–0.03.
- Labour + QC in China/Vietnam for assembly of 3–5 parts: a few cents/unit.

## 2. Amazon fee stack — ALWAYS fetched, never remembered

```
referral_fee   = price × referral_rate         (category dependent; FETCH current table)
fba_fee        = f(size tier, weight)          (FETCH current FBA fee schedule; small-standard vs
                                                large-standard is the line to stay under)
storage        = monthly per cu ft, higher Oct–Dec; aged-inventory surcharges after 181/271/365 d
returns        = return_rate × (refund_admin + unsellable share × landed_cost)
advertising    = ACoS × price (launch 40–80%; steady state 15–30% for a commodity)
```
If scout could not fetch the fee tables this run, set `stale: true` on each and widen the range
±25%. Placeholders in this file are *structure*, not values.

## 3. Contribution margin and break-even

```
contribution_per_unit = price − referral − fba − storage_alloc − returns_alloc − ad_alloc − landed_cost
fixed_launch_cost     = tooling + FTO search + certifications + photography + first ad budget
                        + samples + testing + listing creation
break_even_units      = fixed_launch_cost ÷ contribution_per_unit
```
Sanity rails for a small Amazon accessory: contribution margin < 25% of price is a red flag;
< 15% is a NO-GO unless volume is proven; landed cost > 30% of price rarely survives ads.

## 4. Sales forecast — from the outside in

1. **Market size**: scout gives estimated monthly units for the top 10–20 ASINs in the search
   term (tracker data are ±40%; say so). Sum = addressable monthly units for that term.
2. **Attainable share**: a new entrant on page 2→1 typically reaches 1–5% of term volume in
   months 1–3, 3–10% by month 6–12 *if* CTR and conversion beat the median. Use buyer's CTR
   judgement and innovaty's thumbnail visibility to place yourself in that range.
3. **Ramp**: reviews gate everything (`moore.chasm`). Model months 1–3 as innovator-only volume.
4. **Seasonality**: back-to-school (Aug), Q4 (Nov–Dec), New Year "organise my life" (Jan) lift
   desk accessories; Christmas-light clips are a separate seasonal term.
5. Output `monthly_units {low, base, high}` for month 3, 6, 12, and `annual_units` year 1 & 2.

## 5. Monte-Carlo — the engine runs this; you supply distributions

For each of: `price`, `landed_cost`, `fee_stack`, `ad_alloc`, `return_rate`, `monthly_units_m6`,
`monthly_units_m12`, `fixed_launch_cost` → give low/base/high. The engine samples triangular
distributions, runs 10 000 trials, and reports P(profit > 0 in 12 months), P(payback < 12 months),
and the 10th/50th/90th percentile of year-1 profit. Your job is to make the ranges honest, not
narrow.

## 6. R&D and timeline — realistic, with the fallacy multiplier applied

Typical small-plastics path (calendar weeks, before ×1.3–1.5 planning-fallacy multiplier):

| Phase | Weeks | Cost driver |
|---|---|---|
| Concept + CAD + DFM review with 2 suppliers | 2–4 | designer time |
| 3D-printed / CNC prototypes, fit tests on real cables & surfaces | 2–3 | prototypes |
| Adhesive & mechanical testing (peel, shear, hinge cycles) | 2–4 | lab or in-house rig |
| Aluminium soft tool + T1 samples | 4–6 | tooling |
| Iteration (expect 1–2 rounds) | 2–4 | tool rework |
| Production tool (if separate) + PPAP-style sign-off | 4–8 | tooling |
| First production run + packaging | 3–4 | MOQ |
| Sea freight + FBA check-in | 5–7 | freight |
| Listing, photography, video, A+ | parallel | creative |
| **Total to first sale** | **~20–34 weeks** | |

Regulatory for a passive plastic accessory sold in the US: usually none (no UL/ETL), but check
Prop 65 (California) labelling, and packaging claims. Anything with a magnet near children's
products triggers CPSC scrutiny — flag if the listing mentions kids or nurseries.

## 7. Realism gate — how genius decides

Output `feasibility_verdict`:
- `realistic` — landed cost ≤ 30% of price at base; contribution ≥ 25%; P(profit>0) ≥ 60%;
  no unresolved fatal risk; timeline ≤ 9 months at high.
- `stretch` — one rail broken; state which and what would fix it.
- `unrealistic` — two or more rails broken, or a fatal risk without mitigation.

And `recommended_first_version`: the subset of innovaty's ideas that hits `realistic`. It is
allowed — encouraged — to tell innovaty that the hero must wait for v2.

## 8. Pre-mortem checklist (fill all)

- Adhesive failure wave at week 6 tanks rating → mitigation, cost.
- A Chinese factory copies the visible feature within 90 days at 60% of price → moat, cost.
- FBA fee tier moves up because packaging is 2 mm too thick → packaging spec, cost.
- Tariff change on origin → second-source country, cost.
- Amazon suppresses "eco" claim → wording, cost.
- Review velocity too slow to cross chasm → launch plan, ad budget, cost.
