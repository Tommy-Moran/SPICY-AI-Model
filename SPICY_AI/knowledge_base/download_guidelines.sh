#!/usr/bin/env bash
# Download the three publicly available guideline PDFs used in the published study.
#
# The institutional file (rhh_racpc_instructions.docx) is NOT downloadable here
# — it is available only under a data-use agreement; see README.md.
#
# Usage:  bash download_guidelines.sh
# Verify: shasum -a 256 *.pdf  and compare against checksums.sha256

set -euo pipefail
cd "$(dirname "$0")"

declare -A FILES=(
  [aha_chest_pain_2021.pdf]="https://doi.org/10.1016/j.jacc.2021.07.053"
  [aha_cad_2021.pdf]="https://doi.org/10.1161/CIR.0000000000001038"
  [cdc_dyslipidaemia_2021.pdf]="https://www.cdc.gov/cholesterol/guidelines/index.html"
)

for fname in "${!FILES[@]}"; do
  url="${FILES[$fname]}"
  if [[ -f "$fname" ]]; then
    echo "[skip] $fname already present"
    continue
  fi
  echo "[get ] $fname"
  echo "       URL: $url"
  echo "       These guidelines require accepting publisher terms — open the URL"
  echo "       in a browser, download the PDF, save as $fname in this directory."
done

echo
echo "After placing all three PDFs here, rebuild the vector store:"
echo "  python rag_config.py --index"
echo "Then verify retrieval:"
echo "  python rag_config.py --test"
