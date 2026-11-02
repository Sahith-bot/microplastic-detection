"""Builds the downloadable PDF report with ReportLab."""
import io
from xml.sax.saxutils import escape
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)
from reportlab.graphics.shapes import Drawing, Rect, String
import knowledge

NAVY = colors.HexColor("#0b3c5d")
TEAL = colors.HexColor("#0f8b8d")
MINT = colors.HexColor("#e8f6f3")
LINE = colors.HexColor("#c9e4e0")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=19, textColor=colors.white, alignment=0, leading=23)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13, textColor=NAVY, spaceBefore=10, spaceAfter=6)
BODY = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9.5, leading=13.5)
SMALL = ParagraphStyle("S", parent=BODY, fontSize=8, leading=11, textColor=colors.HexColor("#4a5d66"))
CELL = ParagraphStyle("C", parent=BODY, fontSize=8.5, leading=11)


def _bar_chart(per_class, width=170 * mm):
    rows = [p for p in per_class]
    bh, gap, lab_w = 14, 6, 70
    h = len(rows) * (bh + gap) + 6
    d = Drawing(width, h)
    mx = max([p["count"] for p in rows] + [1])
    usable = width - lab_w - 40
    for i, p in enumerate(rows):
        y = h - (i + 1) * (bh + gap)
        d.add(String(0, y + 3.5, p["name"], fontName="Helvetica", fontSize=9, fillColor=NAVY))
        d.add(Rect(lab_w, y, usable, bh, fillColor=MINT, strokeColor=None))
        if p["count"]:
            d.add(Rect(lab_w, y, usable * p["count"] / mx, bh, fillColor=colors.HexColor(p["color"]), strokeColor=None))
        d.add(String(lab_w + usable + 6, y + 3.5, f'{p["count"]} ({p["percent"]}%)', fontName="Helvetica", fontSize=9, fillColor=NAVY))
    return d


