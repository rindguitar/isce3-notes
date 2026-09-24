<!-- upstream (isce-framework/isce3) に立てる issue の本文。
     下の Title と Body をそのまま貼る。編集はこのファイルで行う。
     2026-09-23 改訂: notes PR #2 のレビュー指摘 1〜5 を反映。 -->

## Title（issue のタイトル欄に入れる）

GCOV/GSLC: geocoded `referenceTerrainHeight` is entirely NaN because a 1-D LUT is misdetected as 2-D

---

## Body（issue の本文欄に入れる。ここから下をそのまま貼る）

## Summary

In GCOV and GSLC products, the geocoded layer
`/science/LSAR/{GCOV,GSLC}/metadata/processingInformation/parameters/referenceTerrainHeight`
is filled entirely with NaN. The workflow still exits with status 0 and the only
visible symptom is a GDAL error on stderr, so it is easy to miss — the layer is
all-NaN in products distributed via the ASF DAAC as well.

The cause is in `BaseL2WriterSingleInput.geocode_metadata_group()` (reached via
`geocode_lut()`): the rank of the LUT is inferred from the presence of a sibling
`slantRange` dataset, but that dataset is the range axis shared by the *other*,
genuinely 2-D LUTs in the same group. The RSLC writer always creates it, so the
1-D branch is never taken.

**Relationship to #165** — these are different problems in different code paths:

| | #165 | this report |
|---|---|---|
| Where | `metadata/sourceData/...` | `metadata/processingInformation/parameters/...` |
| Symptom | values are all **zero** | values are all **NaN** |
| Cause | the RSLC writer fills a placeholder vector of zeros | the L2 writer misdetects the rank when geocoding |

Populating the current 1-D LUT with real terrain heights would not fix the rank
detection; the geocoded layer would still be all NaN.

## Is this known or intended?

The values are still the placeholder zeros of #165, and the comment in the code says
the LUT is expected to become 2-D in the future. If the 1-D case is already tracked
somewhere, a pointer is all I need — I could not find a public record of it, which is
the main reason for writing this up.

## Versions

* Reproduced on `develop` @ `0c775d7ae` (0.26.0-dev).
* **Independently reproduced by a colleague** on the same commit, on a different
  machine (Docker + micromamba, GDAL 3.12.3). The unmodified-fixture observations
  matched — error text, `(az. vector)` count, and the pixel counts below. Details:
  https://github.com/rindguitar/isce3-notes/issues/1#issuecomment-5738541714
