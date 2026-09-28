"""
Author: Ruby Lieber + Emily Vosper
Affiliation: University of Bristol
Date: 30/06/2025

Description: 
Script to generate daily temperature time series for Brazilian municipalities
from downscaled CMIP6 DAMIP climate model data.

Workflow:
---------
1. Input paths:
   - Reads daily near-surface air temperature (`tas`) NetCDF files from the
     downscaled DAMIP dataset.
   - Constructs corresponding output file paths for storing processed results
     in Parquet format.

2. Population weights:
   - Loads a 0.5° population density dataset for Brazil.
   - Used as weights in population-weighted temperature averages.

3. Timeseries extraction:
   - For each input NetCDF file:
       * Loads the temperature data and aligns its CRS with the population raster.
       * Reads the Brazilian municipality shapefile (RGI 2017).
       * Splits the 3D data cube into individual daily rasters.
       * Uses `exactextract` to compute:
            - Area-weighted mean daily temperature
            - Population-weighted mean daily temperature
         for each municipality.
       * Parallelizes computation over time steps using
         `concurrent.futures.ProcessPoolExecutor`.

4. Output:
   - Combines results into a long-format pandas DataFrame with columns:
        ["date", "rgi", "daily_mean_temperature",
         "daily_pop_weighted_temperature"]
   - Optimizes datatypes for storage efficiency.
   - Saves results as compressed Parquet files, one per model/experiment/ensemble.

Notes:
------
- Requires large memory and parallel processing capacity.
- CRS is explicitly set to EPSG:4674 (SIRGAS 2000).
- Uses 48 parallel workers by default.
"""

# --------------------------------------------
# 0. Imports
# --------------------------------------------

import xarray as xr
import numpy as np
import pandas as pd
import geopandas as gpd
import glob
import os
from exactextract import exact_extract
import concurrent.futures
import rioxarray
import gc
from osgeo import osr
osr.UseExceptions()

# --------------------------------------------
# 1. Generate paths
# --------------------------------------------

in_dir = "/bp1/geog-tropical/data/BREATHE/downscale_damip_05_new_temp/"
out_dir = "/bp1/geog-tropical/data/BREATHE/timeseries_igr_new/"

# Get all tas files
in_paths = sorted(glob.glob(os.path.join(in_dir, "tas_*.nc")))
print(in_paths)

# do in batches
models = {
    'ACCESS-CM2', 
    'ACCESS-ESM1-5', 
    'CanESM5', 
    'FGOALS-g3',
    'GFDL-CM4', 
    'HadGEM3-GC31-LL', 
    'IPSL-CM6A-LR', 
    'MRI-ESM2-0', 
    'NorESM2-LM',
}

in_paths = [p for p in in_paths if any(f"_{model}_" in p for model in models)]
print(in_paths)
in_paths = in_paths[-40:-30]
# print(in_paths)

# Create corresponding out_paths
out_paths = []
for i,path in enumerate(in_paths):
    filename = os.path.basename(path)
    parts = filename.split("_")
    model = parts[1]
    experiment = parts[2]
    ens = parts[3]
    out_filename = f"tas_{model}_{experiment}_{ens}_timeseries_2000_2020.parquet"
    # check if file already exists
    if os.path.exists(os.path.join(out_dir, out_filename)):
        print(f"File already exists: {out_filename}", flush=True)
        in_paths[i] = None
        out_paths.append(None)
        continue
    out_paths.append(os.path.join(out_dir, out_filename))

print(len(in_paths), len(out_paths))

# --------------------------------------------
# 2. Population density for weights 
# --------------------------------------------

pop_density = xr.open_dataarray("/bp1/geog-tropical/data/BREATHE/population_density_05deg_corrected.nc").isel(lon=slice(0,82))
pop_density = pop_density.rio.write_crs("EPSG:4674", inplace=True)


# --------------------------------------------
# 3. Generate timeseries
# --------------------------------------------

