#!/usr/bin/env python3
"""
Run SNODAS netCDF builder for 2020-2025
This script executes the full build process from the notebook
"""

import os
import sys
import struct
import tarfile
import gzip
import urllib.request
import urllib.error
import re
from io import BytesIO
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr

# Configuration
START_YEAR = 2020
END_YEAR = 2025
OUTPUT_DIRECTORY = "snodas_nc"
CACHE_DIRECTORY = "snodas_cache"
SUBSET_TO_COLORADO = True
REBUILD_EXISTING = False

# Constants
SNODAS_NODATA = -9999

CO_BOUNDS = {
    'lat_min': 37.0,
    'lat_max': 41.0,
    'lon_min': -109.0,
    'lon_max': -104.0
}

VAR_NAMES = {
    '1036': 'snow_depth',
    '1034': 'swe',
    '1038': 'snow_accumulation',
    '1039': 'snow_melt',
    '1033': 'snow_cover',
    '1037': 'snow_depth_change',
}

GRID_CONFIGS = {
    'old': {
        'XMIN': -124.73375000000000,
        'YMAX': 52.87458333333333,
        'XMAX': -66.94208333333333,
        'YMIN': 24.94958333333333,
        'NCOLS': 6935,
        'NROWS': 3351,
        'name': 'Pre-Oct-2013'
    },
    'new': {
        'XMIN': -124.73333333333333,
        'YMAX': 52.87500000000000,
        'XMAX': -66.94166666666667,
        'YMIN': 24.95000000000000,
        'NCOLS': 3353,
        'NROWS': 3353,
        'name': 'Post-Oct-2013'
    }
}


def subset_to_colorado(lat_array, lon_array, data_array):
    """Subset SNODAS grid to Colorado mountain region."""
    lat_mask = (lat_array >= CO_BOUNDS['lat_min']) & (lat_array <= CO_BOUNDS['lat_max'])
    lon_mask = (lon_array >= CO_BOUNDS['lon_min']) & (lon_array <= CO_BOUNDS['lon_max'])
    
    lat_indices = np.where(lat_mask)[0]
    lon_indices = np.where(lon_mask)[0]
    
    lat_subset = lat_array[lat_indices]
    lon_subset = lon_array[lon_indices]
    
    if data_array.ndim == 2:
        data_subset = data_array[np.ix_(lat_indices, lon_indices)]
    elif data_array.ndim == 3:
        data_subset = data_array[:, lat_indices, :][:, :, lon_indices]
    else:
        raise ValueError(f"Unsupported array dimension: {data_array.ndim}")
    
    return lat_subset, lon_subset, data_subset