* The condition itself is unchanged since it was introduced in 07a033f4 (2025-05-15,
  *"Update GCOV & GSLC writer to geocode 1-D LUTs"*):

  ```console
  $ git log -S 'slant_range_path not in' -- python/packages/nisar/products/writers/BaseL2WriterSingleInput.py
  07a033f4 Update GCOV & GSLC writer to geocode 1-D LUTs
  ```

  `git blame` attributes the current lines to the same commit, and the condition is
  still present at `507208508` (today's `develop`).

## Symptom

```
ERROR 5: tmpXXXXXXXX.vrt, band 1: Access window out of range in RasterIO().
Requested (11,30) of size 229x20 on raster of 80x1.
```

The reader assumes a `len(zeroDopplerTime) x len(slantRange)` raster and requests
blocks of it (`11 + 229 = 240 = len(slantRange)`); the actual raster is the 1-D
`referenceTerrainHeight` opened as an image, `80 x 1`.

## Reproduction

No NISAR data is required — the bundled test data reproduces it.
The first check needs no build and shows the misdetection itself; the second runs the
workflow test and shows the resulting all-NaN layer.

### The misdetection itself (h5py only, no build)

From the repository root:

```python
import h5py

G = '/science/LSAR/SLC/metadata/processingInformation/parameters'
with h5py.File('tests/data/envisat.h5', 'r') as f:
    d = f[f'{G}/referenceTerrainHeight']
    print(d.ndim, d.shape)            # 1 (80,)
    print(f'{G}/slantRange' in f)     # True  -> the writer's condition below is False

    # the condition, copied from BaseL2WriterSingleInput.py
    LUT_1D_AZ_DATASETS = ['referenceTerrainHeight']
    flag_luts_are_1d_az = (all(v in LUT_1D_AZ_DATASETS for v in ['referenceTerrainHeight'])
                           and f'{G}/slantRange' not in f)
    print(flag_luts_are_1d_az)        # False -> the 1-D dataset is treated as 2-D
```

GDAL sees the same thing — the 1-D dataset opens as an 80x1 image, the genuine 2-D LUT
next to it as 240x80 (GDAL prints width, height):

```console
$ P=science/LSAR/SLC/metadata/processingInformation/parameters
$ gdalinfo "HDF5:\"tests/data/envisat.h5\"://$P/referenceTerrainHeight" | grep 'Size is'
Size is 80, 1
$ gdalinfo "HDF5:\"tests/data/envisat.h5\"://$P/effectiveVelocity" | grep 'Size is'
Size is 240, 80
```

### The all-NaN layer (ctest)

`-V` is required: the test passes, and CTest hides a passing test's output otherwise.

```console
$ ctest --test-dir <build> -R '^test\.python\.pkg\.nisar\.workflows\.gcov$' \
        --output-on-failure -V --no-tests=error
ERROR 5: tmpXXXXXXXX.vrt, band 1: Access window out of range in RasterIO().
Requested (11,30) of size 229x20 on raster of 80x1.        # printed 4 times
...
100% tests passed
```

The test **passes** while emitting the error four times (2 geocode modes x 2
noise-correction settings). The products it wrote are left in
`<build>/tests/python/packages/nisar/workflows/`; counting finite pixels on the
metadata geogrid `(10, 41)`:

```python
import h5py, numpy as np

M = '/science/LSAR/GCOV/metadata'
with h5py.File('gcov_envisat_area_noise_correction_false.h5', 'r') as h:
    a = h[f'{M}/processingInformation/parameters/referenceTerrainHeight'][()]
    print(a.shape, int(np.isfinite(a).sum()), a.size)          # (10, 41) 0 410
    for name in ('elevationAntennaPattern', 'noiseEquivalentBackscatter'):
        b = h[f'{M}/calibrationInformation/frequencyA/{name}/HH'][()]
        print(name, int(np.isfinite(b).sum()), b.size)         # 178 410
```

| layer | finite pixels |
|---|---|
| `calibrationInformation/frequencyA/elevationAntennaPattern/HH` | 178 / 410 |
| `calibrationInformation/frequencyA/noiseEquivalentBackscatter/HH` | 178 / 410 |
| `processingInformation/parameters/referenceTerrainHeight` | **0 / 410** |

Other layers on the same grid are populated; only this one is empty. Running the same
command with `gslc` instead of `gcov` shows the same thing in `x_out.h5` / `y_out.h5`
(two errors, 0/410), since both writers share this base class.

The 1-D azimuth branch never runs — its own warning never appears, while the
range-vector branch added in the same change runs normally:

```
"Geolocating one dimensional dataset: ... (rg. vector)"   x4   (crosstalk LUTs)
"Geolocating one dimensional dataset: ... (az. vector)"   x0   (referenceTerrainHeight)
```

## What the product spec expects

`products/XML/L2/nisar_L2_GCOV.xml` defines the two copies of this dataset with
different shapes, so the 1-D → 2-D conversion is the documented job of this code:

| path | shape in the spec | rank |
|---|---|---|
| `sourceData/.../referenceTerrainHeight` | `sourceDataDopplerCentroidTimeLength` | 1-D |
| `processingInformation/parameters/.../referenceTerrainHeight` | `dopplerCentroidShape` | 2-D |

The geocoded one is annotated *"Reference terrain height as a function of map
coordinates"* with `_FillValue="nan"`, i.e. an all-NaN layer means "no valid data
anywhere". Note that `dopplerCentroid`, which the spec gives the *same* shape, is
populated in the products I looked at while this layer is not.

## Cause

https://github.com/isce-framework/isce3/blob/0c775d7ae/python/packages/nisar/products/writers/BaseL2WriterSingleInput.py#L1944-L1952

```python
# The `referenceTerrainHeight` LUT can be either a 1-D LUT (along
# azimuth) or a 2-D LUT. So, to determine the type of the LUT to
# geocode, check the constant `LUT_1D_AZ_DATASETS`, but also verify if
# `slantRange` is present within the LUT group to confirm its dimensions.
slant_range_path = f'{input_h5_group_path}/slantRange'
flag_luts_are_1d_az = (all([var in LUT_1D_AZ_DATASETS
                           for var in input_ds_name_list]) and
                       slant_range_path not in self.input_hdf5_obj)
```

`slantRange` is not specific to `referenceTerrainHeight`: it is the shared range axis
of the group, required by the 2-D LUTs stored alongside it, and `require_lut_axes()`
in the RSLC writer creates it unconditionally, immediately after
`referenceTerrainHeight` is written. In the bundled `tests/data/envisat.h5`:

```
/science/LSAR/SLC/metadata/processingInformation/parameters/
    referenceTerrainHeight   (80,)        <- 1-D, along azimuth
    effectiveVelocity        (80, 240)    <- 2-D, needs both axes
    zeroDopplerTime          (80,)
    slantRange               (240,)       <- the range axis of the 2-D LUT above
```

So `slant_range_path not in self.input_hdf5_obj` is always False, and
`flag_luts_are_1d_az` cannot become True for an RSLC produced by ISCE3 — even though
the comment at the top of the same file states that the 1-D case is the current one:

```python
# For now, `referenceTerrainHeight` is a 1-D Dataset, varying with
# azimuth time. In future, we plan to reimplement this as a 2-D Dataset,
# but in the meantime the code needs to be able to handle the 1-D case.
LUT_1D_AZ_DATASETS = ['referenceTerrainHeight']
```

The code then reads the 1-D dataset as a 2-D raster of
`len(zeroDopplerTime) x len(slantRange)`, which is what the GDAL error reports.

## Impact

The layer is all NaN in the two NISAR L2 products I inspected, which have entirely
different acquisition and processing parameters (frequency A+B vs. B only, dual- vs.
single-pol, 20 vs. 5 MHz, UTM vs. polar stereographic, 20 vs. 80 m posting, steep
terrain vs. flat ice shelf):

| granule (distributed via ASF DAAC) | finite pixels | `softwareVersion` |
|---|---|---|
| `NISAR_L2_PR_GCOV_028_168_D_126_0005_NASV_A_20260824T211408_20260824T211412_P05023_N_P_J_001` | 0 / 156,420 | 0.25.16 |
| `NISAR_L2_PR_GCOV_028_152_A_156_2005_DHDH_A_20260823T185248_20260823T185253_P05023_N_P_J_001` | 0 / 111,531 | 0.25.16 |

Their error message differs only in the array sizes
(`Requested (0,0) of size 105x31 on raster of 31x1` for the first one), which are the
axis lengths of those products.

I have not looked beyond these two products, so I cannot say how general this is. In
the GCOV and GSLC workflow tests the science datasets are unaffected — only this
metadata layer changes.

## A candidate fix

Two decisions are conflated in that single condition: **whether the values must be
replicated along range** (a property of the dataset's rank) and **what the range axis
should be** (whether the group has a `slantRange`). Separating them:

```python
# the rank decides whether to tile
flag_luts_are_1d_az = (
    all([var in LUT_1D_AZ_DATASETS for var in input_ds_name_list]) and
    all([f'{input_h5_group_path}/{var}' in self.input_hdf5_obj and
         self.input_hdf5_obj[f'{input_h5_group_path}/{var}'].ndim == 1
         for var in input_ds_name_list]))

# use the group's own range axis when it has one
if not flag_luts_are_1d_az or slant_range_path in self.input_hdf5_obj:
```

The `not flag_luts_are_1d_az or ...` form matters: a 2-D LUT whose group has no
`slantRange` still takes the original path and is rejected (or skipped, under
`skip_if_not_present`) rather than silently falling back to a synthesized axis.
So genuine 2-D input keeps its existing behaviour, and malformed input with a missing
axis is still refused.

I checked this against the 2-D path you already have, by rewriting
`referenceTerrainHeight` in `tests/data/envisat.h5` as an `(80, 240)` array (the same
values replicated along range) and running the code on it, at `0c775d7ae`:

| input | unmodified | with the change |
|---|---|---|
| 1-D `(80,)` — today's data | **0 / 410** | **178 / 410** |
| 2-D `(80, 240)` — the planned format | 178 / 410 | **178 / 410** |

Both patched results match the unmodified 2-D run exactly (same valid-pixel mask,
maximum absolute difference 0.0). So for these inputs the change produces what the
planned 2-D LUT would produce, and does not alter the 2-D case.

Also observed with the change, on the bundled fixtures: the GDAL errors disappear
(6 → 0 across the GCOV and GSLC tests), the science datasets are bit-identical, the
other geocoded metadata layers on the same grid are unchanged, and the range-vector
(crosstalk) path still runs as before. I have not yet run the full ctest suite with
the change.

I can submit a focused PR with regression tests for the 1-D and 2-D cases.
Is there an existing issue or a preferred approach for this axis handling?
