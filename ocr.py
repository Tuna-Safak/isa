"""
filename: ocr.py
purpose: Load a blood test image, preprocess it, auto-detect rotation,
         run Tesseract OCR with German language support, print and save text.
author: Tuna Safak
date: 2026-06-14
approach: We use Pillow for image preprocessing (grayscale, contrast,
          sharpening) because it provides lightweight, dependency-free
          operations that are fast for single-image pipelines. Rotation is
          detected via Tesseract OSD to handle scanned/photographed images
          robustly, and `pytesseract` is used with German (`deu`) language
          pack for reliable OCR on German-language blood test reports.

This script contains detailed comments and status prints so the processing
steps are clear during execution. It also creates an `output/` folder
automatically and uses try/except for helpful error messages.
"""

import os
import sys
import re
from datetime import datetime

try:
    # Import third-party libraries; wrap in try/except to provide
    # a clear message if dependencies are missing.
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
except Exception as e:
    print("ERROR: Pillow (PIL) is required. Install with 'pip install Pillow'.")
    raise

try:
    import pytesseract
    from pytesseract import image_to_osd
except Exception as e:
    print("ERROR: pytesseract is required. Install with 'pip install pytesseract'.")
    raise


def ensure_output_dir(output_dir):
    """Create the output directory if it does not exist.

    We create the folder relative to this script's directory so the output
    is stored inside the project workspace (safe and portable).
    """
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"ERROR: Failed to create output directory: {e}")
            raise


def preprocess_image(img):
    """Apply a sequence of preprocessing steps and return the processed image.

    Steps and rationale:
    - Convert to grayscale: reduces color noise and focuses OCR on luminance.
    - Increase contrast: helps separate text from background.
    - Sharpen: accentuates text edges for better OCR clarity.
    - Optional small blur/denoise could be added depending on input quality.
    """
    print("Preprocessing: converting to grayscale...")
    gray = ImageOps.grayscale(img)  # keep as PIL Image

    print("Preprocessing: enhancing contrast...")
    # Contrast factor >1 increases contrast; 1.5 is a gentle boost.
    contrast_enhancer = ImageEnhance.Contrast(gray)
    contrasted = contrast_enhancer.enhance(1.5)

    print("Preprocessing: sharpening image...")
    # Use an unsharp mask for a stronger, more natural sharpening effect.
    sharpened = contrasted.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    return sharpened


def detect_rotation_angle(img):
    """Detect rotation using Tesseract OSD and return the rotation angle in degrees.

    We call `image_to_osd` which returns a string containing a 'Rotate:' line
    with the detected clockwise rotation (0,90,180,270). We parse and return
    that angle. If detection fails, return 0 as a safe fallback.
    """
    try:
        print("Detecting image orientation using Tesseract OSD...")
        osd = image_to_osd(img)
        # Example OSD output contains a line like: "Rotate: 90\n"
        m = re.search(r"Rotate:\s*(\d+)", osd)
        if m:
            angle = int(m.group(1))
            print(f"OSD reports rotation: {angle} degrees")
            return angle
        else:
            print("OSD did not report rotation; assuming 0 degrees")
            return 0
    except pytesseract.TesseractError as e:
        print(f"Warning: Tesseract OSD failed: {e}; assuming 0 degrees")
        return 0
    except Exception as e:
        print(f"Warning: orientation detection failed: {e}; assuming 0 degrees")
        return 0


def rotate_image(img, angle):
    """Rotate the image to correct orientation.

    Tesseract OSD returns the clockwise rotation needed to make text upright.
    PIL's `rotate` rotates counter-clockwise, so we negate the angle.
    We use `expand=True` to avoid cropping corners after rotation.
    """
    if not angle or angle == 0:
        print("No rotation needed.")
        return img
    # Rotate by negative angle to correct the image
    corrected = img.rotate(-angle, expand=True)
    print(f"Rotated image by {-angle} degrees to correct orientation.")
    return corrected


def run_ocr(img, lang='deu'):
    """Run Tesseract OCR on the provided PIL Image and return extracted text.

    We pass `lang='deu'` to use German language models (must be installed
    in the system Tesseract installation). If language data is missing,
    Tesseract will raise an error.
    """
    print(f"Running Tesseract OCR with language='{lang}'...")
    try:
        text = pytesseract.image_to_string(img, lang=lang)
        return text
    except pytesseract.TesseractError as e:
        print(f"ERROR: Tesseract failed: {e}")
        raise


def save_text(text, output_path):
    """Save the extracted text to a file, writing a header with timestamp.

    We open the file using UTF-8 to correctly store German umlauts.
    """
    try:
        print(f"Saving OCR output to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            header = f"OCR output saved: {datetime.utcnow().isoformat()} UTC\n\n"
            f.write(header)
            f.write(text)
    except Exception as e:
        print(f"ERROR: Failed to save OCR output: {e}")
        raise


def main():
    # Absolute path to the input image (as requested)
    input_path = '/Users/tunasafak/Desktop/bloodtest.jpg'

    # Choose output directory relative to this script file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    output_file = os.path.join(output_dir, 'ocr_output.txt')

    print("OCR pipeline started.")

    # Ensure output directory exists
    ensure_output_dir(output_dir)

    # Load the image file
    try:
        print(f"Loading image from: {input_path}")
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input image not found: {input_path}")
        img = Image.open(input_path)
    except Exception as e:
        print(f"ERROR: Could not open input image: {e}")
        sys.exit(1)

    # Preprocess the image for better OCR
    try:
        processed = preprocess_image(img)
    except Exception as e:
        print(f"ERROR during preprocessing: {e}")
        sys.exit(1)

    # Detect and fix rotation
    try:
        angle = detect_rotation_angle(processed)
        corrected = rotate_image(processed, angle)
    except Exception as e:
        print(f"ERROR during rotation correction: {e}")
        corrected = processed  # fallback to processed image

    # Run OCR using German language models
    try:
        extracted_text = run_ocr(corrected, lang='deu')
    except Exception as e:
        print("ERROR: OCR step failed. Ensure Tesseract is installed and 'deu' language data is present.")
        print("If Tesseract is not in PATH, set pytesseract.pytesseract.tesseract_cmd to the full executable path.")
        sys.exit(1)

    # Print extracted text so user can see it immediately
    print("--- OCR EXTRACTED TEXT START ---")
    print(extracted_text)
    print("--- OCR EXTRACTED TEXT END ---")

    # Save to output file
    try:
        save_text(extracted_text, output_file)
    except Exception:
        sys.exit(1)

    print("OCR pipeline finished successfully.")


if __name__ == '__main__':
    main()
