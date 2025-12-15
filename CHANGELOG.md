## [1.1.3] - 2025-12-15

### Fixed
- **CRITICAL:** Fixed npm package to include `pyproject.toml` (required for pip installation)
- Removed `__pycache__/` build artifacts from package (saves 148KB)
- Removed `.egg-info/` metadata from package
- Package size reduced from 350KB to 190KB

### Notes
- v1.1.2 was broken due to missing `pyproject.toml`
- v1.1.2 has been deprecated
- All users should upgrade to v1.1.3+

## [1.1.2] - 2025-12-15 [DEPRECATED]
- ❌ Broken package - missing pyproject.toml
- ❌ Includes unnecessary build artifacts
- ⚠️  Use v1.1.3 instead
