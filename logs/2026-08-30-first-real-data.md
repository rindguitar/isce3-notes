# 2026-08-30 NISAR の実データを初めて取得した

**衛星が実際に観測したデータを落とし、ISCE3 で開いて中身を確認した回。**
あわせて、同梱のテストデータだけで NISAR ワークフローが動くことも分かった。

## 今日のゴール

「実データを 1 シーン取得し、ISCE3 で読めるところまで確認する」。

前提として、着手先の候補だった約 40 件の issue（NISAR プロダクトの仕様適合系）は
**実データが無いと確認すらできない**状態で止まっていた。そこを開ける回。

## 1. どのデータを選んだか

### なぜ RSLC と GCOV を「対で」取るのか

最初は「GCOV を 1 シーン見れば十分」と考えていたが、これは誤りだった。

**ISCE3 は GCOV を作る側であって、GCOV を入力に取らない。**
runconfig にそのまま書いてある。

```yaml
# ~/isce3/share/nisar/defaults/gcov.yaml
input_file_group:
    # REQUIRED - One NISAR L1 RSLC formatted HDF5 file
    input_file_path:
```

つまり GCOV だけ落としても「眺める」だけで終わる。動かすなら入口の **RSLC** が要る。
そのうえで同じ観測から作られた**公式の GCOV** も持っておくと、
自分の出力と数値で突き合わせられる。一致すれば環境が正しい証明になり、
食い違えばそれ自体がバグの候補になる。

配布元では RSLC と GCOV が**同じ granule 名で対になっている**（プロダクト種別の
4 文字を差し替えるだけ）ので、片方を見つければもう片方も引ける。

### 選定の過程

検索 API（CMR）で実在する granule を 200 件以上引き、サイズと観測モードを実測した。

| 分かったこと | |
|---|---|
| 日本上空の RSLC | **最小でも 14 GB、最大 25 GB** |
| その理由 | 陸域は 20/40 MHz・2 偏波が既定。高分解能なので必然的に大きい |
| 世界最小クラス | 5 MHz 単偏波・部分フレームなら 200 MB 台 |

日本は初回には重すぎるので外した。2 段構えにした。

| | granule | サイズ | 目的 |
|---|---|---|---|
| Step 1 | `NISAR_L1_PR_RSLC_028_168_D_126_0005_NASV_A_20260824T211408_20260824T211412_P05023_N_P_J_001` | 214 MB | 配線確認 |
| | 同名の `L2_PR_GCOV` | 323 MB | 対の公式出力 |
| Step 2 | `NISAR_L1_PR_RSLC_028_152_A_156_2005_DHDH_A_20260823T185248_20260823T185253_P05023_N_P_J_001` | 2327 MB | 本命（未取得） |
| | 同名の `L2_PR_GCOV` | 434 MB | 同上 |

**今日取得したのは Step 1 のみ**（計 537 MB）。南極、南緯 76°。
5 MHz の単偏波なので絵としては面白くないが、狙いは「落とせるか・開けるか」の確認と、
**実際の軌道とレーダグリッドを手に入れること**。メタデータの構造は大きいシーンと同じ。

Step 2 をニュージーランド南島（サザンアルプス）にしたのは、
**急峻な地形ほどレイオーバーが強く出て幾何のバグが表面化しやすい**ため。

## 2. つまずいた点: アカウントを作るだけでは落とせない

**今回いちばん時間を使ったところ。** 記録に残す価値がある。

Earthdata Login のアカウントを作り、ユーザトークン（JWT、有効 60 日）を発行しても、
`asf_search` は次のように言って通らなかった。

```
ASFAuthenticationError: Invalid/Expired token passed
```

**このメッセージが誤り。** トークンは有効だった。JWT をデコードして確認したところ、
発行 8 分前・期限は 2 か月先。検証エンドポイントを直接叩いたら本当の理由が出た。

```json
{"status_code":403,
 "error_description":"EULA Acceptance Failure",
 "resolution_url":"https://urs.earthdata.nasa.gov/approve_app?client_id=BO_n7nTIlMljdvU6kRRB3g"}
```

**配布元アプリの認可と利用許諾への同意が別途必要だった。**
`resolution_url` を開いて承認したら即座に通った。

原因は `asf_search` の実装。ステータスコードも `error_description` も
`resolution_url` も握り潰して、一律「トークンが不正」と報告している。

```python
# asf_search/ASFSession.py
if not 200 <= response.status_code <= 299:
    if not self._try_legacy_token_auth(token=token):
        raise ASFAuthenticationError('Invalid/Expired token passed')
```

