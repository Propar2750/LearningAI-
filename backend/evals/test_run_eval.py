import csv
import pytest
from evals import run_eval


def _write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def test_load_dataset_valid(tmp_path):
    p = tmp_path / "qa.csv"
    _write_csv(p, ["Topic", "Question", "Correct_Answer"],
               [["Geo", "Capital of France?", "Paris"]])
    rows = run_eval.load_dataset(str(p))
    assert rows == [{
        "id": "1", "category": "Geo",
        "question": "Capital of France?", "expected_answer": "Paris",
    }]


def test_load_dataset_id_is_row_number_and_extra_cols_ignored(tmp_path):
    p = tmp_path / "qa.csv"
    _write_csv(
        p,
        ["Topic", "Question", "Correct_Answer", "Common_Incorrect_Answer_Flag", "Source"],
        [["Math", "2+2?", "4", "says 5", "textbook"],
         ["Math", "3+3?", "6", "says 9", "textbook"]],
    )
    rows = run_eval.load_dataset(str(p))
    assert [r["id"] for r in rows] == ["1", "2"]
    assert rows[0]["category"] == "Math"
    assert rows[0]["question"] == "2+2?"
    assert set(rows[0].keys()) == {"id", "category", "question", "expected_answer"}


def test_load_dataset_skips_rows_without_question(tmp_path):
    p = tmp_path / "qa.csv"
    _write_csv(p, ["Topic", "Question", "Correct_Answer"],
               [["X", "", "ignored"], ["Y", "Q", "A"]])
    rows = run_eval.load_dataset(str(p))
    assert len(rows) == 1 and rows[0]["question"] == "Q"


def test_load_dataset_missing_required_column(tmp_path):
    p = tmp_path / "qa.csv"
    _write_csv(p, ["Topic", "Question"], [["X", "Q"]])
    with pytest.raises(ValueError, match="Correct_Answer"):
        run_eval.load_dataset(str(p))


def test_parse_judge_clean_json():
    raw = '{"verdict": "correct", "reason": "matches reference"}'
    assert run_eval.parse_judge_response(raw) == ("correct", "matches reference")


def test_parse_judge_uppercase_verdict_normalized():
    raw = '{"verdict": "INCORRECT", "reason": "wrong number"}'
    assert run_eval.parse_judge_response(raw) == ("incorrect", "wrong number")


def test_parse_judge_with_surrounding_text():
    raw = 'Here is my answer:\n{"verdict": "correct", "reason": "ok"} Thanks!'
    assert run_eval.parse_judge_response(raw) == ("correct", "ok")


def test_parse_judge_invalid_verdict_raises():
    with pytest.raises(ValueError):
        run_eval.parse_judge_response('{"verdict": "maybe", "reason": "x"}')


def test_parse_judge_bad_json_raises():
    with pytest.raises(ValueError):
        run_eval.parse_judge_response("not json at all")


def test_parse_judge_strips_markdown_fence():
    raw = '```json\n{"verdict": "correct", "reason": "ok"}\n```'
    assert run_eval.parse_judge_response(raw) == ("correct", "ok")


def test_parse_judge_latex_boxed_wrapper():
    # judge wrapped the object in \boxed{...} (observed: ids 19, 136)
    raw = '$\\boxed{"verdict": "correct", "reason": "matches reference"}$'
    assert run_eval.parse_judge_response(raw) == ("correct", "matches reference")


def test_parse_judge_ignores_latex_braces_before_json():
    # chain-of-thought full of LaTeX braces, real verdict object at the end
    # (observed: ids 4, 23, 25, 29 - the old first-{/last-} grab spanned the
    # LaTeX and failed to parse)
    raw = (
        "## Step 1: integrate $\\frac{1}{n}$ over $\\chi_{[0, 1]}$ giving "
        "$\\sum_{s'} P(s')$.\n\n"
        '{"verdict": "incorrect", "reason": "wrong integral"}'
    )
    assert run_eval.parse_judge_response(raw) == ("incorrect", "wrong integral")


