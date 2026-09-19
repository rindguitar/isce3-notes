# 再現手順 — `referenceTerrainHeight` のジオコーディングが全 NaN になる

GCOV / GSLC を作ると、メタデータの
`metadata/processingInformation/parameters/referenceTerrainHeight` が
**全画素 NaN** になります。**処理は終了コード 0 で完了**し、
GDAL のエラーが数行出るだけなので気づきにくい問題です。

**NISAR の実データは不要です。**ISCE3 に同梱のテストデータだけで再現します。

---

## 確かめていただきたいこと

1. 入力データは **1 次元**（時刻ごとに 1 つの標高）であること
2. それなのにコードの判定が **「2 次元」** と答えること
3. その結果、出力レイヤが **全 NaN** になること

**経路 A（ビルド不要・1 分）**と**経路 B（ビルドあり・10 秒）**のどちらでも確認できます。
**A だけでも 1 と 2 は確認できます。**

---

## 経路 A: ビルド不要（`h5py` だけ）

ISCE3 のソースがクローンしてあれば実行できます。ビルドは要りません。

```bash
python3 - <<'PY'
import h5py

H5 = 'tests/data/envisat.h5'           # ← ISCE3 のリポジトリ直下から実行
G  = '/science/LSAR/SLC/metadata/processingInformation/parameters'

with h5py.File(H5, 'r') as f:
    # --- 1. データは何次元か ---
    d = f[f'{G}/referenceTerrainHeight']
    print(f'referenceTerrainHeight : ndim={d.ndim}  shape={d.shape}')
    print(f'同じグループの中身      : {sorted(f[G].keys())}')

    # --- 2. コードの判定式をそのまま写して評価する ---
    #     出典: nisar/products/writers/BaseL2WriterSingleInput.py
    LUT_1D_AZ_DATASETS  = ['referenceTerrainHeight']
    input_ds_name_list  = ['referenceTerrainHeight']
    slant_range_path    = f'{G}/slantRange'

    flag_luts_are_1d_az = (all([v in LUT_1D_AZ_DATASETS for v in input_ds_name_list])
                           and slant_range_path not in f)

    print(f'\n判定式の答え            : {"1 次元" if flag_luts_are_1d_az else "2 次元"}')
    print(f'実際                    : {d.ndim} 次元')
PY
```

**期待される出力:**

```
referenceTerrainHeight : ndim=1  shape=(80,)
同じグループの中身      : ['azimuthChirpWeighting', 'effectiveVelocity', 'frequencyA',
                          'rangeChirpWeighting', 'referenceTerrainHeight',
                          'slantRange', 'zeroDopplerTime']

判定式の答え            : 2 次元
実際                    : 1 次元
```

**ここが要点です。** 判定式は「同じグループに `slantRange` が**無い**か」で次元を決めています。
ところが `slantRange` は**隣の 2 次元データ（`effectiveVelocity (80, 240)`）の軸**として
常に置かれているため、**この判定は決して「1 次元」と答えません。**

---

## 経路 B: ビルドがある場合（`ctest`）

> ⚠️ **`pip install .` で入れた場合、この経路は使えません。**
> `ctest` はビルドディレクトリを必要としますが、pip ではそれが残らないためです。
> その場合は**経路 A だけ**で確認をお願いします（要点は A で確認できます）。

### B-1. GCOV のワークフローテストを実行する

**`--test-dir` には、`cmake -B` で指定したビルドディレクトリ**を渡します。
`CMakeCache.txt` が置かれている場所がそれです。

```bash
conda activate isce3

ctest --test-dir <ビルドディレクトリ> \
      -R '^test\.python\.pkg\.nisar\.workflows\.gcov$' --output-on-failure -V
```

**自分のビルドディレクトリが分からないときは、こう探せます。**

```bash
find ~ -maxdepth 3 -name CMakeCache.txt 2>/dev/null
# → 出てきたパスの「ディレクトリ部分」がビルドディレクトリ

# そのビルドがどのソースのものかも確認できる
grep -m1 CMAKE_HOME_DIRECTORY <ビルドディレクトリ>/CMakeCache.txt
# → CMAKE_HOME_DIRECTORY:INTERNAL=/path/to/isce3
```

> 💡 ビルドディレクトリの中で `ctest` を直接実行してもかまいません
> （`cd <ビルドディレクトリ> && ctest -R ...`）。`--test-dir` はそれを省く書き方です。

**期待される出力:**

```
ERROR 5: tmpXXXXXXXX.vrt, band 1: Access window out of range in RasterIO().
Requested (11,30) of size 229x20 on raster of 80x1.       ← 4 回出る
...
1/1 Test #212: test.python.pkg.nisar.workflows.gcov ...   Passed    5.64 sec
100% tests passed
```

