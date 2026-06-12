# DNMT3A 預測圖與 CSV 結果說明報告

## 1. 報告目的

本報告整理目前在 `D:\DeepLIIF` 專案中已完成的 DNMT3A 影像推論、癌細胞區域限制分析、強度分級視覺化與 CSV 結果整併，說明：

1. 使用到哪些模型與演算法
2. 這些模型在本專案中的訓練方式
3. 已經產出的預測圖與 CSV 檔案各代表什麼
4. 如何把這套流程應用到癌細胞陽性比例與染色強度分析


## 2. 本次已完成的主要輸出

### 2.1 DeepLIIF 預測圖

DeepLIIF 已成功對 `DNMT3A 24例 染色圖及評分` 內的 24 張影像完成推論，輸出在：

- `analysis_outputs/deepliif_prediction_images/`

每張影像都有以下檔案：

- `*_mod1-Hema.png`
  - 預測 Hematoxylin 模態
- `*_mod2-DAPI.png`
  - 預測 DAPI 模態
- `*_mod3-Lap2.png`
  - 預測 Lap2 模態
- `*_mod4-Marker.png`
  - 預測 Marker 模態
- `*_Seg.png`
  - 原始 segmentation 預測圖
- `*_SegOverlaid.png`
  - segmentation 疊在原圖上的 overlay
- `*_SegRefined.png`
  - refined segmentation，可作為後續癌細胞 ROI mask
- `*.json`
  - 單張影像的 DeepLIIF 推論摘要

### 2.2 全圖版強度分析 CSV

使用原始整張圖做 DNMT3A 染色強度分析，輸出在：

- `analysis_outputs/dnmt3a_fullslide_outputs/source_image_summary.csv`
- `analysis_outputs/dnmt3a_fullslide_outputs/patch_results.csv`

這一版代表「不限制癌細胞區域」，直接對全圖組織區域做分析。

### 2.3 癌細胞 mask 版強度分析 CSV

使用 DeepLIIF 輸出的 `*_SegRefined.png` 當 ROI mask，只在預測癌細胞區域內做 DNMT3A 分析，輸出在：

- `analysis_outputs/dnmt3a_cancer_mask_outputs/source_image_summary.csv`
- `analysis_outputs/dnmt3a_cancer_mask_outputs/patch_results.csv`

這一版更接近臨床想要的情境，也就是：

- 先圈出癌細胞區域
- 再計算陽性比例與染色強度

### 2.4 癌細胞 mask 版強度預測圖

已額外產生可視化強度預測圖，輸出在：

- `analysis_outputs/dnmt3a_cancer_mask_prediction_images/`

每張影像都有：

- `*_IntensityMap.png`
  - 強度分類圖
  - `1+` 用黃色
  - `2+` 用橘色
  - `3+` 用紅色
- `*_IntensityOverlay.png`
  - 強度分類疊在原圖上的 overlay
- `*_IntensitySummary.json`
  - 該張圖的摘要數值，包含陽性比例、1+/2+/3+ 百分比、預測分數等

### 2.5 已整理好的比較 CSV

為了方便比較全圖版與癌細胞 mask 版，已整理出：

- `analysis_outputs/dnmt3a_csv_organized/dnmt3a_fullslide_vs_cancer_mask_comparison.csv`
- `analysis_outputs/dnmt3a_csv_organized/dnmt3a_expression_changed_cases.csv`
- `analysis_outputs/dnmt3a_csv_organized/dnmt3a_intensity_changed_cases.csv`

其中：

- `dnmt3a_fullslide_vs_cancer_mask_comparison.csv`
  - 最完整
  - 同時包含全圖版、癌細胞 mask 版與差值欄位
- `dnmt3a_expression_changed_cases.csv`
  - 只列出套用癌細胞 mask 後 `low/high` 有變化的案例
- `dnmt3a_intensity_changed_cases.csv`
  - 只列出套用癌細胞 mask 後 `1+/2+/3+` 強度分級有變化的案例


## 3. 使用到的模型

### 3.1 DeepLIIF

本次預測圖是使用本 repo 的 **DeepLIIF 預訓練模型** 進行推論。

DeepLIIF 的核心任務是：

1. 從 IHC 影像推論多個輔助模態
2. 同時輸出 segmentation
3. 協助後續做 cell-level 或 ROI-level 的定量分析

本次實際解壓並使用的模型權重位於：

- `model-server/DeepLIIF_Latest_Model/`

