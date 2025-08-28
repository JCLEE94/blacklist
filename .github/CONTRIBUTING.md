# Contributing to Blacklist Management System

First off, thank you for considering contributing to the Blacklist Management System! 🎉

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, please include:

- Clear and descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Environment details (OS, Python version, etc.)

### ✨ Suggesting Features

Feature suggestions are welcome! Please:

- Check if the feature has already been suggested
- Provide a clear use case
- Explain why this feature would be useful
- Consider implementation complexity

### 🔧 Pull Requests

1. **Fork the repository** and create your branch from `develop`
2. **Follow the coding standards** (see below)
3. **Write tests** for new functionality
4. **Update documentation** as needed
5. **Ensure all tests pass**
6. **Submit a pull request**

## Development Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git
- PostgreSQL 15+ (for local development)
- Redis 7+ (for local development)

### Local Development

```bash
# Clone the repository
git clone https://github.com/qws941/blacklist.git
cd blacklist

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup environment
cp config/.env.example .env
# Edit .env with your settings

# Initialize database
python scripts/init_database.py

# Run tests
pytest

# Start development server
python app/main.py --debug
```

### Docker Development

```bash
# Build and start services
docker-compose up --build

# Run tests in container
docker-compose exec blacklist pytest

# View logs
docker-compose logs -f blacklist
```

## Coding Standards

### Python Style Guide

We follow PEP 8 with these specifications:

- **Line length**: 88 characters (Black default)
- **Imports**: Sorted with isort
- **Formatting**: Enforced with Black
- **Type hints**: Required for new code
- **Docstrings**: Google style

### File Size Limits

- **Maximum lines per file**: 500
- **Maximum lines per function**: 100
- **Maximum complexity**: 10 (McCabe)

### Code Quality Tools

```bash
# Format code
black .
isort .

# Lint
flake8 .
pylint src/

# Security check
bandit -r src/
safety check

# Type checking
mypy src/
```

### Git Commit Messages

We use conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance
- `perf:` Performance improvement

Example:
```
feat: add REGTECH collector retry mechanism

- Implement exponential backoff
- Add max retry configuration
- Update tests for retry logic

Closes #123
```

### Testing

- **Minimum coverage**: 80%
- **Test naming**: `test_<function_name>_<scenario>`
- **Use pytest fixtures** for setup/teardown
- **Mock external dependencies**

```python
def test_collector_retry_on_failure():
    """Test that collector retries on network failure."""
    # Test implementation
```

## Project Structure

```
blacklist/
├── app/               # Main application
│   └── main.py       # Entry point
├── src/              # Source code
│   └── core/         # Core modules
│       ├── collectors/    # Data collectors
│       ├── routes/       # API routes
│       └── services/     # Business logic
├── tests/            # Test files
│   ├── unit/        # Unit tests
│   └── integration/ # Integration tests
├── docker/          # Docker configurations
├── scripts/         # Utility scripts
└── docs/           # Documentation
```

## Review Process

### Pull Request Review Criteria

1. **Code Quality**
   - Follows coding standards
   - No code smells
   - Proper error handling

2. **Testing**
   - All tests pass
   - New tests for new features
   - Coverage maintained/improved

3. **Documentation**
   - Code is well-commented
   - README updated if needed
   - API documentation current

4. **Security**
   - No hardcoded credentials
   - Input validation
   - SQL injection prevention

5. **Performance**
   - No obvious bottlenecks
   - Efficient queries
   - Proper caching

### Review Timeline

- **Initial review**: Within 48 hours
- **Follow-up**: Within 24 hours of changes
- **Merge**: After approval and CI pass

## Release Process

We use semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Releases are automated through GitHub Actions when tags are pushed.

## Documentation

- **Code comments**: Explain "why", not "what"
- **README**: Keep updated with new features
- **API docs**: Document all endpoints
- **Architecture**: Update diagrams as needed

## Getting Help

- **Discord**: [Join our server](https://discord.gg/blacklist)
- **Discussions**: Use GitHub Discussions
- **Issues**: For bugs and features
- **Email**: support@jclee.me

## Recognition

Contributors are recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Release notes
- Project documentation

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).