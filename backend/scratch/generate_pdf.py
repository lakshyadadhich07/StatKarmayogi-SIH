import os
import re
import subprocess
from markdown_it import MarkdownIt
import pypdf

MD_FILE = "DATABASE_AND_BACKEND_MASTER_GUIDE.md"
HTML_FILE = "DATABASE_AND_BACKEND_MASTER_GUIDE.html"
PDF_FILE = "DATABASE_AND_BACKEND_MASTER_GUIDE.pdf"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

print(f"Reading markdown from {MD_FILE}...")
with open(MD_FILE, "r", encoding="utf-8") as f:
    raw_md = f.read()

# Preprocess markdown callouts line by line
def process_callouts(text):
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^>\s*\[!(NOTE|IMPORTANT|TIP|WARNING|CAUTION)\]", line)
        if m:
            kind = m.group(1).upper()
            content_lines = []
            i += 1
            while i < len(lines) and (lines[i].startswith(">") or (lines[i].strip() == "" and i+1 < len(lines) and lines[i+1].startswith(">"))):
                content_lines.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            content = " ".join([c.strip() for c in content_lines if c.strip()])
            badge_color = {
                "NOTE": "#2563eb",
                "IMPORTANT": "#dc2626",
                "TIP": "#059669",
                "WARNING": "#d97706",
                "CAUTION": "#b91c1c"
            }.get(kind, "#475569")
            bg_color = {
                "NOTE": "#eff6ff",
                "IMPORTANT": "#fef2f2",
                "TIP": "#f0fdf4",
                "WARNING": "#fffbeb",
                "CAUTION": "#fef2f2"
            }.get(kind, "#f8fafc")
            out.append(f'<div class="callout callout-{kind.lower()}" style="background-color: {bg_color}; border-left: 4px solid {badge_color}; padding: 12px 16px; margin: 16px 0; border-radius: 4px;"><div style="font-weight: 700; color: {badge_color}; margin-bottom: 4px; font-size: 9pt; text-transform: uppercase; letter-spacing: 0.5px;">[{kind}]</div><div style="font-size: 9.5pt; line-height: 1.5;">{content}</div></div>\n')
        else:
            out.append(line)
            i += 1
    return "\n".join(out)

# Preprocess LaTeX math blocks into readable formula boxes
def process_math(text):
    def replace_display_math(match):
        formula = match.group(1).strip()
        clean_formula = formula.replace('\\text{', '<span class="math-text">').replace('}', '</span>')
        clean_formula = clean_formula.replace('\\Delta', '&Delta;')
        clean_formula = clean_formula.replace('\\ge', '&ge;')
        clean_formula = clean_formula.replace('\\le', '&le;')
        clean_formula = clean_formula.replace('\\forall', '&forall;')
        clean_formula = clean_formula.replace('\\exists', '&exists;')
        clean_formula = clean_formula.replace('\\lor', '&or;')
        clean_formula = clean_formula.replace('\\times', '&times;')
        clean_formula = clean_formula.replace('\\round', 'round')
        clean_formula = clean_formula.replace('\\left(', '(').replace('\\right)', ')')
        clean_formula = clean_formula.replace('\\in', '&isin;')
        clean_formula = clean_formula.replace('\\case', 'case')
        clean_formula = clean_formula.replace('\\begin{cases}', '<div class="cases">').replace('\\end{cases}', '</div>')
        clean_formula = clean_formula.replace('\\\\', '<br>')
        clean_formula = clean_formula.replace('&', ' &nbsp; ')
        clean_formula = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1 / \2)', clean_formula)
        return f'<div class="math-display-box"><div class="math-content">{clean_formula}</div></div>\n'

    text = re.sub(r'\$\$(.*?)\$\$', replace_display_math, text, flags=re.DOTALL)
    
    def replace_inline_math(match):
        formula = match.group(1).strip()
        clean = formula.replace('\\Delta', '&Delta;').replace('\\ge', '&ge;').replace('\\le', '&le;').replace('\\times', '&times;').replace('\\ne', '&ne;')
        return f'<span class="math-inline">{clean}</span>'
    
    text = re.sub(r'(?<!\$)\$(?!\$)(.*?)\$', replace_inline_math, text)
    return text

processed_md = process_callouts(raw_md)
processed_md = process_math(processed_md)

print("Parsing Markdown to HTML via markdown_it...")
md = MarkdownIt('gfm-like', {'linkify': False, 'html': True})
body_html = md.render(processed_md)

