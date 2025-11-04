"""
Plotting functions for RF instability analysis.
Provides plotting functions compatible with existing notebook code.
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
import numpy as np


def plot_sp_single_P0(fig, ax, df_prof, var='P_unstable', colorbar=True):
    """
    Plot single profile with P_unstable or other variable.
    
    Args:
        fig: matplotlib figure
        ax: matplotlib axes
        df_prof: DataFrame with layer_top and variable column
        var: Variable name to plot (default: 'P_unstable')
        colorbar: Whether to show colorbar
    """
    if 'layer_top' not in df_prof.columns:
        raise ValueError("DataFrame must contain 'layer_top' column")
    
    if var not in df_prof.columns:
        raise ValueError(f"Variable '{var}' not found in DataFrame")
    
    # Get depth values
    depth = df_prof['layer_top'].values
    values = df_prof[var].values
    
    # Create depth edges for pcolormesh
    if len(depth) > 1:
        depth_edges = np.concatenate([[0], depth])
    else:
        depth_edges = np.array([0, depth[0] if len(depth) > 0 else 1])
    
    # Create mesh for pcolormesh
    x = np.array([0, 1])
    depth_mesh = np.tile(depth_edges.reshape(-1, 1), (1, 2))
    values_mesh = np.tile(values.reshape(-1, 1), (1, 2))
    
    # Set colormap
    cmap = plt.cm.get_cmap('RdYlBu_r')
    
    # Plot
    im = ax.pcolormesh(x, depth_mesh, values_mesh, cmap=cmap, shading='flat', vmin=0, vmax=1)
    
    if colorbar:
        plt.colorbar(im, ax=ax, label=var)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, depth.max() if len(depth) > 0 else 1)
    ax.invert_yaxis()
    ax.set_xlabel('')
    ax.set_xticks([])


def plot_evo_SP(df_evo, fig, ax, start, stop, var='P_unstable', colorbar=True, resolution='D'):
    """
    Plot seasonal evolution of instability probability.
    
    Args:
        df_evo: DataFrame with datetime, layer_top, and variable columns
        fig: matplotlib figure
        ax: matplotlib axes
        start: Start timestamp
        stop: Stop timestamp
        var: Variable name to plot (default: 'P_unstable')
        colorbar: Whether to show colorbar
        resolution: Resolution string (e.g., 'D' for daily)
    """
    if 'datetime' not in df_evo.columns or 'layer_top' not in df_evo.columns:
        raise ValueError("DataFrame must contain 'datetime' and 'layer_top' columns")
    
    if var not in df_evo.columns:
        raise ValueError(f"Variable '{var}' not found in DataFrame")
    
    # Get unique dates
    dates = sorted(df_evo['datetime'].unique())
    
    if len(dates) < 2:
        raise ValueError("Need at least 2 dates for evolution plot")
    
    # Create date range
    date_range = pd.date_range(start, stop, freq=resolution)
    
    # Prepare data for plotting
    x = np.arange(len(date_range))
    depth_max = df_evo['layer_top'].max()
    depth_edges = np.linspace(0, depth_max, 21)  # 20 depth bins
    
    # Create mesh data
    Z = np.full((len(depth_edges) - 1, len(x)), np.nan)
    
    for i, dt in enumerate(date_range):
        day_data = df_evo[df_evo['datetime'] == dt]
        if len(day_data) == 0:
            continue
        
        # Interpolate values to depth grid
        for j in range(len(depth_edges) - 1):
            depth_center = (depth_edges[j] + depth_edges[j + 1]) / 2
            # Find closest layer
            idx = np.abs(day_data['layer_top'].values - depth_center).argmin()
            Z[j, i] = day_data[var].iloc[idx]
    
    # Plot
    cmap = plt.cm.get_cmap('RdYlBu_r')
    im = ax.pcolormesh(x, depth_edges, Z, cmap=cmap, shading='flat', vmin=0, vmax=1)
    
    if colorbar:
        plt.colorbar(im, ax=ax, label=var)
    
    # Set x-axis labels
    ax.set_xticks(np.arange(0, len(date_range), max(1, len(date_range) // 10)))
    ax.set_xticklabels([date_range[i].strftime('%Y-%m-%d') for i in ax.get_xticks() if i < len(date_range)], rotation=45)
    
    ax.set_ylabel('Snow depth [cm]')
    ax.invert_yaxis()
    ax.set_xlabel('Date')

