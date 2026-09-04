# `referenceTerrainHeight` 全 NaN — 証拠と再現手順

作成: 2026-09-04。#165 にコメントを残す前の裏取り。
**「自分の環境構築が誤っているだけでは？」を最優先で潰す**構成にした。

---

## 0. 結論

**環境の問題ではない。** 3 通りの独立した方法で確認した。

| 潰し方 | 内容 | 環境が関与するか |
|---|---|---|
| A | ISCE3 のビルドを**一切使わず**、h5py だけで判定式を評価 | ❌ しない |
| B | **自分が作っていない公式プロダクト**が同症状 | ❌ しない |
| C | **同じファイル・同じ実行**の中で、他のレイヤは正常に埋まる | ❌ 切り分け済み |

---

## 1. まず、手元の環境が健全であることの確認

### 1-1. 実際に実行される ISCE3 の実体

```
version : 0.26.0-dev+23f99329d
module  : ~/isce3-build/install/packages/isce3/__init__.py
python  : 3.12.13
```

**読んでいるソースと、実行されるファイルが同一であることを md5 で確認した。**
「ソースを直したつもりが古いものが動いていた」という取り違えは無い。

```
8c9808d4de570a04cb3f86bbc8822fa3  ~/isce3-build/install/packages/nisar/products/writers/BaseL2WriterSingleInput.py
8c9808d4de570a04cb3f86bbc8822fa3  ~/isce3/python/packages/nisar/products/writers/BaseL2WriterSingleInput.py
```

### 1-2. ビルドとソースの対応

* インストール済みのビルドは **`23f99329d`**
* 手元の `develop` は現在 **`f42cea75b`**（2026-09-03 に追従）
* ⚠️ **該当ファイルは両者で完全に同一**（`git diff 23f99329d f42cea75b -- <file>` が空）
  → **ビルドが古いことは今回の結論に影響しない**

### 1-3. テストの基準値

**236/237 合格**（2026-08-30 のフル実行、655 秒）。
唯一の失敗は `nisar.workflows.stage_dem` で、upstream 側のバグ・環境と無関係。
→ **環境が壊れているなら、この 1 件では済まない。**

### 1-4. 依存のバージョンとビルド構成

| 項目 | 値 |
|---|---|
| h5py / libhdf5 | 3.16.0 / 2.2.0 |
| numpy | 1.26.4 |
| GDAL | 3.13.3 |
| C++ コンパイラ | conda 環境の `c++`（GCC 15.3） |
| `WITH_CUDA` | **OFF** |
| `GDAL_MEM_ENABLE_OPEN` | `YES`（設定済み） |
| `PYTHONPATH` | `~/isce3-build/install/packages` |
| `LD_LIBRARY_PATH` | `~/isce3-build/install/lib` |

⚠️ **これらは upstream が試していない新しい組み合わせを含む。**
だから「環境が健全に見える」だけでは不十分で、次の章が要る。

---

## 2. 環境に依存しないことの証明

### A. ISCE3 のビルドを一切使わずに判定式を評価する

ソースの定数と条件式を写し取り、**h5py だけで**評価した。
ISCE3 のビルド・GDAL・C++ のいずれも関与しない。

```python
LUT_1D_AZ_DATASETS = ['referenceTerrainHeight']
input_ds_name_list = ['referenceTerrainHeight']

slant_range_path = f'{group}/slantRange'
flag_luts_are_1d_az = (all([v in LUT_1D_AZ_DATASETS for v in input_ds_name_list]) and
                       slant_range_path not in f)
```

| 製品 | 判定 | 実際 |
|---|---|---|
| `tests/data/envisat.h5`（同梱） | **2 次元** | 1 次元 `(80,)` |
| RSLC `028_152_A_156_2005_DHDH`（実データ） | **2 次元** | 1 次元 `(79,)` |
| RSLC `028_168_D_126_0005_NASV`（実データ） | **2 次元** | 1 次元 `(31,)` |

**3 製品すべてで、実際は 1 次元なのに判定は「2 次元」。**
これはデータと条件式だけで決まる。**環境の入る余地が無い。**

### B. 自分が作っていない公式プロダクトが同症状

JPL が生成し ASF が配布しているプロダクトを開いた（**こちらの環境は一切関与しない**）。

| プロダクト | `referenceTerrainHeight` の有効値 |
|---|---|
| `NISAR_L2_PR_GCOV_028_168_D_126_0005_NASV_A_...` | **0 / 156,420** |
| `NISAR_L2_PR_GCOV_028_152_A_156_2005_DHDH_A_...` | **0 / 111,531** |

どちらも `softwareVersion = 0.25.16` で生成。**リリース版で、他人の環境で、同じ症状。**

