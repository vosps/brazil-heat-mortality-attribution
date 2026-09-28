"""
This script takes the raw mortality data and processed it to produce final results.

Inputs : mortality data in excell spreadsheets

Outputs : 
    weighted mean and percentiles of 
        factual mortality
        counterfactual mortality
        attributable mortality = factual - counterfactual
        attributable mortality per 100,000 population = (attributable mortality / population) * 100,000
        attributable fraction = (factual - counterfactual) / total deaths
        attributable fraction of heat-related deaths = (factual - counterfactual) / factual deaths
        
        on levels of:
        IGR
        Region
        Country-wide
"""

import pandas as pd
import numpy as np
import geopandas as gpd
import pickle
import copy
import os


def weighted_percentile(data, weights, percentiles):
    i = np.argsort(data)
    d_sorted = data[i]
    w_sorted = weights[i]
    lower = np.percentile(d_sorted,percentiles[0],method='inverted_cdf',weights=w_sorted)
    upper = np.percentile(d_sorted,percentiles[1],method='inverted_cdf',weights=w_sorted)
    return lower,upper


# def generate_weights(models):
#     merged = copy.deepcopy({k: v for k, v in models.items() if k != 'CanESM5-P2'})
#     merged['CanESM5']['runs'] = models['CanESM5']['runs'] + models['CanESM5-P2']['runs']
    
#     n_models = len(merged)  # 13
    
#     return np.concatenate([
#         np.full(len(m['runs']) * 1000, 1 / (n_models * len(m['runs']) * 1000))
#         for m in merged.values()
#     ])

def generate_weights(models, simulation_values=None, filter_nans=False):
    merged = copy.deepcopy({k: v for k, v in models.items() if not (k == 'CanESM5-P2' and 'CanESM5' in models)})
    
    if 'CanESM5' in models and 'CanESM5-P2' in models:
        merged['CanESM5']['runs'] = models['CanESM5']['runs'] + models['CanESM5-P2']['runs']
    
    n_models = len(merged)  # 13

    if not filter_nans or simulation_values is None:
        return np.concatenate([
            np.full(len(m['runs']) * 1000, 1 / (n_models * len(m['runs']) * 1000))
            for m in merged.values()
        ])

    # filter_nans=True: weight by non-nan count per model, then zero out nans
    weights_parts = []
    idx = 0
    for m in merged.values():
        model_size  = len(m['runs']) * 1000
        model_vals  = simulation_values[idx : idx + model_size]
        # n_not_nan   = (~np.isnan(model_vals)).sum()
        n_not_nan   = (np.isfinite(model_vals)).sum()
        print('infinite count:', (~np.isfinite(model_vals)).sum())
        print('model:', m['prefix'])
        w_per_sample = 1 / (n_models * n_not_nan) if n_not_nan > 0 else 0
        weights_parts.append(np.full(model_size, w_per_sample))
        idx += model_size

    weights_out = np.concatenate(weights_parts)
    weights_out[~np.isfinite(simulation_values)] = 0
    return weights_out
    