**これは改善提案の issue を立てる価値がある**（ISCE3 ではなく
[asf_search](https://github.com/asfadmin/Discovery-asf_search) 側）。
サーバが解決方法の URL まで返しているのに捨てているので、利用者は原因に辿り着けない。

## 3. 実際に走らせた手順

### 前提

```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate isce3
```

`asf_search`（12.3.1）は isce3 環境に既に入っていた。

### 認証

トークンは `~/.edl_token`（権限 600）に置いた。`~/.netrc` は作っていない。
`asf_search` の認証は `auth_with_token` / `auth_with_creds` / `auth_with_cookiejar` の
3 通りで、`~/.netrc` は必須ではない。

> **なぜトークンにしたか**: パスワードを平文でディスクに残さずに済み、
> 後から失効させられるため。

### 取得

保存先は `~/nisar-data/`。**`~/isce3` の外**（fork を汚さないため）。

```python
import asf_search as asf, pathlib
tok = (pathlib.Path.home()/".edl_token").read_text().strip()
sess = asf.ASFSession().auth_with_token(tok)

res = asf.granule_search(["NISAR_L1_PR_RSLC_028_168_D_126_0005_NASV_A_..."])
url = res[0].properties["url"]
with sess.get(url, stream=True) as r:
    ...  # 1 MB ずつ .part に書き、完了時にリネーム
```

書き込み中は `.part` 拡張子にして、完了時にリネームした。
途中で止まっても不完全なファイルを本物と誤認しない。

**実測: 約 7 MB/s。** RSLC 214 MB が 31 秒、GCOV 323 MB が 45 秒。
この速度なら Step 2 の 2.8 GB は 7 分程度。

### 開く

```python
from nisar.products.readers import open_product
p = open_product("NISAR_L1_PR_RSLC_....h5")   # reader: RSLC
```

## 4. 確認できたこと

### ファイル名の全フィールドがメタデータと一致した

ISCE3 のソースに granule ID のテンプレートが書かれている
（`nisar/products/writers/BaseWriterSingleInput.py` の docstring）。

```
NISAR_IL_PT_PROD_CYL_REL_P_FRM_{MODE}_{POLE}_S_{StartDateTime}_{EndDateTime}_CRID_A_C_LOC_CTR.EXT
```

実データの `/science/LSAR/identification` と突き合わせた。

| 記号 | ファイル名 | メタデータ | |
|---|---|---|---|
| `PT` | `PR` | `processingType = PR` | ✅ |
| `REL` | `168` | `trackNumber = 168` | ✅ |
| `P` | `D` | `orbitPassDirection = Descending` | ✅ |
| `FRM` | `126` | `frameNumber = 126` | ✅ |
| `MODE` | `0005` | `listOfFrequencies = ['B']`、帯域 5.0 MHz | ✅ |
| `POLE` | `NASV` | 周波数 A なし、`frequencyB` の偏波 `['VV']` | ✅ |
| `CRID` | `P05023` | `compositeReleaseId = P05023` | ✅ |
| `C` | `P` | `isFullFrame = False` | ✅ |
| `LOC` | `J` | `processingCenter = J` | ✅ |

**帯域モードの 4 桁は「周波数 A の帯域 + 周波数 B の帯域」（MHz）**で、
`00` はその周波数を使っていないことを表す。`0005` は「A なし + B が 5 MHz」。
偏波の 4 文字も同じく 2 文字ずつで、`NA` が「その周波数が存在しない」。
**モードの `00` と偏波の `NA` は必ず同時に立つ**（ISCE3 の同じ `if` 文で書かれている）。

### `PR` は「PROVISIONAL」ではなかった

コレクション名が `..._PROVISIONAL_V1` なので成熟度だと思い込んでいたが、
**処理種別**だった（`PR` = nominal 生産 / `OD` = 随時処理）。
BETA コレクションの granule も `PR` を持っている。
成熟度の違いは **CRID の頭文字**に出ていた（BETA が `X`、PROVISIONAL が `P`）。

### 実データの軌道

| | |
|---|---|
| 状態ベクトル | **11 点だけ** |
| 間隔 | 10 秒 |
| 時間範囲 | 100 秒分（観測は 4 秒間） |
| 補間方法 | `Hermite` |
| 軌道暦の種別 | `MOE`（中精度） |
| 地心距離 | 7136.5 km（高度およそ 780 km） |

点が 11 個で足りるのは**エルミート補間が前提**だから。位置と速度の両方を使うので、
位置だけの補間より少ない点で精度が出る。

## 5. 反証したこと

granule 名の CRID の次に `N` / `F` / `P` という 1 文字がある。
`NOE` / `FOE` / `POE`（軌道暦の種別）の頭文字と一致するので、
そう推定して wiki に書いていた。**実物で否定された。**

```
metadata/orbit/orbitType   = MOE   ← 軌道暦は MOE
ファイル名の該当フィールド = N     ← M ではない
```

一致しないので、この位置は軌道暦の種別ではない。wiki を「不明」に戻した。

> **教訓**: 推定を書くときは「どの値を見れば否定できるか」を一緒に書いておくと、
> 実物が手に入ったときに一発で片が付く。今回まさにそれで決着した。

なお ISCE3 はこのフィールドを埋めていない。`{MODE}` `{POLE}` `{C}` と日時だけを
差し替え、残りは runconfig の `partial_granule_id` に入った状態で渡ってくる。
**値を決めているのは ISCE3 の外側**なので、このリポジトリからは追えない。

## 6. 副産物: データを落とさなくてもワークフローは動いた

調べる過程で、**`~/isce3/tests/data/` に NISAR 形式の HDF5 が 38 個入っている**
ことが分かった（git が直接追跡。git-lfs ではない。合計 210 MB）。
つまり clone した時点で手元にある。

GCOV ワークフローのテストを 1 件だけ走らせたところ **6.8 秒で通った。**

```bash
ctest --test-dir ~/isce3-build -R '^test\.python\.pkg\.nisar\.workflows\.gcov$' --output-on-failure
```

入力は `winnipeg.h5`（UAVSAR、2012 年、航空機搭載）と `envisat.h5`（ESA の Envisat）を
NISAR の RSLC 形式に入れたもの。**NISAR 衛星の観測ではない。**
出力の GCOV は 16 MB、`grids/frequencyA/HHHH` が 108×68 の float32。

生成された granule ID は
`NISAR_L2_PR_GCOV_105_091_D_006_2000_SHNA_A_...` で、
`2000_SHNA` = 「周波数 A が 20 MHz の単一 HH、周波数 B なし」。
上で確認した命名規則どおりだった。

| やりたいこと | テストデータで足りるか |
|---|---|
| ワークフローの動作を見る・コードを追う | **足りる** |
| 仕様適合系の約 40 issue を確認する | **足りない**（実プロダクトの階層が要る） |
| 公式 GCOV と自分の出力を突き合わせる | **足りない**（対の公式出力が無い） |

## 7. 残っていること

- **Step 2（ニュージーランド、2.8 GB）は未取得。** 約 7 分で落ちる見込み
- **自分で GCOV を作って公式 GCOV と比較する**のはまだやっていない。
  DEM は ASF の `NISAR_DEM`（1°タイル 3 MB、公式と同じ修正版 Copernicus DEM）を使う予定
- 実軌道・実レーダグリッドでの `rdr2geo` / `geo2rdr` の再走も未着手
- `asf_search` のエラーメッセージ改善の issue も未起票
- granule 名の `S`（値 `A`/`M`）は未確定。`isMixedMode` と整合したが、
  `M` の実物をまだ見ていない

## 参考

- 取得手順の詳細: wiki の [NISAR データの取得](https://github.com/rindguitar/isce3-notes/wiki/NISAR-Data-Access)
- 命名規則: wiki の [granule の命名規則](https://github.com/rindguitar/isce3-notes/wiki/Granule-Naming)
- 軌道暦: wiki の [軌道暦](https://github.com/rindguitar/isce3-notes/wiki/Orbit-Ephemeris)
- 処理の連鎖: wiki の [処理レベルの連鎖](https://github.com/rindguitar/isce3-notes/wiki/Processing-Chain)

---

# 追記: Step 1 の中身を精査した

取得しただけで中身を見ていなかったので、両ファイルを開いて数値を洗った。

## 観測諸元（RSLC / frequencyB）

| 項目 | 値 |
|---|---|
| 中心周波数 | 1221.5 MHz（**L バンド**） |
| 帯域 | 5.0 MHz（取得・処理とも同じ） |
| 偏波 | `VV` 1 つだけ |
| パルス繰り返し周波数 | 1911.44 Hz |
| 処理方位帯域 | 1256.37 Hz |
| サブスワス数 | 1 |
| 斜距離 | 918.41 〜 1076.90 km（6345 点） |
| 斜距離間隔 | 24.983 m |
| 方位時刻間隔 | 0.000658 秒 |
| 画像 | 7600 × 6345 の `complex64`、gzip 圧縮、チャンク 512×512 |

非圧縮なら 0.39 GB のところ、ファイルは 214 MB。gzip が効いている。

## シーンの実寸

| 方向 | 画素数 | 画素間隔 | 実寸 |
|---|---|---|---|
| 方位（衛星の進行方向） | 7600 | 4.42 m | **33.6 km** |
| 地上距離 | 6345 | 37.73 m | **239.4 km** |

面積 **8042 km²**。**幅 239 km に対して長さ 34 km** という、横に長い短冊。

観測時間が 5 秒しかないため方位方向が短い。これが granule 名の `C = P`
（部分フレーム）の正体で、`isFullFrame = False` とも一致する。
一方 239 km という幅は NISAR のスワス幅そのもの。

## 幾何: wiki の式を実データで検算できた

入射角はシーン内で **33.89° 〜 47.86°** と大きく変わる。

| | 入射角 |
|---|---|
| 近距離側 | 34.48° |
| 遠距離側 | 47.48° |

wiki の[ジオコーディング](https://github.com/rindguitar/isce3-notes/wiki/Geocoding)に
**Δ地上 ≈ Δ斜距離 / sin(入射角)** と書いてあるので、実データで検算した。

```
斜距離間隔 24.983 m / 地上間隔 37.732 m
→ 式から逆算した入射角  : 41.46°
→ シーン中央の実測入射角: 41.90°
                    差  : 0.44°
```

**合っている。** さらに「地上間隔は近距離ほど広い」という
（直感に反する）性質もこのデータで裏付けられる。

| | 入射角 | 地上間隔 = 24.983 / sin |
|---|---|---|
| 近距離側 | 34.48° | **44.1 m** |
| 遠距離側 | 47.48° | **33.9 m** |

近距離のほうが 3 割ほど粗い。

`metadata/geolocationGrid` には入射角・視線ベクトル・地上速度などが
**(20, 86, 328) の 3 次元**（高度 20 層 × 方位 86 × 距離 328）で入っている。
高度方向を持っているのは、地形の高さによって見える位置が変わるため。

## GCOV の中身

| 項目 | 値 |
|---|---|
| 格子 | 4923 × 4932 |
| 画素間隔 | **80 m** |
| 投影 | **EPSG:3031**（南極極立体投影） |
| 共分散項 | `VVVV` **1 つだけ** |
| 外接矩形 | 394 km × 394 km |

画素間隔 80 m は wiki の「GCOV は帯域により 10 / 20 / 80 m」と一致する
（5 MHz なので最も粗い 80 m）。

### 有効画素が 5.0% しかない

**これが実データを見て初めて分かったこと。**

```
外接矩形    : 155,330 km²
有効画素面積:   7,837 km²  (5.0%)
```

理由は単純で、**斜めに走る細長い短冊を、軸に平行な矩形の格子に収めている**から。
南極極立体投影の格子に対してシーンが斜めなので、外接矩形の大半が空になる。

有効画素の面積 7,837 km² は、RSLC から計算したシーン実寸 8,042 km² と
**差 3%** で一致する。別々の経路で出した数字が合うので、読み方は正しい。

`mask` の内訳も同じことを言っている。

| 値 | 割合 | 意味 |
|---|---|---|
| 255 | 95.0% | 無効 |
| 1 | 4.9% | サブスワス 1 の有効画素 |
| 0 | 0.1% | — |

`mask` の説明文には「**完全に合焦したレーダ画素からのみ生成された場合に限り有効**とする。
平均に使う画素が 1 つでも部分合焦か無効なら、その出力画素は無効」とある。端の扱いが厳しい。

### 後方散乱の値

| | 値 |
|---|---|
| 線形値の中央値 | 0.0295 |
| **dB 換算** | **−15.30 dB** |
| 範囲（線形） | 8.3e-05 〜 3.19 |

`numberOfLooks` は中央値 **39.7**。80 m 四方の出力画素 1 つを作るのに、
レーダ画素をおよそ 40 個平均していることになる。検算すると
80×80 m ÷ (37.73 m × 4.42 m) ≈ 38.4 で、これも合う。

## 数字が互いに整合した

別経路で出した値が一致することを 3 箇所で確認できた。

| 突き合わせ | 結果 |
|---|---|
| 斜距離／地上間隔の比 vs 実測入射角 | 41.46° vs 41.90°（差 0.44°） |
| RSLC のシーン実寸 vs GCOV の有効画素面積 | 8,042 km² vs 7,837 km²（差 3%） |
| 出力画素／入力画素の面積比 vs `numberOfLooks` | 38.4 vs 39.7 |

**読み方を間違えていない**ことの裏付けになる。

## Step 1 で分かること・分からないこと

| | |
|---|---|
| **分かる** | プロダクトの階層構造、メタデータの持ち方、幾何の値、命名規則の照合 |
| **分かる** | 取得から ISCE3 で開くまでの経路が通ること |
| **分からない** | 偏波の共分散まわり（項が `VVVV` 1 つしかなく、交差項も対称化も出てこない） |
| **分からない** | 周波数 A の経路（このシーンは B のみ） |
| **分からない** | 起伏のある地形での挙動（南極の氷上で、しかも 80 m 間隔） |
