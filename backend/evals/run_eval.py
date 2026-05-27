"""Evaluate Groq LLMs on a CSV Q&A dataset using an LLM judge."""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import groq
from groq import Groq
from dotenv import load_dotenv

# ----- Config (override via environment) -----
# A "run" pairs a Groq model with a reasoning setting. ``label`` is the grouping
# key written to results (so the same model at different reasoning efforts stays
# distinct); ``model`` is the real id used for the API call and pricing lookup.
#
# Reasoning notes: gpt-oss-120b/20b accept reasoning_effort low|medium|high
# (default medium, can't be disabled) and do NOT support reasoning_format. qwen3
# accepts none|default|low|medium|high (none disables) and supports
# reasoning_format — we set "parsed" so message.content holds only the final
# answer. Llama models have no reasoning. Only models enabled for this Groq org
# work; others return 403 (list with client.models.list()).
#
# Defaults below are the configs not yet run: qwen reasoning on, and gpt-oss at
# low/high (medium is the default already covered by earlier untracked runs).
_DEFAULT_RUNS = [
    {"label": "qwen/qwen3-32b@on", "model": "qwen/qwen3-32b",
     "reasoning_effort": "default", "reasoning_format": "parsed"},
    {"label": "openai/gpt-oss-120b@low", "model": "openai/gpt-oss-120b",
     "reasoning_effort": "low", "reasoning_format": None},
    {"label": "openai/gpt-oss-120b@high", "model": "openai/gpt-oss-120b",
     "reasoning_effort": "high", "reasoning_format": None},
    {"label": "openai/gpt-oss-20b@low", "model": "openai/gpt-oss-20b",
     "reasoning_effort": "low", "reasoning_format": None},
    {"label": "openai/gpt-oss-20b@high", "model": "openai/gpt-oss-20b",
     "reasoning_effort": "high", "reasoning_format": None},
]


def parse_run_spec(entry: str) -> dict:
    """Parse an ``EVAL_MODELS`` entry ("model" or "model@suffix") into a run spec.

    Suffix maps to a Groq reasoning_effort: low/medium/high pass through, "on"
    enables reasoning ("default"), "off"/"none" disable it. No suffix means no
    reasoning params are sent (backward compatible). reasoning_format is "parsed"
    only for qwen models with reasoning enabled (gpt-oss rejects the param).
    """
    entry = entry.strip()
    model, _, suffix = entry.partition("@")
    model, suffix = model.strip(), suffix.strip().lower()
    effort = {
        "": None, "low": "low", "medium": "medium", "high": "high",
        "on": "default", "off": "none", "none": "none",
    }.get(suffix, suffix)
    enabled = effort not in (None, "none")
    fmt = "parsed" if (enabled and "qwen" in model) else None
    return {"label": entry, "model": model,
            "reasoning_effort": effort, "reasoning_format": fmt}


