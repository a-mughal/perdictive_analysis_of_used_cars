# ROCKBROS Bike Repair Kit Cycling Tubeless Tire Repair Kit for Mountain Bike and Road Bicycle — **FIX-FIRST**
*2 flag(s) to close, each routed to its owner — nothing here kills the product*  ·  critic: flags_to_fix  ·  2026-09-21  ·  `rockbros-tubeless-repair-kit`

## The picture in 6 lines
- **Market:** term **tubeless tire plug kit bike**, page-1 anchor **$16.00** · winning variant: Single hand tool with 3 metal insertion/plug pins plus 5 ru…
- **Worst complaints:** Rubber plug/strip material sitting unused in a saddle bag d… (35%); Sealant-dependent plug systems fail to hold when the tire's… (25%); Premium protected-plug tools are seen as expensive relative… (15%)
- **Why they buy:** pain (**moderate** pain) · top unmet need: I need proof - real ride reports, not just install photos - that a plug holds for actual…
- **Future self:** I picture myself on a gravel climb next month, tire hisses flat, I flip the bike over, flatten the puncture, jam a strip in, two pumps of CO2, and I'm rolling again befo…
- **Buyer today:** click 30% → cart 45% → buy 55% · pays up to **$28.00** with a visible reason
- **Memory hook:** The line 'no glue, no wait, ride away in minutes' - the promise that I'm rolling again before my friends even notice I stopped - paired with how little it weighs, which…

## The winning changes
- ★ **Slotted Hard-Case Kit Tin** [packaging] — It comes in this little case where everything has its own slot — nothing rattles around and the str… · tooling · thumbnail high · realistic · v1
- **Foil-Sealed Strip Freshness Pouch** [durability] — The strips come sealed in their own little pouch so they're not just sitting exposed in my bag goin… · cents · thumbnail low · realistic · v2
- **In-Box QR Proof Card (No-Sealant + Mileage Test)** [experience] — There's a card in the box that actually shows the plug holding air on a bone-dry tire, so I don't f… · cents · thumbnail low · realistic · v2
- **Matte Gunmetal Anodizing + Red Pull-Ring Accent** [color] — It actually looks like a real tool, not some toy — matte black with a little red ring so I can spot… · cents · thumbnail high · realistic · v2
- **Integrated Valve-Core Notch + Numbered Pins** [convenience] — The tool doubles as a valve-core remover and the pins are numbered, so I'm not fumbling to remember… · free · thumbnail medium · stretch · v2
- **Cross-Width Validated Single Strip Geometry** [reliability] — Same kit worked on my buddy's skinny road tubeless and my wide MTB tire — I didn't have to guess if… · free · thumbnail low · realistic · v2
- **Packaging** — In the first ten seconds the buyer lifts a slim hinged lid instead of tearing open a poly bag — the packaging… · tooling
- **Colors** — product: Brand-direction target: matte gunmetal-black anodized aluminum body with a smal… · main-image anchor: A warm sandstone-to-charcoal gradient background rather than stark clinical whi…
- **Extra in the box** — Not a v1 launch feature — this is a v2_later fast-follow co…: Once fast-followed alongside I2, this directly answers the fear that strips deg… · cents
- **Title (first 60):** `ROCKBROS Tubeless Tire Plug Kit, No-Glue Repair, Hard Case`

## The money  *(computed, not estimated)*
- Price **$16.99** · landed $3.27 (19.2%) · contribution **$1.17/unit (6.9%)**
- Break-even **10,308 units** (~>12 months) · P(profit 12 m) **0%** · year-1 P50 $-15,211 (P10 $-23,406)
- First sale in 31 wk (24 wk–38 wk) · rails 5/8 — broken: contribution >= 25% of price; contribution >= 15% of price (hard floor); P(profit > 0 in 12 months) >= 60%

## Flags to close first  *(routed to their owners — nothing here is a flop)*
- [genius] broken rail: contribution >= 15% of price (hard floor)
- [genius] broken rail: P(profit > 0 in 12 months) >= 60%

