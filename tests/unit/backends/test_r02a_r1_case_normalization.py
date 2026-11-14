"""R02A-R1: exact capacitor manager normalization, retaining fail-closed identity."""

import pytest

from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.backends.base import OpenDSSSimBackendError


class FakeCapacitor:
    def __init__(self, full_name):
        self.full_name = full_name

    def FullName(self):
        return self.full_name


class FakeCapacitorManager:
    def __init__(self, full_name="Capacitor.C83"):
        self.full_name = full_name
        self.asked = []

    def find(self, requested):
        self.asked.append(requested)
        return FakeCapacitor(self.full_name)


class FakeContext:
    def __init__(self, manager):
        self.Capacitor = manager


def backend_with_fake(manager):
    # Avoid creating any native context for this isolated unit test.
    backend = object.__new__(AltDSSBackend)
    backend._context = FakeContext(manager)
    backend._closed = False
    backend._loaded_source = object()
    return backend


@pytest.mark.parametrize("object_ref", ["capacitor.c83", "Capacitor.C83", "CAPACITOR.C83"])
def test_capacitor_class_case_is_normalized_with_exact_object_identity(object_ref):
    manager = FakeCapacitorManager()
    backend = backend_with_fake(manager)
    assert backend._resolve_native_object(object_ref).FullName() == "Capacitor.C83"
    assert manager.asked == [object_ref.split(".", 1)[1]]


def test_matching_class_does_not_relax_native_object_identity():
    backend = backend_with_fake(FakeCapacitorManager("Capacitor.NotC83"))
    with pytest.raises(OpenDSSSimBackendError, match="Resolved native object mismatch"):
        backend._resolve_native_object("capacitor.c83")


def test_non_capacitor_classes_still_reject_unavailable_lowercase_manager():
    backend = backend_with_fake(FakeCapacitorManager())
    with pytest.raises(OpenDSSSimBackendError, match="manager not available"):
        backend._resolve_native_object("transformer.t1")


def test_unknown_capacitor_object_fails_closed():
    class MissingManager:
        def find(self, _):
            raise KeyError("unrecognized capacitor")
    backend = backend_with_fake(MissingManager())
    with pytest.raises(OpenDSSSimBackendError, match="Unable to resolve native object"):
        backend._resolve_native_object("capacitor.not_present")
