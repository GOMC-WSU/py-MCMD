# Engine layer

This package contains the shared engine base class and the concrete NAMD and
GOMC engine wrappers used by the orchestrator.

The engine layer is responsible for:

- resolving engine executables and templates,
- writing per-run input files,
- launching NAMD or GOMC through the subprocess runner,
- parsing engine output needed for handoff and energy checks,
- supporting dry-run execution for integration tests.

Engine-specific parsing and writer helpers live under `engines/namd/` and
`engines/gomc/`.