import argparse
import json
import os
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from skimage.color import rgb2hed
from skimage.filters import threshold_otsu
from skimage.measure import label, regionprops_table
from skimage.morphology import binary_closing, binary_opening, disk, remove_small_objects


@dataclass
class ImageAnalysis:
    file: str
    patient_id: str
    gt_intensity: int
    gt_percent_score: int
    gt_final_score: int
    gt_expression: str
    location: str
    region_features: np.ndarray
    nuclei_features: np.ndarray
    tissue_pixels: int
    positive_pixels: int
    positive_area_pct: float


def discover_dataset(root_dir: str) -> tuple[str, str]:
    dataset_dir = next(
        entry for entry in os.listdir(root_dir)
        if entry.startswith("DNMT3A ") and os.path.isdir(os.path.join(root_dir, entry))
    )
    excel_file = next(
        entry for entry in os.listdir(os.path.join(root_dir, dataset_dir))
        if entry.lower().endswith(".xlsx")
    )
    return os.path.join(root_dir, dataset_dir), excel_file


def load_annotations(dataset_dir: str, excel_file: str) -> pd.DataFrame:
    df = pd.read_excel(os.path.join(dataset_dir, excel_file))
    df = df[df["patientId"].notna()].copy().iloc[:, :6]
    df.columns = [
        "patient_id",
        "intensity",
        "percent_score",
        "final_score",
        "expression",
        "location",
    ]
    for col in ["intensity", "percent_score", "final_score"]:
        df[col] = df[col].astype(str).str.extract(r"(\d+)").astype(int)
    df["patient_id"] = df["patient_id"].astype(str)
    df["expression"] = df["expression"].astype(str).str.lower()
    return df


def map_file_to_patient_id(filename: str, patient_ids: set[str]) -> str | None:
    match = re.match(r"DNMT3A_(\d+)_block(\d+)\.(jpg|jpeg|png|tif|tiff)$", filename, re.I)
    if not match:
        return None
    pid, block = match.group(1), match.group(2)
    block_key = f"{pid}_{block}"
    return block_key if block_key in patient_ids else pid


def white_balance(img: np.ndarray) -> np.ndarray:
    gray = img.mean(axis=2)
    bright_mask = gray >= np.quantile(gray, 0.9)
    if bright_mask.sum() == 0:
        return img
    reference = np.percentile(img[bright_mask], 95, axis=0)
    reference = np.clip(reference, 180, 255)
    balanced = img.astype(np.float32) / reference * 255.0
    return np.clip(balanced, 0, 255).astype(np.uint8)


def analyze_image(image_path: str, region_low_percentile: float = 70.0) -> tuple[np.ndarray, np.ndarray, int, int]:
    img = np.asarray(Image.open(image_path).convert("RGB"))
    img = white_balance(img)
    img_f = img.astype(np.float32) / 255.0

    gray = img_f.mean(axis=2)
    tissue_mask = gray < min(0.95, np.quantile(gray, 0.95))

    dab = np.clip(rgb2hed(img_f)[:, :, 2], 0, None)
    dab_tissue = dab[tissue_mask]
    if dab_tissue.size == 0:
        return np.array([], dtype=float), np.array([], dtype=float), 0, 0

    dab_thresh = max(np.percentile(dab_tissue, region_low_percentile), threshold_otsu(dab_tissue))
    positive_mask = (dab > dab_thresh) & tissue_mask
    positive_mask = binary_opening(positive_mask, disk(1))
    positive_mask = binary_closing(positive_mask, disk(1))
    positive_mask = remove_small_objects(positive_mask, 16)

    labeled = label(positive_mask)
    props = regionprops_table(
        labeled,
        intensity_image=dab,
        properties=("label", "area", "mean_intensity"),
    )
    region_features = np.array([], dtype=float)
    if len(props["label"]) > 0:
        areas = np.asarray(props["area"])
        means = np.asarray(props["mean_intensity"])
        keep = (areas >= 16) & (areas <= 20000)
        means = means[keep]
        if means.size > 0:
            norm = max(np.percentile(dab_tissue, 99), 1e-6)
            region_features = (means / norm).astype(float)

    hematoxylin = np.clip(rgb2hed(img_f)[:, :, 0], 0, None)
    h_tissue = hematoxylin[tissue_mask]
    if h_tissue.size == 0:
        return region_features, np.array([], dtype=float), int(tissue_mask.sum()), int(positive_mask.sum())
    nuclei_thresh = threshold_otsu(h_tissue)
    nuclei_mask = (hematoxylin > nuclei_thresh) & tissue_mask
    nuclei_mask = binary_opening(nuclei_mask, disk(1))
    nuclei_mask = binary_closing(nuclei_mask, disk(1))
    nuclei_mask = remove_small_objects(nuclei_mask, 24)

    nuclei_labeled = label(nuclei_mask)
    nuclei_props = regionprops_table(
        nuclei_labeled,
        intensity_image=dab,
        properties=("label", "area", "mean_intensity"),
    )
    nuclei_features = np.array([], dtype=float)
    if len(nuclei_props["label"]) > 0:
        nuclei_areas = np.asarray(nuclei_props["area"])
        nuclei_means = np.asarray(nuclei_props["mean_intensity"])
        keep = (nuclei_areas >= 24) & (nuclei_areas <= 4000)
        nuclei_means = nuclei_means[keep]
        if nuclei_means.size > 0:
            norm = max(np.percentile(dab_tissue, 99), 1e-6)
            nuclei_features = (nuclei_means / norm).astype(float)

    return region_features, nuclei_features, int(tissue_mask.sum()), int(positive_mask.sum())


