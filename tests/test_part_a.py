"""
PART A Integration Tests
Comprehensive tests for all PART A functionality.
"""

import pytest
from datetime import datetime
from schemas.part_a.v1.main_schema import (
    PartAInputSchema,
    SpecimenDataUpload,
    BloodSpecimenData,
    BloodAnalyte,
    ISFMonitorData,
    ISFAnalyteStream,
    SignalQuality,
    VitalsData,
    CardiovascularVitals,
    RespiratoryTemperatureVitals,
    SleepRecoveryActivityVitals,
    SOAPProfile,
    DemographicsAnthropometrics,
    MedicalHistory,
    MedicationsSupplements,
    Medication,
    DietProfile,
    ActivityLifestyle,
    Symptoms,
    QualitativeEncoding,
    FileFormatEnum,
    FastingStatusEnum,
    SpecimenModalityEnum
)

from encoding.qualitative_to_quantitative import get_encoding_registry
from ingestion.specimens.blood import parse_blood_specimen


def test_schema_validation_minimal():
    """Test minimal valid PART A schema."""
    part_a = PartAInputSchema(
        specimen_data=SpecimenDataUpload(
            modalities_selected=[SpecimenModalityEnum.BLOOD],
            blood=[BloodSpecimenData(
                collection_datetime=datetime.utcnow(),
                fasting_status=FastingStatusEnum.FASTING,
                analytes=[
                    BloodAnalyte(name="glucose", value=95.0, unit="mg/dL")
                ],
                source_format=FileFormatEnum.MANUAL_ENTRY
            )]
        ),
        isf_monitor_data=ISFMonitorData(
            core_analytes=[
                ISFAnalyteStream(
                    name="glucose",
                    values=[95.0, 96.0],
                    timestamps=[datetime.utcnow(), datetime.utcnow()],
                    unit="mg/dL"
                )
            ],
            signal_quality=SignalQuality(
                calibration_status="recent",
                sensor_drift_score=0.1,
                noise_score=0.05,
                dropout_percentage=2.0
            )
        ),
        vitals_data=VitalsData(
            cardiovascular=CardiovascularVitals(),
            respiratory_temperature=RespiratoryTemperatureVitals(),
            sleep_recovery_activity=SleepRecoveryActivityVitals()
        ),
        soap_profile=SOAPProfile(
            demographics_anthropometrics=DemographicsAnthropometrics(
                age=35,
                sex_at_birth="male",
                height_cm=175.0,
                weight_kg=75.0
            ),
            medical_history=MedicalHistory(),
            medications_supplements=MedicationsSupplements(),
            diet=DietProfile(
                pattern="mediterranean",
                sodium_intake="normal",
                hydration_intake="normal",
                caffeine="moderate",
                alcohol="low",
                meal_timing="consistent"
            ),
            activity_lifestyle=ActivityLifestyle(
                activity_level="moderate",
                sleep_schedule_consistency="consistent",
                nicotine_tobacco="none"
            ),
            symptoms=Symptoms()
        ),
        qualitative_encoding=QualitativeEncoding()
    )
    
    assert part_a.schema_version == "1.0.0"
    assert len(part_a.specimen_data.modalities_selected) >= 1


