import csv, math
import pytest
from anomalynerd.ingest import read_csv, read_tables, _parse_number
from anomalynerd.model import MISSING, is_num
from anomalynerd.stat_tests import digit_tests

def write(tmp_path,header,rows):
    p=tmp_path/'table.csv'
    with p.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)
    return str(p)

@pytest.mark.parametrize('token',['inf','-inf','1e999'])
def test_nonfinite_excluded(token):
    assert _parse_number(token) is MISSING
    assert not is_num(float(token))

def test_accuracy_direction_default(tmp_path):
    t=read_csv(write(tmp_path,['method','accuracy'],[['A',.9],['B',.8]]))
    assert not t.lower_is_better

def test_monotonic_named_metrics_not_lost(tmp_path):
    p=write(tmp_path,['threshold','accuracy','latency'],[[i/100,.5+i/1000,100+i] for i in range(100)])
    tables=read_tables(p)
    assert sorted(t.metric_name for t in tables)==['accuracy','latency']
    assert all('threshold' in t.axes for t in tables)
    assert not next(t for t in tables if t.metric_name=='accuracy').lower_is_better

def test_same_scale_different_metrics_split(tmp_path):
    p=write(tmp_path,['method','accuracy','loss'],[[f'M{i}',.8+(i%7)/100,.3+(i%5)/100] for i in range(100)])
    assert sorted(t.metric_name for t in read_tables(p))==['accuracy','loss']

def test_raw_terminal_precision_preserved(tmp_path):
    p=write(tmp_path,['idx','value'],[[i,f'{1+i/100:.3f}'] for i in range(100)])
    t=read_csv(p,metric_col='value')
    assert t.rows[0].get('_raw')=='1.000'
    result=next(x for x in digit_tests(t) if x.kind=='terminal_digit')
    assert result.status=='finding' and result.evidence['n']==100

def test_bounded_values_not_benford_accusation(tmp_path):
    p=write(tmp_path,['idx','accuracy'],[[i,f'{.8+(i%10)/100:.2f}'] for i in range(100)])
    result=next(x for x in digit_tests(read_csv(p)) if x.kind=='benford')
    assert result.status=='not_applicable'
