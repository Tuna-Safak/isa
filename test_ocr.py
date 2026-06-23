import sys

import pytesseract
from PIL import Image, ImageOps, ImageEnhance


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_ocr.py <input.pdf or image>")
        sys.exit(1)

    input_path = sys.argv[1]

    image = Image.open(input_path)

    # falls Bild falsch herum ist, teste 90, 180 oder 270
    image = image.rotate(180, expand=True)

    # Graustufen
    image = ImageOps.grayscale(image)

    # Kontrast erhöhen
    image = ImageEnhance.Contrast(image).enhance(2)

    text = pytesseract.image_to_string(image, lang="deu")
    print(text)


if __name__ == "__main__":
    main()
