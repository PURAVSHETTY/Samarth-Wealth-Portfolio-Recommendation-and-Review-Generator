import os
import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, PageTemplate, Frame, NextPageTemplate, Image
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
from reportlab.graphics.charts.piecharts import Pie

# Register TrueType fonts to support the Indian Rupee symbol (₹)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

# Workspace paths
current_dir = os.path.dirname(os.path.abspath(__file__))

# Font mapping registration safety wrappers
try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
    FONT_SANS = "Arial"
    FONT_SANS_BOLD = "Arial-Bold"
except Exception:
    FONT_SANS = "Helvetica"
    FONT_SANS_BOLD = "Helvetica-Bold"

try:
    pdfmetrics.registerFont(TTFont('TimesNewRoman', 'times.ttf'))
    pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', 'timesbd.ttf'))
    FONT_SERIF = "TimesNewRoman"
    FONT_SERIF_BOLD = "TimesNewRoman-Bold"
except Exception:
    FONT_SERIF = "Times-Roman"
    FONT_SERIF_BOLD = "Times-Bold"

try:
    # Check parent directory as fallback if current_dir is codebase/
    def find_font(name):
        p1 = os.path.join(current_dir, name)
        if os.path.exists(p1):
            return p1
        p2 = os.path.join(os.path.dirname(current_dir), name)
        if os.path.exists(p2):
            return p2
        return name

    pdfmetrics.registerFont(TTFont('DejaVuSans', find_font('DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', find_font('DejaVuSans-Bold.ttf')))
    FONT_UNICODE_SANS = "DejaVuSans"
    FONT_UNICODE_SANS_BOLD = "DejaVuSans-Bold"
    
    pdfmetrics.registerFont(TTFont('DejaVuSerif', find_font('DejaVuSerif.ttf')))
    pdfmetrics.registerFont(TTFont('DejaVuSerif-Bold', find_font('DejaVuSerif-Bold.ttf')))
    FONT_UNICODE_SERIF = "DejaVuSerif"
    FONT_UNICODE_SERIF_BOLD = "DejaVuSerif-Bold"
except Exception:
    FONT_UNICODE_SANS = FONT_SANS
    FONT_UNICODE_SANS_BOLD = FONT_SANS_BOLD
    FONT_UNICODE_SERIF = FONT_SERIF
    FONT_UNICODE_SERIF_BOLD = FONT_SERIF_BOLD

# Mappings for bold/italic TrueType fonts to ensure <b> tags render correctly
try:
    addMapping('DejaVuSans', 0, 0, 'DejaVuSans')
    addMapping('DejaVuSans', 1, 0, 'DejaVuSans-Bold')
    addMapping('DejaVuSans', 0, 1, 'DejaVuSans')
    addMapping('DejaVuSans', 1, 1, 'DejaVuSans-Bold')
    
    addMapping('DejaVuSerif', 0, 0, 'DejaVuSerif')
    addMapping('DejaVuSerif', 1, 0, 'DejaVuSerif-Bold')
    addMapping('DejaVuSerif', 0, 1, 'DejaVuSerif')
    addMapping('DejaVuSerif', 1, 1, 'DejaVuSerif-Bold')
except Exception:
    pass

class RoundedTable(Table):
    def __init__(self, data, colWidths=None, rowHeights=None, style=None,
                 displayName=None, fillMode=0, repeatRows=0, repeatCols=0,
                 splitByRow=1, bg_color=colors.HexColor("#FAF9F5"), border_color=colors.HexColor("#E2E8F0"), rx=8, ry=8, shadow=True):
        Table.__init__(self, data, colWidths, rowHeights, style, displayName,
                       fillMode, repeatRows, repeatCols, splitByRow)
        self.bg_color = bg_color
        self.border_color = border_color
        self.rx = rx
        self.ry = ry
        self.shadow = shadow

    def draw(self):
        self.canv.saveState()
        if self.shadow:
            self.canv.setFillColor(colors.Color(0, 0, 0, 0.02))
            self.canv.roundRect(1.5, -1.5, self._width, self._height, self.rx, stroke=0, fill=1)
            self.canv.roundRect(0.7, -0.7, self._width, self._height, self.rx, stroke=0, fill=1)
        self.canv.setFillColor(self.bg_color)
        if self.border_color:
            self.canv.setStrokeColor(self.border_color)
            self.canv.setLineWidth(0.5)
            stroke_val = 1
        else:
            stroke_val = 0
        self.canv.roundRect(0, 0, self._width, self._height, self.rx, stroke=stroke_val, fill=1)
        self.canv.restoreState()
        Table.draw(self)

# Colour palette (Samarth Wealth Branding)
NAVY       = colors.HexColor("#0B3624")  # Deep Forest Green (Primary)
GOLD       = colors.HexColor("#9A6A00")  # Antique Gold (Accent)
WHITE      = colors.white
LIGHT_GREY = colors.HexColor("#FAF9F5")  # Cream background
MID_GREY   = colors.HexColor("#CBD5E1")  # Slate border
DARK_GREY  = colors.HexColor("#334155")  # Charcoal text

W, H = landscape(A4)  # 841.89 x 595.27 pt
W_net = W - 102       # 739.89 pt

# ── Formatting Helpers ───────────────────────────────────────────────────────
def clean_float(val):
    if val is None:
        return 0.0
    s = str(val).strip().replace(",", "").replace("₹", "").replace("%", "")
    if s == "" or s.lower() == "nan" or s == "—":
        return 0.0
    try:
        return float(s)
    except:
        return 0.0

def format_indian_number(val):
    try:
        val_float = float(val)
        is_negative = val_float < 0
        n = abs(int(round(val_float)))
        s = str(n)
        if len(s) <= 3:
            res = s
        else:
            last_three = s[-3:]
            remaining = s[:-3]
            groups = []
            while remaining:
                groups.append(remaining[-2:])
                remaining = remaining[:-2]
            groups.reverse()
            res = ",".join(groups) + "," + last_three
        return f"-{res}" if is_negative else res
    except Exception:
        return str(val)

def format_rupee_words(val):
    try:
        val_float = clean_float(val)
        if val_float >= 10000000:
            cr = val_float / 10000000
            if cr.is_integer():
                return f'<font name="DejaVuSans-Bold">₹</font> {int(cr)} Crores'
            else:
                return f'<font name="DejaVuSans-Bold">₹</font> {cr:.2f} Crores'
        elif val_float >= 100000:
            lakhs = val_float / 100000
            if lakhs.is_integer():
                return f'<font name="DejaVuSans-Bold">₹</font> {int(lakhs)} Lakhs'
            else:
                return f'<font name="DejaVuSans-Bold">₹</font> {lakhs:.2f} Lakhs'
        else:
            return f'<font name="DejaVuSans-Bold">₹</font> {format_indian_number(val_float)}'
    except Exception:
        return f'<font name="DejaVuSans-Bold">₹</font> {val}'

def format_short_amount(val):
    try:
        val_float = float(val)
        if val_float >= 10000000:
            return f"{val_float / 10000000:.2f} Cr"
        elif val_float >= 100000:
            return f"{val_float / 100000:.2f} L"
        else:
            return f"{val_float:,.0f}"
    except Exception:
        return str(val)

def format_rupees_no_dec(val):
    try:
        val_float = float(val)
        formatted = format_indian_number(val_float)
        if formatted.startswith("-"):
            return f"-₹&nbsp;{formatted[1:]}"
        else:
            return f"₹&nbsp;{formatted}"
    except Exception:
        return f"₹&nbsp;{val}"

def shorten_scheme_name(name):
    if not name:
        return ""
    s = str(name).strip()
    replacements = {
        "Aditya Birla SunLife": "ABSL",
        "Aditya Birla Sun Life": "ABSL",
        "Aditya Birla": "ABSL",
        "ICICI Prudential": "ICICI Pru",
        "ICICI Pru": "ICICI Pru",
        "Nippon India": "Nippon",
        "Franklin Templeton": "Franklin",
        "Mirae Asset": "Mirae",
        "DSP BlackRock": "DSP",
        "Motilal Oswal": "Motilal",
        "Kotak Mahindra": "Kotak",
        "SBI Mutual Fund": "SBI",
        "HDFC Mutual Fund": "HDFC",
        "Reliance Mutual Fund": "Reliance",
        
        "Regular Growth": "Reg-G",
        "Regular Plan-Growth": "Reg-G",
        "Regular Plan - Growth": "Reg-G",
        "Regular Plan": "Reg",
        "Regular": "Reg",
        "Growth Option": "G",
        "Growth": "G",
        "Direct Plan": "Dir",
        "Direct Growth": "Dir-G",
        "Direct": "Dir",
        
        "Balanced Advantage": "BAF",
        "Multi Asset Allocation": "Multi Asset",
        "Opportunities": "Opp",
        "Opportunity": "Opp",
        "Fund": "Fd",
    }
    import re
    for old, new in replacements.items():
        pattern = re.compile(re.escape(old), re.IGNORECASE)
        s = pattern.sub(new, s)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*-\s*', '-', s)
    return s.strip()

# ── Custom Graphic Drawings ─────────────────────────────────────────────────
def make_growth_chart(invested, current, width=320, height=185):
    d = Drawing(width, height)
    # Background card
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#FAF9F5"), strokeColor=MID_GREY, strokeWidth=0.5, rx=6, ry=6))
    
    # Title
    d.add(String(15, height - 18, "Portfolio Growth Summary", fontName=FONT_UNICODE_SANS_BOLD, fontSize=13.0, fillColor=NAVY))
    
    max_val = max(invested, current)
    scale = (height - 65) / max_val if max_val > 0 else 1.0
    
    h_inv = invested * scale
    h_cur = current * scale
    
    w_bar = 50
    gap = 40
    x_inv = width / 2 - w_bar - gap / 2
    x_cur = width / 2 + gap / 2
    
    y_base = 30
    
    # Gridlines
    for y_val in [0.25, 0.5, 0.75, 1.0]:
        y_pos = y_base + (height - 65) * y_val
        d.add(Line(20, y_pos, width - 20, y_pos, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5))
        
    # Bars
    d.add(Rect(x_inv, y_base, w_bar, h_inv, fillColor=colors.HexColor("#1E40AF"), strokeColor=None))
    d.add(Rect(x_cur, y_base, w_bar, h_cur, fillColor=colors.HexColor("#15803D"), strokeColor=None))
    
    # Value annotations
    d.add(String(x_inv + w_bar/2, y_base + h_inv + 5, f"₹ {format_short_amount(invested)}", textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=12.2, fillColor=colors.HexColor("#1E40AF")))
    d.add(String(x_cur + w_bar/2, y_base + h_cur + 5, f"₹ {format_short_amount(current)}", textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=12.2, fillColor=colors.HexColor("#15803D")))
    
    # Labels
    d.add(String(x_inv + w_bar/2, y_base - 14, "Invested Capital", textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=12.2, fillColor=colors.HexColor("#1E40AF")))
    d.add(String(x_cur + w_bar/2, y_base - 14, "Present Value", textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=12.2, fillColor=colors.HexColor("#15803D")))
    
    return d

def make_donut_chart(category_pcts, size=220, total_value=None, color_map=None):
    d = Drawing(size, size)
    d.add(Circle(size/2, size/2, size/2, fillColor=colors.white, strokeColor=None))
    
    pie = Pie()
    pie.x = size * 0.05
    pie.y = size * 0.05
    pie.width = size * 0.9
    pie.height = size * 0.9
    
    # Premium bright professional palette
    if color_map is None:
        color_map = {
            'Flexi Cap': colors.HexColor("#2563EB"),
            'Large Cap': colors.HexColor("#6B7280"),
            'Mid Cap': colors.HexColor("#3B82F6"),
            'Small Cap': colors.HexColor("#F97316"),
            'Hybrid': colors.HexColor("#10B981"),
            'Multi Asset': colors.HexColor("#14B8A6"),
            'ELSS': colors.HexColor("#F59E0B"),
            'Sector/Thematic': colors.HexColor("#8B5CF6"),
            'Debt': colors.HexColor("#6B7280"),
            'Others': colors.HexColor("#6B7280")
        }
    
    sorted_cats = sorted(category_pcts.items(), key=lambda x: x[1], reverse=True)
    data = []
    labels = []
    slice_colors = []
    for cat, pct in sorted_cats:
        if pct > 0:
            data.append(pct)
            labels.append(cat)
            slice_colors.append(color_map.get(cat, colors.HexColor("#6B7280")))
            
    if not data:
        data = [100]
        labels = ["No Assets"]
        pie.slices[0].fillColor = colors.HexColor("#E2E8F0")
    else:
        pie.data = data
        for i, color in enumerate(slice_colors):
            pie.slices[i].fillColor = color
            
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    pie.startAngle = 90
    pie.direction = "clockwise"
    # Increase donut thickness by 15% (fraction reduced from 0.72 to 0.68)
    pie.innerRadiusFraction = 0.68
    # Keep labels outside (do not assign labels to pie.labels, so no labels are drawn on the chart slices)
    pie.labels = None
    
    d.add(pie)
    
    # Center text
    cx, cy = size / 2, size / 2
    d.add(Circle(cx, cy, size * 0.32, fillColor=colors.white, strokeColor=None))
    
    d.add(String(cx, cy + 8, "TOTAL CORPUS", textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=7.5, fillColor=colors.HexColor("#64748B")))
    
    # Format total corpus value
    if total_value is not None:
        try:
            val_float = float(total_value)
            if val_float >= 10000000:
                corpus_str = f"₹ {val_float / 10000000:.2f} Crores"
            elif val_float >= 100000:
                corpus_str = f"₹ {val_float / 100000:.2f} Lakhs"
            else:
                corpus_str = f"₹ {val_float:,.0f}"
        except Exception:
            corpus_str = f"₹ {total_value}"
    else:
        corpus_str = "₹ 83.59 Lakhs"
        
    d.add(String(cx, cy - 6, corpus_str, textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=9.5, fillColor=NAVY))
    return d

def make_comparison_bar_chart(variance, width=200, height=140):
    d = Drawing(width, height)
    # Background
    d.add(Circle(width/2, height/2, min(width, height)/2, fillColor=colors.HexColor("#FAF9F5"), strokeColor=None))
    
    classes = ['Equity', 'Debt', 'Hybrid', 'Gold/Alts']
    class_keys = {
        'Equity': 'Equity',
        'Debt': 'Debt',
        'Hybrid': 'Hybrid',
        'Gold/Alts': 'Gold/Alternatives'
    }
    
    y_base = 20
    chart_h = height - 40 # 100 pt
    scale = chart_h / 100.0
    
    # Grid lines
    for val in [25, 50, 75, 100]:
        y_pos = y_base + val * scale
        d.add(Line(15, y_pos, width - 10, y_pos, strokeColor=MID_GREY, strokeWidth=0.5))
        
    w_bar = 10
    col_w = (width - 25) / 4.0
    
    # Legend
    d.add(Rect(25, height - 12, 8, 8, fillColor=NAVY, strokeColor=None))
    d.add(String(37, height - 12, "Current", fontName=FONT_UNICODE_SANS_BOLD, fontSize=6.5, fillColor=colors.HexColor("#475569")))
    d.add(Rect(80, height - 12, 8, 8, fillColor=GOLD, strokeColor=None))
    d.add(String(92, height - 12, "Target", fontName=FONT_UNICODE_SANS_BOLD, fontSize=6.5, fillColor=colors.HexColor("#475569")))
    
    for i, cls in enumerate(classes):
        key = class_keys[cls]
        v_data = variance.get(key, {})
        c_val = v_data.get('current_pct', 0.0)
        t_val = v_data.get('target_pct', 0.0)
        
        h_curr = max(1.0, c_val * scale)
        h_targ = max(1.0, t_val * scale)
        
        center_x = 15 + i * col_w + col_w / 2.0
        x_curr = center_x - w_bar - 1
        x_targ = center_x + 1
        
        # Draw Bars
        d.add(Rect(x_curr, y_base, w_bar, h_curr, fillColor=NAVY, strokeColor=None))
        d.add(Rect(x_targ, y_base, w_bar, h_targ, fillColor=GOLD, strokeColor=None))
        
        # Value annotations
        if c_val > 0:
            d.add(String(x_curr + w_bar/2, y_base + h_curr + 2, f"{int(c_val)}%", textAnchor="middle", fontName=FONT_UNICODE_SANS, fontSize=5.5, fillColor=NAVY))
        if t_val > 0:
            d.add(String(x_targ + w_bar/2, y_base + h_targ + 2, f"{int(t_val)}%", textAnchor="middle", fontName=FONT_UNICODE_SANS, fontSize=5.5, fillColor=GOLD))
            
        # Class Label
        d.add(String(center_x, y_base - 10, cls, textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=7.0, fillColor=colors.HexColor("#475569")))
        
    return d

def make_rank_badge(rank_num):
    d = Drawing(20, 20)
    d.add(Circle(10, 10, 9, fillColor=GOLD, strokeColor=None))
    d.add(String(10, 7, f"#{rank_num}", textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8, fillColor=WHITE))
    return d

def make_circular_gauge(score, size=90):
    d = Drawing(size, size)
    pie = Pie()
    pie.x = 0
    pie.y = 0
    pie.width = size
    pie.height = size
    
    # Slice 0 is the score, Slice 1 is the remainder
    pie.data = [score, max(0, 100 - score)]
    
    if score >= 80:
        color = colors.HexColor("#1E7E34") # Green
    elif score >= 50:
        color = colors.HexColor("#9A6A00") # Gold
    else:
        color = colors.HexColor("#BD2130") # Red
        
    pie.slices[0].fillColor = color
    pie.slices[1].fillColor = colors.HexColor("#E2E8F0")
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 0.5
    pie.startAngle = 90
    pie.direction = "clockwise"
    pie.innerRadiusFraction = 0.75
    d.add(pie)
    
    # Center score text
    cx, cy = size / 2, size / 2
    d.add(Circle(cx, cy, size * 0.32, fillColor=colors.HexColor("#FAF9F5"), strokeColor=None))
    d.add(String(cx, cy - 4, f"{score}", textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=13, fillColor=color))
    return d

def make_contributors_chart(holdings, width=320, height=185):
    d = Drawing(width, height)
    # Background card
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#FAF9F5"), strokeColor=MID_GREY, strokeWidth=0.5, rx=6, ry=6))
    
    # Title
    d.add(String(15, height - 18, "Top Contributors (Absolute Gains)", fontName=FONT_UNICODE_SANS_BOLD, fontSize=13.0, fillColor=NAVY))
    
    # Sort holdings by gain
    gains = []
    for h in holdings:
        gain = h["current_value_inr"] - h["purchase_cost_inr"]
        gains.append((h["product_name"], gain))
    gains.sort(key=lambda x: x[1], reverse=True)
    top_5 = gains[:5]
    
    if not top_5:
        return d
        
    max_gain = max(x[1] for x in top_5) if top_5 else 1.0
    scale = (width - 190.0) / max_gain if max_gain > 0 else 1.0
    
    y_base = height - 32
    y_gap = (height - 45) / 5.0 if len(top_5) > 0 else 20
    
    for idx, (name, val) in enumerate(top_5):
        short_name = shorten_scheme_name(name)
        if len(short_name) > 22:
            short_name = short_name[:20] + ".."
        w_bar = max(2, val * scale)
        y_pos = y_base - idx * y_gap
        
        BLUE_PALETTE = ["#1E3A8A", "#1D4ED8", "#2563EB", "#3B82F6", "#60A5FA"]
        bar_color = colors.HexColor(BLUE_PALETTE[idx % len(BLUE_PALETTE)])
        
        # Label left of bar
        d.add(String(15, y_pos + 4, short_name, fontName=FONT_UNICODE_SANS, fontSize=10.8, fillColor=DARK_GREY))
        # Draw bar
        d.add(Rect(140, y_pos - 4, w_bar, 10, fillColor=bar_color, strokeColor=None))
        # Value text next to bar
        d.add(String(140 + w_bar + 5, y_pos - 1, f"₹{format_short_amount(val)}", fontName=FONT_UNICODE_SANS_BOLD, fontSize=10.8, fillColor=colors.HexColor("#1E3A8A")))
        
    return d

def make_rebalancing_chart(variance_dict, width=320, height=185):
    d = Drawing(width, height)
    # Background card
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#FAF9F5"), strokeColor=MID_GREY, strokeWidth=0.5, rx=6, ry=6))
    
    # Title
    d.add(String(15, height - 18, "Asset Category Variance (Current vs Ideal)", fontName=FONT_UNICODE_SANS_BOLD, fontSize=9, fillColor=NAVY))
    
    cats = list(variance_dict.keys())[:5]  # top 5 categories
    if not cats:
        return d
        
    max_var = max(abs(clean_float(variance_dict[c].get("variance_pct", 0))) for c in cats) if cats else 1.0
    if max_var == 0:
        max_var = 1.0
    scale = 75.0 / max_var # max bar length 75pt
    
    cx = 160.0 # center line X
    y_base = height - 42
    y_gap = 26
    
    # Draw center line
    d.add(Line(cx, y_base + 10, cx, y_base - 5 * y_gap, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.75))
    
    for idx, cat in enumerate(cats):
        val = clean_float(variance_dict[cat].get("variance_pct", 0))
        w_bar = abs(val) * scale
        y_pos = y_base - idx * y_gap
        
        # Color: green if close to 0, gold if variance, red if high variance
        if abs(val) <= 2.5:
            color = colors.HexColor("#27AE60")
        elif val > 0:
            color = colors.HexColor("#9A6A00")
        else:
            color = colors.HexColor("#BD2130")
            
        if val >= 0:
            # Draw bar to the right
            d.add(Rect(cx, y_pos - 4, w_bar, 10, fillColor=color, strokeColor=None))
            # Value label
            d.add(String(cx + w_bar + 5, y_pos - 1, f"+{val:.1f}%", fontName=FONT_UNICODE_SANS_BOLD, fontSize=7.5, fillColor=color))
            # Category label
            d.add(String(cx - 5, y_pos - 1, cat, textAnchor="end", fontName=FONT_UNICODE_SANS, fontSize=7.5, fillColor=DARK_GREY))
        else:
            # Draw bar to the left
            d.add(Rect(cx - w_bar, y_pos - 4, w_bar, 10, fillColor=color, strokeColor=None))
            # Value label
            d.add(String(cx - w_bar - 25, y_pos - 1, f"{val:.1f}%", fontName=FONT_UNICODE_SANS_BOLD, fontSize=7.5, fillColor=color))
            # Category label
            d.add(String(cx + 5, y_pos - 1, cat, textAnchor="start", fontName=FONT_UNICODE_SANS, fontSize=7.5, fillColor=DARK_GREY))
            
    return d

def get_advisor_view(notes, xirr):
    notes_l = notes.lower()
    if "switch" in notes_l or "redeem" in notes_l or "sell" in notes_l or xirr < 8.0:
        return "Switch Recommended"
    elif "monitor" in notes_l or "attention" in notes_l or xirr < 10.0:
        return "Monitor Closely"
    elif "increase" in notes_l or "additional" in notes_l or "accumulate" in notes_l:
        return "Additional Allocation Opportunity"
    elif "core" in notes_l or "long-term" in notes_l:
        return "Core Long-Term Allocation"
    else:
        return "Continue Holding"

# ── Canvas Background Callbacks ─────────────────────────────────────────────
def _draw_spaced_text_on_canvas(c, text, font_name, font_size, fill_color, y, letter_gap, word_gap):
    """Draw text centred on the page with explicit per-character spacing."""
    total_w = 0.0
    for i, ch in enumerate(text):
        total_w += c.stringWidth(ch, font_name, font_size)
        if i < len(text) - 1:
            total_w += word_gap if ch == ' ' else letter_gap
    x = (W - total_w) / 2.0
    c.setFont(font_name, font_size)
    c.setFillColor(fill_color)
    for i, ch in enumerate(text):
        c.drawString(x, y, ch)
        x += c.stringWidth(ch, font_name, font_size)
        if i < len(text) - 1:
            x += word_gap if ch == ' ' else letter_gap

def draw_review_cover_bg(c, doc):
    """Draws background AND borders directly on the canvas."""
    c.saveState()
    # Solid Navy top 2/3
    c.setFillColor(NAVY)
    c.rect(0, 198.42, W, H - 198.42, fill=1, stroke=0)
    
    # Thin gold accent border inside the green area
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.rect(30, 198.42 + 30, W - 60, H - 198.42 - 50, fill=0, stroke=1)
    
    # White bottom 1/3
    c.setFillColor(WHITE)
    c.rect(0, 0, W, 198.42, fill=1, stroke=0)
    
    # Golden horizontal separator line
    c.setFillColor(GOLD)
    c.rect(0, 196.42, W, 4, fill=1, stroke=0)
    
    c.restoreState()

def draw_review_later_bg(canvas, doc):
    canvas.saveState()
    # Page background (Cream)
    canvas.setFillColor(LIGHT_GREY)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    
    page_num = canvas.getPageNumber()
    
    # Running header text
    canvas.setFillColor(NAVY)
    canvas.setFont(FONT_UNICODE_SANS_BOLD, 8.5)
    if page_num == 2:
        logo_path = os.path.join(current_dir, "extracted_img_p2_1_147.jpeg")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(os.path.dirname(current_dir), "extracted_img_p2_1_147.jpeg")
        if not os.path.exists(logo_path):
            logo_path = "extracted_img_p2_1_147.jpeg"
            
        if os.path.exists(logo_path):
            # Draw logo image: height=9pt, width=14.4pt (aspect ratio 1.6) to match text height
            canvas.drawImage(logo_path, 51, H - 25.5, width=14.4, height=9)
            canvas.drawString(51 + 14.4 + 4, H - 25, "SAMARTH WEALTH PVT. LTD.")
        else:
            canvas.drawString(51, H - 25, "SAMARTH WEALTH PVT. LTD.")
    else:
        canvas.drawString(51, H - 25, "SAMARTH WEALTH PVT. LTD.  |  PORTFOLIO REVIEW REPORT")
    
    # Top Gold divider
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.75)
    canvas.line(51, H - 30, W - 51, H - 30)
    
    # Bottom running line
    canvas.line(51, 35, W - 51, 35)
    
    # Footer content
    if page_num != 2:
        canvas.setFillColor(DARK_GREY)
        canvas.setFont(FONT_UNICODE_SANS, 7.5)
        canvas.drawString(51, 22, "CONFIDENTIAL  -  PREPARED FOR CLIENT REVIEW ONLY")
    
    canvas.setFillColor(GOLD)
    canvas.setFont(FONT_UNICODE_SANS_BOLD, 7.5)
    canvas.drawRightString(W - 51, 22, "Clients First. Always and Everytime")
    
    # Page number
    if page_num != 2:
        canvas.setFillColor(NAVY)
        canvas.setFont(FONT_UNICODE_SANS_BOLD, 8.0)
        canvas.drawRightString(W - 51, H - 25, f"PAGE {page_num}")
    canvas.restoreState()

