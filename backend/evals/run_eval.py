"""Evaluate Groq LLMs on a CSV Q&A dataset using an LLM judge."""
from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

# ----- Config (override via environment) -----
_DEFAULT_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]
MODELS = (
    [m.strip() for m in os.environ["EVAL_MODELS"].split(",") if m.strip()]
    if os.environ.get("EVAL_MODELS")
    else _DEFAULT_MODELS
)
JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "llama-3.3-70b-versatile")
REQUEST_DELAY = float(os.environ.get("EVAL_REQUEST_DELAY", "0.5"))
MAX_RETRIES = 3
BASE_BACKOFF = 1.0  # seconds

_THIS_DIR = Path(__file__).resolve().parent
# The dataset and .env both live in the Learning.AI root, two levels up.
QA_PATH = _THIS_DIR.parent.parent / "qa.csv"
ENV_PATH = _THIS_DIR.parent.parent / ".env"
RESULTS_DIR = _THIS_DIR / "results"

# qa.csv column names mapped to internal record keys.
QUESTION_COL = "Question"
ANSWER_COL = "Correct_Answer"
CATEGORY_COL = "Topic"

RESULT_FIELDS = [
    "model", "id", "category", "question",
    "expected_answer", "model_answer", "verdict", "reason",
]


def load_dataset(path: str) -> list[dict]:
    """Read qa.csv. Requires the Question and Correct_Answer columns.

    Topic maps to category (default ""); the 1-based source-row number becomes
    id. Rows with no question are skipped. Other columns are ignored.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        missing = [c for c in (QUESTION_COL, ANSWER_COL) if c not in fields]
        if missing:
            raise ValueError(
                f"qa.csv is missing required column(s): {', '.join(missing)}"
            )
        rows = []
        for i, raw in enumerate(reader, start=1):
            question = (raw.get(QUESTION_COL) or "").strip()
            expected = (raw.get(ANSWER_COL) or "").strip()
            if not question:
                continue
            rows.append({
                "id": str(i),
                "category": (raw.get(CATEGORY_COL) or "").strip(),
                "question": question,
                "expected_answer": expected,
            })
        return rows
