import json

import pytest

from anomalynerd.analyze_pdf import analyze_source
from anomalynerd.pdf_ingest import _extract_stat_strings
from anomalynerd.stat_tests import statcheck


@pytest.mark.parametrize('text', [
    'χ²(2, N = 120) = 0.10, p < .001',
    'χ2(2) = .10, p < .001',
    'chi-square(2) = .10, p < .001',
    'chi square(2) = .10, p < .001',
    't(20) = .5, p < .001',
    't(20) = -.5, p < 1e-3',
    'F(2, 57) = .5, p < .001',
    'r(20) = .01, p < .001',
    'z = 5e-1, p < .001',
])
def test_extracted_statistics_reach_checker(text):
    assert _extract_stat_strings(text) == [text]
    result = statcheck(_extract_stat_strings(text))
    assert len(result) == 1
    assert result[0].status == 'finding'


@pytest.mark.parametrize('text', [
    't(0) = 2, p = .05',
    't(-2) = 2, p = .05',
    'F(2, 0) = 2, p = .05',
    'F(2, 20) = -2, p = .05',
    'r(20) = 1.1, p = .05',
    'r(0) = .5, p = .05',
    'chi-square(0) = 2, p = .05',
    'chi-square(2) = -2, p = .05',
    'z = .5, p = 1.5',
    'z = .5, p = -.05',
    'z = 1e999, p = .05',
])
def test_invalid_statistics_never_report_consistent(text):
    result = statcheck(_extract_stat_strings(text))
    assert len(result) == 1
    assert result[0].status == 'not_applicable'
    assert 'invalid' in result[0].detail
    json.dumps(result[0].evidence, allow_nan=False)


def test_perfect_correlation_is_checkable():
    assert statcheck(['r(20) = 1, p < .001'])[0].status == 'ok'


def test_extract_all_tests_from_one_paragraph():
    text = 't(20) = .5, p < .001; z = .5, p < .001; χ²(2, N = 120) = .1, p < .001'
    snippets = _extract_stat_strings(text)
    assert len(snippets) == 3
    assert all(f.status == 'finding' for f in statcheck(snippets))


def test_latex_pipeline_checks_chi_square_with_sample_size(tmp_path):
    path = tmp_path / 'statistics.tex'
    path.write_text('χ²(2, N = 120) = 0.10, p < .001')
    report = analyze_source(str(path))
    assert any(f.kind == 'statcheck' and f.status == 'finding' for f in report.stat_findings)


@pytest.mark.parametrize('text', [
    't(20) = .5, p < .001.',
    'z = 5e-1, p < 1e-3.',
])
def test_sentence_period_does_not_hide_statistic(text):
    snippets = _extract_stat_strings(text)
    assert len(snippets) == 1
    assert statcheck(snippets)[0].status == 'finding'


@pytest.mark.parametrize('text', ['z = .5, p = .03e', 'z = .5, p = .03.5'])
def test_malformed_p_value_not_truncated(text):
    assert _extract_stat_strings(text) == []
