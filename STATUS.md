# STATUS

最終更新: 2026-08-23（セッション終了時に必ず更新）

## 現在のフェーズ

**環境構築 完了 → 開発着手前。** ISCE3 のコードにはまだ一切手を付けていない。
取り組むテーマも未定。

## 前回やったこと

- Miniforge 導入 → `environment.yml` から conda 環境作成 → CMake 直叩きでビルド（`~/isce3-build`）
- 依存のバージョンずれを 4 件切り分け。`eigen<4` / `pybind11<3` / `GDAL_MEM_ENABLE_OPEN=YES` で 3 件解決
- **ctest の基準値を確定: 235/237**
- conda の activate / deactivate フックを作成（`PYTHONPATH` / `LD_LIBRARY_PATH` / `GDAL_MEM_ENABLE_OPEN`）
- `~/isce3-notes` を作成し、ログ・資料・用語集を整備

## 次の一手（優先順）

1. **取り組むテーマを決める。** ISCE3 のどの領域に貢献するかが未定。
   upstream の open issue を眺めて、手を付けられそうなものを探すところから
2. テーマが決まったら、該当ディレクトリの**読み取り許可を出す**（現状 `cxx/` `python/` `tests/` は
   前回の調査に限った許可であり、恒久的なものではない）
3. 作業ブランチを切る前に `git fetch upstream && git merge upstream/develop --ff-only` で追従する

### 任意（急がない）

- `GeoToRdr` の未解決 failure を追うなら、UBSan (`-fsanitize=undefined`) 付きの
  最適化ビルドで UB の場所を特定する

## 未解決・保留中の問題

- **`GeometryTest.GeoToRdr` が最適化ビルドで失敗する。** `-O0` で通り `-O2` で落ちる。
  `-ffp-contract=off` でも落ちるので FMA は無関係 → **UB の疑い**。未対処。
  詳細は `logs/2026-08-23-test-failures.md`
- `nisar.workflows.stage_dem` は upstream のバグ（テストが `bbox_epsg` を渡していないのに
  `main()` が参照している）。**環境と無関係なので対処不要**
- `io.background` は flaky。落ちても再実行で判断する
- **GPU (CUDA) ビルドは未対応。** CUDA 12.0 と GCC のバージョン不整合が原因。
  やるなら conda-forge の `cuda-nvcc` で揃える方向
- `hdf5` が 2.x で入っている。今のところ問題は出ていないが、
  `environment.yml` の上限なし問題の同類なので潜在リスク

## 直近の決定事項

- 2026-08-23: ビルドは `pip install .` ではなく **CMake 直叩き** → `ctest` と差分ビルドのため
- 2026-08-23: ビルドディレクトリを**リポジトリの外**（`~/isce3-build`）に置く → `~/isce3` を汚さないため
- 2026-08-23: メモは fork の wiki ではなく**独立した private リポジトリ** → fork 削除で消えるのを避けるため
- 2026-08-23: `CLAUDE.md` は `~/isce3-notes` に置き、`--add-dir ~/isce3` で運用する

詳細は `decisions.md`
