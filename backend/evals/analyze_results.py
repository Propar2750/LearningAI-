"""Turn an eval results CSV into accuracy and cost charts.

Reads a ``results_*.csv`` produced by run_eval.py and writes four PNGs:
overall accuracy, accuracy by category, cost per model, and cost vs. accuracy.

Cost is derived from token counts using an editable ``pricing.json`` and counts
the model-under-test tokens only (judge tokens are excluded). Run from this
directory:

    python3 analyze_results.py                 # latest results, default pricing
    python3 analyze_results.py --results <csv> --pricing <json> --outdir <dir>
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

# Reuse the harness aggregators rather than reimplementing them. The dual import
# supports both running this file as a script (run_eval on sys.path) and being
# imported as part of the ``evals`` package (e.g. from the test suite).
try:
    from run_eval import summarize, token_totals, RESULTS_DIR
except ImportError:  # pragma: no cover - exercised via the package import path
    from evals.run_eval import summarize, token_totals, RESULTS_DIR

logger = logging.getLogger("evals.analyze_results")

_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_PRICING = _THIS_DIR / "pricing.json"


# ----- Data -----

def read_results(path: str) -> list[dict]:
    """Read a results CSV into a list of row dicts (missing columns tolerated)."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_results(results_dir: Path) -> list[Path]:
    """Return all ``results_*.csv`` in results_dir, oldest first.

    Filenames embed a sortable ``YYYYMMDD_HHMMSS`` timestamp, so lexical sort is
    chronological. Raises SystemExit with a clear message if none exist.
    """
    matches = sorted(Path(results_dir).glob("results_*.csv"))
    if not matches:
        raise SystemExit(f"No results_*.csv found in {results_dir}")
    return matches


def combine_records(paths: list[str]) -> list[dict]:
    """Read and merge several results CSVs into one record list.

    Files are read in the given order (pass them oldest-first). Rows are keyed by
    (model, id) so a model re-run in a later file overrides the earlier one
    rather than double-counting; rows from distinct models simply accumulate.
    Insertion order (and thus first-seen model order) follows the file order.
    """
    merged: dict[tuple[str, str], dict] = {}
    for path in paths:
        for r in read_results(path):
            merged[(r.get("model", ""), r.get("id", ""))] = r
    return list(merged.values())


def exclude_models(records: list[dict], exclude: list[str]) -> list[dict]:
    """Drop records whose ``model`` label is in ``exclude`` (exact match).

    Matching is on the full label, so excluding a default label (e.g.
    ``gpt-oss-20b``) leaves any reasoning-suffixed sibling (``gpt-oss-20b@low``)
    untouched. Use this to drop runs with unreliable/missing data.
    """
    skip = set(exclude)
    return [r for r in records if r.get("model", "") not in skip]


