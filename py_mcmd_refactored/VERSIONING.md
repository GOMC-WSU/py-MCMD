# py-MCMD Versioning Strategy

py-MCMD uses **Semantic Versioning** with a Python-friendly version string format.

## Version format

Stable releases use:

`MAJOR.MINOR.PATCH`

Examples:

- `2.0.0`
- `2.1.0`
- `2.1.1`

Pre-release and development versions use PEP 440-compatible suffixes:

- Development snapshot: `MAJOR.MINOR.PATCH.devN`
- Release candidate: `MAJOR.MINOR.PATCHrcN`

Examples:

- `0.2.0.dev1`
- `0.2.0rc1`

## Meaning of version components

### MAJOR
Increment the major version for breaking changes, including changes such as:

- incompatible CLI behavior
- incompatible configuration/JSON behavior
- incompatible restart behavior
- incompatible output or logging conventions that users/scripts depend on

### MINOR
Increment the minor version for backward-compatible feature additions, including:

- new framework capabilities
- new optional configuration fields
- new supported workflows
- new user-facing functionality that does not break existing usage

### PATCH
Increment the patch version for backward-compatible fixes and small improvements, including:

- bug fixes
- correctness fixes
- non-breaking refactors
- documentation or test corrections tied to an existing release line

## Initial version for the refactored framework

The refactored py-MCMD framework starts at:

`2.0.0`

- FIFO implementation version

`2.1.0`

This indicates an early but usable release of the refactored architecture.

## Project policy

- py-MCMD must have one authoritative version string in the codebase.
- Other locations must read from that single source of truth.
- Version strings must not be duplicated manually across multiple code files.
- User-facing version output must always come from the same authoritative version source.

## Single source of truth

The authoritative framework version lives in:

`py_mcmd_refactored/version.py`

That module defines:

- `__version__`
- `get_version()`

The package root re-exports the version helpers from:

`py_mcmd_refactored/__init__.py`

## User-visible version exposure

The framework version is exposed in two places:

1. **CLI**
   - `python -m py_mcmd_refactored.cli.main --version`

2. **Startup flow**
   - the orchestrator startup logging emits the framework version at the beginning of a run

## How to bump the version

When preparing a new release:

### 1. Update the authoritative version
Edit:

`py_mcmd_refactored/version.py`

Change:

```python
__version__ = "2.1.0"