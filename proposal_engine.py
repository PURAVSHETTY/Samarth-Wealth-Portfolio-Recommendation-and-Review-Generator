"""
proposal_engine.py
────────────────────────────────────────────────────────────
Refactored engine for automated portfolio proposal generation.
Generates an 11-page A4 Landscape slide-deck matching the reference blueprint.
Supports TrueType fonts (Arial, Times New Roman) to render the Rupee symbol (₹).
"""

import sys
import os
import io
from datetime import datetime

import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Flowable, Image,
    PageTemplate, Frame, NextPageTemplate
)
from reportlab.graphics.shapes import Drawing, Wedge, Circle, String, Rect, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def get_roman_numeral(n):
    num_map = [
        (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')
    ]
    roman = ""
    for val, char in num_map:
        while n >= val:
            roman += char
            n -= val
    return roman


# Register TrueType fonts to support the Indian Rupee symbol (₹)
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Italic', 'ariali.ttf'))
    pdfmetrics.registerFont(TTFont('TimesNewRoman', 'times.ttf'))
    pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', 'timesbd.ttf'))
    pdfmetrics.registerFont(TTFont('TimesNewRoman-Italic', 'timesi.ttf'))
    pdfmetrics.registerFont(TTFont('TimesNewRoman-BoldItalic', 'timesbi.ttf'))
    FONT_SANS = "Arial"
    FONT_SANS_BOLD = "Arial-Bold"
    FONT_SANS_ITALIC = "Arial-Italic"
    FONT_SERIF = "TimesNewRoman"
    FONT_SERIF_BOLD = "TimesNewRoman-Bold"
    FONT_SERIF_ITALIC = "TimesNewRoman-Italic"
except Exception as e:
    print(f"[proposal_engine] TrueType font registration failed: {e}. Falling back to standard Helvetica/Times.")
    FONT_SANS = "Helvetica"
    FONT_SANS_BOLD = "Helvetica-Bold"
    FONT_SANS_ITALIC = "Helvetica-Oblique"
    FONT_SERIF = "Times-Roman"
    FONT_SERIF_BOLD = "Times-Bold"
    FONT_SERIF_ITALIC = "Times-Italic"

# Register local DejaVu Unicode fonts as a secondary set
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdfmetrics.registerFont(TTFont('DejaVuSans', os.path.join(current_dir, 'DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', os.path.join(current_dir, 'DejaVuSans-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Italic', os.path.join(current_dir, 'DejaVuSans-Oblique.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVuSerif', os.path.join(current_dir, 'DejaVuSerif.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVuSerif-Bold', os.path.join(current_dir, 'DejaVuSerif-Bold.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVuSerif-Italic', os.path.join(current_dir, 'DejaVuSerif-Italic.ttf')))
    FONT_UNICODE_SANS = "DejaVuSans"
    FONT_UNICODE_SANS_BOLD = "DejaVuSans-Bold"
    FONT_UNICODE_SANS_ITALIC = "DejaVuSans-Italic"
    FONT_UNICODE_SERIF = "DejaVuSerif"
    FONT_UNICODE_SERIF_BOLD = "DejaVuSerif-Bold"
    FONT_UNICODE_SERIF_ITALIC = "DejaVuSerif-Italic"
except Exception as e:
    print(f"[proposal_engine] Unicode font registration failed: {e}. Falling back to original fonts.")
    FONT_UNICODE_SANS = FONT_SANS
    FONT_UNICODE_SANS_BOLD = FONT_SANS_BOLD
    FONT_UNICODE_SANS_ITALIC = FONT_SANS_ITALIC
    FONT_UNICODE_SERIF = FONT_SERIF
    FONT_UNICODE_SERIF_BOLD = FONT_SERIF_BOLD
    FONT_UNICODE_SERIF_ITALIC = FONT_SERIF_ITALIC

# Mappings for bold/italic TrueType fonts to ensure <b> tags render correctly
from reportlab.lib.fonts import addMapping
try:
    addMapping('DejaVuSans', 0, 0, 'DejaVuSans')
    addMapping('DejaVuSans', 1, 0, 'DejaVuSans-Bold')
    addMapping('DejaVuSans', 0, 1, 'DejaVuSans-Italic')
    addMapping('DejaVuSans', 1, 1, 'DejaVuSans-Bold')
except Exception as e:
    print(f"[proposal_engine] DejaVuSans mapping failed: {e}")

try:
    addMapping('DejaVuSerif', 0, 0, 'DejaVuSerif')
    addMapping('DejaVuSerif', 1, 0, 'DejaVuSerif-Bold')
    addMapping('DejaVuSerif', 0, 1, 'DejaVuSerif-Italic')
    addMapping('DejaVuSerif', 1, 1, 'DejaVuSerif-Bold')
except Exception as e:
    print(f"[proposal_engine] DejaVuSerif mapping failed: {e}")

try:
    addMapping('Arial', 0, 0, 'Arial')
    addMapping('Arial', 1, 0, 'Arial-Bold')
    addMapping('Arial', 0, 1, 'Arial-Italic')
    addMapping('Arial', 1, 1, 'Arial-Bold')
except Exception as e:
    print(f"[proposal_engine] Arial mapping failed: {e}")

try:
    addMapping('TimesNewRoman', 0, 0, 'TimesNewRoman')
    addMapping('TimesNewRoman', 1, 0, 'TimesNewRoman-Bold')
    addMapping('TimesNewRoman', 0, 1, 'TimesNewRoman-Italic')
    addMapping('TimesNewRoman', 1, 1, 'TimesNewRoman-BoldItalic')
except Exception as e:
    print(f"[proposal_engine] TimesNewRoman mapping failed: {e}")


# ── Colour palette ──────────────────────────────────────────────────────────
NAVY       = colors.HexColor("#0B3624")  # Premium Deep Forest Green
GOLD       = colors.HexColor("#9A6A00")  # Gold accent
WHITE      = colors.white
LIGHT_GREY = colors.HexColor("#FAF9F5")  # Page background cream (subtle)
MID_GREY   = colors.HexColor("#E2E8F0")  # Borders / lines
DARK_GREY  = colors.HexColor("#334155")  # Soft charcoal slate
BG_BEIGE   = colors.HexColor("#F3ECE0")  # Segment headers background
GOLD_TEXT  = colors.HexColor("#9A6A00")  # Rich deep gold/bronze for readable text on light backgrounds
DARK_NAVY  = colors.HexColor("#0A2540")  # Clean dark blue institutional color



# Donut chart colors
PIE_COLORS = [
    colors.HexColor("#8E44AD"),  # Purple (Liquidity & Safety)
    colors.HexColor("#2980B9"),  # Blue (Regular Income)
    colors.HexColor("#F39C12"),  # Orange (Hedged Growth)
    colors.HexColor("#27AE60"),  # Green (Wealth Compounding)
]

W, H = landscape(A4)  # 841.89 x 595.27 pt
W_net = W - 102       # 739.89 pt


# ── Typography helpers ───────────────────────────────────────────────────────
def style(name, **kw):
    return ParagraphStyle(name, **kw)


# Restrained institutional proposal typography
TITLE_PAGE = style("TitlePage",
    fontName=FONT_SERIF_BOLD, fontSize=28, leading=33,
    textColor=NAVY, alignment=1)

TITLE_LARGE = style("TitleLarge",
    fontName=FONT_SERIF_BOLD, fontSize=22, leading=26,
    textColor=NAVY, spaceAfter=6)

TITLE_MED = style("TitleMed",
    fontName=FONT_SERIF_BOLD, fontSize=18, leading=22,
    textColor=NAVY, spaceAfter=5)

TITLE_SMALL = style("TitleSmall",
    fontName=FONT_SERIF_BOLD, fontSize=13, leading=16,
    textColor=NAVY, spaceAfter=3)

LABEL_GOLD = style("LabelGold",
    fontName=FONT_SANS_BOLD, fontSize=9, leading=11,
    textColor=GOLD, spaceAfter=2)

BODY = style("Body",
    fontName=FONT_UNICODE_SANS, fontSize=11.5, leading=16,
    textColor=DARK_GREY, spaceAfter=3)

BODY_BOLD = style("BodyBold",
    fontName=FONT_UNICODE_SANS_BOLD, fontSize=11.5, leading=16,
    textColor=NAVY, spaceAfter=3)

BODY_ITALIC = style("BodyItalic",
    fontName=FONT_UNICODE_SANS_ITALIC, fontSize=11.5, leading=16,
    textColor=DARK_GREY, spaceAfter=3)

TABLE_HEADER = style("TableHeader",
    fontName=FONT_UNICODE_SANS_BOLD, fontSize=11.5, leading=15,
    textColor=WHITE, alignment=1)

TABLE_HEADER_LEFT = style("TableHeaderLeft",
    fontName=FONT_UNICODE_SANS_BOLD, fontSize=11.5, leading=15,
    textColor=WHITE, alignment=0)

TABLE_HEADER_CENTER = style("TableHeaderCenter",
    fontName=FONT_UNICODE_SANS_BOLD, fontSize=11.5, leading=15,
    textColor=WHITE, alignment=1)

TABLE_CELL = style("TableCell",
    fontName=FONT_UNICODE_SANS, fontSize=10.5, leading=14.5,
    textColor=DARK_NAVY)

TABLE_CELL_BOLD = style("TableCellBold",
    fontName=FONT_UNICODE_SANS_BOLD, fontSize=10.5, leading=14.5,
    textColor=DARK_NAVY)

TABLE_CELL_CENTER = style("TableCellCenter",
    fontName=FONT_UNICODE_SANS, fontSize=10.5, leading=14.5,
    textColor=DARK_NAVY, alignment=1)

TABLE_CELL_CENTER_BOLD = style("TableCellCenterBold",
    fontName=FONT_UNICODE_SANS_BOLD, fontSize=10.5, leading=14.5,
    textColor=DARK_NAVY, alignment=1)

TABLE_CELL_AMOUNT = style("TableCellAmount",
    fontName=FONT_UNICODE_SANS_BOLD, fontSize=10.5, leading=14.5,
    textColor=DARK_NAVY, alignment=1)

DISCLAIMER = style("Disclaimer",
    fontName=FONT_SANS, fontSize=8, leading=11,
    textColor=DARK_GREY, spaceAfter=4)


# ── Format helpers ───────────────────────────────────────────────────────────
def clean_float(val):
    if val is None:
        return 0.0
    val_str = str(val).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace(" ", "").strip()
    if not val_str or val_str == "nan":
        return 0.0
        
    is_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_negative = True
        val_str = val_str[1:-1].strip()
        
    multiplier = 1.0
    if "crore" in val_str or "cr" in val_str:
        multiplier = 10000000.0
        val_str = val_str.replace("crores", "").replace("crore", "").replace("cr", "")
    elif "lakh" in val_str or "l" in val_str:
        if any(x in val_str for x in ["lakhs", "lakh"]):
            multiplier = 100000.0
            val_str = val_str.replace("lakhs", "").replace("lakh", "")
        elif val_str.endswith("l"):
            multiplier = 100000.0
            val_str = val_str[:-1]
    elif "million" in val_str or val_str.endswith("m"):
        multiplier = 1000000.0
        val_str = val_str.replace("million", "")
        if val_str.endswith("m"):
            val_str = val_str[:-1]
    elif "thousand" in val_str or val_str.endswith("k"):
        multiplier = 1000.0
        val_str = val_str.replace("thousand", "")
        if val_str.endswith("k"):
            val_str = val_str[:-1]
            
    try:
        import re
        val_str = re.sub(r"[^\d\.\-]", "", val_str)
        if not val_str:
            return 0.0
        result = float(val_str) * multiplier
        if is_negative:
            result = -result
        return result
    except ValueError:
        return 0.0

def get_table_padding_and_fontsize(num_rows):
    if num_rows > 12:
        return 1.2, 8.5, 11.0
    elif num_rows > 8:
        return 2.2, 9.5, 12.5
    else:
        return 3.5, 10.5, 14.5

def format_corpus_short(corpus_val):
    try:
        val_float = clean_float(corpus_val)
        if val_float >= 10000000:
            cr = val_float / 10000000
            if cr.is_integer():
                return f"₹ {int(cr)} Cr"
            else:
                return f"₹ {cr:.1f} Cr"
        elif val_float >= 100000:
            lakhs = val_float / 100000
            if lakhs.is_integer():
                return f"₹ {int(lakhs)} Lakh"
            else:
                return f"₹ {lakhs:.1f} Lakh"
        else:
            return f"₹ {val_float:,.0f}"
    except:
        return f"₹ {corpus_val}"


def format_rupee_words(val):
    try:
        val_float = clean_float(val)
        if val_float >= 10000000:
            cr = val_float / 10000000
            if cr.is_integer():
                return f'<font name="DejaVuSans-Bold">₹</font> {int(cr)} Crore' + ("s" if cr > 1 else "")
            else:
                return f'<font name="DejaVuSans-Bold">₹</font> {cr:.1f} Crores'
        elif val_float >= 100000:
            lakhs = val_float / 100000
            if lakhs.is_integer():
                return f'<font name="DejaVuSans-Bold">₹</font> {int(lakhs)} Lakhs'
            else:
                return f'<font name="DejaVuSans-Bold">₹</font> {lakhs:.1f} Lakhs'
        else:
            return f'<font name="DejaVuSans-Bold">₹</font> {val_float:,.0f}'
    except:
        return f'<font name="DejaVuSans-Bold">₹</font> {val}'


# ── Custom Flowables / Drawings ──────────────────────────────────────────────
def make_image_placeholder(title_text, width=340, height=170):
    d = Drawing(width, height)
    # solid navy rect
    d.add(Rect(0, 0, width, height, fillColor=NAVY, strokeColor=None))
    # inner gold rect with padding
    d.add(Rect(12, 12, width - 24, height - 24, fillColor=None, strokeColor=GOLD, strokeWidth=1))
    # text initials or name in center
    d.add(String(width / 2, height / 2 - 4, title_text.upper(), textAnchor="middle",
                 fontName=FONT_SERIF_BOLD, fontSize=14, fillColor=WHITE))
    return d


def make_gold_bar(width=54, height=3.6):
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=GOLD, strokeColor=None))
    return d


def make_dashboard_donut(allocations, corpus_str, size=200):
    d = Drawing(size, size)
    pie = Pie()
    pie.x = size * 0.05
    pie.y = size * 0.05
    pie.width = size * 0.9
    pie.height = size * 0.9
    
    # Extract values and colors dynamically mapping to their Part numbers
    raw_data = []
    slice_colors = []
    for a in allocations:
        val = clean_float(a.get("Allocation %", 0))
        if val > 0:
            raw_data.append(val)
            part_idx = int(a.get("Part", 1)) - 1
            slice_colors.append(PIE_COLORS[part_idx % len(PIE_COLORS)])
            
    # Safeguard against zero-sum or empty allocation data
    if not raw_data or sum(raw_data) == 0:
        pie.data = [100]
        pie.slices.strokeWidth = 0.5
        pie.slices.strokeColor = colors.white
        pie.slices[0].fillColor = colors.lightgrey
    else:
        pie.data = raw_data
        pie.slices.strokeWidth = 0.5
        pie.slices.strokeColor = colors.white
        for i, c in enumerate(slice_colors):
            pie.slices[i].fillColor = c
            
    pie.startAngle = 90
    pie.direction = "clockwise"
    pie.innerRadiusFraction = 0.76  # Modern, thin donut
    d.add(pie)
    
    # Center hole label (Total Corpus, e.g. 10 Cr)
    cx, cy = size / 2, size / 2
    d.add(String(cx, cy + 5, "Total Corpus", textAnchor="middle",
                 fontName=FONT_SANS, fontSize=9, fillColor=DARK_GREY))
    d.add(String(cx, cy - 10, format_corpus_short(corpus_str), textAnchor="middle",
                 fontName=FONT_UNICODE_SERIF_BOLD, fontSize=18, fillColor=NAVY))
    return d


def make_dashboard_legend_table(allocations):
    rows = []
    active_allocs = [a for a in allocations if clean_float(a.get("Allocation %", 0)) > 0]
    
    # Legend headers
    legend_header_style = ParagraphStyle(
        "LegendHeader",
        fontName=FONT_SANS_BOLD,
        fontSize=9,
        leading=11,
        textColor=GOLD
    )
    rows.append([
        "",
        Paragraph("ALLOC.", legend_header_style),
        Paragraph("PORTFOLIO SEGMENT", legend_header_style),
        Paragraph("STRATEGIC ROLE & OBJECTIVE", legend_header_style)
    ])
    
    for i, a in enumerate(active_allocs):
        part_idx = int(a.get("Part", 1)) - 1
        color = PIE_COLORS[part_idx % len(PIE_COLORS)]
        pct_str = str(a.get("Allocation %", 0)).replace("%", "").strip()
        name_val = str(a.get("Segment Name", ""))
        sub_val = str(a.get("AMFI_Subtitle", ""))
        if sub_val:
            name = f"{name_val}<br/><font size='8.5' color='#9A6A00'><b>{sub_val}</b></font>"
        else:
            name = name_val
        desc = str(a.get("Objective", ""))
        
        # Color square drawing - aligned slightly higher to align with text
        sq = Drawing(10, 10)
        sq.add(Rect(0, 1, 8, 8, fillColor=color, strokeColor=None))
        
        # Text styles - tighter sizing and leading
        pct_style = ParagraphStyle(
            f"PctStyle_{i}",
            fontName=FONT_SANS_BOLD,
            fontSize=11.5,
            leading=14.5,
            textColor=color
        )
        name_style = ParagraphStyle(
            f"NameStyle_{i}",
            fontName=FONT_SANS_BOLD,
            fontSize=11.5,
            leading=14.5,
            textColor=NAVY
        )
        desc_style = ParagraphStyle(
            f"DescStyle_{i}",
            fontName=FONT_SANS,
            fontSize=10.5,
            leading=14.5,
            textColor=DARK_GREY
        )
        
        rows.append([
            sq,
            Paragraph(f"{pct_str}%", pct_style),
            Paragraph(name, name_style),
            Paragraph(desc, desc_style)
        ])
        
    # Safeguard against empty legendary listings
    if len(rows) == 1:
        placeholder_style = ParagraphStyle(
            "PlaceholderStyle",
            fontName=FONT_SANS,
            fontSize=9.5,
            leading=12,
            textColor=DARK_GREY
        )
        placeholder_bold = ParagraphStyle(
            "PlaceholderBold",
            fontName=FONT_SANS_BOLD,
            fontSize=9.5,
            leading=12,
            textColor=GOLD
        )
        rows.append([
            Drawing(10, 10),
            Paragraph("0%", placeholder_bold),
            Paragraph("No Allocations", placeholder_bold),
            Paragraph("Please provide allocation details in template", placeholder_style)
        ])
        
    t = Table(rows, colWidths=[12, 45, 155, W_net - 160 - 12 - 45 - 155], hAlign='LEFT')
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, GOLD), # Accent line under headers
    ]))
    return t


