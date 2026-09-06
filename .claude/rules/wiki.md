---
paths:
  - "**/README.md"
  - "docs/**/*.md"
---

# GitHub Wiki 構成規約

<!--
  wiki は本体とは別の git リポジトリなので、paths による自動ロードが効かない場合がある。
  wiki を触る指示を受けたら、このファイルを明示的に読むこと。
-->

## ⚠️ wiki は別リポジトリ

セッションから直接は読み書きできない。**編集するには clone が要る。**

```bash
git clone https://github.com/rindguitar/isce3-notes.wiki.git /tmp/wiki
```

現在 **42 ページ**。全体像は
[Documentation-Map](https://github.com/rindguitar/isce3-notes/wiki/Documentation-Map)。

## 何を wiki に書くか

| 置き場所 | 内容 |
|---|---|
| GitHub Wiki | **用語集**。技術・概念の解説（「そもそも InSAR とは」「GCOV とは」） |
| `README.md`（各ディレクトリ） | そのディレクトリの構成・一覧・使い方 |
| `docs/decisions.md` | 設計判断の記録（なぜそれを選んだか） |
| `docs/STATUS.md` | 現在地・次の一手 |
| `logs/` | その日に何が起きたかの記録（追記のみ） |
| `reference/` | 現時点の事実（環境・ビルド設定など。上書き更新） |

**1 ページ 1 概念。** 1 つのページに複数の概念を詰めない。

## ページの命名と表記

- ページ名（ファイル名）は**英語のケバブケース**: `Radar-Geometry.md`, `Look-Side.md`
- Home からのリンクは**日本語の表示名 + 1 行説明**を付ける

```markdown
- **[斜距離（slant range）](Slant-Range)** - 衛星から地表までの直線距離。地上距離との違いと換算
```

- 略称は単独で使わず日本語と併記する（例: `参照地形高（referenceTerrainHeight）`）

## Home.md の構成

Home はハブとして機能させる。構成は以下の順:

1. **冒頭**: プロジェクトの 1 行説明 + ドキュメントマップへのリンク
2. **技術ドキュメント**: ジャンルごとに `<details>` で折りたたむ
3. **プロジェクト情報**: 本体リポジトリ・README への導線
4. **更新履歴**: `<details>` で折りたたみ。追加・改訂を 1 行ずつ

```markdown
<details>
<summary><b>ジャンル名</b> — このジャンルが何を扱うかの一言</summary>

- **[表示名](Page-Name)** - 1 行説明

</details>
```

### ジャンル分けの原則

**「分野で通じる汎用知識」と「この環境固有の調査・判断」を必ず分ける。**
前者は他プロジェクトでも再利用でき、後者は文脈が変われば無効になる。混ぜると
どちらが持ち出せる知識なのか分からなくなる。

このリポジトリのジャンル:

- SAR / InSAR の基礎（観測の原理・幾何・偏波）
- ISCE3 の仕組み（処理レベル・プロダクト・ワークフロー）
- NISAR ミッションと実データ（命名規則・取得手順）
- 環境・ツール（conda / CMake / Claude Code）
- 調査レポート → **固有のものはここに隔離する**

## ドキュメントマップ

全ページのリンク関係を 1 枚の図にしたページ（`Documentation-Map`）を置く。
用途は「どこから読むか」と、**どのページが孤立しているか**の把握。

- IMPORTANT: ページを追加したりリンクを張り替えたら、**ドキュメントマップを作り直す**。
  元データが変わると図が実態とずれ、孤立ページ検出という本来の用途が壊れる
- 図の作り方は `.claude/rules/mermaid.md` に従う（特に「まとめる → 分ける」の 2 階層化）

### 作り直しの手順

```bash
# 1. wiki を clone する
git clone https://github.com/rindguitar/isce3-notes.wiki.git /tmp/wiki
```

```python
# 2. ページ間のリンクを抽出する
#    各ページ本文の ](ページ名) を走査し、wiki 内のページ名と一致するものだけ拾う
#    向きは落とす。往復しているものは 1 本に畳む
import os, re
d = '/tmp/wiki'
skip = {'Home', 'Documentation-Map'}
pages = {f[:-3]: open(os.path.join(d, f), encoding='utf-8').read()
         for f in os.listdir(d) if f.endswith('.md')}
edges = {tuple(sorted((src, t.split('#')[0].strip())))
         for src, txt in pages.items() if src not in skip
         for t in re.findall(r'\]\(([^)]+)\)', txt)
         if t.split('#')[0].strip() in pages
         and t.split('#')[0].strip() not in skip | {src}}
print(len(pages), 'ページ /', len(edges), '本')
```

3. **密に繋がるまとまりを見つける**。分類を人が決めないことが大事で、そうすることで
   「Home の分類と実際のリンク構造がずれている」といった発見が出る
4. **図を絞る**: 全体地図 → ブロックごとの内訳、の 2 階層にする。ブロックの名前だけは
   中身を見て人が付ける
5. **画像に描き出して、全枚数を目視する**（省略しない。1 枚でも貫通していれば誤読される）
6. push して、Home の更新履歴に 1 行足す

```bash
cd /tmp/wiki && git add -A && git commit -m "docs: ..." && git push
```
