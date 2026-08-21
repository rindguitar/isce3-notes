# ISCE3 のビルドオプションと挙動

最終更新: 2026-08-22 / `0.26.0-dev` の `CMakeLists.txt`・`pyproject.toml` を読んで整理したもの。

## ビルド方法は 2 通り

| | `pip install .` | CMake 直叩き |
|---|---|---|
| ビルド場所 | **一時ディレクトリ**（`pyproject.toml` に `build-dir` 指定なし） | 自分で掘る（慣例で `build/`） |
| リポジトリが汚れるか | **汚れない** | `build/` ができる |
| `ctest` | **使えない**（ビルドツリーが残らない） | 使える |
| 差分ビルド | 効かない。変更のたびフルビルド相当 | 効く |
| 環境変数の設定 | 不要 | `PYTHONPATH` と `LD_LIBRARY_PATH` が必要 |
| 向き | 使うだけ / 動作確認 | **開発** |

### CMake 直叩きの場合の環境変数

```bash
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(realpath install/lib*)
export PYTHONPATH=$PYTHONPATH:$(realpath install/packages)
```

## scikit-build-core への CMake 変数の渡し方

```bash
pip install . -C cmake.define.<変数名>=<値>

# 例
pip install . -C cmake.define.WITH_CUDA=OFF
```

## CMake オプション

| オプション | 既定値 | 説明 |
|---|---|---|
| `WITH_CUDA` | **`Auto`** | `Auto` は **nvcc の有無を自動検出**して ON/OFF を決める。`ON`/`OFF` 明示も可 |
| `ISCE_CUDA_ARCHS` | `Auto` | `Auto` = 搭載 GPU を検出。`3.5,5.0,5.2` 形式で明示も可。`""` で既定 |
| `CMAKE_BUILD_TYPE` | **`RelWithDebInfo`** | `Debug` / `Release` / `RelWithDebInfo` のみ。他はエラーで停止 |
| `ISCE3_FETCH_DEPS` | scikit-build 経由: `OFF` / 直叩き: `ON` | 外部依存をビルド時にネットから取得するか |
| `ISCE3_FETCH_EIGEN` | 下記参照 | Eigen を取得 |
| `ISCE3_FETCH_GTEST` | 下記参照 | googletest を取得 |
| `ISCE3_FETCH_PYBIND11` | 下記参照 | pybind11 を取得 |
| `ISCE3_FETCH_PYRE` | 下記参照 | pyre を取得 |
| `ISCE3_WITH_CYTHON` | `OFF` | **削除済み機能**。ON にするとエラーになる |

### `ISCE3_FETCH_*` の落とし穴

これらは `cmake_dependent_option` で定義されている:

```cmake
cmake_dependent_option(ISCE3_FETCH_EIGEN "..." ON "ISCE3_FETCH_DEPS" OFF)
```

意味は「`ISCE3_FETCH_DEPS` が真なら既定 ON、**偽なら強制的に OFF**」。

つまり **`ISCE3_FETCH_DEPS=OFF` の状態で `ISCE3_FETCH_EIGEN=ON` を指定しても無視される。**
個別に有効化したい場合でも `ISCE3_FETCH_DEPS=ON` が必要で、
そうすると Eigen だけでなく googletest・pybind11・pyre もまとめてネットから取り直される。

### fetch 対象外の依存

`fftw` / `gdal` / `hdf5` / OpenMP / Python は **fetch されない**。
常に conda またはシステムから探される。OpenMP のみ任意扱い。

## その他の CMake の挙動

- **C++17** 必須（`CheckCXX()` で検証）
- **in-source ビルドは明示的に拒否される**（`AssureOutOfSourceBuilds()`）。
  必ず別ディレクトリを掘る
- **`ccache` が PATH にあれば自動で有効化**される。
  開発で再ビルドが頻繁になるなら `conda install -n isce3 ccache` を入れておくと効く
- CUDA 有効時、**CUDA 11 未満は `FATAL_ERROR` で停止**する
- バージョン文字列は `VERSION.txt` から生成され、git のコミットハッシュが付く
  （例: `0.26.0-dev+0d1600d8`）

## CUDA ビルド時の環境変数

| 変数 | 説明 |
|---|---|
| `CUDACXX` | CUDA コンパイラ (nvcc) のパス |
| `CUDAHOSTCXX` | CUDA コードのホストコンパイラ。`$CXX` と一致させる |

```bash
export CUDAHOSTCXX=$CXX
export CUDACXX=$CONDA_PREFIX/bin/nvcc
```

**注意**: `environment.yml` に CUDA パッケージは含まれていない。
CUDA ビルドをやるならシステムの nvcc に頼らず、
conda-forge の `cuda-nvcc` を環境に入れて conda 側で揃えるのが切り分けやすい。
nvcc はホスト GCC のバージョンに厳しく、対応範囲外だと
`unsupported GNU version` で止まる。

## 開発時に必要なツール（CONTRIBUTING.md より）

| ツール | 用途 | 備考 |
|---|---|---|
| `clang-format` | C++/CUDA の整形 | **pre-commit では自動実行されない。push 前に手動で走らせる** |
| `pre-commit` | フック実行 | `pre-commit install` が必要 |
| `detect-secrets` v1.4.0 | 秘密情報スキャン | pre-commit に設定されている唯一のフック |

`.clang-format` の要点: LLVM ベース / インデント 4 / タブ禁止 /
関数のみブレース改行 / include を 5 グループに自動並べ替え。

Python 側は PEP 8。PR のマージにはコアメンバー 2 名の承認が必要。
