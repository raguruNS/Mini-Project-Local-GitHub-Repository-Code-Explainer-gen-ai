"""Local LLM access: Ollama (HTTP) or Hugging Face Transformers (in-process)."""
import requests

from . import config

_hf_pipeline = None


def build_prompt(context: str, languages: list) -> str:
    return f"""You are a senior software engineer explaining a GitHub repository to a beginner.
Read the repository files below and explain the project in SIMPLE language.
Base everything ONLY on the provided files. Do not invent features.

Detected languages (from file extensions): {", ".join(languages) or "unknown"}

Write the answer in Markdown using exactly this structure:

## Project Overview
(2-3 sentences: what the project is and what problem it solves)

## What the application can do
(bullet list of the main features)

## Main Technologies
(bullet list of languages, frameworks, libraries and databases actually used)

## How it works
(short step-by-step explanation of how the parts talk to each other)

## Important Files
(bullet list: file name - what it does)

REPOSITORY CONTENT:
{context}
"""


def _ollama_generate(prompt: str) -> str:
    try:
        r = requests.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": config.TEMPERATURE,
                    "num_predict": config.MAX_NEW_TOKENS,
                    "num_ctx": 8192,
                },
            },
            timeout=config.LLM_TIMEOUT,
        )
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Cannot reach Ollama. Start it with 'ollama serve' and pull the model: "
            f"'ollama pull {config.OLLAMA_MODEL}'."
        ) from exc
    if r.status_code != 200:
        raise RuntimeError(f"Ollama error {r.status_code}: {r.text[:300]}")
    return r.json().get("response", "").strip()


def _hf_generate(prompt: str) -> str:
    global _hf_pipeline
    if _hf_pipeline is None:
        from transformers import pipeline  # imported lazily: heavy

        _hf_pipeline = pipeline(
            "text-generation", model=config.HF_MODEL, device_map="auto", torch_dtype="auto"
        )
    messages = [{"role": "user", "content": prompt}]
    out = _hf_pipeline(
        messages,
        max_new_tokens=config.MAX_NEW_TOKENS,
        do_sample=config.TEMPERATURE > 0,
        temperature=max(config.TEMPERATURE, 0.01),
    )
    return out[0]["generated_text"][-1]["content"].strip()


def model_name() -> str:
    return config.OLLAMA_MODEL if config.LLM_BACKEND == "ollama" else config.HF_MODEL


def generate(prompt: str) -> str:
    if config.LLM_BACKEND == "hf":
        return _hf_generate(prompt)
    return _ollama_generate(prompt)
