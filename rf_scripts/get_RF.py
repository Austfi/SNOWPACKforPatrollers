"""
Wrapper module for RF instability analysis using pyunstable.

This module provides compatibility with the original RF instability model API
from the WSL/SLF repository:
https://git.wsl.ch/mayers/random_forest_snow_instability_model.git

Original code by: mayers, fherla (WSL Institute for Snow and Avalanche Research SLF)

The underlying functions (comp_features, comp_rf_probability) are from pyunstable.py,
which contains the original implementation. This wrapper provides the create_RFprof()
function for compatibility with existing notebook workflows.
"""
import pandas as pd
import numpy as np
import pyunstable


def create_RFprof(prof, slopeangle, model):
    """
    Create RF profile dataframe with features and P_unstable.
    Includes original profile fields (hardness, graintype) for plotting compatibility.
    
    Args:
        prof: Profile dictionary from readProfile.read_profile()
        slopeangle: Slope angle in degrees
        model: Random Forest model (loaded with joblib)
    
    Returns:
        DataFrame with features, P_unstable, and original profile fields
    """
    # Compute features using pyunstable
    features = pyunstable.comp_features(prof, slopeangle)
    
    # Compute P_unstable probabilities
    P_unstable = pyunstable.comp_rf_probability(features, model)
    
    # Add P_unstable to features dataframe
    features['P_unstable'] = P_unstable
    
    # Add layer_top if available
    if 'height' in prof:
        features['layer_top'] = prof['height']
    
    # Add original profile fields for plotting compatibility
    if 'hand_hardness' in prof:
        features['hardness'] = prof['hand_hardness']
    elif 'hardness' in prof:
        features['hardness'] = prof['hardness']
    
    if 'grain_type' in prof:
        features['graintype'] = prof['grain_type']
    elif 'graintype' in prof:
        features['graintype'] = prof['graintype']
    
    return features


# Expose original function names for direct API compatibility
# These match the original getRF module API from the WSL/SLF repository
def comp_features(prof, slopeangle):
    """
    Compute features for RF model (original API compatibility).
    
    Args:
        prof: Profile dictionary from readProfile.read_profile()
        slopeangle: Slope angle in degrees
    
    Returns:
        DataFrame with features: ['viscdefrate', 'rcflat', 'sphericity', 'grainsize', 'penetrationdepth', 'slab_rhogs']
    """
    return pyunstable.comp_features(prof, slopeangle)


def comp_rf_probability(features, model):
    """
    Compute RF instability probability (original API compatibility).
    
    Args:
        features: DataFrame with features from comp_features()
        model: Random Forest model (loaded with joblib)
    
    Returns:
        Array of P_unstable values
    """
    return pyunstable.comp_rf_probability(features, model)

