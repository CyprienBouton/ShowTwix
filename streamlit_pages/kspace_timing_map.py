import streamlit as st
import time
import plotly.graph_objects as go
import numpy as np

def plot_fig(df, marker_size, is3D, show_flags):
    y = df.Par if is3D else df.Sli
    ylabel = 'Partition' if is3D else 'Slice'
    
    # Prepare hover data
    base_customdata = np.vstack([[ylabel] * len(df), df.Time]).T
    customdata = base_customdata if not show_flags \
        else np.hstack([base_customdata, df[['Flags']].values])
    hovertemplate = (
        f'Line: %{{x}}<br>{ylabel}: %{{y}}<br>Time: %{{customdata[1]:.2f}} s' +
        ('<br>Flags: %{customdata[2]}' if show_flags else '') +
        '<extra></extra>'
    )


    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.Lin,
        y=y,
        mode='markers',
        marker=dict(size=marker_size, color=df.Time, colorscale='jet',
                    colorbar=dict(title='Time (s)'),
                    cmin=df.Time.min(), cmax=df.Time.max()),
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

def kspace_timing_map():
    st.header("K-Space Timing Map")
    if 'df' not in st.session_state or 'twix' not in st.session_state:
        st.error("❗ Please upload a raw data file  first.")
        return

    df = st.session_state.df
    twix = st.session_state.twix
    is3D = twix[-1]['hdr']['Config']['Is3D'].lower() == 'true'

    marker_size = st.sidebar.slider("Marker Size", 2, 10, 6)
    show_flags = st.sidebar.checkbox("Show Flags", value=False)

    fig = plot_fig(df, marker_size, is3D, show_flags)
    st.plotly_chart(fig, use_container_width=True)
