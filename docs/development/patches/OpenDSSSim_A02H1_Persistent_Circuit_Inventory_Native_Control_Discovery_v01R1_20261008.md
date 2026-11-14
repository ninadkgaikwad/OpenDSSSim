# OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_v01R1_20261008

## Patch identity

- Date: 2026-10-08
- Stage: A02H1
- Logical plant predecessor: `OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007`
- Physical shared-repository predecessor files: `72`
- Rebased predecessor source-manifest SHA256: `391A3AEC79882BFE2BCA7DF7DAFA2399AF42EE9A10A9FDD478727B5B84859983`
- Directed-input SHA256: `440A817B6226D12C260C70C1D7DAB6B329831F71A5CFCAA2090808EAB73B11FA`
- Environment: `scalebridge-dev-gpu-laptop`
- Environment mutation: **NONE**


## Revision note

The original v01 installer was intentionally blocked before payload installation
because the shared repository had advanced through the parallel controller-science
track. The drift audit found exactly 10 modified controller-science documents,
2 added controller-science files, 0 missing files, and no plant/source/test drift.

v01R1 therefore keeps the A02H1 plant implementation unchanged and rebases its
authority onto that exact 72-file state. All controller-science content is
preserved byte-for-byte and is outside the A02H1 payload.

## Purpose

Add persistent static circuit inventory and explicit native OpenDSS
control/protection relationship discovery without changing plant physics or
controller authority.

## Frozen contract

`docs/development/architecture/OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_Contract_v01R1_20261008.md`

## Key implementation decisions

- official OpenDSS/DSS-Extensions control-element catalog is used;
- `GICTransformer` is not treated as a control object;
- A02 full property snapshots are used only as one-time compiler input;
- persisted inventory strips dynamic property values/state;
- source identity is conservative whole-source-root content identity;
- valid inventories are loaded instead of rediscovered on each episode;
- cache invalidation is deterministic and explicit;
- existing Gym action/observation spaces remain unchanged.

## A02 predecessor validator adaptation

`validate_a02.py` now checks the frozen `A02_DISCOVERY_PATCH_ID` so A02 remains
a behavioral regression gate under successor patch IDs, matching the earlier A01
successor pattern.

## Rollback

Installer backs up modified predecessor files, removes newly added payload files,
and restores the exact 72-file rebased predecessor if any qualification gate fails.

## Successor

A03 — persistent seven semantic registries and mutability classification.
