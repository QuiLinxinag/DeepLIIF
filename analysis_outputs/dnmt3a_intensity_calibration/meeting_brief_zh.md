# DNMT3A 系統總整理

## 1. 這套系統在做什麼

這套系統的目的是把 IHC 染色影像轉成可量化的結果，輸出：

1. `weak(1+) %`
2. `medium(2+) %`
3. `strong(3+) %`
4. `pred_intensity_score`
5. `pred_percent_score`
6. `pred_final_score`
7. `pred_expression (low / high)`

目前結果表主要在：
- [per_image_results.csv](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/per_image_results.csv:1)

---

## 2. `1+ / 2+ / 3+ %` 是什麼意思

`weak(1+) %`、`medium(2+) %`、`strong(3+) %` 的意思是：

> 在同一張影像中，被系統判定為 DAB-positive 的區域裡，各種強度所占的比例。

也就是先把 DAB-positive regions 找出來，再根據門檻：

- `intensity < T1` → weak(1+)
- `T1 <= intensity < T2` → medium(2+)
- `intensity >= T2` → strong(3+)

所以：
- `weak(1+) %` = 弱染色區域占比
- `medium(2+) %` = 中等染色區域占比
- `strong(3+) %` = 強染色區域占比

---

## 3. 跟 `pred_intensity_score = 1 / 2 / 3` 的關係

兩者不是完全一樣的東西。

- `weak/medium/strong %`：是在描述**一張圖裡面各強度區域的組成比例**
- `pred_intensity_score`：是在描述**整張圖最後被歸類成哪一級**

目前系統是用整張圖的強度分布摘要值來判定 `pred_intensity_score`，不是直接看哪個百分比最大就決定。

簡單講：

> `1+ / 2+ / 3+ %` 是組成；`pred_intensity_score` 是整體結論。

---

## 4. DeepLIIF 是什麼神經網路

DeepLIIF 不是單一神經網路，而是一套多 generator、多 discriminator 的深度學習架構。

原始 DeepLIIF 會：

1. 以 IHC 當輸入
2. 學習轉換到多個模態
   - Hematoxylin
   - DAPI
   - Lap2
   - Marker
3. 再根據 IHC 與這些模態共同做 segmentation

### backbone

原始預設 backbone 是：

- Translation generators：`ResNet-9block`
- Segmentation generators：`UNet-512`

對應檔案：
- [Model Types.md](/abs/path/d:/DeepLIIF/Model%20Types.md:29)
- [DeepLIIF_model.py](/abs/path/d:/DeepLIIF/deepliif/models/DeepLIIF_model.py:8)

---

## 5. 我們現在這次用的是什麼

這次要分兩層講：

### 5.1 DeepLIIF 原生模型

DeepLIIF 原生模型本身可做：

- modality translation
- segmentation
- positive / negative counting
- `num_total / num_pos / num_neg / percent_pos`

### 5.2 這次 DNMT3A 的 `1+ / 2+ / 3+`

這次 `per_image_results.csv` 不是由 DeepLIIF 直接端到端輸出 `1+ / 2+ / 3+`，
而是我們另外建立的**規則式分析流程**跑出來的。

主程式是：
- [calibrate_dnmt3a_intensity_thresholds.py](/abs/path/d:/DeepLIIF/Scripts/calibrate_dnmt3a_intensity_thresholds.py:1)

也就是說：

> DeepLIIF 提供的是整體專案與病理影像分析基礎；這次 DNMT3A 的 1+/2+/3+ 與 low/high，是在專案內另外加上的規則式分析模組。

---

## 6. 系統方法怎麼做

### 步驟 1：讀入資料

- IHC 影像
- 人工評分 Excel

### 步驟 2：影像前處理

- white balance
- tissue mask 排除背景

### 步驟 3：stain separation

用 `rgb2hed` 把影像分成：

- `DAB channel`：棕色染色強度
- `hematoxylin channel`：nuclei-like 結構

### 步驟 4：擷取區域

- 從 DAB channel 擷取 `DAB-positive regions`
- 從 hematoxylin 擷取 `nuclei-like regions`

### 步驟 5：計算特徵

計算每個區域的 `mean DAB OD`，再做 normalization。

### 步驟 6：反推門檻

