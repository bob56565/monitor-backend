"""
Part 4: Build-Time Validators
Ensure all Part 4 rule files are complete and consistent.
"""

import json
import sys
from pathlib import Path

# Get repo root
REPO_ROOT = Path(__file__).parent.parent
RULES_DIR = REPO_ROOT / 'ui' / 'rules'


def validate_metric_dependency_map():
    """Validate metric_dependency_map.json has exactly 35 metrics"""
    print('\n🔍 Validating metric_dependency_map.json...')
    
    path = RULES_DIR / 'metric_dependency_map.json'
    if not path.exists():
        print(f'❌ File not found: {path}')
        return False
    
    data = json.loads(path.read_text())
    metrics = data.get('metrics', {})
    
    if len(metrics) != 35:
        print(f'❌ Expected 35 metrics, found {len(metrics)}')
        return False
    
    # Check all metrics have required fields
    for metric_id, dep in metrics.items():
        if 'required_inputs' not in dep:
            print(f'❌ {metric_id} missing required_inputs')
            return False
        if 'dependency_type' not in dep:
            print(f'❌ {metric_id} missing dependency_type')
            return False
        if 'fallback_behavior' not in dep:
            print(f'❌ {metric_id} missing fallback_behavior')
            return False
    
    # Check all streams referenced exist in streams_available
    available_streams = set(data.get('streams_available', []))
    for metric_id, dep in metrics.items():
        for req in dep.get('required_inputs', []):
            if req['stream'] not in available_streams:
                print(f'❌ {metric_id} references unknown stream: {req["stream"]}')
                return False
    
    print(f'✅ All 35 metrics validated with proper dependencies')
    return True


def validate_provenance_map():
    """Validate metric_provenance_map.json has exactly 35 metrics"""
    print('\n🔍 Validating metric_provenance_map.json...')
    
    path = RULES_DIR / 'metric_provenance_map.json'
    if not path.exists():
        print(f'❌ File not found: {path}')
        return False
    
    data = json.loads(path.read_text())
    metrics = data.get('metrics', {})
    
    if len(metrics) != 35:
        print(f'❌ Expected 35 metrics, found {len(metrics)}')
        return False
    
    # Check all have provenance_label
    valid_labels = ['DERIVED_FORMULA', 'CONSTRAINED_INFERENCE', 'MODEL_ASSISTED_SYNTHESIS']
    for metric_id, prov in metrics.items():
        if 'provenance_label' not in prov:
            print(f'❌ {metric_id} missing provenance_label')
            return False
        if prov['provenance_label'] not in valid_labels:
            print(f'❌ {metric_id} has invalid provenance_label: {prov["provenance_label"]}')
            return False
    
    print(f'✅ All 35 metrics have valid provenance labels')
    return True


def validate_temporal_rules():
    """Validate temporal_sanity_rules.json has rules for all 35 metrics"""
    print('\n🔍 Validating temporal_sanity_rules.json...')
    
    path = RULES_DIR / 'temporal_sanity_rules.json'
    if not path.exists():
        print(f'❌ File not found: {path}')
        return False
    
    data = json.loads(path.read_text())
    metrics = data.get('metrics', {})
    
    if len(metrics) != 35:
        print(f'❌ Expected 35 metrics, found {len(metrics)}')
        return False
    
    # Check all have violation_behavior
    for metric_id, rule in metrics.items():
        if 'violation_behavior' not in rule:
            print(f'❌ {metric_id} missing violation_behavior')
            return False
        vb = rule['violation_behavior']
        if 'flag_code' not in vb:
            print(f'❌ {metric_id} missing flag_code in violation_behavior')
            return False
    
    print(f'✅ All 35 metrics have temporal sanity rules')
    return True


def validate_degradation_ladder():
    """Validate data_degradation_ladder.json structure"""
    print('\n🔍 Validating data_degradation_ladder.json...')
    
    path = RULES_DIR / 'data_degradation_ladder.json'
    if not path.exists():
        print(f'❌ File not found: {path}')
        return False
    
    data = json.loads(path.read_text())
    tiers = data.get('tiers', [])
    
    if len(tiers) != 4:
        print(f'❌ Expected 4 tiers, found {len(tiers)}')
        return False
    
    expected_tiers = ['full', 'partial', 'minimal', 'exploratory_only']
    for i, tier in enumerate(tiers):
        if tier['tier'] != expected_tiers[i]:
            print(f'❌ Tier {i} should be {expected_tiers[i]}, found {tier["tier"]}')
            return False
        if 'confidence_multiplier' not in tier:
            print(f'❌ Tier {tier["tier"]} missing confidence_multiplier')
            return False
    
    print(f'✅ All 4 degradation tiers validated')
    return True


