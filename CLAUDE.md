# CLAUDE.md

このファイルは Claude Code が **ISCE3 の開発**を手伝う際のガイド。
**このファイルは薄く保つこと。** 詳細は `reference/` と `glossary/` に置き、
必要時のみ参照する（末尾の「参照ドキュメント」）。

@STATUS.md

## 起動方法

**`~/isce3-notes` を主フォルダにして起動する。** このファイルは起点から親方向へ
探索されるため、`~/isce3` を起点にすると（兄弟ディレクトリなので）永久に見つからない。

| 使う版 | 方法 |
|---|---|
| ターミナル | `cd ~/isce3-notes && claude --add-dir ~/isce3` |
| VS Code 拡張 | `~/isce3-notes/isce3.code-workspace` を開く（マルチルート） |

**`~/isce3` にはこのファイルを置かない。** upstream の fork なので、
追跡対象外のファイルを増やしたくないため。

`--add-dir` が必要なのは**起動時のみ**。`/clear` はプロセスを終了させず
会話履歴を消すだけなので、カレントディレクトリも追加ディレクトリも維持され、
このファイルは新しい文脈に再読み込みされる。起動後に追加したい場合は `/add-dir <パス>`。

詳細は [glossary/07-claude-code.md](glossary/07-claude-code.md)。

## プロジェクト概要

扱うリポジトリは 2 つ。

| パス | 何か | ブランチ |
|---|---|---|
| `~/isce3` | ISCE3 本体（`isce-framework/isce3` の fork）。**成果物はここから出す PR** | `develop` |
| `~/isce3-notes` | このリポジトリ。作業ログ・資料・用語集（private） | `main` |

ISCE3 = NASA JPL の InSAR / SAR 処理ライブラリ。C++/CUDA のコア +
Python バインディング。NISAR ミッションの処理基盤。

### 🔴 最重要: `~/isce3` のソースは許可制

**`~/isce3` のソースコードを、ユーザーの明示的な許可なく読まない・書き換えない。**

| 状態 | 対象 |
|---|---|
| 許可済み | `README.md`, `LICENSE`, `VERSION.txt`, `CONTRIBUTING.md`, `docs/`, `doc/`, `environment.yml`, `pyproject.toml`, `CMakeLists.txt`, `.pre-commit-config.yaml`, `.clang-format` |
| 調査目的で個別に許可 | `tests/`, `python/`, `cxx/` — **その調査に限る。恒久的な許可ではない** |
| 未許可 | `share/`, `bin/`, `tools/`, `extern/`, `.cmake/`, `.github/`, `.ci/` |

読む必要が出たら、**対象パスと「それを読むと何が分かるか」を述べて許可を求める。**
許可の範囲を推測で広げない。ディレクトリ一覧と git のメタ情報コマンドは許可不要。

### 環境の制約（コードから読み取れない事実のみ）

* WSL2 (Ubuntu 24.04) / 8 コア / RAM 15GB
* GPU は GTX 1060 6GB (CC 6.1) だが **CUDA ビルドは不可**。
  システムの nvcc は CUDA 12.0 で対応ホスト GCC は 12.x まで、環境の GCC は 15.3。
  → **常に `-DWITH_CUDA=OFF`**（既定は `Auto` で nvcc を拾ってしまう）
* `environment.yml` は下限指定のみで上限がない。
  **`eigen<4` と `pybind11<3` の手動固定が必須**（外すとビルド・テストが壊れる）
* `GDAL_MEM_ENABLE_OPEN=YES` が必要（conda の activate フックで設定済み）
* **ctest の基準値は 235/237。** `geometry.geometry` と `nisar.workflows.stage_dem` は
  既知の失敗。**3 件以上落ちたら自分の変更を疑う**

## セッションプロトコル（最重要）

### 開始時

1. `STATUS.md`（このファイルに @import 済み）で現在地・次の一手・未解決事項を把握する
2. 作業を始める前に**今日のゴールを 1〜3 行で確認**し、ユーザーと認識を合わせる
3. `~/isce3` で作業するなら `git -C ~/isce3 branch --show-current` で現在のブランチを確認する

### 終了時

**`/clear` の前もここに含まれる。** 会話の記憶が消えるので、
`STATUS.md` に残していないことは失われる。ユーザーが `/clear` すると言ったら、
その前に下記を済ませたか確認する。

1. `STATUS.md` を更新する（何をした / 何が残った / 次に何をすべきか / 詰まった点）
2. 設計判断があれば `decisions.md` に追記する
3. `git -C ~/isce3 status --short` で **`~/isce3` が汚れていないこと**を確認する
4. コミット・プッシュ漏れがないか確認する

## コマンド実行のルール

### ⚠️ 実行前に目的を説明する

**コマンドは、何をするもので・なぜ必要で・何を変更するかを述べてから実行する。**
読み取り専用のものでも同じ。ユーザーの質問には、行動より先に順番に答える。

### ⚠️ 時間のかかる操作はユーザーが実行する

以下は Claude Code で実行せず、**コマンドを提示してユーザーに渡す**:

* フルビルド（`cmake --build`、15〜40 分）
* フルテスト（`ctest` の全実行、約 10 分）
* conda 環境の作成、大きな依存の入れ替え

理由: ユーザーがターミナルで進捗を見ながら実行したいため。

## 開発コマンド

