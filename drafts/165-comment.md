<!-- #165 に残すコメントの下書き。英語。貼る前に数値と commit を再確認すること -->

While reading this issue I ran into what looks like a second, separate problem with
the same dataset, and I would like to ask whether it is intended before filing
anything separately.

**Question:** in GCOV (and GSLC, which shares the writer base class), the geocoded
layer `.../metadata/processingInformation/parameters/referenceTerrainHeight` comes
out entirely NaN, and the GCOV workflow test passes while printing four
`Access window out of range in RasterIO()` errors. Is that known and accepted for
now — for example because the values are the placeholder zeros this issue is about —
or is it a separate defect worth its own issue?

To be clear about the relationship to this issue: the failure below is in a different
code path (the L2 writer geocoding the LUT, not the RSLC writer filling it), and it
would still produce NaN even if the RSLC contained real terrain heights.

### What I observe

Reproduced with the bundled test data only — no NISAR data needed. The build is
23f99329d; `BaseL2WriterSingleInput.py` is byte-identical at the current `develop`
(f42cea75b), and has not changed since 07a033f4 (2025-05-15):

```console
$ ctest -R '^test\.python\.pkg\.nisar\.workflows\.gcov$' -V
ERROR 5: tmp9v1bgg2s.vrt, band 1: Access window out of range in RasterIO().
Requested (11,30) of size 229x20 on raster of 80x1.        # printed 4 times
1/1 Test #212: test.python.pkg.nisar.workflows.gcov ...   Passed    5.64 sec
100% tests passed
```

In the product the test just wrote, on the metadata geogrid `(10, 41)`:

| layer | finite pixels |
|---|---|
| `calibrationInformation/frequencyA/elevationAntennaPattern/HH` | 178 / 410 |
| `calibrationInformation/frequencyA/noiseEquivalentBackscatter/HH` | 178 / 410 |
| `processingInformation/parameters/referenceTerrainHeight` | **0 / 410** |

The 1-D azimuth branch never runs. Its own warning never appears, while the
range-vector branch added in the same change runs normally:

```
"Geolocating one dimensional dataset: ... (rg. vector)"   x4   (crosstalk LUTs)
"Geolocating one dimensional dataset: ... (az. vector)"   x0   (referenceTerrainHeight)
```

### Why it happens

`BaseL2WriterSingleInput.geocode_lut()` decides the rank of the LUT from the presence
of a sibling `slantRange` dataset. But `slantRange` is the shared range axis of that
group — it belongs to the genuinely 2-D LUTs stored next to it, and `require_lut_axes()`
in the RSLC writer creates it unconditionally. In `tests/data/envisat.h5`:

```
processingInformation/parameters/
    referenceTerrainHeight   (80,)        <- 1-D
    effectiveVelocity        (80, 240)    <- 2-D, needs both axes
    zeroDopplerTime          (80,)
    slantRange               (240,)       <- axis of the 2-D LUT above
```

So `flag_luts_are_1d_az` is False even though the dataset is 1-D, and the 1-D array is
opened as a raster (GDAL reports `Size is 80, 1`) while a `240 x 80` window is
requested. Evaluating that expression with h5py alone, outside ISCE3, gives the same
answer for every product I have: the bundled `envisat.h5` `(80,)`, and two NISAR RSLCs
`(79,)` and `(31,)` — all 1-D, all classified as 2-D.

The delivered products show it too. Both of these have an all-NaN layer
(0 of 156,420 and 0 of 111,531 finite), and both record `softwareVersion = 0.25.16`:

```
NISAR_L2_PR_GCOV_028_168_D_126_0005_NASV_A_20260824T211408_20260824T211412_P05023_N_P_J_001
NISAR_L2_PR_GCOV_028_152_A_156_2005_DHDH_A_20260823T185248_20260823T185253_P05023_N_P_J_001
```

### If it is not intended

Checking the rank of the dataset itself instead of a sibling makes the error
disappear (4 -> 0 in both the GCOV and GSLC tests), populates the layer (134 of 410
on `envisat.h5`, the rest being outside the LUT extent), keeps the existing tests
passing, and leaves the science datasets bit-identical. I am happy to open a separate
issue with the details and a PR with a regression test — there is currently no test
covering this dataset. Just let me know which you prefer, and whether keying on the
rank is acceptable given the plan to move to a 2-D LUT.
