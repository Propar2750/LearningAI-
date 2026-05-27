"""Evaluate Groq LLMs on a CSV Q&A dataset using an LLM judge."""
from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

import groq
from groq import Groq
from dotenv import load_dotenv

# ----- Config (override via environment) -----
# Only models enabled for this Groq org work; others return 403. List the
# enabled ones with: client.models.list(). Override the set below via EVAL_MODELS.
_DEFAULT_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.1-8b-instant",
]
MODELS = (
    [m.strip() for m in os.environ["EVAL_MODELS"].split(",") if m.strip()]
    if os.environ.get("EVAL_MODELS")
    else _DEFAULT_MODELS
)
JUDGE_MODEL = os.environ.get(
    "EVAL_JUDGE_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)
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


def format_table(summary: list[dict]) -> str:
    """Render the per-model accuracy table as a string."""
    header = f"{'Model':<32}{'Correct':>9}{'Incorrect':>11}{'Errors':>8}{'Accuracy':>11}"
    lines = [header, "-" * len(header)]
    for s in summary:
        acc = "n/a" if s["accuracy"] is None else f"{s['accuracy']}%"
        lines.append(
            f"{s['model']:<32}{s['correct']:>9}{s['incorrect']:>11}"
            f"{s['errors']:>8}{acc:>11}"
        )
    return "\n".join(lines)


def write_results(records: list[dict], path: str) -> None:
    """Write one row per model x question to a CSV with RESULT_FIELDS columns."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in RESULT_FIELDS})


JUDGE_SYSTEM = (
    "You are a strict grader. You compare a candidate answer to a reference "
    "answer for a question and decide if the candidate is factually correct. "
    "Judge factual/semantic correctness, not wording, length, or style; a "
    "correct answer may be phrased differently from the reference. Respond with "
    "ONLY a JSON object and nothing else, in the form "
    '{"verdict": "correct" or "incorrect", "reason": "<one short sentence>"}.'
)


def build_judge_messages(question: str, expected: str, answer: str) -> list[dict]:
    user = (
        f"Question:\n{question}\n\n"
        f"Reference answer:\n{expected}\n\n"
        f"Candidate answer:\n{answer}\n\n"
        "Is the candidate answer correct?"
    )
    return [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": user},
    ]


def groq_chat(client: Groq, model: str, messages: list[dict]) -> str:
    """Call Groq chat completions with retry/backoff on API errors."""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=model, messages=messages, temperature=0,
            )
            return resp.choices[0].message.content or ""
        except groq.APIError as exc:  # base class for rate-limit/status/conn errors
            last_exc = exc
            if attempt == MAX_RETRIES - 1:
                break
            time.sleep(BASE_BACKOFF * (2 ** attempt))
    raise last_exc


def ask_model(client: Groq, model: str, question: str) -> str:
    return groq_chat(client, model, [{"role": "user", "content": question}])


def judge(client: Groq, question: str, expected: str, answer: str) -> tuple[str, str]:
    """Grade an answer. Never raises: returns ('error', detail) on failure."""
    messages = build_judge_messages(question, expected, answer)
    last_raw = ""
    for _ in range(2):  # one retry on unparseable JSON
        try:
            last_raw = groq_chat(client, JUDGE_MODEL, messages)
        except groq.APIError as exc:
            return "error", f"judge API error: {exc}"
        try:
            return parse_judge_response(last_raw)
        except ValueError:
            continue
    return "error", f"unparseable judge response: {last_raw[:200]!r}"


def main() -> None:
    load_dotenv(ENV_PATH)
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit(f"GROQ_API_KEY not found (looked in {ENV_PATH})")
    client = Groq(api_key=api_key)

    dataset = load_dataset(str(QA_PATH))
    if not dataset:
        raise SystemExit(f"No questions found in {QA_PATH}")
    print(f"Loaded {len(dataset)} questions; testing {len(MODELS)} model(s); "
          f"judge={JUDGE_MODEL}\n")

    records: list[dict] = []
    for model in MODELS:
        print(f"== {model} ==")
        for row in dataset:
            base = {
                "model": model, "id": row["id"], "category": row["category"],
                "question": row["question"], "expected_answer": row["expected_answer"],
            }
            try:
                answer = ask_model(client, model, row["question"])
                verdict, reason = judge(
                    client, row["question"], row["expected_answer"], answer
                )
            except groq.APIError as exc:
                answer, verdict, reason = "", "error", f"model API error: {exc}"
            records.append({**base, "model_answer": answer,
                            "verdict": verdict, "reason": reason})
            print(f"  [{verdict}] #{row['id']} {row['question'][:50]}")
            time.sleep(REQUEST_DELAY)
        print()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"results_{ts}.csv"
    write_results(records, str(out_path))

    print(format_table(summarize(records)))
    print(f"\nDetailed results written to {out_path}")


if __name__ == "__main__":
    main()
