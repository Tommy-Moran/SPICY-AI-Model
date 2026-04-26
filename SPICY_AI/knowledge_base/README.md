# SPICY-AI Knowledge Base

This directory holds the four guideline documents used to ground SPICY-AI's retrieval layer
in the published study. Three are publicly available; one is an institutional protocol.

## Files used in the published study

| File | Source | Redistributable |
|---|---|---|
| `aha_chest_pain_2021.pdf` | 2021 AHA/ACC Chest Pain Guidelines | Yes — obtain from publisher |
| `aha_cad_2021.pdf` | 2021 AHA/ACC Coronary Artery Revascularization Guidelines | Yes — obtain from publisher |
| `cdc_dyslipidaemia_2021.pdf` | 2021 CDC Cholesterol Management Guidelines | Yes — obtain from publisher |
| `rhh_racpc_instructions.docx` | RHH RACPC Institutional Protocols | **No — data-use agreement required** |

## Obtaining the guideline PDFs

Run `bash download_guidelines.sh` for the canonical URLs. Because these guidelines require
accepting publisher terms, the script prints the URL for each file rather than downloading
automatically. Open each URL in a browser, save the PDF with the filename shown above, and
place it in this directory.

## Obtaining the institutional protocol

`rhh_racpc_instructions.docx` contains RHH-specific operating procedures and is the property
of the Royal Hobart Hospital Department of Cardiology. It is available under a data-use
agreement. Contact the corresponding author (thomas.moran@ths.tas.gov.au); requests will
be considered subject to RHH HREC and Department of Cardiology approval.

## Indexing

Once all files are present, build the FAISS vector store:

```bash
python rag_config.py --check   # confirm all four files present
python rag_config.py --index   # build vectorstore/
python rag_config.py --test    # smoke-test retrieval
```

## Guideline-only mode

SPICY-AI will run with only the three public PDFs. Performance may be reduced on cases
requiring institution-specific pathways (local troponin thresholds, referral destinations).
