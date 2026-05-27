import csv

import pytest
from evals import analyze_results as ar


def _write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def _rec(model, category, verdict, m_in=0, m_out=0, m_reasoning=0, model_id=None):
    return {"model": model, "model_id": model_id or model,
            "category": category, "verdict": verdict,
            "model_tokens_in": m_in, "model_tokens_out": m_out,
            "model_reasoning_tokens": m_reasoning,
            "judge_tokens_in": 999, "judge_tokens_out": 999}


# ----- read_results -----

def test_read_results_roundtrip(tmp_path):
    p = tmp_path / "results_20260101_000000.csv"
    _write_csv(p, ["model", "category", "verdict"],
               [["A", "Physics", "correct"], ["A", "Maths", "incorrect"]])
    rows = ar.read_results(str(p))
    assert [r["model"] for r in rows] == ["A", "A"]
    assert rows[0]["category"] == "Physics" and rows[0]["verdict"] == "correct"


# ----- find_results -----

def test_find_results_sorted_oldest_first(tmp_path):
    (tmp_path / "results_20260527_184302.csv").write_text("model\n")
    (tmp_path / "results_20260101_000000.csv").write_text("model\n")
    names = [p.name for p in ar.find_results(tmp_path)]
    assert names == ["results_20260101_000000.csv", "results_20260527_184302.csv"]


def test_find_results_raises_when_none(tmp_path):
    with pytest.raises(SystemExit, match="No results"):
        ar.find_results(tmp_path)


# ----- combine_records -----

def test_combine_records_accumulates_distinct_models(tmp_path):
    a = tmp_path / "results_1.csv"
    b = tmp_path / "results_2.csv"
    _write_csv(a, ["model", "id", "verdict"], [["A", "1", "correct"]])
    _write_csv(b, ["model", "id", "verdict"], [["B", "1", "incorrect"]])
    merged = ar.combine_records([str(a), str(b)])
    assert [(r["model"], r["id"]) for r in merged] == [("A", "1"), ("B", "1")]


def test_combine_records_later_file_overrides_same_model_id(tmp_path):
    a = tmp_path / "results_old.csv"
    b = tmp_path / "results_new.csv"
    _write_csv(a, ["model", "id", "verdict"], [["A", "1", "incorrect"]])
    _write_csv(b, ["model", "id", "verdict"], [["A", "1", "correct"]])
    merged = ar.combine_records([str(a), str(b)])  # b passed last -> wins
    assert len(merged) == 1
    assert merged[0]["verdict"] == "correct"


# ----- exclude_models -----

def test_exclude_models_drops_listed_label():
    records = [_rec("A", "X", "correct"), _rec("B", "X", "correct")]
    kept = ar.exclude_models(records, ["B"])
    assert [r["model"] for r in kept] == ["A"]


def test_exclude_models_is_exact_label_match():
    # The default label must not also drop its reasoning-suffixed sibling.
    records = [_rec("gpt", "X", "correct"), _rec("gpt@low", "X", "correct")]
    kept = ar.exclude_models(records, ["gpt"])
    assert [r["model"] for r in kept] == ["gpt@low"]


def test_exclude_models_empty_list_keeps_all():
    records = [_rec("A", "X", "correct"), _rec("B", "X", "correct")]
    assert ar.exclude_models(records, []) == records


# ----- model_costs -----

def test_model_costs_math():
    pricing = {"default": {"in": 0.0, "out": 0.0},
               "models": {"A": {"in": 1.0, "out": 2.0}}}
    # 1,000,000 in @ $1/M + 500,000 out @ $2/M = 1.0 + 1.0 = 2.0
    records = [_rec("A", "Physics", "correct", m_in=1_000_000, m_out=500_000)]
    costs = ar.model_costs(records, pricing)
    assert costs[0]["model"] == "A"
    assert costs[0]["cost"] == pytest.approx(2.0)


def test_model_costs_preserves_first_seen_order():
    pricing = {"default": {"in": 0.0, "out": 0.0},
               "models": {"Z": {"in": 1.0, "out": 1.0}, "A": {"in": 1.0, "out": 1.0}}}
    records = [_rec("Z", "X", "correct"), _rec("A", "X", "correct")]
    assert [c["model"] for c in ar.model_costs(records, pricing)] == ["Z", "A"]


def test_model_costs_unknown_model_uses_default(caplog):
    pricing = {"default": {"in": 3.0, "out": 4.0}, "models": {}}
    records = [_rec("ghost", "X", "correct", m_in=1_000_000, m_out=1_000_000)]
    with caplog.at_level("WARNING"):
        costs = ar.model_costs(records, pricing)
    assert costs[0]["cost"] == pytest.approx(7.0)
    assert "ghost" in caplog.text