def percent_to_score(positive_pct: float) -> int:
    if positive_pct <= 0:
        return 0
    if positive_pct < 10:
        return 1
    if positive_pct <= 50:
        return 2
    return 3


def summarize_feature(values: np.ndarray, feature_name: str) -> float:
    if feature_name == "mean":
        return float(np.mean(values))
    if feature_name == "median":
        return float(np.median(values))
    if feature_name == "p75":
        return float(np.percentile(values, 75))
    if feature_name == "p90":
        return float(np.percentile(values, 90))
    raise ValueError(f"Unsupported feature summary: {feature_name}")


def predict_intensity(values: np.ndarray, t0: float, t1: float, t2: float, summary_name: str) -> int:
    filtered = values[values >= t0]
    pool = filtered if filtered.size else values
    if pool.size == 0:
        return 1
    summary_value = summarize_feature(pool, summary_name)
    if summary_value < t1:
        return 1
    if summary_value < t2:
        return 2
    return 3


def intensity_consistency_adjustment(
    raw_intensity: int,
    region_features: np.ndarray,
    nuclei_features: np.ndarray,
    t1: float,
    t2: float,
    min_strong_pct_for_strong: float = 12.0,
    min_weak_pct_for_demotion: float = 70.0,
) -> int:
    if region_features.size == 0 and nuclei_features.size > 0:
        nuclei_summary = summarize_feature(nuclei_features, "p90")
        return 1 if nuclei_summary < t1 else 2 if nuclei_summary < t2 else 3

    if region_features.size == 0:
        return raw_intensity

    weak_pct = 100.0 * np.mean(region_features < t1)
    strong_pct = 100.0 * np.mean(region_features >= t2)
    if raw_intensity == 3 and strong_pct < min_strong_pct_for_strong and weak_pct >= min_weak_pct_for_demotion:
        return 2
    return raw_intensity


def search_thresholds(samples: list[ImageAnalysis]) -> dict:
    pooled = np.concatenate([s.region_features for s in samples if s.region_features.size > 0])
    candidates = np.unique(np.round(np.quantile(pooled, np.linspace(0.05, 0.95, 21)), 4))
    summary_names = ["mean", "median", "p75", "p90"]

    best = None
    for t0 in candidates[:-2]:
        for t1 in candidates[1:-1]:
            if t1 <= t0:
                continue
            for t2 in candidates[2:]:
                if t2 <= t1:
                    continue
                for summary_name in summary_names:
                    y_true = []
                    y_pred = []
                    for sample in samples:
                        pred = predict_intensity(sample.region_features, t0, t1, t2, summary_name)
                        pred = intensity_consistency_adjustment(
                            pred,
                            sample.region_features,
                            sample.nuclei_features,
                            t1,
                            t2,
                        )
                        y_true.append(sample.gt_intensity)
                        y_pred.append(pred)

                    macro_f1 = f1_score(y_true, y_pred, average="macro", labels=[1, 2, 3])
                    acc = accuracy_score(y_true, y_pred)
                    score = (macro_f1, acc)
                    if best is None or score > (best["macro_f1"], best["accuracy"]):
                        best = {
                            "t0": float(t0),
                            "t1": float(t1),
                            "t2": float(t2),
                            "summary_name": summary_name,
                            "macro_f1": float(macro_f1),
                            "accuracy": float(acc),
                        }
    return best


