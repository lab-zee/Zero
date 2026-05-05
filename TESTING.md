# Testing Guide

## Overview

LabZ has comprehensive test coverage for both backend and frontend with CI/CD integration.

**Target Coverage**: 70% minimum (enforced in CI)

---

## Backend Testing (Python/pytest)

### Setup

```bash
cd backend
pip install -r requirements.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::TestUserModel::test_create_user

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov --cov-report=html
```

### Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py           # Fixtures and test configuration
├── test_models.py        # Database model tests
├── test_api.py          # API endpoint tests
└── test_agents.py       # Agent system tests
```

### Key Fixtures

- `db` - Fresh database session for each test
- `client` - FastAPI test client
- `test_user` - Pre-created test user
- `admin_user` - Pre-created admin user
- `test_organization` - Pre-created test organization
- `test_thread` - Pre-created test thread
- `test_query` - Pre-created test query

### Writing Tests

```python
def test_create_user(db: Session):
    """Test creating a user."""
    user = models.User(
        email="test@example.com",
        username="testuser",
        password_hash=auth.hash_password("password"),
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
```

---

## Frontend Testing (Vitest + React Testing Library)

### Setup

```bash
cd frontend
npm install
```

### Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui

# Watch mode
npm test -- --watch

# Run specific test file
npm test -- src/tests/components/ReAskButton.test.tsx
```

### Test Structure

```
frontend/src/tests/
├── setup.ts                          # Test configuration
├── components/
│   ├── ReAskButton.test.tsx
│   └── ProgressTimeline.test.tsx
└── utils/
    └── validation.test.ts
```

### Writing Tests

```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { ReAskButton } from '../../components/ReAskButton';

const renderWithChakra = (ui: React.ReactElement) => {
  return render(<ChakraProvider>{ui}</ChakraProvider>);
};

describe('ReAskButton', () => {
  it('renders re-ask button', () => {
    const mockOnReAsk = vi.fn();
    renderWithChakra(
      <ReAskButton
        queryId={1}
        currentMode="light"
        onReAsk={mockOnReAsk}
      />
    );

    expect(screen.getByText('Re-ask')).toBeInTheDocument();
  });
});
```

---

## Continuous Integration

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

### CI Workflow

1. **Backend Tests** - Pytest with PostgreSQL service
2. **Frontend Tests** - Vitest with coverage
3. **Linting** - Code quality checks
4. **Build** - Frontend build verification

### Coverage Reports

Coverage reports are uploaded to Codecov:
- Backend: `backend-coverage`
- Frontend: `frontend-coverage`

View coverage at: `https://codecov.io/gh/your-org/LabZ`

---

## Coverage Requirements

**Minimum Coverage**: 70% (enforced in CI)

### Current Coverage

Run `pytest --cov` or `npm run test:coverage` to see current coverage.

### Coverage Goals

- **Models**: 90%+
- **API Endpoints**: 80%+
- **Critical Components**: 85%+
- **Utilities**: 90%+

---

## Best Practices

### Backend

✅ **Do:**
- Use fixtures for common test data
- Test happy path AND error cases
- Mock external services (LLM APIs, web scraping)
- Test database constraints
- Test authentication/authorization

❌ **Don't:**
- Make real API calls to external services
- Commit test database files
- Skip error case testing

### Frontend

✅ **Do:**
- Wrap components in ChakraProvider for testing
- Test user interactions (clicks, form inputs)
- Mock API calls
- Test loading and error states
- Test accessibility

❌ **Don't:**
- Test implementation details
- Test third-party library internals
- Snapshot test everything

---

## Debugging Tests

### Backend

```bash
# Run with print statements visible
pytest -s

# Run with debugger
pytest --pdb

# Stop on first failure
pytest -x
```

### Frontend

```bash
# Run with UI for debugging
npm run test:ui

# Debug specific test
npm test -- --reporter=verbose ReAskButton.test.tsx
```

---

## Adding New Tests

### Backend Test Checklist

- [ ] Add test file in `backend/tests/`
- [ ] Import required fixtures from `conftest.py`
- [ ] Test happy path
- [ ] Test error cases
- [ ] Test edge cases
- [ ] Run coverage check

### Frontend Test Checklist

- [ ] Add test file in `frontend/src/tests/`
- [ ] Wrap components in ChakraProvider
- [ ] Test rendering
- [ ] Test user interactions
- [ ] Test props and callbacks
- [ ] Run coverage check

---

## Troubleshooting

### "ImportError: cannot import name 'X'"

Ensure you're running tests from the correct directory:
```bash
cd backend && pytest
```

### "Module not found" (Frontend)

Install dependencies:
```bash
cd frontend && npm install
```

### "Database connection error"

Check that PostgreSQL is running (for local tests with real DB).
Tests use in-memory SQLite by default.

---

*Last Updated: 2026-01-31*
