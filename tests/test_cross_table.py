"""Cross-table consistency: same metric + same coordinates in two tables of one source
should agree within rounding of the printed values."""
import math
from anomalynerd.model import TidyTable, Axis
from anomalynerd.cross_table import (
    find_cross_table_inconsistencies, _rounding_tolerance, _decimals_in)
from anomalynerd.analyze import score
from anomalynerd.analyze_pdf import analyze_source, format_report


def mk(name, rows, metric="RMSE", axes=None):
    axes = axes or {"method": Axis("method", "unordered_cat")}
    return TidyTable(name, axes, "method", metric, True, rows)


def test_flags_beyond_rounding():
    a = mk("table2", [{"method": "A", "value": 1.61, "_raw": "1.61"},
                      {"method": "B", "value": 2.10, "_raw": "2.10"}])
    b = mk("table5", [{"method": "A", "value": 1.83, "_raw": "1.83"},
                      {"method": "B", "value": 2.10, "_raw": "2.10"}])
    flags, notes = find_cross_table_inconsistencies([a, b])
    assert len(flags) == 1 and not notes
    f = flags[0]
    assert f.type == "cross_table_inconsistency"
    assert f.coords == {"method": "A"}
    assert f.detail["shared_cells"] == 2 and f.detail["consistent_cells"] == 1
    assert f.support == 0.5


def test_within_rounding_not_flagged():
    a = mk("t1", [{"method": "A", "value": 1.61, "_raw": "1.61"}])
    b = mk("t2", [{"method": "A", "value": 1.62, "_raw": "1.62"}])
    flags, _ = find_cross_table_inconsistencies([a, b])
    assert flags == []


def test_different_metrics_not_compared():
    a = mk("t1", [{"method": "A", "value": 1.61, "_raw": "1.61"}], metric="RMSE")
    b = mk("t2", [{"method": "A", "value": 9.99, "_raw": "9.99"}], metric="MAE")
    flags, notes = find_cross_table_inconsistencies([a, b])
    assert flags == [] and notes == []


def test_metric_name_case_insensitive():
    a = mk("t1", [{"method": "A", "value": 1.61, "_raw": "1.61"}], metric="rmse")
    b = mk("t2", [{"method": "A", "value": 1.90, "_raw": "1.90"}], metric="RMSE")
    flags, _ = find_cross_table_inconsistencies([a, b])
    assert len(flags) == 1


def test_different_axis_sets_not_compared_but_noted():
    axes2 = {"method": Axis("method", "unordered_cat"),
             "dataset": Axis("dataset", "unordered_cat")}
    a = mk("t1", [{"method": "A", "value": 1.61, "_raw": "1.61"}])
    b = mk("t2", [{"method": "A", "dataset": "d1", "value": 9.9, "_raw": "9.9"}], axes=axes2)
    flags, notes = find_cross_table_inconsistencies([a, b])
    assert flags == []
    assert len(notes) == 1 and "not compared" in notes[0]


def test_missing_values_skipped():
    a = mk("t1", [{"method": "A", "value": None, "_raw": "--"}])
    b = mk("t2", [{"method": "A", "value": 9.9, "_raw": "9.9"}])
    flags, _ = find_cross_table_inconsistencies([a, b])
    assert flags == []


def test_unknown_precision_flags_but_stays_low():
    # No raw text -> no rounding slack, so even a 1e-7 gap is flagged; but its
    # strength is the raw gap, so the scorer keeps it LOW rather than crying wolf.
    a = mk("t1", [{"method": "A", "value": 1.6100001, "_raw": ""}])
    b = mk("t2", [{"method": "A", "value": 1.61, "_raw": ""}])
    flags, _ = find_cross_table_inconsistencies([a, b])
    assert len(flags) == 1
    score(flags)
    assert flags[0].priority == "LOW"
    # Float-noise-level identity is not flagged.
    c = mk("t3", [{"method": "A", "value": 1.61 + 1e-12, "_raw": ""}])
    flags2, _ = find_cross_table_inconsistencies([b, c])
    assert flags2 == []


def test_tolerance_helpers():
    assert _decimals_in("1.61") == (2, 1.0)
    assert _decimals_in("8x10^-3")[1] == 1e-3
    assert abs(_rounding_tolerance("1.61", 1.61) - 0.005) < 1e-12
    assert _rounding_tolerance("", 1.0) == 0.0
    assert _rounding_tolerance(None, 1.0) == 0.0


def test_scorer_priority():
    a = mk("t1", [{"method": m, "value": 1.0 + i, "_raw": str(1.0 + i)} for i, m in enumerate("ABCD")])
    b = mk("t2", [{"method": m, "value": 1.0 + i, "_raw": str(1.0 + i)} for i, m in enumerate("ABCD")])
    b.rows[0]["value"] = 9.99; b.rows[0]["_raw"] = "9.99"
    flags, _ = find_cross_table_inconsistencies([a, b])
    score(flags)
    assert flags[0].priority == "HIGH"      # huge gap, 3 of 4 cells agree


def test_end_to_end_latex(tmp_path):
    tex = r"""
\begin{table}
\caption{Main results}
\begin{tabular}{lr}
Method & RMSE \\
A & 1.61 \\
B & 2.10 \\
\end{tabular}
\end{table}
\begin{table}
\caption{Ablation}
\begin{tabular}{lr}
Method & RMSE \\
A & 1.83 \\
B & 2.10 \\
\end{tabular}
\end{table}
"""
    p = tmp_path / "paper.tex"
    p.write_text(tex)
    res = analyze_source(str(p))
    assert res.cross_table_flags, "contradiction across the two tables should be flagged"
    rep = format_report(res)
    assert "Cross-table consistency" in rep
    assert "1.61" in rep and "1.83" in rep


def test_end_to_end_consistent_latex_quiet(tmp_path):
    tex = r"""
\begin{table}
\begin{tabular}{lr}
Method & RMSE \\
A & 1.61 \\
\end{tabular}
\end{table}
\begin{table}
\begin{tabular}{lr}
Method & RMSE \\
A & 1.61 \\
\end{tabular}
\end{table}
"""
    p = tmp_path / "paper.tex"
    p.write_text(tex)
    res = analyze_source(str(p))
    assert res.cross_table_flags == []
