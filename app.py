import streamlit as st
from streamlit_pages import kspace_timing_map, select_raw_data, pmu, raw_data, kspace_recovery_durations

if __name__=="__main__":
    page_names_to_funcs = {
    "Choose raw data": select_raw_data.select_raw_data,
    "Acquisition Timeline": kspace_timing_map.kspace_timing_map,
    "Physiological Data": pmu.pmu,
    "Raw Data Metadata": raw_data.raw_data,
    "Recovery Durations": kspace_recovery_durations.kspace_recovery_durations,
    }
    selected_page = st.sidebar.selectbox("Go to page", page_names_to_funcs.keys())
    page_names_to_funcs[selected_page]()