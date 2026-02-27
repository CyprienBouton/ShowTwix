################
# Import necessary libraries
################


import streamlit as st
import numpy as np
import plotly.graph_objs as go
import pandas as pd

from streamlit_pages import pmu
from utils.twix_dataframe import build_line_dataframe
from utils.optimized_pulse import series_Mz_1FA_SPPRESS, find_corrupted_shot, find_1_optimal_pulse


###############
# Useful functions
###############


def udpate_trigger_method():
    st.session_state.df = build_line_dataframe(
        st.session_state.twix, 
        trigger_method=st.session_state.trigger_method,
        include_patrefscan=not st.session_state.recotwix.prot.isRefScanSeparate,
    )

def convert_timestamp_seconds(timestamp, starttime=None):
    if starttime is not None:
        timestamp = timestamp - starttime
    return timestamp * 2.5e-3  # convert to seconds


def T1_species_list():
    # Input form for T1 species
    with st.form(key="T1_species_form"):
        species_input = st.text_input("Enter T1 species values (in seconds) (e.g., 1.2, 2.4, 3.0)", "")
        species_names_input = st.text_input("Enter species names (optional, comma separated)")

        # Submit button for adding species to the list
        submit_button = st.form_submit_button("Add T1s")
        
        if submit_button and species_input:
            try:
                # Parse the species values
                T1_values = [float(num.strip()) for num in species_input.split(',')]
                
                # Parse species names or assign default names
                if species_names_input:
                    species_names = [name.strip() for name in species_names_input.split(',')]
                else:
                    species_names = [f"Species {chr(65 + i)}" for i in range(len(T1_values))]  # Default names: Species A, Species B, etc.

                # Add species names and their T1 values into the dictionary
                for name, value in zip(species_names, T1_values):
                    st.session_state.T1_dict[name] = value
            
            except ValueError:
                st.warning("Please enter valid numbers for species values.")

        elif submit_button and not species_input:
            st.warning("Please enter valid species values.")

    # Display the species dictionary
    if st.session_state.T1_dict:
        species_df = pd.DataFrame(list(st.session_state.T1_dict.items()), columns=["Species Name", "T1 Value (seconds)"])
        st.dataframe(species_df)
        

###############
# Main functions for the page
###############


def longitudinal_magnetizations():
    st.header("Longitudinal Magnetizations")
    if 'df' not in st.session_state or 'twix' not in st.session_state:
        st.error("❗ Please upload a raw data file  first.")
        return
    
    twix = st.session_state.twix
    df = st.session_state.df
    
    if 'pmu' not in st.session_state.twix:
        st.error("❗ No PMU data found in the Twix file. \
            Please ensure the raw data contains physiological data.")
        return
    
    TI = twix['hdr']['Meas']['alTI'][0]*1e-6  # convert to seconds
    # Choose trigger method
    pmu_data = twix['pmu']
    default_keys = [
        key for key in pmu_data.signal 
        if not key.startswith('LEARN_') 
        and np.any(pmu_data.trigger[key])
    ]
    trigger_selected = st.selectbox(
        "Choose a trigger method:", 
        default_keys,
        key='trigger_method',
        on_change=udpate_trigger_method
    )
    udpate_trigger_method()  # Ensure the DataFrame is updated with the selected trigger method
        
    mask = twix['pmu'].trigger[trigger_selected]>0
    trigger_times = twix['pmu'].timestamp_trigger[trigger_selected][mask]
    trigger_times = (trigger_times - twix['pmu'].timestamp_trigger[trigger_selected][0])*2.5e-3 # convert to seconds
    readout_times = df.Time.values
    
    default_flip_angle = twix['hdr']['Meas']['adFlipAngleDegree'][0]
        
    # Asking the user for flip angle input
    flip_angle = st.number_input(
        "Enter flip angle in degrees",
        min_value=0.,  # Assuming flip angle is a positive value
        value=default_flip_angle,  # Default value is from the given dictionary
        step=1.  # Step size (you can adjust based on precision)
    )
    
    do_SPPRESS = st.checkbox("Include SPPRESS", value=True)
    reordering = st.selectbox("Choose reordering scheme:",['Centric', 'Linear'])
    correction_method = st.selectbox("Correction method", ['None', 'Custom pulse', "One optimized pulse", "Dummy scan"] )
    if "Custom pulse" in correction_method:
        all_t_a_opt = st.slider("t_a (seconds)", 0.0, TI, 0.1, step=0.001)
        all_alpha_b_opt = st.slider("alpha_b (degrees)", 0.0, 180.0, 90.0, step=1.0)
    elif "One optimized pulse" in correction_method:
        all_t_a_opt, all_alpha_b_opt = find_1_optimal_pulse(trigger_times, readout_times, TI)
    else:
        all_t_a_opt, all_alpha_b_opt = None, None

    # Initialize session state if not present
    if 'T1_dict' not in st.session_state:
        st.session_state.T1_dict = {}

    T1_species_list()
    
    # Button to trigger plotting
    if len(st.session_state.T1_dict) >= 1:
        if st.button("Plot Magnitude"):
            plot_magnetization(
                trigger_times, 
                readout_times, 
                st.session_state.T1_dict, 
                TI, 
                flip_angle,
                do_SPPRESS=do_SPPRESS,
                reordering=reordering,
                t_a=all_t_a_opt,
                alpha_b=all_alpha_b_opt,
            ) # convert T1s to seconds
    else:
        st.warning("Please add at least one species to plot.")


