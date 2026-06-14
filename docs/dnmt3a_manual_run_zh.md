# DNMT3A 強度分析手動操作教學

這份文件整理目前專案中和 `DNMT3A` 分析最直接相關的三件事：

1. 怎麼手動跑程式
2. 程式實際用到的神經網路模型
3. `ImageJ` / `Fiji` 要怎麼搭配使用

---

## 1. 系統可以辨識什麼

目前流程可輸出：

- `1+` 染色強度比例
- `2+` 染色強度比例
- `3+` 染色強度比例
- 陽性 nuclei 比例
- 最終強度分數
- 百分比分數
- 最終表現分數

對應欄位包括：

- `weak_1plus_pct`
- `medium_2plus_pct`
- `strong_3plus_pct`
- `positive_nuclei_pct`
- `pred_intensity_score`
- `pred_percent_score`
- `pred_final_score`
- `pred_expression`

要先特別說明：

目前 `1+ / 2+ / 3+` 和陽性比例不是神經網路直接輸出，而是：

1. 先用 `DeepLIIF` 預測 segmentation
2. 再把 segmentation 當成癌細胞 ROI
3. 在 ROI 內做 `DNMT3A` 規則式強度分析

---

## 2. 手動執行流程

整體建議依序分成 3 步。

### 步驟 1：先跑 DeepLIIF 預測

目的：

- 把原始 IHC 影像送進 `DeepLIIF`
- 取得 segmentation 與 `SegRefined` 結果

範例：

```bash
deepliif test --input-dir "DNMT3A 24例 染色圖及評分" --output-dir analysis_outputs/deepliif_prediction_images --model-dir model-server/DeepLIIF_Latest_Model --tile-size 512
```

這一步常見輸出會包含：

- `*_Seg.png`
- `*_SegOverlaid.png`
- `*_SegRefined.png`
- `*_mod1-Hema.png`
- `*_mod2-DAPI.png`
- `*_mod3-Lap2.png`
- `*_mod4-Marker.png`

其中最重要的是：

- `*_SegRefined.png`

因為後續會把它當作癌細胞 ROI mask。

### 步驟 2：計算癌細胞區域內的 DNMT3A 強度與陽性比例

目的：

- 只在癌細胞區域內統計 `DNMT3A`
- 產出 `1+ / 2+ / 3+` 比例和陽性比例 CSV

範例：

```bash
python Scripts/apply_dnmt3a_intensity_thresholds.py ^
  --input-dir "DNMT3A 24例 染色圖及評分" ^
  --mask-dir analysis_outputs/deepliif_prediction_images ^
  --mask-suffix _SegRefined ^
  --output-dir analysis_outputs/dnmt3a_cancer_mask_outputs
```

輸出：

- `analysis_outputs/dnmt3a_cancer_mask_outputs/patch_results.csv`
- `analysis_outputs/dnmt3a_cancer_mask_outputs/source_image_summary.csv`

如果不想限制在癌細胞區域，也可以不加 `--mask-dir`：

```bash
python Scripts/apply_dnmt3a_intensity_thresholds.py --input-dir "DNMT3A 24例 染色圖及評分" --output-dir analysis_outputs/dnmt3a_fullslide_outputs
```

### 步驟 3：輸出強度預測圖

目的：

- 不只看 CSV
- 直接在圖上顯示哪些癌細胞區域屬於 `1+ / 2+ / 3+`

範例：

```bash
python Scripts/generate_dnmt3a_intensity_prediction_images.py ^
  --input-dir "DNMT3A 24例 染色圖及評分" ^
  --mask-dir analysis_outputs/deepliif_prediction_images ^
  --mask-suffix _SegRefined ^
  --output-dir analysis_outputs/dnmt3a_cancer_mask_prediction_images
```

輸出：

- `*_IntensityMap.png`
- `*_IntensityOverlay.png`
- `*_IntensitySummary.json`

### 步驟 4：整理比較報表

如果要比較全圖分析和癌細胞 mask 分析，可以再跑：

