"""
SPICY-AI: Smart Platform for Integrated Chest Pain Evaluation Yielded by Artificial Intelligence
=========================================================================================================
A locally deployed Retrieval-Augmented Generation (RAG) LLM for the Royal Hobart Hospital
Rapid Access Chest Pain Clinic (RACPC).

Architecture:
  - Base model  : DeepSeek-R1 14B (via Ollama, running on-premises, Q4_K_M quantisation)
  - Embeddings  : sentence-transformers (all-MiniLM-L6-v2)
  - Vector store: FAISS
  - Framework   : LangChain

Knowledge base (see knowledge_base/README.md):
  - 2021 AHA/ACC Chest Pain Guidelines
  - 2021 AHA/ACC Coronary Artery Disease Guidelines
  - 2021 CDC Dyslipidaemia Guidelines
  - RHH RACPC Institutional Protocols (not redistributed; see data-use agreement)

Usage:
    python spicy_ai.py --case "Patient clinical notes here..."

Requirements: see requirements_spicy.txt
"""

import argparse
import re
import os
from pathlib import Path

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter

# ── Configuration ────────────────────────────────────────────────────────────
KNOWLEDGE_BASE_DIR = Path(__file__).parent / "knowledge_base"
VECTOR_STORE_PATH  = Path(__file__).parent / "vectorstore"
PROMPT_PATH        = Path(__file__).parent / "prompt.txt"

# Model + retrieval configuration used in the published study.
# These values are load-bearing for reproducibility — change them and you
# will get different SPICY-AI outputs.
EMBED_MODEL    = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_REVISION = "8b3219a92973c328a8e22fadcfa821b5dc75636a"  # HF commit pin
OLLAMA_MODEL   = "deepseek-r1:14b"
# Verify model digest before running:
#   ollama show deepseek-r1:14b --modelfile | head -1
# Expected digest used in the published study:
EXPECTED_OLLAMA_DIGEST = "sha256:6e9f90f02bb3b39b59e81916e8cfce9deb45aeaeb9a54a5be4414486b907dc1e"
OLLAMA_BASE    = "http://localhost:11434"
CHUNK_SIZE     = 1000
CHUNK_OVERLAP  = 200
TOP_K          = 6      # number of retrieved context chunks
RNG_SEED       = 42     # for any stochastic retrieval/sampling
MAX_WORDS      = 200    # plan output cap (enforced programmatically after generation)


# ── Output post-processing ────────────────────────────────────────────────────

def postprocess_plan(raw: str) -> str:
    """Strip chain-of-thought blocks and enforce the 200-word output cap.

    DeepSeek-R1 wraps internal reasoning in <think>...</think> tags.
    These must be removed before the plan is returned or stored.
    """
    # Remove <think>...</think> blocks (greedy, handles multiline)
    clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Strip any leading "Plan:" echo the model may prepend
    if clean.lower().startswith("plan:"):
        clean = clean[5:].strip()

    # Enforce word cap: truncate at MAX_WORDS while preserving whole sentences
    words = clean.split()
    if len(words) > MAX_WORDS:
        truncated = " ".join(words[:MAX_WORDS])
        # Try to end at the last complete sentence within the limit
        last_stop = max(truncated.rfind("."), truncated.rfind("•"))
        if last_stop > len(truncated) // 2:
            clean = truncated[: last_stop + 1].strip()
        else:
            clean = truncated.rstrip(",") + "…"

    return clean


def validate_plan(plan: str) -> list[str]:
    """Return a list of QA warnings for the generated plan."""
    warnings = []
    wc = len(plan.split())
    if wc < 20:
        warnings.append(f"Plan suspiciously short ({wc} words) — possible generation failure.")
    if wc > MAX_WORDS:
        warnings.append(f"Plan exceeds {MAX_WORDS}-word cap ({wc} words) — truncation failed.")
    if "<think>" in plan.lower():
        warnings.append("Plan contains residual <think> tags — stripping failed.")
    if re.search(r"\binvent\b|\bassume\b|\bI don't have\b|\bI cannot\b", plan, re.I):
        warnings.append("Plan may contain hedge language suggesting missing information.")
    return warnings


# ── RAG pipeline ─────────────────────────────────────────────────────────────

