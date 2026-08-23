# 03. 環境まわり — conda / 環境変数 / パス

## conda

### 何をするものか

**プログラムとその依存関係を、隔離された箱の中に入れて管理するツール。**

Python パッケージだけでなく、**C++ ライブラリやコンパイラも同じ仕組みで扱える**のが
`pip` との決定的な違い。ISCE3 は GDAL・HDF5・Eigen といった C++ ライブラリに
依存するので、conda が向いている。

### Miniforge

conda の配布形態のひとつ。**conda-forge を既定チャネルにした最小構成**。
ISCE3 の公式ドキュメントもこれを推奨している。

| 配布 | 特徴 |
|---|---|
| Anaconda | 大量のパッケージ同梱。商用利用にライセンス上の注意 |
| Miniconda | 最小構成。既定チャネルは Anaconda 社のもの |
| **Miniforge** | 最小構成 + conda-forge 既定。**これを使った** |

### チャネル (channel)

パッケージの配布元。`conda-forge` はコミュニティ運営の最大手。

`environment.yml` の記述:

```yaml
channels:
  - conda-forge
  - nodefaults
```

`nodefaults` は「Anaconda 社の既定チャネルを**使うな**」という指定。
配布元を混ぜるとライブラリの噛み合わせが壊れやすいため。

### 環境 (environment)

**隔離された箱そのもの。** 名前を付けて管理する。

```
~/miniforge3/                 conda 本体
  └── envs/
       └── isce3/             ← これが「環境」。この中に全部入っている
            ├── bin/python
            ├── lib/
            └── include/
```

重要なのは、**環境はディレクトリに紐づかない**こと。

| ツール | 置き場所 | 参照方法 |
|---|---|---|
| npm | `<project>/node_modules` | プロジェクト内から自動解決 |
| venv | `<project>/.venv` | パス指定 |
| **conda** | **`~/miniforge3/envs/<名前>`** | **名前で参照** |

だから isce3 の環境をクローンの中に作らなかった。
conda の標準的な使い方ではないうえ、リポジトリが汚れる。

### `conda activate` は「起動」ではない

**プロセスは 1 つも立たない。** シェルの環境変数を書き換えているだけ。

```bash
conda activate isce3
```

これがやること:
- `PATH` の先頭に `~/miniforge3/envs/isce3/bin` を追加
- `activate.d/*.sh` を順に実行

ターミナルを閉じても「何かが止まる」わけではない。停止操作は不要。

### `environment.yml`

環境の設計図。「何を入れるか」を書いたファイル。

```yaml
name: isce3
dependencies:
  - eigen>=3.3
  - gdal>=3.6
```

### バージョン指定の書き方

| 書き方 | 意味 |
|---|---|
| `eigen>=3.3` | 3.3 以上。**上限なし** |
| `eigen<4` | 4 未満 |
| `hdf5>=1.10.2,!=1.14.0` | 1.10.2 以上、ただし 1.14.0 は除外 |
| `pybind11=2.13.6` | ちょうどこの版 |

**ISCE3 の `environment.yml` はほぼ全て下限のみ。** 上限がない。
そのため conda は常に最新を入れようとし、
メジャーバージョンが上がった依存で壊れる。
今回これで 4 回連続で壊れた（eigen / gdal / pybind11 / gcc）。

### セマンティックバージョニング

`3.4.0` のような 3 つ組を **メジャー.マイナー.パッチ** と読む慣習。

| 位置 | 上がるとき |
|---|---|
| メジャー | 互換性が壊れる変更 |
| マイナー | 機能追加（互換性は保つ） |
| パッチ | バグ修正 |

**メジャーが上がったら壊れて当然**という前提の仕組み。
だから「壊れたらまずメジャーバージョンを疑う」が有効。

### spec file

`environment.yml` が「条件」なのに対し、spec file は
**解決済みの具体的なバージョンを全部並べたもの**。完全に同じ環境を再現できる。

ISCE3 は Docker イメージ用にこれを持っている（`tools/` 配下、未確認）。
`environment.yml` の緩さを根本的に避けたいなら、こちらへの乗り換えを検討する。

## 環境変数

**プロセスに渡される名前付きの設定値。** 子プロセスに引き継がれる。

```bash
export NAME=value    # 設定して子プロセスに引き継ぐ
echo $NAME           # 参照
```

`export` を付けないと引き継がれない。

**注意: `export` はそのシェルの中だけ。** ターミナルを閉じると消える。
毎回必要な設定は、どこかに書いて自動実行させる必要がある。

### `PATH`

**コマンドを探すディレクトリの一覧。** `:` 区切り。

`python3` と打ったとき、シェルは `PATH` を**先頭から順に**探し、
最初に見つかったものを実行する。

`conda activate` が環境の `bin/` を先頭に追加するので、
conda の Python が優先されるようになる。

### `PYTHONPATH`

**Python がモジュールを探す場所の追加指定。**

`import isce3` したとき、Python は `sys.path` を順に探す。
`PYTHONPATH` の内容は **`site-packages` より先**に入るため、優先される。

今回これを設定するまで `import isce3` が
`ModuleNotFoundError` になっていた。CMake でインストールした先
（`~/isce3-build/install/packages`）を Python が知らなかったため。

なお pip 版と CMake 版が両方あると、この優先順位のせいで
**どちらを使っているか分からなくなる**。だから移行時に `pip uninstall isce3` した。

### `LD_LIBRARY_PATH`

**共有ライブラリ (`.so`) を探す場所の追加指定。** Linux 固有。

Python の拡張モジュール（`isce3.ext.isce3`）は C++ で書かれていて、
実行時に `libisce3.so` を読み込む必要がある。
その場所を教えるのがこれ。

`PYTHONPATH` が「Python のモジュールを探す道」なら、
`LD_LIBRARY_PATH` は「C++ のライブラリを探す道」。**両方要る。**

### `GDAL_MEM_ENABLE_OPEN`

GDAL 固有の設定。今回必要になった。

GDAL は `MEM:::DATAPOINTER=0x...` という
**生のメモリアドレスを指定してデータを開く構文**を持っていたが、
セキュリティ上の理由で既定無効になった。ISCE3 はこれを使っている。

```bash
export GDAL_MEM_ENABLE_OPEN=YES
```

これが無いとテストが 3 件落ちる。

## conda の activate フック

**`conda activate` したときに自動実行されるスクリプト。**

```
~/miniforge3/envs/isce3/etc/conda/
├── activate.d/     activate 時に実行
└── deactivate.d/   deactivate 時に実行
```

`~/.bashrc` に書くのとの違い:

| 置き場所 | 有効範囲 |
|---|---|
| `~/.bashrc` | **全てのシェル**。他のプロジェクトにも漏れる |
| `activate.d/` | **その環境を activate したときだけ** |

ISCE3 用の設定は後者に置いた。`PYTHONPATH` が他の conda 環境に
漏れると事故のもとになるため。

deactivate 側も作るのが作法。元の値を退避しておいて復元する。
これをやらないと `conda deactivate` しても設定が残り続ける。

### `~/.bashrc` と非対話シェル

Ubuntu の `~/.bashrc` は冒頭でこう書かれている:

```bash
case $- in
    *i*) ;;      # 対話シェルなら続行
      *) return;;  # 非対話シェルなら即終了
esac
```

そのため、**スクリプトから実行したシェルでは conda の初期化行に到達しない**。
今回「私の環境では `conda: command not found` になるが、
あなたの環境では動く」という食い違いが起きた原因がこれ。

スクリプトから conda を使うなら、明示的に読み込む:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
```
