# 環境建置教學（Windows / Conda）

這份文件提供目前專案可直接使用的環境建置方式，目標是讓使用者在 Windows 環境中，透過 `Conda + pip` 快速完成：

- `DeepLIIF` CLI 安裝
- `DNMT3A` 分析腳本可執行
- 預測圖與 CSV 報表可正常輸出

---

## 1. 建立 Conda 環境

```powershell
conda create -n deepliif-win python=3.8 -y
conda activate deepliif-win
conda install -c conda-forge openjdk maven -y
python -m pip install --upgrade pip
```

---

## 2. 安裝 PyTorch

### 2.1 若有 NVIDIA GPU

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 2.2 若只使用 CPU

```powershell
pip install torch torchvision torchaudio
```

---

## 3. 安裝專案相依套件

在專案根目錄執行：

```powershell
cd d:\DeepLIIF
pip install opencv-python==4.8.1.78 scikit-image==0.18.3 dominate==2.6.0 numba==0.57.1 Click==8.0.3 requests==2.32.2 dask==2021.11.2 visdom python-bioformats imagecodecs==2023.3.16 zarr==2.16.1 pandas openpyxl scikit-learn
pip install -e . --no-deps
```

說明：

- 這個 repo 目前沒有 `requirements.txt`
- `pip install -e . --no-deps` 可避免重新覆蓋前面已安裝好的 `torch`
- 若直接執行 `pip install -e .`，可能會因 `setup.py` 中的相依版本重新拉套件

---

## 4. 測試安裝是否成功

```powershell
python cli.py --help
deepliif --help
```

若兩個指令都能正常顯示說明頁，表示基本安裝成功。

---

## 5. 建立輸出資料夾

```powershell
New-Item -ItemType Directory -Force analysis_outputs
New-Item -ItemType Directory -Force analysis_outputs\deepliif_prediction_images
New-Item -ItemType Directory -Force analysis_outputs\dnmt3a_fullslide_outputs
New-Item -ItemType Directory -Force analysis_outputs\dnmt3a_cancer_mask_outputs
New-Item -ItemType Directory -Force analysis_outputs\dnmt3a_cancer_mask_prediction_images
New-Item -ItemType Directory -Force analysis_outputs\dnmt3a_csv_organized
```

---

## 6. 放置 DeepLIIF 預訓練模型

請將官方模型解壓到以下位置：

```powershell
model-server\DeepLIIF_Latest_Model
```

可用下列指令檢查：

```powershell
Get-ChildItem model-server\DeepLIIF_Latest_Model
```

---

## 7. 執行 DeepLIIF segmentation

```powershell
deepliif test --input-dir "DNMT3A 24例 染色圖及評分" --output-dir analysis_outputs\deepliif_prediction_images --model-dir model-server\DeepLIIF_Latest_Model --tile-size 512
```

這一步會產生：

- `*_Seg.png`
- `*_SegOverlaid.png`
- `*_SegRefined.png`
- `*_mod1-Hema.png`
- `*_mod2-DAPI.png`
- `*_mod3-Lap2.png`
- `*_mod4-Marker.png`

---

## 8. 執行 DNMT3A 全圖分析

```powershell
python Scripts\apply_dnmt3a_intensity_thresholds.py --input-dir "DNMT3A 24例 染色圖及評分" --output-dir analysis_outputs\dnmt3a_fullslide_outputs
```

輸出：

- `analysis_outputs\dnmt3a_fullslide_outputs\patch_results.csv`
- `analysis_outputs\dnmt3a_fullslide_outputs\source_image_summary.csv`

---

## 9. 執行癌細胞遮罩版 DNMT3A 分析

```powershell
python Scripts\apply_dnmt3a_intensity_thresholds.py --input-dir "DNMT3A 24例 染色圖及評分" --mask-dir analysis_outputs\deepliif_prediction_images --image-suffix .jpg --mask-suffix _SegRefined.png --output-dir analysis_outputs\dnmt3a_cancer_mask_outputs
```

輸出：

- `analysis_outputs\dnmt3a_cancer_mask_outputs\patch_results.csv`
- `analysis_outputs\dnmt3a_cancer_mask_outputs\source_image_summary.csv`

---

## 10. 產生癌細胞遮罩版強度預測圖

```powershell
python Scripts\generate_dnmt3a_intensity_prediction_images.py --input-dir "DNMT3A 24例 染色圖及評分" --mask-dir analysis_outputs\deepliif_prediction_images --image-suffix .jpg --mask-suffix _SegRefined.png --output-dir analysis_outputs\dnmt3a_cancer_mask_prediction_images
```

輸出：

- `*_IntensityMap.png`
- `*_IntensityOverlay.png`
- `*_IntensitySummary.json`

---

## 11. 整理比較 CSV

```powershell
python Scripts\organize_dnmt3a_csvs.py --fullslide-csv analysis_outputs\dnmt3a_fullslide_outputs\source_image_summary.csv --cancer-mask-csv analysis_outputs\dnmt3a_cancer_mask_outputs\source_image_summary.csv --output-dir analysis_outputs\dnmt3a_csv_organized
```

輸出：

- `dnmt3a_fullslide_vs_cancer_mask_comparison.csv`
- `dnmt3a_expression_changed_cases.csv`
- `dnmt3a_intensity_changed_cases.csv`

---

## 12. 編譯 ImageJ 外掛（選用）

若需要編譯 `ImageJ` 外掛，可執行：

```powershell
cd d:\DeepLIIF\ImageJ_Plugin
mvn package
```

編譯完成後，產物通常位於：

```powershell
ImageJ_Plugin\target
```

---

## 13. 最短可執行流程

若環境與模型都已準備完成，實際分析常用流程如下：

```powershell
conda activate deepliif-win
cd d:\DeepLIIF
deepliif test --input-dir "DNMT3A 24例 染色圖及評分" --output-dir analysis_outputs\deepliif_prediction_images --model-dir model-server\DeepLIIF_Latest_Model --tile-size 512
python Scripts\apply_dnmt3a_intensity_thresholds.py --input-dir "DNMT3A 24例 染色圖及評分" --output-dir analysis_outputs\dnmt3a_fullslide_outputs
python Scripts\apply_dnmt3a_intensity_thresholds.py --input-dir "DNMT3A 24例 染色圖及評分" --mask-dir analysis_outputs\deepliif_prediction_images --image-suffix .jpg --mask-suffix _SegRefined.png --output-dir analysis_outputs\dnmt3a_cancer_mask_outputs
python Scripts\generate_dnmt3a_intensity_prediction_images.py --input-dir "DNMT3A 24例 染色圖及評分" --mask-dir analysis_outputs\deepliif_prediction_images --image-suffix .jpg --mask-suffix _SegRefined.png --output-dir analysis_outputs\dnmt3a_cancer_mask_prediction_images
python Scripts\organize_dnmt3a_csvs.py --fullslide-csv analysis_outputs\dnmt3a_fullslide_outputs\source_image_summary.csv --cancer-mask-csv analysis_outputs\dnmt3a_cancer_mask_outputs\source_image_summary.csv --output-dir analysis_outputs\dnmt3a_csv_organized
```

---

## 14. 建議檢查點

若流程要確認是否成功，可依序檢查：

- `deepliif --help` 是否正常
- `model-server\DeepLIIF_Latest_Model` 是否存在
- `analysis_outputs\deepliif_prediction_images\*_SegRefined.png` 是否成功產出
- `source_image_summary.csv` 是否成功產出
- `analysis_outputs\dnmt3a_cancer_mask_prediction_images\` 是否有 `IntensityMap / Overlay / Summary`
