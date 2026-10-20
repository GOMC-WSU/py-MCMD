# input models & validation

## `developer_mode`

`SimulationConfig` accepts an optional `developer_mode: bool` field.

- default: `false`
- missing key: treated as `false`
- invalid non-boolean values: rejected during validation

See `docs/fifo_output_and_developer_mode.md` for the runtime behavior contract:
- default mode uses FIFO-backed output handling with disk persistence controlled by engine-specific allow-lists,
- developer mode keeps FIFO behavior and additionally writes FIFO-managed outputs to disk.

## Versioning

Framework version policy, source-of-truth location, and version bump workflow are documented in the repository-level `VERSIONING.md`.