def test_model_costs_zero_tokens_is_zero():
    pricing = {"default": {"in": 0.0, "out": 0.0},
               "models": {"A": {"in": 1.0, "out": 1.0}}}
    records = [_rec("A", "X", "error", m_in=0, m_out=0)]
    assert ar.model_costs(records, pricing)[0]["cost"] == pytest.approx(0.0)


def test_model_costs_pricing_resolves_via_model_id():
    # The label carries a reasoning suffix; pricing is keyed by the real id.
    pricing = {"default": {"in": 0.0, "out": 0.0},
               "models": {"gpt": {"in": 1.0, "out": 2.0}}}
    records = [_rec("gpt@high", "X", "correct", m_in=1_000_000, m_out=500_000,
                    m_reasoning=300_000, model_id="gpt")]
    cost = ar.model_costs(records, pricing)[0]
    assert cost["model"] == "gpt@high"
    # Reasoning tokens are inside model_out, so cost is unchanged by them.
    assert cost["cost"] == pytest.approx(2.0)
    assert cost["reasoning"] == 300_000


# ----- category_accuracy -----

def test_category_accuracy_basic():
    records = [
        _rec("A", "Physics", "correct"), _rec("A", "Physics", "correct"),
        _rec("A", "Physics", "incorrect"),  # 2/3 -> 66.7
        _rec("A", "Maths", "correct"),       # 1/1 -> 100.0
    ]
    out = ar.category_accuracy(records)
    assert out["A"]["Physics"] == pytest.approx(66.7, abs=0.05)
    assert out["A"]["Maths"] == pytest.approx(100.0)


def test_category_accuracy_all_errors_is_none():
    records = [_rec("A", "Physics", "error"), _rec("A", "Physics", "error")]
    assert ar.category_accuracy(records)["A"]["Physics"] is None


def test_category_accuracy_per_model():
    records = [_rec("A", "Physics", "correct"), _rec("B", "Physics", "incorrect")]
    out = ar.category_accuracy(records)
    assert out["A"]["Physics"] == pytest.approx(100.0)
    assert out["B"]["Physics"] == pytest.approx(0.0)


# ----- category_order -----

def test_category_order_by_pooled_accuracy_desc():
    records = [
        _rec("A", "Easy", "correct"), _rec("B", "Easy", "correct"),  # 100%
        _rec("A", "Mid", "correct"), _rec("B", "Mid", "incorrect"),  # 50%
        _rec("A", "Hard", "incorrect"), _rec("B", "Hard", "incorrect"),  # 0%
    ]
    assert ar.category_order(records) == ["Easy", "Mid", "Hard"]


def test_category_order_all_error_category_sorts_last():
    records = [
        _rec("A", "Graded", "correct"),
        _rec("A", "AllErr", "error"), _rec("B", "AllErr", "error"),
    ]
    assert ar.category_order(records) == ["Graded", "AllErr"]


# ----- plot smoke tests (headless) -----

@pytest.fixture(scope="module", autouse=True)
def _agg_backend():
    import matplotlib
    matplotlib.use("Agg")
    import seaborn as sns
    sns.set_theme(style="whitegrid")


def _sample_records():
    return [
        _rec("A", "Physics", "correct", 100, 200),
        _rec("A", "Maths", "incorrect", 120, 220),
        _rec("B", "Physics", "correct", 80, 150),
        _rec("B", "Maths", "correct", 90, 160),
    ]


def _pricing():
    return {"default": {"in": 0.0, "out": 0.0},
            "models": {"A": {"in": 0.5, "out": 1.0}, "B": {"in": 0.5, "out": 1.0}}}


def test_plot_overall_accuracy_writes_png(tmp_path):
    p = tmp_path / "acc.png"
    ar.plot_overall_accuracy(_sample_records(), p)
    assert p.exists() and p.stat().st_size > 0


def test_plot_accuracy_by_category_writes_png(tmp_path):
    p = tmp_path / "cat.png"
    ar.plot_accuracy_by_category(_sample_records(), p)
    assert p.exists() and p.stat().st_size > 0


def test_plot_cost_writes_png(tmp_path):
    p = tmp_path / "cost.png"
    ar.plot_cost(_sample_records(), _pricing(), p)
    assert p.exists() and p.stat().st_size > 0


def test_plot_cost_vs_accuracy_writes_png(tmp_path):
    p = tmp_path / "cva.png"
    ar.plot_cost_vs_accuracy(_sample_records(), _pricing(), p)
    assert p.exists() and p.stat().st_size > 0
