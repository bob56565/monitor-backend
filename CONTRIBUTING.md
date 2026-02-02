# Contributing to MONITOR

Thank you for your interest in contributing to MONITOR! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and professional. We're building healthcare technology that affects real people.

## Getting Started

### Prerequisites

- Python 3.10+
- pip
- Git

### Local Setup

```bash
# Clone the repository
git clone https://github.com/bob56565/monitor-backend.git
cd monitor-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start local API
python -m uvicorn api_worker:app --reload
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_inference_v2.py -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

## How to Contribute

### Reporting Issues

1. Check existing issues first
2. Use the issue template
3. Include:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details

### Suggesting Features

1. Open a feature request issue
2. Describe the use case
3. Explain the benefit
4. Consider backward compatibility

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Add/update tests
5. Update documentation
6. Run tests: `pytest tests/ -v`
7. Commit with clear message
8. Push and create PR

### Commit Messages

Format:
```
type: short description

Longer description if needed.

Closes #issue
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring
- `style`: Formatting
- `chore`: Maintenance

### Pull Request Guidelines

1. Reference related issue(s)
2. Describe changes clearly
3. Include test coverage
4. Update documentation
5. Ensure CI passes

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Maximum line length: 100
- Use docstrings (Google style)

```python
def assess_glycemic_status(
    glucose: Optional[float],
    a1c: Optional[float]
) -> Optional[InferenceResult]:
    """
    Assess glycemic status based on ADA criteria.
    
    Args:
        glucose: Fasting glucose in mg/dL
        a1c: Hemoglobin A1c percentage
    
    Returns:
        InferenceResult with risk level and confidence, or None if insufficient data
    
    Example:
        >>> result = assess_glycemic_status(108, 5.9)
        >>> result.risk_level
        'MODERATE'
    """
```

### Testing

- Test file naming: `test_*.py`
- Function naming: `test_<function>_<scenario>`
- Use fixtures for common setup
- Cover edge cases

```python
def test_assess_glycemic_status_prediabetes():
    result = assess_glycemic_status(108, 5.9)
    assert result.risk_level == "MODERATE"
    assert result.confidence >= 0.85
```

## Clinical Guidelines

When adding or modifying clinical inference:

1. **Cite sources** - Include reference to clinical guideline
2. **Verify thresholds** - Double-check against authoritative sources
3. **Document reasoning** - Explain the clinical logic
4. **Update verification** - Add to PRIORS_VERIFICATION.md

Example:
```python
# ADA Standards of Care 2024
# Prediabetes: FPG 100-125 mg/dL or A1c 5.7-6.4%
if glucose >= 100 and glucose < 126:
    risk = "MODERATE"  # Prediabetes range per ADA
```

## Areas for Contribution

### High Priority
- New biomarker assessments
- Test coverage improvements
- Documentation enhancements
- Bug fixes

### Medium Priority
- Performance optimization
- Error handling improvements
- Logging enhancements
- CLI tools

### Research Opportunities
- Confidence calibration studies
- Multi-marker interaction analysis
- Validation against clinical outcomes

## Questions?

- Open an issue for questions
- Email: abedelhamdan@gmail.com

## License

By contributing, you agree that your contributions will be licensed under the project's license.

---

Thank you for helping make health data more accessible! 🧬
