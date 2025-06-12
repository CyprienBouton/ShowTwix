import streamlit as st
import os
from io import BytesIO
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
from recotwix import recotwix


def apply_window(img, window_level=None, window_width=None):
    # Set default values
    if window_level is None:
        upper = np.percentile(abs(img), 99)
        window_level = upper/2
    if window_width is None:
        upper = np.percentile(abs(img), 99)
        window_width = upper
    
    # Convert to float
    img = img.astype(np.float32)

    # Apply window level and width
    lower = window_level - (window_width / 2)
    upper = window_level + (window_width / 2)
    img = np.clip(img, lower, upper)

    # Normalize to 0–1 for display
    img = (img - lower) / (upper - lower + 1e-8)
    return img


def display_slice(slice_2d):
    # Defaults for WL and WW
    if "window_level" not in st.session_state:
        st.session_state.window_level = None
    if "window_width" not in st.session_state:
        st.session_state.window_width = None

    adjusted = apply_window(slice_2d, st.session_state.window_level, st.session_state.window_width)

    fig, ax = plt.subplots()
    ax.imshow(np.fliplr(np.rot90(adjusted)), cmap="gray")
    ax.axis("off")
    st.pyplot(fig)
        
    st.markdown("Window Level", unsafe_allow_html=True)
    st.session_state.window_level = st.slider(
        " ", min_value=0., max_value=1.,
        value=st.session_state.window_level, key="wl_slider", label_visibility="collapsed"
    )

    st.markdown("Window Width", unsafe_allow_html=True)
    st.session_state.window_width = st.slider(
        " ", min_value=0., max_value=1.,
        value=st.session_state.window_width, key="ww_slider", label_visibility="collapsed"
    )
    return fig




def make_square(img):
    h, w = img.shape
    size = max(h, w)
    pad_h = (size - h) // 2
    pad_w = (size - w) // 2
    return np.pad(img, ((pad_h, size - h - pad_h), (pad_w, size - w - pad_w)))


def visualize_image():
    st.header("🫀Visualize image")
    
    if st.session_state.img_nii is None:
        # reconstruct image
        with st.spinner("Reconstructing image..."):
            with open("uploaded_file.dat", "wb") as f:
                f.write(st.session_state.buffer_file)
            reco = recotwix("uploaded_file.dat")
            reco.runReco_GRAPPA()
            img_nii = reco.make_nifti(reco.img.abs())
            # convert image to RAS coordinates
            st.session_state.img_nii = nib.as_closest_canonical(img_nii)
            st.success("Image reconstructed!")
            os.remove("uploaded_file.dat")

    if st.session_state.img_nii is not None:
        # Load the NIfTI image
        data = st.session_state.img_nii.get_fdata()

        st.write(f"Shape: {data.shape}")
        
        # Handle 2D images
        if data.squeeze().ndim==2:
            slice_2d = data.squeeze()
            
        else:
            # Select axis and slice index
            axis = st.selectbox("View Axis", options=["Plane 1", "Plane 2", "Plane 3"])
            axis_map = {"Plane 1": 0, "Plane 2": 1, "Plane 3": 2}
            ax = axis_map[axis]

            max_index = data.shape[ax] - 1
            if max_index>0:
                slice_idx = st.slider(f"Slice along {axis}", 0, max_index, max_index // 2)
            else:
                slice_idx = 0
                
            # Extract the slice
            if ax == 0:
                slice_2d = data[slice_idx, :, :]
            elif ax == 1:
                slice_2d = data[:, slice_idx, :]
            else:
                slice_2d = data[:, :, slice_idx]

        # Normalize and rearrange image for display
        slice_2d = (slice_2d - np.min(slice_2d)) / (np.max(slice_2d) - np.min(slice_2d) + 1e-8)
        slice_2d = make_square(slice_2d)

        # Display with matplotlib
        fig = display_slice(slice_2d)
        
        if st.button("Save image"):
            # Save to in-memory buffer
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0)
            buf.seek(0)  # Rewind buffer
            
            st.session_state['image_buffer'] = buf
            st.success("Image saved to memory buffer.")