css = """
@page {
    size: A4 portrait;
    margin: 18mm 16mm 18mm 16mm;
    @top-right {
        content: "StatKarmayogi Backend Master Guide";
        font-size: 7.5pt;
        color: #64748b;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    @bottom-center {
        content: "Page " counter(page);
        font-size: 8pt;
        color: #64748b;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.55;
    color: #1e293b;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
}

/* Cover Page */
.cover-page {
    page-break-after: always;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
    padding: 20px 10px 10px 10px;
}

.cover-header {
    border-bottom: 3px solid #0f2942;
    padding-bottom: 16px;
}

.gov-badge {
    display: inline-block;
    background-color: #0f2942;
    color: #ffffff;
    font-size: 8.5pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 6px 14px;
    border-radius: 3px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.cover-title-group h1 {
    font-size: 26pt;
    color: #0f2942;
    margin: 15px 0 10px 0;
    line-height: 1.15;
    font-weight: 800;
    letter-spacing: -0.5px;
    border: none;
    padding: 0;
}

.cover-title-group .subtitle {
    font-size: 13pt;
    color: #0369a1;
    font-weight: 600;
    margin: 0 0 10px 0;
    line-height: 1.3;
}

.cover-title-group .doc-desc {
    font-size: 10pt;
    color: #475569;
    font-style: italic;
    margin-top: 10px;
    border-left: 3px solid #0369a1;
    padding-left: 12px;
}

.cover-meta-grid {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 16px 22px;
    margin: 24px 0;
}

.meta-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #e2e8f0;
    font-size: 9pt;
}

.meta-row:last-child {
    border-bottom: none;
}

.meta-label {
    font-weight: 600;
    color: #475569;
}

.meta-value {
    font-weight: 700;
    color: #0f2942;
}

.cover-footer {
    border-top: 1px solid #cbd5e1;
    padding-top: 12px;
    font-size: 8pt;
    color: #64748b;
    display: flex;
    justify-content: space-between;
}

/* Headings */
h1 {
    font-size: 15pt;
    color: #0f2942;
    font-weight: 700;
    border-bottom: 2px solid #0284c7;
    padding-bottom: 5px;
    margin-top: 28px;
    margin-bottom: 12px;
    page-break-after: avoid;
}

/* Force major parts to start on a fresh page */
h2[id^="part-"] {
    page-break-before: always;
    font-size: 13pt;
    color: #0f2942;
    background-color: #f1f5f9;
    padding: 8px 12px;
    border-left: 5px solid #0284c7;
    margin-top: 20px;
    margin-bottom: 14px;
    page-break-after: avoid;
}

h2 {
    font-size: 12.5pt;
    color: #1e3a8a;
    font-weight: 700;
    margin-top: 22px;
    margin-bottom: 10px;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
    page-break-after: avoid;
}

h3 {
    font-size: 11pt;
    color: #0369a1;
    font-weight: 600;
    margin-top: 16px;
    margin-bottom: 8px;
    page-break-after: avoid;
}

h4 {
    font-size: 10pt;
    color: #334155;
    font-weight: 600;
    margin-top: 12px;
    margin-bottom: 6px;
    page-break-after: avoid;
}

p {
    margin-top: 0;
    margin-bottom: 10px;
    text-align: justify;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 16px 0;
    font-size: 7.8pt;
    line-height: 1.35;
    page-break-inside: avoid;
}

table th {
    background-color: #0f2942;
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 6px 7px;
    border: 1px solid #0f2942;
}

table td {
    padding: 5px 7px;
    border: 1px solid #cbd5e1;
    vertical-align: top;
}

table tr:nth-child(even) {
    background-color: #f8fafc;
}

/* Code & Preformatted Text */
pre {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 3px solid #0369a1;
    border-radius: 4px;
    padding: 9px 11px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 7pt;
    line-height: 1.3;
    color: #0f172a;
    overflow-x: auto;
    white-space: pre;
    page-break-inside: avoid;
    margin: 10px 0 14px 0;
}

code {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 8pt;
    background-color: #f1f5f9;
    color: #0f2942;
    padding: 1px 3px;
    border-radius: 3px;
    border: 1px solid #e2e8f0;
}

pre code {
    background-color: transparent;
    padding: 0;
    border: none;
    font-size: 7pt;
    color: inherit;
}

/* Math Display Box */
.math-display-box {
    background-color: #f8fafc;
    border: 1px dashed #0284c7;
    border-radius: 4px;
    padding: 8px 14px;
    margin: 10px 0;
    text-align: center;
    page-break-inside: avoid;
}

.math-content {
    font-family: 'Cambria Math', 'Times New Roman', serif;
    font-size: 10pt;
    color: #0f2942;
    font-style: italic;
}

.math-inline {
    font-family: 'Cambria Math', 'Times New Roman', serif;
    font-style: italic;
    color: #0f2942;
    padding: 0 2px;
}

.math-text {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-style: normal;
    font-weight: 500;
}

.cases {
    display: inline-block;
    text-align: left;
    margin-left: 8px;
    border-left: 2px solid #0f2942;
    padding-left: 8px;
}

/* Lists */
ul, ol {
    margin-top: 0;
    margin-bottom: 8px;
    padding-left: 20px;
}

li {
    margin-bottom: 3px;
}

/* Links */
a {
    color: #0284c7;
    text-decoration: none;
}

hr {
    border: 0;
    border-top: 1px solid #cbd5e1;
    margin: 16px 0;
}

/* Print specific optimizations */
@media print {
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
}
"""

