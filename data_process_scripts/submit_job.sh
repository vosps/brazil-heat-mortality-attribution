#!/bin/bash
#SBATCH --job-name=generate_timeseries
#SBATCH --time=0-72:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --mem=128gb
#SBATCH --partition dmm,short,compute
#SBATCH --account=GEOG022743
# # # #SBATCH --begin=now+7hours




#########

# script_name="download_era5.py"
script_name="timeseries_IGR.py"
# script_name="process_time_slice_obs.py"
# script_name="download_damip.py"
# activate conda environment
# source activate /user/work/al18709/.conda/envs/aquatic
# run script
# python -u $script_name
# echo $script_name

# script_name="generate_timeseries_state_level.py"
# # activate pixi environment and run script
pixi run python -u "$script_name"

# tas_CanESM5_hist-nat_r10i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_hist-nat_r1i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_hist-nat_r2i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_hist-nat_r3i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_hist-nat_r4i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_hist-nat_r5i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_hist-nat_r6i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_hist-nat_r7i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_hist-nat_r8i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_hist-nat_r9i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r10i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r1i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r2i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r3i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r4i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r5i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r6i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r7i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r8i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_CanESM5_historical_r9i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_GFDL-CM4_hist-nat_r1i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_GFDL-CM4_historical_r1i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_MRI-ESM2-0_hist-nat_r1i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_MRI-ESM2-0_hist-nat_r3i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_MRI-ESM2-0_hist-nat_r5i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_MRI-ESM2-0_historical_r1i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_MRI-ESM2-0_historical_r3i1p1f1_downscaled_05_masked_2000_2018.nc
# tas_MRI-ESM2-0_historical_r5i1p1f1_downscaled_05_masked_2000_2018.nc

# pixi run python -u $script_name "/user/work/nh25161/downscale_damip_05_mask/"

# Directory containing the NetCDF files
# data_dir="/user/work/nh25161/downscale_damip_01"
# echo "running"
# # Loop through all matching .nc files
# for file in "$data_dir"/tas_*.nc; do
#     echo $file
#     # Check if the file exists (in case glob doesn't match anything)
#     # if [[ -f "$file" ]]; then
#     echo "Processing $file"
#     pixi run python -u "$script_name" "$file" --cpus 48 --mem-per-worker 1G
#     # fi
# done


# now=$(date +"%Y-%m-%d")
# log_path="logs/$script_name/$now/%A/%a.log"
# sbatch -o $log_path submit_job.sh

#########


# script_name="create_reforecast_regional_dataframes"

# now=$(date +"%Y-%m-%d")
# log_path="logs/$script_name/$now/%A/%a.log"

# sbatch -o $log_path $1 $script_name