# Contributing to AgCluster Container

Thank you for your interest in contributing to AgCluster Container! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- Anthropic API key (for testing)

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/agcluster-container.git
cd agcluster-container
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

3. **Build Docker images**

```bash
docker compose build
```

4. **Run tests**

```bash
pytest tests/
```

## How to Contribute

### Reporting Issues

- Use the GitHub issue tracker
- Check if the issue already exists
- Provide detailed information:
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details (OS, Python version, Docker version)
  - Logs and error messages

### Suggesting Features

- Open an issue with the "enhancement" label
- Describe the feature and its use case
- Explain why it would be valuable

### Submitting Pull Requests

1. **Create a branch**

Use descriptive branch names following this convention:
- `feature/` - New features (e.g., `feature/add-file-upload`)
- `fix/` - Bug fixes (e.g., `fix/session-cleanup`)
- `docs/` - Documentation changes (e.g., `docs/update-readme`)
- `refactor/` - Code refactoring (e.g., `refactor/provider-interface`)
- `test/` - Test additions/changes (e.g., `test/add-integration-tests`)

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**

- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

3. **Run tests and linting**

```bash
# Run all tests
pytest tests/

# Run linting
ruff check src/ tests/

# Run formatting check
black --check src/ tests/

# Apply formatting
black src/ tests/
```

4. **Commit your changes**

Write clear, descriptive commit messages:

```bash
git commit -m "feat: add file upload support

- Add upload endpoint with multipart form support
- Implement provider abstraction for Docker/Fly
- Add comprehensive tests
- Update documentation"
```

Follow conventional commits format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks
- `style:` - Code style changes (formatting, etc.)

5. **Push and create PR**

```bash
git push origin feature/your-feature-name
```

Then open a pull request on GitHub with:
- Clear title and description
- Reference related issues
- Explain what changed and why
- Include test results if applicable

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Maximum line length: 88 characters (Black default)
- Use meaningful variable and function names
- Add docstrings for public functions and classes

**Example:**

```python
from typing import Optional

def create_session(
    api_key: str,
    config_id: str,
    timeout: Optional[int] = None
) -> dict:
    """Create a new agent session.

    Args:
        api_key: Anthropic API key
        config_id: Agent configuration ID
        timeout: Optional timeout in seconds

    Returns:
        Session details dict with session_id and agent_id

    Raises:
        ValueError: If config_id is invalid
    """
    pass
```

### JavaScript/TypeScript (UI)

- Use TypeScript for all new code
- Follow React best practices
- Use functional components with hooks
- Add proper typing

## Testing

### Writing Tests

- Add tests for all new functionality
- Aim for high test coverage (>80%)
- Use descriptive test names
- Follow the AAA pattern (Arrange, Act, Assert)

**Example:**

```python
def test_session_creation_with_valid_config():
    """Test that sessions are created successfully with valid config."""
    # Arrange
    session_manager = SessionManager()
    config = AgentConfig(id="test", name="Test Agent")

    # Act
    session_id = session_manager.create_session("test-api-key", config)

    # Assert
    assert session_id is not None
    assert session_manager.get_session(session_id) is not None
```

### Running Tests

```bash
# All tests
pytest tests/

# Specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# With coverage
pytest --cov=agcluster.container tests/

# Specific test file
pytest tests/unit/test_session_manager.py -v
```

## Documentation

- Update README.md for user-facing changes
- Update docstrings for code changes
- Add comments for complex logic
- Update CHANGELOG.md for notable changes

## Project Structure

```
agcluster-container/
├── src/agcluster/container/
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Core logic (sessions, containers, providers)
│   ├── models/           # Pydantic models
│   └── ui/               # Next.js Web UI
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── configs/              # Agent configurations
├── docker/               # Dockerfiles
└── docs/                 # Documentation
```

## Review Process

1. All PRs require at least one review
2. CI tests must pass
3. Code must be formatted with Black and pass ruff checks
4. Documentation must be updated
5. Maintainers will review and provide feedback
6. Address feedback and push updates
7. Once approved, maintainers will merge

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## Questions?

- Open an issue for questions
- Check existing issues and PRs
- Reach out to maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to AgCluster Container! 🎉
