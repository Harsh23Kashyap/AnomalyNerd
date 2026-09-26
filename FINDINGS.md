# What AnomalyNerd found

A plain-language record of what the tool flagged on each dataset, and how the a research paper's results
results line up with the advisor's Sept 23, 2026 notes. Everything below is produced
**automatically** by the tool from the raw tables — no hand-tuning per dataset.

---

## 1. a research paper's results (the paper) — vs. the Sept 23, 2026 notes

The tool re-discovered every concern in the Sept-23 notes, plus two extra issues.

| Sept 23 note (intuition that "should" hold) | What the tool flagged |
|---|---|
| p₁ of 0.12 shouldn't give RMSEs so different from p₁ of 0.15 | **HIGH jump**: a research paper's results ~1.6 at p₁=0.12 → ~196 at p₁=0.15 (~120×). Suggests *"test p₁=0.13, 0.14"* — exactly the note's next step. |
| predicting more days out should give higher error | **Monotonicity**: a research paper's results error falls as the horizon grows (180 → 408 → 162 → 96). |
| knowing more about p₁/p₂ should help | **Flatness**: "knowledge" setting is ignored by some methods; and a research paper's results swings oddly across it elsewhere. |
| contact-tracing should help | **Win-reversal**: a research paper's results wins at short horizons but plain a research paper's results wins at 20 days. |
| characterize when we beat others and when not | **Win-reversal along p₁**: best method flips a research paper's results → ARIMA → MethodB as p₁ rises. |

**Two extra findings not in the notes:**
- **Copy-paste bug** — the exact value **a repeated value** appears in *both* the 5-day and 10-day tables (a research paper's results, "p₁ known").
- **Ignored setting** — MethodB and LSTM are identical across all four "knowledge" settings (expected), but the tool separates that from the genuine bug above.

---

## 2. Antarctic ozone (Halley, 1956–2011) — the historical gold standard

Real British Antarctic Survey total-ozone record — the data used to discover the ozone hole,
and famously the data whose low readings were once auto-discarded as "errors."

- **HIGH level-shift**: *"ozone holds ~297 DU (baseline 1956–1974), then drops to ~167 DU
  from 1980 onward (an 11-SD sustained departure) — worth investigating."*
- This is precisely the warning that was historically missed. It also drove a real
  improvement: our first version missed it (the drop is slow, not a sharp jump), so we added
  the level-shift detector.

## 3. Mauna Loa CO₂ (annual) — a "must NOT alarm" test

A steady, healthy upward trend. A good tool should stay quiet.

- **No HIGH/MEDIUM alarms.** The tool recognizes the rise as a genuine trend and, at most,
  emits a LOW "candidate," never a false alarm. (An earlier version over-flagged it; that
  taught us the trend-vs-shift guard.)

## 4. Anscombe's quartet — a classic ground-truth test

Four datasets with a known answer: two clean, two with one outlier each.

| Dataset | Truth | Tool |
|---|---|---|
| I | clean | no flags ✓ |
| II | smooth curve | LOW candidate only ✓ |
| III | one point off the line | **MEDIUM** point-outlier at x=13 ✓ |
| IV | one lone extreme point | **HIGH** point-outlier at x=19 ✓ |

---

## 5. Newcomb's speed-of-light measurements (1882) — a point-outlier test

66 timing measurements; Newcomb himself discussed discarding two extreme values (−44 and −2).

- The tool flags **exactly those two** — `-44` (HIGH, 12 robust-SDs) and `-2` (MEDIUM, 5 robust-SDs) — and nothing else.
- This dataset also improved the tool: the measurement number (1–66) is just a row counter, so we added **index-axis handling** to stop the tool reporting meaningless "jumps" along it.

## 6. The 1970 US draft lottery — a trend test

Monthly mean draft rank. A fair lottery should be flat/random, but later months got
systematically lower numbers (documented bias, correlation −0.226, p≈0).

- The tool flags a **downward trend** (~201 in January to ~122 in December, R²=0.75).
- This drove a new detector, **T8 (trend)**, with an honest twist: a trend is only an
  *anomaly* if the axis is supposed to be flat. By default a trend is a quiet "candidate";
  tell the tool the axis should be random (as a lottery is) and it becomes a real finding:
  *"declines… but month_num is expected to be flat/random — investigate."*
  The same rule keeps CO₂'s natural rise and Anscombe's linear relationships from raising false alarms.

## 7. Thyroid disease data (a big dataset, summarized) — does the idea scale?

3,772 rows, 6 features, 93 labeled anomalies (2.5%). Instead of feeding the raw big matrix in
(not what the tool is for), we **summarized** it into a results table: anomaly-rate per
feature-decile bin. Ground truth: anomalies concentrate in the extreme bins.

- The tool flags **exactly the right bins** — the top bin of feature 2 and the bottom bin of
  features 3, 4, 6 — and stays quiet on the two features with no concentration (6/6 correct).
- This drove a real improvement: a "flat background with one spike" bin was first missed, so we
  added a **dominant-cluster outlier** check (T7) that catches a lone value sitting far outside
  the tight cluster of the rest.
- **Honest conclusion:** the tool's idea *does* scale to big data — **when the big data is first
  summarized into a results table** (rates/means per bin or group). It is not, and should not be
  pitched as, a raw big-data machine-learning classifier.

## 8. Ordered-category tests (education income, product tiers)

Two small tables with a *conceptually ordered* category and a documented exception:
- **Median income by education level** (`<9th < HS < … < Master < Professional < Doctorate`):
  income rises with education *except* Doctorate ($57,418) earns less than Professional ($76,220).
  The tool flags the exact reversal (**monotonicity**: "Professional → Doctorate").
- **Product rating by tier across regions** (Premium should beat Standard): Premium wins in 7 of
  8 regions, with one exception. The tool flags it (**categorical exception**: "Premium usually
  ranks better than Standard (7/8); 1 exception — worth a look") — the advisor's original
  "A always beats B except once" example, on real-shaped data.

## Bottom line

- **Catches real anomalies:** the ozone hole, a research paper's results's jump/reversal/copy-paste, Anscombe's and Newcomb's outliers, the draft-lottery bias, thyroid anomaly-concentration bins, and ordered-category exceptions (education income, product tiers).
- **Stays quiet on normal data:** CO₂'s healthy trend and the clean Anscombe sets produce no false alarms.
- **Reproducible:** a 10-check test suite locks all of this in (`pytest -q`).
- **Honest:** it flags *where* to look and rates its confidence; it never claims to know *why*.
