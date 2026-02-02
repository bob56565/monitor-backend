"""
Imaging/Diagnostic Report Parser
Handles radiology, echo, ECG, sleep study reports.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from schemas.part_a.v1.main_schema import (
    ImagingReportData,
    FileFormatEnum
)


def parse_imaging_report(
    file_path: Optional[str] = None,
    file_content: Optional[bytes] = None,
    source_format: FileFormatEnum = FileFormatEnum.MANUAL_ENTRY,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[ImagingReportData, Optional[Dict]]:
    """Parse imaging/diagnostic report data."""
    try:
        imaging_data = ImagingReportData(
            report_type=metadata.get('report_type', 'other') if metadata else 'other',
            report_date=datetime.fromisoformat(metadata['report_date']) if metadata and 'report_date' in metadata else datetime.utcnow(),
            impression=metadata.get('impression') if metadata else None,
            key_measurements=metadata.get('key_measurements', {}) if metadata else {},
            severity_statements=metadata.get('severity_statements', []) if metadata else [],
            follow_up_recommendations=metadata.get('follow_up_recommendations') if metadata else None,
            source_format=source_format,
            raw_artifact_path=file_path,
            parsing_notes=metadata.get('parsing_notes') if metadata else None
        )
        
        return imaging_data, None
        
    except Exception as e:
        return ImagingReportData(
            report_type='other',
            report_date=datetime.utcnow(),
            source_format=source_format,
            raw_artifact_path=file_path
        ), {'error': str(e)}
