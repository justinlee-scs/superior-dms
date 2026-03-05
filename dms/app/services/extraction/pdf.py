from io import BytesIO
from typing import List
from pdf2image import convert_from_bytes
from PIL import Image


def pdf_to_images(file_bytes: bytes) -> List[Image.Image]:
    """Convert a PDF into a flat list of PIL Images (one per page).

    Parameters:
        file_bytes (type=bytes): Raw file content used for validation or processing.
    """

    images = convert_from_bytes(file_bytes)

    # convert_from_bytes already returns List[Image.Image],
    # but this ensures correctness if wrapped elsewhere
    flat_images: List[Image.Image] = []

    for img in images:
        if isinstance(img, list):
            flat_images.extend(img)
        else:
            flat_images.append(img)

    return flat_images
