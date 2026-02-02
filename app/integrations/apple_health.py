"""
Apple Health Integration
Processes Apple Health export data (XML format)
Supports HealthKit data types via API bridges (Terra, Vital, etc.)
"""

import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any, Generator
from pydantic import BaseModel
from enum import Enum
from pathlib import Path
import json


# ===== HealthKit Data Type Mappings =====

HEALTHKIT_TYPES = {
    # Activity
    "HKQuantityTypeIdentifierStepCount": {
        "category": "activity",
        "name": "steps",
        "unit": "count"
    },
    "HKQuantityTypeIdentifierDistanceWalkingRunning": {
        "category": "activity", 
        "name": "distance_walking_running",
        "unit": "km"
    },
    "HKQuantityTypeIdentifierDistanceCycling": {
        "category": "activity",
        "name": "distance_cycling",
        "unit": "km"
    },
    "HKQuantityTypeIdentifierFlightsClimbed": {
        "category": "activity",
        "name": "flights_climbed",
        "unit": "count"
    },
    "HKQuantityTypeIdentifierActiveEnergyBurned": {
        "category": "activity",
        "name": "active_calories",
        "unit": "kcal"
    },
    "HKQuantityTypeIdentifierBasalEnergyBurned": {
        "category": "activity",
        "name": "basal_calories",
        "unit": "kcal"
    },
    "HKQuantityTypeIdentifierAppleExerciseTime": {
        "category": "activity",
        "name": "exercise_minutes",
        "unit": "min"
    },
    "HKQuantityTypeIdentifierAppleStandTime": {
        "category": "activity",
        "name": "stand_minutes",
        "unit": "min"
    },
    "HKQuantityTypeIdentifierAppleMoveTime": {
        "category": "activity",
        "name": "move_minutes",
        "unit": "min"
    },
    
    # Heart
    "HKQuantityTypeIdentifierHeartRate": {
        "category": "heart",
        "name": "heart_rate",
        "unit": "bpm"
    },
    "HKQuantityTypeIdentifierRestingHeartRate": {
        "category": "heart",
        "name": "resting_heart_rate",
        "unit": "bpm"
    },
    "HKQuantityTypeIdentifierWalkingHeartRateAverage": {
        "category": "heart",
        "name": "walking_heart_rate",
        "unit": "bpm"
    },
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": {
        "category": "heart",
        "name": "hrv_sdnn",
        "unit": "ms"
    },
    "HKQuantityTypeIdentifierHeartRateRecoveryOneMinute": {
        "category": "heart",
        "name": "heart_rate_recovery",
        "unit": "bpm"
    },
    
    # Respiratory
    "HKQuantityTypeIdentifierRespiratoryRate": {
        "category": "respiratory",
        "name": "respiratory_rate",
        "unit": "breaths/min"
    },
    "HKQuantityTypeIdentifierOxygenSaturation": {
        "category": "respiratory",
        "name": "spo2",
        "unit": "%"
    },
    "HKQuantityTypeIdentifierVO2Max": {
        "category": "respiratory",
        "name": "vo2_max",
        "unit": "mL/kg/min"
    },
    
    # Body Measurements
    "HKQuantityTypeIdentifierBodyMass": {
        "category": "body",
        "name": "weight",
        "unit": "kg"
    },
    "HKQuantityTypeIdentifierHeight": {
        "category": "body",
        "name": "height",
        "unit": "cm"
    },
    "HKQuantityTypeIdentifierBodyMassIndex": {
        "category": "body",
        "name": "bmi",
        "unit": "count"
    },
    "HKQuantityTypeIdentifierBodyFatPercentage": {
        "category": "body",
        "name": "body_fat_percentage",
        "unit": "%"
    },
    "HKQuantityTypeIdentifierLeanBodyMass": {
        "category": "body",
        "name": "lean_body_mass",
        "unit": "kg"
    },
    "HKQuantityTypeIdentifierWaistCircumference": {
        "category": "body",
        "name": "waist_circumference",
        "unit": "cm"
    },
    
    # Vitals
    "HKQuantityTypeIdentifierBodyTemperature": {
        "category": "vitals",
        "name": "body_temperature",
        "unit": "degC"
    },
    "HKQuantityTypeIdentifierBloodPressureSystolic": {
        "category": "vitals",
        "name": "blood_pressure_systolic",
        "unit": "mmHg"
    },
    "HKQuantityTypeIdentifierBloodPressureDiastolic": {
        "category": "vitals",
        "name": "blood_pressure_diastolic",
        "unit": "mmHg"
    },
    "HKQuantityTypeIdentifierBloodGlucose": {
        "category": "vitals",
        "name": "blood_glucose",
        "unit": "mg/dL"
    },
    
    # Sleep
    "HKCategoryTypeIdentifierSleepAnalysis": {
        "category": "sleep",
        "name": "sleep_analysis",
        "unit": "category"
    },
    
    # Nutrition
    "HKQuantityTypeIdentifierDietaryEnergyConsumed": {
        "category": "nutrition",
        "name": "calories_consumed",
        "unit": "kcal"
    },
    "HKQuantityTypeIdentifierDietaryCarbohydrates": {
        "category": "nutrition",
        "name": "carbohydrates",
        "unit": "g"
    },
    "HKQuantityTypeIdentifierDietaryProtein": {
        "category": "nutrition",
        "name": "protein",
        "unit": "g"
    },
    "HKQuantityTypeIdentifierDietaryFatTotal": {
        "category": "nutrition",
        "name": "fat",
        "unit": "g"
    },
    "HKQuantityTypeIdentifierDietarySugar": {
        "category": "nutrition",
        "name": "sugar",
        "unit": "g"
    },
    "HKQuantityTypeIdentifierDietaryFiber": {
        "category": "nutrition",
        "name": "fiber",
        "unit": "g"
    },
    "HKQuantityTypeIdentifierDietarySodium": {
        "category": "nutrition",
        "name": "sodium",
        "unit": "mg"
    },
    "HKQuantityTypeIdentifierDietaryCaffeine": {
        "category": "nutrition",
        "name": "caffeine",
        "unit": "mg"
    },
    "HKQuantityTypeIdentifierDietaryWater": {
        "category": "nutrition",
        "name": "water",
        "unit": "mL"
    },
    
    # Mindfulness
    "HKCategoryTypeIdentifierMindfulSession": {
        "category": "mindfulness",
        "name": "mindful_minutes",
        "unit": "category"
    },
    
    # Reproductive Health
    "HKCategoryTypeIdentifierMenstrualFlow": {
        "category": "reproductive",
        "name": "menstrual_flow",
        "unit": "category"
    },
    "HKQuantityTypeIdentifierBasalBodyTemperature": {
        "category": "reproductive",
        "name": "basal_body_temperature",
        "unit": "degC"
    },
    
    # Audio
    "HKQuantityTypeIdentifierEnvironmentalAudioExposure": {
        "category": "audio",
        "name": "environmental_sound_level",
        "unit": "dB"
    },
    "HKQuantityTypeIdentifierHeadphoneAudioExposure": {
        "category": "audio",
        "name": "headphone_audio_level",
        "unit": "dB"
    }
}

