# DNMT3A Intensity Threshold Calibration

## Recommended thresholds
- T0 summary filter: 0.4420
- T1 weak->medium: 0.6310
- T2 medium->strong: 0.7133
- Image-level summary statistic: `p90` of filtered DAB-positive region intensities
- Consistency rule: if a case is predicted as 3+ but strong-region percentage is <12% while weak-region percentage is >=70%, demote it to 2+
- Empty-region fallback: if no DAB-positive regions are extracted, use nuclei `p90` against T1/T2

## Metrics
- Intensity accuracy: 0.833
- Intensity macro-F1: 0.760
- Expression accuracy: 0.833
- Expression macro-F1: 0.700
- Percent-score accuracy: 0.917

## Confusion matrices
- Intensity labels [1, 2, 3]:
  [[2, 2, 0], [1, 6, 0], [0, 1, 12]]
- Percent-score labels [0, 1, 2, 3]:
  [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 2], [0, 0, 0, 22]]
- Expression labels [low, high]:
  [[2, 3], [1, 18]]

## Notes
- The rule is intentionally interpretable: white balance -> color deconvolution -> DAB-positive region extraction -> percentile-normalized OD thresholds.
- Weak/medium/strong percentages are percentages of segmented DAB-positive regions in each image.
- Final score uses predicted intensity x predicted percentage score, where percentage score is derived from the proportion of nuclei-like regions with DAB OD above P0 using the provided 0/<10/11-50/>50 rule.
- Because the ground truth is image-level and the cohort is only 24 images, this should be treated as a preliminary calibration rather than a final clinical threshold set.
