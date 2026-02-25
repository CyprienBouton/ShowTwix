import numpy as np
import pandas as pd

import plotly.graph_objs as go

def build_line_dataframe(twix, trigger_method='ECG1'):
    """ Build a DataFrame containing line, partition, slice, time, flags, and recovery duration (if available)
    from the given twix data structure.
    Parameters:
    - twix: The twix data structure containing the raw data and PMU information.
    - trigger_method: The method used to trigger the acquisition (default is 'ECG1').
    Returns:
    - A pandas DataFrame with columns: 'Lin', 'Par', 'Sli', 'Time', 'Flags', and optionally 'RD' (Recovery Duration).
    """
    # if PMU data is available and the specified trigger method has triggers, use the first trigger timestamp as the start time
    if 'pmu' in twix and any(twix['pmu'].trigger[trigger_method]):
        start_time = twix['pmu'].timestamp_trigger[trigger_method][0]
    else:
        start_time = twix['mdb'][0].mdh.TimeStamp
    mdbs = [mdb for mdb in twix['mdb'] if mdb.is_image_scan()]
    timestamps = np.array([mdb.mdh.TimeStamp for mdb in mdbs])
    timestamps = (timestamps - start_time) * 2.5e-3  # convert to seconds
        
    df = pd.DataFrame({
        'Time': timestamps,
        'Lin': [mdb.cLin for mdb in mdbs],
        'Par': [mdb.cPar for mdb in mdbs],
        'Sli': [mdb.cSlc for mdb in mdbs],
        'Flags': [' '.join(f for f in mdb.get_active_flags()) for mdb in mdbs],
    })
    
    # Add recovery durations if available
    if 'pmu' in twix and any(twix['pmu'].trigger[trigger_method]):
        trigger_timing = get_trigger_timing(twix, trigger_method)
        idxs_sorted = np.searchsorted(trigger_timing, timestamps)
        RDs = np.diff(trigger_timing)[idxs_sorted-2] # last trigger - previous trigger
        df['RD'] =  np.round(RDs, 2)
    
    return df


def get_trigger_timing(twix, trigger_method='ECG1'):
    """
    Get trigger timing from the twix data.

    Parameters:
    - twix: The twix data structure.
    - trigger_method: The method used to trigger the acquisition.

    Returns:
    - Array of trigger timings.
    """
    assert 'pmu' in twix and any(twix['pmu'].trigger[trigger_method]), \
        f"No PMU data found for trigger method '{trigger_method}'."
    pmu = twix['pmu']
    start_time = pmu.timestamp_trigger[trigger_method][0]
    mask = pmu.trigger[trigger_method]>0
    trigger_timing = pmu.timestamp_trigger[trigger_method][mask]
    trigger_timing = (trigger_timing - start_time)  * 2.5e-3 # convert to seconds

    return trigger_timing