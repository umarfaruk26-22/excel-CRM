import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from PIL import Image as PILImage

from backend.app.core.config import settings

class NumberedCanvas(canvas.Canvas):
    firm_name = "Customer Follow-up CRM"

    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Footer text
        footer_text = f"{NumberedCanvas.firm_name}  •  Confidential  •  Page {self._pageNumber} of {page_count}"
        self.drawRightString(842 - 36, 20, footer_text)
        
        # Subtle footer separator line
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 32, 842 - 36, 32)
        
        self.restoreState()


class PDFService:
    @staticmethod
    def _build_branded_header(
        firm_info: Optional[Dict[str, Any]],
        report_title: str,
        filter_summary: str,
        total_records: int,
        styles: Any
    ) -> List[Any]:
        elements = []
        firm = firm_info or {}
        firm_name = firm.get("firm_name") or "Customer Follow-up CRM"
        firm_tagline = firm.get("firm_tagline") or ""
        firm_phone = firm.get("firm_phone") or ""
        firm_email = firm.get("firm_email") or ""
        firm_address = firm.get("firm_address") or ""
        firm_gst = firm.get("firm_gst") or ""
        firm_logo = firm.get("firm_logo") or ""

        # Set canvas footer branding
        NumberedCanvas.firm_name = firm_name

        # Check logo on disk
        logo_element = None
        target_w = 0
        target_h = 0
        if firm_logo:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            logo_name = Path(firm_logo).name
            candidate_paths = [
                base_dir / "storage" / "uploads" / logo_name,
                base_dir / "storage" / logo_name,
                base_dir / firm_logo.lstrip("/")
            ]
            for p in candidate_paths:
                if p.exists():
                    try:
                        with PILImage.open(p) as pimg:
                            pw, ph = pimg.size
                            aspect = pw / ph
                            target_h = 36
                            target_w = target_h * aspect
                            if target_w > 120:
                                target_w = 120
                                target_h = target_w / aspect
                            logo_element = RLImage(str(p), width=target_w, height=target_h)
                            break
                    except Exception:
                        pass

        # Left Column: Branding info
        left_flowables = []
        if logo_element:
            title_p = Paragraph(f"<font size=14 color='#1e3a8a'><b>{firm_name.upper()}</b></font>", styles['Normal'])
            logo_table = Table([[logo_element, title_p]], colWidths=[target_w + 10, 480 - target_w - 10])
            logo_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            left_flowables.append(logo_table)
        else:
            left_flowables.append(Paragraph(f"<font size=15 color='#1e3a8a'><b>{firm_name.upper()}</b></font>", styles['Normal']))

        if firm_tagline:
            left_flowables.append(Spacer(1, 2))
            left_flowables.append(Paragraph(f"<font size=8 color='#64748b'><i>{firm_tagline}</i></font>", styles['Normal']))
        
        contact_parts = []
        if firm_address: contact_parts.append(firm_address)
        if firm_phone: contact_parts.append(f"Tel: {firm_phone}")
        if firm_email: contact_parts.append(f"Email: {firm_email}")
        if firm_gst: contact_parts.append(f"GST: {firm_gst}")

        if contact_parts:
            left_flowables.append(Spacer(1, 2))
            left_flowables.append(Paragraph(f"<font size=7.5 color='#475569'>{' &nbsp;|&nbsp; '.join(contact_parts)}</font>", styles['Normal']))

        # Right Column: Report metadata
        gen_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
        right_flowables = [
            Paragraph(f"<font size=12 color='#0f172a'><b>{report_title}</b></font>", ParagraphStyle('RTitle', alignment=TA_RIGHT, fontName='Helvetica-Bold')),
            Spacer(1, 2),
            Paragraph(f"<font size=7.5 color='#475569'><b>Generated:</b> {gen_time}<br/><b>Records:</b> {total_records} &nbsp;|&nbsp; <b>Filter:</b> {filter_summary}</font>", ParagraphStyle('RMeta', alignment=TA_RIGHT, leading=10.5))
        ]

        # Top 2-Column Banner Table (width 770pt)
        top_table = Table([[left_flowables, right_flowables]], colWidths=[490, 280])
        top_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1'))
        ]))

        elements.append(top_table)
        elements.append(Spacer(1, 8))
        return elements

    @staticmethod
    def generate_calls_pdf(
        calls: List[Dict[str, Any]],
        filter_summary: str = "All Calls & Work Records",
        stats_summary: Optional[Dict[str, int]] = None,
        firm_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates a professional landscape PDF report of filtered call and completed work records.
        """
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"calls_report_{ts}.pdf"
        output_path = os.path.join(settings.EXPORT_DIR, filename)

        # Page setup: A4 Landscape with 36pt (0.5 inch) margins
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=42
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        th_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=colors.white
        )
        cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor('#1e293b')
        )
        cell_bold = ParagraphStyle(
            'TableCellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor('#0f172a')
        )
        outcome_converted = ParagraphStyle(
            'OutcomeConverted',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor('#047857')
        )
        outcome_interested = ParagraphStyle(
            'OutcomeInterested',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor('#0284c7')
        )

        elements = []

        # Branded Header
        header_elements = PDFService._build_branded_header(
            firm_info=firm_info,
            report_title="WORK & CALL ACTIVITY REPORT",
            filter_summary=filter_summary,
            total_records=len(calls),
            styles=styles
        )
        elements.extend(header_elements)

        # KPI Stats Summary Banner if available
        if stats_summary:
            kpi_data = [[
                Paragraph(f"<b>Total Logged:</b> {stats_summary.get('total', len(calls))}", cell_style),
                Paragraph(f"<b>Completed:</b> {stats_summary.get('converted', 0)}", cell_style),
                Paragraph(f"<b>Interested:</b> {stats_summary.get('interested', 0)}", cell_style),
                Paragraph(f"<b>Follow-up Scheduled:</b> {stats_summary.get('scheduled', 0)}", cell_style),
                Paragraph(f"<b>Other Outcomes:</b> {stats_summary.get('other', 0)}", cell_style)
            ]]
            kpi_table = Table(kpi_data, colWidths=[154, 154, 154, 154, 154])
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(kpi_table)
            elements.append(Spacer(1, 12))

        # Table Headers (Widths sum = 770 pt)
        col_widths = [120, 85, 80, 95, 215, 105, 70]
        table_data = [[
            Paragraph("Customer Name", th_style),
            Paragraph("Mobile", th_style),
            Paragraph("Date & Time", th_style),
            Paragraph("Work Outcome", th_style),
            Paragraph("Call / Work Notes", th_style),
            Paragraph("Next Action", th_style),
            Paragraph("Logged By", th_style)
        ]]

        for c in calls:
            raw_outcome = c.get("outcome", "-")
            out_style = cell_bold
            outcome_display = raw_outcome
            if raw_outcome == "Converted":
                out_style = outcome_converted
                outcome_display = "Completed"
            elif raw_outcome in ["Interested", "Call Back Required"]:
                out_style = outcome_interested

            table_data.append([
                Paragraph(c.get("customer_name") or "Unknown", cell_bold),
                Paragraph(c.get("customer_mobile") or "-", cell_style),
                Paragraph(c.get("call_datetime") or "-", cell_style),
                Paragraph(outcome_display, out_style),
                Paragraph(c.get("notes") or "-", cell_style),
                Paragraph(c.get("next_action") or "-", cell_style),
                Paragraph(c.get("created_by_name") or "Admin", cell_style)
            ])

        main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Alternating row styles
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]

        for i in range(1, len(table_data)):
            if i % 2 == 0:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8fafc')))
            else:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.white))

        main_table.setStyle(TableStyle(t_style))
        elements.append(main_table)

        doc.build(elements, canvasmaker=NumberedCanvas)
        return output_path

    @staticmethod
    def generate_customers_pdf(
        customers: List[Dict[str, Any]],
        filter_summary: str = "All Customers",
        firm_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates a landscape PDF of filtered customers (e.g., Converted, Interested, By File).
        """
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"customers_report_{ts}.pdf"
        output_path = os.path.join(settings.EXPORT_DIR, filename)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=42
        )

        styles = getSampleStyleSheet()

        th_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8.5,
            leading=11,
            textColor=colors.white
        )
        cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor('#1e293b')
        )
        cell_bold = ParagraphStyle(
            'TableCellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor('#0f172a')
        )

        elements = []

        # Branded Header
        header_elements = PDFService._build_branded_header(
            firm_info=firm_info,
            report_title="CUSTOMER DIRECTORY & WORK STATUS REPORT",
            filter_summary=filter_summary,
            total_records=len(customers),
            styles=styles
        )
        elements.extend(header_elements)

        # Table Widths: 770 pt total:
        # Code: 60, Name: 130, Mobile: 90, Email: 120, Company: 100, City: 75, Status: 85, Source: 110
        col_widths = [60, 130, 90, 120, 100, 75, 85, 110]
        table_data = [[
            Paragraph("Code", th_style),
            Paragraph("Customer Name", th_style),
            Paragraph("Mobile", th_style),
            Paragraph("Email", th_style),
            Paragraph("Company", th_style),
            Paragraph("City", th_style),
            Paragraph("Status", th_style),
            Paragraph("Source / File", th_style)
        ]]

        for c in customers:
            status_text = c.get("status") or "New"
            table_data.append([
                Paragraph(c.get("customer_code") or f"#{c.get('id', '')}", cell_style),
                Paragraph(c.get("name") or "Unknown", cell_bold),
                Paragraph(c.get("mobile") or "-", cell_style),
                Paragraph(c.get("email") or "-", cell_style),
                Paragraph(c.get("company") or "-", cell_style),
                Paragraph(c.get("city") or "-", cell_style),
                Paragraph(status_text, cell_bold),
                Paragraph(c.get("import_filename") or c.get("source") or "Direct", cell_style)
            ])

        main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]

        for i in range(1, len(table_data)):
            if i % 2 == 0:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8fafc')))
            else:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.white))

        main_table.setStyle(TableStyle(t_style))
        elements.append(main_table)

        doc.build(elements, canvasmaker=NumberedCanvas)
        return output_path
