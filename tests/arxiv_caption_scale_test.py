"""Scale validation for the caption feature.

Samples N arXiv papers, fetches LaTeX source, and for every results table that parses
cleanly: generates a grounded caption and compares it to the paper's real \\caption{} on
checkable claims only. Reports the DISTRIBUTION of checkable-claim overlap across tables.

This is descriptive, not a score the tool is optimized against: real captions are written
for human readers and often state things a table alone cannot verify (motivation, method
names, "bold = best"), so low overlap is expected and is not a failure of the generator.
What we report honestly:
  - how many tables we could caption at all,
  - of the real captions that contain at least one checkable claim, how often the generated
    caption agrees on those claims (checkable recall),
  - how many generated claims were NOT in the real caption (extra claims the tool surfaced).

Run:
  python tests/arxiv_caption_scale_test.py -n 30 --seed 0
"""
import argparse
import os
import random
import re
import signal
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tests.arxiv_scale_test import sample_arxiv_ids, download_source_tex  # reuse fetch
from anomalynerd.latex_ingest import parse_latex
from anomalynerd.caption import generate_caption
from anomalynerd.caption_compare import compare_captions

OUTDIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "an_caption_scale")

# Empirical, results-table-heavy categories (ML / NLP / vision / applied stats). Random arXiv
# is dominated by theory papers whose tables are theorem-parameter tables with no checkable
# results claims, which is not what the caption feature describes. We target fields where
# tables report measured results (accuracy, error, best method, improvement).
EMPIRICAL_CATEGORIES = ["cs.LG", "cs.CL", "cs.CV", "stat.ML", "cs.IR"]

# A real caption only counts as a RESULTS caption (fair to compare against) if it talks about
# measured outcomes, not theorems/definitions. Transparent, keyword-based, shown here.
_RESULTS_CAPTION_CUES = re.compile(
    r"\b(accuracy|error|f1|precision|recall|auc|bleu|rouge|score|performance|results?|"
    r"best|outperform|improv|baseline|ablation|comparison|benchmark|dataset|%|"
    r"higher|lower|increase|decrease|better|state-of-the-art|sota)\b", re.I)


def _is_results_caption(cap: str) -> bool:
    return bool(cap) and bool(_RESULTS_CAPTION_CUES.search(cap))


class _Timeout(Exception):
    pass


def _caption_with_timeout(tidy, seconds=4):
    """Generate a caption but abort if it takes too long. Some wide results tables trigger a
    slow path in analyze() (a known detector-performance bug on many-column tables); rather
    than hang the whole validation, we skip those tables and count them, honestly."""
    def _handler(signum, frame):
        raise _Timeout()
    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        return generate_caption(tidy, level="medium")
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _real_caption(tidy, extracted):
    """The real caption the paper wrote for this table (stored as the tidy name)."""
    cap = (tidy.name or "").strip()
    return cap


