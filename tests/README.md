# Testing Guide

This directory contains comprehensive tests for the SignalTrader application, organized by test type and component.

## Test Structure

```
tests/
├── fixtures/              # Test fixtures and mock data
│   ├── __init__.py
│   ├── test_base.py      # Base test class with utilities
│   └── mock_data.py      # Mock objects and test data
├── unit/                 # Unit tests (isolated components)
│   ├── analyzer/         # Signal analyzer tests
│   ├── metatrader/       # MT5 integration tests
│   ├── database/         # Database operation tests
│   ├── configure/        # Configuration tests
│   └── ...
├── integration/          # Integration tests (component interaction)
│   ├── metatrader/       # Full MT5 workflow tests
│   ├── database/         # Database integration tests
│   └── telegram/         # Telegram integration tests
├── utils/                # Test utilities and data generators
│   └── ScrapperGenerator/ # Signal data generation tools
└── __init__.py           # Test runner utilities
```

## Running Tests

### Run All Tests
```bash
python -m pytest tests/
# or
python tests/__init__.py
```

### Run Unit Tests Only
```bash
python -m pytest tests/unit/
# or
python -c "from tests import run_unit_tests; run_unit_tests()"
```

### Run Integration Tests Only
```bash
python -m pytest tests/integration/
# or
python -c "from tests import run_integration_tests; run_integration_tests()"
```

### Run Specific Test File
```bash
python -m pytest tests/unit/analyzer/test_text_processor.py
```

### Run Tests with Coverage
```bash
pip install pytest-cov
pytest --cov=app --cov-report=html tests/
```

## Test Categories

### Unit Tests
- **Analyzer Tests**: Signal parsing, text processing, action detection
- **MetaTrader Tests**: Lot calculation, validation, connection mocking
- **Database Tests**: Repository operations, model validation
- **Configuration Tests**: Settings loading, validation

### Integration Tests
- **MetaTrader Integration**: Full trading workflows with mocked MT5
- **Database Integration**: Multi-table operations, migrations
- **Telegram Integration**: Message handling, API interactions

## Test Fixtures

### TestBase Class
All tests inherit from `TestBase` which provides:
- Temporary directory management
- Logging configuration
- Common assertion helpers
- Mock utilities

### Mock Data
Pre-configured mock objects for:
- MT5 connections and responses
- Telegram messages
This directory contains comprehensive tests for the SignalTrader application, organized by test type and component.
- Trading signals

## Writing New Tests

### Basic Test Structure
```python
import unittest
from tests.fixtures import TestBase

class TestMyComponent(TestBase):

    def setUp(self):
        super().setUp()
        # Component-specific setup

    def test_feature(self):
        # Arrange
        # Act
        # Assert
```

### Using Mocks
```python
from unittest.mock import patch, MagicMock

def test_with_mock(self):
    with patch('module.function') as mock_func:
        mock_func.return_value = expected_value
        # Test code
```

### Database Testing
```python
@patch('sqlite3.connect')
def test_database_operation(self, mock_connect):
    mock_conn = self.mock_database_connection()
    mock_connect.return_value = mock_conn
    # Test database operations
```

## Test Data

### Signal Test Data
Located in `fixtures/mock_data.py`:
- Sample trading signals in multiple formats
- Expected parsing results
- Edge cases and error conditions

### MT5 Test Data
- Mock positions and orders
- Simulated market data
- Error conditions

## Continuous Integration

Tests are designed to run in CI environments:
- No external dependencies required
- All external APIs mocked
- Fast execution (< 30 seconds)
- Deterministic results

## Test Coverage Goals

- **Unit Tests**: > 80% coverage of individual functions
- **Integration Tests**: Cover all major workflows
- **Error Handling**: Test all error paths
- **Edge Cases**: Boundary conditions and unusual inputs

## Adding Test Data

### Signal Data
Add new test signals to `fixtures/mock_data.py`:
```python
analyzer_test_data.append({
    "input": "NEW_SIGNAL_FORMAT",
    "expected": {
        "action": "BUY",
        "symbol": "SYMBOL",
        "price": 1.2345,
        "sl": 1.2200,
        "tp": [1.2500, 1.2600]
    }
})
```

### Mock Objects
Extend mock data in `fixtures/mock_data.py` for new test scenarios.

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `PYTHONPATH` includes project root
2. **Mock Failures**: Check mock setup and return values
3. **Database Tests**: Verify mock connection setup
4. **Coverage Issues**: Check test file discovery

### Debug Mode
```bash
pytest -v -s tests/unit/analyzer/test_text_processor.py::TestTextProcessor::test_clean_text_basic
```

## Contributing

When adding new features:
1. Add corresponding unit tests
2. Update integration tests if needed
3. Ensure all tests pass
4. Update this documentation