# Sleep stage mappings
SLEEP_STAGE_MAPPINGS = {
    "HKCategoryValueSleepAnalysisInBed": "in_bed",
    "HKCategoryValueSleepAnalysisAsleep": "asleep",
    "HKCategoryValueSleepAnalysisAwake": "awake",
    "HKCategoryValueSleepAnalysisAsleepCore": "core",
    "HKCategoryValueSleepAnalysisAsleepDeep": "deep",
    "HKCategoryValueSleepAnalysisAsleepREM": "rem",
    "HKCategoryValueSleepAnalysisAsleepUnspecified": "asleep"
}


# ===== Data Models =====

class HealthKitRecord(BaseModel):
    """Generic HealthKit record"""
    type: str
    source_name: str
    source_bundle_id: Optional[str] = None
    device: Optional[str] = None
    unit: Optional[str] = None
    creation_date: datetime
    start_date: datetime
    end_date: datetime
    value: Optional[float] = None
    category_value: Optional[str] = None


class DailySummary(BaseModel):
    """Daily health summary from Apple Health data"""
    date: date
    
    # Activity
    steps: Optional[int] = None
    distance_km: Optional[float] = None
    flights_climbed: Optional[int] = None
    active_calories: Optional[int] = None
    basal_calories: Optional[int] = None
    exercise_minutes: Optional[int] = None
    stand_minutes: Optional[int] = None
    
    # Heart
    resting_heart_rate: Optional[int] = None
    walking_heart_rate: Optional[int] = None
    hrv_avg: Optional[float] = None
    heart_rate_min: Optional[int] = None
    heart_rate_max: Optional[int] = None
    heart_rate_avg: Optional[int] = None
    
    # Sleep
    sleep_duration_hours: Optional[float] = None
    sleep_in_bed_hours: Optional[float] = None
    deep_sleep_hours: Optional[float] = None
    core_sleep_hours: Optional[float] = None
    rem_sleep_hours: Optional[float] = None
    awake_hours: Optional[float] = None
    
    # Body
    weight_kg: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    
    # Vitals
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    spo2_avg: Optional[float] = None
    respiratory_rate_avg: Optional[float] = None
    body_temperature: Optional[float] = None
    
    # Nutrition
    calories_consumed: Optional[int] = None
    water_ml: Optional[int] = None
    carbs_g: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    
    # Other
    mindful_minutes: Optional[int] = None
    vo2_max: Optional[float] = None


