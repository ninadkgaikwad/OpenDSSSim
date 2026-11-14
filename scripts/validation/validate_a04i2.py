"""Standalone A04I2 semantic-runtime-access qualification."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

from opendsssim import A04I2_PATCH_ID, __version__
from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.network.loading import CircuitSource
from opendsssim.runtime import SemanticRuntimeAccess
from opendsssim.semantics.schema import (
    NativePropertyAddress,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
)


EXPECTED_PATCH_ID = "OpenDSSSim_A04I2_SemanticRuntimeAccess_AltDSSBinding_v01R1_20261020"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def qualify(repo_root: Path) -> dict[str, Any]:
    fixture = repo_root / "tests" / "fixtures" / "a03_semantic" / "Master.dss"
    gates: dict[str, bool] = {}

    gates["patch_id"] = A04I2_PATCH_ID == EXPECTED_PATCH_ID
    gates["package_version"] = __version__ == "0.1.0a5"

    backend = AltDSSBackend()
    try:
        backend.load_circuit(CircuitSource.from_path(fixture))
        solved = backend.solve_snapshot()
        _require(solved.converged, "Initial A03 semantic fixture solve did not converge.")
        context_id = backend.context_identity
        access = SemanticRuntimeAccess(backend)

        pv = NativePropertyAddress("PVSystem.PV1", "kvar")
        original_q = float(access.read(pv))
        _require(float(access.write(pv, 11.25)) == 11.25, "PV kvar write/readback failed.")
        _require(abs(float(access.read(pv)) - 11.25) < 1e-12, "PV kvar semantic read failed.")
        access.write(pv, original_q)
        gates["native_property_read_write"] = True

        line_enabled = NativePropertyAddress("Line.Feeder", "Enabled")
        _require(bool(access.write(line_enabled, False)) is False, "Enabled=False write failed.")
        _require(bool(access.read(line_enabled)) is False, "Enabled=False readback failed.")
        _require(bool(access.write(line_enabled, True)) is True, "Enabled=True restore failed.")
        gates["enabled_false"] = True

        volts = access.read(RuntimeReadoutAddress("Bus", "source", "voltage"))
        pu = access.read(RuntimeReadoutAddress("Bus", "source", "pu_voltage"))
        _require(len(volts) == len(pu) and len(volts) > 0, "Bus readout shape mismatch.")
        _require(all(isinstance(v, complex) for v in volts), "Bus voltage is not complex-valued.")
        _require(all(isinstance(v, float) and math.isfinite(v) for v in pu), "Bus pu readout invalid.")
        gates["bus_readouts"] = True

        currents = access.read(RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "currents"))
        powers = access.read(RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "terminal_power"))
        losses = access.read(RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "losses"))
        open_state = access.read(RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "open_state"))
        _require(len(currents) > 0 and all(isinstance(v, complex) for v in currents), "Current readout failed.")
        _require(len(powers) == 2 and all(isinstance(v, complex) for v in powers), "Terminal power readout failed.")
        _require(isinstance(losses, complex), "Losses readout failed.")
        _require(open_state == (False, False), f"Unexpected initial open state: {open_state!r}")
        gates["element_readouts"] = True

        _require(access.read(RuntimeReadoutAddress("Solution", None, "converged")) is True, "Solution readout failed.")
        topology = access.read(RuntimeReadoutAddress("Topology", None, "connectivity"))
        _require("num_loops" in topology and "isolated_branches" in topology, "Topology readout failed.")
        gates["solution_topology_readouts"] = True

        _require(
            bool(access.write(NativePropertyAddress("RegControl.RC1", "Enabled"), False)) is False,
            "RegControl disable failed.",
        )
        tap_state = RuntimeReadoutAddress("Transformer", "Transformer.RegX", "taps")
        taps_before = access.read(tap_state)
        _require(len(taps_before) == 2, "Transformer tap readout shape mismatch.")
        target = 1.025
        taps_commanded = access.write(
            RuntimeCommandAddress("Transformer", "Transformer.RegX", "set_tap"),
            target,
        )
        _require(abs(float(taps_commanded[1]) - target) < 1e-12, "Tap command readback failed.")
        _require(backend.solve_snapshot().converged, "Post-tap solve failed.")
        taps_after = access.read(tap_state)
        _require(abs(float(taps_after[1]) - target) < 1e-12, "Tap did not persist with native control disabled.")
        gates["transformer_tap_command"] = True

        _require(
            bool(access.write(NativePropertyAddress("SwtControl.SC1", "Enabled"), False)) is False,
            "SwtControl disable failed.",
        )
        switch = RuntimeCommandAddress("CircuitElement", "Line.Feeder", "open_close")
        switch_state = RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "open_state")
        opened = access.write(switch, "OPEN")
        _require(bool(opened[0]) is True and bool(access.read(switch_state)[0]) is True, "OPEN command failed.")
        closed = access.write(switch, "CLOSED")
        _require(bool(closed[0]) is False and bool(access.read(switch_state)[0]) is False, "CLOSED command failed.")
        gates["switch_command"] = True

        gates["persistent_context_identity"] = backend.context_identity == context_id
    finally:
        backend.close()

    failed = [name for name, passed in gates.items() if not passed]
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "patch_id": EXPECTED_PATCH_ID,
        "repo_root": str(repo_root),
        "gates": gates,
        "failed_gates": failed,
        "status": "PASS" if not failed else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = qualify(args.repo_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"REPORT={args.output}")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] == "PASS":
        print("A04I2 STANDALONE VALIDATOR: PASS")
        return 0
    print("A04I2 STANDALONE VALIDATOR: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