def append_contact_block(story, firm, tagline, firm_name_raw):
    story.append(Spacer(1, 15))
    
    addr = firm.get("Address", "G-75/76, Eternity Commercial Premises, Thane (W)")
    email = firm.get("Email", "relationships@samarthedufin.com")
    website = firm.get("Website", "www.samarthwealth.in")
    phone = firm.get("Phone", "")
    
    # White/Gold styles for Navy background
    style_title = style("CLeftTitleWhite", fontName=FONT_SANS_BOLD, fontSize=10.5, leading=13, textColor=colors.white)
    style_addr = style("CLeftAddrWhite", fontName=FONT_SANS, fontSize=8, leading=11, textColor=colors.HexColor("#CBD5E1"))
    style_details = style("CLeftDetailsWhite", fontName=FONT_SANS, fontSize=8, leading=11, textColor=colors.HexColor("#CBD5E1"))
    style_tagline = style("CRightTaglineWhite", fontName=FONT_SERIF_ITALIC, fontSize=11, leading=14, textColor=colors.white, alignment=2)
    
    contact_left = [
        Paragraph(f"<b>{firm_name_raw}</b>", style_title),
        Spacer(1, 2),
        Paragraph(addr, style_addr),
        Spacer(1, 2),
        Paragraph(f"Email: {email}  |  Web: {website}  |  Contact: {phone}", style_details)
    ]
    
    contact_right = [
        Spacer(1, 8),
        Paragraph(f'"{tagline}"', style_tagline)
    ]
    
    contact_table = Table([[contact_left, contact_right]], colWidths=[W_net * 0.60, W_net * 0.40], hAlign='CENTER')
    contact_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("LINEABOVE", (0, 0), (-1, 0), 1.5, GOLD),
    ]))
    story.append(contact_table)