def plot_magnetization(
    trigger_times, 
    readout_times, 
    T1_dict, 
    TI, 
    FA, 
    do_SPPRESS=True, 
    reordering='Centric', 
    t_a=0, 
    alpha_b=0,
):
    """plot the magnetization from trigger and readout timings.

    Args:
        trigger_times (list, np.array): list of trigger times in seconds.
        readout_times (list, np.array): list of readout times in seconds.
        T1_dict (dict): dictionary of species names and their corresponding T1 relaxation times in seconds.
        TI (float): inversion time in seconds.
        FA (float): flip angle in degrees.
        do_SPPRESS (bool, optional): whether to do SPPRESS. Defaults to True.
        reordering (str, optional): reordering scheme. Defaults to 'Centric'.
        t_a (float, optional): delay of the optimized block pre readout in seconds. Defaults to 0.
        alpha_b (float, optional): alpha_b pulse angle in degrees. Defaults to 0.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=readout_times, y=[0]*len(readout_times), mode='markers', name='Readout Times'))
    if t_a is not None and alpha_b is not None:
        corrupted_shots = find_corrupted_shot(np.diff(trigger_times), tolerance=0.15, precision=5e-2)
        st.info(f"{np.sum(corrupted_shots)} corrupted shots out of {len(trigger_times)} ({np.sum(corrupted_shots)/len(trigger_times)*100:.2f}%)")
    else:
        corrupted_shots = []
    for name_T1, T1 in T1_dict.items():
        all_times, all_Mz, all_times_center, all_Mz_center = series_Mz_1FA_SPPRESS(
            TI, 
            T1, 
            FA, 
            readout_times, 
            trigger_times,
            corrupted_shots=np.where(corrupted_shots)[0], 
            t_a=t_a,
            alpha_b=alpha_b,
            do_SPPRESS=do_SPPRESS, 
            reordering=reordering,
        )
        fig.add_trace(go.Scatter(x=all_times, y=all_Mz, mode='lines', name=f'Magnetization {name_T1}, T1={T1} s'))
        fig.add_trace(go.Scatter(x=all_times_center, y=all_Mz_center, mode='markers', name=f'Center Shot {name_T1}, T1={T1} s'))
        
    fig.update_layout(
        xaxis=dict(title='Time (seconds)'),
        yaxis=dict(title='Recovery Duration (seconds)'),
        legend=dict(title='Legend'),
        height=600,
        margin=dict(t=40, b=40),
        template='simple_white'
    )
    st.plotly_chart(fig, use_container_width=True)
    

