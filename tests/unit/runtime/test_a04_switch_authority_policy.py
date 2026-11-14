"""A04I4A authority proof. Synthetic inventory; no AltDSS required."""
from dataclasses import replace
from types import SimpleNamespace
import pytest

from opendsssim.persistence.inventory_schema import NativeControlRelationship
from opendsssim.runtime.binding import RuntimeBindingError, _native_controls_to_disable


def _rel(**kwargs):
    fields=dict(source_full_name="SwtControl.sc1",source_class="SwtControl",
        role="SWITCHES",property_name="SwitchedObj",target_reference="Line.Feeder",
        target_full_name="Line.Feeder",target_kind="OBJECT",
        resolution="EXPLICIT_RESOLVED",terminal=1)
    fields.update(kwargs)
    return NativeControlRelationship(**fields)


def _inventory(*relations):
    return SimpleNamespace(
        objects=(SimpleNamespace(full_name="Line.Feeder", property_names=("Enabled",)),
                 SimpleNamespace(full_name="SwtControl.sc1", property_names=("Enabled",))),
        native_controls=(SimpleNamespace(full_name="SwtControl.sc1",dss_class="SwtControl",
                 property_names=("Enabled",)),),
        elements=(SimpleNamespace(full_name="Line.Feeder",dss_class="Line",num_terminals=2),),
        control_relationships=relations,
    )


def _problem(*, external=("Line.Feeder",), native=()):
    return SimpleNamespace(control_authority=SimpleNamespace(external_entities=external,native_entities=native))


def test_verified_switches_owns_exactly_the_native_switch_controller():
    assert _native_controls_to_disable(_problem(),_inventory(_rel())) == ("SwtControl.sc1",)
    assert _native_controls_to_disable(_problem(native=("Line.Feeder",), external=()),
                                       _inventory(_rel())) == ()


@pytest.mark.parametrize('change', [
    {'source_class':'Relay'}, {'source_full_name':'Relay.sc1'},
    {'property_name':'MonitoredObj'}, {'resolution':'EXPLICIT_UNRESOLVED'},
    {'target_kind':'BUS'}, {'terminal':None}, {'terminal':0}, {'terminal':3},
    {'target_full_name':None},
])
def test_malformed_or_ambiguous_switch_relation_fails_closed(change):
    with pytest.raises(RuntimeBindingError):
        _native_controls_to_disable(_problem(),_inventory(_rel(**change)))


def test_unresolved_switch_target_fails_closed_without_writes():
    with pytest.raises(RuntimeBindingError,match="Unresolved SWITCHES"):
        _native_controls_to_disable(_problem(),_inventory(_rel(target_full_name=None,
                                                   resolution="EXPLICIT_UNRESOLVED")))


def test_protection_and_monitoring_never_grant_suppression():
    monitor=_rel(role="MONITORS",source_full_name="Relay.rr1",source_class="Relay")
    protect=_rel(role="PROTECTS",source_full_name="Fuse.ff1",source_class="Fuse")
    assert _native_controls_to_disable(_problem(),_inventory(monitor,protect)) == ()


def test_hybrid_partition_conflict_fails_closed():
    # A malformed/disputed inventory can claim the same native controller for
    # both authority partitions; this MUST NOT be auto-resolved.
    rel_external=_rel()
    rel_native=_rel(role="CONTROLS",target_full_name="Capacitor.Cap1")
    with pytest.raises(RuntimeBindingError,match="HYBRID"):
        _native_controls_to_disable(_problem(native=("Capacitor.Cap1",)),
                                    _inventory(rel_external,rel_native))


def test_missing_native_enabled_property_fails_closed():
    inv=_inventory(_rel())
    native=replace(inv.native_controls[0], property_names=()) if hasattr(inv.native_controls[0],"__dataclass_fields__") else SimpleNamespace(
        full_name="SwtControl.sc1",dss_class="SwtControl",property_names=())
    obj=SimpleNamespace(full_name="SwtControl.sc1",property_names=())
    inv.native_controls=(native,)
    inv.objects=(inv.objects[0],obj)
    with pytest.raises(RuntimeBindingError,match="suppressible"):
        _native_controls_to_disable(_problem(),inv)