def get_snodas_grid(date_str: str, cache_dir: str, subset_co: bool = True, verbose: bool = False):
    """Extract all available SNODAS variables for a specific date."""
    tar_filename = f"SNODAS_{date_str}.tar"
    data_base = "https://noaadata.apps.nsidc.org/NOAA/G02158/masked"
    year = date_str[:4]
    month = date_str[4:6]
    month_names = ["01_Jan", "02_Feb", "03_Mar", "04_Apr", "05_May", "06_Jun",
                   "07_Jul", "08_Aug", "09_Sep", "10_Oct", "11_Nov", "12_Dec"]
    month_dir = month_names[int(month) - 1]
    data_url = f"{data_base}/{year}/{month_dir}/{tar_filename}"
    
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, tar_filename)
    
    try:
        if os.path.exists(cache_path):
            if verbose:
                print(f"    Using cached: {date_str}")
            with open(cache_path, 'rb') as f:
                tar_data = BytesIO(f.read())
        else:
            if verbose:
                print(f"    Downloading: {date_str}")
            with urllib.request.urlopen(data_url, timeout=60) as response:
                tar_data = BytesIO(response.read())
                with open(cache_path, 'wb') as f:
                    f.write(tar_data.getvalue())
            tar_data.seek(0)
        
        variables_dict = {}
        grid_config = None
        grid_info = None
        
        with tarfile.open(fileobj=tar_data, mode='r') as tar:
            for member in tar.getmembers():
                if member.name.endswith('.dat.gz'):
                    codes = re.findall(r'(\d{4})', member.name)
                    
                    var_code = None
                    for code in codes:
                        if code in VAR_NAMES:
                            var_code = code
                            break
                    
                    if var_code is None:
                        if '1036' in member.name:
                            var_code = '1036'
                        elif '1034' in member.name:
                            var_code = '1034'
                        elif '1038' in member.name:
                            var_code = '1038'
                        elif '1039' in member.name:
                            var_code = '1039'
                        elif '1033' in member.name:
                            var_code = '1033'
                        elif '1037' in member.name:
                            var_code = '1037'
                        else:
                            continue
                    
                    var_name = VAR_NAMES.get(var_code, f'var_{var_code}')
                    
                    var_file = tar.extractfile(member)
                    with gzip.open(var_file, 'rb') as gz_file:
                        data = gz_file.read()
                    
                    if grid_config is None:
                        num_values = len(data) // 2
                        for config in GRID_CONFIGS.values():
                            if num_values == config['NCOLS'] * config['NROWS']:
                                grid_config = config
                                break
                        
                        if grid_config is None:
                            if verbose:
                                print(f"    Error: Unknown grid size for {date_str}")
                            return None
                        
                        XMIN = grid_config['XMIN']
                        YMAX = grid_config['YMAX']
                        XMAX = grid_config['XMAX']
                        YMIN = grid_config['YMIN']
                        NCOLS = grid_config['NCOLS']
                        NROWS = grid_config['NROWS']
                        CELLSIZE_X = (XMAX - XMIN) / NCOLS
                        CELLSIZE_Y = (YMAX - YMIN) / NROWS
                        
                        lon = np.linspace(XMIN + CELLSIZE_X/2, XMAX - CELLSIZE_X/2, NCOLS)
                        lat = np.linspace(YMAX - CELLSIZE_Y/2, YMIN + CELLSIZE_Y/2, NROWS)
                    
                    NCOLS = grid_config['NCOLS']
                    NROWS = grid_config['NROWS']
                    values = struct.unpack(f">{NCOLS * NROWS}h", data)
                    var_array = np.array(values, dtype=np.float32).reshape((NROWS, NCOLS))
                    
                    var_array = var_array.astype(np.float32) / 1000.0
                    var_array[var_array < 0.01] = 0.0
                    var_array[var_array == SNODAS_NODATA / 1000.0] = np.nan
                    
                    if subset_co:
                        lat_sub, lon_sub, var_array = subset_to_colorado(lat, lon, var_array)
                        if grid_info is None:
                            grid_info = {
                                'lat': lat_sub,
                                'lon': lon_sub,
                                'config': grid_config,
                                'date': date_str,
                                'subset_co': True
                            }
                    else:
                        if grid_info is None:
                            grid_info = {
                                'lat': lat,
                                'lon': lon,
                                'config': grid_config,
                                'date': date_str,
                                'subset_co': False
                            }
                    
                    variables_dict[var_name] = var_array
        
        if not variables_dict:
            if verbose:
                print(f"    Error: No variables found in {date_str}")
            return None
        
        return variables_dict, grid_info
        
    except Exception as e:
        if verbose:
            print(f"    Error processing {date_str}: {e}")
        return None