def search_positive_nuclei_threshold(samples: list[ImageAnalysis]) -> dict:
    pooled = np.concatenate([s.nuclei_features for s in samples if s.nuclei_features.size > 0])
    candidates = np.unique(np.round(np.quantile(pooled, np.linspace(0.05, 0.95, 31)), 4))

    best = None
    for p0 in candidates:
        y_true = []
        y_pred = []
        for sample in samples:
            if sample.nuclei_features.size == 0:
                positive_pct = 0.0
            else:
                positive_pct = 100.0 * np.mean(sample.nuclei_features >= p0)
            y_true.append(sample.gt_percent_score)
            y_pred.append(percent_to_score(positive_pct))

        acc = accuracy_score(y_true, y_pred)
        macro_f1 = f1_score(y_true, y_pred, average="macro", labels=[0, 1, 2, 3], zero_division=0)
        score = (acc, macro_f1)
        if best is None or score > (best["accuracy"], best["macro_f1"]):
            best = {
                "p0": float(p0),
                "accuracy": float(acc),
                "macro_f1": float(macro_f1),
            }
    return best


def build_samples(dataset_dir: str, annotations: pd.DataFrame, region_low_percentile: float) -> list[ImageAnalysis]:
    patient_ids = set(annotations["patient_id"])
    samples: list[ImageAnalysis] = []
    for filename in sorted(os.listdir(dataset_dir)):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
            continue
        patient_id = map_file_to_patient_id(filename, patient_ids)
        if patient_id is None:
            continue
        row = annotations[annotations["patient_id"] == patient_id].iloc[0]
        region_features, nuclei_features, tissue_pixels, positive_pixels = analyze_image(
            os.path.join(dataset_dir, filename),
            region_low_percentile=region_low_percentile,
        )
        positive_area_pct = 100.0 * positive_pixels / tissue_pixels if tissue_pixels > 0 else 0.0
        samples.append(
            ImageAnalysis(
                file=filename,
                patient_id=patient_id,
                gt_intensity=int(row["intensity"]),
                gt_percent_score=int(row["percent_score"]),
                gt_final_score=int(row["final_score"]),
                gt_expression=str(row["expression"]),
                location=str(row["location"]),
                region_features=region_features,
                nuclei_features=nuclei_features,
                tissue_pixels=tissue_pixels,
                positive_pixels=positive_pixels,
                positive_area_pct=positive_area_pct,
            )
        )
    return samples


