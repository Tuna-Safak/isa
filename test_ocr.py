import pytesseract
from PIL import Image, ImageOps, ImageEnhance

image = Image.open("/Users/tunasafak/Desktop/bloodtest.jpg")

# falls Bild falsch herum ist, teste 90, 180 oder 270
image = image.rotate(180, expand=True)

# Graustufen
image = ImageOps.grayscale(image)

# Kontrast erhöhen
image = ImageEnhance.Contrast(image).enhance(2)

text = pytesseract.image_to_string(image, lang="deu")

print(text) 