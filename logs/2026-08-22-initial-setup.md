# 2026-08-22 ISCE3 開発環境の初期構築（WSL2 / CPU ビルド）

## 目的

ISCE3 の開発に参加するため、手元にビルド環境を作る。
単に使うだけなら conda-forge のリリース版で足りるが、自分の変更をビルドして
動かす必要があるので、クローンした `develop`（`0.26.0-dev`）をソースからビルドする。

## 結論（先に）

CPU 版のビルドとインストールに成功。`import isce3` が通り、リポジトリは汚れていない。

```
0.26.0-dev+0d1600d8
~/miniforge3/envs/isce3/lib/python3.12/site-packages/isce3/__init__.py
```

途中で 3 箇所詰まった。いずれも自分の環境の問題ではなく、
**`environment.yml` のバージョン指定に上限がないこと**と、
**システムに CUDA が入っていること**に起因する。詳細は後述。

## 前提環境

| 項目 | 値 |
|---|---|
| OS | WSL2 (Ubuntu 24.04, kernel 5.15 microsoft-standard-WSL2) |
| CPU | 8 コア |
| メモリ | 15 GB |
| ディスク空き | 905 GB |
| GPU | GeForce GTX 1060 6GB / Compute Capability **6.1** / driver 581.57 |
| システムの nvcc | `/usr/bin/nvcc` → **CUDA 12.0** (V12.0.140) |
| システムの gcc | 13.3.0 |
| クローン | `~/isce3`（fork 済み、`upstream` remote 設定済み、branch `develop`） |
| HEAD | `0d1600d8` |

## 選んだ手順

