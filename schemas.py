"""Pydantic request/response models."""
import re
from typing import List
from pydantic import BaseModel, field_validator

GITHUB_RE = re.compile(r"^https://github\.com/[\w.\-]+/[\w.\-]+?(\.git)?/?$")


class ExplainRequest(BaseModel):
    repo_url: str

    @field_validator("repo_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not GITHUB_RE.match(v):
            raise ValueError(
                "Enter a valid GitHub URL like https://github.com/username/repository"
            )
        return v


class ExplainResponse(BaseModel):
    repo_url: str
    explanation: str
    languages: List[str]
    files_analyzed: List[str]
    model: str