```bash
python Scripts/organize_dnmt3a_csvs.py --fullslide-csv analysis_outputs/dnmt3a_fullslide_outputs/source_image_summary.csv --cancer-mask-csv analysis_outputs/dnmt3a_cancer_mask_outputs/source_image_summary.csv --output-dir analysis_outputs/dnmt3a_csv_organized
```

輸出：

- `dnmt3a_fullslide_vs_cancer_mask_comparison.csv`
- `dnmt3a_expression_changed_cases.csv`
- `dnmt3a_intensity_changed_cases.csv`

---

## 3. 怎麼理解這些分數

### 3.1 `1+ / 2+ / 3+`

目前定義是依 DAB 強度區域分級：

- `1+`：弱陽性
- `2+`：中度陽性
- `3+`：強陽性

對應輸出欄位：

- `weak_1plus_pct`
- `medium_2plus_pct`
- `strong_3plus_pct`

### 3.2 陽性比例

陽性比例主要看：

- `positive_nuclei_pct`

也就是在 nuclei-like 區域中，被判定為陽性的比例。

### 3.3 最終分數

系統會再轉成：

- `pred_intensity_score`
- `pred_percent_score`
- `pred_final_score`
- `pred_expression`

規則為：

- `pred_percent_score`
  - `0% -> 0`
  - `<10% -> 1`
  - `10%~50% -> 2`
  - `>50% -> 3`
- `pred_final_score = pred_intensity_score x pred_percent_score`
- `pred_expression`
  - `pred_final_score > 4` 為 `high`
  - 其餘為 `low`

---

## 4. 程式背後使用的模型

### 4.1 神經網路主體

這個專案目前真正使用的神經網路主體是 `DeepLIIF`。

它不是只有單一一個 U-Net，而是多任務模型，包含：

- modality translation generators
- segmentation generator
- discriminators

### 4.2 主要架構

依專案中的模型說明，原始 `DeepLIIF` 主要配置為：

- translation generator：`ResNet-9block`
- segmentation generator：`UNet-512`
- discriminator：`PatchGAN`

也就是說：

- IHC 影像先被轉成多模態影像
- 再整合出 segmentation
- 最後得到 `SegRefined` 等結果

### 4.3 為什麼說它「類似 U-Net」

如果你是從病理 segmentation 的角度理解，這樣講是對的：

- segmentation 那一段可以用 `UNet-512`
- repo 也支援 `unet_128 / unet_256 / unet_512 / unet_512_attention`

但目前這份專案成果不是單獨訓練一顆純 U-Net 來直接輸出 `1+ / 2+ / 3+`。

真正流程是：

1. `DeepLIIF` 先做 segmentation
2. 後處理腳本再做 `DNMT3A` 強度量化

### 4.4 後處理不是神經網路

目前 `DNMT3A` 強度分析部分主要是影像分析流程，不是第二個深度學習分類器。

大致步驟為：

1. 建立 tissue mask
2. 若有癌細胞 mask，則只保留 ROI
3. 轉成 `HED` 色彩空間
4. 取出 `DAB` channel
5. 用 threshold 找出 DAB-positive 區域
6. 計算各區域平均強度
7. 分成 `1+ / 2+ / 3+`
8. 估計 positive nuclei 百分比

---

## 5. ImageJ / Fiji 教學

### 5.1 ImageJ 在這個專案裡的角色

這個 repo 有 `ImageJ` 外掛，但它原生是讓使用者把影像或 ROI 送去 `DeepLIIF` 做推論。

它不是直接用來執行你這次新增的：

- `DNMT3A` 1+ / 2+ / 3+ 量化
- 癌細胞 mask 限制分析
- `IntensityMap` 與 `IntensityOverlay` 產圖

因此實務上建議這樣分工：

- `ImageJ`：用來開圖、畫 ROI、看結果、做人工比對
- `Python / CLI`：用來跑正式的 `DNMT3A` 量化與報表

### 5.2 安裝 ImageJ 外掛

