# AnomalyNerd: three follow-up changes

1. Nonfinite numeric tokens become missing and are excluded by numeric helpers; accuracy/score defaults are higher-better.
2. Named multi-metric tables split without losing monotonic accuracy/latency outputs; each metric keeps shared axes and direction. Same-scale accuracy/loss is no longer collapsed.
3. Preserve original cell precision for terminal-digit tests; trailing zeros count, unknown/scientific precision is not invented from float repr. Benford skips narrow ranges or insufficient expected digit counts.

Examples: python examples/measurement_integrity.py. Full42test suite passes. All examples synthetic; no scientific fraud claim. Metric-name inference and two-order Benford screen are conservative heuristics, not proof of eligibility. Fixed precision can naturally cause digit departures. GRIM/statcheck semantics unchanged.

All measured examples are offline and synthetic. No deploy/merge/release. Backend changes only, no screenshot claims.

## Regression before

```text
FFFFFFFF                                                                 [100%]
=================================== FAILURES ===================================
_________________________ test_nonfinite_excluded[inf] _________________________
tests/test_measurement_integrity.py:15: in test_nonfinite_excluded
    assert _parse_number(token) is MISSING
E   AssertionError: assert inf is None
E    +  where inf = _parse_number('inf')
________________________ test_nonfinite_excluded[-inf] _________________________
tests/test_measurement_integrity.py:15: in test_nonfinite_excluded
    assert _parse_number(token) is MISSING
E   AssertionError: assert -inf is None
E    +  where -inf = _parse_number('-inf')
________________________ test_nonfinite_excluded[1e999] ________________________
tests/test_measurement_integrity.py:15: in test_nonfinite_excluded
    assert _parse_number(token) is MISSING
E   AssertionError: assert inf is None
E    +  where inf = _parse_number('1e999')
_______________________ test_accuracy_direction_default ________________________
tests/test_measurement_integrity.py:20: in test_accuracy_direction_default
    assert not t.lower_is_better
E   AssertionError: assert not True
E    +  where True = TidyTable(name='table.csv', axes={'method': Axis(name='method', kind='unordered_cat', order=None)}, entity_axis='method', metric_name='accuracy', lower_is_better=True, rows=[{'method': 'A', 'value': 0.9}, {'method': 'B', 'value': 0.8}]).lower_is_better
____________________ test_monotonic_named_metrics_not_lost _____________________
tests/test_measurement_integrity.py:25: in test_monotonic_named_metrics_not_lost
    assert sorted(t.metric_name for t in tables)==['accuracy','latency']
E   AssertionError: assert ['accuracy'] == ['accuracy', 'latency']
E     
E     Right contains one more item: 'latency'
E     Use -v to get more diff
___________________ test_same_scale_different_metrics_split ____________________
tests/test_measurement_integrity.py:31: in test_same_scale_different_metrics_split
    assert sorted(t.metric_name for t in read_tables(p))==['accuracy','loss']
E   AssertionError: assert ['accuracy'] == ['accuracy', 'loss']
E     
E     Right contains one more item: 'loss'
E     Use -v to get more diff
____________________ test_raw_terminal_precision_preserved _____________________
tests/test_measurement_integrity.py:36: in test_raw_terminal_precision_preserved
    assert t.rows[0].get('_raw')=='1.000'
E   AssertionError: assert None == '1.000'
E    +  where None = <built-in method get of dict object at 0x7f627c2eb980>('_raw')
E    +    where <built-in method get of dict object at 0x7f627c2eb980> = {'idx': 0.0, 'value': 1.0}.get
__________________ test_bounded_values_not_benford_accusation __________________
tests/test_measurement_integrity.py:43: in test_bounded_values_not_benford_accusation
    assert result.status=='not_applicable'
E   AssertionError: assert 'finding' == 'not_applicable'
E     
E     - not_applicable
E     + finding
=========================== short test summary info ============================
FAILED tests/test_measurement_integrity.py::test_nonfinite_excluded[inf] - As...
FAILED tests/test_measurement_integrity.py::test_nonfinite_excluded[-inf] - A...
FAILED tests/test_measurement_integrity.py::test_nonfinite_excluded[1e999] - ...
FAILED tests/test_measurement_integrity.py::test_accuracy_direction_default
FAILED tests/test_measurement_integrity.py::test_monotonic_named_metrics_not_lost
FAILED tests/test_measurement_integrity.py::test_same_scale_different_metrics_split
FAILED tests/test_measurement_integrity.py::test_raw_terminal_precision_preserved
FAILED tests/test_measurement_integrity.py::test_bounded_values_not_benford_accusation
8 failed in 1.26s
```

## Regression after

```text
..........................................                               [100%]
42 passed in 0.66s
```

## Large example before

```text
1000-row learning curve: [('accuracy', 1000, True, ['threshold'])]
1000 fixed-precision values: [('benford', 'finding', 1000), ('terminal_digit', 'finding', 990)]
1000 bounded accuracy values: [('benford', 'finding'), ('terminal_digit', 'finding')]
Nonfinite import values: [inf, -inf, inf]
```

## Large example after

```text
1000-row learning curve: [('accuracy', 1000, False, ['threshold']), ('latency', 1000, True, ['threshold'])]
1000 fixed-precision values: [('benford', 'not_applicable', None), ('terminal_digit', 'finding', 1000)]
1000 bounded accuracy values: [('benford', 'not_applicable'), ('terminal_digit', 'ok')]
Nonfinite import values: [None, None, None]
```
