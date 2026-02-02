"""
Oura Ring Integration
Full implementation for Oura API v2
"""

import httpx
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any
from pydantic import BaseModel
from enum import Enum


# ===== Configuration =====
OURA_API_BASE = "https://api.ouraring.com/v2"
OURA_AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
OURA_TOKEN_URL = "https://api.ouraring.com/oauth/token"

# Scopes available
OURA_SCOPES = [
    "personal",
    "daily",
    "heartrate", 
    "workout",
    "tag",
    "session",
    "spo2"
]


# ===== Data Models =====

class SleepPhase(str, Enum):
    AWAKE = "awake"
    LIGHT = "light"
    DEEP = "deep"
    REM = "rem"


class SleepData(BaseModel):
    """Oura sleep data model"""
    id: str
    day: date
    bedtime_start: datetime
    bedtime_end: datetime
    
    # Duration metrics (seconds)
    total_sleep_duration: int
    awake_time: int
    light_sleep_duration: int
    deep_sleep_duration: int
    rem_sleep_duration: int
    
    # Efficiency
    efficiency: int  # 0-100
    
    # Timing
    latency: int  # seconds to fall asleep
    
    # Physiological
    average_heart_rate: Optional[float] = None
    lowest_heart_rate: Optional[int] = None
    average_hrv: Optional[int] = None
    average_breath: Optional[float] = None
    
    # Temperature
    temperature_delta: Optional[float] = None
    temperature_deviation: Optional[float] = None
    temperature_trend_deviation: Optional[float] = None
    
    # Movement
    restless_periods: Optional[int] = None
    
    # Sleep stages (5-min intervals)
    hypnogram_5min: Optional[str] = None  # "1" = deep, "2" = light, "3" = REM, "4" = awake
    
    # Heart rate data (5-min intervals)
    heart_rate_5min: Optional[List[int]] = None
    hrv_5min: Optional[List[int]] = None

    @property
    def sleep_efficiency_score(self) -> float:
        """Calculate sleep efficiency as percentage"""
        total_time_in_bed = (self.bedtime_end - self.bedtime_start).total_seconds()
        if total_time_in_bed == 0:
            return 0
        return (self.total_sleep_duration / total_time_in_bed) * 100
    
    @property
    def deep_sleep_percentage(self) -> float:
        if self.total_sleep_duration == 0:
            return 0
        return (self.deep_sleep_duration / self.total_sleep_duration) * 100
    
    @property
    def rem_sleep_percentage(self) -> float:
        if self.total_sleep_duration == 0:
            return 0
        return (self.rem_sleep_duration / self.total_sleep_duration) * 100


class ReadinessData(BaseModel):
    """Oura readiness/recovery data"""
    id: str
    day: date
    score: int  # 0-100
    
    # Contributors
    activity_balance: Optional[int] = None
    body_temperature: Optional[int] = None
    hrv_balance: Optional[int] = None
    previous_day_activity: Optional[int] = None
    previous_night: Optional[int] = None
    recovery_index: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    sleep_balance: Optional[int] = None
    
    temperature_deviation: Optional[float] = None
    temperature_trend_deviation: Optional[float] = None


class ActivityData(BaseModel):
    """Oura daily activity data"""
    id: str
    day: date
    score: Optional[int] = None  # 0-100
    
    # Movement
    steps: int
    active_calories: int
    total_calories: int
    
    # Activity levels (minutes)
    sedentary_time: int
    light_activity_time: int
    moderate_activity_time: int
    high_activity_time: int
    
    # Movement metrics
    equivalent_walking_distance: int  # meters
    non_wear_time: Optional[int] = None
    
    # MET
    met_min_inactive: Optional[int] = None
    met_min_low: Optional[int] = None
    met_min_medium: Optional[int] = None
    met_min_high: Optional[int] = None
    
    # Goals
    target_calories: Optional[int] = None
    target_meters: Optional[int] = None


class HeartRateData(BaseModel):
    """Oura heart rate data"""
    bpm: int
    source: str  # "awake", "rest", "sleep", "workout"
    timestamp: datetime


class SpO2Data(BaseModel):
    """Oura SpO2 (blood oxygen) data"""
    day: date
    spo2_percentage: Optional[float] = None
    breathing_disturbance_index: Optional[float] = None