cover_html = """
<div class="cover-page">
    <div class="cover-header">
        <div class="gov-badge">Government of India &bull; MoSPI</div>
        <div style="font-size: 9.5pt; color: #475569; font-weight: 600;">Ministry of Statistics and Programme Implementation</div>
    </div>
    
    <div class="cover-title-group">
        <h1>StatKarmayogi</h1>
        <div class="subtitle">AI-Driven Competency Assessment & Adaptive iGOT Learning Pathway</div>
        <div style="font-size: 14pt; color: #0f2942; font-weight: 700; margin-top: 14px; letter-spacing: -0.2px;">
            DATABASE & BACKEND MASTER GUIDE
        </div>
        <div class="doc-desc">
            Final As-Built Technical Report, Enterprise Architecture Specification, and Developer Reference Guide for the Complete Database and Backend Implementation.
        </div>
    </div>
    
    <div class="cover-meta-grid">
        <div class="meta-row">
            <span class="meta-label">SIH Problem Statement:</span>
            <span class="meta-value">SIH26101</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">Target Ministry:</span>
            <span class="meta-value">MoSPI (Indian Statistical Service & Subordinate Statistical Service)</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">System Implementation Status:</span>
            <span class="meta-value">Production-Ready Prototype / 100% Implemented</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">Automated Test Suite:</span>
            <span class="meta-value">174 of 174 Tests Passed (100% Pass Rate)</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">Relational Database Engine:</span>
            <span class="meta-value">PostgreSQL 16+ (Strictly 16 Tables Verified)</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">Vector Database & AI Engine:</span>
            <span class="meta-value">ChromaDB Local Vector Store & Mistral AI Large LLM / Embeddings</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">Document Date:</span>
            <span class="meta-value">September 2026</span>
        </div>
    </div>
    
    <div class="cover-footer">
        <span>Confidential &bull; Smart India Hackathon 2026 &bull; Team Zero Risk 64</span>
        <span>Authoritative Technical As-Built Report</span>
    </div>
</div>
"""

full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>StatKarmayogi — Database & Backend Master Guide</title>
    <style>
        {css}
    </style>
</head>
<body>
    {cover_html}
    <div class="document-content">
        {body_html}
    </div>
</body>
</html>
"""

print(f"Writing complete HTML to {HTML_FILE}...")
with open(HTML_FILE, "w", encoding="utf-8") as f:
    f.write(full_html)

print("Invoking Chrome Headless to compile PDF...")
pdf_abs = os.path.abspath(PDF_FILE)
html_abs = os.path.abspath(HTML_FILE)

cmd = [
    CHROME_PATH,
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    "--run-all-compositor-stages-before-draw",
    f"--print-to-pdf={pdf_abs}",
    html_abs
]

res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode != 0:
    print(f"Error compiling PDF: {res.stderr}")
    exit(1)

if not os.path.exists(PDF_FILE):
    print("Error: PDF file was not created!")
    exit(1)

reader = pypdf.PdfReader(PDF_FILE)
num_pages = len(reader.pages)
file_size_kb = os.path.getsize(PDF_FILE) / 1024

print("=" * 80)
print(f"SUCCESS: Generated PDF at {PDF_FILE}")
print(f"Total Pages: {num_pages}")
print(f"File Size: {file_size_kb:.1f} KB")
print("=" * 80)
