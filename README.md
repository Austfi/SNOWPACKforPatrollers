# SNOWPACKforPatrollers

This repository is to help get more people running the SNOWPACK model and getting tools used in snow instability modeling used by those without extensive coding backgrounds. This idea developed out of the growing gap from finishing the highest level of avalanche professional education in the United States (Pro2) and the tools that large avalanche forecasting centers are currently using. The goal of this is to get more people using the tools and techniques that high level forecasting and research are using currently. 

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Austfi/SNOWPACKforPatrollers/blob/main/SNOWPACKforPatrollers.ipynb)

---
<img width="350" height="350" alt="image" src="https://github.com/user-attachments/assets/bf34d4b6-4378-43e3-82aa-6e65556023e2" />

## Notebooks

This repository contains four main notebooks:

1. **`SNOWPACKforPatrollers.ipynb`** — Main notebook for running SNOWPACK simulations
2. **`Snowprofile_Colab_Tutorial.ipynb`** — Tutorial for reading, plotting, and analyzing CAAML v6 snow profile files
3. **`RF_Instability.ipynb`** — Random Forest snow instability analysis using SNOWPACK PRO files
4. **`HRRR_OpenMeteo_to_SMET.ipynb`** — Download HRRR historical forecast data and convert to SMET format

---

## SNOWPACKforPatrollers.ipynb

