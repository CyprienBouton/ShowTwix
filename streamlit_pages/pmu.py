import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px  # For color palette

def convert_timestamp_seconds(timestamp):
    return (timestamp - timestamp[0]) * 2.5e-3  # convert to seconds

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
        fig.add_trace(go.Scatter(
            x=convert_timestamp_seconds(pmu.timestamp[key]),
            y=pmu.signal[key],
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
                pmu.timestamp_trigger[key][pmu.trigger[key] > 0]
            )
            fig.add_trace(go.Scatter(
                x=trigger_times,
                y=[-0.1] * len(trigger_times),
                mode='markers',
                marker=dict(symbol='line-ns-open', size=12, color=colors[key]),
                name=f'{key} Trigger',
                showlegend=False,
            ))
        fig.update_yaxes(range=[-0.2, 1.1], title='signal (with triggers)')

    st.plotly_chart(fig, use_container_width=True)


def pmu():
    st.header("PMU Signal Visualization")
    if 'twix' not in st.session_state or 'df' not in st.session_state:
        st.error("❗ Please upload a raw data file  first.")
        return

    pmu_data = st.session_state.twix[-1]['pmu']
    # discard empty signals and learning signals
    default_keys = [
        key for key in pmu_data.signal 
        if not key.startswith('LEARN_') 
        and np.ptp(pmu_data.signal[key])>0
    ]
    keys = st.multiselect("Select Signals to Display", list(pmu_data.signal.keys()), default=default_keys)
    show_trigger = st.checkbox("Show Trigger Events", value=True)

    plot_signals_streamlit(pmu_data, keys, show_trigger)