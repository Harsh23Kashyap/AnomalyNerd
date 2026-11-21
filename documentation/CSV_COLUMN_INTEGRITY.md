# CSV column integrity

Duplicate named column headers overwrote earlier values during CSV import, and
rows with more cells than the header silently discarded the extra values. The
import now rejects both ambiguous shapes before inference or detector
execution, while keeping main's tolerance for harmless shapes (maintainer
review on PR #19):

- Rejected: a duplicate NON-BLANK header (a named-column lookup could return
  the wrong source column).
- Rejected: any cell beyond the header width that contains data (those values
  would be silently discarded).
- Accepted, as on main: blank or whitespace-only column names, singly or
  repeated (they are unnamed positional columns; no name lookup can collide).
- Accepted, as on main: trailing empty or whitespace-only cells beyond the
  header width (they carry no values).

The error names the duplicate header or the row's ending line instead of
returning findings on a different table from the supplied file. Short rows,
quoted commas, leading comments, BOMs and blank rows retain their existing
behavior. Header names are not renamed or normalized. This does not fix
scientific labels or PDF extraction. The existing upload error remains
HTTP 500 with a detail message; this patch does not redesign that response
contract.

```sh
python -B -m unittest discover -s tests -p test_csv_column_integrity.py -v
python -B -m pytest -q -rs
```

The 22 offline tests give 8 failures/14 passes on unmodified main (5f40ba1)
and 22 passes with the fix, including `read_tables` and the real local upload
route; the 8 main failures are exactly the rejection behaviors this branch
adds. Ten repeats pass 220 checks. The full suite gives 304 passes/8 failures
on this branch, and the identical 8 tests fail on unmodified main in this
environment (they depend on external arXiv PDF fixtures and the optional
docling layout model). Those paths remain unqualified. This does not
establish that older PDF failures are fixed, or change scientific
labels/priority ranking. No models, manuscripts, paid runs, merge or
deployment are involved.
