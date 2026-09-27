"""Metric direction changes winner and exception detection; never guess it blindly."""
import pytest
from anomalynerd.ingest import read_csv
from anomalynerd.cli import main


def test_infers_accuracy_as_higher_better(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text("setting,method,accuracy\n1,A,0.9\n1,B,0.7\n2,A,0.8\n2,B,0.9\n3,A,0.7\n3,B,0.95\n")
    assert read_csv(path).lower_is_better is False
    assert read_csv(path, lower_is_better=True).lower_is_better is True


def test_unknown_direction_requires_choice(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text("setting,method,quality\n1,A,10\n1,B,20\n")
    with pytest.raises(ValueError, match="--lower-better or --higher-better"):
        read_csv(path, metric_col="quality")
    assert read_csv(path, metric_col="quality", lower_is_better=False).lower_is_better is False


def test_wide_table_requires_choice(tmp_path):
    path = tmp_path / "results.csv"
    path.write_text("setting,MethodA,MethodB\n1,10,20\n2,11,21\n")
    with pytest.raises(ValueError, match="--lower-better or --higher-better"):
        read_csv(path)
    assert read_csv(path, lower_is_better=True).lower_is_better is True


def test_empty_csv_is_a_useful_error(tmp_path, capsys):
    path = tmp_path / "empty.csv"
    path.write_text("")
    assert main([str(path)]) == 2
    assert "CSV has no header" in capsys.readouterr().err


def test_cli_report_direction_and_json(tmp_path, capsys):
    path = tmp_path / "accuracy.csv"
    path.write_text("setting,method,accuracy\n1,A,0.9\n1,B,0.7\n2,A,0.8\n2,B,0.9\n3,A,0.7\n3,B,0.95\n")
    assert main([str(path)]) == 0
    output = capsys.readouterr().out
    assert "accuracy (higher is better)" in output
    assert "No anomalies flagged." in output
    assert main([str(path), "--json"]) == 0
    import json
    data = json.loads(capsys.readouterr().out)
    assert data["lower_is_better"] is False
    with pytest.raises(SystemExit, match="2"):
        main([str(path), "--lower-better", "--higher-better"])


def test_color_only_when_requested():
    from anomalynerd.cli import _fmt_report
    from anomalynerd.model import Flag
    flag = Flag("point_outlier", "sample", "year", {}, {}, 8, 1, "HIGH", "Check this year.")
    plain = _fmt_report([flag], "sample", "score", False)
    color = _fmt_report([flag], "sample", "score", False, color=True)
    import re
    assert "\033[" not in plain
    assert "\033[" in color
    assert re.sub(r"\033\[[0-9;]*m", "", color) == plain