def load_simulations(simulation_dir, cohort='COHORT_noRH'):
    models = {
        'ACCESS-CM2':      {'prefix': 'accesscm2', 'runs': [f'r{r}i1p1f1' for r in [1]]},
        'ACCESS-ESM1-5':   {'prefix': 'access',    'runs': [f'r{r}i1p1f1' for r in range(1, 4)]},
        'BCC-CSM2-MR':     {'prefix': 'bcc',       'runs': [f'r{r}i1p1f1' for r in [1]]},
        'CanESM5':         {'prefix': 'canesm',    'runs': [f'r{r}i1p1f1' for r in range(1, 26) if r not in [12, 16, 17, 18, 19, 20, 21, 24]]},
        'CanESM5-P2':      {'prefix': 'canesmp2',  'runs': [f'r{r}i1p2f1' for r in range(1, 26) if r not in [3, 7, 12, 13, 14, 15, 17, 19, 23]]},
        'CNRM-CM6-1':      {'prefix': 'cnrm',      'runs': [f'r{r}i1p1f2' for r in range(1, 4)]},
        'FGOALS-g3':       {'prefix': 'fgoals',    'runs': [f'r{r}i1p1f1' for r in [1]]},
        'GFDL-CM4':        {'prefix': 'gfdl',      'runs': [f'r{r}i1p1f1' for r in [1]]},
        'GFDL-ESM4':       {'prefix': 'gfdlesm',   'runs': [f'r{r}i1p1f1' for r in [1]]},
        'HadGEM3-GC31-LL': {'prefix': 'hadgem',    'runs': [f'r{r}i1p1f3' for r in range(1, 61) if r not in [6, 7, 8, 9, 10]]},
        'IPSL-CM6A-LR':    {'prefix': 'ipsl',      'runs': [f'r{r}i1p1f1' for r in range(1, 7) if r != 3]},
        'MIROC6':          {'prefix': 'miroc',     'runs': [f'r{r}i1p1f1' for r in range(1, 3)]},
        'MRI-ESM2-0':      {'prefix': 'mri',       'runs': [f'r{r}i1p1f1' for r in range(1, 6) if r != 4]},
        'NorESM2-LM':      {'prefix': 'noresm',    'runs': [f'r{r}i1p1f1' for r in range(1, 4)]},
    }

    simulations = {}
    for model_name, config in models.items():
        prefix = config['prefix']
        # CanESM5-P2 files use CanESM5 in the filename
        file_model_name = 'CanESM5' if model_name == 'CanESM5-P2' else model_name
        for i, run in enumerate(config['runs'], start=1):
            
            if cohort == 'moderate_vs_high_p95':
                
    
                factual_path_moderate        = simulation_dir + f'low_p95/FACTUAL_AN_COHORT_noRH_lowP95_tas_{file_model_name}_{run}.xlsx'
                counterfactual_path_moderate = simulation_dir + f'low_p95/COUNTERFACTUAL_AN_COHORT_noRH_lowP95_tas_{file_model_name}_{run}.xlsx'
                factual_path_high            = simulation_dir + f'high_p95/FACTUAL_AN_COHORT_noRH_highP95_tas_{file_model_name}_{run}.xlsx'
                counterfactual_path_high     = simulation_dir + f'high_p95/COUNTERFACTUAL_AN_COHORT_noRH_highP95_tas_{file_model_name}_{run}.xlsx'

                simulations[(prefix, i)] = {
                    'factual_moderate':        pd.read_excel(factual_path_moderate),
                    'counterfactual_moderate': pd.read_excel(counterfactual_path_moderate),
                    'factual_high':        pd.read_excel(factual_path_high),
                    'counterfactual_high': pd.read_excel(counterfactual_path_high),
                    
                }
            else:
                factual_path        = simulation_dir + f'FACTUAL_AN_{cohort}_tas_{file_model_name}_{run}.xlsx'
                counterfactual_path = simulation_dir + f'COUNTERFACTUAL_AN_{cohort}_tas_{file_model_name}_{run}.xlsx'
                simulations[(prefix, i)] = {
                    'factual':        pd.read_excel(factual_path),
                    'counterfactual': pd.read_excel(counterfactual_path),
                }

    print(f"Total simulation pairs loaded: {len(simulations)}")
    return simulations, models


