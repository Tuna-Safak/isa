# ocr.py
import os
import sys
import re
import argparse
from pathlib import Path

import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

# Optional: set this if Tesseract is not in PATH on Windows/macOS
# pytesseract.pytesseract.tesseract_cmd = r"/usr/local/bin/tesseract"

KEYWORDS = [
    "cholesterin", "glucose", "glukose", "hba1c", "hdl", "ldl",
    "triglyceride", "leukozyten", "erythrozyten", "hemoglobin",
    "hämatokrit", "vitamin", "mg/dl", "mmol/l", "g/dl", "referenz",
    "anforderung", "ergebnis", "einheit", "normbereich", "befund",
    "globulin", "albumin"
]

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".pdf"}


def score_text(text: str) -> int:
    text_l = text.lower()
    keyword_hits = sum(1 for k in KEYWORDS if k in text_l)
    digits = len(re.findall(r"\d", text))
    units = len(re.findall(r"(mg/dl|mmol/l|g/dl|pg/ml|ng/ml|%|u/l)", text_l))
    lines = len([ln for ln in text.splitlines() if ln.strip()])
    return keyword_hits * 30 + units * 10 + digits + lines


def score_candidate(text: str, confidences: list[float]) -> float:
    text_l = text.lower()
    keyword_hits = sum(1 for k in KEYWORDS if k in text_l)
    alpha_words = len(re.findall(r"\b[a-zäöüß]{3,}\b", text_l))
    digit_groups = len(re.findall(r"\d+", text_l))
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return avg_conf + keyword_hits * 25 + alpha_words * 0.25 + digit_groups * 0.1


def preprocess_variants(img: Image.Image):
    variants = []

    gray = ImageOps.grayscale(img)

    # Variant 1: simple grayscale
    variants.append(("gray", gray))

    # Variant 2: autocontrast
    auto = ImageOps.autocontrast(gray)
    variants.append(("autocontrast", auto))

    # Variant 3: sharpen + autocontrast
    sharp = ImageOps.autocontrast(gray.filter(ImageFilter.SHARPEN))
    variants.append(("sharp", sharp))

    # Variant 4: threshold
    bw = ImageOps.autocontrast(gray)
    bw = bw.point(lambda x: 255 if x > 160 else 0)
    variants.append(("threshold_160", bw))

    # Variant 5: stronger contrast + threshold
    contrast = ImageEnhance.Contrast(gray).enhance(2.0)
    contrast = ImageOps.autocontrast(contrast)
    bw2 = contrast.point(lambda x: 255 if x > 140 else 0)
    variants.append(("contrast_threshold_140", bw2))

    # Variant 6: median filter + threshold
    med = gray.filter(ImageFilter.MedianFilter(size=3))
    med = ImageOps.autocontrast(med)
    bw3 = med.point(lambda x: 255 if x > 150 else 0)
    variants.append(("median_threshold_150", bw3))

    return variants


def oriented_images(img: Image.Image):
    return [
        ("rot0", img),
        ("rot90_ccw", img.rotate(90, expand=True)),
        ("rot180", img.rotate(180, expand=True)),
        ("rot270_ccw", img.rotate(270, expand=True)),
    ]


def run_ocr_on_image(img: Image.Image, lang: str = "deu+eng"):
    configs = [
        ("psm6", f"--oem 3 --psm 6 -l {lang}"),
        ("psm11", f"--oem 3 --psm 11 -l {lang}"),
        ("psm4", f"--oem 3 --psm 4 -l {lang}"),
    ]

    best_text = ""
    best_score = float("-inf")
    best_meta = None

    for rotation_name, oriented_img in oriented_images(ImageOps.exif_transpose(img)):
        for variant_name, variant_img in preprocess_variants(oriented_img):
            for config_name, config in configs:
                data = pytesseract.image_to_data(
                    variant_img,
                    config=config,
                    output_type=Output.DICT,
                )
                confs = [
                    float(conf)
                    for conf in data["conf"]
                    if conf not in ("-1", "-1.0")
                ]
                text = " ".join(
                    word.strip()
                    for word in data["text"]
                    if word and word.strip()
                )
                s = score_candidate(text, confs)

                if s > best_score:
                    best_score = s
                    best_text = pytesseract.image_to_string(variant_img, config=config)
                    best_meta = (rotation_name, variant_name, config_name)

    return best_text, best_score, best_meta


def pdf_to_images(pdf_path: str, dpi: int = 400):
    return convert_from_path(pdf_path, dpi=dpi)