def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(TEAL)
    canvas.rect(0, h - 6 * mm, w, 6 * mm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#6b7f88"))
    canvas.drawString(18 * mm, 10 * mm, "MicroPlastic Detector - YOLOv8 automated analysis")
    canvas.drawRightString(w - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(result, annotated_img):
    """annotated_img: a file path or a file-like object (JPEG/PNG bytes)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=14 * mm, bottomMargin=18 * mm, title="Microplastic Detection Report")
    s = result["summary"]
    W = doc.width
    story = []

    # Title banner
    try:
        created = datetime.fromisoformat(str(result.get("created"))).strftime("%d %b %Y, %H:%M UTC")
    except ValueError:
        created = ""
    banner = Table([[Paragraph("Microplastic Detection Report", H1)],
                    [Paragraph(f'<font color="#d9f2ee">Report ID {escape(str(result.get("id", "")))} &nbsp;|&nbsp; {created}</font>', BODY)]],
                   colWidths=[W])
    banner.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("LEFTPADDING", (0, 0), (-1, -1), 12),
                                ("TOPPADDING", (0, 0), (-1, 0), 12), ("BOTTOMPADDING", (0, -1), (-1, -1), 12)]))
    story += [banner, Spacer(1, 8)]

    # Sample details
    meta = [["Image file", result["filename"]], ["Image size", f'{result["width"]} x {result["height"]} px'],
            ["Confidence threshold", f'{result["conf"]:.2f}'], ["Detection engine", f'YOLOv8 ({result["engine"]})']]
    if result.get("sample_name"):
        meta.insert(0, ["Sample name", result["sample_name"]])
    if s.get("volume_l"):
        meta.append(["Sample volume", f'{s["volume_l"]} L'])
    mt = Table([[Paragraph(f"<b>{a}</b>", CELL), Paragraph(escape(str(b)), CELL)] for a, b in meta], colWidths=[45 * mm, W - 45 * mm])
    mt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, 0), (0, -1), MINT),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [Paragraph("Sample details", H2), mt]

    # Assessment box
    lvl_col = colors.HexColor(s["level_color"])
    lines = [f'<font size="15" color="{s["level_color"]}"><b>{s["level"]} contamination</b></font>',
             f'<b>{s["total"]}</b> microplastic particles detected'
             + (f' &nbsp;|&nbsp; dominant type: <b>{s["dominant"]}</b>' if s["dominant"] else ""),
             s["level_meaning"]]
    if s.get("per_litre") is not None:
        lines.append(f'Estimated concentration: <b>{s["per_litre"]} particles/L</b> ({s["conc_level"]})')
    box = Table([[Paragraph("<br/>".join(lines), ParagraphStyle("A", parent=BODY, leading=17))]], colWidths=[W])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.4, lvl_col), ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 8),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    thr = ", ".join(f'{t["level"]}: {"<= " + str(t["max"]) if t["max"] is not None else "more"}' for t in s["thresholds"])
    story += [Paragraph("Threshold assessment", H2), box, Spacer(1, 3),
              Paragraph(f"Thresholds used (particles per image): {thr}.", SMALL)]

    # Annotated image
    ar = result["height"] / result["width"]
    iw = min(W, 120 * mm / ar) if ar > 0 else W
    iw = min(iw, W)
    story += [Paragraph("Detected particles", H2), Image(annotated_img, width=iw, height=iw * ar)]

    # Counts
    rows = [["Type", "Count", "Share", "Avg. confidence"]]
    for p in s["per_class"]:
        rows.append([p["name"], p["count"], f'{p["percent"]}%', f'{p["avg_conf"]:.2f}' if p["avg_conf"] else "-"])
    rows.append(["Total", s["total"], "100%" if s["total"] else "0%", f'{s["mean_conf"]:.2f}' if s["mean_conf"] else "-"])
    ct = Table(rows, colWidths=[W * 0.34, W * 0.18, W * 0.2, W * 0.28])
    ct.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                            ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, -1), (-1, -1), MINT),
                            ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story += [KeepTogether([Paragraph("Summary by type", H2), _bar_chart(s["per_class"]), Spacer(1, 6), ct])]

    # Info on types found
    found = [p for p in s["per_class"] if p["count"]]
    if found:
        story += [Paragraph("About the microplastics found", H2)]
        for p in found:
            k = knowledge.INFO.get(p["label"])
            if not k:
                continue
            t = Table([[Paragraph(f'<font color="{p["color"]}"><b>{k["name"]}</b></font> &nbsp; ({p["count"]} detected)', BODY)],
                       [Paragraph(f'<b>Appearance:</b> {k["shape"]}<br/><b>Common sources:</b> {k["sources"]}<br/>'
                                  f'<b>Typical polymers:</b> {k["polymers"]}<br/><b>Why it matters:</b> {k["impact"]}<br/>'
                                  f'<b>How to reduce it:</b> {k["reduce"]}', CELL)]], colWidths=[W])
            t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINE), ("BACKGROUND", (0, 0), (-1, 0), MINT),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
            story += [KeepTogether([t]), Spacer(1, 5)]

    # Detection table
    if result["detections"]:
        story += [PageBreak(), Paragraph("Detection details", H2)]
        rows = [["#", "Type", "Confidence", "Box (x1, y1, x2, y2) px", "Size (w x h) px"]]
        for d in result["detections"]:
            b = d["box"]
            rows.append([d["id"], d["name"], f'{d["conf"]:.2f}', f"{b[0]:.0f}, {b[1]:.0f}, {b[2]:.0f}, {b[3]:.0f}",
                         f'{d["width_px"]:.0f} x {d["height_px"]:.0f}'])
        dt = Table(rows, colWidths=[W * 0.08, W * 0.2, W * 0.16, W * 0.32, W * 0.24], repeatRows=1)
        dt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                                ("GRID", (0, 0), (-1, -1), 0.3, LINE), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, MINT])]))
        story.append(dt)

    story += [Spacer(1, 10), Paragraph("Method and notes", H2),
              Paragraph(knowledge.GENERAL, BODY), Spacer(1, 4),
              Paragraph("Particles were detected automatically by a YOLOv8 object-detection model trained on labelled "
                        "microscope images of four microplastic types (fiber, film, fragment, pellet). Each detection "
                        "above the confidence threshold is counted once. Results are an automated screening estimate and "
                        "should be confirmed by spectroscopic analysis (for example FTIR or Raman) where accuracy matters.",
                        SMALL)]
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()
