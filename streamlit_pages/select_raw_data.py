import streamlit as st
import os
from recotwix import recotwix
import tempfile
from utils.twix_dataframe import build_line_dataframe

def select_raw_data():
    st.title("Select Raw Data")
    
    if 'file' in st.session_state:
        st.write(f"Current raw data file: {st.session_state.file}")
    uploaded_file = st.file_uploader("Upload your .dat Twix file", type=["dat"])
    if uploaded_file is not None:
        with st.spinner("Reading Twix file..."):
            # 1. Save uploaded file to a persistent temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as tmp:
                tmp.write(uploaded_file.read())
                st.session_state.temp_file_path = tmp.name
            
            # 2. Load recotwix with the saved file
            try:
                reco = recotwix(filename=st.session_state.temp_file_path)
                st.session_state.recotwix = reco
                st.session_state.twix = reco.twixobj
                st.success("File loaded successfully!")
                st.session_state.df = build_line_dataframe(reco.twixobj, include_patrefscan=not reco.prot.isRefScanSeparate)
                st.session_state.file = os.path.basename(uploaded_file.name)
                st.session_state.img_nii = None
                st.session_state.image_buffer = None

            except Exception as e:
                st.error(f"Failed to read Twix file: {e}")

    elif 'file' not in st.session_state:
        st.info("Please upload a .dat Twix file to start.")

