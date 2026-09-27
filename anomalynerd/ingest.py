"""Generic ingest: CSV -> TidyTable, with schema auto-inference.

Two accepted CSV shapes:
  (A) LONG/tidy: columns are axes + one metric column. e.g.
        p1,p2,method,RMSE
        0.12,0.05,MethodA,1.61
  (B) WIDE: some index columns + many metric columns (one per entity). e.g.
        p1,MethodB,ARIMA,MethodA
        0.12,48.72,86.44,1.61
      -> melted into long form with entity axis = the metric-column name.

Schema inference is a best-effort GUESS; every choice can be overridden by the caller.
"""
from __future__ import annotations
import csv, re
from pathlib import Path
from .model import TidyTable, Axis, MISSING

_METRIC_WORDS = ("rmse", "mae", "mse", "error", "err", "loss", "accuracy", "acc",
                 "score", "auc", "f1", "precision", "recall", "value", "runtime",
                 "time", "latency")
_LOWER_BETTER = {"rmse", "mae", "mse", "error", "err", "loss", "runtime", "time", "latency", "deviation"}
_HIGHER_BETTER = {"accuracy", "acc", "score", "auc", "f1", "precision", "recall", "rating", "income"}


def _metric_direction(metric_name, override):
    """Use an explicit choice first; never silently call an unknown metric lower-better."""
    if override is not None:
        return override
    tokens = set(re.findall(r"[a-z0-9]+", metric_name.lower()))
    lower = bool(tokens & _LOWER_BETTER)
    higher = bool(tokens & _HIGHER_BETTER)
    if lower != higher:
        return lower
    raise ValueError(
        f"Cannot infer whether {metric_name!r} is lower or higher better; "
        "pass --lower-better or --higher-better."
    )


_MISSING_TOKENS = {"", "--", "-", "n/a", "na", "nan", "none", "null"}

_ORDER_LEXICON = [
    ["low", "medium", "med", "high"],
    ["none", "some", "all"],
    ["both known", "p_1 known", "p_2 known", "both unknown"],
    ["small", "medium", "large"],
    ["cold", "warm", "hot"],
]


def _parse_number(s: str):
    if s is None:
        return MISSING
    t = s.strip().lower()
    if t in _MISSING_TOKENS:
        return MISSING
    t2 = s.strip().replace(",", "").replace("%", "")
    t2 = re.sub(r"[×x]\s*10\^?(-?\d+)", lambda m: f"e{m.group(1)}", t2)  # 8×10^3 -> 8e3
    t2 = t2.replace("−", "-")  # unicode minus
    try:
        return float(t2)
    except ValueError:
        return MISSING


def _looks_numeric(values):
    got = 0; total = 0
    for v in values:
        if v is None or str(v).strip().lower() in _MISSING_TOKENS:
            continue
        total += 1
        if _parse_number(v) is not MISSING:
            got += 1
    return total > 0 and got / total >= 0.8


def _infer_order(levels):
    lows = [str(l).strip().lower() for l in levels]
    for lex in _ORDER_LEXICON:
        if set(lows) <= set(lex):
            idx = {v: i for i, v in enumerate(lex)}
            return sorted(levels, key=lambda x: idx[str(x).strip().lower()])
    return None


