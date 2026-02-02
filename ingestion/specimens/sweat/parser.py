"""
Sweat Specimen Parser
Handles Na+, K+, Cl−, sweat rate, pH, lactate, glucose.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from schemas.part_a.v1.main_schema import (
    SweatSpecimenData,
    SweatAnalyte,
    FileFormatEnum
)


def parse_sweat_specimen(
    file_content: Optional[bytes] = None,
    source_format: FileFormatEnum = FileFormatEnum.MANUAL_ENTRY,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[SweatSpecimenData, Optional[Dict]]:
    """Parse sweat specimen data."""
    try:
        if metadata and 'analytes' in metadata:
            analytes = [
                SweatAnalyte(
                    name=a['name'],
                    value=float(a['value']),
                    unit=a['unit'],
                    timestamp=datetime.fromisoformat(a['timestamp']) if 'timestamp' in a and a['timestamp'] else None,
                    reference_range_low=a.get('reference_range_low'),
                    reference_range_high=a.get('reference_range_high')
                )
                for a in metadata['analytes']
            ]
        else:
            analytes = []
        
        sweat_data = SweatSpecimenData(
            analytes=analytes,
            sweat_rate=metadata.get('sweat_rate') if metadata else None,
            osmolality=metadata.get('osmolality') if metadata else None,
            collection_datetime=datetime.fromisoformat(metadata['collection_datetime']) if metadata and 'collection_datetime' in metadata else None,
            source_format=source_format
        )
        
        return sweat_data, None
        
    except Exception as e:
        return SweatSpecimenData(
            analytes=[],
            source_format=source_format
        ), {'error': str(e)}
