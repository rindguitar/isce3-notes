# 用語集

ISCE3 を触るうえで出てくる技術・用語の解説。初歩から書いてある。

`logs/` や `reference/` が「何をやったか / いまどうなっているか」なのに対し、
ここは「**そもそもそれは何か**」を置く場所。
新しい用語に出会ったら該当ファイルに追記していく。

## 読む順

上から順に読むと積み上がるように並べてある。急ぐなら 03 と 05 だけでも実用になる。

| # | ファイル | 内容 |
|---|---|---|
| 01 | [languages.md](01-languages.md) | C++ / Python / CUDA。なぜ 2 言語で書かれているのか、バインディングとは何か |
| 02 | [build.md](02-build.md) | コンパイル・リンクとは何か。CMake / Ninja / ccache / pip |
| 03 | [environment.md](03-environment.md) | conda、環境変数、`PATH` と `PYTHONPATH`、共有ライブラリの探し方 |
| 04 | [git.md](04-git.md) | git、fork、`upstream`、PR。OSS への参加手順 |
| 05 | [testing.md](05-testing.md) | ctest / gtest / pytest。テストの読み方 |
| 06 | [sar.md](06-sar.md) | SAR / InSAR / NISAR のドメイン用語 |
| 07 | [claude-code.md](07-claude-code.md) | Claude Code の仕組み。`CLAUDE.md` の探索規則、`/clear`、ワークスペース |

## 書き方の方針

- **今回実際に出てきたコマンドや現象と結びつける。**
  抽象的な定義だけでは後で読み返しても使えないため
- 分からないまま流したものも「分かっていない」と書いて残す