def load_pricing(path: str) -> dict:
    """Read pricing.json: {'default': {in,out}, 'models': {name: {in,out}}}."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def model_costs(records: list[dict], pricing: dict) -> list[dict]:
    """Per-model USD cost from model-under-test tokens, in first-seen order.

    cost = model_in/1e6 * rate_in + model_out/1e6 * rate_out. Pricing is keyed by
    the real model id (``model_id``, falling back to the label for older results
    that predate it), since the label may carry a reasoning suffix. Reasoning
    tokens are already inside ``model_out`` (billed as output), so they need no
    separate rate; ``reasoning`` is reported for visibility. Models absent from
    the pricing config fall back to ``default`` (with a warning). Returns dicts
    of {model, model_in, model_out, reasoning, cost}.
    """
    rates = pricing.get("models", {})
    default = pricing.get("default", {"in": 0.0, "out": 0.0})
    out = []
    for t in token_totals(records):
        model = t["model"]
        price_key = t.get("model_id") or model
        rate = rates.get(price_key)
        if rate is None:
            logger.warning("no pricing for %r; using default rate", price_key)
            rate = default
        cost = (t["model_in"] / 1e6) * rate.get("in", 0.0) + \
               (t["model_out"] / 1e6) * rate.get("out", 0.0)
        out.append({
            "model": model, "model_in": t["model_in"],
            "model_out": t["model_out"], "reasoning": t["reasoning"],
            "cost": cost,
        })
    return out


def category_accuracy(records: list[dict]) -> dict[str, dict[str, float | None]]:
    """Per-model, per-category accuracy %.

    accuracy = correct / (correct + incorrect) * 100, or None when no graded
    rows exist for that (model, category) — mirrors summarize() in run_eval.py.
    Models and categories are kept in first-seen order.
    """
    # {model: {category: [correct, incorrect]}}
    counts: dict[str, dict[str, list[int]]] = {}
    for r in records:
        model, cat, verdict = r["model"], r.get("category", ""), r["verdict"]
        per_cat = counts.setdefault(model, {})
        tally = per_cat.setdefault(cat, [0, 0])
        if verdict == "correct":
            tally[0] += 1
        elif verdict == "incorrect":
            tally[1] += 1
    result: dict[str, dict[str, float | None]] = {}
    for model, per_cat in counts.items():
        result[model] = {}
        for cat, (correct, incorrect) in per_cat.items():
            graded = correct + incorrect
            result[model][cat] = round(100.0 * correct / graded, 1) if graded else None
    return result


def category_order(records: list[dict]) -> list[str]:
    """Categories ranked by pooled accuracy across all models, highest first.

    Pools correct/incorrect over every row in the category (model-agnostic), so
    the chart reads left-to-right as easiest-to-hardest subject. Categories with
    no graded rows sort last; ties break alphabetically.
    """
    counts: dict[str, list[int]] = {}
    for r in records:
        tally = counts.setdefault(r.get("category", ""), [0, 0])
        if r["verdict"] == "correct":
            tally[0] += 1
        elif r["verdict"] == "incorrect":
            tally[1] += 1

    def acc(cat: str) -> float:
        correct, incorrect = counts[cat]
        graded = correct + incorrect
        return correct / graded if graded else -1.0

    return sorted(counts, key=lambda c: (-acc(c), c))


# ----- Plots -----
# Imported lazily inside main() so the data functions (and their tests) don't
# require matplotlib/seaborn to be installed.

def _annotate_bars(ax, fmt: str) -> None:
    """Write each bar's value above it."""
    for container in ax.containers:
        ax.bar_label(container, fmt=fmt, padding=3, fontsize=9)


def _rotate_xticks(ax, rotation: int) -> None:
    """Rotate x tick labels in place (avoids set_xticklabels FixedLocator warning)."""
    for label in ax.get_xticklabels():
        label.set_rotation(rotation)
        label.set_horizontalalignment("right")