def aggregate_simulations(simulations, models, spatial_level,cohort):
    """
    Aggregate raw simulations into a dict of DataFrames, one per geographic unit.
    
    spatial_level: 'igr', 'region', or 'country'
    
    Returns dict of {geographic_unit: DataFrame} where each DataFrame has columns:
        factual_mortality, counterfactual_mortality, total_deaths, population
    """
    uf_code_to_region = {
        11: 'North', 12: 'North', 13: 'North', 14: 'North', 15: 'North', 16: 'North', 17: 'North',
        21: 'Northeast', 22: 'Northeast', 23: 'Northeast', 24: 'Northeast', 25: 'Northeast',
        26: 'Northeast', 27: 'Northeast', 28: 'Northeast', 29: 'Northeast',
        31: 'Southeast', 32: 'Southeast', 33: 'Southeast', 35: 'Southeast',
        41: 'South', 42: 'South', 43: 'South',
        50: 'Central-West', 51: 'Central-West', 52: 'Central-West', 53: 'Central-West',
    }
    
    # Mirror the merging logic from generate_weights
    # merged_models = copy.deepcopy({k: v for k, v in models.items() 
    #     if not (k == 'CanESM5-P2' and 'CanESM5' in models)})
    # if 'CanESM5' in models and 'CanESM5-P2' in models:
    #     merged_models['CanESM5']['runs'] = (models['CanESM5']['runs'] 
    #                                         + models['CanESM5-P2']['runs'])

    # Load population and total deaths, indexed by IGR
    population_df = pd.read_parquet('/bp1/geog-tropical/data/BREATHE/igr_population.parquet')
    population_df['rgi'] = population_df['rgi'].astype(str)
    population_df = population_df.set_index('rgi')
    
    person_years_df = pd.read_excel('/user/home/al18709/breathe/data_analysis/total_person_years.xlsx')
    person_years_df['rgi'] = person_years_df['cod_rgi'].astype(float).astype('Int64').astype(str)
    person_years_df = person_years_df.set_index('rgi')

    if "SIM" in cohort:
        descriptives_df = pd.read_excel('/user/home/al18709/breathe/data_analysis/Results_SIM_noRH_tas_ACCESS-CM2_r1i1p1f1.xlsx')
    else:
        descriptives_df = pd.read_excel('/user/home/al18709/breathe/data_analysis/Results_COHORT_noRH_tas_ACCESS-CM2_r1i1p1f1.xlsx')
    descriptives_df = descriptives_df.rename(columns={'COD_RGI': 'rgi'})
    descriptives_df['rgi'] = descriptives_df['rgi'].astype(str)
    descriptives_df = descriptives_df.set_index('rgi')

    if cohort == 'moderate_vs_high_p95':
        first_df    = next(iter(simulations.values()))['factual_moderate']
    else:
        first_df    = next(iter(simulations.values()))['factual']
    igr_columns = first_df.columns.tolist()

    # Derive igr -> region from the first two digits of the IGR code
    igr_to_region_map = {
        igr: uf_code_to_region[int(str(igr)[:2])]
        for igr in igr_columns
    }

    if spatial_level == 'igr':
        igr_groups = {igr: [igr] for igr in igr_columns}
    elif spatial_level == 'region':
        igr_groups = {}
        for igr in igr_columns:
            region = igr_to_region_map[igr]
            igr_groups.setdefault(region, []).append(igr)
    elif spatial_level == 'country':
        igr_groups = {'Brazil': igr_columns}

    aggregated = {}
    for geographic_unit, igrs_in_unit in igr_groups.items():
        
        if cohort == 'moderate_vs_high_p95':
            factual_runs_moderate        = []
            counterfactual_runs_moderate = []
            factual_runs_high            = []
            counterfactual_runs_high     = []
            for model_name, config in models.items():
                prefix = config['prefix']
                for run_index in range(1, len(config['runs']) + 1):
                    factual_df_moderate        = simulations[(prefix, run_index)]['factual_moderate']
                    counterfactual_df_moderate = simulations[(prefix, run_index)]['counterfactual_moderate']
                    factual_runs_moderate.append(factual_df_moderate[igrs_in_unit].sum(axis=1).values)
                    counterfactual_runs_moderate.append(counterfactual_df_moderate[igrs_in_unit].sum(axis=1).values)
                    factual_df_high        = simulations[(prefix, run_index)]['factual_high']
                    counterfactual_df_high = simulations[(prefix, run_index)]['counterfactual_high']
                    factual_runs_high.append(factual_df_high[igrs_in_unit].sum(axis=1).values)
                    counterfactual_runs_high.append(counterfactual_df_high[igrs_in_unit].sum(axis=1).values)
            # Aggregate population and total deaths for this geographic unit
            unit_population   = population_df.loc[igrs_in_unit, 'population_count'].sum()
            unit_total_deaths = descriptives_df.loc[igrs_in_unit, 'total_obitos'].sum()

            aggregated[geographic_unit] = pd.DataFrame({
                'factual_mortality_moderate':        np.concatenate(factual_runs_moderate),
                'counterfactual_mortality_moderate': np.concatenate(counterfactual_runs_moderate),
                'factual_mortality_high':            np.concatenate(factual_runs_high),
                'counterfactual_mortality_high':     np.concatenate(counterfactual_runs_high),
                'total_deaths':                     unit_total_deaths,  # scalar, broadcast across rows
                'population':                       unit_population,    # scalar, broadcast across rows
            })

        else:   
            factual_runs        = []
            counterfactual_runs = []
            for model_name, config in models.items():
                prefix = config['prefix']
                for run_index in range(1, len(config['runs']) + 1):
                    factual_df        = simulations[(prefix, run_index)]['factual']
                    counterfactual_df = simulations[(prefix, run_index)]['counterfactual']
                    factual_runs.append(factual_df[igrs_in_unit].sum(axis=1).values)
                    counterfactual_runs.append(counterfactual_df[igrs_in_unit].sum(axis=1).values)

            # Aggregate population and total deaths for this geographic unit
            unit_population   = population_df.loc[igrs_in_unit, 'population_count'].sum()
            unit_total_deaths = descriptives_df.loc[igrs_in_unit, 'total_obitos'].sum()
            unit_person_years = person_years_df.loc[igrs_in_unit, 'total_person_years'].sum()

            aggregated[geographic_unit] = pd.DataFrame({
                'factual_mortality':        np.concatenate(factual_runs),
                'counterfactual_mortality': np.concatenate(counterfactual_runs),
                'total_deaths':             unit_total_deaths,  # scalar, broadcast across rows
                'population':               unit_population,    # scalar, broadcast across rows
                'person_years':             unit_person_years,  # scalar, broadcast across rows
            })
        

    return aggregated


