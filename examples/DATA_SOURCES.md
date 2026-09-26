# Example data sources

- **halley_ozone_october.csv / halley_ozone_long.csv** — Antarctic total column ozone at
  Halley, from the British Antarctic Survey (J.D. Shanklin), file ZOZ5699.DAT
  (https://legacy.bas.ac.uk/met/jds/ozone/). Monthly means, Dobson Units; 0 in the source
  means "no measurement" and is treated as missing. October column = the ozone-hole signature.
- **co2_annual.csv / co2_raw.csv** — NOAA GML Mauna Loa annual mean CO2
  (https://gml.noaa.gov/ccgg/trends/). `unc` = reported uncertainty (metadata, not an axis).
- **anscombe.csv** — Anscombe's quartet (Anscombe 1973), via the seaborn-data mirror.
- **wide.csv / long.csv** — tiny synthetic examples showing the two CSV shapes the tool accepts.
- **a research paper's results** tables are read directly from the paper's LaTeX source (not redistributed here);
  the loaders live in (internal loaders, not included).
- **newcomb_speed_of_light.csv** — Simon Newcomb's 1882 light passage-time measurements
  (deviations from 24800 ns), the canonical set from Stigler (1977) / R's MASS::newcomb.
  Contains the two well-known outliers (-44 and -2).
- **draft_lottery_1970.csv** — Monthly mean draft rank from the 1970 US draft lottery,
  computed from the JSE dataset (Starr 1997; raw draft70yr.dat). Documented non-randomness:
  ranks decline in later months (correlation -0.226, p~0).
- **thyroid_anomaly_rate_by_bin.csv / thyroid_feature_bins.csv** — summaries of the ADBench
  'thyroid' anomaly dataset (3772x6, 93 labeled anomalies), from
  github.com/Minqi824/ADBench. Each feature's values binned into deciles; value = anomaly rate
  per bin. Ground truth: anomalies concentrate in extreme bins (feat2 top, feat3/4/6 bottom).
- **income_by_education.csv** — US median annual income by highest education level (NCES Digest
  of Education Statistics, 1993 dollars). Education is ordered; income rises with it except
  Doctorate < Professional.
- **product_tier_ratings.csv** — small illustrative table: product rating by tier (Premium >
  Standard) across 8 regions; Premium beats Standard in 7/8, one exception. Tests the
  categorical-order-exception detector.