RUNS = (
    [parse_run_spec(e) for e in os.environ["EVAL_MODELS"].split(",") if e.strip()]
    if os.environ.get("EVAL_MODELS")
    else _DEFAULT_RUNS
)
JUDGE_MODEL = os.environ.get(
    "EVAL_JUDGE_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)
REQUEST_DELAY = float(os.environ.get("EVAL_REQUEST_DELAY", "0.5"))
# Cap on tokens generated per call — for reasoning models this covers reasoning
# AND the visible answer combined. Set high so high reasoning effort can't
# consume the whole budget and leave the answer truncated (the cause of empty
# answers at the per-model defaults of 2048/3072 — a single high-effort JEE
# question was measured using ~15.8k tokens). You only pay for tokens actually
# generated, so a generous cap costs nothing extra. Within every model's output
# limit (gpt-oss 65536, qwen3-32b 40960). Override via EVAL_MAX_COMPLETION_TOKENS.
MAX_COMPLETION_TOKENS = int(os.environ.get("EVAL_MAX_COMPLETION_TOKENS", "32768"))
MAX_RETRIES = 3
BASE_BACKOFF = 1.0  # seconds

_THIS_DIR = Path(__file__).resolve().parent
# The dataset and .env both live in the Learning.AI root, two levels up.
QA_PATH = _THIS_DIR.parent.parent / "qa.csv"
ENV_PATH = _THIS_DIR.parent.parent / ".env"
RESULTS_DIR = _THIS_DIR / "results"
# Full per-question inputs/outputs go here for debugging; rotated by size,
# appended across runs. File only — never printed to the console.
LOG_PATH = _THIS_DIR / "eval.log"

logger = logging.getLogger("evals.run_eval")

# qa.csv column names mapped to internal record keys.
QUESTION_COL = "Question"
ANSWER_COL = "Correct_Answer"
CATEGORY_COL = "Topic"

RESULT_FIELDS = [
    # ``model`` is the run label (grouping key); ``model_id`` is the real Groq id.
    "model", "model_id", "reasoning_effort", "id", "category", "question",
    "expected_answer", "model_answer", "verdict", "reason", "judge_raw",
    "model_tokens_in", "model_tokens_out", "model_reasoning_tokens",
    "judge_tokens_in", "judge_tokens_out",
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


def setup_logging() -> None:
    """Attach a size-rotated file handler to the module logger.

    The log file is the only sink (propagate is off), so full prompts and
    responses are written to LOG_PATH but never reach the console. Safe to
    call more than once: it won't add duplicate handlers.
    """
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        return
    handler = RotatingFileHandler(
        LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)


_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*(.*?)\s*```$", re.DOTALL)
# Fallbacks for when the judge emits JSON the loader can't read: LaTeX-escaped
# braces (`$\{...\}$`) or a reply truncated mid-string. Match the verdict/reason
# keys directly. `\W{0,4}` spans the `": "` (and an optional opening quote).
_VERDICT_RE = re.compile(r"verdict\W{0,4}(correct|incorrect)", re.IGNORECASE)
_REASON_RE = re.compile(r'reason\W{0,4}"((?:[^"\\]|\\.)*)"', re.IGNORECASE)


def _iter_json_objects(text: str):
    """Yield balanced ``{...}`` substrings, outermost-first, left to right.

    Scanning for individually-balanced objects lets us skip LaTeX braces
    (``\\frac{1}{n}``) and find a real verdict object embedded in chain-of-
    thought prose, rather than grabbing first-``{``..last-``}`` and spanning
    the LaTeX (which never parses).
    """
    depth = start = 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0:
                yield text[start:i + 1]


def parse_judge_response(raw: str) -> tuple[str, str]:
    """Parse judge output into (verdict, reason).

    Tolerates the ways the judge model strays from "JSON only": markdown
    fences, LaTeX ``\\boxed{...}`` wrapping, a verdict object buried in
    chain-of-thought, and LaTeX-escaped or truncated JSON. Raises ValueError
    if no verdict can be recovered or it is not 'correct'/'incorrect'.
    """
    text = (raw or "").strip()
    fence = _FENCE_RE.match(text)
    if fence:
        text = fence.group(1).strip()

    data = None
    # Prefer a real JSON object carrying a "verdict" key: the whole string, then
    # any balanced object embedded in it (skipping LaTeX braces along the way).
    candidates = []
    try:
        candidates.append(json.loads(text))
    except json.JSONDecodeError:
        pass
    for chunk in _iter_json_objects(text):
        try:
            candidates.append(json.loads(chunk))
        except json.JSONDecodeError:
            continue
    for obj in candidates:
        if isinstance(obj, dict) and "verdict" in obj:
            data = obj
            break

    # No parseable object (escaped/truncated JSON): pull the keys out by regex.
    if data is None:
        m = _VERDICT_RE.search(text)
        if m:
            data = {"verdict": m.group(1)}
            rm = _REASON_RE.search(text)
            if rm:
                data["reason"] = rm.group(1)

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


def token_totals(records: list[dict]) -> list[dict]:
    """Sum model and judge token usage per model label, in first-seen order.

    ``reasoning`` is a subset of ``model_out`` (reasoning tokens are billed as
    output tokens), broken out here for visibility. ``model_id`` carries the real
    Groq id (first-seen) so callers can look up pricing; it falls back to the
    label for older results that predate the model_id column.
    """
    order: list[str] = []
    totals: dict[str, dict] = {}
    for r in records:
        m = r["model"]
        if m not in totals:
            order.append(m)
            totals[m] = {"model_id": r.get("model_id") or m,
                         "model_in": 0, "model_out": 0, "reasoning": 0,
                         "judge_in": 0, "judge_out": 0}
        totals[m]["model_in"] += int(r.get("model_tokens_in") or 0)
        totals[m]["model_out"] += int(r.get("model_tokens_out") or 0)
        totals[m]["reasoning"] += int(r.get("model_reasoning_tokens") or 0)
        totals[m]["judge_in"] += int(r.get("judge_tokens_in") or 0)
        totals[m]["judge_out"] += int(r.get("judge_tokens_out") or 0)
    return [{"model": m, **totals[m]} for m in order]


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


def usage_from_response(resp) -> dict:
    """Extract token usage as {'in': int, 'out': int, 'reasoning': int}.

    'reasoning' is the reasoning-token count (0 for non-reasoning models/calls)
    and is a subset of 'out' — reasoning tokens are billed as output tokens.
    """
    u = getattr(resp, "usage", None)
    if u is None:
        return {"in": 0, "out": 0, "reasoning": 0}
    details = getattr(u, "completion_tokens_details", None)
    reasoning = int(getattr(details, "reasoning_tokens", 0) or 0) if details else 0
    return {
        "in": int(getattr(u, "prompt_tokens", 0) or 0),
        "out": int(getattr(u, "completion_tokens", 0) or 0),
        "reasoning": reasoning,
    }


def groq_chat(
    client: Groq, model: str, messages: list[dict],
    reasoning_effort: str | None = None, reasoning_format: str | None = None,
    max_completion_tokens: int | None = MAX_COMPLETION_TOKENS,
) -> tuple[str, dict]:
    """Call Groq chat completions with retry/backoff on API errors.

    reasoning_effort/reasoning_format are forwarded only when set (gpt-oss
    rejects reasoning_format, so leave it None for those models).
    max_completion_tokens caps reasoning + answer; sent unless None. Returns
    (content, usage) where usage is {'in': int, 'out': int, 'reasoning': int}.
    """
    kwargs: dict = {"model": model, "messages": messages, "temperature": 0}
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    if reasoning_format is not None:
        kwargs["reasoning_format"] = reasoning_format
    if max_completion_tokens is not None:
        kwargs["max_completion_tokens"] = max_completion_tokens
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or ""), usage_from_response(resp)
        except groq.APIError as exc:  # base class for rate-limit/status/conn errors
            last_exc = exc
            if attempt == MAX_RETRIES - 1:
                break
            backoff = BASE_BACKOFF * (2 ** attempt)
            logger.warning(
                "%s attempt %d/%d failed: %s; retrying in %.1fs",
                model, attempt + 1, MAX_RETRIES, exc, backoff,
            )
            time.sleep(backoff)
    raise last_exc


def ask_model(client: Groq, run: dict, question: str) -> tuple[str, dict]:
    """Return (answer, usage) for a run spec's reply to a bare question."""
    return groq_chat(
        client, run["model"], [{"role": "user", "content": question}],
        reasoning_effort=run.get("reasoning_effort"),
        reasoning_format=run.get("reasoning_format"),
    )


def judge(
    client: Groq, question: str, expected: str, answer: str
) -> tuple[str, str, str, dict]:
    """Grade an answer. Returns (verdict, reason, raw, usage). Never raises.

    raw is the judge's last raw response text ("" on API error); usage is the
    judge call's {'in': int, 'out': int}, zeros on failure.
    """
    messages = build_judge_messages(question, expected, answer)
    last_raw = ""
    usage = {"in": 0, "out": 0, "reasoning": 0}
    for _ in range(2):  # one retry on unparseable JSON
        try:
            last_raw, usage = groq_chat(client, JUDGE_MODEL, messages)
        except groq.APIError as exc:
            logger.warning("judge API error: %s", exc)
            return "error", f"judge API error: {exc}", "", {"in": 0, "out": 0, "reasoning": 0}
        try:
            verdict, reason = parse_judge_response(last_raw)
            return verdict, reason, last_raw, usage
        except ValueError:
            continue
    logger.warning("unparseable judge response: %r", last_raw[:500])
    return "error", f"unparseable judge response: {last_raw[:200]!r}", last_raw, usage


def main() -> None:
    setup_logging()
    load_dotenv(ENV_PATH)
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit(f"GROQ_API_KEY not found (looked in {ENV_PATH})")
    client = Groq(api_key=api_key)

    dataset = load_dataset(str(QA_PATH))
    if not dataset:
        raise SystemExit(f"No questions found in {QA_PATH}")
    print(f"Loaded {len(dataset)} questions; testing {len(RUNS)} run(s); "
          f"judge={JUDGE_MODEL}\n")

    records: list[dict] = []
    total = len(dataset)
    w = len(str(total))
    for run in RUNS:
        label = run["label"]
        print(f"== {label} ==")
        for i, row in enumerate(dataset, start=1):
            base = {
                "model": label, "model_id": run["model"],
                "reasoning_effort": run.get("reasoning_effort") or "",
                "id": row["id"], "category": row["category"],
                "question": row["question"], "expected_answer": row["expected_answer"],
            }
            zero = {"in": 0, "out": 0, "reasoning": 0}
            judge_raw = ""
            t0 = time.perf_counter()
            try:
                answer, m_usage = ask_model(client, run, row["question"])
                verdict, reason, judge_raw, j_usage = judge(
                    client, row["question"], row["expected_answer"], answer
                )
            except groq.APIError as exc:
                answer, verdict, reason = "", "error", f"model API error: {exc}"
                m_usage, j_usage = zero, zero
                logger.warning("%s model API error on #%s: %s", label, row["id"], exc)
            elapsed = time.perf_counter() - t0
            records.append({
                **base, "model_answer": answer,
                "verdict": verdict, "reason": reason, "judge_raw": judge_raw,
                "model_tokens_in": m_usage["in"], "model_tokens_out": m_usage["out"],
                "model_reasoning_tokens": m_usage["reasoning"],
                "judge_tokens_in": j_usage["in"], "judge_tokens_out": j_usage["out"],
            })
            logger.info(
                "model=%s id=%s category=%s verdict=%s elapsed=%.1fs\n"
                "QUESTION:\n%s\nMODEL_ANSWER:\n%s\nJUDGE_RAW:\n%s\n"
                "REASON: %s\nTOKENS model=%d/%d (reasoning %d) judge=%d/%d",
                label, row["id"], row["category"], verdict, elapsed,
                row["question"], answer, judge_raw, reason,
                m_usage["in"], m_usage["out"], m_usage["reasoning"],
                j_usage["in"], j_usage["out"],
            )
            print(f"  [{i:>{w}}/{total}] #{row['id']:<3} {row['category']:<10} "
                  f"[{verdict}] {elapsed:5.1f}s")
            time.sleep(REQUEST_DELAY)
        print()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"results_{ts}.csv"
    write_results(records, str(out_path))

    print(format_table(summarize(records)))
    print("\nToken usage per model (in/out; reasoning is a subset of out):")
    for t in token_totals(records):
        print(f"  {t['model']:<42} answer={t['model_in']}/{t['model_out']} "
              f"(reasoning {t['reasoning']})  judge={t['judge_in']}/{t['judge_out']}")
    print(f"\nDetailed results written to {out_path}")


if __name__ == "__main__":
    main()
