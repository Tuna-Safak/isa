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
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
except Exception:
    print("ERROR: Pillow (PIL) is required. Install with 'pip install Pillow'.")
    raise

try:
    import pytesseract
    from pytesseract import image_to_osd
except Exception:
    print("ERROR: pytesseract is required. Install with 'pip install pytesseract'.")
    raise


def ensure_output_dir(output_dir):
    """Create the output directory if it does not exist."""
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"ERROR: Failed to create output directory: {e}")
            raise


def preprocess_image(img):
    """Apply a sequence of preprocessing steps and return the processed image."""
    print("Preprocessing: converting to grayscale...")
    gray = ImageOps.grayscale(img)

    print("Preprocessing: enhancing contrast...")
    contrast_enhancer = ImageEnhance.Contrast(gray)
    contrasted = contrast_enhancer.enhance(1.5)

    print("Preprocessing: sharpening image...")
    sharpened = contrasted.filter(
        ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3)
    )

    return sharpened


def detect_rotation_angle(img):
    """Detect rotation using Tesseract OSD and return the rotation angle in degrees."""
    try:
        print("Detecting image orientation using Tesseract OSD...")
        osd = image_to_osd(img)
        # image_to_osd may return bytes on some installations
        if isinstance(osd, bytes):
            try:
                osd = osd.decode('utf-8', errors='ignore')
            except Exception:
                osd = str(osd)

        # Try several common OSD output patterns
        for pattern in [r"Rotate:\s*(\d+)", r"Orientation in degrees:\s*(\d+)", r"orientation:\s*(\d+)"]:
            m = re.search(pattern, osd, flags=re.IGNORECASE)
            if m:
                angle = int(m.group(1))
                print(f"OSD reports rotation: {angle} degrees")
                return angle

        print("OSD did not report rotation; assuming 0 degrees")
        return 0
    except Exception as e:
        # pytesseract can raise a variety of exceptions (including TesseractNotFoundError)
        print(f"Warning: orientation detection failed: {e}; assuming 0 degrees")
        return 0


def rotate_image(img, angle):
    """Rotate the image to correct orientation."""
    if not angle or angle == 0:
        print("No rotation needed.")
        return img

    corrected = img.rotate(-angle, expand=True)
    print(f"Rotated image by {-angle} degrees to correct orientation.")
    return corrected


def run_ocr(img, lang='deu'):
    """Run Tesseract OCR on the provided PIL Image and return extracted text."""
    print(f"Running Tesseract OCR with language='{lang}'...")
    try:
        # Use a sensible default page segmentation mode; users can override by
        # changing this function if needed. Keep config simple and reliable.
        config = '--psm 6'
        text = pytesseract.image_to_string(img, lang=lang, config=config)
        return text
    except pytesseract.TesseractError as e:
        print(f"ERROR: Tesseract failed: {e}")
        raise


def save_text(text, output_path):
    """Save the extracted text to a file, writing a header with timestamp."""
    try:
        print(f"Saving OCR output to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            header = f"OCR output saved: {datetime.utcnow().isoformat()} UTC\n\n"
            f.write(header)
            f.write(text)
    except Exception as e:
        print(f"ERROR: Failed to save OCR output: {e}")
        raise


def process_image_file(input_path, lang='deu'):
    """
    Full OCR pipeline for one image file.

    Parameters:
        input_path (str): Path to the image file
        lang (str): Tesseract language, default 'deu'

    Returns:
        str: extracted OCR text
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    output_file = os.path.join(output_dir, 'ocr_output.txt')

    print("OCR pipeline started.")
    ensure_output_dir(output_dir)

    try:
        print(f"Loading image from: {input_path}")
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input image not found: {input_path}")
        img = Image.open(input_path)
    except Exception as e:
        print(f"ERROR: Could not open input image: {e}")
        raise

    try:
        processed = preprocess_image(img)
    except Exception as e:
        print(f"ERROR during preprocessing: {e}")
        raise

    try:
        angle = detect_rotation_angle(processed)
        corrected = rotate_image(processed, angle)
    except Exception as e:
        print(f"ERROR during rotation correction: {e}")
        corrected = processed

    try:
        extracted_text = run_ocr(corrected, lang=lang)
    except Exception:
        print("ERROR: OCR step failed. Ensure Tesseract is installed and 'deu' language data is present.")
        print("If Tesseract is not in PATH, set pytesseract.pytesseract.tesseract_cmd to the full executable path.")
        raise

    print("--- OCR EXTRACTED TEXT START ---")
    print(extracted_text)
    print("--- OCR EXTRACTED TEXT END ---")

    save_text(extracted_text, output_file)

    print("OCR pipeline finished successfully.")
    return extracted_text


def main():
    default_path = '/Users/tunasafak/Desktop/bloodtest.jpg'

    # Accept an optional command-line argument for the input image path.
    if len(sys.argv) > 1:
        if sys.argv[1] in ('-h', '--help'):
            print('Usage: python ocr.py [/path/to/image.jpg]')
            sys.exit(0)
        input_path = sys.argv[1]
    else:
        input_path = default_path

    if not os.path.exists(input_path):
        print(f"ERROR: Input image not found: {input_path}")
        print('Provide a valid image path as the first argument.')
        sys.exit(2)

    try:
        process_image_file(input_path)
    except Exception:
        sys.exit(1)


if __name__ == '__main__':
    main()