1. 安裝 `ImageJ` 或 `Fiji`
2. 準備 `DeepLIIF_ImageJ.jar`
3. 在 `ImageJ` 中點選 `Plugins > Install...`
4. 選擇 `DeepLIIF_ImageJ.jar`
5. 安裝到 `ImageJ/plugins` 資料夾
6. 重新啟動 `ImageJ`

### 5.3 單張影像基本操作

1. 開啟一張 IHC 影像
2. 若只想分析局部，就先畫 ROI
3. 從外掛選單執行 DeepLIIF 相關命令
4. 檢視 segmentation 和分類 overlay

### 5.4 多個 ROI 操作

1. 開啟影像
2. 用選取工具畫多個 ROI
3. 把 ROI 加入 `ROI Manager`
4. 執行 `Plugins > DeepLIIF > Submit ROIs to DeepLIIF`
5. 等待推論完成
6. 檢視各 ROI 輸出結果

### 5.5 ROI 使用注意事項

目前 repo 內文件提到：

- ROI 尺寸上限約為 `3000 x 3000` 像素

所以如果影像很大，建議：

- 先在 `ImageJ` 中切局部區域
- 或先改以 patch / tile 方式處理

### 5.6 如果要自己編譯 ImageJ 外掛

在專案根目錄下執行：

```bash
cd ImageJ_Plugin
mvn package
```

成功後會產生：

- `DeepLIIF_ImageJ.jar`

---

## 6. 建議的實務使用方式

如果你的目的是真正完成癌細胞 `DNMT3A` 報告，建議採用下面流程：

1. 用 `DeepLIIF` 跑 segmentation
2. 用 `SegRefined` 當癌細胞 mask
3. 用 `apply_dnmt3a_intensity_thresholds.py` 算強度與陽性比例
4. 用 `generate_dnmt3a_intensity_prediction_images.py` 產生視覺化圖
5. 用 `organize_dnmt3a_csvs.py` 整理成報表
6. 用 `ImageJ` 做人工檢視與 ROI 對照

---

## 7. 對外說明時可以怎麼講

如果要簡單對外說明這個系統，可以用這句：

> 本系統先利用 DeepLIIF 進行癌細胞相關 segmentation，再以癌細胞 ROI 為基礎，計算 DNMT3A 的 1+、2+、3+ 染色強度比例與陽性比例，並輸出 CSV 與可視化預測圖。

如果要更精確一點，也可以補充：

> 其中 segmentation 使用 DeepLIIF 的深度學習模型，DNMT3A 強度與陽性比例則由後續影像分析規則計算，不是神經網路直接端到端輸出。

---

## 8. 報告可直接貼上的公式版說明

以下段落可直接放入方法章節、專題報告或論文草稿中。

### 8.1 DNMT3A 染色強度與陽性比例計算原理

本系統之 `DNMT3A` 染色強度分析並非由神經網路直接端到端輸出 `1+ / 2+ / 3+` 結果，而是先以 `DeepLIIF` 取得 segmentation 或癌細胞 ROI，之後再於 ROI 內進行規則式影像分析。其計算流程可表示如下。

首先，令輸入 RGB 病理影像為 `I(x,y)`，將其轉為灰階影像 `I_gray(x,y)`，並建立組織遮罩 `T(x,y)`：

\[
T(x,y)=
\begin{cases}
1, & I_{gray}(x,y) < \min\left(0.95,\ Q_{95}(I_{gray})\right) \\
0, & \text{otherwise}
\end{cases}
\]

其中 `Q95` 表示第 95 百分位數，用以排除過亮背景像素。若有癌細胞 ROI mask，則最終分析區域為組織遮罩與 ROI 遮罩之交集。

接著，將 RGB 影像轉換至 `HED` 色彩空間，取其 `DAB` 通道 `D(x,y)` 作為棕色染色訊號強度：

\[
D(x,y)=\text{DAB channel}\left(\text{rgb2hed}(I)\right)
\]

於組織區域內，計算 `DAB` 門檻值 `\tau_{dab}`：

\[
\tau_{dab}=\max \left(Q_{p}(D|T),\ \text{Otsu}(D|T)\right)
\]

