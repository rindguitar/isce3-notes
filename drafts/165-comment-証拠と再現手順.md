# `referenceTerrainHeight` 全 NaN — 証拠・再現手順・修正案

作成: 2026-09-04（2026-09-10 に修正案の検証を追加）。#165 にコメントを残す前の裏取り。
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

### 1-0. どうやって環境を作ったか

**「環境構築が間違っているのでは」を検討できるよう、作り方をそのまま書いておく。**
詳細と落とし穴は `reference/environment.md`。

```bash
# 1. 依存環境（conda）
source ~/miniforge3/etc/profile.d/conda.sh
cd ~/isce3
conda env create -f environment.yml
# ⚠️ environment.yml は下限指定のみで上限が無い。この 2 つの固定は必須
conda install -n isce3 'eigen<4' 'pybind11<3' ccache
conda activate isce3

# 2. ビルド（CMake 直叩き。ビルド先はリポジトリの外）
cmake -S ~/isce3 -B ~/isce3-build -G Ninja \
  -DISCE3_FETCH_DEPS=OFF \
  -DWITH_CUDA=OFF \
  -DCMAKE_INSTALL_PREFIX=~/isce3-build/install
cmake --build ~/isce3-build -j8
cmake --install ~/isce3-build

# 3. テスト
ctest --test-dir ~/isce3-build --output-on-failure
```

環境変数（`PYTHONPATH` / `LD_LIBRARY_PATH` / `GDAL_MEM_ENABLE_OPEN`）は
conda の activate フックで設定している。**これが無いと対話的な Python から
`import isce3` が通らない。**

`-DWITH_CUDA=OFF` が必要なのは、既定が `Auto` でシステムの nvcc（CUDA 12.0）を
拾ってしまい、環境の GCC 15.3 と非対応でビルドが壊れるため。

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

### 1-2. ビルドとソースの対応（ここは誤解されやすいので詳しく）

**`23f99329d` は git の短縮コミットハッシュ**（`Solve CI failures (#366)`、2026-08-24）。
「インストール済みのビルドは `23f99329d`」とは、**`~/isce3` がそのコミットだったときの
ソースから作られたものが `~/isce3-build/install` に入っている**という意味。

版名 `0.26.0-dev+23f99329d` の内訳（実装は `~/isce3/.cmake/Isce3Version.cmake`）:

| 部分 | 出どころ |
|---|---|
| `0.26.0-dev` | `~/isce3/VERSION.txt` の中身 |
| `+23f99329d` | `git describe --always --dirty` の出力 |

⚠️ **版名は configure 時に確定する。** 指すのは「最後に configure したときの HEAD」で、
最後にビルドしたソースとは限らない。作業ツリーが汚れていれば `-dirty` が付く
（今回は付いていない = **汚れていない状態でビルドした**）。

現状（2026-09-10 に `cmake --install` を実行して揃えた）:

| 項目 | 値 |
|---|---|
| ソースの HEAD | `67bccb0ce` |
| インストール済みの Python | **ソースと完全一致**（`diff -rq` が空） |
| `23f99329d`→`67bccb0ce` の **C++ の変更** | **ゼロ**（`git diff --stat` が空）→ `.so` は HEAD に対しても正しい |
| 版名 | `0.26.0-dev+23f99329d` のまま（**configure 時に確定するため。異常ではない**） |

**ctest が読むのはインストール先。** テスト定義の `PYTHONPATH` は
`~/isce3-build/install/packages` が先頭にあり、ビルドツリー側
（`~/isce3-build/packages`）はその後ろに置かれる。

⚠️ **`cmake --install` はインストール先しか更新しない。**
ビルドツリー側の Python コピーは `cmake --build` で更新される。
今回は ctest が読む側（インストール先）が揃っていれば十分。

**確かめ方**（更新時刻ではなく中身で比べる。`cmake --install` はソースの
更新時刻を保持するため、mtime は当てにならない）:

```bash
python3 -c 'import isce3; print(isce3.__version__, isce3.__file__)'
git -C ~/isce3 log --oneline -1
diff -rq ~/isce3-build/install/packages/nisar ~/isce3/python/packages/nisar | grep '^Files'
```

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

**2026-09-10 に取り直した**（ソースと完全一致したインストールで実行）。
結果は同一: エラー 4 回・`(az. vector)` 0 回・`(rg. vector)` 4 回・出力 0/410 で合格。

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
* **仕様はこの層を「地図座標の関数」と定義している**（`XML/L2/nisar_L2_GCOV.xml`、
  `shape="dopplerCentroidShape"`）。**埋まっているべき層**であり、置き場所の間違いではない
* **取得方法の問題ではない。** ISCE3 に 2 次元で書く経路が無く
  （生成は `writers/SLC.py` の 1 か所、アジマス長で固定）、現在の実データは 1 次元しかない
* 公式配布プロダクトでも同症状（**他人の環境・リリース版 0.25.16**）
* 同じ実行の中で他のレイヤは正常 → ジオコーディング基盤の問題ではない
* 1 次元経路に入った形跡が無い（専用警告が 0 回）

