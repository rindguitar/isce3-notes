# 作業ログ

日付ごとの作業記録。

**追記のみ。過去のログは修正しない。**
「そのとき何が起きたか」を残すのが目的なので、後から正しい知識に直してしまうと
記録としての価値が失われる。内容が古くなった事実は [`reference/`](../reference/README.md) 側を更新する。

ファイル名は `YYYY-MM-DD-<短い題名>.md`。

## 一覧（新しい順）

| 日付 | ログ | 内容 |
|---|---|---|
| 2026-08-27 | [初めて動かした（幾何 API の試運転）](2026-08-27-first-run.md) | `core` / `geometry` を外から叩き、楕円体・軌道補間・rdr2geo / geo2rdr を実測。`Orbit` が参照エポックを付け替えること、地上間隔は近距離ほど広いことが判明 |
| 2026-08-23 | [記録の置き場所と Claude Code 設定](2026-08-23-notes-repo-setup.md) | このリポジトリの構造を決め、`CLAUDE.md` / `STATUS.md` / `decisions.md` と用語集を整備。`CLAUDE.md` の探索規則、`/clear` の挙動、拡張機能版との違いが判明 |
| 2026-08-23 | [ctest 失敗の切り分け](2026-08-23-test-failures.md) | 237 件中 7 件失敗の原因を 4 系統に分離。GDAL 3.13 の仕様変更（解決済）、pybind11 3.x の型変換（仮説）、数値収束（仮説）、upstream バグ、flaky |
| 2026-08-23 | [初期構築](2026-08-23-initial-setup.md) | Miniforge 導入 → conda 環境作成 → CPU ビルド → `import isce3` まで。詰まった点 3 件（conda が PATH に無い / Eigen 5.0.1 の不一致 / nvcc 自動検出）とその原因 |
