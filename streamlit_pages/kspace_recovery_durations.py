import streamlit as st
import io
import plotly.graph_objects as go
import numpy as np
import pandas as pd

from utils.twix_dataframe import build_line_dataframe, get_trigger_timing

def udpate_trigger_method():
    st.session_state.df = build_line_dataframe(
        st.session_state.twix, 
        trigger_method=st.session_state.trigger_method
    )

def plot_fig(df, marker_size, is3D, show_flags, cmin, cmax):
    # Set colorbar scale
    if cmin is None:
        cmin = df.RD.min()
    if cmax is None:
        cmax = df.RD.max()
    
    y = df.Par if is3D else df.Sli
    ylabel = 'Partition' if is3D else 'Slice'
    
    # Prepare hover data
    base_customdata = np.vstack([[ylabel] * len(df), df.RD]).T
    customdata = base_customdata if not show_flags \
        else np.hstack([base_customdata, df[['Flags']].values])
    hovertemplate = (
        f'Line: %{{x}}<br>{ylabel}: %{{y}}<br>recovery duration: %{{customdata[1]:.2f}} s' +
        ('<br>Flags: %{customdata[2]}' if show_flags else '') +
        '<extra></extra>'
    )


    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.Lin,
        y=y,
        mode='markers',
        marker=dict(size=marker_size, color=df.RD, colorscale='jet',
                    colorbar=dict(title='recovery duration (s)'),
                    cmin=cmin, cmax=cmax),
        customdata=customdata,
        hovertemplate=hovertemplate,
        showlegend=False,
    ))
    fig.update_layout(
        xaxis=dict(title="Line"),
        yaxis=dict(title=ylabel),
        height=800, width=800,
        template='simple_white'
    )
    return fig

def kspace_recovery_durations():
    st.header("K-Space Timing Map")
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
            
    
    is3D = twix[-1]['hdr']['Config']['Is3D'].lower() == 'true'

    marker_size = st.sidebar.slider("Marker Size", 2, 10, 6)
    show_flags = st.sidebar.checkbox("Show Flags", value=False)

    scale_colorbar = st.sidebar.checkbox("Scale colorbar", value=True)

    if scale_colorbar:
        cmin = st.sidebar.slider("Colorbar Min (s)", 0.0, 5.0, 0.4, step=0.1)
        cmax = st.sidebar.slider("Colorbar Max (s)", 0.5, 10.0, 2.0, step=0.1)
    else:
        cmin, cmax = None, None


    fig = plot_fig(df, marker_size, is3D, show_flags, cmin, cmax)
    st.plotly_chart(fig, use_container_width=True)

    # Download RD button
    with io.StringIO() as buffer:
        list_RRs = np.diff(get_trigger_timing(twix, selected))  # Ensure trigger timing is calculated
        rr_series = pd.Series(list_RRs, name="RR_intervals")
        rr_series.to_csv(buffer, index=False, header=True)
        st.download_button(
            label="📥 Download Recovery Durations (RD)",
            data=buffer.getvalue(),
            file_name="recovery_durations.csv",
            mime="text/csv"
        )
