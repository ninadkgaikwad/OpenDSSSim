"""OpenDSSSim package foundation through A04I3 runtime integration."""

from .environment.simulator import OpenDSSSimulator
from .plant.solution import SolutionResult
from .problem import (
    ActionSpec,
    CompiledGymSpaces,
    ObservationSpec,
    ProblemSpec,
    ResolvedProblemSpec,
    compile_gym_spaces,
    resolve_problem,
)
from .persistence.inventory_schema import CircuitInventory
from .runtime import (
    ExecutionProfile, HistoryLevel, ProblemRuntimeBinding, RuntimeStepContext,
    SemanticRuntimeAccess, SemanticRuntimeAccessError,
)
from .semantics.policy import SEMANTIC_POLICY_SHA256
from .semantics.schema import SemanticRegistryBundle

__version__ = "0.1.0a6"

PATCH_ID = "OpenDSSSim_A03_Persistent_Seven_Semantic_Registries_v01R4_20261010"
A01_FOUNDATION_PATCH_ID = "OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005"
A02_DISCOVERY_PATCH_ID = "OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007"
A02H1_PATCH_ID = "OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_v01R1_20261008"
A03D1_DOCUMENTATION_PATCH_ID = "OpenDSSSim_A03D1_SemanticRegistries_DocumentationFreeze_v01_20261009"
A02_DISCOVERY_CONTRACT_ID = "OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_Contract_v01_20261006"
A02H1_CONTRACT_ID = "OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_Contract_v01R1_20261008"
A03_CONTRACT_ID = "OpenDSSSim_A03_Persistent_Seven_Semantic_Registries_Contract_v01_20261009"
A04I1_PATCH_ID = "OpenDSSSim_A04I1_ProblemContract_Resolution_GymSpaces_v01R1_20261020"
A04I2_PATCH_ID = "OpenDSSSim_A04I2_SemanticRuntimeAccess_AltDSSBinding_v01R1_20261020"
A04I3_PATCH_ID = "OpenDSSSim_A04I3_RuntimeBinding_Environment_History_Preflight_v01R3_20261021"

ARCHITECTURE_DOCUMENT_ID = "OpenDSSSim_A0_Architecture_Development_Plan_v01R1_20260930"
SMARTCOMMUNITY_AUDIT_DOCUMENT_ID = "OpenDSSSim_A0_SmartCommunitySim2_ReuseAdaptNewMatrix_v01_20260930"
PRE_A01_SOURCE_MANIFEST_SHA256 = "175411EEB2EFB0697D929E69DBD6EDCFE5524595A1E5D6F5426780EA9631E161"

__all__ = [
    "CircuitInventory",
    "SemanticRegistryBundle",
    "ProblemSpec",
    "ResolvedProblemSpec",
    "ObservationSpec",
    "ActionSpec",
    "CompiledGymSpaces",
    "resolve_problem",
    "compile_gym_spaces",
    "SemanticRuntimeAccess",
    "SemanticRuntimeAccessError",
    "ProblemRuntimeBinding",
    "RuntimeStepContext",
    "HistoryLevel",
    "ExecutionProfile",
    "OpenDSSSimulator",
    "SolutionResult",
    "SEMANTIC_POLICY_SHA256",
    "__version__",
    "PATCH_ID",
    "A01_FOUNDATION_PATCH_ID",
    "A02_DISCOVERY_PATCH_ID",
    "A02H1_PATCH_ID",
    "A03D1_DOCUMENTATION_PATCH_ID",
    "A02_DISCOVERY_CONTRACT_ID",
    "A02H1_CONTRACT_ID",
    "A03_CONTRACT_ID",
    "A04I1_PATCH_ID",
    "A04I2_PATCH_ID",
    "A04I3_PATCH_ID",
    "ARCHITECTURE_DOCUMENT_ID",
    "SMARTCOMMUNITY_AUDIT_DOCUMENT_ID",
    "PRE_A01_SOURCE_MANIFEST_SHA256",
]
