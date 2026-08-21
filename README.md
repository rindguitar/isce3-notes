# isce3-notes

[ISCE3](https://github.com/isce-framework/isce3) を触るにあたっての作業ログと調査メモ。

ISCE3 は NASA JPL の InSAR / SAR 処理ライブラリ（C++ / CUDA コア + Python バインディング）。
初めて扱う技術スタックなので、手順・詰まった点・判明した仕様をここに残していく。

## このリポジトリについて

- **ISCE3 の fork ではない。** 本体のソースは一切含まない。純粋にメモ。
- クローン本体は別の場所（`~/isce3`）に置き、このリポジトリとは混ぜない。
  fork のコードツリーにメモを置くと upstream との差分に混ざり、PR を出すときに邪魔になるため。
- fork の wiki ではなく独立したリポジトリにしてある。fork は消すことがあり、
  消すと wiki も一緒に消えるため。

## 構成

```
logs/       日付ごとの作業ログ。後から書き換えない（そのときの記録として残す）
reference/  現時点の事実をまとめた資料。状況が変わったら上書き更新する
```

各ディレクトリの索引は、それぞれの README を参照。

- [logs/README.md](logs/README.md) — 作業ログの一覧
- [reference/README.md](reference/README.md) — 資料の一覧

## 運用ルール

- `logs/` は `YYYY-MM-DD-<短い題名>.md`。**追記のみ、過去のログは修正しない。**
  「そのとき何が起きたか」を残すのが目的なので、後から正しくしない。
- 内容が古くなった事実は `reference/` 側を直す。
- パスは `~/...` で書く。ユーザ名を含む絶対パスは書かない。

## 現在の状態

- ISCE3 `0.26.0-dev` を **CPU ビルド**でインストール済み、`import isce3` 通過
- GPU (CUDA) ビルドは未対応
- `ctest` によるテスト実行は未対応（CMake 直叩きビルドが必要）

詳細は [logs/2026-08-22-initial-setup.md](logs/2026-08-22-initial-setup.md) の「残課題」を参照。

## 参考リンク

- upstream: https://github.com/isce-framework/isce3
- 公式ドキュメント: https://isce-framework.github.io/isce3/
- ビルド手順（公式）: https://isce-framework.github.io/isce3/buildinstall/