包含：

- `G1.pt` ~ `G4.pt`
- `G51.pt` ~ `G55.pt`
- `latest_net_G*.pth`
- `latest_net_D*.pth`
- `train_opt.txt`

### 3.2 DeepLIIF 的生成器架構

依照本 repo 文件與模型設定：

- modality translation generators 以 **ResNet-9block** 為主
- segmentation generators 以 **UNet-512** 為主

也就是：

- 模態轉換：偏向影像到影像轉換
- segmentation：偏向 U-Net 類語意分割

這也是為什麼本專案很適合做：

- 先找出癌細胞相關區域
- 再做染色強度或陽性比例分析


## 3.1 哪些是 DeepLIIF 原生功能，哪些是後來加上的功能

為了避免混淆，這裡把目前整體流程拆成兩部分：

1. **DeepLIIF 原生功能**
2. **本次為 DNMT3A 分析另外加上的功能**

### A. DeepLIIF 原生功能

以下功能屬於 DeepLIIF 原始 repo 就具備的能力：

- `deepliif train`
  - 用來訓練 DeepLIIF 模型
- `deepliif test`
  - 用來對輸入 IHC 影像做推論
- 多模態影像預測
  - 例如輸出：
    - Hematoxylin
    - DAPI
    - Lap2
    - Marker
- segmentation 預測
  - 可輸出：
    - `Seg`
    - `SegOverlaid`
    - `SegRefined`
- TorchScript serialize
  - 可把模型轉成部署用格式
- WSI 推論
  - 可針對較大影像做分塊推論
- segmentation / cell 後處理
  - 例如 positive / negative cell 分類、cell counting 等

換句話說，本次在 `analysis_outputs/deepliif_prediction_images/` 內看到的這些輸出，屬於 DeepLIIF 原生能力：

- `*_mod1-Hema.png`
- `*_mod2-DAPI.png`
- `*_mod3-Lap2.png`
- `*_mod4-Marker.png`
- `*_Seg.png`
- `*_SegOverlaid.png`
- `*_SegRefined.png`
- `*.json`

### B. 本次後來加上的功能

以下功能不是 DeepLIIF 原始 repo 直接提供的，而是這次為 DNMT3A 強度分析與癌細胞 ROI 分析另外補上的流程。

#### B1. 癌細胞 ROI 限制分析

這不是 DeepLIIF 原生功能。

本次做法是：

- 使用 `SegRefined.png` 當作癌細胞區域 mask
- 只在這些 ROI 內做後續的強度分析

相關腳本：

- `Scripts/apply_dnmt3a_intensity_thresholds.py`
- `Scripts/calibrate_dnmt3a_intensity_thresholds.py`

#### B2. DNMT3A 規則式強度分級

這不是 DeepLIIF 原生功能。

目前 `1+ / 2+ / 3+` 強度分級與陽性比例，並不是 DeepLIIF 神經網路直接輸出，而是後來加上的規則式分析流程，包含：

- `weak_1plus_pct`
- `medium_2plus_pct`
- `strong_3plus_pct`
- `positive_nuclei_pct`
- `pred_intensity_score`
- `pred_percent_score`
- `pred_final_score`
- `pred_expression`

也就是：

- DeepLIIF 提供 segmentation / ROI
- DNMT3A 分析腳本負責輸出病理定量分數

#### B3. 癌細胞 mask 版強度預測圖

這不是 DeepLIIF 原生功能。

本次新增輸出：

- `*_IntensityMap.png`
- `*_IntensityOverlay.png`
- `*_IntensitySummary.json`

其功能是把癌細胞區域中的強度分級直接畫成可視化預測圖，讓使用者不只看到 CSV，還能直接看到：

- 哪些癌細胞區域是 `1+`
- 哪些是 `2+`
- 哪些是 `3+`

相關腳本：

- `Scripts/generate_dnmt3a_intensity_prediction_images.py`

#### B4. CSV 整理與比較報表

這不是 DeepLIIF 原生功能。

本次新增的整理內容包含：

- 全圖版 vs 癌細胞 mask 版比較
- expression changed cases
- intensity changed cases

相關腳本：

- `Scripts/organize_dnmt3a_csvs.py`

#### B5. 新增 CLI 輔助指令

這不是 DeepLIIF 原本就有的功能。

本次另外補上的 CLI 指令包括：

- `prepare-cancer-seg-data`
- `apply-cancer-mask`

