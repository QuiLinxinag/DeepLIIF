import argparse
import json
import os

import numpy as np
from PIL import Image
from skimage.color import rgb2hed
from skimage.filters import threshold_otsu
from skimage.measure import label, regionprops
from skimage.morphology import binary_closing, binary_opening, disk, remove_small_objects

from apply_dnmt3a_intensity_thresholds import classify_image, infer_mask_name, load_thresholds
from calibrate_dnmt3a_intensity_thresholds import load_roi_mask, white_balance


CLASS_COLORS = {
    0: np.array([0, 0, 0], dtype=np.uint8),
    1: np.array([255, 230, 80], dtype=np.uint8),
    2: np.array([255, 140, 0], dtype=np.uint8),
    3: np.array([220, 30, 30], dtype=np.uint8),
}


def build_intensity_maps(
    image_path: str,
    roi_mask_path: str,
    thresholds: dict,
    region_low_percentile: float,
    mask_threshold: int,
):
    img = np.asarray(Image.open(image_path).convert("RGB"))
    img = white_balance(img)
    img_f = img.astype(np.float32) / 255.0

    gray = img_f.mean(axis=2)
    tissue_mask = gray < min(0.95, np.quantile(gray, 0.95))
    roi_mask = load_roi_mask(roi_mask_path, tissue_mask.shape, mask_threshold=mask_threshold)
    tissue_mask = tissue_mask & roi_mask

    dab = np.clip(rgb2hed(img_f)[:, :, 2], 0, None)
    dab_tissue = dab[tissue_mask]
    if dab_tissue.size == 0:
        shape = tissue_mask.shape
        return img, np.zeros((shape[0], shape[1]), dtype=np.uint8), np.zeros((shape[0], shape[1], 3), dtype=np.uint8)

    dab_thresh = max(np.percentile(dab_tissue, region_low_percentile), threshold_otsu(dab_tissue))
    positive_mask = (dab > dab_thresh) & tissue_mask
    positive_mask = binary_opening(positive_mask, disk(1))
    positive_mask = binary_closing(positive_mask, disk(1))
    positive_mask = remove_small_objects(positive_mask, 16)

    labeled = label(positive_mask)
    norm = max(np.percentile(dab_tissue, 99), 1e-6)

    intensity_class_map = np.zeros_like(labeled, dtype=np.uint8)
    for region in regionprops(labeled, intensity_image=dab):
        if region.area < 16 or region.area > 20000:
            continue
        feature = float(region.mean_intensity / norm)
        if feature < thresholds["t1_weak_to_medium"]:
            cls = 1
        elif feature < thresholds["t2_medium_to_strong"]:
            cls = 2
        else:
            cls = 3
        coords = region.coords
        intensity_class_map[coords[:, 0], coords[:, 1]] = cls

    intensity_rgb = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
    for cls, color in CLASS_COLORS.items():
        if cls == 0:
            continue
        intensity_rgb[intensity_class_map == cls] = color

    overlay = img.copy()
    alpha = 0.45
    active = intensity_class_map > 0
    overlay[active] = (
        (1.0 - alpha) * overlay[active].astype(np.float32) +
        alpha * intensity_rgb[active].astype(np.float32)
    ).astype(np.uint8)

    return img, intensity_class_map, overlay


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cancer-mask-scoped DNMT3A intensity prediction images.")
    parser.add_argument("--input-dir", required=True, help="Directory containing source images.")
    parser.add_argument("--mask-dir", required=True, help="Directory containing cancer ROI masks.")
    parser.add_argument(
        "--summary-json",
        default=os.path.join("analysis_outputs", "dnmt3a_intensity_calibration", "summary.json"),
        help="Calibration summary JSON with T0/T1/T2/P0 thresholds.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join("analysis_outputs", "dnmt3a_cancer_mask_prediction_images"),
        help="Directory to save intensity prediction images.",
    )
    parser.add_argument("--image-suffix", default=".jpg", help="Filename token in source images for mask matching.")
    parser.add_argument("--mask-suffix", default="_SegRefined.png", help="Filename token used for ROI mask files.")
    parser.add_argument("--mask-threshold", type=int, default=127, help="Binary threshold applied to grayscale ROI masks.")
    parser.add_argument("--region-low-percentile", type=float, default=70.0, help="Lower percentile used in DAB-positive region extraction.")
    args = parser.parse_args()

    thresholds = load_thresholds(args.summary_json)
    os.makedirs(args.output_dir, exist_ok=True)

    processed = 0
    for filename in sorted(os.listdir(args.input_dir)):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
            continue

        image_path = os.path.join(args.input_dir, filename)
        mask_name = infer_mask_name(filename, args.image_suffix, args.mask_suffix)
        roi_mask_path = os.path.join(args.mask_dir, mask_name)
        if not os.path.exists(roi_mask_path):
            raise FileNotFoundError(f"ROI mask not found for {filename}: expected {roi_mask_path}")

        _, class_map, overlay = build_intensity_maps(
            image_path,
            roi_mask_path,
            thresholds,
            args.region_low_percentile,
            args.mask_threshold,
        )
        summary = classify_image(
            image_path,
            thresholds,
            args.region_low_percentile,
            roi_mask_path=roi_mask_path,
            mask_threshold=args.mask_threshold,
        )

        stem = os.path.splitext(filename)[0]
        class_rgb = np.zeros((class_map.shape[0], class_map.shape[1], 3), dtype=np.uint8)
        for cls, color in CLASS_COLORS.items():
            if cls == 0:
                continue
            class_rgb[class_map == cls] = color

        Image.fromarray(class_rgb).save(os.path.join(args.output_dir, f"{stem}_IntensityMap.png"))
        Image.fromarray(overlay).save(os.path.join(args.output_dir, f"{stem}_IntensityOverlay.png"))

        summary["roi_mask_path"] = roi_mask_path
        summary["image_path"] = image_path
        with open(os.path.join(args.output_dir, f"{stem}_IntensitySummary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        processed += 1

    print("Processed images:", processed)
    print("Output directory:", args.output_dir)


if __name__ == "__main__":
    main()
