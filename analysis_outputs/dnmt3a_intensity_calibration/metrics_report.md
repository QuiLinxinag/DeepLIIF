# DNMT3A Metrics Report

## Overall Metrics
- Case count: 24
- Intensity accuracy: 0.833
- Intensity macro-F1: 0.760
- Percent-score accuracy: 0.917
- Percent-score macro-F1: 0.239
- Expression accuracy: 0.833
- Expression macro-F1: 0.700

## Detailed Metric File
- See `all_classification_metrics.csv` for accuracy / precision / recall / F1 / support by task and class.

## Recommended Thresholds
- T0 summary filter: 0.442
- T1 weak->medium: 0.631
- T2 medium->strong: 0.7133
- P0 positive nucleus: 0.0971
- Intensity summary statistic: `p90`

## Confusion Matrices
- Intensity [rows=GT 1/2/3, cols=Pred 1/2/3]: [[2, 2, 0], [1, 6, 0], [0, 1, 12]]
- Percent-score [rows=GT 0/1/2/3, cols=Pred 0/1/2/3]: [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 2], [0, 0, 0, 22]]
- Expression [rows=GT low/high, cols=Pred low/high]: [[2, 3], [1, 18]]

## Match Counts
- Intensity match: 20/24
- Percent-score match: 22/24
- Expression match: 20/24
- Any mismatch: 6/24

## Mean Predicted Composition
- Mean weak(1+) %: 61.52
- Mean medium(2+) %: 12.11
- Mean strong(3+) %: 22.20
- Mean positive area %: 15.35
- Mean positive nuclei %: 95.69

## Remaining Mismatch Cases
- DNMT3A_1874_block1.jpg: intensity 1 vs 2, percent 3 vs 3, expression low vs high
- DNMT3A_1882_block1.jpg: intensity 2 vs 1, percent 3 vs 3, expression high vs low
- DNMT3A_1910_block2.jpg: intensity 2 vs 3, percent 3 vs 3, expression high vs high
- DNMT3A_2083_block1.jpg: intensity 2 vs 1, percent 3 vs 3, expression high vs low
- DNMT3A_2252_block2.jpg: intensity 3 vs 3, percent 3 vs 2, expression high vs high
- DNMT3A_3257_block1.jpg: intensity 2 vs 2, percent 3 vs 2, expression high vs low
