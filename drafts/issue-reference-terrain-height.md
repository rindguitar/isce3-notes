<!-- upstream (isce-framework/isce3) に立てる issue の本文。英語。
     2026-09-20 改訂: #165 へのコメントではなく「単独の issue」として整えた。
     起票前に commit / 行番号 / issue 番号を再確認すること。 -->

# Title

GCOV/GSLC: geocoded `referenceTerrainHeight` is entirely NaN because a 1-D LUT is misdetected as 2-D

# Body

## Summary

In GCOV and GSLC products, the geocoded layer
`/science/LSAR/{GCOV,GSLC}/metadata/processingInformation/parameters/referenceTerrainHeight`
is filled entirely with NaN. The workflow still exits with status 0 and the only
visible symptom is a GDAL error on stderr, so it is easy to miss — the layer is
all-NaN in delivered products as well.

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

Fixing #165 would not change the outcome here: with real terrain heights in the
RSLC, the geocoded layer would still be all NaN.

## Versions

* Reproduced on `develop` @ 23f99329d (0.26.0-dev).
* **Independently reproduced by a colleague on `develop` @ 0c775d7ae** (a different
  machine, Docker + micromamba, GDAL 3.12.3, Python 3.13) — every observation below
  matched, including the error text and the pixel counts.
* The condition itself is unchanged: `git log -S` on the condition text returns only
  the commit that introduced it (07a033f4, 2025-05-15, *"Update GCOV & GSLC writer to
  geocode 1-D LUTs"*), and `git blame` attributes the current lines to that commit.

## Symptom

```
ERROR 5: tmp7acypfvt.vrt, band 1: Access window out of range in RasterIO().
Requested (0,0) of size 105x31 on raster of 31x1.
In isce3::io::Raster::get/setValue() - error in RasterIO.
```

The requested window is `len(slantRange) x len(zeroDopplerTime)`; the actual raster
(`31 x 1`) is the 1-D `referenceTerrainHeight` opened as an image.

## Reproduction

No NISAR data is required — the bundled test data reproduces it.

```console
$ ctest --test-dir <build> -R '^test\.python\.pkg\.nisar\.workflows\.gcov$' --output-on-failure
ERROR 5: ..., band 1: Access window out of range in RasterIO().   # printed 4 times
...
100% tests passed
```

The test **passes** while emitting the error four times (2 geocode modes x 2
noise-correction settings). Inspecting the product it just wrote, on the metadata
geogrid `(10, 41)`:

| layer | finite pixels |
|---|---|
| `calibrationInformation/frequencyA/elevationAntennaPattern/HH` | 178 / 410 |
| `calibrationInformation/frequencyA/noiseEquivalentBackscatter/HH` | 178 / 410 |
| `processingInformation/parameters/referenceTerrainHeight` | **0 / 410** |

Other layers on the same grid are populated; only this one is empty. The GSLC
workflow test behaves the same way (it shares this base class).

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
populated in the delivered products while this layer is not.

## Cause

`python/packages/nisar/products/writers/BaseL2WriterSingleInput.py`
(lines 1929-1937 as of 828ab91a3):

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

## Why this was not caught

* **The failure is not an exception.** GDAL prints to stderr and processing continues,
  so the workflow exits 0 with the layer left at its NaN fill value.
* **Nothing asserts on the layer.** The errors are emitted inside
  `GcovWriter.populate_metadata()`, while the test's only assertion compares the
  science data (`grids/frequencyA/HHHH`) against the noise power from the RSLC.
* **No test covers this dataset.** `referenceTerrainHeight` does not appear in the
  test *code* under `tests/` at all (it is present inside 11 `.h5` fixtures, but
  nothing checks it). The sibling 1-D path added in the same change — the
  range-varying crosstalk LUTs — *is* covered, and that path works.

## Impact

Observed on two NISAR L2 scenes with entirely different acquisition and processing
parameters (frequency A+B vs. B only, dual- vs. single-pol, 20 vs. 5 MHz, UTM vs.
polar stereographic, 20 vs. 80 m posting, steep terrain vs. flat ice shelf) — the
layer is all NaN in both.

The corresponding delivered products have an all-NaN layer as well (0 of 156,420 and
0 of 111,531 finite values), both produced with `softwareVersion = 0.25.16`:

```
NISAR_L2_PR_GCOV_028_168_D_126_0005_NASV_A_20260824T211408_20260824T211412_P05023_N_P_J_001
NISAR_L2_PR_GCOV_028_152_A_156_2005_DHDH_A_20260823T185248_20260823T185253_P05023_N_P_J_001
```

Only this metadata layer is affected; the science datasets are not.

## A candidate fix

Two decisions are conflated in that single condition: **whether the values must be
replicated along range** (a property of the dataset's rank) and **what the range axis
should be** (whether the group has a `slantRange`). Separating them fixes it:

```python
# the rank decides whether to tile
flag_luts_are_1d_az = (
    all([var in LUT_1D_AZ_DATASETS for var in input_ds_name_list]) and
    all([f'{input_h5_group_path}/{var}' in self.input_hdf5_obj and
         self.input_hdf5_obj[f'{input_h5_group_path}/{var}'].ndim == 1
         for var in input_ds_name_list]))

# the presence of slantRange decides the range axis
if slant_range_path in self.input_hdf5_obj:     # was: if not flag_luts_are_1d_az:
```

I cross-checked this against the 2-D path you already have, by rewriting
`referenceTerrainHeight` in `tests/data/envisat.h5` as an `(80, 240)` array (the same
values replicated along range) and running the code on it:

| input | unmodified | with the change |
|---|---|---|
| 1-D `(80,)` — today's data | **0 / 410** | **178 / 410** |
| 2-D `(80, 240)` — the planned format | 178 / 410 | **178 / 410** |

Both patched results match the unmodified 2-D run exactly (same valid-pixel mask,
maximum absolute difference 0.0). So the change produces today what the planned 2-D
LUT would produce later, and **leaves the 2-D case untouched**.

Also observed with the change: the GDAL errors disappear (6 → 0 across the GCOV and
GSLC tests), the science datasets are bit-identical, the other geocoded metadata
layers are unchanged, the range-vector (crosstalk) path still runs as before, and both
tests pass. Checking only the rank — without the second change — also removes the
errors but covers a narrower range extent (134/410), because the 1-D branch rebuilds
the range axis from the RSLC radar grid instead of using the axis already in the group.
I have not yet run the full ctest suite with the change.

I am happy to open a PR along these lines, together with a regression test asserting
that the geocoded layer contains valid values — there is currently no test covering
this dataset. Please let me know if you would prefer a different treatment of the axis
handling, or if this is already known and accepted for the time being (for instance
because the values are the placeholder zeros of #165 and the LUT is expected to become
2-D anyway) — in that case feel free to close this.
