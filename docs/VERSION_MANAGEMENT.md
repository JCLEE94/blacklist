# Automated Version Management System

## Overview

The Blacklist project now includes a comprehensive automated version management system that ensures version consistency across the entire codebase and automates version bumping based on conventional commit messages.

## 🎯 Key Features

- **Automatic Version Detection**: Analyzes commit messages to determine appropriate version bump type
- **Comprehensive Updates**: Updates ALL version references across the codebase
- **Git Integration**: Pre-push hooks prevent pushes without proper version management
- **CI/CD Integration**: GitHub Actions workflow validates and manages versions
- **Multiple Formats**: Supports various version formats and file types
- **Fallback Mechanisms**: Robust error handling with fallback strategies

## 🚀 Quick Start

### 1. Setup Git Hooks (One-time setup)

```bash
# Setup automated version management
bash scripts/setup-git-hooks.sh

# This will:
# - Make scripts executable
# - Install pre-push hook
# - Validate version management system
```

### 2. Fix Existing Version Inconsistencies

```bash
# Check current version references
python3 scripts/version-manager.py --show-references

# Fix inconsistent version references (interactive)
python3 scripts/fix-version-references.py

# Or dry-run to see what would be changed
python3 scripts/fix-version-references.py --dry-run
```

### 3. Normal Development Workflow

After setup, version management happens automatically:

```bash
# Make your changes
git add .
git commit -m "feat: add new feature"  # or "fix: bug fix"

# Version is automatically bumped on push to main
git push origin main
```

## 📋 Version Bump Rules

The system follows conventional commit standards:

| Commit Type | Version Bump | Example |
|-------------|--------------|---------|
| `fix:` | **Patch** (1.0.X) | `fix: resolve API timeout issue` |
| `feat:` | **Minor** (1.X.0) | `feat: add user authentication` |
| `BREAKING CHANGE:` | **Major** (X.0.0) | `feat!: redesign API structure` |
| Other commits | **Patch** (1.0.X) | `chore: update dependencies` |

## 🛠️ Manual Version Management

### Interactive Version Bump

```bash
# Interactive mode with prompts
python3 scripts/version-manager.py --interactive

# Example output:
# 🔄 Interactive Version Bump
# 📍 Current version: 1.0.37
# 📋 Recent commits:
#    abc123 feat: add new dashboard
#    def456 fix: resolve collection issue
# 
# 🎯 Select bump type:
#    1. patch (1.0.X) - Bug fixes
#    2. minor (1.X.0) - New features  
#    3. major (X.0.0) - Breaking changes
#    4. auto   - Detect from commits
#    5. cancel - Exit without changes
```

### Force Specific Bump Type

```bash
# Force patch version bump
python3 scripts/version-manager.py --bump-type patch

# Force minor version bump
python3 scripts/version-manager.py --bump-type minor

# Force major version bump
python3 scripts/version-manager.py --bump-type major

# Auto-detect from commits
python3 scripts/version-manager.py --bump-type auto
```

### Validation and Inspection

```bash
# Check version consistency across codebase
python3 scripts/version-manager.py --validate-only

# Show all version references
python3 scripts/version-manager.py --show-references

# Show just first 10 references
python3 scripts/version-manager.py --show-references | head -20
```

## 📁 Files Updated by Version Management

The system automatically finds and updates version references in:

### Python Files (`**/*.py`)
- Version variables and constants
- Docstrings and comments
- Configuration values

### Configuration Files
- `**/*.json` - JSON configuration files
- `**/*.yml`, `**/*.yaml` - YAML configuration files
- `**/*.toml` - TOML configuration files

### Docker Files
- `**/Dockerfile*` - Docker build files
- `docker-compose*.yml` - Docker Compose configurations

### Documentation
- `**/*.md` - Markdown documentation
- `**/*.rst` - reStructuredText files
- `**/*.txt` - Text files

### Scripts
- `**/*.sh` - Shell scripts
- `**/*.ps1` - PowerShell scripts

## 🔧 GitHub Actions Integration

The enhanced workflow includes:

### Version Validation
```yaml
- name: Validate version consistency
  run: |
    python3 scripts/version-manager.py --validate-only --project-root .
```

