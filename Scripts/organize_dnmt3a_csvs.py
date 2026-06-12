import os

import pandas as pd


BASE_DIR = os.path.join("analysis_outputs")
FULLSLIDE_CSV = os.path.join(BASE_DIR, "dnmt3a_fullslide_outputs", "source_image_summary.csv")
MASK_CSV = os.path.join(BASE_DIR, "dnmt3a_cancer_mask_outputs", "source_image_summary.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "dnmt3a_csv_organized")


def rename_columns(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    renamed = df.copy()
    keep_key = {"relative_dir", "source_image"}
    renamed.columns = [
        col if col in keep_key else f"{prefix}_{col}"
        for col in renamed.columns
    ]
    return renamed


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fullslide_df = pd.read_csv(FULLSLIDE_CSV)
    mask_df = pd.read_csv(MASK_CSV)

    fullslide_prefixed = rename_columns(fullslide_df, "fullslide")
    mask_prefixed = rename_columns(mask_df, "cancer_mask")

    comparison_df = fullslide_prefixed.merge(
        mask_prefixed,
        on=["relative_dir", "source_image"],
        how="outer",
    )

    delta_pairs = [
        ("region_count", "region_count"),
        ("nuclei_count", "nuclei_count"),
        ("positive_area_pct", "positive_area_pct"),
        ("positive_nuclei_pct", "positive_nuclei_pct"),
        ("weak_1plus_pct", "weak_1plus_pct"),
        ("medium_2plus_pct", "medium_2plus_pct"),
        ("strong_3plus_pct", "strong_3plus_pct"),
        ("pred_intensity_score", "pred_intensity_score"),
        ("pred_percent_score", "pred_percent_score"),
        ("pred_final_score", "pred_final_score"),
    ]
    for left, right in delta_pairs:
        comparison_df[f"delta_{left}"] = (
            comparison_df[f"cancer_mask_{right}"] - comparison_df[f"fullslide_{left}"]
        )

    ordered_columns = [
        "relative_dir",
        "source_image",
        "fullslide_pred_expression",
        "cancer_mask_pred_expression",
        "fullslide_pred_intensity_score",
        "cancer_mask_pred_intensity_score",
        "delta_pred_intensity_score",
        "fullslide_pred_percent_score",
        "cancer_mask_pred_percent_score",
        "delta_pred_percent_score",
        "fullslide_pred_final_score",
        "cancer_mask_pred_final_score",
        "delta_pred_final_score",
        "fullslide_positive_nuclei_pct",
        "cancer_mask_positive_nuclei_pct",
        "delta_positive_nuclei_pct",
        "fullslide_positive_area_pct",
        "cancer_mask_positive_area_pct",
        "delta_positive_area_pct",
        "fullslide_weak_1plus_pct",
        "cancer_mask_weak_1plus_pct",
        "delta_weak_1plus_pct",
        "fullslide_medium_2plus_pct",
        "cancer_mask_medium_2plus_pct",
        "delta_medium_2plus_pct",
        "fullslide_strong_3plus_pct",
        "cancer_mask_strong_3plus_pct",
        "delta_strong_3plus_pct",
        "fullslide_region_count",
        "cancer_mask_region_count",
        "delta_region_count",
        "fullslide_nuclei_count",
        "cancer_mask_nuclei_count",
        "delta_nuclei_count",
    ]
    comparison_df = comparison_df[ordered_columns].sort_values("source_image")

    expression_changed_df = comparison_df[
        comparison_df["fullslide_pred_expression"] != comparison_df["cancer_mask_pred_expression"]
    ].copy()
    intensity_changed_df = comparison_df[
        comparison_df["fullslide_pred_intensity_score"] != comparison_df["cancer_mask_pred_intensity_score"]
    ].copy()

    comparison_path = os.path.join(OUTPUT_DIR, "dnmt3a_fullslide_vs_cancer_mask_comparison.csv")
    expression_changed_path = os.path.join(OUTPUT_DIR, "dnmt3a_expression_changed_cases.csv")
    intensity_changed_path = os.path.join(OUTPUT_DIR, "dnmt3a_intensity_changed_cases.csv")

    comparison_df.to_csv(comparison_path, index=False, encoding="utf-8-sig")
    expression_changed_df.to_csv(expression_changed_path, index=False, encoding="utf-8-sig")
    intensity_changed_df.to_csv(intensity_changed_path, index=False, encoding="utf-8-sig")

    print("Comparison CSV:", comparison_path)
    print("Expression-changed CSV:", expression_changed_path)
    print("Intensity-changed CSV:", intensity_changed_path)


if __name__ == "__main__":
    main()