def image_file_to_image(image_path: str):
    with Image.open(image_path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def extract_text_from_pdf(pdf_path: str, lang: str = "deu+eng"):
    pages = pdf_to_images(pdf_path, dpi=400)
    all_text = []

    print(f"Detected {len(pages)} page(s).\n")

    for i, page in enumerate(pages, start=1):
        text, score, meta = run_ocr_on_image(page, lang=lang)
        all_text.append(f"\n===== PAGE {i} =====\n{text}")
        print(f"[Page {i}] Best rotation={meta[0]}, variant={meta[1]}, config={meta[2]}, score={score:.2f}")

    return "\n".join(all_text)


def extract_text_from_image(image_path: str, lang: str = "deu+eng"):
    img = image_file_to_image(image_path)
    text, score, meta = run_ocr_on_image(img, lang=lang)
    print(f"Best rotation={meta[0]}, variant={meta[1]}, config={meta[2]}, score={score:.2f}")
    return text


def save_output(text: str, input_path: str):
    output_file = Path(input_path).stem + "_ocr_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    return output_file


def is_supported_input_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def iter_supported_input_files(input_path: Path, recursive: bool = False):
    if input_path.is_file():
        if is_supported_input_file(input_path):
            yield input_path
        return

    iterator = input_path.rglob("*") if recursive else input_path.iterdir()
    for candidate in sorted(iterator):
        if is_supported_input_file(candidate):
            yield candidate


def extract_text_from_path(input_path: str, lang: str = "deu+eng"):
    path = Path(input_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(input_path, lang=lang)
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return extract_text_from_image(input_path, lang=lang)
    raise ValueError("Unsupported file type. Use PDF or image.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OCR a PDF or image file and save text output.")
    parser.add_argument("input_path", help="Path to the PDF/image file or a folder with files")
    parser.add_argument(
        "-o",
        "--output",
        help="Optional output text file path for single-file input, or output directory for folders",
    )
    parser.add_argument(
        "--lang",
        default="deu+eng",
        help="Tesseract language code, for example deu, eng, or deu+eng",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan subfolders when input_path is a directory",
    )
    return parser


def process_directory(input_dir: Path, output_dir: Path, lang: str, recursive: bool):
    files = list(iter_supported_input_files(input_dir, recursive=recursive))
    if not files:
        print(f"No supported PDF/image files found in: {input_dir}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    combined_parts = []

    for file_path in files:
        print(f"\n=== Processing {file_path} ===")
        text = extract_text_from_path(str(file_path), lang=lang)
        combined_parts.append(f"\n===== {file_path} =====\n{text}")
        file_output = output_dir / f"{file_path.stem}_ocr_output.txt"
        file_output.write_text(text, encoding="utf-8")
        print(f"Saved file OCR to: {file_output}")

    combined_output = output_dir / f"{input_dir.name}_ocr_combined.txt"
    combined_output.write_text("\n".join(combined_parts), encoding="utf-8")
    print(f"\nSaved combined OCR to: {combined_output}")
    return combined_output


def main():
    parser = build_parser()
    args = parser.parse_args()

    input_path = args.input_path

    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        sys.exit(1)

    input_file = Path(input_path)

    if input_file.is_dir():
        output_dir = Path(args.output) if args.output else input_file / "ocr_output"
        process_directory(input_file, output_dir, lang=args.lang, recursive=args.recursive)
        return

    try:
        text = extract_text_from_path(input_path, lang=args.lang)
    except ValueError:
        print("Unsupported file type. Use PDF or image.")
        sys.exit(1)

    if args.output:
        output_file = Path(args.output)
        output_file.write_text(text, encoding="utf-8")
    else:
        output_file = save_output(text, input_path)

    print("\n===== OCR OUTPUT PREVIEW =====\n")
    print(text[:5000])  # preview first 5000 chars
    print(f"\nFull OCR output saved to: {output_file}")

    # simple quality hint
    lower_text = text.lower()
    found = [k for k in KEYWORDS if k in lower_text]
    print("\nDetected keywords:", found if found else "None")

    if found:
        print("\nStep 1 looks promising: OCR found medically relevant terms.")
    else:
        print("\nStep 1 not good enough yet: still improve preprocessing or image quality.")


def process_image_file(input_path: str, lang: str = 'deu') -> str:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input image not found: {input_path}")
    return extract_text_from_image(input_path, lang=lang)


if __name__ == "__main__":
    main()
