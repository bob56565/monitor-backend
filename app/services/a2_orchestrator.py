"""
A2 Orchestration Service

Manages A2 run lifecycle: creation, status tracking, execution, persistence.
Ensures atomic operations and proper error handling.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import A2Run, A2Summary, A2Artifact, A2StatusEnum
from app.services.a2_processor import a2_processor

logger = logging.getLogger(__name__)


class A2Orchestrator:
    """
    A2 Orchestration Service.
    
    Manages A2 run lifecycle:
    - Create run record
    - Execute A2 processing
    - Persist canonical A2 Summary
    - Track status transitions
    - Handle errors
    """
    
    @staticmethod
    def create_run(
        db: Session,
        submission_id: str,
        user_id: int,
        triggered_by: str = "auto"
    ) -> A2Run:
        """
        Create a new A2 run record in QUEUED state.
        
        Args:
            db: Database session
            submission_id: Part A submission ID
            user_id: User ID
            triggered_by: "auto", "manual", "retry"
            
        Returns:
            A2Run record
        """
        a2_run_id = str(uuid.uuid4())
        
        run = A2Run(
            a2_run_id=a2_run_id,
            submission_id=submission_id,
            user_id=user_id,
            status=A2StatusEnum.QUEUED,
            progress=0.0,
            triggered_by=triggered_by,
            created_at=datetime.utcnow()
        )
        
        db.add(run)
        db.flush()  # Get ID
        
        # Create initial completeness check artifact
        artifact = A2Artifact(
            a2_run_id=a2_run_id,
            submission_id=submission_id,
            user_id=user_id,
            artifact_type="completeness_check",
            artifact_data={"status": "queued", "created_at": datetime.utcnow().isoformat()}
        )
        db.add(artifact)
        
        db.commit()
        db.refresh(run)
        
        logger.info(f"Created A2 run {a2_run_id} for submission {submission_id}")
        return run
    
    @staticmethod
    def execute_run(
        db: Session,
        a2_run_id: str
    ) -> Dict[str, Any]:
        """
        Execute A2 processing for a run.
        
        Updates status to RUNNING, processes data, creates summary, updates to COMPLETED or FAILED.
        
        Args:
            db: Database session
            a2_run_id: A2 run identifier
            
        Returns:
            Result dictionary with status and summary
        """
        run = db.query(A2Run).filter(A2Run.a2_run_id == a2_run_id).first()
        if not run:
            raise ValueError(f"A2 run {a2_run_id} not found")
        
        # Update to RUNNING
        run.status = A2StatusEnum.RUNNING
        run.started_at = datetime.utcnow()
        run.progress = 0.1
        db.commit()
        
        try:
            start_time = datetime.utcnow()
            
            # Process A2 analysis
            summary_data = a2_processor.process_submission(
                db=db,
                a2_run_id=a2_run_id,
                submission_id=run.submission_id,
                user_id=run.user_id
            )
            
            # Create canonical A2 Summary
            summary = A2Summary(**summary_data)
            db.add(summary)
            
            # Update run to COMPLETED
            end_time = datetime.utcnow()
            computation_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            run.status = A2StatusEnum.COMPLETED
            run.completed_at = end_time
            run.progress = 1.0
            run.computation_time_ms = computation_time_ms
            
            # Update completeness check artifact
            artifact = db.query(A2Artifact).filter(
                A2Artifact.a2_run_id == a2_run_id,
                A2Artifact.artifact_type == "completeness_check"
            ).first()
            if artifact:
                artifact.artifact_data = {
                    "status": "completed",
                    "completed_at": end_time.isoformat(),
                    "stream_coverage": summary_data["stream_coverage"],
                    "gating": summary_data["gating"]
                }
            
            db.commit()
            db.refresh(run)
            db.refresh(summary)
            
            logger.info(f"A2 run {a2_run_id} completed successfully in {computation_time_ms}ms")
            
            return {
                "status": "completed",
                "a2_run_id": a2_run_id,
                "summary": summary_data
            }
            
        except Exception as e:
            # Update run to FAILED
            run.status = A2StatusEnum.FAILED
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            run.progress = 0.0
            
            db.commit()
            
            logger.error(f"A2 run {a2_run_id} failed: {str(e)}", exc_info=True)
            
            return {
                "status": "failed",
                "a2_run_id": a2_run_id,
                "error": str(e)
            }
    
    @staticmethod
    def get_run_status(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest A2 run status for a submission.
        
        Args:
            db: Database session
            submission_id: Part A submission ID
            user_id: User ID
            
        Returns:
            Status dictionary or None if no run exists
        """
        run = db.query(A2Run).filter(
            A2Run.submission_id == submission_id,
            A2Run.user_id == user_id,
            A2Run.superseded == False
        ).order_by(A2Run.created_at.desc()).first()
        
        if not run:
            return None
        
        return {
            "submission_id": submission_id,
            "user_id": user_id,
            "a2_run_id": run.a2_run_id,
            "status": run.status.value,
            "progress": run.progress,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat(),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "updated_at": run.updated_at.isoformat()
        }
    
    @staticmethod
    def get_summary(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get canonical A2 Summary for a submission.
        
        Args:
            db: Database session
            submission_id: Part A submission ID
            user_id: User ID
            
        Returns:
            Summary dictionary or None if no summary exists
        """
        # Find latest completed run
        run = db.query(A2Run).filter(
            A2Run.submission_id == submission_id,
            A2Run.user_id == user_id,
            A2Run.status == A2StatusEnum.COMPLETED,
            A2Run.superseded == False
        ).order_by(A2Run.created_at.desc()).first()
        
        if not run:
            return None
        
        # Get summary
        summary = db.query(A2Summary).filter(
            A2Summary.a2_run_id == run.a2_run_id
        ).first()
        
        if not summary:
            return None
        
        return {
            "submission_id": summary.submission_id,
            "user_id": summary.user_id,
            "a2_run_id": summary.a2_run_id,
            "created_at": summary.created_at.isoformat(),
            "stream_coverage": summary.stream_coverage,
            "gating": summary.gating,
            "priors_used": summary.priors_used,
            "prior_decay_state": summary.prior_decay_state,
            "conflict_flags": summary.conflict_flags,
            "derived_features_count": summary.derived_features_count,
            "derived_features_detail": summary.derived_features_detail,
            "anchor_strength_by_domain": summary.anchor_strength_by_domain,
            "confidence_distribution": summary.confidence_distribution,
            "schema_version": summary.schema_version
        }
    
    @staticmethod
    def retry_run(
        db: Session,
        submission_id: str,
        user_id: int
    ) -> A2Run:
        """
        Retry A2 processing for a submission.
        
        Creates a new run and marks previous run as superseded.
        
        Args:
            db: Database session
            submission_id: Part A submission ID
            user_id: User ID
            
        Returns:
            New A2Run record
        """
        # Mark previous run as superseded
        previous_run = db.query(A2Run).filter(
            A2Run.submission_id == submission_id,
            A2Run.user_id == user_id,
            A2Run.superseded == False
        ).order_by(A2Run.created_at.desc()).first()
        
        if previous_run:
            previous_run.superseded = True
            db.commit()
        
        # Create new run
        new_run = A2Orchestrator.create_run(
            db=db,
            submission_id=submission_id,
            user_id=user_id,
            triggered_by="retry"
        )
        
        logger.info(f"Created retry run {new_run.a2_run_id} for submission {submission_id}")
        return new_run
    
    @staticmethod
    def run_synchronous(
        db: Session,
        submission_id: str,
        user_id: int,
        triggered_by: str = "auto"
    ) -> Dict[str, Any]:
        """
        Create and immediately execute an A2 run synchronously.
        
        Args:
            db: Database session
            submission_id: Part A submission ID
            user_id: User ID
            triggered_by: "auto", "manual", "retry"
            
        Returns:
            Result dictionary with status and summary
        """
        run = A2Orchestrator.create_run(
            db=db,
            submission_id=submission_id,
            user_id=user_id,
            triggered_by=triggered_by
        )
        
        result = A2Orchestrator.execute_run(db=db, a2_run_id=run.a2_run_id)
        return result


# Singleton instance
a2_orchestrator = A2Orchestrator()
