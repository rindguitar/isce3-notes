# STATUS

最終更新: 2026-08-30（セッション終了時に必ず更新）

## 現在のフェーズ

**環境構築 完了 → API を一度動かした → issue 調査 完了 → 実データ取得 完了 → 比較の準備中。**

**2026-08-30: NISAR の実データを初めて取得した。** これで仕様適合系の約 40 件が射程に入った。
**2026-08-28: `~/isce3` のソース読み取りが全面許可された**（書き換えは毎回確認）。

方針は定まった。ISCE3 の専門分野は未学習のため、
**issue にある問題の対処と、バグを発見して issue を立てるのがメイン。**

## 前回やったこと

2026-08-30: **NISAR の実データを初取得。** 詳細は `logs/2026-08-30-first-real-data.md`

- Step 1（南極・RSLC 214MB + GCOV 323MB）を `~/nisar-data/` へ取得。**約 7 MB/s**
- **関門はアカウント作成ではなく EULA。** アプリの認可と利用許諾への同意が別途要る。
  この状態で `asf_search` は `Invalid/Expired token passed` と誤報する（実体は 403 EULA 失敗）
- ファイル名の全フィールドを実データの `identification` と照合。命名規則が確定した
- **軌道暦の種別だという推定は反証**（`orbitType = MOE` に対しファイル名は `N`）
- 副産物: **`~/isce3/tests/data/` に NISAR 形式の HDF5 が 38 個**あり、
  ダウンロード無しで GCOV ワークフローが 6.8 秒で通る（ただし UAVSAR / Envisat 由来）
- 認証は `~/.netrc` ではなく**ユーザトークン**（`~/.edl_token`、権限 600）にした

2026-08-28: **NISAR 実データの取得先を決め、wiki をソースで裏取りした。**

- **落とすものを決めた: L1 RSLC を主、同じ granule の L2 GCOV を答え合わせ用に対で取る。**
  GCOV は ISCE3 の出力なので、GCOV だけでは「動かした」ことにならない
  （runconfig に `REQUIRED - One NISAR L1 RSLC formatted HDF5 file` と明記）
- **日本上空の RSLC は最小でも 14 GB**（陸域は 20/40MHz・2 偏波が既定）。初回には重い
- ソース読み取り許可を受け、wiki の記述を実装と突き合わせて **誤りを 3 つ修正**
  （`PR` は PROVISIONAL ではなく処理種別 / `polsar` は対称化のみ / 偏波は 8 通り）
- wiki に「処理レベルの連鎖」「granule の命名規則」を追加。図を 2 枚作成
- **`asf_search` は導入済み。`~/.netrc` は未作成**（＝まだ落とせない）

2026-08-27（2 本目）: **upstream の open issue 97 件を調査。**
詳細は `logs/2026-08-27-upstream-issues.md`

- 分類した結果、約 40 件が NISAR プロダクトの仕様適合系で、**実データがないと着手不可**
- **PR は作者を問わず滞留している**（open 65 件、最古は 2024-11。外部の方の PR #270 は 3 か月未レビュー）
  → **issue 起票を主軸に置く**判断をした
- **#255（`DateTime` が TZ 指定子を一切受け付けない）を手元で再現。未着手・PR なし**
- #223 / #335 は既に修正済み（issue が閉じ忘れ）、#265 と #353 は重複と判明

2026-08-27（1 本目）: **ISCE3 を初めて動かした。** 詳細は `logs/2026-08-27-first-run.md`

- `core` / `geometry` を外から叩き、楕円体・軌道補間・rdr2geo / geo2rdr・スワス断面を実測
- **`Orbit` が参照エポックを付け替える**ことを発見（知らないと地上 750 km ずれる）
- **地上間隔は近距離ほど広い**（Δ地上 ≈ Δ斜距離 / sin 入射角）ことを実測
- 用語集に「学問分野」の章を追加し、SAR の章に確認済み項目を追記（現在は wiki）

