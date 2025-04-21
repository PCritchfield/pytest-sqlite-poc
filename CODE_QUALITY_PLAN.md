# Code Quality Improvement Plan

This document outlines a phased approach to improving code quality in the pytest-sqlite-poc project.

## Current Status

We've integrated several code quality tools:
- Black (code formatter)
- isort (import sorter)
- Flake8 (linter with docstring checking)
- mypy (type checker)
- Bandit (security linter)
- pre-commit hooks

We've configured these tools with temporary leniency to allow for a gradual improvement process.

## Issues to Address

### Phase 1: Basic Code Formatting (Completed)
- ✅ Configure Black and isort
- ✅ Set up pre-commit hooks
- ✅ Fix line length issues
- ✅ Fix trailing whitespace
- ✅ Fix unused imports

### Phase 2: Type Annotations (In Progress)
- ✅ Add type annotations to dictionaries in `data/sample_data.py`
- ✅ Fix tuple type mismatches in `tests/conftest.py`
- ✅ Create custom type definitions for complex data structures
- 🔄 Add type hints to all public functions (ongoing)

Completed improvements:
- Added `dict[int, list[int]]` and `dict[int, list[dict]]` type annotations to dictionaries
- Created an `AddressTuple` type definition to clarify expected tuple structure
- Fixed type inconsistencies between home and work address tuples
- Added proper imports for typing modules

### Phase 3: Security Improvements
- Address Bandit security warnings:
  - Replace `random` with more appropriate alternatives where needed
  - Fix SQL injection vulnerabilities by using parameterized queries
  - Document cases where `random` is acceptable for non-security purposes

### Phase 4: Docstring Standardization
- Standardize docstring format (Google style)
- Ensure all modules have proper docstrings
- Ensure all public functions have proper docstrings
- Update flake8 configuration to enforce docstring standards

### Phase 5: Code Complexity Reduction
- Refactor complex functions (e.g., `insert_sample_data` in conftest.py)
- Improve test organization
- Reduce duplicate code

## Implementation Strategy

1. **Small, Focused PRs**: Each improvement should be made in small, focused PRs
2. **Test-Driven**: Ensure tests pass after each change
3. **Documentation**: Update documentation as code improves
4. **Gradual Enforcement**: Gradually increase the strictness of linting rules

## Timeline

- Phase 1: Complete
- Phase 2: Next sprint
- Phases 3-5: Subsequent sprints, prioritized based on project needs

## Monitoring Progress

Track progress by:
1. Reducing the number of linting exceptions in configuration files
2. Increasing the percentage of type-annotated code
3. Eliminating security warnings
4. Improving docstring coverage