## Watch list
- [innovaty] The near-zero-cost printed step insert added in this pass to fix what_i_cut's gap ('sits right where the buyer's eye lands' per packaging.unboxing_moment) is not depicted in any of the three image_prompts or the 'what's in the box' listing image brief. The packaging image_prompt describes the case open showing only the pins and strips, with no mention of the step insert/slip card at all — so the one instructional aid v1 actually ships with is invisible in every image meant to prove it exists, undercutting the fix's own rationale (post.review_trigger / 'first attempt succeeds unread' only works if the buyer can see or find the guide, and image #3 is the number-one conversion leak per the buyer-journey gates). — fix: Add the printed step insert (lid print or slip card) to the packaging image_prompt and to image_briefs_2_to_4's 'what's in the box' brief, and resolve the still-open either/or ('printed on the inside of the case lid OR a thin slip card') into one concrete implementation so genius can decide whether it needs its own foam slot.
- [innovaty] The sustainability claim was correctly softened this pass to compare against 'a typical poly-bag baseline for this product category' rather than asserting anything about this ASIN's own prior packaging — that fixes the Amazon-suppression risk on the specific-ASIN framing. But the category-baseline premise itself is still attributed to 'scout's observation of a rival tile (the Genuine Innovations kit)', and scout's actual competitor entry never mentions packaging format at all — it only describes the product photo as 'a plastic-handled plug tool shown beside a flat sheet of rubber plug strips' (F4-adjacent). A flat sheet visible in a product photo is not evidence of poly-bag retail packaging. The 'typical poly-bag baseline for this product category' is still an inference dressed as a scout-sourced observation, just one level removed from the original (now-fixed) ASIN-specific version of the same problem. — fix: Either get scout to source an actual competitor packaging-format fact (a listing photo or description that shows the retail packaging, not just the product), or reword the claim as innovaty's own working assumption about category norms rather than something 'scout observed'.
- [genius] Unresolved from the first pass: the BOM line for the aluminum tool body still cites '~48g per F3' as the tool body's own weight. F3 actually states the whole kit (3 plug tools + 5 rubber strips) weighs about 48g total, not the metal body alone — and F3 describes a kit with '3 plug tools' (plural separate tools), which may not even be the same physical shape as this ASIN's single tool with 3 integrated pins (scout's own variant_chosen flags this ambiguity). unit_weight_g (93g for v1_hero_case) is built on top of this mislabeled figure, and it directly feeds premortem #3 (packaging crossing the FBA size-tier line), one of the two 'major' impact premortem items. — fix: Re-derive the tool body's own weight as a fraction of F3's 48g kit total (strips are a small share of it), or get an actual supplier weight before locking case/foam dimensions, since this number is load-bearing for the size-tier risk genius itself is worried about.
- [genius] Unresolved from the first pass: several timeline ranges are still narrower than the brief's ±30% floor for uncertain estimates even after the 1.35x planning-fallacy multiplier — phase 2 (prototypes/compliance testing) ≈±20.6%, phase 3 (soft tooling/T1) ≈±20%, phase 5 (production run) ≈±14.4%, phase 6 (freight/FBA check-in) ≈±16.7%, and the rolled-up weeks_to_first_sale ≈±21.7%. These are exactly the phases most exposed to genius's own flagged risks: a first-time compliance/aging test regime with this supplier, soft tooling for a new case, and a 22%-probability 'fatal' tariff/HTS premortem item sitting right next to the tooling and freight phases. — fix: Widen phases 2, 3, 5 and 6 (and the rolled-up total) to at least ±30% around base, reflecting the tariff/HTS and first-time-compliance uncertainty already named in the premortem.

## Next step
Close the flags above, then order samples of v1 (I1).

## Nano Banana prompts
**Main listing image**
```
A macro product photograph of a compact silver-toned raw-anodized aluminum bike tire plug tool with three integrated pins, shown open beside its slim charcoal hard case whose molded foam insert holds the tool in its own slot, three plain unnumbered chrome-tipped steel pins in their own slots, and five ordinary dark-red rubber bacon strips resting in their own foam compartment exactly as they ship today — nothing foil-wrapped, no printed card; the open case with its organized slotted foam layout is the single hero visual, arranged in a tidy three-quarter overhead flat-lay on a warm sandstone-to-charcoal gradient background with soft diffused studio lighting that puts a gentle highlight along the foam texture and the tool's brushed metal finish, sharp focus throughout, no text or logos overlaid, photorealistic e-commerce product photography.
```
**Packaging**
```
A close-up lifestyle photograph of a pair of dust-smudged cyclist's hands lifting the hinged lid off a slim charcoal hard case, revealing three plain unnumbered chrome pins and five dark-red rubber strips seated snugly in individual molded foam slots with zero rattle, exactly as the kit ships today; the case rests on a weathered wooden tailgate or a gravel-dusted bike top-tube, warm early-morning side light raking across the foam texture, shallow depth of field blurring a gravel bike frame in the background, documentary-style product-in-use photography, no visible text or brand logos legible.
```
**Lifestyle — the buyer's future self**
```
A candid outdoor action-documentary photograph of a dusty, self-sufficient gravel cyclist crouched beside their bike on a sun-lit dirt shoulder, tire laid flat toward camera, one hand pressing the plug tool in its current stock finish into the punctured tread while a small CO2 inflator rests ready on the ground nearby; dust and trail grit visible on the rider's forearms and gloves, golden-hour side light, shallow depth of field with a blurred gravel road and hills behind, no other people in frame, confident unhurried body language, natural color grade, no text overlays.
```