位置：

- `cli.py`

### C. 最簡單的總結

可以把目前整個系統理解成：

- **DeepLIIF 原生部分**
  - 負責：`IHC -> 多模態預測 + segmentation`
- **後加分析部分**
  - 負責：`拿 segmentation 當癌細胞 ROI，再做 DNMT3A 陽性比例與 1+/2+/3+ 強度分析`

因此本次成果不是單純只有 DeepLIIF 原生推論，也不是完全新的模型，而是：

**DeepLIIF 原生 segmentation 能力 + 後加的 DNMT3A 規則式量化與視覺化流程**


## 4. 模型怎麼訓練

### 4.1 DeepLIIF 原始訓練邏輯

在本專案中，DeepLIIF 的訓練資料格式是把多張 patch 橫向拼接成一張訓練圖。

以原始 DeepLIIF 為例，訓練資料通常是：

- `(IHC, Hematoxylin, DAPI, Lap2, Marker, Seg)`

每一塊 patch 會學到：

1. IHC 到多模態的轉換
2. segmentation 的對應關係

訓練入口在：

- `cli.py`
- `deepliif/scripts/train.py`

常見訓練命令範例：

```bash
deepliif train --dataroot /path/to/dataset --name Model_Name
```

### 4.2 本專案加上的「癌細胞先分割」思路

這次我們在 repo 中另外補了兩階段應用流程：

1. 第一階段先取得癌細胞區域 mask
2. 第二階段只在癌細胞區域內計算 DNMT3A 染色強度與陽性比例

這樣做的原因是：

- 排除非腫瘤背景
- 減少間質與非癌細胞對強度統計的干擾
- 讓強度分析更聚焦在病理關心的癌區

目前這份報告中的癌細胞 mask，實務上是用：

- `analysis_outputs/deepliif_prediction_images/*_SegRefined.png`

作為 ROI mask。

### 4.3 DNMT3A 強度分析不是直接用神經網路輸出 1+/2+/3+

這點很重要。

目前 `1+ / 2+ / 3+` 與陽性比例不是由 DeepLIIF 直接端到端輸出，而是採用：

1. 影像分析方法分離 DAB 訊號
2. 在組織或 ROI 內找出 DAB-positive 區域
3. 在 nuclei-like 區域中估計 positive nuclei 百分比
4. 再根據校正好的門檻，把區域分成 `1+ / 2+ / 3+`

也就是說，這裡是：

- DeepLIIF 負責提供 segmentation / ROI 能力
- DNMT3A 規則式分析負責輸出強度分級與陽性比例


## 5. 強度分析的運作方式

### 5.1 使用的關鍵腳本

主要分析腳本：

- `Scripts/calibrate_dnmt3a_intensity_thresholds.py`
- `Scripts/apply_dnmt3a_intensity_thresholds.py`
- `Scripts/generate_dnmt3a_intensity_prediction_images.py`
- `Scripts/organize_dnmt3a_csvs.py`

### 5.2 主要步驟

1. 讀入原始 IHC 影像
2. 白平衡處理
3. 建立 tissue mask，排除背景
4. 若提供 ROI mask，則 tissue mask 再與癌細胞 mask 相交
5. 轉換到 HED 色彩空間
6. 擷取 DAB channel
7. 用 `max(DAB percentile, Otsu threshold)` 找出 DAB-positive 區域
8. 計算每個區域的平均 DAB 強度
9. 依門檻分成 weak / medium / strong
10. 估計 nuclei-like 區域中的 positive nuclei 百分比
11. 轉成：
    - `weak_1plus_pct`
    - `medium_2plus_pct`
    - `strong_3plus_pct`
    - `positive_nuclei_pct`
    - `pred_intensity_score`
    - `pred_percent_score`
    - `pred_final_score`

### 5.3 分數定義

- `pred_intensity_score`
  - 強度等級，通常是 `1 / 2 / 3`
- `pred_percent_score`
  - 陽性比例分數
  - 規則為：
    - `0%` -> `0`
    - `<10%` -> `1`
    - `10%~50%` -> `2`
    - `>50%` -> `3`
- `pred_final_score = pred_intensity_score x pred_percent_score`
- `pred_expression`
  - 若 `pred_final_score > 4` 則為 `high`
  - 否則為 `low`


## 6. 本次如何應用到癌細胞陽性比例與強度預測圖

本次的應用流程如下：

