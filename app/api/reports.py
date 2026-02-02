"""
Reports API: Generate PDF reports from run data.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from app.db.session import get_db
from app.models import User, RawSensorData, CalibratedFeatures, InferenceResult
from app.api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


class PDFReportRequest(BaseModel):
    """Request to generate PDF report."""
    raw_id: Optional[int] = None
    calibrated_id: Optional[int] = None
    trace_id: Optional[str] = None
    
    @model_validator(mode='after')
    def check_at_least_one_id(self):
        if not self.raw_id and not self.calibrated_id and not self.trace_id:
            raise ValueError("At least one of raw_id, calibrated_id, or trace_id must be provided")
        return self


def generate_pdf_report(
    raw_id: Optional[int] = None,
    calibrated_id: Optional[int] = None,
    trace_id: Optional[str] = None,
    user_id: int = None,
    db: Session = None,
) -> bytes:
    """
    Generate a PDF report from run data.
    Returns PDF bytes.
    """
    # Create PDF in memory
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    
    # Collect elements to add to PDF
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#003366'),
        spaceAfter=30,
    )
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph("MONITOR MVP Report", title_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Header info
    report_date = datetime.utcnow().isoformat()
    elements.append(Paragraph(f"<b>Generated:</b> {report_date}", normal_style))
    elements.append(Paragraph(f"<b>User ID:</b> {user_id}", normal_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Raw data section
    if raw_id:
        raw_data = db.query(RawSensorData).filter(
            RawSensorData.id == raw_id,
            RawSensorData.user_id == user_id,
        ).first()
        
        if raw_data:
            elements.append(Paragraph("Raw Data Summary", heading_style))
            raw_table_data = [
                ["Field", "Value"],
                ["Raw ID", str(raw_data.id)],
                ["Timestamp", str(raw_data.timestamp)],
                ["Sensor Value 1", f"{raw_data.sensor_value_1:.4f}"],
                ["Sensor Value 2", f"{raw_data.sensor_value_2:.4f}"],
                ["Sensor Value 3", f"{raw_data.sensor_value_3:.4f}"],
            ]
            raw_table = Table(raw_table_data, colWidths=[2 * inch, 3 * inch])
            raw_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(raw_table)
            elements.append(Spacer(1, 0.3 * inch))
    
    # Preprocessing / Calibration section
    if calibrated_id:
        cal_data = db.query(CalibratedFeatures).filter(
            CalibratedFeatures.id == calibrated_id,
            CalibratedFeatures.user_id == user_id,
        ).first()
        
        if cal_data:
            elements.append(Paragraph("Preprocessing / Calibration Summary", heading_style))
            cal_table_data = [
                ["Field", "Value"],
                ["Calibrated ID", str(cal_data.id)],
                ["Feature 1", f"{cal_data.feature_1:.6f}"],
                ["Feature 2", f"{cal_data.feature_2:.6f}"],
                ["Feature 3", f"{cal_data.feature_3:.6f}"],
                ["Derived Metric", f"{cal_data.derived_metric:.6f}"],
                ["Created At", str(cal_data.created_at)],
            ]
            cal_table = Table(cal_table_data, colWidths=[2 * inch, 3 * inch])
            cal_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(cal_table)
            elements.append(Spacer(1, 0.3 * inch))
    
    # Inference results section (if trace_id provided)
    if trace_id:
        # For now, just add a placeholder since we don't store trace_id in InferenceResult yet
        elements.append(Paragraph("Inference Results", heading_style))
        elements.append(Paragraph(
            f"Trace ID: {trace_id}<br/>Model: MONITOR_MVP_Inference v1.0",
            normal_style
        ))
        elements.append(Spacer(1, 0.2 * inch))
    
    # Assumptions and limitations
    elements.append(PageBreak())
    elements.append(Paragraph("Assumptions & Limitations", heading_style))
    elements.append(Paragraph("""
    <b>Assumptions:</b><br/>
    • Features have been calibrated according to system specifications<br/>
    • Input data is within expected operational range<br/>
    • Model was trained on similar specimen types<br/>
    <br/>
    <b>Limitations:</b><br/>
    • MVP model is linear and does not capture complex interactions<br/>
    • Uncertainty estimate is heuristic-based, not Bayesian<br/>
    • Limited training data in current MVP phase<br/>
    • Not suitable for clinical decision-making without external validation<br/>
    <br/>
    <b>Disclaimer:</b><br/>
    This is an MVP model for research purposes. Do not use for clinical decisions without independent validation.
    """, normal_style))
    
    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


@router.post("/pdf")
def generate_pdf(
    request: PDFReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate and return a PDF report.
    
    Accepts at least one of: raw_id, calibrated_id, or trace_id.
    Returns PDF bytes with appropriate Content-Disposition header.
    """
    try:
        pdf_bytes = generate_pdf_report(
            raw_id=request.raw_id,
            calibrated_id=request.calibrated_id,
            trace_id=request.trace_id,
            user_id=current_user.id,
            db=db,
        )
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=monitor_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}",
        )