# ── Excel reader ─────────────────────────────────────────────────────────────
def read_excel(path_or_file):
    """
    Reads data from an Excel file (path, file-like object, or bytes).
    Returns a dictionary of parsed tables.
    Performs validation on sheets, column schemas, and empty critical cells.
    """
    try:
        xl = pd.read_excel(path_or_file, sheet_name=None, header=0)
    except Exception as e:
        raise ValueError(f"Invalid Excel file or corrupted format: {str(e)}")

    # Validate Sheet Existence
    required_sheets = ["Firm_Info", "Client_Info", "Asset_Allocation", "Products"]
    for sheet in required_sheets:
        if sheet not in xl:
            raise ValueError(f"Invalid Excel Template: Missing sheet '{sheet}'")

    data = {}

    # Parse & Validate Firm_Info
    df_firm = xl["Firm_Info"]
    if df_firm.empty or len(df_firm.columns) < 2:
        raise ValueError("Firm_Info sheet is empty or incorrectly formatted (must have 2 columns)")
    firm_dict = dict(zip(df_firm.iloc[:, 0].astype(str).str.strip(), df_firm.iloc[:, 1]))
    firm_dict = {k: (str(v).strip() if pd.notna(v) else "") for k, v in firm_dict.items() if k and k.lower() != "nan"}
    
    if "Firm Name" not in firm_dict or not firm_dict["Firm Name"]:
        raise ValueError("Validation Error: 'Firm Name' is missing or empty in Firm_Info sheet")
    data["firm"] = firm_dict

    # Parse & Validate Client_Info
    df_client = xl["Client_Info"]
    if df_client.empty or len(df_client.columns) < 2:
        raise ValueError("Client_Info sheet is empty or incorrectly formatted (must have 2 columns)")
    client_dict = dict(zip(df_client.iloc[:, 0].astype(str).str.strip(), df_client.iloc[:, 1]))
    client_dict = {k: (str(v).strip() if pd.notna(v) else "") for k, v in client_dict.items() if k and k.lower() != "nan"}
    
    if "Client Name" not in client_dict or not client_dict["Client Name"]:
        raise ValueError("Validation Error: 'Client Name' is missing or empty in Client_Info sheet")
    if "Portfolio Corpus (INR)" not in client_dict or not client_dict["Portfolio Corpus (INR)"]:
        raise ValueError("Validation Error: 'Portfolio Corpus (INR)' is missing or empty in Client_Info sheet")
    data["client"] = client_dict

    # Parse & Auto-Map Asset_Allocation
    df_alloc = xl["Asset_Allocation"]
    if df_alloc.empty:
        raise ValueError("Asset_Allocation sheet is empty")
        
    alloc_cols = df_alloc.columns.tolist()
    mapped_alloc = {}
    for col in alloc_cols:
        norm = str(col).strip().lower()
        if "part" in norm:
            mapped_alloc[col] = "Part"
        elif "segment" in norm or "name" in norm:
            mapped_alloc[col] = "Segment Name"
        elif "alloc" in norm or "%" in norm:
            mapped_alloc[col] = "Allocation %"
        elif "objective" in norm or "obj" in norm:
            mapped_alloc[col] = "Objective"

    required_alloc_cols = ["Part", "Segment Name", "Allocation %"]
    for req in required_alloc_cols:
        if req not in mapped_alloc.values():
            raise ValueError(f"Validation Error: Could not map required column for Asset_Allocation (expected: '{req}')")

    df_alloc = df_alloc.rename(columns=mapped_alloc)
    df_alloc = df_alloc[list(mapped_alloc.values())]
    df_alloc = df_alloc.fillna("")
    
    alloc_list = df_alloc.to_dict("records")
    for idx, row in enumerate(alloc_list):
        if not str(row.get("Part", "")).strip():
            raise ValueError(f"Validation Error: Asset_Allocation row {idx+2} has an empty 'Part' cell")
        if not str(row.get("Segment Name", "")).strip():
            raise ValueError(f"Validation Error: Asset_Allocation row {idx+2} has an empty 'Segment Name' cell")
        if not str(row.get("Allocation %", "")).strip():
            raise ValueError(f"Validation Error: Asset_Allocation row {idx+2} has an empty 'Allocation %' cell")
            
    data["allocation"] = alloc_list

    # Parse & Auto-Map Products
    df_prod = xl["Products"]
    if df_prod.empty:
        raise ValueError("Products sheet is empty")
        
    prod_cols = df_prod.columns.tolist()
    mapped_prod = {}
    for col in prod_cols:
        norm = str(col).strip().lower()
        if "part" in norm:
            mapped_prod[col] = "Part"
        elif "segment" in norm:
            mapped_prod[col] = "Segment"
        elif "product" in norm or "name" in norm:
            mapped_prod[col] = "Product Name"
        elif "asset" in norm or "class" in norm:
            mapped_prod[col] = "Asset Class"
        elif "alloc" in norm or "inr" in norm or "amount" in norm:
            mapped_prod[col] = "Allocation (INR)"
        elif "return" in norm or "irr" in norm or "yield" in norm:
            mapped_prod[col] = "Target Return"
        elif "rationale" in norm or "core" in norm or "reason" in norm:
            mapped_prod[col] = "Core Rationale"

    required_prod_cols = ["Part", "Product Name", "Allocation (INR)"]
    for req in required_prod_cols:
        if req not in mapped_prod.values():
            raise ValueError(f"Validation Error: Could not map required column for Products (expected: '{req}')")

    df_prod = df_prod.rename(columns=mapped_prod)
    df_prod = df_prod[list(mapped_prod.values())]
    df_prod = df_prod.fillna("")
    
    prod_list = df_prod.to_dict("records")
    for idx, row in enumerate(prod_list):
        if not str(row.get("Part", "")).strip():
            raise ValueError(f"Validation Error: Products row {idx+2} has an empty 'Part' cell")
        if not str(row.get("Product Name", "")).strip():
            raise ValueError(f"Validation Error: Products row {idx+2} has an empty 'Product Name' cell")
        if not str(row.get("Allocation (INR)", "")).strip():
            raise ValueError(f"Validation Error: Products row {idx+2} has an empty 'Allocation (INR)' cell")
            
    data["products"] = prod_list

    return data


