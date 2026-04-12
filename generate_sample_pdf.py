"""
Generate a clean, properly formatted sample question paper PDF.
Run: python generate_sample_pdf.py
Output: sample_question_paper.pdf
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "sample_question_paper.pdf"


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    # ─── Styles ────────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    college_name = ParagraphStyle(
        "CollegeName",
        fontSize=13, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=2, leading=16
    )
    dept_name = ParagraphStyle(
        "DeptName",
        fontSize=10, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4
    )
    normal_center = ParagraphStyle(
        "NormalCenter",
        fontSize=9, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=2
    )
    section_header = ParagraphStyle(
        "SectionHeader",
        fontSize=10, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4, spaceBefore=6,
        textColor=colors.black
    )
    sub_header = ParagraphStyle(
        "SubHeader",
        fontSize=9, fontName="Helvetica-Oblique",
        alignment=TA_CENTER, spaceAfter=6
    )
    question_style = ParagraphStyle(
        "Question",
        fontSize=9.5, fontName="Helvetica",
        alignment=TA_JUSTIFY, spaceAfter=5, spaceBefore=3,
        leftIndent=0, leading=14
    )
    sub_question_style = ParagraphStyle(
        "SubQuestion",
        fontSize=9.5, fontName="Helvetica",
        alignment=TA_JUSTIFY, spaceAfter=4,
        leftIndent=20, leading=14
    )

    elements = []

    # ─── Header ────────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.black))
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(Paragraph("SRI VENKATESWARA COLLEGE OF ENGINEERING", college_name))
    elements.append(Paragraph("DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING", dept_name))
    elements.append(Spacer(1, 0.15 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    elements.append(Spacer(1, 0.2 * cm))

    # Info table
    info_data = [
        ["Subject: Data Structures and Algorithms", "Subject Code: CS3301"],
        ["Semester: III", "Regulation: R2021"],
        ["Exam Type: Internal Assessment - I", "Max. Marks: 100"],
        ["Duration: 3 Hours", "Date: 12-04-2026"],
    ]
    info_table = Table(info_data, colWidths=["55%", "45%"])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.black))
    elements.append(Spacer(1, 0.3 * cm))

    # ─── Part A ────────────────────────────────────────────────────────────────
    elements.append(Paragraph("PART – A (2 Marks)", section_header))
    elements.append(Paragraph("Answer ALL Questions &nbsp;&nbsp; (10 × 2 = 20 Marks)", sub_header))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.2 * cm))

    part_a = [
        ("1.", "Define data structure and classify its types.", "2", "K1"),
        ("2.", "State the difference between linear and non-linear data structures.", "2", "K1"),
        ("3.", "What is a stack? Mention its basic operations.", "2", "K1"),
        ("4.", "List the applications of queue in real-time systems.", "2", "K1"),
        ("5.", "Define a linked list. State its advantages over arrays.", "2", "K1"),
        ("6.", "Write the postfix notation for the expression (A+B)*(C-D).", "2", "K2"),
        ("7.", "State the properties of a binary tree.", "2", "K1"),
        ("8.", "Define graph and mention its types.", "2", "K1"),
        ("9.", "What is hashing? List any two collision resolution techniques.", "2", "K1"),
        ("10.", "Mention the difference between BFS and DFS traversal.", "2", "K2"),
    ]

    for qno, qtext, marks, bloom in part_a:
        row_data = [
            [Paragraph(qno, question_style),
             Paragraph(qtext, question_style),
             Paragraph(f"[{marks}]", normal_center),
             Paragraph(bloom, normal_center)]
        ]
        t = Table(row_data, colWidths=["6%", "78%", "8%", "8%"])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t)

    elements.append(Spacer(1, 0.3 * cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.black))
    elements.append(Spacer(1, 0.2 * cm))

    # ─── Part B ────────────────────────────────────────────────────────────────
    elements.append(Paragraph("PART – B (16 Marks)", section_header))
    elements.append(Paragraph("Answer any FIVE Questions &nbsp;&nbsp; (5 × 16 = 80 Marks)", sub_header))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.2 * cm))

    def add_question(qno, qtext, marks, bloom, sub_parts=None):
        row_data = [
            [Paragraph(qno, question_style),
             Paragraph(qtext, question_style),
             Paragraph(f"[{marks}]", normal_center),
             Paragraph(bloom, normal_center)]
        ]
        t = Table(row_data, colWidths=["6%", "78%", "8%", "8%"])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t)
        if sub_parts:
            for sp_label, sp_text, sp_marks, sp_bloom in sub_parts:
                sp_data = [
                    [Paragraph(sp_label, sub_question_style),
                     Paragraph(sp_text, sub_question_style),
                     Paragraph(f"[{sp_marks}]", normal_center),
                     Paragraph(sp_bloom, normal_center)]
                ]
                st = Table(sp_data, colWidths=["8%", "76%", "8%", "8%"])
                st.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                ]))
                elements.append(st)
        elements.append(Spacer(1, 0.2 * cm))

    add_question(
        "11.", "Explain the array representation of stack and queue with suitable examples. Discuss push, pop, enqueue, and dequeue operations with algorithms.", "16", "K2"
    )
    add_question(
        "12.", "Describe the singly linked list. Write algorithms for the following operations:", "16", "K2",
        sub_parts=[
            ("(a)", "Insertion at the beginning, middle, and end of a linked list.", "8", "K2"),
            ("(b)", "Deletion of a node from any given position.", "8", "K2"),
        ]
    )
    add_question(
        "13.", "Analyze the time and space complexity of the following sorting algorithms:", "16", "K4",
        sub_parts=[
            ("(a)", "Bubble Sort", "4", "K4"),
            ("(b)", "Selection Sort", "4", "K4"),
            ("(c)", "Insertion Sort", "4", "K4"),
            ("(d)", "Merge Sort", "4", "K4"),
        ]
    )
    add_question(
        "14.", "Explain binary search tree (BST). Construct a BST for the elements: 50, 30, 70, 20, 40, 60, 80. Perform in-order, pre-order, and post-order traversal on the constructed tree.", "16", "K2"
    )
    add_question(
        "15.", "Design a hash table of size 10 using chaining method for the keys: 25, 42, 96, 101, 102, 162, 197. Analyze performance and compare with open addressing.", "16", "K6"
    )
    add_question(
        "16.", "Compare BFS and DFS graph traversal. Apply both on graph V={A,B,C,D,E}, E={AB,AC,BD,BE,CD,CE,DE}. Draw the traversal order.", "16", "K4"
    )
    add_question(
        "17.", "Discuss AVL trees and their rotations with examples.", "16", "K2",
        sub_parts=[
            ("(a)", "Explain LL, RR, LR, and RL rotations with diagrams.", "8", "K2"),
            ("(b)", "Construct an AVL tree inserting: 10, 20, 30, 40, 50, 25.", "8", "K3"),
        ]
    )

    # ─── Footer ────────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.black))
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(Paragraph("*** END OF QUESTION PAPER ***", normal_center))

    doc.build(elements)
    print(f"✅ PDF generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    try:
        build_pdf()
    except ImportError:
        print("reportlab not installed. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "reportlab"], check=True)
        build_pdf()
