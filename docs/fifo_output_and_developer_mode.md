# FIFO output storage and developer mode

## Runtime modes

### Default mode (`developer_mode=false`)
- FIFO is the default output mechanism.
- Engine outputs are expected to flow through FIFO-backed handoff paths by default.
- Disk persistence is limited to explicit engine-specific allow-lists defined under `utils/`.
- Any output that is not allow-listed should be treated as FIFO-only.

### Developer mode (`developer_mode=true`)
- FIFO behavior remains the primary handoff mechanism.
- FIFO-managed outputs are also written to disk for inspection and debugging.
- This is a dual-write mode: FIFO plus filesystem persistence.
- Engine-specific disk allow-lists still exist, but developer mode additionally preserves FIFO-managed artifacts on disk.

## Configuration

Add the following optional JSON key:

```json
{
  "developer_mode": true
}
