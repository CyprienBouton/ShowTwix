import streamlit as st
import time
import plotly.graph_objects as go
import numpy as np

from utils.twix_dataframe import build_line_dataframe

def udpate_trigger_method():
    st.session_state.df = build_line_dataframe(
        st.session_state.twix, 
        trigger_method=st.session_state.trigger_method,
        include_patrefscan=not st.session_state.recotwix.prot.isRefScanSeparate,
    )

def plot_hist(df, rd_min=None, rd_max=None):
    fig = go.Figure()
    if rd_min is not None and rd_max is not None:
        x_range = rd_max - rd_min
    else:
        x_range = df.RD.max() - df.RD.min()

    nbinsx = int(max(round(50 * (df.RD.max() - df.RD.min())/ x_range), 2))
    
    # Adjusting the number of bins to control bar width
    fig.add_trace(go.Histogram(
        x=df.RD, 
        nbinsx=nbinsx  # Fewer bins = wider bars
    ))

    fig.update_layout(
        xaxis=dict(
            title="Recovery duration (seconds)",
            title_font=dict(size=35),  # Title font size
            tickfont=dict(size=30),    # Tick label font size
            range=[rd_min, rd_max] if rd_min is not None and rd_max is not None else None
        ),
        yaxis=dict(
            title="Number of occurrences",
            title_font=dict(size=35),  # Title font size
            tickfont=dict(size=30)     # Tick label font size
        ),
        height=800, width=800,
        template='simple_white',
        bargap=0.1,  # Slight gap between bars
    )
    
    return fig

def pmu_stats():
    st.header("Physiological Statistics")
    if 'df' not in st.session_state or 'twix' not in st.session_state:
        st.error("❗ Please upload a raw data file  first.")
        return
    
    twix = st.session_state.twix
    df = st.session_state.df
    
    if 'pmu' not in st.session_state.twix:
        st.error("❗ No PMU data found in the Twix file. \
            Please ensure the raw data contains physiological data.")
        return
    
    # Choose trigger method
    pmu_data = twix['pmu']
    default_keys = [
        key for key in pmu_data.signal 
        if not key.startswith('LEARN_') 
        and np.any(pmu_data.trigger[key])
    ]
    selected = st.selectbox(
        "Choose a trigger method:", 
        default_keys,
        key='trigger_method',
        on_change=udpate_trigger_method
    )
    
    if 'RD' not in df.columns:
        st.error(f"❗ Choose another trigger method. Selected: '{selected}'.")
        return

    # Sidebar controls for scaling
    scale_hist = st.sidebar.checkbox("Scale x-axis (RD)", value=True)

    if scale_hist or np.ptp(df.RD)==0: # if all RD values are the same, allow scaling to visualize the histogram
        rd_min = st.sidebar.slider("RD Min (s)", 0.0, 5.0, 0.5, step=0.1)
        rd_max = st.sidebar.slider("RD Max (s)", 0.5, 10.0, 1.5, step=0.1)
    else:
        rd_min, rd_max = None, None
        
    fig = plot_hist(df, rd_min, rd_max)
    st.plotly_chart(fig, use_container_width=True)