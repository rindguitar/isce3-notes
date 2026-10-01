<!-- upstream (isce-framework/isce3) に出す PR の本文。#402 の修正案。
     下の Title と Body をそのまま使う。フル ctest の結果を入れてから出す。 -->

## Title（PR のタイトル欄に入れる）

Fix geocoding of the 1-D `referenceTerrainHeight` LUT in the GCOV and GSLC writers

---

## Body（PR の本文欄に入れる。ここから下をそのまま貼る）

Proposed fix for #402.

The rank of `referenceTerrainHeight` was inferred from the presence of a sibling `slantRange` dataset.
That dataset is always present, because it is the range axis of the 2-D LUTs stored in the same group, so the 1-D LUT was read as a 2-D raster and the geocoded layer was entirely NaN.

## Changes

Two decisions were conflated in that single condition: **whether the values must be replicated along range** (a property of the dataset's rank) and **what the range axis should be** (whether the group has a `slantRange`).
This PR separates them in `BaseL2WriterSingleInput.geocode_metadata_group()`:

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

The `not flag_luts_are_1d_az or ...` form matters: a 2-D LUT whose group has no `slantRange` takes the existing path and is rejected (or skipped, under `skip_if_not_present`) rather than silently falling back to a synthesized axis.
Among 2-D inputs, the only one handled differently is a `referenceTerrainHeight` without `slantRange`: the current condition misclassifies it as 1-D, while with this change it is rejected (or skipped) like any other 2-D LUT missing its axis.

## Tests

* New: `test_run_envisat_1d_reference_terrain_height` in `tests/python/packages/nisar/workflows/gcov.py`.
  It fills the 1-D `referenceTerrainHeight` of a copy of `tests/data/envisat.h5` with values that vary along azimuth, and compares the geocoded result with that of the same values explicitly replicated along range as a 2-D LUT (the planned format).
  The valid-pixel masks and the values must match.
  It fails without this change (the 1-D result is all NaN) and passes with it.
* The existing GCOV and GSLC workflow tests still pass, and the `Access window out of range` errors they used to print are gone (6 → 0).
  The range-vector (crosstalk) path, checked by `test_run_winnipeg`, is unchanged.
* Full ctest: 【フル ctest の結果を入れる】
  Note that the existing tests also passed with the bug, so the full suite shows that nothing else broke; the new test is what shows the fix.

Happy to adjust or drop this if you have a different treatment in mind.