# ── Canvas Background Drawings ──────────────────────────────────────────────
def draw_cover_bg(c, doc):
    c.saveState()
    # Solid Navy top 2/3: from y = 198 to H (y-up in ReportLab)
    # H = 595.27. 2/3 of H is approx 396.85. Top part starts at y = 198.42
    c.setFillColor(NAVY)
    c.rect(0, 198.42, W, H - 198.42, fill=1, stroke=0)
    
    # Draw a thin gold accent border inside the green area (30pt from margins)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.rect(30, 198.42 + 30, W - 60, H - 198.42 - 50, fill=0, stroke=1)
    
    # White bottom 1/3: from y = 0 to 198.42
    c.setFillColor(WHITE)
    c.rect(0, 0, W, 198.42, fill=1, stroke=0)
    
    # Golden horizontal separator line (transition line) at y = 198.42 (4pt height)
    c.setFillColor(GOLD)
    c.rect(0, 196.42, W, 4, fill=1, stroke=0)
    c.restoreState()


def draw_later_bg(c, doc):
    # Clean page background with no outer border or stripes
    pass


def make_target_return_badge(return_text, fs_val):
    if not return_text or return_text == "—":
        badge_style_empty = ParagraphStyle(
            "BadgeStyleEmpty",
            fontName=FONT_SANS,
            fontSize=fs_val,
            leading=fs_val + 2.5,
            textColor=DARK_GREY,
            alignment=1
        )
        return Paragraph("—", badge_style_empty)
        
    p_style = ParagraphStyle(
        "BadgeStyleText",
        fontName=FONT_SANS_BOLD,
        fontSize=fs_val - 0.5,
        leading=fs_val + 1,
        textColor=colors.HexColor("#27AE60"),
        alignment=1
    )
    p = Paragraph(return_text, p_style)
    
    # Single-cell Table to act as a green badge
    badge_table = Table([[p]], colWidths=[65], hAlign='CENTER')
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#E2F3E9")), # light green
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    return badge_table


