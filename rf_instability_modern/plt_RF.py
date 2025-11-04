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
    
    # Get depth values (layer tops)
    depth = df_prof['layer_top'].values
    values = df_prof[var].values
    
    # Create depth edges for pcolormesh
    # For N layers, we need N+1 edges: [0, depth[0], depth[1], ..., depth[N-1]]
    if len(depth) > 1:
        depth_edges = np.concatenate([[0], depth])
    else:
        depth_edges = np.array([0, depth[0] if len(depth) > 0 else 1])
    
    # For pcolormesh with shading='flat':
    # - X edges: shape (M,) where M = number of X edges
    # - Y edges: shape (N,) where N = number of Y edges  
    # - C values: shape (N-1, M-1) where C[i,j] is the value for the cell between edges [i:i+1, j:j+1]
    
    # Create X edges: [0, 1] for a single column plot
    x_edges = np.array([0, 1])
    
    # Create C array: shape (len(depth_edges)-1, len(x_edges)-1) = (N, 1)
    # Each row represents one depth layer
    C = values.reshape(-1, 1)  # Shape: (N, 1)
    
    # Set colormap
    cmap = plt.cm.get_cmap('RdYlBu_r')
    
    # Plot with correct dimensions
    # x_edges: (2,), depth_edges: (N+1,), C: (N, 1)
    im = ax.pcolormesh(x_edges, depth_edges, C, cmap=cmap, shading='flat', vmin=0, vmax=1)
    
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
    # For pcolormesh with shading='flat':
    # - X edges: shape (M,) where M = number of X edges
    # - Y edges: shape (N,) where N = number of Y edges
    # - C values: shape (N-1, M-1)
    
    # Create X edges: need len(date_range) + 1 edges for len(date_range) cells
    x_centers = np.arange(len(date_range))
    if len(x_centers) > 1:
        # For M centers, we need M+1 edges: [center[0]-0.5, center[0]+0.5, center[1]+0.5, ..., center[M-1]+0.5]
        x_edges = np.concatenate([[x_centers[0] - 0.5], x_centers + 0.5])
    else:
        x_edges = np.array([x_centers[0] - 0.5, x_centers[0] + 0.5])
    
    depth_max = df_evo['layer_top'].max()
    depth_edges = np.linspace(0, depth_max, 21)  # 21 edges = 20 depth bins
    
    # Create mesh data: shape (len(depth_edges)-1, len(date_range))
    # Which is (N-1, M-1) where M = len(x_edges), N = len(depth_edges)
    Z = np.full((len(depth_edges) - 1, len(date_range)), np.nan)
    
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
    
    # Plot with correct dimensions
    # x_edges: (len(date_range)+1,), depth_edges: (21,), Z: (20, len(date_range))
    cmap = plt.cm.get_cmap('RdYlBu_r')
    im = ax.pcolormesh(x_edges, depth_edges, Z, cmap=cmap, shading='flat', vmin=0, vmax=1)
    
    if colorbar:
        plt.colorbar(im, ax=ax, label=var)
    
    # Set x-axis labels - use x_centers for tick positions
    num_ticks = min(10, len(date_range))
    tick_indices = np.linspace(0, len(x_centers) - 1, num_ticks, dtype=int)
    ax.set_xticks(x_centers[tick_indices])
    ax.set_xticklabels([date_range[i].strftime('%Y-%m-%d') for i in tick_indices], rotation=45)
    
    ax.set_ylabel('Snow depth [cm]')
    ax.invert_yaxis()
    ax.set_xlabel('Date')

