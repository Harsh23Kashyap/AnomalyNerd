# Nested HTML table coverage

This follow-on to HTML-input PR30 rejects an outer table containing a nested table, with an explicit not-analyzed note. Previously a nested table reset the outer row and could silently discard numeric cells. Independent flat tables and prose after the rejected table remain available. Numeric checks and ranking priorities are unchanged.

## Verification

At PR30 head e2aa949a6e11f9975871d536c7d64e3d846b9fd2:

- Eleven new regression cases: original source 7 failed / 4 passed; fixed source 11 passed.
- HTML cases, including the existing real web-upload TestClient path: 28 passed, one dependency deprecation warning.
- Full local suite with declared dependencies: 571 passed, 8 failed, 11 subtests passed. The same eight caption failures reproduce against the original HTML module. They require the optional docling backend, which was absent.
- An isolated overlay of PR31's three current test guard files at f917028fe085b051d67308f87704c290d3a7f751: 571 passed, 8 skipped, 11 subtests passed. The overlay was removed after the run and is not part of this change.

These results do not qualify docling behavior, visual browser presentation, or arbitrary malformed/nested HTML support. Nested tables are reported as unsupported, not silently flattened into evidence. No merge, deployment, or provider calls.
