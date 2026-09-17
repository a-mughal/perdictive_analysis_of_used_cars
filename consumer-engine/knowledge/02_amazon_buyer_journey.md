# 02 — The Amazon buyer journey, second by second

The general psychology in `01` applied to the specific machine the buyer is standing in front of.
The buyer agent must walk this path *in the first person*, in real time, and record what it feels
at each gate. The innovaty agent must map every idea onto the gate it improves.

## Stage 0 — The hiring moment (before Amazon opens)

Something happened. A cable fell. A desk arrived. A call showed the mess. Record:
- `trigger` — the event (jtbd.hiring_moment)
- `fired_solution` — what they used until now and why it failed (jtbd.firing)
- `urgency` — today / this week / someday. Urgency lowers price sensitivity and raises Prime bias.
- `search_term` — the literal words typed. This decides which grid they see and therefore which
  anchors, decoys and competitors exist for them. **Different search terms are different markets.**

## Stage 1 — The grid (≈ 3–8 seconds)

The buyer sees ~16 tiles above the fold on desktop, ~4 on mobile. Roughly 60%+ of Amazon traffic
is mobile. Each tile: image, first ~60 characters of title, stars + count, price, Prime badge,
sometimes a "bought in past month" line.

Gates, in the order the eye hits them:

1. `gate.image_orientation` — *What is it and how big?* If unclear in 300 px, the tile is skipped.
2. `gate.image_fit` — *Will it work with MY thing?* The buyer mentally superimposes the product on
   their own cable / desk / monitor. Kahneman.wysiati: if the image doesn't show their case, they
   assume it doesn't fit. Show the hardest case (thickest cable, textured surface) in the main image.
3. `gate.social_proof` — stars ≥ 4.3 and count ≥ ~300 to be a "safe" click. Below 20 reviews, only
   `rogers.innovators` click.
4. `gate.price_vs_anchor` — price relative to the row median. ≤1.3× passes silently; 1.3–2× needs a
   visible reason in the image; >2× is a different mental category.
5. `gate.title_scan` — first 3–5 words confirm the search term and one differentiator. Everything
   after ~60 characters is invisible on mobile.

Output of stage 1: **click-through**. This is the single KPI that predicts revenue. Every
innovation must be scored on whether it moves CTR (i.e., is visible at this stage).

## Stage 2 — The listing (≈ 20–90 seconds)

Now System 2 is half-awake. The buyer swipes images first, reads bullets second, price third.

- `gate.image_2_to_6` — the image carousel is the real product page. Expected sequence that
  converts: (2) size / scale with hand or ruler, (3) the hard case working, (4) install in 3 steps,
  (5) what's in the box, (6) lifestyle in a room like theirs. Missing (3) is the #1 conversion leak.
- `gate.bullets` — read as a *checklist of fears*, not features. Bullets that pre-empt the 1-star
  reviews ("will not hold on textured walls") convert better than bullets that boast.
- `gate.reviews_negative_first` — a large share of buyers sort by "most recent" or filter 1-star
  before buying. They are looking for the *pattern* of failure, not the count. Three 1-stars saying
  "fell off" is fatal; three saying different things is noise.
- `gate.reviews_with_photos` — weighted 5–10× (kahneman.availability). One photo of paint damage
  ends the sale.
- `gate.qna` — used for fit questions the images didn't answer. Every Q&A is a missing image.
- `gate.variations` — every dropdown loses buyers (schwartz.overload, underhill.butt_brush).
- `gate.brand_trust` — unfamiliar brand + safety-adjacent product (adhesive on furniture, anything
  electrical) triggers System 2 fully. Named components (cialdini.authority) and an honest
  limitation (cialdini.reciprocity) defuse it.

Output of stage 2: **add-to-cart rate**.

## Stage 3 — The hesitation (seconds to days)

Cart abandonment is where the buyer imagines regret (kahneman.loss_aversion; ariely.pain_of_paying):
- "What if it doesn't fit?" → return-policy salience
- "Is there a better one?" → they go back to the grid; you must win on second viewing too
- "Do I really need this?" → urgency from Stage 0 decides

## Stage 4 — Delivery and first 60 seconds

`kano.delighter` and `post.review_trigger` live here. The box, the smell, the instruction card,
the first install attempt. If install fails on first try (surface not cleaned, adhesive not
cured), the product is judged broken — not the user. **Design the first attempt to succeed.**

## Stage 5 — The failure moment (weeks to months)

Adhesive products fail at 2–12 weeks; the review is written *then*, long after the honeymoon.
Amazon's review request email lands ~1–2 weeks after delivery: before most failures, after most
delights. A product that survives 3 weeks harvests reviews from the delight window.

## Stage 6 — Removal / disposal

`kahneman.peak_end`: the last memory is the removal. Paint damage at removal = 1-star two years
later, and a warning to friends. Clean removal is a *review* feature, not an engineering nicety.

---

## Metrics the engine cares about, and which stage owns them

| Metric | Stage | Moved by |
|---|---|---|
| Impressions | 0 | search term choice, ads |
| CTR | 1 | main image, price, review count |
| Conversion | 2–3 | images 2–6, bullets, negative-review pattern |
| Return rate | 4 | fit accuracy, first-attempt success |
| Review rate & rating | 4–5 | delight in first 60 s, survival past week 3 |
| Repeat / referral | 6 | clean removal, spare parts |

## Buyer agent instructions

Walk stages 0–6 in the first person for the *target buyer* in `brief.json`. At every gate, record:
`what_i_see`, `what_i_think`, `what_i_feel`, `pass|hesitate|leave`, `tag`. Then list, in priority
order, the fears the listing must answer and the must-haves the product must have. Then score the
top-8 desired outcomes (ulwick) as importance × (1 − satisfaction), using scout's review mining
for the satisfaction number.
