import asyncio
import io
import os
from PIL import Image
import pytesseract
from ocr_pipeline import _ocr_pil_image

async def run_ocr():
    img_path = r"C:\Users\mangudi\.gemini\antigravity-ide\brain\75a01a3c-85fc-487a-8655-7bd302cc07ac\media__1779600112621.png"
    img = Image.open(img_path)
    text = await _ocr_pil_image(img)
    print("----- OCR TEXT -----")
    print(text)
    print("--------------------")

if __name__ == "__main__":
    asyncio.run(run_ocr())
