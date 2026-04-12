"""
Generate a PDF question bank from sample_question_bank.txt
Run: python generate_bank_pdf.py
Output: sample_question_bank.pdf
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from pathlib import Path
import re

INPUT_TXT = Path(__file__).parent / "sample_question_bank.txt"
OUTPUT_PDF = Path(__file__).parent / "sample_question_bank.pdf"

# Patterns
UNIT_HEADER  = re.compile(r'^UNIT\s+\d+', re.IGNORECASE)
PART_HEADER  = re.compile(r'^PART\s*[-–]\s*[AB]', re.IGNORECASE)
DIVIDER      = re.compile(r'^[=\-]{10,}')
QUESTION_NO  = re.compile(r'^(\d{1,3})\.\s+(.+)')
MARKS_TAG    = re.compile(r'\[(\d+)\]\s*(K\d)')
END_LINE     = re.compile(r'^END OF', re.IGNORECASE)


def build_bank_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF), pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=2*cm, rightMargin=2*cm
    )

    # Styles
    title_style = ParagraphStyle("Title", fontSize=12, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=3)
    sub_title   = ParagraphStyle("Sub",   fontSize=9,  fontName="Helvetica",     alignment=TA_CENTER, spaceAfter=4)
    unit_style  = ParagraphStyle("Unit",  fontSize=10, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=3, spaceBefore=8,
                                 textColor=colors.HexColor("#1a1a5e"))
    part_style  = ParagraphStyle("Part",  fontSize=9,  fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=3, spaceBefore=4)
    q_style     = ParagraphStyle("Q",     fontSize=9,  fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=3, leading=13)
    tag_style   = ParagraphStyle("Tag",   fontSize=8,  fontName="Helvetica", alignment=TA_CENTER)

    elements = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.black))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("SRI VENKATESWARA COLLEGE OF ENGINEERING", title_style))
    elements.append(Paragraph("QUESTION BANK — DATA STRUCTURES AND ALGORITHMS", title_style))
    elements.append(Paragraph("Subject Code: CS3301  |  Semester: III  |  Regulation: R2021", sub_title))
    elements.append(Spacer(1, 0.1*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.black))
    elements.append(Spacer(1, 0.3*cm))

    lines = INPUT_TXT.read_text(encoding="utf-8").splitlines()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            elements.append(Spacer(1, 0.1*cm))
            continue
        if DIVIDER.match(line):
            elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.grey))
            elements.append(Spacer(1, 0.1*cm))
            continue
        if END_LINE.match(line):
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black))
            elements.append(Spacer(1, 0.15*cm))
            elements.append(Paragraph("*** END OF QUESTION BANK ***", sub_title))
            continue
        if UNIT_HEADER.match(line):
            elements.append(Paragraph(line, unit_style))
            continue
        if PART_HEADER.match(line):
            elements.append(Paragraph(line, part_style))
            continue
        if line.startswith("Subject Code:") or line.startswith("QUESTION BANK"):
            continue  # already in header

        q_match = QUESTION_NO.match(line)
        if q_match:
            qno  = q_match.group(1) + "."
            rest = q_match.group(2)
            m = MARKS_TAG.search(rest)
            marks_str = ""
            bloom_str = ""
            if m:
                marks_str = f"[{m.group(1)}]"
                bloom_str = m.group(2)
                rest = rest[:m.start()].strip()

            row = [[
                Paragraph(qno, tag_style),
                Paragraph(rest, q_style),
                Paragraph(marks_str, tag_style),
                Paragraph(bloom_str, tag_style),
            ]]
            t = Table(row, colWidths=["6%", "77%", "8%", "9%"])
            t.setStyle(TableStyle([
                ("VALIGN",        (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING",   (0,0), (-1,-1), 0),
                ("RIGHTPADDING",  (0,0), (-1,-1), 2),
                ("BOTTOMPADDING", (0,0), (-1,-1), 2),
                ("TOPPADDING",    (0,0), (-1,-1), 1),
            ]))
            elements.append(t)
        else:
            # Sub-topic titles or section info
            elements.append(Paragraph(line, part_style))

    doc.build(elements)
    print(f"✅ Question bank PDF: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_bank_pdf()
