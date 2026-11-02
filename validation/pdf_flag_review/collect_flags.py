"""Re-collect every flag AnomalyNerd raises on the 22 papers of the PDF flag review.

    python validation/pdf_flag_review/collect_flags.py [download_dir] [--heldout | --fresh | --fresh2]
                                                       [--cache DIR]

Downloads each paper (arXiv or PLOS, public), runs the article pipeline, and writes
flags.json (heldout_flags.json with --heldout, fresh_flags.json with --fresh,
fresh2_flags.json with --fresh2) next to this script. Compare it with labels.json or
heldout_labels.json, which hold the hand judgments.

--cache DIR saves Docling's layout-model output for each PDF in DIR and reuses it on later
runs (see docling_cache.py). It also saves each detector's result per table, reused only while
the detector code and the table are unchanged. A first run takes as long as before.
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

PLOS = {"doi:10.1371/journal.pone.0287795": "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0287795&type=printable",
        "doi:10.1371/journal.pmed.1003583": "https://journals.plos.org/plosmedicine/article/file?id=10.1371/journal.pmed.1003583&type=printable"}


def url_for(source):
    if source.startswith("arXiv:"):
        return "https://arxiv.org/pdf/" + source.split(":", 1)[1]
    return PLOS[source]


def main():
    argv = sys.argv[1:]
    if "--cache" in argv:
        i = argv.index("--cache")
        cache_dir = argv[i + 1]
        del argv[i:i + 2]
        sys.path.insert(0, HERE)
        import docling_cache
        docling_cache.enable(cache_dir)
        checkpoint_dir = docling_cache.detector_dir(cache_dir)
    else:
        checkpoint_dir = None
    from anomalynerd.analyze_pdf import analyze_source
    args = [a for a in argv if a not in ("--heldout", "--fresh", "--fresh2")]
    heldout = "--heldout" in sys.argv
    fresh = "--fresh" in sys.argv
    fresh2 = "--fresh2" in sys.argv
    prefix = "heldout_" if heldout else ("fresh2_" if fresh2 else ("fresh_" if fresh else ""))
    out_dir = args[0] if args else os.path.join(HERE, "pdfs")
    os.makedirs(out_dir, exist_ok=True)
    papers = json.load(open(os.path.join(HERE, prefix + "papers.json")))
    flags = []
    for p in papers:
        path = os.path.join(out_dir, p["name"] + ".pdf")
        if not os.path.exists(path):
            req = urllib.request.Request(url_for(p["source"]), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
                f.write(r.read())
        res = analyze_source(path, checkpoint_dir=checkpoint_dir)
        for key, fl in res.table_flags.items():
            for f in fl:
                flags.append({"paper": p["name"], "page": key[0], "priority": f.priority,
                              "type": f.type, "suggestion": f.suggestion})
        for s in res.stat_findings:
            if s.status == "finding":
                flags.append({"paper": p["name"], "page": None, "priority": s.severity.upper(),
                              "type": "stat:" + s.kind, "suggestion": s.detail})
        print(f"{p['name']}: {sum(1 for x in flags if x['paper'] == p['name'])} flags", flush=True)
    out = prefix + "flags.json"
    json.dump(flags, open(os.path.join(HERE, out), "w"), indent=1, ensure_ascii=False)
    print(f"total {len(flags)} flags -> {out}")


if __name__ == "__main__":
    main()