# ===== Apple Health Export Parser =====

class AppleHealthParser:
    """
    Parse Apple Health export.xml file
    
    Usage:
        parser = AppleHealthParser("export.xml")
        records = parser.parse_records(data_types=["HKQuantityTypeIdentifierStepCount"])
        daily = parser.get_daily_summaries(start_date="2024-01-01", end_date="2024-01-31")
    """
    
    def __init__(self, export_path: str):
        self.export_path = Path(export_path)
        self._tree = None
        self._root = None
    
    def _ensure_loaded(self):
        """Lazy load the XML tree"""
        if self._tree is None:
            self._tree = ET.parse(self.export_path)
            self._root = self._tree.getroot()
    
    def parse_records(
        self,
        data_types: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        source_name: Optional[str] = None
    ) -> Generator[HealthKitRecord, None, None]:
        """
        Parse records from export file
        
        Args:
            data_types: List of HK type identifiers to include
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format
            source_name: Filter by source (e.g., "Apple Watch")
        """
        self._ensure_loaded()
        
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date + "T23:59:59") if end_date else None
        
        for record in self._root.iter("Record"):
            record_type = record.get("type")
            
            # Filter by data type
            if data_types and record_type not in data_types:
                continue
            
            # Filter by source
            record_source = record.get("sourceName", "")
            if source_name and source_name.lower() not in record_source.lower():
                continue
            
            # Parse dates
            creation_date = self._parse_date(record.get("creationDate"))
            record_start = self._parse_date(record.get("startDate"))
            record_end = self._parse_date(record.get("endDate"))
            
            # Filter by date range
            if start_dt and record_start < start_dt:
                continue
            if end_dt and record_start > end_dt:
                continue
            
            # Parse value
            value = None
            category_value = None
            
            if record.get("value"):
                try:
                    value = float(record.get("value"))
                except ValueError:
                    category_value = record.get("value")
            
            yield HealthKitRecord(
                type=record_type,
                source_name=record_source,
                source_bundle_id=record.get("sourceBundleIdentifier"),
                device=record.get("device"),
                unit=record.get("unit"),
                creation_date=creation_date,
                start_date=record_start,
                end_date=record_end,
                value=value,
                category_value=category_value
            )
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse Apple Health date format"""
        # Format: 2024-01-15 08:30:00 -0600
        try:
            return datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        except:
            return datetime.fromisoformat(date_str.replace(" ", "T")[:19])
    
    def get_daily_summaries(
        self,
        start_date: str,
        end_date: str,
        sources: Optional[List[str]] = None
    ) -> List[DailySummary]:
        """
        Generate daily summaries for a date range
        
        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format
            sources: Optional list of preferred sources
        """
        self._ensure_loaded()
        
        # Initialize daily data containers
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        daily_data = {}
        current = start
        while current <= end:
            daily_data[current] = {
                "steps": [],
                "distance": [],
                "flights": [],
                "active_cal": [],
                "basal_cal": [],
                "exercise_min": [],
                "stand_min": [],
                "resting_hr": [],
                "walking_hr": [],
                "hrv": [],
                "hr": [],
                "weight": [],
                "body_fat": [],
                "bp_sys": [],
                "bp_dia": [],
                "spo2": [],
                "resp_rate": [],
                "body_temp": [],
                "sleep_stages": [],
                "calories_in": [],
                "water": [],
                "carbs": [],
                "protein": [],
                "fat": [],
                "mindful": [],
                "vo2max": []
            }
            current += timedelta(days=1)
        
        # Process all records
        for record in self.parse_records(start_date=start_date, end_date=end_date):
            record_date = record.start_date.date()
            if record_date not in daily_data:
                continue
            
            day = daily_data[record_date]
            rt = record.type
            
            if rt == "HKQuantityTypeIdentifierStepCount" and record.value:
                day["steps"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierDistanceWalkingRunning" and record.value:
                day["distance"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierFlightsClimbed" and record.value:
                day["flights"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierActiveEnergyBurned" and record.value:
                day["active_cal"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierBasalEnergyBurned" and record.value:
                day["basal_cal"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierAppleExerciseTime" and record.value:
                day["exercise_min"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierAppleStandTime" and record.value:
                day["stand_min"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierRestingHeartRate" and record.value:
                day["resting_hr"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierWalkingHeartRateAverage" and record.value:
                day["walking_hr"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN" and record.value:
                day["hrv"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierHeartRate" and record.value:
                day["hr"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierBodyMass" and record.value:
                day["weight"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierBodyFatPercentage" and record.value:
                day["body_fat"].append(record.value * 100)  # Convert to percentage
            elif rt == "HKQuantityTypeIdentifierBloodPressureSystolic" and record.value:
                day["bp_sys"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierBloodPressureDiastolic" and record.value:
                day["bp_dia"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierOxygenSaturation" and record.value:
                day["spo2"].append(record.value * 100)  # Convert to percentage
            elif rt == "HKQuantityTypeIdentifierRespiratoryRate" and record.value:
                day["resp_rate"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierBodyTemperature" and record.value:
                day["body_temp"].append(record.value)
            elif rt == "HKCategoryTypeIdentifierSleepAnalysis":
                duration = (record.end_date - record.start_date).total_seconds() / 3600
                stage = SLEEP_STAGE_MAPPINGS.get(record.category_value, "unknown")
                day["sleep_stages"].append({"stage": stage, "hours": duration})
            elif rt == "HKQuantityTypeIdentifierDietaryEnergyConsumed" and record.value:
                day["calories_in"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierDietaryWater" and record.value:
                day["water"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierDietaryCarbohydrates" and record.value:
                day["carbs"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierDietaryProtein" and record.value:
                day["protein"].append(record.value)
            elif rt == "HKQuantityTypeIdentifierDietaryFatTotal" and record.value:
                day["fat"].append(record.value)
            elif rt == "HKCategoryTypeIdentifierMindfulSession":
                duration = (record.end_date - record.start_date).total_seconds() / 60
                day["mindful"].append(duration)
            elif rt == "HKQuantityTypeIdentifierVO2Max" and record.value:
                day["vo2max"].append(record.value)
        
        # Convert to DailySummary objects
        summaries = []
        for d, data in sorted(daily_data.items()):
            sleep_total = sum(s["hours"] for s in data["sleep_stages"] if s["stage"] != "in_bed")
            in_bed_total = sum(s["hours"] for s in data["sleep_stages"])
            deep_total = sum(s["hours"] for s in data["sleep_stages"] if s["stage"] == "deep")
            core_total = sum(s["hours"] for s in data["sleep_stages"] if s["stage"] == "core")
            rem_total = sum(s["hours"] for s in data["sleep_stages"] if s["stage"] == "rem")
            awake_total = sum(s["hours"] for s in data["sleep_stages"] if s["stage"] == "awake")
            
            summary = DailySummary(
                date=d,
                steps=int(sum(data["steps"])) if data["steps"] else None,
                distance_km=sum(data["distance"]) if data["distance"] else None,
                flights_climbed=int(sum(data["flights"])) if data["flights"] else None,
                active_calories=int(sum(data["active_cal"])) if data["active_cal"] else None,
                basal_calories=int(sum(data["basal_cal"])) if data["basal_cal"] else None,
                exercise_minutes=int(sum(data["exercise_min"])) if data["exercise_min"] else None,
                stand_minutes=int(sum(data["stand_min"])) if data["stand_min"] else None,
                resting_heart_rate=int(sum(data["resting_hr"]) / len(data["resting_hr"])) if data["resting_hr"] else None,
                walking_heart_rate=int(sum(data["walking_hr"]) / len(data["walking_hr"])) if data["walking_hr"] else None,
                hrv_avg=sum(data["hrv"]) / len(data["hrv"]) if data["hrv"] else None,
                heart_rate_min=int(min(data["hr"])) if data["hr"] else None,
                heart_rate_max=int(max(data["hr"])) if data["hr"] else None,
                heart_rate_avg=int(sum(data["hr"]) / len(data["hr"])) if data["hr"] else None,
                sleep_duration_hours=sleep_total if sleep_total > 0 else None,
                sleep_in_bed_hours=in_bed_total if in_bed_total > 0 else None,
                deep_sleep_hours=deep_total if deep_total > 0 else None,
                core_sleep_hours=core_total if core_total > 0 else None,
                rem_sleep_hours=rem_total if rem_total > 0 else None,
                awake_hours=awake_total if awake_total > 0 else None,
                weight_kg=data["weight"][-1] if data["weight"] else None,  # Latest value
                body_fat_percentage=data["body_fat"][-1] if data["body_fat"] else None,
                blood_pressure_systolic=int(sum(data["bp_sys"]) / len(data["bp_sys"])) if data["bp_sys"] else None,
                blood_pressure_diastolic=int(sum(data["bp_dia"]) / len(data["bp_dia"])) if data["bp_dia"] else None,
                spo2_avg=sum(data["spo2"]) / len(data["spo2"]) if data["spo2"] else None,
                respiratory_rate_avg=sum(data["resp_rate"]) / len(data["resp_rate"]) if data["resp_rate"] else None,
                body_temperature=data["body_temp"][-1] if data["body_temp"] else None,
                calories_consumed=int(sum(data["calories_in"])) if data["calories_in"] else None,
                water_ml=int(sum(data["water"])) if data["water"] else None,
                carbs_g=sum(data["carbs"]) if data["carbs"] else None,
                protein_g=sum(data["protein"]) if data["protein"] else None,
                fat_g=sum(data["fat"]) if data["fat"] else None,
                mindful_minutes=int(sum(data["mindful"])) if data["mindful"] else None,
                vo2_max=data["vo2max"][-1] if data["vo2max"] else None  # Latest value
            )
            summaries.append(summary)
        
        return summaries
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Extract user profile info from export"""
        self._ensure_loaded()
        
        profile = {}
        
        me = self._root.find(".//Me")
        if me is not None:
            profile["date_of_birth"] = me.get("HKCharacteristicTypeIdentifierDateOfBirth")
            profile["biological_sex"] = me.get("HKCharacteristicTypeIdentifierBiologicalSex")
            profile["blood_type"] = me.get("HKCharacteristicTypeIdentifierBloodType")
            profile["fitzpatrick_skin_type"] = me.get("HKCharacteristicTypeIdentifierFitzpatrickSkinType")
        
        return profile
    
    def get_available_sources(self) -> List[str]:
        """Get list of all data sources in the export"""
        self._ensure_loaded()
        
        sources = set()
        for record in self._root.iter("Record"):
            source = record.get("sourceName")
            if source:
                sources.add(source)
        
        return sorted(list(sources))
    
    def get_available_types(self) -> List[str]:
        """Get list of all data types in the export"""
        self._ensure_loaded()
        
        types = set()
        for record in self._root.iter("Record"):
            record_type = record.get("type")
            if record_type:
                types.add(record_type)
        
        return sorted(list(types))