其中 `Qp` 為 DAB 強度的百分位數，本系統預設 `p=70`；`Otsu(D|T)` 為在組織區域內以 Otsu 方法求得之二值化門檻。之後定義 DAB 陽性區域遮罩 `P(x,y)`：

\[
P(x,y)=
\begin{cases}
1, & D(x,y)>\tau_{dab}\ \land\ T(x,y)=1 \\
0, & \text{otherwise}
\end{cases}
\]

再對陽性遮罩做形態學開閉運算與小區域移除，以降低雜訊干擾。將最終 DAB 陽性連通區域記為第 `i` 個區塊 `R_i`，則其平均 DAB 強度為：

\[
m_i=\frac{1}{|R_i|}\sum_{(x,y)\in R_i} D(x,y)
\]

為了讓不同影像之間的強度具有可比較性，再以組織區域內 DAB 強度第 99 百分位數進行正規化：

\[
f_i=\frac{m_i}{Q_{99}(D|T)}
\]

其中 `f_i` 即為每個陽性區域的正規化強度特徵。接著設定三個門檻 `t0`、`t1`、`t2`。首先以 `t0` 去除過弱訊號，僅保留：

\[
S=\{f_i \mid f_i \ge t_0\}
\]

若 `S` 為空，則退回使用全部 `f_i`。之後對 `S` 計算摘要統計量 `s`，可為平均值、中位數、75 百分位數或 90 百分位數：

\[
s=\text{summary}(S)
\]

最後依門檻 `t1` 與 `t2` 將染色強度分為 `1+`、`2+`、`3+`：

\[
\text{Intensity Score}=
\begin{cases}
1, & s < t_1 \\
2, & t_1 \le s < t_2 \\
3, & s \ge t_2
\end{cases}
\]

此外，系統亦統計所有陽性區域落在各強度等級的比例。令：

\[
N_{1+}=\sum_i \mathbf{1}(f_i<t_1)
\]

\[
N_{2+}=\sum_i \mathbf{1}(t_1\le f_i<t_2)
\]

\[
N_{3+}=\sum_i \mathbf{1}(f_i\ge t_2)
\]

總陽性區域數為：

\[
N=N_{1+}+N_{2+}+N_{3+}
\]

則各強度比例分別為：

\[
\text{weak\_1plus\_pct}=100\times \frac{N_{1+}}{N}
\]

\[
\text{medium\_2plus\_pct}=100\times \frac{N_{2+}}{N}
\]

\[
\text{strong\_3plus\_pct}=100\times \frac{N_{3+}}{N}
\]

為估計陽性細胞比例，系統另於 `Hematoxylin` 通道中擷取 nuclei-like 區域，對每個細胞核候選區塊計算其對應 DAB 平均強度，記為 `g_j`。若 `g_j` 高於陽性細胞核門檻 `p0`，則視為陽性 nuclei：

\[
N_{pos}=\sum_j \mathbf{1}(g_j\ge p_0)
\]

\[
\text{positive\_nuclei\_pct}=100\times \frac{N_{pos}}{N_{nuclei}}
\]

其中 `N_nuclei` 為 nuclei-like 區域總數。之後再將陽性比例轉換為百分比分數：

\[
\text{Percent Score}=
\begin{cases}
0, & p \le 0 \\
1, & 0 < p < 10 \\
2, & 10 \le p \le 50 \\
3, & p > 50
\end{cases}
\]

其中 `p=positive_nuclei_pct`。最終分數定義為：

\[
\text{Final Score}=\text{Intensity Score}\times \text{Percent Score}
\]

並依最終分數區分表現型：

\[
\text{Expression}=
\begin{cases}
\text{high}, & \text{Final Score}>4 \\
\text{low}, & \text{Final Score}\le 4
\end{cases}
\]

綜上所述，本系統係先以 `DeepLIIF` 提供 segmentation 或癌細胞 ROI，再基於 DAB 強度、區域統計與 nuclei-like 區域陽性比例，完成 `DNMT3A` 之 `1+ / 2+ / 3+` 染色強度分級與陽性比例量化。
