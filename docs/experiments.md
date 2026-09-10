# 実験結果・検証済みの知見

**実測して確認できたことだけを書く。推測は書かない。**

3 つの文書の役割分担:

| ファイル | 役割 |
|---|---|
| `docs/STATUS.md` | 現在地・次の一手（**今どうなっているか**） |
| `logs/*.md` | その日に何が起きたかの記録。追記のみ（**どういう経緯だったか**） |
| **このファイル** | 検証を経て確定した知見（**何が言えるか**） |

各項目には**検証日**と**詳細のありか**を付ける。あとで「本当にそう言えるのか」を
たどれるようにするため。

---

## 使うときに引っかかる ISCE3 の仕様

- **時刻は `orbit.reference_epoch` からの経過秒数。** `Orbit` は
  コンストラクタで基準を先頭の状態ベクトル時刻に付け替える
- **LLH の順番は「経度・緯度・高度」で、角度はラジアン。** 緯度経度ではない
- **`DateTime` は TZ 指定子を受け付けない**（`Z` も `+00:00` も不可）。これが #255
- rdr2geo / geo2rdr は反復解法。解がなければ
  `RuntimeError: rdr2geo failed to converge` を投げる（黙って誤答は返さない）
- **granule 名の `PR` は「PROVISIONAL」ではなく処理種別**（nominal 生産）。
  成熟度は CRID の頭文字で分かる（BETA が `X`、PROVISIONAL が `P`）
- **GCOV は ISCE3 の出力であって入力ではない。** 動かすなら RSLC が要る
  （runconfig に `REQUIRED - One NISAR L1 RSLC formatted HDF5 file`）
- **実データの軌道は状態ベクトルが 11 点だけ**（10 秒間隔・100 秒分）。
  エルミート補間が前提なので、これで足りる
- **`polsar` は偏波処理一般ではない。** `symmetrize.h` 1 本で対称化のみ
- **公式プロダクトは自分を作った runconfig 全文を持っている。**
  `metadata/processingInformation/parameters/runConfigurationContents`。
  入力・DEM・TEC・軌道・ISCE3 のバージョンも記録されている
- **公式 GCOV は `mantissa_nbits: 16` で非可逆圧縮されている。** 比較時は設定を揃える
- runconfig の `processing.geocode.top_left` / `bottom_right` で**出力範囲を絞れる**

---

## 1. 幾何 API の実測（2026-08-27）

`core` / `geometry` を Python から叩いて、楕円体・軌道補間・rdr2geo / geo2rdr・
スワス断面を実測した。詳細は `logs/2026-08-27-first-run.md`。

| 測ったこと | 結果 |
|---|---|
| `Orbit` の参照エポック | **コンストラクタで先頭の状態ベクトル時刻に付け替わる。** 知らずに元のエポックで時刻を渡すと**地上で約 750 km ずれる** |
| 地上間隔と斜距離の関係 | **近距離ほど地上間隔が広い。** Δ地上 ≈ Δ斜距離 / sin(入射角) |
| geo2rdr の正常系 | 高精度で収束する（往復誤差が数値誤差の範囲） |

---

## 2. ビルドとテスト

### ctest の基準値の推移

| 日付 | 結果 | 所要 | 落ちたもの |
|---|---|---|---|
| 2026-08-23 | 235/237 | 608 秒 | `GeometryTest.GeoToRdr` / `nisar.workflows.stage_dem` |
| **2026-08-30** | **236/237** | 655 秒 | `nisar.workflows.stage_dem` のみ |

→ **2 件以上落ちたら自分の変更を疑う。**

### `GeoToRdr` の失敗は未初期化変数だった（2026-08-30 確定）

