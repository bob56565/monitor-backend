"""
Part B Report Orchestrator

Coordinates generation of complete Part B report by calling all panel inference modules,
integrating with A2 services (gating, confidence, provenance), and assembling final output.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import time

from app.part_b.schemas.output_schemas import (
    PartBReport,
    PanelSection,
    OutputLineItem,
    PartBGenerationRequest,
    PartBGenerationResponse,
    OutputFrequency,
    OutputStatus
)
from app.part_b.data_helpers import PartADataHelper
from app.part_b.inference.metabolic_regulation import MetabolicRegulationInference
from app.part_b.inference.lipid_cardiometabolic import LipidCardiometabolicInference
from app.part_b.inference.micronutrient_vitamin import MicronutrientVitaminInference
from app.part_b.inference.inflammatory_immune import InflammatoryImmuneInference
from app.part_b.inference.endocrine_neurohormonal import EndocrineNeurohormonalInference
from app.part_b.inference.renal_hydration import RenalHydrationInference
from app.part_b.inference.comprehensive_integrated import ComprehensiveIntegratedInference
from app.models.provenance import ProvenanceHelper
from app.services.a2_orchestrator import a2_orchestrator


class PartBOrchestrator:
    """
    Orchestrates Part B report generation.
    
    Workflow:
    1. Validate Part A data exists and meets minimums
    2. Call each panel inference module
    3. For each output: gating → compute → confidence → provenance
    4. Assemble complete report
    5. Return structured response
    """
    
    @staticmethod
    def generate_report(
        db: Session,
        user_id: int,
        request: PartBGenerationRequest
    ) -> PartBGenerationResponse:
        """
        Generate complete Part B report.
        
        Args:
            db: Database session
            user_id: Authenticated user ID
            request: Generation request with submission_id and filters
        
        Returns:
            PartBGenerationResponse with complete report or errors
        """
        start_time = time.time()
        errors = []
        warnings = []
        
        # Step 0: Get A2 summary (required for phase-awareness)
        a2_summary = a2_orchestrator.get_summary(
            db=db,
            submission_id=request.submission_id,
            user_id=user_id
        )
        
        if not a2_summary:
            return PartBGenerationResponse(
                status="error",
                errors=["A2 analysis not found. Run A2 before generating Part B."],
                warnings=["Part B requires completed A2 analysis for phase-awareness."],
                generation_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Check A2 gating eligibility
        if not a2_summary["gating"]["eligible_for_part_b"]:
            return PartBGenerationResponse(
                status="error",
                errors=["Not eligible for Part B according to A2 gating."],
                warnings=a2_summary["gating"]["reasons"],
                generation_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Build A2 header block
        a2_header_block = {
            "a2_status": "completed",
            "a2_run_id": a2_summary["a2_run_id"],
            "a2_completed_at": a2_summary["created_at"],
            "a2_coverage_snapshot": a2_summary["stream_coverage"],
            "a2_conflicts_count": len(a2_summary["conflict_flags"]),
            "a2_anchor_strength_snapshot": a2_summary["anchor_strength_by_domain"]
        }
        
        # Step 1: Validate Part A submission exists and meets minimums
        submission = PartADataHelper.get_submission(db, request.submission_id, user_id)
        
        if not submission:
            return PartBGenerationResponse(
                status="error",
                errors=["Part A submission not found or access denied"],
                generation_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Check minimum requirements
        requirements = PartADataHelper.check_minimum_requirements(
            db, request.submission_id, user_id
        )
        
        if not requirements['meets_requirements']:
            return PartBGenerationResponse(
                status="error",
                errors=[
                    "Part A does not meet minimum data requirements",
                    f"Missing: {', '.join(requirements['missing_items'])}"
                ],
                warnings=[
                    "Part B requires: ≥1 specimen upload, ISF data, vitals, and SOAP profile"
                ],
                generation_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Step 2: Generate each panel section
        try:
            # Panel 1: Metabolic Regulation
            metabolic_panel = PartBOrchestrator._generate_metabolic_panel(
                db, request.submission_id, user_id, request
            )
            
            # Panel 2: Lipid & Cardiometabolic
            lipid_panel = PartBOrchestrator._generate_lipid_cardiometabolic_panel(
                db, request.submission_id, user_id, request
            )
            
            # Panel 3: Micronutrient & Vitamin
            micronutrient_panel = PartBOrchestrator._generate_micronutrient_vitamin_panel(
                db, request.submission_id, user_id, request
            )
            
            # Panel 4: Inflammatory & Immune
            inflammatory_panel = PartBOrchestrator._generate_inflammatory_immune_panel(
                db, request.submission_id, user_id, request
            )
            
            # Panel 5: Endocrine & Neurohormonal
            endocrine_panel = PartBOrchestrator._generate_endocrine_neurohormonal_panel(
                db, request.submission_id, user_id, request
            )
            
            # Panel 6: Renal & Hydration
            renal_panel = PartBOrchestrator._generate_renal_hydration_panel(
                db, request.submission_id, user_id, request
            )
            
            # Panel 7: Comprehensive Integrated
            comprehensive_panel = PartBOrchestrator._generate_comprehensive_integrated_panel(
                db, request.submission_id, user_id, request
            )
            
        except Exception as e:
            import traceback
            errors.append(f"Error generating panels: {str(e)}")
            errors.append(f"Traceback: {traceback.format_exc()}")
            return PartBGenerationResponse(
                status="error",
                errors=errors,
                generation_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Step 3: Aggregate statistics
        all_outputs = (
            metabolic_panel.outputs +
            lipid_panel.outputs +
            micronutrient_panel.outputs +
            inflammatory_panel.outputs +
            endocrine_panel.outputs +
            renal_panel.outputs +
            comprehensive_panel.outputs
        )
        
        total_outputs = len(all_outputs)
        successful_outputs = sum(1 for o in all_outputs if o.status == OutputStatus.SUCCESS)
        insufficient_outputs = sum(1 for o in all_outputs if o.status == OutputStatus.INSUFFICIENT_DATA)
        
        # Average confidence (only successful outputs)
        successful_confidences = [o.confidence_percent for o in all_outputs if o.status == OutputStatus.SUCCESS]
        avg_confidence = sum(successful_confidences) / len(successful_confidences) if successful_confidences else 0
        
        # Step 4: Build report with A2 header
        report = PartBReport(
            report_id=f"partb_{user_id}_{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            submission_id=request.submission_id,
            a2_run_id=a2_summary["a2_run_id"],
            a2_header_block=a2_header_block,
            report_generated_at=datetime.utcnow(),
            data_window_start=datetime.utcnow() - timedelta(days=request.time_window_days),
            data_window_end=datetime.utcnow(),
            metabolic_regulation=metabolic_panel,
            lipid_cardiometabolic=lipid_panel,
            micronutrient_vitamin=micronutrient_panel,
            inflammatory_immune=inflammatory_panel,
            endocrine_neurohormonal=endocrine_panel,
            renal_hydration=renal_panel,
            comprehensive_integrated=comprehensive_panel,
            total_outputs=total_outputs,
            successful_outputs=successful_outputs,
            insufficient_data_outputs=insufficient_outputs,
            average_confidence=round(avg_confidence, 1),
            data_quality_summary=requirements
        )
        
        # Step 5: Persist provenance records for successful outputs
        for output in all_outputs:
            if output.status == OutputStatus.SUCCESS:
                try:
                    provenance = ProvenanceHelper.create_provenance_record(
                        session=db,
                        user_id=user_id,
                        output_id=output.output_id,
                        panel_name=output.panel_name,
                        metric_name=output.metric_name,
                        output_type=output.measured_vs_inferred,
                        input_chain=output.input_chain,
                        raw_input_refs=output.input_references,
                        methodologies_used=output.methodologies_used,
                        method_why=" | ".join(output.method_why),
                        confidence_payload=output.confidence_payload,
                        gating_payload=output.gating_payload,
                        output_value=output.value_score,
                        output_range_low=output.value_range_low,
                        output_range_high=output.value_range_high,
                        output_units=output.units,
                        time_window_days=request.time_window_days
                    )
                    output.provenance_id = provenance.id
                except Exception as e:
                    warnings.append(f"Failed to create provenance for {output.metric_name}: {str(e)}")
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        return PartBGenerationResponse(
            status="success" if successful_outputs == total_outputs else "partial",
            report=report,
            errors=errors,
            warnings=warnings,
            generation_time_ms=generation_time_ms
        )
    
    @staticmethod
    def _generate_metabolic_panel(
        db: Session,
        submission_id: str,
        user_id: int,
        request: PartBGenerationRequest
    ) -> PanelSection:
        """Generate metabolic regulation panel outputs."""
        outputs = []
        
        # 1. Estimated HbA1c Range
        outputs.append(
            MetabolicRegulationInference.estimate_hba1c_range(db, submission_id, user_id)
        )
        
        # 2. Insulin Resistance Probability
        outputs.append(
            MetabolicRegulationInference.compute_insulin_resistance_score(db, submission_id, user_id)
        )
        
        # 3. Metabolic Flexibility Score
        outputs.append(
            MetabolicRegulationInference.compute_metabolic_flexibility_score(db, submission_id, user_id)
        )
        
        # 4. Postprandial Dysregulation Phenotype
        outputs.append(
            MetabolicRegulationInference.compute_postprandial_dysregulation_phenotype(db, submission_id, user_id)
        )
        
        # 5. Prediabetes Trajectory
        outputs.append(
            MetabolicRegulationInference.compute_prediabetes_trajectory(db, submission_id, user_id)
        )
        
        return PanelSection(
            panel_name="metabolic_regulation",
            panel_display_name="Metabolic Regulation",
            outputs=outputs,
            summary_notes="Glucose metabolism and insulin resistance indicators"
        )
    
    @staticmethod
    def _generate_placeholder_panel(
        panel_name: str,
        panel_display_name: str
    ) -> PanelSection:
        """Generate placeholder panel for panels not yet fully implemented."""
        return PanelSection(
            panel_name=panel_name,
            panel_display_name=panel_display_name,
            outputs=[],
            summary_notes="Panel implementation in progress"
        )
    
    @staticmethod
    def _generate_lipid_cardiometabolic_panel(
        db: Session, submission_id: str, user_id: int, request: PartBGenerationRequest
    ) -> PanelSection:
        """Generate lipid & cardiometabolic panel outputs."""
        return PanelSection(
            panel_name="lipid_cardiometabolic",
            panel_display_name="Lipid & Cardiometabolic Indications",
            outputs=[
                LipidCardiometabolicInference.compute_atherogenic_risk_phenotype(db, submission_id, user_id),
                LipidCardiometabolicInference.compute_triglyceride_elevation_probability(db, submission_id, user_id),
                LipidCardiometabolicInference.compute_ldl_pattern_risk_proxy(db, submission_id, user_id),
                LipidCardiometabolicInference.compute_hdl_functional_likelihood(db, submission_id, user_id),
                LipidCardiometabolicInference.compute_cardiometabolic_risk_score(db, submission_id, user_id)
            ],
            summary_notes="Lipid metabolism and cardiovascular risk assessment"
        )
    
    @staticmethod
    def _generate_micronutrient_vitamin_panel(
        db: Session, submission_id: str, user_id: int, request: PartBGenerationRequest
    ) -> PanelSection:
        """Generate micronutrient & vitamin panel outputs."""
        return PanelSection(
            panel_name="micronutrient_vitamin",
            panel_display_name="Micronutrient & Vitamin Score",
            outputs=[
                MicronutrientVitaminInference.compute_vitamin_d_sufficiency_likelihood(db, submission_id, user_id),
                MicronutrientVitaminInference.compute_b12_functional_adequacy_score(db, submission_id, user_id),
                MicronutrientVitaminInference.compute_iron_utilization_status_class(db, submission_id, user_id),
                MicronutrientVitaminInference.compute_magnesium_adequacy_proxy(db, submission_id, user_id),
                MicronutrientVitaminInference.compute_micronutrient_risk_summary(db, submission_id, user_id)
            ],
            summary_notes="Micronutrient and vitamin status assessment"
        )
    
    @staticmethod
    def _generate_inflammatory_immune_panel(
        db: Session, submission_id: str, user_id: int, request: PartBGenerationRequest
    ) -> PanelSection:
        """Generate inflammatory & immune panel outputs."""
        return PanelSection(
            panel_name="inflammatory_immune",
            panel_display_name="Inflammatory & Immune Activity",
            outputs=[
                InflammatoryImmuneInference.compute_chronic_inflammation_index(db, submission_id, user_id),
                InflammatoryImmuneInference.compute_acute_vs_chronic_pattern_classifier(db, submission_id, user_id),
                InflammatoryImmuneInference.compute_inflammation_driven_ir_modifier(db, submission_id, user_id),
                InflammatoryImmuneInference.compute_recovery_capacity_score(db, submission_id, user_id),
                InflammatoryImmuneInference.compute_cardio_inflammatory_coupling_index(db, submission_id, user_id)
            ],
            summary_notes="Inflammation and immune system activity"
        )
    
    @staticmethod
    def _generate_endocrine_neurohormonal_panel(
        db: Session, submission_id: str, user_id: int, request: PartBGenerationRequest
    ) -> PanelSection:
        """Generate endocrine & neurohormonal panel outputs."""
        return PanelSection(
            panel_name="endocrine_neurohormonal",
            panel_display_name="Endocrine & Neurohormonal Balance",
            outputs=[
                EndocrineNeurohormonalInference.compute_cortisol_rhythm_integrity_score(db, submission_id, user_id),
                EndocrineNeurohormonalInference.compute_stress_adaptation_vs_maladaptation_classifier(db, submission_id, user_id),
                EndocrineNeurohormonalInference.compute_thyroid_functional_pattern(db, submission_id, user_id),
                EndocrineNeurohormonalInference.compute_sympathetic_dominance_index(db, submission_id, user_id),
                EndocrineNeurohormonalInference.compute_burnout_risk_trajectory(db, submission_id, user_id)
            ],
            summary_notes="Hormonal and stress response systems"
        )
    
    @staticmethod
    def _generate_renal_hydration_panel(
        db: Session, submission_id: str, user_id: int, request: PartBGenerationRequest
    ) -> PanelSection:
        """Generate renal & hydration panel outputs."""
        outputs = [
            RenalHydrationInference.compute_hydration_status(db, submission_id, user_id),
            RenalHydrationInference.compute_electrolyte_regulation_efficiency_score(db, submission_id, user_id),
            RenalHydrationInference.compute_renal_stress_index(db, submission_id, user_id),
            RenalHydrationInference.compute_dehydration_driven_creatinine_elevation_risk(db, submission_id, user_id),
            RenalHydrationInference.compute_egfr_trajectory_class(db, submission_id, user_id)
        ]
        
        return PanelSection(
            panel_name="renal_hydration",
            panel_display_name="Renal & Hydration Balance",
            outputs=outputs,
            summary_notes="Kidney function and hydration status assessment"
        )
    
    @staticmethod
    def _generate_comprehensive_integrated_panel(
        db: Session, submission_id: str, user_id: int, request: PartBGenerationRequest
    ) -> PanelSection:
        """Generate comprehensive integrated panel outputs."""
        return PanelSection(
            panel_name="comprehensive_integrated",
            panel_display_name="Comprehensive Integrated Physiological State",
            outputs=[
                ComprehensiveIntegratedInference.compute_homeostatic_resilience_score(db, submission_id, user_id),
                ComprehensiveIntegratedInference.compute_allostatic_load_proxy(db, submission_id, user_id),
                ComprehensiveIntegratedInference.compute_metabolic_inflammatory_coupling_index(db, submission_id, user_id),
                ComprehensiveIntegratedInference.compute_autonomic_status(db, submission_id, user_id),
                ComprehensiveIntegratedInference.compute_physiological_age_proxy(db, submission_id, user_id)
            ],
            summary_notes="Integrated multi-system physiological health assessment"
        )
