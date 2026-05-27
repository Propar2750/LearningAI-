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
