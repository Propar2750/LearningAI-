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


def parse_judge_response(raw: str) -> tuple[str, str]:
    """Parse judge output into (verdict, reason).

    Accepts a bare JSON object or one embedded in surrounding text.
    Raises ValueError if it cannot be parsed or the verdict is not
    'correct'/'incorrect'.
    """
    text = (raw or "").strip()
    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                data = None
    if not isinstance(data, dict) or "verdict" not in data:
        raise ValueError(f"could not parse judge response: {raw!r}")
    verdict = str(data["verdict"]).strip().lower()
    if verdict not in ("correct", "incorrect"):
        raise ValueError(f"unexpected verdict {verdict!r} in: {raw!r}")
    reason = str(data.get("reason", "")).strip()
    return verdict, reason


def summarize(records: list[dict]) -> list[dict]:
    """Aggregate per model in first-seen order.

    accuracy = correct / (correct + incorrect) * 100, or None if that
    denominator is 0 (rendered as 'n/a').
    """
    order: list[str] = []
    stats: dict[str, dict] = {}
    for r in records:
        m = r["model"]
        if m not in stats:
            order.append(m)
            stats[m] = {"correct": 0, "incorrect": 0, "errors": 0}
        v = r["verdict"]
        if v == "correct":
            stats[m]["correct"] += 1
        elif v == "incorrect":
            stats[m]["incorrect"] += 1
        else:
            stats[m]["errors"] += 1
    summary = []
    for m in order:
        s = stats[m]
        graded = s["correct"] + s["incorrect"]
        accuracy = round(100.0 * s["correct"] / graded, 1) if graded else None
        summary.append({"model": m, **s, "accuracy": accuracy})
    return summary