# ── Custom Flowables / Drawings for Founder Profile ──────────────────────────
def make_image_placeholder(title_text, width=340, height=170):
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=NAVY, strokeColor=None))
    d.add(Rect(12, 12, width - 24, height - 24, fillColor=None, strokeColor=GOLD, strokeWidth=1))
    d.add(String(width / 2, height / 2 - 4, title_text.upper(), textAnchor="middle",
                 fontName=FONT_UNICODE_SERIF_BOLD, fontSize=14, fillColor=WHITE))
    return d

def make_gold_bar(width=54, height=3.6):
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=GOLD, strokeColor=None))
    return d

# ── Main Generator ──────────────────────────────────────────────────────────
def generate_review_pdf(review_context, output_path):
    print(f"[Review PDF Rebuild] Rendering 9-page landscape review PDF to: {output_path}")
    
    # Context variables
    client = review_context["client"]
    analytics = review_context["analytics"]
    holdings = review_context["holdings"]
    variance = analytics["allocation_variance"]
    health = analytics["health_score"]
    top_performers = analytics["top_performers"]
    attention_funds = analytics["attention_funds"]
    ai_narratives = review_context.get("ai_narratives", {})
    
    total_value = client["portfolio_value_inr"]
    total_cost = client["total_purchase_cost_inr"]
    total_gain = total_value - total_cost
    gain_pct = (total_gain / total_cost * 100.0) if total_cost > 0.0 else 0.0
    weighted_xirr = client["portfolio_xirr_pct"]
    tail_count = len([h for h in holdings if h.get('allocation_pct', 0.0) < 3.0])
    category_variance_dict = analytics["category_variance"]
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=51, rightMargin=51,
        topMargin=42, bottomMargin=42
    )
    
    # Custom PageTemplates
    cover_frame = Frame(
        51, 32,
        739.89, 531.27,
        id='CoverFrame',
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0
    )
    cover_template = PageTemplate(id='FirstPage', frames=cover_frame, onPage=draw_review_cover_bg)
    
    later_frame = Frame(51, 42, doc.width, doc.height, id='LaterFrame', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    later_template = PageTemplate(id='LaterPage', frames=later_frame, onPage=draw_review_later_bg)
    
    doc.addPageTemplates([cover_template, later_template])
    
    # Common styles
    styles = {
        "CoverTitle": ParagraphStyle("CoverTitle", fontName=FONT_SERIF_BOLD, fontSize=34, leading=40, textColor=WHITE, alignment=1),
        "CoverTagline": ParagraphStyle("CoverTagline", fontName=FONT_SANS_BOLD, fontSize=8.5, leading=11, textColor=colors.HexColor("#D4AF37"), alignment=1),
        "CoverClient": ParagraphStyle("CoverClient", fontName=FONT_SERIF_BOLD, fontSize=27, leading=32, textColor=NAVY, alignment=1),
        "CoverCorpus": ParagraphStyle("CoverCorpus", fontName=FONT_SERIF_BOLD, fontSize=16, leading=19, textColor=GOLD, alignment=1),
        "CoverPrep": ParagraphStyle("CoverPrep", fontName=FONT_UNICODE_SANS, fontSize=9.5, leading=14, textColor=DARK_GREY, alignment=1),
        "CoverSubText": ParagraphStyle("CoverSubText", fontName=FONT_SERIF_BOLD, fontSize=14, leading=17, textColor=WHITE, alignment=1),
        
        "Heading": ParagraphStyle("Heading", fontName=FONT_UNICODE_SERIF_BOLD, fontSize=22, leading=26, textColor=NAVY, spaceAfter=2),
        "SubHeading": ParagraphStyle("SubHeading", fontName=FONT_UNICODE_SERIF_BOLD, fontSize=12, leading=15, textColor=GOLD, spaceAfter=4),
        "Body": ParagraphStyle("Body", fontName=FONT_UNICODE_SANS, fontSize=9.5, leading=14, textColor=DARK_GREY, spaceAfter=4),
        "BodyBold": ParagraphStyle("BodyBold", fontName=FONT_UNICODE_SANS_BOLD, fontSize=9.5, leading=14, textColor=NAVY, spaceAfter=4),
        "BodySmall": ParagraphStyle("BodySmall", fontName=FONT_UNICODE_SANS, fontSize=8.2, leading=12, textColor=DARK_GREY),
        
        "TableHeader": ParagraphStyle("TableHeader", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.2, leading=11, textColor=WHITE, alignment=0),
        "TableHeaderCenter": ParagraphStyle("TableHeaderCenter", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.2, leading=11, textColor=WHITE, alignment=1),
        "TableCell": ParagraphStyle("TableCell", fontName=FONT_UNICODE_SANS, fontSize=8.0, leading=11, textColor=DARK_GREY),
        "TableCellBold": ParagraphStyle("TableCellBold", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.0, leading=11, textColor=NAVY),
        "TableCellCenter": ParagraphStyle("TableCellCenter", fontName=FONT_UNICODE_SANS, fontSize=8.0, leading=11, textColor=DARK_GREY, alignment=1),
        "TableCellCenterBold": ParagraphStyle("TableCellCenterBold", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.0, leading=11, textColor=NAVY, alignment=1),
        
        "TableHeaderRight": ParagraphStyle("TableHeaderRight", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.2, leading=11, textColor=WHITE, alignment=2),
        "TableCellRight": ParagraphStyle("TableCellRight", fontName=FONT_UNICODE_SANS, fontSize=8.0, leading=11, textColor=DARK_GREY, alignment=2),
        "TableCellRightBold": ParagraphStyle("TableCellRightBold", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.0, leading=11, textColor=NAVY, alignment=2),
        "Disclaimer": ParagraphStyle("Disclaimer", fontName=FONT_UNICODE_SANS, fontSize=8.8, leading=12.2, textColor=colors.HexColor("#000000"))
    }
    
    story = []
    
    # ── PAGE 1: COVER PAGE ──────────────────────────────────────────────────
    story.append(Spacer(1, 15))
    firm = review_context.get("firm", {})
    firm_name_raw = firm.get("Firm Name", "Samarth Wealth")
    clean_firm = firm_name_raw.replace("PVT.", "").replace("LTD.", "").replace("Pvt.", "").replace("Ltd.", "").strip().title()
    story.append(Paragraph(clean_firm, styles["CoverTitle"]))
    
    tagline = firm.get("Tagline", "Clients First. Always and Everytime.")
    tagline_spaced = "&nbsp;&nbsp;".join(list(tagline.upper()))
    story.append(Paragraph(f'"{tagline_spaced}"', styles["CoverTagline"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="20%", thickness=1.5, color=GOLD, spaceBefore=0, spaceAfter=0, hAlign='CENTER'))
    story.append(Spacer(1, 20))
    
    subtitle_text = "Portfolio Review Report"
    story.append(Paragraph(subtitle_text, styles["CoverSubText"]))
    story.append(Spacer(1, 12))
    
    client_name = client.get("client_name", "Valued Client")
    
    box_content = [
        [Spacer(1, 10)],
        [Paragraph(client_name, styles["CoverClient"])],
        [Spacer(1, 10)],
        [Paragraph(f"Current Portfolio Value: {format_rupee_words(total_value)}", styles["CoverCorpus"])],
        [Spacer(1, 10)]
    ]
    box_table = Table(box_content, colWidths=[460])
    box_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 1.5, GOLD),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(box_table)
    
    # Set to LaterPage template for subsequent slides
    story.append(NextPageTemplate("LaterPage"))
    
    # ── PAGE 2: EXECUTIVE SUMMARY & PORTFOLIO SNAPSHOT ─────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 6))

    # Premium colors specific to Page 2
    NAVY_BLUE   = NAVY
    ROYAL_BLUE  = GOLD
    LIGHT_GREY_BG = LIGHT_GREY
    BORDER_GREY = MID_GREY
    GOLD_ACCENT = GOLD
    SECTION_BG  = colors.HexColor("#F3ECE0")

    # Page 2 header
    p2_title_style = ParagraphStyle("P2Title", parent=styles["Heading"], fontSize=18, leading=21, textColor=NAVY_BLUE)
    story.append(Paragraph("Executive Summary & Portfolio Snapshot", p2_title_style))
    story.append(HRFlowable(width="100%", thickness=1.2, color=GOLD, spaceBefore=2, spaceAfter=8))

    # ── KPI values ──────────────────────────────────────────────────────────────
    invested_val = format_rupees_no_dec(total_cost)
    value_val    = format_rupees_no_dec(total_value)

    if total_gain >= 0:
        wealth_val   = f"+{format_rupees_no_dec(total_gain)}"
        wealth_color = colors.HexColor("#15803D")
        wealth_bar   = colors.HexColor("#10B981")
    else:
        wealth_val   = format_rupees_no_dec(total_gain)
        wealth_color = colors.HexColor("#B91C1C")
        wealth_bar   = colors.HexColor("#EF4444")

    xirr_val = f"{weighted_xirr:.2f}%"

    # Parse Health Score
    health_score_num = 0
    health_rating_str = "Balanced"
    if isinstance(health, dict):
        health_score_num  = health.get("total", 0)
        health_rating_str = health.get("rating", "Healthy").strip()
    else:
        try:
            health_score_num = int(health)
        except:
            health_score_num = 0
        health_rating_str = "Portfolio Health"

    health_rating_clean = health_rating_str.title()
    health_val = f"{health_score_num}/100"

    if health_score_num >= 85:
        health_bar_color = colors.HexColor("#0D9488")
        health_val_color = colors.HexColor("#0F766E")
    elif health_score_num >= 70:
        health_bar_color = colors.HexColor("#3B82F6")
        health_val_color = colors.HexColor("#1D4ED8")
    elif health_score_num >= 50:
        health_bar_color = colors.HexColor("#F59E0B")
        health_val_color = colors.HexColor("#B45309")
    else:
        health_bar_color = colors.HexColor("#EF4444")
        health_val_color = colors.HexColor("#B91C1C")

    # ── KPI Card builder (compact, single-row version) ──────────────────────────
    def make_kpi_card(label, value, subtext, width, val_color=colors.HexColor("#0F172A"),
                      bar_color=colors.HexColor("#1D4ED8")):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        
        lbl_style = ParagraphStyle(
            f"KL_{label[:6]}",
            fontName=FONT_UNICODE_SANS_BOLD,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=0
        )
        
        # Available width is width - 22 (from padding)
        avail_w = width - 22
        
        # Clean the string for measuring width
        val_clean = value.replace("&nbsp;", " ").replace("<font name=\"DejaVuSans-Bold\">", "").replace("</font>", "")
        
        # Determine the font size dynamically so it fits on one line
        fs = 20
        while fs > 8:
            w = stringWidth(val_clean, FONT_UNICODE_SANS_BOLD, fs)
            if w <= avail_w:
                break
            fs -= 1
            
        val_style = ParagraphStyle(
            f"KV_{label[:6]}",
            fontName=FONT_UNICODE_SANS_BOLD,
            fontSize=fs,
            leading=fs + 2,
            textColor=val_color
        )
        sub_style = ParagraphStyle(
            f"KS_{label[:6]}",
            fontName=FONT_UNICODE_SANS,
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#94A3B8")
        )
        
        lbl_p = Paragraph(label.upper(), lbl_style)
        val_p = Paragraph(value, val_style)
        sub_p = Paragraph(subtext, sub_style)
        
        # Inner table to stack texts with fixed row heights for horizontal alignment
        card_table = Table([
            [lbl_p],
            [val_p],
            [sub_p]
        ], colWidths=[avail_w], rowHeights=[12, 26, 10])
        card_table.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("ALIGN",         (0,0),(-1,-1), "LEFT"),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        
        # Outer table with fixed height (62pt) to vertically center the inner table block
        t = Table([[card_table]], colWidths=[width], rowHeights=[62])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.white),
            ("BOX",           (0,0),(-1,-1), 0.8, BORDER_GREY),
            ("LINELEFT",      (0,0),(0,-1),  4.0, bar_color),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ]))
        return t

    # ── 4 KPI cards in one horizontal row ───────────────────────────────────────
    # Total width budget = 739.89 pt (4 cards * 172.0 pt + 3 gaps * 17.29 pt)
    kpi_w = 172.0
    gap_w = 17.29

    c1 = make_kpi_card("Total Invested",  invested_val, "Cumulative Capital Deployed",   kpi_w, bar_color=colors.HexColor("#475569"))
    c2 = make_kpi_card("Portfolio Value",  value_val,   "Current Market Valuation",       kpi_w, bar_color=GOLD)
    c3 = make_kpi_card("Profit",           wealth_val,  "Net Capital Appreciation",       kpi_w, val_color=wealth_color,    bar_color=wealth_bar)
    c4 = make_kpi_card("Portfolio XIRR",   xirr_val,   "Annualised Rate of Return",       kpi_w, val_color=NAVY,            bar_color=GOLD)

    kpi_row = Table(
        [[c1, "", c2, "", c3, "", c4]],
        colWidths=[kpi_w, gap_w, kpi_w, gap_w, kpi_w, gap_w, kpi_w],
        hAlign="CENTER"
    )
    kpi_row.setStyle(TableStyle([
        ("VALIGN",         (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",     (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 0),
        ("LEFTPADDING",    (0,0),(-1,-1), 0),
        ("RIGHTPADDING",   (0,0),(-1,-1), 0),
    ]))
    story.append(kpi_row)
    story.append(Spacer(1, 12))

    # ── Divider ─────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.6, color=BORDER_GREY, spaceBefore=0, spaceAfter=12))

    # ── Style helpers with optimized fonts to prevent overflow ─────────────────
    sec_head = ParagraphStyle("P2SecH", fontName=FONT_UNICODE_SANS_BOLD,
                              fontSize=9.5, leading=12.0,
                              textColor=NAVY, spaceBefore=0, spaceAfter=4)
    body_sm  = ParagraphStyle("P2Body", fontName=FONT_UNICODE_SANS,
                              fontSize=8.2, leading=12.0,
                              textColor=colors.HexColor("#334155"), spaceBefore=0)
    bullet_sm= ParagraphStyle("P2Bull", fontName=FONT_UNICODE_SANS,
                              fontSize=8.2, leading=12.0,
                              textColor=colors.HexColor("#334155"),
                              leftIndent=10, bulletIndent=0)
    risk_sm  = ParagraphStyle("P2Risk", fontName=FONT_UNICODE_SANS,
                              fontSize=8.2, leading=12.0,
                              textColor=colors.HexColor("#334155"),
                              leftIndent=10, bulletIndent=0)

    # ── COL 1: Wealth Manager Executive Review ──────────────────────────────────
    exec_text = ai_narratives.get("executive_summary", "") if isinstance(ai_narratives, dict) else ""
    # Clean emoji from exec text for PDF rendering safety
    import re as _re
    exec_text_clean = _re.sub(r'[^\x00-\xFF\u20B9]', '', exec_text).strip()
    if not exec_text_clean:
        exec_text_clean = (
            f"We have conducted a comprehensive wealth audit for {client.get('client_name', 'the client')}. "
            f"The aggregate portfolio, valued at {value_val}, reflects capital appreciation of {wealth_val} "
            f"against a total deployment of {invested_val}. The portfolio demonstrates a strong compounding "
            f"trajectory underpinned by disciplined manager selection across equity and hybrid categories."
        )

    # Macro outlook
    macro = ai_narratives.get("macro_outlook", {}) if isinstance(ai_narratives, dict) else {}
    inv_strategy = ""
    if isinstance(macro, dict):
        inv_strategy = macro.get("investment_strategy", "")
    inv_strategy_clean = _re.sub(r'[^\x00-\xFF\u20B9]', '', inv_strategy).strip()

    col1_items = [
        Paragraph("WEALTH MANAGER EXECUTIVE REVIEW", sec_head),
        HRFlowable(width="100%", thickness=0.6, color=GOLD, spaceBefore=0, spaceAfter=4),
        Paragraph(exec_text_clean, body_sm),
    ]
    if inv_strategy_clean:
        col1_items += [
            Spacer(1, 6),
            Paragraph("INVESTMENT STRATEGY OUTLOOK", sec_head),
            HRFlowable(width="100%", thickness=0.6, color=GOLD, spaceBefore=0, spaceAfter=4),
            Paragraph(inv_strategy_clean, body_sm),
        ]

    exec_box = Table([[col1_items]], colWidths=[739.89])
    exec_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER_GREY),
        ("LINELEFT", (0, 0), (0, -1), 4.0, GOLD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))

    # ── COL 2: Portfolio Strengths ───────────────────────────────────────────────
    strengths_raw = ai_narratives.get("portfolio_strengths", []) if isinstance(ai_narratives, dict) else []
    if not strengths_raw:
        strengths_raw = [
            "Core equity holdings demonstrate strong risk-adjusted returns backed by seasoned fund managers.",
            "Diversified category exposure across Flexi Cap, Hybrid, and Debt reduces single-segment risk.",
            "Systematic investment discipline has compounded capital efficiently across market cycles."
        ]
    def clean_bullet(txt):
        t = _re.sub(r'[^\x00-\xFF\u20B9]', '', str(txt)).strip()
        # Remove leading punctuation artefacts
        t = t.lstrip('- ').strip()
        return t

    col2_items = [
        Paragraph("PORTFOLIO STRENGTHS", sec_head),
        HRFlowable(width="100%", thickness=0.6, color=GOLD, spaceBefore=0, spaceAfter=4),
    ]
    for s in strengths_raw[:4]:
        cleaned = clean_bullet(s)
        if cleaned:
            col2_items.append(Paragraph(f"<bullet>&#x2022;</bullet> {cleaned}", bullet_sm))
            col2_items.append(Spacer(1, 3))

    # ── COL 3: Key Risks & Opportunities ────────────────────────────────────────
    improvements_raw = ai_narratives.get("portfolio_improvements", []) if isinstance(ai_narratives, dict) else []
    if not improvements_raw:
        improvements_raw = [
            "Rebalancing required: equity overweight exposes portfolio to elevated drawdown risk.",
            "Tail-end consolidation opportunity: sub-3% holdings add complexity without return contribution.",
            "Fixed-income sleeve under-deployed relative to target; optimising yields is a priority action."
        ]

    col3_items = [
        Paragraph("KEY RISKS &amp; OPPORTUNITIES", sec_head),
        HRFlowable(width="100%", thickness=0.6, color=GOLD, spaceBefore=0, spaceAfter=4),
    ]
    for r in improvements_raw[:4]:
        cleaned = clean_bullet(r)
        if cleaned:
            col3_items.append(Paragraph(f"<bullet>&#x2022;</bullet> {cleaned}", risk_sm))
            col3_items.append(Spacer(1, 3))

    strengths_box = Table([[col2_items]], colWidths=[360])
    strengths_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER_GREY),
        ("LINELEFT", (0, 0), (0, -1), 4.0, colors.HexColor("#10B981")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))

    risks_box = Table([[col3_items]], colWidths=[360])
    risks_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, BORDER_GREY),
        ("LINELEFT", (0, 0), (0, -1), 4.0, colors.HexColor("#EF4444")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))

    two_col = Table(
        [[strengths_box, "", risks_box]],
        colWidths=[360, 19.89, 360],
        hAlign="CENTER"
    )
    two_col.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(exec_box)
    story.append(Spacer(1, 8))
    story.append(two_col)

    
    # ── PAGE 3: PORTFOLIO ASSET ALLOCATION ───────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 2))
    
    NAVY_BLUE = NAVY
    ROYAL_BLUE = GOLD
    LIGHT_GREY_BG = LIGHT_GREY
    BORDER_GREY = MID_GREY
    
    p3_title_style = ParagraphStyle("P3Title", parent=styles["Heading"], fontSize=18, leading=22, textColor=NAVY_BLUE)
    story.append(Paragraph("Portfolio Asset Allocation", p3_title_style))
    story.append(HRFlowable(width="100%", thickness=1.0, color=GOLD, spaceBefore=1, spaceAfter=2))
    
    # Prepare Category summary details
    cat_details = {}
    for h in holdings:
        cat = h["category"]
        if cat not in cat_details:
            cat_details[cat] = {"count": 0, "value": 0.0}
        cat_details[cat]["count"] += 1
        cat_details[cat]["value"] += h["current_value_inr"]
        
    sorted_cats = sorted(cat_details.items(), key=lambda x: x[1]["value"], reverse=True)
    
    # Premium bright professional palette as requested (Page 3 only)
    color_map = {
        'Flexi Cap': colors.HexColor("#2563EB"),
        'Large Cap': colors.HexColor("#6B7280"),
        'Mid Cap': colors.HexColor("#3B82F6"),
        'Small Cap': colors.HexColor("#F97316"),
        'Hybrid': colors.HexColor("#10B981"),
        'Multi Asset': colors.HexColor("#14B8A6"),
        'ELSS': colors.HexColor("#F59E0B"),
        'Sector/Thematic': colors.HexColor("#8B5CF6"),
        'Debt': colors.HexColor("#6B7280"),
        'Others': colors.HexColor("#6B7280")
    }
    
    # Prepare donut chart data
    donut = make_donut_chart(analytics["category_allocation"], size=245, total_value=total_value, color_map=color_map)
    
    # 1. Right Side Legend Cells
    legend_cells = []
    for cat, data in sorted_cats:
        alloc_pct = (data["value"] / total_value * 100.0) if total_value > 0.0 else 0.0
        color = color_map.get(cat, colors.HexColor("#6B7280"))
        hex_color = f"#{int(color.red * 255):02X}{int(color.green * 255):02X}{int(color.blue * 255):02X}"
        legend_cells.append(Paragraph(
            f"<font color='{hex_color}' size='12'>&#9632;</font> <font size='9.5' color='#475569'><b>{cat} - {alloc_pct:.2f}%</b></font>",
            styles["BodySmall"]
        ))
        
    legend_rows = []
    for i in range(0, len(legend_cells), 2):
        row = [legend_cells[i]]
        if i + 1 < len(legend_cells):
            row.append(legend_cells[i+1])
        else:
            row.append(Paragraph("", styles["BodySmall"]))
        legend_rows.append(row)
        
    legend_table = Table(legend_rows, colWidths=[220, 220])
    legend_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    
    # Legend layout panel
    legend_panel = [
        Paragraph("<b>ASSET ALLOCATION SUMMARY</b>", ParagraphStyle("P3LegendH", parent=styles["SubHeading"], fontSize=10.5, leading=13, textColor=NAVY_BLUE)),
        Spacer(1, 4),
        legend_table
    ]
    
    # Top Section Layout: Donut + Legend Panel
    top_layout = Table([[donut, legend_panel]], colWidths=[265, 475])
    top_layout.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(top_layout)
    story.append(Spacer(1, 6))
    
    # 2. Second Section: Category-Wise Allocation Table
    category_table_rows = [
        [
            Paragraph("<b>Category</b>", ParagraphStyle("H1", parent=styles["TableHeader"], fontSize=9.5, textColor=colors.white)),
            Paragraph("<b>Current Value</b>", ParagraphStyle("H2", parent=styles["TableHeaderRight"], fontSize=9.5, textColor=colors.white)),
            Paragraph("<b>Allocation %</b>", ParagraphStyle("H3", parent=styles["TableHeaderRight"], fontSize=9.5, textColor=colors.white))
        ]
    ]
    for cat, data in sorted_cats:
        alloc_pct = (data["value"] / total_value * 100.0) if total_value > 0.0 else 0.0
        color = color_map.get(cat, colors.HexColor("#64748B"))
        hex_color = f"#{int(color.red * 255):02X}{int(color.green * 255):02X}{int(color.blue * 255):02X}"
        category_table_rows.append([
            Paragraph(f"<font color='{hex_color}' size='12'>&#9632;</font> <b>{cat}</b>", ParagraphStyle("T1", parent=styles["TableCellBold"], fontSize=9)),
            Paragraph(format_rupee_words(data["value"]), ParagraphStyle("T2", parent=styles["TableCellRight"], fontSize=9)),
            Paragraph(f"{alloc_pct:.2f}%", ParagraphStyle("T3", parent=styles["TableCellRight"], fontSize=9))
        ])
        
    category_table = Table(category_table_rows, colWidths=[310, 215, 215])
    category_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("LINEABOVE", (0, 0), (-1, 0), 1.5, GOLD),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, GOLD),
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
    ]))
    
    story.append(Paragraph("<b>CATEGORY-WISE ALLOCATION</b>", ParagraphStyle("P3TableH", parent=styles["SubHeading"], fontSize=10.5, leading=13, textColor=NAVY_BLUE)))
    story.append(Spacer(1, 4))
    story.append(category_table)
    story.append(Spacer(1, 6))
    
    # Key Allocation Insights boxes (Largest Category / Equity Exposure / Diversification Score /
    # Recommended Action) removed per user request. Layout rebalances naturally.

    
    # ── PAGE 4: DETAILED PORTFOLIO HOLDINGS SUMMARY ──────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 4))
    story.append(Paragraph("Detailed Portfolio Holdings Summary", styles["Heading"]))
    story.append(HRFlowable(width="100%", thickness=1.2, color=GOLD, spaceBefore=2, spaceAfter=8))

    # ── Roman numeral helper ─────────────────────────────────────────────
    def _to_roman(n):
        val_map = [(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]
        r = ""
        for v, s in val_map:
            while n >= v:
                r += s; n -= v
        return r

    # ── Risk-ordered canonical category list ─────────────────────────────
    _ORDERED_CATS = [
        "Liquid Fund", "Overnight Fund", "Ultra Short Duration", "Low Duration",
        "Short Duration", "Corporate Bond", "Banking & PSU Debt", "Gilt Fund",
        "Dynamic Bond", "Balanced Advantage Fund", "Conservative Hybrid",
        "Aggressive Hybrid", "Hybrid", "Multi Asset", "Large Cap",
        "Large & Mid Cap", "Value / Contra", "Flexi Cap", "Multi Cap",
        "ELSS", "Mid Cap", "Small Cap", "Focused Fund",
        "Sector / Thematic", "International / Global",
    ]

    # ── Normalize raw category string to closest canonical label ─────────
    def _canon(raw):
        r = str(raw).lower().strip().replace(" ","").replace("/","").replace("&","").replace("-","")
        _MAP = {
            "liquidfund":"Liquid Fund","overnightfund":"Overnight Fund",
            "ultrashortduration":"Ultra Short Duration","ultrashort":"Ultra Short Duration",
            "lowduration":"Low Duration","shortduration":"Short Duration",
            "corporatebond":"Corporate Bond","bankingpsudebt":"Banking & PSU Debt",
            "bankingpsu":"Banking & PSU Debt","giltfund":"Gilt Fund","gilt":"Gilt Fund",
            "dynamicbond":"Dynamic Bond",
            "balancedadvantage":"Balanced Advantage Fund","baf":"Balanced Advantage Fund",
            "conservativehybrid":"Conservative Hybrid",
            "aggressivehybrid":"Aggressive Hybrid",
            "hybrid":"Hybrid","multiasset":"Multi Asset",
            "largecap":"Large Cap","largemidcap":"Large & Mid Cap",
            "valuecontra":"Value / Contra","contra":"Value / Contra",
            "flexicap":"Flexi Cap","multicap":"Multi Cap","elss":"ELSS",
            "midcap":"Mid Cap","smallcap":"Small Cap",
            "focusedfund":"Focused Fund","focused":"Focused Fund",
            "sectorthematic":"Sector / Thematic","sectoralthematic":"Sector / Thematic",
            "international":"International / Global","global":"International / Global",
        }
        if r in _MAP: return _MAP[r]
        if "sector" in r or "thematic" in r:        return "Sector / Thematic"
        if "international" in r or "global" in r:   return "International / Global"
        if "balancedadvantage" in r or "baf" in r:  return "Balanced Advantage Fund"
        if "largemid" in r:                         return "Large & Mid Cap"
        if "largecap" in r or ("large" in r and "cap" in r): return "Large Cap"
        if "smallcap" in r or ("small" in r and "cap" in r): return "Small Cap"
        if "midcap" in r  or ("mid" in r  and "cap" in r):   return "Mid Cap"
        if "flexicap" in r or "flexi" in r:         return "Flexi Cap"
        if "multicap" in r or "multic" in r:        return "Multi Cap"
        if "multiasset" in r:                       return "Multi Asset"
        if "elss" in r or "taxsaver" in r:          return "ELSS"
        if "hybrid" in r:                           return "Hybrid"
        if "gilt" in r:                             return "Gilt Fund"
        if "liquid" in r:                           return "Liquid Fund"
        return raw

    # ── Group & order holdings ───────────────────────────────────────────
    _groups = {}
    for h in holdings:
        c = _canon(h.get("category", ""))
        _groups.setdefault(c, []).append(h)
    for c in _groups:
        _groups[c].sort(key=lambda x: x.get("current_value_inr", 0), reverse=True)
    ordered_groups = [(c, _groups[c]) for c in _ORDERED_CATS if c in _groups]
    for c, hl in _groups.items():
        if c not in _ORDERED_CATS:
            ordered_groups.append((c, hl))

    # ── Style definitions ────────────────────────────────────────────────
    BG_BEIGE  = colors.HexColor("#F3ECE0")
    BG_ALT    = colors.HexColor("#F8F6F1")   # very light cream for alternating rows

    fs        = 8.5     # base font size
    lead      = 11.0
    pad       = 3.2     # row padding

    col_hdr_L = ParagraphStyle("P4CH_L", fontName=FONT_UNICODE_SANS_BOLD,
                               fontSize=7.8, leading=10, textColor=WHITE, alignment=0)
    col_hdr_C = ParagraphStyle("P4CH_C", fontName=FONT_UNICODE_SANS_BOLD,
                               fontSize=7.8, leading=10, textColor=WHITE, alignment=1)
    seg_style = ParagraphStyle("P4Seg",  fontName=FONT_UNICODE_SANS_BOLD,
                               fontSize=fs, leading=lead, textColor=NAVY)
    fund_style= ParagraphStyle("P4Fund", fontName=FONT_UNICODE_SANS_BOLD,
                               fontSize=fs, leading=lead, textColor=NAVY)
    num_style = ParagraphStyle("P4Num",  fontName=FONT_UNICODE_SANS_BOLD,
                               fontSize=fs - 0.5, leading=lead, textColor=DARK_GREY, alignment=2)
    pct_style = ParagraphStyle("P4Pct",  fontName=FONT_UNICODE_SANS_BOLD,
                               fontSize=fs - 0.5, leading=lead, textColor=DARK_GREY, alignment=2)
    reco_style = ParagraphStyle("P4Reco", fontName=FONT_UNICODE_SANS,
                                fontSize=fs - 0.7, leading=10, textColor=DARK_GREY, alignment=0)

    # Column widths — single unified table, fills available width: 730 pt
    # Fund Name (165) | Invested (75) | Current Value (75) | Return % (65) | Weight % (60) | Review & Recommendation (290)
    _CW = [165, 75, 75, 65, 60, 290]

    # Recommendation Generator Logic
    def _get_reco(h):
        notes = h.get("advisor_notes", "").strip()
        
        # 1. Excel recommendation takes absolute highest priority and must match verbatim (Rule 2)
        if notes:
            return notes

        # 2. Only if the Excel cell is blank, generate a new professional recommendation (Rule 3)
        xirr = h.get("xirr_pct", 0.0)
        wt = h.get("allocation_pct", 0.0)
        ret = h.get("gain_loss_pct", 0.0)
        val = h.get("current_value_inr", 0.0)
        canon_cat = _canon(h.get("category", ""))

        # Check underperformance first (XIRR < 8% and not defensive/hybrid/debt)
        is_hybrid = canon_cat in ["Balanced Advantage Fund", "Conservative Hybrid", "Aggressive Hybrid", "Hybrid"]
        is_debt = canon_cat in ["Liquid Fund", "Overnight Fund", "Ultra Short Duration", "Low Duration", "Short Duration", "Corporate Bond", "Banking & PSU Debt", "Gilt Fund", "Dynamic Bond"]
        
        if xirr < 8.0 and not is_hybrid and not is_debt:
            return "Review Allocation – Evaluate future allocation during the next portfolio rebalancing cycle."

        # Category specific recommendations
        if is_debt:
            if "liquid" in canon_cat.lower() or "overnight" in canon_cat.lower():
                return "Continue Holding – High-liquidity cash surrogate suitable for capital safety and immediate deployment."
            return "Continue Holding – Quality debt exposure offers portfolio stability and stable accruals."

        if is_hybrid:
            return "Continue Holding – Provides portfolio stability and reduces downside volatility."

        if canon_cat == "Multi Asset":
            return "Continue Holding – Maintains diversification across asset classes and enhances portfolio resilience."

        if canon_cat == "Large Cap":
            return "Continue Holding – Suitable as a stable core allocation for long-term wealth creation."

        if canon_cat == "Large & Mid Cap":
            return "Continue Holding – Dual large and mid-cap strategy captures both market stability and mid-cap alpha."

        if canon_cat in ["Flexi Cap", "Multi Cap", "Value / Contra"]:
            if canon_cat == "Flexi Cap":
                return "Continue Holding – Flexible investment strategy continues to support long-term growth."
            elif canon_cat == "Multi Cap":
                return "Continue Holding – Multi-cap allocation enables active capital rotation to optimize growth across cycles."
            else: # Value / Contra
                return "Continue Holding – Value-oriented mandate provides margin of safety with consistent absolute return."

        if canon_cat == "ELSS":
            return "Continue Holding – Tax-saving equity allocation with disciplined long-term wealth creation potential."

        if canon_cat == "Mid Cap":
            return "Continue Holding – Strong growth potential with acceptable long-term risk."

        if canon_cat == "Small Cap":
            return "Continue Holding – High-growth opportunity suitable for long-term investors despite higher volatility."

        if canon_cat == "Sector / Thematic":
            return "Continue Holding – Retain exposure for long-term sector-specific growth while monitoring volatility."

        # General default
        return "Continue Holding – Aligned with long-term asset allocation and portfolio objectives."

    # ── Build the single unified table ───────────────────────────────────
    table_rows = []
    t_style = [
        # Global defaults
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 1), (-1, -1), pad),
        ("BOTTOMPADDING",(0, 1), (-1, -1), pad),
        # Column header row (row 0)
        ("BACKGROUND",   (0, 0), (-1, 0), NAVY),
        ("LINEABOVE",    (0, 0), (-1, 0), 1.5, GOLD),
        ("LINEBELOW",    (0, 0), (-1, 0), 1.5, GOLD),
        ("TOPPADDING",   (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 5),
    ]

    # Row 0 — column headers
    table_rows.append([
        Paragraph("FUND NAME",                  col_hdr_L),
        Paragraph("INVESTED",                   col_hdr_C),
        Paragraph("CURRENT VALUE",              col_hdr_C),
        Paragraph("RETURN %",                   col_hdr_C),
        Paragraph("WEIGHT %",                   col_hdr_C),
        Paragraph("INVESTMENT REVIEW & ACTION", col_hdr_L),
    ])
    row_idx = 1
    roman_n  = 0

    for canon_cat, cat_holdings in ordered_groups:
        roman_n += 1
        cat_val    = sum(h.get("current_value_inr",  0) for h in cat_holdings)
        cat_weight = sum(h.get("allocation_pct",     0) for h in cat_holdings)

        # ── Category header row (spans all 6 columns) ─────────────────
        cat_label = (
            f"<b>{_to_roman(roman_n)}. {canon_cat.upper()}</b>"
            f"&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;"
            f"<font color='#9A6A00'><b>{format_rupee_words(cat_val)}</b></font>"
            f"&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;"
            f"<font color='#334155'>Portfolio Weight: <b>{cat_weight:.1f}%</b></font>"
        )
        table_rows.append([Paragraph(cat_label, seg_style), "", "", "", "", ""])
        t_style += [
            ("SPAN",         (0, row_idx), (-1, row_idx)),
            ("BACKGROUND",   (0, row_idx), (-1, row_idx), BG_BEIGE),
            ("LINEBELOW",    (0, row_idx), (-1, row_idx), 1.2, GOLD),
            ("TOPPADDING",   (0, row_idx), (-1, row_idx), 6 if row_idx > 1 else 4),
            ("BOTTOMPADDING",(0, row_idx), (-1, row_idx), 6),
        ]
        row_idx += 1

        # ── Fund rows ──────────────────────────────────────────────────
        for fi, h in enumerate(cat_holdings):
            wc   = h["current_value_inr"] - h["purchase_cost_inr"]
            sign = "+" if wc >= 0 else ""
            bg   = WHITE if fi % 2 == 0 else BG_ALT

            table_rows.append([
                Paragraph(shorten_scheme_name(h["product_name"]), fund_style),
                Paragraph(format_rupees_no_dec(h["purchase_cost_inr"]),          num_style),
                Paragraph(format_rupees_no_dec(h["current_value_inr"]),           num_style),
                Paragraph(f"{sign}{h['gain_loss_pct']:.2f}%",                    pct_style),
                Paragraph(f"{h['allocation_pct']:.2f}%",                          pct_style),
                Paragraph(_get_reco(h),                                           reco_style),
            ])
            t_style += [
                ("BACKGROUND", (0, row_idx), (-1, row_idx), bg),
                ("LINEBELOW",  (0, row_idx), (-1, row_idx), 0.4, MID_GREY),
            ]
            row_idx += 1

    # ── Render the single unified table ──────────────────────────────────
    main_table = Table(table_rows, colWidths=_CW, hAlign="LEFT", repeatRows=1)
    main_table.setStyle(TableStyle(t_style))
    story.append(main_table)
    story.append(Spacer(1, 6))

    story.append(PageBreak())
    p5_heading_style = ParagraphStyle("P5Heading", parent=styles["Heading"], fontSize=24, leading=26, spaceAfter=1)
    story.append(Paragraph("Performance Summary", p5_heading_style))
    story.append(HRFlowable(width="100%", thickness=1.0, color=GOLD, spaceBefore=1, spaceAfter=5))

    from reportlab.platypus import Flowable

    class RoundedSectionContainer(Flowable):
        def __init__(self, title, content, width=355, height=170):
            Flowable.__init__(self)
            self.title = title
            self.content = content
            self.width = width
            self.height = height
            
        def wrap(self, availWidth, availHeight):
            return self.width, self.height
            
        def draw(self):
            self.canv.saveState()
            self.canv.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.canv.setLineWidth(1.0)
            self.canv.roundRect(0, 0, self.width, self.height - 10, 5, stroke=1, fill=0)
            
            self.canv.setFont(FONT_UNICODE_SANS_BOLD, 9.0)
            self.canv.setFillColor(NAVY)
            title_width = self.canv.stringWidth(self.title, FONT_UNICODE_SANS_BOLD, 9.0)
            x_text = (self.width - title_width) / 2
            
            self.canv.setFillColor(colors.white)
            self.canv.rect(x_text - 5, self.height - 14, title_width + 10, 8, stroke=0, fill=1)
            
            self.canv.setFillColor(NAVY)
            self.canv.drawString(x_text, self.height - 13, self.title)
            self.canv.restoreState()
            
            self.content.wrapOn(self.canv, self.width - 20, self.height - 30)
            self.content.drawOn(self.canv, 10, 10)

    # Custom Styles for Page 6 Redesign
    p5_section_title = ParagraphStyle(
        "P5SectionTitle", 
        parent=styles["BodySmall"], 
        fontName=FONT_UNICODE_SANS_BOLD, 
        fontSize=8.5, 
        leading=11.0, 
        textColor=NAVY
    )
    p5_table_header_white = ParagraphStyle(
        "P5TableHeaderWhite", 
        parent=styles["BodySmall"], 
        fontName=FONT_UNICODE_SANS_BOLD, 
        fontSize=8.5, 
        leading=11.0, 
        textColor=colors.white, 
        alignment=1
    )
    p5_table_header_left_white = ParagraphStyle(
        "P5TableHeaderLeftWhite", 
        parent=styles["BodySmall"], 
        fontName=FONT_UNICODE_SANS_BOLD, 
        fontSize=8.5, 
        leading=11.0, 
        textColor=colors.white, 
        alignment=0
    )
    p5_table_header_grey = ParagraphStyle(
        "P5TableHeaderGrey", 
        parent=styles["BodySmall"], 
        fontName=FONT_UNICODE_SANS_BOLD, 
        fontSize=8.0, 
        leading=10.0, 
        textColor=colors.HexColor("#475569"), 
        alignment=0
    )
    p5_table_header_grey_right = ParagraphStyle(
        "P5TableHeaderGreyRight", 
        parent=styles["BodySmall"], 
        fontName=FONT_UNICODE_SANS_BOLD, 
        fontSize=8.0, 
        leading=10.0, 
        textColor=colors.HexColor("#475569"), 
        alignment=2
    )
    p5_card_text_style = ParagraphStyle(
        "P5CardText", 
        parent=styles["BodySmall"], 
        fontName=FONT_UNICODE_SANS,
        fontSize=8.0, 
        leading=11.0, 
        textColor=DARK_GREY
    )
    p5_card_text_right_style = ParagraphStyle(
        "P5CardTextRight", 
        parent=styles["BodySmall"], 
        fontName=FONT_UNICODE_SANS,
        fontSize=8.0, 
        leading=11.0, 
        textColor=DARK_GREY, 
        alignment=2
    )
    p5_card_text_bold_style = ParagraphStyle(
        "P5CardTextBold",
        parent=p5_card_text_style,
        fontName=FONT_UNICODE_SANS_BOLD,
        alignment=1
    )
    p5_body_text_style = ParagraphStyle(
        "P5BodyText", 
        parent=styles["BodySmall"], 
        fontName=FONT_UNICODE_SANS,
        fontSize=8.0, 
        leading=11.0, 
        textColor=DARK_GREY
    )

    # Rank circles and drawing helpers
    def make_rank_circle(rank_num, color_hex):
        d = Drawing(14, 14)
        d.add(Circle(7, 7, 7, strokeColor=None, fillColor=colors.HexColor(color_hex)))
        d.add(String(7, 4, str(rank_num), textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=7.5, fillColor=colors.white))
        return d

    def make_growth_chart_vertical(invested, current, width=335, height=130):
        import math
        d = Drawing(width, height)
        
        v_inv = invested / 100000.0
        v_cur = current / 100000.0
        max_raw = max(v_inv, v_cur)
        if max_raw <= 0:
            max_raw = 100.0
            
        # Include 15% headroom
        max_with_headroom = max_raw * 1.15
        
        # Select clean step size targeting 3 to 5 tick intervals
        power = 10 ** math.floor(math.log10(max_with_headroom))
        candidates = [
            power * 0.1,
            power * 0.2,
            power * 0.25,
            power * 0.5,
            power * 1.0,
            power * 2.0,
            power * 5.0,
            power * 10.0
        ]
        
        best_step = None
        best_num_ticks = None
        for step in candidates:
            if step <= 0:
                continue
            num_intervals = math.ceil(max_with_headroom / step)
            if num_intervals >= 3 and num_intervals <= 5:
                best_step = step
                best_num_ticks = num_intervals
                break
                
        if best_step is None:
            best_step = power * 0.25
            best_num_ticks = math.ceil(max_with_headroom / best_step)
            
        y_max_axis_lakhs = best_num_ticks * best_step
        y_max_axis = y_max_axis_lakhs * 100000.0
        
        scale_height = height - 35
        scale = scale_height / y_max_axis if y_max_axis > 0 else 1.0
        
        h_inv = invested * scale
        h_cur = current * scale
        
        w_bar = 40
        gap = 85
        x_inv = 75
        x_cur = x_inv + w_bar + gap
        y_base = 15
        
        # Draw dynamic grid lines and tick labels on the left side
        for i in range(best_num_ticks + 1):
            tick_lakhs = i * best_step
            y_tick = y_base + (tick_lakhs * 100000.0) * scale
            
            d.add(Line(45, y_tick, width - 20, y_tick, strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=0.5))
            
            tick_str = f"{tick_lakhs:,.0f}" if tick_lakhs.is_integer() else f"{tick_lakhs:,.1f}"
            d.add(String(40, y_tick - 3, tick_str, textAnchor="end", fontName=FONT_UNICODE_SANS, fontSize=8.0, fillColor=DARK_GREY))
            
        d.add(String(20, height - 12, "Amount (\u20b9 Lakhs)", fontName=FONT_UNICODE_SANS, fontSize=8.0, fillColor=DARK_GREY))
        
        d.add(Rect(x_inv, y_base, w_bar, h_inv, fillColor=NAVY, strokeColor=None, rx=1, ry=1))
        d.add(Rect(x_cur, y_base, w_bar, h_cur, fillColor=colors.HexColor("#C59B27"), strokeColor=None, rx=1, ry=1))
        
        # Draw values on top of bars formatted nicely
        v_inv_str = f"{v_inv:,.2f}" if v_inv < 1000 else f"{v_inv:,.1f}"
        v_cur_str = f"{v_cur:,.2f}" if v_cur < 1000 else f"{v_cur:,.1f}"
        d.add(String(x_inv + w_bar/2, y_base + h_inv + 4, v_inv_str, textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.5, fillColor=NAVY))
        d.add(String(x_cur + w_bar/2, y_base + h_cur + 4, v_cur_str, textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.5, fillColor=colors.HexColor("#C59B27")))
        
        d.add(String(x_inv + w_bar/2, y_base - 10, "Total Invested", textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.0, fillColor=DARK_GREY))
        d.add(String(x_cur + w_bar/2, y_base - 10, "Current Value", textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.0, fillColor=DARK_GREY))
        
        y_inv_top = y_base + h_inv
        y_cur_top = y_base + h_cur
        d.add(Line(x_inv + w_bar, y_inv_top + 10, x_cur, y_cur_top + 10, strokeColor=NAVY, strokeWidth=1, strokeDashArray=[3, 3]))
        
        d.add(Line(x_cur, y_cur_top + 10, x_cur - 8, y_cur_top + 8, strokeColor=NAVY, strokeWidth=1))
        d.add(Line(x_cur, y_cur_top + 10, x_cur - 5, y_cur_top + 4, strokeColor=NAVY, strokeWidth=1))
        
        abs_return_pct = ((current - invested) / invested) * 100 if invested > 0 else 0.0
        abs_return_str = f"{abs_return_pct:+.2f}%" if abs_return_pct >= 0 else f"{abs_return_pct:.2f}%"
        text_color = colors.HexColor("#16A34A") if abs_return_pct >= 0 else colors.HexColor("#DC2626")
        
        y_text = min(max(y_inv_top, y_cur_top) + 15, height - 12)
        d.add(String((x_inv + w_bar + x_cur)/2, y_text, abs_return_str, textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=9.0, fillColor=text_color))
        
        return d

    def make_badge_drawing():
        d = Drawing(16, 16)
        d.add(Circle(8, 8, 8, strokeColor=GOLD, strokeWidth=1, fillColor=colors.white))
        d.add(Line(8, 13, 10, 9, strokeColor=GOLD, strokeWidth=1))
        d.add(Line(10, 9, 14, 9, strokeColor=GOLD, strokeWidth=1))
        d.add(Line(14, 9, 11, 7, strokeColor=GOLD, strokeWidth=1))
        d.add(Line(11, 7, 12, 3, strokeColor=GOLD, strokeWidth=1))
        d.add(Line(12, 3, 8, 5, strokeColor=GOLD, strokeWidth=1))
        d.add(Line(8, 5, 4, 3, strokeColor=GOLD, strokeWidth=1))
        d.add(Line(4, 3, 5, 7, strokeColor=GOLD, strokeWidth=1))
        d.add(Line(5, 7, 2, 9, strokeColor=GOLD, strokeWidth=1))
        d.add(Line(2, 9, 6, 9, strokeColor=GOLD, strokeWidth=1))
        d.add(Line(6, 9, 8, 13, strokeColor=GOLD, strokeWidth=1))
        return d

    def make_icon_card(icon_name, text_lines, width=70, height=85):
        d = Drawing(width, height)
        d.add(Rect(0, 0, width, height, fillColor=NAVY, strokeColor=None, rx=4, ry=4))
        
        if icon_name == "lightbulb":
            d.add(Circle(width/2, height/2 + 12, 8, strokeColor=colors.white, strokeWidth=1, fillColor=NAVY))
            d.add(Line(width/2 - 4, height/2 + 5, width/2 + 4, height/2 + 5, strokeColor=colors.white, strokeWidth=1))
            d.add(Line(width/2 - 2, height/2 + 3, width/2 + 2, height/2 + 3, strokeColor=colors.white, strokeWidth=1))
        else:
            d.add(Rect(width/2 - 8, height/2 + 4, 4, 10, fillColor=colors.white, strokeColor=None))
            d.add(Rect(width/2 - 2, height/2 + 4, 4, 15, fillColor=colors.white, strokeColor=None))
            d.add(Rect(width/2 + 4, height/2 + 4, 4, 8, fillColor=colors.white, strokeColor=None))
            
        y_start = height/2 - 10
        for line in text_lines:
            d.add(String(width/2, y_start, line, textAnchor="middle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=7.0, fillColor=colors.white))
            y_start -= 9
        return d

    # Data Calculations
    holdings_by_gain = sorted(holdings, key=lambda x: x["current_value_inr"] - x["purchase_cost_inr"], reverse=True)
    top_contributors = holdings_by_gain[:3]
    top_performers_3 = top_performers[:3]

    bench_cagr = 11.21
    alpha = weighted_xirr - bench_cagr
    alpha_str = f"+{alpha:.2f}%" if alpha >= 0 else f"{alpha:.2f}%"

    # Row 2: Portfolio Growth Chart & Benchmark Comparison side-by-side
    growth_chart = make_growth_chart_vertical(total_cost, total_value, width=335, height=130)
    growth_container = RoundedSectionContainer("PORTFOLIO GROWTH CHART", growth_chart, width=360, height=165)

    bench_data = [
        [
            Paragraph("METRIC", p5_table_header_left_white),
            Paragraph("PORTFOLIO", p5_table_header_white),
            Paragraph("BENCHMARK", p5_table_header_white),
            Paragraph("ADVANTAGE", p5_table_header_white)
        ],
        [
            Paragraph("Portfolio XIRR", p5_card_text_style),
            Paragraph(f"<b>{weighted_xirr:.2f}%</b>", p5_card_text_bold_style),
            Paragraph(f"<b>{bench_cagr:.2f}%</b>", p5_card_text_bold_style),
            Paragraph(f"<font color='#16A34A'><b>{alpha_str}</b></font>", p5_card_text_bold_style)
        ],
        [
            Paragraph("Benchmark CAGR", p5_card_text_style),
            Paragraph(f"<b>{bench_cagr:.2f}%</b>", p5_card_text_bold_style),
            Paragraph(f"<b>{bench_cagr:.2f}%</b>", p5_card_text_bold_style),
            Paragraph("-", p5_card_text_style)
        ],
        [
            Paragraph("Alpha Generated", p5_card_text_style),
            Paragraph(f"<font color='#16A34A'><b>{alpha_str}</b></font>", p5_card_text_bold_style),
            Paragraph("-", p5_card_text_style),
            Paragraph("-", p5_card_text_style)
        ]
    ]
    bench_t = Table(bench_data, colWidths=[115, 75, 75, 75])
    bench_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    assess_data = [
        [
            make_badge_drawing(),
            Paragraph(f"<b>OVERALL ASSESSMENT</b><br/>The portfolio has outperformed the benchmark, generating an alpha of <b>{alpha_str}</b>.", p5_card_text_style)
        ]
    ]
    assess_t = Table(assess_data, colWidths=[20, 310])
    assess_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAF8F0")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    bench_flowables = [
        bench_t,
        Spacer(1, 6),
        assess_t
    ]
    bench_content = Table([[bench_flowables]], colWidths=[340])
    bench_content.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    bench_container = RoundedSectionContainer("BENCHMARK COMPARISON", bench_content, width=360, height=165)

    row2_table = Table([[growth_container, bench_container]], colWidths=[370, 370])
    row2_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(row2_table)
    story.append(Spacer(1, 10))

    # Row 3: Top Contributors and Top Performers side-by-side
    tc_table_data = [[
        "",
        Paragraph("<b>SCHEME NAME</b>", p5_table_header_grey),
        Paragraph("<b>ABSOLUTE GAIN</b>", p5_table_header_grey_right),
        Paragraph("<b>RETURN %</b>", p5_table_header_grey_right)
    ]]
    for idx, tc in enumerate(top_contributors, 1):
        gain_val = tc["current_value_inr"] - tc["purchase_cost_inr"]
        short_name = shorten_scheme_name(tc["product_name"])
        tc_table_data.append([
            make_rank_circle(idx, ["#C59B27", "#94A3B8", "#CD7F32"][idx-1]),
            Paragraph(short_name, p5_card_text_style),
            Paragraph(f"₹ {format_short_amount(gain_val)}", p5_card_text_right_style),
            Paragraph(f"{tc['gain_loss_pct']:.2f}%", p5_card_text_right_style)
        ])
    tc_t = Table(tc_table_data, colWidths=[20, 170, 75, 75])
    tc_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (1, 0), (-1, 0), 1.0, colors.HexColor("#CBD5E1")),
        ("LINEBELOW", (1, 1), (-1, -2), 0.5, colors.HexColor("#F1F5F9")),
    ]))
    tc_content = [
        tc_t,
        Spacer(1, 4),
        Paragraph("<font color='#64748B'>*Based on absolute gain in rupees.</font>", ParagraphStyle("NoteP", parent=styles["BodySmall"], fontName=FONT_UNICODE_SANS, fontSize=6.5, textColor=DARK_GREY))
    ]
    tc_wrapper = Table([[tc_content]], colWidths=[340])
    tc_wrapper.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    tc_container = RoundedSectionContainer("TOP CONTRIBUTORS (ABSOLUTE GAINS)", tc_wrapper, width=360, height=125)

    tp_table_data = [[
        "",
        Paragraph("<b>SCHEME NAME</b>", p5_table_header_grey),
        Paragraph("<b>XIRR %</b>", p5_table_header_grey_right),
        Paragraph("<b>CURRENT VALUE</b>", p5_table_header_grey_right)
    ]]
    for idx, tp in enumerate(top_performers_3, 1):
        short_name = shorten_scheme_name(tp["product_name"])
        tp_table_data.append([
            make_rank_circle(idx, ["#C59B27", "#94A3B8", "#CD7F32"][idx-1]),
            Paragraph(short_name, p5_card_text_style),
            Paragraph(f"{tp['xirr_pct']:.2f}%", p5_card_text_right_style),
            Paragraph(f"₹ {format_short_amount(tp['current_value_inr'])}", p5_card_text_right_style)
        ])
    tp_t = Table(tp_table_data, colWidths=[20, 170, 75, 75])
    tp_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (1, 0), (-1, 0), 1.0, colors.HexColor("#CBD5E1")),
        ("LINEBELOW", (1, 1), (-1, -2), 0.5, colors.HexColor("#F1F5F9")),
    ]))
    tp_content = [
        tp_t,
        Spacer(1, 4),
        Paragraph("<font color='#64748B'>*Based on XIRR (annualised).</font>", ParagraphStyle("NoteP", parent=styles["BodySmall"], fontName=FONT_UNICODE_SANS, fontSize=6.5, textColor=DARK_GREY))
    ]
    tp_wrapper = Table([[tp_content]], colWidths=[340])
    tp_wrapper.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    tp_container = RoundedSectionContainer("TOP PERFORMERS (BY XIRR)", tp_wrapper, width=360, height=125)

    row3_table = Table([[tc_container, tp_container]], colWidths=[370, 370])
    row3_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(row3_table)
    story.append(Spacer(1, 10))

    # Row 4: Key Performance Drivers & Portfolio Insights
    drivers_icon = make_icon_card("chart", ["KEY", "PERFORMANCE", "DRIVERS"])
    drivers_bullets = [
        "• <b>Strong Equity Allocation</b>: Higher allocation to Mid Cap and Flexi Cap funds drove strong overall returns.",
        "• <b>Effective Fund Selection</b>: Active fund selection across categories has significantly outperformed benchmarks.",
        "• <b>Diversified Approach</b>: Exposure across equity, hybrid and multi-asset funds reduced overall portfolio volatility.",
        "• <b>Long-term Discipline</b>: SIP contributions and long-term holding strategy enhanced wealth compounding."
    ]
    drivers_html = "<br/>".join(drivers_bullets)
    drivers_t = Table([[drivers_icon, Paragraph(drivers_html, p5_body_text_style)]], colWidths=[75, 275])
    drivers_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    insights_icon = make_icon_card("lightbulb", ["PORTFOLIO", "INSIGHTS"])
    insights_bullets = []
    for h in holdings:
        note = h.get("advisor_notes", "").strip()
        if note and note.lower() not in ["continue to hold.", "fund is doing well. continue to hold."]:
            short_name = shorten_scheme_name(h["product_name"])
            insights_bullets.append(f"• <b>{short_name}</b>: {note}")
    if not insights_bullets:
        insights_bullets.append("• No specific portfolio action points identified in the review period.")
    insights_html = "<br/>".join(insights_bullets)
    insights_t = Table([[insights_icon, Paragraph(insights_html, p5_body_text_style)]], colWidths=[75, 275])
    insights_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    row4_table = Table([[drivers_t, insights_t]], colWidths=[370, 370])
    row4_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(row4_table)
    # ── Page: Our Founders (added before Disclaimer)
    story.append(PageBreak())
    story.append(Spacer(1, 10))
    
    founders_elements = []
    founders_elements.append(Paragraph("Our Founders", styles["Heading"]))
    founders_elements.append(HRFlowable(width="100%", thickness=1.2, color=GOLD, spaceBefore=2, spaceAfter=15))
    P2_FOUNDER_NAME = ParagraphStyle("P2FounderName", fontName=FONT_UNICODE_SERIF_BOLD, fontSize=16.5, leading=19.5, textColor=NAVY, alignment=1)
    P2_FOUNDER_TITLE = ParagraphStyle("P2FounderTitle", fontName=FONT_UNICODE_SANS_BOLD, fontSize=11.5, leading=14.0, textColor=GOLD, alignment=1, spaceAfter=8)
    P2_BIO_BODY = ParagraphStyle("P2BioBody", parent=styles["Body"], fontSize=9.8, leading=13.0, textColor=DARK_GREY, alignment=4, spaceAfter=8)
    P2_INFO_LABEL = ParagraphStyle("P2InfoLabel", fontName=FONT_UNICODE_SANS_BOLD, fontSize=8.8, leading=11.5, textColor=NAVY)
    P2_INFO_VAL = ParagraphStyle("P2InfoVal", fontName=FONT_UNICODE_SANS, fontSize=8.8, leading=11.5, textColor=DARK_GREY)
    
    # Process circular images
    def make_circular_img(in_path, out_path, size=200):
        if not in_path or not os.path.exists(in_path):
            return None
        try:
            from PIL import Image, ImageOps, ImageDraw
            im = Image.open(in_path)
            if im.mode != "RGBA":
                im = im.convert("RGBA")
            im = ImageOps.fit(im, (size, size), Image.Resampling.LANCZOS)
            mask = Image.new('L', (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            im.putalpha(mask)
            im.save(out_path, "PNG")
            return out_path
        except Exception as e:
            print(f"Error circularizing image {in_path}: {e}")
            return None

    def resolve_image_path(name):
        p1 = os.path.join(current_dir, name)
        if os.path.exists(p1):
            return p1
        p2 = os.path.join(os.path.dirname(current_dir), name)
        if os.path.exists(p2):
            return p2
        if os.path.exists(name):
            return name
        return None

    # Resolve paths
    founder1_img_path = resolve_image_path("founder.jpeg") or resolve_image_path("founder.jpg") or resolve_image_path("extracted_img_p2_2_150.jpeg")
    founder2_img_path = resolve_image_path("founder_2.jpg")

    # Generate circular versions
    circular_f1 = None
    if founder1_img_path:
        circular_f1 = os.path.join(os.path.dirname(founder1_img_path) if os.path.dirname(founder1_img_path) else ".", "circular_f1.png")
        make_circular_img(founder1_img_path, circular_f1, size=150)

    circular_f2 = None
    if founder2_img_path:
        circular_f2 = os.path.join(os.path.dirname(founder2_img_path) if os.path.dirname(founder2_img_path) else ".", "circular_f2.png")
        make_circular_img(founder2_img_path, circular_f2, size=150)

    # Left Card details (Pranjal Wagh)
    wagh_name = "Pranjal Wagh"
    wagh_title = "Co-Founder"
    wagh_bio = (
        "Pranjal Wagh is the Co-Founder of Samarth Wealth, with over 16 years of extensive private banking "
        "and relationship management expertise. Prior to co-founding the firm, he held leadership and advisory "
        "positions at HDFC Bank, managing high-net-worth client relationships and delivering custom portfolio solutions. "
        "He specializes in private wealth planning and simplifying complex asset structures to align strategic decisions with client objectives."
    )
    wagh_exp = "16+ Years in Private Banking & Wealth Management (HDFC Bank)"
    wagh_qual = "MBA in Marketing (N.L. Dalmia), Certified Advanced Financial Goal Planner, Business Strategy Program (IIM Udaipur)"
    wagh_exp_list = "Financial Goal Planning, Wealth Management, Relationship Advisory, Business Strategy"

    # Right Card details (Abhinandan Honale)
    firm = review_context.get("firm", {})
    honale_name = firm.get("Advisor Name", "Abhinandan Honale")
    honale_title = "Co-Founder"
    honale_bio = (
        "Abhinandan Honale is the Co-Founder of Samarth Wealth, bringing extensive expertise in financial risk modeling "
        "and wealth management. Prior to co-founding the firm, he managed HNI portfolios at ICICI Bank Wealth Management "
        "and spearheaded investment strategy analysis at Deutsche Bank. Under his leadership, the firm combines institutional-grade "
        "investment discipline with an analytical, risk-conscious approach to build resilient portfolios."
    )
    honale_exp = "Investment Banking & Wealth Management (Deutsche Bank, ICICI Bank)"
    honale_qual = "B.E., MBA in Finance, Financial Risk Manager (FRM, GARP USA)"
    honale_exp_list = "Risk Management, Portfolio Construction, Capital Preservation, Investment Strategy"

    # Build Left Card Flowable (Pranjal Wagh)
    card_w = (739.89 - 30) / 2 # 354 pt
    
    if circular_f2 and os.path.exists(circular_f2):
        wagh_p_img = Image(circular_f2, width=72, height=72)
    else:
        wagh_p_img = make_image_placeholder(wagh_name, width=72, height=72)

    wagh_img_table = Table([[wagh_p_img]], colWidths=[card_w - 24], hAlign='CENTER')
    wagh_img_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    wagh_info_data = [
        [Paragraph("Experience", P2_INFO_LABEL), Paragraph(wagh_exp, P2_INFO_VAL)],
        [Paragraph("Qualifications", P2_INFO_LABEL), Paragraph(wagh_qual, P2_INFO_VAL)],
        [Paragraph("Core Expertise", P2_INFO_LABEL), Paragraph(wagh_exp_list, P2_INFO_VAL)],
    ]
    wagh_info_table = Table(wagh_info_data, colWidths=[90, card_w - 24 - 90], hAlign='LEFT')
    wagh_info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E2E8F0")),
    ]))

    wagh_card_content = [
        [wagh_img_table],
        [Spacer(1, 4)],
        [Paragraph(wagh_name, P2_FOUNDER_NAME)],
        [Paragraph(wagh_title, P2_FOUNDER_TITLE)],
        [Paragraph(wagh_bio, P2_BIO_BODY)],
        [Spacer(1, 4)],
        [wagh_info_table]
    ]
    
    wagh_outer_table = Table(wagh_card_content, colWidths=[card_w - 24], hAlign='CENTER')
    wagh_outer_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    wagh_card_box = Table([[wagh_outer_table]], colWidths=[card_w], hAlign='LEFT')
    wagh_card_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FDFDFD")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0,0), (-1,-1), 16),
        ('BOTTOMPADDING', (0,0), (-1,-1), 16),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))

    # Build Right Card Flowable (Abhinandan Honale)
    if circular_f1 and os.path.exists(circular_f1):
        honale_p_img = Image(circular_f1, width=72, height=72)
    else:
        honale_p_img = make_image_placeholder(honale_name, width=72, height=72)

    honale_img_table = Table([[honale_p_img]], colWidths=[card_w - 24], hAlign='CENTER')
    honale_img_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    honale_info_data = [
        [Paragraph("Experience", P2_INFO_LABEL), Paragraph(honale_exp, P2_INFO_VAL)],
        [Paragraph("Qualifications", P2_INFO_LABEL), Paragraph(honale_qual, P2_INFO_VAL)],
        [Paragraph("Core Expertise", P2_INFO_LABEL), Paragraph(honale_exp_list, P2_INFO_VAL)],
    ]
    honale_info_table = Table(honale_info_data, colWidths=[90, card_w - 24 - 90], hAlign='LEFT')
    honale_info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E2E8F0")),
    ]))

    honale_card_content = [
        [honale_img_table],
        [Spacer(1, 4)],
        [Paragraph(honale_name, P2_FOUNDER_NAME)],
        [Paragraph(honale_title, P2_FOUNDER_TITLE)],
        [Paragraph(honale_bio, P2_BIO_BODY)],
        [Spacer(1, 4)],
        [honale_info_table]
    ]
    
    honale_outer_table = Table(honale_card_content, colWidths=[card_w - 24], hAlign='CENTER')
    honale_outer_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    honale_card_box = Table([[honale_outer_table]], colWidths=[card_w], hAlign='LEFT')
    honale_card_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FDFDFD")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0,0), (-1,-1), 16),
        ('BOTTOMPADDING', (0,0), (-1,-1), 16),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))

    # Main double-column layout table
    founders_layout = Table([[wagh_card_box, "", honale_card_box]], colWidths=[card_w, 30, card_w], hAlign='LEFT')
    founders_layout.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    founders_elements.append(founders_layout)
    story.append(KeepTogether(founders_elements))

    # ── PAGE 9: DISCLAIMER & CONTACT DETAILS ──────────────────────────────
    story.append(PageBreak())
    story.append(Spacer(1, 10))
    story.append(Paragraph("Disclaimer & Contact Details", styles["Heading"]))
    story.append(HRFlowable(width="100%", thickness=1.0, color=GOLD, spaceBefore=2, spaceAfter=15))
    
    # Office Details only (RM Contact section removed)
    office_data = [
        [
            Paragraph("<b>OFFICE ADDRESS</b>", styles["TableCellBold"])
        ],
        [
            Paragraph(
                "Samarth Wealth Pvt. Ltd.<br/>"
                "G-75/76, Eternity Commercial Premises,<br/>"
                "Teen Hath Naka Flyover,<br/>"
                "Off Lal Bahadur Shastri Marg,<br/>"
                "Kashish Park,<br/>"
                "Thane, Maharashtra – 400604<br/>"
                "Website: https://www.samarthwealth.in/<br/>"
                "Contact No.: +91 97690 99956 / +91 98195 86940",
                styles["TableCell"]
            )
        ]
    ]
    office_table = Table(office_data, colWidths=[739.89])
    office_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("LINEABOVE", (0, 0), (-1, 0), 1.5, GOLD),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, GOLD),
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(office_table)
    story.append(Spacer(1, 15))
    
    discl_text = (
        "<b>REGULATORY DISCLOSURES:</b><br/><br/>"
        "Samarth Wealth Pvt. Ltd. is an AMFI-registered Mutual Fund & Specialized Investment Fund Distributor (ARN-286847). "
        "All Mutual Funds, SIF, AIF, and PMS investments are subject to market risks. Please read all scheme-related documents "
        "carefully before investing. Past performance is not indicative of future results. Insurance is the subject matter of "
        "solicitation. For more details on risk factors, terms, and conditions, please read the sales brochure carefully "
        "before investing. Any target IRRs mentioned are based on fund manager projections and market conditions as of "
        "March/April 2026 and are not guaranteed."
    )
    story.append(Paragraph(discl_text, styles["Disclaimer"]))
    
    # Render document
    # (debug print removed)
    doc.build(story)
    print(f"[Review PDF Rebuild] PDF generated successfully at: {output_path}")
