# LLM Accuracy Eval — Design

## Purpose

A standalone, re-runnable script that measures how accurately various Groq-served
LLMs answer a small fixed set of questions. Each model is asked every question;
its answer is graded against a known expected answer by an LLM judge. Output is a
per-model accuracy table plus a detailed results CSV for auditing.

## Locked decisions

- **Artifact:** standalone eval script (run directly, not pytest).
- **Dataset:** CSV file, hand-editable, version-controlled.
- **Models under test:** Groq only, via the existing `GROQ_API_KEY`.
- **Scoring:** binary `correct`/`incorrect` plus a one-line reason from the judge.
- **Judge:** a single configurable Groq model (defaults to a strong Llama).
- **Reporting:** console accuracy table + detailed results CSV on disk. The
  detailed CSV MUST record, for every `model × question` pair, exactly which
  question was asked, the model's answer, and whether it was right or wrong
  (`verdict`) — i.e. per-question right/wrong is always persisted, never just the
  aggregate.
- **Errors:** excluded from accuracy (accuracy = correct / (correct + incorrect));
  reported as a separate count.
- **Scope:** always run the full dataset against all configured models. No CLI
  flags (no `--limit`, no `--models`) in v0.

## Layout

```
backend/evals/
  questions.csv            # dataset (user-owned; ships with example rows)
  run_eval.py              # the script
  results/                 # timestamped output CSVs (gitignored)
    .gitkeep
```

## Dataset format (`questions.csv`)

Columns:

- `question` (required) — the prompt sent to each model.
- `expected_answer` (required) — the reference answer the judge grades against.
- `id` (optional) — stable identifier; passed through to the results CSV if present.
- `category` (optional) — passed through to the results CSV if present.

Ships with 2-3 example rows so the script runs out of the box; the user replaces
them with real questions.

## Configuration

Defined at the top of `run_eval.py`, each overridable by environment variable:

- `MODELS` — list of Groq model ids under test (e.g. Llama 3.x, Gemma, Mixtral).
  Override via `EVAL_MODELS` (comma-separated).
- `JUDGE_MODEL` — Groq model id used for grading; defaults to a strong Llama.
  Override via `EVAL_JUDGE_MODEL`.
- `REQUEST_DELAY` — seconds to sleep between API calls to respect Groq rate
  limits.

`GROQ_API_KEY` is loaded from `../.env` (parent `Learning.AI` directory) via
`python-dotenv`.

## Data flow

1. Load `../.env` → `GROQ_API_KEY`. Load `questions.csv` into a list of rows.
2. For each `model` in `MODELS`, for each `row` in the dataset:
   a. Ask the model `row.question`; collect `model_answer`.
   b. Call `JUDGE_MODEL` with the rubric prompt (question + expected_answer +
      model_answer); parse JSON `{verdict, reason}`.
   c. Append a result record.
3. Aggregate per model.
4. Print the console table; write `results/results_<timestamp>.csv`.

## Components

Each is small and independently testable.

- `groq_chat(model, system, user) -> str`
  Thin wrapper over the Groq SDK chat-completions call. Retries on rate-limit
  (429) / transient errors with exponential backoff; raises after N attempts.

- `ask_model(model, question) -> str`
  Sends the question as a plain user turn (minimal/no system prompt so we measure
  the model's own behavior). Returns the answer text.

- `judge(question, expected, answer) -> (verdict, reason)`
  Builds a strict grading prompt instructing the judge to return JSON only:
  `{"verdict": "correct"|"incorrect", "reason": "<one line>"}`. Parses the JSON.
  On parse failure: one retry; then returns `("error", "<parse failure detail>")`.
  Verdict is normalized to lowercase and validated against the allowed set.

- `load_dataset(path) -> list[dict]`
  Reads the CSV; validates required columns exist; raises a clear error otherwise.

- `summarize(records) -> list[dict]`
  Per model: counts correct / incorrect / error; accuracy = correct /
  (correct + incorrect), or `n/a` if that denominator is 0.

- `write_results(records, path)`
  Writes the detailed CSV with columns:
  `model, id, category, question, expected_answer, model_answer, verdict, reason`.
  (`id`/`category` columns blank when absent from the dataset.)

- `main()`
  Orchestrates the flow above; prints the summary table.

## Judge rubric prompt (intent)

The judge is told: you are grading whether a candidate answer is correct given a
reference answer; focus on factual/semantic correctness, not wording or style;
a correct answer may be phrased differently from the reference; return JSON only
in the specified shape. The exact wording is finalized during implementation.

## Error handling

- **API / network errors** (incl. 429 rate limits): retry with exponential
  backoff up to N attempts. If a *candidate model* call ultimately fails, record
  `verdict="error"` with the error detail. If a *judge* call ultimately fails,
  record `verdict="error"` likewise.
- **Judge JSON parse failure:** one retry; then `verdict="error"`.
- **Errors are excluded** from the accuracy denominator and shown as a separate
  `errors` count in both the console table and (per-row) the results CSV.
- **Rate limiting:** `REQUEST_DELAY` sleep between calls; backoff on 429.

## Console output (shape)

```
Model                          Correct  Incorrect  Errors  Accuracy
llama-3.x-...                       8         2        0      80.0%
gemma-...                           6         4        0      60.0%
...
Detailed results written to evals/results/results_<timestamp>.csv
```

## Dependencies

- `groq` — official Groq Python SDK.
- `python-dotenv` — load `../.env`.

No `requirements.txt` exists yet; create one in `backend/` listing these (plus
any already-relied-upon packages discovered during implementation) and install
into the existing `.venv`.

## Testing approach

This is an eval script, not production code, so testing is light and focused on
the pure logic (no live API calls in tests):

- Unit-test `judge`'s JSON parsing on well-formed, malformed, and
  unexpected-verdict inputs (parser extracted so it takes a raw string).
- Unit-test `summarize` accuracy math, including the all-errors / zero-denominator
  case.
- Unit-test `load_dataset` column validation.
- A manual smoke run against the shipped example `questions.csv` confirms the
  end-to-end path.

## Out of scope (v0)

- Multi-provider support (OpenAI/Anthropic/Google) — Groq only for now.
- CLI flags / subset selection.
- Graded (0-5) scoring.
- Concurrency / parallel requests.
- Caching of model answers between runs.
