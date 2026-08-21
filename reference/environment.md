# 環境スナップショット

最終更新: 2026-08-22 / ISCE3 `0.26.0-dev+0d1600d8`（HEAD = `0d1600d8`）

状況が変わったらこのファイルを上書き更新する。

## マシン構成

| 項目 | 値 |
|---|---|
| OS | WSL2 (Ubuntu 24.04, kernel 5.15 microsoft-standard-WSL2) |
| CPU | 8 コア |
| メモリ | 15 GB |
| GPU | GeForce GTX 1060 6GB / Compute Capability 6.1 / driver 581.57 |
| システム nvcc | `/usr/bin/nvcc` → CUDA 12.0 (V12.0.140) |
| システム gcc | 13.3.0 |
| conda | Miniforge / conda 26.5.3 / `~/miniforge3` |
| チャネル | `conda-forge` のみ |

※ ドライバ番号などは参考値。

## パスの配置

```
~/miniforge3/              conda 本体（全プロジェクト共通）
  └── envs/isce3/          ISCE3 の実行環境
~/isce3/                   upstream の fork をクローンしたもの
~/isce3-notes/             このメモ
```

## 実際に解決された依存バージョン

`conda env create -f environment.yml` の結果（Eigen のみ手動で降格）。

| パッケージ | 入った版 | `environment.yml` の指定 | 備考 |
|---|---|---|---|
| python | 3.12.13 | `python>=3.8` | |
| **eigen** | **3.4.0** | `eigen>=3.3` | **手動で `eigen<4` に降格。** 既定では 5.0.1 が入りビルド失敗 |
| **hdf5** | **2.2.0** | `hdf5>=1.10.2,!=1.14.0` | ⚠️ メジャー 2 系。上限指定がないため。潜在リスク |
| gdal | 3.13.3 | `gdal>=3.6` | |
| fftw | 3.3.11 (nompi) | `fftw>=3.3` | |
| numpy | 1.26.4 | `numpy>=1.20` | |
| scipy | 1.17.1 | `scipy!=1.10.0` | |
| shapely | 2.1.2 | `shapely>=2` | |
| pyre | 1.12.6 | `pyre>=1.12.5` | |
| snaphu | 0.4.1 | `snaphu>=0.4` | 位相アンラップ |
| gcc (conda) | 15.3.0 | `cxx-compiler`（無指定） | ⚠️ 非常に新しい |
| cmake | 4.4.2 | `cmake>=3.18` | ⚠️ CMake 4 系 |
| scikit-build-core | 1.0.3 | （ビルド時に pip が取得） | |

### バージョン指定に上限がない問題

`environment.yml` は**ほぼ全て下限のみの指定**で、上限がない。
そのため conda は常に最新を入れようとし、メジャーバージョンが上がった依存で壊れる。

実際に踏んだのが Eigen（3 系を期待しているところに 5.0.1）。
`hdf5`・`cmake`・`cxx-compiler` も同じ構造なので、
**ビルドや実行が壊れたときは、まず依存のメジャーバージョンを疑う。**

## `environment.yml` の全依存（参考）

チャネル: `conda-forge` + `nodefaults` / 環境名: `isce3`

**ビルド**: `cmake>=3.18`, `ninja`, `cxx-compiler`
**C++ ライブラリ**: `eigen>=3.3`, `fftw>=3.3`, `gdal>=3.6`, `hdf5>=1.10.2,!=1.14.0`,
`libgdal-hdf5`, `libgdal-netcdf`, `pybind11>=2.5`, `pyre>=1.12.5`, `gtest>=1.10`, `gmock>=1.10`
**Python 基盤**: `python>=3.8`, `numpy>=1.20`, `scipy!=1.10.0`, `h5py>=3`, `shapely>=2`
**SAR 処理**: `pyaps3>=0.3`（大気位相補正）, `raider-base>=0.4.5`（対流圏遅延）,
`pysolid>=0.2`（固体地球潮汐）, `snaphu>=0.4`（位相アンラップ）
**その他**: `ruamel.yaml`, `yamale`（設定検証）, `backoff`, `pytest`

`pip` は明記されていない。無い場合は `conda install -n isce3 pip` を足す。
CUDA 関連は**一切含まれていない**。

## 環境の再現手順

```bash
source ~/miniforge3/etc/profile.d/conda.sh
cd ~/isce3
conda env create -f environment.yml
conda install -n isce3 'eigen<4'          # ← 必須。これが無いとビルドが通らない
conda activate isce3
pip install . -C cmake.define.WITH_CUDA=OFF
python3 -c 'import isce3; print(isce3.__version__)'
```
