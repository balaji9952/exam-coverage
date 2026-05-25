import asyncio, sys
sys.path.insert(0, 'backend')
from ocr_pipeline import extract_text_from_pdf

async def debug():
    with open('sample_question_bank.pdf', 'rb') as f:
        data = f.read()
    text = await extract_text_from_pdf(data)
    print("--- RAW TEXT START ---")
    print(text[:2000])
    print("--- RAW TEXT END ---")

asyncio.run(debug())