def build_year_dataset(year: int, output_dir: str, cache_dir: str, 
                      subset_co: bool = True, rebuild: bool = False, 
                      verbose: bool = True) -> bool:
    """Build or update netCDF dataset for a single year with all available variables."""
    os.makedirs(output_dir, exist_ok=True)
    
    if subset_co:
        output_file = os.path.join(output_dir, f"snodas_co_{year}.nc")
    else:
        output_file = os.path.join(output_dir, f"snodas_{year}.nc")
    
    start_date = pd.Timestamp(f"{year}-01-01")
    if year == pd.Timestamp.now().year:
        end_date = pd.Timestamp.now().date()
    else:
        end_date = pd.Timestamp(f"{year}-12-31").date()
    
    all_dates = pd.date_range(start_date, end_date, freq='D')
    
    if verbose:
        print(f"\nProcessing year {year} ({len(all_dates)} days)...")
        if subset_co:
            print(f"  Subsetting to Colorado: {CO_BOUNDS['lat_min']}-{CO_BOUNDS['lat_max']}°N, {CO_BOUNDS['lon_min']}-{CO_BOUNDS['lon_max']}°W")
    
    existing_dates = set()
    if os.path.exists(output_file) and not rebuild:
        try:
            ds_existing = xr.open_dataset(output_file)
            existing_dates = set(pd.to_datetime(ds_existing.time.values).strftime('%Y%m%d'))
            ds_existing.close()
            if verbose:
                print(f"  Found existing file with {len(existing_dates)} dates")
        except Exception as e:
            if verbose:
                print(f"  Warning: Could not read existing file: {e}")
    
    dates_to_process = []
    for date in all_dates:
        date_str = date.strftime('%Y%m%d')
        if date_str not in existing_dates:
            dates_to_process.append(date_str)
    
    if not dates_to_process:
        if verbose:
            print(f"  ✓ Year {year} is complete. No new dates to process.")
        return True
    
    if verbose:
        print(f"  Processing {len(dates_to_process)} new/missing dates...")
    
    all_variables = {}
    dates = []
    grid_info = None
    failed_dates = []
    
    for idx, date_str in enumerate(dates_to_process, 1):
        if verbose and idx % 30 == 0:
            print(f"    Progress: {idx}/{len(dates_to_process)} ({100*idx/len(dates_to_process):.1f}%)")
        
        result = get_snodas_grid(date_str, cache_dir, subset_co=subset_co, verbose=False)
        if result is not None:
            var_dict, info = result
            dates.append(pd.to_datetime(date_str, format='%Y%m%d'))
            
            for var_name, grid in var_dict.items():
                if var_name not in all_variables:
                    all_variables[var_name] = []
                all_variables[var_name].append(grid)
            
            if grid_info is None:
                grid_info = info
        else:
            failed_dates.append(date_str)
    
    if not all_variables:
        if verbose:
            print(f"  ✗ No data retrieved for year {year}")
        return False
    
    if verbose:
        print(f"  ✓ Retrieved {len(dates)}/{len(dates_to_process)} dates")
        print(f"  Variables found: {', '.join(sorted(all_variables.keys()))}")
        if failed_dates:
            print(f"  ⚠ Failed dates: {len(failed_dates)}")
    
    lat = grid_info['lat']
    lon = grid_info['lon']
    
    # Filter variables to only include those with data for all dates
    # Some variables (like snow_cover) may not be available for all dates
    expected_time_steps = len(dates)
    data_vars = {}
    skipped_vars = []
    
    for var_name, grids in all_variables.items():
        if len(grids) == expected_time_steps:
            var_3d = np.stack(grids, axis=0)
            data_vars[var_name] = (['time', 'latitude', 'longitude'], var_3d)
        else:
            skipped_vars.append(f"{var_name} ({len(grids)}/{expected_time_steps} dates)")
    
    if skipped_vars and verbose:
        print(f"  ⚠ Skipped variables with incomplete data: {', '.join(skipped_vars)}")
    
    if not data_vars:
        if verbose:
            print(f"  ✗ No variables with complete data for all dates")
        return False
    
    ds_new = xr.Dataset(
        data_vars,
        coords={
            'time': pd.to_datetime(dates),
            'latitude': lat,
            'longitude': lon,
        },
        attrs={
            'title': f'SNODAS Dataset - {year}' + (' (Colorado)' if subset_co else ''),
            'source': 'NOAA NSIDC SNODAS',
            'units': 'meters',
            'nodata': 'NaN',
            'grid_config': grid_info['config']['name'],
            'variables': ', '.join(sorted(all_variables.keys())),
            'colorado_bounds': str(CO_BOUNDS) if subset_co else 'full_conus'
        }
    )
    
    if os.path.exists(output_file) and not rebuild and existing_dates:
        try:
            ds_existing = xr.open_dataset(output_file)
            ds_combined = xr.concat([ds_existing, ds_new], dim='time')
            ds_combined = ds_combined.sortby('time')
            ds_existing.close()
            ds_new = ds_combined
            if verbose:
                print(f"  ✓ Merged with existing data")
        except Exception as e:
            if verbose:
                print(f"  Warning: Could not merge with existing file: {e}")
    
    encoding = {}
    for var_name in all_variables.keys():
        encoding[var_name] = {
            'zlib': True,
            'complevel': 4,
            'dtype': 'float32'
        }
    
    if verbose:
        print(f"  Saving to {output_file}...")
    
    ds_new.to_netcdf(output_file, encoding=encoding)
    
    if verbose:
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"  ✓ Saved: {file_size_mb:.2f} MB")
        print(f"    Dimensions: {ds_new.sizes}")
        print(f"    Variables: {', '.join(sorted(all_variables.keys()))}")
        print(f"    Time range: {ds_new.time.min().values} to {ds_new.time.max().values}")
    
    return True