def compute_summary(aggregated, weights, models):
    results = {}

    for geographic_unit, simulation_df in aggregated.items():
        factual_mortality        = simulation_df['factual_mortality'].values
        counterfactual_mortality = simulation_df['counterfactual_mortality'].values
        attributable_mortality   = factual_mortality - counterfactual_mortality
        total_deaths             = simulation_df['total_deaths'].iloc[0]
        population               = simulation_df['population'].iloc[0]
        person_years             = simulation_df['person_years'].iloc[0]

        statistics = {
            'factual_mortality':                   factual_mortality,
            'counterfactual_mortality':             counterfactual_mortality,
            'attributable_mortality':               attributable_mortality,
            'attributable_mortality_per_100k':      (attributable_mortality / population) * 100_000,
            'attributable_mortality_per_person_year': (attributable_mortality / person_years),
            'attributable_fraction':                (attributable_mortality / total_deaths) * 100,
            'heat_related_attributable_fraction':   (attributable_mortality / factual_mortality) * 100,
            
        }

        rows = []
        for statistic_name, simulation_values in statistics.items():
            if statistic_name in ['heat_related_attributable_fraction','moderate_high_ratio']:
                weights_nan = generate_weights(models, simulation_values, filter_nans=True)
                valid = ~np.isfinite(simulation_values)
                values_hr  = np.where(valid, 0, simulation_values)
                # values_hr  = np.where(np.isnan(simulation_values), 0, simulation_values)
                p2_5, p97_5 = weighted_percentile(values_hr, weights_nan, [2.5, 97.5])
                rows.append({
                    'statistic': statistic_name,
                    'mean':      np.average(values_hr, weights=weights_nan),
                    'p2.5':      p2_5,
                    'p97.5':     p97_5,
                })
            else:
                p2_5, p97_5 = weighted_percentile(simulation_values, weights, [2.5, 97.5])
                rows.append({
                    'statistic': statistic_name,
                    'mean':      np.average(simulation_values, weights=weights),
                    'p2.5':      p2_5,
                    'p97.5':     p97_5,
                })

        results[geographic_unit] = pd.DataFrame(rows).set_index('statistic')

    return results

