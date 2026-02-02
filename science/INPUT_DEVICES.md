# Consumer Device Input Specifications

## Supported Input Categories

### 1. Continuous Glucose Monitors (CGM)

#### Dexcom G6/G7
- **Data format:** mg/dL, 5-minute intervals
- **Export:** CSV, API (with patient consent)
- **Metrics derived:**
  - Time in range (TIR)
  - Glucose variability (CV%)
  - Mean glucose
  - GMI (Glucose Management Indicator)
  - Time above/below range

#### Abbott Freestyle Libre
- **Data format:** mg/dL, 15-minute intervals (scan)
- **Export:** CSV, PDF reports
- **Metrics derived:** Same as Dexcom

### 2. Smart Scales

#### Withings Body+
- **Data:** Weight, BMI, body fat %, muscle mass, water %
- **Export:** API, CSV
- **Integration:** OAuth

#### Renpho Smart Scale
- **Data:** Weight, body composition (12 metrics)
- **Export:** App export, CSV

### 3. Blood Pressure Monitors

#### Omron Connect
- **Data:** Systolic, diastolic, pulse, irregular heartbeat
- **Export:** App, CSV
- **Classification:** AHA BP categories

#### Withings BPM
- **Data:** Same as Omron
- **Export:** API integration

### 4. Home Test Kits

#### Urine Test Strips (Various)
- **Analytes:** pH, specific gravity, protein, glucose, ketones, blood, nitrites, leukocytes
- **Input:** Manual entry or photo analysis
- **Mapping:** Semi-quantitative to quantitative

#### Home Cholesterol Tests
- **Analytes:** Total cholesterol, some include HDL/LDL
- **Input:** Manual entry
- **Accuracy:** ±10-15% vs lab

#### Home A1c Tests
- **Analytes:** Hemoglobin A1c
- **Input:** Manual entry
- **Accuracy:** ±0.5% vs lab

### 5. Wearables

#### Apple Watch
- **Data:** HR, HRV, SpO2, sleep, activity, AFib detection
- **Export:** HealthKit API
- **Derived:** Resting HR trends, sleep quality score

#### Oura Ring
- **Data:** HR, HRV, temperature, sleep stages, readiness
- **Export:** API
- **Derived:** Recovery score, sleep efficiency

#### Whoop
- **Data:** HR, HRV, respiratory rate, skin temp, sleep
- **Export:** API
- **Derived:** Strain, recovery percentage

#### Fitbit
- **Data:** HR, sleep, SpO2, stress score
- **Export:** API
- **Derived:** Similar to Apple Watch

### 6. Other Devices

#### Smart Thermometers
- **Data:** Body temperature, fever tracking
- **Use:** Infection detection, ovulation tracking

#### Pulse Oximeters
- **Data:** SpO2, pulse rate
- **Use:** Respiratory health, sleep apnea indicators

## Data Normalization Pipeline

```
Raw Device Data
      ↓
[Unit Conversion] → Standard units (mg/dL, mmHg, etc.)
      ↓
[Timestamp Normalization] → UTC, consistent intervals
      ↓
[Quality Filtering] → Remove artifacts, invalid readings
      ↓
[Aggregation] → Daily/weekly summaries, trends
      ↓
[Feature Extraction] → Derived metrics (variability, slopes, etc.)
      ↓
Normalized Feature Vector
```

## Input Schema

```json
{
  "device_type": "cgm|scale|bp|test_kit|wearable",
  "device_model": "string",
  "timestamp": "ISO8601",
  "readings": [
    {
      "metric": "string",
      "value": "number",
      "unit": "string",
      "quality": "high|medium|low"
    }
  ],
  "metadata": {
    "user_id": "string",
    "collection_method": "automatic|manual"
  }
}
```

## Accuracy Considerations

| Device Type | Lab Correlation | Notes |
|-------------|-----------------|-------|
| CGM glucose | r=0.95+ | Well validated |
| Smart scale weight | ±0.1 kg | Highly accurate |
| Smart scale body fat | ±3-5% | Use for trends only |
| Home BP monitors | ±5 mmHg | Validated devices only |
| Home A1c tests | ±0.5% | Less accurate than lab |
| Wearable HR | ±3 bpm | Good for trends |
| Wearable SpO2 | ±2% | Not medical grade |
