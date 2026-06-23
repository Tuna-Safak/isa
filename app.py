
import os
try:
    # If pytesseract is available, point it to Homebrew-installed tesseract.
    # We do this before importing `ocr` so `pytesseract` inside `ocr.py`
    # uses the correct executable path. If `pytesseract` isn't installed
    # yet this will be a no-op.
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
except Exception:
    pass

import streamlit as st
from ocr import process_image_file

st.set_page_config(page_title="Blood Test OCR", layout="wide")

st.title("Blood Test OCR Demo")
st.write("Upload a blood test image to extract the text with OCR.")

# Ensure output folder exists
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

uploaded_file = st.file_uploader(
    "Upload blood test image",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    st.success(f"File uploaded: {uploaded_file.name}")

    saved_file_path = os.path.join(OUTPUT_DIR, uploaded_file.name)

    with open(saved_file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    st.write("File saved successfully.")
    
    if st.button("Run OCR"):
        try:
            with st.spinner("Running OCR..."):
                extracted_text = process_image_file(saved_file_path)

            st.subheader("OCR Output")
            st.text_area("Extracted text", extracted_text, height=400)

        except Exception as e:
            st.error(f"An error occurred during OCR: {e}")