2026-08-27（3 本目）: **記録の置き場所を再編。**

- **用語集を wiki へ移し、1 ページ 1 概念の 42 ページに再編**（https://github.com/rindguitar/isce3-notes/wiki）。本体は作業の記録に絞る
- リンクを実測して[ドキュメントマップ](https://github.com/rindguitar/isce3-notes/wiki/Documentation-Map)を作成。孤立ページなし
- ⚠️ **wiki は別リポジトリなので、セッションから直接は読み書きできない。**
  用語集に追記するには `git clone https://github.com/rindguitar/isce3-notes.wiki.git` が要る
- NISAR の実データ取得手順を wiki に起こした（https://github.com/rindguitar/isce3-notes/wiki/NISAR-Data-Access）。**未検証**
- 図を 8 枚作成（本体 1 枚 / wiki 7 枚）。`mermaid-guide.md` をこのリポジトリ用に書き直した

2026-08-23: 環境構築。**ctest の基準値 235/237 を確定。** `~/isce3-notes` を整備。

## 次の一手（優先順）

**4 が主線になった**（実データが手に入ったため）。1〜3 は引き続き有効な候補。

1. **#255 `DateTime` の TZ 指定子未対応**（第一候補）
   - 再現済み・未着手・修正範囲が 1 関数（`cxx/isce3/core/DateTime.cpp` の `strptime`、413 行目付近）
   - 読む場所: `cxx/isce3/core/DateTime.cpp`、`tests/cxx` の DateTime テスト、
     `python/extensions` の DateTime バインディング（**許可不要になった**）
   - 進め方: **issue に再現結果（範囲は `Z` だけでなく TZ 指定子全般）をコメント → 反応を見て PR**
2. **numpy 2.x でのバグ探し**（issue 起票側の主戦場）
   - numpy 2.x の conda 環境を別に作り、再ビルド → ctest → 基準値 235/237 と比較
   - #335 の報告者が「他のビットシフト箇所も NEP 50 の観点で監査すべき」と書き残している
   - ビルドとテストは**ユーザーが実行する**
3. **#199 GDAL 3.12 の `SetGeoTransform` API 変更への追従**
   - 手元は GDAL 3.13.3 なので検証可能。機械的だが変更範囲が広がる可能性
4. **実データでの検証**（🔴 **進行中。いまの主線**）

   **Step 1 は取得済み**（`~/nisar-data/`、南極・計 537 MB）。認証も通っている。
   残りはこの順:

   1. **Step 2 を取得する**（ニュージーランド南島・計 2.8 GB、約 7 分）

      ```
      NISAR_L1_PR_RSLC_028_152_A_156_2005_DHDH_A_20260823T185248_20260823T185253_P05023_N_P_J_001
      NISAR_L2_PR_GCOV_028_152_A_156_2005_DHDH_A_20260823T185248_20260823T185253_P05023_N_P_J_001
      ```

   2. **DEM を取得する。** ASF の `NISAR_DEM`（1°タイル 3 MB、EPSG:4326、v1.2）。
      公式 GCOV と同じ修正版 Copernicus DEM なので、差分の原因切り分けが楽になる。
      `stage_dem.py` は ctest 既知失敗なので使わない
   3. **自分で GCOV を作り、公式 GCOV と数値で比較する。** 食い違えばバグの候補。
      出力範囲は runconfig の `processing.geocode.top_left` / `bottom_right` で絞れる
   4. **HDF5 の階層構造を精査**して仕様適合系の issue に着手する。
      手元のプロダクトは `productSpecificationVersion = 1.5.0`

   - 取得手順は wiki の [NISAR Data Access](https://github.com/rindguitar/isce3-notes/wiki/NISAR-Data-Access)（**検証済み**）
5. **`asf_search` のエラーメッセージ改善**（軽い。ISCE3 ではなく別プロジェクト）
   - 403 EULA 失敗を「トークンが不正」と報告し、`resolution_url` を捨てている
   - 手元に再現手順と実際の応答がある。[asf_search](https://github.com/asfadmin/Discovery-asf_search) へ issue

### 任意（急がない）

- `GeoToRdr` の未解決 failure を追うなら、UBSan (`-fsanitize=undefined`) 付きの
  最適化ビルドで UB の場所を特定する
- 信号処理側（`focus` / `signal`）にはまだ一度も触れていない

## upstream の実態（2026-08-27 時点）

- **2025 年 5 月まで外部 PR を受け付けていなかった**（内部リポジトリのミラーだった）。
  2021〜2024 の古い issue が放置されているのはこのため
- **open PR 65 件。最古は 2024-11 の #27（約 21 か月）。** コア開発者 gshiroma だけで 17 件 open
- ボトルネックはレビュー能力。**内部の人の PR も 1 年以上待たされている**
- issue はラベル運用されていない（open 97 件中 94 件が無ラベル）
- ⚠️ **`gh issue view` は使えない**（Projects classic 廃止で GraphQL エラー）。`gh api` を使う

## 未解決・保留中の問題

- **`GeometryTest.GeoToRdr` が最適化ビルドで失敗する。** `-O0` で通り `-O2` で落ちる。
  `-ffp-contract=off` でも落ちるので FMA は無関係 → **UB の疑い**。未対処。
  詳細は `logs/2026-08-23-test-failures.md`
  - 2026-08-27 追記: Python 経由の `geo2rdr` は**正常系が高精度で通った**。
    C++ 側のテストなので反証にはならないが、追うなら
    **失敗する特定の入力条件の絞り込み**が次の一歩（`tests/cxx/` を読めばよい）
- `nisar.workflows.stage_dem` は upstream のバグ。**環境と無関係なので対処不要**
- `io.background` は flaky。落ちても再実行で判断する
- **GPU (CUDA) ビルドは未対応。** そのため #265 / #353（CUDA バインディング）には着手できない
- `hdf5` が 2.x で入っている。**#223 の報告時より新しい組み合わせ**なので、
  リスクであると同時にバグ発見の材料でもある

## 手元の依存バージョン（upstream が試していない組み合わせ）

| 依存 | 手元 | 意味 |
|---|---|---|
| GDAL | 3.13.3 | #199 で問題になった 3.12 より新しい |
| HDF5 / h5py | 2.2.0 / 3.16.0 | #223 報告時（2.0.0 / 3.15.1）より新しい |
| GCC | 15.3.0 | 非常に新しい。`GeoToRdr` 失敗もこれ起因の可能性 |
| numpy | 1.26.4 | **古い。NEP 50 系のバグが見えない** → 2.x 環境を作る価値がある |

## 使うときに引っかかる ISCE3 の仕様（確認済み）

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

## 直近の決定事項

- 2026-08-30: 認証は `~/.netrc` ではなく**ユーザトークン**にする。
  パスワードを平文で置かずに済み、失効させられるため
- 2026-08-30: 実データは **`~/nisar-data/`** に置く（`~/isce3` の外。fork を汚さない）
- 2026-08-27: **貢献の主軸は issue 起票**。PR はマージまで数か月かかる前提で出す
- 2026-08-27: 試行コードは**ファイルに残さず標準入力から実行**する（heredoc）
- 2026-08-27: 最初の題材として**幾何（rdr2geo / geo2rdr）**を選んだ
- 2026-08-23: ビルドは `pip install .` ではなく **CMake 直叩き** → `ctest` と差分ビルドのため
- 2026-08-23: ビルドディレクトリを**リポジトリの外**（`~/isce3-build`）に置く
- 2026-08-23: メモは fork の wiki ではなく**独立したリポジトリ**（公開。wiki を使うため）
- 2026-08-23: `CLAUDE.md` は `~/isce3-notes` に置き、`--add-dir ~/isce3` で運用する

詳細は `decisions.md`