> ⚠️ **エラーを 4 回出しながら「合格」します。** 終了コードは 0 です。
> `raster of 80x1` が、1 次元データを画像として開いた姿です。
>
> 💡 **テスト番号（`#212`）と所要秒数は環境で変わります。**見るべきは
> **「`Access window out of range` が 4 回」「それでも合格」「終了コード 0」**の 3 点です。

### B-2. 出力プロダクトを開く

テストの作業ディレクトリに出力が残ります。

```bash
cd <ビルドディレクトリ>/tests/python/packages/nisar/workflows/
```

```bash
python3 - <<'PY'
import h5py, numpy as np

F = 'gcov_envisat_area_noise_correction_false.h5'
P = '/science/LSAR/GCOV/metadata/processingInformation/parameters/referenceTerrainHeight'

with h5py.File(F, 'r') as h:
    a = h[P][()]
    print(f'{P.split("/")[-1]}: shape={a.shape}  有効 {int(np.isfinite(a).sum())}/{a.size}')

    # 同じ地図格子に載る他の層と比べる（こちらは埋まっている）
    for name in ['calibrationInformation/frequencyA/elevationAntennaPattern/HH',
                 'calibrationInformation/frequencyA/noiseEquivalentBackscatter/HH']:
        b = h[f'/science/LSAR/GCOV/metadata/{name}'][()]
        print(f'  （比較）{name.split("/")[-2]}: 有効 {int(np.isfinite(b).sum())}/{b.size}')
PY
```

**期待される出力:**

```
referenceTerrainHeight: shape=(10, 41)  有効 0/410
  （比較）elevationAntennaPattern: 有効 178/410
  （比較）noiseEquivalentBackscatter: 有効 178/410
```

> **同じ地図格子に載る他の層は埋まっていて、この層だけが 0 です。**

### B-3（任意）. GDAL からどう見えているか

```bash
gdalinfo 'HDF5:"tests/data/envisat.h5"://science/LSAR/SLC/metadata/processingInformation/parameters/referenceTerrainHeight'
#   Size is 80, 1      ← エラー文の "raster of 80x1" と一致

gdalinfo 'HDF5:"tests/data/envisat.h5"://science/LSAR/SLC/metadata/processingInformation/parameters/effectiveVelocity'
#   Size is 240, 80    ← 本物の 2 次元 LUT はこう見える
```

---

## つまずきやすい点

| | |
|---|---|
| `cmake: command not found` | **`conda activate isce3` を先に。** cmake は conda 環境の中にあります（`apt` で入れないこと） |
| `import isce3` が通らない | 同上。activate フックが `PYTHONPATH` を通します |
| テスト出力が見つからない | 出力はテストの**作業ディレクトリ**（`<build>/tests/python/packages/nisar/workflows/`）に出ます |
| 他のテストを `-R` で絞ったら落ちた | ctest の `DEPENDS` は**順序を決めるだけ**で前提テストを自動実行しません。<br>ただし **`workflows.gcov` に `DEPENDS` は無い**ので単独実行して問題ありません |
| インストールが古い可能性 | `cmake --install <ビルドディレクトリ>` で揃います（C++ が未変更なら再ビルド不要） |
| ビルドディレクトリが分からない | `find ~ -maxdepth 3 -name CMakeCache.txt` で探せます（B-1 参照） |
| `pip install .` で入れている | **経路 B は使えません**（ビルドツリーが残らないため）。経路 A をお使いください |

---

## 確認できたら言えること

* **入力は 1 次元**（仕様どおり）
* **判定式は「2 次元」と答える**（データではなく、隣に何が置いてあるかで判定しているため）
* **出力は全 NaN**。しかも**同じ格子の他の層は埋まっている**ので、
  ジオコーディング基盤の問題ではなく、この層に固有

**なお、この症状は手元だけの話ではありません。**
ASF が配布している公式 GCOV プロダクトでも同じレイヤが全 NaN です
（有効値 0/156,420 と 0/111,531、`softwareVersion = 0.25.16`）。

---

## もっと詳しい根拠

* **証拠のすべて**: `docs/experiments.md`
  （環境要因を 3 通りで潰した記録、経緯、修正案 A / B の実測）
* **仕組みの説明**: `docs/referenceTerrainHeight-解説.md`（①〜⑥ の順）
* **概念**: wiki の
  [参照地形高](https://github.com/rindguitar/isce3-notes/wiki/Reference-Terrain-Height)
