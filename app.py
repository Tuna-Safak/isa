
import os
import subprocess
import sys
from pathlib import Path

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

st.set_page_config(page_title="BloodTest AI", layout="wide")

st.title("BloodTest AI")
st.write("Upload a blood test image, extract the text, and generate a PowerPoint report.")

# Ensure output folder exists
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OCR_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "ocr_output.txt")
CSV_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "bloodtest_results.csv")
PPTX_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "bloodtest_report.pptx")

if "uploaded_path" not in st.session_state:
    st.session_state.uploaded_path = None
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""
if "ocr_done" not in st.session_state:
    st.session_state.ocr_done = False
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False

uploaded_file = st.file_uploader(
    "Upload blood test image",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    st.success(f"File uploaded: {uploaded_file.name}")

    saved_file_path = os.path.join(OUTPUT_DIR, uploaded_file.name)
    st.session_state.uploaded_path = saved_file_path

    with open(saved_file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    st.write("File saved successfully.")

    if st.button("Run OCR"):
        try:
            with st.spinner("Running OCR..."):
                extracted_text = process_image_file(saved_file_path)
                st.session_state.extracted_text = extracted_text
                st.session_state.ocr_done = True
                with open(OCR_OUTPUT_PATH, "w", encoding="utf-8") as handle:
                    handle.write(extracted_text)

            st.subheader("OCR Output")
            st.text_area("Extracted text", extracted_text, height=400)

        except Exception as e:
            st.error(f"An error occurred during OCR: {e}")

    if st.session_state.ocr_done:
        st.success("OCR finished. You can now generate the PowerPoint report.")
        st.text_area("Extracted text", st.session_state.extracted_text, height=300)

        if st.button("Generate PowerPoint"):
            try:
                with st.spinner("Building CSV, JSON, and PowerPoint report..."):
                    subprocess.run(
                        [sys.executable, "extractor.py", OCR_OUTPUT_PATH],
                        cwd=BASE_DIR,
                        check=True,
                    )
                    subprocess.run(
                        [sys.executable, "generate_presentation.py"],
                        cwd=BASE_DIR,
                        check=True,
                    )
                    st.session_state.report_ready = True

                st.success(f"PowerPoint generated: {PPTX_OUTPUT_PATH}")
                pptx_path = Path(PPTX_OUTPUT_PATH)
                if pptx_path.exists():
                    with pptx_path.open("rb") as file_handle:
                        st.download_button(
                            "Download PowerPoint",
                            data=file_handle,
                            file_name="bloodtest_report.pptx",
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        )
            except subprocess.CalledProcessError as e:
                st.error(f"Report generation failed: {e}")
            except Exception as e:
                st.error(f"Unexpected error while generating the PowerPoint: {e}")