# ── PDF GENERATION FROM DICTIONARY DATA ─────────────────────────────────────────
def generate_pdf_from_data(data, output_path=None):
    """
    Generates an 11-page A4 Landscape slide-deck portfolio proposal.
    """
    style_hdr_left = style("HdrLeftWhite", fontName=FONT_SANS_BOLD, fontSize=9, leading=12, textColor=WHITE, alignment=0)
    style_hdr_center = style("HdrCenterWhite", fontName=FONT_SANS_BOLD, fontSize=9, leading=12, textColor=WHITE, alignment=1)

    firm      = data.get("firm", {})
    client    = data.get("client", {})
    allocs    = data.get("allocation", [])
    products  = data.get("products", [])

    # If the product list doesn't have expanded rationales (e.g. read from Excel directly),
    # run generate_ai_portfolio to auto-allocate and write rationales!
    if not data.get("executive_summary") or (len(products) > 0 and "Why Selected" not in products[0]):
        from ai_engine import generate_ai_portfolio
        print("[proposal_engine] Running dynamic AI fallback integration to populate narrative content...")
        ai_res = generate_ai_portfolio(client, products)
        data["allocation"] = ai_res.get("allocation", [])
        data["products"] = ai_res.get("products", [])
        data["executive_summary"] = ai_res.get("executive_summary", "")
        data["portfolio_thesis"] = ai_res.get("portfolio_thesis", "")
        data["market_commentary"] = ai_res.get("market_commentary", "")
        
        # update references
        allocs    = data["allocation"]
        products  = data["products"]

    # Print parsed investment data in terminal logs (Requirement 1)
    print("\n==================================================", flush=True)
    print("PARSED INVESTMENT DATA BEFORE PDF GENERATION:", flush=True)
    print(f"Client Name: {client.get('Client Name', 'N/A')}", flush=True)
    print(f"Portfolio Corpus: {client.get('Portfolio Corpus (INR)', 'N/A')}", flush=True)
    print(f"Total Products Detected: {len(products) if products else 0}", flush=True)
    if products:
        for idx, p in enumerate(products, 1):
            print(f"  Product {idx}: {p.get('Product Name', 'N/A')}", flush=True)
            print(f"    Allocation: {p.get('Allocation (INR)', '0')}", flush=True)
            print(f"    Category: {p.get('Segment', 'N/A')}", flush=True)
            print(f"    Target Return: {p.get('Target Return', 'N/A')}", flush=True)
    print("Asset Allocation Dashboard (Segments):", flush=True)
    if allocs:
        for idx, a in enumerate(allocs, 1):
            print(f"  Segment {idx}: {a.get('Segment Name', 'N/A')} | Allocation: {a.get('Allocation %', '0')}% | Objective: {a.get('Objective', 'N/A')}", flush=True)
    print("==================================================\n", flush=True)

    # ── VALIDATION AND LOGGING OF REAL INVESTMENT DATA ──────────────────────────────
    if not products or len(products) == 0:
        raise ValueError("Parser failed: No investment products detected.")
        
    total_alloc_val = sum(clean_float(p.get("Allocation (INR)")) for p in products)
    if total_alloc_val == 0.0:
        raise ValueError("Parser failed: No investment products detected.")
        
    for idx, p in enumerate(products, 1):
        if not p.get("Product Name") or str(p.get("Product Name")).strip() == "" or str(p.get("Product Name")).lower() == "nan":
            raise ValueError("Parser failed: No investment products detected.")
        if clean_float(p.get("Allocation (INR)")) < 0.0:
            raise ValueError("Validation Error: Mapped Product has a negative allocation.")

    # Normalize segment allocation percentage dynamically to sum to exactly 100% instead of raising ValueError
    total_pct = sum(clean_float(a.get("Allocation %", 0)) for a in allocs)
    if abs(total_pct - 100.0) > 0.01:
        print(f"[proposal_engine] Normalizing segment allocations from {total_pct}% to 100%")
        if total_pct > 0:
            factor = 100.0 / total_pct
            for a in allocs:
                a["Allocation %"] = round(clean_float(a.get("Allocation %", 0)) * factor)
            # Recheck and adjust any rounding error
            new_total = sum(a["Allocation %"] for a in allocs)
            if new_total != 100 and len(allocs) > 0:
                largest = max(allocs, key=lambda x: x["Allocation %"])
                largest["Allocation %"] += (100 - new_total)
        else:
            share = round(100.0 / len(allocs)) if len(allocs) > 0 else 100
            for a in allocs:
                a["Allocation %"] = share
            new_total = sum(a["Allocation %"] for a in allocs)
            if new_total != 100 and len(allocs) > 0:
                allocs[0]["Allocation %"] += (100 - new_total)
        
    # Synchronize total product allocations sum and Portfolio Corpus instead of raising ValueError
    corpus_val = clean_float(client.get("Portfolio Corpus (INR)", "0"))
    if corpus_val == 0.0 or abs(corpus_val - total_alloc_val) > 1.0:
        print(f"[proposal_engine] Synchronizing corpus value from {corpus_val} to sum of product allocations {total_alloc_val}")
        client["Portfolio Corpus (INR)"] = f"{int(total_alloc_val):,}"
        corpus_val = total_alloc_val

    client_name = client.get("Client Name", "Client Portfolio")
    safe_name   = client_name.replace(" ", "_").replace("&", "and").replace(".", "")
    filename    = f"Proposal_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"

    # Determine target file-like or path
    return_bytes = False
    if output_path == "bytes":
        target = io.BytesIO()
        return_bytes = True
    elif output_path is None:
        target = filename
    else:
        target = output_path

    # Group products by Part dynamically
    parts_data = {}
    for p in products:
        try:
            pt = int(float(str(p.get("Part", 1)).replace("Part", "").strip()))
        except:
            pt = 1
        if pt not in parts_data:
            parts_data[pt] = []
        parts_data[pt].append(p)
        
    active_parts = sorted(list(parts_data.keys()))
    last_active_part = active_parts[-1] if active_parts else 1
    
    part_allocations = {}
    for pt in active_parts:
        part_allocations[pt] = sum(clean_float(p.get("Allocation (INR)", "0")) for p in parts_data[pt])

    doc = SimpleDocTemplate(
        target,
        pagesize=landscape(A4),
        leftMargin=51, rightMargin=51,
        topMargin=32, bottomMargin=32,
        onFirstPage=draw_cover_bg,
        onLaterPages=draw_later_bg
    )
    
    # Custom PageTemplate for Cover (Page 1)
    cover_frame = Frame(
        51, 32,
        doc.width, doc.height,
        id='CoverFrame',
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0
    )
    cover_template = PageTemplate(
        id='FirstPage',
        frames=cover_frame,
        onPage=draw_cover_bg
    )

    # Custom PageTemplate for Page 2 (12pt margins left/right, 2pt top/bottom)
    page2_frame = Frame(
        12, 2,                  # x, y
        doc.width + 78, 591.27, # width, height (817.89 x 591.27)
        id='Page2Frame',
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0
    )
    page2_template = PageTemplate(
        id='Page2Template',
        frames=page2_frame,
        onPage=draw_later_bg
    )

    # Custom PageTemplate for Later Pages
    later_frame = Frame(
        51, 32,
        doc.width, doc.height,
        id='LaterFrame',
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0
    )
    later_template = PageTemplate(
        id='Later',
        frames=later_frame,
        onPage=draw_later_bg
    )
    
    doc.addPageTemplates([cover_template, page2_template, later_template])

    story = []
    
    # ── Page 1: Cover Page
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 15))
    firm_name_raw = firm.get("Firm Name", "Samarth Wealth").upper()
    clean_firm = firm_name_raw.replace("PVT.", "").replace("LTD.", "").strip()
    words = clean_firm.split()
    spaced_words = ["&nbsp;&nbsp;&nbsp;".join(list(word)) for word in words]
    spaced_firm = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;".join(spaced_words)  # Elegant luxury tracking and word separation
    story.append(Paragraph(spaced_firm, style("CoverTitle", parent=TITLE_PAGE, textColor=WHITE)))
    
    tagline = firm.get("Tagline", "Clients First. Always and Everytime.")
    tagline_spaced = "&nbsp;&nbsp;".join(list(tagline.upper()))
    tagline_style = style("CoverTagline", fontName=FONT_SANS_BOLD, fontSize=8.5, leading=11, textColor=GOLD, alignment=1)
    story.append(Paragraph(f'"{tagline_spaced}"', tagline_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="20%", thickness=1.5, color=GOLD, spaceBefore=0, spaceAfter=0, hAlign='CENTER'))
    story.append(Spacer(1, 20))
    
    subtitle_text = "Strategic Investment Recommendation"
    story.append(Paragraph(subtitle_text, style("CoverSub", fontName=FONT_SERIF_BOLD, fontSize=14, leading=17, textColor=WHITE, alignment=1)))
    story.append(Spacer(1, 12))
    
    # Center box with client details (solid gold border, white background)
    box_content = [
        [Spacer(1, 10)],
        [Paragraph(client_name, style("CoverClient", fontName=FONT_SERIF_BOLD, fontSize=27, leading=32, textColor=NAVY, alignment=1))],
        [Spacer(1, 10)],
        [Paragraph(f"Portfolio Corpus: {format_rupee_words(client.get('Portfolio Corpus (INR)', '10,00,00,000'))}", 
                   style("CoverCorpus", fontName=FONT_SERIF_BOLD, fontSize=16, leading=19, textColor=GOLD, alignment=1))],
        [Spacer(1, 10)]
    ]
    box_table = Table(box_content, colWidths=[460])
    box_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 1.5, GOLD), # Premium gold border
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    
    story.append(box_table)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Page 2: Company Profile
    # ─────────────────────────────────────────────────────────────────────────
    story.append(NextPageTemplate('Page2Template'))
    story.append(PageBreak())
    
    P2_CENTER_SUB = style("P2CenterSub", fontName=FONT_SANS_BOLD, fontSize=9.0, leading=12, textColor=GOLD, alignment=1)
    P2_CENTER_TITLE = style("P2CenterTitle", fontName=FONT_SERIF_BOLD, fontSize=24, leading=28, textColor=NAVY, alignment=1)
    P2_BODY = style("P2Body", parent=BODY, fontSize=12.0, leading=15.0, spaceAfter=2, alignment=4)
    P2_LEGACY_TITLE = style("P2LegacyTitle", fontName=FONT_SERIF_BOLD, fontSize=24, leading=28, textColor=NAVY)
    P2_PAGE_TITLE = style("P2PageTitle", parent=P2_LEGACY_TITLE, leftIndent=39)
    
    firm_p1 = (
        "Established in 2011, <b>Samarth Wealth Pvt. Ltd.</b> has spent the last 15 years "
        "institutionalizing the philosophy of <b>\"Client Interest First.\"</b> Headquartered "
        "in <b>Thane</b>, we are a team of <b>30+ dedicated wealth management professionals</b> "
        "committed to helping individuals, families, business owners, and professionals "
        "achieve their long-term financial goals. Today, we manage a diversified "
        "<b>Assets Under Management (AUM) of over ₹1,500 Crores</b> across Mutual Funds, "
        "Portfolio Management Services (PMS), Alternative Investment Funds (AIFs), "
        "Specialized Investment Funds (SIFs), and Direct Equity. Through a disciplined, "
        "research-driven approach and personalized financial planning, we strive to "
        "deliver investment solutions that are aligned with each client's unique "
        "objectives, risk appetite, and wealth creation journey."
    )
    firm_p2 = (
        "Our core strength lies in our rigorous investment selection process and our "
        "continuous engagement with Fund Managers, Chief Investment Officers (CIOs), "
        "and senior leadership teams of leading Asset Management Companies (AMCs). "
        "These direct interactions provide valuable insights into market trends, "
        "investment strategies, and emerging opportunities, enabling us to make "
        "informed decisions on behalf of our clients. At <b>Samarth Wealth Pvt. Ltd.</b>, transparency, "
        "trust, and ethical conduct are at the heart of everything we do. Guided by "
        "a strict <b>Zero Mis-selling Policy</b>, we ensure that every recommendation is "
        "made solely in the best interest of our clients. We believe wealth management "
        "goes beyond managing investments—it is about preserving capital, creating "
        "sustainable long-term growth, and safeguarding the financial legacy of "
        "generations to come."
    )
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_img_path = os.path.join(current_dir, "extracted_img_p2_1_147.jpeg")
    if not os.path.exists(logo_img_path):
        if os.path.exists("extracted_img_p2_1_147.jpeg"):
            logo_img_path = "extracted_img_p2_1_147.jpeg"

    if not os.path.exists(logo_img_path):
        logo_table = make_image_placeholder("Samarth Wealth", width=352, height=220)
    else:
        logo_img = Image(logo_img_path, width=352, height=220)
        logo_table = Table([[logo_img]], colWidths=[352], hAlign='CENTER')
        logo_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
    story.append(Paragraph("<u>COMPANY PROFILE</u>", P2_PAGE_TITLE))
    story.append(Spacer(1, 10))
    story.append(logo_table)
    story.append(Spacer(1, 20))
    story.append(Paragraph("OUR FIRM", P2_CENTER_SUB))
    story.append(Spacer(1, 8))
    story.append(Paragraph("The Samarth Wealth Legacy", P2_CENTER_TITLE))
    story.append(Spacer(1, 8))
    gold_bar_table = Table([[make_gold_bar(54, 3.6)]], colWidths=[54], hAlign='CENTER')
    gold_bar_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(gold_bar_table)
    story.append(Spacer(1, 20))
    
    desc_content = [
        Paragraph(firm_p1, P2_BODY),
        Spacer(1, 15),
        Paragraph(firm_p2, P2_BODY)
    ]
    desc_table = Table([[desc_content]], colWidths=[760], hAlign='CENTER')
    desc_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(desc_table)
    
    # ── Page 3: Our Founders
    # ─────────────────────────────────────────────────────────────────────────
    story.append(NextPageTemplate('Later'))
    story.append(PageBreak())
    
    P2_FOUNDER_NAME = style("P2FounderName", fontName=FONT_SERIF_BOLD, fontSize=24, leading=28, textColor=NAVY)
    P2_FOUNDER_TITLE = style("P2FounderTitle", fontName=FONT_SANS_BOLD, fontSize=13.0, leading=17.0, textColor=GOLD, spaceAfter=3)
    P2_BIO_BODY = style("P2BioBody", parent=BODY, fontSize=9.8, leading=11.5, spaceAfter=2, alignment=4)
    P2_LEGACY_TITLE = style("P2LegacyTitle", fontName=FONT_SERIF_BOLD, fontSize=24, leading=28, textColor=NAVY)
    header_style_lbl = style("P2HeaderLbl", fontName=FONT_SANS_BOLD, fontSize=9.0, leading=12, textColor=GOLD)
    
    story.append(Paragraph("<u>OUR FOUNDERS</u>", P2_LEGACY_TITLE))
    story.append(Spacer(1, 15))
    
    adv_name = firm.get("Advisor Name", "Abhinandan Honale")
    adv_title = "Co-Founder"  # Hardcoded — always display as Co-Founder
    adv_bg = (
        "As a Co-Founder, <b>Abhinandan Honale</b> brings a unique combination of technical expertise, "
        "financial acumen, and institutional experience to <b>Samarth Wealth Pvt. Ltd.</b> After completing "
        "his <b>Engineering degree</b>, he pursued an <b>MBA in Finance</b> and further strengthened "
        "his credentials by earning the globally recognized <b>Financial Risk Manager (FRM)</b> "
        "certification from the <b>Global Association of Risk Professionals (GARP), USA</b>. His "
        "strong academic foundation enables him to approach wealth management with a "
        "disciplined, analytical, and risk-conscious mindset."
    )
    adv_p2 = (
        "Prior to co-founding <b>Samarth Wealth Pvt. Ltd.</b>, Abhinandan gained valuable experience at "
        "leading financial institutions, including <b>ICICI Bank Wealth Management</b> and "
        "<b>Deutsche Bank Investment Banking</b>. These roles provided him with deep exposure to "
        "<b>portfolio management</b>, financial markets, <b>risk assessment</b>, and "
        "<b>investment strategy</b>. Leveraging this institutional background, he helps clients "
        "navigate complex market environments by focusing not only on wealth creation but "
        "also on <b>capital preservation</b>. His expertise in <b>risk management</b> ensures that "
        "client portfolios are designed to withstand market volatility and global macroeconomic "
        "uncertainties while remaining aligned with <b>long-term financial goals</b>. Under his "
        "leadership, <b>Samarth Wealth Pvt. Ltd.</b> combines <b>institutional-grade investment discipline</b> "
        "with a client-centric approach, helping investors build resilient and sustainable "
        "wealth across market cycles."
    )
    
    adv2_name = "Pranjal Wagh"
    adv2_title = "Co-Founder"  # Hardcoded — always display as Co-Founder
    adv2_bg = (
        "As a Co-Founder, <b>Pranjal Wagh</b> brings over <b>16 years of extensive experience</b> "
        "in the financial services industry, with expertise spanning <b>wealth management</b>, "
        "<b>financial goal planning</b>, <b>client relationship management</b>, and "
        "<b>business strategy</b>. Following his <b>MBA in Marketing</b> from <b>N. L. Dalmia "
        "Institute of Management Studies & Research</b>, he further strengthened his "
        "professional credentials by becoming a <b>Certified Advanced Financial Goal Planner</b> "
        "and completing the <b>Business Strategy Excellence Program</b> from <b>IIM Udaipur</b>. "
        "His strong academic foundation, combined with years of hands-on industry "
        "experience, enables him to understand the evolving financial needs of "
        "individuals and families across different stages of wealth creation and preservation."
    )
    adv2_p2 = (
        "His professional journey includes formative years at <b>HDFC Bank</b>, where he honed "
        "his skills in team leadership, <b>client acquisition</b>, <b>relationship management</b>, "
        "and delivering customized <b>financial solutions</b>. Over the years, he has built a "
        "reputation for creating practical, client-centric wealth strategies that balance growth "
        "opportunities with long-term financial security. His ability to simplify complex "
        "financial concepts and align investment decisions with client objectives has been "
        "instrumental in helping investors achieve sustainable wealth creation and lasting "
        "financial success."
    )

    
    founder1_img_path = os.path.join(current_dir, "founder.jpeg")
    if not os.path.exists(founder1_img_path):
        founder1_img_path = os.path.join(current_dir, "founder.jpg")
    if not os.path.exists(founder1_img_path):
        founder1_img_path = os.path.join(current_dir, "extracted_img_p2_2_150.jpeg")
    if not os.path.exists(founder1_img_path):
        if os.path.exists("founder.jpeg"):
            founder1_img_path = "founder.jpeg"
        elif os.path.exists("founder.jpg"):
            founder1_img_path = "founder.jpg"
        elif os.path.exists("extracted_img_p2_2_150.jpeg"):
            founder1_img_path = "extracted_img_p2_2_150.jpeg"

    if not os.path.exists(founder1_img_path):
        f1_img = make_image_placeholder(adv_name, width=230, height=130)
    else:
        founder1_img = Image(founder1_img_path, width=230, height=130)
        f1_img = Table([[founder1_img]], colWidths=[230], hAlign='LEFT')
        f1_img.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.75, GOLD),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

    founder2_img_path = os.path.join(current_dir, "founder_2.jpg")
    if not os.path.exists(founder2_img_path):
        if os.path.exists("founder_2.jpg"):
            founder2_img_path = "founder_2.jpg"

    if not os.path.exists(founder2_img_path):
        f2_img = make_image_placeholder(adv2_name, width=230, height=130)
    else:
        founder2_img = Image(founder2_img_path, width=230, height=130)
        f2_img = Table([[founder2_img]], colWidths=[230], hAlign='LEFT')
        f2_img.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.75, GOLD),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

    founder1_top = [
        f1_img,
        Spacer(1, 5),
        Paragraph("FOUNDER PROFILE", header_style_lbl),
        Spacer(1, 5),
        Paragraph(adv_name, P2_FOUNDER_NAME),
        Spacer(1, 4),
        make_gold_bar(54, 3.6),
        Spacer(1, 5),
        Paragraph(adv_title.replace("&", "&amp;"), P2_FOUNDER_TITLE),
        Spacer(1, 5),
    ]
    
    founder2_top = [
        f2_img,
        Spacer(1, 5),
        Paragraph("FOUNDER PROFILE", header_style_lbl),
        Spacer(1, 5),
        Paragraph(adv2_name, P2_FOUNDER_NAME),
        Spacer(1, 4),
        make_gold_bar(54, 3.6),
        Spacer(1, 5),
        Paragraph(adv2_title.replace("&", "&amp;"), P2_FOUNDER_TITLE),
        Spacer(1, 5),
    ]
    
    bio1_flow = [
        Paragraph(adv_bg, P2_BIO_BODY),
        Spacer(1, 2),
        Paragraph(adv_p2, P2_BIO_BODY)
    ]
    
    bio2_flow = [
        Paragraph(adv2_bg, P2_BIO_BODY),
        Spacer(1, 2),
        Paragraph(adv2_p2, P2_BIO_BODY)
    ]
    
    col_w = (739.89 - 20) / 2
    table_content = [
        [founder1_top, "", founder2_top],
        [bio1_flow, "", bio2_flow]
    ]
    bottom_table = Table(table_content, colWidths=[col_w, 20, col_w], hAlign='LEFT')
    bottom_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    
    # Debug print
    _, h_bot_dbg = bottom_table.wrap(817.89, 600)
    print(f"[DEBUG] Actual Bottom Table wrapped height: {h_bot_dbg}", flush=True)
    
    story.append(bottom_table)

    # ─────────────────────────────────────────────────────────────────────────
    # Page 3: Investment Proposal Summary
    # ─────────────────────────────────────────────────────────────────────────
    story.append(NextPageTemplate('Later'))
    story.append(PageBreak())
    
    # Page 3 Top Header
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_img_path = os.path.join(current_dir, "extracted_img_p2_1_147.jpeg")
    if not os.path.exists(logo_img_path):
        if os.path.exists("extracted_img_p2_1_147.jpeg"):
            logo_img_path = "extracted_img_p2_1_147.jpeg"

    if os.path.exists(logo_img_path):
        p3_logo = Image(logo_img_path, width=100.8, height=63)
    else:
        p3_logo = make_image_placeholder("Samarth Wealth", width=100.8, height=63)

    header_left = [
        p3_logo,
        Spacer(1, 6),
        Paragraph("INVESTMENT PROPOSAL SUMMARY", style("P3H1", fontName=FONT_SANS_BOLD, fontSize=9.5, leading=12, textColor=GOLD)),
        Paragraph(client_name, style("P3H2", fontName=FONT_SERIF_BOLD, fontSize=24, leading=28, textColor=NAVY))
    ]

    # Founder signature block removed from top-right per requirement
    header_right = [
        Spacer(1, 8)
    ]

    header_table = Table([[header_left, header_right]], colWidths=[W_net * 0.65, W_net * 0.35], hAlign='LEFT')
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceBefore=2, spaceAfter=6))
    
    # Dashboard layout: Pie on left, details on right (Tightened & Proportional)
    donut_draw = make_dashboard_donut(allocs, client.get("Portfolio Corpus (INR)", "10,00,00,000"), size=160)
    legend_table = make_dashboard_legend_table(allocs)
    
    right_dashboard = [
        Paragraph("Asset Allocation Dashboard", style("P3DashTitle", fontName=FONT_SERIF_BOLD, fontSize=14, leading=17, textColor=NAVY)),
        Spacer(1, 4),
        legend_table
    ]
    
    dash_table = Table([[donut_draw, right_dashboard]], colWidths=[160, W_net - 160], hAlign='LEFT')
    dash_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(dash_table)
    
    # ── Narrative briefing card/panel at bottom (Tightly structured, reduces white space) ──
    story.append(Spacer(1, 8))
    
    exec_summary_text = data.get("executive_summary", "")
    thesis_text = data.get("portfolio_thesis", "")
    
    summary_style = ParagraphStyle(
        "SummaryText",
        parent=BODY,
        fontSize=10.5,
        leading=14.5,
        textColor=DARK_GREY,
        spaceAfter=0
    )
    title_style = ParagraphStyle(
        "SummaryTitle",
        parent=TITLE_SMALL,
        fontSize=11.5,
        leading=14,
        textColor=NAVY,
        fontName=FONT_SERIF_BOLD,
        spaceAfter=2
    )
    
    col1_content = [
        Paragraph("EXECUTIVE BRIEFING", title_style),
        make_gold_bar(30, 1.5),
        Spacer(1, 3),
        Paragraph(exec_summary_text, summary_style)
    ]
    col2_content = [
        Paragraph("PORTFOLIO THESIS & MARKET OVERVIEW", title_style),
        make_gold_bar(30, 1.5),
        Spacer(1, 3),
        Paragraph(thesis_text, summary_style)
    ]
    
    summary_table = Table([[col1_content, col2_content]], colWidths=[W_net * 0.50, W_net * 0.50], hAlign='CENTER')
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAF9F5")), # Very light cream background card
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), # Slate-300 border
        ("LINEBEFORE", (1, 0), (1, -1), 0.5, colors.HexColor("#E2E8F0")), # Inner column divider line
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(summary_table)

    # ─────────────────────────────────────────────────────────────────────────
    # Page 4: Detailed Recommendation Summary (Merged Table, flows naturally)
    # ─────────────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Detailed Recommendation Summary", TITLE_LARGE))
    story.append(Spacer(1, 5))
    
    headers = [
        Paragraph("SEGMENT / RECOMMENDED PRODUCT", TABLE_HEADER_LEFT),
        Paragraph("ALLOCATION", TABLE_HEADER_CENTER),
        Paragraph("TARGET RETURN", TABLE_HEADER_CENTER),
        Paragraph("CORE RATIONALE", TABLE_HEADER_LEFT)
    ]
    
    # Calculate row count to adjust styles dynamically (headers + products + segments + grand total)
    total_table_rows = 2
    for pt in [1, 2, 3, 4]:
        if len(parts_data[pt]) > 0:
            total_table_rows += 1 + len(parts_data[pt])
            
    padding, fs, lead = get_table_padding_and_fontsize(total_table_rows)
    
    style_cell = ParagraphStyle("TableCellSummary", parent=TABLE_CELL, fontSize=fs, leading=lead)
    style_cell_bold = ParagraphStyle("TableCellBoldSummary", parent=TABLE_CELL_BOLD, fontSize=fs, leading=lead)
    style_cell_center = ParagraphStyle("TableCellCenterSummary", parent=TABLE_CELL_CENTER, fontSize=fs, leading=lead)
    style_cell_center_bold = ParagraphStyle("TableCellCenterBoldSummary", parent=TABLE_CELL_CENTER_BOLD, fontSize=fs, leading=lead)
    style_cell_amount = ParagraphStyle("TableCellAmountSummary", parent=TABLE_CELL_AMOUNT, fontSize=fs, leading=lead)
    
    style_segment_header = ParagraphStyle("SegmentHeaderSummary", parent=TABLE_CELL_BOLD, fontSize=fs + 1.0, leading=lead + 1.5, textColor=NAVY)
    
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, GOLD), # Top bounding gold border
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, GOLD), # Gold divider line
        ('TOPPADDING', (0, 1), (-1, -1), padding + 1.5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), padding + 1.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    
    table_rows = [headers]
    row_idx = 1
    
    active_parts = sorted(list(parts_data.keys()))
    
    segment_titles = {}
    for pt_num in active_parts:
        a = next((x for x in allocs if int(x.get("Part", 0)) == pt_num), None)
        if a and a.get("Segment Name"):
            seg_name = str(a.get("Segment Name")).upper()
            sub_val = str(a.get("AMFI_Subtitle", ""))
            if sub_val:
                seg_name_formatted = f"{seg_name}<br/><font size='7.5' color='#9A6A00'><b>{sub_val.upper()}</b></font>"
            else:
                seg_name_formatted = seg_name
        else:
            seg_name_formatted = f"CATEGORY {pt_num}"
        segment_titles[pt_num] = f"{get_roman_numeral(pt_num)}. {seg_name_formatted}"
    
    for pt in active_parts:
        pt_products = parts_data[pt]
        if len(pt_products) > 0:
            pt_alloc = part_allocations[pt]
            table_rows.append([
                Paragraph(f"<b>{segment_titles[pt]} &nbsp;&nbsp;|&nbsp;&nbsp; <font color='#9A6A00'>{format_rupee_words(pt_alloc)}</font></b>", style_segment_header),
                "", "", ""
            ])
            t_style.append(('SPAN', (0, row_idx), (-1, row_idx)))
            t_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), BG_BEIGE))
            t_style.append(('LINEBELOW', (0, row_idx), (-1, row_idx), 1.0, GOLD)) # Gold accent line below segment header
            row_idx += 1
            
            for p in pt_products:
                amt_val = clean_float(p.get("Allocation (INR)", "0"))
                amt_str = f'<font name="DejaVuSans-Bold">₹</font> {amt_val:,.0f}' if amt_val > 0 else "—"
                
                # Wrap target return in green badge
                tr_badge = make_target_return_badge(p.get("Target Return", ""), fs)
                
                table_rows.append([
                    Paragraph(p.get("Product Name", ""), style_cell_bold),
                    Paragraph(amt_str, style_cell_amount), # Dark navy bold amount
                    tr_badge,
                    Paragraph(p.get("summary_rationale") or p.get("Why Selected") or p.get("Core Rationale") or "", style_cell)
                ])
                t_style.append(('LINEBELOW', (0, row_idx), (-1, row_idx), 0.5, colors.HexColor("#CBD5E1")))
                row_idx += 1
                
    # Add Grand Total row at the end of Detailed Recommendation Summary
    total_amt_str = format_rupee_words(total_alloc_val)
    style_total_label = ParagraphStyle("TotalLabelSummary", parent=TABLE_CELL_BOLD, fontSize=fs + 0.5, leading=lead + 1.0, textColor=NAVY)
    style_total_amount = ParagraphStyle("TotalAmountSummary", parent=TABLE_CELL_AMOUNT, fontSize=fs + 1.0, leading=lead + 1.5, textColor=DARK_NAVY)
    
    table_rows.append([
        Paragraph("<b>TOTAL RECOMMENDED PORTFOLIO</b>", style_total_label),
        Paragraph(total_amt_str, style_total_amount),
        Paragraph("—", style_cell_center_bold),
        Paragraph("", style_cell)
    ])
    t_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor("#FAF9F5")))
    t_style.append(('LINEABOVE', (0, row_idx), (-1, row_idx), 1.0, NAVY)) # separating dark line
    t_style.append(('LINEBELOW', (0, row_idx), (-1, row_idx), 1.5, GOLD)) # Bounding gold border at table bottom
    t_style.append(('VALIGN', (0, row_idx), (-1, row_idx), 'MIDDLE'))
    t_style.append(('TOPPADDING', (0, row_idx), (-1, row_idx), 6))
    t_style.append(('BOTTOMPADDING', (0, row_idx), (-1, row_idx), 6))
    row_idx += 1
    
    t_summary = Table(table_rows, colWidths=[W_net * 0.30, W_net * 0.15, W_net * 0.13, W_net * 0.42], hAlign='LEFT', repeatRows=1)
    t_summary.setStyle(TableStyle(t_style))
    story.append(t_summary)

    # ─────────────────────────────────────────────────────────────────────────
    # Dynamic Category-wise Detail Pages
    # ─────────────────────────────────────────────────────────────────────────
    for pt in active_parts:
        pt_products = parts_data[pt]
        if len(pt_products) == 0:
            continue
            
        story.append(PageBreak())
        
        # Get category details
        a = next((x for x in allocs if int(x.get("Part", 0)) == pt), {})
        p_name = a.get("Segment Name") or "Category Details"
        p_sub = a.get("AMFI_Subtitle") or ""
        p_obj = a.get("Objective") or ""
        pt_alloc = part_allocations[pt]
        
        # Format the title with the subtitle
        if p_sub:
            p_title_formatted = f"{p_name}<br/><font size='10' color='#9A6A00'><b>{p_sub}</b></font>"
        else:
            p_title_formatted = p_name
            
        left_flow = [
            Paragraph(f"PART {pt}", style(f"PartGold_{pt}", fontName=FONT_SANS_BOLD, fontSize=9, leading=11, textColor=GOLD)),
            Spacer(1, 2),
            Paragraph(p_title_formatted, style(f"PartTitle_{pt}", fontName=FONT_SERIF_BOLD, fontSize=20, leading=24, textColor=NAVY)),
            Spacer(1, 4),
            make_gold_bar(54, 3)
        ]
        right_flow = [
            Spacer(1, 8),
            Paragraph(format_rupee_words(pt_alloc), style(f"PartAlloc_{pt}", fontName=FONT_SERIF_BOLD, fontSize=18, leading=22, textColor=GOLD, alignment=2))
        ]
        header_table = Table([[left_flow, right_flow]], colWidths=[W_net - 260, 260], hAlign='LEFT')
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 10))
        
        story.append(Paragraph(f"<b>Objective:</b> {p_obj}", BODY))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceBefore=4, spaceAfter=10))
        
        # Separate products into PMS vs Mutual Funds
        pms_products = []
        mf_products = []
        for p in pt_products:
            ac = str(p.get("Asset Class", "")).lower()
            pn = str(p.get("Product Name", "")).lower()
            is_pms = (
                "pms" in ac or "pms" in pn or 
                "portfolio management" in ac or "portfolio management" in pn or 
                "p.m.s" in ac or "p.m.s" in pn or
                any(kw in pn for kw in ["buoyant", "rising stars", "valuequest", "ask growth", "marcellus"])
            )
            if is_pms:
                pms_products.append(p)
            else:
                mf_products.append(p)
                
        # Render PMS cards if any exist
        if len(pms_products) > 0:
            pms_alloc_sum = sum(clean_float(p.get("Allocation (INR)", "0")) for p in pms_products)
            pms_alloc_str = format_rupee_words(pms_alloc_sum).replace("Rupees ", "")
            pms_alloc_str = pms_alloc_str.replace('<font name="DejaVuSans-Bold">₹</font> ', '')
            pms_alloc_str = pms_alloc_str.replace('₹ ', '').replace('Rs. ', '')
            
            story.append(Paragraph(f"Portfolio Management Services (PMS) - <font name=\"DejaVuSans-Bold\">₹</font> {pms_alloc_str}", TITLE_SMALL))
            story.append(Spacer(1, 5))
            
            card_tables = []
            for i, p in enumerate(pms_products):
                amt_val = clean_float(p.get("Allocation (INR)", "0"))
                amt_words = format_rupee_words(amt_val)
                
                pms_title_style = ParagraphStyle(
                    f"PmsCardTitle_{pt}_{i}",
                    fontName=FONT_SANS_BOLD,
                    fontSize=9.5,
                    leading=13,
                    textColor=DARK_NAVY
                )
                
                pms_alloc_style = ParagraphStyle(
                    f"PmsCardAlloc_{pt}_{i}",
                    fontName=FONT_SANS_BOLD,
                    fontSize=8.5,
                    leading=11,
                    textColor=DARK_NAVY
                )
                
                pms_tr = p.get('Target Return', '')
                if pms_tr:
                    pms_alloc_text = f"<b>Allocation: {amt_words}</b>&nbsp;&nbsp;|&nbsp;&nbsp;<font color='#0A2540'><b>Exp. Return: {pms_tr}</b></font>"
                else:
                    pms_alloc_text = f"<b>Allocation: {amt_words}</b>"
                
                card_content = [
                    Paragraph(f"<b>{p.get('Product Name', '')}</b>", pms_title_style),
                    Spacer(1, 4),
                    Paragraph(pms_alloc_text, pms_alloc_style),
                    Spacer(1, 6),
                    Paragraph(p.get("detailed_rationale") or p.get("Why Selected") or p.get("Core Rationale") or "", BODY)
                ]
                
                border_color = NAVY if (i % 2 == 0) else GOLD
                bg_color = colors.HexColor("#F0F4F8") if (i % 2 == 0) else colors.HexColor("#FAF7F0")
                
                t_card = Table([[card_content]], colWidths=[W_net * 0.48])
                t_card.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                    ('BOX', (0, 0), (-1, -1), 1.5, border_color),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
                card_tables.append(t_card)
                
            if len(card_tables) >= 2:
                for idx_card in range(0, len(card_tables), 2):
                    if idx_card + 1 < len(card_tables):
                        pair_table = Table([[card_tables[idx_card], "", card_tables[idx_card+1]]], colWidths=[W_net * 0.48, W_net * 0.04, W_net * 0.48], hAlign='LEFT')
                        pair_table.setStyle(TableStyle([
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 0),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                        ]))
                        story.append(pair_table)
                        story.append(Spacer(1, 10))
                    else:
                        story.append(card_tables[idx_card])
                        story.append(Spacer(1, 10))
            elif len(card_tables) == 1:
                story.append(card_tables[0])
                story.append(Spacer(1, 10))
                
            story.append(Spacer(1, 15))
            
        # Render Mutual Funds if any exist
        if len(mf_products) > 0:
            mf_alloc_sum = sum(clean_float(p.get("Allocation (INR)", "0")) for p in mf_products)
            mf_alloc_str = format_rupee_words(mf_alloc_sum).replace("Rupees ", "")
            mf_alloc_str = mf_alloc_str.replace('<font name="DejaVuSans-Bold">₹</font> ', '')
            mf_alloc_str = mf_alloc_str.replace('₹ ', '').replace('Rs. ', '')
            
            if len(pms_products) > 0:
                story.append(Paragraph(f"Mutual Funds - <font name=\"DejaVuSans-Bold\">₹</font> {mf_alloc_str}", TITLE_SMALL))
                story.append(Spacer(1, 5))
                
            mf_cols = [
                Paragraph("RECOMMENDED PRODUCT", style_hdr_left),
                Paragraph("STRATEGY & RATIONALE", style_hdr_left),
                Paragraph("ALLOCATION", style_hdr_center)
            ]
            mf_table_rows = [mf_cols]
            
            mf_total_rows = len(mf_products) + 2
            padding_mf, fs_mf, lead_mf = get_table_padding_and_fontsize(mf_total_rows)
            
            style_mf = ParagraphStyle(f"TableCellMF_{pt}", parent=TABLE_CELL, fontSize=fs_mf, leading=lead_mf)
            style_mf_bold = ParagraphStyle(f"TableCellBoldMF_{pt}", parent=TABLE_CELL_BOLD, fontSize=fs_mf, leading=lead_mf)
            style_mf_amount = ParagraphStyle(f"TableCellAmountMF_{pt}", parent=TABLE_CELL_AMOUNT, fontSize=fs_mf, leading=lead_mf)
            
            for p in mf_products:
                amt_val = clean_float(p.get("Allocation (INR)", "0"))
                amt_words = format_rupee_words(amt_val) if amt_val > 0 else p.get("Allocation (INR)", "")
                    
                p_cell = [
                    Paragraph(f"<b>{p.get('Product Name', '')}</b>", style_mf_bold)
                ]
                asset_class_str = p.get("Asset Class", "")
                tr_val = p.get("Target Return", "")
                if tr_val:
                    irr_label = "Net IRR" if "debt" in p_name.lower() or "liquid" in p_name.lower() or "corporate bond" in p_name.lower() or "arbitrage" in p_name.lower() else "Exp. Return"
                    p_cell.append(Paragraph(f"<font color='#0A2540'><b>{asset_class_str} &nbsp;|&nbsp; {irr_label}: {tr_val}</b></font>", style_mf_bold))
                else:
                    p_cell.append(Paragraph(f"<font color='#0A2540'><b>{asset_class_str}</b></font>", style_mf_bold))
                
                mf_table_rows.append([
                    p_cell,
                    Paragraph(p.get("detailed_rationale") or p.get("Why Selected") or p.get("Core Rationale") or "", style_mf),
                    Paragraph(amt_words, style_mf_amount)
                ])
                
            mf_table_rows.append([
                Paragraph("<b>TOTAL SECTION ALLOCATION</b>", style_mf_bold),
                Paragraph("", style_mf),
                Paragraph(format_rupee_words(mf_alloc_sum), style_mf_amount)
            ])
            
            mf_table = Table(mf_table_rows, colWidths=[W_net * 0.27, W_net * 0.57, W_net * 0.16], hAlign='LEFT', repeatRows=1)
            mf_table_style = [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("LINEABOVE", (0, 0), (-1, 0), 1.5, GOLD),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, GOLD),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("LINEBELOW", (0, -1), (-1, -1), 1.5, GOLD),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 1), (-1, -1), padding_mf + 2),
                ("BOTTOMPADDING", (0, 1), (-1, -1), padding_mf + 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
            if len(mf_table_rows) > 2:
                mf_table_style.extend([
                    ("LINEABOVE", (0, -1), (-1, -1), 1.0, NAVY),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FAF9F5")),
                    ("VALIGN", (0, -1), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, -1), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
                ])
            mf_table.setStyle(TableStyle(mf_table_style))
            story.append(mf_table)
            
        if "arbitrage" in p_name.lower() or "hybrid" in p_name.lower():
            story.append(Spacer(1, 8))
            swp_txt = "<b>Income Generation via SWP:</b> A Regular Income (Monthly/Quarterly) can be created via Systematic Withdrawal Plans (SWP) from hybrid/arbitrage funds."
            story.append(Paragraph(swp_txt, BODY_BOLD))
            
        # Append contact block if it's the last active section
        if pt == last_active_part:
            append_contact_block(story, firm, tagline, firm_name_raw)


    # ─────────────────────────────────────────────────────────────────────────
    # Page 11: Regulatory Disclosures
    # ─────────────────────────────────────────────────────────────────────────
    story.append(PageBreak())
    
    arn = firm.get("AMFI ARN", "ARN-286847")
    discl_text = (
        f"<b>SAMARTH WEALTH PVT. LTD.</b> is an AMFI-registered Mutual Fund & Specialized Investment "
        f"Fund Distributor ({arn}). All Mutual Funds, SIF, AIF, and PMS investments are subject to market "
        f"risks. Please read all scheme-related documents carefully before investing. Past performance "
        f"is not indicative of future results. Insurance is the subject matter of solicitation. For more details on "
        f"risk factors, terms, and conditions, please read the sales brochure carefully before investing. Any target "
        f"IRRs mentioned are based on fund manager projections and market conditions as of March/April 2026 and "
        f"are not guaranteed."
    )
    
    disc_content = [
        Paragraph("REGULATORY DISCLOSURES:", style("DisHeaderWhite", fontName=FONT_SERIF_BOLD, fontSize=11, leading=14, textColor=GOLD)),
        Spacer(1, 4),
        Paragraph(discl_text, style("DisclaimerWhite", fontName=FONT_SANS, fontSize=9, leading=13.5, textColor=colors.white))
    ]
    
    disc_table = Table([[disc_content]], colWidths=[W_net])
    disc_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 15),
        ("RIGHTPADDING", (0, 0), (-1, -1), 15),
        ("BOX", (0, 0), (-1, -1), 1.5, GOLD),
    ]))
    story.append(disc_table)
    
    story.append(Spacer(1, 20))
    copy_style = style("DisCopy", fontName=FONT_SANS, fontSize=8.5, leading=11, textColor=DARK_GREY)
    story.append(Paragraph(f"© {datetime.now().year} {firm_name_raw.rstrip('.')}. All Rights Reserved.", copy_style))

    # Build the document
    doc.build(story, onFirstPage=draw_cover_bg, onLaterPages=draw_later_bg)

    if return_bytes:
        target.seek(0)
        return target.getvalue(), filename
    else:
        return target
