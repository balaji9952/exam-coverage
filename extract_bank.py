import asyncio
import sys
import json
import os
from pathlib import Path

# Add backend to path to import ocr_pipeline
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from ocr_pipeline import process_uploaded_file, extract_structured_bank_data

async def process_file(file_path: Path):
    print(f"Processing: {file_path.name}...")
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    
    # Use the full pipeline which now includes table-aware parsing for PDFs
    raw_text, questions = await process_uploaded_file(file_bytes, file_path.name)

    if not questions and not raw_text.strip():
        print(f"Warning: No data extracted from {file_path.name}")
        return

    print(f"Structuring data for {file_path.name}...")
    # Get metadata from raw text but use the high-quality questions from the pipeline
    structured_data = extract_structured_bank_data(raw_text)
    
    # If the pipeline found questions (especially via table extraction), use those
    if questions:
        # Organize questions into sections for the JSON format
        sections_map = {}
        for q in questions:
            sec = q.get("section_name", "GENERAL")
            if sec not in sections_map: sections_map[sec] = []
            sections_map[sec].append({
                "question_no": q["question_no"],
                "question_text": q["question_text"],
                "marks": q["marks"],
                "blooms_level": q["blooms_level"],
                "question_type": q["question_type"],
                "unit_no": q["unit_no"]
            })
        
        structured_data["sections"] = [
            {"section_name": k, "questions": v} for k, v in sorted(sections_map.items())
        ]
    
    output_file = file_path.with_suffix(".json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2)
    
    # NEW: Also save a pretty text version
    from ocr_pipeline import format_question_bank_to_text
    txt_output = file_path.with_suffix(".extracted.txt")
    with open(txt_output, "w", encoding="utf-8") as f:
        f.write(format_question_bank_to_text(structured_data))
    
    print(f"Extraction complete! Results saved to {output_file.name} and {txt_output.name}")

async def main_async():
    if len(sys.argv) < 2:
        print("Usage: python extract_bank.py <path_to_file_or_directory>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: Path {input_path} not found.")
        sys.exit(1)

    if input_path.is_file():
        await process_file(input_path)
    elif input_path.is_dir():
        print(f"Scanning directory: {input_path}")
        # Process all .pdf and .txt files in the folder
        files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.txt"))
        if not files:
            print("No PDF or TXT files found in directory.")
            return
        
        for f in files:
            try:
                await process_file(f)
            except Exception as e:
                print(f"Error processing {f.name}: {e}")
    
    print("\nBatch process finished.")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
