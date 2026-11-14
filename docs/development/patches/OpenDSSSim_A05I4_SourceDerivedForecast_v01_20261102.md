# A05I4 source-derived forecast oracle, runtime implementation candidate

This is a scoped **A05I4** implementation on the qualified A05I3 (229-file) baseline.
Only qualified A05I2 in-memory exogenous and A05I3 replay data are eligible; no new provider, forecast model, noise, scenario draws, controller action, fault/event or power-flow solve is introduced.

`OpenDSSSimulator.exogenous_forecast(H, channel_ids=None, entity_ids=None, required=True)` obtains a deterministic point forecast anchored at the **next logical decision** `k` (`t[k]`), not the most recent electrical sample. It is read-only and returns immutable `ForecastResult` / `ForecastValue` records with explicit issue/target UTC, episode/index/lead, source+binding hashes, canonical index/cycle, channel/entity and unit. `.to_dict()` produces a detached copy.

- **Tile**: reuses A05I3 source's original full-period index/cycle; strict failure is typed `ForecastCoverageError` and does not truncate the Plant.
- **No source**: `ForecastUnavailableError` for required requests or typed `NOT_CONFIGURED` for optional requests.
- **Explicit finite A05I2 source**: does not synthesize a replay policy; missing future samples fail closed.
- **PV**: same Faiman conversion/25°C fallback as A05I2. Signed PF uses the A05I2 reactive-power formula; multipliers are disclosed in pu without silently reading private native baselines.
- **Privacy**: only explicitly declared physical exogenous channels are returned; no voltages, device topology, backend handles, mutable truth table or forecast cache. The existing A04 Gym Dict and `info` remain untouched. Full A05I6 ControllerContext and observation permissions are **not** claimed here.
- **Scientific interpretation**: `oracle_perfect_exogenous` explicitly denotes perfect future-source knowledge, **not** an operational causal forecast. A05I5 forecast error remains unimplemented.
- **Authority**: zero AltDSS writes/solves on forecast lookup. Existing Option-A reset/step, H0–H3, A03/A04, both IEEE-123 feeders and R02A backend are immutable.

The independent validator must pass targeted A05I4+A05I1-I3+R02A and three fresh full regressions, with zero skips and JSON decode errors. Reliability concerns R01/R02 remain open.
