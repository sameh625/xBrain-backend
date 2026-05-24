"""Convert PROGRESS_REPORT.md to a styled HTML file suitable for printing to PDF."""
import re
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
SRC = HERE / "PROGRESS_REPORT.md"
DST = HERE / "PROGRESS_REPORT.html"

CSS = """
<style>
    @page { size: A4; margin: 18mm; }
    body {
        font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.55;
        color: #000;
        background: #fff;
        max-width: 800px;
        margin: 40px auto;
        padding: 0 20px;
    }
    h1 {
        font-size: 24pt;
        color: #000;
        border-bottom: 2px solid #000;
        padding-bottom: 6px;
        margin-top: 30px;
        margin-bottom: 14px;
        page-break-before: avoid;
        font-weight: 700;
    }
    h2 {
        font-size: 17pt;
        color: #000;
        border-bottom: 1px solid #000;
        padding-bottom: 4px;
        margin-top: 30px;
        margin-bottom: 12px;
        page-break-after: avoid;
        font-weight: 700;
    }
    h3 {
        font-size: 13pt;
        color: #000;
        margin-top: 20px;
        margin-bottom: 8px;
        page-break-after: avoid;
        font-weight: 700;
    }
    p, li { margin: 6px 0; }
    a { color: #000; text-decoration: underline; }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 14px 0;
        font-size: 10pt;
        page-break-inside: avoid;
        border: 1px solid #000;
    }
    th {
        background: #fff;
        color: #000;
        text-align: left;
        padding: 7px 10px;
        font-weight: 700;
        border: 1px solid #000;
    }
    td {
        padding: 7px 10px;
        border: 1px solid #000;
        vertical-align: top;
        color: #000;
    }
    code {
        background: #fff;
        padding: 1px 4px;
        border: 1px solid #ccc;
        border-radius: 2px;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 9.5pt;
        color: #000;
    }
    pre {
        background: #fff;
        color: #000;
        padding: 10px 12px;
        border: 1px solid #000;
        border-radius: 3px;
        overflow-x: auto;
        font-size: 9pt;
        line-height: 1.45;
        page-break-inside: avoid;
        margin: 10px 0;
    }
    pre code {
        background: transparent;
        color: #000;
        padding: 0;
        border: none;
        font-size: inherit;
    }
    blockquote {
        border-left: 3px solid #000;
        margin: 10px 0;
        padding: 4px 14px;
        color: #000;
        background: #fff;
        font-style: italic;
    }
    hr {
        border: none;
        border-top: 1px solid #000;
        margin: 22px 0;
    }
    strong { color: #000; font-weight: 700; }
    em { color: #000; }
    ul, ol { margin: 6px 0; padding-left: 24px; }
    /* Force black-and-white in print */
    @media print {
        * {
            color: #000 !important;
            background: #fff !important;
            box-shadow: none !important;
        }
        body { margin: 0; padding: 0; max-width: none; }
        h1, h2 { border-color: #000 !important; }
        table, th, td, pre, code {
            border-color: #000 !important;
        }
    }
</style>
"""


def convert():
    md_text = SRC.read_text(encoding="utf-8")

    # Plain code blocks (no syntax coloring) for clean black-and-white printing
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>xBrain Backend – Sprint Report</title>
{CSS}
</head>
<body>
{html_body}
</body>
</html>
"""
    DST.write_text(page, encoding="utf-8")
    print(f"Generated: {DST}")
    print()
    print("To save as PDF:")
    print("  1. Open the file in any browser (double-click or right-click → Open with).")
    print("  2. Press Ctrl+P (or File → Print).")
    print("  3. Choose 'Save as PDF' as the destination.")
    print("  4. Set margins to 'Default', enable 'Background graphics'.")
    print("  5. Save.")


if __name__ == "__main__":
    convert()