* 原因: `double aztime, slantRange;` が**未初期化のまま `geo2rdr` の反復初期値に渡っていた**
* upstream が 2026-08-24 に修正。手元では 2026-08-30 の再ビルドで**合格を確認**
* **「未定義動作（UB）の疑い」という推測は当たっていた。** UBSan 調査は不要になった
* ⚠️ **GCC 15.3 が新しすぎたせいではなかった。** 経緯は `logs/2026-08-23-test-failures.md`

### ⚠️ ctest の `DEPENDS` は順序を決めるだけ

前提テストを自動実行しない。**`-R` で絞ると前提が走らず落ちるものがある**
（`crossmul` / `geocode_insar` / `resample_slc` / `resample_slc_v2`）。
`workflows.gcov` には `DEPENDS` が無いので単独実行してよい。

---

## 3. NISAR 実データ（2026-08-30 取得）

詳細は `logs/2026-08-30-first-real-data.md`。

| 項目 | 実測値 |
|---|---|
| ダウンロード速度 | 約 7 MB/s（Step 1 は RSLC 214 MB + GCOV 323 MB） |
| 認証の関門 | **アカウント作成ではなく EULA**（アプリの認可と利用許諾は別） |
| `asf_search` の誤報 | 403 EULA 失敗を `Invalid/Expired token passed` と報告する |
| 同梱テストデータ | `~/isce3/tests/data/` に NISAR 形式 HDF5 が **38 個**。GCOV ワークフローが **6.8 秒**で通る |

---

## 4. 公式 GCOV の再現（2026-08-30）

**環境が正しいことの証明になった実験。** 公式プロダクトに埋め込まれた
`runConfigurationContents` から設定を写し、同じ RSLC から GCOV を作って比較した。

| 比較項目 | 結果 |
|---|---|
| **有効画素マスクの一致率** | **100.0000%** |
| 値の相対差（最大） | 1.46e-05 |
| 保存精度（`mantissa_nbits: 16`） | 2⁻¹⁶ = 1.53e-05 → **差は保存精度未満** |
| 処理時間 / メモリ | 100 秒 / 3.9 GB |

**言えないこと:** このシーンは**平坦な棚氷・単偏波 `VV`・周波数 B のみ**。
**地形補正と偏波の正しさは確かめられていない**（Step 2 が必要な理由）。

---

## 5. `referenceTerrainHeight` が全 NaN になる（2026-08-30 発見）

1 次元の LUT を 2 次元と誤判定して読み出しに失敗し、レイヤ全体が NaN になる。
**終了コードは 0。** 下書きと根拠は `drafts/`。

### データ自身の形（3 製品すべて 1 次元）

| 製品 | `referenceTerrainHeight` | 同居する `slantRange` | 判定式の答え |
|---|---|---|---|
| `tests/data/envisat.h5` | ndim=1 `(80,)` | `(240,)` | **2 次元**（誤り） |
| RSLC `028_152`（実データ） | ndim=1 `(79,)` | `(107,)` | **2 次元**（誤り） |
| RSLC `028_168`（実データ） | ndim=1 `(31,)` | `(105,)` | **2 次元**（誤り） |

`slantRange` は同居する 2 次元 LUT（`effectiveVelocity (80, 240)`）の軸であり、
RSLC ライタ自身が `require_lut_axes()` で**無条件に書き込む**。
→ **ISCE3 が作った RSLC では判定が正解を出しようがない。**

### GDAL からどう見えるか

```
referenceTerrainHeight → Size is 80, 1      ← エラー文の "raster of 80x1"
effectiveVelocity      → Size is 240, 80    ← 本物の 2 次元 LUT
```

### 観測される症状

| 項目 | 値 |
|---|---|
| テストの合否 | **合格**（5.64 秒・終了コード 0） |
| `Access window out of range` エラー | **4 回** |
| 1 次元経路の警告 `(az. vector)` | **0 回** ← 一度も入っていない |
| 同じ PR で入った `(rg. vector)` | **4 回**（crosstalk。こちらは動く） |
| `tests/` 内の `referenceTerrainHeight` 出現回数 | **0**（検証しているテストが無い） |

