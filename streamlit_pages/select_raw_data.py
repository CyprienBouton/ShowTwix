import streamlit as st
import os
from twixtools import twixtools
from utils.twix_dataframe import build_line_dataframe

def select_raw_data():
    st.title("Select Raw Data")
    
    if 'file' in st.session_state:
        st.write(f"Current raw data file: {st.session_state.file}")
    uploaded_file = st.file_uploader("Upload your .dat Twix file", type=["dat"])
    if uploaded_file is not None:
        with st.spinner("Reading Twix file..."):
            st.session_state.buffer_file = uploaded_file.getbuffer()
            with open("uploaded_file.dat", "wb") as f:
                f.write(st.session_state.buffer_file)
            try:
                twix = twixtools.read_twix("uploaded_file.dat")
                st.session_state.twix = twix
                st.success("File loaded!")
                st.session_state.df = build_line_dataframe(twix)
                st.session_state.file = os.path.basename(uploaded_file.name)
                st.session_state.img_nii = None
                st.session_state.image_buffer = None
                os.remove("uploaded_file.dat")
            except Exception as e:
                st.error(f"Failed to read twix file: {e}")
    else:
        st.info("Please upload a .dat Twix file to start.")

