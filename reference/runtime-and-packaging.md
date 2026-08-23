# 実行形態と配布形態

最終更新: 2026-08-23

## ISCE3 はライブラリであって、サーバではない

**常駐プロセスが存在しないので、「起動・停止」という概念自体がない。**

- Python から `import isce3` して使う
- あるいはワークフローを**バッチ実行**する（走って、終わって、プロセスが消える）

性質としてはコンパイラや `ffmpeg` に近い。
PostgreSQL や nginx のように「立ち上げておく」対象ではない。

### `conda activate isce3` は「起動」ではない

混同しやすいので明記しておく。`conda activate` がやっているのは
**そのシェルの `PATH` と環境変数を書き換えることだけ**で、プロセスは 1 つも立たない。

- ターミナルを閉じても「何かが止まる」わけではなく、その設定が消えるだけ
- 停止操作は不要。`conda deactivate` も後始末として必須ではない

### 結論

**ローカルで開発する分には Docker もクラウドインスタンスも不要。**
必要なのは `conda activate isce3` だけ。

---

## Docker は使われているが、開発者向けではない

出典: `~/isce3/docs/maintainer/docker-image-updates.md`

> Docker images are the primary software deliverable of the NISAR Algorithm
> Development Team (ADT) to the Science Data System (SDS).

用途は **NISAR ミッションの運用系（SDS）への納品形式**であって、
開発してテストするための道具ではない。

| 項目 | 内容 |
|---|---|
| ベースイメージ | Oracle Linux 8（セキュリティパッチ適用版） |
| 取得元 | **JPL 内部の Artifactory**（`cae-artifactory.jpl.nasa.gov`） |
| conda | イメージ内に Miniforge を入れて構築 |
| 中身 | ISCE3 + NISAR QA + SoilMoisture |

**ベースイメージは外部から取得できない。** 作りたくても作れないので、この経路は考えなくてよい。
ADT の納品に関わる立場になったら、そのときアクセス権も付いてくるはず。

---

## ★ バージョン固定された conda spec file が存在する

同じドキュメントより:

> ISCE3's runtime and build-time dependencies are separated into distinct spec
> files. ... These spec files are tracked by Git and can be used to
> **exactly reproduce each conda environment** on the same platform.

つまりプロジェクトは、`environment.yml`（下限のみで上限がない、緩い定義）**とは別に、
バージョンを完全固定した conda spec file を持っている。**

| 項目 | 内容 |
|---|---|
| 種類 | `runtime` / `dev` / `soil-moisture` の 3 つ |
| 生成 | `./tools/create_spec_file.py <種類>` |
| 実体 | `tools/imagesets/...` 配下（**未確認** — `tools/` はまだ中を見ていない） |
| 管理 | git 管理されている |

### なぜ重要か

**これを使っていれば、[初期構築時に踏んだ Eigen 5.0.1 の問題](../logs/2026-08-23-initial-setup.md#b-eigen-のバージョン不一致でビルド失敗-今回の主因)は
起きなかった可能性が高い。**

conda の linux-64 パッケージはディストリビューション非依存なので、
Oracle Linux 8 向けに固定されたものでも WSL2 の Ubuntu で動く見込みがある
（Oracle Linux 8 の glibc は Ubuntu 24.04 より古いので、前方互換の方向）。

**次に依存関係が原因で詰まったときの手札**として覚えておく。
今の環境は動いているので、急いで乗り換える必要はない。

---

## 将来クラウドが必要になるとしたら

必要になる理由は「**ISCE3 がコンテナを要求するから**」ではなく、
単に「**手元のマシンが足りないから**」。

| 現状 | 値 |
|---|---|
| メモリ | 15 GB |
| VRAM | 6 GB (GTX 1060) |

NISAR の実データは 1 シーンで数十 GB 規模になるため、
本格的に実データを扱い始めると頭打ちになる可能性がある。
そうなったら初めてクラウドを検討する話であって、今の段階では関係ない。
