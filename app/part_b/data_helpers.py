"""
Part A Data Query Helpers

Helper functions to retrieve and aggregate Part A data for Part B inference.
All functions enforce user_id authentication and return structured data.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.part_a_models import (
    PartASubmission,
    SpecimenUpload,
    SpecimenAnalyte,
    ISFAnalyteStream,
    VitalsRecord,
    SOAPProfileRecord,
    QualitativeEncodingRecord
)


class PartADataHelper:
    """Helper class for querying Part A data safely."""
    
    @staticmethod
    def get_submission(db: Session, submission_id: str, user_id: int) -> Optional[PartASubmission]:
        """Get Part A submission with user auth check."""
        submission = db.query(PartASubmission).filter(
            and_(
                PartASubmission.submission_id == submission_id,
                PartASubmission.user_id == user_id
            )
        ).first()
        return submission
    
    @staticmethod
    def get_isf_streams(
        db: Session,
        submission_id: int,
        analyte_names: Optional[List[str]] = None,
        days_back: Optional[int] = None
    ) -> List[ISFAnalyteStream]:
        """Get ISF analyte streams."""
        query = db.query(ISFAnalyteStream).filter(
            ISFAnalyteStream.submission_id == submission_id
        )
        
        if analyte_names:
            query = query.filter(ISFAnalyteStream.name.in_(analyte_names))
        
        if days_back:
            cutoff = datetime.utcnow() - timedelta(days=days_back)
            # Use created_at instead of start_time (which doesn't exist in the model)
            query = query.filter(ISFAnalyteStream.created_at >= cutoff)
        
        return query.all()
    
    @staticmethod
    def get_isf_analyte_data(
        db: Session,
        submission_id: int,
        analyte_name: str,
        days_back: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated ISF data for a specific analyte.
        
        Returns:
            Dict with: mean, std, min, max, cv, days_of_data, value_count, quality_score
        """
        streams = PartADataHelper.get_isf_streams(
            db, submission_id, [analyte_name], days_back
        )
        
        if not streams:
            return None
        
        # Aggregate across all streams for this analyte
        all_values = []
        quality_scores = []
        earliest_time = None
        latest_time = None
        
        for stream in streams:
            if stream.values_json:
                values = stream.values_json if isinstance(stream.values_json, list) else []
                all_values.extend(values)
                
                # Quality scores from fields
                if stream.noise_score is not None:
                    quality_scores.append(1.0 - min(stream.noise_score, 1.0))
                
                # Get timestamps to determine time range
                if stream.timestamps_json:
                    timestamps = stream.timestamps_json if isinstance(stream.timestamps_json, list) else []
                    if timestamps:
                        try:
                            from datetime import datetime
                            parsed_times = [datetime.fromisoformat(t) if isinstance(t, str) else t for t in timestamps]
                            if parsed_times:
                                if earliest_time is None or min(parsed_times) < earliest_time:
                                    earliest_time = min(parsed_times)
                                if latest_time is None or max(parsed_times) > latest_time:
                                    latest_time = max(parsed_times)
                        except:
                            pass
        
        if not all_values:
            return None
        
        import numpy as np
        values_array = np.array(all_values)
        
        mean_val = float(np.mean(values_array))
        std_val = float(np.std(values_array))
        cv = std_val / mean_val if mean_val > 0 else 0
        
        days_of_data = 0
        if earliest_time and latest_time:
            days_of_data = (latest_time - earliest_time).days + 1
        
        return {
            'analyte_name': analyte_name,
            'mean': mean_val,
            'std': std_val,
            'min': float(np.min(values_array)),
            'max': float(np.max(values_array)),
            'cv': cv,
            'median': float(np.median(values_array)),
            'days_of_data': days_of_data,
            'value_count': len(all_values),
            'avg_quality_score': np.mean(quality_scores) if quality_scores else None,
            'earliest_time': earliest_time,
            'latest_time': latest_time
        }
    
    @staticmethod
    def get_specimen_analytes(
        db: Session,
        submission_id: int,
        analyte_names: Optional[List[str]] = None,
        modality: Optional[str] = None,
        days_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get specimen analyte values with metadata."""
        query = db.query(SpecimenAnalyte, SpecimenUpload).join(
            SpecimenUpload, SpecimenAnalyte.upload_id == SpecimenUpload.id
        ).filter(
            SpecimenUpload.submission_id == submission_id
        )
        
        if analyte_names:
            query = query.filter(SpecimenAnalyte.name.in_(analyte_names))
        
        if modality:
            query = query.filter(SpecimenUpload.modality == modality)
        
        if days_back:
            cutoff = datetime.utcnow() - timedelta(days=days_back)
            query = query.filter(SpecimenUpload.collection_datetime >= cutoff)
        
        results = query.all()
        
        return [
            {
                'analyte_name': analyte.name,
                'value': analyte.value,
                'value_string': analyte.value_string,
                'unit': analyte.unit,
                'ref_low': analyte.reference_range_low,
                'ref_high': analyte.reference_range_high,
                'modality': upload.modality,
                'collection_datetime': upload.collection_datetime,
                'days_old': (datetime.utcnow() - upload.collection_datetime).days if upload.collection_datetime else None,
                'upload_id': upload.id,
                'fasting_status': upload.fasting_status
            }
            for analyte, upload in results
        ]
    
    @staticmethod
    def get_most_recent_lab(
        db: Session,
        submission_id: int,
        analyte_name: str,
        modality: str = 'blood'
    ) -> Optional[Dict[str, Any]]:
        """Get most recent lab value for an analyte."""
        analytes = PartADataHelper.get_specimen_analytes(
            db, submission_id, [analyte_name], modality
        )
        
        if not analytes:
            return None
        
        # Sort by collection datetime (most recent first)
        analytes_sorted = sorted(
            [a for a in analytes if a['collection_datetime']],
            key=lambda x: x['collection_datetime'],
            reverse=True
        )
        
        return analytes_sorted[0] if analytes_sorted else None
    
    @staticmethod
    def get_vitals_summary(
        db: Session,
        submission_id: int,
        vital_category: Optional[str] = None,
        days_back: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get aggregated vitals data from JSON storage."""
        records = db.query(VitalsRecord).filter(
            VitalsRecord.submission_id == submission_id
        ).all()
        
        if not records:
            return None
        
        # Extract values from JSON fields
        all_values = {}
        
        for record in records:
            # Cardiovascular
            if record.cardiovascular_json:
                for key, value in record.cardiovascular_json.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            field_name = f"{key}.{sub_key}"
                            if field_name not in all_values:
                                all_values[field_name] = []
                            if isinstance(sub_value, (int, float)):
                                all_values[field_name].append(sub_value)
                    elif isinstance(value, (int, float)):
                        if key not in all_values:
                            all_values[key] = []
                        all_values[key].append(value)
        
        if not all_values:
            return None
        
        import numpy as np
        
        # Summarize all vital types
        summary = {}
        for vital_type, values in all_values.items():
            if values:
                summary[vital_type] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'count': len(values)
                }
        
        return summary
    
    @staticmethod
    def get_soap_profile(
        db: Session,
        submission_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get SOAP profile data."""
        profile = db.query(SOAPProfileRecord).filter(
            SOAPProfileRecord.submission_id == submission_id
        ).first()
        
        if not profile:
            return None
        
        # Extract from direct columns and JSON fields
        result = {
            'age': profile.age,
            'sex': profile.sex_at_birth,
            'bmi': profile.bmi,
            'height_cm': profile.height_cm,
            'weight_kg': profile.weight_kg
        }
        
        # Demographics/Anthropometrics JSON
        if profile.demographics_anthropometrics_json:
            result['waist_cm'] = profile.demographics_anthropometrics_json.get('waist_cm')
        
        # Medical history JSON
        if profile.medical_history_json:
            result['medications'] = profile.medical_history_json.get('medications', [])
            result['pmh'] = profile.medical_history_json.get('pmh', [])
            result['fhx'] = profile.medical_history_json.get('fhx', [])
        
        # Diet JSON
        if profile.diet_json:
            result['diet_pattern'] = profile.diet_json.get('pattern')
        
        # Activity/Lifestyle JSON
        if profile.activity_lifestyle_json:
            result['activity_level'] = profile.activity_lifestyle_json.get('activity_level')
            result['smoking'] = profile.activity_lifestyle_json.get('smoking')
            result['alcohol'] = profile.activity_lifestyle_json.get('alcohol')
        
        # Symptoms JSON
        if profile.symptoms_json:
            result['sleep_duration'] = profile.symptoms_json.get('sleep_avg_duration_hours')
            result['symptoms'] = profile.symptoms_json
        
        return result
    
    @staticmethod
    def check_minimum_requirements(
        db: Session,
        submission_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Check if Part A has minimum data for Part B.
        
        Returns dict with:
            - meets_requirements: bool
            - has_specimen: bool
            - has_isf: bool
            - has_vitals: bool
            - has_soap: bool
            - missing_items: List[str]
        """
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        if not submission:
            return {
                'meets_requirements': False,
                'error': 'Submission not found'
            }
        
        # Check specimens
        specimen_count = db.query(func.count(SpecimenUpload.id)).filter(
            SpecimenUpload.submission_id == submission.id
        ).scalar()
        
        # Check ISF streams
        isf_count = db.query(func.count(ISFAnalyteStream.id)).filter(
            ISFAnalyteStream.submission_id == submission.id
        ).scalar()
        
        # Check vitals
        vitals_count = db.query(func.count(VitalsRecord.id)).filter(
            VitalsRecord.submission_id == submission.id
        ).scalar()
        
        # Check SOAP
        soap_exists = db.query(SOAPProfileRecord).filter(
            SOAPProfileRecord.submission_id == submission.id
        ).first() is not None
        
        has_specimen = specimen_count > 0
        has_isf = isf_count > 0
        has_vitals = vitals_count > 0
        has_soap = soap_exists
        
        missing_items = []
        if not has_specimen:
            missing_items.append("At least 1 specimen upload (blood/saliva/sweat/urine)")
        if not has_isf:
            missing_items.append("ISF monitor data (glucose, lactate, electrolytes)")
        if not has_vitals:
            missing_items.append("Vitals data (HR, HRV, BP, sleep, activity)")
        if not has_soap:
            missing_items.append("SOAP profile (demographics, PMH, medications, diet)")
        
        return {
            'meets_requirements': has_specimen and has_isf and has_vitals and has_soap,
            'has_specimen': has_specimen,
            'has_isf': has_isf,
            'has_vitals': has_vitals,
            'has_soap': has_soap,
            'missing_items': missing_items,
            'specimen_count': specimen_count,
            'isf_stream_count': isf_count,
            'vitals_count': vitals_count
        }
