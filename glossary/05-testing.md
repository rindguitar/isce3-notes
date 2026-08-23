# 05. テストまわり — ctest / gtest / pytest

## なぜテストが要るのか

**自分の変更が既存の機能を壊していないかを機械的に確認するため。**

ISCE3 は 237 件のテストを持っている。1 行変えたあとにこれを流せば、
壊したかどうかが 10 分で分かる。

CONTRIBUTING.md は「PR を出す前にローカルでテストを通すこと」を要求している。

## 3 層構造になっている

ISCE3 のテストは 3 つの仕組みが重なっている。

```
ctest  ─┬─ gtest   （C++ のテストを実行）
        └─ pytest  （Python のテストを実行）
```

`ctest` は**取りまとめ役**で、実際のテスト本体は gtest か pytest が動かす。

### ctest

CMake に付属するテストランナー。**ビルドディレクトリの中で動く。**

```bash
ctest --test-dir ~/isce3-build --output-on-failure
```

| オプション | 意味 |
|---|---|
| `--test-dir <パス>` | どのビルドディレクトリのテストか |
| `--output-on-failure` | **失敗したものだけ詳細を表示**。これが無いと原因が分からない |
| `-R <正規表現>` | 名前が一致するテストだけ実行 |
| `-E <正規表現>` | 名前が一致するテストを除外 |
| `--rerun-failed` | **前回失敗したものだけ再実行**。切り分けで重宝する |
| `--timeout <秒>` | 1 テストあたりの上限。ハング対策 |
| `-j<N>` | 並列実行 |

今回 613 秒かかる全実行を毎回繰り返さずに済んだのは `--rerun-failed` のおかげ。

### 出力の読み方

```
99% tests passed, 2 tests failed out of 237

The following tests FAILED:
         41 - test.cxx.isce3.geometry.geometry.geometry (Failed)
        211 - test.python.pkg.nisar.workflows.stage_dem (Failed)
```

左の数字は**テスト番号**で、`-I` オプションで指定できる。
ただし番号は絶対ではないので、名前で指定するほうが安全。

テスト名の構造:

```
test.cxx.isce3.geometry.geometry.geometry
     ^^^ C++ のテスト

test.python.pybind.io.gdal.raster
     ^^^^^^ ^^^^^^ Python から pybind バインディングをテスト

test.python.pkg.nisar.workflows.stage_dem
            ^^^ Python パッケージのテスト
```

### 基準値 (baseline) の重要性

**「元から落ちているテスト」を把握しておく。**

この環境の基準値は **235/237**。落ちる 2 件は原因も特定済み。
これを知らないと、自分の変更で壊したのか元からなのか判別できない。

> 3 件以上落ちたら、自分の変更を疑う。

## gtest (GoogleTest)

C++ 用のテストフレームワーク。

### 出力の読み方

```
[ RUN      ] GeometryTest.GeoToRdr
/home/rindguitar/isce3/tests/cxx/isce3/geometry/geometry/geometry.cpp:143: Failure
Expected equality of these values:
  stat
    Which is: 0
  1
[  FAILED  ] GeometryTest.GeoToRdr (3 ms)
```

- `GeometryTest` が**テストスイート**、`GeoToRdr` が**テストケース**
- `geometry.cpp:143` が失敗した場所
- `Expected equality of these values` は「この 2 つが等しいはず」
  - `stat` の実際の値が `0`
  - 期待値が `1`

### アサーション (assertion)

**「こうなっているはず」を書いた検査。** 満たされないとテストが失敗する。

| 書き方 | 意味 |
|---|---|
| `ASSERT_EQ(a, b)` | `a == b`。失敗したら**その場で中断** |
| `EXPECT_EQ(a, b)` | `a == b`。失敗しても**続行** |
| `ASSERT_NEAR(a, b, tol)` | `a` と `b` の差が `tol` 以内 |