def load_documents(kb_dir: Path) -> list:
    """Load all PDFs and DOCX files from the knowledge-base directory."""
    docs = []
    loaders = {".pdf": PyPDFLoader, ".docx": Docx2txtLoader}
    for fpath in sorted(kb_dir.glob("**/*")):
        suffix = fpath.suffix.lower()
        if suffix in loaders:
            print(f"  Loading: {fpath.name}")
            docs.extend(loaders[suffix](str(fpath)).load())
    if not docs:
        raise FileNotFoundError(
            f"No PDF or DOCX files found in {kb_dir}. "
            "See knowledge_base/README.md for setup instructions."
        )
    return docs


def build_vectorstore(docs: list, embed_model: str, store_path: Path) -> FAISS:
    """Chunk documents and build (or rebuild) the FAISS vector store."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(docs)
    print(f"  Split into {len(chunks)} chunks")
    embeddings = HuggingFaceEmbeddings(model_name=embed_model)
    vs = FAISS.from_documents(chunks, embeddings)
    vs.save_local(str(store_path))
    print(f"  Vector store saved to {store_path}")
    return vs


def load_or_build_vectorstore(kb_dir: Path, embed_model: str, store_path: Path) -> FAISS:
    embeddings = HuggingFaceEmbeddings(model_name=embed_model)
    if store_path.exists():
        print("Loading existing vector store…")
        return FAISS.load_local(
            str(store_path), embeddings, allow_dangerous_deserialization=True
        )
    print("Building vector store from knowledge-base documents…")
    docs = load_documents(kb_dir)
    return build_vectorstore(docs, embed_model, store_path)


def build_chain(vectorstore: FAISS, system_prompt: str) -> object:
    """Assemble the retrieval chain using the non-deprecated LangChain API."""
    llm = Ollama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE,
        temperature=0.1,   # low temperature for clinical reproducibility
        num_predict=3000,  # DeepSeek-R1 emits <think>...</think> chain-of-thought before the
                           # plan; the think block alone can exceed 1000 tokens. num_predict
                           # must be large enough to complete both. The plan itself is capped
                           # at MAX_WORDS (200) programmatically in postprocess_plan().
        num_ctx=8192,      # system prompt + 6 RAG chunks easily exceeds the default 4096-token
                           # context window; raise to 8192 to avoid mid-generation truncation.
    )

    # System message includes the RACPC instructions and retrieved context slot.
    # DeepSeek-R1 chain-of-thought is stripped in postprocess_plan().
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            system_prompt
            + "\n\nThe following guideline excerpts have been retrieved from your "
            "knowledge base to assist with this case. Use them to ground your plan:\n\n"
            "{context}",
        ),
        ("human", "{input}"),
    ])

    combine_docs_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(
        vectorstore.as_retriever(search_kwargs={"k": TOP_K}),
        combine_docs_chain,
    )


# ── Main entry point ─────────────────────────────────────────────────────────

def run_spicy_ai(case_notes: str, rebuild: bool = False) -> str:
    """Generate a clinical plan for the supplied RACPC case notes."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"System prompt not found at {PROMPT_PATH}")
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()

    if rebuild and VECTOR_STORE_PATH.exists():
        import shutil
        shutil.rmtree(VECTOR_STORE_PATH)

    vectorstore = load_or_build_vectorstore(KNOWLEDGE_BASE_DIR, EMBED_MODEL, VECTOR_STORE_PATH)
    chain = build_chain(vectorstore, system_prompt)
    result = chain.invoke({"input": case_notes})

    raw_plan = result.get("answer", "").strip()
    plan = postprocess_plan(raw_plan)

    warnings = validate_plan(plan)
    if warnings:
        for w in warnings:
            print(f"  [QA WARNING] {w}")

    return plan


def main():
    parser = argparse.ArgumentParser(
        description="SPICY-AI: RAG-LLM clinical plan generator for RHH RACPC"
    )
    parser.add_argument(
        "--case", type=str, required=True,
        help="De-identified clinical notes for the patient"
    )
    parser.add_argument(
        "--rebuild-index", action="store_true",
        help="Force rebuild of the FAISS vector store from knowledge-base documents"
    )
    args = parser.parse_args()

    print("\n=== SPICY-AI — Generating clinical plan ===\n")
    plan = run_spicy_ai(args.case, rebuild=args.rebuild_index)
    print("Plan:\n")
    print(plan)
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