class WorkoutData(BaseModel):
    """Oura workout/activity session data"""
    id: str
    day: date
    activity: str
    start_datetime: datetime
    end_datetime: datetime
    
    calories: Optional[int] = None
    distance: Optional[float] = None  # meters
    intensity: Optional[str] = None
    
    average_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    
    source: str  # "manual", "autodetected", "workout_heart_rate"


class DailyStressData(BaseModel):
    """Oura stress data (Gen 3 feature)"""
    day: date
    stress_high: Optional[int] = None  # minutes
    recovery_high: Optional[int] = None  # minutes
    day_summary: Optional[str] = None  # "restored", "normal", "stressful"


# ===== Oura Client =====

class OuraClient:
    """
    Oura API v2 Client
    
    Usage:
        client = OuraClient(access_token="your_token")
        sleep = await client.get_sleep(start_date="2024-01-01", end_date="2024-01-07")
    """
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make authenticated request to Oura API"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OURA_API_BASE}/{endpoint}",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    # ===== Sleep =====
    
    async def get_sleep(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[SleepData]:
        """
        Get sleep data for date range
        
        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format
        """
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = await self._request("usercollection/sleep", params)
        return [SleepData(**item) for item in data.get("data", [])]
    
    async def get_daily_sleep(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Get daily sleep scores"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = await self._request("usercollection/daily_sleep", params)
        return data.get("data", [])
    
    # ===== Readiness =====
    
    async def get_readiness(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[ReadinessData]:
        """Get readiness/recovery data"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = await self._request("usercollection/daily_readiness", params)
        return [ReadinessData(**item) for item in data.get("data", [])]
    
    # ===== Activity =====
    
    async def get_activity(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[ActivityData]:
        """Get daily activity data"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = await self._request("usercollection/daily_activity", params)
        return [ActivityData(**item) for item in data.get("data", [])]
    
    # ===== Heart Rate =====
    
    async def get_heart_rate(
        self,
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None
    ) -> List[HeartRateData]:
        """
        Get heart rate data (5-min intervals)
        
        Args:
            start_datetime: ISO 8601 format
            end_datetime: ISO 8601 format
        """
        params = {}
        if start_datetime:
            params["start_datetime"] = start_datetime
        if end_datetime:
            params["end_datetime"] = end_datetime
        
        data = await self._request("usercollection/heartrate", params)
        return [HeartRateData(**item) for item in data.get("data", [])]
    
    # ===== SpO2 =====
    
    async def get_spo2(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[SpO2Data]:
        """Get blood oxygen data"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = await self._request("usercollection/daily_spo2", params)
        return [SpO2Data(**item) for item in data.get("data", [])]
    
    # ===== Workouts =====
    
    async def get_workouts(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[WorkoutData]:
        """Get workout sessions"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = await self._request("usercollection/workout", params)
        return [WorkoutData(**item) for item in data.get("data", [])]
    
    # ===== Stress (Gen 3) =====
    
    async def get_stress(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[DailyStressData]:
        """Get daily stress data (Gen 3 only)"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = await self._request("usercollection/daily_stress", params)
        return [DailyStressData(**item) for item in data.get("data", [])]
    
    # ===== Personal Info =====
    
    async def get_personal_info(self) -> Dict:
        """Get user's personal info"""
        return await self._request("usercollection/personal_info")
    
    # ===== Comprehensive Daily Summary =====
    
    async def get_daily_summary(self, target_date: str) -> Dict[str, Any]:
        """
        Get comprehensive summary for a single day
        Combines sleep, readiness, activity, and other metrics
        """
        end_date = target_date
        
        # Fetch all data in parallel would be better, but keeping simple
        sleep_data = await self.get_sleep(target_date, end_date)
        readiness_data = await self.get_readiness(target_date, end_date)
        activity_data = await self.get_activity(target_date, end_date)
        
        summary = {
            "date": target_date,
            "sleep": sleep_data[0].model_dump() if sleep_data else None,
            "readiness": readiness_data[0].model_dump() if readiness_data else None,
            "activity": activity_data[0].model_dump() if activity_data else None
        }
        
        # Try to get SpO2 and stress (may not be available for all users)
        try:
            spo2_data = await self.get_spo2(target_date, end_date)
            summary["spo2"] = spo2_data[0].model_dump() if spo2_data else None
        except:
            summary["spo2"] = None
        
        try:
            stress_data = await self.get_stress(target_date, end_date)
            summary["stress"] = stress_data[0].model_dump() if stress_data else None
        except:
            summary["stress"] = None
        
        return summary


# ===== OAuth Flow Helpers =====

def get_oura_auth_url(client_id: str, redirect_uri: str, state: str = "") -> str:
    """Generate OAuth authorization URL"""
    scopes = " ".join(OURA_SCOPES)
    return (
        f"{OURA_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes}"
        f"&state={state}"
    )


async def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> Dict:
    """Exchange authorization code for access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            OURA_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri
            }
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str
) -> Dict:
    """Refresh expired access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            OURA_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret
            }
        )
        response.raise_for_status()
        return response.json()


# ===== Data Transformation for Monitor =====

def transform_oura_to_monitor_format(oura_data: Dict) -> Dict:
    """
    Transform Oura data to Monitor's unified health data format
    """
    result = {
        "source": "oura",
        "device_type": "smart_ring",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {}
    }
    
    # Sleep metrics
    if oura_data.get("sleep"):
        sleep = oura_data["sleep"]
        result["data"]["sleep"] = {
            "total_sleep_hours": sleep.get("total_sleep_duration", 0) / 3600,
            "deep_sleep_hours": sleep.get("deep_sleep_duration", 0) / 3600,
            "rem_sleep_hours": sleep.get("rem_sleep_duration", 0) / 3600,
            "light_sleep_hours": sleep.get("light_sleep_duration", 0) / 3600,
            "awake_hours": sleep.get("awake_time", 0) / 3600,
            "sleep_efficiency": sleep.get("efficiency"),
            "sleep_latency_minutes": sleep.get("latency", 0) / 60,
            "average_resting_hr": sleep.get("average_heart_rate"),
            "lowest_resting_hr": sleep.get("lowest_heart_rate"),
            "average_hrv": sleep.get("average_hrv"),
            "respiratory_rate": sleep.get("average_breath"),
            "temperature_deviation": sleep.get("temperature_delta")
        }
    
    # Readiness/Recovery
    if oura_data.get("readiness"):
        readiness = oura_data["readiness"]
        result["data"]["readiness"] = {
            "score": readiness.get("score"),
            "recovery_index": readiness.get("recovery_index"),
            "hrv_balance": readiness.get("hrv_balance"),
            "resting_heart_rate_score": readiness.get("resting_heart_rate"),
            "temperature_deviation": readiness.get("temperature_deviation"),
            "temperature_trend": readiness.get("temperature_trend_deviation")
        }
    
    # Activity
    if oura_data.get("activity"):
        activity = oura_data["activity"]
        result["data"]["activity"] = {
            "steps": activity.get("steps"),
            "active_calories": activity.get("active_calories"),
            "total_calories": activity.get("total_calories"),
            "walking_distance_meters": activity.get("equivalent_walking_distance"),
            "sedentary_minutes": activity.get("sedentary_time", 0) // 60,
            "light_activity_minutes": activity.get("light_activity_time", 0) // 60,
            "moderate_activity_minutes": activity.get("moderate_activity_time", 0) // 60,
            "high_activity_minutes": activity.get("high_activity_time", 0) // 60,
            "activity_score": activity.get("score")
        }
    
    # SpO2
    if oura_data.get("spo2"):
        spo2 = oura_data["spo2"]
        result["data"]["spo2"] = {
            "average_spo2": spo2.get("spo2_percentage"),
            "breathing_disturbance_index": spo2.get("breathing_disturbance_index")
        }
    
    # Stress
    if oura_data.get("stress"):
        stress = oura_data["stress"]
        result["data"]["stress"] = {
            "high_stress_minutes": stress.get("stress_high"),
            "recovery_minutes": stress.get("recovery_high"),
            "day_summary": stress.get("day_summary")
        }
    
    return result


# ===== Analysis Helpers =====

def analyze_sleep_quality(sleep_data: SleepData) -> Dict[str, Any]:
    """Analyze sleep quality and provide insights"""
    analysis = {
        "overall_quality": "unknown",
        "insights": [],
        "recommendations": []
    }
    
    # Efficiency analysis
    if sleep_data.efficiency >= 85:
        analysis["insights"].append("Excellent sleep efficiency")
        analysis["overall_quality"] = "good"
    elif sleep_data.efficiency >= 75:
        analysis["insights"].append("Good sleep efficiency")
        analysis["overall_quality"] = "moderate"
    else:
        analysis["insights"].append("Sleep efficiency needs improvement")
        analysis["recommendations"].append("Consider earlier bedtime or sleep hygiene improvements")
        analysis["overall_quality"] = "poor"
    
    # Deep sleep analysis (should be 15-20% for adults)
    total_sleep_mins = sleep_data.total_sleep_duration / 60
    deep_sleep_pct = (sleep_data.deep_sleep_duration / 60) / total_sleep_mins * 100 if total_sleep_mins > 0 else 0
    
    if deep_sleep_pct < 10:
        analysis["insights"].append(f"Low deep sleep ({deep_sleep_pct:.1f}%)")
        analysis["recommendations"].append("Avoid alcohol and heavy meals before bed to improve deep sleep")
    elif deep_sleep_pct >= 15:
        analysis["insights"].append(f"Good deep sleep ({deep_sleep_pct:.1f}%)")
    
    # REM analysis (should be 20-25% for adults)
    rem_sleep_pct = (sleep_data.rem_sleep_duration / 60) / total_sleep_mins * 100 if total_sleep_mins > 0 else 0
    
    if rem_sleep_pct < 15:
        analysis["insights"].append(f"Low REM sleep ({rem_sleep_pct:.1f}%)")
        analysis["recommendations"].append("Ensure adequate total sleep time to allow for REM cycles")
    elif rem_sleep_pct >= 20:
        analysis["insights"].append(f"Good REM sleep ({rem_sleep_pct:.1f}%)")
    
    # Duration analysis
    total_sleep_hours = sleep_data.total_sleep_duration / 3600
    if total_sleep_hours < 6:
        analysis["insights"].append(f"Insufficient sleep duration ({total_sleep_hours:.1f}h)")
        analysis["recommendations"].append("Aim for 7-9 hours of sleep")
    elif total_sleep_hours >= 7 and total_sleep_hours <= 9:
        analysis["insights"].append(f"Good sleep duration ({total_sleep_hours:.1f}h)")
    
    # HRV analysis
    if sleep_data.average_hrv:
        if sleep_data.average_hrv < 20:
            analysis["insights"].append("Low HRV - may indicate stress or poor recovery")
        elif sleep_data.average_hrv > 50:
            analysis["insights"].append("Good HRV - indicates good recovery")
    
    # Temperature analysis
    if sleep_data.temperature_delta:
        if abs(sleep_data.temperature_delta) > 0.5:
            analysis["insights"].append(f"Notable temperature deviation: {sleep_data.temperature_delta:+.2f}°C")
            analysis["recommendations"].append("Monitor for signs of illness if temperature deviation persists")
    
    return analysis


def calculate_weekly_trends(daily_data: List[Dict]) -> Dict[str, Any]:
    """Calculate weekly trends from daily Oura data"""
    if not daily_data:
        return {}
    
    trends = {
        "sleep": {
            "avg_duration_hours": 0,
            "avg_efficiency": 0,
            "avg_hrv": 0,
            "trend_direction": "stable"
        },
        "readiness": {
            "avg_score": 0,
            "trend_direction": "stable"
        },
        "activity": {
            "avg_steps": 0,
            "avg_active_calories": 0,
            "trend_direction": "stable"
        }
    }
    
    # Calculate averages
    sleep_durations = []
    sleep_efficiencies = []
    hrvs = []
    readiness_scores = []
    step_counts = []
    
    for day in daily_data:
        if day.get("sleep"):
            sleep_durations.append(day["sleep"].get("total_sleep_duration", 0) / 3600)
            sleep_efficiencies.append(day["sleep"].get("efficiency", 0))
            if day["sleep"].get("average_hrv"):
                hrvs.append(day["sleep"]["average_hrv"])
        
        if day.get("readiness"):
            readiness_scores.append(day["readiness"].get("score", 0))
        
        if day.get("activity"):
            step_counts.append(day["activity"].get("steps", 0))
    
    if sleep_durations:
        trends["sleep"]["avg_duration_hours"] = sum(sleep_durations) / len(sleep_durations)
    if sleep_efficiencies:
        trends["sleep"]["avg_efficiency"] = sum(sleep_efficiencies) / len(sleep_efficiencies)
    if hrvs:
        trends["sleep"]["avg_hrv"] = sum(hrvs) / len(hrvs)
    if readiness_scores:
        trends["readiness"]["avg_score"] = sum(readiness_scores) / len(readiness_scores)
    if step_counts:
        trends["activity"]["avg_steps"] = sum(step_counts) / len(step_counts)
    
    return trends
