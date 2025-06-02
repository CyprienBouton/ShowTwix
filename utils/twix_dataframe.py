import numpy as np
import pandas as pd

import plotly.graph_objs as go

def build_line_dataframe(twix, trigger_method='ECG1'):
    start_time = twix[-1]['mdb'][0].mdh.TimeStamp
    mdbs = [mdb for mdb in twix[-1]['mdb'] if mdb.is_image_scan()]
    timestamps = np.array([mdb.mdh.TimeStamp for mdb in mdbs])
    timestamps = (timestamps - start_time) * 2.5e-3  # convert to seconds
        
    df = pd.DataFrame({
        'Time': timestamps,
        'Lin': [mdb.cLin for mdb in mdbs],
        'Par': [mdb.cPar for mdb in mdbs],
        'Sli': [mdb.cSlc for mdb in mdbs],
        'Flags': [' '.join(f for f in mdb.get_active_flags()) for mdb in mdbs],
    })
    
    # Add RRs if available
    if 'pmu' in twix[-1] and any(twix[-1]['pmu'].trigger[trigger_method]):
        pmu = twix[-1]['pmu']
        mask = pmu.trigger[trigger_method]>0
        trigger_timing = pmu.timestamp_trigger[trigger_method][mask]
        trigger_timing = (trigger_timing - start_time)  * 2.5e-3 # convert to seconds
        idxs_sorted = np.searchsorted(trigger_timing, timestamps)
        RRs = np.diff(trigger_timing)[idxs_sorted-2] # last trigger - previous trigger
        df['RR'] =  np.round(RRs, 2)
    
    return df