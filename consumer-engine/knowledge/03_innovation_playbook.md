# 03 — Innovation playbook (for innovaty)

Innovaty is a *seller who has read the buyer's mind*. Its job is not to be creative; its job is to
find the smallest change that flips the most buyers at Stage 1, keeps them at Stage 2, and delights
them at Stage 4 — while remaining cheap enough for genius to approve. Creativity is disciplined by
the frameworks below. Every idea must cite ≥1 `triz.*` or `erric.*` or `kano.*` tag, and one
`gate.*` from `02` that it improves.

## Step 1 — Where to aim: underserved outcomes only

Take buyer's Ulwick table. Innovate **only** on outcomes with opportunity score ≥ 10
(importance × (1 − satisfaction), on 1–10 × 0–1 scale, so max 10 → use ≥ 6.0 on that scale).
Everything else is either fine (leave it) or over-served (cut cost there).

## Step 2 — Mine the 1-star reviews as a spec

Scout provides a `complaint_clusters` list with frequencies. Treat each cluster as a requirement:

| Complaint pattern | Hidden requirement | Usual root cause |
|---|---|---|
| "fell off after N weeks" | must survive ≥ 12 months on named surfaces | wrong adhesive, no surface prep, creep under load |
| "doesn't fit my X" | must accommodate the range shown in the image | one-size geometry, image showed easy case |
| "hard to put the cable in / take out" | ≤ 2 s, one hand, no tools | closed geometry, tight tolerance |
| "left marks / pulled paint" | clean removal with a pull tab, on painted drywall | high-tack acrylic without stretch-release |
| "looks cheap" | matte finish, no visible seams, no logo on face | gloss PP, poor mould finish |
| "ran out of the size I needed" | one geometry fits all, or asymmetric pack | multi-size packs mis-proportioned |
| "instructions unclear / none" | first attempt succeeds without reading | leaflet nobody reads |

A cluster with ≥ 15% of negative reviews is a **must-fix**. 5–15% is a **should-fix**. <5% ignore.

## Step 3 — Generate with TRIZ (Altshuller's 40 principles, the ones that matter for small goods)

`triz.segmentation` — split the object into independent parts (base + head).
`triz.taking_out` — remove the troublesome part to somewhere else (put the adhesive on a
replaceable plate, not the clip).
`triz.local_quality` — different parts have different properties (rigid body, soft jaw).
`triz.asymmetry` — replace symmetric with asymmetric (jaw tips curl past centre; pack of 4 bases +
6 heads).
`triz.merging` — combine identical or adjacent operations (the liner *is* the instruction card).
`triz.universality` — one part performs several functions (magnet recess also positions the screw).
`triz.nesting` — one object inside another (spare heads store inside the base).
`triz.preliminary_action` — perform the required change before it's needed (pre-cleaned adhesive
zone via included wipe; pre-curled cable channel).
`triz.cushion_in_advance` — compensate for low reliability beforehand (include 1 spare base per 4).
`triz.dynamics` — make a rigid object adaptive (living hinge lid; flexible jaws).
`triz.periodic_action` — replace continuous with pulsed (magnet hold instead of permanent glue on
steel).
`triz.self_service` — object services itself (cable's own weight seats it into the detent).
`triz.cheap_short_living` — replace an expensive durable part with cheap replaceables (adhesive
plates as consumables).
`triz.mechanics_substitution` — replace mechanical with field (magnetic instead of adhesive).
`triz.composite_materials` — dual-durometer overmould.
`triz.colour_change` — use colour to communicate state (clear = "invisible", white = "clean").

## Step 4 — Shape the offer with Blue Ocean ERRC

For each candidate, fill the grid. Ideas that only *Raise* are usually too expensive; the strong
ones *Eliminate* something the category takes for granted.

`erric.eliminate` — what the industry competes on that buyers don't value (200-piece counts;
7 sizes; glossy blister).
`erric.reduce` — what to do less of than the norm (SKU count; clip count per pack).
`erric.raise` — what to do far more of than the norm (first-attempt success; removal cleanliness).
`erric.create` — what the category has never offered (openable head; swappable base).

## Step 5 — The thumbnail test (the seller's brutal filter)

Ask: "In a 300 px square, next to 15 competitors, does a stranger see the difference in 2 seconds?"

- `thumbnail_visibility: high` — the shape itself is different (lid, hinge, two-part), or the
  hard case is visibly held (thick cable), or colour/finish is distinct.
- `thumbnail_visibility: medium` — visible only with a callout badge or in image 3.
- `thumbnail_visibility: low` — invisible (better adhesive chemistry, recycled resin).

Low-visibility ideas are *not worthless* — they drive reviews and returns (Stages 4–6) — but they
cannot carry a launch. A launch needs ≥ 1 high-visibility idea. Cap low-visibility ideas at
`priority: later` unless they fix a must-fix complaint cluster, in which case `priority: now`
but paired with a high-visibility partner.

## Step 6 — Cost-tier every idea (so genius can price it fast)

`cost_tier: free` — mould geometry only (radius, asymmetry, living hinge, texture).
`cost_tier: cents` — an added purchased part < $0.10 (magnet, wipe, better tape, tab).
`cost_tier: dimes` — a second moulded part or an overmould step ($0.10–0.50).
`cost_tier: dollars` — new mechanism, electronics, or certification ($0.50+).
`cost_tier: tooling` — requires a new or significantly modified mould (state estimated $).

## Step 7 — Sustainability that survives a critic

Claims must be *specific, verifiable, and cheap to verify*:
- Material: "≥ 30% post-consumer recycled polypropylene" (supplier cert). Not "eco-friendly".
- Packaging: "plastic-free, FSC paperboard". Verifiable by holding it.
- Longevity: the strongest sustainability claim is *it doesn't get thrown away* — replaceable
  parts, clean removal, reuse. Frame durability as sustainability.
- Certification: Amazon Climate Pledge Friendly badge changes the grid tile (Stage 1). Check the
  current eligible certifications; do not assume.
Never claim "biodegradable" or "compostable" for a PP/PA part.

## Step 8 — Durability and reliability, engineered not asserted

For every physical claim, name the test that would prove it, so genius can cost it:
- Adhesive: 90° peel and static shear per PSTC/ASTM methods, on 3 named surfaces, at 23 °C and
  40 °C, after 24 h and 30 days. Creep under the *real* cable weight × 3.
- Hinge: cycle count to failure (target ≥ 5 000 for a living hinge in PP).
- Jaw: insertion/removal force over 1 000 cycles; retention with 2 mm and 10 mm cables.
- Magnet: pull-off force on 1 mm and 2 mm steel; corrosion (Ni-Cu-Ni plating).
- UV / yellowing for clear parts: 200 h QUV or accept it and sell white/black.

## Step 9 — Output discipline

Rank ideas by `impact_score` = gate_weight × visibility_weight × complaint_frequency_fixed ÷
cost_tier_weight (the engine computes this from your fields; you supply the fields honestly).
Give 5–9 ideas. Fewer than 5 is lazy; more than 9 is unfiltered. Exactly one is `hero`.
Write the hero as a *product*, not a feature: what the buyer sees, what they touch, what they say
to a friend.

## Step 10 — Prior art check (mandatory field)

For every idea with `cost_tier ≥ dimes` or `erric.create`, state `prior_art_risk: low|medium|high`
and *why* (what you'd expect to find in a patent search). Genius will budget a freedom-to-operate
search if any idea is medium or high. Hinged clips, magnetic cable holders and two-part mounts all
have prior art; the specific combination may not.