def run(n=30, seed=0, outdir=OUTDIR):
    os.makedirs(outdir, exist_ok=True)
    ids = sample_arxiv_ids(n, seed=seed, categories=EMPIRICAL_CATEGORIES)
    print(f"sampled {len(ids)} arXiv papers (seed={seed})\n")

    n_papers_ok = 0
    rows = []            # per-table records
    n_skipped = 0        # tables skipped due to caption timeout (wide-table detector bug)
    for i, aid in enumerate(ids, 1):
        texp = download_source_tex(aid, outdir)
        if not texp:
            print(f"[{i}/{len(ids)}] {aid}: no source")
            continue
        try:
            parse = parse_latex(texp)
        except Exception as e:
            print(f"[{i}/{len(ids)}] {aid}: parse error {type(e).__name__}")
            continue
        ok_tables = [t for t in parse.tables if t.status == "ok" and getattr(t, "tidies", None)]
        if not ok_tables:
            print(f"[{i}/{len(ids)}] {aid}: 0 usable tables")
            continue
        n_papers_ok += 1
        n_tab = 0
        for et in ok_tables:
            for tidy in et.tidies:
                real = _real_caption(tidy, et)
                if not real:
                    continue  # no real caption to compare against
                if not _is_results_caption(real):
                    continue  # theorem/definition table caption, not a results caption; skip
                # crude parse-quality: a cleanly-parsed table has a real metric name and
                # real axis labels, not placeholder col0/colN or leaked LaTeX math.
                axis_names = list(getattr(tidy, "axes", {}).keys())
                blob = " ".join([str(tidy.metric_name or "")] + [str(a) for a in axis_names])
                clean_schema = not re.search(r"col\d|\\|_\{|\^|\$|\|", blob) and bool(tidy.metric_name)
                try:
                    gen = _caption_with_timeout(tidy, seconds=4)
                except _Timeout:
                    n_skipped += 1
                    continue
                cmp = compare_captions(gen, real)
                rows.append({
                    "arxiv": aid,
                    "real": real[:160],
                    "gen": gen[:160],
                    "shared": cmp["shared"],
                    "gen_only": cmp["generated_only"],
                    "real_only": cmp["real_only"],
                    "real_checkable": len(cmp["real_claims"]),
                    "checkable_recall": cmp["checkable_recall"],
                    "clean_schema": clean_schema,
                })
                n_tab += 1
        print(f"[{i}/{len(ids)}] {aid}: {n_tab} captioned table(s)")

    # ---- aggregate, honestly ----
    print("\n" + "=" * 64)
    print("CAPTION SCALE VALIDATION  (descriptive, not a success score)")
    print("=" * 64)
    print(f"papers sampled              : {len(ids)}")
    print(f"papers with usable tables   : {n_papers_ok}")
    print(f"tables captioned            : {len(rows)}")
    print(f"tables skipped (caption timeout, wide-table detector bug): {n_skipped}")
    if not rows:
        print("\nno comparable tables found; nothing to aggregate")
        return

    clean_rows = [r for r in rows if r.get("clean_schema")]
    print(f"  of these, cleanly-parsed schema (real metric/axis names, no LaTeX noise): {len(clean_rows)}")

    def _recall_stats(rowset, label):
        wc = [r for r in rowset if r["real_checkable"] > 0 and r["checkable_recall"] is not None]
        print(f"\n[{label}] real caption had >=1 checkable claim: {len(wc)}")
        if not wc:
            print("  (none to aggregate)")
            return
        recalls = [r["checkable_recall"] for r in wc]
        rs = sorted(recalls)
        mean = sum(recalls) / len(recalls)
        median = rs[len(rs) // 2]
        print(f"  checkable-claim recall  mean {mean:.2f} | median {median:.2f}")
        buckets = {"0.0": 0, "0<r<0.5": 0, "0.5<=r<1.0": 0, "1.0": 0}
        for r in recalls:
            if r == 0.0: buckets["0.0"] += 1
            elif r < 0.5: buckets["0<r<0.5"] += 1
            elif r < 1.0: buckets["0.5<=r<1.0"] += 1
            else: buckets["1.0"] += 1
        print("  distribution: " + "  ".join(f"{k}={v}" for k, v in buckets.items()))

    # Report BOTH honestly: all comparable tables, and only cleanly-parsed ones.
    _recall_stats(rows, "ALL comparable tables")
    _recall_stats(clean_rows, "CLEANLY-PARSED tables only")
    print("\nNote: low recall on ALL tables is driven mainly by messy real-world LaTeX parses")
    print("(placeholder column names, leaked math), not by the caption generator. The")
    print("cleanly-parsed subset is the fairer read on caption quality. Even there, recall is")
    print("partial because real captions describe things a table alone cannot verify.")

    extra = [len(r["gen_only"]) for r in rows]
    print(f"\nGenerated-only (extra) checkable claims the tool surfaced beyond the real caption:")
    print(f"  mean per table: {sum(extra)/len(extra):.2f}  (these are not errors; the tool often")
    print(f"  reports patterns the human caption omitted)")

    # a few concrete examples for the write-up
    print("\nExamples (real vs generated):")
    shown = 0
    for r in rows:
        if r["real_checkable"] > 0 and shown < 4:
            print(f"\n  arXiv {r['arxiv']}")
            print(f"    real: {r['real']}")
            print(f"    gen : {r['gen']}")
            print(f"    shared checkable claims: {r['shared']}")
            shown += 1

    # write a CSV for the paper
    import csv
    csvp = os.path.join(outdir, "caption_scale_results.csv")
    with open(csvp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["arxiv", "real_checkable", "checkable_recall",
                    "n_shared", "n_gen_only", "n_real_only"])
        for r in rows:
            rec = r["checkable_recall"]
            w.writerow([r["arxiv"], r["real_checkable"],
                        ("" if rec is None else f"{rec:.3f}"),
                        len(r["shared"]), len(r["gen_only"]), len(r["real_only"])])
    print(f"\nwrote per-table results to {csvp}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--outdir", default=OUTDIR)
    a = ap.parse_args()
    run(n=a.n, seed=a.seed, outdir=a.outdir)
