# DNMT3A 染色強度分析中文方法報告

## 1. 研究目的

本研究的目標，是根據 IHC 染色影像與人工評分資料，建立一套可解釋、可重現、可調整的染色強度分析流程，用來將影像中的陽性染色表現區分為：

1. `weak (1+)`
2. `medium / moderate (2+)`
3. `strong (3+)`

並進一步輸出每張影像的：

1. `weak(1+) %`
2. `medium(2+) %`
3. `strong(3+) %`
4. `intensity score`
5. `percent score`
6. `final score`
7. `overall expression: low / high`

本系統不是直接以黑盒分類模型輸出最終結果，而是結合 DeepLIIF 專案架構、染色分離、影像特徵量化、人工標註反推門檻與規則式判讀所建立的分析流程。

## 2. 資料來源

本研究使用兩類資料：

1. IHC 染色影像  
   來自 `DNMT3A 24例 染色圖及評分` 資料夾中的 24 張影像。

2. 人工評分資料  
   由同資料夾內的 Excel 檔提供，每張影像包含：
   - `intensity`
   - `percent_score`
   - `final_score`
   - `expression`
   - `location`

人工評分規則如下：

- Intensity:
  - `0 = negative`
  - `1 = weak`
  - `2 = moderate / medium`
  - `3 = strong`
- Percentage score:
  - `0 = 0%`
  - `1 = <10%`
  - `2 = 11–50%`
  - `3 = >50%`
- Final score = `intensity score x percentage score`
- Low expression: `score <= 4`
- High expression: `score > 4`

## 3. DeepLIIF 訓練流程說明

本研究使用的 DeepLIIF，屬於 conditional GAN 架構下的多生成器、多判別器模型。原始 DeepLIIF 的訓練資料為 paired training data，會將多種對應模態依序橫向拼接成 stitched patches，典型組成為：

- `IHC`
- `Hematoxylin`
- `DAPI`
- `Lap2`
- `Marker`
- `Segmentation`

訓練時，模型以 IHC 作為主要輸入，學習將 IHC 轉換到其他模態，並同時學習 segmentation。根據目前專案設定：

- Translation generators 預設 backbone 為 `ResNet-9block`
- Segmentation generators 預設 backbone 為 `UNet-512`

因此，DeepLIIF 的原始訓練流程可概括為：

1. 準備 stitched paired patches 訓練資料
2. 以 `deepliif train` 啟動訓練
3. 學習 modality translation 與 segmentation
4. 產生訓練後的 `checkpoints` 或 `serialized model`
5. 在推論階段輸入 IHC 影像，輸出：
   - modality translation
   - segmentation
   - `num_pos`
   - `num_neg`
   - `percent_pos`

需要特別說明的是，本研究後續的 DNMT3A 染色強度分析，不是由 DeepLIIF 直接端到端輸出 `1+ / 2+ / 3+`，而是在 DeepLIIF 專案基礎上，額外建立了一套規則式染色強度分析流程。

## 4. DNMT3A 染色強度分析流程

### 4.1 影像前處理

每張影像會先進行基本前處理，以降低背景與亮度差異的影響，步驟包括：

1. `white balance`
   - 利用亮背景像素做白平衡修正。
2. `tissue mask`
   - 以亮度資訊排除背景，只保留組織區域。
3. `color deconvolution`
   - 將 RGB 影像轉換到 HED 色彩空間。
   - `DAB channel` 用來代表棕色染色強度。
   - `hematoxylin channel` 用來協助辨識 nuclei-like 區域。

### 4.2 區域偵測

前處理後，系統會分別找出：

1. `DAB-positive regions`
   - 以 DAB channel 強度搭配 threshold 與 morphology 操作擷取陽性染色區域。
2. `nuclei-like regions`
   - 以 hematoxylin channel 擷取類細胞核區域。

### 4.3 染色強度特徵計算

對每張影像，系統會計算：

1. 每個 `DAB-positive region` 的 `mean DAB OD`
2. 每個 `nuclei-like region` 的 `mean DAB OD`

之後再以該影像 tissue 區域中的 DAB `99th percentile` 進行 normalization，降低不同切片亮度與染色批次差異的影響。

### 4.4 門檻校正