### 出力レイヤの状態

| 対象 | 有効画素 |
|---|---|
| `gcov_envisat_*.h5` の `referenceTerrainHeight` | **0 / 410** |
| 同ファイル `elevationAntennaPattern/HH` | 178 / 410 |
| 同ファイル `noiseEquivalentBackscatter/HH` | 178 / 410 |
| 公式 `GCOV_028_168`（0.25.16） | **0 / 156,420** |
| 公式 `GCOV_028_152`（0.25.16） | **0 / 111,531** |

### 経緯（git 履歴から。2026-09-10 調査）

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

### 修正案の検証（2026-09-10。`~/isce3` は書き換えず複製で検証し、毎回 md5 で復元確認）

**元のコードは 2 つの判断を 1 つの条件で兼ねていた。そこが誤りの本体。**

| 判断すること | 正しくは何で決まるか |
|---|---|
| 値を距離方向へ複製する必要があるか | **データセット自身の次元** |
| 距離軸として何を使うか | **`slantRange` があるかどうか** |

| 実行 | envisat の有効画素 |
|---|---|
| 未修正 | **0/410** |
| 候補 A（次元だけ判定） | 134/410 |
| **候補 B（軸も `slantRange` を使う）** | **178/410** |
| **2 次元入力 + 未修正**（目標値） | **178/410** |

🔴 **候補 B は 2 次元経路と完全一致**（マスク一致・値の最大差 0.0）。
`envisat.h5` の `referenceTerrainHeight` を `(80,)` → `(80, 240)` に作り替えて
**未修正コード**で走らせた結果と突き合わせて確認した。
上流には**将来 2 次元化する計画**があるので、**B は「2 次元化後と同じ結果を今出す」**ことになる。

A と B の差は**両端の縁の帯**。1 次元経路が距離軸を RSLC のレーダグリッドから
**21 点 + 余白 5 画素**で作り直し、LUT 本来の `slantRange`（240 点）より狭くなるため。

| 副作用の確認（候補 B） | 結果 |
|---|---|
| `Access window` エラー | 6 回 → **0 回**（GCOV 4 + GSLC 2） |
| GCOV / GSLC の科学データ | **ビット単位で不変** |
| 他のジオコード済みメタデータ層 | **変化なし** |
| crosstalk（レンジ方向 1 次元）経路 | `(rg. vector)` **4 回のまま**＝壊していない |
| テスト | **合格** |
| フル ctest（236/237） | ⚠️ **未実行**。PR 前に必要 |

※ 候補 A では実データでも確認済み（0/156,420 → **31,228/156,420**）。B の実データ再確認は未実施。

### 攻撃側から見直して確かめたこと（2026-09-10）

「他に詰められる点は無いか」を自分で潰した記録。

| 疑い | 検証結果 |
|---|---|
| 公式版 `0.25.16` に、そもそもこの判定式が入っていたのか | ✅ **入っている。**導入コミット `07a033f4f` は `v0.25.16` に含まれ、
該当ファイルは **`v0.25.16` と HEAD で完全に同一**（差分が空） |
| 公式プロダクトの NaN は別原因では | ✅ **同じジオグリッド上の他の層は埋まっている。**
028_152 は 10 層（10〜74%）、028_168 は 4 層が有効値を持ち、**`referenceTerrainHeight` だけが 0.00%** |
| `GDAL_MEM_ENABLE_OPEN=YES` に依存しているのでは | ✅ **外しても完全に同一**（エラー 4 回・`(az. vector)` 0 回・0/410 で合格） |
| `slantRange` は条件付きで書かれるのでは | ✅ **無条件。**`SLC.py` の `set_parameters()` 内で `require_lut_axes()` を条件なしで呼び、
軸は 2 次元の Doppler LUT から作られる |
| `tests/` に検証が増えたのでは | ✅ HEAD 時点でも **出現 0 件** |
| 影響範囲はどこまでか | ✅ `BaseL2WriterSingleInput` を継承するのは **`GcovWriter` と `GslcWriter` の 2 つだけ** |

