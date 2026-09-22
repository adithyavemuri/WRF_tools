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
    return {"inputs":[Path(item).name for item in inputs],"configuration":configuration or {},"software_version":software_version}

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
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
    except ImportError as exc:
        raise ImportError("PDF reports require: pip install wrf-tools[report]") from exc
    target=Path(path); styles=getSampleStyleSheet(); navy=colors.HexColor("#12344D"); blue=colors.HexColor("#1976A3"); pale=colors.HexColor("#EAF2F7")
    styles["Title"].textColor=navy; styles["Title"].fontSize=25; styles["Title"].leading=30
    styles["Heading1"].textColor=navy; styles["Heading1"].spaceBefore=8; styles["Heading1"].spaceAfter=8
    styles["Heading2"].textColor=blue
    styles.add(ParagraphStyle(name="Subtitle",parent=styles["BodyText"],alignment=TA_CENTER,fontSize=12,leading=17,textColor=colors.HexColor("#456778")))
    styles.add(ParagraphStyle(name="FigureCaption",parent=styles["BodyText"],alignment=TA_CENTER,spaceAfter=10,fontSize=9,textColor=colors.HexColor("#34495E")))
    styles.add(ParagraphStyle(name="Callout",parent=styles["BodyText"],fontSize=9,leading=13,borderColor=blue,borderWidth=1,borderPadding=8,backColor=pale))
    cell_style=ParagraphStyle(name="ReportCell",parent=styles["BodyText"],fontSize=7,leading=9,wordWrap="CJK")
    header_style=ParagraphStyle(name="ReportHeader",parent=cell_style,textColor=colors.white,fontName="Helvetica-Bold")
    story=[]
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
    def table_for(rows, widths=(7.2*cm,9.3*cm)):
        cooked=[[Paragraph("Parameter",header_style),Paragraph("Result",header_style)]]
        for key,value in rows:
            cooked.append([Paragraph(html.escape(str(key)),cell_style),Paragraph(html.escape(str(value)),cell_style)])
        table=Table(cooked,colWidths=list(widths),repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),navy),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.3,colors.HexColor("#AAB7C4")),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F3F7F9")]),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        return table
    def comparison_table(domains, rows):
        names=list(domains)
        cooked=[[Paragraph("Parameter",header_style)]+[Paragraph(name.upper(),header_style) for name in names]]
        for label,extractor in rows:
            cooked.append([Paragraph(html.escape(str(label)),cell_style)]+[Paragraph(html.escape(str(extractor(domains[name]))),cell_style) for name in names])
        widths=[6.5*cm]+[10*cm/len(names)]*len(names)
        table=Table(cooked,colWidths=widths,repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),navy),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.3,colors.HexColor("#AAB7C4")),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F3F7F9")]),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        return table

    if "domains" in report:
        overview=report.get("overview",{}); domains=report["domains"]
        story.extend([Spacer(1,1.4*cm),Paragraph(title,styles["Title"]),Spacer(1,.25*cm),Paragraph("Reproducible mesoscale hindcast and wind-resource screening",styles["Subtitle"]),Spacer(1,.8*cm)])
        story.append(table_for([
            ("Simulation period",f"{overview.get('start_time')} to {overview.get('end_time')} UTC"),
            ("Domains",overview.get("domain_count")),
            ("Primary analysis domain",overview.get("analysis_domain")),
            ("Outputs per domain",overview.get("file_count_per_domain")),
            ("Report scope","Meteorology, surface fluxes, precipitation, PBL and 10 m wind-resource screening"),
        ]))
        story.extend([Spacer(1,.5*cm),Paragraph("Interpretation boundary",styles["Heading2"]),Paragraph("This technical report verifies model output and summarizes the simulated period. It is not a climatology, validation against observations, bankable wind-resource assessment, or substitute for physics sensitivity testing.",styles["Callout"])])
        layout=next((Path(item) for item in figures if Path(item).name=="domain_layout.png"),None)
        if layout:
            story.extend([Spacer(1,.5*cm),Image(str(layout),width=15.5*cm,height=11.4*cm),Paragraph("Figure 1. Computational-domain boundaries and nominal grid spacing.",styles["FigureCaption"])])
        story.extend([PageBreak(),Paragraph("Domain configuration comparison",styles["Title"]),Spacer(1,.3*cm)])
        temporal=overview.get("domain_time_steps_seconds",{})
        story.extend([Paragraph("Temporal configuration",styles["Heading1"]),table_for([
            ("ERA5 forcing interval",f"{overview.get('forcing_interval_seconds')} seconds (hourly)"),
            ("WRF output interval",f"{overview.get('history_interval_minutes')} minutes"),
            ("Integration timestep",", ".join(f"{name.upper()}: {value:g} seconds" for name,value in temporal.items())),
            ("Restart checkpoint interval",f"{overview.get('restart_interval_minutes')} minutes"),
            ("Resumed from",overview.get("resumed_from") or "Fresh initialization"),
        ])])
        grid_rows=[("Grid ID",lambda s:s["grid"].get("domain_id")),("Horizontal grid",lambda s:f"{s['grid'].get('west_east')} x {s['grid'].get('south_north')}"),("Spacing",lambda s:f"{s['grid'].get('dx_metres'):g} x {s['grid'].get('dy_metres'):g} m"),("Vertical levels",lambda s:s["grid"].get("vertical_levels")),("Output times",lambda s:s["file_count"])]
        story.extend([Spacer(1,.25*cm),Paragraph("Grid",styles["Heading1"]),comparison_table(domains,grid_rows)])
        physics_keys=list(next(iter(domains.values())).get("physics",{}))
        story.extend([Spacer(1,.35*cm),Paragraph("Physics suite",styles["Heading1"]),comparison_table(domains,[(key.replace("_"," ").upper(),lambda s,key=key:s.get("physics",{}).get(key)) for key in physics_keys])])
        wind_labels={"height_metres":"Diagnostic height (m)","mean_speed_m_s":"Mean wind speed (m s-1)","maximum_speed_m_s":"Maximum wind speed (m s-1)","p50_speed_m_s":"P50 wind speed (m s-1)","p90_speed_m_s":"P90 wind speed (m s-1)","p95_speed_m_s":"P95 wind speed (m s-1)","mean_direction_degrees":"Mean direction (degrees)","mean_air_density_kg_m3":"Mean air density (kg m-3)","mean_power_density_w_m2":"Mean wind-power density (W m-2)"}
        story.extend([PageBreak(),Paragraph("Domain results comparison",styles["Title"]),Paragraph("Wind-resource screening",styles["Heading1"]),comparison_table(domains,[(label,lambda s,key=key:f"{s.get('wind_resource',{}).get(key,float('nan')):.2f}") for key,label in wind_labels.items()])])
        vertical_rows=[("Shear fit layer",lambda s:f"{s.get('vertical_diagnostics',{}).get('shear_fit_layer_metres',[None,None])[0]}-{s.get('vertical_diagnostics',{}).get('shear_fit_layer_metres',[None,None])[1]} m"),("Mean shear exponent",lambda s:f"{s.get('vertical_diagnostics',{}).get('mean_shear_exponent'):.3f}" if s.get('vertical_diagnostics',{}).get('mean_shear_exponent') is not None else "unavailable"),("TKE diagnostic",lambda s:f"{s.get('vertical_diagnostics',{}).get('tke_status','unavailable')} ({s.get('vertical_diagnostics',{}).get('tke_variable') or 'no variable'})")]
        story.extend([Spacer(1,.3*cm),Paragraph("Vertical-profile diagnostics",styles["Heading1"]),comparison_table(domains,vertical_rows)])
        variables=list(next(iter(domains.values())).get("surface_statistics",{}))
        metric_rows=[]
        for variable in variables:
            metric_rows.append((variable,lambda s,variable=variable:f"{s['surface_statistics'][variable]['mean']:.3g} {s['surface_statistics'][variable].get('units','')} (min {s['surface_statistics'][variable]['minimum']:.3g}; max {s['surface_statistics'][variable]['maximum']:.3g})"))
        story.extend([Spacer(1,.35*cm),Paragraph("Meteorological means and ranges",styles["Heading1"]),comparison_table(domains,metric_rows)])
        qc_rows=[("QC status",lambda s:s["quality_control"].get("status")),("Errors",lambda s:s["quality_control"].get("error_count")),("Warnings",lambda s:s["quality_control"].get("warning_count"))]
        story.extend([Spacer(1,.35*cm),Paragraph("Quality-control overview",styles["Heading1"]),comparison_table(domains,qc_rows)])
        for domain,summary in domains.items():
            issues=summary.get("quality_control",{}).get("issues",[])
            if issues: story.extend([Paragraph(f"{domain.upper()} QC details",styles["Heading2"]),table_for([(f"{item.get('severity')} - {item.get('variable')}",item.get("message")) for item in issues])])
        for domain,summary in domains.items():
            domain_figures=[Path(item) for item in figures if Path(item).name.startswith(f"{domain}_")]
            story.extend([PageBreak(),Paragraph(f"Domain {domain} figures",styles["Title"]),Paragraph(f"Grid ID {summary['grid'].get('domain_id')} | {summary['grid'].get('dx_metres'):g} m horizontal spacing",styles["Subtitle"])])
            for row_start in range(0,len(domain_figures),2):
                cells=[]
                for index,figure in enumerate(domain_figures[row_start:row_start+2],row_start+1):
                    image=Image(str(figure)); image._restrictSize(7.55*cm,5.15*cm)
                    caption=Paragraph(f"{domain.upper()} Figure {index}. {figure.stem.removeprefix(domain+'_').replace('_',' ').title()}.",styles["FigureCaption"])
                    cells.append([image,caption])
                while len(cells)<2: cells.append([Spacer(1,1),Spacer(1,1)])
                panel=Table([[cells[0][0],cells[1][0]],[cells[0][1],cells[1][1]]],colWidths=[8.0*cm,8.0*cm])
                panel.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
                story.append(KeepTogether(panel))
                if row_start and (row_start+2)%6==0 and row_start+2<len(domain_figures): story.append(PageBreak())
        provenance_rows=[]
        for key,value in report.get("provenance",{}).items():
            if key == "configuration" and isinstance(value,dict):
                for component,record in value.items():
                    if isinstance(record,dict):
                        provenance_rows.append((component.replace("_"," ").title(),f"{record.get('path','embedded')} | SHA-256 {record.get('sha256','unavailable')}"))
                    else:
                        provenance_rows.append((component.replace("_"," ").title(),str(record)))
            else:
                provenance_rows.append((key,json.dumps(value,default=str)))
        story.extend([PageBreak(),Paragraph("Reproducibility and provenance",styles["Heading1"]),table_for(provenance_rows)])
    else:
        story=[Paragraph(title,styles["Title"]),Spacer(1,.4*cm)]

    if "domains" not in report:
      for heading,value in report.items():
        if heading == "temporal":
            story.append(PageBreak())
        story.append(Paragraph(str(heading).replace("_"," ").title(),styles["Heading1"]))
        table=Table([[Paragraph("Item",header_style),Paragraph("Result",header_style)]]+simple_rows(value),colWidths=[5*cm,11.5*cm],repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#154360")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.25,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4F6F7")]),("FONTSIZE",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5)]))
        story.extend([table,Spacer(1,.35*cm)])
    if figures and "domains" not in report: story.extend([PageBreak(),Paragraph("Diagnostic figures",styles["Heading1"])])
    for figure in (() if "domains" in report else figures):
        image=Image(str(figure)); image._restrictSize(16.5*cm,10.8*cm)
        caption=Path(figure).stem.replace("_"," ").title()
        story.append(KeepTogether([image,Paragraph(caption,styles["FigureCaption"]),Spacer(1,.25*cm)]))
    def footer(canvas,document):
        canvas.saveState(); canvas.setFont("Helvetica",8); canvas.setFillColor(colors.grey)
        canvas.drawString(2*cm,1.1*cm,"Generated by wrf-tools"); canvas.drawRightString(A4[0]-2*cm,1.1*cm,f"Page {document.page}"); canvas.restoreState()
    document=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=1.8*cm,leftMargin=1.8*cm,topMargin=1.7*cm,bottomMargin=1.7*cm,title=title)
    document.build(story,onFirstPage=footer,onLaterPages=footer); return target
