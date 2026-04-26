# NEJM AI Submission Package — SPICY-AI (n = 50)

**Manuscript:** "Clinical Evaluation of SPICY-AI in a Rapid Access Chest Pain Clinic: A Comparative Validation Study of a Novel, Locally Deployed AI Model versus Physicians and GPT-4o"

**Corresponding author:** Dr Thomas Moran (thomas.moran@ths.tas.gov.au)
**Public code repo:** <https://github.com/Tommy-Moran/SPICY-AI-Model>

---

## Quick reproducibility check (for reviewers)

```bash
git clone https://github.com/Tommy-Moran/SPICY-AI-Model.git
cd SPICY-AI-Model
pip install -r requirements.txt
python3 analysis_v3.py
```

This regenerates every statistic and every figure in the paper from the
de-identified `data/scores_long_v3.csv` alone — no raw clinical data,
no Excel workbooks, no external assets required.

---

## Submission checklist

| File | Upload slot on NEJM AI portal | Status |
|---|---|---|
| `cover_letter.docx` | Cover letter | Ready |
| `title_page.docx` | Title page (author details, declarations) | Ready |
| `manuscript_main.docx` | Main manuscript (double-spaced, line-numbered) | Ready |
| `manuscript_blinded.docx` | Blinded manuscript for peer review | Ready |
| `figure_legends.docx` | Figure legends (separate file) | Ready |
| `figures/Figure1A.tiff` | Figure 1A — mean Likert scores, 300 DPI | Ready |
| `figures/Figure1B.tiff` | Figure 1B — error/hallucination rates, 300 DPI | Ready |
| `figures/Figure2.tiff` | Figure 2 — Likert score distributions (box plots) | Ready |
| `figures/Figure3_pipeline.tiff` | Figure 3 — SPICY-AI pipeline diagram | Ready |
| `data_sharing_statement.md` | Paste into Data Availability portal field | Ready |
| `code_availability_statement.md` | Paste into Code Availability portal field | Ready |

### Data files (supplementary / GitHub repo)

| File | Description |
|---|---|
| `data/scores_long_v3.csv` | De-identified Likert scores — 150 rows (50 cases × 3 groups) |
| `data/demographics.csv` | De-identified patient demographics — 50 rows |
| `data/summary_v3.csv` | Mean, SD, median, IQR per domain per group |
| `data/mannwhitney_v3.csv` | Mann-Whitney U statistics + raw and Holm-adjusted p-values |
| `data/error_rates_v3.csv` | Fisher exact test results for minor/major error rates |
| `data/error_summary_v3.csv` | Error counts and rates by group |
| `data/stats_output_v3.txt` | Full human-readable statistics summary |
| `analysis_v3.py` | Fully reproducible analysis pipeline (Python) |

---

## Headline findings (n = 50)

| Domain | Physician | SPICY-AI | GPT-4o | Worst Holm-adjusted p (across 3 pairs) |
|---|---|---|---|---|
| Diagnostic accuracy | 3.32 ± 0.71 | **4.22 ± 0.62** | 3.80 ± 0.70 | 0.008 |
| Management appropriateness | 2.98 ± 0.59 | **4.20 ± 0.67** | 3.78 ± 0.65 | 0.008 |
| Documentation completeness | 2.50 ± 0.86 | **4.44 ± 0.54** | 3.88 ± 0.75 | < 0.001 |
| Documentation clarity | 3.06 ± 0.74 | **4.38 ± 0.57** | 4.04 ± 0.61 | 0.008 |

- **SPICY-AI > GPT-4o > Physician** on all four domains; all 12 pairwise comparisons remain significant (p ≤ 0.008) after Holm-Bonferroni adjustment across the 12 score tests.
- Scored by **4 blinded cardiology reviewers** for all 150 plans.
- **No significant differences in error rates** (major 2–4%, minor 14–18%; all Fisher exact p > 0.05). Note: with 1–2 major-error events per arm the study is not powered to detect safety differences; the null result is a feasibility signal, not evidence of equivalence.

---

## Methodological notes

- **Statistical approach.** Pairwise Mann-Whitney U (two-sided) on ordinal Likert scores; Holm-Bonferroni step-down adjustment across the 12 score comparisons. Fisher exact for minor/major error rates. Means/SDs reported alongside medians/IQRs for descriptive transparency, but inference is rank-based.
- **Rater design.** All 150 plans (50 cases × 3 sources) were independently scored by **four blinded cardiology reviewers**. The manuscript correctly reflects this.
- **Powering.** The study was designed as a feasibility/non-inferiority signal at a single centre; n = 50 is not powered to detect differences in major-error rates.
- **Framing.** Single-centre, single-clinic; external validity is addressed in the Limitations.

---

## Submission steps

1. Open the portal: <https://mc.manuscriptcentral.com/nejmai>
2. Article type: *Original Article*
3. Upload documents in the order listed in the checklist above
4. Paste statements into the Data Sharing and Code Availability fields
5. Complete author metadata; confirm Dr Moran as corresponding author
6. Confirm declarations: no conflicts, no external funding, HREC 2025_ETH01927
7. Submit

---

## NEJM AI limits checklist

- [x] Manuscript body ≤ 3,000 words
- [x] Structured abstract ≤ 250 words — 249 words
- [x] ≤ 5 figures + tables combined — 3 figures + 2 tables = 5 (at cap)
- [x] ≤ 50 references — 18
- [x] ≤ 50 authors — 4
- [x] Figures 300 DPI, submitted as TIFF
- [x] Blinded manuscript provided
- [x] Data sharing and code availability statements prepared

---

## Repository structure

```
SPICY-AI-Model/
├── README.md                        ← this file
├── requirements.txt                 ← pinned versions
├── analysis_v3.py                   ← fully reproducible stats pipeline
├── data/
│   ├── scores_long_v3.csv           ← 150-row de-identified Likert scores
│   ├── demographics.csv             ← 50-row de-identified patient demographics
│   ├── summary_v3.csv
│   ├── mannwhitney_v3.csv           ← raw + Holm-adjusted p-values
│   ├── error_rates_v3.csv
│   ├── error_summary_v3.csv
│   └── stats_output_v3.txt
├── figures/
│   ├── Figure1A.png / .pdf / .tiff
│   ├── Figure1B.png / .pdf / .tiff
│   ├── Figure2.png / .pdf / .tiff
│   └── Figure3_pipeline.png / .pdf / .tiff
└── SPICY_AI/
    ├── prompt.txt                   ← full RACPC system prompt (verbatim)
    ├── spicy_ai.py                  ← RAG-LLM pipeline (pinned model digest, seed)
    ├── rag_config.py                ← knowledge-base manifest and indexing helper
    ├── requirements_spicy.txt       ← pinned SPICY-AI Python dependencies
    ├── Dockerfile                   ← reproducibility container
    └── knowledge_base/
        ├── README.md                ← describes guideline files and DUA
        └── download_guidelines.sh   ← fetches the public guideline PDFs
```

**Not included in the repo**: patient clinical summaries, physician plan text, SPICY-AI or GPT-4o generated plans, raw scoring workbooks. These contain clinical detail about RHH patients and are covered by HREC 2025_ETH01927. The RHH institutional protocol is available under a data-use agreement — contact the corresponding author.

---

*Package prepared: 26 April 2026 | Python 3.10/3.13, pandas 2.2.3, scipy 1.17.1, matplotlib 3.10.8, openpyxl 3.1.5*