def test_parse_judge_recovers_escaped_json():
    # LaTeX-escaped braces make json.loads fail; recover via regex (id 59 style)
    raw = '$\\{"verdict": "incorrect", "reason": "missing format"\\}$'
    assert run_eval.parse_judge_response(raw) == ("incorrect", "missing format")


def test_parse_judge_recovers_verdict_from_truncated_json():
    # response cut off mid-reason: verdict is still recoverable (id 19 style)
    raw = '$\\boxed{"verdict": "correct", "reason": "The candidate accurately expla'
    verdict, _ = run_eval.parse_judge_response(raw)
    assert verdict == "correct"


def _rec(model, verdict):
    return {"model": model, "verdict": verdict}


def test_summarize_basic_accuracy():
    records = [
        _rec("A", "correct"), _rec("A", "correct"),
        _rec("A", "incorrect"), _rec("A", "error"),
    ]
    summary = run_eval.summarize(records)
    row = summary[0]
    assert row["model"] == "A"
    assert row["correct"] == 2
    assert row["incorrect"] == 1
    assert row["errors"] == 1
    # accuracy excludes errors: 2 / (2 + 1)
    assert row["accuracy"] == pytest.approx(66.7, abs=0.05)


def test_summarize_all_errors_is_na():
    records = [_rec("B", "error"), _rec("B", "error")]
    row = run_eval.summarize(records)[0]
    assert row["correct"] == 0 and row["incorrect"] == 0 and row["errors"] == 2
    assert row["accuracy"] is None  # rendered as "n/a"


def test_summarize_preserves_first_seen_order():
    records = [_rec("Z", "correct"), _rec("A", "correct")]
    assert [r["model"] for r in run_eval.summarize(records)] == ["Z", "A"]


def test_format_table_contains_models_and_pct():
    summary = [
        {"model": "A", "correct": 2, "incorrect": 1, "errors": 0, "accuracy": 66.7},
        {"model": "B", "correct": 0, "incorrect": 0, "errors": 2, "accuracy": None},
    ]
    out = run_eval.format_table(summary)
    assert "A" in out and "66.7%" in out
    assert "B" in out and "n/a" in out


def test_write_results_roundtrip(tmp_path):
    records = [{
        "model": "A", "id": "1", "category": "geo",
        "question": "Capital of France?", "expected_answer": "Paris",
        "model_answer": "Paris", "verdict": "correct", "reason": "ok",
    }]
    out = tmp_path / "results.csv"
    run_eval.write_results(records, str(out))
    with open(out, newline="", encoding="utf-8") as f:
        read_back = list(csv.DictReader(f))
    assert read_back[0]["model"] == "A"
    assert read_back[0]["verdict"] == "correct"
    assert list(read_back[0].keys()) == run_eval.RESULT_FIELDS


def test_write_results_includes_judge_raw(tmp_path):
    assert "judge_raw" in run_eval.RESULT_FIELDS
    records = [{
        "model": "A", "id": "1", "category": "geo",
        "question": "Capital of France?", "expected_answer": "Paris",
        "model_answer": "Paris", "verdict": "correct", "reason": "ok",
        "judge_raw": '{"verdict": "correct", "reason": "ok"}',
    }]
    out = tmp_path / "results.csv"
    run_eval.write_results(records, str(out))
    with open(out, newline="", encoding="utf-8") as f:
        read_back = list(csv.DictReader(f))
    assert read_back[0]["judge_raw"] == '{"verdict": "correct", "reason": "ok"}'


def test_setup_logging_is_file_only_and_idempotent(tmp_path, monkeypatch):
    import logging
    from logging.handlers import RotatingFileHandler

    monkeypatch.setattr(run_eval, "LOG_PATH", tmp_path / "eval.log")
    run_eval.logger.handlers.clear()
    try:
        run_eval.setup_logging()
        run_eval.setup_logging()  # second call must not add a duplicate handler
        file_handlers = [
            h for h in run_eval.logger.handlers
            if isinstance(h, RotatingFileHandler)
        ]
        assert len(file_handlers) == 1
        assert run_eval.logger.propagate is False
    finally:
        for h in run_eval.logger.handlers:
            h.close()
        run_eval.logger.handlers.clear()


from types import SimpleNamespace


