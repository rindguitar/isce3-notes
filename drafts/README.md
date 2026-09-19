# 下書き

upstream（`isce-framework/isce3`）へ提出する前の文面と、その根拠をまとめたもの。

**提出したら、このファイルの「状態」を更新する。**
提出後に相手から反応があった場合は、その結果を `docs/STATUS.md` に書く。

## 一覧

**このディレクトリは「upstream へ出すもの」だけを置く。**
根拠は `docs/experiments.md`、仕組みの説明は `docs/referenceTerrainHeight-解説.md`。

| ファイル | 用途 | 言語 | 状態 |
|---|---|---|---|
| [upstream-issue.md](upstream-issue.md) | **upstream に立てる issue の本文。**そのまま貼れる形 | 英語 | **レビュー中**（[PR #2](https://github.com/rindguitar/isce3-notes/pull/2)） |
| [upstream-issue-日本語対訳.md](upstream-issue-日本語対訳.md) | 対訳と**各節の意図**。投稿しない（確認・説明用） | 日本語 | 同上 |
| [再現手順-referenceTerrainHeight.md](再現手順-referenceTerrainHeight.md) | 単独で成立する再現手順 | 日本語 | **投稿済み** → [notes #1](https://github.com/rindguitar/isce3-notes/issues/1) |

⚠️ **`再現手順` はローカルの方が新しい**（テスト番号の注記を後から追加）。
issue #1 の本文を更新するか、次に渡すときに気をつけること。

## 扱っている案件

**`referenceTerrainHeight` のジオコーディングが全 NaN になる**（2026-08-30 発見）。

1 次元の LUT を 2 次元と誤判定するため読み出しに失敗し、レイヤ全体が NaN になる。
終了コードは 0 なので気づきにくく、**公式の配布プロダクトにも入っている**。

進め方は **#165 にコメント → 返答を見て新規 issue → PR** の順。
いきなり起票しないのは、既知・低優先度である可能性を否定できないため。

## 運用ルール

- 🔴 **提出直前に PR を立て、メンターの approve を待ってから merge → 投稿する。**
  **PR に載せるのはレビュー対象の文面だけ**（推敲や整理は `main` に直接コミットしてよい）。
  PR を出したら**レビュアーにメンターを追加する**（コマンドは `CLAUDE.md` の Git 規約）
- **upstream に出す文面は英語。** 日本語の説明メモは別ファイルに分ける
- 公開の場に書く主張は、**実物で裏を取ってから**書く（推測で書かない）
- 「言えないこと」も文書に明記する。検証の範囲を超えた主張をしない
- 提出用ファイルは**そのまま貼れる状態**に保つ。メモやコメントを混ぜない
