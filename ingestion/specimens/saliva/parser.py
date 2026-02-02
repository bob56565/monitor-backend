"""
Saliva Specimen Parser
Handles cortisol rhythm, DHEA-S, salivary CRP, hormones.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from schemas.part_a.v1.main_schema import (
    SalivaSpecimenData,
    SalivaAnalyte,
    FileFormatEnum
)


class SalivaParser:
    """Parser for saliva specimens (spot or serial collections)."""
    
    def parse(
        self,
        file_content: Optional[bytes],
        source_format: FileFormatEnum,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[SalivaSpecimenData, Optional[Dict]]:
        """Parse saliva specimen data."""
        try:
            # For manual entry, expect metadata to contain analytes
            if source_format == FileFormatEnum.MANUAL_ENTRY and metadata:
                analytes_data = metadata.get('analytes', [])
                analytes = [
                    SalivaAnalyte(
                        name=a['name'],
                        value=float(a['value']),
                        unit=a['unit'],
                        timestamp=self._parse_timestamp(a.get('timestamp')),
                        reference_range_low=a.get('reference_range_low'),
                        reference_range_high=a.get('reference_range_high')
                    )
                    for a in analytes_data
                ]
                
                saliva_data = SalivaSpecimenData(
                    collection_type=metadata.get('collection_type', 'spot'),
                    analytes=analytes,
                    source_format=source_format
                )
                
                return saliva_data, None
            
            # For other formats, stub for now
            return SalivaSpecimenData(
                collection_type='spot',
                analytes=[],
                source_format=source_format
            ), {'warning': 'Only manual entry fully implemented'}
            
        except Exception as e:
            return SalivaSpecimenData(
                collection_type='spot',
                analytes=[],
                source_format=source_format
            ), {'error': str(e)}
    
    def _parse_timestamp(self, ts: Any) -> datetime:
        """Parse timestamp flexibly."""
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                pass
        return datetime.utcnow()


def parse_saliva_specimen(
    file_content: Optional[bytes] = None,
    source_format: FileFormatEnum = FileFormatEnum.MANUAL_ENTRY,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[SalivaSpecimenData, Optional[Dict]]:
    """Convenience function for parsing saliva specimens."""
    parser = SalivaParser()
    return parser.parse(file_content, source_format, metadata)
