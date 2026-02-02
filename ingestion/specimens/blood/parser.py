"""
Blood Specimen Parser
Handles parsing of blood lab results from multiple formats: PDF, image, HL7/FHIR, CSV, manual entry.
Implements safe parsing with structured error handling per PART A requirements.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import re
import json

from schemas.part_a.v1.main_schema import (
    BloodSpecimenData,
    BloodAnalyte,
    BloodPanelType,
    FileFormatEnum,
    FastingStatusEnum
)


class BloodParserError(Exception):
    """Custom exception for blood parsing errors."""
    pass


class BloodParser:
    """
    Blood specimen parser supporting multiple input formats.
    Implements safe parsing: failures store artifact and return structured errors without crashing.
    """
    
    # Standard analyte name mappings (normalize variations)
    ANALYTE_NAME_MAP = {
        # Glucose variations
        "glucose": "glucose",
        "glu": "glucose",
        "blood glucose": "glucose",
        "plasma glucose": "glucose",
        
        # Sodium
        "sodium": "sodium_na",
        "na": "sodium_na",
        "na+": "sodium_na",
        
        # Potassium
        "potassium": "potassium_k",
        "k": "potassium_k",
        "k+": "potassium_k",
        
        # Chloride
        "chloride": "chloride_cl",
        "cl": "chloride_cl",
        "cl-": "chloride_cl",
        
        # BUN/Creatinine
        "bun": "bun",
        "blood urea nitrogen": "bun",
        "urea nitrogen": "bun",
        "creatinine": "creatinine",
        "creat": "creatinine",
        
        # Calcium
        "calcium": "calcium",
        "ca": "calcium",
        "ca++": "calcium",
        
        # Lipids
        "total cholesterol": "total_cholesterol",
        "cholesterol total": "total_cholesterol",
        "chol": "total_cholesterol",
        "ldl": "ldl",
        "ldl-c": "ldl",
        "ldl cholesterol": "ldl",
        "hdl": "hdl",
        "hdl-c": "hdl",
        "hdl cholesterol": "hdl",
        "triglycerides": "triglycerides",
        "trig": "triglycerides",
        "vldl": "vldl",
        
        # CBC
        "wbc": "wbc",
        "white blood cell": "wbc",
        "hemoglobin": "hemoglobin",
        "hgb": "hemoglobin",
        "hb": "hemoglobin",
        "hematocrit": "hematocrit",
        "hct": "hematocrit",
        "platelets": "platelets",
        "plt": "platelets",
        "rbc": "rbc",
        "red blood cell": "rbc",
        "mcv": "mcv",
        "rdw": "rdw",
        
        # Liver
        "alt": "alt",
        "sgpt": "alt",
        "ast": "ast",
        "sgot": "ast",
        "alp": "alp",
        "alkaline phosphatase": "alp",
        "bilirubin total": "bilirubin_total",
        "total bilirubin": "bilirubin_total",
        "albumin": "albumin",
        "alb": "albumin",
        "total protein": "total_protein",
        
        # Endocrine
        "tsh": "tsh",
        "free t4": "free_t4",
        "ft4": "free_t4",
        "free t3": "free_t3",
        "ft3": "free_t3",
        "a1c": "a1c",
        "hba1c": "a1c",
        "hemoglobin a1c": "a1c",
        
        # Inflammation
        "crp": "crp",
        "c-reactive protein": "crp",
        "hs-crp": "hs_crp",
        "esr": "esr",
        "ferritin": "ferritin",
        
        # Vitamins/Minerals
        "vitamin d": "vitamin_d",
        "25-oh vitamin d": "vitamin_d",
        "25(oh)d": "vitamin_d",
        "b12": "b12",
        "vitamin b12": "b12",
        "folate": "folate",
        "folic acid": "folate",
        "iron": "iron",
        "magnesium": "magnesium",
        "mg": "magnesium",
    }
    
    def __init__(self):
        """Initialize parser."""
        pass
    
    def parse(
        self,
        file_path: Optional[str],
        file_content: Optional[bytes],
        source_format: FileFormatEnum,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[BloodSpecimenData, Optional[Dict[str, Any]]]:
        """
        Parse blood specimen data from any supported format.
        
        Args:
            file_path: Path to file (if applicable)
            file_content: Raw file content (if applicable)
            source_format: Format type (pdf/image/hl7/fhir/csv/manual_entry)
            metadata: Optional metadata (collection date, fasting status, etc.)
        
        Returns:
            Tuple of (BloodSpecimenData, parsing_errors_dict)
            If parsing fails, still returns structured data with errors dict
        
        Raises:
            Never crashes - always returns structured result
        """
        errors = {}
        parsing_notes = []
        
        try:
            if source_format == FileFormatEnum.CSV:
                analytes = self._parse_csv(file_path, file_content)
            elif source_format == FileFormatEnum.PDF:
                analytes, pdf_errors = self._parse_pdf(file_path, file_content)
                if pdf_errors:
                    errors['pdf_parsing'] = pdf_errors
            elif source_format == FileFormatEnum.IMAGE:
                analytes, image_errors = self._parse_image(file_path, file_content)
                if image_errors:
                    errors['image_parsing'] = image_errors
            elif source_format == FileFormatEnum.HL7:
                analytes = self._parse_hl7(file_content)
            elif source_format == FileFormatEnum.FHIR:
                analytes = self._parse_fhir(file_content)
            elif source_format == FileFormatEnum.MANUAL_ENTRY:
                # Manual entry comes pre-structured in metadata
                analytes = metadata.get('analytes', [])
            else:
                raise BloodParserError(f"Unsupported source format: {source_format}")
            
            # Detect panels
            panels = self._detect_panels(analytes)
            
            # Extract collection datetime and fasting status
            collection_datetime = self._extract_datetime(metadata)
            fasting_status = self._extract_fasting_status(metadata)
            
            # Build BloodSpecimenData
            blood_data = BloodSpecimenData(
                collection_datetime=collection_datetime,
                fasting_status=fasting_status,
                panels=panels,
                analytes=analytes,
                lab_name=metadata.get('lab_name') if metadata else None,
                lab_id=metadata.get('lab_id') if metadata else None,
                source_format=source_format,
                raw_artifact_path=file_path,
                parsing_notes='; '.join(parsing_notes) if parsing_notes else None
            )
            
            return blood_data, errors if errors else None
            
        except Exception as e:
            # Safe failure: return structured error
            errors['critical_error'] = str(e)
            parsing_notes.append(f"Critical parsing error: {str(e)}")
            
            # Return minimal valid structure
            blood_data = BloodSpecimenData(
                collection_datetime=datetime.utcnow(),
                fasting_status=FastingStatusEnum.UNKNOWN,
                panels=[],
                analytes=[],
                source_format=source_format,
                raw_artifact_path=file_path,
                parsing_notes='; '.join(parsing_notes)
            )
            
            return blood_data, errors
    
    def _parse_csv(self, file_path: Optional[str], file_content: Optional[bytes]) -> List[BloodAnalyte]:
        """Parse CSV format. Expected columns: name, value, unit, ref_low, ref_high, flag."""
        import csv
        import io
        
        analytes = []
        
        if file_content:
            content_str = file_content.decode('utf-8')
            reader = csv.DictReader(io.StringIO(content_str))
        elif file_path:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
        else:
            raise BloodParserError("No CSV content provided")
        
        for row in reader:
            name = self._normalize_analyte_name(row.get('name', '').strip())
            if not name:
                continue
            
            analyte = BloodAnalyte(
                name=name,
                value=self._safe_float(row.get('value')),
                unit=row.get('unit', '').strip() or None,
                reference_range_low=self._safe_float(row.get('ref_low')),
                reference_range_high=self._safe_float(row.get('ref_high')),
                flag=row.get('flag', '').strip() or None
            )
            analytes.append(analyte)
        
        return analytes
    
    def _parse_pdf(self, file_path: Optional[str], file_content: Optional[bytes]) -> Tuple[List[BloodAnalyte], Optional[Dict]]:
        """
        Parse PDF lab report.
        This is a stub - full implementation would use pdfplumber or similar.
        Returns empty list with note for now.
        """
        errors = {'not_implemented': 'PDF parsing requires pdfplumber or pypdf2 - stub implementation'}
        return [], errors
    
    def _parse_image(self, file_path: Optional[str], file_content: Optional[bytes]) -> Tuple[List[BloodAnalyte], Optional[Dict]]:
        """
        Parse image lab report using OCR.
        This is a stub - full implementation would use pytesseract or cloud OCR.
        Returns empty list with note for now.
        """
        errors = {'not_implemented': 'Image OCR parsing requires pytesseract - stub implementation'}
        return [], errors
    
    def _parse_hl7(self, file_content: Optional[bytes]) -> List[BloodAnalyte]:
        """
        Parse HL7 format lab results.
        This is a stub - full implementation would use hl7apy or python-hl7.
        """
        # Stub: would parse HL7 OBX segments
        return []
    
    def _parse_fhir(self, file_content: Optional[bytes]) -> List[BloodAnalyte]:
        """
        Parse FHIR JSON format.
        Looks for Observation resources with lab values.
        """
        try:
            fhir_data = json.loads(file_content.decode('utf-8'))
            analytes = []
            
            # Handle both single Observation and Bundle of Observations
            observations = []
            if fhir_data.get('resourceType') == 'Observation':
                observations = [fhir_data]
            elif fhir_data.get('resourceType') == 'Bundle':
                observations = [entry['resource'] for entry in fhir_data.get('entry', []) 
                               if entry.get('resource', {}).get('resourceType') == 'Observation']
            
            for obs in observations:
                name = self._extract_fhir_observation_name(obs)
                if not name:
                    continue
                
                value, unit = self._extract_fhir_value(obs)
                ref_low, ref_high = self._extract_fhir_reference_range(obs)
                
                analyte = BloodAnalyte(
                    name=self._normalize_analyte_name(name),
                    value=value,
                    unit=unit,
                    reference_range_low=ref_low,
                    reference_range_high=ref_high
                )
                analytes.append(analyte)
            
            return analytes
            
        except Exception as e:
            raise BloodParserError(f"FHIR parsing error: {str(e)}")
    
    def _extract_fhir_observation_name(self, obs: Dict) -> Optional[str]:
        """Extract observation name from FHIR code."""
        code = obs.get('code', {})
        # Try display text first, then code
        return code.get('text') or code.get('coding', [{}])[0].get('display') or code.get('coding', [{}])[0].get('code')
    
    def _extract_fhir_value(self, obs: Dict) -> Tuple[Optional[float], Optional[str]]:
        """Extract value and unit from FHIR valueQuantity."""
        value_qty = obs.get('valueQuantity', {})
        return self._safe_float(value_qty.get('value')), value_qty.get('unit')
    
    def _extract_fhir_reference_range(self, obs: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Extract reference range from FHIR referenceRange."""
        ref_range = obs.get('referenceRange', [{}])[0] if obs.get('referenceRange') else {}
        low = self._safe_float(ref_range.get('low', {}).get('value'))
        high = self._safe_float(ref_range.get('high', {}).get('value'))
        return low, high
    
    def _normalize_analyte_name(self, name: str) -> str:
        """Normalize analyte name to standard form."""
        name_lower = name.lower().strip()
        return self.ANALYTE_NAME_MAP.get(name_lower, name_lower)
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _detect_panels(self, analytes: List[BloodAnalyte]) -> List[BloodPanelType]:
        """Detect which panels are present based on analytes."""
        panels = set()
        analyte_names = {a.name for a in analytes}
        
        # Metabolic/CMP markers
        cmp_markers = {'glucose', 'sodium_na', 'potassium_k', 'chloride_cl', 'bun', 'creatinine'}
        if len(analyte_names & cmp_markers) >= 3:
            panels.add(BloodPanelType.METABOLIC_CMP)
        
        # CBC markers
        cbc_markers = {'wbc', 'hemoglobin', 'hematocrit', 'platelets', 'rbc'}
        if len(analyte_names & cbc_markers) >= 3:
            panels.add(BloodPanelType.CBC)
        
        # Lipid markers
        lipid_markers = {'total_cholesterol', 'ldl', 'hdl', 'triglycerides'}
        if len(analyte_names & lipid_markers) >= 2:
            panels.add(BloodPanelType.LIPID)
        
        # Endocrine markers
        endo_markers = {'tsh', 'free_t4', 'free_t3', 'a1c'}
        if len(analyte_names & endo_markers) >= 1:
            panels.add(BloodPanelType.ENDOCRINE)
        
        # Inflammation markers
        inflam_markers = {'crp', 'hs_crp', 'esr', 'ferritin'}
        if len(analyte_names & inflam_markers) >= 1:
            panels.add(BloodPanelType.INFLAMMATION)
        
        # Vitamins/Minerals
        vitamin_markers = {'vitamin_d', 'b12', 'folate', 'iron', 'magnesium'}
        if len(analyte_names & vitamin_markers) >= 1:
            panels.add(BloodPanelType.VITAMINS_MINERALS)
        
        return list(panels) if panels else [BloodPanelType.CUSTOM]
    
    def _extract_datetime(self, metadata: Optional[Dict]) -> datetime:
        """Extract collection datetime from metadata."""
        if not metadata:
            return datetime.utcnow()
        
        dt_str = metadata.get('collection_datetime') or metadata.get('collection_date')
        if not dt_str:
            return datetime.utcnow()
        
        # Try parsing various datetime formats
        if isinstance(dt_str, datetime):
            return dt_str
        
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%SZ']:
            try:
                return datetime.strptime(str(dt_str), fmt)
            except ValueError:
                continue
        
        return datetime.utcnow()
    
    def _extract_fasting_status(self, metadata: Optional[Dict]) -> FastingStatusEnum:
        """Extract fasting status from metadata."""
        if not metadata:
            return FastingStatusEnum.UNKNOWN
        
        fasting = metadata.get('fasting_status', '').lower()
        if 'fast' in fasting or fasting == 'true':
            return FastingStatusEnum.FASTING
        elif 'non' in fasting or fasting == 'false':
            return FastingStatusEnum.NON_FASTING
        else:
            return FastingStatusEnum.UNKNOWN


def parse_blood_specimen(
    file_path: Optional[str] = None,
    file_content: Optional[bytes] = None,
    source_format: FileFormatEnum = FileFormatEnum.MANUAL_ENTRY,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[BloodSpecimenData, Optional[Dict[str, Any]]]:
    """
    Convenience function for parsing blood specimens.
    Returns (BloodSpecimenData, errors_dict)
    """
    parser = BloodParser()
    return parser.parse(file_path, file_content, source_format, metadata)
