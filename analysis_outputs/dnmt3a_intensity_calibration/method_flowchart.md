# DNMT3A 染色強度分析流程圖

```mermaid
flowchart TD
    subgraph T[DeepLIIF 訓練流程]
        T0[訓練資料準備<br/>IHC + Hematoxylin + DAPI + Lap2 + Marker + Seg<br/>組成 stitched paired patches]
        T1[deepliif train]
        T2[DeepLIIF 模型訓練<br/>Translation generators: ResNet-9block<br/>Segmentation generators: UNet-512<br/>以 conditional GAN 架構學習 modality translation 與 segmentation]
        T3[輸出 checkpoints / serialized model]
        T4[DeepLIIF 推論<br/>輸入 IHC 影像<br/>輸出 modality translation、segmentation、num_pos、num_neg、percent_pos]
        T0 --> T1 --> T2 --> T3 --> T4
    end

    subgraph D[DNMT3A 規則式分析流程]
        A0[輸入資料<br/>1. 24 張 IHC 染色影像<br/>2. 人工評分 Excel]
        A1[影像前處理]
        A2[White balance]
        A3[Tissue mask<br/>排除背景區域]
        A4[Color deconvolution<br/>RGB -> HED]
        A5[DAB channel<br/>代表棕色染色強度]
        A6[Hematoxylin channel<br/>協助辨識 nuclei-like 區域]
        A7[DAB-positive region segmentation]
        A8[Nuclei-like region segmentation]
        A9[計算區域特徵<br/>每個 DAB-positive region 的 mean DAB OD]
        A10[計算 nuclei 特徵<br/>每個 nuclei-like region 的 mean DAB OD]
        A11[DAB 強度 normalization<br/>以 tissue 內 DAB 99th percentile 標準化]

        B0[門檻校正]
        B1[搜尋 T0 / T1 / T2]
        B2[以人工 intensity score 作為 ground truth]
        B3[以 accuracy 與 macro-F1 選最佳門檻]
        B4[搜尋 P0]
        B5[以 nuclei-like region 中 DAB 強度高於 P0 的比例估計 percent score]

        C0[影像層級判讀]
        C1[計算 weak(1+) / medium(2+) / strong(3+) 百分比]
        C2[計算 pred_intensity_score]
        C3[計算 pred_percent_score]
        C4[計算 pred_final_score = intensity x percent]
        C5[判定 pred_expression = low / high]

        D0[一致性修正]
        D1[若先判為 3+ 但 strong% 太低且 weak% 太高<br/>則降為 2+]
        D2[若 DAB-positive region 偵測不足<br/>則以 nuclei p90 作為 fallback]

        E0[輸出結果]
        E1[per_image_results.csv]
        E2[summary.json]
        E3[metrics_report.md]
        E4[all_classification_metrics.csv]
        E5[metrics_mismatches.csv]

        A0 --> A1 --> A2 --> A3 --> A4
        A4 --> A5 --> A7 --> A9 --> A11
        A4 --> A6 --> A8 --> A10 --> A11
        A11 --> B0
        B0 --> B1 --> B2 --> B3 --> C0
        A11 --> B4 --> B5 --> C0
        C0 --> C1
        C0 --> C2
        C0 --> C3
        C2 --> C4
        C3 --> C4
        C4 --> C5
        C0 --> D0
        D0 --> D1
        D0 --> D2
        D1 --> E0
        D2 --> E0
        C1 --> E0
        C5 --> E0
        E0 --> E1
        E0 --> E2
        E0 --> E3
        E0 --> E4
        E0 --> E5
    end

    T4 -. 提供 DeepLIIF 原生 segmentation / counting 背景 .-> D
```

## 補充說明

- `T0`：初步過濾低強度區域的 threshold。
- `T1`：`weak(1+)` 與 `medium(2+)` 的切分門檻。
- `T2`：`medium(2+)` 與 `strong(3+)` 的切分門檻。
- `P0`：判定 nuclei-like region 是否屬於陽性的 DAB 強度門檻。
- `DAB OD`：DAB optical density，用來代表棕色染色強度。
- DeepLIIF 訓練流程說明的是原始模型如何從 paired training data 學到 modality translation 與 segmentation。
- DNMT3A 規則式分析流程說明的是本研究如何利用影像分析與人工標註校正，進一步產生 `per_image_results.csv`。