def compute_summary_mod_vs_high(aggregated, weights, models):
    results    = {}
    raw_arrays = {}

    for geographic_unit, simulation_df in aggregated.items():
        factual_mortality_moderate        = simulation_df['factual_mortality_moderate'].values
        counterfactual_mortality_moderate = simulation_df['counterfactual_mortality_moderate'].values
        attributable_mortality_moderate   = factual_mortality_moderate - counterfactual_mortality_moderate

        attributable_fraction_moderate    = (attributable_mortality_moderate / factual_mortality_moderate) * 100
        factual_mortality_high            = simulation_df['factual_mortality_high'].values
        counterfactual_mortality_high     = simulation_df['counterfactual_mortality_high'].values
        attributable_mortality_high       = factual_mortality_high - counterfactual_mortality_high

        attributable_fraction_high        = (attributable_mortality_high / factual_mortality_high) * 100

        attributable_mortality_moderate_negative = attributable_mortality_moderate < 0
        attributable_mortality_high_negative     = attributable_mortality_high < 0
        moderate_vs_high_ratio                   = attributable_fraction_moderate / attributable_fraction_high

        # stash per-unit raw arrays instead of np.save'ing to a shared filename
        raw_arrays[geographic_unit] = {
            'moderate_vs_high_ratio_raw':                   moderate_vs_high_ratio,
            'factual_mortality_moderate' : factual_mortality_moderate,
            'counterfactual_mortality_moderate' : counterfactual_mortality_moderate,
            'factual_mortality_high' : factual_mortality_high,
            'counterfactual_mortality_high' : counterfactual_mortality_high,
            'attributable_mortality_moderate_negative_raw': attributable_mortality_moderate_negative,
            'attributable_mortality_high_negative_raw':     attributable_mortality_high_negative,
            'weights_raw':                                  weights,
        }

        total_deaths = simulation_df['total_deaths'].iloc[0]
        population   = simulation_df['population'].iloc[0]

        statistics = {
            'moderate_high_ratio': moderate_vs_high_ratio,
            'factual_mortality_high': factual_mortality_high,
            'counterfactual_mortality_high': counterfactual_mortality_high,
            'factual_mortality_moderate': factual_mortality_moderate,
            'counterfactual_mortality_moderate': counterfactual_mortality_moderate,
            'attributable_mortality_high': attributable_mortality_high,
            'attributable_mortality_moderate': attributable_mortality_moderate,
        }

        rows = []
        for statistic_name, simulation_values in statistics.items():
            if statistic_name in ['moderate_high_ratio']:
                weights_nan = generate_weights(models, simulation_values, filter_nans=True)
                valid = ~np.isfinite(simulation_values)
                values_hr  = np.where(valid, 0, simulation_values)
                p2_5, p97_5 = weighted_percentile(values_hr, weights_nan, [2.5, 97.5])
                mean = np.average(values_hr, weights=weights_nan)
            else:
                weights = generate_weights(models, simulation_values, filter_nans=False)
                p2_5, p97_5 = weighted_percentile(simulation_values, weights, [2.5, 97.5])
                mean = np.average(simulation_values, weights=weights)
            rows.append({
                'statistic': statistic_name,
                'mean':      mean,
                'p2.5':      p2_5,
                'p97.5':     p97_5,
            })

        results[geographic_unit] = pd.DataFrame(rows).set_index('statistic')

    return results, raw_arrays

