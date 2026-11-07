#!/usr/bin/env bash
# report/report.md -> report/report.pdf (pandoc -> docx -> LibreOffice). Fill every ‹TBD› first.
set -euo pipefail
if grep -q '‹' report/report.md; then echo "report.md still contains ‹…› placeholders"; [ "${FORCE:-0}" = 1 ] || exit 1; fi
pandoc report/report.md -o report/report.docx
soffice --headless --convert-to pdf --outdir report report/report.docx
pdfinfo report/report.pdf | grep Pages
