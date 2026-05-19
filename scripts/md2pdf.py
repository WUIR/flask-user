"""Convert .mdc rule files to PDF using reportlab."""
import os
import re
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Table, TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def strip_yaml_front_matter(text):
    """Remove YAML front matter (--- ... ---)."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text


def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "Heading1", parent=styles["Heading1"],
        fontSize=16, spaceAfter=6 * mm,
        textColor=HexColor("#1a1a2e"),
    ))
    styles.add(ParagraphStyle(
        "Heading2", parent=styles["Heading2"],
        fontSize=13, spaceAfter=4 * mm, spaceBefore=6 * mm,
        textColor=HexColor("#16213e"),
    ))
    styles.add(ParagraphStyle(
        "Heading3", parent=styles["Heading3"],
        fontSize=11, spaceAfter=3 * mm, spaceBefore=4 * mm,
        textColor=HexColor("#0f3460"),
    ))
    styles.add(ParagraphStyle(
        "Heading4", parent=styles["Heading4"],
        fontSize=10, spaceAfter=2 * mm, spaceBefore=3 * mm,
    ))
    styles.add(ParagraphStyle(
        "ListItem", parent=styles["Normal"],
        leftIndent=15, spaceBefore=1 * mm, spaceAfter=1 * mm,
        fontSize=9,
    ))
    styles.add(ParagraphStyle(
        "Code", parent=styles["Code"],
        fontSize=7.5, leftIndent=10, rightIndent=10,
        spaceBefore=2 * mm, spaceAfter=2 * mm,
        backColor=HexColor("#f5f5f5"),
        borderPadding=6,
    ))
    return styles


def md_to_story(text, styles):
    """Convert markdown text to Platypus story elements."""
    story = []
    in_code = False
    code_lines = []
    in_table = False
    table_rows = []

    for raw_line in text.split("\n"):
        line = raw_line.rstrip()

        # ── Code blocks ──────────────────────────────────
        if line.startswith("```"):
            if in_code:
                code_text = "\n".join(code_lines)
                story.append(Paragraph(
                    code_text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace("\n", "<br/>"),
                    styles["Code"],
                ))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        # ── Horizontal rule ──────────────────────────────
        if line.strip() == "---":
            story.append(HRFlowable(width="100%", color=HexColor("#cccccc"),
                                    thickness=0.5))
            story.append(Spacer(1, 2 * mm))
            continue

        # ── Skip empty lines ─────────────────────────────
        if not line.strip():
            story.append(Spacer(1, 1.5 * mm))
            continue

        # ── Inline formatting helper ─────────────────────
        def fmt(s):
            s = re.sub(r'`([^`]+)`', r'<b>\1</b>', s)
            s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
            s = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', s)
            return s

        # ── Headings ─────────────────────────────────────
        if line.startswith("##### "):
            story.append(Paragraph(fmt(line[6:].strip()), styles["Heading4"]))
        elif line.startswith("#### "):
            story.append(Paragraph(fmt(line[5:].strip()), styles["Heading4"]))
        elif line.startswith("### "):
            story.append(Paragraph(fmt(line[4:].strip()), styles["Heading3"]))
        elif line.startswith("## "):
            story.append(Paragraph(fmt(line[3:].strip()), styles["Heading2"]))
        elif line.startswith("# "):
            story.append(Paragraph(fmt(line[2:].strip()), styles["Heading1"]))
        # ── Table rows ───────────────────────────────────
        elif line.startswith("|"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if "---" in line:
                continue  # skip separator
            table_rows.append(cells)
        # ── List items ───────────────────────────────────
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            content = fmt(line.strip()[2:])
            # Handle bold prefix like **text**:
            content = content.replace("<b>", "").replace("</b>", "")
            story.append(Paragraph(f"• {content}", styles["ListItem"]))
        elif line.strip().startswith("1. ") or line.strip().startswith("2. "):
            content = fmt(line.strip()[3:])
            story.append(Paragraph(f"{line.strip()[:2]} {content}",
                                    styles["ListItem"]))
        # ── Regular paragraph ────────────────────────────
        else:
            story.append(Paragraph(fmt(line.strip()), styles["Normal"]))

    # ── Render collected table ────────────────────────────
    if table_rows:
        col_count = max(len(r) for r in table_rows)
        # Rebuild table with header detection
        data = table_rows
        t = Table(data, colWidths=[120 * mm / col_count] * col_count)
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e8e8e8")),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    return story


def convert_file(input_path, output_path, title):
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = strip_yaml_front_matter(content)

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=25 * mm, rightMargin=25 * mm,
        title=title,
    )
    styles = build_styles()
    story = md_to_story(content, styles)
    doc.build(story)
    print(f"  ✓ {os.path.basename(output_path)}")


def main():
    rules_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", ".codebuddy", "rules"
    )
    rules_dir = os.path.abspath(rules_dir)

    files = [
        ("flask-user-system.mdc", "Flask 用户系统 — 系统提示词"),
        ("design-intent.mdc", "Flask 用户系统 — 设计意图文档"),
    ]

    print("Converting .mdc → PDF ...")
    for fname, title in files:
        in_path = os.path.join(rules_dir, fname)
        out_path = os.path.join(rules_dir, fname.replace(".mdc", ".pdf"))
        if os.path.exists(in_path):
            convert_file(in_path, out_path, title)
        else:
            print(f"  ✗ {fname} not found")
    print(f"\nDone. PDFs saved to: {rules_dir}")


if __name__ == "__main__":
    main()
