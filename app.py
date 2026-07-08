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
DOCX_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "bloodtest_report.docx")
REPORT_PYTHON = sys.executable

if "uploaded_path" not in st.session_state:
    st.session_state.uploaded_path = None

if "generated_for_path" not in st.session_state:
    st.session_state.generated_for_path = None

if "generated_pptx_path" not in st.session_state:
    st.session_state.generated_pptx_path = None

if "generated_docx_path" not in st.session_state:
    st.session_state.generated_docx_path = None

uploaded_file = st.file_uploader(
    "Upload blood test image",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    st.success(f"File uploaded: {uploaded_file.name}")

    saved_file_path = os.path.join(OUTPUT_DIR, uploaded_file.name)
    st.session_state.uploaded_path = saved_file_path

    if st.session_state.get("generated_for_path") != saved_file_path:
        st.session_state.generated_for_path = None
        st.session_state.generated_pptx_path = None
        st.session_state.generated_docx_path = None

    with open(saved_file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    st.write("File saved successfully.")

    if st.button("Generate PowerPoint"):
        try:
            with st.spinner("Running OCR and generating report..."):
                extracted_text = process_image_file(saved_file_path)
                with open(OCR_OUTPUT_PATH, "w", encoding="utf-8") as handle:
                    handle.write(extracted_text)

                subprocess.run(
                    [REPORT_PYTHON, "extractor.py", OCR_OUTPUT_PATH],
                    cwd=BASE_DIR,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                subprocess.run(
                    [REPORT_PYTHON, "generate_presentation.py"],
                    cwd=BASE_DIR,
                    check=True,
                    capture_output=True,
                    text=True,
                )

            st.success(f"PowerPoint generated: {PPTX_OUTPUT_PATH}")
            st.session_state.generated_for_path = saved_file_path
            st.session_state.generated_pptx_path = PPTX_OUTPUT_PATH
            st.session_state.generated_docx_path = DOCX_OUTPUT_PATH
        except subprocess.CalledProcessError as e:
            details = e.stderr.strip() if e.stderr else str(e)
            st.error(f"Report generation failed: {details}")
        except Exception as e:
            st.error(f"Unexpected error while generating the PowerPoint: {e}")

    if st.session_state.get("generated_for_path") == saved_file_path:
        pptx_path = Path(st.session_state.generated_pptx_path or PPTX_OUTPUT_PATH)
        docx_path = Path(st.session_state.generated_docx_path or DOCX_OUTPUT_PATH)

        if pptx_path.exists():
            with pptx_path.open("rb") as file_handle:
                st.download_button(
                    "Download PowerPoint",
                    data=file_handle,
                    file_name="bloodtest_report.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )

        if docx_path.exists():
            with docx_path.open("rb") as file_handle:
                st.download_button(
                    "Download Word report",
                    data=file_handle,
                    file_name="bloodtest_report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
