"""Tests for the grounded caption generator + the transparent caption comparison."""
import os
from anomalynerd.ingest import read_csv
from anomalynerd.analyze import analyze
from anomalynerd.caption import generate_caption
from anomalynerd.caption_compare import compare_captions

EX = os.path.join(os.path.dirname(__file__), "..", "examples")


def test_caption_states_known_trend():
    """The lottery caption should state the decreasing trend with its real numbers."""
    t = read_csv(os.path.join(EX, "draft_lottery_1970.csv"))
    cap = generate_caption(t, analyze(t, expect_flat=["month_num"]), level="medium").lower()
    assert "decrease" in cap, "caption should report the downward trend"
    assert "201" in cap and "121" in cap, "caption should include the real endpoint values"


def test_caption_length_knob():
    """short < medium <= detailed in content; short omits the pattern clause."""
    t = read_csv(os.path.join(EX, "newcomb_speed_of_light.csv"))
    fl = analyze(t)
    short = generate_caption(t, fl, level="short")
    medium = generate_caption(t, fl, level="medium")
    detailed = generate_caption(t, fl, level="detailed")
    assert len(short) < len(medium) <= len(detailed)
    assert "outlier" not in short.lower() and "stands out" not in short.lower()
    assert "stands out" in medium.lower()


def test_caption_grounded_no_false_pattern():
    """CO2 is a clean rising series; the caption must NOT invent a flatness/anomaly claim
    (regression for the unc-column flatness leak)."""
    t = read_csv(os.path.join(EX, "co2_annual.csv"))
    cap = generate_caption(t, analyze(t), level="detailed").lower()
    assert "no notable pattern" in cap or ("identical" not in cap and "outlier" not in cap)


def test_comparison_checkable_only():
    """Comparison shares the real caption's checkable direction claim and ignores metadata."""
    t = read_csv(os.path.join(EX, "draft_lottery_1970.csv"))
    gen = generate_caption(t, analyze(t, expect_flat=["month_num"]), level="medium")
    real = "Table 2: mean draft number by month in 1970; later months are lower. Bold = significant."
    rep = compare_captions(gen, real)
    assert "('direction', 'decrease')" in rep["shared"], "should share the downward-trend claim"
    # 'Table 2' and the year 1970 must be filtered out as metadata, not counted as claims
    assert "('value', 1970.0)" not in rep["real_claims"]


def test_caption_keeps_case_and_fixed_coordinates():
    """A slice-specific finding must not become a claim about every method."""
    from anomalynerd.model import Axis, Flag, TidyTable
    table = TidyTable("scope", {"method": Axis("method", "unordered_cat"),
                               "N": Axis("N", "numeric")},
                      "method", "RMSE", True, [])
    flag = Flag("trend", "scope", "N", {"method": "CNN"},
                {"slope": 1, "start_value": 1, "end_value": 5, "r2": 1},
                1, 1, "HIGH")
    caption = generate_caption(table, [flag])
    # relationship wording (description form); the metric and axis names are preserved
    assert "RMSE increases as N increases" in caption
    assert "method=CNN" in caption
    assert "Rmse" not in caption and "method=cnn" not in caption


def test_caption_jump_uses_detector_endpoints():
    """numeric_jump evidence has from/to, not an at coordinate."""
    from anomalynerd.model import Axis, Flag, TidyTable
    table = TidyTable("jump", {"N": Axis("N", "numeric")},
                      None, "RMSE", True, [])
    flag = Flag("numeric_jump", "jump", "N", {},
                {"from": 10, "to": 20, "values": [1, 12]}, 12, 1, "HIGH")
    assert "between N=10 and N=20" in generate_caption(table, [flag])


def test_monotonic_not_linear_relationship():
    """A perfectly monotonic but non-linear series is described as monotonic (Spearman),
    not as a straight line, and reports both coefficients."""
    from anomalynerd.model import Axis, TidyTable
    from anomalynerd.detectors import detect_trends
    t = TidyTable("t", {"X": Axis("X", "numeric")}, None, "Y", False,
                  [{"X": x, "value": y} for x, y in
                   zip([1, 2, 3, 4, 5, 6, 7, 8], [1, 2, 3, 4, 5, 6, 7, 10000])])
    flags = detect_trends(t)
    assert flags, "a monotonic relationship should be detected even with weak linear fit"
    d = flags[0].detail
    assert abs(d["spearman"] - 1.0) < 1e-6          # perfectly monotonic
    assert d["pearson"] < 0.7                        # but not linear
    assert d["well_fit_by_line"] is False
    cap = generate_caption(t, flags, level="medium")
    assert "monotonic" in cap and "not well described by a straight line" in cap


def test_linear_relationship_wording():
    """A near-perfect linear series is described as roughly linear with Pearson r."""
    from anomalynerd.model import Axis, TidyTable
    from anomalynerd.detectors import detect_trends
    t = TidyTable("t", {"X": Axis("X", "numeric")}, None, "RMSE", False,
                  [{"X": x, "value": y} for x, y in
                   zip(range(0, 80, 10), [1, 2, 3, 4, 5, 6, 7, 8])])
    cap = generate_caption(t, detect_trends(t), level="medium")
    assert "roughly linear" in cap and "Pearson r=1.0" in cap