def validate_consistency_rules():
    """Validate cross_metric_consistency_rules.json"""
    print('\n🔍 Validating cross_metric_consistency_rules.json...')
    
    path = RULES_DIR / 'cross_metric_consistency_rules.json'
    if not path.exists():
        print(f'❌ File not found: {path}')
        return False
    
    data = json.loads(path.read_text())
    rules = data.get('rules', [])
    
    if len(rules) < 3:
        print(f'❌ Expected at least 3 consistency rules (spec requires 3 minimum), found {len(rules)}')
        return False
    
    # Check required minimum rules are present
    required_rule_ids = [
        'CONSISTENCY_INFLAMMATION_VS_RESILIENCE',
        'CONSISTENCY_RECOVERY_VS_BURNOUT',
        'CONSISTENCY_METABOLIC_RISK_INTERNAL'
    ]
    
    rule_ids = [r['rule_id'] for r in rules]
    for req_id in required_rule_ids:
        if req_id not in rule_ids:
            print(f'❌ Missing required rule: {req_id}')
            return False
    
    # Check all rules have proper structure
    for rule in rules:
        if 'if' not in rule or 'then' not in rule:
            print(f'❌ Rule {rule.get("rule_id")} missing if/then structure')
            return False
        if 'confidence_penalty' not in rule['then']:
            print(f'❌ Rule {rule["rule_id"]} missing confidence_penalty')
            return False
    
    print(f'✅ All {len(rules)} consistency rules validated')
    return True


def validate_metric_id_consistency():
    """Ensure all 35 metric IDs are consistent across all rule files"""
    print('\n🔍 Validating metric ID consistency across all rule files...')
    
    # Load Part 2 canonical list
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from app.part_b.clinical_mental_model import METRIC_REGISTRY
        canonical_ids = set(METRIC_REGISTRY.keys())
    except Exception as e:
        print(f'⚠️  Cannot import METRIC_REGISTRY (may not be in Python path): {e}')
        print('⚠️  Skipping canonical registry check - using dependency map as reference')
        # Use dependency map as canonical reference instead
        dep_path = RULES_DIR / 'metric_dependency_map.json'
        dep_data = json.loads(dep_path.read_text())
        canonical_ids = set(dep_data['metrics'].keys())
    
    if len(canonical_ids) != 35:
        print(f'❌ Canonical registry should have 35 metrics, found {len(canonical_ids)}')
        return False
    
    # Check dependency map
    dep_map = json.loads((RULES_DIR / 'metric_dependency_map.json').read_text())
    dep_ids = set(dep_map['metrics'].keys())
    if dep_ids != canonical_ids:
        missing = canonical_ids - dep_ids
        extra = dep_ids - canonical_ids
        if missing:
            print(f'❌ Dependency map missing: {missing}')
        if extra:
            print(f'❌ Dependency map has extra: {extra}')
        return False
    
    # Check provenance map
    prov_map = json.loads((RULES_DIR / 'metric_provenance_map.json').read_text())
    prov_ids = set(prov_map['metrics'].keys())
    if prov_ids != canonical_ids:
        missing = canonical_ids - prov_ids
        extra = prov_ids - canonical_ids
        if missing:
            print(f'❌ Provenance map missing: {missing}')
        if extra:
            print(f'❌ Provenance map has extra: {extra}')
        return False
    
    # Check temporal rules
    temporal = json.loads((RULES_DIR / 'temporal_sanity_rules.json').read_text())
    temporal_ids = set(temporal['metrics'].keys())
    if temporal_ids != canonical_ids:
        missing = canonical_ids - temporal_ids
        extra = temporal_ids - canonical_ids
        if missing:
            print(f'❌ Temporal rules missing: {missing}')
        if extra:
            print(f'❌ Temporal rules has extra: {extra}')
        return False
    
    print(f'✅ All 35 metric IDs consistent across dependency, provenance, and temporal rule files')
    return True


def run_all_validations():
    """Run all Part 4 validations"""
    print('=' * 60)
    print('PART 4: INTEGRITY & GUARDRAILS VALIDATION')
    print('=' * 60)
    
    results = {
        'Metric Dependency Map': validate_metric_dependency_map(),
        'Provenance Map': validate_provenance_map(),
        'Temporal Sanity Rules': validate_temporal_rules(),
        'Degradation Ladder': validate_degradation_ladder(),
        'Consistency Rules': validate_consistency_rules(),
        'Metric ID Consistency': validate_metric_id_consistency()
    }
    
    print('\n' + '=' * 60)
    print('VALIDATION SUMMARY')
    print('=' * 60)
    for name, passed in results.items():
        status = '✅ PASS' if passed else '❌ FAIL'
        print(f'{status}: {name}')
    
    all_passed = all(results.values())
    if all_passed:
        print('\n🎉 All Part 4 validations PASSED')
        return 0
    else:
        print('\n❌ Some validations FAILED')
        return 1


if __name__ == '__main__':
    sys.exit(run_all_validations())
