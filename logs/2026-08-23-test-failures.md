# 2026-08-23 ctest の失敗 7 件を切り分け

CMake 直叩きビルドに移行して `ctest` を初めて実行した結果、
**237 件中 230 件成功、7 件失敗**（613 秒）。その切り分け記録。

`docs/buildinstall.md` は「多数のテストが失敗するなら Python パッケージ不足か設定ミス」
と書いているが、7 件はそれに当たらない。個別の原因を持つ失敗として扱った。

## 結果サマリ

| # | テスト | 原因 | 状態 |
|---|---|---|---|
| 5 | `cxx.isce3.container.rsd` | GDAL 3.13 の仕様変更 | ✅ 解決 |
| 85 | `cxx.isce3.io.gdal.gdal-raster` | 同上 | ✅ 解決 |
| 120 | `python.pybind.io.gdal.raster` | 同上 | ✅ 解決 |
| 138 | `python.pybind.geometry.pntintersect` | pybind11 3.x で Eigen 派生型のキャスタが効かない | 🔍 未解決 |
| 41 | `cxx.isce3.geometry.geometry` | 数値収束の失敗 | 🔍 未解決 |
| 211 | `python.pkg.nisar.workflows.stage_dem` | **upstream のバグ**（環境と無関係） | ⚠️ 対処不要 |
| 165 | `python.pkg.isce3.io.background` | flaky（再実行で成功） | — |

`GDAL_MEM_ENABLE_OPEN=YES` を設定すれば **233/237 成功**する状態。開発を始めるには十分。

## 切り分けに使ったコマンド

```bash
# 前回失敗したものだけ再実行（613秒の全実行を繰り返さずに済む）
ctest --test-dir ~/isce3-build --rerun-failed --output-on-failure --timeout 120
```

`--timeout 120` は 1 テストあたりの上限。ネットワーク待ちでハングするテストへの保険。

---

## 原因1: GDAL の `MEM:::DATAPOINTER=` 廃止 ← 3 件（解決済み）

```
ERROR 1: Opening a MEM dataset with the MEM:::DATAPOINTER= syntax is no longer
supported by default for security reasons. If you want to allow it, define the
GDAL_MEM_ENABLE_OPEN configuration option to YES, or build GDAL with the
GDAL_MEM_ENABLE_OPEN compilation definition
```

GDAL が**生のメモリポインタを指定してデータセットを開く構文を、セキュリティ上の理由で
既定で無効化**した。ISCE3 はこの構文を使っている。

エラーメッセージ自体が対処法を案内しており、そのとおりで解決した。

```bash
GDAL_MEM_ENABLE_OPEN=YES ctest --test-dir ~/isce3-build -R 'container\.rsd|io\.gdal'
# → 100% tests passed out of 9
```

**`environment.yml` に上限がない問題の 3 例目**（`gdal>=3.6` に対し 3.13.3 が入っている）。
Eigen 5.0.1、HDF5 2.x に続く。

### 対処

`$CONDA_PREFIX/etc/conda/activate.d/isce3-dev.sh` に追加する。

```bash
export GDAL_MEM_ENABLE_OPEN=YES
```

> この変数は GDAL が意図的に無効化した機能を再有効化する。
> ただしポインタは自プロセス内で生成したものなので、ローカルの開発・テストでは問題ない。
> 本番環境で常用する類のものではない、という位置づけ。

---

## 原因2: `pntintersect` — Eigen 派生型のキャスタが効かない 🔍

```
TypeError: slantrange_from_lookvec(): incompatible function arguments.
The following argument types are supported:
    1. (pos: isce3::core::Vector<3, double>, lkvec: isce3::core::Vector<3, double>,
        ellips: isce3.ext.isce3.core.Ellipsoid = WGS84) -> float

Invoked with: array([-2434576.30959459, -4820687.17249525, 4646675.11971689]),
              array([-0.29242685, 0.70723831, -0.6436618])
```

### 調べて分かった事実

**(1) `Vec3` は Eigen 型そのものではなく、Eigen の派生クラス**

`cxx/isce3/core/Vector.h:13`:

```cpp
template<int N, typename T>
class Vector : public Eigen::Matrix<T, N, 1> {
```

`cxx/isce3/core/forward.h:49`: `using Vec3 = Vector<3>;`

**(2) エラー表示が型ごとに違う**

- `pos` / `lkvec` → **生の C++ 型名** `isce3::core::Vector<3, double>` で表示
  = pybind11 がこの型の変換器を見つけられていない
- `ellips` → `isce3.ext.isce3.core.Ellipsoid` と Python 型名で表示
  = そちらは正常に登録されている

**(3) 同じファイルの隣の関数は成功している**

`test_sr_pos_from_lookvec_dem` は同じ `self._sc_pos_ecef` を渡して**成功**する。
C++ 側のシグネチャも同一（`cxx/isce3/geometry/geometry.h:281, 316`）:

```cpp
double slantRangeFromLookVec(const isce3::core::Vec3& pos,
        const isce3::core::Vec3& lkvec,
        const isce3::core::Ellipsoid& ellips = {});

std::pair<int, double> srPosFromLookVecDem(double& sr,
        isce3::core::Vec3& tg_pos, isce3::core::Vec3& llh,
        const isce3::core::Vec3& sc_pos, const isce3::core::Vec3& lkvec, ...);
```

