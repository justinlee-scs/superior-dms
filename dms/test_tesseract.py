from PIL import Image
import pytesseract

img = Image.open("demotivate.png")  # scanned text image
text = pytesseract.image_to_string(img)

print(text)
