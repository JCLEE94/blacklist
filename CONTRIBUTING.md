# Contributing to Blacklist Management System

Thank you for your interest in contributing to the Blacklist Management System! This document provides guidelines and information for contributors.

## 🌟 Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to ensure a welcoming environment for all contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git
- Make

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/jclee94/blacklist.git
   cd blacklist
   ```

2. **Initialize development environment**
   ```bash
   make init
   ```

3. **Start development services**
   ```bash
   make start
   ```

4. **Run tests**
   ```bash
   make test
   ```

## 📝 Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Follow our coding standards (see below)
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes
```bash
make lint          # Code quality checks
make test          # Run all tests
make security      # Security scans
```

### 4. Submit Pull Request
- Create a pull request against the `main` branch
- Fill out the PR template completely
- Ensure all CI checks pass

## 🎯 Coding Standards

### Python Code Style
- Follow PEP 8 style guide
- Use Black for code formatting
- Use isort for import sorting
- Maximum line length: 88 characters

### File Organization
- Maximum 500 lines per Python file
- Use clear, descriptive function and variable names
- Add docstrings to all public functions and classes

### Testing Requirements
- Maintain 95% test coverage
- Write unit tests for all new functions
- Add integration tests for new features
- Use real data in tests, avoid mocking core functionality

### Documentation
- Update API documentation for changes
- Add inline comments for complex logic
- Update README if needed

## 🏗️ Architecture Guidelines

### CNCF Compliance
This project follows CNCF Cloud Native standards:
- Use container-first approach
- Follow 12-factor app principles
- Implement health checks and metrics
- Use declarative configuration

### Directory Structure
Follow the established CNCF structure:
```
cmd/            # Application entry points
internal/       # Internal packages
pkg/            # Public packages
api/            # API definitions
charts/         # Helm charts
deployments/    # Deployment manifests
```

## 🐛 Bug Reports

### Before Submitting
1. Search existing issues
2. Reproduce the bug
3. Gather system information

### Bug Report Template
```markdown
**Description**
Brief description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. ...

**Expected Behavior**
What should happen

**Actual Behavior** 
What actually happens

**Environment**
- OS: [e.g., Ubuntu 20.04]
- Python version: [e.g., 3.9.7]
- Docker version: [e.g., 20.10.8]
```

## 💡 Feature Requests

### Feature Request Template
```markdown
**Feature Description**
Clear description of the feature

**Use Case**
Why this feature is needed

**Proposed Implementation**
How you think it should work

**Additional Context**
Any other relevant information
```

## 🔄 Pull Request Process

### PR Requirements
- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Security scan passes
- [ ] CNCF compliance maintained

### Review Process
1. Automated checks must pass
2. At least one maintainer review required
3. Address all review feedback
4. Squash commits before merging

## 🛡️ Security

### Reporting Security Issues
- **DO NOT** open public issues for security vulnerabilities
- Email security concerns to: security@jclee.me
- Include detailed description and reproduction steps

### Security Guidelines
- Never commit secrets or credentials
- Use environment variables for configuration
- Follow secure coding practices
- Run security scans before submitting

## 📞 Getting Help

- **Documentation**: Check our [docs/](docs/) directory
- **Issues**: Search existing GitHub issues
- **Questions**: Open a discussion on GitHub

## 📄 License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## 🙏 Recognition

Contributors will be recognized in:
- CHANGELOG.md for significant contributions
- GitHub contributors list
- Release notes for major features

Thank you for contributing to the Blacklist Management System! 🎉