`ASSERT_NEAR` があるのは、**浮動小数点は厳密比較できない**から。
計算順序が変わるだけで最下位桁が変わるため、許容誤差 (tolerance) を決めて比較する。

今回問題になった箇所:

```cpp
int stat = isce3::geometry::geo2rdr(..., 1.0e-10, 50, 10.0);
ASSERT_EQ(stat, 1);
```

`1.0e-10` が**収束の許容誤差**、`50` が**最大反復回数**。
`stat` は「収束したか」を表す戻り値で、`1` が成功、`0` が失敗。
つまり「50 回繰り返しても 1e-10 の精度に届かなかった」という失敗だった。

### `unknown file: Failure`

失敗場所が表示されないパターン。
**テスト本体の外（初期化処理など）で例外が投げられた**ことを意味する。

今回の GDAL 関連の失敗がこれで、
`C++ exception with description "..." thrown in the test body` と続いていた。

## pytest

Python 用のテストフレームワーク。

### 出力の読み方

```
    def test_slantrange_from_lookvec(self):
        ...
>       sr = geom.slantrange_from_lookvec(self._sc_pos_ecef, pnt_ecef)
E       TypeError: slantrange_from_lookvec(): incompatible function arguments.

/home/.../pntintersect.py:42: TypeError
```

- `>` が付いている行が**失敗した行**
- `E` が付いている行が**エラー内容**
- 最後にファイル名と行番号

pytest は失敗箇所の**前後のソースコードも表示する**ので、
文脈が分かりやすい代わりに出力が長くなる。

### `short test summary info`

末尾のまとめ。どれが FAILED でどれが PASSED か一覧になる。
**まずここを見て、それから詳細に戻る**のが速い。

### パラメータ化テスト

```
FAILED .../stage_dem.py::test_dem_description[1.0]
FAILED .../stage_dem.py::test_dem_description[1.1]
FAILED .../stage_dem.py::test_dem_description[1.2]
```

`[1.0]` `[1.1]` は**同じテストを別の入力で繰り返した**もの。
`@pytest.mark.parametrize` で書かれている。
3 つ並んでいても実質 1 つの問題であることが多い。

## flaky（フレーキー）なテスト

**実行するたびに結果が変わるテスト。** 通ったり落ちたりする。

原因は多くの場合タイミング依存（並列処理、待ち時間、ファイル I/O の順序）。

今回 `test.python.pkg.isce3.io.background` がこれだった。
初回は失敗、再実行で成功。名前から**バックグラウンド I/O のテスト**と推測でき、
タイミングに左右されるのは自然。

**flaky なテストは「落ちた」だけでは判断できない。まず再実行する。**

## テストが大量に落ちたときの判断

ISCE3 の公式ドキュメントにこう書かれている:

> 多数のテストが失敗する場合、Python パッケージの不足か設定ミスのサイン

つまり:

| 失敗数 | 疑うべきもの |
|---|---|
| 大半 | **環境の不備**。依存の不足や設定ミス |
| 数件 | **個別の原因**。1 件ずつ切り分ける |

今回は 237 件中 7 件だったので後者と判断し、実際に 4 系統の別々の原因に分かれた。

## 切り分けの手順（今回やったこと）

1. **全体像を見る** — 何件中何件落ちたか。割合で方針が変わる
2. **詳細を取る** — `--rerun-failed --output-on-failure` で失敗分だけ再実行
3. **グループ化する** — 同じエラーメッセージのものはまとめて 1 つの原因
4. **仮説を立てる** — エラーメッセージ自体が対処法を書いていることも多い
5. **1 つだけ変えて検証する** — 同時に 2 つ変えると、どちらが効いたか分からなくなる

4 の例: GDAL のエラーは

```
If you want to allow it, define the GDAL_MEM_ENABLE_OPEN configuration option to YES
```

と対処法まで書いてくれていた。**エラーメッセージは最後まで読む。**