def plot_overall_accuracy(records: list[dict], path: Path) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    summary = summarize(records)
    models = [s["model"] for s in summary]
    accs = [s["accuracy"] or 0.0 for s in summary]

    fig, ax = plt.subplots(figsize=(max(7, 1.6 * len(models)), 5))
    sns.barplot(x=models, y=accs, hue=models, palette="viridis", legend=False, ax=ax)
    _annotate_bars(ax, "%.1f%%")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Accuracy (%)")
    ax.set_xlabel("")
    ax.set_title("Overall accuracy by model")
    _rotate_xticks(ax, 20)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_accuracy_by_category(records: list[dict], path: Path) -> None:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    by_model = category_accuracy(records)
    rows = []
    for model, per_cat in by_model.items():
        for cat, acc in per_cat.items():
            rows.append({"model": model, "category": cat,
                         "accuracy": acc if acc is not None else 0.0})
    df = pd.DataFrame(rows)

    order = category_order(records)
    fig, ax = plt.subplots(figsize=(max(11, 0.9 * len(order)), 6))
    sns.barplot(data=df, x="category", y="accuracy", hue="model",
                order=order, palette="viridis", ax=ax)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Accuracy (%)")
    ax.set_xlabel("")
    ax.set_title("Accuracy by category")
    _rotate_xticks(ax, 40)
    ax.legend(title="Model", bbox_to_anchor=(1.01, 1), loc="upper left",
              fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_cost(records: list[dict], pricing: dict, path: Path) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    costs = model_costs(records, pricing)
    models = [c["model"] for c in costs]
    values = [c["cost"] for c in costs]

    fig, ax = plt.subplots(figsize=(max(7, 1.6 * len(models)), 5))
    sns.barplot(x=models, y=values, hue=models, palette="rocket", legend=False, ax=ax)
    _annotate_bars(ax, "$%.4f")
    ax.set_ylabel("Cost (USD, model tokens only)")
    ax.set_xlabel("")
    ax.set_title("Cost per model over the dataset")
    _rotate_xticks(ax, 20)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_cost_vs_accuracy(records: list[dict], pricing: dict, path: Path) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    summary = {s["model"]: s["accuracy"] for s in summarize(records)}
    costs = model_costs(records, pricing)
    xs = [c["cost"] for c in costs]
    ys = [summary.get(c["model"]) or 0.0 for c in costs]
    labels = [c["model"] for c in costs]

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(x=xs, y=ys, hue=labels, palette="viridis", s=160,
                    edgecolor="black", ax=ax, legend=False)
    for x, y, label in zip(xs, ys, labels):
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(8, 6),
                    fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Cost (USD, model tokens only)")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Cost vs. accuracy")
    ax.margins(x=0.15)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ----- CLI -----

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", nargs="+",
                        help="one or more results CSVs, oldest first "
                             "(default: all results_*.csv in results/, merged)")
    parser.add_argument("--pricing", default=str(DEFAULT_PRICING),
                        help="pricing JSON (default: pricing.json beside this script)")
    parser.add_argument("--outdir", help="output dir (default: results/analysis)")
    parser.add_argument("--exclude-model", nargs="+", default=[], metavar="LABEL",
                        help="model label(s) to drop before analysis, e.g. a run "
                             "with too much missing data (exact match)")
    args = parser.parse_args()

    # matplotlib must pick a headless backend before pyplot is imported.
    import matplotlib
    matplotlib.use("Agg")
    import seaborn as sns
    sns.set_theme(style="whitegrid")

    paths = args.results if args.results else [str(p) for p in find_results(RESULTS_DIR)]
    outdir = Path(args.outdir) if args.outdir else RESULTS_DIR / "analysis"
    outdir.mkdir(parents=True, exist_ok=True)

    records = combine_records(paths)
    if not records:
        raise SystemExit(f"No rows in: {', '.join(paths)}")
    if args.exclude_model:
        before = len(records)
        records = exclude_models(records, args.exclude_model)
        if not records:
            raise SystemExit(f"All rows excluded by --exclude-model "
                             f"{', '.join(args.exclude_model)}")
        print(f"Excluded {', '.join(args.exclude_model)} "
              f"({before - len(records)} rows dropped)")
    pricing = load_pricing(args.pricing)

    models = list(dict.fromkeys(r["model"] for r in records))
    print(f"Analyzing {len(records)} rows merged from {len(paths)} file(s):")
    for p in paths:
        print(f"  - {p}")
    print(f"Models: {', '.join(models)}")

    # Reasoning tokens are a subset of output tokens; show how much of each
    # model's output went to reasoning (0% for non-reasoning models).
    print("Reasoning tokens per model (share of output):")
    for t in token_totals(records):
        share = (100.0 * t["reasoning"] / t["model_out"]) if t["model_out"] else 0.0
        print(f"  {t['model']:<42} reasoning={t['reasoning']} "
              f"({share:.1f}% of {t['model_out']} out)")

    outputs = {
        "01_overall_accuracy.png": lambda p: plot_overall_accuracy(records, p),
        "02_accuracy_by_category.png": lambda p: plot_accuracy_by_category(records, p),
        "03_cost_per_model.png": lambda p: plot_cost(records, pricing, p),
        "04_cost_vs_accuracy.png": lambda p: plot_cost_vs_accuracy(records, pricing, p),
    }
    for name, draw in outputs.items():
        dest = outdir / name
        draw(dest)
        print(f"  wrote {dest}")


if __name__ == "__main__":
    main()