def save_raw_arrays(raw_arrays, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for geographic_unit, arrays in raw_arrays.items():
        safe_unit = str(geographic_unit).replace('/', '_')
        for array_name, array_values in arrays.items():
            path = os.path.join(output_dir, f'{array_name}_{safe_unit}.npy')
            np.save(path, array_values)
    print(f"Raw arrays for {len(raw_arrays)} geographic units saved to {output_dir}")


def save_results(results, output_path):
    with open(output_path, 'wb') as f:
        pickle.dump(results, f)
    print(f"Results saved to {output_path}")


def load_results(output_path):
    with open(output_path, 'rb') as f:
        results = pickle.load(f)
    return results



# ============================================================
# RUNNING THE FULL PIPELINE
# ============================================================


from concurrent.futures import ProcessPoolExecutor

def run_pipeline(simulation_dir, cohort, output_path,stats_test):
    print(f"Starting: {cohort}")
    simulations, models = load_simulations(simulation_dir, cohort=cohort)
    
    # n_zeros_factual = sum(
    # (v['factual'].sum(axis=1) == 0).sum()
    # for v in simulations.values()
    # )
    # n_zeros_counterfactual = sum(
    #     (v['counterfactual'].sum(axis=1) == 0).sum()
    #     for v in simulations.values()
    # )
    # print(f"Number of zeros in factual mortality: {n_zeros_factual} / {len(simulations) * 1000}")
    # print(f"Number of zeros in counterfactual mortality: {n_zeros_counterfactual} / {len(simulations) * 1000}")

    weights            = generate_weights(models)

    igr_aggregated     = aggregate_simulations(simulations, models, spatial_level='igr',cohort=cohort)
    region_aggregated  = aggregate_simulations(simulations, models, spatial_level='region',cohort=cohort)
    country_aggregated = aggregate_simulations(simulations, models, spatial_level='country',cohort=cohort)
    
    # save igr_aggregated
    save_results(igr_aggregated, output_path[:-4] + '_igr_aggregate.pkl')

    if stats_test == True:
        country_aggregated = aggregate_simulations(simulations, models, spatial_level='country',cohort=cohort)
        region_aggregated  = aggregate_simulations(simulations, models, spatial_level='region',cohort=cohort)
        save_results(country_aggregated, output_path[:-4] + '_country.pkl')
        save_results(region_aggregated, output_path[:-4] + '_region.pkl')
        print(f"Done: {cohort} -> {output_path}")
        # save weights to a separate file
        weights_path = output_path.replace('.pkl', '_weights.npy')
        np.save(weights_path, weights)
        
    else:
    
        if cohort == 'moderate_vs_high_p95':
            igr_results, igr_raw_arrays = compute_summary_mod_vs_high(igr_aggregated, weights, models)
            results = {'igr': igr_results}

            raw_arrays_dir = os.path.dirname(output_path) + '/raw_arrays_' + os.path.basename(output_path)[:-4]
            save_raw_arrays(igr_raw_arrays, raw_arrays_dir)
            results2 = {
            'igr':     compute_summary_mod_vs_high(igr_aggregated,     weights, models),
            'region':  compute_summary_mod_vs_high(region_aggregated,  weights, models),
            'country': compute_summary_mod_vs_high(country_aggregated, weights, models),
            }
            save_results(results2, output_path[:-4] + '_mod_high_all_aggregations.pkl')
        else:
            results = {
                'igr':     compute_summary(igr_aggregated,     weights, models),
                'region':  compute_summary(region_aggregated,  weights, models),
                'country': compute_summary(country_aggregated, weights, models),
            }

        save_results(results, output_path)
        # save_results(results2, output_path[:-4] + '_mod_high_all_aggregations.pkl')
        print(f"Done: {cohort} -> {output_path}")


pipeline_configs = [
    ('/bp1/geog-tropical/data/BREATHE/Simulation_v4/100M/',
        'COHORT_noRH',
        '/bp1/geog-tropical/data/BREATHE/results/aggregated_100M.pkl',
        False,
    ),
    ('/bp1/geog-tropical/data/BREATHE/Simulation_v4/SIM/',
        'SIM_noRH',
        '/bp1/geog-tropical/data/BREATHE/results/aggregated_SIM.pkl',
        False,
    ),
    (
        '/bp1/geog-tropical/data/BREATHE/Simulation_v4/100M/',
        'COHORT_noRH',
        '/bp1/geog-tropical/data/BREATHE/results/results_100M.pkl',
        False,
    ),
    (
        '/bp1/geog-tropical/data/BREATHE/Simulation_v4/SIM/',
        'SIM_noRH',
        '/bp1/geog-tropical/data/BREATHE/results/results_SIM.pkl',
        False,
    ),
    (
        '/bp1/geog-tropical/data/BREATHE/Simulation_v4/high_vs_low/low_p95/',
        'COHORT_noRH_lowP95',
        '/bp1/geog-tropical/data/BREATHE/results/results_100M_lowp95.pkl',
        False,
    ),
    (
        '/bp1/geog-tropical/data/BREATHE/Simulation_v4/high_vs_low/high_p95/',
        'COHORT_noRH_highP95',
        '/bp1/geog-tropical/data/BREATHE/results/results_100M_highp95.pkl',
        False,
    ),
    (
        '/bp1/geog-tropical/data/BREATHE/Simulation_v4/high_vs_low/',
        'moderate_vs_high_p95',
        '/bp1/geog-tropical/data/BREATHE/results/results_100M_mod_high_ratio_p95.pkl',
        False,
    ),
        ]

with ProcessPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(run_pipeline, *config) for config in pipeline_configs]
    for future in futures:
        future.result()  # re-raises any exceptions


def generate_model_table(simulation_dir, cohort, output_csv):
    rows = []
    simulations, models = load_simulations(simulation_dir, cohort=cohort)
    
    

    for model_name, config in models.items():
        if model_name == 'CanESM5-P2':
            continue  # handled as part of CanESM5

        prefix = config['prefix']

        if model_name == 'CanESM5':
            # Include both CanESM5 and CanESM5-P2 runs
            p2 = models['CanESM5-P2']
            single_model = {
                'CanESM5':    config,
                'CanESM5-P2': p2,
            }
            single_sims = {
                k: v for k, v in simulations.items()
                if k[0] in (config['prefix'], p2['prefix'])
            }
            n_runs  = len(config['runs']) + len(p2['runs'])
        else:
            single_model = {model_name: config}
            single_sims  = {k: v for k, v in simulations.items() if k[0] == prefix}
            n_runs       = len(config['runs'])

        weights     = np.full(n_runs * 1000, 1 / (n_runs * 1000))
        country_agg = aggregate_simulations(single_sims, single_model, spatial_level='country',cohort=cohort)
        summary     = compute_summary(country_agg, weights, single_model)

        rows.append({
            'model':                  model_name,
            'attributable_mortality': summary['Brazil'].loc['attributable_mortality', 'mean'],
            'attributable_fraction':  summary['Brazil'].loc['attributable_fraction',  'mean'],
        })

    pd.DataFrame(rows).to_csv(output_csv, index=False)
    print(f"Model table saved to {output_csv}")
    