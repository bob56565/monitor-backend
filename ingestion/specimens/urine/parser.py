"""
Urine Specimen Parser
Handles dipstick or lab urine analysis.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from schemas.part_a.v1.main_schema import (
    UrineSpecimenData,
    UrineAnalyte,
    FileFormatEnum
)


def parse_urine_specimen(
    file_content: Optional[bytes] = None,
    source_format: FileFormatEnum = FileFormatEnum.MANUAL_ENTRY,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[UrineSpecimenData, Optional[Dict]]:
    """Parse urine specimen data."""
    try:
        if metadata and 'analytes' in metadata:
            analytes = [
                UrineAnalyte(
                    name=a['name'],
                    value=float(a['value']) if 'value' in a and a['value'] is not None else None,
                    value_string=a.get('value_string'),
                    unit=a.get('unit'),
                    reference_range_text=a.get('reference_range_text')
                )
                for a in metadata['analytes']
            ]
        else:
            analytes = []
        
        urine_data = UrineSpecimenData(
            collection_datetime=datetime.fromisoformat(metadata['collection_datetime']) if metadata and 'collection_datetime' in metadata else datetime.utcnow(),
            collection_type=metadata.get('collection_type', 'spot') if metadata else 'spot',
            analytes=analytes,
            source_format=source_format
        )
        
        return urine_data, None
        
    except Exception as e:
        return UrineSpecimenData(
            collection_datetime=datetime.utcnow(),
            collection_type='spot',
            analytes=[],
            source_format=source_format
        ), {'error': str(e)}
