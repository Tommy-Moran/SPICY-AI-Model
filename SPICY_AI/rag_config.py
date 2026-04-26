"""
RAG configuration and knowledge-base ingestion helper for SPICY-AI.

Run this script once to index the knowledge base:
    python rag_config.py --index

Then verify the index is working:
    python rag_config.py --test
"""

from pathlib import Path
import argparse

# ── Knowledge-base file manifest ─────────────────────────────────────────────
# Files listed here are the guideline sources used in the published study.
# Place copies in the knowledge_base/ directory before indexing.
# The RHH-specific institutional protocols are NOT redistributed (see README).

KNOWLEDGE_BASE_MANIFEST = {
    # Publicly available guidelines (obtainable from publisher websites)
    "aha_chest_pain_2021.pdf": {
        "source": "American Heart Association / American College of Cardiology",
        "title":  "2021 AHA/ACC/ASE/CHEST/SAEM/NMA/PCNA Guideline for the Evaluation and "
                  "Diagnosis of Chest Pain",
        "url":    "https://doi.org/10.1016/j.jacc.2021.07.053",
        "redistributable": True,
    },
    "aha_cad_2021.pdf": {
        "source": "American Heart Association / American College of Cardiology",
        "title":  "2021 ACC/AHA/SCAI Guideline for Coronary Artery Revascularization",
        "url":    "https://doi.org/10.1161/CIR.0000000000001038",
        "redistributable": True,
    },
    "cdc_dyslipidaemia_2021.pdf": {
        "source": "Centers for Disease Control and Prevention",
        "title":  "2021 CDC Guideline for the Management of Blood Cholesterol",
        "url":    "https://www.cdc.gov/cholesterol/guidelines/index.html",
        "redistributable": True,
    },
    # Institutional protocol (not redistributed)
    "rhh_racpc_instructions.docx": {
        "source": "Royal Hobart Hospital Department of Cardiology",
        "title":  "RHH Rapid Access Chest Pain Clinic Institutional Protocols",
        "url":    None,
        "redistributable": False,
        "note":   "Available under data-use agreement. Contact corresponding author."
    },
}

# ── Embedding / retrieval settings ───────────────────────────────────────────
RAG_CONFIG = {
    "embed_model":    "sentence-transformers/all-MiniLM-L6-v2",
    "chunk_size":     1000,
    "chunk_overlap":  200,
    "top_k":          6,
    "ollama_model":   "deepseek-r1:14b",
    "ollama_base":    "http://localhost:11434",
    "temperature":    0.1,
    "num_predict":    3000,  # DeepSeek-R1 emits <think>...</think> reasoning before the plan;
                             # must be large enough to complete both. Plan capped at max_words.
    "num_ctx":        8192,  # system prompt + 6 RAG chunks exceeds default 4096-token window
    "max_words":      200,   # enforced programmatically in postprocess_plan()
}


def check_knowledge_base():
    kb_dir = Path(__file__).parent / "knowledge_base"
    print(f"Knowledge-base directory: {kb_dir}\n")
    present, missing = [], []
    for fname, meta in KNOWLEDGE_BASE_MANIFEST.items():
        fpath = kb_dir / fname
        if fpath.exists():
            present.append(fname)
            print(f"  ✅  {fname}")
        else:
            tag = "(not redistributed)" if not meta["redistributable"] else "(MISSING)"
            missing.append(fname)
            print(f"  ❌  {fname}  {tag}")
            if meta.get("url"):
                print(f"       → {meta['url']}")
    print(f"\n{len(present)}/{len(KNOWLEDGE_BASE_MANIFEST)} files present")
    return len(missing) == 0 or all(
        not KNOWLEDGE_BASE_MANIFEST[f]["redistributable"] for f in missing
    )


def index_knowledge_base():
    from spicy_ai import load_documents, build_vectorstore, KNOWLEDGE_BASE_DIR, VECTOR_STORE_PATH, EMBED_MODEL
    print("Indexing knowledge base…")
    docs = load_documents(KNOWLEDGE_BASE_DIR)
    build_vectorstore(docs, EMBED_MODEL, VECTOR_STORE_PATH)
    print("✅  Index built successfully.")


def test_retrieval():
    from spicy_ai import load_or_build_vectorstore, KNOWLEDGE_BASE_DIR, VECTOR_STORE_PATH, EMBED_MODEL
    from langchain_community.embeddings import HuggingFaceEmbeddings
    vs = load_or_build_vectorstore(KNOWLEDGE_BASE_DIR, EMBED_MODEL, VECTOR_STORE_PATH)
    query = "LDL target for high cardiovascular risk patient on statin"
    docs = vs.similarity_search(query, k=3)
    print(f"Test query: '{query}'\nTop {len(docs)} results:")
    for i, d in enumerate(docs, 1):
        print(f"\n  [{i}] {d.metadata.get('source','?')} p.{d.metadata.get('page','?')}")
        print(f"      {d.page_content[:200].strip()}…")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check",  action="store_true", help="Check KB file presence")
    parser.add_argument("--index",  action="store_true", help="Build/rebuild vector store")
    parser.add_argument("--test",   action="store_true", help="Test retrieval with sample query")
    args = parser.parse_args()

    if args.check or not any(vars(args).values()):
        check_knowledge_base()
    if args.index:
        index_knowledge_base()
    if args.test:
        test_retrieval()