### C. 同じファイル・同じ実行の中で他のレイヤは正常

環境が原因なら、ジオコーディング全体が壊れるはず。実際は違う。
**メタデータ用ジオグリッド `(10, 41)` に載る全レイヤ**を数えた。

| レイヤ | 有効画素 |
|---|---|
| `calibrationInformation/frequencyA/elevationAntennaPattern/HH` | 178 / 410（43.41%） |
| `calibrationInformation/frequencyA/noiseEquivalentBackscatter/HH` | 178 / 410（43.41%） |
| **`processingInformation/parameters/referenceTerrainHeight`** | **0 / 410（0.00%）** |

同一ファイル・同一実行・同一環境で、**このレイヤだけが 0%。**
科学データ（`HHHH`）も正常に生成されている。

---

## 3. 再現手順（第三者がそのまま実行できる）

**NISAR の実データは不要。同梱テストデータだけで再現する。**

### 手順 1: GCOV のワークフローテストを実行する

```bash
ctest --test-dir <build> -R '^test\.python\.pkg\.nisar\.workflows\.gcov$' --output-on-failure -V
```

※ このテストに `DEPENDS` は無いので**単独実行して問題ない**
（`-R` で絞ると前提テストが走らず落ちるものが別にあるが、これは該当しない）

**観測される結果:**

```
ERROR 5: tmp9v1bgg2s.vrt, band 1: Access window out of range in RasterIO().
Requested (11,30) of size 229x20 on raster of 80x1.      ← 4 回出る
1/1 Test #212: test.python.pkg.nisar.workflows.gcov ...   Passed    5.64 sec
100% tests passed
```

→ **エラーを 4 回出しながら「合格」する。終了コードは 0。**

### 手順 2: 出力プロダクトを開く

```python
import h5py, numpy as np
f = 'gcov_envisat_area_noise_correction_false.h5'
with h5py.File(f) as h:
    a = h['/science/LSAR/GCOV/metadata/processingInformation'
          '/parameters/referenceTerrainHeight'][()]
    print(a.shape, np.isfinite(a).sum(), 'of', a.size)
# (10, 41) 0 of 410
```

### 手順 3（任意）: GDAL からどう見えているか確認する

```bash
gdalinfo 'HDF5:"tests/data/envisat.h5"://science/LSAR/SLC/metadata/processingInformation/parameters/referenceTerrainHeight'
#   Size is 80, 1        ← エラー文の "raster of 80x1" と一致

gdalinfo 'HDF5:"...":/.../effectiveVelocity'
#   Size is 240, 80      ← 本物の 2 次元 LUT はこう見える
```

---

## 4. 「1 次元経路に入っていない」直接証拠

ソースには、1 次元として処理したときに出る**専用の警告文**がある。
テスト実行のログを数えた。

| 警告 | 回数 |
|---|---|
| `Geolocating one dimensional dataset: ... (rg. vector)` | **4 回**（crosstalk の 4 データセット） |
| `Geolocating one dimensional dataset: ... (az. vector)` | **0 回** |

`(az. vector)` は `referenceTerrainHeight` 専用の経路。
**一度も出ていない = その分岐に一度も入っていない。**

対照的に、**同じ PR で入ったレンジ方向の 1 次元経路は 4 回動いている。**
→ 同じ仕組みの片方だけが動いていない。環境なら両方おかしくなるはず。

---

## 5. 数値まとめ

| 項目 | 値 |
|---|---|
| 入力 `referenceTerrainHeight`（envisat） | `(80,)` float32・全て 0.0 |
| GDAL から見たサイズ | `80 x 1` |
| 要求されるサイズ | `240 x 80`（`slantRange` × `zeroDopplerTime`） |
| 出力レイヤ | `(10, 41)` **全て NaN** |
| エラー回数 | 4 |
| テストの合否 | **合格**（終了コード 0） |

---

## 6. 何が言えて、何が言えないか

**言える**

* データ自身は 1 次元であり、判定式は 3 製品すべてで誤答する（ビルド不要で確認）
* 公式配布プロダクトでも同症状（**他人の環境・リリース版 0.25.16**）
* 同じ実行の中で他のレイヤは正常 → ジオコーディング基盤の問題ではない
* 1 次元経路に入った形跡が無い（専用警告が 0 回）

**言えない**

* **GDAL のバージョンを変えて試していない。** 手元は 3.13.3 のみ。
  ただし「要求サイズ 240×80」は ISCE3 側の計算なので GDAL に依存しない。
  加えて B（公式プロダクト）が別環境での発生を示している
* 上流が**この件を既に把握しているかどうか**は分からない（内部議論が非公開）
  → だから **#165 で「意図した挙動か」を先に聞く**