本研究並未直接假設 weak、medium、strong 的門檻，而是利用人工標註資料反推最佳切分門檻。

系統會搜尋：

- `T1`：`weak(1+)` 與 `medium(2+)` 的切分門檻
- `T2`：`medium(2+)` 與 `strong(3+)` 的切分門檻

並測試不同的影像摘要統計值，例如：

- `mean`
- `median`
- `p75`
- `p90`

再以人工 `intensity score` 作為 ground truth，透過 `accuracy` 與 `macro-F1` 選出最佳組合。

### 4.5 Percent score 門檻校正

除了 intensity score，系統也會另外搜尋 `P0`，用來判定 nuclei-like region 是否屬於陽性。若某 nuclei-like region 的 normalized DAB OD 高於 `P0`，則視為陽性 nuclei。

之後根據陽性 nuclei 的比例，轉換成：

- `0`
- `1`
- `2`
- `3`

作為 `percent score`。

### 4.6 影像層級輸出

完成門檻校正後，每張影像可輸出：

1. `weak_1plus_pct`
2. `medium_2plus_pct`
3. `strong_3plus_pct`
4. `pred_intensity_score`
5. `pred_percent_score`
6. `pred_final_score`
7. `pred_expression`

其中：

- `pred_final_score = pred_intensity_score x pred_percent_score`
- `pred_expression = high if pred_final_score > 4 else low`

## 5. 一致性修正規則

為了讓結果更符合病理判讀邏輯，系統加入了一致性修正機制。

例如，若某張影像初步被判為 `3+`，但：

- `strong_3plus_pct < 12%`
- `weak_1plus_pct >= 70%`

則會將 intensity score 由 `3+` 下修為 `2+`，避免僅因局部 hotspot 導致整張圖被過度高估。

此外，若某些影像未能穩定偵測出 DAB-positive regions，系統則改用 `nuclei p90` 作為 fallback，避免因區域擷取不足而低估染色強度。

## 6. 本次最佳門檻

根據目前 24 張影像的人工標註與校正結果，本系統得到的最佳門檻如下：

- `T0 = 0.442`
- `T1 = 0.631`
- `T2 = 0.7133`
- `P0 = 0.0971`
- 影像摘要統計值採用 `p90`

## 7. 目前模型表現

目前整理出的分類表現如下：

- `Intensity accuracy = 0.833`
- `Intensity macro-F1 = 0.760`
- `Percent-score accuracy = 0.917`
- `Percent-score macro-F1 = 0.239`
- `Expression accuracy = 0.833`
- `Expression macro-F1 = 0.700`

## 8. 輸出檔案

本流程目前會輸出以下結果：

- `per_image_results.csv`
- `summary.json`
- `metrics_report.md`
- `metrics_aggregate.csv`
- `all_classification_metrics.csv`
- `metrics_mismatches.csv`

其中，`per_image_results.csv` 為每張影像的主要分析結果表；`summary.json` 記錄最佳門檻與整體表現；其餘檔案則用於指標整理與錯分案例檢查。

## 9. 系統限制

本系統目前仍有以下限制：

1. 標註樣本數僅 `24` 張，資料量仍偏少。
2. ground truth 為影像層級評分，而非逐細胞 `1+ / 2+ / 3+` 標註。
3. `percent score` 在本批資料中的類別分布不平均。
4. 目前尚未獨立建立 fold、tear、overlap 等 artifact 排除模組。

因此，本研究得到的門檻可視為初步校正結果，適合作為可解釋規則的第一版，但若要進一步提升穩定性，仍建議以更多標註影像重新校正。

## 10. 總結

整體而言，本研究是以 DeepLIIF 專案作為基礎，先說明其原始訓練與推論架構，再在此基礎上加入 DNMT3A 專用的規則式染色強度分析流程。系統先從 IHC 影像中分離 DAB 染色訊號，擷取陽性區域與 nuclei-like 區域，計算 normalized DAB OD 特徵，再根據人工標註反推出 `T1`、`T2` 與 `P0` 等門檻，最後輸出 weak、medium、strong 百分比，以及 intensity score、percent score、final score 和 low/high expression。

因此，這套方法的重點並不是單純訓練一個黑盒模型，而是建立一套兼具可解釋性、可重現性與可調整性的染色強度分析流程。
