import pytest
from anomalynerd.detectors import detect_point_outliers
from anomalynerd.model import TidyTable, Axis


@pytest.mark.parametrize("missing", [True, False])
def test_categorical_outlier_keeps_full_coordinates(missing):
    rows = [{'group': 'g', 'method': f'm{i}', 'value': v}
            for i, v in enumerate([1, 1.01, 1.02, 1.03, 1.04, 20] + ([None] if missing else []))]
    table = TidyTable('synthetic', {'group': Axis('group', 'unordered_cat'),
                                  'method': Axis('method', 'unordered_cat')},
                      'method', 'score', False, rows)
    flags = [f for f in detect_point_outliers(table) if f.detail.get('mode') == 'categorical']
    assert len(flags) == 1
    assert flags[0].coords == {'group': 'g', 'method': 'm5'}


def test_single_axis_categorical_outlier_coordinates_are_not_empty():
    rows = [{'method': f'm{i}', 'value': v}
            for i, v in enumerate([1, 1.01, 1.02, 1.03, 1.04, 20])]
    table = TidyTable('synthetic', {'method': Axis('method', 'unordered_cat')},
                      'method', 'score', False, rows)
    flags = detect_point_outliers(table)
    assert len(flags) == 1
    assert flags[0].coords == {'method': 'm5'}
    assert flags[0].detail['at'] == 'm5'
