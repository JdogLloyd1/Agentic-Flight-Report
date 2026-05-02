# run_statistics.py — Phase 4: ANOVA / t-tests on validation_scores.csv (course-style).
#
# Usage:
#   cd "hw quality control"
#   pip install pandas scipy pingouin matplotlib
#   python run_statistics.py
#
# Input: experiment_data/validation_scores.csv (from run_validation.py)

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pingouin as pg
from scipy.stats import bartlett

_HWQC = Path(__file__).resolve().parent

_DIM_COLS = (
    "live_reference_separation",
    "section_coverage",
    "grounding",
    "gap_calibration",
    "concision",
)


def _print_run_overview(df: pd.DataFrame, csv_path: Path) -> None:
    print("\n=== Run overview ===")
    print(f"Source: {csv_path.resolve()}")
    prompts = sorted(df["prompt_id"].dropna().unique().tolist())
    print(f"Rows: {len(df)}  |  prompt_id: {', '.join(map(str, prompts))}  ({len(prompts)} group(s))")

    if "run_id" in df.columns:
        n_by = df.groupby("prompt_id")["run_id"].nunique()
        print("\nDistinct run_id per prompt_id:")
        print(n_by.to_string())

    print("\noverall_score — all rows:")
    print(df["overall_score"].describe().round(4).to_string())

    dims = [c for c in _DIM_COLS if c in df.columns]
    if dims:
        print("\nDimension means (1–5, all rows):")
        print(df[dims].mean().round(4).to_string())

    if "checklist_coverage_pct" in df.columns:
        print("\nchecklist_coverage_pct — all rows:")
        print(df["checklist_coverage_pct"].describe().round(2).to_string())

    if "grounding_gate" in df.columns:
        print("\ngrounding_gate:")
        print(df["grounding_gate"].value_counts(dropna=False).sort_index().to_string())

    if "validator_model" in df.columns:
        vm = df["validator_model"].dropna()
        if not vm.empty:
            uniq = vm.unique()
            if len(uniq) == 1:
                print(f"\nvalidator_model: {uniq[0]}")
            else:
                print("\nvalidator_model (counts):")
                print(vm.value_counts().to_string())

    print("\noverall_score by prompt_id (mean, std, count):")
    print(df.groupby("prompt_id")["overall_score"].agg(["mean", "std", "count"]).round(4))
    print("=== End overview ===\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Statistical comparison of validation scores by prompt_id")
    parser.add_argument("--data-dir", default=str(_HWQC / "experiment_data"))
    parser.add_argument("--scores", default="validation_scores.csv")
    args = parser.parse_args()

    path = Path(args.data_dir) / args.scores
    if not path.is_file():
        raise SystemExit(f"Missing {path}. Run run_validation.py first.")

    scores = pd.read_csv(path)
    if scores.empty:
        raise SystemExit("validation_scores.csv is empty")

    _print_run_overview(scores, path)

    prompts = sorted(scores["prompt_id"].dropna().unique().tolist())
    if len(prompts) < 2:
        raise SystemExit("Need at least two prompt_id values for comparison")

    groups = [scores.query(f'prompt_id == "{p}"')["overall_score"] for p in prompts]
    b_stat, b_p = bartlett(*groups)
    print(f"\nBartlett homogeneity p={b_p:.6f}")
    var_equal = b_p >= 0.05

    if len(prompts) == 2:
        a, b = groups[0], groups[1]
        tt = pg.ttest(a, b, correction=not var_equal)
        print("\nT-test (two prompts):")
        print(tt)
    else:
        if var_equal:
            anova = pg.anova(dv="overall_score", between="prompt_id", data=scores)
            print("\nANOVA (equal variances):")
        else:
            anova = pg.welch_anova(dv="overall_score", between="prompt_id", data=scores)
            print("\nWelch ANOVA:")
        print(anova)

    fig, ax = plt.subplots(figsize=(6, 4))
    data = [scores.loc[scores["prompt_id"] == p, "overall_score"].values for p in prompts]
    ax.boxplot(data, tick_labels=prompts)
    ax.set_title("Overall validation score by prompt")
    ax.set_xlabel("prompt_id")
    ax.set_ylabel("overall_score (1–5 mean)")
    plt.tight_layout()
    plot_path = Path(args.data_dir) / "overall_score_by_prompt.png"
    fig.savefig(plot_path, dpi=150)
    print(f"\nWrote plot: {plot_path}")


if __name__ == "__main__":
    main()
