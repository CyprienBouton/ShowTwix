import streamlit as st
import time
import plotly.graph_objects as go
import numpy as np

from utils.twix_dataframe import build_line_dataframe

def udpate_trigger_method():
    st.session_state.df = build_line_dataframe(
        st.session_state.twix, 
        trigger_method=st.session_state.trigger_method
    )

def plot_hist(df):
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=df.RD, nbinsx=50))
    fig.update_layout(
        xaxis=dict(title="Recovery duration (seconds)"),
        yaxis=dict(title="Number of occurrences"),
        height=800, width=800,
        template='simple_white'
    )
    return fig

def pmu_stats():
    st.header("Physiological Statistics")
    if 'df' not in st.session_state or 'twix' not in st.session_state:
        st.error("❗ Please upload a raw data file  first.")
        return
    
    twix = st.session_state.twix
    df = st.session_state.df
    
    if 'pmu' not in st.session_state.twix[-1]:
        st.error("❗ No PMU data found in the Twix file. \
            Please ensure the raw data contains physiological data.")
        return
    
    # Choose trigger method
    pmu_data = twix[-1]['pmu']
    default_keys = [
        key for key in pmu_data.signal 
        if not key.startswith('LEARN_') 
        and np.ptp(pmu_data.signal[key])>0
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

    fig = plot_hist(df)
    st.plotly_chart(fig, use_container_width=True)