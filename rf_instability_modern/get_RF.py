"""
Wrapper module for RF instability analysis using pyunstable.
Provides create_RFprof() function compatible with existing notebook code.
"""
import pandas as pd
import numpy as np
import pyunstable


def create_RFprof(prof, slopeangle, model):
    """
    Create RF profile dataframe with features and P_unstable.
    
    Args:
        prof: Profile dictionary from readProfile.read_profile()
        slopeangle: Slope angle in degrees
        model: Random Forest model (loaded with joblib)
    
    Returns:
        DataFrame with features and P_unstable column
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
    
    return features

