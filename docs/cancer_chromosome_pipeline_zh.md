# 癌細胞先分割、再做染色體辨識流程

這個專案目前最適合實作成兩階段流程：

1. 第一階段先用語意分割模型找出癌細胞區域。
2. 第二階段只在癌細胞區域內做染色體或核相關辨識。

這樣比直接在整張病理圖上找染色體更穩定，因為背景、間質與非腫瘤細胞會先被排除。

## 建議模型

第一階段建議使用 U-Net 類模型做癌細胞 segmentation。
這個 repo 內建的 DeepLIIF 已支援 segmentation generator 使用 `unet_512`。

建議設定：

```bash
deepliif train \
  --dataroot Datasets/CancerStage1 \
  --name cancer_stage1_unet \
  --model DeepLIIF \
  --modalities-no 0 \
  --seg-gen true \
  --net-gs unet_512 \
  --gpu-ids 0
```

重點是：

- `--model DeepLIIF`
- `--modalities-no 0`
- `--seg-gen true`
- `--net-gs unet_512`

這代表模型只學一件事：從輸入病理影像直接輸出癌細胞 segmentation mask。

## 第一階段資料格式

如果原始檔名像下面這樣：

- `Case01_IHC.png`
- `Case01_CancerSeg.png`

可以用新的 CLI 指令建立 stage-1 訓練資料：

```bash
deepliif prepare-cancer-seg-data \
  --input-dir path/to/raw_pairs \
  --output-dir Datasets/CancerStage1 \
  --image-label IHC \
  --mask-label CancerSeg \
  --validation-ratio 0.2
```

這個指令會把每組資料拼成：

```text
(原圖, 癌細胞遮罩)
```

對應到 `DeepLIIF --modalities-no 0` 的訓練格式。

## 第二階段前處理

當第一階段模型產生癌細胞 mask 之後，可以先把非癌區域蓋掉，只留下癌細胞區域，再送進後段染色體辨識模型。

```bash
deepliif apply-cancer-mask \
  --image-dir path/to/raw_images \
  --mask-dir path/to/cancer_masks \
  --output-dir path/to/masked_images \
  --image-label IHC \
  --mask-label CancerSeg
```

輸出的 `masked_images` 就是只保留癌細胞區域的影像。

## 第二階段模型建議

第二階段有兩種常見做法：

1. 如果目標是染色體或細胞核區域分割：
   直接再訓練一個 U-Net 類 segmentation 模型。
2. 如果目標是染色體型態分類或強度判讀：
   先用第一階段 mask 裁出癌區，再訓練分類模型或偵測模型。

如果你的「染色體辨識」本質上還是像素級區域標註，建議第二階段仍然優先用 U-Net 類模型。

## 根據癌細胞區塊計算染色強度與陽性比例

如果你現在的目標是：

- 根據預測好的癌細胞區塊
- 判斷染色強度是 `1+ / 2+ / 3+`
- 計算陽性比例 `%`

目前 repo 已可直接用癌細胞 mask 限制分析範圍，只在癌區內計算：

```bash
python Scripts/apply_dnmt3a_intensity_thresholds.py \
  --input-dir path/to/raw_images \
  --mask-dir path/to/predicted_cancer_masks \
  --summary-json analysis_outputs/dnmt3a_intensity_calibration/summary.json \
  --output-dir analysis_outputs/dnmt3a_masked_outputs \
  --image-suffix _IHC \
  --mask-suffix _CancerSeg
```

輸出重點：

- `weak_1plus_pct`
- `medium_2plus_pct`
- `strong_3plus_pct`
- `positive_nuclei_pct`
- `pred_intensity_score`
- `pred_percent_score`
- `pred_final_score`
- `pred_expression`

其中：

- `pred_intensity_score` 代表整張癌區的主強度等級
- `positive_nuclei_pct` 代表癌區內陽性細胞核比例
- `pred_percent_score` 是把陽性比例換成病理分數

也就是說，這一步已經很接近你說的「根據癌細胞區塊辨識染色強度幾價以及占陽性比例 % 數」。

## 為什麼這樣做

直接讓單一模型同時學癌細胞定位與染色體辨識，通常會遇到兩個問題：

1. 正負樣本不平衡更嚴重。
2. 模型容易把背景紋理誤學成染色體訊號。

先做癌細胞 segmentation 的好處是：

- 降低背景干擾
- 提高後段特徵集中度
- 更容易解釋結果
- 更方便把錯誤切成「定位錯」或「辨識錯」

## 實作建議

- 第一階段 mask 請盡量由病理專家標出癌細胞區域。
- mask 請使用二值圖，癌細胞為白色，其他區域為黑色。
- 第一階段與第二階段都建議先從 512x512 patch 開始。
- 如果染色體標註很少，先做 patch-level gating 再做第二階段訓練，通常比端到端更容易收斂。