### Step 1. 使用 DeepLIIF 對原圖推論

輸出：

- 多模態預測圖
- segmentation
- refined segmentation

### Step 2. 將 `SegRefined` 視為癌細胞 ROI

使用：

- `analysis_outputs/deepliif_prediction_images/*_SegRefined.png`

作為 ROI mask。

### Step 3. 在 ROI 內做 DNMT3A 強度分析

輸出：

- `analysis_outputs/dnmt3a_cancer_mask_outputs/*.csv`

### Step 4. 產生強度預測圖

輸出：

- `analysis_outputs/dnmt3a_cancer_mask_prediction_images/*_IntensityMap.png`
- `analysis_outputs/dnmt3a_cancer_mask_prediction_images/*_IntensityOverlay.png`
- `analysis_outputs/dnmt3a_cancer_mask_prediction_images/*_IntensitySummary.json`

這些圖可以直接用來展示：

- 癌細胞區域在哪裡
- 該區域哪些是 `1+`
- 哪些是 `2+`
- 哪些是 `3+`
- 整張癌區的 positive nuclei 比例


## 7. 怎麼解讀目前產生的圖

### 7.1 `SegRefined.png`

用途：

- 當作癌細胞 ROI mask
- 用來限制後續強度分析只看癌區

### 7.2 `IntensityMap.png`

用途：

- 直接看強度分區結果
- 顏色代表：
  - 黃色：`1+`
  - 橘色：`2+`
  - 紅色：`3+`

### 7.3 `IntensityOverlay.png`

用途：

- 把強度分區疊回原圖
- 最適合對病理影像做人工判讀比對

### 7.4 `IntensitySummary.json`

用途：

- 單張圖的對應數值摘要
- 可與 CSV 搭配使用


## 8. CSV 與預測圖如何搭配

### 若要看整體病例統計

優先看：

- `analysis_outputs/dnmt3a_cancer_mask_outputs/source_image_summary.csv`

### 若要比較全圖與癌細胞 mask 差異

優先看：

- `analysis_outputs/dnmt3a_csv_organized/dnmt3a_fullslide_vs_cancer_mask_comparison.csv`

### 若要看某張圖的實際視覺化預測結果

優先看：

- `analysis_outputs/dnmt3a_cancer_mask_prediction_images/*_IntensityOverlay.png`

### 若要對照數值與影像

搭配看：

- `*_IntensityOverlay.png`
- `*_IntensitySummary.json`


## 9. 目前結果的限制

1. `SegRefined.png` 目前是用 DeepLIIF segmentation 當作癌細胞 ROI 的近似版本，不一定等同於病理專家手工圈出的癌細胞區。
2. `1+/2+/3+` 與陽性比例目前仍屬於規則式分析結果，不是直接由專門的 end-to-end cancer grading model 輸出。
3. `source_image_summary.csv` 的彙總強度欄位與單張直接判定邏輯曾有不一致問題，因此解讀時建議搭配 `patch_results.csv` 或 `IntensitySummary.json` 一起確認。
4. 如果未來要更精確地說是「癌細胞陽性比例」，建議再加入病理專家標註的 cancer-cell ground truth mask 或專門訓練的 cancer segmentation model。


## 10. 建議後續方向

1. 把 `SegRefined` 換成真正的癌細胞 segmentation ground truth 或專門癌細胞模型輸出。
2. 讓 `source_image_summary.csv` 的彙總邏輯與單張圖的 `IntensitySummary.json` 完全一致。
3. 在 `IntensityOverlay.png` 上直接加圖例、百分比與最終分數。
4. 針對病理報告需求，再產生一份精簡版 CSV：
   - 圖檔名
   - `positive_nuclei_pct`
   - `pred_intensity_score`
   - `pred_percent_score`
   - `pred_final_score`
   - `pred_expression`


## 11. 本次成果總結

目前已完成：

1. DeepLIIF 預測圖生成
2. 癌細胞 ROI 限制版強度分析
3. 癌細胞陽性比例與 `1+/2+/3+` 強度預測圖生成
4. 全圖版與癌細胞 mask 版 CSV 的對照整理

因此現在這個專案已經具備一條完整流程：

- 原始 IHC 圖
- DeepLIIF segmentation / 多模態預測
- 癌細胞 ROI 限制
- DAB 強度分析
- 產生 `1+ / 2+ / 3+` 強度預測圖
- 產生 CSV 報表與差異比較表