不是先假設 `1+ / 2+ / 3+` 的界線，而是利用人工標註資料去搜尋最佳門檻：

- `T1`：weak 到 medium
- `T2`：medium 到 strong
- `P0`：positive nucleus 的判定門檻

### 步驟 7：輸出結果

每張圖輸出：

- `weak_1plus_pct`
- `medium_2plus_pct`
- `strong_3plus_pct`
- `pred_intensity_score`
- `pred_percent_score`
- `pred_final_score`
- `pred_expression`

---

## 7. 目前最佳門檻

目前這批 24 張資料校正出的門檻為：

- `T0 = 0.442`
- `T1 = 0.631`
- `T2 = 0.7133`
- `P0 = 0.0971`
- summary statistic：`p90`

來源：
- [summary.json](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/summary.json:1)

---

## 8. 一致性修正規則

系統為了避免少量 hotspot 造成整張圖被判過高，加入兩個規則：

### 8.1 strong 降級規則

如果：

- 原本預測為 `3+`
- 但 `strong% < 12%`
- 且 `weak% >= 70%`

則降成 `2+`

### 8.2 empty-region fallback

如果完全抓不到 DAB-positive regions：

- 改用 nuclei `p90` 去對照 `T1 / T2`

---

## 9. 目前表現

目前整理出的整體指標為：

- Intensity accuracy: `0.833`
- Intensity macro-F1: `0.760`
- Percent-score accuracy: `0.917`
- Expression accuracy: `0.833`
- Expression macro-F1: `0.700`

詳細檔案：
- [metrics_report.md](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/metrics_report.md:1)
- [all_classification_metrics.csv](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/all_classification_metrics.csv:1)

---

## 10. 目前還有不一致的個案

目前 remaining mismatch 主要包括：

- `DNMT3A_1874_block1.jpg`
- `DNMT3A_1882_block1.jpg`
- `DNMT3A_1910_block2.jpg`
- `DNMT3A_2083_block1.jpg`
- `DNMT3A_2252_block2.jpg`
- `DNMT3A_3257_block1.jpg`

清單位置：
- [metrics_mismatches.csv](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/metrics_mismatches.csv:1)

---

## 11. 折片 / 掉片目前怎麼處理

目前程式：

- **沒有專門做折片偵測**
- **沒有做分層分析**

也就是說，若折片區域仍被視為 tissue，且具有 DAB/hematoxylin 訊號，就可能被算進去。

所以如果老師問：

> 現階段較合理的作法是先辨識並排除折片區，而不是分層處理；目前這個版本尚未加入折片排除模組。

---

## 12. 可以直接怎麼講

### 一句話版

> DeepLIIF 本身是以 ResNet-9block 與 UNet-512 為核心的病理影像深度學習架構；而這次 DNMT3A 的 1+/2+/3+ 分析，則是在 DeepLIIF 專案中另外建立的規則式染色強度分析流程，透過 stain separation、DAB 強度特徵與人工標註反推門檻，輸出 weak、medium、strong 百分比與 low/high expression。

### 開會口語版

> 我們這次不是直接訓練一個神經網路去輸出 1+、2+、3+，而是先用影像分析方法把 DAB 棕色訊號分離出來，再根據人工標註去反推門檻，把每張圖裡面的陽性區域分成 weak、medium、strong。最後再根據這些比例與整體強度，算出 intensity score、percent score、final score 和 low/high。至於 DeepLIIF 本身，原始模型是多生成器、多判別器架構，translation generator 用 ResNet-9block，segmentation generator 用 UNet-512。

---

## 13. 重要檔案快速索引

- 方法流程圖：[method_flowchart.md](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/method_flowchart.md:1)
- 中文方法報告：[chinese_method_report.md](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/chinese_method_report.md:1)
- 本檔總整理：[meeting_brief_zh.md](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/meeting_brief_zh.md:1)
- 每張圖結果：[per_image_results.csv](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/per_image_results.csv:1)
- 指標摘要：[metrics_report.md](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/metrics_report.md:1)
- 全部分類指標：[all_classification_metrics.csv](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/all_classification_metrics.csv:1)
- mismatch 清單：[metrics_mismatches.csv](/abs/path/d:/DeepLIIF/analysis_outputs/dnmt3a_intensity_calibration/metrics_mismatches.csv:1)