def test_trend_is_description_not_auto_anomaly():
    """A plain level shift is a DESCRIPTION; the investigation prompt (and its reason) only
    appears when the axis was declared flat/random (expect_flat)."""
    from anomalynerd.model import Axis, TidyTable
    from anomalynerd.detectors import detect_trends
    rows = [{"X": x, "value": y} for x, y in
            zip(range(0, 80, 10), [1, 2, 3, 4, 5, 6, 7, 8])]
    t = TidyTable("t", {"X": Axis("X", "numeric")}, None, "RMSE", False, rows)
    # without expect_flat: described, no investigation prompt
    plain = detect_trends(t)[0].suggestion
    assert "investigate" not in plain.lower()
    # with expect_flat: the reason-stated investigation prompt appears
    flat = detect_trends(t, expect_flat={"X"})[0].suggestion
    assert "you may want to investigate" in flat.lower()
    assert "expected to be flat" in flat.lower()


def test_monotonic_endpoint_not_called_outlier():
    """A monotonic series' extreme endpoint is described as a relationship, NOT flagged as a
    point outlier; a genuine interior spike in a flat series still is an outlier."""
    from anomalynerd.model import Axis, TidyTable
    from anomalynerd.analyze import analyze
    # monotonic climb with a big last value: relationship, not outlier
    mono = TidyTable("m", {"X": Axis("X", "numeric")}, None, "Y", False,
                     [{"X": x, "value": y} for x, y in
                      zip([1, 2, 3, 4, 5, 6, 7, 8], [1, 2, 3, 4, 5, 6, 7, 10000])])
    kinds = {f.type for f in analyze(mono) if f.priority in ("HIGH", "MEDIUM")}
    assert "point_outlier" not in kinds, "monotonic endpoint must not be a HIGH outlier"
    # genuine interior spike in an otherwise flat series: still an outlier
    spike = TidyTable("s", {"X": Axis("X", "numeric")}, None, "Y", False,
                      [{"X": x, "value": y} for x, y in
                       zip(range(12), [1, 1, 1, 1, 1, 15, 1, 1, 1, 1, 1, 1])])
    assert any(f.type == "point_outlier" for f in analyze(spike)), "real spike must still flag"


def test_level_shift_description_vs_judgment():
    """A level shift is a description by default (LOW), and only becomes a HIGH investigation
    prompt when its axis is declared flat/random (expect_flat). Covers the actual level_shift
    path, not detect_trends."""
    from anomalynerd.model import Axis, TidyTable
    from anomalynerd.analyze import analyze
    rows = [{"X": x, "value": v} for x, v in
            zip(range(0, 120, 10), [1, 1, 1, 1, 1, 1, 8, 8, 8, 8, 8, 8])]
    t = TidyTable("t", {"X": Axis("X", "numeric")}, None, "RMSE", False, rows)
    plain = [f for f in analyze(t) if f.type == "level_shift"]
    assert plain, "a level shift should still be detected"
    assert all(f.priority != "HIGH" for f in plain), "level shift is a description by default"
    assert all("investigate" not in f.suggestion.lower() for f in plain)
    flagged = [f for f in analyze(t, expect_flat=["X"]) if f.type == "level_shift"]
    assert any(f.priority == "HIGH" for f in flagged), "expect_flat makes it a real finding"
    assert any("you may want to investigate" in f.suggestion.lower() for f in flagged)


def test_jump_endpoint_of_climb_vs_genuine():
    """The terminal step of a steady monotonic climb is described, not flagged HIGH, while a
    jump-then-plateau and an accelerating series keep a HIGH numeric_jump."""
    from anomalynerd.model import Axis, TidyTable
    from anomalynerd.analyze import analyze

    def mk(xv, ys):
        return TidyTable("t", {"X": Axis("X", "numeric")}, None, "Y", False,
                         [{"X": x, "value": y} for x, y in zip(xv, ys)])

    # steady climb then one endpoint blow-up: jump is a description (not HIGH)
    climb = analyze(mk(range(0, 80, 10), [1, 2, 3, 4, 5, 6, 7, 10000]))
    cj = [f for f in climb if f.type == "numeric_jump"]
    assert cj and all(f.priority != "HIGH" for f in cj), "endpoint-of-climb jump must not be HIGH"

    # accelerating series: NOT a steady climb, so a terminal blow-up stays HIGH
    accel = analyze(mk(range(0, 60, 10), [2, 5, 11, 24, 50, 10000]))
    aj = [f for f in accel if f.type == "numeric_jump"]
    assert aj and any(f.priority == "HIGH" for f in aj), "accelerating jump must stay HIGH"



def test_terminal_jump_reversal_stays_high():
    """A final step that reverses a steady climb is a jump, not its endpoint."""
    from anomalynerd.model import Axis, TidyTable
    from anomalynerd.analyze import analyze

    def jumps(ys):
        t = TidyTable("t", {"X": Axis("X", "numeric")}, None, "Y", False,
                      [{"X": x, "value": y} for x, y in zip(range(0, 80, 10), ys)])
        return [f for f in analyze(t) if f.type == "numeric_jump"]

    reversal = jumps([1, 2, 3, 4, 5, 6, 7, -10000])
    assert reversal and all(f.priority == "HIGH" for f in reversal)
    assert all(not f.detail["in_monotonic_relationship"] for f in reversal)

    endpoint = jumps([1, 2, 3, 4, 5, 6, 7, 10000])
    assert endpoint and all(f.priority == "LOW" for f in endpoint)
    assert all(f.detail["in_monotonic_relationship"] for f in endpoint)
