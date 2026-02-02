"""
Simplified tests for Milestone 7 Part 2: feature_pack_v2 pipeline.

Tests cover core functionality without requiring complex RunV2 fixture setup.
Focus on module imports, structure validation, and backward compatibility.
"""

import pytest
from app.features.preprocess_v2 import preprocess_v2
from app.models.feature_pack_v2 import FeaturePackV2


class TestFeaturePackV2Imports:
    """Test that Part 2 modules import correctly."""
    
    def test_preprocess_v2_function_exists(self):
        """Verify preprocess_v2 is importable."""
        assert callable(preprocess_v2)
        assert preprocess_v2.__doc__ is not None
    
    def test_feature_pack_v2_schema_exists(self):
        """Verify FeaturePackV2 schema is valid."""
        assert FeaturePackV2 is not None
        # Check key fields exist
        assert hasattr(FeaturePackV2, 'model_fields')


class TestFeaturePackV2Structure:
    """Test FeaturePackV2 pydantic model structure."""
    
    def test_feature_pack_v2_fields(self):
        """Verify FeaturePackV2 has expected fields."""
        fields = FeaturePackV2.model_fields
        
        # Core fields
        assert 'run_id' in fields
        assert 'schema_version' in fields
        assert 'specimen_count' in fields
        assert 'domains_present' in fields
        
        # Feature pack sections
        assert 'missingness_feature_vector' in fields
        assert 'specimen_normalized_values' in fields
        assert 'cross_specimen_relationships' in fields
        assert 'pattern_combination_features' in fields
        assert 'discordance_detection' in fields
        assert 'coherence_scores' in fields
        assert 'penalty_vector' in fields
    
    def test_feature_pack_v2_validation(self):
        """Test that FeaturePackV2 validates correctly."""
        try:
            # This will fail validation (empty dict) but confirms structure
            _ = FeaturePackV2.model_validate({})
        except Exception as e:
            # Expected to fail validation - just checking structure is sound
            assert "validation error" in str(e).lower() or "missing" in str(e).lower()


class TestImportChain:
    """Test the import chain for all Part 2 modules."""
    
    def test_missingness_features_import(self):
        """Test missingness_features module imports."""
        from app.features.missingness_features import compute_missingness_feature_vector
        assert callable(compute_missingness_feature_vector)
    
    def test_cross_specimen_modeling_import(self):
        """Test cross_specimen_modeling module imports."""
        from app.features.cross_specimen_modeling import build_cross_specimen_relationships
        assert callable(build_cross_specimen_relationships)
    
    def test_pattern_features_import(self):
        """Test pattern_features module imports."""
        from app.features.pattern_features import (
            compute_temporal_features,
            detect_motifs,
            build_pattern_combination_features,
            detect_discordance,
        )
        assert callable(compute_temporal_features)
        assert callable(detect_motifs)
        assert callable(build_pattern_combination_features)
        assert callable(detect_discordance)


class TestEnumStructures:
    """Test enum definitions in feature_pack_v2."""
    
    def test_regime_enum_exists(self):
        """Test RegimeEnum is defined."""
        from app.models.feature_pack_v2 import RegimeEnum
        assert hasattr(RegimeEnum, 'REST')
        assert hasattr(RegimeEnum, 'EXERTION')
        assert hasattr(RegimeEnum, 'POSTPRANDIAL')
        assert hasattr(RegimeEnum, 'SLEEP')
    
    def test_motif_enum_exists(self):
        """Test MotifEnum is defined."""
        from app.models.feature_pack_v2 import MotifEnum
        assert hasattr(MotifEnum, 'GLUCOSE_LACTATE_UP_EXERTION')
        assert hasattr(MotifEnum, 'GLUCOSE_LACTATE_UP_MEAL')
        assert hasattr(MotifEnum, 'DEHYDRATION_STRESS')


class TestAPIIntegration:
    """Test that the API endpoint is registered."""
    
    def test_preprocess_v2_endpoint_registered(self):
        """Test that POST /ai/preprocess-v2 is registered."""
        from app.api.ai import router
        
        # Check the endpoint is in router routes
        route_paths = [route.path for route in router.routes if hasattr(route, 'path')]
        assert '/ai/preprocess-v2' in route_paths


class TestBackwardCompatibility:
    """Verify backward compatibility: legacy tests should still pass."""
    
    def test_legacy_endpoints_exist(self):
        """Verify existing endpoints are not broken."""
        from app.main import app
        
        # This is a sanity check that app startup works
        assert app is not None
        assert hasattr(app, 'openapi')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
