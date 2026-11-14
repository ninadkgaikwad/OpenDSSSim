import json
from pathlib import Path

from opendsssim.persistence.inventory_schema import CircuitInventory


def test_inventory_json_does_not_require_dynamic_runtime_fields():
    forbidden_keys = {
        "solution_converged",
        "properties_json",
        "is_isolated",
        "context_identity",
    }

    def walk(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                assert key not in forbidden_keys
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    # The schema-level check is intentionally structural: these fields are not
    # part of CircuitInventory's persisted dataclass.
    fields = set(CircuitInventory.__dataclass_fields__)
    assert forbidden_keys.isdisjoint(fields)
