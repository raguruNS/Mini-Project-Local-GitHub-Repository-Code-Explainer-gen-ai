"""FastAPI backend.  Run:  uvicorn backend.main:app --reload --port 8000"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import llm, repo_processor
from .schemas import ExplainRequest, ExplainResponse

app = FastAPI(title="GitHub Repository Code Explainer", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "model": llm.model_name()}


@app.post("/explain", response_model=ExplainResponse)
def explain(req: ExplainRequest):
    # Sync endpoint -> FastAPI runs it in a worker thread, so slow cloning/LLM calls don't block.
    try:
        data = repo_processor.process_repo(req.repo_url)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not data["files"]:
        raise HTTPException(status_code=422, detail="No readable source files found in this repository.")

    try:
        explanation = llm.generate(llm.build_prompt(data["context"], data["languages"]))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return ExplainResponse(
        repo_url=req.repo_url,
        explanation=explanation,
        languages=data["languages"],
        files_analyzed=data["files"],
        model=llm.model_name(),
    )
