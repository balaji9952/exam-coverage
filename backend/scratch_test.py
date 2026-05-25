import re

def remove_marking_artifacts(text: str) -> str:
    if not text:
        return text
    
    # 1. Matches "13 CO1, K3" type combinations anywhere if preceded by space
    # Tolerate commas, periods, pipes after the number
    text = re.sub(
        r'(?<=\s)\b(?:[2-9]|1[0-9])\s*[,.:|\\-]*\s+(?:CO[1-6sS]?|C0[1-6sS]?|COS|COs|CO)\b(?:[\s,]*K[1-6])?\s*,?\s*',
        ' ',
        text,
        flags=re.IGNORECASE
    )
    # Also match if it's at the very end of the string
    text = re.sub(
        r'\b(?:[2-9]|1[0-9])\s*[,.:|\\-]*\s+(?:CO[1-6sS]?|C0[1-6sS]?|COS|COs|CO)\b(?:[\s,]*K[1-6])?\s*,?\s*$',
        ' ',
        text,
        flags=re.IGNORECASE
    )

    # 2. Aggressively remove stranded mark numbers in the MIDDLE of a sentence
    # e.g., "suitable 13, examples" or "that 13 improved"
    # We require a letter before and after to ensure we don't accidentally eat question numbers at the start
    text = re.sub(
        r'(?<=[a-zA-Z])\s*[,.:|\\-]*\s*\b(?:12|13|14|15|16|20)\b\s*[,.:|\\-]*\s+(?=[a-zA-Z])',
        ' ',
        text
    )

    # 3. Matches standalone CO indicators
    text = re.sub(
        r'(?<![-/a-zA-Z0-9])(?:CO[1-6]|C0[1-6]|COs|COS)\b\s*,?\s*(?:K[1-6])?\s*',
        ' ',
        text,
        flags=re.IGNORECASE
    )
    
    # 4. Matches standalone CO/co word
    text = re.sub(
        r'(?<![-/a-zA-Z0-9])CO\b(?!\s*[-/a-zA-Z0-9])\s*,?\s*',
        ' ',
        text,
        flags=re.IGNORECASE
    )
    
    # 5. Standalone marks numbers like 12, 13, 14, 15, 16, 20
    # ONLY remove if they are at the END of the string
    text = re.sub(
        r'\s+\b(?:12|13|14|15|16|20)\b\s*$',
        ' ',
        text
    )
    
    # 6. Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

tests = [
    "Explore the various types of digital marketing methods with suitable 13, CO1, K3 examples",
    "Explore the various types of digital marketing methods with suitable 13, examples",
    "Prepare a 13, CO1 digital marketing strategy",
    "Prepare a 13, digital marketing strategy",
    "analyze how SEO and SEM 13. complement each other",
    "websites that 13, improved rankings drastically",
    "websites that 13 improved rankings drastically",
    "13 Discuss the critical success factors of SEO",
    "13.(a) Explore the various types of digital marketing methods"
]

for t in tests:
    print(f"Original: {t}")
    print(f"Cleaned:  {remove_marking_artifacts(t)}")
    print("-" * 40)
