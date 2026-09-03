<!-- upstream (isce-framework/isce3) へ貼る本文。英語。起票前にリンク行の番号を確認すること -->

# Title

GCOV/GSLC: geocoded `referenceTerrainHeight` is entirely NaN because a 1-D LUT is misdetected as 2-D

# Body

## Summary

In GCOV and GSLC products, the geocoded layer
`/science/LSAR/{GCOV,GSLC}/metadata/processingInformation/parameters/referenceTerrainHeight`
is filled entirely with NaN. The workflow still exits with status 0, and the only
visible symptom is a GDAL error printed to stderr, so this is easy to miss.

The cause is in `BaseL2WriterSingleInput.geocode_lut()`: the rank of the LUT is
inferred from the presence of a sibling `slantRange` dataset, but that dataset is
the range axis shared by the *other*, genuinely 2-D LUTs stored in the same group.
It is always present in an RSLC written by ISCE3, so the 1-D branch is never taken.

**This is not a duplicate of #165.** #165 concerns the *values* written by the RSLC
writer (a vector of zeros) propagating into `metadata/sourceData/...`. This report
concerns a different code path — the geocoding performed by the L2 writer — and
fixing #165 would not change the outcome here: the geocoded layer would still be NaN.

## Version

Reproduced on `develop` @ 23f99329d (0.26.0-dev), and the code in question is
unchanged in the current `develop` @ f42cea75b. It has not been touched since
07a033f4 (2025-05-15, "Update GCOV & GSLC writer to geocode 1-D LUTs").

## Symptom

```
ERROR 5: tmp7acypfvt.vrt, band 1: Access window out of range in RasterIO().
Requested (0,0) of size 105x31 on raster of 31x1.
In isce3::io::Raster::get/setValue() - error in RasterIO.
```

The requested window (105 x 31) is the product of the two axis lengths in the group;
the actual raster (31 x 1) is the 1-D `referenceTerrainHeight` itself.

## Reproduction

No NISAR data is required — the bundled test data reproduces it.

```console
$ ctest --test-dir <build> -R test.python.pkg.nisar.workflows.gcov --output-on-failure
...
ERROR 5: ..., band 1: Access window out of range in RasterIO().   # printed 4 times
...
1 test passed
```

The test passes while emitting the error four times. Inspecting its output:

```python
import h5py, numpy as np

with h5py.File("gcov_envisat_area_noise_correction_false.h5") as h:
    a = h["/science/LSAR/GCOV/metadata/processingInformation/parameters"
          "/referenceTerrainHeight"][()]
    print(a.shape, np.isfinite(a).sum(), "of", a.size)
# (10, 41) 0 of 410
```

The same happens in the GSLC workflow test, which shares this base class.

## Cause

`python/packages/nisar/products/writers/BaseL2WriterSingleInput.py` (lines 1909-1917):

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

`slantRange` is not specific to `referenceTerrainHeight`. It is the shared range
axis of the group, required by the 2-D LUTs stored alongside it, and the RSLC
writer creates it unconditionally in `require_lut_axes()`
(`writers/SLC.py`, called immediately after `referenceTerrainHeight` is written).

For example, in the bundled `tests/data/envisat.h5`:

```
/science/LSAR/SLC/metadata/processingInformation/parameters/
    referenceTerrainHeight   (80,)        <- 1-D, along azimuth
    effectiveVelocity        (80, 240)    <- 2-D, needs both axes
    zeroDopplerTime          (80,)
    slantRange               (240,)       <- the range axis of the 2-D LUT above
```

So `slant_range_path not in self.input_hdf5_obj` is always False and
`flag_luts_are_1d_az` can never become True for an RSLC produced by ISCE3, even
though the comment at the top of the same file states that the 1-D case is the
current one:

```python
# For now, `referenceTerrainHeight` is a 1-D Dataset, varying with
# azimuth time. In future, we plan to reimplement this as a 2-D Dataset,
# but in the meantime the code needs to be able to handle the 1-D case.
LUT_1D_AZ_DATASETS = ['referenceTerrainHeight']
```

The code then reads the 1-D dataset as if it were a 2-D raster of
`len(zeroDopplerTime) x len(slantRange)`, which is what the GDAL error reports.

## Why this was not caught

`referenceTerrainHeight` does not appear anywhere under `tests/` (zero occurrences).
The other 1-D path added in the same change — the range-varying crosstalk LUTs — is
covered by `tests/python/packages/nisar/workflows/gcov.py`, and that path works.

## Impact

Observed on two NISAR L2 scenes with entirely different acquisition and processing
parameters (frequency A+B vs. B only, dual- vs. single-pol, 20 vs. 5 MHz, UTM vs.
polar stereographic, 20 vs. 80 m posting, steep terrain vs. flat ice shelf), and in
both cases the layer is all NaN. The corresponding official products
contain an all-NaN layer as well (0 of 156,420 and 0 of 111,531 finite values), so
this affects delivered products:

```
NISAR_L2_PR_GCOV_028_168_D_126_0005_NASV_A_20260824T211408_20260824T211412_P05023_N_P_J_001
NISAR_L2_PR_GCOV_028_152_A_156_2005_DHDH_A_20260823T185248_20260823T185253_P05023_N_P_J_001
```

Both were produced with `softwareVersion = 0.25.16`, so this is not specific to
`develop`.

Only this metadata layer is affected; the science datasets are unaffected.

## A possible fix, for reference

Deciding the rank from the dataset itself rather than from a sibling:

```python
flag_luts_are_1d_az = (
    all([var in LUT_1D_AZ_DATASETS for var in input_ds_name_list]) and
    all([f'{input_h5_group_path}/{var}' in self.input_hdf5_obj and
         self.input_hdf5_obj[f'{input_h5_group_path}/{var}'].ndim == 1
         for var in input_ds_name_list]))
```

With this change I observed: the GDAL error disappears from both the GCOV and GSLC
workflow tests (4 -> 0 occurrences), the layer is populated (134 of 410 valid pixels
on `envisat.h5`; 31,228 of 156,420 on a real NISAR scene, the rest being outside the
LUT extent), the existing tests still pass, and the science datasets are bit-identical.

I am not sure whether keying on `.ndim` is the right long-term choice given the plan
to move to a 2-D LUT, so I am reporting the problem rather than proposing a patch.
Happy to open a PR if this direction looks reasonable, and to add a regression test
that asserts the geocoded layer contains valid values.
