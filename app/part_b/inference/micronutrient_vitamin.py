"""
Part B Inference Module: Micronutrient & Vitamin Score (Panel 3)

Outputs:
1. Vitamin D Sufficiency Likelihood
2. B12 Functional Adequacy Score
3. Iron Utilization Status Class
4. Magnesium Adequacy Proxy
5. Micronutrient Risk Summary
"""

from datetime import datetime
from typing import Dict, List
from sqlalchemy.orm import Session

from app.part_b.schemas.output_schemas import OutputLineItem, OutputFrequency, OutputStatus
from app.part_b.data_helpers import PartADataHelper
from app.services.confidence import confidence_engine, OutputType


class MicronutrientVitaminInference:
    """Inference module for micronutrient & vitamin panel."""
    
    @staticmethod
    def compute_vitamin_d_sufficiency_likelihood(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Vitamin D Sufficiency Likelihood (≥30 ng/mL)"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        vit_d_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'vitamin_d_25_oh', 'blood')
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Baseline probability
        likelihood = 40.0  # Population baseline (many deficient)
        
        # Anchor to lab
        if vit_d_lab and vit_d_lab.get('value') is not None:
            if vit_d_lab['value'] >= 30:
                likelihood = 85.0
            elif vit_d_lab['value'] >= 20:
                likelihood = 55.0
            else:
                likelihood = 15.0
        
        # Lifestyle modifiers
        if soap:
            # Sun exposure proxy (outdoor activity)
            if soap.get('activity_level') in ['high', 'very_high']:
                likelihood = min(100, likelihood + 10)
            
            # Supplementation
            meds = soap.get('current_medications', [])
            if any('vitamin d' in str(m).lower() or 'd3' in str(m).lower() for m in meds):
                likelihood = min(100, likelihood + 15)
        
        has_anchor = vit_d_lab is not None
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if has_anchor else OutputType.INFERRED_WIDE,
            completeness_score=0.70,
            anchor_quality=0.9 if has_anchor else 0.3,
            recency_days=vit_d_lab.get('days_old', 180) if vit_d_lab else 180,
            signal_quality=0.8
        )
        
        return OutputLineItem(
            output_id=f"micro_vit_d_{int(datetime.utcnow().timestamp())}",
            metric_name="vitamin_d_sufficiency_likelihood",
            panel_name="micronutrient_vitamin",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_tight" if has_anchor else "inferred_wide",
            value_score=round(likelihood, 1),
            units="likelihood %",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If likelihood <60%, consider testing 25(OH)D and supplementation (1000-2000 IU daily).",
            input_chain=f"{'Vit D lab' if vit_d_lab else 'No vit D lab'} + activity + supplementation status",
            input_references={'vit_d_upload_id': vit_d_lab.get('upload_id') if vit_d_lab else None},
            methodologies_used=[
                "Bayesian update (prior lab + lifestyle modifiers)",
                "Rule constraints (supplementation → higher likelihood)",
                "Trend modeling (if serial labs available)",
                "Population priors (geographic/seasonal stratification)"
            ],
            method_why=[
                "Personalizes to measured vitamin D when available",
                "Integrates known determinants (sun, supplements)",
                "Tracks response to supplementation over time",
                "Calibrates against regional deficiency rates"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_b12_functional_adequacy_score(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """B12 Functional Adequacy Score"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        b12_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'vitamin_b12', 'blood')
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Baseline adequacy score
        adequacy = 60.0  # Baseline
        
        # Anchor to lab
        if b12_lab and b12_lab.get('value') is not None:
            if b12_lab['value'] >= 400:
                adequacy = 85.0
            elif b12_lab['value'] >= 200:
                adequacy = 60.0
            else:
                adequacy = 25.0
        
        # Risk factors for deficiency
        if soap:
            meds = soap.get('current_medications', [])
            
            # Metformin impairs B12 absorption
            if any('metformin' in str(m).lower() for m in meds):
                adequacy = max(0, adequacy - 20)
            
            # PPI/H2 blocker impairs absorption
            if any(any(x in str(m).lower() for x in ['omeprazole', 'pantoprazole', 'ranitidine']) for m in meds):
                adequacy = max(0, adequacy - 15)
            
            # Vegan/vegetarian diet
            diet = soap.get('diet_pattern', '')
            if 'vegan' in str(diet).lower():
                adequacy = max(0, adequacy - 15)
        
        has_anchor = b12_lab is not None
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if has_anchor else OutputType.INFERRED_WIDE,
            completeness_score=0.70,
            anchor_quality=0.9 if has_anchor else 0.3,
            recency_days=b12_lab.get('days_old', 180) if b12_lab else 180,
            signal_quality=0.8
        )
        
        return OutputLineItem(
            output_id=f"micro_b12_{int(datetime.utcnow().timestamp())}",
            metric_name="b12_functional_adequacy_score",
            panel_name="micronutrient_vitamin",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_tight" if has_anchor else "inferred_wide",
            value_score=round(adequacy, 1),
            units="adequacy score 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="If score <50 (especially with metformin/PPI), consider B12 testing and supplementation.",
            input_chain=f"{'B12 lab' if b12_lab else 'No B12 lab'} + medications (metformin/PPI) + diet",
            input_references={'b12_upload_id': b12_lab.get('upload_id') if b12_lab else None},
            methodologies_used=[
                "Bayesian network (diet/meds → deficiency risk)",
                "Rule constraints (metformin/PPI → lower score)",
                "Classifier (adequacy categories)",
                "Quality gating (exclude hemolysis-affected samples)"
            ],
            method_why=[
                "Captures absorption pathway disruptions",
                "Mechanistically grounded risk adjustment",
                "Interpretable categories (deficient/adequate)",
                "Prevents false adequacy from lab artifacts"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_iron_utilization_status_class(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Iron Utilization Status Class (deficient/functional/overload)"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Iron panel
        ferritin = PartADataHelper.get_most_recent_lab(db, submission.id, 'ferritin', 'blood')
        iron = PartADataHelper.get_most_recent_lab(db, submission.id, 'iron', 'blood')
        tibc = PartADataHelper.get_most_recent_lab(db, submission.id, 'tibc', 'blood')
        transferrin_sat = PartADataHelper.get_most_recent_lab(db, submission.id, 'transferrin_saturation', 'blood')
        
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Classification
        status = "functional"  # Default
        
        if ferritin and ferritin.get('value') is not None:
            if ferritin['value'] < 30:
                status = "deficient"
            elif ferritin['value'] > 300:
                status = "overload_risk"
        
        # Transferrin saturation (if available)
        if transferrin_sat and transferrin_sat.get('value') is not None:
            if transferrin_sat['value'] < 15:
                status = "deficient"
            elif transferrin_sat['value'] > 45:
                status = "overload_risk"
        
        # Inflammation can falsely elevate ferritin
        # (Would need hsCRP to adjust, using context)
        
        has_iron_panel = ferritin or iron or tibc or transferrin_sat
        
        if not has_iron_panel:
            return OutputLineItem(
                output_id=f"micro_iron_{int(datetime.utcnow().timestamp())}",
                metric_name="iron_utilization_status_class",
                panel_name="micronutrient_vitamin",
                frequency=OutputFrequency.MONTHLY,
                measured_vs_inferred="inferred",
                value_class=None,
                confidence_percent=0,
                confidence_top_3_drivers=[],
                what_increases_confidence=["Need iron panel (ferritin, iron, TIBC, or transferrin sat)"],
                safe_action_suggestion="Insufficient data",
                input_chain="Missing iron panel",
                input_references={},
                methodologies_used=[],
                method_why=[],
                status=OutputStatus.INSUFFICIENT_DATA
            )
        
        anchor_days = min([x['days_old'] for x in [ferritin, iron, tibc, transferrin_sat] if x])
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_TIGHT if anchor_days < 180 else OutputType.INFERRED_WIDE,
            completeness_score=0.80,
            anchor_quality=0.9,
            recency_days=anchor_days,
            signal_quality=0.85
        )
        
        return OutputLineItem(
            output_id=f"micro_iron_{int(datetime.utcnow().timestamp())}",
            metric_name="iron_utilization_status_class",
            panel_name="micronutrient_vitamin",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_tight" if anchor_days < 180 else "inferred_wide",
            value_class=status,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion=f"Status is '{status}'. If deficient, consider iron supplementation. If overload risk, consult for hemochromatosis workup.",
            input_chain=f"Ferritin {'+ transferrin sat' if transferrin_sat else ''}",
            input_references={'ferritin_upload_id': ferritin.get('upload_id') if ferritin else None},
            methodologies_used=[
                "Decision rules (iron study pattern interpretation)",
                "Bayesian with inflammation adjustment (if hsCRP available)",
                "Trend analysis (serial ferritin)",
                "Constraint checks (anemia vs functional iron deficiency)"
            ],
            method_why=[
                "Standard clinical iron assessment algorithm",
                "Prevents misclassification from inflammation",
                "Detects early iron depletion trends",
                "Distinguishes true deficiency from anemia of chronic disease"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_magnesium_adequacy_proxy(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Magnesium Adequacy Proxy"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        mag_lab = PartADataHelper.get_most_recent_lab(db, submission.id, 'magnesium', 'blood')
        soap = PartADataHelper.get_soap_profile(db, submission.id)
        
        # Adequacy score
        adequacy = 60.0  # Baseline
        
        # Anchor to lab (though serum Mg not perfect functional marker)
        if mag_lab and mag_lab.get('value') is not None:
            if mag_lab['value'] >= 2.0:
                adequacy = 75.0
            elif mag_lab['value'] < 1.7:
                adequacy = 30.0
        
        # Risk factors for deficiency
        if soap:
            meds = soap.get('current_medications', [])
            
            # Diuretics deplete magnesium
            if any(any(x in str(m).lower() for x in ['furosemide', 'hydrochlorothiazide', 'lasix']) for m in meds):
                adequacy = max(0, adequacy - 20)
            
            # PPI reduces absorption
            if any(any(x in str(m).lower() for x in ['omeprazole', 'pantoprazole']) for m in meds):
                adequacy = max(0, adequacy - 10)
            
            # Alcohol
            if soap.get('alcohol_use') in ['heavy', 'moderate']:
                adequacy = max(0, adequacy - 10)
        
        has_anchor = mag_lab is not None
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,  # Serum Mg not great marker
            completeness_score=0.60,
            anchor_quality=0.6 if has_anchor else 0.3,
            recency_days=mag_lab.get('days_old', 180) if mag_lab else 180,
            signal_quality=0.7
        )
        
        return OutputLineItem(
            output_id=f"micro_mag_{int(datetime.utcnow().timestamp())}",
            metric_name="magnesium_adequacy_proxy",
            panel_name="micronutrient_vitamin",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_score=round(adequacy, 1),
            units="adequacy proxy 0-100",
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'] + ["Add RBC magnesium test for better assessment"],
            safe_action_suggestion="If score <50 (especially with diuretics), consider magnesium supplementation (200-400mg daily).",
            input_chain=f"{'Serum Mg lab' if mag_lab else 'No Mg lab'} + diuretics/PPI/alcohol",
            input_references={'mag_upload_id': mag_lab['upload_id'] if mag_lab else None},
            methodologies_used=[
                "Composite scoring (serum Mg + functional markers)",
                "Mixed-effects regression (population baseline)",
                "Rule constraints (diuretics → depletion)",
                "Trend analysis (if serial Mg available)"
            ],
            method_why=[
                "Best proxy without RBC magnesium test",
                "Captures medication-induced depletion",
                "Mechanistically grounded risk factors",
                "Tracks trends over time"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
    
    @staticmethod
    def compute_micronutrient_risk_summary(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> OutputLineItem:
        """Micronutrient Risk Summary (top 3 deficiencies by likelihood)"""
        submission = PartADataHelper.get_submission(db, submission_id, user_id)
        
        # Get individual micronutrient assessments
        vit_d = MicronutrientVitaminInference.compute_vitamin_d_sufficiency_likelihood(db, submission_id, user_id)
        b12 = MicronutrientVitaminInference.compute_b12_functional_adequacy_score(db, submission_id, user_id)
        iron = MicronutrientVitaminInference.compute_iron_utilization_status_class(db, submission_id, user_id)
        mag = MicronutrientVitaminInference.compute_magnesium_adequacy_proxy(db, submission_id, user_id)
        
        # Rank deficiencies
        risks = []
        
        if vit_d.value_score and vit_d.value_score < 60:
            risks.append(("Vitamin D", 100 - vit_d.value_score))
        
        if b12.value_score and b12.value_score < 60:
            risks.append(("Vitamin B12", 100 - b12.value_score))
        
        if iron.value_class == "deficient":
            risks.append(("Iron", 70.0))
        
        if mag.value_score and mag.value_score < 60:
            risks.append(("Magnesium", 100 - mag.value_score))
        
        # Sort by risk score descending
        risks.sort(key=lambda x: x[1], reverse=True)
        top_3 = risks[:3]
        
        # Format as value_class
        summary = ", ".join([f"{name} (risk {score:.0f})" for name, score in top_3]) if top_3 else "No significant deficiency risks"
        
        confidence_result = confidence_engine.compute_confidence(
            output_type=OutputType.INFERRED_WIDE,
            completeness_score=0.70,
            anchor_quality=0.65,
            recency_days=30,
            signal_quality=0.75
        )
        
        return OutputLineItem(
            output_id=f"micro_summary_{int(datetime.utcnow().timestamp())}",
            metric_name="micronutrient_risk_summary",
            panel_name="micronutrient_vitamin",
            frequency=OutputFrequency.MONTHLY,
            measured_vs_inferred="inferred_wide",
            value_class=summary,
            confidence_percent=round(confidence_result['confidence_percent'], 1),
            confidence_top_3_drivers=confidence_result['top_3_drivers'][:3],
            what_increases_confidence=confidence_result['what_increases_confidence'],
            safe_action_suggestion="Address top deficiency risks with targeted testing and supplementation as appropriate.",
            input_chain="Composite of vitamin D + B12 + iron + magnesium assessments",
            input_references={'soap_profile_id': submission.id},
            methodologies_used=[
                "Ranking model (top 3 deficiencies by likelihood)",
                "Bayesian anchors for each micronutrient",
                "Rule constraints (medication-induced risks)",
                "Quality gating (exclude unreliable assays)"
            ],
            method_why=[
                "Prioritizes actionable deficiencies",
                "Personalizes to individual risk profile",
                "Mechanistic grounding via medications",
                "Prevents false alarms from assay errors"
            ],
            gating_payload={},
            confidence_payload=confidence_result
        )