This notebook automates the entire workflow of:
1. **Installing and compiling** SNOWPACK and MeteoIO from source
2. **Fetching historical weather data** from multiple forecast models
3. **Configuring virtual slopes** (flat, N, E, S, W, or custom aspects)
4. **Running SNOWPACK simulations** for multiple slope aspects
5. **Downloading profile outputs** (`.pro` files) to visualize in [niViz](https://run.niviz.org)

All parameters are exposed as form fields.

---

##  Workflow Overview

### Step 1: Environment Setup 
Run these cells once per session:
- Install system packages (6 minutes for MeteoIO, 2 minutes for SNOWPACK)
- Download and compile SNOWPACK/MeteoIO
- Set up paths
- Establishes a runtime and file structure to run SNOWPACK 

### Step 2: Generate Configuration Files 
**Configurable parameters:**
- `station_id` — Unique identifier for your location
- `station_name` — Human-readable name
- `latitude`, `longitude`, `altitude` — Site coordinates
- `profile_date` — Start date for simulation (ISO format: `YYYY-MM-DDTHH:MM:SS`)
  - This will be the date SNOWPACK simulation starts from
- `num_slopes`, `default_slope_angle` — Number and steepness of virtual slopes
- `north_slope`, `east_slope`, `south_slope`, `west_slope` — Toggle cardinal aspects
- `custom_directions` — Comma-separated azimuth angles (e.g., `45,135,225,315`)
- `snowpack_end_date_input` - Chooses the end of the simulation
- Adding more form based options for selecting .ini and .sno files.
- Current structure is to start from a no snow on the ground profile. Initial .sno profile starts from zero snow layers. 

**Output:** Creates `.sno` (snow profile initialization) and `.ini` (SNOWPACK configuration) files.

### Step 3: Fetch Weather Data
**Configurable parameters:**
- `latitude`, `longitude`, `altitude` — Location (should match Step 2)
- `station_name` — Station identifier
- `start_date`, `end_date` — Simulation period (format: `YYYY-MM-DD`)
- `model_selection` — Weather model
- Time period for this should cover and extend over the end date choosen for the simulation.

**Output:** Generates `.smet` file with hourly meteorological forcing data.

### Step 4: Run SNOWPACK 
Executes the compiled `snowpack` binary with your configuration.
- Processes all virtual slopes in parallel
- Applies snow erosion and redistribution algorithms
- Writes profile outputs every 3 hours (configurable)

**Runtime:** Typically 1–5 minutes depending on simulation length and number of slopes.

### Step 5: Download Results 
- Collects all `.pro` files from the output directory
- Packages them into `snowpack_profiles.zip`
- Automatic download of .zip file begins
- Provides instructions for opening in [niViz](https://run.niviz.org)

### Configuration Reference (`master.ini`)

The repository includes a `master.ini` file which serves as a **professional reference configuration** (based on CAA/CAIC standards). 

> [!NOTE]
> This file is **not directly used** by the `SNOWPACKforPatrollers.ipynb` notebook. The notebook dynamically generates its own `.ini` file based on the form parameters you select.
> The `master.ini` file is provided for educational purposes to compare against the notebook-generated configuration.

---

## Snowprofile_Colab_Tutorial.ipynb

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Austfi/SNOWPACKforPatrollers/blob/dev/Snowprofile_Colab_Tutorial.ipynb)

Tutorial for working with CAAML v6 snow profile files using the [`snowprofile`](https://snowprofile.readthedocs.io/en/latest/) Python package. Teaches you how to:
- Load and read CAAML files
- Explore snow profile data (stratigraphy, temperature, density profiles)
- Analyze temperature gradients
- Create visualizations

**Use case**: Process and visualize snow profile data from field observations or SNOWPACK outputs.

---

## RF_Instability.ipynb

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Austfi/SNOWPACKforPatrollers/blob/dev/RF_Instability.ipynb)

Random Forest snow instability analysis using SNOWPACK PRO files. Features:
- **Single profile analysis**: Analyze instability probabilities for a specific timestamp
- **Seasonal evolution**: Track instability probabilities over time
- **CSV export**: Export daily instability metrics for further analysis

Automatically downloads and selects the best RF model version for your Python environment. Based on the [WSL/SLF Random Forest Snow Instability Model](https://git.wsl.ch/mayers/random_forest_snow_instability_model.git) (WSL Institute for Snow and Avalanche Research SLF).

**Use case**: Analyze SNOWPACK simulation outputs to assess snowpack instability probabilities.

---

## HRRR_OpenMeteo_to_SMET.ipynb

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Austfi/SNOWPACKforPatrollers/blob/dev/HRRR_OpenMeteo_to_SMET.ipynb)

Downloads HRRR (High-Resolution Rapid Refresh) historical forecast data from the Open-Meteo API and converts it to SMET 1.2 format for use with SNOWPACK. Features:
- **HRRR data download**: Query historical forecast data for any location
- **SNODAS integration**: Automatically integrates SNODAS snow depth data when available
- **SMET conversion**: Converts meteorological data to SMET 1.2 format compatible with SNOWPACK
- **Data visualization**: Creates plots to visualize the downloaded data

**Use case**: Generate SMET files from HRRR forecast data for SNOWPACK simulations, either as a standalone workflow or as an alternative to the weather data fetching in the main SNOWPACK notebook.

---

## File Structure

## Folders 
content/                        # Default folder in Google Colab for files viewing upon opening a runtime
├── input/                      # Folder created to store .sno files and .smet files
  ├── $CREATEDFILE.sno          # Created .sno files for virtual slopes will be here. The will have a $FILE1.sno, $FILE2... naming.
  └── $CREATEDFILE.smet         # .smet file created from historic weather forecast
├── config/                     # Holds .ini file and output folder
  ├── $CREATEDFILE.ini          # Created .ini file for the SNOWPACK run
  └── output/                   # Holds the .pro, .haz, .smet, and other output files that are options in the .ini file structure
    └── $CREATEDFILE.pro        # Created .pro files from SNOWPACK runs that are the snowprofile time series plots for NiViz
    
## Output Files

### `.pro` Files (Profile Outputs)
Each virtual slope generates its own `.pro` file:
- `keystone_model_res_0001.pro` — Flat terrain (if enabled)
- `keystone_model_res_0002.pro` — North-facing slope
- `keystone_model_res_0003.pro` — East-facing slope
- `keystone_model_res_0004.pro` — South-facing slope
- `keystone_model_res_0005.pro` — West-facing slope

### Visualizing in niViz
1. Go to [https://run.niviz.org](https://run.niviz.org)
2. Drag any `.pro` file into the browser window
3. Use the timeline slider to step through dates
4. Compare different aspects side-by-side

---

## Dependencies & Licenses

This project uses the following open-source software and data sources:

### Core Software Components

- **[SNOWPACK](https://github.com/snowpack-model/snowpack)** — Physical snow cover model  
  License: [LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.html)  
  Copyright: WSL Institute for Snow and Avalanche Research SLF  

- **[MeteoIO](https://github.com/snowpack-model/meteoio)** — Meteorological data preprocessing library  
  License: [LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.html)  
  Copyright: WSL Institute for Snow and Avalanche Research SLF

### Weather Data Source

- **[Open-Meteo API](https://open-meteo.com/)** — Historical weather data  
  License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)  
  Attribution: "Weather data by Open-Meteo.com"  
  Note: Open-Meteo aggregates data from national weather services (NOAA, DWD, ECMWF, etc.)

### Additional Tools

- **[snowprofile](https://snowprofile.readthedocs.io/en/latest/)** — Python package for reading, analyzing, and visualizing CAAML snow profile files  
  Used in: `Snowprofile_Colab_Tutorial.ipynb`

- **[Random Forest Snow Instability Model](https://git.wsl.ch/mayers/random_forest_snow_instability_model.git)** — Machine learning model for assessing snowpack instability  
  Authors: mayers, fherla (WSL Institute for Snow and Avalanche Research SLF)  
  Used in: `RF_Instability.ipynb`

---

## Links

- [SNOWPACK Official Website](https://models.slf.ch/p/snowpack/)
- [SNOWPACK GitHub Repository](https://github.com/snowpack-model/snowpack)
- [niViz Online Visualizer](https://run.niviz.org)
- [MeteoIO Documentation](https://models.slf.ch/p/meteoio/)
- [snowprofile Documentation](https://snowprofile.readthedocs.io/en/latest/)
- [Open-Meteo API](https://open-meteo.com/)

---

