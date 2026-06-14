# QuiLinxinag DeepLIIF-DNMT3A Docs

這份文件入口頁是針對目前這個客製化版本整理的，不再以原始 `DeepLIIF` 官方說明原文為主，而是聚焦在你現在實際使用的 `DNMT3A` 分析流程、癌細胞 ROI 應用方式與輸出結果。

## 文件定位

本版本保留 `DeepLIIF` 作為底層推論核心，但文件主軸改成：

- 癌細胞 segmentation 結果如何被拿來當 ROI
- `DNMT3A` 陽性比例與強度如何計算
- 預測圖、CSV、JSON 如何閱讀
- 哪些功能是原生 `DeepLIIF`，哪些是本專案後加

## 你可以從這裡理解什麼

如果你是要交付報告、展示成果或重跑分析，重點可以先看以下幾個面向：

- `DeepLIIF` 如何輸出 `SegRefined` 作為癌細胞 mask
- 後處理腳本如何把癌細胞區域轉成 `1+ / 2+ / 3+` 強度分級
- 全圖分析與癌細胞 mask 分析的差異
- 最後如何整理成報表與可視化預測圖

## 主要文件

建議優先閱讀：

- `analysis_outputs/dnmt3a_prediction_report_zh.md`
- `docs/dnmt3a_manual_run_zh.md`
- `docs/environment_setup_zh.md`

這份報告已經整理：

- 系統架構
- 模型來源
- 訓練方式
- 預測流程
- CSV 欄位意義
- 預測圖用途
- 原生功能與客製功能區分

而 `docs/dnmt3a_manual_run_zh.md` 則更偏向操作文件，整理：

- 手動執行指令範例
- `1+ / 2+ / 3+` 與陽性比例的解讀方式
- 神經網路模型與後處理分工
- `ImageJ / Fiji` 的使用教學

`docs/environment_setup_zh.md` 則提供可直接貼上執行的環境建置流程，包含：

- Conda 環境建立
- PyTorch 安裝
- 專案套件安裝
- DeepLIIF segmentation 執行
- DNMT3A 全圖 / 癌細胞遮罩版分析指令

## 主要程式位置

### DeepLIIF 核心與 CLI

- `cli.py`
- `deepliif/scripts/train.py`

### DNMT3A 客製分析腳本

- `Scripts/calibrate_dnmt3a_intensity_thresholds.py`
- `Scripts/apply_dnmt3a_intensity_thresholds.py`
- `Scripts/generate_dnmt3a_intensity_prediction_images.py`
- `Scripts/organize_dnmt3a_csvs.py`

## 分析輸出位置

### DeepLIIF 推論輸出

- `analysis_outputs/deepliif_prediction_images/`

### DNMT3A 全圖定量

- `analysis_outputs/dnmt3a_fullslide_outputs/`

### DNMT3A 癌細胞 mask 定量

- `analysis_outputs/dnmt3a_cancer_mask_outputs/`

### 癌細胞 mask 強度預測圖

- `analysis_outputs/dnmt3a_cancer_mask_prediction_images/`

### CSV 整理比較

- `analysis_outputs/dnmt3a_csv_organized/`

## 原生與客製功能的界線

### 原生 DeepLIIF

原始 `DeepLIIF` 主要負責：

- IHC 到多模態影像轉換
- segmentation 預測
- 訓練與測試流程
- WSI 與 patch 型推論支援

### 本專案後加

這個版本額外補上的內容包括：

- 以 `SegRefined` 為癌細胞 ROI 的限制分析
- `DNMT3A` 規則式強度分級
- `*_IntensityMap.png` 與 `*_IntensityOverlay.png`
- 全圖版與癌細胞 mask 版 CSV 比較報表

## 來源註記

這個專案屬於基於 `DeepLIIF` 的客製化應用版本，請在文件、簡報或對外說明中保留下列參考來源：

- Upstream repository: `https://github.com/nadeemlab/DeepLIIF`
- Official site: `https://deepliif.org/`

若需完整原始技術說明、官方部署方式或原論文資訊，請回到原始 `DeepLIIF` 專案文件查閱。