# ===== Data Transformation =====

def transform_apple_health_to_monitor_format(daily_summary: DailySummary) -> Dict:
    """Transform Apple Health daily summary to Monitor's unified format"""
    return {
        "source": "apple_health",
        "device_type": "apple_watch_iphone",
        "date": daily_summary.date.isoformat(),
        "data": {
            "activity": {
                "steps": daily_summary.steps,
                "distance_km": daily_summary.distance_km,
                "flights_climbed": daily_summary.flights_climbed,
                "active_calories": daily_summary.active_calories,
                "basal_calories": daily_summary.basal_calories,
                "exercise_minutes": daily_summary.exercise_minutes,
                "stand_minutes": daily_summary.stand_minutes
            },
            "heart": {
                "resting_heart_rate": daily_summary.resting_heart_rate,
                "walking_heart_rate": daily_summary.walking_heart_rate,
                "hrv_avg_ms": daily_summary.hrv_avg,
                "heart_rate_min": daily_summary.heart_rate_min,
                "heart_rate_max": daily_summary.heart_rate_max,
                "heart_rate_avg": daily_summary.heart_rate_avg
            },
            "sleep": {
                "total_sleep_hours": daily_summary.sleep_duration_hours,
                "in_bed_hours": daily_summary.sleep_in_bed_hours,
                "deep_sleep_hours": daily_summary.deep_sleep_hours,
                "core_sleep_hours": daily_summary.core_sleep_hours,
                "rem_sleep_hours": daily_summary.rem_sleep_hours,
                "awake_hours": daily_summary.awake_hours,
                "sleep_efficiency": (
                    (daily_summary.sleep_duration_hours / daily_summary.sleep_in_bed_hours * 100)
                    if daily_summary.sleep_in_bed_hours and daily_summary.sleep_duration_hours
                    else None
                )
            },
            "body": {
                "weight_kg": daily_summary.weight_kg,
                "body_fat_percentage": daily_summary.body_fat_percentage
            },
            "vitals": {
                "blood_pressure_systolic": daily_summary.blood_pressure_systolic,
                "blood_pressure_diastolic": daily_summary.blood_pressure_diastolic,
                "spo2_percentage": daily_summary.spo2_avg,
                "respiratory_rate": daily_summary.respiratory_rate_avg,
                "body_temperature_c": daily_summary.body_temperature
            },
            "nutrition": {
                "calories_consumed": daily_summary.calories_consumed,
                "water_ml": daily_summary.water_ml,
                "carbohydrates_g": daily_summary.carbs_g,
                "protein_g": daily_summary.protein_g,
                "fat_g": daily_summary.fat_g
            },
            "fitness": {
                "vo2_max": daily_summary.vo2_max
            },
            "mindfulness": {
                "mindful_minutes": daily_summary.mindful_minutes
            }
        }
    }


