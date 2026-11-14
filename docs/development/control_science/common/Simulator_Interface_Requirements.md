# Simulator Interface Requirements from Controller Science

**Status:** living C0-C3 interface ledger

This file records requirements discovered by the controller-science track that must be
implemented by the simulator track. It is not permission for controllers to bypass
OpenDSSSim.

| ID | Problem | Required simulator service | Why controller needs it | Needed by | Simulator stage | Status |
|---|---|---|---|---|---|---|
| CSI-001 | Common | Capability query | Decide supported/unsupported before instantiation | All | A02/A03 | OPEN |
| CSI-002 | Common | Circuit/native-object registry | Bind generalized selectors to actual feeder objects | All | A03 | OPEN |
| CSI-003 | Common | ProblemSpec | Freeze selected state/action/disturbance/constraint surface | All | A04 | OPEN |
| CSI-004 | Common | Read-only current observation/state view | Controller input without backend access | All | A04 | OPEN |
| CSI-005 | Common | Requested-action schema | Produce `a_req` using plant-owned semantics | All | A04 | OPEN |
| CSI-006 | Common | Explicit unsupported/error surface | Machine-readable compatibility outcome | All | A03/A04 | OPEN |
| CSI-007 | Common | Forecast view | Explicit future exogenous information | MPC/RL if used | A05 | OPEN |
| CSI-008 | Common | Non-mutating topology/model service | Graph logic / predictive optimization without plant mutation | P1/P2 ref+MPC | TBD | OPEN |
| CSI-009 | Common | Applied/realized action reporting | Fair diagnostics and requested-realized comparison | All | A04+ | OPEN |

Add entries only when supported by audited controller science.