def evaluate_samples(samples: list[ImageAnalysis], best: dict, positive_best: dict) -> tuple[pd.DataFrame, dict]:
    rows = []
    gt_intensity = []
    pred_intensity = []
    gt_expression = []
    pred_expression = []

    for sample in samples:
        values = sample.region_features
        intensity_score = predict_intensity(
            values,
            best["t0"],
            best["t1"],
            best["t2"],
            best["summary_name"],
        )
        intensity_score = intensity_consistency_adjustment(
            intensity_score,
            sample.region_features,
            sample.nuclei_features,
            best["t1"],
            best["t2"],
        )
        if values.size == 0:
            weak_pct = 0.0
            medium_pct = 0.0
            strong_pct = 0.0
        else:
            weak_count = int(np.sum(values < best["t1"]))
            medium_count = int(np.sum((values >= best["t1"]) & (values < best["t2"])))
            strong_count = int(np.sum(values >= best["t2"]))
            total_regions = max(weak_count + medium_count + strong_count, 1)
            weak_pct = 100.0 * weak_count / total_regions
            medium_pct = 100.0 * medium_count / total_regions
            strong_pct = 100.0 * strong_count / total_regions

        if sample.nuclei_features.size == 0:
            positive_nuclei_pct = 0.0
        else:
            positive_nuclei_pct = 100.0 * np.mean(sample.nuclei_features >= positive_best["p0"])
        percent_score = percent_to_score(positive_nuclei_pct)
        final_score = intensity_score * percent_score
        expression = "high" if final_score > 4 else "low"

        gt_intensity.append(sample.gt_intensity)
        pred_intensity.append(intensity_score)
        gt_expression.append(sample.gt_expression)
        pred_expression.append(expression)

        rows.append(
            {
                "file": sample.file,
                "patient_id": sample.patient_id,
                "location": sample.location,
                "region_count": int(values.size),
                "positive_area_pct": round(sample.positive_area_pct, 2),
                "positive_nuclei_pct": round(positive_nuclei_pct, 2),
                "weak_1plus_pct": round(weak_pct, 2),
                "medium_2plus_pct": round(medium_pct, 2),
                "strong_3plus_pct": round(strong_pct, 2),
                "pred_intensity_score": intensity_score,
                "pred_percent_score": percent_score,
                "pred_final_score": final_score,
                "pred_expression": expression,
                "gt_intensity_score": sample.gt_intensity,
                "gt_percent_score": sample.gt_percent_score,
                "gt_final_score": sample.gt_final_score,
                "gt_expression": sample.gt_expression,
            }
        )

    results_df = pd.DataFrame(rows)
    metrics = {
        "intensity_accuracy": float(accuracy_score(gt_intensity, pred_intensity)),
        "intensity_macro_f1": float(f1_score(gt_intensity, pred_intensity, average="macro", labels=[1, 2, 3])),
        "expression_accuracy": float(accuracy_score(gt_expression, pred_expression)),
        "expression_macro_f1": float(f1_score(gt_expression, pred_expression, average="macro", labels=["low", "high"])),
        "percent_score_accuracy": float(accuracy_score(results_df["gt_percent_score"], results_df["pred_percent_score"])),
        "percent_score_macro_f1": float(f1_score(results_df["gt_percent_score"], results_df["pred_percent_score"], average="macro", labels=[0, 1, 2, 3], zero_division=0)),
        "intensity_confusion_matrix": confusion_matrix(gt_intensity, pred_intensity, labels=[1, 2, 3]).tolist(),
        "percent_score_confusion_matrix": confusion_matrix(results_df["gt_percent_score"], results_df["pred_percent_score"], labels=[0, 1, 2, 3]).tolist(),
        "expression_confusion_matrix": confusion_matrix(gt_expression, pred_expression, labels=["low", "high"]).tolist(),
    }
    return results_df, metrics