def test_schema_validation_requires_specimen():
    """Test that at least 1 specimen modality is required."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="at least 1"):
        PartAInputSchema(
            specimen_data=SpecimenDataUpload(
                modalities_selected=[],  # Empty - should fail
                blood=[]
            ),
            isf_monitor_data=ISFMonitorData(
                core_analytes=[
                    ISFAnalyteStream(
                        name="glucose",
                        values=[95.0],
                        timestamps=[datetime.utcnow()],
                        unit="mg/dL"
                    )
                ],
                signal_quality=SignalQuality(
                    calibration_status="recent",
                    sensor_drift_score=0.1,
                    noise_score=0.05,
                    dropout_percentage=2.0
                )
            ),
            vitals_data=VitalsData(
                cardiovascular=CardiovascularVitals(),
                respiratory_temperature=RespiratoryTemperatureVitals(),
                sleep_recovery_activity=SleepRecoveryActivityVitals()
            ),
            soap_profile=SOAPProfile(
                demographics_anthropometrics=DemographicsAnthropometrics(
                    age=35, sex_at_birth="male", height_cm=175.0, weight_kg=75.0
                ),
                medical_history=MedicalHistory(),
                medications_supplements=MedicationsSupplements(),
                diet=DietProfile(
                    pattern="standard", sodium_intake="normal", hydration_intake="normal",
                    caffeine="none", alcohol="none", meal_timing="consistent"
                ),
                activity_lifestyle=ActivityLifestyle(
                    activity_level="moderate", sleep_schedule_consistency="consistent",
                    nicotine_tobacco="none"
                ),
                symptoms=Symptoms()
            ),
            qualitative_encoding=QualitativeEncoding()
        )


def test_qualitative_encoding_high_sodium():
    """Test A5 example: 'High sodium diet' encoding."""
    registry = get_encoding_registry()
    
    rule = registry.get_rule("diet.sodium_intake", "high")
    assert rule is not None
    assert rule.standardized_code == "DIET_SODIUM_HIGH"
    assert rule.numeric_weight == 1.35
    assert rule.time_window == "chronic"
    assert "dehydration_risk" in rule.direction_of_effect
    assert rule.direction_of_effect["dehydration_risk"] == 0.35
    assert rule.direction_of_effect["bp_risk"] == 0.20


def test_qualitative_encoding_diuretic():
    """Test A5 example: 'Diuretic use' encoding."""
    registry = get_encoding_registry()
    
    rule = registry.get_rule("medications.special_flags", "diuretics")
    assert rule is not None
    assert rule.standardized_code == "MED_DIURETIC"
    assert rule.numeric_weight == 1.45
    assert rule.direction_of_effect["electrolyte_instability"] == 0.45
    assert rule.direction_of_effect["dehydration_risk"] == 0.30


def test_qualitative_encoding_keto_diet():
    """Test A5 example: 'Keto diet' encoding."""
    registry = get_encoding_registry()
    
    rule = registry.get_rule("diet.pattern", "keto")
    assert rule is not None
    assert rule.standardized_code == "DIET_PATTERN_KETO"
    assert rule.direction_of_effect["ketone_likelihood"] == 0.60
    assert rule.direction_of_effect["triglyceride_variability"] == 0.20


def test_qualitative_encoding_poor_sleep():
    """Test A5 example: 'Poor sleep' encoding."""
    registry = get_encoding_registry()
    
    rule = registry.get_rule("activity_lifestyle.sleep_schedule_consistency", "inconsistent")
    assert rule is not None
    assert rule.standardized_code == "SLEEP_POOR"
    assert rule.direction_of_effect["inflammation_index"] == 0.25
    assert rule.direction_of_effect["insulin_resistance_modifier"] == 0.20


def test_qualitative_encoding_high_caffeine():
    """Test A5 example: 'High caffeine' encoding."""
    registry = get_encoding_registry()
    
    rule = registry.get_rule("diet.caffeine", "high")
    assert rule is not None
    assert rule.standardized_code == "CAFFEINE_HIGH"
    assert rule.direction_of_effect["sympathetic_dominance"] == 0.20


def test_qualitative_encoding_apply_multiple():
    """Test applying multiple encoding rules to a SOAP profile."""
    registry = get_encoding_registry()
    
    soap_dict = {
        "diet": {
            "sodium_intake": "high",
            "caffeine": "high",
            "pattern": "keto"
        },
        "activity_lifestyle": {
            "sleep_schedule_consistency": "inconsistent"
        },
        "medical_history": {
            "conditions": ["prediabetes"]
        },
        "medications_supplements": {
            "medications": [
                {"name": "Furosemide", "dose": "40mg", "frequency": "daily", "special_flags": ["diuretics"]}
            ]
        }
    }
    
    applied_rules = registry.encode_qualitative_inputs(soap_dict)
    
    # Should have 5 rules applied
    assert len(applied_rules) >= 5
    
    # Check codes are present
    codes = {rule.standardized_code for rule in applied_rules}
    assert "DIET_SODIUM_HIGH" in codes
    assert "CAFFEINE_HIGH" in codes
    assert "DIET_PATTERN_KETO" in codes
    assert "SLEEP_POOR" in codes
    assert "MED_DIURETIC" in codes


def test_qualitative_encoding_aggregate_modifiers():
    """Test computing aggregate modifiers from multiple rules."""
    registry = get_encoding_registry()
    
    soap_dict = {
        "diet": {
            "sodium_intake": "high",
            "hydration_intake": "low"
        },
        "medications_supplements": {
            "medications": [
                {"name": "Furosemide", "dose": "40mg", "frequency": "daily", "special_flags": ["diuretics"]}
            ]
        }
    }
    
    applied_rules = registry.encode_qualitative_inputs(soap_dict)
    aggregate = registry.compute_aggregate_modifiers(applied_rules)
    
    # dehydration_risk should be sum of: +0.35 (high sodium) + +0.40 (low hydration) + +0.30 (diuretic)
    assert "dehydration_risk" in aggregate
    assert aggregate["dehydration_risk"] == pytest.approx(1.05, abs=0.01)


def test_blood_parser_csv():
    """Test blood specimen CSV parsing."""
    csv_content = """name,value,unit,ref_low,ref_high,flag
glucose,95.0,mg/dL,70,100,Normal
sodium,140.0,mmol/L,135,145,Normal
potassium,4.0,mmol/L,3.5,5.0,Normal
"""
    
    blood_data, errors = parse_blood_specimen(
        file_content=csv_content.encode('utf-8'),
        source_format=FileFormatEnum.CSV,
        metadata={"collection_datetime": "2026-01-29T08:00:00"}
    )
    
    assert errors is None or len(errors) == 0
    assert len(blood_data.analytes) == 3
    assert blood_data.analytes[0].name == "glucose"
    assert blood_data.analytes[0].value == 95.0
    assert blood_data.analytes[0].unit == "mg/dL"


def test_blood_parser_normalization():
    """Test analyte name normalization."""
    csv_content = """name,value,unit