def read_csv(path, metric_col=None, entity_col=None, lower_is_better=None,
             name=None, orders=None, index_cols=None, ignore_cols=None):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or not any(h.strip() for h in header):
            raise ValueError("CSV has no header")
        data = [row for row in reader if any(c.strip() for c in row)]
        if not data:
            raise ValueError("CSV has no data rows")
    cols = {h: [row[i] if i < len(row) else "" for row in data] for i, h in enumerate(header)}
    name = name or Path(path).name
    orders = orders or {}

    numeric_cols = [h for h in header if _looks_numeric(cols[h])]
    cat_cols = [h for h in header if h not in numeric_cols]

    # decide shape
    metric_by_name = [h for h in header if any(w in h.lower() for w in _METRIC_WORDS)]

    if metric_col is None and len(numeric_cols) >= 2 and len(metric_by_name) == 0:
        # WIDE: many numeric columns, none obviously "the metric" -> entities are those columns.
        # Index columns: caller hint > categorical columns > default to the FIRST column
        # (near-universal convention for a wide results table: leading col is the grid axis).
        if index_cols is not None:
            idx_cols = list(index_cols)
        elif cat_cols:
            idx_cols = list(cat_cols)
        else:
            idx_cols = [header[0]]
        entity_cols = [h for h in numeric_cols if h not in idx_cols]
        if not entity_cols:                        # safety: fall back to treating last col as metric (LONG)
            metric_col = numeric_cols[-1]
        else:
            rows = []
            for r_i in range(len(data)):
                base = {c: _coerce(cols[c][r_i]) for c in idx_cols}
                for ec in entity_cols:
                    rows.append({**base, "method": ec, "value": _parse_number(cols[ec][r_i])})
            axes = {}
            for c in idx_cols:
                axes[c] = _make_axis(c, [_coerce(x) for x in cols[c]], orders)
            axes["method"] = Axis("method", "unordered_cat")
            lib = _metric_direction("value", lower_is_better)
            return TidyTable(name, axes, entity_axis="method", metric_name="value",
                             lower_is_better=lib, rows=rows)

    # LONG: pick metric col
    mcol = metric_col or (metric_by_name[0] if metric_by_name else numeric_cols[-1])
    axis_cols = [h for h in header if h != mcol]
    # Drop caller-ignored columns and redundant continuous covariates: a numeric column
    # with (nearly) one distinct value per row is a per-row attribute (e.g. an uncertainty
    # 'unc' or an id), NOT an analysis axis. Keep it only if it's the sole axis.
    ignore = set(ignore_cols or [])
    if len(axis_cols) > 1:
        near_unique_numeric = [h for h in axis_cols
                               if h in numeric_cols and h != entity_col
                               and len(set(cols[h])) >= 0.95 * len(data)]
        # keep the FIRST such column as the primary index; drop the rest (redundant covariates
        # like 'unc' that pair 1:1 with the index and are per-row attributes, not axes).
        for h in near_unique_numeric[1:]:
            ignore.add(h)
    axis_cols = [h for h in axis_cols if h not in ignore]
    ecol = entity_col
    if ecol is None:
        # entity = the categorical axis with the most levels (methods) if any.
        # An explicitly-ordered column (order hint or lexicon match) is a real ordered axis,
        # NOT an entity/competitor — exclude such columns from entity auto-detection.
        cat_axis = [h for h in axis_cols if h in cat_cols and _make_axis(h, [_coerce(x) for x in cols[h]], orders).kind != "ordered_cat"]
        ecol = max(cat_axis, key=lambda h: len(set(cols[h]))) if cat_axis else None
    rows = []
    for r_i in range(len(data)):
        row = {c: _coerce(cols[c][r_i]) for c in axis_cols}
        row["value"] = _parse_number(cols[mcol][r_i])
        rows.append(row)
    axes = {}
    for c in axis_cols:
        kind_vals = [_coerce(x) for x in cols[c]]
        ax = _make_axis(c, kind_vals, orders)
        # only force unordered-entity when the column isn't an explicitly ordered axis
        if c == ecol and ax.kind != "ordered_cat":
            ax = Axis(c, "unordered_cat")
        axes[c] = ax
    lib = _metric_direction(mcol, lower_is_better)
    return TidyTable(name, axes, entity_axis=ecol, metric_name=mcol,
                     lower_is_better=lib, rows=rows)


def _coerce(x):
    n = _parse_number(x)
    return n if n is not MISSING else (x.strip() if isinstance(x, str) else x)


def _make_axis(name, values, orders):
    if name in orders:
        return Axis(name, "ordered_cat", order=orders[name])
    if _looks_numeric([str(v) for v in values]):
        return Axis(name, "numeric")
    order = _infer_order(list(dict.fromkeys(values)))
    if order:
        return Axis(name, "ordered_cat", order=order)
    return Axis(name, "unordered_cat")
