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
