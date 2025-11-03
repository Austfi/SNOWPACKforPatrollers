# SNOWPACKforPatrollers

A Google Colab notebook for running the SNOWPACK snow cover model to support avalanche forecasting and snowpack analysis. Designed specifically for those who want to run snowpack simulations without terminal commands or coding experience.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Austfi/SNOWPACKforPatrollers/blob/main/SNOWPACKforPatrollers.ipynb)

---

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
---

## Links

- [SNOWPACK Official Website](https://models.slf.ch/p/snowpack/)
- [SNOWPACK GitHub Repository](https://github.com/snowpack-model/snowpack)
- [niViz Online Visualizer](https://run.niviz.org)
- [MeteoIO Documentation](https://models.slf.ch/p/meteoio/)
- [Open-Meteo API](https://open-meteo.com/)

---

