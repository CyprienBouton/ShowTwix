import streamlit as st
import json


def raw_data():
    st.header("Raw Data Metadata")
    if 'df' not in st.session_state or 'twix' not in st.session_state:
        st.error("❗ Please upload a raw data file  first.")
        return
    
    twix = st.session_state.twix
    st.text(json.dumps(twix[-1]['hdr'], indent=4))