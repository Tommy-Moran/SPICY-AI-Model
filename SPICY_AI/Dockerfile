# SPICY-AI Docker image
# Reproduces the retrieval and generation pipeline against a public base model.
# NOTE: The RHH institutional protocol (rhh_racpc_instructions.docx) is NOT
# included. See knowledge_base/README.md for instructions on how to obtain it
# under a data-use agreement, or run without it (guideline-only mode).

FROM python:3.10-slim

# System deps
RUN apt-get update && apt-get install -y \
    curl build-essential git \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

WORKDIR /app

COPY requirements_spicy.txt .
RUN pip install --no-cache-dir -r requirements_spicy.txt

COPY . .

# Download embedding model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 11434

# Entry: start Ollama, pull model, index KB, then run SPICY-AI
CMD bash -c "\
  ollama serve & \
  sleep 5 && \
  ollama pull llama3:70b && \
  python rag_config.py --index && \
  echo 'SPICY-AI ready. Run: python spicy_ai.py --case \"<clinical notes>\"' && \
  tail -f /dev/null"
