"""Priority scoring + runner. Priority = f(strength, support), per the advisor's
'against-the-majority' idea: bucking an overwhelming pattern = HIGH."""
from __future__ import annotations
from .model import TidyTable, Flag
from . import detectors


def score(flags: list[Flag]) -> list[Flag]:
    for f in flags:
        s = f.strength
        sup = f.support
        if f.type == "numeric_jump":
            hi = s >= 10; med = s >= 3
        elif f.type == "win_reversal":
            hi = s >= 3; med = s >= 2
        elif f.type == "cat_exception":
            # support is fraction the rule holds; higher support + fewer fails = higher priority
            hi = sup >= 0.9; med = sup >= 0.75
        elif f.type == "duplicate":
            hi = s >= 3; med = s >= 2
        elif f.type == "flatness":
            hi = False; med = True
        elif f.type == "point_outlier":
            hi = s >= 6; med = s >= 3.5
        elif f.type == "monotonicity":
            hi = s >= 0.5; med = s >= 0.2
        elif f.type == "level_shift":
            # flat-baseline shift (support~1) can be HIGH; trend-departure (support 0.4) capped at LOW
            if sup >= 0.9:
                hi = s >= 5; med = s >= 3
            else:
                hi = False; med = False
        elif f.type == "trend":
            # only a real finding when the axis is expected flat (support~1); otherwise LOW
            if sup >= 0.9:
                hi = s >= 0.8; med = s >= 0.5
            else:
                hi = False; med = False
        else:
            hi = med = False
        f.priority = "HIGH" if hi else ("MEDIUM" if med else "LOW")
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    flags.sort(key=lambda f: (order[f.priority], -f.strength))
    return flags


def _suppress_index_axis(flags, index_axes):
    """On an index-like axis, per-STEP jumps and level-shifts are meaningless (x is just a
    serial number) — keep only point_outlier. But a TREND over an index is still meaningful
    ('values drift with collection order / position'), so trends are NOT suppressed."""
    if not index_axes:
        return flags
    kept = []
    for f in flags:
        if f.axis in index_axes and f.type in ("numeric_jump", "level_shift"):
            continue
        kept.append(f)
    return kept


def _suppress_jumps_adjacent_to_outliers(flags):
    """A jump whose step lands on an already-flagged point_outlier is just that outlier seen
    from the neighbor view — drop it to avoid double-reporting (Newcomb's -44 / -2)."""
    outlier_pts = {(f.axis, f.detail.get("at")) for f in flags if f.type == "point_outlier"}
    if not outlier_pts:
        return flags
    kept = []
    for f in flags:
        if f.type == "numeric_jump":
            a = (f.axis, float(f.detail.get("from"))) if f.detail.get("from") is not None else None
            b = (f.axis, float(f.detail.get("to"))) if f.detail.get("to") is not None else None
            if a in outlier_pts or b in outlier_pts:
                continue
        kept.append(f)
    return kept


def analyze(t: TidyTable, expected_monotonic: dict | None = None, expect_flat: list | None = None) -> list[Flag]:
    idx = detectors.index_like_axes(t)
    flags = []
    flags += detectors.detect_numeric_jumps(t)
    flags += detectors.detect_win_reversals(t)
    flags += detectors.detect_monotonicity(t, expected=expected_monotonic)
    flags += detectors.detect_cat_exceptions(t)
    flags += detectors.detect_duplicates_and_flatness(t)
    flags += detectors.detect_level_shifts(t)
    flags += detectors.detect_point_outliers(t)
    flags += detectors.detect_trends(t, index_axes=idx, expect_flat=expect_flat)
    flags = _suppress_index_axis(flags, idx)
    flags = _suppress_jumps_adjacent_to_outliers(flags)
    return score(flags)


def report(flags: list[Flag]) -> str:
    if not flags:
        return "No anomalies flagged."
    lines = []
    for f in flags:
        head = f"[{f.priority}] {f.type}"
        if f.axis:
            head += f" along '{f.axis}'"
        if f.coords:
            head += f"  {f.coords}"
        lines.append(head)
        lines.append(f"    -> {f.suggestion}")
    return "\n".join(lines)
