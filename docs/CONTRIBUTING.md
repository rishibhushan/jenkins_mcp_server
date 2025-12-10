# Contributing to Jenkins MCP Server

Thank you for your interest in contributing to Jenkins MCP Server! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in all interactions.

### Expected Behavior

- ✅ Be respectful and inclusive
- ✅ Welcome newcomers and help them get started
- ✅ Provide constructive feedback
- ✅ Focus on what is best for the community
- ✅ Show empathy towards others

### Unacceptable Behavior

- ❌ Harassment, discrimination, or offensive comments
- ❌ Trolling or insulting/derogatory comments
- ❌ Public or private harassment
- ❌ Publishing others' private information
- ❌ Other unprofessional conduct

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** installed
- **Node.js 14+** installed (for npm wrapper)
- **Git** for version control
- A **GitHub account**
- Access to a **Jenkins instance** (for testing)

### Finding an Issue

1. **Check existing issues**: Browse [open issues](https://github.com/rishibhushan/jenkins_mcp_server/issues)
2. **Good first issues**: Look for issues labeled `good first issue`
3. **Help wanted**: Check issues labeled `help wanted`
4. **Create new issue**: If you find a bug or have a feature request

### Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements to documentation
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `performance` - Performance improvements
- `security` - Security-related issues

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/jenkins_mcp_server.git
cd jenkins_mcp_server

# Add upstream remote
git remote add upstream https://github.com/rishibhushan/jenkins_mcp_server.git
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install in editable mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# If requirements-dev.txt doesn't exist, install manually:
pip install pytest pytest-asyncio pytest-cov black mypy flake8 pylint
```

### 4. Configure Jenkins Connection

Create a `.env` file for testing:

```bash
# .env
JENKINS_URL=http://your-jenkins-server:8080
JENKINS_USERNAME=your-username
JENKINS_TOKEN=your-api-token

# Optional: Performance tuning
JENKINS_TIMEOUT=30
JENKINS_CONNECT_TIMEOUT=10
```

### 5. Verify Setup

```bash
# Run tests
pytest tests/ -v

# Run the server
python -m jenkins_mcp_server --env-file .env --verbose
```

---

## Making Changes

### Branch Naming Convention

Create a branch with a descriptive name:

```bash
# Feature branch
git checkout -b feature/add-pipeline-support

# Bug fix branch
git checkout -b fix/timeout-error-handling

# Documentation branch
git checkout -b docs/update-api-reference
```

### Branch Prefixes

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or modifications
- `perf/` - Performance improvements
- `chore/` - Maintenance tasks

### Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes**
   - Follow code style guidelines
   - Write/update tests
   - Update documentation

3. **Test your changes**
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Run type checking
   mypy src/
   
   # Run linting
   flake8 src/ tests/
   black --check src/ tests/
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add pipeline support"
   ```

5. **Keep your fork updated**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/my-new-feature
   ```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage
pytest tests/ --cov=jenkins_mcp_server --cov-report=html

# Run only fast tests (skip integration)
pytest tests/ -v -m "not integration"
```

### Writing Tests

#### Unit Tests

```python
# tests/test_validation.py
import pytest
from jenkins_mcp_server.server import validate_job_name

def test_validate_job_name_success():
    """Test valid job name"""
    result = validate_job_name("my-job")
    assert result == "my-job"

def test_validate_job_name_empty():
    """Test empty job name raises error"""
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_job_name("")

def test_validate_job_name_wrong_type():
    """Test non-string job name raises error"""
    with pytest.raises(ValueError, match="must be a string"):
        validate_job_name(123)
```

#### Async Tests

```python
# tests/test_cache.py
import pytest
import asyncio
from jenkins_mcp_server.cache import CacheManager

@pytest.mark.asyncio
async def test_cache_set_get():
    """Test cache set and get operations"""
    cache = CacheManager()
    await cache.set("key", "value", ttl_seconds=60)
    result = await cache.get("key")
    assert result == "value"

@pytest.mark.asyncio
async def test_cache_expiry():
    """Test cache expiration"""
    cache = CacheManager()
    await cache.set("key", "value", ttl_seconds=1)
    await asyncio.sleep(2)
    result = await cache.get("key")
    assert result is None
```

#### Integration Tests

```python
# tests/test_integration.py
import pytest
from jenkins_mcp_server.jenkins_client import JenkinsClient
from jenkins_mcp_server.config import JenkinsSettings

@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_jobs_integration():
    """Test listing jobs from real Jenkins instance"""
    settings = JenkinsSettings(
        url=os.getenv("JENKINS_URL"),
        username=os.getenv("JENKINS_USERNAME"),
        token=os.getenv("JENKINS_TOKEN")
    )
    client = JenkinsClient(settings)
    jobs = client.get_jobs()
    assert isinstance(jobs, list)
    assert len(jobs) > 0
```

### Test Organization

```
tests/
├── unit/
│   ├── test_config.py         # Configuration tests
│   ├── test_validation.py     # Input validation tests
│   ├── test_cache.py          # Cache tests
│   └── test_metrics.py        # Metrics tests
├── integration/
│   ├── test_jenkins_client.py # Jenkins API tests
│   └── test_server.py         # MCP server tests
├── conftest.py                # Pytest fixtures
└── fixtures/
    ├── job_config.xml         # Test fixtures
    └── mock_responses.json    # Mock API responses
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
from jenkins_mcp_server.config import JenkinsSettings

@pytest.fixture
def test_settings():
    """Provide test Jenkins settings"""
    return JenkinsSettings(
        url="http://test-jenkins:8080",
        username="test-user",
        token="test-token"
    )

@pytest.fixture
def mock_jenkins_client(mocker, test_settings):
    """Provide mocked Jenkins client"""
    client = mocker.Mock()
    client.get_jobs.return_value = [
        {"name": "test-job", "url": "http://test-jenkins/job/test-job/"}
    ]
    return client
```

---

## Code Style

### Python Style Guide

We follow [PEP 8](https://peps.python.org/pep-0008/) with some modifications.

#### Formatting

Use **Black** for automatic formatting:

```bash
# Format all code
black src/ tests/

# Check without modifying
black --check src/ tests/
```

#### Linting

Use **Flake8** for linting:

```bash
# Run flake8
flake8 src/ tests/

# Configuration in setup.cfg:
[flake8]
max-line-length = 100
exclude = .git,__pycache__,.venv
ignore = E203,W503
```

#### Type Checking

Use **mypy** for type checking:

```bash
# Run mypy
mypy src/

# Configuration in setup.cfg:
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

### Code Guidelines

#### 1. Type Hints

Always use type hints:

```python
# Good ✅
def validate_job_name(job_name: Any) -> str:
    """Validate job name parameter"""
    if not isinstance(job_name, str):
        raise ValueError(f"job_name must be string, got {type(job_name).__name__}")
    return job_name.strip()

# Bad ❌
def validate_job_name(job_name):
    if not isinstance(job_name, str):
        raise ValueError("Invalid type")
    return job_name.strip()
```

#### 2. Docstrings

Use Google-style docstrings:

```python
# Good ✅
def trigger_build(job_name: str, parameters: Optional[Dict] = None) -> Dict:
    """
    Trigger a Jenkins job build.
    
    Args:
        job_name: Name of the Jenkins job
        parameters: Optional build parameters
        
    Returns:
        Dictionary containing queue_id and build_number
        
    Raises:
        ValueError: If job_name is invalid
        ConnectionError: If cannot connect to Jenkins
        
    Example:
        >>> result = trigger_build("my-job", {"ENV": "prod"})
        >>> print(result["queue_id"])
        12345
    """
    pass

# Bad ❌
def trigger_build(job_name, parameters=None):
    # Triggers a build
    pass
```

#### 3. Error Handling

Use specific exceptions with clear messages:

```python
# Good ✅
try:
    job_info = client.get_job_info(job_name)
except jenkins.JenkinsException as e:
    if "404" in str(e):
        raise ValueError(
            f"Job '{job_name}' not found. "
            f"Check job name (case-sensitive) or use list-jobs to see available jobs."
        )
    raise

# Bad ❌
try:
    job_info = client.get_job_info(job_name)
except Exception as e:
    raise ValueError("Error")
```

#### 4. Logging

Use appropriate log levels:

```python
# Good ✅
logger.debug(f"Fetching job details for '{job_name}'")
logger.info(f"Build triggered: {job_name} #{build_number}")
logger.warning(f"Cache expired for key '{cache_key}'")
logger.error(f"Failed to connect to Jenkins: {error}", exc_info=True)

# Bad ❌
print(f"Getting job {job_name}")  # Don't use print
logger.info(f"Some error: {e}")   # Use appropriate level
```

#### 5. Constants

Use uppercase for constants:

```python
# Good ✅
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
CACHE_TTL_SECONDS = 60

# Bad ❌
default_timeout = 30
maxRetries = 3
```

#### 6. Naming Conventions

```python
# Functions and variables: snake_case
def get_job_details(job_name: str) -> Dict:
    cache_key = f"job:{job_name}"
    return cached_data

# Classes: PascalCase
class JenkinsClient:
    pass

class CacheManager:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_CACHE_SIZE = 1000
DEFAULT_TTL = 60

# Private methods/variables: prefix with _
def _internal_helper(self):
    pass

_global_cache = {}
```

---

## Commit Guidelines

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature/bug change)
- `perf`: Performance improvements
- `test`: Adding/updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples

```bash
# Feature
git commit -m "feat(cache): add TTL-based caching system"

# Bug fix
git commit -m "fix(validation): handle empty job names correctly"

# Documentation
git commit -m "docs(api): add examples for all tools"

# Performance
git commit -m "perf(client): reduce API calls by 33%"

# Breaking change
git commit -m "feat(config)!: change timeout default from 30s to 10s

BREAKING CHANGE: Default timeout reduced for faster failure detection.
Users relying on 30s default may need to explicitly set JENKINS_TIMEOUT=30"
```

### Commit Best Practices

1. **One logical change per commit**
   ```bash
   # Good ✅
   git commit -m "feat(cache): add cache manager"
   git commit -m "feat(server): integrate cache in list-jobs"
   
   # Bad ❌
   git commit -m "add cache and fix bugs and update docs"
   ```

2. **Write descriptive messages**
   ```bash
   # Good ✅
   git commit -m "fix(timeout): increase default from 10s to 30s for slow networks"
   
   # Bad ❌
   git commit -m "fix timeout"
   ```

3. **Reference issues**
   ```bash
   git commit -m "fix(auth): handle 401 errors gracefully

   Closes #123
   Fixes #124"
   ```

---

## Pull Request Process

### Before Submitting

1. ✅ **Run all tests**
   ```bash
   pytest tests/ -v
   ```

2. ✅ **Check code style**
   ```bash
   black --check src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

3. ✅ **Update documentation**
   - Update README.md if needed
   - Update API.md for new tools
   - Add/update docstrings

4. ✅ **Update CHANGELOG.md**
   ```markdown
   ## [Unreleased]
   
   ### Added
   - New pipeline support tools (#123)
   
   ### Fixed
   - Timeout error handling (#124)
   ```

5. ✅ **Ensure branch is up-to-date**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

### Creating Pull Request

1. **Push your branch**
   ```bash
   git push origin feature/my-feature
   ```

2. **Open PR on GitHub**
   - Go to your fork on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template

3. **PR Title Format**
   ```
   feat(cache): add TTL-based caching system
   ```

4. **PR Description Template**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [x] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Changes Made
   - Added cache.py module
   - Integrated caching in list-jobs
   - Added cache statistics tool
   
   ## Testing
   - [x] Unit tests added
   - [x] Integration tests added
   - [x] Manual testing completed
   
   ## Checklist
   - [x] Code follows style guidelines
   - [x] Self-review completed
   - [x] Comments added for complex code
   - [x] Documentation updated
   - [x] Tests pass locally
   - [x] No new warnings
   
   ## Related Issues
   Closes #123
   Related to #124
   ```

### PR Review Process

1. **Automated Checks** (CI/CD)
   - ✅ Tests must pass
   - ✅ Code style checks must pass
   - ✅ Type checking must pass

2. **Code Review**
   - Maintainers will review your code
   - Address feedback promptly
   - Update PR as needed

3. **Approval**
   - At least 1 maintainer approval required
   - All conversations must be resolved

4. **Merge**
   - Maintainer will merge your PR
   - Branch will be deleted automatically

### After Merge

1. **Update your fork**
   ```bash
   git checkout main
   git fetch upstream
   git merge upstream/main
   git push origin main
   ```

2. **Delete your branch**
   ```bash
   git branch -d feature/my-feature
   git push origin --delete feature/my-feature
   ```

---

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality
- **PATCH** version for backwards-compatible bug fixes

Example: `2.1.3`
- Major: 2
- Minor: 1
- Patch: 3

### Release Workflow

**For Maintainers Only**

1. **Update version**
   ```python
   # src/jenkins_mcp_server/__init__.py
   __version__ = "2.1.0"
   ```

2. **Update CHANGELOG.md**
   ```markdown
   ## [2.1.0] - 2024-12-15
   
   ### Added
   - Pipeline support (#123)
   - Batch operations (#124)
   
   ### Fixed
   - Timeout handling (#125)
   ```

3. **Create release commit**
   ```bash
   git add .
   git commit -m "chore(release): v2.1.0"
   git tag -a v2.1.0 -m "Release v2.1.0"
   ```

4. **Push to GitHub**
   ```bash
   git push origin main
   git push origin v2.1.0
   ```

5. **Create GitHub Release**
   - Go to Releases on GitHub
   - Click "Create a new release"
   - Select tag v2.1.0
   - Fill in release notes
   - Publish release

6. **Publish to npm**
   ```bash
   npm publish --access public
   ```

7. **Publish to PyPI** (optional)
   ```bash
   python -m build
   twine upload dist/*
   ```

---

## Documentation

### Updating Documentation

When making changes, update relevant documentation:

#### README.md
- Update feature list
- Add usage examples
- Update configuration section

#### docs/API.md
- Document new tools
- Update tool schemas
- Add examples

#### docs/ARCHITECTURE.md
- Document new modules
- Update architecture diagrams
- Add technical details

### Writing Good Documentation

1. **Be Clear and Concise**
   ```markdown
   # Good ✅
   The `timeout` parameter controls how long to wait for a response.
   
   # Bad ❌
   The timeout thing is for when you want to wait or something
   ```

2. **Provide Examples**
   ```markdown
   # Good ✅
   ```bash
   # Set timeout to 60 seconds
   export JENKINS_TIMEOUT=60
   ```
   
   # Bad ❌
   Set the timeout variable.
   ```

3. **Use Visual Aids**
   ```markdown
   # Good ✅
   ```
   Request → Validate → Cache Check → API Call → Response
   ```
   
   # Bad ❌
   First it validates then checks cache and calls API
   ```

---

## Getting Help

### Resources

- **Documentation**: [docs/](../docs/)
- **Issues**: [GitHub Issues](https://github.com/rishibhushan/jenkins_mcp_server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rishibhushan/jenkins_mcp_server/discussions)

### Questions

- Create a [Discussion](https://github.com/rishibhushan/jenkins_mcp_server/discussions/new) for questions
- Tag with `question` label
- Search existing discussions first

### Reporting Bugs

1. **Search existing issues** first
2. **Create new issue** if not found
3. **Use bug report template**
4. **Provide**:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Logs/screenshots

### Feature Requests

1. **Search existing issues** first
2. **Create new issue** with `enhancement` label
3. **Describe**:
   - Use case
   - Expected behavior
   - Benefits
   - Example usage

---

## Recognition

Contributors will be:

- ✨ Listed in README.md
- 🏆 Mentioned in release notes
- 🎖️ Credited in commits
- 💯 Appreciated by the community!

### Hall of Fame

Top contributors:
- Feature contributors
- Bug fixers
- Documentation writers
- Issue reporters

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Thank You! 🎉

Thank you for contributing to Jenkins MCP Server! Your contributions help make CI/CD automation more accessible and powerful.

---

**Questions?** Open a [Discussion](https://github.com/rishibhushan/jenkins_mcp_server/discussions)

**Found a bug?** Open an [Issue](https://github.com/rishibhushan/jenkins_mcp_server/issues)

**Want to chat?** Join our [Discussions](https://github.com/rishibhushan/jenkins_mcp_server/discussions)