前提: `conda activate isce3`。activate フックが `PYTHONPATH` / `LD_LIBRARY_PATH` /
`GDAL_MEM_ENABLE_OPEN` を設定する。非対話シェルからは先に
`source ~/miniforge3/etc/profile.d/conda.sh` が要る。

| 目的 | コマンド |
|---|---|
| 差分ビルド | `cmake --build ~/isce3-build -j8` |
| インストール | `cmake --install ~/isce3-build` |
| テスト全実行 | `ctest --test-dir ~/isce3-build --output-on-failure` |
| 一部だけ実行 | `ctest --test-dir ~/isce3-build -R '<正規表現>' --output-on-failure` |
| 失敗分だけ再実行 | `ctest --test-dir ~/isce3-build --rerun-failed --output-on-failure` |
| 整形 | `clang-format -i <file>` — **push 前に手動。pre-commit では走らない** |

ビルドディレクトリは `~/isce3-build`。**リポジトリの外**に置いてある。
構成をやり直す場合のオプションは `reference/environment.md` を参照。

## 実装ワークフロー（説明可能性の担保）

**実装前に方針を先に提示し、承認を得てから書く。**

1. 方針提示: 何を・どこを・どう変えるか、箇条書き 3〜5 行
2. 承認後に実装
3. ビルド → テスト → **基準値 235/237 と比較** → clang-format → コミット → プッシュ
   （この順序を崩さない）

理由: ユーザーは自分で説明できないコードは採用しない。
方針を先に合わせることで、書き直しによるトークン浪費も防ぐ。

## コーディング規約

### ⚠️ upstream に出すコードは英語で書く

`~/isce3` は国際的な OSS で、PR は本家に出す。
**コメント・docstring・コミットメッセージは英語。**
日本語で書いてよいのは `~/isce3-notes` の中だけ。

* C++ / CUDA: `.clang-format` に従う（LLVM ベース / インデント 4 / タブ禁止 /
  include を 5 グループに自動並べ替え）
* Python: PEP 8
* 処理の流れはコメントで説明する。ただし自明な 1 行ごとのコメント
  （`i += 1  // increment` 等）は書かない
* ハードコード禁止。設定値は引数・環境変数・設定ファイルへ
* **周囲のコードに合わせる。** コメントの密度・命名・書き方を既存に揃える

## Git 規約

### `~/isce3`（fork）

* IMPORTANT: **`develop` への直接コミット禁止。** 必ず作業ブランチを切る
* 作業開始時に upstream へ追従する:

  ```bash
  git checkout develop
  git fetch upstream
  git merge upstream/develop --ff-only
  git checkout -b <ブランチ名>
  ```

* PR は本家の `develop` に出す。マージには**コアメンバー 2 名の承認**が必要
* CI が通らないとマージされない。**資源節約のため、ローカルでテストしてからまとめて push する**
* コミットは detect-secrets と CodeQL でスキャンされる。秘密情報を含めない
* 長寿命ブランチは **`develop` のみ**。他は全て短命な作業ブランチで、マージ後に削除する

### `~/isce3-notes`（このリポジトリ）

* `STATUS.md` と `decisions.md` の更新は `main` に直接コミットしてよい
* `logs/` は `YYYY-MM-DD-<題名>.md`。**追記のみ。過去のログを後から修正しない**
  （そのとき何が起きたかを残すのが目的なので、後から正しくしない）
* `reference/` は事実が変わったら**上書き更新**する
* 新しい用語に出会ったら `glossary/` の該当ファイルに追記する
* パスは `~/...` で書く。ユーザ名を含む絶対パスを書かない

## モデル運用ルール（コスト規律）

メインセッションの役割は**設計・レビュー・難所の実装のみ**。以下は委譲する。

| 作業 | 担当 | 理由 |
|---|---|---|
| 探索・grep・ファイル特定 | haiku サブエージェント | 安価・高速で十分 |
| テスト実行・結果要約 | haiku サブエージェント | 出力が長いだけの作業 |
| 定型実装（設計が決まっているもの） | sonnet サブエージェント | 実装力は十分 |
| 設計・アーキテクチャ判断・コードレビュー | メイン | 判断が必要 |
| サブエージェントが 2 回失敗したタスク | メイン | エスカレーション |

* ⚠️ **サブエージェントにも許可制は適用される。** 未許可のパスを探索させない。
  委譲するときは許可済みの範囲を明示的に伝える
* 大きなファイル（ビルドログ・ctest の全出力）をメインのコンテキストに直接読み込まない。
  必要ならサブエージェントに要約させる
* 同じファイルを繰り返し読み直さない。一度読んだ内容は会話内の記憶を使う

## 参照ドキュメント（必要時のみ読む）

| ファイル | 内容 | 読むタイミング |
|---|---|---|
| `STATUS.md` | 現在地・次の一手 | **毎セッション開始時（@import 済み）** |
| `decisions.md` | 設計判断の記録 | 過去の判断を確認するとき |
| `reference/environment.md` | 環境の再現手順・依存バージョン | 環境が壊れたとき |
| `reference/build-options.md` | CMake / scikit-build のオプション | ビルド設定を変えるとき |
| `reference/runtime-and-packaging.md` | 実行形態・Docker・spec file | 配布や再現性を考えるとき |
| `glossary/*.md` | 技術・用語の解説 | 知らない用語に出会ったとき |
| `logs/*.md` | 過去の作業ログ | 「前にどう解決したか」を探すとき |
