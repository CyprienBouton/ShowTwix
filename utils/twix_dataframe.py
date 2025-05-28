import numpy as np
import pandas as pd

import plotly.graph_objs as go

def build_line_dataframe(twix):
    mdbs = [mdb for mdb in twix[-1]['mdb'] if mdb.is_image_scan()]
    timestamps = np.array([mdb.mdh.TimeStamp for mdb in mdbs])
    timestamps = (timestamps - timestamps[0]) * 2.5e-3  # convert to seconds

    df = pd.DataFrame({
        'Time': timestamps,
        'Lin': [mdb.cLin for mdb in mdbs],
        'Par': [mdb.cPar for mdb in mdbs],
        'Sli': [mdb.cSlc for mdb in mdbs],
        'Flags': [' '.join(f for f in mdb.get_active_flags()) for mdb in mdbs],
    })
    return df