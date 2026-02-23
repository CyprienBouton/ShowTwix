import os
import time
import tempfile
import streamlit as st
from streamlit_pages import kspace_timing_map, select_raw_data, pmu, kspace_recovery_durations, pmu_stats, longitudinal_magnetizations
import PIL.Image as Image

def cleanup_old_temp_files(age=3600):
    now = time.time()
    for f in os.listdir(tempfile.gettempdir()):
        if f.endswith(".dat"):
            path = os.path.join(tempfile.gettempdir(), f)
            if now - os.path.getmtime(path) > age:
                try: os.remove(path)
                except: pass

if __name__=="__main__":
    cleanup_old_temp_files()
    page_names_to_funcs = {
    "Choose raw data": select_raw_data.select_raw_data,
    "Acquisition Timeline": kspace_timing_map.kspace_timing_map,
    "Physiological Data": pmu.pmu,
    "Physiological Statistics": pmu_stats.pmu_stats,
    "Recovery Durations": kspace_recovery_durations.kspace_recovery_durations,
    "Longitudinal Magnetizations": longitudinal_magnetizations.longitudinal_magnetizations,
    }
    selected_page = st.sidebar.selectbox("Go to page", page_names_to_funcs.keys())
    page_names_to_funcs[selected_page]()

    if 'image_buffer' in st.session_state and st.session_state.image_buffer is not None:
        # Load image from buffer and display
        img = Image.open(st.session_state['image_buffer'])
        with st.sidebar:
            st.image(img, caption="Saved Image")