# DNMT3A 方法流程圖

```mermaid
flowchart TD
    A[輸入資料<br/>1. IHC影像<br/>2. 人工評分Excel] --> B[影像前處理]
    B --> B1[White balance]
    B1 --> B2[Tissue mask<br/>排除亮背景]
    B2 --> B3[Color deconvolution<br/>RGB -> HED]
    B3 --> C[特徵擷取]
    C --> C1[DAB channel<br/>代表棕色染色強度]
    C --> C2[Hematoxylin channel<br/>代表 nuclei-like 結構]
    C1 --> D[DAB-positive region segmentation]
    C2 --> E[Nuclei-like region segmentation]
    D --> D1[計算每個 region 的 mean DAB OD]
    E --> E1[計算每個 nuclei-like region 的 mean DAB OD]
    D1 --> F[以 tissue DAB 99th percentile 做 normalization]
    E1 --> F
    F --> G[門檻校正]
    G --> G1[搜尋 T0/T1/T2]
    G1 --> G2[用人工 intensity score 當 ground truth]
    G2 --> G3[最大化 accuracy 與 macro-F1]
    F --> H[陽性比例門檻校正]
    H --> H1[搜尋 P0]
    H1 --> H2[以 nuclei-like region 中高於 P0 的比例估 percent score]
    H2 --> H3[對應 0 / 1 / 2 / 3]
    G3 --> I[影像層級預測]
    H3 --> I
    I --> I1[weak(1+) / medium(2+) / strong(3+) 百分比]
    I --> I2[intensity score]
    I --> I3[percent score]
    I --> I4[final score = intensity x percent]
    I --> I5[expression = low/high]
    I2 --> J[一致性修正]
    J --> J1[若預測 3+ 但 strong% 太低且 weak% 太高 -> 降為 2+]
    J --> J2[若抓不到 DAB-positive region -> 用 nuclei p90 fallback]
    J1 --> K[輸出檔案]
    J2 --> K
    K --> K1[per_image_results.csv]
    K --> K2[summary.json]
    K --> K3[metrics_report.md]
    K --> K4[all_classification_metrics.csv]
    K --> K5[metrics_mismatches.csv]
```

## 圖例說明

- `T0`：影像層級 summary filter threshold
- `T1`：weak(1+) 與 medium(2+) 的切分門檻
- `T2`：medium(2+) 與 strong(3+) 的切分門檻
- `P0`：判定 nuclei-like region 是否為陽性的門檻
- `DAB OD`：DAB optical density，代表棕色染色強度