def test_usage_from_response_reads_tokens():
    resp = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=42, completion_tokens=7))
    assert run_eval.usage_from_response(resp) == {"in": 42, "out": 7, "reasoning": 0}


def test_usage_from_response_reads_reasoning_tokens():
    resp = SimpleNamespace(usage=SimpleNamespace(
        prompt_tokens=42, completion_tokens=20,
        completion_tokens_details=SimpleNamespace(reasoning_tokens=13)))
    assert run_eval.usage_from_response(resp) == {"in": 42, "out": 20, "reasoning": 13}


def test_usage_from_response_handles_missing_usage():
    resp = SimpleNamespace(usage=None)
    assert run_eval.usage_from_response(resp) == {"in": 0, "out": 0, "reasoning": 0}


def test_token_totals_sums_per_model_in_order():
    records = [
        {"model": "Z", "model_id": "z-real", "model_tokens_in": 10,
         "model_tokens_out": 5, "model_reasoning_tokens": 2,
         "judge_tokens_in": 3, "judge_tokens_out": 1},
        {"model": "Z", "model_id": "z-real", "model_tokens_in": 20,
         "model_tokens_out": 8, "model_reasoning_tokens": 3,
         "judge_tokens_in": 4, "judge_tokens_out": 2},
        {"model": "A", "model_tokens_in": 1, "model_tokens_out": 1,
         "judge_tokens_in": 1, "judge_tokens_out": 1},
    ]
    totals = run_eval.token_totals(records)
    assert [t["model"] for t in totals] == ["Z", "A"]
    assert totals[0] == {"model": "Z", "model_id": "z-real", "model_in": 30,
                         "model_out": 13, "reasoning": 5,
                         "judge_in": 7, "judge_out": 3}
    # No model_id column -> falls back to the label.
    assert totals[1]["model_id"] == "A" and totals[1]["reasoning"] == 0


def test_parse_run_spec_efforts_and_labels():
    assert run_eval.parse_run_spec("openai/gpt-oss-120b@high") == {
        "label": "openai/gpt-oss-120b@high", "model": "openai/gpt-oss-120b",
        "reasoning_effort": "high", "reasoning_format": None}
    # "on" enables qwen reasoning ("default") and selects the parsed format.
    assert run_eval.parse_run_spec("qwen/qwen3-32b@on") == {
        "label": "qwen/qwen3-32b@on", "model": "qwen/qwen3-32b",
        "reasoning_effort": "default", "reasoning_format": "parsed"}
    assert run_eval.parse_run_spec("qwen/qwen3-32b@off")["reasoning_effort"] == "none"
    # Bare model: no reasoning params, label is the model id (backward compatible).
    assert run_eval.parse_run_spec("llama-3.3-70b-versatile") == {
        "label": "llama-3.3-70b-versatile", "model": "llama-3.3-70b-versatile",
        "reasoning_effort": None, "reasoning_format": None}


def test_groq_chat_forwards_reasoning_params_only_when_set():
    calls = []

    class _FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))

    client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))

    content, usage = run_eval.groq_chat(client, "m", [{"role": "user", "content": "q"}])
    assert content == "ok" and "reasoning_effort" not in calls[-1]
    assert "reasoning_format" not in calls[-1]
    # The completion-token cap is sent by default so reasoning can't truncate the answer.
    assert calls[-1]["max_completion_tokens"] == run_eval.MAX_COMPLETION_TOKENS

    run_eval.groq_chat(client, "m", [{"role": "user", "content": "q"}],
                       reasoning_effort="high")
    assert calls[-1]["reasoning_effort"] == "high"
    assert "reasoning_format" not in calls[-1]

    run_eval.groq_chat(client, "qwen/qwen3-32b", [{"role": "user", "content": "q"}],
                       reasoning_effort="default", reasoning_format="parsed")
    assert calls[-1]["reasoning_effort"] == "default"
    assert calls[-1]["reasoning_format"] == "parsed"

    run_eval.groq_chat(client, "m", [{"role": "user", "content": "q"}],
                       max_completion_tokens=None)
    assert "max_completion_tokens" not in calls[-1]
