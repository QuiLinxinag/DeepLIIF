# DNMT3A 染色強度分析系統中文報告

## 1. 目的

本系統的目標是根據 IHC 影像與人工評分資料，建立一套可解釋、可重現、可調整的染色強度分析流程，將影像中的染色區域分為：

1. `weak (1+)`
2. `medium / moderate (2+)`
3. `strong (3+)`

並進一步輸出：

1. `weak(1+) %`
2. `medium(2+) %`
3. `strong(3+) %`
4. `intensity score`
5. `percent score`
6. `final score`
7. `overall expression: low / high`

本方法不是直接使用黑盒分類器，而是先從影像中抽取與染色強度相關的可解釋特徵，再根據人工評分資料反推最合適的門檻。

## 2. 輸入資料

本系統使用兩類資料：

1. IHC 染色影像  
   位置：`DNMT3A 24例 染色圖及評分`

2. 人工評分表  
   Excel 內容包含：
   - `intensity`
   - `percent_score`
   - `final_score`
   - `expression`
   - `location`

人工規則為：

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
- Final score = `intensity score × percentage score`
- Low expression: `score <= 4`
- High expression: `score > 4`

## 3. 方法步驟

### 3.1 影像前處理

每張圖先進行以下處理：

1. `white balance`
   - 使用亮背景像素進行白平衡
2. `tissue mask`
   - 利用亮度將背景排除，只保留組織區域
3. `color deconvolution`
   - 將 RGB 轉為 HED
   - `DAB channel` 作為棕色染色強度來源
   - `hematoxylin channel` 作為 nuclei-like 結構來源

### 3.2 區域擷取

系統分別擷取兩種區域：

1. `DAB-positive regions`
   - 代表可疑陽性染色區
   - 使用 `max(DAB percentile, Otsu threshold)` 決定門檻
   - 再用 morphology 去除小雜訊

2. `nuclei-like regions`
   - 由 hematoxylin channel 擷取
   - 用於估算陽性 nuclei 比例

### 3.3 強度特徵計算

對每個偵測到的區域計算 `mean DAB OD`，再用 tissue 內 DAB 的 `99th percentile` 做 normalization。  
因此後續門檻是在 normalized DAB OD 空間中進行。

### 3.4 強度門檻校正

系統不直接假設 weak / medium / strong 的門檻，而是從人工評分資料反推：

- `T1`：weak(1+) 與 medium(2+) 的切分門檻
- `T2`：medium(2+) 與 strong(3+) 的切分門檻

同時也會測試不同影像層級 summary statistic，例如：

- `mean`
- `median`
- `p75`
- `p90`

再根據人工 `intensity score` 當 ground truth，以 `accuracy` 與 `macro-F1` 搜尋最佳組合。

### 3.5 percent score 門檻校正

另外再搜尋一個 `P0`，用來判定 nuclei-like region 是否屬於陽性：

- 若 nuclei-like region 的 normalized DAB OD >= `P0`
  - 視為陽性 nuclei

接著計算整張圖中陽性 nuclei 的比例，再轉成：

- `0`
- `1`
- `2`
- `3`

### 3.6 最終輸出規則

每張圖最後會輸出：

1. `weak_1plus_pct`
2. `medium_2plus_pct`
3. `strong_3plus_pct`
4. `pred_intensity_score`
5. `pred_percent_score`
6. `pred_final_score`
7. `pred_expression`

其中：

- `pred_final_score = pred_intensity_score × pred_percent_score`
- `pred_expression = high if pred_final_score > 4 else low`

## 4. 一致性修正規則

為了避免某些圖被少量強 hotspot 拉成不合理的 `3+`，系統加入了可解釋的一致性規則：

1. 若先預測為 `3+`
2. 但 `strong_3plus_pct < 12%`
3. 且 `weak_1plus_pct >= 70%`

則將 intensity 從 `3+` 降為 `2+`

此外，若某張圖完全抓不到 DAB-positive region，系統會改用 `nuclei p90` 做 fallback，以避免因區域偵測失敗而低估強度。

## 5. 本次校正得到的最佳門檻

根據目前 24 張影像資料，本次最佳門檻如下：

- `T0 = 0.442`
- `T1 = 0.631`
- `T2 = 0.7133`
- `P0 = 0.0971`
- 影像層級 summary statistic：`p90`

## 6. 目前表現

本次資料上的結果如下：

- `Intensity accuracy = 0.833`
- `Intensity macro-F1 = 0.760`
- `Percent-score accuracy = 0.917`
- `Percent-score macro-F1 = 0.239`
- `Expression accuracy = 0.833`
- `Expression macro-F1 = 0.700`

## 7. 輸出檔案

目前分析結果整理於：

- `per_image_results.csv`
- `summary.json`
- `metrics_report.md`
- `metrics_aggregate.csv`
- `all_classification_metrics.csv`
- `metrics_mismatches.csv`

## 8. 限制與說明

本系統雖然可解釋且可重現，但仍有以下限制：

1. 目前只有 `24` 張影像
2. ground truth 為「影像層級標註」，不是逐細胞 `1+/2+/3+` 標註
3. `% score` 類別分布不平衡，大部分為 `3`
4. 尚未針對折片、掉片、重疊等 artifact 建立專門排除模組

因此，本次門檻應視為：

- 一套合理的初步校正規則
- 可作為後續模型與臨床判讀整合的基礎
- 但仍建議加入更多標註影像後重新校正

## 9. 結論

本系統已可完成：

1. 由 IHC 影像抽取 DAB 染色強度特徵
2. 依人工資料反推 weak / medium / strong 門檻
3. 輸出每張圖的 weak / medium / strong 百分比
4. 計算 intensity score、percent score、final score 與 low/high expression
5. 產生 accuracy、precision、recall、F1 等評估結果

整體來看，這是一套偏向規則式、可解釋的染色強度分析流程，適合做為初步研究與方法報告，也方便後續再依病理需求調整。
