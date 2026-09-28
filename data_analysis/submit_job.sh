#!/bin/bash
#SBATCH --job-name=generate_timeseries
#SBATCH --time=0-72:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=5
#SBATCH --mem=128gb
#SBATCH --partition dmm,short,compute
#SBATCH --account=GEOG022743
# # # #SBATCH --begin=now+7hours




#########


script_name="results.py"

pixi run python -u "$script_name"