公式の [buildinstall](https://isce-framework.github.io/isce3/buildinstall/) には
3 通り書かれている。

1. conda-forge のリリース版（`isce3-cpu` / `isce3-cuda`）← 使うだけならこれ
2. `conda env create -f environment.yml` + `pip install .` ← **今回これ**
3. CMake 直叩き（Advanced）

開発参加が目的なので 1 は除外。2 は scikit-build-core がビルドを一時ディレクトリで
行うため**リポジトリ内に `build/` を作らない**という利点があり、まずはこれを選んだ。

## 手順

### 1. Miniforge の導入

conda 本体はプロジェクト固有ではないのでホームに入れる。

```bash
cd ~
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
bash Miniforge3-Linux-x86_64.sh -b -p ~/miniforge3
~/miniforge3/bin/conda init bash
```

`-b` は非対話インストール、`-p` は導入先。
`conda init bash` が `~/.bashrc` を書き換えるので、**シェルを開き直す**。

導入されたのは conda 26.5.3。チャネルは `conda-forge` のみで、
`environment.yml` の `nodefaults` 指定と一致していた。

### 2. 依存環境の作成

```bash
cd ~/isce3
conda env create -f environment.yml   # 環境名は yml 内で "isce3" と定義されている
conda activate isce3
```

conda 環境はディレクトリではなく名前で管理され、実体は `~/miniforge3/envs/isce3/` に入る。
npm の `node_modules` や venv と違い、プロジェクトディレクトリの中には作らない。

### 3. ビルドとインストール

```bash
pip install . -C cmake.define.WITH_CUDA=OFF
```

`-C cmake.define.<VAR>=<値>` は scikit-build-core が CMake に変数を渡す書式。
`WITH_CUDA=OFF` を明示する理由は後述（詰まった点 C）。

### 4. 確認

```bash
python3 -c 'import isce3; print(isce3.__version__)'   # → 0.26.0-dev+0d1600d8
git -C ~/isce3 status --short                         # → 空。リポジトリは汚れていない
```

サブモジュールは 22 個:

```
antenna, atmosphere, cal, container, core, ext, extisce3, focus, geocode,
geogrid, geometry, image, io, matchtemplate, math, noise, polsar, product,
signal, solid_earth_tides, splitspectrum, unwrap
```

`isce3.cuda` は存在しない（`WITH_CUDA=OFF` なので想定どおり）。

---

## 詰まった点と対処

### A. `conda: command not found`

`conda init bash` の直後、まだ conda が使えなかった。

**原因**: `conda init` は `~/.bashrc` に初期化ブロックを書き込むだけなので、
既に開いているシェルには反映されない。

**対処**: シェルを開き直す（または `source ~/.bashrc`）。

**補足**: 非対話シェルではこれでも解決しない。Ubuntu の `~/.bashrc` は冒頭で
「非対話シェルなら `return`」としており、conda の初期化行（123 行目付近）に到達しない。
スクリプトや自動化から使う場合は毎回これを先頭に置く:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
```

### B. Eigen のバージョン不一致でビルド失敗 ★今回の主因

```
CMake Error at extern/CMakeLists.txt:5 (find_package):
  Could not find a configuration file for package "Eigen3" that is compatible
  with requested version "3.3.7".
    .../share/eigen3/cmake/Eigen3Config.cmake, version: 5.0.1
      The version found is not compatible with the version requested.
```

**原因**: `environment.yml` の指定が `eigen>=3.3` で**上限がない**ため、
conda が最新の **Eigen 5.0.1** を入れた。一方 ISCE3 は `find_package(Eigen3 3.3.7)`
を要求している。Eigen の `Eigen3ConfigVersion.cmake` は
**「メジャーバージョンが一致すれば互換」**という判定方式なので、
メジャー 5 はメジャー 3 の要求を満たさない。

数値としては `5.0.1 > 3.3.7` だが、**「新しければ通る」わけではない**のがポイント。

**対処**:

```bash
conda install -n isce3 'eigen<4'      # → 3.4.0 が入る
```

**採らなかった代替案**: ISCE3 自身に Eigen を取得させる方法もあるが、
`ISCE3_FETCH_EIGEN` は `cmake_dependent_option` で定義されており、
親の `ISCE3_FETCH_DEPS` が OFF だと**強制的に OFF になる**ため単独指定は効かない。
有効化するには `ISCE3_FETCH_DEPS=ON` が必要で、そうすると googletest・pybind11・pyre も
まとめてネットから取り直すことになる。

### C. nvcc が自動検出されて CUDA ビルドに入ってしまう

**原因**: `CMakeLists.txt` の `WITH_CUDA` は既定値が **`Auto`** で、
nvcc を見つけると自動的に CUDA ビルドへ切り替わる。
このマシンには `/usr/bin/nvcc`（CUDA 12.0）が入っていたため、放置すると CUDA ビルドが走る。

**なぜ避けたか**:

- `environment.yml` に CUDA パッケージが含まれていない。
  つまりこの組み合わせはプロジェクトが想定・テストしている構成ではない。
- システムの nvcc（apt 版）と conda の `cxx-compiler` が混ざる。
  実際、ビルドログでは conda 側の **GCC 15.3.0** が使われていた。
  CUDA 12.0 が公式サポートするホスト GCC は 12.x までとされるため、
  この組み合わせは通らない見込み（未検証。初回は切り分けを優先して回避した）。
- CUDA ビルドは単純に時間がかかる。

**対処**: `-C cmake.define.WITH_CUDA=OFF` を明示。

**補足**: GPU 自体は CC 6.1 で、CUDA 12.0 でも（deprecated 扱いだが）使用可能。
問題はコンパイラの組み合わせだけ。GPU 対応をやるなら、
システムの nvcc ではなく conda-forge の新しい `cuda-nvcc` を環境に入れる方向で切り分ける。

---

## 残課題

### 1. `ctest` が実行できない ← 優先度高

`pip install .` はビルドを一時ディレクトリで行って破棄するため、
テストを走らせる手段が残らない。CONTRIBUTING.md は
「PR を出す前にローカルでテストを通すこと」を要求しているので、ここは埋める必要がある。

→ **CMake 直叩きビルド**に移行する。ビルドツリーを残せるので `ctest` が使え、
差分ビルドも効く。ただし `build/` をリポジトリ内に作ることになるので、
`.gitignore` の確認が必要。

### 2. コード変更のたびに再インストールが必要

`pip install .` は editable インストールではない。ソースを 1 行変えるたびに
`pip install .` をやり直す必要があり、開発サイクルとしては現実的でない。
これも CMake 直叩きへの移行で解消する。

### 3. GPU (CUDA) 未対応

上記 C のとおり。conda-forge の `cuda-nvcc` を使う方向で別途取り組む。

### 4. HDF5 が 2.x で入っている（潜在リスク）

`hdf5` が **2.2.0** で入った。`environment.yml` の指定は `hdf5>=1.10.2,!=1.14.0` で、
これも上限がないためメジャー 2 系が入っている。
ビルドと import は通っているが、Eigen と同じ「上限指定なし」問題の別の現れ。
**実データを扱い始めて HDF5 由来の不具合が出たら、まずここを疑う。**

### 5. ドキュメントの記述の食い違い（要確認）

- `README.md` は conda パッケージ名を `isce3-cpu` / `isce3-cuda` と書いているが、
  `docs/buildinstall.md` は `isce3` と書いている
- `CONTRIBUTING.md` が参照している `install_linux.html` / `install_osx.html` は、
  現行のドキュメント構成（`buildinstall.md`）と食い違っており、リンク切れの可能性が高い

いずれも upstream に既知の issue がある可能性があるので、報告する前にまず既存 issue を確認する。

---

## 参考

- 公式ビルド手順: https://isce-framework.github.io/isce3/buildinstall/
- CONTRIBUTING: `~/isce3/CONTRIBUTING.md`
- ビルドオプションの詳細: [../reference/build-options.md](../reference/build-options.md)
- 確定したバージョン一覧: [../reference/environment.md](../reference/environment.md)
