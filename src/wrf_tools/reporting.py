"""Machine-readable summaries for batch post-processing."""
from __future__ import annotations
from pathlib import Path
import json
import html

def dataset_summary(dataset):
    return {"dimensions": dict(dataset.sizes), "variables": sorted(dataset.data_vars), "coordinates": sorted(dataset.coords), "attributes": dict(dataset.attrs)}

def write_json_report(report, path):
    target = Path(path)
    target.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return target

def comparison_report(model, observation, *, labels=None):
    from .validation import comparison_summary
    report={"statistics":comparison_summary(model,observation),"count":int(len(model))}
    if labels is not None: report["labels"]=list(labels)
    return report

def provenance(*, inputs, configuration=None, software_version=None):
    return {"inputs":[str(Path(item).resolve()) for item in inputs],"configuration":configuration or {},"software_version":software_version}

def write_html_report(report, path, *, title="WRF Tools case report", figures=()):
    target=Path(path); sections=[]
    for heading,value in report.items():
        content=html.escape(json.dumps(value,indent=2,default=str))
        sections.append(f"<section><h2>{html.escape(str(heading).replace('_',' ').title())}</h2><pre>{content}</pre></section>")
    images="".join(f'<figure><img src="{html.escape(Path(item).name)}"><figcaption>{html.escape(Path(item).stem.replace("_"," ").title())}</figcaption></figure>' for item in figures)
    document=f'''<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title><style>body{{font:15px Arial,sans-serif;max-width:1100px;margin:2rem auto;color:#17202a}}h1{{color:#154360}}h2{{border-bottom:2px solid #5dade2;padding-bottom:.3rem}}pre{{background:#f4f6f7;padding:1rem;white-space:pre-wrap}}figure{{margin:2rem 0}}img{{max-width:100%;height:auto}}figcaption{{font-weight:bold;text-align:center}}</style></head><body><h1>{html.escape(title)}</h1>{''.join(sections)}<h2>Figures</h2>{images}</body></html>'''
    target.write_text(document,encoding="utf-8"); return target

def write_pdf_report(report, path, *, title="WRF Tools case report", figures=()):
    """Create a paginated PDF report; requires the optional report dependency."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
    except ImportError as exc:
        raise ImportError("PDF reports require: pip install wrf-tools[report]") from exc
    target=Path(path); styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name="FigureCaption",parent=styles["BodyText"],alignment=TA_CENTER,spaceAfter=10,fontSize=9,textColor=colors.HexColor("#34495E")))
    cell_style=ParagraphStyle(name="ReportCell",parent=styles["BodyText"],fontSize=7,leading=9,wordWrap="CJK")
    header_style=ParagraphStyle(name="ReportHeader",parent=cell_style,textColor=colors.white,fontName="Helvetica-Bold")
    story=[Paragraph(title,styles["Title"]),Spacer(1,.4*cm)]
    def simple_rows(value):
        if not isinstance(value,dict): return [["Value",str(value)]]
        rows=[]
        for key,item in value.items():
            if isinstance(item,(dict,list,tuple)):
                text=json.dumps(item,default=str)
                if len(text)>220: text=text[:217]+"..."
            else: text=str(item)
            rows.append([Paragraph(html.escape(str(key).replace("_"," ").title()),cell_style),Paragraph(html.escape(text),cell_style)])
        return rows
    for heading,value in report.items():
        if heading == "temporal":
            story.append(PageBreak())
        story.append(Paragraph(str(heading).replace("_"," ").title(),styles["Heading1"]))
        table=Table([[Paragraph("Item",header_style),Paragraph("Result",header_style)]]+simple_rows(value),colWidths=[5*cm,11.5*cm],repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#154360")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.25,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4F6F7")]),("FONTSIZE",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5)]))
        story.extend([table,Spacer(1,.35*cm)])
    if figures: story.extend([PageBreak(),Paragraph("Diagnostic figures",styles["Heading1"])])
    for figure in figures:
        image=Image(str(figure)); image._restrictSize(16.5*cm,10.8*cm)
        caption=Path(figure).stem.replace("_"," ").title()
        story.append(KeepTogether([image,Paragraph(caption,styles["FigureCaption"]),Spacer(1,.25*cm)]))
    def footer(canvas,document):
        canvas.saveState(); canvas.setFont("Helvetica",8); canvas.setFillColor(colors.grey)
        canvas.drawString(2*cm,1.1*cm,"Generated by wrf-tools"); canvas.drawRightString(A4[0]-2*cm,1.1*cm,f"Page {document.page}"); canvas.restoreState()
    document=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=1.8*cm,leftMargin=1.8*cm,topMargin=1.7*cm,bottomMargin=1.7*cm,title=title)
    document.build(story,onFirstPage=footer,onLaterPages=footer); return target
