import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px  # For color palette

def convert_timestamp_seconds(timestamp, starttime=None):
    if starttime is not None:
        timestamp = timestamp - starttime
    return timestamp * 2.5e-3  # convert to seconds

def plot_signals_streamlit(pmu, keys=None, show_trigger=True):
    fig = go.Figure()
    colors = {}
    trig_keys = []
    palette = px.colors.qualitative.Dark24
        
    # default keys
    if keys is None or len(keys) == 0:
        keys = [
            key for key in pmu.signal 
            if not key.startswith('LEARN_') 
            and np.ptp(pmu.signal[key])>0
        ]
    
    # Assign colors to keys
    for i, key in enumerate(keys):
        colors[key] = palette[i]
        
    for key in keys:
        y_normalized = (pmu.signal[key] - pmu.signal[key].min())/(pmu.signal[key].max() - pmu.signal[key].min()+1e-8)
        fig.add_trace(go.Scatter(
            x=convert_timestamp_seconds(pmu.timestamp[key], starttime=pmu.timestamp[key][0]),
            y=y_normalized,
            mode='lines',
            name=key,
            line=dict(color=colors[key])
        ))
        if show_trigger and np.any(pmu.trigger[key]):
            trig_keys.append(key)

    fig.update_layout(
        xaxis=dict(
            title='Time (seconds)',
        ),
        yaxis=dict(title='Normalized signal'),
        legend=dict(title='Signals'),
        height=600 if show_trigger and trig_keys else 500,
        margin=dict(t=40, b=40),
        template='simple_white'
    )

    # Optional: add trigger eventplot
    if show_trigger and trig_keys:
        for key in trig_keys:
            trigger_times = convert_timestamp_seconds(
                pmu.timestamp_trigger[key][pmu.trigger[key] > 0], starttime=pmu.timestamp[key][0]
            )
            bg_color = fig.layout.plot_bgcolor  # Get the background color of the plot
            # Choose the line color based on the background color (light or dark theme)
            line_color = 'black' if bg_color in ['white', 'lightgray', 'rgba(255, 255, 255, 0)'] else 'white'
            for t in trigger_times:
                fig.add_trace(go.Scatter(
                    x=[t, t],
                    y=[0, 1],
                    mode='lines',
                    line=dict(color=line_color, width=2),
                    showlegend=False,
                ))
        fig.update_yaxes(range=[-0.2, 1.1], title='Normalized signal (with triggers)')

    st.plotly_chart(fig, use_container_width=True)


def pmu():
    st.header("PMU Signal Visualization")
    if 'twix' not in st.session_state or 'df' not in st.session_state:
        st.error("❗ Please upload a raw data file  first.")
        return

    pmu_data = st.session_state.twix['pmu']
    # discard empty signals and learning signals
    default_keys = [
        key for key in pmu_data.signal 
        if not key.startswith('LEARN_') 
        and np.ptp(pmu_data.signal[key])>0
    ]
    keys = st.multiselect("Select Signals to Display", list(pmu_data.signal.keys()), default=default_keys)
    show_trigger = st.checkbox("Show Trigger Events", value=True)

    plot_signals_streamlit(pmu_data, keys, show_trigger)