"""Add PART A tables

Revision ID: 002_part_a_tables
Revises: 001_initial
Create Date: 2026-01-29

Adds all tables needed for PART A raw data user input ingestion.
Non-breaking, additive migration only.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '002_part_a_tables'
down_revision = '001_base_tables'  # Updated to depend on 001
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all PART A tables."""
    
    # part_a_submissions table
    op.create_table(
        'part_a_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('schema_version', sa.String(), nullable=False, server_default='1.0.0'),
        sa.Column('status', sa.Enum('DRAFT', 'SUBMITTED', 'PROCESSING', 'COMPLETED', 'FAILED', name='submissionstatusenum'), nullable=False, server_default='DRAFT'),
        sa.Column('submission_timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('full_payload_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('processing_notes', sa.Text(), nullable=True),
        sa.Column('validation_errors', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_part_a_submissions_id'), 'part_a_submissions', ['id'], unique=False)
    op.create_index(op.f('ix_part_a_submissions_submission_id'), 'part_a_submissions', ['submission_id'], unique=True)
    
    # specimen_uploads table
    op.create_table(
        'specimen_uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('modality', sa.String(), nullable=False),
        sa.Column('collection_datetime', sa.DateTime(), nullable=True),
        sa.Column('source_format', sa.String(), nullable=False),
        sa.Column('raw_artifact_path', sa.String(), nullable=True),
        sa.Column('raw_artifact_hash', sa.String(), nullable=True),
        sa.Column('raw_artifact_size_bytes', sa.Integer(), nullable=True),
        sa.Column('parsed_data_json', sa.JSON(), nullable=True),
        sa.Column('parsing_status', sa.String(), nullable=True, server_default='pending'),
        sa.Column('parsing_errors', sa.JSON(), nullable=True),
        sa.Column('parsing_notes', sa.Text(), nullable=True),
        sa.Column('lab_name', sa.String(), nullable=True),
        sa.Column('lab_id', sa.String(), nullable=True),
        sa.Column('fasting_status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['submission_id'], ['part_a_submissions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_specimen_uploads_id'), 'specimen_uploads', ['id'], unique=False)
    op.create_index(op.f('ix_specimen_uploads_modality'), 'specimen_uploads', ['modality'], unique=False)
    
    # specimen_analytes table
    op.create_table(
        'specimen_analytes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('value_string', sa.String(), nullable=True),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('reference_range_low', sa.Float(), nullable=True),
        sa.Column('reference_range_high', sa.Float(), nullable=True),
        sa.Column('reference_range_text', sa.String(), nullable=True),
        sa.Column('flag', sa.String(), nullable=True),
        sa.Column('method', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['upload_id'], ['specimen_uploads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_specimen_analytes_id'), 'specimen_analytes', ['id'], unique=False)
    op.create_index(op.f('ix_specimen_analytes_name'), 'specimen_analytes', ['name'], unique=False)
    
    # isf_analyte_streams table
    op.create_table(
        'isf_analyte_streams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('unit', sa.String(), nullable=False),
        sa.Column('device_id', sa.String(), nullable=True),
        sa.Column('sensor_type', sa.String(), nullable=True),
        sa.Column('values_json', sa.JSON(), nullable=False),
        sa.Column('timestamps_json', sa.JSON(), nullable=False),
        sa.Column('calibration_status', sa.String(), nullable=True),
        sa.Column('sensor_drift_score', sa.Float(), nullable=True),
        sa.Column('noise_score', sa.Float(), nullable=True),
        sa.Column('dropout_percentage', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['submission_id'], ['part_a_submissions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_isf_analyte_streams_id'), 'isf_analyte_streams', ['id'], unique=False)
    op.create_index(op.f('ix_isf_analyte_streams_name'), 'isf_analyte_streams', ['name'], unique=False)
    
    # vitals_records table
    op.create_table(
        'vitals_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('cardiovascular_json', sa.JSON(), nullable=True),
        sa.Column('respiratory_temperature_json', sa.JSON(), nullable=True),
        sa.Column('sleep_recovery_activity_json', sa.JSON(), nullable=True),
        sa.Column('baseline_learning_days', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['submission_id'], ['part_a_submissions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vitals_records_id'), 'vitals_records', ['id'], unique=False)
    
    # soap_profile_records table
    op.create_table(
        'soap_profile_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('sex_at_birth', sa.String(), nullable=True),
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('bmi', sa.Float(), nullable=True),
        sa.Column('demographics_anthropometrics_json', sa.JSON(), nullable=True),
        sa.Column('medical_history_json', sa.JSON(), nullable=True),
        sa.Column('medications_supplements_json', sa.JSON(), nullable=True),
        sa.Column('diet_json', sa.JSON(), nullable=True),
        sa.Column('activity_lifestyle_json', sa.JSON(), nullable=True),
        sa.Column('symptoms_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['submission_id'], ['part_a_submissions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_soap_profile_records_id'), 'soap_profile_records', ['id'], unique=False)
    
    # qualitative_encoding_records table
    op.create_table(
        'qualitative_encoding_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('input_field', sa.String(), nullable=False),
        sa.Column('input_value', sa.String(), nullable=False),
        sa.Column('standardized_code', sa.String(), nullable=False),
        sa.Column('numeric_weight', sa.Float(), nullable=False),
        sa.Column('time_window', sa.String(), nullable=False),
        sa.Column('direction_of_effect_json', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['submission_id'], ['part_a_submissions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_qualitative_encoding_records_id'), 'qualitative_encoding_records', ['id'], unique=False)
    op.create_index(op.f('ix_qualitative_encoding_records_input_field'), 'qualitative_encoding_records', ['input_field'], unique=False)
    op.create_index(op.f('ix_qualitative_encoding_records_standardized_code'), 'qualitative_encoding_records', ['standardized_code'], unique=False)


def downgrade() -> None:
    """Remove all PART A tables."""
    op.drop_table('qualitative_encoding_records')
    op.drop_table('soap_profile_records')
    op.drop_table('vitals_records')
    op.drop_table('isf_analyte_streams')
    op.drop_table('specimen_analytes')
    op.drop_table('specimen_uploads')
    op.drop_table('part_a_submissions')
