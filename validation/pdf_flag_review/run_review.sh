#!/bin/sh
# Run the flag review on all four paper sets at once, with caching.
#   sh validation/pdf_flag_review/run_review.sh <pdf_dir> <cache_dir>
# <pdf_dir> holds every paper's PDF (they are downloaded there if missing). The first run takes
# about 30 minutes; later runs reuse Docling and unchanged detector results.
PDFS=${1:?pdf_dir}; CACHE=${2:?cache_dir}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$CACHE"
PY=${PYTHON:-python3}
for set in "" --heldout --fresh --fresh2; do
  "$PY" "$HERE/collect_flags.py" "$PDFS" $set --cache "$CACHE" > "$CACHE/run${set:-_dev}.log" 2>&1 &
done
wait
grep -h total "$CACHE"/run*.log
