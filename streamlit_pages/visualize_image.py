###############################
# IMPORTS
###############################


import streamlit as st
import os
import tempfile
import shutil
import dicom2nifti
from PIL import Image
from io import BytesIO
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
from recotwix import recotwix


###############################
# UTILITIES
###############################


def convert_dicoms_to_nifti_object(uploaded_files):
    """Convert DICOM files to an in-memory NIfTI object."""
    with tempfile.TemporaryDirectory() as dicom_dir, tempfile.TemporaryDirectory() as nifti_output_dir:
        # Save all uploaded files
        for file in uploaded_files:
            file_path = os.path.join(dicom_dir, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())

        # Convert to NIfTI
        dicom2nifti.convert_directory(dicom_dir, nifti_output_dir, compression=False, reorient=True)

        # Load the first NIfTI file
        nii_files = [f for f in os.listdir(nifti_output_dir) if f.endswith(".nii") or f.endswith(".nii.gz")]
        if not nii_files:
            raise RuntimeError("No NIfTI file generated")

        nii_path = os.path.join(nifti_output_dir, nii_files[0])
        img = nib.load(nii_path)

        # Force data into memory to avoid losing temp file reference
        data = img.get_fdata().copy()  # full image data
        affine = img.affine.copy()
        header = img.header.copy()

        # Recreate a completely in-memory Nifti1Image object
        return nib.Nifti1Image(data, affine, header)
    
    
def apply_window(img, window_level=None, window_width=None):
    """Apply window level and width normalization."""
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


def make_square(img):
    h, w = img.shape
    size = max(h, w)
    pad_h = (size - h) // 2
    pad_w = (size - w) // 2
    return np.pad(img, ((pad_h, size - h - pad_h), (pad_w, size - w - pad_w)))


###############################
# IMAGE INPUT
###############################


def obtain_image():
    import streamlit as st

    # Option list
    options = [
        "Select an option...",
        "Upload PNG file",
        "Upload DICOM directory",
        "SENSE reconstruction with POCS",
        "Direct reconstruction (handle GRAPPA)"
    ]

    # Step 1: Selectbox for choosing the method
    choice = st.selectbox("Choose an image source:", options)

    # Step 2: Logic to wait for meaningful user interaction
    if choice == "Select an option...":
        st.warning("Please choose a method to continue.")
        st.stop()

    # Step 3: If upload is selected, show uploader and wait for file
    elif choice == "Upload PNG file":
        uploaded_file = st.file_uploader("Upload your PNG file", type=["png", "jpeg"])
        if not uploaded_file:
            st.info("Waiting for PNG file upload...")
            st.stop()  # Wait until file is uploaded
        else:
            st.success("PNG uploaded successfully.")
            img = Image.open(uploaded_file).convert('L')  # Convert to grayscale

            # Convert to 3D if needed (e.g. single-slice volume)
            img_3d = np.expand_dims(img, axis=2)  # Shape becomes (H, W, 1)
            H, W = img_3d.shape[:2]
    
            # Create an affine (identity, or customize as needed)
            affine = np.array([
                [0, -1, 0, H - 1],  # x' = -j + H - 1
                [-1, 0, 0, W - 1],  # y' = -i + W - 1
                [0, 0, 1, 0],       # z stays the same
                [0, 0, 0, 1]
            ])

            # Create NIfTI image
            img_nii = nib.Nifti1Image(img_3d, affine)

    # Step 4: If upload is selected, show uploader and wait for folder
    elif choice == "Upload DICOM directory":
        uploaded_files = st.file_uploader(
            "Upload multiple DICOM (.dcm) files", type=["dcm"], accept_multiple_files=True
        )

        if not uploaded_files:
            st.info("Waiting for DICOM files upload...")
            st.stop()  # Wait until file is uploaded
        else:
            img_nii = convert_dicoms_to_nifti_object(uploaded_files)

    
    # Step 5: If SENSE reconstruction selected, process accordingly
    elif choice == "SENSE reconstruction with POCS":
        st.success(f"Selected reconstruction method: {choice}")
        # Call your reconstruction function here
        coil_sens_methods = [
            "Select an option...",
            "caldir",
            "espirit",
        ]
        method_sensitivity = st.selectbox("Choose coil sensitivity method:", coil_sens_methods)
        if method_sensitivity == "Select an option...":
            st.warning("Please choose a coil sensitivity method to continue.")
            st.stop()
        with st.spinner("Reconstructing image..."):
            with open("uploaded_file.dat", "wb") as f:
                f.write(st.session_state.buffer_file)
            reco = recotwix("uploaded_file.dat")
            reco.runReco(method_sensitivity=method_sensitivity)
            img_nii = reco.make_nifti(reco.img.abs())
            os.remove("uploaded_file.dat")
            
    # Step 6: Direct reconstruction
    else:
        st.success(f"Selected reconstruction method: {choice}")
        # Call your reconstruction function here
        with st.spinner("Reconstructing image..."):
            with open("uploaded_file.dat", "wb") as f:
                f.write(st.session_state.buffer_file)
            reco = recotwix("uploaded_file.dat")
            reco.runReco_GRAPPA()
            img_nii = reco.make_nifti(reco.img.abs())
            os.remove("uploaded_file.dat")
    return img_nii


###############################
# SLICE EXTRACTION AND VIEW
###############################


def display_slice(slice_2d):
    """Display image slice and allow window-level/width adjustment."""
    # Defaults values
    if "window_level" not in st.session_state:
        st.session_state.window_level = .3
    if "window_width" not in st.session_state:
        st.session_state.window_width = .7

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


def get_slice_from_nii(img_nii):
    """Extract 2D slice from 3D NIfTI."""
    data = img_nii.get_fdata()
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
    low = 0
    high = np.percentile(abs(slice_2d), 99)
    slice_2d = (slice_2d - low) / (high - low + 1e-8)
    slice_2d = make_square(slice_2d)
    return slice_2d


###############################
# MAIN FUNCTION
###############################
        

def visualize_image():
    st.header("🫀Visualize image")
    if 'twix' not in st.session_state or 'df' not in st.session_state:
        st.error("❗ Please upload a raw data file  first.")
        return
    
    if st.session_state.img_nii is None:
        # Get image either reconstruct raw data or ask png
        img_nii = obtain_image()
        # convert image to RAS coordinates
        st.session_state.img_nii = nib.as_closest_canonical(img_nii)
        st.success("Image reconstructed!")
    
    # If there is a nifti image show it            
    if st.session_state.img_nii is not None:
        slice_2d = get_slice_from_nii(st.session_state.img_nii)

        # Display with matplotlib
        fig = display_slice(slice_2d)
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0)
        buf.seek(0)  # Rewind buffer
        
        if st.button("Save image"):
            # Save to in-memory buffer
            st.session_state.image_buffer = buf
            st.success("Image saved to memory buffer.")
        
        # Download button
        st.download_button(
            label="📥 Export Image as PNG",
            data=buf.getvalue(),
            file_name="exported_image.png",
            mime="image/png",
        )
        
        if st.button("Reload image"):
            st.session_state.img_nii = None