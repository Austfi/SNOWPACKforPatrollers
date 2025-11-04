"""
Plotting functions for RF instability analysis.

This module provides plotting functions compatible with the original RF instability model
workflow from the WSL/SLF repository:
https://git.wsl.ch/mayers/random_forest_snow_instability_model.git

Original plotting code by: Stephanie Mayer (WSL Institute for Snow and Avalanche Research SLF)
Original model by: mayers, fherla (WSL Institute for Snow and Avalanche Research SLF)

Functions:
- plot_sp_single_P0: Plot single profile with grain types, hardness, and P_unstable
- plot_evo_SP: Plot seasonal evolution of P_unstable over time
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import datetime


def plot_sp_single_P0(fig, ax, df_prof, var='P_unstable', colorbar=True):
    """
    Plot single profile with grain types, hardness, and P_unstable.
    Matches original implementation by Stephanie Mayer.
    
    Args:
        fig: matplotlib figure
        ax: matplotlib axes
        df_prof: DataFrame with layer_top, hardness, graintype, and variable column
        var: Variable name to plot (default: 'P_unstable')
        colorbar: Whether to show grain type colorbar
    """
    # Check required columns
    required_cols = ['layer_top', 'hardness', 'graintype', var]
    missing_cols = [col for col in required_cols if col not in df_prof.columns]
    if missing_cols:
        raise ValueError(f"DataFrame must contain columns: {missing_cols}")
    
    # Extract data
    hh = df_prof['hardness'].values
    layer_top = df_prof['layer_top'].values
    P_unstable = df_prof[var].values
    nr_uppermost = len(layer_top) - 1
    
    # Extract grain type (first two digits)
    gt = np.divmod(df_prof['graintype'].values, 100)[0].astype(int)
    
    # Grain type colormap (original colors)
    cmap = ['greenyellow', 'darkgreen', 'pink', 'lightblue', 'blue', 'magenta', 'red', 'cyan', 'lightblue']
    
    # Handle depth units - convert to cm if needed (original uses cm)
    # Assume if max depth < 10, it's in meters, otherwise cm
    if layer_top[-1] < 10:
        layer_top_cm = layer_top * 100
    else:
        layer_top_cm = layer_top
    
    # Plot contours
    ax.plot([0, 0], [0, layer_top_cm[-1]], c='black', linewidth=1)
    ax.plot([0, -hh[0]], [0, 0], c='black', linewidth=1)
    
    # Plot profile against hand hardness
    y1 = 0
    for iy, y in enumerate(layer_top_cm):
        if iy == nr_uppermost:
            ax.plot([0, -hh[iy]], [y, y], c='black', linewidth=1)
        else:
            ax.plot([0, np.max([-hh[iy], -hh[iy + 1]])], [y, y], c='black', linewidth=1)
        ax.plot([-hh[iy], -hh[iy]], [y1, y], c='black', linewidth=1)
        # Fill with grain type color
        gt_idx = int(gt[iy]) - 1
        if 0 <= gt_idx < len(cmap):
            ax.fill_betweenx([y1, y], 0, -hh[iy], color=cmap[gt_idx])
        y1 = y
    
    # Set x-axis for hand hardness
    ax.set_xlim(0, 5.5)
    ax.set_xticks(np.arange(0, 5.5, 1))
    ax.set_xticklabels(['', 'F ', '4F', '1F', 'P', 'K'])
    ax.set_ylabel('Snow depth [cm]')
    ax.set_xlabel('hand hardness')
    
    # Plot P_unstable on second x-axis
    ax11 = None
    if len(P_unstable) > 0:
        ax11 = ax.twiny()
        height_var = np.repeat(np.concatenate((np.array([0]), layer_top_cm)), 2)[1:-1]
        var_repeat = np.repeat(P_unstable, 2)
        ax11.plot(var_repeat, height_var, c='black', linewidth=2.5, label='$\\mathregular{P_{unstable}}$')
        ax11.set_xlim([0, 1])
        ax11.set_xticks([0, 0.5, 1])
        ax11.set_xticklabels(['0', '0.5', '1'])
        ax11.set_xlabel('$P_{unstable}$')
        ax11.legend(loc=1)
    
    # Grain type colorbar
    if colorbar:
        # Adjust subplot to make room for colorbar
        plt.subplots_adjust(bottom=0.1, right=0.82, top=0.9)
        ax_pos = np.array(ax.get_position())
        # Position colorbar adjacent to plot (right edge of plot + small gap)
        colorbar_x = ax_pos[1, 0] + 0.02  # Just to the right of plot
        colorbar_width = 0.02
        axcolor = fig.add_axes([colorbar_x, ax_pos[0, 1], colorbar_width, ax_pos[1, 1] - ax_pos[0, 1]])
        cmapcolorbar = ['greenyellow', 'darkgreen', 'pink', 'lightblue', 'blue', 'magenta', 'red', 'cyan']
        ticklabels = ['PP', 'DF', 'RG', 'FC', 'DH', 'SH', 'MF', 'IF']
        cmapc = mpl.colors.ListedColormap(cmapcolorbar)
        bounds = np.arange(len(cmapcolorbar) + 1)
        norm = mpl.colors.BoundaryNorm(bounds, cmapc.N)
        # Create ticks at midpoints: [0.5, 1.5, 2.5, ..., 7.5] (8 ticks for 8 labels)
        ticks = np.arange(len(cmapcolorbar)) + 0.5
        cb1 = mpl.colorbar.ColorbarBase(axcolor, cmap=cmapc, norm=norm, ticks=ticks, 
                                        orientation='vertical', label='grain type')
        cb1.ax.set_yticklabels(ticklabels)
    
    return ax11


def plot_evo_SP(df_evo, fig, ax, start, stop, var='P_unstable', colorbar=True, resolution='D'):
    """
    Plot seasonal evolution of instability probability.
    Matches original implementation by Stephanie Mayer.
    
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
    
    # Grain type colormap (for graintype plotting)
    cgt = ['greenyellow', 'darkgreen', 'pink', 'lightblue', 'blue', 'magenta', 'red', 'cyan', 'lightblue']
    cmap_gt = mcolors.ListedColormap(cgt)
    
    # Get date range
    mydates = pd.date_range(start, stop, freq=resolution).tolist()
    
    # Plot each date individually (original approach)
    for ts in mydates:
        df = df_evo[df_evo['datetime'] == ts].copy()
        df.reset_index(inplace=True, drop=True)
        
        if len(df) == 0:
            continue
        
        depth = np.array(df['layer_top'])
        # Handle depth units - convert to cm if needed (original uses cm)
        if depth.max() < 10:
            depth = depth * 100
        depth_edges = np.concatenate((np.array([0]), depth))
        
        # Handle graintype plotting
        if var == 'graintype':
            if 'graintype' not in df.columns:
                continue
            gt = np.divmod(df['graintype'].values, 100)[0].astype(int)
            if len(gt) == 0:
                continue
            x = [ts, ts + datetime.timedelta(days=1)]
            # For pcolormesh with shading='flat':
            # X edges: 2 elements (M=2), Y edges: len(depth_edges) elements (N)
            # C needs shape (N-1, M-1) = (len(depth_edges)-1, 1)
            # So reshape gt to (len(gt), 1) instead of (len(gt), 2)
            gt_reshaped = gt.reshape(-1, 1)
            cb = ax.pcolormesh(x, depth_edges, gt_reshaped, 
                              cmap=cmap_gt, vmin=0.5, vmax=9.5)
        else:
            # Plot P_unstable (or other variable)
            p = df[var].values
            if len(p) == 0:
                continue
            
            # Use viridis colormap (original choice)
            cmap = plt.cm.viridis
            cmaplist = [cmap(i) for i in range(cmap.N)]
            cmap = mpl.colors.LinearSegmentedColormap.from_list('Custom cmap', cmaplist, cmap.N)
            
            # Define bins and normalize
            bounds = np.linspace(0, 1, 11)
            norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
            
            x = [ts, ts + datetime.timedelta(days=1)]
            # For pcolormesh with shading='flat':
            # X edges: 2 elements (M=2), Y edges: len(depth_edges) elements (N)
            # C needs shape (N-1, M-1) = (len(depth_edges)-1, 1)
            # So reshape p to (len(p), 1) instead of (len(p), 2)
            p_reshaped = p.reshape(-1, 1)
            cb = ax.pcolormesh(x, depth_edges, p_reshaped, 
                              cmap=cmap, norm=norm)
    
    ax.set_ylabel('Snow depth [cm]')
    ax.set_xlabel('Date')
    ax.set_xlim(start, stop)
    
    # Format dates
    fig.autofmt_xdate()
    ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
    
    # Colorbar
    if colorbar:
        # Adjust subplot to make room for colorbar
        plt.subplots_adjust(bottom=0.15, right=0.85, top=0.9)
        ax_pos = np.array(ax.get_position())
        # Position colorbar adjacent to plot (right edge of plot + small gap)
        colorbar_x = ax_pos[1, 0] + 0.02  # Just to the right of plot
        colorbar_width = 0.02
        axcolor = fig.add_axes([colorbar_x, ax_pos[0, 1], colorbar_width, ax_pos[1, 1] - ax_pos[0, 1]])
        
        if var == 'graintype':
            cgt_no_rf = ['greenyellow', 'darkgreen', 'pink', 'lightblue', 'blue', 'magenta', 'red', 'cyan']
            cmapc = mcolors.ListedColormap(np.array(cgt_no_rf))
            # Create 8 ticks for 8 grain types at midpoints
            ticks = np.arange(8) + 0.5
            norm = mpl.colors.BoundaryNorm(np.arange(9), cmapc.N)
            cbar = mpl.colorbar.ColorbarBase(axcolor, cmap=cmapc, norm=norm, ticks=ticks,
                                            orientation='vertical')
            cbar.set_ticklabels(['PP', 'DF', 'RG', 'FC', 'DH', 'SH', 'MF(cr)', 'IF'])
            cbar.set_label('Grain type')
        else:
            cbar = plt.colorbar(cb, axcolor)
            cbar.set_label('$P_\\mathrm{unstable}$')
    
    fig.autofmt_xdate()
    
    return cb
