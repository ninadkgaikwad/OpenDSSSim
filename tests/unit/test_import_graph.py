"""Regression coverage for the A01R1 package import boundary."""


def test_public_import_graph_has_no_circular_initialization():
    import opendsssim
    from opendsssim.backends.base import DistributionBackend
    from opendsssim.plant import OpenDSSPlant, SolutionResult
    from opendsssim.plant.solution import SolutionResult as DirectSolutionResult

    assert opendsssim.SolutionResult is DirectSolutionResult
    assert SolutionResult is DirectSolutionResult
    assert OpenDSSPlant.__name__ == "OpenDSSPlant"
    assert DistributionBackend.__name__ == "DistributionBackend"