for i, path in enumerate(in_paths):
    if path is None:
        print(path, '\n already processed, skipping...', flush=True)
        continue
    
    print(f"Starting file {i+1}/{len(in_paths)}: {path}", flush=True)
    
    if not os.path.exists(path):
        print(f"File not found: {path}", flush=True)
        continue

    # Read in Brazil temperature data 
    data = xr.open_dataarray(path)

    # Align spatial reference systems
    data.rio.write_crs("EPSG:4674", inplace=True)

    # Read in full municipality shapefile
    shapefile = gpd.read_file("/bp1/geog-tropical/data/BREATHE/RG2017_rgi_20180911/RG2017_rgi.shp")
    rgis = [str(rgi) for rgi in rgis]
    print(rgis)
    # Set index for exactextract
    rgi_indexed = shapefile.set_index("rgi")
    
    # crop to our sublist of rgis
    rgi_indexed = rgi_indexed.loc[rgis]
    print(rgi_indexed)

    # Convert 3D obs into list of 2D rasters (one per time step)
    data_list = [data.isel(time=t).drop_vars("time") for t in range(data.sizes["time"])]
    data_list = [da.load() for da in data_list]  # read all data into memory now
    times = data.time.values

    def process_time_step(i):
        """
        Extract mean daily temperature values for all municipalities 
        at a given time step.

        Parameters
        ----------
        i : int
            Index of the time step to process.

        Returns
        -------
        tuple
            (i, unweighted_means, weighted_means) where:
            - i : int, the time step index
            - unweighted_means : list of float
                Area-weighted mean temperature per municipality
            - weighted_means : list of float
                Population-weighted mean temperature per municipality
        """
        date = str(times[i])
        # print(f"Processing time step {i}: {date}", flush=True)

        # Rename coordinates
        data_renamed = data_list[i].rename({"lat": "y", "lon": "x"})
        pop_renamed = pop_density.rename({"lat": "y", "lon": "x"})

        # Extract both unweighted and weighted means
        df = exact_extract(
            data_renamed,
            rgi_indexed,
            ['mean(coverage_weight=area_spherical_m2)', 'weighted_mean(coverage_weight=area_spherical_m2)'],
            weights=pop_renamed,
            output='pandas'
        )

        return i, df["mean"].tolist(), df["weighted_mean"].tolist()

    results = []
    # with concurrent.futures.ProcessPoolExecutor(max_workers=48) as executor:
    with concurrent.futures.ProcessPoolExecutor(max_workers=48) as executor:
        futures = [executor.submit(process_time_step, i) for i in range(len(data_list))]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # Sort results
    results.sort(key=lambda x: x[0])

    # Unpack means
    unweighted_means = [r[1] for r in results]
    weighted_means = [r[2] for r in results]

    # Flatten into long-format DataFrame
    records = []
    for time, unweighted, weighted in zip(times, unweighted_means, weighted_means):
        for rgi, mean_val, wmean_val in zip(rgi_indexed.index, unweighted, weighted):
            records.append((np.datetime64(time), rgi, mean_val, wmean_val))

    result_df = pd.DataFrame.from_records(
        records,
        columns=["date", "rgi", "daily_mean_temperature", "daily_pop_weighted_temperature"]
    )

    # Optimise types for Parquet
    result_df["rgi"] = result_df["rgi"].astype("category")
    result_df["date"] = result_df["date"].astype("category")
    result_df["daily_mean_temperature"] = result_df["daily_mean_temperature"].astype("float32")
    result_df["daily_pop_weighted_temperature"] = result_df["daily_pop_weighted_temperature"].astype("float32")

    # Save parquet
    out_path = out_paths[i]
    
    # open parquet file:
    current_pq = pd.read_parquet(out_path)

    
    # fill out current_pq rgis that are nans with result_df rgis that are not nans
    rgis_to_update = result_df["rgi"].unique()
    current_pq = current_pq[~current_pq["rgi"].isin(rgis_to_update)]
    current_pq = pd.concat([current_pq, result_df]) #, ignore_index=True)
    
    current_pq.to_parquet(out_path)
    # result_df.to_parquet(out_path)
    print(f"Finished and saved: {out_path}", flush=True)
    nan_rgis = current_pq.groupby("rgi", observed=True)["daily_pop_weighted_temperature"].apply(lambda x: x.isna().any())
    print(f"RGIs with NaNs: {nan_rgis.sum()} / {nan_rgis.shape[0]}")
    print(nan_rgis[nan_rgis].index.tolist())

    # Clean up memory in loop 
    del data, shapefile, data_list, results, result_df
    gc.collect()