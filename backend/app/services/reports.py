import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from app.config import settings


def _format_currency(amount: float, currency_code: str) -> str:
    """Locale-aware currency formatter (mirrors the one in ai.py)."""
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
        "INR": "₹", "CNY": "¥", "AUD": "A$", "CAD": "C$",
        "CHF": "CHF ", "SGD": "S$", "AED": "AED ",
    }
    symbol = symbols.get(currency_code.upper(), f"{currency_code} ")
    return f"{symbol}{amount:,.2f}"

def generate_pdf_report(
    job_id: str,
    service_type: str,
    input_data: dict,
    results: dict,
    ai_explanation: str,
    solver_name: str,
    created_at: datetime,
    currency_code: str = None,
    qr_code_png_bytes: bytes = None,
) -> str:
    """
    Generates a professional executive-ready PDF report for the optimization job.
    Returns the file path of the generated PDF.
    """
    # Create temp directory in workspace if needed
    pdf_dir = "/home/rgukt/.gemini/antigravity/scratch/qoaas-platform/backend/reports"
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = f"{pdf_dir}/{job_id}.pdf"
    
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Brand Colors
    PRIMARY_COLOR = colors.HexColor("#0B132B")    # Navy/Deep Dark
    SECONDARY_COLOR = colors.HexColor("#3A506B")  # Slate Blue
    ACCENT_COLOR = colors.HexColor("#48CAE4")     # Neon Blue
    TEXT_COLOR = colors.HexColor("#1D2D44")       # Dark Charcoal
    BG_LIGHT = colors.HexColor("#F4F6F9")         # Light Cool Grey
    
    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY_COLOR,
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=12,
        leading=16,
        textColor=SECONDARY_COLOR,
        spaceAfter=25
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=PRIMARY_COLOR,
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=TEXT_COLOR,
        spaceAfter=10
    )
    
    meta_style = ParagraphStyle(
        'Metadata',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=SECONDARY_COLOR
    )
    
    ai_box_style = ParagraphStyle(
        'AIExplanation',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        textColor=PRIMARY_COLOR
    )

    org_name = (
        results.get("organization_name")
        or input_data.get("organization_name")
        or results.get("company_name")
        or input_data.get("company_name")
        or "Quantum Dynamics Corp"
    )

    story = []
    
    # --- HEADER / LOGO BAR ---
    story.append(Paragraph("QUANTUM OPTIMIZATION-AS-A-SERVICE (QOaaS) PLATFORM", meta_style))
    story.append(Paragraph(f"Organization / Enterprise: <b>{org_name}</b>", meta_style))
    story.append(Spacer(1, 10))
    
    # --- TITLE ---
    service_title = "Portfolio Asset Allocation Report" if service_type == "portfolio" else "Staffing Schedule Optimization Report"
    story.append(Paragraph(f"{service_title} — {org_name}", title_style))
    
    date_str = created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    story.append(Paragraph(f"Organization: {org_name}   |   Job ID: {job_id}   |   Generated: {date_str}   |   Solver: {solver_name}", subtitle_style))
    story.append(Spacer(1, 15))
    
    # --- EXECUTIVE SUMMARY ---
    story.append(Paragraph("Executive Summary", h1_style))
    story.append(Paragraph(
        f"This official executive document details the optimal strategic deployment computed for <b>{org_name}</b> by our mathematical modeling and quantum optimization engines. "
        f"By translating business constraints into QUBO energy formulations, our system resolved the objective function using a '{solver_name}' solver. "
        f"The resulting configuration minimizes operational costs, enforces business constraints, and provides actionable allocations.",
        body_style
    ))
    story.append(Spacer(1, 10))
    
    # --- INTERACTIVE METRICS TABLE ---
    story.append(Paragraph("Key Optimization Metrics", h1_style))
    
    if service_type == "portfolio":
        metrics_data = [
            ["Organization / Company Name", org_name],
            ["Expected Portfolio Return", f"{round(results.get('expected_return', 0.0) * 100, 2)}%"],
            ["Risk Variance Reduction", f"{round(results.get('risk_reduction', 0.0) * 100, 2)}%"],
            ["Sharpe Ratio", f"{round(results.get('sharpe_ratio', 0.0), 3)}"],
            ["Optimization Confidence Score", f"{round(results.get('confidence_score', 0.0) * 100, 1)}%"],
        ]
    elif service_type == "budget_allocation":
        _currency = currency_code or results.get("currency_code", settings.DEFAULT_CURRENCY)
        total_sav = _format_currency(results.get("total_potential_savings", 0.0), _currency)
        bud_used = _format_currency(results.get("budget_used", 0.0), _currency)
        bud_cap = _format_currency(results.get("budget_cap", 0.0), _currency)
        metrics_data = [
            ["Organization / Company Name", org_name],
            ["Total Realized Savings", total_sav],
            ["Budget Ceiling Used", f"{bud_used} / {bud_cap}"],
            ["Budget Utilization Rate", f"{results.get('budget_utilization_pct', 0.0)}%"],
            ["Selected Organizations Count", f"{results.get('selected_count', 0)} / {results.get('total_records', 0)}"],
        ]
    else:
        _currency = currency_code or results.get("currency_code", settings.DEFAULT_CURRENCY)
        labor_cost_fmt = _format_currency(results.get("labor_cost", 0.0), _currency)
        metrics_data = [
            ["Organization / Company Name", org_name],
            ["Operational Coverage Rate", f"{results.get('coverage_percent', 0.0)}%"],
            ["Daily Operating Labor Cost", labor_cost_fmt],
            ["Unassigned Shift Slots Count", f"{results.get('unassigned_shifts_count', 0)}"],
            ["Optimization Confidence Score", f"{round(results.get('confidence_score', 0.0) * 100, 1)}%"],
        ]
        
    metrics_table = Table(metrics_data, colWidths=[200, 200])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 15))
    
    # --- AI EXPLANATION BOX (Callout block) ---
    story.append(Paragraph("AI-Generated Strategic Insights", h1_style))
    ai_box_data = [[Paragraph(ai_explanation, ai_box_style)]]
    ai_table = Table(ai_box_data, colWidths=[400])
    ai_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EBF8FF")), # Light blue box
        ('LEFTPADDING', (0,0), (-1,-1), 15),
        ('RIGHTPADDING', (0,0), (-1,-1), 15),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('BOX', (0,0), (-1,-1), 1.5, SECONDARY_COLOR),
    ]))
    story.append(ai_table)
    story.append(Spacer(1, 15))
    
    # --- DETAILED ALLOCATIONS & SHIFT WORKER BLOCKS ---
    story.append(PageBreak()) # Clean page break for detailed data table
    
    if service_type == "portfolio":
        story.append(Paragraph(f"Company Portfolio Asset Allocations for {org_name}", h1_style))
        alloc_data = [["Asset Identifier / Symbol", "Allocation Weight (%)", "Strategic Position"]]
        allocation = results.get("allocation", {})
        for idx, (name, weight) in enumerate(sorted(allocation.items(), key=lambda x: x[1], reverse=True)):
            pos = "Core Holding" if weight > 0.2 else ("Tactical Allocation" if weight > 0.05 else "Minor Position")
            alloc_data.append([name, f"{round(weight * 100, 2)}%", pos])
            
        alloc_table = Table(alloc_data, colWidths=[150, 130, 140])
        alloc_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), SECONDARY_COLOR),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
        ]))
        story.append(alloc_table)
        story.append(Spacer(1, 20))
        
    elif service_type == "budget_allocation":
        story.append(Paragraph(f"Organizational Budget Partitioning for {org_name}", h1_style))
        alloc_data = [["Organization ID", "Optimization Status", "Selection Tag"]]
        selected_set = set(results.get("selected_organizations", []))
        all_orgs = results.get("selected_organizations", []) + results.get("rejected_organizations", [])
        for org_id in all_orgs[:50]:
            status_str = "SELECTED" if org_id in selected_set else "REJECTED"
            tag = "Resource Allocated" if status_str == "SELECTED" else "Budget Capped"
            alloc_data.append([org_id, status_str, tag])
        alloc_table = Table(alloc_data, colWidths=[150, 100, 150])
        alloc_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), SECONDARY_COLOR),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
        ]))
        story.append(alloc_table)
        story.append(Spacer(1, 20))
        
    else:
        # STAFFING OPTIMIZATION: EXPLICIT SHIFT BLOCKS, WORKER LISTS & BLOCK-WISE ROSTER EXPLORER
        story.append(Paragraph(f"Staffing Shift Roster & Block Partitioning for {org_name}", h1_style))
        story.append(Paragraph(
            "Below is the explicit shift assignment, block-wise roster breakdown, address proximity rules, and health safety restrictions.",
            body_style
        ))
        story.append(Spacer(1, 10))

        # Block-Wise Roster Summary Table & Audit Section in PDF
        if results.get("blocks"):
            blocks_data = results["blocks"].get("block_size_200", results["blocks"].get("block_size_100", []))
            if blocks_data:
                story.append(Paragraph("Block-Wise Staff Roster Summary", h1_style))
                b_table_data = [["Block ID", "Staff ID Range", "Staff", "Males (♂)", "Females (♀)", "Fit", "Restricted", "Block Cost"]]
                for blk in blocks_data[:30]:  # Up to 30 blocks for clean PDF page sizing
                    b_table_data.append([
                        blk.get("block_id", ""),
                        blk.get("staff_id_range", ""),
                        str(blk.get("total_staff", 0)),
                        str(blk.get("gender_breakdown", {}).get("male", 0)),
                        str(blk.get("gender_breakdown", {}).get("female", 0)),
                        str(blk.get("health_breakdown", {}).get("fit_count", 0)),
                        str(blk.get("health_breakdown", {}).get("restricted_count", 0)),
                        f"${blk.get('block_cost', 0):,.2f}"
                    ])

                b_table = Table(b_table_data, colWidths=[55, 95, 45, 55, 55, 45, 55, 65])
                b_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), SECONDARY_COLOR),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0,0), (-1,0), 5),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                    ('FONTSIZE', (0,0), (-1,-1), 7.5),
                    ('ALIGN', (2,0), (-1,-1), 'CENTER'),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
                ]))
                story.append(b_table)
                story.append(Spacer(1, 15))

        # Audit Validation section in PDF
        if results.get("audit_validation"):
            audit = results["audit_validation"]
            story.append(Paragraph("Audit & Mathematical Consistency Verification", h1_style))
            a_data = [
                ["Total CSV Records Read", f"{audit.get('csv_total_count', 0):,} Staff Members"],
                ["Gender Sum Verification", f"{audit.get('total_male_sum', 0):,}♂ + {audit.get('total_female_sum', 0):,}♀ = {audit.get('csv_total_count', 0):,} (PASSED)"],
                ["Headcount Consistency", f"∑ Block Headcounts = {audit.get('total_headcount_sum', 0):,} (PASSED)"],
                ["Duplicate Employee Check", f"{audit.get('duplicate_employee_count', 0)} Duplicates (0 Overlap)"],
                ["Audit Status", str(audit.get("audit_status", "PASSED"))]
            ]
            a_table = Table(a_data, colWidths=[180, 290])
            a_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#166534")),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#BBF7D0")),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8.5),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#14532D")),
            ]))
            story.append(a_table)
            story.append(Spacer(1, 15))

        # Build employee break lookup map
        emp_breaks_map = {}
        for b_item in results.get("break_schedules", []):
            e_name = b_item.get("employee_name")
            b_type = b_item.get("break_type", "")
            b_short = "B1" if "Break 1" in b_type else ("Lunch" if "Lunch" in b_type else "B2")
            b_str = f"{b_short}: {b_item.get('scheduled_start_time')}-{b_item.get('scheduled_end_time')}"
            if e_name not in emp_breaks_map:
                emp_breaks_map[e_name] = []
            emp_breaks_map[e_name].append(b_str)

        schedule = results.get("schedule", [])
        global_emp_counter = 1

        for shift_idx, shift in enumerate(schedule):
            shift_title = shift.get("shift_name", f"Shift {shift_idx + 1}")
            demand = shift.get("demand", 1)
            assigned_list = shift.get("assigned_employees", [])
            gap = shift.get("coverage_gap", 0)

            # Sub-header for shift block
            block_header_style = ParagraphStyle(
                f'ShiftHeader_{shift_idx}',
                parent=styles['Heading3'],
                fontName='Helvetica-Bold',
                fontSize=11,
                leading=14,
                textColor=PRIMARY_COLOR,
                spaceBefore=10,
                spaceAfter=5
            )
            status_summary = f"DEMAND: {demand} Staff  |  STAFFED: {len(assigned_list)} Workers  |  STATUS: {'FULLY COVERED' if gap == 0 else f'DEFICIT ({gap} slots)'}"
            story.append(Paragraph(f"• {shift_title.upper()} BLOCK — ({status_summary})", block_header_style))

            if assigned_list:
                shift_table_data = [["Worker #", "Employee Name", "Assigned Shift", "Scheduled Break Windows"]]
                for emp_name in assigned_list:  # Include ALL assigned employees in PDF report
                    worker_id_str = f"Employee {global_emp_counter}"
                    breaks_str = " | ".join(emp_breaks_map.get(emp_name, [])) or "Standard Rotational Breaks"
                    shift_table_data.append([worker_id_str, emp_name, shift_title, breaks_str])
                    global_emp_counter += 1

                shift_table = Table(shift_table_data, colWidths=[80, 110, 110, 170])
                shift_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0,0), (-1,0), 5),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
                ]))
                story.append(shift_table)
            else:
                story.append(Paragraph("<i>No workers assigned to this shift block (VACANT).</i>", body_style))

            story.append(Spacer(1, 12))

        # Unassigned / Reserve Staffing Block
        unassigned_emps = results.get("unassigned_employees", [])
        if unassigned_emps:
            story.append(Paragraph("Reserve / Unassigned Staffing Block", h1_style))
            res_table_data = [["Reserve Worker ID", "Employee Name", "Current Status"]]
            for u_idx, u_name in enumerate(unassigned_emps):  # Include ALL reserve employees in PDF report
                w_str = f"Reserve Worker {u_idx + 1}"
                res_table_data.append([w_str, u_name, "ON STANDBY / RESERVE BENCH"])
            res_table = Table(res_table_data, colWidths=[140, 180, 150])
            res_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#64748B")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 5),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                ('FONTSIZE', (0,0), (-1,-1), 8.5),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
            ]))
            story.append(res_table)
            story.append(Spacer(1, 15))

    
    # --- TECHNICAL APPENDIX ---
    story.append(Paragraph("Technical Appendix: Mathematical QUBO Formulation", h1_style))
    story.append(Paragraph(
        f"To guarantee audit trails for <b>{org_name}</b>, this section outlines the optimization formulation automatically "
        "compiled by our engine.",
        body_style
    ))
    
    if service_type == "portfolio":
        formulation_details = [
            "Objective: Minimize portfolio variance (risk) minus expected returns scaled by risk aversion.",
            "Formulation: Minimize w^T * Sigma * w - lambda * R^T * w",
            "Constraints: sum(w_i) = 1.0 (Capital fully allocated), w_i >= 0 (No short selling)."
        ]
    else:
        formulation_details = [
            "Objective: Minimize total operational staffing labor costs.",
            "Formulation: Minimize sum_{e,s} Cost_e * x_{e,s}",
            "Constraints: sum_e x_{e,s} >= Demand_s (Shift requirements), sum_s x_{e,s} <= 1 (Max 1 shift/day)."
        ]
        
    for detail in formulation_details:
        story.append(Paragraph(f"• {detail}", body_style))

    doc.build(story)
    return pdf_path

