"""Three large synthetic research tables, no article accuracy claim."""
import csv,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from anomalynerd.ingest import read_csv,read_tables,_parse_number
from anomalynerd.stat_tests import digit_tests
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'learning_curve.csv'
    with p.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['threshold','accuracy','latency'])
        w.writerows([[i/1000,.5+i/10000,100+i] for i in range(1000)])
    tables=read_tables(str(p))
    print('1000-row learning curve:',[(t.metric_name,len(t.rows),t.lower_is_better,sorted(t.axes)) for t in tables])
    p=Path(tmp)/'reported_precision.csv'
    with p.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['idx','value']);w.writerows([[i,f'{1+i/100:.3f}'] for i in range(1000)])
    results=digit_tests(read_csv(str(p),metric_col='value'))
    print('1000 fixed-precision values:',[(r.kind,r.status,r.evidence.get('n')) for r in results])
    p=Path(tmp)/'bounded_accuracy.csv'
    with p.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['idx','accuracy']);w.writerows([[i,f'{.8+(i%10)/100:.2f}'] for i in range(1000)])
    print('1000 bounded accuracy values:',[(r.kind,r.status) for r in digit_tests(read_csv(str(p)))])
    print('Nonfinite import values:',[_parse_number(x) for x in ['inf','-inf','1e999']])