Glu,95.0,mg/dL
Na,140.0,mmol/L
K+,4.0,mmol/L
Total Cholesterol,180.0,mg/dL
"""
    
    blood_data, errors = parse_blood_specimen(
        file_content=csv_content.encode('utf-8'),
        source_format=FileFormatEnum.CSV
    )
    
    # Check normalization
    names = {a.name for a in blood_data.analytes}
    assert "glucose" in names
    assert "sodium_na" in names
    assert "potassium_k" in names
    assert "total_cholesterol" in names


def test_complete_part_a_submission():
    """Test complete PART A submission with all sections."""
    from schemas.part_a.v1.main_schema import SalivaSpecimenData
    part_a = PartAInputSchema(
        specimen_data=SpecimenDataUpload(
            modalities_selected=[SpecimenModalityEnum.BLOOD, SpecimenModalityEnum.SALIVA],
            blood=[BloodSpecimenData(
                collection_datetime=datetime.utcnow(),
                fasting_status=FastingStatusEnum.FASTING,
                panels=[],
                analytes=[
                    BloodAnalyte(name="glucose", value=95.0, unit="mg/dL"),
                    BloodAnalyte(name="sodium_na", value=140.0, unit="mmol/L"),
                    BloodAnalyte(name="total_cholesterol", value=180.0, unit="mg/dL")
                ],
                source_format=FileFormatEnum.CSV
            )],
            saliva=[SalivaSpecimenData(
                collection_type="spot",
                analytes=[],
                source_format=FileFormatEnum.MANUAL_ENTRY
            )],  # Satisfies modality selection
        ),
        isf_monitor_data=ISFMonitorData(
            core_analytes=[
                ISFAnalyteStream(
                    name="glucose",
                    values=[95.0, 96.0, 94.0],
                    timestamps=[datetime.utcnow() for _ in range(3)],
                    unit="mg/dL"
                ),
                ISFAnalyteStream(
                    name="lactate",
                    values=[2.0, 2.1, 2.0],
                    timestamps=[datetime.utcnow() for _ in range(3)],
                    unit="mmol/L"
                )
            ],
            signal_quality=SignalQuality(
                calibration_status="recent",
                sensor_drift_score=0.1,
                noise_score=0.05,
                dropout_percentage=2.0
            )
        ),
        vitals_data=VitalsData(
            cardiovascular=CardiovascularVitals(
                heart_rate_resting=[65, 66, 64],
                hrv_rmssd=[45.0, 46.0, 44.0]
            ),
            respiratory_temperature=RespiratoryTemperatureVitals(),
            sleep_recovery_activity=SleepRecoveryActivityVitals(
                total_sleep_time_hours=7.5,
                sleep_efficiency_percent=88.0
            )
        ),
        soap_profile=SOAPProfile(
            demographics_anthropometrics=DemographicsAnthropometrics(
                age=35,
                sex_at_birth="male",
                height_cm=175.0,
                weight_kg=75.0,
                bmi=24.5
            ),
            medical_history=MedicalHistory(
                conditions=["prediabetes"],
                family_history=["early_cad", "diabetes"]
            ),
            medications_supplements=MedicationsSupplements(
                medications=[
                    Medication(
                        name="Metformin",
                        dose="500mg",
                        frequency="twice daily",
                        special_flags=[]
                    )
                ]
            ),
            diet=DietProfile(
                pattern="mediterranean",
                sodium_intake="high",
                hydration_intake="normal",
                caffeine="moderate",
                alcohol="low",
                meal_timing="consistent"
            ),
            activity_lifestyle=ActivityLifestyle(
                activity_level="high",
                sleep_schedule_consistency="inconsistent",
                nicotine_tobacco="none"
            ),
            symptoms=Symptoms(
                free_text="Occasional fatigue after meals"
            )
        ),
        qualitative_encoding=QualitativeEncoding()
    )
    
    # Apply encoding
    registry = get_encoding_registry()
    soap_dict = part_a.soap_profile.model_dump()
    applied_rules = registry.encode_qualitative_inputs(soap_dict)
    
    # Verify encoding was applied
    assert len(applied_rules) > 0
    codes = {rule.standardized_code for rule in applied_rules}
    assert "DIET_SODIUM_HIGH" in codes  # High sodium diet
    assert "SLEEP_POOR" in codes  # Inconsistent sleep
    assert "ACTIVITY_HIGH" in codes  # High activity
    assert "DX_PREDIABETES" in codes  # Prediabetes condition
    
    # Verify schema is complete and valid
    assert part_a.schema_version == "1.0.0"
    assert len(part_a.specimen_data.modalities_selected) == 2
    assert len(part_a.specimen_data.blood) == 1
    assert len(part_a.isf_monitor_data.core_analytes) == 2
    assert part_a.soap_profile.demographics_anthropometrics.age == 35


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
