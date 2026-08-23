# 04. git と OSS への参加

## git の基礎

**変更履歴を記録するツール。** 「いつ・誰が・何を変えたか」を全部残す。

| 用語 | 意味 |
|---|---|
| **リポジトリ (repository)** | 履歴を含むプロジェクト全体。「リポ」と略される |
| **コミット (commit)** | 変更の記録 1 単位。スナップショット |
| **ブランチ (branch)** | 履歴の枝。並行して別の作業を進められる |
| **HEAD** | いま自分がいる位置 |
| **リモート (remote)** | ネット上にあるリポジトリの別名 |
| **クローン (clone)** | リモートを手元に複製すること |

### 作業の流れ

```
編集  →  git add（記録する対象を選ぶ） →  git commit（記録する） →  git push（送る）
```

`git add` を挟むのは、**変更の一部だけをコミットできる**ようにするため。

### よく使う確認コマンド

```bash
git status          # いま何が変わっているか
git status --short  # 短縮表示。何も出なければ「変更なし」
git log --oneline   # 履歴を 1 行ずつ
git diff            # 変更内容の詳細
```

今回 `git -C ~/isce3 status --short` を繰り返し実行して
「リポジトリを汚していない」ことを確認していた。
`-C <パス>` は「そのディレクトリで実行する」という指定。

## fork と upstream

### fork（フォーク）

**他人のリポジトリを、自分のアカウントにコピーすること。** GitHub の機能。

なぜ必要かというと、**他人のリポジトリには直接書き込めない**から。
ISCE3 の CONTRIBUTING.md にもこう書かれている:

> External contributors cannot directly create or modify branches on the isce3 repository.

### origin と upstream

fork して作業するとき、リモートが 2 つになる。

| 名前 | 指す先 | 用途 |
|---|---|---|
| **origin** | 自分の fork | push する先 |
| **upstream** | 本家 | 最新を取り込む元 |

```bash
git remote -v    # 設定を確認
```

名前は単なる慣習で、git が特別扱いしているわけではない。

### 最新を取り込む

本家が進んだら、自分の手元にも反映する。

```bash
git checkout develop
git fetch upstream                    # 本家の最新を取得（まだ反映はしない）
git merge upstream/develop --ff-only  # 反映する
```

`fetch` と `merge` が分かれているのは、
「取得」と「自分の作業への反映」を分けて考えられるようにするため。

### fast-forward (`--ff-only`)

**自分が何も変更していない場合に、履歴を一直線に進める**マージ方法。
余計なマージコミットができないので履歴がきれいになる。

ISCE3 の CONTRIBUTING.md はこれを推奨している。
失敗した場合は自分側にも変更があるということなので、通常の merge に切り替える。

## ブランチとプルリクエスト

### ブランチを切る

```bash
git checkout -b my-branch-name
```

`-b` は「新規作成して移動」。作業ごとに別のブランチを作るのが基本。

### プルリクエスト (PR)

**「この変更を取り込んでください」という提案。** GitHub の機能。

```
自分の fork のブランチ  →  PR  →  本家の develop
```

ISCE3 の場合、マージには**コアメンバー 2 名の承認**が必要。

### ISCE3 のブランチ構成

| ブランチ | 役割 |
|---|---|
| `develop` | 開発の主軸。**PR はここに出す** |
| `main` | 安定版 |

一般的な OSS では `main` に出すことが多いが、ISCE3 は `develop` が主軸。

## コミットメッセージ

慣習として、こう書く:

```
Fix the troposphere phase screen datacube across the dateline

（空行）
なぜこの変更が必要だったか、何をしたかの説明。
```

- 1 行目は**要約**。50〜72 文字程度、命令形（`Fix`, `Add`, `Remove`）
- 空行を 1 つ空ける
- 以降に詳細

ISCE3 の実際の履歴もこの形式:

```
0d1600d8 Update STATIC workflow for new water mask spec (#334)
be7b3d99 Fix failing unit test test.cxx.isce3.io.raster.raster (#348)
```

末尾の `(#334)` は PR 番号。

## `.gitignore`

**git に記録させないファイルの一覧。**
ビルド生成物やエディタの設定など、履歴に残す意味のないものを書く。

今回はビルドディレクトリを**リポジトリの外**（`~/isce3-build`）に置いたので、
`.gitignore` を気にする必要がなくなった。

## ISCE3 の開発で使うツール

CONTRIBUTING.md で要求されているもの。

### clang-format

**C++ コードの整形ツール。** インデントや改行位置を機械的に揃える。

設定は `.clang-format` に書かれている（LLVM ベース、インデント 4、タブ禁止）。

**注意: pre-commit では自動実行されない。push 前に手動で走らせる必要がある。**

### pre-commit

**コミット前に自動でチェックを走らせる仕組み。**

```bash
pre-commit install    # 有効化。これをやらないと動かない
```

ISCE3 で設定されているフックは **detect-secrets 1 つだけ**。

### detect-secrets

**パスワードや API キーの混入を検出するツール。**
一度公開リポジトリに入れてしまうと履歴から完全に消すのは困難なので、
入口で止める。

### CI (Continuous Integration)

**PR を出すと自動でビルドとテストが走る仕組み。** GitHub Actions で動く。

CI が通らないとマージされない。CONTRIBUTING.md には
「資源の無駄を避けるため、ローカルでテストしてからまとめて push せよ」とある。

**手元で `ctest` を通せる状態にしたのは、このため。**
