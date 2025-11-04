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
    
    # Set colormap - use YlOrRd (Yellow-Orange-Red) for intuitive visualization:
    # Yellow = low instability (stable), Red = high instability (unstable)
    cmap = plt.cm.get_cmap('YlOrRd')
    
    # Plot with correct dimensions
    # x_edges: (2,), depth_edges: (N+1,), C: (N, 1)
    im = ax.pcolormesh(x_edges, depth_edges, C, cmap=cmap, shading='flat', vmin=0, vmax=1)
    
    if colorbar:
        cbar = plt.colorbar(im, ax=ax, label=var)
        cbar.ax.tick_params(labelsize=10)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, depth.max() if len(depth) > 0 else 1)
    ax.invert_yaxis()
    ax.set_xlabel('')
    ax.set_xticks([])
    ax.set_ylabel('Snow depth [m]', fontsize=12)
    ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_title('P_unstable Profile', fontsize=13, fontweight='bold')


def plot_evo_SP(df_evo, fig, ax, start, stop, var='P_unstable', colorbar=True, resolution='D'):
    """
    Plot seasonal evolution of instability probability.
    Matches original 2022 implementation style using actual datetime values and layer depths.
    
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
    
    # Create date range matching the original style
    date_range = pd.date_range(start, stop, freq=resolution)
    
    # Get unique dates that actually exist in the data
    dates_in_data = sorted(df_evo['datetime'].unique())
    
    if len(dates_in_data) < 2:
        raise ValueError("Need at least 2 dates for evolution plot")
    
    # Build a unified depth grid from all unique layer_top values across all dates
    # This preserves the actual layer structure rather than interpolating to a fixed grid
    all_depths = sorted(df_evo['layer_top'].unique())
    if len(all_depths) == 0:
        raise ValueError("No depth data found")
    
    # Create depth edges: [0, depth[0], depth[1], ..., depth[N-1]]
    # Using actual layer depths preserves the original plotting style
    if len(all_depths) == 1:
        depth_edges = np.array([0.0, all_depths[0]])
    else:
        depth_edges = np.concatenate([[0.0], all_depths])
    
    # Create a pivot table: rows = depths, columns = dates
    # This matches the original implementation structure
    pivot_table = df_evo.pivot_table(
        index='layer_top', 
        columns='datetime', 
        values=var,
        aggfunc='first'  # Take first value if duplicates exist
    )
    
    # Sort by depth (descending, so surface is at top)
    pivot_table = pivot_table.sort_index(ascending=False)
    
    # Reindex to include all dates in date_range (fill missing with NaN)
    pivot_table = pivot_table.reindex(columns=date_range)
    
    # Reindex to include all depth edges (for proper pcolormesh edges)
    # Use the actual depth values and interpolate if needed
    depth_index = pivot_table.index.values
    Z = pivot_table.values  # Shape: (n_depths, n_dates)
    
    # For pcolormesh with shading='flat':
    # - X edges: datetime edges (n_dates + 1)
    # - Y edges: depth edges (n_depths + 1)
    # - C values: Z (n_depths, n_dates) = (N, M) where N=n_depths, M=n_dates
    # But we need C shape (N-1, M-1) for shading='flat'
    
    # Create depth edges from the actual depth values
    # depth_index is sorted descending (surface to bottom), so depth[0] is largest (surface)
    if len(depth_index) > 1:
        # Sort depths ascending for edge calculation (0 = surface, increasing = deeper)
        depths_sorted = np.sort(depth_index)
        depth_edges_actual = np.zeros(len(depths_sorted) + 1)
        depth_edges_actual[0] = 0.0  # Surface
        # Create edges as midpoints between consecutive depths
        for i in range(len(depths_sorted) - 1):
            depth_edges_actual[i + 1] = (depths_sorted[i] + depths_sorted[i + 1]) / 2
        # Last edge extends beyond deepest layer
        depth_edges_actual[-1] = depths_sorted[-1] + (depths_sorted[-1] - depths_sorted[-2]) / 2 if len(depths_sorted) > 1 else depths_sorted[-1] + 0.1
        # Reverse to match descending order (surface at top for plotting)
        depth_edges_actual = depth_edges_actual[::-1]
    else:
        depth_edges_actual = np.array([depth_index[0] + 0.1, 0.0]) if len(depth_index) > 0 else np.array([0.0, 1.0])
    
    # Create datetime edges
    if len(date_range) > 1:
        # Calculate half-interval for datetime edges
        half_interval = (date_range[1] - date_range[0]) / 2
        date_edges = pd.to_datetime(
            np.concatenate([
                [date_range[0] - half_interval],
                date_range + half_interval
            ])
        )
    else:
        half_interval = pd.Timedelta(days=0.5)
        date_edges = pd.to_datetime([
            date_range[0] - half_interval,
            date_range[0] + half_interval
        ])
    
    # For pcolormesh with shading='flat':
    # If X has M elements and Y has N elements, C must be (N-1, M-1)
    # Our Z is (n_depths, n_dates), so we need to adjust
    
    # Actually, with shading='flat', if we have:
    # - X edges: shape (M,) = len(date_edges)
    # - Y edges: shape (N,) = len(depth_edges_actual)
    # - C: shape (N-1, M-1) = (len(depth_edges_actual)-1, len(date_edges)-1)
    
    # But Z is (n_depths, n_dates) = (len(depth_index), len(date_range))
    # We need Z to be (len(depth_edges_actual)-1, len(date_edges)-1)
    
    # Since depth_edges_actual has len(depth_index)+1 elements and date_edges has len(date_range)+1 elements,
    # Z should be (len(depth_index), len(date_range)) which matches!
    
    # Plot with actual datetime values and actual depth values
    # Use YlOrRd (Yellow-Orange-Red) for intuitive visualization:
    # Yellow = low instability (stable), Red = high instability (unstable)
    cmap = plt.cm.get_cmap('YlOrRd')
    
    # Convert datetime edges to matplotlib date numbers for pcolormesh
    date_edges_num = mpl.dates.date2num(date_edges)
    
    # Ensure Z has correct shape: (N-1, M-1) where N=len(depth_edges_actual), M=len(date_edges)
    # Z currently is (len(depth_index), len(date_range))
    # depth_edges_actual has len(depth_index)+1 elements
    # date_edges has len(date_range)+1 elements
    # So Z shape (len(depth_index), len(date_range)) = (N-1, M-1) ✓
    
    im = ax.pcolormesh(date_edges_num, depth_edges_actual, Z, cmap=cmap, shading='flat', vmin=0, vmax=1)
    
    if colorbar:
        cbar = plt.colorbar(im, ax=ax, label=var)
        cbar.ax.tick_params(labelsize=10)
    
    # Format x-axis as dates
    ax.xaxis_date()
    fig.autofmt_xdate(rotation=45)
    
    ax.set_ylabel('Snow depth [m]', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.3, linestyle='--', which='both')
    ax.invert_yaxis()
    
    return fig

