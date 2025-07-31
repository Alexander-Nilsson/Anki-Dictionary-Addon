# CI/CD Setup for Anki Dictionary Addon

This document explains how to use the automated CI/CD pipeline for the Anki Dictionary Addon.

## Overview

The CI/CD pipeline automatically:
- ✅ Runs tests on every push and pull request
- ✅ Builds both `.ankiaddon` and standalone packages
- ✅ Creates releases with downloadable assets
- ✅ Performs code quality checks

## Files Added

### GitHub Actions Workflow
- `.github/workflows/ci-cd.yml` - Main CI/CD pipeline

### Build and Release Scripts
- `build.py` - Build script for local development and CI
- `scripts/release.py` - Automated release script
- `dev.py` - Development helper script

### Configuration
- Enhanced `pyproject.toml` with build configuration and tool settings

## Usage

### For Development

#### Local Development Commands
```bash
# Install development dependencies
python dev.py install

# Run tests
python dev.py test

# Check code formatting and linting
python dev.py lint

# Format code
python dev.py format

# Build packages locally
python dev.py build

# Run all CI checks locally
python dev.py ci

# Show project info
python dev.py info
```

#### Build Packages Manually
```bash
# Build everything (addon + standalone)
python build.py all

# Build just the addon
python build.py build
python build.py package

# Build just standalone
python build.py standalone

# Clean build artifacts
python build.py clean

# Show build information
python build.py info
```

### For Releases

#### Option 1: Automated Release (Recommended)
```bash
# Update version and create release
python scripts/release.py 1.2.3

# This will:
# 1. Update version in pyproject.toml
# 2. Commit the change
# 3. Create and push a git tag
# 4. GitHub Actions builds and creates the release automatically
```

#### Option 2: Manual GitHub Release
1. Go to GitHub → Releases → "Create a new release"
2. Create a new tag (e.g., `v1.2.3`)
3. Fill in release notes
4. Publish release
5. GitHub Actions will automatically build and attach the packages

### Continuous Integration

#### Automatic Testing
- **On Push**: Tests run on `main`, `develop`, and `pyright` branches
- **On Pull Request**: Tests run for PRs targeting `main`
- **Testing includes**:
  - Code linting with flake8
  - Code formatting check with black
  - Type checking with mypy (optional)
  - Addon structure validation
  - Test suite execution

#### Automatic Building
- **Triggers**: Push to main branches (not PRs)
- **Outputs**: 
  - `.ankiaddon` package for Anki installation
  - Standalone `.zip` package
- **Artifacts**: Stored for 30 days

#### Automatic Releases
- **Trigger**: Publishing a GitHub release
- **Process**:
  1. Builds both addon and standalone packages
  2. Uploads packages as release assets
  3. Creates formatted release notes
  4. Includes installation instructions

## Workflow Details

### Jobs

1. **Test Job**
   - Runs on Ubuntu with Python 3.11
   - Installs dependencies with uv or pip
   - Runs linting, formatting checks, and tests
   - Validates addon structure

2. **Build Job**
   - Runs after tests pass
   - Only on non-PR events
   - Creates both addon and standalone packages
   - Uploads artifacts

3. **Release Job**
   - Runs on GitHub release publication
   - Builds packages and uploads to release
   - Creates formatted release description

### Supported Branches
- `main` - Production releases
- `develop` - Development branch
- `pyright` - Current working branch
- Pull requests to `main`

## Development Workflow

### Feature Development
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and test locally
python dev.py ci

# Push and create PR
git push origin feature/new-feature
# Create PR on GitHub - tests run automatically
```

### Release Process
```bash
# On main branch, ready to release
git checkout main
git pull origin main

# Create release (automated)
python scripts/release.py 2.1.0

# Or manually:
# 1. Update version in pyproject.toml
# 2. Commit and push
# 3. Create release on GitHub
```

## Customization

### Adding More Tests
Add test files to `tests/` directory following the pattern `test_*.py`.

### Modifying Build Process
Edit `build.py` to change which files are included in packages.

### Changing CI Configuration
Edit `.github/workflows/ci-cd.yml` to modify the CI/CD pipeline.

### Tool Configuration
Modify tool settings in `pyproject.toml`:
- `[tool.black]` - Code formatting
- `[tool.pytest.ini_options]` - Test configuration
- `[tool.mypy]` - Type checking

## Troubleshooting

### Build Failures
```bash
# Check build locally
python build.py all

# Validate build output
python build.py validate

# Check what's included
python build.py info
```

### Test Failures
```bash
# Run tests locally
python dev.py test

# Run specific test file
python -m pytest tests/test_specific.py -v
```

### Release Issues
```bash
# Check git status
git status

# Check current version
python dev.py info

# Test release script (dry run)
python scripts/release.py --help
```

### GitHub Actions Debugging
1. Go to GitHub → Actions tab
2. Click on the failed workflow
3. Expand the failed job to see error details
4. Check the "Artifacts" section for build outputs

## Security Notes

- The workflow uses `GITHUB_TOKEN` (automatically provided)
- No additional secrets are required
- All builds happen in GitHub's secure environment
- Release assets are automatically signed by GitHub

## Benefits

1. **Automated Quality**: Every change is tested automatically
2. **Consistent Builds**: Same build process every time
3. **Easy Releases**: One command creates a full release
4. **Documentation**: Build artifacts and release notes are generated
5. **Multi-format**: Supports both Anki addon and standalone distributions
6. **Version Management**: Automatic version tracking and tagging