**言えない**

* **GDAL のバージョンを変えて試していない。** 手元は 3.13.3 のみ。
  ただし「要求サイズ 240×80」は ISCE3 側の計算なので GDAL に依存しない。
  加えて B（公式プロダクト）が別環境での発生を示している
* 上流が**この件を既に把握しているかどうか**は分からない（内部議論が非公開）
  → だから **#165 で「意図した挙動か」を先に聞く**
* ~~インストール済みツリーが古い~~ → **2026-09-10 に解消**。
  `cmake --install` 後、ソースと完全一致した状態で再現を取り直し、結果は同一だった

---

## 7. 経緯と設計意図（git 履歴）
**「1 次元を意図的に足切りしたのでは」を確かめるため、履歴を遡った。結論は逆だった。**

| 版 | 変更 | 結果 |
|---|---|---|
| v0.23.0（2024-08） | #1928 が `referenceTerrainHeight` を `sourceData` へ複製 | — |
| **v0.24.2（2025-01）** | **#1929 がジオコーディングを追加** | 🔴 **ここから全 NaN**。1 次元の扱いは無く、常に 2 次元として開いていた |
| v0.25.0（2025-05） | #2137 が 1 次元 LUT のジオコーディングを追加 | 🔴 **まだ全 NaN**。アジマス側の分岐が開かない |
| v0.25.16（2026-06） | 公式プロダクトの生成版 | 🔴 全 NaN のまま配布 |

**2 回、1 次元に対処しようとして 2 回とも外している。**

1. **#1929 の時点で 1 次元を想定していた。** ラスタ生成が `try/except` で囲まれ、
   コメントに理由が書いてある:

   ```python
   # Read `raster_ref` catching/handling potential problems:
   # - Dataset does not exist;
   # - Dataset is a 1-D vector instead of a 2-D array.   ← ここ
   try:
       temp_raster = isce3.io.Raster(raster_ref)
   ```

   ⚠️ **この防御は働かない。** 1 次元データでも `isce3.io.Raster()` は**成功する**
   （GDAL が 80×1 として開く）。失敗するのは**その後の読み出し**なので例外にならない

2. **#2137 は 1 次元対応を実装し、テストまで追加している。**
   コミットメッセージの最後に **`add unit test to exercise the geocoding of 1D LUTs`**。
   ⚠️ ただし追加されたテストは **crosstalk（レンジ方向）だけ**で、
   使われた `winnipeg.h5` には **`referenceTerrainHeight` が存在しない**
   （同コミットで `winnipeg.h5` に crosstalk を足している）

**兄弟の判定と比べると差が際立つ。**

```python
flag_luts_are_1d_rg = all([var in LUT_1D_RG_DATASETS for var in input_ds_name_list])
                      # 名前だけで判定 → 動く

flag_luts_are_1d_az = (all([var in LUT_1D_AZ_DATASETS for var in input_ds_name_list])
                       and slant_range_path not in self.input_hdf5_obj)
                       # ↑ この条件が余分。決して真にならない
```

→ **「1 次元を足切りした」のではなく、「1 次元に対応しようとして届かなかった」。**
`LUT_1D_AZ_DATASETS = ['referenceTerrainHeight']` という定数は、
**この 1 つのデータセットのためだけに存在している。**

### なぜその条件を書いたのか（相手の意図の読み取り）

**追加された条件は「1 次元の判定」ではなく、「2 次元用の安全弁」だったと読める。**
ここを理解しておかないと、指摘が的外れになる。

判定は 2 つの部分でできている。

```python
flag_luts_are_1d_az = (all([var in LUT_1D_AZ_DATASETS ...])   # ← 1 次元の判定（名前で）
                       and slant_range_path not in ...)        # ← 後から足された安全弁
```

**前半だけなら正しく動く。** 兄弟のレンジ方向はこの形のままで、実際に動いている。

では後半は何のためか。コミットの箇条書きが順番に語っている。

```
* add geocoding of 1-D LUTs to BaseL2WriterSingleInput        ← まず 1 次元対応
* handle case in which `referenceTerrainHeight` is a 2-D LUT  ← ここで安全弁を追加
```

**名前だけで判定すると、将来 2 次元化したときに「1 次元だ」と誤判定して複製してしまう。**
それを防ぐ実行時チェックが要る、と考えて「距離軸があるかどうか」を選んだ、と読むのが自然
（squash されているので断定はできない）。

> **将来の 2 次元化に備えて足した安全弁が、現在の 1 次元の経路まで閉ざしてしまった。**

⚠️ **この読み方は修正案 B と整合する。** B は「安全弁（＝距離軸の選択）」と
「複製の要否（＝データの次元）」を**別々に判断させる**もので、
**相手が守ろうとしたもの（将来の 2 次元化）を壊さずに** 1 次元を通す。
だから B は 2 次元入力でも同じ答えを出す（→ 8 節で実測）。

