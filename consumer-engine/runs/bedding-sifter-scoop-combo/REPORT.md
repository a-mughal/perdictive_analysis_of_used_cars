# Small-Animal Habitat Bedding Sifter & Waste Scoop Combo — **FIX-FIRST**
*2 flag(s) to close, each routed to its owner — nothing here kills the product*  ·  critic: flags_to_fix  ·  2026-09-21  ·  `bedding-sifter-scoop-combo`

## The picture in 6 lines
- **Market:** term **hamster litter scoop sifter**, page-1 anchor **$10.17** · winning variant: Plastic 2-to-3-piece sifter/scoop combo set (a fine-mesh si…
- **Worst complaints:** The scoop's mesh/holes are sized for clumping cat litter, s… (40%); The plastic scoop or sifter body feels flimsy, clumps stick… (25%)
- **Why they buy:** pain (**moderate** pain) · top unmet need: I need a mesh gauge actually sized for loose paper/aspen bedding fines, not clumping cat…
- **Future self:** I picture myself doing the Sunday-night cage clean in under a minute: one scoop through the bedding, the tray catches the wet clumps and droppings, the clean fluffy bedd…
- **Buyer today:** click 30% → cart 35% → buy 55% · pays up to **$20.00** with a visible reason
- **Memory hook:** The image of bedding fines raining cleanly through the mesh while a wet clump stays trapped - that specific before/after moment is what I'll keep picturing the next time…

## The winning changes
- ★ **See-Through Sift Window** [pain_removal] — You can actually watch the bedding fall through the side while the gross clump just sits there on t… · dimes · thumbnail high · stretch · v2
- **High-Contrast Dual-Color Fine Mesh** [eye_catching] — You can literally see how fine the holes are from the product photo — it doesn't look like just ano… · cents · thumbnail high · realistic · v1
- **Molded-In 3mm Gauge Callout** [design] — It actually says 3mm right on the tray, molded in — not some sticker that's going to peel off in a… · free · thumbnail medium · realistic · v1
- **Compact Cage-Fit Scoop Head & Contoured Short Handle** [comfort] — It actually fits through the cage door without me wrestling it in sideways like the cat scoop did. · tooling · thumbnail medium · realistic · v1
- **Ribbed Non-Stick Mesh Underside + Reinforced Frame** [durability] — One little tap and the clump just drops off — it doesn't stick and smear across the mesh like the l… · cents · thumbnail low · realistic · v1
- **Durable Molded Depth Marks** [convenience] — The fill-level marks are actually molded in, not printed on, so they're not rubbing off after a mon… · cents · thumbnail low · unrealistic · v2
- **Packaging** — A small die-cut window in the box lid sits directly over the mesh tray, so before the lid is even lifted the… · dimes
- **Colors** — product: Sage green tray, scoop and handle accents — a soft, natural pet-care tone that… · main-image anchor: Amazon requires a pure white background on the primary listing image, so the an…
- **Extra in the box** — A second, narrower snap-in 3mm mesh insert sized for tight…: Answers fear rank 3 (does this actually fit small/awkward spaces) and pre-empts… · dimes
- **Title (first 60):** `Hamster Bedding Sifter Scoop Combo - See-Through 3mm Mesh`

## The money  *(computed, not estimated)*
- Price **$18.99** · landed $4.44 (23.4%) · contribution **$1.60/unit (8.4%)**
- Break-even **10,551 units** (~>12 months) · P(profit 12 m) **0%** · year-1 P50 $-18,675 (P10 $-26,535)
- First sale in 46 wk (33 wk–55 wk) · rails 4/8 — broken: contribution >= 25% of price; contribution >= 15% of price (hard floor); P(profit > 0 in 12 months) >= 60%; first sale within 9 months at high

## Flags to close first  *(routed to their owners — nothing here is a flop)*
- [genius] broken rail: contribution >= 15% of price (hard floor)
- [genius] broken rail: P(profit > 0 in 12 months) >= 60%

## Watch list
- [buyer] Amazon product/review pages were blocked this session, so scout's price_ladder and competitors[] entirely come from Walmart listings (F3-F6) -- the true Amazon combo-set comparators (tafit, Ilofdsn, Niteangel, BFLCTTBD, Mollcouver named in F1/F2) still have no price or rating data at all this run. Buyer's anchoring judgement ('The row I see runs $4.29-$10.17...', anchor_seen_usd: 10.17, unchanged from the prior pass) treats this Walmart-sourced ladder as if it were the literal Amazon grid row, without flagging the marketplace mismatch. That figure still feeds gate.price_vs_anchor / kahneman.anchoring reasoning and, downstream, genius's price_usd rationale ('Buyer's stated band is $14.39-$21.59... buyer.price_psychology names a $12 ceiling'). — fix: Scout should tag each competitor entry with its marketplace and state explicitly that no Amazon-native price anchor exists this run. Buyer should treat the $4.29-$10.17/$10.17 figures as a directional, non-Amazon proxy with wider stated uncertainty rather than 'the row I see', until Amazon data is retrievable.
- [genius] genius.premortem[3] (packaging tier-line jump) still assigns 30% probability to the upgraded die-cut box + shaped inner tray pushing the packed product over the 8oz small-standard tier line -- genius's own top-named packaging risk. But economics.fba_fee_usd (low 2.90 / base 3.45 / high 4.15) only widens the same-tier estimate by roughly +20%; there is still no next-tier fee scenario at the high end, so the Monte-Carlo input doesn't carry the risk genius itself flags as the most consequential packaging failure mode. Unchanged from the prior critic pass. — fix: Either fold an explicit tier-jump scenario into the high end of fba_fee_usd (price the next FBA size tier's fee), or state clearly in the assumption that the current range assumes the pin-gauge/scale-check mitigation succeeds and that a tier-jump remains an unmodeled tail risk.
- [innovaty] The 'second, narrower snap-in 3mm mesh insert for tight corners' plus a replacement-SKU card is still introduced outside the formal ideas[] array -- no idea_id, no kano_class, no prior_art_risk, no thumbnail_visibility, only an ad hoc 'dimes' cost tier -- and it still does not appear in version_plan.v1_now or v2_later. Neither version's BOM in genius.json prices this extra mesh insert or card. Unchanged from the prior pass. — fix: Give it an idea_id, run it through the same TRIZ/ERRC/prior-art/thumbnail-test discipline as I1-I6, and place it explicitly in v1_now or v2_later so genius can cost it in the BOM (or drop it as aspirational scope, not actual v1 content).
- [innovaty] I1 and I3 (both list N4 in improves_needs, N4 = 'real proof it was tested on small-animal bedding', severity 4) still target a need below the innovation playbook's severity>=5 funding threshold, while target_spec.needs_targeted correctly lists only N1-N3. I1 is a 'dimes' cost-tier idea; its primary justification is N1 (severity 8), but N4 riding along uncosted-and-unflagged in the same field is an internal inconsistency between what target_spec claims is funded and what the ideas claim to serve. Unchanged from the prior pass. — fix: Remove N4 from I1's and I3's improves_needs, or add a note in target_spec that N4 is addressed incidentally at zero marginal cost as a side effect, not as a funded target.

## Next step
Close the flags above, then order samples of v1 (I2, I3, I4, I5).

## Nano Banana prompts
**Main listing image**
```
Studio product photograph of a sage-green plastic pet-bedding sifter tray and matching waste scoop, shot from slightly above at a three-quarter angle tilted downward so the mesh floor of the tray is visible: pale beige paper and aspen bedding fines are frozen mid-fall through the crisp white fine-mesh grid that contrasts sharply against the sage-green frame, while a single dark, moist-looking bedding clump rests visibly retained on top of the mesh; the tray rim shows embossed raised lettering reading '3MM BEDDING MESH' catching a soft raking highlight; background is pure seamless white (Amazon primary-image compliant, RGB 255,255,255, no gradient, no props) with soft diffused studio lighting and a faint natural contact shadow beneath the tray, no shadows harsh enough to hide detail, no text overlays, no logos, no side viewing window or transparent panel anywhere on the tray body, clean commercial e-commerce product photography, high resolution.
```
**Packaging**
```
Overhead unboxing photograph of a matte sage-green and cream cardboard box with a small die-cut oval window in the lid that reveals the real white 3mm mesh tray underneath even before opening; a pair of hands is mid-motion lifting the open lid away, revealing the sage-green sifter tray and scoop nested snugly in a shaped cardboard inner tray with zero rattle or loose fill, alongside a small printed insert card reading '3mm, built for bedding - not cat litter' resting beside the tray; warm soft natural window light from the upper left, a plain light wood tabletop surface, shallow depth of field with the box and tray in sharp focus, cozy home setting, no clinical white background, photorealistic product photography.
```
**Lifestyle — the buyer's future self**
```
Warm, softly lit evening photograph inside a cozy home: a person's hands are gently sifting fresh paper bedding over an open-top hamster cage using the sage-green sifter tray and scoop, clean fluffy bedding visibly falling back into the cage while a small clump sits caught in the tray; a curious hamster is visible nearby on the cage's clean bedding, undisturbed and alert, not startled; the setting is a lived-in bedroom or living room corner with warm lamp light, wood shelving, and soft shadows, nothing sterile or clinical, no white bathroom tile, no cat imagery anywhere in frame; candid documentary-style photography, slightly shallow depth of field, camera at a natural eye-level angle looking down at the cage and hands, evoking a calm, satisfied one-minute routine rather than a chore.
```
