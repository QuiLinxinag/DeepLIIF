import argparse
import json
import os

import pandas as pd

from calibrate_dnmt3a_intensity_thresholds import (
    analyze_image,
    intensity_consistency_adjustment,
    percent_to_score,
    predict_intensity,
)


def load_thresholds(summary_json: str) -> dict:
    with open(summary_json, "r", encoding="utf-8") as f:
        summary = json.load(f)
    return summary["recommended_thresholds"]


def infer_mask_name(filename: str, image_suffix: str, mask_suffix: str) -> str:
    if image_suffix and image_suffix in filename:
        return filename.replace(image_suffix, mask_suffix)
    stem, ext = os.path.splitext(filename)
    return f"{stem}{mask_suffix}{ext}"


def classify_image(
    image_path: str,
    thresholds: dict,
    region_low_percentile: float,
    roi_mask_path: str | None = None,
    mask_threshold: int = 127,
) -> dict:
    region_features, nuclei_features, tissue_pixels, positive_pixels = analyze_image(
        image_path,
        region_low_percentile=region_low_percentile,
        roi_mask_path=roi_mask_path,
        mask_threshold=mask_threshold,
    )

    intensity_score = predict_intensity(
        region_features,
        thresholds["t0_summary_filter"],
        thresholds["t1_weak_to_medium"],
        thresholds["t2_medium_to_strong"],
        thresholds["intensity_summary_statistic"],
    )
    intensity_score = intensity_consistency_adjustment(
        intensity_score,
        region_features,
        nuclei_features,
        thresholds["t1_weak_to_medium"],
        thresholds["t2_medium_to_strong"],
    )

    if region_features.size == 0:
        weak_count = 0
        medium_count = 0
        strong_count = 0
        weak_pct = 0.0
        medium_pct = 0.0
        strong_pct = 0.0
    else:
        weak_count = int((region_features < thresholds["t1_weak_to_medium"]).sum())
        medium_count = int(((region_features >= thresholds["t1_weak_to_medium"]) & (region_features < thresholds["t2_medium_to_strong"])).sum())
        strong_count = int((region_features >= thresholds["t2_medium_to_strong"]).sum())
        total_regions = max(weak_count + medium_count + strong_count, 1)
        weak_pct = 100.0 * weak_count / total_regions
        medium_pct = 100.0 * medium_count / total_regions
        strong_pct = 100.0 * strong_count / total_regions

    if nuclei_features.size == 0:
        positive_nuclei_count = 0
        positive_nuclei_pct = 0.0
    else:
        positive_nuclei_count = int((nuclei_features >= thresholds["p0_positive_nucleus"]).sum())
        positive_nuclei_pct = 100.0 * positive_nuclei_count / nuclei_features.size

    positive_area_pct = 100.0 * positive_pixels / tissue_pixels if tissue_pixels > 0 else 0.0
    percent_score = percent_to_score(positive_nuclei_pct)
    final_score = intensity_score * percent_score
    expression = "high" if final_score > 4 else "low"

    return {
        "region_count": int(region_features.size),
        "nuclei_count": int(nuclei_features.size),
        "weak_count": int(weak_count),
        "medium_count": int(medium_count),
        "strong_count": int(strong_count),
        "positive_nuclei_count": int(positive_nuclei_count),
        "tissue_pixels": int(tissue_pixels),
        "positive_pixels": int(positive_pixels),
        "positive_area_pct": round(positive_area_pct, 2),
        "positive_nuclei_pct": round(positive_nuclei_pct, 2),
        "weak_1plus_pct": round(weak_pct, 2),
        "medium_2plus_pct": round(medium_pct, 2),
        "strong_3plus_pct": round(strong_pct, 2),
        "pred_intensity_score": int(intensity_score),
        "pred_percent_score": int(percent_score),
        "pred_final_score": int(final_score),
        "pred_expression": expression,
    }


