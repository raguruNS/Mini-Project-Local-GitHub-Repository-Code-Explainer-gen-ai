"""Clone a GitHub repo, pick the relevant source files and build an LLM-ready context."""
import os
import shutil
import tempfile
from collections import Counter
from typing import Dict, List, Tuple

from git import Repo

from . import config

IGNORE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build",
    ".idea", ".vscode", "target", "vendor", ".next", ".pytest_cache", "site-packages",
    "coverage", "migrations", "static", "assets", "images", "docs",
}
IGNORE_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock",
    "composer.lock", "Cargo.lock", "go.sum",
}
CODE_EXT = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript (React)", ".ts": "TypeScript",
    ".tsx": "TypeScript (React)", ".java": "Java", ".c": "C", ".cpp": "C++", ".h": "C/C++ header",
    ".cs": "C#", ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".kt": "Kotlin",
    ".swift": "Swift", ".html": "HTML", ".css": "CSS", ".sql": "SQL", ".sh": "Shell",
    ".ipynb": "Jupyter Notebook", ".vue": "Vue", ".dart": "Dart",
}
DOC_CONFIG = {
    "readme.md", "readme.rst", "readme.txt", "readme", "requirements.txt", "package.json",
    "pyproject.toml", "pom.xml", "build.gradle", "cargo.toml", "go.mod", "composer.json",
    "gemfile", "dockerfile", "docker-compose.yml", "setup.py",
}
ENTRY_NAMES = {
    "main", "app", "index", "server", "manage", "run", "cli", "__main__", "routes", "models",
}


def clone_repo(url: str) -> str:
    """Shallow-clone `url` into a temp dir and return its path."""
    tmp = tempfile.mkdtemp(prefix="repo_explainer_")
    try:
        Repo.clone_from(url, tmp, depth=1)
    except Exception as exc:
        cleanup(tmp)
        raise RuntimeError(f"Could not clone repository: {exc}") from exc
    return tmp


def cleanup(path: str) -> None:
    def _onerror(func, p, _exc):  # Windows: .git files are read-only
        try:
            os.chmod(p, 0o700)
            func(p)
        except Exception:
            pass
    shutil.rmtree(path, onerror=_onerror)


def _priority(rel_path: str) -> int:
    """Lower number = more important."""
    name = os.path.basename(rel_path).lower()
    stem = os.path.splitext(name)[0]
    depth = rel_path.count(os.sep)
    if name.startswith("readme"):
        return 0
    if name in DOC_CONFIG:
        return 1
    if stem in ENTRY_NAMES:
        return 2 + depth
    return 10 + depth


def collect_files(repo_path: str) -> List[str]:
    """Return relative paths of relevant files, most important first."""
    found: List[str] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for f in files:
            if f in IGNORE_FILES:
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, repo_path)
            ext = os.path.splitext(f)[1].lower()
            if ext not in CODE_EXT and f.lower() not in DOC_CONFIG:
                continue
            try:
                if os.path.getsize(full) > config.MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            found.append(rel)
    found.sort(key=lambda p: (_priority(p), p))
    return found[: config.MAX_FILES]


def read_file(repo_path: str, rel: str) -> str:
    try:
        with open(os.path.join(repo_path, rel), "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return ""
    if "\x00" in text:  # binary
        return ""
    if len(text) > config.MAX_CHARS_PER_FILE:
        text = text[: config.MAX_CHARS_PER_FILE] + "\n... [truncated]"
    return text


def detect_languages(files: List[str]) -> List[str]:
    c = Counter(CODE_EXT[os.path.splitext(f)[1].lower()] for f in files
                if os.path.splitext(f)[1].lower() in CODE_EXT)
    return [lang for lang, _ in c.most_common()]


def file_tree(repo_path: str, limit: int = 60) -> str:
    lines: List[str] = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS and not d.startswith("."))
        rel_root = os.path.relpath(root, repo_path)
        depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
        if depth > 3:
            continue
        if rel_root != ".":
            lines.append(f"{'  ' * (depth - 1)}{os.path.basename(root)}/")
        for f in sorted(files):
            if not f.startswith("."):
                lines.append(f"{'  ' * depth}{f}")
        if len(lines) >= limit:
            lines.append("...")
            break
    return "\n".join(lines[: limit + 1])


def build_context(repo_path: str) -> Tuple[str, List[str], List[str]]:
    """Return (context_text, files_used, languages)."""
    all_files = collect_files(repo_path)
    languages = detect_languages(all_files)
    parts: List[str] = [f"FOLDER STRUCTURE:\n{file_tree(repo_path)}\n"]
    used: List[str] = []
    budget = config.CONTEXT_CHAR_BUDGET - len(parts[0])
    for rel in all_files:
        text = read_file(repo_path, rel)
        if not text.strip():
            continue
        block = f"\n=== FILE: {rel} ===\n{text}\n"
        if len(block) > budget:
            if budget < 500:
                break
            block = block[:budget]
        parts.append(block)
        used.append(rel)
        budget -= len(block)
        if budget <= 0:
            break
    return "".join(parts), used, languages


def process_repo(url: str) -> Dict:
    path = clone_repo(url)
    try:
        context, used, languages = build_context(path)
    finally:
        cleanup(path)
    return {"context": context, "files": used, "languages": languages}