**(4) 違いは束縛の書き方だけ**

`python/extensions/pybind_isce3/geometry/pntintersect.cpp`:

| 関数 | 束縛方法 | 結果 |
|---|---|---|
| `slantrange_from_lookvec` (19行目) | **関数ポインタ** `&geom::slantRangeFromLookVec` | ❌ 失敗 |
| `sr_pos_from_lookvec_dem` (60行目) | **ラムダ** `[](const Vec3_t& sc_pos, ...)` | ✅ 成功 |

同ファイル 3 行目に `#include <pybind11/eigen.h>` はある。

### 仮説

**pybind11 3.1.0 が、関数ポインタ経由の引数型推論では
`Eigen::Matrix` の派生クラスを Eigen 型として検出できていない。**
ラムダ経由では検出できている。

`environment.yml` の指定は **`pybind11>=2.5` で上限なし**。
つまりこれも上限なし問題の 4 例目。

### 検証方法（未実施）

```bash
conda install -n isce3 'pybind11<3'
# → 再ビルド（15〜40分）して pntintersect が通るか確認
```

pybind11 はヘッダオンリーのビルド時依存なので、**降格には再ビルドが必要**。

---

## 原因3: `GeometryTest.GeoToRdr` — 数値収束の失敗 🔍

```
tests/cxx/isce3/geometry/geometry/geometry.cpp:143: Failure
Expected equality of these values:
  stat / Which is: 0
  1
```

143 行目は `geo2rdr` の戻り値チェック（`1` = 収束、`0` = 収束せず）。
呼び出し側（137〜139 行目）:

```cpp
int stat = isce3::geometry::geo2rdr(llh, ellipsoid, orbit, doppler, aztime,
        slantRange, swath.processedWavelength(), lookSide, 1.0e-10, 50, 10.0);
```

**収束閾値 `1.0e-10`、最大 50 反復。** かなり厳しい。

同じテストスイート内の `RdrToGeoWithOrbit`（閾値 `1.0e-8`）は成功しているので、
計算全体が壊れているわけではなく、**この閾値に届かない**という話。

### 仮説

**GCC 15.3 の最適化による浮動小数点演算の差。**
FMA の縮約などで最終桁が変わり、`1e-10` に収束しなくなっている可能性。

環境の GCC は 15.3.0（`environment.yml` の `cxx-compiler` に版指定がないため最新が入った）。
これも上限なし問題の系統。

### 検証方法（未実施）

```bash
# 別ディレクトリに Debug ビルドを作って比較する（既存ビルドを壊さない）
cmake -S ~/isce3 -B ~/isce3-build-debug -G Ninja \
  -DISCE3_FETCH_DEPS=OFF -DWITH_CUDA=OFF -DCMAKE_BUILD_TYPE=Debug
```

Debug で通れば最適化起因と確定する。`-ffp-contract=off` を足して切り分ける手もある。

---

## 原因4: `stage_dem` — upstream のバグ（環境と無関係）

```
poly, bbox_epsg = determine_polygon(opts.product, opts.bbox, opts.bbox_epsg)
E  AttributeError: 'Namespace' object has no attribute 'bbox_epsg'
```

テストが `argparse.Namespace` を組み立てる際に `bbox_epsg` を渡していないのに、
呼ばれる側の `main()` がそれを参照している。
**コード側に引数が追加された際にテストが追随していない**、典型的な取り残し。

5 件中 5 件がこの理由で失敗し、`test_dateline_crossing` と `test_point2epsg` は成功している。

**`develop` を clone した誰でも再現する。環境の問題ではないので手を出さない。**
upstream に既知の issue がある可能性が高い。

## 原因5: `io.background` — flaky

初回失敗、再実行で成功。タイミング依存。環境の問題ではない。

---

## 次の一手

1. `GDAL_MEM_ENABLE_OPEN=YES` を activate フックに追加する（確定した対処）
2. 原因2の検証: `pybind11<3` に降格して再ビルド
3. 原因3の検証: Debug ビルドで比較
4. 原因4・5 は対処しない

**優先度は低い。** 残る 2 件は、いま触ろうとしている領域と無関係なら後回しでよい。
`GDAL_MEM_ENABLE_OPEN=YES` さえ設定すれば 233/237 通る。

## この日の教訓

`environment.yml` に上限指定がない問題が、**4 つの依存で連続して顕在化した**。

| 依存 | 入った版 | 症状 |
|---|---|---|
| eigen | 5.0.1 | ビルドが通らない（初期構築時） |
| gdal | 3.13.3 | GDAL 関連テスト 3 件が失敗 |
| pybind11 | 3.1.0 | 型変換テスト 1 件が失敗（仮説） |
| cxx-compiler (gcc) | 15.3.0 | 数値収束テスト 1 件が失敗（仮説） |

**何か壊れたら、まず依存のメジャーバージョンを疑う。**
根本的に避けるなら、[pinned な conda spec file](../reference/runtime-and-packaging.md) への
乗り換えを検討する。