🔴 **製品仕様 XML に定義があった**（`python/packages/nisar/products/XML/L2/nisar_L2_GCOV.xml:2654`）。

```xml
<real name="/science/LSAR/GCOV/metadata/processingInformation/parameters/referenceTerrainHeight"
      shape="dopplerCentroidShape" width="32">
  ... _FillValue="nan" ... units="meters">Reference terrain height as a function of map coordinates
```

* **仕様は「地図座標の関数」として定義している** → 埋まっているべき層であり、置き場所の間違いではない
* **形状は `dopplerCentroidShape`**（`dopplerCentroid` と同じ）。
  公式プロダクトでは **`dopplerCentroid` が 23〜30% 埋まり、`referenceTerrainHeight` は 0%**。
  **同じ形状・同じジオグリッドで、一方だけが空**
* `_FillValue="nan"` なので、**全 NaN は「有効値がどこにも無い」を意味する**

---

## 6. 環境が原因ではないことの検証（2026-09-04）

「自分の環境構築が誤っているだけでは？」を 3 通りで潰した。
詳細は `drafts/165-comment-証拠と再現手順.md`。

| 方法 | 内容 | 環境の関与 |
|---|---|---|
| A | **ISCE3 のビルドを使わず** h5py だけで判定式を評価 → 3 製品すべて誤判定 | ❌ しない |
| B | **自分が作っていない公式プロダクト**が同症状（0.25.16、他人の環境） | ❌ しない |
| C | **同一ファイル・同一実行**で他の 2 層は 178/410 埋まる | ❌ 切り分け済み |

あわせて環境の健全性も確認した。

* **実行されるファイルと読んだソースが md5 一致**（取り違えなし）
* `WITH_CUDA=OFF` / `GDAL_MEM_ENABLE_OPEN=YES` / ctest 236/237
* **2026-09-10 に `cmake --install` を実行し、インストール先をソース（`67bccb0ce`）と
  完全一致させたうえで再現を取り直した。結果は同一**
  （エラー 4 回・`(az. vector)` 0 回・`(rg. vector)` 4 回・出力 0/410 で合格）
  → **「ビルドが古いせいでは」という指摘の余地が無くなった**

**言えないこと:** GDAL は **3.13.3 でしか試していない**。
ただし要求サイズは ISCE3 側の計算なので GDAL に依存せず、B が別環境での発生を担保する。

---

## 7. 反証された推定（間違えたことの記録）

**推測で書いて外したものを残す。**同じ間違い方を繰り返さないため。

| 当初の推定 | 実際 | 判明日 |
|---|---|---|
| granule 名の `PR` は成熟度 PROVISIONAL | **処理種別**（nominal 生産）。成熟度は CRID の頭文字 | 2026-08-28 |
| `polsar` は偏波処理一般 | `symmetrize.h` 1 本で**対称化のみ** | 2026-08-28 |
| ファイル名の `N` は軌道暦の種別 | **反証。** `orbitType = MOE` に対しファイル名は `N` | 2026-08-30 |
| `GeoToRdr` の失敗は GCC 15.3 起因か最適化起因 | **未初期化変数**。UB の疑いのほうが当たっていた | 2026-08-30 |

---

## 8. まだ検証できていないこと

- **地形補正と偏波の正しさ**（Step 1 は平坦な棚氷・単偏波・周波数 B のみ）
- **Step 2 の定量比較**（データは `~/nisar-data/` に取得済み。有効画素マスクの一致率が未了）
- **numpy 2.x での挙動**（手元は 1.26.4 なので NEP 50 系のバグが見えない）
- **GPU (CUDA) 経路**（ビルドできないため一切触れていない）
- **信号処理側（`focus` / `signal`）**（一度も触っていない）