def source_image_name(filename: str) -> str:
    if "_x" in filename:
        return filename.split("_x", 1)[0]
    return os.path.splitext(filename)[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply calibrated DNMT3A intensity thresholds to a folder of images.")
    parser.add_argument("--input-dir", required=True, help="Directory containing images, scanned recursively.")
    parser.add_argument(
        "--summary-json",
        default=os.path.join("analysis_outputs", "dnmt3a_intensity_calibration", "summary.json"),
        help="Calibration summary JSON with T0/T1/T2/P0 thresholds.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join("analysis_outputs", "dnmt3a_patch_outputs"),
        help="Directory to save CSV outputs.",
    )
    parser.add_argument(
        "--region-low-percentile",
        type=float,
        default=70.0,
        help="Lower percentile used in DAB-positive region extraction.",
    )
    parser.add_argument(
        "--mask-dir",
        default="",
        help="Optional directory containing predicted cancer masks. When provided, analysis is restricted to masked cancer regions.",
    )
    parser.add_argument(
        "--image-suffix",
        default="",
        help="Filename token in source images to be replaced when matching masks, e.g. _IHC.",
    )
    parser.add_argument(
        "--mask-suffix",
        default="_CancerSeg",
        help="Filename token used for mask files when matching masks, e.g. _CancerSeg.",
    )
    parser.add_argument(
        "--mask-threshold",
        type=int,
        default=127,
        help="Binary threshold applied to grayscale cancer masks.",
    )
    args = parser.parse_args()

    thresholds = load_thresholds(args.summary_json)
    rows = []

    for cur, _, files in os.walk(args.input_dir):
        rel_dir = os.path.relpath(cur, args.input_dir)
        for filename in sorted(files):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
                continue
            image_path = os.path.join(cur, filename)
            roi_mask_path = None
            if args.mask_dir:
                rel_mask_dir = cur if rel_dir == "." else os.path.join(args.mask_dir, rel_dir)
                if rel_dir == ".":
                    rel_mask_dir = args.mask_dir
                mask_name = infer_mask_name(filename, args.image_suffix, args.mask_suffix)
                candidate_mask_path = os.path.join(rel_mask_dir, mask_name)
                if not os.path.exists(candidate_mask_path):
                    raise FileNotFoundError(
                        f"Predicted cancer mask not found for {image_path}: expected {candidate_mask_path}"
                    )
                roi_mask_path = candidate_mask_path

            result = classify_image(
                image_path,
                thresholds,
                args.region_low_percentile,
                roi_mask_path=roi_mask_path,
                mask_threshold=args.mask_threshold,
            )
            result.update(
                {
                    "relative_dir": rel_dir,
                    "file": filename,
                    "source_image": source_image_name(filename),
                    "image_path": image_path,
                    "roi_mask_path": roi_mask_path or "",
                }
            )
            rows.append(result)

    os.makedirs(args.output_dir, exist_ok=True)
    patch_df = pd.DataFrame(rows)
    patch_csv = os.path.join(args.output_dir, "patch_results.csv")
    patch_df.to_csv(patch_csv, index=False, encoding="utf-8-sig")

    source_df = patch_df.groupby(["relative_dir", "source_image"], as_index=False).agg(
        {
            "region_count": "sum",
            "nuclei_count": "sum",
            "weak_count": "sum",
            "medium_count": "sum",
            "strong_count": "sum",
            "positive_nuclei_count": "sum",
            "tissue_pixels": "sum",
            "positive_pixels": "sum",
        }
    )
    total_regions = (source_df["weak_count"] + source_df["medium_count"] + source_df["strong_count"]).clip(lower=1)
    source_df["weak_1plus_pct"] = 100.0 * source_df["weak_count"] / total_regions
    source_df["medium_2plus_pct"] = 100.0 * source_df["medium_count"] / total_regions
    source_df["strong_3plus_pct"] = 100.0 * source_df["strong_count"] / total_regions
    source_df["positive_area_pct"] = 100.0 * source_df["positive_pixels"] / source_df["tissue_pixels"].clip(lower=1)
    source_df["positive_nuclei_pct"] = 100.0 * source_df["positive_nuclei_count"] / source_df["nuclei_count"].clip(lower=1)

    source_df["pred_intensity_score"] = source_df[["weak_count", "medium_count", "strong_count"]].idxmax(axis=1).map(
        {"weak_count": 1, "medium_count": 2, "strong_count": 3}
    )
    source_df["pred_percent_score"] = source_df["positive_nuclei_pct"].apply(percent_to_score)
    source_df["pred_final_score"] = source_df["pred_intensity_score"] * source_df["pred_percent_score"]
    source_df["pred_expression"] = source_df["pred_final_score"].apply(lambda x: "high" if x > 4 else "low")
    for col in ["weak_1plus_pct", "medium_2plus_pct", "strong_3plus_pct", "positive_area_pct", "positive_nuclei_pct"]:
        source_df[col] = source_df[col].round(2)
    source_csv = os.path.join(args.output_dir, "source_image_summary.csv")
    source_df.to_csv(source_csv, index=False, encoding="utf-8-sig")

    print("Processed images:", len(patch_df))
    print("Patch results:", patch_csv)
    print("Source summary:", source_csv)


if __name__ == "__main__":
    main()
