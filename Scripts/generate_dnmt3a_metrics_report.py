import argparse
import json
import os

import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def build_task_metrics(y_true, y_pred, labels, task_name):
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        zero_division=0,
    )
    rows = []
    for label, p, r, f, s in zip(labels, precision, recall, f1, support):
        rows.append(
            {
                "task": task_name,
                "label": str(label),
                "metric_scope": "class",
                "accuracy": "",
                "precision": round(float(p), 6),
                "recall": round(float(r), 6),
                "f1": round(float(f), 6),
                "support": int(s),
            }
        )

    rows.append(
        {
            "task": task_name,
            "label": "overall",
            "metric_scope": "overall",
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
            "precision": round(float(precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)[0]), 6),
            "recall": round(float(precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)[1]), 6),
            "f1": round(float(precision_recall_fscore_support(y_true, y_pred, labels=labels, average="macro", zero_division=0)[2]), 6),
            "support": int(len(y_true)),
        }
    )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a compact metrics report from DNMT3A calibration outputs.")
    parser.add_argument(
        "--input-dir",
        default=os.path.join("analysis_outputs", "dnmt3a_intensity_calibration"),
        help="Directory containing summary.json and per_image_results.csv",
    )
    args = parser.parse_args()

    summary_path = os.path.join(args.input_dir, "summary.json")
    results_path = os.path.join(args.input_dir, "per_image_results.csv")
    report_path = os.path.join(args.input_dir, "metrics_report.md")
    mismatch_path = os.path.join(args.input_dir, "metrics_mismatches.csv")
    aggregate_path = os.path.join(args.input_dir, "metrics_aggregate.csv")
    all_metrics_path = os.path.join(args.input_dir, "all_classification_metrics.csv")
    accuracy_path = os.path.join(args.input_dir, "accuracy_metrics.csv")

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    df = pd.read_csv(results_path)

    df["intensity_match"] = df["pred_intensity_score"] == df["gt_intensity_score"]
    df["percent_match"] = df["pred_percent_score"] == df["gt_percent_score"]
    df["expression_match"] = df["pred_expression"] == df["gt_expression"]
    metrics = summary["metrics"]

    mismatch_df = df.loc[
        ~(df["intensity_match"] & df["percent_match"] & df["expression_match"]),
        [
            "file",
            "patient_id",
            "location",
            "weak_1plus_pct",
            "medium_2plus_pct",
            "strong_3plus_pct",
            "positive_area_pct",
            "positive_nuclei_pct",
            "pred_intensity_score",
            "gt_intensity_score",
            "pred_percent_score",
            "gt_percent_score",
            "pred_final_score",
            "gt_final_score",
            "pred_expression",
            "gt_expression",
        ],
    ].copy()
    mismatch_df.to_csv(mismatch_path, index=False, encoding="utf-8-sig")

    aggregate_rows = [
        {"metric": "case_count", "value": len(df)},
        {"metric": "intensity_match_count", "value": int(df["intensity_match"].sum())},
        {"metric": "percent_match_count", "value": int(df["percent_match"].sum())},
        {"metric": "expression_match_count", "value": int(df["expression_match"].sum())},
        {"metric": "mismatch_case_count", "value": len(mismatch_df)},
        {"metric": "mean_weak_1plus_pct", "value": round(df["weak_1plus_pct"].mean(), 4)},
        {"metric": "mean_medium_2plus_pct", "value": round(df["medium_2plus_pct"].mean(), 4)},
        {"metric": "mean_strong_3plus_pct", "value": round(df["strong_3plus_pct"].mean(), 4)},
        {"metric": "mean_positive_area_pct", "value": round(df["positive_area_pct"].mean(), 4)},
        {"metric": "mean_positive_nuclei_pct", "value": round(df["positive_nuclei_pct"].mean(), 4)},
    ]
    aggregate_df = pd.DataFrame(aggregate_rows)
    aggregate_df.to_csv(aggregate_path, index=False, encoding="utf-8-sig")

    all_metric_rows = []
    all_metric_rows.extend(
        build_task_metrics(
            df["gt_intensity_score"],
            df["pred_intensity_score"],
            [1, 2, 3],
            "intensity",
        )
    )
    all_metric_rows.extend(
        build_task_metrics(
            df["gt_percent_score"],
            df["pred_percent_score"],
            [0, 1, 2, 3],
            "percent_score",
        )
    )
    all_metric_rows.extend(
        build_task_metrics(
            df["gt_expression"],
            df["pred_expression"],
            ["low", "high"],
            "expression",
        )
    )
    all_metrics_df = pd.DataFrame(all_metric_rows)
    all_metrics_df.to_csv(all_metrics_path, index=False, encoding="utf-8-sig")

    accuracy_rows = [
        {"metric": "intensity_accuracy", "value": metrics["intensity_accuracy"]},
        {"metric": "percent_score_accuracy", "value": metrics["percent_score_accuracy"]},
        {"metric": "expression_accuracy", "value": metrics["expression_accuracy"]},
        {"metric": "intensity_match_count", "value": int(df["intensity_match"].sum())},
        {"metric": "percent_score_match_count", "value": int(df["percent_match"].sum())},
        {"metric": "expression_match_count", "value": int(df["expression_match"].sum())},
        {"metric": "total_case_count", "value": len(df)},
    ]
    pd.DataFrame(accuracy_rows).to_csv(accuracy_path, index=False, encoding="utf-8-sig")

    thresholds = summary["recommended_thresholds"]

    lines = [
        "# DNMT3A Metrics Report",
        "",
        "## Overall Metrics",
        f"- Case count: {len(df)}",
        f"- Intensity accuracy: {metrics['intensity_accuracy']:.3f}",
        f"- Intensity macro-F1: {metrics['intensity_macro_f1']:.3f}",
        f"- Percent-score accuracy: {metrics['percent_score_accuracy']:.3f}",
        f"- Percent-score macro-F1: {metrics['percent_score_macro_f1']:.3f}",
        f"- Expression accuracy: {metrics['expression_accuracy']:.3f}",
        f"- Expression macro-F1: {metrics['expression_macro_f1']:.3f}",
        "",
        "## Detailed Metric File",
        f"- See `all_classification_metrics.csv` for accuracy / precision / recall / F1 / support by task and class.",
        "",
        "## Recommended Thresholds",
        f"- T0 summary filter: {thresholds['t0_summary_filter']}",
        f"- T1 weak->medium: {thresholds['t1_weak_to_medium']}",
        f"- T2 medium->strong: {thresholds['t2_medium_to_strong']}",
        f"- P0 positive nucleus: {thresholds['p0_positive_nucleus']}",
        f"- Intensity summary statistic: `{thresholds['intensity_summary_statistic']}`",
        "",
        "## Confusion Matrices",
        f"- Intensity [rows=GT 1/2/3, cols=Pred 1/2/3]: {metrics['intensity_confusion_matrix']}",
        f"- Percent-score [rows=GT 0/1/2/3, cols=Pred 0/1/2/3]: {metrics['percent_score_confusion_matrix']}",
        f"- Expression [rows=GT low/high, cols=Pred low/high]: {metrics['expression_confusion_matrix']}",
        "",
        "## Match Counts",
        f"- Intensity match: {int(df['intensity_match'].sum())}/{len(df)}",
        f"- Percent-score match: {int(df['percent_match'].sum())}/{len(df)}",
        f"- Expression match: {int(df['expression_match'].sum())}/{len(df)}",
        f"- Any mismatch: {len(mismatch_df)}/{len(df)}",
        "",
        "## Mean Predicted Composition",
        f"- Mean weak(1+) %: {df['weak_1plus_pct'].mean():.2f}",
        f"- Mean medium(2+) %: {df['medium_2plus_pct'].mean():.2f}",
        f"- Mean strong(3+) %: {df['strong_3plus_pct'].mean():.2f}",
        f"- Mean positive area %: {df['positive_area_pct'].mean():.2f}",
        f"- Mean positive nuclei %: {df['positive_nuclei_pct'].mean():.2f}",
        "",
        "## Remaining Mismatch Cases",
    ]

    if mismatch_df.empty:
        lines.append("- None")
    else:
        for _, row in mismatch_df.iterrows():
            lines.append(
                f"- {row['file']}: intensity {row['pred_intensity_score']} vs {row['gt_intensity_score']}, "
                f"percent {row['pred_percent_score']} vs {row['gt_percent_score']}, "
                f"expression {row['pred_expression']} vs {row['gt_expression']}"
            )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("Report:", report_path)
    print("Mismatch CSV:", mismatch_path)
    print("Aggregate CSV:", aggregate_path)
    print("All metrics CSV:", all_metrics_path)


if __name__ == "__main__":
    main()
