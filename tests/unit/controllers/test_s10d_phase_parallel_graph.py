"""S10D P2 bus-level radiality must not count phase-disjoint regulator phases twice."""
from types import SimpleNamespace as NS
from opendsssim.controllers.reference.p2_graph import _graph, _phase_disjoint_regulator_corridor


def item(name,cls,buses,phases):
    return NS(native_entity=name,dss_class=cls,terminal_bus_specs=tuple(buses),num_phases=phases)


def context(more=()):
    elem=(item('Transformer.reg1a','Transformer',('150','150r'),3),
          item('Line.Sw1','Line',('150r','149'),3),
          item('Line.L30','Line',('149','25'),3),
          item('Transformer.reg3a','Transformer',('25.1','25r.1'),1),
          item('Transformer.reg3c','Transformer',('25.3','25r.3'),1),
          item('Line.L40','Line',('25r','86'),3),
          item('Transformer.reg4a','Transformer',('86.1','160r.1'),1),
          item('Transformer.reg4b','Transformer',('86.2','160r.2'),1),
          item('Transformer.reg4c','Transformer',('86.3','160r.3'),1))
    return NS(static_network=NS(source_bus_candidates=('150',),elements=elem+tuple(more)))


def test_phase_disjoint_regulator_corridor_is_one_bus_edge():
    c=context()
    energized,radial=_graph(c,{},set())
    assert radial and {'150','150r','149','25','25r','86','160r'}.issubset(energized)


def test_duplicate_same_phase_transformer_remains_cycle():
    c=context([item('Transformer.reg3a_duplicate','Transformer',('25.1','25r.1'),1)])
    _,radial=_graph(c,{},set())
    assert radial is False


def test_genuine_line_parallel_path_remains_cycle():
    c=context([item('Line.backfeed','Line',('150r','86'),3)])
    _,radial=_graph(c,{},set())
    assert radial is False


def test_fault_disconnection_remains_fail_closed():
    c=context()
    energized,radial=_graph(c,{}, {'line.sw1'})
    assert radial and '149' not in energized


def test_ambiguous_phase_specs_are_never_collapsed():
    e=item('Transformer.unknown','Transformer',('25','25r.3'),1)
    assert _phase_disjoint_regulator_corridor(e) is None