# ===== Analysis Helpers =====

def analyze_apple_health_trends(summaries: List[DailySummary]) -> Dict[str, Any]:
    """Analyze trends from Apple Health data"""
    if not summaries:
        return {}
    
    analysis = {
        "period": {
            "start": summaries[0].date.isoformat(),
            "end": summaries[-1].date.isoformat(),
            "days": len(summaries)
        },
        "activity": {},
        "sleep": {},
        "heart": {},
        "trends": []
    }
    
    # Activity averages
    steps = [s.steps for s in summaries if s.steps is not None]
    if steps:
        analysis["activity"]["avg_steps"] = int(sum(steps) / len(steps))
        analysis["activity"]["total_steps"] = sum(steps)
        analysis["activity"]["best_day_steps"] = max(steps)
    
    exercise = [s.exercise_minutes for s in summaries if s.exercise_minutes is not None]
    if exercise:
        analysis["activity"]["avg_exercise_minutes"] = int(sum(exercise) / len(exercise))
        analysis["activity"]["total_exercise_minutes"] = sum(exercise)
    
    # Sleep averages
    sleep_hours = [s.sleep_duration_hours for s in summaries if s.sleep_duration_hours is not None]
    if sleep_hours:
        analysis["sleep"]["avg_sleep_hours"] = round(sum(sleep_hours) / len(sleep_hours), 1)
        analysis["sleep"]["min_sleep_hours"] = round(min(sleep_hours), 1)
        analysis["sleep"]["max_sleep_hours"] = round(max(sleep_hours), 1)
    
    # Heart rate
    resting_hr = [s.resting_heart_rate for s in summaries if s.resting_heart_rate is not None]
    if resting_hr:
        analysis["heart"]["avg_resting_hr"] = int(sum(resting_hr) / len(resting_hr))
        analysis["heart"]["min_resting_hr"] = min(resting_hr)
        analysis["heart"]["max_resting_hr"] = max(resting_hr)
    
    hrv = [s.hrv_avg for s in summaries if s.hrv_avg is not None]
    if hrv:
        analysis["heart"]["avg_hrv_ms"] = round(sum(hrv) / len(hrv), 1)
    
    # Simple trend detection
    if len(steps) >= 7:
        first_half = steps[:len(steps)//2]
        second_half = steps[len(steps)//2:]
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg * 1.1:
            analysis["trends"].append("Activity levels improving (+{:.0f}%)".format((second_avg/first_avg - 1) * 100))
        elif second_avg < first_avg * 0.9:
            analysis["trends"].append("Activity levels declining ({:.0f}%)".format((second_avg/first_avg - 1) * 100))
    
    if len(sleep_hours) >= 7:
        first_half = sleep_hours[:len(sleep_hours)//2]
        second_half = sleep_hours[len(sleep_hours)//2:]
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg + 0.5:
            analysis["trends"].append("Sleep duration improving")
        elif second_avg < first_avg - 0.5:
            analysis["trends"].append("Sleep duration declining")
    
    return analysis
