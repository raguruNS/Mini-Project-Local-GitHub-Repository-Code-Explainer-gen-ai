"""Central configuration. Override any value with environment variables."""
import os

# "ollama" (default, easiest) or "hf" (Hugging Face Transformers, fully in-process)
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama").lower()

# Ollama settings
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# Hugging Face settings
HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")

# Generation settings
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "700"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "600"))

# Repository processing limits (small models have small context windows)
MAX_FILE_BYTES = 60_000          # skip individual files bigger than this
MAX_CHARS_PER_FILE = 2_500       # truncate each file to this many characters
CONTEXT_CHAR_BUDGET = int(os.getenv("CONTEXT_CHAR_BUDGET", "9000"))  # total code sent to LLM
MAX_FILES = 25