---

## 8. 修正案（実験で検証済み・2026-09-10）

`~/isce3` は書き換えず、**`~/isce3-build/install` の複製にパッチを当てて検証し、
毎回 md5 で復元を確認した**（復元後 `8c9808d4…` = ソースと一致）。

### 候補 A: 判定をデータ自身の次元で行う

```python
flag_luts_are_1d_az = (
    all([var in LUT_1D_AZ_DATASETS for var in input_ds_name_list]) and
    all([f'{input_h5_group_path}/{var}' in self.input_hdf5_obj and
         self.input_hdf5_obj[f'{input_h5_group_path}/{var}'].ndim == 1
         for var in input_ds_name_list]))
```

| | 結果 |
|---|---|
| `Access window` エラー | **6 回 → 0 回**（GCOV 4 + GSLC 2） |
| 出力レイヤ | 0/410 → **134/410**（値はすべて 0.0。入力が全ゼロなので正しい） |
| 科学データ | **ビット単位で不変**（GCOV / GSLC とも） |

⚠️ **限界がある。** 後述の 2 次元経路（178/410）より**狭い**。
1 次元経路は距離軸を **RSLC のレーダグリッドから 21 点 + 余白 5 画素**で作り直すため、
LUT 本来の `slantRange`（240 点）より範囲が狭くなる。

### 候補 B: 次元は「複製の要否」、距離軸は既にある `slantRange` を使う（**推奨**）

A に加えて、距離軸の取得条件を変える。

```python
# 変更前: if not flag_luts_are_1d_az:
# 変更後:
if slant_range_path in self.input_hdf5_obj:
```

**考え方**: 2 つの判断を分ける。

| 判断すること | 何で決めるか |
|---|---|
| 値を距離方向へ複製する必要があるか | **データセット自身の次元** |
| 距離軸として何を使うか | **`slantRange` があるかどうか** |

元のコードはこの 2 つを 1 つの条件で兼ねていた。**そこが誤りの本体。**

| | 結果 |
|---|---|
| `Access window` エラー | **6 回 → 0 回** |
| 出力レイヤ | 0/410 → **178/410** |
| **2 次元経路との一致** | **マスク完全一致・値の最大差 0.0** ✅ |
| 科学データ | **ビット単位で不変**（GCOV / GSLC とも） |
| 他のメタデータ層 | **変化なし** |
| crosstalk（レンジ方向 1 次元）経路 | `(rg. vector)` **4 回のまま** ＝ 壊していない |
| テスト | **合格** |

### 検証方法: 「2 次元だったらどうなるか」と突き合わせた

**同梱 `envisat.h5` の `referenceTerrainHeight` を `(80,)` → `(80, 240)` に作り替え**
（値は距離方向へ複製。1 次元経路の `np.repeat` と同じ作り方）、
**未修正コード**で実行した。エラーは 0 回で、出力は **178/410**。

これが「上流が既に持っている 2 次元経路の答え」であり、**B はこれと完全に一致する。**

> 💡 コードのコメントには**将来 2 次元 LUT へ移行する計画**が書かれている。
> つまり **B は「2 次元化した後と同じ結果を、今出す」**ことになる。

同じ runconfig・同じ入力値での比較:

| 実行 | 有効画素 |
|---|---|
| 1 次元入力 + 未修正 | **0/410** |
| 1 次元入力 + 候補 A | 134/410 |
| 1 次元入力 + **候補 B** | **178/410** |
| **2 次元入力 + 未修正**（目標） | **178/410** |

### 「今も将来も正しく通るか」を 2×2 で確かめた（2026-09-10）

**入力データの次元 × コードの状態**の 4 通りをすべて実行した。

| | 未修正 | **修正案 B** |
|---|---|---|
| **1 次元（現在の実データ）** | 🔴 **0/410**（＝今のバグ） | ✅ **178/410** |
| **2 次元（将来の移行後）** | ✅ 178/410 | ✅ **178/410** |

* **④ 2 次元 + B は、② 2 次元 + 未修正と完全一致**（マスク一致・値の最大差 **0.0**）
  → **将来 2 次元化したときの動きを一切変えない**
* **③ 1 次元 + B も、② と完全一致**（マスク一致・値の最大差 **0.0**）
  → **保存形式が 1 次元でも 2 次元でも、出てくる答えが同じになる**

> **B の性質: 出力が「データの保存され方」に依存しなくなる。**
> これは上流が移行の前後で結果の連続性を保ちたいはずの点と一致する。


A と B の差は**両端の縁の帯**（`+` が B と 2 次元だけが覆えた画素）:

```
行 0 |........................++++#############|
行 4 |.......................++++#############+|
行 9 |......................+++##############++|
        # = A でも覆える   + = B と 2 次元だけ   . = どちらも無効
```

### まだ確認していないこと

* **フル ctest（236/237）は未実行。** PR を出す前に必要
* 実データ（NISAR）での候補 B の再確認は未実施（候補 A では 31,228/156,420 を確認済み）
