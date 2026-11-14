# B00I2R1 — native queue display/sentinel repair (guarded)

## Forensic evidence and reason
The B00I2 P0/P1/P2 combined campaign installed 260 tracked source files, but
failed all four new IEEE-123 native tests on the first solved reset. The
independent read-only diagnostic captured `ControlQueue.QueueSize = 0`,
`ControlQueue.NumActions = 0`, `ControlQueue.Queue = ["No events"]`, and
`Solution.EventLog = []` in each feeder. The previous backend/recorder incorrectly
required `len(Queue)` to equal `QueueSize`. The native "No events" display row
is not one pending action.

## Authorized repair
- Retain the native numeric `QueueSize` as pending-action count.
- Preserve the raw `Queue` display rows and `EventLog`, including sentinel
  strings, alongside a readback-format status and raw row count.
- Do not treat display rows as actions or infer timestamps/physical operations.
- Reject negative/invalid counts and contradictory nonzero count + empty sentinel.
- Keep native readback opt-in, read-only, after the same authoritative solve.
- Update the B00 metrics recorder to use action count without asserting display
  row parity, and expose both measurements for the HTML renderer and audit.
- Add pure unit tests for empty sentinel, real queue, mismatched display rows,
  contradictory readbacks, and malformed action counts.

## Boundaries
No changes to A04 Gym schemas, A05 replay, controller authority, feeder assets,
restoration models, B00I1 default behavior, or the renderer's data source.
B00 quasi-static Snapshot solves do not validate regulator delay timing.
R01 remains OPEN. R02 remains OPEN with mitigation qualified. B00 science
freeze is not authorized until the complete Windows gate campaign and an
independent evidence audit pass.