def main():
    """Main execution."""
    print("=" * 60)
    print("SNODAS netCDF Dataset Builder")
    print("=" * 60)
    
    if START_YEAR > END_YEAR:
        raise ValueError(f"start_year ({START_YEAR}) must be <= end_year ({END_YEAR})")
    
    current_year = pd.Timestamp.now().year
    end_year = min(END_YEAR, current_year)
    
    if END_YEAR > current_year:
        print(f"⚠ Warning: end_year ({END_YEAR}) is in the future. Clamping to {current_year}.")
    
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    os.makedirs(CACHE_DIRECTORY, exist_ok=True)
    
    print(f"\nProcessing years {START_YEAR} to {end_year}")
    print(f"Output directory: {OUTPUT_DIRECTORY}")
    print(f"Cache directory: {CACHE_DIRECTORY}")
    print(f"Subset to Colorado: {SUBSET_TO_COLORADO}")
    print(f"Rebuild existing: {REBUILD_EXISTING}")
    print("\n" + "=" * 60)
    
    successful_years = []
    failed_years = []
    
    for year in range(START_YEAR, end_year + 1):
        try:
            success = build_year_dataset(
                year=year,
                output_dir=OUTPUT_DIRECTORY,
                cache_dir=CACHE_DIRECTORY,
                subset_co=SUBSET_TO_COLORADO,
                rebuild=REBUILD_EXISTING,
                verbose=True
            )
            if success:
                successful_years.append(year)
            else:
                failed_years.append(year)
        except Exception as e:
            print(f"\n✗ Error processing year {year}: {e}")
            failed_years.append(year)
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✓ Successful years: {len(successful_years)}")
    if successful_years:
        print(f"  {successful_years}")
    if failed_years:
        print(f"✗ Failed years: {len(failed_years)}")
        print(f"  {failed_years}")
    print("\n" + "=" * 60)
    
    # List created files
    import glob
    nc_files = sorted(glob.glob(os.path.join(OUTPUT_DIRECTORY, "snodas*.nc")))
    if nc_files:
        print(f"\nCreated {len(nc_files)} file(s):")
        total_size = 0
        for nc_file in nc_files:
            file_size = os.path.getsize(nc_file)
            file_size_mb = file_size / (1024 * 1024)
            total_size += file_size
            print(f"  {os.path.basename(nc_file):30s} {file_size_mb:8.2f} MB")
        total_size_gb = total_size / (1024 * 1024 * 1024)
        print(f"  {'Total':30s} {total_size_gb:8.2f} GB")


if __name__ == "__main__":
    main()

