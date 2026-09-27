"""AnomalyNerd CLI — the single entry point.

Usage:
    python -m anomalynerd.cli FILE.csv [options]

Examples:
    python -m anomalynerd.cli examples/halley_ozone_october.csv --metric ozone_DU --lower-better
    python -m anomalynerd.cli examples/co2_annual.csv --metric mean --higher-better --ignore unc
    python -m anomalynerd.cli results.csv --order "knowledge=Both known,p_1 known,p_2 known,Both unknown"
    python -m anomalynerd.cli results.csv --json           # machine-readable output

The tool POINTS at what deserves a closer look; it does not diagnose or re-run anything.
"""
import argparse, json, sys
from textwrap import wrap
from .ingest import read_csv
from .analyze import analyze


def _fmt_report(flags, table_name, metric_name, lower_is_better, width=82):
    direction = "lower is better" if lower_is_better else "higher is better"
    counts = {p: sum(f.priority == p for f in flags) for p in ("HIGH", "MEDIUM", "LOW")}
    lines = ["ANOMALYNERD  /  RESULTS REVIEW",
             "=" * width,
             f"Table    {table_name}",
             f"Metric   {metric_name} ({direction})",
             f"Flags    {len(flags)}  |  HIGH {counts['HIGH']}   MEDIUM {counts['MEDIUM']}   LOW {counts['LOW']}",
             "-" * width]
    if not flags:
        return "\n".join(lines + ["No anomalies flagged. This is not a validation of the results."])
    for i, f in enumerate(flags, 1):
        title = f.type.replace("_", " ").capitalize()
        if f.axis:
            title += f"  /  {f.axis}"
        lines.append(f"{i:02d}  {f.priority:<6}  {title}")
        if f.coords:
            context = ", ".join(f"{k}={v}" for k, v in f.coords.items())
            lines.extend(wrap("Context: " + context, width=width - 5, initial_indent="     ", subsequent_indent="     "))
        lines.extend(wrap(f.suggestion, width=width - 5,
                          initial_indent="     ", subsequent_indent="     ",
                          break_long_words=False, break_on_hyphens=False))
        lines.append("")
    lines.append("Flags point to checks, not proven errors.")
    return "\n".join(lines)


def _parse_orders(spec):
    """--order "axis=a,b,c;axis2=x,y" -> {axis:[a,b,c], ...}"""
    orders = {}
    if not spec:
        return orders
    for part in spec.split(";"):
        if "=" in part:
            ax, vals = part.split("=", 1)
            orders[ax.strip()] = [v.strip() for v in vals.split(",")]
    return orders


def main(argv=None):
    ap = argparse.ArgumentParser(prog="anomalynerd", description="Flag anomalies worth investigating in a results table.")
    ap.add_argument("csv", help="Path to the CSV results table")
    ap.add_argument("--metric", help="Name of the metric column (auto-detected if omitted)")
    ap.add_argument("--entity", help="Name of the competitor/entity column (e.g. 'method')")
    direction = ap.add_mutually_exclusive_group()
    direction.add_argument("--lower-better", dest="lower", action="store_true", help="Lower metric is better (RMSE/error)")
    direction.add_argument("--higher-better", dest="higher", action="store_true", help="Higher metric is better (accuracy)")
    ap.add_argument("--ignore", nargs="*", default=None, help="Columns to ignore (e.g. uncertainty)")
    ap.add_argument("--order", help='Conceptual order for categorical axes: "axis=a,b,c;axis2=x,y"')
    ap.add_argument("--expect-increasing", nargs="*", default=None, help="Axes where the metric should increase")
    ap.add_argument("--expect-decreasing", nargs="*", default=None, help="Axes where the metric should decrease")
    ap.add_argument("--expect-flat", nargs="*", default=None, help="Axes that should be flat/random (a trend there is a real anomaly, e.g. a lottery)")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    args = ap.parse_args(argv)

    lower = True if args.lower else (False if args.higher else None)
    try:
        t = read_csv(args.csv, metric_col=args.metric, entity_col=args.entity,
                     lower_is_better=lower, orders=_parse_orders(args.order),
                     ignore_cols=args.ignore)
    except (KeyError, ValueError, IndexError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    expected = {}
    for a in (args.expect_increasing or []):
        expected[a] = "increasing"
    for a in (args.expect_decreasing or []):
        expected[a] = "decreasing"

    flags = analyze(t, expected_monotonic=expected or None, expect_flat=args.expect_flat)

    if args.json:
        print(json.dumps({"table": t.name, "metric": t.metric_name,
                          "lower_is_better": t.lower_is_better,
                          "flags": [f.to_dict() for f in flags]}, indent=2))
    else:
        print(_fmt_report(flags, t.name, t.metric_name, t.lower_is_better))
    return 0


if __name__ == "__main__":
    sys.exit(main())