### Automatic Version Bumping
```yaml
- name: Bump version
  run: |
    chmod +x scripts/bump-version.sh
    ./scripts/bump-version.sh
    echo "VERSION=$(cat version.txt)" >> $GITHUB_ENV
```

### Docker Image Tagging
```yaml
# Multiple tags for Docker images
-t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
-t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
-t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:v${{ env.VERSION }}
```

### GitHub Release Creation
Automatically creates GitHub releases with:
- Version tag (`v1.1.5`)
- Release notes with Docker image references
- Links to live system and documentation

## 🔄 Git Hook Workflow

### Pre-push Hook Behavior

The pre-push hook (`/home/jclee/app/blacklist/.git/hooks/pre-push`) automatically:

1. **Branch Detection**: Only runs on pushes to `main` branch
2. **Version Analysis**: Detects commits since last version tag
3. **Version Bump**: Runs comprehensive version management
4. **File Updates**: Updates all version references in codebase
5. **Git Operations**: Creates version commit and git tag
6. **Validation**: Ensures version consistency before push

### Hook Output Example

```bash
🔄 Pre-push hook: Automated Version Management
🎯 Pushing to main branch - running version management
📈 Found 3 commits since last version tag (v1.0.37)
🐍 Running comprehensive version management...
✅ Version management completed successfully
🎯 New version: 1.1.5
📝 Version updates detected - staging changes
✅ Version bump commit created successfully
🏷️  Created tag: v1.1.5
🔍 Running final version validation...
✅ Version validation passed
🎉 Pre-push version management completed successfully
🚀 Push can proceed with version: 1.1.5
```

## 📊 Current Status

### Version File Location
- **Primary**: `/home/jclee/app/blacklist/version.txt`
- **Current Version**: `1.0.37`
- **Format**: Semantic versioning (MAJOR.MINOR.PATCH)

### Known Version References (Examples)
- `CLAUDE.md`: Live System Status comments
- Docker configurations
- GitHub workflow files
- Python source files
- Documentation files

## 🚨 Troubleshooting

### Common Issues

**1. Pre-push Hook Not Running**
```bash
# Check if hook is executable
ls -la .git/hooks/pre-push

# Make executable if needed
chmod +x .git/hooks/pre-push
```

**2. Version Inconsistencies**
```bash
# Check for inconsistent versions
python3 scripts/version-manager.py --validate-only

# Fix inconsistencies
python3 scripts/fix-version-references.py
```

**3. Python Script Errors**
```bash
# Check Python script
python3 scripts/version-manager.py --help

# Use fallback method
bash scripts/bump-version.sh
```

**4. Git Hook Bypass (Emergency)**
```bash
# Skip hooks for emergency push
git push --no-verify origin main
```

### Debug Mode

```bash
# Run with detailed output
python3 scripts/version-manager.py --interactive --project-root .

# Check specific file references
python3 scripts/version-manager.py --show-references | grep "filename"
```

## 🔗 Integration Points

### Docker Registry
- **Registry**: `registry.jclee.me`
- **Image Tags**: 
  - `latest` (always latest build)
  - `v{VERSION}` (semantic version)
  - `{SHA}` (git commit hash)

### Live System
- **Production URL**: https://blacklist.jclee.me/
- **Health Check**: https://blacklist.jclee.me/health
- **Portfolio**: https://jclee94.github.io/blacklist/

### GitHub Integration
- **Actions**: Automated CI/CD with version management
- **Releases**: Automatic release creation with version tags
- **Container Registry**: Multi-tag Docker image publishing

## 💡 Best Practices

### Commit Message Format
```bash
# Good commit messages for automatic detection
git commit -m "feat: add user authentication system"
git commit -m "fix: resolve API timeout issue"
git commit -m "feat!: redesign API structure (BREAKING CHANGE)"

# Avoid generic messages
git commit -m "update code"  # Will default to patch bump
```

### Development Workflow
1. **Feature Branch**: Develop on feature branches
2. **Conventional Commits**: Use conventional commit format
3. **Test Before Merge**: Ensure tests pass before merging to main
4. **Automatic Versioning**: Let the system handle version bumps
5. **Review Releases**: Check generated GitHub releases

### Version Consistency
- Always use the version management system
- Don't manually edit version references
- Run validation before major releases
- Keep version.txt as the single source of truth

---

*This version management system ensures consistent, automated, and reliable version handling across the entire Blacklist project codebase.*