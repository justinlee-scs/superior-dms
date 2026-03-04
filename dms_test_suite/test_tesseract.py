from PIL import Image
import pytesseract
from pathlib import Path

img_path = Path(__file__).resolve().parent.parent / "dms" / "demotivate.png"
img = Image.open(img_path)  # scanned text image
text = pytesseract.image_to_string(img)

print(text)
