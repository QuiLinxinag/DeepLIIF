# QuiLinxinag DeepLIIF-DNMT3A

<!-- PROJECT LOGO -->
<br />
<p align="center">
  <img src="./images/DeepLIIF_logo.png" width="50%">
</p>

以 `DeepLIIF` 為基礎延伸的病理影像分析專案，主軸是先從 IHC 影像取得癌細胞相關 segmentation，再針對 `DNMT3A` 染色做強度分級、陽性比例統計、預測圖輸出與 CSV 報表整理。

## 專案重點

- 使用 `DeepLIIF` 產出的 `SegRefined` 作為癌細胞 ROI
- 將 `DNMT3A` 定量限制在癌細胞區域內
- 產生強度地圖、疊圖與摘要 JSON
- 匯出全圖版與癌細胞 mask 版 CSV
- 整理比較結果，方便檢視表現差異

## 主要流程

1. 使用 `DeepLIIF` 對 IHC 影像做推論，輸出 segmentation 與輔助模態影像。
2. 使用 `Scripts/apply_dnmt3a_intensity_thresholds.py` 做 `DNMT3A` 強度與陽性比例分析。
3. 使用 `Scripts/generate_dnmt3a_intensity_prediction_images.py` 產生可視化預測圖。
4. 使用 `Scripts/organize_dnmt3a_csvs.py` 整理全圖版與癌細胞 mask 版結果。

## 常見輸出

### DeepLIIF 推論輸出

- `analysis_outputs/deepliif_prediction_images/`
- `*_Seg.png`
- `*_SegOverlaid.png`
- `*_SegRefined.png`
- `*_mod1-Hema.png`
- `*_mod2-DAPI.png`
- `*_mod3-Lap2.png`
- `*_mod4-Marker.png`

### DNMT3A 定量輸出

- `analysis_outputs/dnmt3a_fullslide_outputs/source_image_summary.csv`
- `analysis_outputs/dnmt3a_fullslide_outputs/patch_results.csv`
- `analysis_outputs/dnmt3a_cancer_mask_outputs/source_image_summary.csv`
- `analysis_outputs/dnmt3a_cancer_mask_outputs/patch_results.csv`

### 預測圖輸出

- `analysis_outputs/dnmt3a_cancer_mask_prediction_images/`
- `*_IntensityMap.png`
- `*_IntensityOverlay.png`
- `*_IntensitySummary.json`

## 環境安裝

Windows 建議使用 `Conda + pip`：

```powershell
conda create -n deepliif-win python=3.8 -y
conda activate deepliif-win
conda install -c conda-forge openjdk maven -y
python -m pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install opencv-python==4.8.1.78 scikit-image==0.18.3 dominate==2.6.0 numba==0.57.1 Click==8.0.3 requests==2.32.2 dask==2021.11.2 visdom python-bioformats imagecodecs==2023.3.16 zarr==2.16.1 pandas openpyxl scikit-learn
pip install -e . --no-deps
```

安裝後可驗證：

```powershell
python cli.py --help
deepliif --help
```

## 常用指令

### DeepLIIF segmentation

```bash
deepliif test --input-dir /path/to/input/images --output-dir /path/to/output/images --model-dir /path/to/model --tile-size 512
```

### DNMT3A 強度分析

```bash
python Scripts/apply_dnmt3a_intensity_thresholds.py --input-dir /path/to/images --output-dir /path/to/output
```

### 癌細胞 mask 限制分析

```bash
python Scripts/apply_dnmt3a_intensity_thresholds.py --input-dir /path/to/images --mask-dir /path/to/segrefined_masks --output-dir /path/to/output
```

### 產生強度預測圖

```bash
python Scripts/generate_dnmt3a_intensity_prediction_images.py --input-dir /path/to/images --mask-dir /path/to/segrefined_masks --output-dir /path/to/output
```

### 整理比較 CSV

```bash
python Scripts/organize_dnmt3a_csvs.py --fullslide-csv /path/to/fullslide/source_image_summary.csv --cancer-mask-csv /path/to/cancer_mask/source_image_summary.csv --output-dir /path/to/output
```

## 相關文件

- `docs/environment_setup_zh.md`
- `docs/dnmt3a_manual_run_zh.md`
- `analysis_outputs/dnmt3a_prediction_report_zh.md`

## 上游來源

本專案建立在原始 `DeepLIIF` 之上：

- Upstream project: `DeepLIIF`
- Upstream repository: `https://github.com/nadeemlab/DeepLIIF`
- Official website: `https://deepliif.org/`

本 repo 的主要新增價值在於：

- 癌細胞 ROI 限制分析
- `DNMT3A` 規則式量化流程
- 預測圖與摘要輸出
- CSV 比較整理流程

## 授權與使用

使用本專案時，請一併遵守上游 `DeepLIIF` 的授權、模型來源與資料使用限制。
