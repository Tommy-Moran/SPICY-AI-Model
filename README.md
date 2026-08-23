# SPICY-AI: Smart Platform for Integrated Chest Pain Evaluation Yielded by AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

A locally deployed, specialty-specific Retrieval-Augmented Generation (RAG) small language model (SLM) for generating Rapid Access Chest Pain Clinic (RACPC) **written management plans**. The base model is **DeepSeek-R1-Distill-Qwen-14B** (Ollama tag `deepseek-r1:14b`, Q4_K_M), run on-premises.

This repository is the **inference package**: code, study prompts, and retrieval settings so you can run SPICY-AI on your own de-identified cases. It is not a public dump of the evaluation score file.

> **Associated manuscript (prepared for NEJM AI):** Moran T, Lees C, Hoang W, Bradley M, Martin W, Black A. *Clinical Evaluation of SPICY-AI in a Rapid Access Chest Pain Clinic: A Comparative Validation Study of a Locally Deployed Retrieval-Augmented Small Language Model versus Physicians and GPT-4o.* A College ATRP on the same study is a training assessment, not a journal publication.

---

## Study scores (available on request)

De-identified Likert scores and error flags from the n = 50 evaluation are **not** in this repository. The public tree is for model reuse, not for reconstructing the paper analysis from a score table.

The score file is available from the corresponding author on request for bona fide verification of the published tables: TommyMoran@gmail.com.

---

## Published results (n = 50 cases, 150 plans)

As reported in the manuscript. These summary figures are not a substitute for the score file.

| Domain | Physician | GPT-4o | **SPICY-AI** |
|---|:---:|:---:|:---:|
| Diagnostic accuracy | 3.04 ± 0.64 | 3.64 ± 0.60 | **4.12 ± 0.72** |
| Management appropriateness | 2.76 ± 0.62 | 3.56 ± 0.64 | **4.00 ± 0.86** |
| Documentation completeness | 2.28 ± 0.70 | 3.62 ± 0.67 | **4.20 ± 0.70** |
| Documentation clarity | 2.72 ± 0.57 | 3.76 ± 0.56 | **4.18 ± 0.60** |

Primary analysis: Wilcoxon signed-rank, paired by case; Holm–Bonferroni across 12 Likert tests. Worst adjusted p = **0.006**. Major error rates: SPICY-AI 4%, physician 10%, GPT-4o 10% (McNemar exact p ≥ 0.25).

---

## Repository structure

```
SPICY-AI-Model/
├── analysis.py                 # Stats script (needs the score file from the authors)
├── requirements.txt            # Python dependencies for analysis.py
├── figures/                    # Publication figures (pipeline + reported results)
└── SPICY_AI/
    ├── spicy_ai.py             # RAG inference
    ├── rag_config.py           # Knowledge-base manifest + index/test helpers
    ├── prompt.txt              # SPICY-AI system prompt used in the study
    ├── gpt4o_prompt.txt        # GPT-4o comparator prompt used in the study
    ├── requirements_spicy.txt
    └── knowledge_base/         # Manifest + download URLs (PDFs not redistributed)
```

---

## Running SPICY-AI

Requires [Ollama](https://ollama.ai) with **DeepSeek-R1-Distill-Qwen-14B** (`deepseek-r1:14b`):

```bash
git clone https://github.com/Tommy-Moran/SPICY-AI-Model
cd SPICY-AI-Model

ollama pull deepseek-r1:14b
ollama show deepseek-r1:14b --modelfile | head -1   # should match spicy_ai.py EXPECTED_OLLAMA_DIGEST

pip install -r SPICY_AI/requirements_spicy.txt
bash SPICY_AI/knowledge_base/download_guidelines.sh
# Place PDFs in SPICY_AI/knowledge_base/ as named there.
# Optionally add a local RACPC protocol as rhh_racpc_instructions.docx

python3 SPICY_AI/rag_config.py --check
python3 SPICY_AI/rag_config.py --index
python3 SPICY_AI/rag_config.py --test

python3 SPICY_AI/spicy_ai.py --case "65-year-old male, HTN, dyslipidaemia, presenting with atypical chest pain..."
```

**Prompts:** `SPICY_AI/prompt.txt` and `SPICY_AI/gpt4o_prompt.txt`. The GPT-4o API snapshot, temperature, and seed were not logged. In `spicy_ai.py`, `RNG_SEED = 42` is defined but was **not passed** to Ollama at generation.

**Knowledge base:** 2021 AHA/ACC chest-pain guideline, 2021 ACC/AHA/SCAI revascularization guideline, 2021 Canadian Cardiovascular Society dyslipidemia guideline, and the RHH RACPC protocol. Public PDFs come from the publishers. The institutional protocol is not redistributed; use your own local protocol.

---

## Ethics

University of Tasmania HREC Project ID H40430 (26 May 2026). Individual consent was waived for a retrospective audit of de-identified data.

---

## Citation

```
Moran T, Lees C, Hoang W, Bradley M, Martin W, Black A.
Clinical Evaluation of SPICY-AI in a Rapid Access Chest Pain Clinic:
A Comparative Validation Study of a Locally Deployed Retrieval-Augmented
Small Language Model versus Physicians and GPT-4o.
Manuscript prepared for NEJM AI, 2026.
GitHub: https://github.com/Tommy-Moran/SPICY-AI-Model
```

---

## License

MIT License. See [LICENSE](LICENSE).