def save_outputs(output_dir: str, best: dict, positive_best: dict, results_df: pd.DataFrame, metrics: dict, region_low_percentile: float) -> None:
    os.makedirs(output_dir, exist_ok=True)

    results_df.to_csv(os.path.join(output_dir, "per_image_results.csv"), index=False, encoding="utf-8-sig")

    summary = {
        "recommended_thresholds": {
            "t0_summary_filter": round(best["t0"], 4),
            "t1_weak_to_medium": round(best["t1"], 4),
            "t2_medium_to_strong": round(best["t2"], 4),
            "intensity_summary_statistic": best["summary_name"],
            "p0_positive_nucleus": round(positive_best["p0"], 4),
            "strong_demote_rule": {
                "if_predicted_3plus_and_strong_pct_below": 12.0,
                "and_weak_pct_at_or_above": 70.0,
                "then_demote_to": 2,
            },
            "empty_region_fallback": "If no DAB-positive regions are extracted, use nuclei p90 against T1/T2.",
        },
        "preprocessing": {
            "normalization": "95th-percentile white balance on bright background pixels, then DAB OD normalized by tissue DAB 99th percentile",
            "stain_separation": "rgb2hed color deconvolution, DAB channel used for brown stain strength",
            "region_segmentation": f"DAB-positive region mask with threshold = max(DAB {region_low_percentile:.0f}th percentile, Otsu threshold)",
        },
        "metrics": metrics,
        "caveat": "Thresholds are calibrated from 24 image-level labels rather than cell-level pathologist annotations, so they should be treated as preliminary and re-calibrated with more labeled cases.",
    }
    with open(os.path.join(output_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    report_lines = [
        "# DNMT3A Intensity Threshold Calibration",
        "",
        "## Recommended thresholds",
        f"- T0 summary filter: {best['t0']:.4f}",
        f"- T1 weak->medium: {best['t1']:.4f}",
        f"- T2 medium->strong: {best['t2']:.4f}",
        f"- Image-level summary statistic: `{best['summary_name']}` of filtered DAB-positive region intensities",
        "- Consistency rule: if a case is predicted as 3+ but strong-region percentage is <12% while weak-region percentage is >=70%, demote it to 2+",
        "- Empty-region fallback: if no DAB-positive regions are extracted, use nuclei `p90` against T1/T2",
        "",
        "## Metrics",
        f"- Intensity accuracy: {metrics['intensity_accuracy']:.3f}",
        f"- Intensity macro-F1: {metrics['intensity_macro_f1']:.3f}",
        f"- Expression accuracy: {metrics['expression_accuracy']:.3f}",
        f"- Expression macro-F1: {metrics['expression_macro_f1']:.3f}",
        f"- Percent-score accuracy: {metrics['percent_score_accuracy']:.3f}",
        "",
        "## Confusion matrices",
        "- Intensity labels [1, 2, 3]:",
        f"  {metrics['intensity_confusion_matrix']}",
        "- Percent-score labels [0, 1, 2, 3]:",
        f"  {metrics['percent_score_confusion_matrix']}",
        "- Expression labels [low, high]:",
        f"  {metrics['expression_confusion_matrix']}",
        "",
        "## Notes",
        "- The rule is intentionally interpretable: white balance -> color deconvolution -> DAB-positive region extraction -> percentile-normalized OD thresholds.",
        "- Weak/medium/strong percentages are percentages of segmented DAB-positive regions in each image.",
        "- Final score uses predicted intensity x predicted percentage score, where percentage score is derived from the proportion of nuclei-like regions with DAB OD above P0 using the provided 0/<10/11-50/>50 rule.",
        "- Because the ground truth is image-level and the cohort is only 24 images, this should be treated as a preliminary calibration rather than a final clinical threshold set.",
    ]
    with open(os.path.join(output_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate interpretable DNMT3A IHC intensity thresholds from image-level scores.")
    parser.add_argument("--root-dir", default=".", help="Repository root containing the DNMT3A dataset folder.")
    parser.add_argument(
        "--output-dir",
        default=os.path.join("analysis_outputs", "dnmt3a_intensity_calibration"),
        help="Directory to write CSV/JSON/Markdown outputs.",
    )
    parser.add_argument(
        "--region-low-percentile",
        type=float,
        default=70.0,
        help="Lower percentile used in DAB-positive region extraction before threshold search.",
    )
    args = parser.parse_args()

    dataset_dir, excel_file = discover_dataset(args.root_dir)
    annotations = load_annotations(dataset_dir, excel_file)
    samples = build_samples(dataset_dir, annotations, args.region_low_percentile)
    best = search_thresholds(samples)
    positive_best = search_positive_nuclei_threshold(samples)
    results_df, metrics = evaluate_samples(samples, best, positive_best)
    save_outputs(args.output_dir, best, positive_best, results_df, metrics, args.region_low_percentile)

    print("Output directory:", args.output_dir)
    print("Recommended T0/T1/T2:", round(best["t0"], 4), round(best["t1"], 4), round(best["t2"], 4))
    print("Recommended P0:", round(positive_best["p0"], 4))
    print("Summary statistic:", best["summary_name"])
    print("Intensity accuracy:", round(metrics["intensity_accuracy"], 4))
    print("Intensity macro-F1:", round(metrics["intensity_macro_f1"], 4))
    print("Percent-score accuracy:", round(metrics["percent_score_accuracy"], 4))
    print("Expression accuracy:", round(metrics["expression_accuracy"], 4))
    print("Expression macro-F1:", round(metrics["expression_macro_f1"], 4))


if __name__ == "__main__":
    main()
